#!/usr/bin/env python3
"""
Discovery session: Emily Riehl's Stable Infinity-Categories
Target: Identify structural links between stability axioms and triangulated structure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.category import Category
from core.cosmos import InfinityCosmos
from core.optimus import OptimusEngine

cat = Category(db_path=":memory:")

# ========================================================
# LAYER 1: Stable Infinity-Categories Axioms
# ========================================================
concepts = [
    # Foundations
    "InfinityCategory", "StableInfinityCategory", "PointedCategory",
    "ZeroObject", "FiniteLimits", "FiniteColimits",
    # Stability condition
    "StabilityCondition", "PushoutSquare", "PullbackSquare",
    "CofiberSequence", "FiberSequence",
    # Functors
    "SuspensionFunctor", "LoopFunctor", "SuspensionLoopEquivalence",
    # Structure
    "TriangulatedStructure", "HomotopyCategory", "AdditiveCategory",
    "ExactTriangle", "OctahedronAxiom",
    # Higher structure
    "InfinityCosmos", "Isofibration", "SpectralSequence",
    "DerivedCategory", "PerfectComplex",
    # FRONTIER CONJECTURES
    "SyntheticStability", "SyntheticTriangulated",
    "StableDirectedUnivalence", "StableSimplicialYoneda",
    "CoherentOctahedron", "SyntheticSpectralSequence",
]

for c_name in concepts:
    cat.add(c_name, type_name="concept")

# ========================================================
# MORPHISMS: Axiomatic links
# ========================================================
edges = [
    # Definitions
    ("InfinityCategory", "PointedCategory", "specializes_to", 0.9),
    ("PointedCategory", "ZeroObject", "has", 0.95),
    ("InfinityCategory", "FiniteLimits", "can_have", 0.8),
    ("InfinityCategory", "FiniteColimits", "can_have", 0.8),

    # The Stability Axiom
    ("ZeroObject", "StableInfinityCategory", "required_for", 0.95),
    ("FiniteLimits", "StableInfinityCategory", "required_for", 0.9),
    ("FiniteColimits", "StableInfinityCategory", "required_for", 0.9),
    ("StabilityCondition", "StableInfinityCategory", "defines", 0.95),
    ("PushoutSquare", "StabilityCondition", "is_pullback_in", 0.9),
    ("PullbackSquare", "StabilityCondition", "is_pushout_in", 0.9),

    # Fibrations / Sequences
    ("StableInfinityCategory", "FiberSequence", "has", 0.9),
    ("StableInfinityCategory", "CofiberSequence", "has", 0.9),
    ("FiberSequence", "CofiberSequence", "equivalent_in_stable", 0.95),

    # Suspension / Loop
    ("StableInfinityCategory", "SuspensionFunctor", "admits", 0.9),
    ("StableInfinityCategory", "LoopFunctor", "admits", 0.9),
    ("SuspensionFunctor", "SuspensionLoopEquivalence", "part_of", 0.95),
    ("LoopFunctor", "SuspensionLoopEquivalence", "part_of", 0.95),
    ("StableInfinityCategory", "SuspensionLoopEquivalence", "satisfies", 0.95),

    # Triangulated Structure
    ("StableInfinityCategory", "HomotopyCategory", "has", 0.9),
    ("HomotopyCategory", "TriangulatedStructure", "is", 0.85),
    ("StableInfinityCategory", "TriangulatedStructure", "induces", 0.9),
    ("TriangulatedStructure", "ExactTriangle", "contains", 0.9),
    ("TriangulatedStructure", "OctahedronAxiom", "satisfies", 0.8),
    ("StableInfinityCategory", "AdditiveCategory", "is", 0.85),

    # Cosmos context
    ("InfinityCosmos", "StableInfinityCategory", "contains", 0.8),
    ("Isofibration", "FiberSequence", "models", 0.75),

    # ========================================
    # FRONTIER: Connections to synthetic theory
    # ========================================
    ("StabilityCondition", "SyntheticStability", "internalizes_to", 0.6),
    ("TriangulatedStructure", "SyntheticTriangulated", "internalizes_to", 0.5),
    ("StableInfinityCategory", "StableDirectedUnivalence", "should_satisfy", 0.45),
    ("ExactTriangle", "CoherentOctahedron", "lifts_to", 0.4),
    ("OctahedronAxiom", "CoherentOctahedron", "refines_to", 0.5),
    ("StableInfinityCategory", "SyntheticSpectralSequence", "induces", 0.4),
    ("SpectralSequence", "SyntheticSpectralSequence", "formalizes_to", 0.5),
]

for src, tgt, rel, conf in edges:
    cat.connect(src, tgt, rel, confidence=conf)

print(f"Built category: {len(cat.objects())} objects, {len(cat.morphisms())} morphisms")
print()

# ========================================================
# OPTIMUS: Find structural gaps
# ========================================================
optimus = OptimusEngine(cat, max_depth=3)
gaps = optimus.find_structural_gaps()
print(f"=== STRUCTURAL GAPS (candidate conjectures): {len(gaps)} ===")
for g in gaps[:20]:
    print(f"  {g}")
print()

# ========================================================
# OPTIMUS: Discover intermediate objects
# ========================================================
print("=== INTERMEDIATE OBJECT DISCOVERY ===")
discovery_pairs = [
    ("ZeroObject", "TriangulatedStructure"),
    ("StabilityCondition", "SuspensionLoopEquivalence"),
    ("FiberSequence", "ExactTriangle"),
    ("InfinityCategory", "StableInfinityCategory"),
    ("OctahedronAxiom", "CoherentOctahedron"),
    ("StableInfinityCategory", "SyntheticSpectralSequence"),
    ("PushoutSquare", "FiberSequence"),
]
for src, tgt in discovery_pairs:
    intermediates = optimus.discover_intermediates(src, tgt)
    if intermediates:
        chain = " -> ".join(str(i) for i in intermediates)
        print(f"  {src} -> {chain} -> {tgt}")
    else:
        print(f"  {src} -> [MISSING LINK] -> {tgt}  ** CONJECTURE CANDIDATE **")
print()

# ========================================================
# COSMOS: Higher categorical structure
# ========================================================
cosmos = InfinityCosmos(cat)
h2k = cosmos.homotopy_2_category()
two_cells = list(h2k.two_cells.values())
print(f"=== HOMOTOPY 2-CATEGORY ===")
print(f"  2-cells found: {len(two_cells)}")

fibs = list(cosmos.cartesian_fibrations().values())
print(f"  Cartesian fibrations: {len(fibs)}")

yoneda = cosmos.yoneda_embedding()
print(f"  Yoneda faithfulness: {yoneda.faithfulness_score}")
print()

# ========================================================
# DualEngine: classify conjectures
# ========================================================
try:
    from zfc.category_store_adapter import StoreAdapter
    from zfc.category_bridge import DualEngineBridge

    adapter = StoreAdapter(cat)
    dual = DualEngineBridge(adapter, category=cat)

    print("=== DUAL ENGINE CONJECTURE CLASSIFICATION ===")
    conjectures = [
        ("StabilityCondition", "SyntheticStability", "satisfies"),
        ("TriangulatedStructure", "SyntheticTriangulated", "internalizes"),
        ("StableInfinityCategory", "StableDirectedUnivalence", "satisfies"),
        ("OctahedronAxiom", "CoherentOctahedron", "refines_to"),
        ("StableInfinityCategory", "SyntheticSpectralSequence", "induces"),
    ]
    for src, tgt, rel in conjectures:
        r = dual.query(src, tgt, rel)
        delta = r.delta_type if hasattr(r, 'delta_type') else str(r)
        print(f"  {src} --{rel}--> {tgt}: {delta}")
except Exception as e:
    print(f"DualEngine: {e}")

print("\n=== DISCOVERY SESSION COMPLETE ===")
