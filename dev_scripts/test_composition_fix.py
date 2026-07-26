"""Test the fixed CompositionStrategy."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from oracle.strategies import CompositionStrategy

# Load data
loader = BioDomainLoader()
category = loader.load_tier1("data/drugs/tier1.db")

# Create strategy
strategy = CompositionStrategy(category)

# Test on a few Drug-Disease pairs
drugs = [obj for obj in category.objects() if obj.type_name == "Drug"]
diseases = [obj for obj in category.objects() if obj.type_name == "Disease"]

print(f"Testing CompositionStrategy with type filtering")
print(f"Drugs: {len(drugs)}, Diseases: {len(diseases)}")
print()

# Test first 5 drugs against first 3 diseases
count = 0
for drug in drugs[:5]:
    for disease in diseases[:3]:
        predictions = strategy.predict(drug.name, disease.name)
        if predictions:
            count += len(predictions)
            for pred in predictions:
                print(f"{drug.name} -> {disease.name}")
                print(f"  Confidence: {pred.confidence:.3f}")
                print(f"  Intermediate: {pred.evidence.get('intermediate')}")
                print(f"  Reasoning: {pred.reasoning}")
                print()

print(f"Total predictions: {count}")

# Also test all Drug-Disease pairs
all_preds = 0
for drug in drugs:
    for disease in diseases:
        predictions = strategy.predict(drug.name, disease.name)
        all_preds += len(predictions)

print(f"\nTotal Drug-Disease predictions: {all_preds} out of {len(drugs) * len(diseases)} possible pairs")
