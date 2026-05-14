"""
Verify the AUROC claim by checking actual predictions and scores.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle.strategies import KanExtensionStrategy, TypeHeuristicStrategy, StructuralHoleStrategy, CompositionStrategy
from oracle.topos_strategy import ToposLogicStrategy
from oracle.calibration import StrategyCalibrator, weighted_average

# Load data
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

print(f"Ground truth: {len(dd_edges)} Drug->Disease edges")
print(f"Total possible pairs: {len(drugs)} x {len(diseases)} = {len(drugs) * len(diseases)}")
print()

# Load strategies
strategies = [
    KanExtensionStrategy(category),
    TypeHeuristicStrategy(category),
    StructuralHoleStrategy(category),
    ToposLogicStrategy(category),
]

# Score ALL pairs and check distribution
true_scores = []
false_scores = []
no_prediction_count = 0

print("Checking all pairs...")
for drug in drugs:
    for disease in diseases:
        pair = (drug.name, disease.name)
        is_true = pair in dd_edges

        # Get predictions
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
            score = sum(c for _, c in votes) / len(votes)

            if is_true:
                true_scores.append((drug.name, disease.name, score))
            else:
                false_scores.append((drug.name, disease.name, score))
        else:
            no_prediction_count += 1

print(f"\nResults:")
print(f"  Pairs WITH predictions: {len(true_scores) + len(false_scores)}")
print(f"  Pairs WITHOUT predictions: {no_prediction_count}")
print(f"  True pairs scored: {len(true_scores)}/{len(dd_edges)}")
print(f"  False pairs scored: {len(false_scores)}/{len(drugs)*len(diseases) - len(dd_edges)}")
print()

# Check score distributions
if true_scores:
    min_true = min(s[2] for s in true_scores)
    max_true = max(s[2] for s in true_scores)
    avg_true = sum(s[2] for s in true_scores) / len(true_scores)
    print(f"True pair scores: min={min_true:.3f}, max={max_true:.3f}, avg={avg_true:.3f}")

if false_scores:
    min_false = min(s[2] for s in false_scores)
    max_false = max(s[2] for s in false_scores)
    avg_false = sum(s[2] for s in false_scores) / len(false_scores)
    print(f"False pair scores: min={min_false:.3f}, max={max_false:.3f}, avg={avg_false:.3f}")
    print()

# Check for overlap
if true_scores and false_scores:
    overlap_count = sum(1 for _, _, fs in false_scores if fs >= min_true)
    print(f"False pairs scoring >= min true score: {overlap_count}")

    if overlap_count > 0:
        print(f"  This means AUROC < 1.0 (there IS overlap)")
        print(f"\n  Top false pairs (should be ranked below true pairs):")
        sorted_false = sorted(false_scores, key=lambda x: -x[2])[:10]
        for drug, disease, score in sorted_false:
            print(f"    {drug} -> {disease}: {score:.3f}")
    else:
        print(f"  All true pairs scored higher than all false pairs → AUROC = 1.0 ✓")
        print(f"\n  Lowest true pair: {min(true_scores, key=lambda x: x[2])}")
        print(f"  Highest false pair: {max(false_scores, key=lambda x: -x[2])}")

# Manual AUROC calculation
def compute_auroc_manual(true_scores, false_scores):
    """Compute AUROC by counting comparisons."""
    if not true_scores or not false_scores:
        return None

    # Count how many times true > false
    correct_comparisons = 0
    total_comparisons = 0

    for _, _, ts in true_scores:
        for _, _, fs in false_scores:
            total_comparisons += 1
            if ts > fs:
                correct_comparisons += 1
            elif ts == fs:
                correct_comparisons += 0.5  # Ties count as 0.5

    return correct_comparisons / total_comparisons if total_comparisons > 0 else 0.5

auroc = compute_auroc_manual(true_scores, false_scores)
print(f"\nManual AUROC calculation: {auroc:.4f}" if auroc else "\nCannot compute AUROC (missing true or false scores)")
