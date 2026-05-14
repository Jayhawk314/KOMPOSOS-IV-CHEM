"""
MOF Interface Validator
========================

Validates MOF suitability for a target application by combining all five
interaction scorers into a weighted composite MOFInterfaceScore.

Unlike other bridges that validate A-vs-B compatibility, the MOF bridge
validates a SINGLE MOF against operating conditions/requirements.

Usage:
    validator = MOFInterfaceValidator()
    result = validator.validate_mof('ZIF-8', target_molecule_diameter=3.4)
    print(f"Suitable: {result.suitable}, Score: {result.total:.2f}")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from mof_bridge.material_properties import MOF, MOFApplication, get_mof
from mof_bridge.interaction_scoring import (
    score_pore_accessibility,
    score_chemical_stability,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_application_suitability,
    ScorerResult,
)


@dataclass
class MOFConditions:
    """Operating conditions for MOF application screening."""
    target_molecule_diameter: Optional[float] = None  # Angstrom
    operating_temp_C: float = 25.0
    operating_pressure_bar: float = 1.0
    environment: str = "dry"  # "dry", "humid", "aqueous", "acidic", "basic"
    target_application: Optional[MOFApplication] = None
    requires_water_stable: bool = False
    requires_acid_stable: bool = False
    min_surface_area: Optional[float] = None  # m2/g
    min_pore_volume: Optional[float] = None  # cm3/g
    requires_regeneration: bool = False
    regeneration_temp_C: Optional[float] = None


@dataclass
class MOFInterfaceScore:
    """Composite MOF suitability score with component breakdown."""
    total: float                       # Weighted composite (0-1)
    pore_accessibility: float          # Component score
    chemical_stability: float          # Component score
    thermal_compatibility: float       # Component score
    mechanical_compatibility: float    # Component score
    application_suitability: float     # Component score
    suitable: bool                     # Above threshold?
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'pore_accessibility': round(self.pore_accessibility, 4),
            'chemical_stability': round(self.chemical_stability, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'application_suitability': round(self.application_suitability, 4),
            'suitable': self.suitable,
        }


@dataclass
class MOFWeights:
    """Configurable weights for the five scoring components."""
    pore: float = 0.25
    chemical: float = 0.20
    thermal: float = 0.20
    mechanical: float = 0.15
    application: float = 0.20

    def validate(self):
        total = (self.pore + self.chemical + self.thermal +
                 self.mechanical + self.application)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'MOFWeights':
        return cls()

    @classmethod
    def separation_focus(cls) -> 'MOFWeights':
        """Weights for gas separation applications."""
        return cls(pore=0.35, chemical=0.20, thermal=0.15, mechanical=0.10, application=0.20)

    @classmethod
    def storage_focus(cls) -> 'MOFWeights':
        """Weights for gas storage applications."""
        return cls(pore=0.30, chemical=0.15, thermal=0.15, mechanical=0.20, application=0.20)

    @classmethod
    def catalysis_focus(cls) -> 'MOFWeights':
        """Weights for catalysis applications."""
        return cls(pore=0.20, chemical=0.25, thermal=0.25, mechanical=0.10, application=0.20)

    @classmethod
    def water_focus(cls) -> 'MOFWeights':
        """Weights for water harvesting / aqueous applications."""
        return cls(pore=0.15, chemical=0.35, thermal=0.15, mechanical=0.10, application=0.25)


class MOFInterfaceValidator:
    """
    Validates MOF suitability for target applications.

    Usage:
        validator = MOFInterfaceValidator()
        result = validator.validate_mof('ZIF-8', target_molecule_diameter=3.4)
        print(f"Suitable: {result.suitable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[MOFWeights] = None,
        suitability_threshold: float = 0.50,
    ):
        self.weights = weights or MOFWeights.default()
        self.weights.validate()
        self.suitability_threshold = suitability_threshold

    def validate_mof(
        self,
        mof_name: str,
        conditions: Optional[MOFConditions] = None,
        **kwargs,
    ) -> MOFInterfaceScore:
        """
        Validate a MOF by name for suitability.

        Args:
            mof_name: Name of MOF (e.g. 'ZIF-8')
            conditions: Operating conditions (or pass kwargs)
            **kwargs: Shortcut for conditions fields

        Returns:
            MOFInterfaceScore

        Raises:
            ValueError: If MOF name not found
        """
        mof = get_mof(mof_name)
        if mof is None:
            raise ValueError(f"Unknown MOF: '{mof_name}'")

        if conditions is None:
            conditions = MOFConditions(**kwargs)

        return self.validate_material(mof, conditions)

    def validate_material(
        self,
        mof: MOF,
        conditions: Optional[MOFConditions] = None,
    ) -> MOFInterfaceScore:
        """
        Validate a MOF object for suitability.

        Args:
            mof: MOF material
            conditions: Operating conditions

        Returns:
            MOFInterfaceScore with full breakdown
        """
        conditions = conditions or MOFConditions()

        # Run all five scorers
        s_pore = score_pore_accessibility(
            mof,
            target_molecule_diameter=conditions.target_molecule_diameter,
            min_surface_area=conditions.min_surface_area,
            min_pore_volume=conditions.min_pore_volume,
        )
        s_chem = score_chemical_stability(
            mof,
            requires_water_stable=conditions.requires_water_stable,
            requires_acid_stable=conditions.requires_acid_stable,
            environment=conditions.environment,
        )
        s_therm = score_thermal_compatibility(
            mof,
            operating_temp_C=conditions.operating_temp_C,
            requires_regeneration=conditions.requires_regeneration,
            regeneration_temp_C=conditions.regeneration_temp_C,
        )
        s_mech = score_mechanical_compatibility(
            mof,
            operating_pressure_bar=conditions.operating_pressure_bar,
        )
        s_app = score_application_suitability(
            mof,
            target_application=conditions.target_application,
        )

        # Weighted composite
        total = (
            self.weights.pore * s_pore.score +
            self.weights.chemical * s_chem.score +
            self.weights.thermal * s_therm.score +
            self.weights.mechanical * s_mech.score +
            self.weights.application * s_app.score
        )

        details = {
            'mof_name': mof.name,
            'pore_details': s_pore.details,
            'chemical_details': s_chem.details,
            'thermal_details': s_therm.details,
            'mechanical_details': s_mech.details,
            'application_details': s_app.details,
            'conditions': {
                'operating_temp_C': conditions.operating_temp_C,
                'operating_pressure_bar': conditions.operating_pressure_bar,
                'environment': conditions.environment,
            },
        }

        return MOFInterfaceScore(
            total=total,
            pore_accessibility=s_pore.score,
            chemical_stability=s_chem.score,
            thermal_compatibility=s_therm.score,
            mechanical_compatibility=s_mech.score,
            application_suitability=s_app.score,
            suitable=total >= self.suitability_threshold,
            details=details,
        )

    def screen_all(
        self,
        conditions: Optional[MOFConditions] = None,
    ) -> List[Tuple[str, MOFInterfaceScore]]:
        """
        Screen all MOFs against conditions, sorted by score descending.

        Args:
            conditions: Operating conditions

        Returns:
            List of (mof_name, score) tuples sorted by total score
        """
        from mof_bridge.material_properties import ALL_MOFS

        results = []
        for name, mof in ALL_MOFS.items():
            score = self.validate_material(mof, conditions)
            results.append((name, score))

        results.sort(key=lambda x: x[1].total, reverse=True)
        return results


def validate_mof(
    mof_name: str,
    conditions: Optional[MOFConditions] = None,
    **kwargs,
) -> MOFInterfaceScore:
    """Convenience function for quick MOF validation."""
    validator = MOFInterfaceValidator()
    return validator.validate_mof(mof_name, conditions, **kwargs)
