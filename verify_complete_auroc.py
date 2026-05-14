"""
Reproduce the historical legacy AUROC benchmark.

This script intentionally uses the named legacy view from
validation/repurposing_benchmark.py. Production loading should use
BioDomainLoader or the full_typed benchmark view instead.
"""

from validation.repurposing_benchmark import evaluate_category, load_legacy_view


category = load_legacy_view("data/drugs/tier1.db")
result = evaluate_category(category, view="legacy", protocol="as_loaded")

true_scores = result.true_scores
false_count = result.n_negatives
missing_true = result.n_true_unscored

print("COMPLETE AUROC (legacy 224-pair benchmark view)")
print("=" * 60)
print(f"Total pairs evaluated: {result.n_pairs}")
print(f"True pairs:  {result.n_positives} (scores: {['%.3f' % s for s in true_scores]})")
print(f"False pairs: {false_count}")
print(f"True pairs with no predictions: {missing_true}")
print()
print(f"Concordant (true > false):  {result.concordant}")
print(f"Discordant (true < false):  {result.discordant}")
print(f"Tied (true == false):       {result.tied}")
print(f"Total comparisons:          {result.concordant + result.discordant + result.tied}")
print()
print(f"AUROC = {result.auroc:.6f}")
print()
print(f"Min true score:  {min(true_scores):.4f}")
print(f"Max true score:  {max(true_scores):.4f}")
print(f"Max false score: {result.max_false_score:.4f}")
