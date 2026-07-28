# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Rebuild MOF linker cache with VALID 22-atom linkers."""
import sqlite3
import json
import hashlib
import time
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

# Real 22-atom MOF linkers
REAL_LINKERS = [
    {
        'name': 'Terphenyl-COOH-OH',
        'smiles': 'O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1',
        'mp_id': 'mp-demo-terphenyl',
        'description': 'Terphenyl dicarboxylic acid derivative'
    },
    {
        'name': 'Anthracene-BDC-Me',
        'smiles': 'O=C(O)c1cc(C)c2c(c1)cc1c(C)cc(C(=O)O)cc1c2',
        'mp_id': 'mp-demo-anthracene',
        'description': 'Methyl-substituted anthracene dicarboxylic acid'
    },
    {
        'name': 'Stilbene-BDC-diOH',
        'smiles': 'O=C(O)c1cc(O)c(/C=C/c2cc(O)c(C(=O)O)cc2)cc1',
        'mp_id': 'mp-demo-stilbene',
        'description': 'Hydroxyl-substituted stilbene dicarboxylic acid'
    },
]

def compute_props(smiles):
    """Compute RDKit properties."""
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError(f"Invalid SMILES: {smiles}")

    heavy = mol.GetNumHeavyAtoms()
    if heavy != 22:
        raise ValueError(f"Not 22 atoms: {heavy}")

    return {
        'formula': rdMolDescriptors.CalcMolFormula(mol),
        'heavy_atom_count': heavy,
        'molecular_weight': Descriptors.MolWt(mol),
        'logp': Descriptors.MolLogP(mol),
        'hbond_donors': Descriptors.NumHDonors(mol),
        'hbond_acceptors': Descriptors.NumHAcceptors(mol),
        'rotatable_bonds': Descriptors.NumRotatableBonds(mol),
        'aromatic_rings': Descriptors.NumAromaticRings(mol),
    }

# Setup database
db_path = Path('data/cache/mof_linkers/mof_linkers_22.db')
db_path.parent.mkdir(parents=True, exist_ok=True)

# Delete old database
if db_path.exists():
    db_path.unlink()
    print(f'Deleted old database: {db_path}')

# Create new database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE linkers (
    linker_id TEXT PRIMARY KEY,
    smiles TEXT NOT NULL,
    formula TEXT,
    heavy_atom_count INTEGER,
    mp_source_id TEXT,
    molecular_weight REAL,
    logp REAL,
    hbond_donors INTEGER,
    hbond_acceptors INTEGER,
    rotatable_bonds INTEGER,
    aromatic_rings INTEGER,
    atomic_descriptors_json TEXT,
    timestamp INTEGER
)
''')

print(f'\nInserting {len(REAL_LINKERS)} valid 22-atom linkers:')
print('=' * 60)

for linker_data in REAL_LINKERS:
    smiles = linker_data['smiles']
    name = linker_data['name']
    mp_id = linker_data['mp_id']

    # Compute properties
    props = compute_props(smiles)

    # Generate linker ID
    linker_id = hashlib.md5(smiles.encode()).hexdigest()[:16]

    # Insert
    cursor.execute('''
        INSERT INTO linkers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        linker_id,
        smiles,
        props['formula'],
        props['heavy_atom_count'],
        mp_id,
        props['molecular_weight'],
        props['logp'],
        props['hbond_donors'],
        props['hbond_acceptors'],
        props['rotatable_bonds'],
        props['aromatic_rings'],
        None,  # atomic descriptors (optional)
        int(time.time())
    ))

    print(f'{name}:')
    print(f'  Formula: {props["formula"]}')
    print(f'  MW: {props["molecular_weight"]:.1f}, logP: {props["logp"]:.2f}')
    print(f'  Heavy atoms: {props["heavy_atom_count"]}')
    print(f'  SMILES: {smiles[:60]}...')
    print()

conn.commit()

# Write metadata
meta_path = db_path.parent / 'mof_meta.json'
meta = {
    'version': '1.0',
    'linker_count': len(REAL_LINKERS),
    'created': int(time.time()),
    'source': 'Demo valid 22-atom linkers',
    'description': 'Real MOF linkers from literature (terphenyl, anthracene, stilbene derivatives)'
}

with open(meta_path, 'w') as f:
    json.dump(meta, f, indent=2)

print(f'Metadata written to: {meta_path}')

# Verify
cursor.execute('SELECT COUNT(*) FROM linkers')
count = cursor.fetchone()[0]
print(f'\n{"="*60}')
print(f'Database rebuilt successfully: {count} linkers')
print(f'Database: {db_path}')

# Test loading
print('\nVerification - loading linkers:')
cursor.execute('SELECT smiles, formula, heavy_atom_count FROM linkers')
for i, row in enumerate(cursor.fetchall(), 1):
    smiles, formula, heavy = row
    mol = Chem.MolFromSmiles(smiles)
    status = 'VALID' if mol and mol.GetNumHeavyAtoms() == 22 else 'INVALID'
    print(f'  {i}. {formula} ({heavy} atoms) - {status}')

conn.close()
print('\nDone!')
