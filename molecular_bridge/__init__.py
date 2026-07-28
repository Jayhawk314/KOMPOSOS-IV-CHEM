# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular Bridge
================

Molecular-level property database and interaction scoring for chemistry
and materials. This is the molecular-level counterpart to the material-level
bridges (battery_bridge, polymer_bridge, etc.).

Molecules are objects, reactions/interactions are morphisms.
"""

from molecular_bridge.molecule_properties import (
    MoleculeClass,
    Molecule,
    ALL_MOLECULES,
    ELECTROLYTE_SOLVENTS,
    SALT_ANIONS,
    POLYMER_MONOMERS,
    REAGENTS,
    COATINGS,
    GAS_MOLECULES,
    get_molecule,
    get_molecules_by_class,
    list_molecule_names,
)

__all__ = [
    'MoleculeClass',
    'Molecule',
    'ALL_MOLECULES',
    'ELECTROLYTE_SOLVENTS',
    'SALT_ANIONS',
    'POLYMER_MONOMERS',
    'REAGENTS',
    'COATINGS',
    'GAS_MOLECULES',
    'get_molecule',
    'get_molecules_by_class',
    'list_molecule_names',
]
