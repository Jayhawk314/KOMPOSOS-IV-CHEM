#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Discovery session: Emily Riehl's Simplicial Type Theory + Infinity-Cosmos
Target: find structural gaps that are CANDIDATE NOVEL CONJECTURES

Outputs results to JSON for downstream consumption.
Optionally pipes through IntegratedDiscoveryPipeline for full verification.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.category import Category
from core.cosmos import InfinityCosmos
from core.optimus import OptimusEngine

cat = Category(db_path=":memory:")

# ========================================================
# LAYER 1: Simplicial Type Theory (Riehl-Shulman 2017)
# ========================================================
concepts = [
    # STT foundations
    "SimplicialType", "FibrantType", "CovariantFamily", "ContravariantFamily",
    "SegalType", "RezkType", "DiscreteType", "DirectedInterval",
    "SimplexCategory", "HornInclusion", "InnerHorn", "OuterHorn",
    "ExtensionType", "DependentProduct", "DependentSum",
    "IdentityType", "PathType", "HomType",
    # Infinity-categorical structures (Riehl-Verity)
    "InfinityCosmos", "InfinityCategory", "InfinityFunctor",
    "InfinityNatTrans", "AdjointFunctor",
    "QuasiCategory", "CompleteSegalSpace", "SegalCategory",
    "Isofibration", "TrivialFibration", "InnerFibration",
    "CartesianFibration", "CoCartesianFibration",
    "Homotopy2Category", "YonedaEmbedding", "YonedaLemma",
    "PointwiseKanExt", "AbsoluteKanExt",
    "AdjointFunctorThm", "LimitThm", "ColimitThm",
    # Known results
    "SegalCondition", "RezkCompleteness", "UnivalenceAxiom",
    "ModelIndependence", "CoherentAdjunction", "MonadicAdjunction",
    "CommaObject", "SliceInfCosmos",
    # OPEN PROBLEMS (low-confidence frontier)
    "SimplicialYoneda", "DirectedUnivalence",
    "SyntheticCartFib", "SyntheticLimits",
    "SyntheticAdjoint", "HigherCoherence",
    "InternalLanguageInfCosmos", "SyntheticMonad",
    "DirectedHomotopyHypothesis", "SyntheticStableInfCat",
]

for c_name in concepts:
    cat.add(c_name, type_name="concept")

# ========================================================
# MORPHISMS: dependency/implication structure
# ========================================================
edges = [
    # STT foundations
    ("SimplicialType", "FibrantType", "refines_to", 0.95),
    ("FibrantType", "SegalType", "specializes_to", 0.9),
    ("SegalType", "RezkType", "completes_to", 0.85),
    ("RezkType", "InfinityCategory", "models", 0.9),
    ("DirectedInterval", "SimplicialType", "generates", 0.95),
    ("SimplexCategory", "DirectedInterval", "contains", 0.9),
    ("FibrantType", "CovariantFamily", "has_family", 0.85),
    ("FibrantType", "ContravariantFamily", "has_family", 0.85),

    # Extension types
    ("ExtensionType", "HomType", "generalizes", 0.85),
    ("ExtensionType", "PathType", "generalizes", 0.85),
    ("HomType", "IdentityType", "degeneracy_of", 0.8),
    ("ExtensionType", "DependentProduct", "expressed_via", 0.8),
    ("ExtensionType", "DependentSum", "dual_of", 0.75),

    # Segal condition
    ("SegalCondition", "SegalType", "defines", 0.95),
    ("InnerHorn", "SegalCondition", "characterizes", 0.9),
    ("HornInclusion", "InnerHorn", "includes", 0.95),
    ("HornInclusion", "OuterHorn", "includes", 0.95),
    ("OuterHorn", "CartesianFibration", "characterizes", 0.85),

    # Cosmos
    ("InfinityCosmos", "Isofibration", "has_class", 0.95),
    ("Isofibration", "TrivialFibration", "specializes", 0.9),
    ("Isofibration", "InnerFibration", "generalizes", 0.85),
    ("CartesianFibration", "Isofibration", "is_a", 0.9),
    ("CoCartesianFibration", "Isofibration", "is_a", 0.9),
    ("CartesianFibration", "CovariantFamily", "classifies", 0.8),
    ("CoCartesianFibration", "ContravariantFamily", "classifies", 0.8),

    # Model independence
    ("ModelIndependence", "QuasiCategory", "applies_to", 0.95),
    ("ModelIndependence", "CompleteSegalSpace", "applies_to", 0.95),
    ("ModelIndependence", "SegalCategory", "applies_to", 0.95),
    ("InfinityCosmos", "ModelIndependence", "guarantees", 0.95),

    # Yoneda
    ("YonedaEmbedding", "YonedaLemma", "proved_by", 0.95),
    ("YonedaEmbedding", "InfinityCategory", "embeds_into", 0.9),
    ("InfinityFunctor", "InfinityNatTrans", "has", 0.9),

    # Kan extensions
    ("PointwiseKanExt", "LimitThm", "uses", 0.85),
    ("PointwiseKanExt", "ColimitThm", "uses", 0.85),
    ("AbsoluteKanExt", "PointwiseKanExt", "specializes", 0.9),
    ("YonedaLemma", "AbsoluteKanExt", "characterizes", 0.85),

    # Adjunctions
    ("AdjointFunctor", "CoherentAdjunction", "has_data", 0.9),
    ("MonadicAdjunction", "AdjointFunctor", "is_a", 0.85),
    ("AdjointFunctorThm", "AdjointFunctor", "produces", 0.9),

    # Homotopy 2-category
    ("InfinityCosmos", "Homotopy2Category", "has", 0.95),
    ("Homotopy2Category", "InfinityFunctor", "1cells", 0.9),
    ("Homotopy2Category", "InfinityNatTrans", "2cells", 0.9),
    ("Homotopy2Category", "AdjointFunctor", "contains", 0.85),

    # Comma / slice
    ("CommaObject", "InfinityCosmos", "lives_in", 0.9),
    ("SliceInfCosmos", "InfinityCosmos", "is_a", 0.85),
    ("CommaObject", "PointwiseKanExt", "computes_via", 0.8),

    # ========================================
    # FRONTIER: connections to open problems
    # (lower confidence = less certain)
    # ========================================
    ("RezkType", "DirectedUnivalence", "conjectured", 0.6),
    ("UnivalenceAxiom", "DirectedUnivalence", "generalizes_to", 0.6),
    ("SegalType", "SyntheticCartFib", "should_define", 0.5),
    ("OuterHorn", "SyntheticCartFib", "should_characterize", 0.5),
    ("ExtensionType", "SyntheticLimits", "should_express", 0.5),
    ("SimplicialType", "SimplicialYoneda", "should_prove", 0.5),
    ("YonedaLemma", "SimplicialYoneda", "lifts_to", 0.55),
    ("CoherentAdjunction", "SyntheticAdjoint", "internalizes_to", 0.5),
    ("AdjointFunctorThm", "SyntheticAdjoint", "should_lift", 0.45),
    ("RezkType", "InternalLanguageInfCosmos", "is_candidate_for", 0.65),
    ("InfinityCosmos", "InternalLanguageInfCosmos", "needs", 0.7),
    ("MonadicAdjunction", "SyntheticMonad", "should_internalize", 0.45),
    ("RezkType", "DirectedHomotopyHypothesis", "should_satisfy", 0.4),
    ("InfinityCategory", "DirectedHomotopyHypothesis", "classifies", 0.4),
    ("SyntheticLimits", "SyntheticStableInfCat", "needed_for", 0.4),
    ("SyntheticAdjoint", "SyntheticStableInfCat", "needed_for", 0.4),
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
    ("SimplicialType", "InfinityCategory"),
    ("ExtensionType", "YonedaLemma"),
    ("SegalType", "CartesianFibration"),
    ("UnivalenceAxiom", "DirectedUnivalence"),
    ("RezkType", "InternalLanguageInfCosmos"),
    ("OuterHorn", "CoCartesianFibration"),
    ("HomType", "InfinityNatTrans"),
    ("MonadicAdjunction", "SyntheticMonad"),
    ("SegalCondition", "Homotopy2Category"),
    ("ExtensionType", "SyntheticLimits"),
]
intermediate_results = []
for src, tgt in discovery_pairs:
    intermediates = optimus.discover_intermediates(src, tgt)
    if intermediates:
        chain = " -> ".join(str(i) for i in intermediates)
        print(f"  {src} -> {chain} -> {tgt}")
        intermediate_results.append({
            "source": src, "target": tgt,
            "intermediates": [str(i) for i in intermediates],
        })
    else:
        print(f"  {src} -> [MISSING LINK] -> {tgt}  ** CONJECTURE CANDIDATE **")
        intermediate_results.append({
            "source": src, "target": tgt,
            "intermediates": [],
            "conjecture_candidate": True,
        })
print()

# ========================================================
# COSMOS: Higher categorical structure
# ========================================================
cosmos = InfinityCosmos(cat)
h2k = cosmos.homotopy_2_category()
two_cells = list(h2k.two_cells.values())
print(f"=== HOMOTOPY 2-CATEGORY ===")
print(f"  2-cells found: {len(two_cells)}")
for tc in two_cells[:10]:
    print(f"    {tc}")

fibs = list(cosmos.cartesian_fibrations().values())
print(f"\n  Cartesian fibrations: {len(fibs)}")
for f in fibs[:10]:
    print(f"    {f}")

yoneda = cosmos.yoneda_embedding()
print(f"\n  Yoneda faithfulness: {yoneda.faithfulness_score}")
print(f"  Representables: {len(yoneda.presheaf_objects)}")
print()

# ========================================================
# OPTIMUS REFINE: categorical gradient descent
# ========================================================
print("=== OPTIMUS CATEGORICAL GRADIENT DESCENT ===")
result = optimus.refine(max_steps=30, depth=2)
print(f"  Steps: {result.get('steps', '?')}")
print(f"  Synced morphisms: {result.get('synced_morphisms', '?')}")
print(f"  Improvements: {result.get('improvements', '?')}")
print()

# ========================================================
# DualEngine: classify conjectures
# ========================================================
dual_results = []
try:
    from zfc.category_store_adapter import StoreAdapter
    from zfc.category_bridge import DualEngineBridge

    adapter = StoreAdapter(cat)
    dual = DualEngineBridge(adapter, category=cat)

    print("=== DUAL ENGINE CONJECTURE CLASSIFICATION ===")
    conjectures = [
        ("RezkType", "DirectedUnivalence", "satisfies"),
        ("ExtensionType", "SyntheticLimits", "expresses"),
        ("SimplicialType", "SimplicialYoneda", "proves"),
        ("SegalType", "SyntheticCartFib", "defines"),
        ("RezkType", "InternalLanguageInfCosmos", "is_language_of"),
        ("MonadicAdjunction", "SyntheticMonad", "internalizes"),
        ("OuterHorn", "SyntheticCartFib", "characterizes"),
        ("InfinityCategory", "DirectedHomotopyHypothesis", "satisfies"),
    ]
    for src, tgt, rel in conjectures:
        r = dual.query(src, tgt, rel)
        delta = r.delta_type.name if hasattr(r.delta_type, "name") else str(r.delta_type)
        print(f"  {src} --{rel}--> {tgt}: {delta}")
        dual_results.append({
            "source": src, "target": tgt, "relation": rel,
            "verdict": delta,
            "zfc_says": r.zfc_says if hasattr(r, "zfc_says") else None,
            "cat_says": r.cat_says if hasattr(r, "cat_says") else None,
        })
except Exception as e:
    print(f"DualEngine: {e}")

# ========================================================
# OPTIONAL: Pipe through IntegratedDiscoveryPipeline
# ========================================================
pipeline_result = None
try:
    from discovery.pipeline import IntegratedDiscoveryPipeline

    print("\n=== INTEGRATED DISCOVERY PIPELINE ===")
    pipeline = IntegratedDiscoveryPipeline(category=cat)

    # Convert gaps to hole format
    holes = [
        {"source": str(g).split("->")[0].strip() if "->" in str(g) else str(g),
         "target": str(g).split("->")[1].strip() if "->" in str(g) else "",
         "type": "structural_gap"}
        for g in gaps[:20]
    ]

    # Convert dual results to conjecture format
    conj_for_pipeline = [
        {"source": d["source"], "target": d["target"], "relation": d["relation"]}
        for d in dual_results
    ]

    pipeline_result = pipeline.run(
        holes=holes,
        conjectures=conj_for_pipeline,
        cluster_objects=[c for c in concepts[:15]],
    )
    print(f"  Holes COG-verified: {pipeline_result.holes_cog_verified}")
    print(f"  Holes COG-rejected: {pipeline_result.holes_cog_rejected}")
    print(f"  OPTIMUS intermediates: {pipeline_result.optimus_intermediates_found}")
    print(f"  Conjectures AGREE: {pipeline_result.conjectures_agree}")
    print(f"  Conjectures HOLLOW: {pipeline_result.conjectures_hollow}")
except Exception as e:
    print(f"Pipeline: {e}")

# ========================================================
# SAVE RESULTS TO JSON
# ========================================================
output = {
    "meta": {
        "description": "Riehl STT Discovery Session Results",
        "date": "2026-05-19",
        "objects": len(cat.objects()),
        "morphisms": len(cat.morphisms()),
    },
    "gaps": [str(g) for g in gaps[:30]],
    "intermediates": intermediate_results,
    "cosmos": {
        "two_cells": len(two_cells),
        "fibrations": len(fibs),
        "yoneda_faithfulness": yoneda.faithfulness_score,
        "representables": len(yoneda.presheaf_objects),
    },
    "optimus_refine": {
        "steps": result.get("steps"),
        "synced_morphisms": result.get("synced_morphisms"),
        "improvements": result.get("improvements"),
    },
    "dual_engine": dual_results,
}

if pipeline_result:
    output["pipeline"] = {
        "holes_cog_verified": pipeline_result.holes_cog_verified,
        "holes_cog_rejected": pipeline_result.holes_cog_rejected,
        "optimus_intermediates": pipeline_result.optimus_intermediates_found,
        "conjectures_agree": pipeline_result.conjectures_agree,
        "conjectures_hollow": pipeline_result.conjectures_hollow,
        "conjectures_orphan": pipeline_result.conjectures_orphan,
        "conjectures_reject": pipeline_result.conjectures_reject,
    }

output_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "riehl_stt_results.json",
)

with open(output_path, "w") as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nResults saved to: {output_path}")

print("\n=== DISCOVERY SESSION COMPLETE ===")
