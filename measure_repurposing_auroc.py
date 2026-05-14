#!/usr/bin/env python3
"""
Measure Drug Repurposing AUROC on tier1.db using KOMPOSOS-IV

Direct measurement without the complex loader - just use tier1.db as-is.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.category import Category
from domains.bio import BioDomainLoader
from oracle.strategies import (
    KanExtensionStrategy,
    CompositionStrategy,
    YonedaPatternStrategy,
    FibrationLiftStrategy,
    TypeHeuristicStrategy,
    StructuralHoleStrategy
)
import random

def compute_auroc(scores, labels):
    """Compute AUROC manually (no sklearn dependency)."""
    if not scores or not labels:
        return 0.0

    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0

    # Sort by score descending
    paired = sorted(zip(scores, labels), key=lambda x: -x[0])

    tp = 0
    fp = 0
    prev_fpr = 0.0
    prev_tpr = 0.0
    auroc = 0.0
    prev_score = None

    for score, label in paired:
        if prev_score is not None and score != prev_score:
            fpr = fp / n_neg
            tpr = tp / n_pos
            # Trapezoidal area
            auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
            prev_fpr = fpr
            prev_tpr = tpr
        prev_score = score
        if label == 1:
            tp += 1
        else:
            fp += 1

    # Final point
    fpr = fp / n_neg
    tpr = tp / n_pos
    auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0

    return auroc


def main():
    print("="*70)
    print("KOMPOSOS-IV-PHARM Drug Repurposing AUROC Measurement")
    print("="*70)
    print()

    # Load tier1.db using BioDomainLoader
    db_path = "data/drugs/tier1.db"
    print(f"Loading {db_path}...")
    loader = BioDomainLoader()
    category = Category(name="DrugRepurposing", db_path=":memory:")
    loader.load_tier1(db_path, category)
    stats = loader.get_stats()
    print(f"  Loaded: {stats['objects_loaded']} objects, {stats['morphisms_loaded']} morphisms")

    # Get all objects
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count objects by type
    cursor.execute("SELECT type_name, COUNT(*) FROM objects GROUP BY type_name ORDER BY COUNT(*) DESC")
    print("\nObject counts by type:")
    for type_name, count in cursor.fetchall():
        print(f"  {type_name}: {count}")

    # Get Drug->Disease edges (ground truth)
    cursor.execute("""
        SELECT src.name, tgt.name, m.confidence
        FROM morphisms m
        JOIN objects src ON m.source_name = src.name
        JOIN objects tgt ON m.target_name = tgt.name
        WHERE src.type_name = 'Drug' AND tgt.type_name = 'Disease'
        ORDER BY src.name
    """)
    true_edges = cursor.fetchall()
    print(f"\nGround truth Drug->Disease edges: {len(true_edges)}")
    for drug, disease, conf in true_edges:
        print(f"  {drug} -> {disease} ({conf:.2f})")

    # Get all drugs and diseases
    cursor.execute("SELECT name FROM objects WHERE type_name = 'Drug' ORDER BY name")
    drugs = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT name FROM objects WHERE type_name = 'Disease' ORDER BY name")
    diseases = [row[0] for row in cursor.fetchall()]

    print(f"\nTotal drugs: {len(drugs)}")
    print(f"Total diseases: {len(diseases)}")
    print(f"Possible Drug->Disease pairs: {len(drugs) * len(diseases)}")
    print(f"Known edges: {len(true_edges)}")
    print(f"Candidates to predict: {len(drugs) * len(diseases) - len(true_edges)}")

    conn.close()

    # Create true edge set
    true_set = {(drug, disease) for drug, disease, _ in true_edges}

    # Initialize strategies (no embeddings needed)
    print("\nInitializing 6 strategies (no embeddings)...")
    strategies = [
        KanExtensionStrategy(category),
        CompositionStrategy(category),
        YonedaPatternStrategy(category),
        FibrationLiftStrategy(category),
        TypeHeuristicStrategy(category),
        StructuralHoleStrategy(category),
    ]
    print(f"  Strategies: {[s.__class__.__name__ for s in strategies]}")

    # Holdout validation: remove 20% of edges
    random.seed(42)
    holdout_size = max(1, len(true_edges) // 5)
    holdout = random.sample(true_edges, holdout_size)
    train_set = true_set - {(drug, disease) for drug, disease, _ in holdout}

    print(f"\nHoldout split:")
    print(f"  Training edges: {len(train_set)}")
    print(f"  Holdout edges: {len(holdout)}")

    # Predict all pairs
    print("\nPredicting all Drug->Disease pairs...")
    scores = []
    labels = []

    for i, drug in enumerate(drugs):
        if (i+1) % 10 == 0:
            print(f"  Processing drug {i+1}/{len(drugs)}: {drug}")

        for disease in diseases:
            # Skip training edges
            if (drug, disease) in train_set:
                continue

            # Predict using strategies
            votes = []
            for strategy in strategies:
                try:
                    result = strategy.predict(drug, disease)
                    if result and hasattr(result, 'confidence'):
                        votes.append(result.confidence)
                except:
                    pass

            # Combine scores: simple average (this is the bottleneck we'll improve later)
            score = sum(votes) / len(votes) if votes else 0.0

            scores.append(score)
            labels.append(1 if (drug, disease) in true_set else 0)

    # Compute AUROC
    auroc = compute_auroc(scores, labels)

    print("\n" + "="*70)
    print(f"AUROC: {auroc:.4f}")
    print("="*70)

    # Statistics
    n_positives = sum(labels)
    n_negatives = len(labels) - n_positives
    print(f"\nTest set statistics:")
    print(f"  Positive pairs (true edges): {n_positives}")
    print(f"  Negative pairs (false edges): {n_negatives}")
    print(f"  Total pairs tested: {len(labels)}")
    print(f"  Mean score (positives): {sum(s for s, l in zip(scores, labels) if l == 1) / n_positives if n_positives > 0 else 0:.4f}")
    print(f"  Mean score (negatives): {sum(s for s, l in zip(scores, labels) if l == 0) / n_negatives if n_negatives > 0 else 0:.4f}")

    return auroc


if __name__ == "__main__":
    main()
