# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Ceramic Interface Validator
============================

Validates ceramic interface/composite viability between two materials,
analogous to metal_bridge/interface_validator.py.

Pattern:
  Metal bridge:    "Can metal A be joined to metal B?"
  Ceramic bridge:  "Can ceramic A be co-sintered/bonded with ceramic B?"

The validator combines all five interaction scorers into a weighted
composite CeramicInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ceramic_bridge.material_properties import CeramicMaterial, CeramicFailureMode, get_ceramic
from ceramic_bridge.interaction_scoring import (
    score_sintering_compatibility,
    score_cte_match,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    ScorerResult,
)
from oracle.compatibility_context import CompatibilityContext
from oracle.typed_morphisms import apply_typed_morphism_adjustment


@dataclass
class CeramicConditions:
    """Operating/environmental conditions that affect composite viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    environment: str = "indoor"  # "indoor", "outdoor", "furnace", "corrosive", "biomedical"
    thermal_cycling: bool = False
    mechanical_load_MPa: float = 0.0


@dataclass
class CeramicInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors MetalInterfaceScore from metal_bridge.
    """
    total: float                           # Weighted composite (0-1)
    sintering_compatibility: float         # Component score
    cte_match: float                       # Component score
    mechanical_compatibility: float        # Component score
    chemical_compatibility: float          # Component score
    degradation_penalty: float             # Component score
    viable: bool                           # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'sintering_compatibility': round(self.sintering_compatibility, 4),
            'cte_match': round(self.cte_match, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'chemical_compatibility': round(self.chemical_compatibility, 4),
            'degradation_penalty': round(self.degradation_penalty, 4),
            'viable': self.viable,
        }


@dataclass
class CeramicWeights:
    """Configurable weights for the five scoring components."""
    sintering: float = 0.20
    cte: float = 0.25
    mechanical: float = 0.20
    chemical: float = 0.20
    degradation: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.sintering + self.cte + self.mechanical +
                 self.chemical + self.degradation)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'CeramicWeights':
        """Default weights for general ceramic compatibility."""
        return cls()

    @classmethod
    def structural_focus(cls) -> 'CeramicWeights':
        """Weights for structural/load-bearing ceramic applications."""
        return cls(
            sintering=0.15,
            cte=0.20,
            mechanical=0.35,
            chemical=0.15,
            degradation=0.15,
        )

    @classmethod
    def thermal_focus(cls) -> 'CeramicWeights':
        """Weights for thermal barrier / high-temp applications."""
        return cls(
            sintering=0.15,
            cte=0.35,
            mechanical=0.15,
            chemical=0.20,
            degradation=0.15,
        )

    @classmethod
    def biomedical_focus(cls) -> 'CeramicWeights':
        """Weights for biomedical ceramic applications."""
        return cls(
            sintering=0.10,
            cte=0.15,
            mechanical=0.20,
            chemical=0.25,
            degradation=0.30,
        )


class CeramicInterfaceValidator:
    """
    Validates ceramic interface/composite viability.

    Mirrors MetalInterfaceValidator pattern exactly.

    Usage:
        validator = CeramicInterfaceValidator()
        result = validator.validate('Al2O3', 'ZrO2_YSZ')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[CeramicWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or CeramicWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        ceramic_a: str,
        ceramic_b: str,
        conditions: Optional[CeramicConditions] = None,
    ) -> CeramicInterfaceScore:
        """
        Validate an interface between two ceramics by name.

        Args:
            ceramic_a: Name of first ceramic
            ceramic_b: Name of second ceramic
            conditions: Optional operating conditions

        Returns:
            CeramicInterfaceScore with component breakdown

        Raises:
            ValueError: If ceramic name not found
        """
        mat_a = get_ceramic(ceramic_a)
        mat_b = get_ceramic(ceramic_b)
        if mat_a is None:
            raise ValueError(f"Unknown ceramic: '{ceramic_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown ceramic: '{ceramic_b}'")

        return self.validate_materials(mat_a, mat_b, conditions, ceramic_a, ceramic_b)

    def validate_materials(
        self,
        material_a: CeramicMaterial,
        material_b: CeramicMaterial,
        conditions: Optional[CeramicConditions] = None,
        material_a_key: Optional[str] = None,
        material_b_key: Optional[str] = None,
    ) -> CeramicInterfaceScore:
        """
        Validate an interface between two CeramicMaterial objects.

        Args:
            material_a: First ceramic
            material_b: Second ceramic
            conditions: Optional operating conditions

        Returns:
            CeramicInterfaceScore with full breakdown
        """
        conditions = conditions or CeramicConditions()
        material_a_key = material_a_key or _ceramic_key(material_a)
        material_b_key = material_b_key or _ceramic_key(material_b)

        # Run all five scorers
        s_sint = score_sintering_compatibility(material_a, material_b)
        s_cte = score_cte_match(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_chem = score_chemical_compatibility(material_a, material_b)
        s_deg = score_degradation_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'sintering': s_sint.score,
            'cte': s_cte.score,
            'mechanical': s_mech.score,
            'chemical': s_chem.score,
            'degradation': s_deg.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Weighted composite
        total = (
            self.weights.sintering * scores['sintering'] +
            self.weights.cte * scores['cte'] +
            self.weights.mechanical * scores['mechanical'] +
            self.weights.chemical * scores['chemical'] +
            self.weights.degradation * scores['degradation']
        )

        # Collect details
        all_details = {
            'sintering_details': s_sint.details,
            'cte_details': s_cte.details,
            'mechanical_details': s_mech.details,
            'chemical_details': s_chem.details,
            'degradation_details': s_deg.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'environment': conditions.environment,
                'thermal_cycling': conditions.thermal_cycling,
            },
            'ceramic_a': material_a.formula,
            'ceramic_b': material_b.formula,
        }

        # Veto check: Large CTE mismatch causes thermal shock cracking
        # ASM Handbook: ΔCTE > 4 ppm/K = high risk of interfacial failure
        # Exception: known compatible composites survive CTE mismatch
        # (e.g., Al2O3-SiC whisker composites, BaTiO3-PZT multilayers)
        from ceramic_bridge.interaction_scoring import _COMPATIBLE_PAIRS, _get_base_formula
        from ceramic_bridge.material_properties import CeramicClass
        is_viable = total >= self.viability_threshold
        cte_a = material_a.cte_per_K
        cte_b = material_b.cte_per_K
        if cte_a is not None and cte_b is not None:
            cte_diff = abs(cte_a - cte_b)
            name_a = _get_base_formula(material_a)
            name_b = _get_base_formula(material_b)
            pair_known_good = (name_a, name_b) in _COMPATIBLE_PAIRS or (name_b, name_a) in _COMPATIBLE_PAIRS
            silica_like_a = name_a == "SiO2" or material_a.ceramic_class == CeramicClass.GLASS
            silica_like_b = name_b == "SiO2" or material_b.ceramic_class == CeramicClass.GLASS
            silica_glass_family = (
                not conditions.thermal_cycling
                and conditions.environment != "furnace"
                and silica_like_a
                and silica_like_b
                and "SiO2" in {name_a, name_b}
            )
            if silica_glass_family:
                all_details['silica_glass_family_exception'] = (
                    'Ambient silica-network glass family contact; CTE veto is not applied '
                    'unless thermal cycling/furnace sealing context is requested.'
                )
            if cte_diff > 4.0 and not pair_known_good and not silica_glass_family:
                is_viable = False
                total = min(total, 0.38) # Below 0.45 threshold
                all_details['veto'] = f'CTE mismatch {cte_diff:.1f} ppm/K > 4 ppm/K: thermal shock cracking risk (ASM Handbook Vol 4)'

        # Veto check: known-bad ceramic pairs with severe degradation
        if scores['degradation'] < 0.15:
            is_viable = False
            total = min(total, 0.35)
            all_details['veto'] = all_details.get('veto', '') + '; known-bad pairing (degradation veto)'

        morphism_adjustment = apply_typed_morphism_adjustment(
            total,
            is_viable,
            material_a_key,
            material_b_key,
            "ceramic",
            CompatibilityContext(
                environment=conditions.environment,
                temperature_C=conditions.temperature_C,
            ),
        )
        if morphism_adjustment.morphism is not None:
            all_details['typed_morphism'] = morphism_adjustment.to_dict()
        if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
            total = morphism_adjustment.score
            is_viable = morphism_adjustment.predicted_compatible

        return CeramicInterfaceScore(
            total=total,
            sintering_compatibility=scores['sintering'],
            cte_match=scores['cte'],
            mechanical_compatibility=scores['mechanical'],
            chemical_compatibility=scores['chemical'],
            degradation_penalty=scores['degradation'],
            viable=is_viable,
            details=all_details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: CeramicMaterial,
        material_b: CeramicMaterial,
        conditions: CeramicConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # Furnace / high-temperature environment
        if conditions.environment == "furnace" or conditions.temperature_C > 500:
            temp_factor = max(0.5, 1.0 - (conditions.temperature_C - 500) / 2000)
            modified['degradation'] *= temp_factor
            # CTE effects amplified at high temperature
            modified['cte'] *= max(0.6, 1.0 - (conditions.temperature_C - 500) / 2000)

        # Corrosive environment
        if conditions.environment == "corrosive":
            modified['degradation'] *= 0.7
            modified['chemical'] *= 0.8

        # Biomedical environment
        if conditions.environment == "biomedical":
            modified['degradation'] *= 0.8
            modified['chemical'] *= 0.85

        # Thermal cycling: CTE mismatch becomes more critical
        if conditions.thermal_cycling:
            # Penalize if either material is thermal-shock susceptible
            for mat in [material_a, material_b]:
                if CeramicFailureMode.THERMAL_SHOCK in mat.failure_modes:
                    modified['cte'] *= 0.8
            # General thermal cycling penalty on CTE
            modified['cte'] *= 0.9

        # High humidity: hydrolysis risk
        if conditions.humidity_pct > 80:
            for mat in [material_a, material_b]:
                if (CeramicFailureMode.HYDROLYSIS in mat.failure_modes or
                        mat.chemical_stability == 'hygroscopic'):
                    modified['degradation'] *= 0.7

        # Outdoor: moisture + temperature cycling
        if conditions.environment == "outdoor":
            modified['degradation'] *= 0.85

        return modified

    def validate_all_interfaces(
        self,
        ceramics: List[str],
        conditions: Optional[CeramicConditions] = None,
    ) -> Dict[Tuple[str, str], CeramicInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of ceramics.

        Args:
            ceramics: List of ceramic names
            conditions: Operating conditions

        Returns:
            Dict mapping (ceramic_a, ceramic_b) to CeramicInterfaceScore
        """
        results = {}
        for i in range(len(ceramics)):
            for j in range(i + 1, len(ceramics)):
                key = (ceramics[i], ceramics[j])
                try:
                    results[key] = self.validate(ceramics[i], ceramics[j], conditions)
                except ValueError:
                    pass
        return results


def validate_interface(
    ceramic_a: str,
    ceramic_b: str,
    conditions: Optional[CeramicConditions] = None,
) -> CeramicInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = CeramicInterfaceValidator()
    return validator.validate(ceramic_a, ceramic_b, conditions)


def _ceramic_key(material: CeramicMaterial) -> str:
    from ceramic_bridge.material_properties import ALL_CERAMICS

    for name, candidate in ALL_CERAMICS.items():
        if candidate is material:
            return name
    return material.formula
