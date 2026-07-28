#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Generate MMLKG GraphML using mizgra."""

import sys
import os

# Set encoding early
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from mizgra import Mizgra

esx_dir = 'data_sources/mmlkg/esx_files-main/esx_mml'
mml_lar = 'data_sources/mmlkg/esx_files-main/mml.lar'
output_file = 'data_sources/mmlkg/mmlkg.graphml'

print(f"Loading ESX files from {esx_dir}...")
print(f"Loading mml.lar from {mml_lar}...")

try:
    mizgra = Mizgra(esx_dir, mml_lar)
    print("Generating GraphML...")
    
    graphml = mizgra.to_graphml()
    
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(graphml)
    
    print(f"Done! Generated {output_file}")
    print(f"File size: {os.path.getsize(output_file) / 1e6:.1f} MB")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
