
import sys
import ast
from pathlib import Path

# Ensure we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gray_coherence import SoftwareCategoryBuilder

builder = SoftwareCategoryBuilder().from_source_file("KOMPOSOS-IV/examples/mythos_victim.py")

print(f"Objects: {len(builder.objects)}")
for obj_name, obj in builder.objects.items():
    print(f"  Obj: {obj_name}, Priv: {obj.privilege}")

print(f"\nMorphisms: {len(builder.morphisms)}")
for m in builder.morphisms:
    print(f"  Morphism: {m.source} -> {m.target}, Label: {m.label}, Conf: {m.confidence}")

pairs = builder.enumerate_2cell_pairs()
print(f"\n2-Cell Pairs found: {len(pairs)}")
