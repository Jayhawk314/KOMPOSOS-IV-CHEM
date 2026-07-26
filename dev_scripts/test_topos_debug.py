"""Debug topos pathway prediction."""
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

# Test a specific Drug-Disease pair without direct edge
# Gefitinib -> NSCLC (no direct edge, but should have path via EGFR)
source = "Gefitinib"
target = "NSCLC"

print(f"Testing pathway prediction for {source} -> {target}")
print()

# Check if direct edge exists
direct = strategy._has_direct_edge(source, target)
print(f"Direct edge exists: {direct is not None}")
print()

# Check pathway support directly
pathway_result = strategy._check_pathway_support(source, target)
print(f"Pathway result: {pathway_result}")
print()

# Find paths manually
paths = category.find_paths(source, target, max_length=3)
print(f"Paths found: {len(paths)}")
for path in paths[:5]:
    print(f"  {' -> '.join(path)}")
print()

# Full prediction
predictions = strategy.predict(source, target)
print(f"Predictions: {len(predictions)}")
for pred in predictions:
    print(f"  {pred.evidence.get('truth_type')}: confidence={pred.confidence:.3f}")
    print(f"  {pred.reasoning}")
