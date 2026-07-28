# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Debug pathway support method step by step."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader

# Load data
loader = BioDomainLoader()
category = loader.load_tier1("data/drugs/tier1.db")

source = "Gefitinib"
target = "NSCLC"

# Step by step
source_obj = category.get(source)
target_obj = category.get(target)

print(f"Source: {source} (type: {source_obj.type_name if source_obj else 'None'})")
print(f"Target: {target} (type: {target_obj.type_name if target_obj else 'None'})")
print()

# Find paths
paths = category.find_paths(source, target, max_length=3)
print(f"Paths found: {len(paths)}")
for i, path in enumerate(paths):
    print(f"  Path {i+1}: {' -> '.join(path)}")
    if len(path) == 3:
        intermediate = category.get(path[1])
        print(f"    Intermediate: {path[1]} (type: {intermediate.type_name if intermediate else 'None'})")
print()

# Check protein types
protein_types = {
    "Receptor", "Signaling", "Transcription", "TumorSuppressor",
    "Apoptosis", "Oncogene", "DNARepair", "CellCycle", "Regulator",
    "Splicing", "Epigenetic", "Metabolic", "Structural", "Chaperone"
}

valid_paths = []
for path in paths:
    if len(path) == 3:
        intermediate = category.get(path[1])
        if intermediate and intermediate.type_name in protein_types:
            valid_paths.append(path)
            print(f"VALID: {' -> '.join(path)}")

print(f"\nValid paths: {len(valid_paths)}")

# Get edge confidences
for path in valid_paths:
    edge1 = None
    edge2 = None
    for mor in category.morphisms():
        if mor.source == path[0] and mor.target == path[1]:
            edge1 = mor
        if mor.source == path[1] and mor.target == path[2]:
            edge2 = mor

    if edge1 and edge2:
        print(f"{path[0]} -> {path[1]}: {edge1.confidence:.3f}")
        print(f"{path[1]} -> {path[2]}: {edge2.confidence:.3f}")
        print(f"  Min: {min(edge1.confidence, edge2.confidence):.3f}")
    else:
        print(f"Missing edge for path {' -> '.join(path)}")
        print(f"  edge1: {edge1}")
        print(f"  edge2: {edge2}")
