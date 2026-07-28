# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from mof_bridge.linker_generator import LinkerGenerator
from mof_bridge.mp_mof_loader import MOFLinkerCache, MOFLinker
import sqlite3

print('Loading linkers from database...')
conn = sqlite3.connect('data/cache/mof_linkers/mof_linkers_22.db')
cursor = conn.cursor()
cursor.execute('SELECT smiles, formula, heavy_atom_count, mp_source_id, molecular_weight, logp, hbond_donors, hbond_acceptors, rotatable_bonds, aromatic_rings FROM linkers')

known_linkers = []
for row in cursor:
    linker = MOFLinker(
        linker_id='test',
        smiles=row[0],
        formula=row[1],
        heavy_atom_count=row[2],
        mp_source_id=row[3],
        molecular_weight=row[4],
        logp=row[5],
        hbond_donors=row[6],
        hbond_acceptors=row[7],
        rotatable_bonds=row[8],
        aromatic_rings=row[9],
        atomic_descriptors=None,
    )
    known_linkers.append(linker)

conn.close()
print(f'Loaded {len(known_linkers)} known linkers')

print('\nGenerating NEW 22-atom linkers...')
gen = LinkerGenerator(known_linkers)
candidates = gen.generate_candidates(n_candidates=20, application_context='breath_VOC_sensing')

print(f'\n✅ Generated {len(candidates)} NEW candidates!')
print('\nFirst 5:')
for i, c in enumerate(candidates[:5], 1):
    print(f'{i}. {c}')

# Check novelty
known_smiles = {l.smiles for l in known_linkers}
novel_count = sum(1 for c in candidates if c not in known_smiles)
print(f'\n📊 Novel (not in known set): {novel_count}/{len(candidates)}')
