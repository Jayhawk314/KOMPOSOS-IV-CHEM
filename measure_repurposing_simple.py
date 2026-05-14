"""
Simple AUROC measurement for drug repurposing using IV-PHARM API.

Loads tier1.db, scores all Drug->Disease pairs, computes AUROC.
No adapters, no legacy code - just the actual IV API.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle import CategoricalOracle
from oracle.strategies import create_all_strategies
from data import EmbeddingsEngine
import numpy as np


def compute_auroc(scores, labels):
    """Compute AUROC manually (no sklearn dependency)."""
    # Sort by score descending
    pairs = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)

    n_pos = sum(labels)
    n_neg = len(labels) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Compute TPR and FPR at each threshold
    tp = fp = 0
    prev_fpr = prev_tpr = 0.0
    auroc = 0.0

    for score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1

        tpr = tp / n_pos
        fpr = fp / n_neg

        # Trapezoidal rule
        auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_fpr = fpr
        prev_tpr = tpr

    # Final segment to (1, 1)
    auroc += (1.0 - prev_fpr) * (1.0 + prev_tpr) / 2.0

    return auroc


def main():
    print("=" * 70)
    print("KOMPOSOS-IV-PHARM Drug Repurposing AUROC")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading tier1.db...")
    loader = BioDomainLoader()
    category = loader.load_tier1("data/drugs/tier1.db")

    # Get Drug and Disease objects
    drugs = [obj for obj in category.objects() if obj.type_name == "Drug"]
    diseases = [obj for obj in category.objects() if obj.type_name == "Disease"]

    print(f"  Found {len(drugs)} drugs, {len(diseases)} diseases")

    # Find existing Drug->Disease edges (ground truth)
    dd_edges = set()
    for mor in category.morphisms():
        src = category.get(mor.source)
        tgt = category.get(mor.target)
        if src and tgt and src.type_name == "Drug" and tgt.type_name == "Disease":
            dd_edges.add((mor.source, mor.target))

    print(f"  Found {len(dd_edges)} existing Drug->Disease edges (ground truth)")

    # Create Oracle
    print("\n[2/4] Creating Oracle with all 22 strategies...")
    engine = EmbeddingsEngine()
    strategies = create_all_strategies(category, engine)
    oracle = CategoricalOracle(category=category, embeddings=engine, strategies=strategies)

    print(f"  Loaded {len(strategies)} strategies")

    # Score all Drug->Disease pairs
    print(f"\n[3/4] Scoring {len(drugs)} × {len(diseases)} = {len(drugs) * len(diseases)} pairs...")

    all_scores = []
    all_labels = []

    for drug in drugs:
        for disease in diseases:
            pair = (drug.name, disease.name)
            label = 1 if pair in dd_edges else 0

            # Get oracle prediction
            pred = oracle.predict(drug.name, disease.name)
            score = pred.confidence if pred else 0.0

            all_scores.append(score)
            all_labels.append(label)

    print(f"  Positives: {sum(all_labels)}")
    print(f"  Negatives: {len(all_labels) - sum(all_labels)}")

    # Compute AUROC
    print("\n[4/4] Computing AUROC...")
    auroc = compute_auroc(all_scores, all_labels)

    print("\n" + "=" * 70)
    print(f"AUROC: {auroc:.4f}")
    print("=" * 70)

    # Show some stats
    pos_scores = [s for s, l in zip(all_scores, all_labels) if l == 1]
    neg_scores = [s for s, l in zip(all_scores, all_labels) if l == 0]

    if pos_scores and neg_scores:
        print(f"\nPositive pairs: mean={np.mean(pos_scores):.4f}, max={max(pos_scores):.4f}")
        print(f"Negative pairs: mean={np.mean(neg_scores):.4f}, max={max(neg_scores):.4f}")

    return auroc


if __name__ == "__main__":
    main()
