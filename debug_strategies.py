from domains.bio import BioDomainLoader
from oracle.strategies import CompositionStrategy
from core.category import Category

loader = BioDomainLoader()
category = loader.load_tier1("data/drugs/tier1.db")

print(f"Category: {category}")
print(f"Num objects: {len(category.objects())}")
print(f"Num morphisms: {len(category.morphisms())}")

strategy = CompositionStrategy(category)
morphisms = strategy._get_morphisms()
print(f"Strategy morphisms: {len(morphisms)}")

if morphisms:
    m = morphisms[0]
    print(f"Morphism type: {type(m)}")
    print(f"Morphism source: {getattr(m, 'source', 'N/A')}")
    print(f"Morphism target: {getattr(m, 'target', 'N/A')}")
    print(f"Morphism source_name: {getattr(m, 'source_name', 'N/A')}")

outgoing, incoming = strategy._build_morphism_index()
print(f"Outgoing index size: {len(outgoing)}")
print(f"Incoming index size: {len(incoming)}")

# Test a known positive if possible
# Imatinib -> BCR-ABL (protein) -> CML (disease)
# Wait, let's just test any composition.
for src in outgoing:
    for mor1 in outgoing[src]:
        inter = getattr(mor1, 'target', getattr(mor1, 'target_name', None))
        if inter in outgoing:
            print(f"Found potential composition: {src} -> {inter} -> {getattr(outgoing[inter][0], 'target', '???')}")
            preds = strategy.predict(src, getattr(outgoing[inter][0], 'target', '???'))
            print(f"Predictions: {preds}")
            if preds:
                break
    else:
        continue
    break
