# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Glass Interface Validator
============================

Validates glass interface/assembly viability between two materials,
analogous to ceramic_bridge/interface_validator.py.

Pattern:
  Ceramic bridge:  "Can ceramic A be co-sintered with ceramic B?"
  Glass bridge:    "Can glass A be sealed/bonded/assembled with glass B?"

The validator combines all five interaction scorers into a weighted
composite GlassInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from glass_bridge.material_properties import GlassMaterial, GlassFailureMode, get_glass
from glass_bridge.interaction_scoring import (
    score_thermal_expansion_match,
    score_viscosity_compatibility,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    ScorerResult,
)


@dataclass
class GlassConditions:
    """Operating/environmental conditions that affect glass assembly viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    environment: str = "indoor"  # "indoor", "outdoor", "furnace", "chemical", "biomedical", "optical_clean"
    thermal_cycling: bool = False
    uv_exposure: bool = False


@dataclass
class GlassInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors CeramicInterfaceScore from ceramic_bridge.
    """
    total: float                           # Weighted composite (0-1)
    thermal_expansion_match: float         # Component score
    viscosity_compatibility: float         # Component score
    mechanical_compatibility: float        # Component score
    chemical_compatibility: float          # Component score
    degradation_penalty: float             # Component score
    viable: bool                           # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'thermal_expansion_match': round(self.thermal_expansion_match, 4),
            'viscosity_compatibility': round(self.viscosity_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'chemical_compatibility': round(self.chemical_compatibility, 4),
            'degradation_penalty': round(self.degradation_penalty, 4),
            'viable': self.viable,
        }


@dataclass
class GlassWeights:
    """Configurable weights for the five scoring components."""
    thermal: float = 0.30
    viscosity: float = 0.20
    mechanical: float = 0.15
    chemical: float = 0.20
    degradation: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.thermal + self.viscosity + self.mechanical +
                 self.chemical + self.degradation)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'GlassWeights':
        """Default weights for general glass compatibility."""
        return cls()

    @classmethod
    def optical_focus(cls) -> 'GlassWeights':
        """Weights for optical glass assemblies (lenses, prisms)."""
        return cls(
            thermal=0.25,
            viscosity=0.15,
            mechanical=0.20,
            chemical=0.30,
            degradation=0.10,
        )

    @classmethod
    def sealing_focus(cls) -> 'GlassWeights':
        """Weights for glass-to-glass sealing applications."""
        return cls(
            thermal=0.35,
            viscosity=0.30,
            mechanical=0.10,
            chemical=0.15,
            degradation=0.10,
        )

    @classmethod
    def biomedical_focus(cls) -> 'GlassWeights':
        """Weights for biomedical glass applications."""
        return cls(
            thermal=0.15,
            viscosity=0.10,
            mechanical=0.15,
            chemical=0.25,
            degradation=0.35,
        )


class GlassInterfaceValidator:
    """
    Validates glass interface/assembly viability.

    Mirrors CeramicInterfaceValidator pattern exactly.

    Usage:
        validator = GlassInterfaceValidator()
        result = validator.validate('BK7', 'F2')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[GlassWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or GlassWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        glass_a: str,
        glass_b: str,
        conditions: Optional[GlassConditions] = None,
    ) -> GlassInterfaceScore:
        """
        Validate an interface between two glasses by name.

        Args:
            glass_a: Name of first glass
            glass_b: Name of second glass
            conditions: Optional operating conditions

        Returns:
            GlassInterfaceScore with component breakdown

        Raises:
            ValueError: If glass name not found
        """
        mat_a = get_glass(glass_a)
        mat_b = get_glass(glass_b)
        if mat_a is None:
            raise ValueError(f"Unknown glass: '{glass_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown glass: '{glass_b}'")

        return self.validate_materials(mat_a, mat_b, conditions)

    def validate_materials(
        self,
        material_a: GlassMaterial,
        material_b: GlassMaterial,
        conditions: Optional[GlassConditions] = None,
    ) -> GlassInterfaceScore:
        """
        Validate an interface between two GlassMaterial objects.

        Args:
            material_a: First glass
            material_b: Second glass
            conditions: Optional operating conditions

        Returns:
            GlassInterfaceScore with full breakdown
        """
        conditions = conditions or GlassConditions()

        # Run all five scorers
        s_cte = score_thermal_expansion_match(material_a, material_b)
        s_visc = score_viscosity_compatibility(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_chem = score_chemical_compatibility(material_a, material_b)
        s_deg = score_degradation_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'thermal': s_cte.score,
            'viscosity': s_visc.score,
            'mechanical': s_mech.score,
            'chemical': s_chem.score,
            'degradation': s_deg.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Weighted composite
        total = (
            self.weights.thermal * scores['thermal'] +
            self.weights.viscosity * scores['viscosity'] +
            self.weights.mechanical * scores['mechanical'] +
            self.weights.chemical * scores['chemical'] +
            self.weights.degradation * scores['degradation']
        )

        # Collect details
        all_details = {
            'thermal_details': s_cte.details,
            'viscosity_details': s_visc.details,
            'mechanical_details': s_mech.details,
            'chemical_details': s_chem.details,
            'degradation_details': s_deg.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'environment': conditions.environment,
                'thermal_cycling': conditions.thermal_cycling,
            },
            'glass_a': material_a.formula,
            'glass_b': material_b.formula,
        }

        return GlassInterfaceScore(
            total=total,
            thermal_expansion_match=scores['thermal'],
            viscosity_compatibility=scores['viscosity'],
            mechanical_compatibility=scores['mechanical'],
            chemical_compatibility=scores['chemical'],
            degradation_penalty=scores['degradation'],
            viable=total >= self.viability_threshold,
            details=all_details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: GlassMaterial,
        material_b: GlassMaterial,
        conditions: GlassConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # Furnace / high-temperature
        if conditions.environment == "furnace" or conditions.temperature_C > 300:
            modified['degradation'] *= max(0.6, 1.0 - (conditions.temperature_C - 300) / 1500)

        # Chemical environment
        if conditions.environment == "chemical":
            modified['degradation'] *= 0.7
            modified['chemical'] *= 0.8

        # Biomedical
        if conditions.environment == "biomedical":
            modified['degradation'] *= 0.8
            modified['chemical'] *= 0.85

        # Thermal cycling: CTE mismatch becomes critical
        if conditions.thermal_cycling:
            for mat in [material_a, material_b]:
                if GlassFailureMode.THERMAL_SHOCK in mat.failure_modes:
                    modified['thermal'] *= 0.8
            modified['thermal'] *= 0.9

        # Outdoor: moisture + UV + temp cycling
        if conditions.environment == "outdoor":
            modified['degradation'] *= 0.85
            for mat in [material_a, material_b]:
                if GlassFailureMode.WEATHERING in mat.failure_modes:
                    modified['degradation'] *= 0.8

        # UV exposure
        if conditions.uv_exposure:
            for mat in [material_a, material_b]:
                if GlassFailureMode.SOLARIZATION in mat.failure_modes:
                    modified['degradation'] *= 0.8

        # High humidity
        if conditions.humidity_pct > 80:
            for mat in [material_a, material_b]:
                if GlassFailureMode.HYDROLYTIC_ATTACK in mat.failure_modes:
                    modified['degradation'] *= 0.7

        return modified

    def validate_all_interfaces(
        self,
        glasses: List[str],
        conditions: Optional[GlassConditions] = None,
    ) -> Dict[Tuple[str, str], GlassInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of glasses.

        Args:
            glasses: List of glass names
            conditions: Operating conditions

        Returns:
            Dict mapping (glass_a, glass_b) to GlassInterfaceScore
        """
        results = {}
        for i in range(len(glasses)):
            for j in range(i + 1, len(glasses)):
                key = (glasses[i], glasses[j])
                try:
                    results[key] = self.validate(glasses[i], glasses[j], conditions)
                except ValueError:
                    pass
        return results


def validate_interface(
    glass_a: str,
    glass_b: str,
    conditions: Optional[GlassConditions] = None,
) -> GlassInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = GlassInterfaceValidator()
    return validator.validate(glass_a, glass_b, conditions)
