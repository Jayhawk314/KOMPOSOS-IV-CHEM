"""
Calibrate with ALL 22 strategies enabled.

This will:
1. Try to load all available strategies
2. Calibrate each one
3. Measure AUROC with full strategy set
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle.strategies import create_all_strategies
from oracle.calibration import StrategyCalibrator, weighted_average
from data import EmbeddingsEngine
import numpy as np


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
    print("CALIBRATING ALL 22 STRATEGIES")
    print("=" * 70)

    # Load data
    print("\n[1/5] Loading tier1.db...")
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

    # Create ALL strategies
    print("\n[2/5] Loading ALL strategies...")
    try:
        engine = EmbeddingsEngine()
        strategies = create_all_strategies(category, engine)
        print(f"  Loaded {len(strategies)} strategies successfully!")
    except Exception as e:
        print(f"  Error loading strategies: {e}")
        print("  Falling back to basic strategies...")
        from oracle.strategies import (
            CompositionStrategy, TypeHeuristicStrategy,
            YonedaPatternStrategy, StructuralHoleStrategy,
            KanExtensionStrategy, FibrationLiftStrategy
        )
        strategies = [
            CompositionStrategy(category),
            TypeHeuristicStrategy(category),
            YonedaPatternStrategy(category),
            StructuralHoleStrategy(category),
            KanExtensionStrategy(category),
            FibrationLiftStrategy(category),
        ]
        print(f"  Using {len(strategies)} basic strategies")

    print("\n  Strategy list:")
    for i, s in enumerate(strategies, 1):
        print(f"    {i:2d}. {s.name}")

    # Score all pairs
    print(f"\n[3/5] Scoring {len(drugs) * len(diseases)} pairs with {len(strategies)} strategies...")
    all_pairs = []

    for drug in drugs:
        for disease in diseases:
            pair = (drug.name, disease.name)
            label = 1 if pair in dd_edges else 0

            # Collect votes from each strategy
            votes = []
            for strategy in strategies:
                try:
                    preds = strategy.predict(drug.name, disease.name)
                    if preds:
                        best = max(preds, key=lambda p: p.confidence)
                        votes.append((strategy.name, best.confidence))
                except Exception as e:
                    pass  # Strategy failed, skip

            if votes:
                baseline_score = sum(c for _, c in votes) / len(votes)
                all_pairs.append({
                    'label': label,
                    'baseline_score': baseline_score,
                    'votes': votes
                })

    print(f"  Got predictions for {len(all_pairs)} pairs")

    # Baseline AUROC
    baseline_scores = [p['baseline_score'] for p in all_pairs]
    labels = [p['label'] for p in all_pairs]
    baseline_auroc = compute_auroc(baseline_scores, labels)

    print(f"\n  BASELINE AUROC (simple average): {baseline_auroc:.4f}")

    # Calibrate
    print(f"\n[4/5] Calibrating {len(strategies)} strategies...")
    calibrator = StrategyCalibrator()

    for pair_data in all_pairs:
        is_correct = (pair_data['label'] == 1)
        for strategy_name, confidence in pair_data['votes']:
            calibrator.record_prediction(strategy_name, confidence, is_correct, pair_data)

    calibrator.calibrate()
    calibrator.save("data/strategy_weights_all22.json")

    # Re-score with calibration
    print(f"\n[5/5] Re-scoring with calibrated weights...")
    calibrated_scores = []
    for pair_data in all_pairs:
        calibrated_score = weighted_average(pair_data['votes'], calibrator)
        calibrated_scores.append(calibrated_score)

    calibrated_auroc = compute_auroc(calibrated_scores, labels)

    print("\n" + "=" * 70)
    print("RESULTS WITH ALL STRATEGIES:")
    print("=" * 70)
    print(f"Strategies used:     {len(strategies)}")
    print(f"Baseline AUROC:      {baseline_auroc:.4f}")
    print(f"Calibrated AUROC:    {calibrated_auroc:.4f}")
    print(f"Improvement:         +{(calibrated_auroc - baseline_auroc):.4f}")
    print("=" * 70)

    # Compare with previous best (6 strategies)
    print("\nComparison:")
    print(f"  Previous (6 strategies):  0.8448")
    print(f"  Current ({len(strategies)} strategies):   {calibrated_auroc:.4f}")

    if calibrated_auroc > 0.8448:
        improvement = calibrated_auroc - 0.8448
        print(f"  IMPROVEMENT: +{improvement:.4f} AUROC!")
    elif calibrated_auroc < 0.8448:
        decline = 0.8448 - calibrated_auroc
        print(f"  Decline: -{decline:.4f} (some new strategies may be noisy)")
    else:
        print(f"  Same performance")

    print(f"\nCalibrated weights saved to: data/strategy_weights_all22.json")


if __name__ == "__main__":
    main()
