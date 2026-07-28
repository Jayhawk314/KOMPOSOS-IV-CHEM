# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Atomic Descriptor Extraction for MOF Linkers
==============================================

Computes atom-centered descriptors for KOMPOSOS verdict reasoning.

Uses RDKit to extract:
- Atomic properties (element, charge, hybridization)
- Electronic properties (electronegativity, partial charge)
- Structural properties (bonding, rings, conjugation)

Pattern: Similar to molecular_bridge/molecule_properties.py but per-atom
instead of per-molecule.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


# Pauling electronegativity scale (for elements commonly found in MOF linkers)
ELECTRONEGATIVITY = {
    'H': 2.20, 'C': 2.55, 'N': 3.04, 'O': 3.44, 'F': 3.98,
    'P': 2.19, 'S': 2.58, 'Cl': 3.16, 'Br': 2.96, 'I': 2.66,
    'B': 2.04, 'Si': 1.90,
}


def compute_atomic_descriptors(smiles: str) -> Dict:
    """Compute atom-centered descriptors for a molecule.

    Args:
        smiles: Canonical SMILES string

    Returns:
        Dictionary with:
            'atoms': List of per-atom descriptors
            'bonds': List of per-bond descriptors
            'global': Global molecular properties

    Raises:
        ImportError: If RDKit not installed
        ValueError: If SMILES invalid
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors, rdPartialCharges
    except ImportError as e:
        raise ImportError(
            "RDKit required for atomic descriptors. "
            "Install: pip install rdkit"
        ) from e

    # Parse SMILES
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    # Compute Gasteiger partial charges
    try:
        rdPartialCharges.ComputeGasteigerCharges(mol)
    except Exception:
        # If charge computation fails, continue with zeros
        pass

    # Extract atom descriptors
    atoms = []
    for atom in mol.GetAtoms():
        symbol = atom.GetSymbol()
        idx = atom.GetIdx()

        # Get partial charge (Gasteiger)
        try:
            partial_charge = float(atom.GetProp('_GasteigerCharge'))
            if not (-10 < partial_charge < 10):  # Sanity check
                partial_charge = 0.0
        except Exception:
            partial_charge = 0.0

        # Get hybridization
        hyb = atom.GetHybridization()
        hyb_str = str(hyb).split('.')[-1] if hyb else 'UNKNOWN'

        # Get neighbors
        neighbors = [n.GetIdx() for n in atom.GetNeighbors()]

        atom_desc = {
            'index': idx,
            'element': symbol,
            'atomic_number': atom.GetAtomicNum(),
            'formal_charge': atom.GetFormalCharge(),
            'hybridization': hyb_str,
            'aromatic': atom.GetIsAromatic(),
            'num_bonds': atom.GetTotalDegree(),
            'neighbors': neighbors,
            'electronegativity': ELECTRONEGATIVITY.get(symbol, 2.0),
            'partial_charge': round(partial_charge, 3),
            'in_ring': atom.IsInRing(),
            'conjugated': atom.GetIsAromatic(),  # Simplified: aromatic = conjugated
            'num_h': atom.GetTotalNumHs(),
        }
        atoms.append(atom_desc)

    # Extract bond descriptors
    bonds = []
    for bond in mol.GetBonds():
        bond_type = bond.GetBondType()
        bond_type_str = str(bond_type).split('.')[-1]

        # Map bond type to bond order
        bond_order_map = {
            'SINGLE': 1.0,
            'DOUBLE': 2.0,
            'TRIPLE': 3.0,
            'AROMATIC': 1.5,
        }
        bond_order = bond_order_map.get(bond_type_str, 1.0)

        bond_desc = {
            'atom_i': bond.GetBeginAtomIdx(),
            'atom_j': bond.GetEndAtomIdx(),
            'bond_type': bond_type_str,
            'bond_order': bond_order,
            'conjugated': bond.GetIsConjugated(),
            'in_ring': bond.IsInRing(),
        }
        bonds.append(bond_desc)

    # Global molecular properties
    ring_info = mol.GetRingInfo()
    num_aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)

    # Conjugation length (simplified: number of conjugated bonds)
    conjugated_bonds = [b for b in bonds if b['conjugated']]
    conjugation_length = len(conjugated_bonds)

    # Heteroatoms (non-C, non-H)
    heteroatoms = [a for a in atoms if a['element'] not in ('C', 'H')]

    # Max ring size
    ring_sizes = [len(ring) for ring in ring_info.AtomRings()]
    max_ring_size = max(ring_sizes) if ring_sizes else 0

    global_desc = {
        'num_aromatic_rings': num_aromatic_rings,
        'conjugation_length': conjugation_length,
        'has_heteroatom': len(heteroatoms) > 0,
        'max_ring_size': max_ring_size,
        'num_rings': ring_info.NumRings(),
    }

    return {
        'atoms': atoms,
        'bonds': bonds,
        'global': global_desc,
    }


def count_heavy_atoms(smiles: str) -> int:
    """Count heavy (non-hydrogen) atoms in a molecule.

    Args:
        smiles: SMILES string

    Returns:
        Number of heavy atoms

    Raises:
        ImportError: If RDKit not installed
        ValueError: If SMILES invalid
    """
    try:
        from rdkit import Chem
    except ImportError as e:
        raise ImportError("RDKit required. Install: pip install rdkit") from e

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    return mol.GetNumHeavyAtoms()


def get_molecular_properties(smiles: str) -> Dict:
    """Get basic molecular properties (no RDKit descriptors needed).

    Args:
        smiles: SMILES string

    Returns:
        Dictionary with MW, logP, HBD, HBA, rotatable bonds, aromatic rings

    Raises:
        ImportError: If RDKit not installed
        ValueError: If SMILES invalid
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors, Crippen
    except ImportError as e:
        raise ImportError("RDKit required. Install: pip install rdkit") from e

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    return {
        'molecular_weight': Descriptors.MolWt(mol),
        'logp': Crippen.MolLogP(mol),
        'hbond_donors': rdMolDescriptors.CalcNumHBD(mol),
        'hbond_acceptors': rdMolDescriptors.CalcNumHBA(mol),
        'rotatable_bonds': rdMolDescriptors.CalcNumRotatableBonds(mol),
        'aromatic_rings': rdMolDescriptors.CalcNumAromaticRings(mol),
    }


if __name__ == "__main__":
    # Demo usage
    test_smiles = "c1ccc(-c2ccccc2)cc1"  # Biphenyl (simpler example)

    print("Testing atomic descriptor extraction...")
    print(f"SMILES: {test_smiles}")

    try:
        descriptors = compute_atomic_descriptors(test_smiles)

        print(f"\nAtoms: {len(descriptors['atoms'])}")
        for atom in descriptors['atoms'][:5]:
            print(f"  Atom {atom['index']}: {atom['element']} (hybrid: {atom['hybridization']}, "
                  f"charge: {atom['partial_charge']}, aromatic: {atom['aromatic']})")

        print(f"\nBonds: {len(descriptors['bonds'])}")
        for bond in descriptors['bonds'][:5]:
            print(f"  Bond {bond['atom_i']}-{bond['atom_j']}: {bond['bond_type']} "
                  f"(order: {bond['bond_order']}, conjugated: {bond['conjugated']})")

        print(f"\nGlobal properties:")
        for key, value in descriptors['global'].items():
            print(f"  {key}: {value}")

        print(f"\nHeavy atom count: {count_heavy_atoms(test_smiles)}")

        mol_props = get_molecular_properties(test_smiles)
        print(f"\nMolecular properties:")
        for key, value in mol_props.items():
            print(f"  {key}: {value}")

    except ImportError as e:
        print(f"Error: {e}")
        print("Install RDKit: pip install rdkit")
