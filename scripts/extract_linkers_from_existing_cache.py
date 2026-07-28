#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Extract 22-atom linkers from EXISTING MP cache (no API key needed)."""

import sys
from pathlib import Path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import sqlite3
import json
import time
from composition_engine.mp_loader import MPCache
from mof_bridge.mp_mof_loader import MOFLinkerCache

print("="*70)
print("Extracting 22-atom linkers from existing MP cache")
print("="*70)

# Load existing MP cache
print("\n1. Loading existing MP cache...")
mp_cache = MPCache()
if not mp_cache.is_available():
    print("ERROR: MP cache not available. Run download_mp_data.py first.")
    sys.exit(1)

entries = mp_cache.load_entries()
print(f"   Loaded {len(entries):,} MP entries")

# Initialize MOF linker cache
print("\n2. Initializing MOF linker cache...")
mof_cache = MOFLinkerCache()
mof_cache._init_database()

# Try to load RDKit
print("\n3. Checking RDKit availability...")
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    print("   RDKit available")
except ImportError:
    print("   ERROR: RDKit not installed. Install with: pip install rdkit")
    print("   Falling back to formula-based extraction (limited)")
    Chem = None

# Extract linkers
print("\n4. Extracting linkers with exactly 22 heavy atoms...")
print("   (This will take 5-10 minutes for 103k entries)")

linkers_found = 0
start_time = time.time()

for i, entry in enumerate(entries):
    if i % 5000 == 0 and i > 0:
        elapsed = time.time() - start_time
        rate = i / elapsed
        remaining = (len(entries) - i) / rate / 60
        print(f"   Progress: {i:,}/{len(entries):,} ({100*i/len(entries):.1f}%) | "
              f"{linkers_found} linkers | ETA: {remaining:.1f} min")

    # Strategy: Check if composition has C, H, O, N (organic linker indicators)
    # and count heavy atoms
    comp = entry.composition

    # Must contain carbon (organic)
    if "C" not in comp:
        continue

    # Count heavy atoms (all except H)
    heavy_atoms = sum(
        int(count) for elem, count in comp.items()
        if elem != "H"
    )

    # Must be exactly 22 heavy atoms
    if heavy_atoms != 22:
        continue

    # Generate approximate SMILES (if RDKit available, use structure; otherwise use formula)
    if Chem and hasattr(entry, 'structure') and entry.structure:
        # TODO: Extract actual SMILES from structure
        # For now, just use formula as placeholder
        smiles = entry.formula.replace(" ", "")
    else:
        # Fallback: use formula
        smiles = entry.formula.replace(" ", "")

    # Create linker entry
    linker_id = f"mp_{entry.mp_id}_{heavy_atoms}"

    # Compute properties
    if Chem:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            mw = Descriptors.MolWt(mol)
            logp = Descriptors.MolLogP(mol)
            hbd = rdMolDescriptors.CalcNumHBD(mol)
            hba = rdMolDescriptors.CalcNumHBA(mol)
            rotatable = rdMolDescriptors.CalcNumRotatableBonds(mol)
            aromatic = rdMolDescriptors.CalcNumAromaticRings(mol)
        else:
            # Failed to parse, skip
            continue
    else:
        # Fallback estimates
        mw = sum(
            {"C": 12, "H": 1, "O": 16, "N": 14, "S": 32, "P": 31}.get(elem, 12) * count
            for elem, count in comp.items()
        )
        logp = 0.0
        hbd = comp.get("O", 0) + comp.get("N", 0)
        hba = comp.get("O", 0) + comp.get("N", 0)
        rotatable = 0
        aromatic = 0

    # Insert into database
    try:
        with sqlite3.connect(mof_cache.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO linkers (
                    linker_id, smiles, formula, heavy_atom_count,
                    mp_source_id, molecular_weight, logp,
                    hbond_donors, hbond_acceptors, rotatable_bonds,
                    aromatic_rings, atomic_descriptors_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                linker_id,
                smiles,
                entry.formula,
                heavy_atoms,
                entry.mp_id,
                mw,
                logp,
                hbd,
                hba,
                rotatable,
                aromatic,
                None,  # atomic_descriptors computed on demand
                int(time.time()),
            ))
            conn.commit()
        linkers_found += 1
    except Exception as e:
        print(f"   Error inserting linker {linker_id}: {e}")

elapsed = time.time() - start_time

# Write metadata
print("\n5. Writing metadata...")
meta = {
    'version': '1.0',
    'linker_count': linkers_found,
    'created': int(time.time()),
    'source': 'Extracted from existing MP cache (103k entries)',
    'extraction_time_sec': elapsed,
}
with open(mof_cache.meta_path, 'w') as f:
    json.dump(meta, f, indent=2)

print("\n" + "="*70)
print("COMPLETE")
print("="*70)
print(f"Linkers found: {linkers_found:,}")
print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
print(f"Cache: {mof_cache.db_path}")
print(f"Ready for use in MOF Designer")
print("="*70)
