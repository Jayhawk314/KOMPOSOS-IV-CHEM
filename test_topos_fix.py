"""Test the fixed ToposLogicStrategy."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle.topos_strategy import ToposLogicStrategy

# Load data
loader = BioDomainLoader()
category = loader.load_tier1("data/drugs/tier1.db")

# Create strategy
strategy = ToposLogicStrategy(category)

# Test on a few Drug-Disease pairs
drugs = [obj for obj in category.objects() if obj.type_name == "Drug"][:10]
diseases = [obj for obj in category.objects() if obj.type_name == "Disease"][:3]

# Find ground truth
dd_edges = set()
for mor in category.morphisms():
    src = category.get(mor.source)
    tgt = category.get(mor.target)
    if src and tgt and src.type_name == "Drug" and tgt.type_name == "Disease":
        dd_edges.add((mor.source, mor.target))

print(f"Testing ToposLogicStrategy with pathway prediction")
print(f"Ground truth: {len(dd_edges)} Drug->Disease edges")
print()

# Test all
total_preds = 0
correct_preds = 0

for drug in drugs:
    for disease in diseases:
        predictions = strategy.predict(drug.name, disease.name)
        if predictions:
            total_preds += len(predictions)
            is_true = (drug.name, disease.name) in dd_edges

            if is_true:
                correct_preds += len(predictions)

            for pred in predictions:
                truth_mark = " [TRUE]" if is_true else ""
                print(f"{drug.name} -> {disease.name}{truth_mark}")
                print(f"  Type: {pred.evidence.get('truth_type')}")
                print(f"  Confidence: {pred.confidence:.3f}")
                print(f"  Reasoning: {pred.reasoning}")
                print()

print(f"\nTotal predictions: {total_preds}")
print(f"Correct predictions: {correct_preds}")
if total_preds > 0:
    print(f"Precision: {correct_preds/total_preds:.1%}")
