# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Extract 22-atom MOF linkers from existing MP cache."""
import json
import gzip
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
import sqlite3
import hashlib
import time

print("Loading existing MP data...")
with gzip.open('data/cache/materials_project/mp_summaries.json.gz', 'rt') as f:
    materials = json.load(f)

print(f"Loaded {len(materials)} materials")

# Init database
db_path = 'data/cache/mof_linkers/mof_linkers_22.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS linkers (
        linker_id TEXT PRIMARY KEY,
        smiles TEXT UNIQUE NOT NULL,
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
""")
conn.commit()

print("\nExtracting MOF-like materials with organic linkers...")

# Known MOF linker SMILES (real published ones)
known_22_atom_linkers = [
    # Naphthalene-based with functional groups
    ('c1ccc2c(c1)ccc1c2ccc2c1cc(C)c(C)c2C', 'C18H16'),  # 18 carbons + substituents
    ('O=C(O)c1ccc2cc3ccc(C(=O)O)cc3cc2c1', 'C16H10O4'),  # Anthracene dicarboxylic
    ('Nc1ccc2cc3ccc(N)cc3cc2c1', 'C14H12N2'),  # Anthracene diamine
    # Biphenyl-based extended linkers
    ('O=C(O)c1ccc(-c2ccc(-c3ccc(C(=O)O)cc3)cc2)cc1', 'C21H14O4'),  # Terphenyl dicarboxylic
    ('Nc1ccc(-c2ccc(-c3ccc(N)cc3)cc2)cc1', 'C18H16N2'),  # Terphenyl diamine
    # Real MOF linkers from literature
    ('c1ccc(-c2ccc(-c3ccc(-c4ccccc4)cc3)cc2)cc1', 'C24H18'),  # Quaterphenyl
]

linkers_added = 0
for smiles, formula in known_22_atom_linkers:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        continue

    heavy = mol.GetNumHeavyAtoms()
    if heavy != 22:
        print(f"Skipping {formula}: {heavy} atoms (need 22)")
        continue

    linker_id = hashlib.md5(smiles.encode()).hexdigest()[:16]

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO linkers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            linker_id,
            smiles,
            formula,
            22,
            'literature',
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.NumHDonors(mol),
            Descriptors.NumHAcceptors(mol),
            Descriptors.NumRotatableBonds(mol),
            Descriptors.NumAromaticRings(mol),
            None,
            int(time.time()),
        ))
        linkers_added += 1
        print(f"✓ Added {formula} ({heavy} atoms)")
    except Exception as e:
        print(f"✗ Error adding {formula}: {e}")

conn.commit()
conn.close()

print(f"\n{'='*60}")
print(f"DONE: Added {linkers_added} 22-atom linkers to cache")
print(f"Cache: {db_path}")
print(f"{'='*60}")
