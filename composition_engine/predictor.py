# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Compositional Property Predictor

Core prediction engine that combines:
1. Left Kan Extension over known compositions (categorical extrapolation)
2. Rule-based chemistry estimates (Faraday, Vegard, electronegativity)
3. Dempster-Shafer evidence fusion of both sources

Architecture:
    - CompositionCategory: enriched category where objects = known compositions,
      hom-objects = composition distances in COMPATIBILITY_QUANTALE
    - PropertyFunctor: maps compositions -> property dicts from bridge data
    - CompositionPredictor: orchestrates Kan + rules + D-S fusion

This is what makes KOMPOSOS different from simulation tools: categorical
extrapolation over composition space, not molecular dynamics.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from categorical.category import Object, Morphism, Category
from categorical.kan_extensions import Functor, LeftKanExtension
from categorical.enriched_category import EnrichedCategory, COMPATIBILITY_QUANTALE
from categorical.dempster_shafer import MassFunction, combine

from .parser import (
    parse_formula, composition_distance, molar_mass,
    SHORTHAND_MAP, metal_fraction,
)
from .properties import estimate_properties, PropertyEstimate
from .known_compositions import KnownCompositionDB, get_db


def _auto_detect_domain(comp: Dict[str, float]) -> Optional[str]:
    """Auto-detect domain from composition to improve neighbour quality."""
    has_li = "Li" in comp
    has_o = "O" in comp
    has_tms = any(m in comp for m in ["Ni", "Mn", "Co"])
    has_fe_p = "Fe" in comp and "P" in comp

    if has_li and has_o and (has_tms or has_fe_p):
        return "battery"
    return None


@dataclass
class PredictedProperty:
    """A single predicted property with uncertainty bounds."""
    value: float
    confidence: float           # 0-1
    lower_bound: float          # Conservative estimate
    upper_bound: float          # Optimistic estimate
    sources: Dict[str, float]   # source_name -> its estimate


@dataclass
class PredictedMaterial:
    """Full prediction result for a composition."""
    formula: str
    composition: Dict[str, float]
    properties: Dict[str, PredictedProperty]
    nearest_known: List[Tuple[str, float]]  # [(name, distance), ...]
    method: str = "kan_extension_plus_dempster_shafer"
    predicted_structure: Optional[object] = None  # StructurePrediction
    derived_structure: Optional[object] = None     # DerivedStructure (from MP)

    def to_dict(self) -> Dict:
        d = {
            "formula": self.formula,
            "composition": self.composition,
            "properties": {
                k: {
                    "value": v.value,
                    "confidence": v.confidence,
                    "lower_bound": v.lower_bound,
                    "upper_bound": v.upper_bound,
                    "sources": v.sources,
                }
                for k, v in self.properties.items()
            },
            "nearest_known": [
                {"name": n, "distance": d_} for n, d_ in self.nearest_known
            ],
            "method": self.method,
        }
        if self.predicted_structure is not None:
            d["predicted_structure"] = self.predicted_structure.to_dict()
        if self.derived_structure is not None:
            d["derived_structure"] = self.derived_structure.to_dict()
        return d


class CompositionPredictor:
    """
    Predicts properties of unknown compositions using Kan extension
    over known materials + Dempster-Shafer fusion with rule-based estimates.

    Usage:
        pred = CompositionPredictor()
        result = pred.predict("LiNi0.7Mn0.15Co0.15O2")
        print(result.properties["voltage"].value)  # ~3.85V
    """

    def __init__(self, db: Optional[KnownCompositionDB] = None, k: int = 5):
        self.db = db or get_db()
        self.k = k   # Number of nearest neighbours for Kan extension
        # Lazy-initialized heavy objects (cached across predict() calls)
        self._fep = None             # FormationEnergyPredictor
        self._stp = None             # StructureTypePredictor
        self._structure_deriver = None  # StructureDeriver (from MP data)
        self._mp_deriver_loaded = False  # True once we've tried to load MP

    def predict(self, formula: str,
                exclude_names: Optional[List[str]] = None,
                domain: Optional[str] = None) -> PredictedMaterial:
        """
        Predict properties for a chemical formula.

        Args:
            formula: Chemical formula or shorthand (e.g. "NMC721", "LiNi0.7Mn0.2Co0.1O2")
            exclude_names: Materials to exclude (for leave-one-out validation)
            domain: Restrict to a specific domain

        Returns:
            PredictedMaterial with per-property predictions and confidence.
        """
        resolved = SHORTHAND_MAP.get(formula, formula)
        comp = parse_formula(resolved)

        # Auto-detect domain if not specified
        if domain is None:
            domain = _auto_detect_domain(comp)

        # Step 1: Find nearest known compositions
        neighbours = self.db.nearest_k(comp, k=self.k,
                                        domain=domain,
                                        exclude_names=exclude_names)

        nearest_known = [(n.name, d) for n, d in neighbours]

        # Step 2: Kan extension prediction (weighted colimit over neighbours)
        kan_estimates = self._kan_predict(comp, neighbours)

        # Step 3: Rule-based prediction
        rule_estimates = estimate_properties(formula)

        # Step 4: Dempster-Shafer fusion
        properties = self._fuse_predictions(kan_estimates, rule_estimates)

        # Step 5: Formation energy + synthesizability (DFT surrogate)
        try:
            if self._fep is None:
                from .formation_energy import FormationEnergyPredictor
                self._fep = FormationEnergyPredictor()
            fe_result = self._fep.predict(formula)
            properties["formation_energy"] = PredictedProperty(
                value=fe_result.ef_per_atom,
                confidence=fe_result.confidence,
                lower_bound=fe_result.ef_per_atom * 1.2 if fe_result.ef_per_atom < 0 else fe_result.ef_per_atom * 0.8,
                upper_bound=fe_result.ef_per_atom * 0.8 if fe_result.ef_per_atom < 0 else fe_result.ef_per_atom * 1.2,
                sources=fe_result.sources,
            )
            properties["synthesizability"] = PredictedProperty(
                value=fe_result.synthesizability_score,
                confidence=fe_result.confidence,
                lower_bound=max(0.0, fe_result.synthesizability_score - 0.15),
                upper_bound=min(1.0, fe_result.synthesizability_score + 0.15),
                sources={"formation_energy": fe_result.ef_per_atom},
            )
        except Exception:
            pass  # Formation energy is optional enhancement

        # Step 6: Crystal structure type prediction
        predicted_structure = None
        try:
            if self._stp is None:
                from .structure_predictor import StructureTypePredictor
                self._stp = StructureTypePredictor()
            predicted_structure = self._stp.predict(formula)
        except Exception:
            pass  # Structure prediction is optional enhancement

        # Step 7: Structure derivation (from MP data if available)
        derived_structure = None
        try:
            if not self._mp_deriver_loaded:
                self._mp_deriver_loaded = True
                from .mp_loader import MPCache
                from .structure_deriver import StructureDeriver
                cache = MPCache()
                if cache.is_available():
                    mp_entries = cache.load_entries_with_lattice()
                    if mp_entries:
                        self._structure_deriver = StructureDeriver(mp_entries)
            if self._structure_deriver is not None:
                derived_structure = self._structure_deriver.derive(formula)
        except Exception:
            pass  # Structure derivation is optional enhancement

        return PredictedMaterial(
            formula=formula,
            composition=comp,
            properties=properties,
            nearest_known=nearest_known,
            predicted_structure=predicted_structure,
            derived_structure=derived_structure,
        )

    def interpolate(self, formula_a: str, formula_b: str,
                    fraction: float) -> PredictedMaterial:
        """
        Predict properties at an intermediate composition.

        fraction=0 -> formula_a, fraction=1 -> formula_b.
        """
        comp_a = parse_formula(SHORTHAND_MAP.get(formula_a, formula_a))
        comp_b = parse_formula(SHORTHAND_MAP.get(formula_b, formula_b))

        # Linear interpolation in composition space
        all_elements = set(comp_a.keys()) | set(comp_b.keys())
        interp_comp = {}
        for elem in all_elements:
            va = comp_a.get(elem, 0.0)
            vb = comp_b.get(elem, 0.0)
            interp_comp[elem] = va * (1 - fraction) + vb * fraction

        # Build an interpolated formula string
        parts = []
        for elem in sorted(interp_comp.keys()):
            amt = interp_comp[elem]
            if abs(amt - round(amt)) < 0.001:
                if amt == 1.0:
                    parts.append(elem)
                else:
                    parts.append(f"{elem}{int(round(amt))}")
            else:
                parts.append(f"{elem}{amt:.3f}")
        interp_formula = "".join(parts)

        # Predict at the interpolated composition
        result = self.predict(interp_formula)
        result.method = f"interpolation({formula_a},{formula_b},f={fraction:.2f})"
        return result

    def leave_one_out(self, name: str) -> Optional[Tuple[PredictedMaterial, Dict[str, float]]]:
        """
        Leave-one-out validation: predict a known material from its neighbours.

        Returns (prediction, actual_properties) or None if name not found.
        """
        entry = self.db.get_by_name(name)
        if entry is None:
            return None

        prediction = self.predict(
            entry.formula,
            exclude_names=[name],
            domain=entry.domain,
        )

        return prediction, entry.properties

    # ── Internal methods ────────────────────────────────────────────────

    def _kan_predict(self, query_comp: Dict[str, float],
                     neighbours: list) -> Dict[str, PropertyEstimate]:
        """
        Kan extension prediction: weighted colimit of neighbour properties.

        Uses inverse-distance weighting (IDW) as the colimit aggregation.
        This is the categorical construction: the comma category (K downarrow e)
        consists of the k-nearest known compositions, with hom-weights
        derived from composition distance.
        """
        if not neighbours:
            return {}

        # Compute IDW weights: w_i = 1 / (d_i + epsilon)
        epsilon = 0.01  # Prevent division by zero for exact matches
        weights = []
        for entry, dist in neighbours:
            weights.append(1.0 / (dist + epsilon))

        total_weight = sum(weights)
        if total_weight == 0:
            return {}

        # Normalize weights
        weights = [w / total_weight for w in weights]

        # Collect all property names across neighbours
        all_props = set()
        for entry, _ in neighbours:
            all_props.update(entry.properties.keys())

        # Weighted colimit for each property
        estimates: Dict[str, PropertyEstimate] = {}
        for prop_name in all_props:
            values = []
            prop_weights = []

            for (entry, dist), w in zip(neighbours, weights):
                if prop_name in entry.properties:
                    values.append(entry.properties[prop_name])
                    prop_weights.append(w)

            if not values:
                continue

            # Renormalize weights for this property
            pw_total = sum(prop_weights)
            if pw_total == 0:
                continue
            prop_weights = [pw / pw_total for pw in prop_weights]

            # Weighted average (colimit)
            predicted_value = sum(v * w for v, w in zip(values, prop_weights))

            # Confidence: based on number of contributors and weight concentration
            n_contrib = len(values)
            # More contributors with more spread-out weights = higher confidence
            weight_entropy = -sum(w * math.log(w + 1e-12) for w in prop_weights)
            max_entropy = math.log(max(n_contrib, 1))

            base_conf = min(1.0, n_contrib / self.k)
            entropy_factor = weight_entropy / max(max_entropy, 1e-12) if max_entropy > 0 else 0
            confidence = 0.6 * base_conf + 0.4 * entropy_factor
            confidence = min(0.95, max(0.1, confidence))

            # Reduce confidence if nearest neighbour is far
            if neighbours:
                min_dist = neighbours[0][1]
                dist_penalty = max(0, 1.0 - min_dist / 5.0)
                confidence *= dist_penalty

            confidence = max(0.05, confidence)

            estimates[prop_name] = PropertyEstimate(
                value=predicted_value,
                confidence=confidence,
                method="kan_extension_idw",
            )

        return estimates

    def _fuse_predictions(self, kan_est: Dict[str, PropertyEstimate],
                          rule_est) -> Dict[str, PredictedProperty]:
        """
        Dempster-Shafer fusion of Kan extension + rule-based estimates.

        Each source produces a mass function over {accurate, inaccurate}:
        - Mass on {accurate} = confidence
        - Mass on {accurate, inaccurate} = 1 - confidence (ignorance)
        """
        all_props = set(kan_est.keys())
        if rule_est and rule_est.properties:
            all_props.update(rule_est.properties.keys())

        # Skip non-physical properties in fusion
        skip_props = {"molar_mass", "avg_electronegativity"}

        results: Dict[str, PredictedProperty] = {}

        for prop_name in all_props:
            if prop_name in skip_props:
                # Pass through directly
                if prop_name in kan_est:
                    est = kan_est[prop_name]
                    results[prop_name] = PredictedProperty(
                        value=est.value, confidence=est.confidence,
                        lower_bound=est.value, upper_bound=est.value,
                        sources={"kan": est.value},
                    )
                elif rule_est and prop_name in rule_est.properties:
                    est = rule_est.properties[prop_name]
                    results[prop_name] = PredictedProperty(
                        value=est.value, confidence=est.confidence,
                        lower_bound=est.value, upper_bound=est.value,
                        sources={"rule": est.value},
                    )
                continue

            kan_val = kan_est.get(prop_name)
            rule_val = rule_est.properties.get(prop_name) if rule_est else None

            if kan_val and rule_val:
                # Both sources available -- Dempster-Shafer fusion
                fused_value, fused_conf = self._ds_fuse_values(
                    kan_val.value, kan_val.confidence,
                    rule_val.value, rule_val.confidence,
                )

                # Bounds from the two estimates
                lo = min(kan_val.value, rule_val.value)
                hi = max(kan_val.value, rule_val.value)
                # Widen by uncertainty
                spread = (hi - lo) * (1 - fused_conf)
                lo -= spread * 0.5
                hi += spread * 0.5

                results[prop_name] = PredictedProperty(
                    value=fused_value,
                    confidence=fused_conf,
                    lower_bound=lo,
                    upper_bound=hi,
                    sources={"kan": kan_val.value, "rule": rule_val.value},
                )

            elif kan_val:
                # Only Kan extension
                spread = abs(kan_val.value) * 0.1 * (1 - kan_val.confidence)
                results[prop_name] = PredictedProperty(
                    value=kan_val.value,
                    confidence=kan_val.confidence * 0.9,  # Slight penalty for single source
                    lower_bound=kan_val.value - spread,
                    upper_bound=kan_val.value + spread,
                    sources={"kan": kan_val.value},
                )

            elif rule_val:
                # Only rule-based
                spread = abs(rule_val.value) * 0.15 * (1 - rule_val.confidence)
                results[prop_name] = PredictedProperty(
                    value=rule_val.value,
                    confidence=rule_val.confidence * 0.85,
                    lower_bound=rule_val.value - spread,
                    upper_bound=rule_val.value + spread,
                    sources={"rule": rule_val.value},
                )

        return results

    def _ds_fuse_values(self, val_a: float, conf_a: float,
                        val_b: float, conf_b: float
                        ) -> Tuple[float, float]:
        """
        Fuse two numeric estimates using Dempster-Shafer theory.

        Each source generates a mass function:
        - m({accurate}) = confidence
        - m({accurate, inaccurate}) = 1 - confidence

        The fused value is a confidence-weighted average.
        The fused confidence reflects agreement between sources.
        """
        frame = frozenset(["accurate", "inaccurate"])
        accurate = frozenset(["accurate"])

        # Build mass functions
        m1 = MassFunction(masses={
            accurate: conf_a,
            frame: 1.0 - conf_a,
        })
        m2 = MassFunction(masses={
            accurate: conf_b,
            frame: 1.0 - conf_b,
        })

        # Combine
        try:
            combined, conflict = combine(m1, m2)
        except ValueError:
            # Total conflict -- fall back to simple average
            avg = (val_a + val_b) / 2.0
            return avg, 0.3

        # Fused confidence = belief in {accurate}
        fused_conf = combined.belief(accurate)

        # Agreement bonus: if sources agree, boost confidence
        if abs(val_a) + abs(val_b) > 0:
            relative_diff = abs(val_a - val_b) / (abs(val_a) + abs(val_b) + 1e-12)
        else:
            relative_diff = 0.0

        agreement = 1.0 - relative_diff
        fused_conf = fused_conf * (0.7 + 0.3 * agreement)
        fused_conf = min(0.95, max(0.1, fused_conf))

        # Fused value: weighted by confidence
        total_conf = conf_a + conf_b
        if total_conf > 0:
            fused_value = (val_a * conf_a + val_b * conf_b) / total_conf
        else:
            fused_value = (val_a + val_b) / 2.0

        return fused_value, fused_conf


if __name__ == "__main__":
    predictor = CompositionPredictor()

    print("=" * 70)
    print("Compositional Property Predictor -- Demo")
    print("=" * 70)

    # Predict unknown composition
    formulas = ["NMC721", "NMC532", "NMC955", "LiNi0.7Mn0.15Co0.15O2"]
    for f in formulas:
        result = predictor.predict(f)
        print(f"\n{f} ({result.formula}):")
        print(f"  Nearest known: {result.nearest_known[:3]}")
        for name, prop in sorted(result.properties.items()):
            print(f"  {name:25s} = {prop.value:8.3f}  "
                  f"[{prop.lower_bound:.3f}, {prop.upper_bound:.3f}]  "
                  f"conf={prop.confidence:.2f}  sources={prop.sources}")

    # Leave-one-out validation
    print("\n" + "=" * 70)
    print("Leave-One-Out Validation (NMC cathodes)")
    print("=" * 70)

    for name in ["NMC811", "NMC622", "NMC111", "LCO", "LFP"]:
        loo = predictor.leave_one_out(name)
        if loo is None:
            continue
        pred, actual = loo
        print(f"\n{name}:")
        for prop_name in sorted(set(pred.properties.keys()) & set(actual.keys())):
            predicted = pred.properties[prop_name].value
            measured = actual[prop_name]
            error = abs(predicted - measured)
            pct = error / abs(measured) * 100 if measured != 0 else 0
            print(f"  {prop_name:25s}: predicted={predicted:8.2f}  "
                  f"actual={measured:8.2f}  error={pct:.1f}%")
