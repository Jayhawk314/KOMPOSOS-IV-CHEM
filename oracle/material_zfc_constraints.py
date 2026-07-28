# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Material -> ZFC Constraint Bridge

Converts material bridge scorer results into ZFC logical constraints.
This lets the SeparationChecker detect when:
- A predicted material compatibility violates physical constraints
- Voltage windows don't overlap
- CTE mismatch exceeds tolerable limits
- Known incompatible pairs are flagged
- Bond lengths violate minimum/maximum physical bounds (NIST-derived)
- Coordination numbers are outside known stable ranges
- Charge balance is violated for ionic compounds

These constraints join the normal prediction constraints in the separation
checker, creating a unified logical view of both structural AND physical
evidence.

Adapted from chemistry/zfc_constraints.py (protein version) in the
sibling project KOMPOSOS-III-LAMBDA-max-3D.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Graceful ZFC import
try:
    from zfc.logic import Formula, atom, neg, conj, implies, const
    from zfc.separation import Constraint
    ZFC_LOGIC_AVAILABLE = True
except ImportError:
    ZFC_LOGIC_AVAILABLE = False

import math

from data.colabfit_loader import ColabFitClient, BondDistribution
from data.empirical_bond_statistics import get_stats


class BondConstraint:
    """Probabilistic bond constraint using cached empirical bond statistics."""

    def __init__(self, elem_a: str, elem_b: str, client: Optional[ColabFitClient] = None,
                 bounds: Optional[tuple] = None):
        self.elem_a = elem_a
        self.elem_b = elem_b
        self.client = client or ColabFitClient()
        self.distribution = self.client.get_bond_distribution(elem_a, elem_b, bounds=bounds)
        
    def probability_valid(self, distance: float) -> float:
        """Return P(distance is physically plausible)."""
        stats = get_stats(self.elem_a, self.elem_b)
        if stats is not None:
            std = float(stats["std"])
            if std > 0:
                z = (float(distance) - float(stats["mean"])) / std
                return math.exp(-0.5 * z * z)

        # Fallback for bounds-only or generic distributions: centrality in the CDF.
        cdf_val = self.distribution.cdf(distance)
        return 1.0 - 2.0 * abs(0.5 - cdf_val)

    def is_valid(self, distance: float, threshold: float = 0.05) -> bool:
        """Flag as invalid if P(distance) < 5%."""
        return self.probability_valid(distance) > threshold


def _oxidation_state_combos(elements_with_states):
    """
    Generate all combinations of oxidation states for elements.

    Args:
        elements_with_states: List of (elem, amt, states_list) tuples.

    Yields:
        Tuples of oxidation states, one per element.
    """
    if not elements_with_states:
        yield ()
        return

    first_elem, first_amt, first_states = elements_with_states[0]
    rest = elements_with_states[1:]

    for state in first_states:
        for rest_combo in _oxidation_state_combos(rest):
            yield (state,) + rest_combo


class MaterialZFCBridge:
    """
    Converts material bridge validation results to ZFC constraints.

    Usage:
        bridge = MaterialZFCBridge()
        constraints = bridge.score_constraints(
            mat_a="NMC811",
            mat_b="LLZO",
            scores={"ion_transport": ScorerResult(0.8, ...), ...},
        )
        # constraints is List[Constraint] ready for SeparationChecker
    """

    def __init__(
        self,
        score_threshold: float = 0.45,
        veto_threshold: float = 0.20,
        cte_threshold: float = 0.20,
        voltage_margin: float = 0.5,
    ):
        """
        Args:
            score_threshold: scorer value above which material pair is "compatible"
            veto_threshold: scorer value below which a hard veto is issued
            cte_threshold: fractional CTE mismatch above which materials are incompatible
            voltage_margin: minimum voltage headroom (V) for stability
        """
        self.score_threshold = score_threshold
        self.veto_threshold = veto_threshold
        self.cte_threshold = cte_threshold
        self.voltage_margin = voltage_margin

    @property
    def is_available(self) -> bool:
        """Whether ZFC logic imports succeeded."""
        return ZFC_LOGIC_AVAILABLE

    def score_constraints(
        self,
        mat_a: str,
        mat_b: str,
        scores: Dict[str, Any],
    ) -> List:
        """
        Convert 5 bridge scorer results into ZFC logical constraints.

        For each scorer:
          score > threshold -> atom("scorer_name_compatible")
          score < veto_threshold -> atom("scorer_name_veto") -> implies(veto, neg(viable))
          All compatible -> conj(...) -> implies(conj, atom("interface_viable"))

        Args:
            mat_a: First material name
            mat_b: Second material name
            scores: Dict mapping scorer name to ScorerResult (or any object with .score)

        Returns:
            List[Constraint] ready for SeparationChecker. Empty if ZFC unavailable.
        """
        if not ZFC_LOGIC_AVAILABLE:
            return []

        constraints = []
        a = const(mat_a)
        b = const(mat_b)
        compatible_atoms = []

        scorer_names = [
            'ion_transport', 'electrochemical_stability',
            'interface_compatibility', 'mechanical_compatibility',
            'degradation_penalty',
        ]
        scorer_names.extend(
            name for name in scores
            if name.startswith("md_") and name not in scorer_names
        )

        for scorer_name in scorer_names:
            result = scores.get(scorer_name)
            if result is None:
                continue

            score_val = result.score if hasattr(result, 'score') else float(result)

            if score_val >= self.score_threshold:
                # Compatible for this scorer
                compat = atom(f"{scorer_name}_compatible", a, b)
                compatible_atoms.append(compat)
                constraints.append(Constraint(
                    formula=compat,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": f"{scorer_name}_compatible",
                        "confidence": score_val,
                        "strategy": f"material_{scorer_name}",
                    },
                    confidence=score_val,
                    strategy=f"material_{scorer_name}",
                ))
            elif score_val < self.veto_threshold:
                # Hard veto — this scorer says incompatible
                veto = atom(f"{scorer_name}_veto", a, b)
                viable = atom("interface_viable", a, b)
                veto_implies_not_viable = implies(veto, neg(viable))

                constraints.append(Constraint(
                    formula=veto,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": f"{scorer_name}_veto",
                        "confidence": 1.0 - score_val,
                        "strategy": f"material_{scorer_name}",
                    },
                    confidence=1.0 - score_val,
                    strategy=f"material_{scorer_name}",
                ))
                constraints.append(Constraint(
                    formula=veto_implies_not_viable,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "veto_implies_not_viable",
                        "confidence": 1.0 - score_val,
                        "strategy": f"material_{scorer_name}_veto_rule",
                    },
                    confidence=1.0 - score_val,
                    strategy=f"material_{scorer_name}_veto_rule",
                ))

        # If all scorers are compatible, assert interface viability
        if len(compatible_atoms) == len(scorer_names):
            viable = atom("interface_viable", a, b)
            constraints.append(Constraint(
                formula=viable,
                source_prediction={
                    "source": mat_a, "target": mat_b,
                    "relation": "interface_viable",
                    "confidence": 0.9,
                    "strategy": "material_all_compatible",
                },
                confidence=0.9,
                strategy="material_all_compatible",
            ))

        return constraints

    def voltage_constraints(
        self,
        mat_a: str,
        mat_b: str,
        voltage_window_a: Optional[Any] = None,
        voltage_window_b: Optional[Any] = None,
        oxidation_potential: Optional[float] = None,
        reduction_potential: Optional[float] = None,
    ) -> List:
        """
        Voltage window overlap check.

        Args:
            mat_a: Electrode material name
            mat_b: Electrolyte material name
            voltage_window_a: VoltageWindow of electrode (has .lower, .upper)
            voltage_window_b: VoltageWindow of electrolyte (if applicable)
            oxidation_potential: Electrolyte oxidation potential (V vs Li/Li+)
            reduction_potential: Electrolyte reduction potential (V vs Li/Li+)

        Returns:
            List[Constraint]
        """
        if not ZFC_LOGIC_AVAILABLE:
            return []

        constraints = []
        a = const(mat_a)
        b = const(mat_b)

        if voltage_window_a is not None and oxidation_potential is not None:
            headroom = oxidation_potential - voltage_window_a.upper
            if headroom >= self.voltage_margin:
                formula = atom("voltage_compatible", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "voltage_compatible",
                        "confidence": min(1.0, headroom / 2.0),
                        "strategy": "material_voltage",
                    },
                    confidence=min(1.0, headroom / 2.0),
                    strategy="material_voltage",
                ))
            elif headroom < 0:
                formula = neg(atom("voltage_compatible", a, b))
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "voltage_incompatible",
                        "confidence": min(1.0, abs(headroom) / 1.0),
                        "strategy": "material_voltage",
                    },
                    confidence=min(1.0, abs(headroom) / 1.0),
                    strategy="material_voltage",
                ))

        if voltage_window_a is not None and reduction_potential is not None:
            headroom = voltage_window_a.lower - reduction_potential
            if headroom < -self.voltage_margin:
                formula = atom("reduction_risk", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "reduction_risk",
                        "confidence": min(1.0, abs(headroom) / 2.0),
                        "strategy": "material_voltage",
                    },
                    confidence=min(1.0, abs(headroom) / 2.0),
                    strategy="material_voltage",
                ))

        return constraints

    def thermal_constraints(
        self,
        mat_a: str,
        mat_b: str,
        cte_a: Optional[float] = None,
        cte_b: Optional[float] = None,
        thermal_stability_a: Optional[float] = None,
        thermal_stability_b: Optional[float] = None,
    ) -> List:
        """
        CTE mismatch and thermal stability constraints.

        Args:
            mat_a: First material name
            mat_b: Second material name
            cte_a: Coefficient of thermal expansion for mat_a (ppm/K)
            cte_b: Coefficient of thermal expansion for mat_b (ppm/K)
            thermal_stability_a: Max operating temperature for mat_a (C)
            thermal_stability_b: Max operating temperature for mat_b (C)

        Returns:
            List[Constraint]
        """
        if not ZFC_LOGIC_AVAILABLE:
            return []

        constraints = []
        a = const(mat_a)
        b = const(mat_b)

        # CTE mismatch
        if cte_a is not None and cte_b is not None:
            max_cte = max(abs(cte_a), abs(cte_b))
            if max_cte > 0:
                mismatch = abs(cte_a - cte_b) / max_cte
                if mismatch < self.cte_threshold:
                    formula = atom("cte_compatible", a, b)
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": "cte_compatible",
                            "confidence": 1.0 - mismatch,
                            "strategy": "material_thermal",
                        },
                        confidence=1.0 - mismatch,
                        strategy="material_thermal",
                    ))
                else:
                    formula = neg(atom("cte_compatible", a, b))
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": "cte_incompatible",
                            "confidence": min(1.0, mismatch),
                            "strategy": "material_thermal",
                        },
                        confidence=min(1.0, mismatch),
                        strategy="material_thermal",
                    ))

        # Thermal stability floor
        if thermal_stability_a is not None and thermal_stability_b is not None:
            min_stability = min(thermal_stability_a, thermal_stability_b)
            if min_stability < 100:
                formula = atom("thermal_risk", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "thermal_risk",
                        "confidence": max(0.5, 1.0 - min_stability / 200.0),
                        "strategy": "material_thermal",
                    },
                    confidence=max(0.5, 1.0 - min_stability / 200.0),
                    strategy="material_thermal",
                ))
            elif min_stability >= 200:
                formula = atom("thermal_stable", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "thermal_stable",
                        "confidence": min(1.0, min_stability / 500.0),
                        "strategy": "material_thermal",
                    },
                    confidence=min(1.0, min_stability / 500.0),
                    strategy="material_thermal",
                ))

        return constraints

    def chemical_constraints(
        self,
        mat_a: str,
        mat_b: str,
        known_bad_pair: bool = False,
        shared_failure_modes: Optional[List[str]] = None,
    ) -> List:
        """
        Known incompatible pairs from bridge veto lists.

        Args:
            mat_a: First material name
            mat_b: Second material name
            known_bad_pair: Whether this is a known incompatible pair
            shared_failure_modes: List of shared critical failure modes

        Returns:
            List[Constraint]
        """
        if not ZFC_LOGIC_AVAILABLE:
            return []

        constraints = []
        a = const(mat_a)
        b = const(mat_b)

        if known_bad_pair:
            formula = atom("known_incompatible", a, b)
            viable = atom("interface_viable", a, b)
            constraints.append(Constraint(
                formula=formula,
                source_prediction={
                    "source": mat_a, "target": mat_b,
                    "relation": "known_incompatible",
                    "confidence": 0.95,
                    "strategy": "material_chemical",
                },
                confidence=0.95,
                strategy="material_chemical",
            ))
            constraints.append(Constraint(
                formula=implies(formula, neg(viable)),
                source_prediction={
                    "source": mat_a, "target": mat_b,
                    "relation": "incompatible_implies_not_viable",
                    "confidence": 0.95,
                    "strategy": "material_chemical_rule",
                },
                confidence=0.95,
                strategy="material_chemical_rule",
            ))

        if shared_failure_modes:
            critical = {'thermal_runaway', 'dendrite_growth'}
            shared_critical = [f for f in shared_failure_modes if f in critical]
            if shared_critical:
                formula = atom("shared_critical_failures", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "shared_critical_failures",
                        "confidence": 0.8,
                        "strategy": "material_chemical",
                    },
                    confidence=0.8,
                    strategy="material_chemical",
                ))

        return constraints

    # ─────────────────────────────────────────────────────────────────────
    # NIST-derived bonding constraints
    # ─────────────────────────────────────────────────────────────────────
    #
    # Bond length bounds from NIST Interatomic Potentials Repository and
    # CRC Handbook of Chemistry and Physics. These are hard physical limits:
    # if a predicted structure violates them, it is flagged as HOLLOW.
    #
    # Format: (element_a, element_b) -> (min_angstrom, max_angstrom)
    # Min = sum of covalent radii * 0.8 (repulsive wall)
    # Max = typical bond length * 1.4 (beyond this, no bond)

    BOND_LENGTH_BOUNDS = {
        # ─── Metal-oxygen bonds (NIST EAM + CRC) ─────────────────────
        ("Li", "O"): (1.60, 2.40),   # Li2O, LiCoO2, LiMn2O4
        ("Na", "O"): (1.95, 2.80),   # NaCoO2, NaFeO2
        ("Mg", "O"): (1.75, 2.30),   # MgO
        ("Al", "O"): (1.65, 2.10),   # Al2O3, AlPO4
        ("Ca", "O"): (2.00, 2.80),   # CaO, CaTiO3
        ("Ti", "O"): (1.75, 2.25),   # TiO2
        ("Mn", "O"): (1.75, 2.25),   # MnO2, LiMnO2
        ("Fe", "O"): (1.75, 2.20),   # Fe2O3, LiFePO4
        ("Co", "O"): (1.75, 2.15),   # CoO, LiCoO2
        ("Ni", "O"): (1.75, 2.15),   # NiO, LiNiO2
        ("Cu", "O"): (1.70, 2.20),   # CuO, Cu2O
        ("Zn", "O"): (1.75, 2.20),   # ZnO
        ("Zr", "O"): (1.85, 2.40),   # ZrO2, Li7La3Zr2O12
        ("La", "O"): (2.20, 2.90),   # La2O3, LLZO
        ("Ba", "O"): (2.40, 3.10),   # BaO, BaTiO3
        ("Sr", "O"): (2.20, 2.90),   # SrO, SrTiO3
        ("Y", "O"):  (2.10, 2.60),   # Y2O3, YSZ
        ("Ce", "O"): (2.15, 2.65),   # CeO2
        ("Si", "O"): (1.55, 1.80),   # SiO2
        ("P", "O"):  (1.45, 1.65),   # PO4 groups (LiFePO4)
        ("Ge", "O"): (1.65, 1.95),   # GeO2
        # ─── Metal-sulfur bonds ───────────────────────────────────────
        ("Li", "S"): (2.10, 2.80),   # Li2S, LGPS
        ("Na", "S"): (2.50, 3.20),   # Na2S, Na3PS4
        ("Mo", "S"): (2.25, 2.60),   # MoS2
        ("Fe", "S"): (2.05, 2.50),   # FeS2
        ("Zn", "S"): (2.15, 2.60),   # ZnS
        ("Cu", "S"): (2.10, 2.50),   # Cu2S
        # ─── Metal-nitrogen bonds ─────────────────────────────────────
        ("Ti", "N"): (1.85, 2.35),   # TiN
        ("Al", "N"): (1.75, 2.15),   # AlN
        ("Ga", "N"): (1.80, 2.15),   # GaN
        ("Si", "N"): (1.65, 1.90),   # Si3N4
        ("B", "N"):  (1.35, 1.65),   # BN
        ("Li", "N"): (1.85, 2.30),   # Li3N
        ("Zr", "N"): (1.95, 2.45),   # ZrN
        # ─── III-V semiconductor bonds ────────────────────────────────
        ("Ga", "As"): (2.30, 2.65),  # GaAs
        ("Ga", "P"):  (2.20, 2.55),  # GaP
        ("In", "P"):  (2.40, 2.75),  # InP
        ("In", "As"): (2.50, 2.85),  # InAs
        ("Al", "As"): (2.25, 2.60),  # AlAs
        # ─── Metal-carbon bonds ───────────────────────────────────────
        ("Ti", "C"): (1.90, 2.35),   # TiC
        ("W", "C"):  (1.85, 2.25),   # WC
        ("Si", "C"): (1.75, 2.05),   # SiC
        # ─── Metal-fluorine bonds ─────────────────────────────────────
        ("Li", "F"): (1.55, 2.10),   # LiF
        ("Na", "F"): (1.90, 2.50),   # NaF
        ("Ca", "F"): (2.05, 2.70),   # CaF2
        ("Al", "F"): (1.60, 2.00),   # AlF3
        # ─── Metal-metal bonds (intermetallics) ──────────────────────
        ("Ni", "Al"): (2.30, 2.80),  # NiAl, Ni3Al
        ("Ti", "Al"): (2.50, 3.10),  # TiAl
        ("Fe", "Co"): (2.35, 2.75),  # FeCo
        ("Ni", "Ti"): (2.40, 2.90),  # NiTi (shape memory)
    }

    # Coordination number bounds from crystal chemistry.
    # Format: element -> (min_CN, max_CN) for the most common structures.
    # Derived from Shannon ionic radii / Pauling rules / ICSD statistics.
    COORDINATION_BOUNDS = {
        "Li": (2, 8),    # 4 (tetrahedral) or 6 (octahedral) typical
        "Na": (4, 9),    # 6 (octahedral) or 8 (cubic) typical
        "K":  (6, 12),   # 8-12 typical (large cation)
        "Mg": (4, 6),    # 6 (octahedral) dominant
        "Ca": (6, 12),   # 6-8 typical
        "Ba": (6, 12),   # 8-12 typical
        "Sr": (6, 12),   # 8-12 typical
        "Al": (4, 6),    # 4 (tetrahedral) or 6 (octahedral)
        "Si": (4, 6),    # 4 (tetrahedral) dominant, 6 under pressure
        "Ti": (4, 6),    # 6 (octahedral) dominant
        "V":  (4, 6),    # 4-6
        "Cr": (4, 6),    # 6 (octahedral) dominant
        "Mn": (4, 6),    # 4, 5, or 6
        "Fe": (4, 6),    # 4 (tetrahedral) or 6 (octahedral)
        "Co": (4, 6),    # 4 or 6
        "Ni": (4, 6),    # 4 (square planar) or 6 (octahedral)
        "Cu": (2, 6),    # 2 (linear), 4, or 6
        "Zn": (4, 6),    # 4 (tetrahedral) dominant
        "Zr": (6, 8),    # 6-8
        "La": (6, 12),   # 8-12 (large cation)
        "Ce": (6, 12),   # 8-12
        "Y":  (6, 9),    # 6-8
        "O":  (2, 6),    # 2-4 typical (anion)
        "S":  (2, 6),    # 2-6
        "F":  (1, 6),    # 1-4 typical (anion)
        "N":  (2, 4),    # 3-4 typical (anion)
        "P":  (4, 6),    # 4 (tetrahedral in PO4)
        "Ge": (4, 6),    # 4 (tetrahedral)
        "Ga": (4, 6),    # 4 (tetrahedral in III-V)
        "In": (4, 6),    # 4-6
        "B":  (3, 4),    # 3 (trigonal) or 4 (tetrahedral)
    }

    # Common oxidation states for charge balance checking.
    # Format: element -> list of allowed oxidation states.
    ALLOWED_OXIDATION_STATES = {
        "Li": [1],        "Na": [1],        "K":  [1],
        "Mg": [2],        "Ca": [2],        "Ba": [2],
        "Sr": [2],        "Al": [3],        "Si": [4],
        "Ti": [2, 3, 4],  "V":  [2, 3, 4, 5],  "Cr": [2, 3, 6],
        "Mn": [2, 3, 4, 7], "Fe": [2, 3],   "Co": [2, 3],
        "Ni": [2, 3],     "Cu": [1, 2],     "Zn": [2],
        "Zr": [4],        "La": [3],        "Ce": [3, 4],
        "Y":  [3],        "Ge": [2, 4],     "Ga": [3],
        "In": [3],        "Nb": [3, 5],     "Mo": [4, 6],
        "W":  [4, 6],     "Pb": [2, 4],     "Bi": [3, 5],
        "Sc": [3],        "Hf": [4],        "Ta": [5],
        "O":  [-2],       "S":  [-2],       "F":  [-1],
        "Cl": [-1],       "N":  [-3],       "P":  [3, 5],
        "B":  [3],        "C":  [-4, 4],    "H":  [-1, 1],
    }

    def bonding_constraints(
        self,
        mat_a: str,
        mat_b: str,
        bond_lengths: Optional[Dict[tuple, float]] = None,
        coordination_numbers: Optional[Dict[str, int]] = None,
        composition: Optional[Dict[str, float]] = None,
    ) -> List:
        """
        NIST-derived bonding constraints: bond lengths, coordination numbers,
        and charge balance.

        These are hard physical axioms. Any violation means the predicted
        structure is physically impossible and should be flagged HOLLOW.

        Args:
            mat_a: First material name (for constraint labeling)
            mat_b: Second material name (for constraint labeling)
            bond_lengths: Dict mapping (elem_a, elem_b) -> length_angstrom.
                Each pair is checked against BOND_LENGTH_BOUNDS.
            coordination_numbers: Dict mapping element -> coordination number.
                Checked against COORDINATION_BOUNDS.
            composition: Dict mapping element -> stoichiometry (e.g. {"Li": 1, "Fe": 1, "P": 1, "O": 4}).
                Used for charge balance check.

        Returns:
            List[Constraint] -- violations generate neg() constraints.
        """
        if not ZFC_LOGIC_AVAILABLE:
            return []

        constraints = []
        a = const(mat_a)
        b = const(mat_b)

        # ── 1. Bond length bounds ───────────────��─────────────────────
        if bond_lengths:
            for (elem_a, elem_b), length in bond_lengths.items():
                # Look up bounds in either ordering
                bounds = (self.BOND_LENGTH_BOUNDS.get((elem_a, elem_b))
                          or self.BOND_LENGTH_BOUNDS.get((elem_b, elem_a)))
                if bounds is None:
                    continue  # Skip pairs without physical data
                constraint = BondConstraint(elem_a, elem_b, bounds=bounds)
                p_valid = constraint.probability_valid(length)
                
                if not constraint.is_valid(length):
                    # Physically implausible regime
                    formula = atom("bond_physically_implausible", a, b)
                    viable = atom("interface_viable", a, b)
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": f"bond_implausible_{elem_a}_{elem_b}_dist{length:.2f}",
                            "confidence": 1.0 - p_valid,
                            "strategy": "colabfit_dynamic_potential",
                        },
                        confidence=1.0 - p_valid,
                        strategy="colabfit_dynamic_potential",
                    ))
                    constraints.append(Constraint(
                        formula=implies(formula, neg(viable)),
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": "implausible_implies_not_viable",
                            "confidence": 0.95,
                            "strategy": "colabfit_dynamic_rule",
                        },
                        confidence=0.95,
                        strategy="colabfit_dynamic_rule",
                    ))
                else:
                    # Physically plausible bond length
                    formula = atom("bond_length_plausible", a, b)
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": f"bond_plausible_{elem_a}_{elem_b}_dist{length:.2f}",
                            "confidence": p_valid,
                            "strategy": "colabfit_dynamic_potential",
                        },
                        confidence=p_valid,
                        strategy="colabfit_dynamic_potential",
                    ))

        # ── 2. Coordination number bounds ─────────────────────────────
        if coordination_numbers:
            for elem, cn in coordination_numbers.items():
                bounds = self.COORDINATION_BOUNDS.get(elem)
                if bounds is None:
                    continue

                min_cn, max_cn = bounds
                if cn < min_cn or cn > max_cn:
                    formula = atom("coordination_violation", a, b)
                    viable = atom("interface_viable", a, b)
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": f"coordination_violation_{elem}_CN{cn}",
                            "confidence": 0.85,
                            "strategy": "nist_coordination",
                        },
                        confidence=0.85,
                        strategy="nist_coordination",
                    ))
                    constraints.append(Constraint(
                        formula=implies(formula, neg(viable)),
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": "coordination_violation_implies_not_viable",
                            "confidence": 0.85,
                            "strategy": "nist_coordination_rule",
                        },
                        confidence=0.85,
                        strategy="nist_coordination_rule",
                    ))
                else:
                    formula = atom("coordination_valid", a, b)
                    constraints.append(Constraint(
                        formula=formula,
                        source_prediction={
                            "source": mat_a, "target": mat_b,
                            "relation": f"coordination_valid_{elem}_CN{cn}",
                            "confidence": 0.85,
                            "strategy": "nist_coordination",
                        },
                        confidence=0.85,
                        strategy="nist_coordination",
                    ))

        # ── 3. Charge balance ─────────────────────────────────────────
        if composition:
            # For elements with multiple oxidation states, try all
            # combinations and pick the one closest to charge neutrality.
            # This handles cases like P (+3 or +5) in phosphates.
            elements_with_states = []
            for elem, amt in composition.items():
                states = self.ALLOWED_OXIDATION_STATES.get(elem)
                if states is None:
                    continue
                elements_with_states.append((elem, amt, states))

            # Greedy approach: fix anion charges first (usually unambiguous),
            # then for each cation try the state that best balances.
            anion_charge = 0.0
            cation_elements = []
            for elem, amt, states in elements_with_states:
                if all(s < 0 for s in states):
                    # Anion -- use its (typically unique) state
                    anion_charge += states[0] * amt
                else:
                    cation_elements.append((elem, amt, states))

            # Find best cation state combination to neutralize anions
            best_imbalance = float('inf')
            for combo in _oxidation_state_combos(cation_elements):
                cation_charge = sum(s * amt for (_, amt, _), s in zip(cation_elements, combo))
                imbalance = abs(cation_charge + anion_charge)
                if imbalance < best_imbalance:
                    best_imbalance = imbalance

            total_atoms = sum(composition.values())
            relative_imbalance = best_imbalance / max(total_atoms, 1)

            if relative_imbalance > 0.15:
                formula = atom("charge_imbalanced", a, b)
                viable = atom("interface_viable", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "charge_imbalanced",
                        "confidence": min(1.0, relative_imbalance),
                        "strategy": "nist_charge_balance",
                    },
                    confidence=min(1.0, relative_imbalance),
                    strategy="nist_charge_balance",
                ))
                constraints.append(Constraint(
                    formula=implies(formula, neg(viable)),
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "charge_imbalance_implies_not_viable",
                        "confidence": 0.80,
                        "strategy": "nist_charge_balance_rule",
                    },
                    confidence=0.80,
                    strategy="nist_charge_balance_rule",
                ))
            else:
                formula = atom("charge_balanced", a, b)
                constraints.append(Constraint(
                    formula=formula,
                    source_prediction={
                        "source": mat_a, "target": mat_b,
                        "relation": "charge_balanced",
                        "confidence": max(0.7, 1.0 - relative_imbalance),
                        "strategy": "nist_charge_balance",
                    },
                    confidence=max(0.7, 1.0 - relative_imbalance),
                    strategy="nist_charge_balance",
                ))

        return constraints
