"""
KOMPOSOS Integration Layer for MOF Bridge
=============================================

Wires MOF materials into the KOMPOSOS-III categorical infrastructure:

- Objects = MOFs
- Morphisms = Application suitability scores
- Category = MOFMaterials

Mirrors ceramic_bridge/integration.py pattern.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from data.store import StoredObject, StoredMorphism
    STORE_AVAILABLE = True
except ImportError:
    STORE_AVAILABLE = False
    StoredObject = None
    StoredMorphism = None

try:
    from categorical.category import Category, Object, Morphism
    CATEGORY_AVAILABLE = True
except ImportError:
    CATEGORY_AVAILABLE = False

from mof_bridge.material_properties import (
    MOF, ALL_MOFS, get_mof,
)
from mof_bridge.interface_validator import (
    MOFInterfaceValidator, MOFInterfaceScore, MOFConditions,
)


# =============================================================================
# MOF -> StoredObject
# =============================================================================

def mof_to_stored_object(mof: MOF) -> 'StoredObject':
    """Convert a MOF to a StoredObject for the categorical store."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'name': mof.name,
        'metal_node': mof.metal_node,
        'linker': mof.linker,
        'topology': mof.topology.value,
        'formula': mof.formula,
        'bet_surface_area_m2g': mof.bet_surface_area_m2g,
        'pore_volume_cm3g': mof.pore_volume_cm3g,
        'pore_diameter_angstrom': mof.pore_diameter_angstrom,
        'thermal_stability_C': mof.thermal_stability_C,
        'water_stability': mof.water_stability,
        'primary_application': mof.primary_application.value,
        'doi': mof.doi,
        'domain': 'mof',
    }

    return StoredObject(
        name=mof.name,
        type_name=f"mof_{mof.topology.value}",
        metadata=metadata,
        provenance='mof_bridge.material_properties',
    )


# =============================================================================
# MOFMorphism
# =============================================================================

@dataclass
class MOFMorphism:
    """A MOF application suitability as a categorical morphism."""
    mof: MOF
    conditions: MOFConditions
    interface_score: MOFInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        app_name = (self.conditions.target_application.value
                    if self.conditions.target_application
                    else self.mof.primary_application.value)

        return StoredMorphism(
            name='mof_suitability',
            source_name=self.mof.name,
            target_name=f"application_{app_name}",
            metadata={
                'pore_accessibility': self.interface_score.pore_accessibility,
                'chemical_stability': self.interface_score.chemical_stability,
                'thermal_compatibility': self.interface_score.thermal_compatibility,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'application_suitability': self.interface_score.application_suitability,
                'suitable': self.interface_score.suitable,
                'domain': 'mof',
            },
            confidence=self.interface_score.total,
            provenance='mof_bridge.interface_validator',
        )


def create_mof_morphism(
    mof_name: str,
    conditions: Optional[MOFConditions] = None,
    validator: Optional[MOFInterfaceValidator] = None,
) -> MOFMorphism:
    """Create a MOFMorphism for a MOF under given conditions."""
    mof = get_mof(mof_name)
    if mof is None:
        raise ValueError(f"Unknown MOF: {mof_name}")

    conditions = conditions or MOFConditions()
    validator = validator or MOFInterfaceValidator()
    score = validator.validate_material(mof, conditions)

    return MOFMorphism(mof=mof, conditions=conditions, interface_score=score)


# =============================================================================
# Build MOF Category
# =============================================================================

def build_mof_category(
    mof_names: Optional[List[str]] = None,
    conditions: Optional[MOFConditions] = None,
) -> Optional['Category']:
    """
    Build a Category object from MOF materials.

    Objects = MOFs, Morphisms = suitable application pairings.

    Args:
        mof_names: List of MOF names (uses all if None)
        conditions: Operating conditions for scoring

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    mof_names = mof_names or list(ALL_MOFS.keys())
    conditions = conditions or MOFConditions()
    cat = Category(name="MOFMaterials")
    validator = MOFInterfaceValidator()

    for name in mof_names:
        mof = get_mof(name)
        if mof:
            obj = Object(
                name=mof.name,
                type_info={
                    'topology': mof.topology.value,
                    'metal_node': mof.metal_node,
                    'application': mof.primary_application.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for suitable MOFs
    for name in mof_names:
        mof = get_mof(name)
        if mof is None:
            continue

        try:
            score = validator.validate_material(mof, conditions)
            if score.suitable:
                src = cat.objects.get(mof.name)
                if src:
                    # Create application target node if needed
                    app_name = f"app_{mof.primary_application.value}"
                    if app_name not in cat.objects:
                        app_obj = Object(
                            name=app_name,
                            type_info={'type': 'application_target'},
                        )
                        cat.add_object(app_obj)

                    tgt = cat.objects.get(app_name)
                    if tgt:
                        mor = Morphism(
                            name=f"suitable_{mof.name}_{mof.primary_application.value}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'mof_application_suitability',
                            },
                        )
                        cat.add_morphism(mor)
        except Exception:
            pass

    return cat
