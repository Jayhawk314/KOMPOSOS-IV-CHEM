# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Find exactly 22-atom MOF linkers."""
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

# Build candidates by systematically adding groups
candidates = [
    # Terphenyl + functional groups
    ('Terphenyl-COOH-OH', 'O=C(O)c1ccc(-c2ccc(-c3ccccc3)cc2)c(O)c1'),
    # Pyrene + groups
    ('Pyrene-diCOOH', 'O=C(O)c1cc(C(=O)O)c2ccc3cccc4ccc(c1)c2c34'),
    # Anthracene + extensions
    ('Anthracene-BDC-Me', 'O=C(O)c1cc(C)c2c(c1)cc1c(C)cc(C(=O)O)cc1c2'),
    # Naphthalene + more groups
    ('Naphthalene-triCOOH', 'O=C(O)c1cc(C(=O)O)c2cc(C(=O)O)ccc2c1'),
    # Stilbene + OH
    ('Stilbene-BDC-diOH', 'O=C(O)c1cc(O)c(/C=C/c2cc(O)c(C(=O)O)cc2)cc1'),
    # Biphenyl + dimethyl + diCOOH
    ('Biphenyl-Me2-BDC', 'O=C(O)c1cc(C)c(-c2cc(C)c(C(=O)O)cc2)cc1'),
    # Try exact calculation: C18 + 4O = 22
    ('Quaterphenyl', 'c1ccc(-c2ccc(-c3ccc(-c4ccccc4)cc3)cc2)cc1'),  # 4 benzene rings
    # Fluorene + COOH
    ('Fluorene-diCOOH', 'O=C(O)c1ccc2c(c1)Cc1cc(C(=O)O)ccc1-2'),
    # Bipyridine extended
    ('Bipyridine-BDC', 'O=C(O)c1ccc(-c2ccncc2)nc1'),
    # Exact 22: need C + N + O mix
    ('Extended-BDC-1', 'O=C(O)c1ccc2c(c1)sc1cc(C(=O)O)ccc12'),  # thiophene bridge
]

print('Finding 22-atom linkers:')
print('=' * 60)
valid_22 = []

for name, smiles in candidates:
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        heavy = mol.GetNumHeavyAtoms()
        formula = rdMolDescriptors.CalcMolFormula(mol)
        mw = Descriptors.MolWt(mol)

        marker = ' <<< MATCH!' if heavy == 22 else f' ({heavy})'
        print(f'{name}: {formula} - {heavy} atoms{marker}')

        if heavy == 22:
            logp = Descriptors.MolLogP(mol)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            print(f'  SMILES: {smiles}')
            print(f'  MW={mw:.1f}, logP={logp:.2f}, HBD={hbd}, HBA={hba}')
            valid_22.append((name, smiles, formula))
    else:
        print(f'{name}: INVALID SMILES')

print(f'\n{"="*60}')
print(f'Found {len(valid_22)} exact 22-atom linkers')

if valid_22:
    print('\nValid linkers:')
    for name, smiles, formula in valid_22:
        print(f'  {name}: {smiles}')
else:
    print('\nNeed to build more candidates. Try:')
    print('  - Quaterphenyl variations')
    print('  - Pyrene + substituents')
    print('  - Dendritic linkers')
