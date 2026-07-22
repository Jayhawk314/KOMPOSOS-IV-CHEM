# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery Interface Validator
==============================

Validates electrochemical interface viability between two materials,
analogous to chemistry/van_der_waals.py's VanDerWaalsConstraints.validate_structure()
and the ProductionPhysicsValidator pattern in the protein bridge.

Pattern:
  Protein bridge:  "Can residue i contact residue j?"
  Battery bridge:  "Can material A interface with material B?"

The validator combines all five interaction scorers into a weighted
composite InterfaceScore with configurable weights and thresholds.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from battery_bridge.material_properties import BatteryMaterial, get_material


def _element_symbols(formula: str) -> Set[str]:
    """Element symbols in a chemical formula.

    Parses capital-letter-plus-optional-lowercase tokens so that, for example,
    'Si' yields {'Si'} (silicon) and never a spurious {'S'} (sulfur), while
    'Li2S' correctly yields {'Li', 'S'}.
    """
    return set(re.findall(r"[A-Z][a-z]?", formula or ""))
from battery_bridge.interaction_scoring import (
    score_ion_transport,
    score_electrochemical_stability,
    score_interface_compatibility,
    score_mechanical_compatibility,
    score_degradation_penalty,
    ScorerResult,
)

#: Score ceiling applied when a physical veto fires. Well below the 0.50
#: viability threshold, matching the ceramic/polymer bridges' vetoed band, so a
#: vetoed pair can never surface a score that outranks a viable one.
VETO_SCORE_CAP = 0.35

def _vetoed_score(total: float) -> float:
    """Map a vetoed composite below the viability threshold, PRESERVING ORDER.

    A hard clamp (``min(total, CAP)``) collapses every vetoed pair onto one
    value, which destroys ranking information among rejected candidates and
    manufactures exactly the kind of constant, non-discriminating score this
    codebase treats as a defect elsewhere. Scaling instead keeps the ordering
    (a vetoed pair that was strong on its other axes still ranks above one that
    was weak) while guaranteeing the result sits below ``VETO_SCORE_CAP`` and
    therefore below the viability threshold.
    """
    return VETO_SCORE_CAP * max(0.0, min(1.0, total))



@dataclass
class InterfaceConditions:
    """Operating conditions that affect interface viability."""
    temperature_C: float = 25.0       # Operating temperature
    c_rate: float = 1.0               # Charge/discharge rate (1C default)
    cycle_number: int = 0             # Cycle count (fresh = 0)
    pressure_MPa: float = 0.0        # Stack pressure (relevant for solid-state)


@dataclass
class BatteryInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors the EnergyBreakdown dataclass pattern from chemistry/energy_functions.py.
    """
    total: float                       # Weighted composite (0-1)
    ion_transport: float               # Component score
    electrochemical_stability: float   # Component score
    interface_compatibility: float     # Component score
    mechanical_compatibility: float    # Component score
    degradation_penalty: float         # Component score
    viable: bool                       # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'ion_transport': round(self.ion_transport, 4),
            'electrochemical_stability': round(self.electrochemical_stability, 4),
            'interface_compatibility': round(self.interface_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'degradation_penalty': round(self.degradation_penalty, 4),
            'viable': self.viable,
        }


# Backward-compatible alias (original name used throughout codebase)
InterfaceScore = BatteryInterfaceScore


@dataclass
class InterfaceWeights:
    """Configurable weights for the five scoring components."""
    ion_transport: float = 0.25
    electrochemical_stability: float = 0.30
    interface_compatibility: float = 0.20
    mechanical_compatibility: float = 0.10
    degradation_penalty: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.ion_transport + self.electrochemical_stability +
                 self.interface_compatibility + self.mechanical_compatibility +
                 self.degradation_penalty)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'InterfaceWeights':
        """Default weights emphasizing electrochemical stability."""
        return cls()

    @classmethod
    def mechanical_focus(cls) -> 'InterfaceWeights':
        """Weights for solid-state cells where mechanical issues dominate."""
        return cls(
            ion_transport=0.20,
            electrochemical_stability=0.20,
            interface_compatibility=0.15,
            mechanical_compatibility=0.30,
            degradation_penalty=0.15,
        )

    @classmethod
    def safety_focus(cls) -> 'InterfaceWeights':
        """Weights emphasizing degradation and thermal safety."""
        return cls(
            ion_transport=0.15,
            electrochemical_stability=0.25,
            interface_compatibility=0.15,
            mechanical_compatibility=0.10,
            degradation_penalty=0.35,
        )


class BatteryInterfaceValidator:
    """
    Validates material interface viability for battery applications.

    Mirrors the pattern of VanDerWaalsConstraints.validate_structure() and
    ProductionPhysicsValidator from the protein bridge.

    Usage:
        validator = BatteryInterfaceValidator()
        result = validator.validate('NMC811', 'EC')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[InterfaceWeights] = None,
        viability_threshold: float = 0.50,
    ):
        """
        Initialize the interface validator.

        Args:
            weights: Scoring weights (uses default if None)
            viability_threshold: Score above which an interface is "viable"
        """
        self.weights = weights or InterfaceWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        material_a: str,
        material_b: str,
        conditions: Optional[InterfaceConditions] = None,
    ) -> BatteryInterfaceScore:
        """
        Validate an interface between two materials by name.

        Args:
            material_a: Name of first material (must be in ALL_MATERIALS)
            material_b: Name of second material
            conditions: Optional operating conditions

        Returns:
            BatteryInterfaceScore with component breakdown

        Raises:
            ValueError: If material name not found
        """
        mat_a = get_material(material_a)
        mat_b = get_material(material_b)
        if mat_a is None:
            raise ValueError(f"Unknown material: '{material_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown material: '{material_b}'")

        return self.validate_materials(mat_a, mat_b, conditions)

    def validate_materials(
        self,
        material_a: BatteryMaterial,
        material_b: BatteryMaterial,
        conditions: Optional[InterfaceConditions] = None,
    ) -> BatteryInterfaceScore:
        """
        Validate an interface between two BatteryMaterial objects.

        Args:
            material_a: First material
            material_b: Second material
            conditions: Optional operating conditions

        Returns:
            BatteryInterfaceScore with full breakdown
        """
        conditions = conditions or InterfaceConditions()

        # Run all five scorers
        s_ion = score_ion_transport(material_a, material_b)
        s_echem = score_electrochemical_stability(material_a, material_b)
        s_iface = score_interface_compatibility(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_degrad = score_degradation_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'ion_transport': s_ion.score,
            'electrochemical_stability': s_echem.score,
            'interface_compatibility': s_iface.score,
            'mechanical_compatibility': s_mech.score,
            'degradation_penalty': s_degrad.score,
        }
        scores = self._apply_condition_modifiers(scores, material_a, material_b, conditions)

        # Weighted composite
        total = (
            self.weights.ion_transport * scores['ion_transport'] +
            self.weights.electrochemical_stability * scores['electrochemical_stability'] +
            self.weights.interface_compatibility * scores['interface_compatibility'] +
            self.weights.mechanical_compatibility * scores['mechanical_compatibility'] +
            self.weights.degradation_penalty * scores['degradation_penalty']
        )

        # Collect details
        all_details = {
            'ion_transport_details': s_ion.details,
            'electrochemical_details': s_echem.details,
            'interface_details': s_iface.details,
            'mechanical_details': s_mech.details,
            'degradation_details': s_degrad.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'c_rate': conditions.c_rate,
                'cycle_number': conditions.cycle_number,
            },
            'material_a': material_a.name,
            'material_b': material_b.name,
        }

        # Current-collector chemistry vetoes.
        #
        # The five component scorers reason about the ELECTROCHEMICAL window
        # (oxidation/reduction potentials). Two dominant collector failure modes
        # are not electrochemical oxidation and were therefore invisible: a
        # collector could be scored identically whether it was the correct or the
        # catastrophic choice (Graphite+Al_foil scored the same as
        # Graphite+Cu_foil; S8+Cu_foil the same as S8+Al_foil).
        collector_veto = self._collector_chemistry_veto(material_a, material_b)

        # Veto check: Critical instability
        # If degradation is extreme or interface doesn't passivate, it's not viable
        is_viable = total >= self.viability_threshold
        if collector_veto is not None:
            # Physical veto: annihilates the composite rather than being diluted
            # through the weighted sum (same principle as the MOF pore-access and
            # polymer Flory-Huggins vetoes).
            is_viable = False
            total = min(total, 0.10)
            all_details['veto'] = collector_veto
        # Each of these is a physical block, so it annihilates the composite
        # rather than being diluted by the weighted sum -- and capping `total`
        # keeps the surfaced score consistent with the verdict, so a vetoed pair
        # can never report a higher score than a viable one.
        elif scores['degradation_penalty'] <= 0.4:
            is_viable = False
            total = _vetoed_score(total)
            all_details['veto'] = 'Extreme degradation risk: interface non-viable'
        elif scores['interface_compatibility'] < 0.4:
            is_viable = False
            total = _vetoed_score(total)
            all_details['veto'] = 'Interface instability: SEI/CEI cannot stabilize'
        elif scores['electrochemical_stability'] < 0.3:
            is_viable = False
            total = _vetoed_score(total)
            all_details['veto'] = 'Electrochemical instability: electrolyte decomposes at electrode voltage'
        elif scores['mechanical_compatibility'] < 0.3:
            is_viable = False
            total = _vetoed_score(total)
            all_details['veto'] = 'Mechanical incompatibility: expansion/contact loss risk'

        return BatteryInterfaceScore(
            total=total,
            ion_transport=scores['ion_transport'],
            electrochemical_stability=scores['electrochemical_stability'],
            interface_compatibility=scores['interface_compatibility'],
            mechanical_compatibility=scores['mechanical_compatibility'],
            degradation_penalty=scores['degradation_penalty'],
            viable=is_viable,
            details=all_details,
        )


    # Al-Li alloying onset vs Li/Li+. Below this, aluminium lithiates to LiAl and
    # cannot serve as a current collector; this is why Li-ion anodes use copper.
    # LTO (nominal 1.55 V, lower 1.0 V) sits safely above it, which is why
    # commercial LTO cells legitimately use aluminium on BOTH electrodes.
    _AL_LI_ALLOYING_V = 0.3

    @staticmethod
    def _is_collector(material: BatteryMaterial, element: str) -> bool:
        """True if `material` is a metal-foil current collector of `element`."""
        formula = (material.formula or "").strip()
        name = (material.name or "").strip().lower()
        return formula == element and ("foil" in name or "tab" in name)

    def _collector_chemistry_veto(
        self,
        material_a: BatteryMaterial,
        material_b: BatteryMaterial,
    ) -> Optional[str]:
        """Non-electrochemical current-collector failure modes.

        Returns a veto reason, or None if no collector veto applies.

        Covers two mechanisms the potential-window scorers cannot see:
          1. Li-Al alloying: aluminium lithiates below ~0.3 V vs Li/Li+.
          2. Sulfide corrosion: sulfur chemistry converts copper to Cu2S.
        """
        for collector, partner in ((material_a, material_b), (material_b, material_a)):
            # --- 1. Aluminium collector against a low-potential (lithiating) electrode
            if self._is_collector(collector, "Al"):
                window = getattr(partner, "voltage_window", None)
                lower = getattr(window, "lower", None) if window else None
                if lower is not None and lower < self._AL_LI_ALLOYING_V:
                    return (
                        f"Li-Al alloying: {partner.name} operates down to {lower:.2f} V "
                        f"vs Li, below the ~{self._AL_LI_ALLOYING_V:.1f} V aluminium "
                        "lithiation onset. Al foil forms LiAl and fails as a collector; "
                        "copper is used on the anode side."
                    )

            # --- 2. Copper collector against a SULFUR-CATHODE active material.
            # Restricted to cathode active materials on purpose. A blanket
            # "sulfur in the formula" rule is wrong twice over:
            #   * LiTFSI's sulfur is fully-oxidized sulfonyl (SO2CF3); it does not
            #     sulfidize copper -- vetoing Cu+LiTFSI is a false positive.
            #   * sulfide SOLID ELECTROLYTES (Li3PS4, LGPS) sit against the anode,
            #     where copper is the standard, generally-stable collector -- a
            #     blanket veto there is a likely false negative.
            # The undisputed case is an elemental-sulfur / polysulfide CATHODE
            # (high potential), which does convert Cu to Cu2S.
            if self._is_collector(collector, "Cu"):
                formula = (partner.formula or "")
                is_cathode = getattr(partner.material_class, "name", "") == "CATHODE"
                if is_cathode and "S" in _element_symbols(formula):
                    return (
                        f"Sulfide corrosion: {partner.name} ({formula}) is a "
                        "sulfur-bearing cathode; at cathode potential it converts "
                        "copper to Cu2S. Sulfur cathodes use aluminium collectors, "
                        "not copper."
                    )
        return None

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: BatteryMaterial,
        material_b: BatteryMaterial,
        conditions: InterfaceConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # Temperature effects
        if conditions.temperature_C > 60:
            # Elevated temperature accelerates degradation
            temp_factor = max(0.5, 1.0 - (conditions.temperature_C - 60) / 200)
            modified['degradation_penalty'] *= temp_factor
            # But improves ion transport (Arrhenius)
            modified['ion_transport'] = min(1.0, modified['ion_transport'] * 1.1)

        if conditions.temperature_C < 0:
            # Low temperature hurts ion transport significantly
            temp_factor = max(0.3, 1.0 + conditions.temperature_C / 50)
            modified['ion_transport'] *= temp_factor

        # High C-rate effects
        if conditions.c_rate > 3.0:
            # Fast charging stresses interfaces mechanically
            modified['mechanical_compatibility'] *= max(0.5, 1.0 - (conditions.c_rate - 3) / 10)
            # And increases polarization (effective voltage shifts)
            modified['electrochemical_stability'] *= 0.9

        # Cycling degradation
        if conditions.cycle_number > 500:
            aging_factor = max(0.6, 1.0 - (conditions.cycle_number - 500) / 5000)
            modified['interface_compatibility'] *= aging_factor
            modified['degradation_penalty'] *= aging_factor

        return modified

    def validate_all_interfaces(
        self,
        materials: List[str],
        conditions: Optional[InterfaceConditions] = None,
    ) -> Dict[Tuple[str, str], BatteryInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of materials.

        Args:
            materials: List of material names
            conditions: Operating conditions

        Returns:
            Dict mapping (mat_a, mat_b) to BatteryInterfaceScore
        """
        results = {}
        for i in range(len(materials)):
            for j in range(i + 1, len(materials)):
                key = (materials[i], materials[j])
                try:
                    results[key] = self.validate(materials[i], materials[j], conditions)
                except ValueError as e:
                    # Skip unknown materials
                    pass
        return results


def validate_interface(
    material_a: str,
    material_b: str,
    conditions: Optional[InterfaceConditions] = None,
) -> BatteryInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = BatteryInterfaceValidator()
    return validator.validate(material_a, material_b, conditions)


if __name__ == "__main__":
    print("=" * 70)
    print("Battery Interface Validator - Demo")
    print("=" * 70)
    print()

    validator = BatteryInterfaceValidator()

    # Good pairing
    print("--- LFP + EC (good pairing) ---")
    result = validator.validate('LFP', 'EC')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Ion transport:    {result.ion_transport:.3f}")
    print(f"  Echem stability:  {result.electrochemical_stability:.3f}")
    print(f"  Interface compat: {result.interface_compatibility:.3f}")
    print(f"  Mechanical:       {result.mechanical_compatibility:.3f}")
    print(f"  Degradation:      {result.degradation_penalty:.3f}")
    print()

    # Bad pairing
    print("--- LGPS + NMC811 (known bad) ---")
    result = validator.validate('LGPS', 'NMC811')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Ion transport:    {result.ion_transport:.3f}")
    print(f"  Echem stability:  {result.electrochemical_stability:.3f}")
    print(f"  Interface compat: {result.interface_compatibility:.3f}")
    print(f"  Mechanical:       {result.mechanical_compatibility:.3f}")
    print(f"  Degradation:      {result.degradation_penalty:.3f}")
