# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Metal Interface Validator
============================

Validates metal interface/joint viability between two materials,
analogous to polymer_bridge/interface_validator.py.

Pattern:
  Polymer bridge:  "Can polymer A blend with polymer B?"
  Metal bridge:    "Can metal A be joined to metal B?"

The validator combines all five interaction scorers into a weighted
composite MetalInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from metal_bridge.material_properties import MetalMaterial, get_metal
from metal_bridge.interaction_scoring import (
    score_galvanic_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_metallurgical_compatibility,
    score_corrosion_penalty,
    _get_base_element,
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
class MetalConditions:
    """Operating/environmental conditions that affect joint viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    environment: str = "indoor"  # "indoor", "outdoor", "marine", "industrial", "cryogenic"
    cyclic_loading: bool = False
    stress_MPa: float = 0.0


@dataclass
class MetalInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors PolymerInterfaceScore from polymer_bridge.
    """
    total: float                          # Weighted composite (0-1)
    galvanic_compatibility: float         # Component score
    thermal_compatibility: float          # Component score
    mechanical_compatibility: float       # Component score
    metallurgical_compatibility: float    # Component score
    corrosion_penalty: float              # Component score
    viable: bool                          # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'galvanic_compatibility': round(self.galvanic_compatibility, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'metallurgical_compatibility': round(self.metallurgical_compatibility, 4),
            'corrosion_penalty': round(self.corrosion_penalty, 4),
            'viable': self.viable,
        }


@dataclass
class MetalWeights:
    """Configurable weights for the five scoring components."""
    galvanic: float = 0.35  # Increased from 0.25 to penalize galvanic mismatch
    thermal: float = 0.20
    mechanical: float = 0.20
    metallurgical: float = 0.15  # Reduced from 0.20
    corrosion: float = 0.10  # Reduced from 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.galvanic + self.thermal + self.mechanical +
                 self.metallurgical + self.corrosion)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'MetalWeights':
        """Default weights for general metal compatibility."""
        return cls()

    @classmethod
    def structural_focus(cls) -> 'MetalWeights':
        """Weights for structural/load-bearing applications."""
        return cls(
            galvanic=0.15,
            thermal=0.15,
            mechanical=0.35,
            metallurgical=0.20,
            corrosion=0.15,
        )

    @classmethod
    def corrosion_focus(cls) -> 'MetalWeights':
        """Weights for marine/corrosive environment applications."""
        return cls(
            galvanic=0.35,
            thermal=0.10,
            mechanical=0.10,
            metallurgical=0.15,
            corrosion=0.30,
        )

    @classmethod
    def high_temp_focus(cls) -> 'MetalWeights':
        """Weights for high-temperature applications (turbines, exhaust)."""
        return cls(
            galvanic=0.10,
            thermal=0.35,
            mechanical=0.20,
            metallurgical=0.20,
            corrosion=0.15,
        )


class MetalInterfaceValidator:
    """
    Validates metal interface/joint viability.

    Mirrors PolymerInterfaceValidator pattern exactly.

    Usage:
        validator = MetalInterfaceValidator()
        result = validator.validate('SS_304', 'SS_316')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[MetalWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or MetalWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        metal_a: str,
        metal_b: str,
        conditions: Optional[MetalConditions] = None,
    ) -> MetalInterfaceScore:
        """
        Validate an interface between two metals by name.

        Args:
            metal_a: Name of first metal
            metal_b: Name of second metal
            conditions: Optional operating conditions

        Returns:
            MetalInterfaceScore with component breakdown

        Raises:
            ValueError: If metal name not found
        """
        mat_a = get_metal(metal_a)
        mat_b = get_metal(metal_b)
        if mat_a is None:
            raise ValueError(f"Unknown metal: '{metal_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown metal: '{metal_b}'")

        return self.validate_materials(mat_a, mat_b, conditions)

    def validate_materials(
        self,
        material_a: MetalMaterial,
        material_b: MetalMaterial,
        conditions: Optional[MetalConditions] = None,
    ) -> MetalInterfaceScore:
        """
        Validate an interface between two MetalMaterial objects.

        Args:
            material_a: First metal
            material_b: Second metal
            conditions: Optional operating conditions

        Returns:
            MetalInterfaceScore with full breakdown
        """
        conditions = conditions or MetalConditions()

        # Run all five scorers
        s_galv = score_galvanic_compatibility(material_a, material_b)
        s_therm = score_thermal_compatibility(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_met = score_metallurgical_compatibility(material_a, material_b)
        s_corr = score_corrosion_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'galvanic': s_galv.score,
            'thermal': s_therm.score,
            'mechanical': s_mech.score,
            'metallurgical': s_met.score,
            'corrosion': s_corr.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Weighted composite
        total = (
            self.weights.galvanic * scores['galvanic'] +
            self.weights.thermal * scores['thermal'] +
            self.weights.mechanical * scores['mechanical'] +
            self.weights.metallurgical * scores['metallurgical'] +
            self.weights.corrosion * scores['corrosion']
        )

        # Collect details
        all_details = {
            'galvanic_details': s_galv.details,
            'thermal_details': s_therm.details,
            'mechanical_details': s_mech.details,
            'metallurgical_details': s_met.details,
            'corrosion_details': s_corr.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'environment': conditions.environment,
                'cyclic_loading': conditions.cyclic_loading,
            },
            'metal_a': material_a.formula,
            'metal_b': material_b.formula,
        }

        # Veto check: Severe galvanic mismatch (>0.5V) requires electrical insulation
        # Per MIL-STD-889D: >0.5V = "avoid direct contact"
        is_viable = total >= self.viability_threshold
        elem_a = _get_base_element(material_a)
        elem_b = _get_base_element(material_b)
        wet_or_corrosive = conditions.environment in {
            "outdoor",
            "marine",
            "industrial",
            "conductive_moisture",
            "wet",
            "salt_spray",
        } or conditions.humidity_pct > 80
        fe_base_join = elem_a == "Fe" and elem_b == "Fe"
        if scores['galvanic'] < 0.30 and not (fe_base_join and not wet_or_corrosive):
            is_viable = False
            # A physical block survives composition (min/annihilator), it is not
            # diluted by the weighted sum. Capping `total` also keeps the SURFACED
            # SCORE consistent with the verdict: without this a vetoed pair could
            # report a higher score than a non-vetoed one (Ni+Fe 0.721 -> not
            # viable vs Al+Fe 0.674 -> viable), so the number contradicted the
            # decision it was shown next to.
            total = _vetoed_score(total)
            all_details['veto'] = 'Severe galvanic mismatch (>0.5V potential difference): direct contact prohibited per MIL-STD-889D'
        elif scores['galvanic'] < 0.30:
            all_details['galvanic_veto_relaxed'] = (
                'Fe-base stainless/carbon or low-alloy steel joint in non-corrosive service; '
                'galvanic warning retained but not treated as a hard veto.'
            )

        # Veto check: known-bad corrosion pair (MIL-STD-889D incompatible groups)
        if scores['corrosion'] < 0.55:
            is_viable = False
            total = _vetoed_score(total)
            all_details['veto'] = all_details.get('veto', '') + '; known corrosion-incompatible pair (MIL-STD-889D)'

        return MetalInterfaceScore(
            total=total,
            galvanic_compatibility=scores['galvanic'],
            thermal_compatibility=scores['thermal'],
            mechanical_compatibility=scores['mechanical'],
            metallurgical_compatibility=scores['metallurgical'],
            corrosion_penalty=scores['corrosion'],
            viable=is_viable,
            details=all_details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: MetalMaterial,
        material_b: MetalMaterial,
        conditions: MetalConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # Marine environment: galvanic and corrosion much worse
        if conditions.environment == "marine":
            modified['galvanic'] *= 0.7
            modified['corrosion'] *= 0.6

        # Industrial (acidic, polluted): corrosion worse
        if conditions.environment == "industrial":
            modified['corrosion'] *= 0.75

        # Outdoor: moderate corrosion penalty
        if conditions.environment == "outdoor":
            modified['corrosion'] *= 0.85

        # High temperature: creep and oxidation concerns
        if conditions.temperature_C > 300:
            temp_factor = max(0.5, 1.0 - (conditions.temperature_C - 300) / 1000)
            modified['corrosion'] *= temp_factor
            # CTE effects amplified at high temperature
            modified['thermal'] *= max(0.6, 1.0 - (conditions.temperature_C - 300) / 1500)

        # Cryogenic: embrittlement risk for BCC metals
        if conditions.environment == "cryogenic" or conditions.temperature_C < -50:
            for mat in [material_a, material_b]:
                if mat.crystal_system == CrystalSystem.BCC:
                    modified['mechanical'] *= 0.7

        # Cyclic loading: fatigue becomes critical
        if conditions.cyclic_loading:
            for mat in [material_a, material_b]:
                if MetalFailureMode.FATIGUE in mat.failure_modes:
                    modified['mechanical'] *= 0.85

        # High humidity: galvanic corrosion accelerated
        if conditions.humidity_pct > 80:
            modified['galvanic'] *= 0.85
            modified['corrosion'] *= 0.9

        return modified

    def validate_all_interfaces(
        self,
        metals: List[str],
        conditions: Optional[MetalConditions] = None,
    ) -> Dict[Tuple[str, str], MetalInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of metals.

        Args:
            metals: List of metal names
            conditions: Operating conditions

        Returns:
            Dict mapping (metal_a, metal_b) to MetalInterfaceScore
        """
        results = {}
        for i in range(len(metals)):
            for j in range(i + 1, len(metals)):
                key = (metals[i], metals[j])
                try:
                    results[key] = self.validate(metals[i], metals[j], conditions)
                except ValueError:
                    pass
        return results


# Need CrystalSystem for condition modifiers
from metal_bridge.material_properties import CrystalSystem, MetalFailureMode


def validate_interface(
    metal_a: str,
    metal_b: str,
    conditions: Optional[MetalConditions] = None,
) -> MetalInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = MetalInterfaceValidator()
    return validator.validate(metal_a, metal_b, conditions)
