# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Check if our validated predictions were already in the STRING training data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data import KomposOSStore

# Load the STRING database that was used for training
store = KomposOSStore('data/proteins/cancer_proteins.db')

# Get all morphisms (known interactions) in the training data
all_morphisms = store.list_morphisms(limit=10000)
known_edges = set()
for m in all_morphisms:
    known_edges.add((m.source_name, m.target_name))
    # Also add reverse direction since protein interactions can be bidirectional
    known_edges.add((m.target_name, m.source_name))

print("=" * 80)
print("NOVELTY CHECK: Are our predictions genuinely NEW?")
print("=" * 80)
print()
print(f"Known edges in training data: {len(all_morphisms)}")
print()

# Our validated predictions
predictions = [
    ("KRAS", "MYC", "VALIDATED"),
    ("EGFR", "MYC", "VALIDATED"),
    ("PTEN", "BAX", "VALIDATED"),
    ("EGFR", "BRAF", "VALIDATED"),
    ("EGFR", "RAF1", "VALIDATED"),
    ("BRCA1", "RAD51", "VALIDATED"),
    ("PIK3CA", "MYC", "VALIDATED"),
    ("NRAS", "MYC", "VALIDATED"),
    ("STAT3", "KRAS", "VALIDATED"),
    ("NRAS", "KRAS", "UNCLEAR"),
    ("RAF1", "TP53", "VALIDATED"),
    ("BRAF", "TP53", "VALIDATED"),
    ("PIK3CA", "KRAS", "UNCLEAR"),
    ("CDK4", "TP53", "VALIDATED"),
    ("CDK6", "TP53", "VALIDATED"),
]

print("Checking each prediction:")
print("-" * 80)
print()

in_training = 0
genuinely_novel = 0

for src, tgt, status in predictions:
    # Check if this edge was in training data
    if (src, tgt) in known_edges:
        novelty = "IN TRAINING DATA"
        in_training += 1
    elif (tgt, src) in known_edges:
        novelty = "IN TRAINING DATA (reverse)"
        in_training += 1
    else:
        novelty = "GENUINELY NOVEL (not in training data)"
        genuinely_novel += 1

    print(f"{src:10s} -> {tgt:10s} | {status:10s} | {novelty}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print(f"Total predictions: {len(predictions)}")
print(f"Already in training data: {in_training}")
print(f"Genuinely novel (missing from training): {genuinely_novel}")
print()

if genuinely_novel > 0:
    print(f"SUCCESS: {genuinely_novel} predictions are GENUINELY NEW")
    print("The system is discovering missing edges, not just memorizing!")
else:
    print("CONCERN: All predictions were already in training data")
    print("The system might just be reconstructing what it already knows")

print()
print("=" * 80)
print("KEY INSIGHT")
print("=" * 80)
print()
print("Even if predictions weren't in STRING training data, they might be")
print("encoded in the semantic embeddings model (all-mpnet-base-v2), which")
print("was trained on scientific literature including biomedical papers.")
print()
print("TRUE NOVELTY requires:")
print("1. Not in STRING training data ✓ (we can check)")
print("2. Not in literature (harder - requires exhaustive search)")
print("3. Experimentally validated as NEW biology (requires lab work)")
print()
