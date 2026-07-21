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

from oracle.compatibility_context import CompatibilityContext
from oracle.typed_morphisms import apply_typed_morphism_adjustment

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

        return self.validate_materials(mat_a, mat_b, conditions, glass_a, glass_b)

    def validate_materials(
        self,
        material_a: GlassMaterial,
        material_b: GlassMaterial,
        conditions: Optional[GlassConditions] = None,
        material_a_key: Optional[str] = None,
        material_b_key: Optional[str] = None,
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
        material_a_key = material_a_key or _glass_key(material_a)
        material_b_key = material_b_key or _glass_key(material_b)

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

        is_viable = total >= self.viability_threshold

        # CTE veto: >3 ppm/K difference causes stress fracture at seal
        # (Shelby, Introduction to Glass Science 2005)
        # Exceptions:
        # - same glass class (e.g., both chalcogenide) can tolerate larger CTE diffs
        # - known graded-seal pairs (Schott catalog, Hench biomedical)
        from glass_bridge.material_properties import CompositionType
        comp_a = getattr(material_a, 'composition_type', None)
        comp_b = getattr(material_b, 'composition_type', None)
        class_a = getattr(material_a, 'glass_class', None)
        class_b = getattr(material_b, 'glass_class', None)
        same_family = class_a is not None and class_a == class_b
        # Known pairs that work despite CTE mismatch (graded seals, biomedical)
        _CTE_EXEMPT_PAIRS = {
            # Schott graded seal standard (Schott Optical Glass Catalog 2023)
            frozenset({'BK7', 'Boro_33'}),
            frozenset({'Boro_33', 'FusedSilica'}),
            # Biomedical: Hench, J. Am. Ceram. Soc. 1998
            frozenset({'Bioglass_45S5', 'SodaLime_Float'}),
        }
        name_a = material_a_key
        name_b = material_b_key
        pair_exempt = name_a and name_b and frozenset({name_a, name_b}) in _CTE_EXEMPT_PAIRS
        optical_assembly_exempt = (
            frozenset({name_a, name_b}) == frozenset({'BK7', 'FusedSilica'})
            and conditions.environment != "furnace"
            and not conditions.thermal_cycling
        )
        cte_a = material_a.cte_per_K
        cte_b = material_b.cte_per_K
        if cte_a is not None and cte_b is not None:
            cte_diff = abs(cte_a - cte_b)
            if cte_diff > 3.0 and not same_family and not pair_exempt and not optical_assembly_exempt:
                is_viable = False
                # A physical block survives composition (min/annihilator) and must
                # also keep the surfaced score consistent with the verdict; a
                # vetoed pair must never outrank a viable one.
                total = _vetoed_score(total)
                all_details['veto'] = f'CTE mismatch {cte_diff:.1f} ppm/K > 3 ppm/K: seal will crack (Shelby 2005)'

        # Chemical incompatibility veto: phosphate + silicate network reaction
        # (Campbell & Suratwala, J. Non-Cryst. Solids 2000)
        if comp_a and comp_b:
            incompat = {
                frozenset({CompositionType.PHOSPHATE, CompositionType.SILICATE}),
            }
            if frozenset({comp_a, comp_b}) in incompat:
                is_viable = False
                total = _vetoed_score(total)
                all_details['veto'] = all_details.get('veto', '') + '; phosphate-silicate chemical incompatibility'

        morphism_adjustment = apply_typed_morphism_adjustment(
            total,
            is_viable,
            material_a_key,
            material_b_key,
            "glass",
            CompatibilityContext(
                interface_type="optical_glass_assembly" if optical_assembly_exempt else None,
                environment=conditions.environment,
                temperature_C=conditions.temperature_C,
            ),
        )
        if morphism_adjustment.morphism is not None:
            all_details['typed_morphism'] = morphism_adjustment.to_dict()
        if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
            total = morphism_adjustment.score
            is_viable = morphism_adjustment.predicted_compatible

        return GlassInterfaceScore(
            total=total,
            thermal_expansion_match=scores['thermal'],
            viscosity_compatibility=scores['viscosity'],
            mechanical_compatibility=scores['mechanical'],
            chemical_compatibility=scores['chemical'],
            degradation_penalty=scores['degradation'],
            viable=is_viable,
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


def _glass_key(material: GlassMaterial) -> str:
    from glass_bridge.material_properties import ALL_GLASSES

    for name, candidate in ALL_GLASSES.items():
        if candidate is material:
            return name
    return material.formula
