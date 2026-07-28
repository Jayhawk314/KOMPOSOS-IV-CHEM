# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS Integration Layer for Molecular Bridge
=================================================

Wires molecules and their interactions into the KOMPOSOS-III categorical
infrastructure, following the pattern of battery_bridge/integration.py.

- Objects = Molecules
- Morphisms = Molecular interactions (compatible interfaces)
- Category = Graph of molecule compatibility
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

from molecular_bridge.molecule_properties import (
    Molecule, ALL_MOLECULES, get_molecule,
)
from molecular_bridge.interface_validator import (
    MolecularInterfaceValidator, MolecularInterfaceScore,
)


def molecule_to_stored_object(molecule: Molecule) -> 'StoredObject':
    """Convert a Molecule to a StoredObject for the categorical store."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available")

    return StoredObject(
        name=molecule.name,
        type_name=molecule.molecule_class.value,
        metadata={
            'formula': molecule.formula,
            'molecular_weight': molecule.molecular_weight,
            'pubchem_cid': molecule.pubchem_cid,
            'cas_number': molecule.cas_number,
            'functional_groups': molecule.functional_groups,
            'domain': 'molecular_chemistry',
        },
        provenance='molecular_bridge.molecule_properties',
    )


@dataclass
class MolecularMorphism:
    """A molecular interaction as a categorical morphism."""
    molecule_a: Molecule
    molecule_b: Molecule
    interface_score: MolecularInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='molecular_interaction',
            source_name=self.molecule_a.name,
            target_name=self.molecule_b.name,
            metadata={
                'electronic_compatibility': self.interface_score.electronic_compatibility,
                'thermodynamic_stability': self.interface_score.thermodynamic_stability,
                'steric_compatibility': self.interface_score.steric_compatibility,
                'solubility_compatibility': self.interface_score.solubility_compatibility,
                'reactivity_risk': self.interface_score.reactivity_risk,
                'viable': self.interface_score.viable,
                'domain': 'molecular_chemistry',
            },
            confidence=self.interface_score.total,
            provenance='molecular_bridge.interface_validator',
        )


def build_molecular_category(
    molecules: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from molecules and their interactions.

    Objects = molecules, Morphisms = viable interactions.
    """
    if not CATEGORY_AVAILABLE:
        return None

    molecules = molecules or list(ALL_MOLECULES.keys())
    cat = Category(name="MolecularInteractions")
    validator = MolecularInterfaceValidator()

    for name in molecules:
        mol = get_molecule(name)
        if mol:
            obj = Object(
                name=mol.name,
                type_info={
                    'formula': mol.formula,
                    'class': mol.molecule_class.value,
                    'mw': mol.molecular_weight,
                },
            )
            cat.add_object(obj)

    for i, name_a in enumerate(molecules):
        for name_b in molecules[i + 1:]:
            mol_a = get_molecule(name_a)
            mol_b = get_molecule(name_b)
            if mol_a is None or mol_b is None:
                continue

            try:
                score = validator.validate_molecules(mol_a, mol_b)
                if score.viable:
                    src = cat.objects.get(name_a)
                    tgt = cat.objects.get(name_b)
                    if src and tgt:
                        mor = Morphism(
                            name=f"interaction_{name_a}_{name_b}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'molecular_interaction',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat
