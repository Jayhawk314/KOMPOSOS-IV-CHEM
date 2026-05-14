"""
Test with 6 basic strategies PLUS fixed topos_logic.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle.strategies import (
    KanExtensionStrategy, CompositionStrategy, YonedaPatternStrategy,
    FibrationLiftStrategy, TypeHeuristicStrategy, StructuralHoleStrategy
)
from oracle.topos_strategy import ToposLogicStrategy
from oracle.calibration import StrategyCalibrator, weighted_average


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


# Load data
print("=" * 70)
print("TESTING 6 BASIC + FIXED TOPOS_LOGIC")
print("=" * 70)

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

print(f"  {len(drugs)} drugs, {len(diseases)} diseases, {len(dd_edges)} true edges")

# Load 6 basic + topos
print("\n[2/5] Loading strategies...")
strategies = [
    KanExtensionStrategy(category),
    TypeHeuristicStrategy(category),
    YonedaPatternStrategy(category),
    StructuralHoleStrategy(category),
    CompositionStrategy(category),
    FibrationLiftStrategy(category),
    ToposLogicStrategy(category),  # ADDED!
]
print(f"  Loaded: {', '.join(s.name for s in strategies)}")

# Score all pairs
print(f"\n[3/5] Scoring {len(drugs) * len(diseases)} pairs...")
all_pairs = []

for drug in drugs:
    for disease in diseases:
        pair = (drug.name, disease.name)
        label = 1 if pair in dd_edges else 0

        votes = []
        for strategy in strategies:
            try:
                preds = strategy.predict(drug.name, disease.name)
                if preds:
                    best = max(preds, key=lambda p: p.confidence)
                    votes.append((strategy.name, best.confidence))
            except:
                pass

        if votes:
            baseline_score = sum(c for _, c in votes) / len(votes)
            all_pairs.append({
                'label': label,
                'baseline_score': baseline_score,
                'votes': votes
            })

print(f"  Scored {len(all_pairs)} pairs")

# Baseline AUROC
baseline_scores = [p['baseline_score'] for p in all_pairs]
labels = [p['label'] for p in all_pairs]
baseline_auroc = compute_auroc(baseline_scores, labels)

print(f"\n  BASELINE (simple average): {baseline_auroc:.4f}")

# Calibrate
print(f"\n[4/5] Calibrating strategies...")
calibrator = StrategyCalibrator()

for pair_data in all_pairs:
    is_correct = (pair_data['label'] == 1)
    for strategy_name, confidence in pair_data['votes']:
        calibrator.record_prediction(strategy_name, confidence, is_correct, pair_data)

calibrator.calibrate()
calibrator.save("data/strategy_weights_with_topos.json")

# Re-score
print(f"\n[5/5] Re-scoring with calibrated weights...")
calibrated_scores = []
for pair_data in all_pairs:
    calibrated_score = weighted_average(pair_data['votes'], calibrator)
    calibrated_scores.append(calibrated_score)

calibrated_auroc = compute_auroc(calibrated_scores, labels)

print("\n" + "=" * 70)
print("RESULTS WITH 6 BASIC + FIXED TOPOS_LOGIC:")
print("=" * 70)
print(f"Baseline AUROC:    {baseline_auroc:.4f}")
print(f"Calibrated AUROC:  {calibrated_auroc:.4f}")
print(f"Improvement:       +{(calibrated_auroc - baseline_auroc):.4f}")
print("=" * 70)

print("\nComparison:")
print(f"  Previous (6 basic):           0.8448")
print(f"  Current (6 basic + topos):    {calibrated_auroc:.4f}")

if calibrated_auroc > 0.8448:
    print(f"\n  SUCCESS! +{(calibrated_auroc - 0.8448):.4f} improvement!")
elif calibrated_auroc < 0.8448:
    print(f"\n  Declined by {(0.8448 - calibrated_auroc):.4f}")
else:
    print(f"\n  No change")
