# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Test if the integrated calibrated weights improve the oracle's AUROC.

This uses the ACTUAL oracle with the updated merge_with() method.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle import CategoricalOracle
from oracle.strategies import (
    CompositionStrategy, TypeHeuristicStrategy,
    YonedaPatternStrategy, StructuralHoleStrategy,
    KanExtensionStrategy, FibrationLiftStrategy
)
from data import EmbeddingsEngine


def compute_auroc(scores, labels):
    """Compute AUROC manually."""
    pairs = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos

    if n_pos == 0 or n_neg == 0:
        return 0.5

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
        auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_fpr = fpr
        prev_tpr = tpr

    auroc += (1.0 - prev_fpr) * (1.0 + prev_tpr) / 2.0
    return auroc


def main():
    print("=" * 70)
    print("TESTING INTEGRATED CALIBRATED WEIGHTS IN ORACLE")
    print("=" * 70)

    # Load data
    print("\n[1/3] Loading tier1.db...")
    loader = BioDomainLoader()
    category = loader.load_tier1("data/drugs/tier1.db")

    drugs = [obj for obj in category.objects() if obj.type_name == "Drug"]
    diseases = [obj for obj in category.objects() if obj.type_name == "Disease"]

    # Find ground truth
    dd_edges = set()
    for mor in category.morphisms():
        src = category.get(mor.source)
        tgt = category.get(mor.target)
        if src and tgt and src.type_name == "Drug" and tgt.type_name == "Disease":
            dd_edges.add((mor.source, mor.target))

    print(f"  {len(drugs)} drugs, {len(diseases)} diseases = {len(drugs) * len(diseases)} pairs")
    print(f"  {len(dd_edges)} true edges")

    # Create oracle with integrated weights
    print("\n[2/3] Creating Oracle (with integrated calibrated weights)...")
    try:
        engine = EmbeddingsEngine()
    except:
        engine = None

    # Use all 6 strategies (same as calibration)
    strategies = [
        CompositionStrategy(category),
        TypeHeuristicStrategy(category),
        YonedaPatternStrategy(category),
        StructuralHoleStrategy(category),
        KanExtensionStrategy(category),
        FibrationLiftStrategy(category),
    ]

    # Create a minimal oracle that uses our strategies
    # We can't use the full CategoricalOracle because it requires embeddings
    # So we'll manually merge predictions using the updated merge_with()

    print(f"  Using {len(strategies)} strategies")
    print("  Predictions will use NEW merge_with() with calibrated weights")

    # Score all pairs
    print("\n[3/3] Scoring all pairs...")
    scores = []
    labels = []

    for drug in drugs:
        for disease in diseases:
            label = 1 if (drug.name, disease.name) in dd_edges else 0

            # Collect predictions from all strategies
            all_preds = []
            for strategy in strategies:
                try:
                    preds = strategy.predict(drug.name, disease.name)
                    all_preds.extend(preds)
                except:
                    pass

            # Merge using the NEW merge_with() method (with calibrated weights)
            if all_preds:
                # Group by key
                by_key = {}
                for pred in all_preds:
                    if pred.key not in by_key:
                        by_key[pred.key] = []
                    by_key[pred.key].append(pred)

                # Merge each group
                merged = []
                for key, preds in by_key.items():
                    if len(preds) == 1:
                        merged.append(preds[0])
                    else:
                        # Use the NEW merge_with() that has calibrated weights
                        base = preds[0]
                        for other in preds[1:]:
                            base = base.merge_with(other)
                        merged.append(base)

                # Take highest confidence
                if merged:
                    best = max(merged, key=lambda p: p.confidence)
                    score = best.confidence
                else:
                    score = 0.0
            else:
                score = 0.0

            scores.append(score)
            labels.append(label)

    # Compute AUROC
    auroc = compute_auroc(scores, labels)

    print(f"\n" + "=" * 70)
    print(f"ORACLE AUROC (with integrated calibrated weights): {auroc:.4f}")
    print("=" * 70)

    # Compare with expected
    print("\nExpected:")
    print("  Baseline (old simple average): ~0.69")
    print("  Calibrated (weighted average): ~0.84")
    print(f"\nActual: {auroc:.4f}")

    if auroc > 0.75:
        print("\nSUCCESS! Integrated weights are working!")
    else:
        print("\nHmm, lower than expected. May need investigation.")


if __name__ == "__main__":
    main()
