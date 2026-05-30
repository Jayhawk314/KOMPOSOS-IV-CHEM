# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer Interface Validator
===============================

Validates polymer interface/blend viability between two materials,
analogous to battery_bridge/interface_validator.py.

Pattern:
  Battery bridge:  "Can material A interface with material B?"
  Polymer bridge:  "Can polymer A blend with polymer B?"

The validator combines all five interaction scorers into a weighted
composite PolymerInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from polymer_bridge.material_properties import PolymerMaterial, get_polymer
from polymer_bridge.interaction_scoring import (
    score_solubility_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_chemical_resistance,
    score_aging_penalty,
    ScorerResult,
)
from polymer_bridge.flory_huggins import assess_flory_huggins


@dataclass
class PolymerConditions:
    """Operating/environmental conditions that affect polymer viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    uv_exposure: bool = False
    chemical_environment: str = "air"  # "air", "water", "acid", "base", "electrolyte"


@dataclass
class PolymerInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors InterfaceScore from battery_bridge.
    """
    total: float                        # Weighted composite (0-1)
    solubility_compatibility: float     # Component score
    thermal_compatibility: float        # Component score
    mechanical_compatibility: float     # Component score
    chemical_resistance: float          # Component score
    aging_penalty: float                # Component score
    viable: bool                        # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'solubility_compatibility': round(self.solubility_compatibility, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'chemical_resistance': round(self.chemical_resistance, 4),
            'aging_penalty': round(self.aging_penalty, 4),
            'viable': self.viable,
        }


@dataclass
class PolymerWeights:
    """Configurable weights for the five scoring components."""
    solubility: float = 0.35  # Increased from 0.30 to penalize immiscibility more
    thermal: float = 0.20
    mechanical: float = 0.20
    chemical_resistance: float = 0.10  # Reduced from 0.15
    aging: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.solubility + self.thermal + self.mechanical +
                 self.chemical_resistance + self.aging)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'PolymerWeights':
        """Default weights emphasizing solubility compatibility."""
        return cls()

    @classmethod
    def blend_focus(cls) -> 'PolymerWeights':
        """Weights for blend miscibility assessment."""
        return cls(
            solubility=0.40,
            thermal=0.20,
            mechanical=0.15,
            chemical_resistance=0.10,
            aging=0.15,
        )

    @classmethod
    def structural_focus(cls) -> 'PolymerWeights':
        """Weights for structural/mechanical applications."""
        return cls(
            solubility=0.15,
            thermal=0.15,
            mechanical=0.35,
            chemical_resistance=0.15,
            aging=0.20,
        )

    @classmethod
    def durability_focus(cls) -> 'PolymerWeights':
        """Weights emphasizing long-term durability and aging."""
        return cls(
            solubility=0.15,
            thermal=0.15,
            mechanical=0.15,
            chemical_resistance=0.20,
            aging=0.35,
        )


class PolymerInterfaceValidator:
    """
    Validates polymer interface/blend viability.

    Mirrors BatteryInterfaceValidator pattern exactly.

    Usage:
        validator = PolymerInterfaceValidator()
        result = validator.validate('PVDF', 'PMMA')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[PolymerWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or PolymerWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        polymer_a: str,
        polymer_b: str,
        conditions: Optional[PolymerConditions] = None,
    ) -> PolymerInterfaceScore:
        """
        Validate an interface between two polymers by name.

        Args:
            polymer_a: Name/abbreviation of first polymer
            polymer_b: Name/abbreviation of second polymer
            conditions: Optional operating conditions

        Returns:
            PolymerInterfaceScore with component breakdown

        Raises:
            ValueError: If polymer name not found
        """
        mat_a = get_polymer(polymer_a)
        mat_b = get_polymer(polymer_b)
        if mat_a is None:
            raise ValueError(f"Unknown polymer: '{polymer_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown polymer: '{polymer_b}'")

        return self.validate_materials(mat_a, mat_b, conditions)

    def validate_materials(
        self,
        material_a: PolymerMaterial,
        material_b: PolymerMaterial,
        conditions: Optional[PolymerConditions] = None,
    ) -> PolymerInterfaceScore:
        """
        Validate an interface between two PolymerMaterial objects.

        Args:
            material_a: First polymer
            material_b: Second polymer
            conditions: Optional operating conditions

        Returns:
            PolymerInterfaceScore with full breakdown
        """
        conditions = conditions or PolymerConditions()

        # Run all five scorers
        s_sol = score_solubility_compatibility(material_a, material_b)
        s_therm = score_thermal_compatibility(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_chem = score_chemical_resistance(material_a, material_b)
        s_aging = score_aging_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'solubility': s_sol.score,
            'thermal': s_therm.score,
            'mechanical': s_mech.score,
            'chemical_resistance': s_chem.score,
            'aging': s_aging.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Weighted composite
        total = (
            self.weights.solubility * scores['solubility'] +
            self.weights.thermal * scores['thermal'] +
            self.weights.mechanical * scores['mechanical'] +
            self.weights.chemical_resistance * scores['chemical_resistance'] +
            self.weights.aging * scores['aging']
        )

        # Collect details
        all_details = {
            'solubility_details': s_sol.details,
            'thermal_details': s_therm.details,
            'mechanical_details': s_mech.details,
            'chemical_details': s_chem.details,
            'aging_details': s_aging.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'humidity_pct': conditions.humidity_pct,
                'uv_exposure': conditions.uv_exposure,
                'chemical_environment': conditions.chemical_environment,
            },
            'polymer_a': material_a.abbreviation,
            'polymer_b': material_b.abbreviation,
        }

        # Veto check: High Flory-Huggins χ indicates immiscibility (phase separation)
        # Critical χ ≈ 0.04 for many polymer pairs (Krause 1972, Nishi & Wang 1975)
        # Current implementation uses chain-length critical chi, not a fixed cutoff.
        is_viable = total >= self.viability_threshold
        fh = assess_flory_huggins(material_a, material_b)
        all_details['flory_huggins'] = fh.to_dict()

        if fh.miscible is False:
            is_viable = False
            total = min(total, 0.35)
            all_details['veto'] = (
                f"Immiscible blend (chi={fh.chi:.4g} > chi_c={fh.critical_chi:.4g}): "
                "Flory-Huggins phase separation expected"
            )
        elif fh.miscible is None and fh.chi is not None and fh.chi > 0.15:
            is_viable = False
            total = min(total, 0.45)
            all_details['veto'] = (
                f"Immiscible blend (chi={fh.chi:.3f}; missing chain length): "
                "phase separation expected"
            )
        elif fh.chi is None and scores['solubility'] < 0.30:
            # No tabulated chi: fall back to the Hansen solubility score. A very
            # low solubility score = strongly mismatched cohesive energy density
            # -> immiscibility. Same 0.30 threshold blend_analyzer already uses.
            # NOTE: this only catches clearly mismatched pairs; it cannot detect
            # crystallinity/entropy-driven immiscibility of solubility-matched
            # polyolefins (e.g. HDPE/PP), which needs curated chi data.
            is_viable = False
            total = min(total, 0.45)
            all_details['veto'] = (
                f"Immiscible (no tabulated chi; solubility={scores['solubility']:.2f} < 0.30)"
            )

        return PolymerInterfaceScore(
            total=total,
            solubility_compatibility=scores['solubility'],
            thermal_compatibility=scores['thermal'],
            mechanical_compatibility=scores['mechanical'],
            chemical_resistance=scores['chemical_resistance'],
            aging_penalty=scores['aging'],
            viable=is_viable,
            details=all_details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: PolymerMaterial,
        material_b: PolymerMaterial,
        conditions: PolymerConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # High temperature effects
        if conditions.temperature_C > 80:
            # Elevated temperature accelerates aging
            temp_factor = max(0.5, 1.0 - (conditions.temperature_C - 80) / 300)
            modified['aging'] *= temp_factor
            # May soften thermoplastics (worse mechanical performance)
            modified['mechanical'] *= max(0.7, 1.0 - (conditions.temperature_C - 80) / 500)

        # Low temperature effects
        if conditions.temperature_C < -20:
            # Embrittlement below Tg
            modified['mechanical'] *= max(0.5, 1.0 + conditions.temperature_C / 100)

        # UV exposure
        if conditions.uv_exposure:
            from polymer_bridge.material_properties import PolymerFailureMode
            uv_sensitive = sum(
                1 for m in [material_a, material_b]
                if PolymerFailureMode.UV_DEGRADATION in m.failure_modes
            )
            if uv_sensitive > 0:
                modified['aging'] *= max(0.4, 1.0 - uv_sensitive * 0.25)

        # Wet/aqueous environment
        if conditions.chemical_environment == "water":
            modified['chemical_resistance'] *= 0.8
            # Extra penalty for hygroscopic materials
            for mat in [material_a, material_b]:
                if mat.water_absorption_pct and mat.water_absorption_pct > 5.0:
                    modified['chemical_resistance'] *= 0.7

        # High humidity
        if conditions.humidity_pct > 80:
            for mat in [material_a, material_b]:
                if mat.water_absorption_pct and mat.water_absorption_pct > 2.0:
                    modified['aging'] *= 0.85

        return modified

    def validate_all_interfaces(
        self,
        polymers: List[str],
        conditions: Optional[PolymerConditions] = None,
    ) -> Dict[Tuple[str, str], PolymerInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of polymers.

        Args:
            polymers: List of polymer names
            conditions: Operating conditions

        Returns:
            Dict mapping (poly_a, poly_b) to PolymerInterfaceScore
        """
        results = {}
        for i in range(len(polymers)):
            for j in range(i + 1, len(polymers)):
                key = (polymers[i], polymers[j])
                try:
                    results[key] = self.validate(polymers[i], polymers[j], conditions)
                except ValueError:
                    pass
        return results


def validate_interface(
    polymer_a: str,
    polymer_b: str,
    conditions: Optional[PolymerConditions] = None,
) -> PolymerInterfaceScore:
    """Convenience function for quick interface validation."""
    validator = PolymerInterfaceValidator()
    return validator.validate(polymer_a, polymer_b, conditions)


if __name__ == "__main__":
    print("=" * 70)
    print("Polymer Interface Validator - Demo")
    print("=" * 70)
    print()

    validator = PolymerInterfaceValidator()

    # Good pairing
    print("--- PVDF + PMMA (miscible blend) ---")
    result = validator.validate('PVDF', 'PMMA')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Solubility:   {result.solubility_compatibility:.3f}")
    print(f"  Thermal:      {result.thermal_compatibility:.3f}")
    print(f"  Mechanical:   {result.mechanical_compatibility:.3f}")
    print(f"  Chem resist:  {result.chemical_resistance:.3f}")
    print(f"  Aging:        {result.aging_penalty:.3f}")
    print()

    # Bad pairing
    print("--- HDPE + PA6 (immiscible) ---")
    result = validator.validate('HDPE', 'PA6')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Solubility:   {result.solubility_compatibility:.3f}")
    print(f"  Thermal:      {result.thermal_compatibility:.3f}")
    print(f"  Mechanical:   {result.mechanical_compatibility:.3f}")
    print(f"  Chem resist:  {result.chemical_resistance:.3f}")
    print(f"  Aging:        {result.aging_penalty:.3f}")
