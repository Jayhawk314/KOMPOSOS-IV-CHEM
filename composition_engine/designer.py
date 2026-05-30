# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Inverse Composition Designer

Given target properties, searches composition space for candidate materials
that satisfy the constraints. Uses the forward predictor (CompositionPredictor)
as a fast oracle (~5ms/call) and generates candidates via 4 strategies:

1. Anchor perturbation -- stoichiometry shifts on known materials
2. Interpolation sweeps -- walk between same-domain material pairs
3. Element substitution -- swap elements within chemical groups
4. Stoichiometry variation -- NMC triangle grid, olivine M-site sweep

This is the "inverse" of predict(): instead of formula -> properties,
it solves properties -> [formulas].
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from .parser import (
    parse_formula, composition_distance, composition_vector, SHORTHAND_MAP, ELEMENT_TABLE,
)
from .known_compositions import KnownCompositionDB, get_db
from .predictor import CompositionPredictor, PredictedMaterial


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PropertyTarget:
    """A single target property with acceptable range."""
    name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    weight: float = 1.0

    def is_met(self, value: float) -> bool:
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True

    def distance(self, value: float) -> float:
        """Distance from value to target range (0 if inside)."""
        if self.is_met(value):
            return 0.0
        if self.min_value is not None and value < self.min_value:
            return (self.min_value - value) / max(abs(self.min_value), 1e-6)
        if self.max_value is not None and value > self.max_value:
            return (value - self.max_value) / max(abs(self.max_value), 1e-6)
        return 0.0


@dataclass
class ElementConstraint:
    """Constraints on which elements may appear in candidates."""
    required_elements: List[str] = field(default_factory=list)
    excluded_elements: List[str] = field(default_factory=list)
    max_elements: Optional[int] = None


@dataclass
class DesignSpec:
    """Full specification for an inverse design search."""
    targets: List[PropertyTarget]
    element_constraints: Optional[ElementConstraint] = None
    min_synthesizability: float = 0.0
    require_stable: bool = False
    pfas_free: bool = False
    domain: Optional[str] = None
    max_candidates: int = 500


@dataclass
class DesignCandidate:
    """A single candidate composition from the design search."""
    formula: str
    composition: Dict[str, float]
    predicted_properties: Dict[str, float]
    overall_score: float
    target_scores: Dict[str, float]
    targets_met: List[str]
    targets_missed: List[str]
    strategy: str
    anchor: Optional[str] = None
    synthesizability: float = 0.0
    formation_energy: Optional[float] = None
    structure_type: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "formula": self.formula,
            "composition": self.composition,
            "predicted_properties": self.predicted_properties,
            "overall_score": self.overall_score,
            "target_scores": self.target_scores,
            "targets_met": self.targets_met,
            "targets_missed": self.targets_missed,
            "strategy": self.strategy,
            "anchor": self.anchor,
            "synthesizability": self.synthesizability,
            "formation_energy": self.formation_energy,
            "structure_type": self.structure_type,
            "confidence": self.confidence,
        }


@dataclass
class DesignResult:
    """Result of an inverse design search."""
    candidates: List[DesignCandidate]
    num_evaluated: int
    num_passed_filters: int
    strategies_used: List[str]
    elapsed_seconds: float
    num_physical_gated: int = 0  # candidates rejected by physical gates (e.g. charge balance)

    def to_dict(self) -> Dict:
        return {
            "num_candidates": len(self.candidates),
            "num_evaluated": self.num_evaluated,
            "num_passed_filters": self.num_passed_filters,
            "num_physical_gated": self.num_physical_gated,
            "strategies_used": self.strategies_used,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "candidates": [c.to_dict() for c in self.candidates],
        }


# ═══════════════════════════════════════════════════════════════════════════
# SUBSTITUTION GROUPS
# ═══════════════════════════════════════════════════════════════════════════

SUBSTITUTION_GROUPS: Dict[str, List[str]] = {
    "transition_metal_cathode": ["Ni", "Mn", "Co", "Fe", "Cr", "V", "Ti", "Al"],
    "alkali": ["Li", "Na", "K"],
    "alkaline_earth": ["Mg", "Ca", "Sr", "Ba"],
    "chalcogenide": ["O", "S", "Se"],
    "halide": ["F", "Cl", "Br"],
    "group_iv": ["Si", "Ge", "Sn"],
    "rare_earth": ["La", "Y", "Ce"],
}

# Known property names the predictor can produce
KNOWN_PROPERTIES: Set[str] = {
    "voltage", "theoretical_capacity", "thermal_stability",
    "ionic_conductivity", "density", "volume_expansion",
    "formation_energy", "synthesizability",
    "band_gap", "electron_mobility", "lattice_constant",
    "melting_point", "thermal_conductivity", "hardness",
    "fracture_toughness", "cte", "youngs_modulus",
    "molar_mass", "avg_electronegativity",
}


# ═══════════════════════════════════════════════════════════════════════════
# COMPOSITION DESIGNER
# ═══════════════════════════════════════════════════════════════════════════

class CompositionDesigner:
    """
    Inverse design: given target properties, find candidate compositions.

    Uses the forward predictor as a fast oracle and generates candidates
    via 4 complementary search strategies over known materials.

    Usage:
        designer = CompositionDesigner()
        spec = DesignSpec(targets=[PropertyTarget("voltage", min_value=4.0)])
        result = designer.design(spec)
        for c in result.candidates[:5]:
            print(f"{c.formula}: score={c.overall_score:.3f}")
    """

    def __init__(self, predictor: Optional[CompositionPredictor] = None,
                 db: Optional[KnownCompositionDB] = None):
        self.predictor = predictor or CompositionPredictor()
        self.db = db or get_db()

    def design(self, spec: DesignSpec) -> DesignResult:
        """Main entry point: search for compositions matching spec."""
        from composition_engine.physical_gates import passes_physical_gates
        t0 = time.perf_counter()

        # Generate candidate formulas from all strategies
        raw_candidates = self._generate_candidates(spec)

        # Deduplicate by composition distance
        unique = self._deduplicate(raw_candidates)

        # Pre-filter by element constraints (fast, no predict() call)
        filtered = [
            (formula, strategy, anchor) for formula, strategy, anchor in unique
            if self._passes_element_filter(formula, spec.element_constraints)
        ]

        # Evaluate each candidate with the forward predictor
        scored: List[DesignCandidate] = []
        num_evaluated = 0

        for formula, strategy, anchor in filtered:
            if num_evaluated >= spec.max_candidates:
                break
            try:
                prediction = self.predictor.predict(formula, domain=spec.domain)
            except Exception:
                continue
            num_evaluated += 1

            candidate = self._score_candidate(prediction, spec, strategy, anchor)

            # Apply post-filters
            if spec.min_synthesizability > 0 and candidate.synthesizability < spec.min_synthesizability:
                continue
            if spec.require_stable and candidate.formation_energy is not None and candidate.formation_energy > 0:
                continue

            scored.append(candidate)

        # Rank by overall score descending
        scored.sort(key=lambda c: c.overall_score, reverse=True)

        # Physical gate, applied POST-ranking: only the top candidates we would
        # actually surface get the expensive pymatgen charge-balance check. The
        # deep tail (never shown) is left ungated. Cheap-filters-first funnel.
        GATE_SURFACE_CAP = 100
        kept: List[DesignCandidate] = []
        num_gated = 0
        for c in scored:
            if len(kept) < GATE_SURFACE_CAP and not passes_physical_gates(c.formula):
                num_gated += 1
                continue
            kept.append(c)
        scored = kept

        strategies_used = sorted(set(c.strategy for c in scored)) if scored else []
        elapsed = time.perf_counter() - t0

        return DesignResult(
            candidates=scored,
            num_evaluated=num_evaluated,
            num_passed_filters=len(scored),
            strategies_used=strategies_used,
            elapsed_seconds=elapsed,
            num_physical_gated=num_gated,
        )

    # ── Candidate generation ───────────────────────────────────────────

    # Max anchor materials to use per strategy (prevents combinatorial explosion
    # when DB has 100K+ entries from Materials Project).
    MAX_ANCHORS = 200

    def _generate_candidates(self, spec: DesignSpec) -> List[Tuple[str, str, Optional[str]]]:
        """Generate candidate formulas from all 4 strategies.

        Returns list of (formula, strategy_name, anchor_name).
        When the DB is large (e.g. 103K MP entries), anchors are sampled
        down to MAX_ANCHORS to keep generation in the thousands, not millions.
        """
        candidates: List[Tuple[str, str, Optional[str]]] = []

        entries = self.db.entries
        if spec.domain:
            entries = [e for e in entries if e.domain == spec.domain]

        # Cap anchors to prevent combinatorial explosion with large DBs
        anchors = self._sample_anchors(entries)

        # Generate per-strategy, then round-robin interleave so the downstream
        # evaluation budget (max_candidates) is shared across all four strategies
        # rather than being consumed by whichever is generated first.
        strategy_lists = [
            self._strategy_perturbation(anchors),
            self._strategy_interpolation(anchors),
            self._strategy_substitution(anchors),
            self._strategy_stoichiometry(entries),
        ]
        i = 0
        while any(i < len(lst) for lst in strategy_lists):
            for lst in strategy_lists:
                if i < len(lst):
                    candidates.append(lst[i])
            i += 1

        return candidates

    def _sample_anchors(self, entries) -> list:
        """Sample representative anchors when the entry list is large.

        Prefers diverse domain coverage: takes all bridge-origin entries,
        then fills remaining slots evenly across MP entries (strided sample).
        """
        if len(entries) <= self.MAX_ANCHORS:
            return entries

        # Separate bridge-origin (hand-curated) from MP entries
        bridge = [e for e in entries if not e.name.startswith("mp-")]
        mp = [e for e in entries if e.name.startswith("mp-")]

        selected = list(bridge)
        remaining = self.MAX_ANCHORS - len(selected)

        if remaining > 0 and mp:
            # Strided sample for even coverage across MP entries
            stride = max(1, len(mp) // remaining)
            selected.extend(mp[::stride][:remaining])

        return selected[:self.MAX_ANCHORS]

    def _strategy_perturbation(self, entries) -> List[Tuple[str, str, Optional[str]]]:
        """Vary element RATIOS, not the global scale.

        Scaling every element by the same factor is a no-op in composition space
        (it leaves the stoichiometric ratios unchanged). To actually explore, we
        perturb one element at a time, and also emit the anchor itself (x1.0) so
        known-good ratios are in the candidate pool.
        """
        candidates = []
        factors = [0.70, 0.85, 1.15, 1.30]

        for entry in entries:
            comp = entry.composition
            # anchor itself (ratios preserved as a candidate)
            candidates.append((self._comp_to_formula(dict(comp)), "perturbation", entry.name))
            for elem in list(comp.keys()):
                for factor in factors:
                    new_comp = dict(comp)
                    new_comp[elem] = comp[elem] * factor
                    formula = self._comp_to_formula(new_comp)
                    candidates.append((formula, "perturbation", entry.name))

        return candidates

    def _strategy_interpolation(self, entries) -> List[Tuple[str, str, Optional[str]]]:
        """Interpolate between pairs of same-domain materials at 0.1 steps."""
        candidates = []

        # Group by domain
        by_domain: Dict[str, list] = {}
        for e in entries:
            by_domain.setdefault(e.domain, []).append(e)

        for domain, group in by_domain.items():
            # Limit pairs to avoid combinatorial explosion
            n = len(group)
            max_pairs = min(n * (n - 1) // 2, 50)
            pair_count = 0
            for i in range(n):
                if pair_count >= max_pairs:
                    break
                for j in range(i + 1, n):
                    if pair_count >= max_pairs:
                        break
                    for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                        comp_a = group[i].composition
                        comp_b = group[j].composition
                        interp = self._interpolate_comp(comp_a, comp_b, frac)
                        formula = self._comp_to_formula(interp)
                        anchor = f"{group[i].name}+{group[j].name}"
                        candidates.append((formula, "interpolation", anchor))
                    pair_count += 1

        return candidates

    def _strategy_substitution(self, entries) -> List[Tuple[str, str, Optional[str]]]:
        """Swap elements within chemical groups."""
        candidates = []

        for entry in entries:
            comp = entry.composition
            for group_name, group_elements in SUBSTITUTION_GROUPS.items():
                present = [e for e in group_elements if e in comp]
                absent = [e for e in group_elements if e not in comp]

                for old_elem in present:
                    for new_elem in absent:
                        new_comp = dict(comp)
                        new_comp[new_elem] = new_comp.pop(old_elem)
                        formula = self._comp_to_formula(new_comp)
                        candidates.append((formula, "substitution", entry.name))

        return candidates

    def _strategy_stoichiometry(self, entries) -> List[Tuple[str, str, Optional[str]]]:
        """NMC triangle grid and olivine M-site sweep."""
        candidates = []

        # NMC triangle: Li(NixMnyCo(1-x-y))O2, step 0.1
        for ni_10 in range(1, 10):
            for mn_10 in range(1, 10 - ni_10):
                co_10 = 10 - ni_10 - mn_10
                if co_10 < 1:
                    continue
                ni = ni_10 / 10.0
                mn = mn_10 / 10.0
                co = co_10 / 10.0
                formula = f"LiNi{ni:.1f}Mn{mn:.1f}Co{co:.1f}O2"
                candidates.append((formula, "stoichiometry", "NMC_grid"))

        # Olivine M-site sweep: LiMPO4, M = Fe, Mn, Co, Ni
        for metal in ["Fe", "Mn", "Co", "Ni"]:
            formula = f"Li{metal}PO4"
            candidates.append((formula, "stoichiometry", "olivine_sweep"))

        # Olivine mixed M-site: Li(Fe_xMn_{1-x})PO4
        for fe_10 in range(1, 10):
            fe = fe_10 / 10.0
            mn = 1.0 - fe
            formula = f"LiFe{fe:.1f}Mn{mn:.1f}PO4"
            candidates.append((formula, "stoichiometry", "olivine_sweep"))

        # Spinel variations: LiM2O4
        for m1 in ["Mn", "Ni", "Co"]:
            for m2 in ["Mn", "Ni", "Co"]:
                if m1 == m2:
                    formula = f"Li{m1}2O4"
                else:
                    formula = f"Li{m1}0.5{m2}1.5O4"
                candidates.append((formula, "stoichiometry", "spinel_sweep"))

        return candidates

    # ── Filtering ──────────────────────────────────────────────────────

    def _passes_element_filter(self, formula: str,
                                constraint: Optional[ElementConstraint]) -> bool:
        """Check if formula satisfies element constraints (no predict() call)."""
        if constraint is None:
            return True

        try:
            comp = parse_formula(formula)
        except Exception:
            return False

        elements = set(comp.keys())

        for req in constraint.required_elements:
            if req not in elements:
                return False

        for excl in constraint.excluded_elements:
            if excl in elements:
                return False

        if constraint.max_elements is not None and len(elements) > constraint.max_elements:
            return False

        return True

    def _deduplicate(self, candidates: List[Tuple[str, str, Optional[str]]]
                     ) -> List[Tuple[str, str, Optional[str]]]:
        """Remove near-duplicate compositions (distance < 0.01).

        Uses spatial index (KD-tree radius_search) for large candidate sets,
        reducing O(N^2) to O(N log N). Falls back to linear scan for small sets.
        """
        # Parse all formulas first
        parsed: List[Tuple[Dict[str, float], str, str, Optional[str]]] = []
        for formula, strategy, anchor in candidates:
            try:
                comp = parse_formula(formula)
                parsed.append((comp, formula, strategy, anchor))
            except Exception:
                continue

        if len(parsed) <= 500:
            # Small set: use original linear scan
            return self._deduplicate_linear(parsed)

        # Large set: use spatial index for fast dedup
        return self._deduplicate_spatial(parsed)

    def _deduplicate_linear(self, parsed):
        """O(N^2) linear dedup for small candidate sets."""
        seen_comps: List[Dict[str, float]] = []
        unique: List[Tuple[str, str, Optional[str]]] = []

        for comp, formula, strategy, anchor in parsed:
            is_dup = False
            for seen in seen_comps:
                if composition_distance(comp, seen) < 0.01:
                    is_dup = True
                    break
            if not is_dup:
                seen_comps.append(comp)
                unique.append((formula, strategy, anchor))

        return unique

    def _deduplicate_spatial(self, parsed):
        """O(N log N) spatial dedup using KD-tree radius_search."""
        from .parser import composition_vector
        from .spatial_index import CompositionIndex

        # Build vectors for all candidates
        vecs = np.array([composition_vector(comp) for comp, _, _, _ in parsed])

        # Build index over all candidates
        index = CompositionIndex(list(range(len(parsed))), vectors=vecs)

        seen = set()
        unique: List[Tuple[str, str, Optional[str]]] = []

        for i, (comp, formula, strategy, anchor) in enumerate(parsed):
            if i in seen:
                continue

            # Mark this candidate and all near-duplicates as seen
            neighbours = index.radius_search(vecs[i], radius=0.01)
            for idx_entry, _ in neighbours:
                seen.add(idx_entry)

            unique.append((formula, strategy, anchor))

        return unique

    # ── Scoring ────────────────────────────────────────────────────────

    def _score_candidate(self, prediction: PredictedMaterial,
                         spec: DesignSpec, strategy: str,
                         anchor: Optional[str]) -> DesignCandidate:
        """Score a predicted material against the design spec."""
        props = prediction.properties
        pred_values: Dict[str, float] = {}
        for pname, pprop in props.items():
            pred_values[pname] = pprop.value

        target_scores: Dict[str, float] = {}
        targets_met: List[str] = []
        targets_missed: List[str] = []

        for target in spec.targets:
            if target.name not in props:
                target_scores[target.name] = 0.0
                targets_missed.append(target.name)
                continue

            value = props[target.name].value
            confidence = props[target.name].confidence

            if target.is_met(value):
                score = 0.8 + 0.2 * confidence
                targets_met.append(target.name)
            else:
                dist = target.distance(value)
                score = math.exp(-2.0 * dist) * confidence
                targets_missed.append(target.name)

            target_scores[target.name] = score

        # Weighted sum of target scores
        total_weight = sum(t.weight for t in spec.targets)
        if total_weight > 0:
            weighted_sum = sum(
                target_scores.get(t.name, 0.0) * t.weight
                for t in spec.targets
            ) / total_weight
        else:
            weighted_sum = 0.0

        # Synthesizability factor
        synth = 0.5  # default
        if "synthesizability" in props:
            synth = props["synthesizability"].value

        # Stability factor
        stability_factor = 1.0
        fe_value = None
        if "formation_energy" in props:
            fe_value = props["formation_energy"].value
            if fe_value < 0:
                stability_factor = 1.0
            else:
                stability_factor = max(0.3, 1.0 - fe_value)

        # Average confidence across target properties
        conf_values = [
            props[t.name].confidence for t in spec.targets if t.name in props
        ]
        avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.5

        overall = weighted_sum * (0.5 + 0.5 * synth) * stability_factor * (0.5 + 0.5 * avg_conf)
        overall = max(0.0, min(1.0, overall))

        # Structure type
        struct_type = None
        if prediction.predicted_structure is not None:
            struct_type = prediction.predicted_structure.predicted_type

        return DesignCandidate(
            formula=prediction.formula,
            composition=prediction.composition,
            predicted_properties=pred_values,
            overall_score=overall,
            target_scores=target_scores,
            targets_met=targets_met,
            targets_missed=targets_missed,
            strategy=strategy,
            anchor=anchor,
            synthesizability=synth,
            formation_energy=fe_value,
            structure_type=struct_type,
            confidence=avg_conf,
        )

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _comp_to_formula(comp: Dict[str, float]) -> str:
        """Convert a composition dict back to a formula string."""
        parts = []
        for elem in sorted(comp.keys()):
            amt = comp[elem]
            if amt <= 0:
                continue
            if abs(amt - round(amt)) < 0.001:
                if int(round(amt)) == 1:
                    parts.append(elem)
                else:
                    parts.append(f"{elem}{int(round(amt))}")
            else:
                parts.append(f"{elem}{amt:.3f}")
        return "".join(parts)

    @staticmethod
    def _interpolate_comp(comp_a: Dict[str, float], comp_b: Dict[str, float],
                          frac: float) -> Dict[str, float]:
        """Linearly interpolate between two compositions."""
        all_elems = set(comp_a.keys()) | set(comp_b.keys())
        result = {}
        for elem in all_elems:
            va = comp_a.get(elem, 0.0)
            vb = comp_b.get(elem, 0.0)
            result[elem] = va * (1 - frac) + vb * frac
        return result
