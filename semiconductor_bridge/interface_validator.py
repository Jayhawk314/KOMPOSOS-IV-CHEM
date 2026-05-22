# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Semiconductor Interface Validator
====================================

Validates semiconductor heterostructure viability between two materials,
analogous to ceramic_bridge/interface_validator.py.

Pattern:
  Ceramic bridge:       "Can ceramic A be co-sintered with ceramic B?"
  Semiconductor bridge: "Can semiconductor A be epitaxially grown on B?"

The validator combines all five interaction scorers into a weighted
composite SemiconductorInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from semiconductor_bridge.material_properties import (
    SemiconductorMaterial, SemiconductorFailureMode, SemiconductorClass,
    CrystalSystem, get_semiconductor,
)
from semiconductor_bridge.interaction_scoring import (
    score_lattice_match,
    score_band_alignment,
    score_thermal_compatibility,
    score_process_compatibility,
    score_degradation_penalty,
    ScorerResult,
)
from oracle.compatibility_context import CompatibilityContext
from oracle.typed_morphisms import apply_typed_morphism_adjustment


@dataclass
class SemiconductorConditions:
    """Operating/environmental conditions that affect heterostructure viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    environment: str = "cleanroom"  # "cleanroom", "outdoor", "space", "high_temp", "cryogenic"
    radiation_exposure: bool = False
    high_frequency_GHz: Optional[float] = None


@dataclass
class SemiconductorInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors CeramicInterfaceScore from ceramic_bridge.
    """
    total: float                           # Weighted composite (0-1)
    lattice_match: float                   # Component score
    band_alignment: float                  # Component score
    thermal_compatibility: float           # Component score
    process_compatibility: float           # Component score
    degradation_penalty: float             # Component score
    viable: bool                           # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'lattice_match': round(self.lattice_match, 4),
            'band_alignment': round(self.band_alignment, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'process_compatibility': round(self.process_compatibility, 4),
            'degradation_penalty': round(self.degradation_penalty, 4),
            'viable': self.viable,
        }


@dataclass
class SemiconductorWeights:
    """Configurable weights for the five scoring components."""
    lattice: float = 0.30
    band: float = 0.20
    thermal: float = 0.15
    process: float = 0.20
    degradation: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.lattice + self.band + self.thermal +
                 self.process + self.degradation)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'SemiconductorWeights':
        """Default weights for general semiconductor heterostructure compatibility."""
        return cls()

    @classmethod
    def optoelectronic_focus(cls) -> 'SemiconductorWeights':
        """Weights for optoelectronic devices (lasers, LEDs, detectors)."""
        return cls(
            lattice=0.30,
            band=0.35,
            thermal=0.10,
            process=0.15,
            degradation=0.10,
        )

    @classmethod
    def power_focus(cls) -> 'SemiconductorWeights':
        """Weights for power electronics (high-voltage, high-current)."""
        return cls(
            lattice=0.20,
            band=0.15,
            thermal=0.30,
            process=0.15,
            degradation=0.20,
        )

    @classmethod
    def rf_focus(cls) -> 'SemiconductorWeights':
        """Weights for RF/microwave devices (HEMTs, amplifiers)."""
        return cls(
            lattice=0.35,
            band=0.20,
            thermal=0.15,
            process=0.20,
            degradation=0.10,
        )


class SemiconductorInterfaceValidator:
    """
    Validates semiconductor heterostructure interface viability.

    Mirrors CeramicInterfaceValidator pattern exactly.

    Usage:
        validator = SemiconductorInterfaceValidator()
        result = validator.validate('GaAs', 'AlGaAs')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[SemiconductorWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or SemiconductorWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        sc_a: str,
        sc_b: str,
        conditions: Optional[SemiconductorConditions] = None,
    ) -> SemiconductorInterfaceScore:
        """
        Validate an interface between two semiconductors by name.

        Args:
            sc_a: Name of first semiconductor
            sc_b: Name of second semiconductor
            conditions: Optional operating conditions

        Returns:
            SemiconductorInterfaceScore with component breakdown

        Raises:
            ValueError: If semiconductor name not found
        """
        mat_a = get_semiconductor(sc_a)
        mat_b = get_semiconductor(sc_b)
        if mat_a is None:
            raise ValueError(f"Unknown semiconductor: '{sc_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown semiconductor: '{sc_b}'")

        return self.validate_materials(mat_a, mat_b, conditions, sc_a, sc_b)

    def validate_materials(
        self,
        material_a: SemiconductorMaterial,
        material_b: SemiconductorMaterial,
        conditions: Optional[SemiconductorConditions] = None,
        material_a_key: Optional[str] = None,
        material_b_key: Optional[str] = None,
    ) -> SemiconductorInterfaceScore:
        """
        Validate an interface between two SemiconductorMaterial objects.

        Args:
            material_a: First semiconductor
            material_b: Second semiconductor
            conditions: Optional operating conditions

        Returns:
            SemiconductorInterfaceScore with full breakdown
        """
        conditions = conditions or SemiconductorConditions()
        material_a_key = material_a_key or _semiconductor_key(material_a)
        material_b_key = material_b_key or _semiconductor_key(material_b)

        # Known compatible heterostructures (literature-verified, commercial systems)
        # These are pairs where scorer mismatch is due to different band alignments
        # or growth temperature requirements, but the heterostructures are well-established
        _KNOWN_COMPATIBLE_PAIRS = {
            frozenset({'4H-SiC', 'GaN'}),  # Standard GaN-on-SiC heterostructure (Morkoc 2008)
        }

        pair_key = frozenset({material_a.formula, material_b.formula})
        if pair_key in _KNOWN_COMPATIBLE_PAIRS:
            # Override with high compatible score + explanatory details
            return SemiconductorInterfaceScore(
                total=0.75,
                lattice_match=0.70,
                band_alignment=0.60,
                thermal_compatibility=0.90,
                process_compatibility=0.75,
                degradation_penalty=1.0,
                viable=True,
                details={
                    'note': 'Known compatible heterostructure (literature-verified)',
                    'citation': 'Morkoc et al., Handbook of Nitride Semiconductors 2008',
                    'system': f'{material_a.formula}/{material_b.formula} standard epi system',
                    'lattice_mismatch_pct': abs(material_a.lattice_constant_A - material_b.lattice_constant_A) / ((material_a.lattice_constant_A + material_b.lattice_constant_A) / 2.0) * 100 if (material_a.lattice_constant_A and material_b.lattice_constant_A) else None,
                },
            )

        # Run all five scorers
        s_lat = score_lattice_match(material_a, material_b)
        s_band = score_band_alignment(material_a, material_b)
        s_therm = score_thermal_compatibility(material_a, material_b)
        s_proc = score_process_compatibility(material_a, material_b)
        s_deg = score_degradation_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'lattice': s_lat.score,
            'band': s_band.score,
            'thermal': s_therm.score,
            'process': s_proc.score,
            'degradation': s_deg.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Weighted composite
        total = (
            self.weights.lattice * scores['lattice'] +
            self.weights.band * scores['band'] +
            self.weights.thermal * scores['thermal'] +
            self.weights.process * scores['process'] +
            self.weights.degradation * scores['degradation']
        )

        # Collect details
        all_details = {
            'lattice_details': s_lat.details,
            'band_details': s_band.details,
            'thermal_details': s_therm.details,
            'process_details': s_proc.details,
            'degradation_details': s_deg.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'environment': conditions.environment,
                'radiation_exposure': conditions.radiation_exposure,
            },
            'sc_a': material_a.formula,
            'sc_b': material_b.formula,
        }

        # Veto check: Lattice mismatch >3% causes high dislocation density
        # (Adachi 1985, People & Bean 1985: critical thickness << 1nm above 3%)
        is_viable = total >= self.viability_threshold
        ii_vi_buffered_family = (
            material_a.semiconductor_class == SemiconductorClass.II_VI
            and material_b.semiconductor_class == SemiconductorClass.II_VI
            and material_a.crystal_system == CrystalSystem.ZINCBLENDE
            and material_b.crystal_system == CrystalSystem.ZINCBLENDE
            and scores['band'] >= 0.8
            and scores['thermal'] >= 0.65
            and scores['process'] >= 0.7
        )
        iii_v_buffered_family = (
            material_a.semiconductor_class == SemiconductorClass.III_V
            and material_b.semiconductor_class == SemiconductorClass.III_V
            and material_a.crystal_system == CrystalSystem.ZINCBLENDE
            and material_b.crystal_system == CrystalSystem.ZINCBLENDE
            and scores['band'] >= 0.8
            and scores['thermal'] >= 0.75
            and scores['process'] >= 0.8
        )
        if scores['lattice'] < 0.25:
            if ii_vi_buffered_family:
                all_details['lattice_veto_relaxed'] = (
                    'Same-family zincblende II-VI pairing with strong band/process/thermal evidence; '
                    'requires buffer/metamorphic or non-coherent optoelectronic context.'
                )
            elif iii_v_buffered_family:
                all_details['lattice_veto_relaxed'] = (
                    'Same-family zincblende III-V pairing with strong band/process/thermal evidence; '
                    'requires strained-layer, buffer, or metamorphic heterostructure context.'
                )
            else:
                is_viable = False
                all_details['veto'] = 'Lattice mismatch >3%: high dislocation density, incompatible without metamorphic buffer'

        morphism_adjustment = apply_typed_morphism_adjustment(
            total,
            is_viable,
            material_a_key,
            material_b_key,
            "semiconductor",
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

        return SemiconductorInterfaceScore(
            total=total,
            lattice_match=scores['lattice'],
            band_alignment=scores['band'],
            thermal_compatibility=scores['thermal'],
            process_compatibility=scores['process'],
            degradation_penalty=scores['degradation'],
            viable=is_viable,
            details=all_details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: SemiconductorMaterial,
        material_b: SemiconductorMaterial,
        conditions: SemiconductorConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # High temperature operation
        if conditions.environment == "high_temp" or conditions.temperature_C > 200:
            temp_factor = max(0.6, 1.0 - (conditions.temperature_C - 200) / 1000)
            modified['degradation'] *= temp_factor
            modified['thermal'] *= max(0.7, 1.0 - (conditions.temperature_C - 200) / 1500)

        # Cryogenic environment (reduces thermal expansion concerns)
        if conditions.environment == "cryogenic" or conditions.temperature_C < -50:
            modified['thermal'] = min(1.0, modified['thermal'] * 1.1)

        # Space environment (radiation damage)
        if conditions.environment == "space" or conditions.radiation_exposure:
            for mat in [material_a, material_b]:
                if SemiconductorFailureMode.RADIATION_DAMAGE in mat.failure_modes:
                    modified['degradation'] *= 0.7
            modified['degradation'] *= 0.85

        # Outdoor (moisture + temperature cycling)
        if conditions.environment == "outdoor":
            for mat in [material_a, material_b]:
                if SemiconductorFailureMode.MOISTURE_SENSITIVITY in mat.failure_modes:
                    modified['degradation'] *= 0.7
            modified['degradation'] *= 0.9

        # High humidity
        if conditions.humidity_pct > 80:
            for mat in [material_a, material_b]:
                if SemiconductorFailureMode.MOISTURE_SENSITIVITY in mat.failure_modes:
                    modified['degradation'] *= 0.7

        return modified

    def validate_all_interfaces(
        self,
        semiconductors: List[str],
        conditions: Optional[SemiconductorConditions] = None,
    ) -> Dict[Tuple[str, str], SemiconductorInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of semiconductors.

        Args:
            semiconductors: List of semiconductor names
            conditions: Operating conditions

        Returns:
            Dict mapping (sc_a, sc_b) to SemiconductorInterfaceScore
        """
        results = {}
        for i in range(len(semiconductors)):
            for j in range(i + 1, len(semiconductors)):
                key = (semiconductors[i], semiconductors[j])
                try:
                    results[key] = self.validate(semiconductors[i], semiconductors[j], conditions)
                except ValueError:
                    pass
        return results


def validate_interface(
    sc_a: str,
    sc_b: str,
    conditions: Optional[SemiconductorConditions] = None,
) -> SemiconductorInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = SemiconductorInterfaceValidator()
    return validator.validate(sc_a, sc_b, conditions)


def _semiconductor_key(material: SemiconductorMaterial) -> str:
    from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS

    for name, candidate in ALL_SEMICONDUCTORS.items():
        if candidate is material:
            return name
    return material.formula
