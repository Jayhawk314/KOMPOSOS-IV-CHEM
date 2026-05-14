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

        return self.validate_materials(mat_a, mat_b, conditions)

    def validate_materials(
        self,
        material_a: CeramicMaterial,
        material_b: CeramicMaterial,
        conditions: Optional[CeramicConditions] = None,
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

        return CeramicInterfaceScore(
            total=total,
            sintering_compatibility=scores['sintering'],
            cte_match=scores['cte'],
            mechanical_compatibility=scores['mechanical'],
            chemical_compatibility=scores['chemical'],
            degradation_penalty=scores['degradation'],
            viable=total >= self.viability_threshold,
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
