# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from mof_bridge.mp_mof_loader import MOFLinkerCache

cache = MOFLinkerCache()
print(f"Cache available: {cache.is_available()}")

count = cache.entry_count()
print(f"Linkers in cache: {count}")

if count > 0:
    linkers = cache.load_linkers()
    print(f"Successfully loaded {len(linkers)} linkers\n")

    for i, l in enumerate(linkers):
        print(f"{i+1}. {l.smiles[:60]:60s} | {l.heavy_atom_count} atoms | {l.mp_source_id}")
else:
    print("No linkers in cache")
