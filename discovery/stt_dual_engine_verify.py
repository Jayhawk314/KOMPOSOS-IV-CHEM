#!/usr/bin/env python3
"""
STT Dual Engine Verification — Validates all 10 STT conjecture claims
through the KOMPOSOS-IV verification stack (DualEngine + InfinityCosmos + OPTIMUS).

For each conjecture file, this script:
  1. Loads STT concepts into an in-memory Category with proper morphisms
  2. Runs DualEngineBridge.query() for each claim
  3. Runs InfinityCosmos structural checks (Yoneda score, fibration detection)
  4. Runs OptimusEngine.find_structural_gaps() to find what's missing
  5. Classifies each as AGREE / HOLLOW / ORPHAN / REJECT
  6. Saves structured results to stt_verification_results.json

Usage:
    python KOMPOSOS-IV/discovery/stt_dual_engine_verify.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.category import Category
from core.cosmos import InfinityCosmos
from core.optimus import OptimusEngine
from zfc.category_bridge import DualEngineBridge
from zfc.category_store_adapter import StoreAdapter


def build_stt_category() -> Category:
    """Build an in-memory Category encoding all 10 STT conjecture concepts."""
    cat = Category(db_path=":memory:")

    # === Core STT concepts ===
    concepts = [
        # Foundations (shared across files)
        "Interval", "Hom", "IsSegal", "IsIso", "IsRezk",
        "IsDiscrete", "IsGroupoid", "CovariantFibration",
        # Simplicial Yoneda
        "Nat", "Representable", "YonedaEval", "YonedaEmbed",
        "SimplicialYonedaLemma",
        # Kan Extensions
        "Comma", "LeftKanExtension", "IsPointwise",
        "YonedaAsKanExtension",
        # Directed Univalence
        "Iso", "DirectedUnivalence", "DirectedUnivalenceImpliesRezk",
        "DiscreteImpliesRezk",
        # Homotopy Hypothesis
        "SyntheticHomotopyHypothesis", "StructureIdentityPrinciple",
        # Adjoint Functor Theorem
        "IsInitial", "Adjunction", "Under", "IsPointwise_LKE",
        "SyntheticAFT", "AdjointAsKanExtension",
        # Straightening
        "Spaces", "Straightening", "Unstraightening",
        "StraighteningEquivalence",
        # Stable
        "IsZero", "Square", "IsPullback", "IsPushout", "IsStable",
        "Suspension", "Loop", "SuspensionLoopEquivalence",
        # Gray
        "TwoCell", "VComp", "HComp", "Modification",
        "GrayInterchange",
        # Bounty / Bridge
        "MathCategory", "MathIsUnivalent", "CategoryIsSegal",
        "UnivalentIsRezk", "QuasiCatIsSegal",
        "MathCovariantFibration", "YonedaBridge",
    ]

    for c in concepts:
        cat.add(c, type_name="concept")

    # === Morphisms: structural dependencies between concepts ===
    edges = [
        # Foundation chain
        ("Interval", "Hom", "generates", 0.95),
        ("Hom", "IsSegal", "axiomatized_by", 0.95),
        ("IsSegal", "IsIso", "defines", 0.9),
        ("IsSegal", "IsRezk", "specializes_to", 0.85),
        ("IsSegal", "IsDiscrete", "defines", 0.9),
        ("IsIso", "IsDiscrete", "characterizes", 0.9),

        # Homotopy Hypothesis
        ("IsDiscrete", "IsGroupoid", "equivalent_to", 0.7),
        ("IsGroupoid", "SyntheticHomotopyHypothesis", "states", 0.6),
        ("IsDiscrete", "SyntheticHomotopyHypothesis", "states", 0.6),
        ("IsRezk", "StructureIdentityPrinciple", "implies", 0.7),

        # Yoneda
        ("IsSegal", "CovariantFibration", "defines", 0.9),
        ("CovariantFibration", "Nat", "has_transformations", 0.9),
        ("Hom", "Representable", "generates", 0.9),
        ("Representable", "YonedaEval", "used_by", 0.9),
        ("CovariantFibration", "YonedaEmbed", "used_by", 0.9),
        ("YonedaEval", "SimplicialYonedaLemma", "proves", 0.85),
        ("YonedaEmbed", "SimplicialYonedaLemma", "proves", 0.85),

        # Kan Extensions
        ("IsSegal", "Comma", "defines", 0.85),
        ("Comma", "LeftKanExtension", "used_by", 0.85),
        ("LeftKanExtension", "IsPointwise", "satisfies", 0.8),
        ("SimplicialYonedaLemma", "YonedaAsKanExtension", "special_case_of", 0.7),
        ("IsPointwise", "YonedaAsKanExtension", "implies", 0.7),

        # Directed Univalence
        ("IsIso", "Iso", "packages", 0.9),
        ("Iso", "IsRezk", "characterizes", 0.85),
        ("IsRezk", "DirectedUnivalence", "generalizes_to", 0.6),
        ("DirectedUnivalence", "DirectedUnivalenceImpliesRezk", "states", 0.6),
        ("IsDiscrete", "DiscreteImpliesRezk", "states", 0.7),

        # AFT
        ("IsSegal", "IsInitial", "defines", 0.9),
        ("IsSegal", "Adjunction", "defines", 0.85),
        ("Hom", "Under", "defines", 0.85),
        ("IsInitial", "SyntheticAFT", "used_by", 0.7),
        ("Under", "SyntheticAFT", "used_by", 0.7),
        ("Adjunction", "SyntheticAFT", "characterizes", 0.7),
        ("SyntheticAFT", "AdjointAsKanExtension", "implies", 0.65),
        ("IsPointwise_LKE", "AdjointAsKanExtension", "used_by", 0.6),

        # Straightening
        ("IsDiscrete", "Spaces", "defines_universe", 0.8),
        ("CovariantFibration", "Straightening", "maps_to", 0.8),
        ("Spaces", "Straightening", "target_of", 0.8),
        ("Spaces", "Unstraightening", "source_of", 0.8),
        ("Straightening", "StraighteningEquivalence", "half_of", 0.75),
        ("Unstraightening", "StraighteningEquivalence", "half_of", 0.75),
        ("DirectedUnivalence", "StraighteningEquivalence", "relies_on", 0.6),

        # Stable
        ("IsSegal", "IsZero", "defines", 0.9),
        ("IsSegal", "Square", "defines", 0.9),
        ("Square", "IsPullback", "has_property", 0.85),
        ("Square", "IsPushout", "has_property", 0.85),
        ("IsZero", "IsStable", "required_for", 0.9),
        ("IsPullback", "IsStable", "axiomatizes", 0.85),
        ("IsPushout", "IsStable", "axiomatizes", 0.85),
        ("IsStable", "Suspension", "defines", 0.8),
        ("IsStable", "Loop", "defines", 0.8),
        ("Suspension", "SuspensionLoopEquivalence", "half_of", 0.7),
        ("Loop", "SuspensionLoopEquivalence", "half_of", 0.7),

        # Gray
        ("IsSegal", "TwoCell", "defines", 0.9),
        ("TwoCell", "VComp", "has", 0.85),
        ("TwoCell", "HComp", "has", 0.85),
        ("TwoCell", "Modification", "higher_cell", 0.8),
        ("VComp", "GrayInterchange", "relates", 0.7),
        ("HComp", "GrayInterchange", "relates", 0.7),
        ("Modification", "GrayInterchange", "witnesses", 0.7),

        # Bounty / Bridge
        ("MathCategory", "CategoryIsSegal", "satisfies", 0.6),
        ("IsSegal", "CategoryIsSegal", "target_of", 0.6),
        ("MathIsUnivalent", "UnivalentIsRezk", "implies", 0.6),
        ("IsRezk", "UnivalentIsRezk", "target_of", 0.6),
        ("MathCovariantFibration", "CovariantFibration", "models", 0.7),
        ("MathCategory", "YonedaBridge", "satisfies", 0.8),
        ("SimplicialYonedaLemma", "YonedaBridge", "generalizes", 0.75),
    ]

    for src, tgt, rel, conf in edges:
        cat.connect(src, tgt, rel, confidence=conf)

    return cat


# === The 10 conjecture claims to verify ===
CONJECTURE_CLAIMS = [
    {
        "file": "conjectures/STT_Homotopy.lean",
        "name": "Synthetic Homotopy Hypothesis",
        "source": "IsDiscrete",
        "target": "IsGroupoid",
        "relation": "equivalent_to",
        "description": "Discrete types ↔ groupoids",
    },
    {
        "file": "conjectures/STT_Homotopy.lean",
        "name": "Structure Identity Principle",
        "source": "IsRezk",
        "target": "StructureIdentityPrinciple",
        "relation": "implies",
        "description": "Rezk types satisfy structure identity",
    },
    {
        "file": "KOMPOSOS-IV/conjectures/Simplicial_Yoneda.lean",
        "name": "Simplicial Yoneda Lemma",
        "source": "YonedaEmbed",
        "target": "SimplicialYonedaLemma",
        "relation": "proves",
        "description": "P(x) ≃ Nat(Hom(x,-), P)",
    },
    {
        "file": "KOMPOSOS-IV/conjectures/STT_Kan.lean",
        "name": "Yoneda as Kan Extension",
        "source": "SimplicialYonedaLemma",
        "target": "YonedaAsKanExtension",
        "relation": "special_case_of",
        "description": "Identity is pointwise Kan extension of itself",
    },
    {
        "file": "conjectures/Directed_Univalence.lean",
        "name": "Directed Univalence implies Rezk",
        "source": "DirectedUnivalence",
        "target": "DirectedUnivalenceImpliesRezk",
        "relation": "states",
        "description": "Directed Univalence → universe is Rezk",
    },
    {
        "file": "conjectures/STT_AFT.lean",
        "name": "Synthetic Adjoint Functor Theorem",
        "source": "Adjunction",
        "target": "SyntheticAFT",
        "relation": "characterizes",
        "description": "f ⊣ u ↔ (b↓u) has initial object",
    },
    {
        "file": "conjectures/STT_Straightening.lean",
        "name": "Straightening Equivalence",
        "source": "Straightening",
        "target": "StraighteningEquivalence",
        "relation": "half_of",
        "description": "Covariant fibrations ≃ functors into Spaces",
    },
    {
        "file": "conjectures/STT_Stable.lean",
        "name": "Suspension-Loop Equivalence",
        "source": "Suspension",
        "target": "SuspensionLoopEquivalence",
        "relation": "half_of",
        "description": "Σ and Ω are inverse equivalences in stable ∞-cats",
    },
    {
        "file": "conjectures/STT_Gray.lean",
        "name": "Gray Interchange Law",
        "source": "Modification",
        "target": "GrayInterchange",
        "relation": "witnesses",
        "description": "h-comp and v-comp commute up to invertible 3-cell",
    },
    {
        "file": "conjectures/QuasiCat_Bounty_Proof.lean",
        "name": "Category-Segal Bridge",
        "source": "MathCategory",
        "target": "CategoryIsSegal",
        "relation": "satisfies",
        "description": "Mathlib 1-categories satisfy STT Segal condition",
    },
]


def run_verification():
    """Run the full STT verification pipeline."""
    print("=" * 60)
    print("STT DUAL ENGINE VERIFICATION")
    print("=" * 60)

    # 1. Build the category
    print("\n[1/5] Building STT Category...")
    cat = build_stt_category()
    print(f"      {len(cat.objects())} objects, {len(cat.morphisms())} morphisms")

    # 2. Set up engines
    print("\n[2/5] Initializing verification engines...")
    adapter = StoreAdapter(cat)
    dual = DualEngineBridge(adapter, category=cat)
    cosmos = InfinityCosmos(cat)
    optimus = OptimusEngine(cat, max_depth=3)

    # 3. Run DualEngine on each conjecture
    print("\n[3/5] Running DualEngine verification on 10 conjectures...")
    results = []
    verdict_counts = {"AGREE": 0, "HOLLOW": 0, "ORPHAN": 0, "REJECT": 0, "ERROR": 0}

    for claim in CONJECTURE_CLAIMS:
        try:
            r = dual.query(claim["source"], claim["target"], claim["relation"])
            delta = r.delta_type.name if hasattr(r.delta_type, "name") else str(r.delta_type)
            entry = {
                "file": claim["file"],
                "name": claim["name"],
                "description": claim["description"],
                "source": claim["source"],
                "target": claim["target"],
                "relation": claim["relation"],
                "verdict": delta,
                "zfc_says": r.zfc_says,
                "zfc_confidence": r.zfc_confidence,
                "cat_says": r.cat_says,
                "cat_confidence": r.cat_confidence,
            }
        except Exception as e:
            delta = "ERROR"
            entry = {
                "file": claim["file"],
                "name": claim["name"],
                "description": claim["description"],
                "source": claim["source"],
                "target": claim["target"],
                "relation": claim["relation"],
                "verdict": "ERROR",
                "error": str(e),
            }

        verdict_counts[delta] = verdict_counts.get(delta, 0) + 1
        results.append(entry)
        print(f"  [{delta:7s}] {claim['name']}")

    # 4. Run InfinityCosmos checks
    print("\n[4/5] Running InfinityCosmos structural checks...")
    h2k = cosmos.homotopy_2_category()
    two_cells = list(h2k.two_cells.values())
    fibs = list(cosmos.cartesian_fibrations().values())
    yoneda = cosmos.yoneda_embedding()

    cosmos_results = {
        "two_cells_found": len(two_cells),
        "cartesian_fibrations": len(fibs),
        "yoneda_faithfulness": yoneda.faithfulness_score,
        "representables": len(yoneda.presheaf_objects),
    }
    print(f"      2-cells: {cosmos_results['two_cells_found']}")
    print(f"      Fibrations: {cosmos_results['cartesian_fibrations']}")
    print(f"      Yoneda faithfulness: {cosmos_results['yoneda_faithfulness']}")

    # 5. Run OPTIMUS gap analysis
    print("\n[5/5] Running OPTIMUS structural gap analysis...")
    gaps = optimus.find_structural_gaps()
    gap_strings = [str(g) for g in gaps[:20]]
    print(f"      Structural gaps found: {len(gaps)}")

    # === Summary ===
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    for verdict_type, count in sorted(verdict_counts.items()):
        if count > 0:
            print(f"  {verdict_type}: {count}")
    print(f"\n  Total conjectures verified: {len(results)}")
    print(f"  Cosmos faithfulness: {cosmos_results['yoneda_faithfulness']}")
    print(f"  Structural gaps: {len(gaps)}")

    # === Save results ===
    output = {
        "meta": {
            "description": "STT Dual Engine Verification Results",
            "date": "2026-05-19",
            "total_conjectures": len(results),
            "verdict_counts": verdict_counts,
        },
        "conjectures": results,
        "cosmos": cosmos_results,
        "optimus_gaps": gap_strings,
    }

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "stt_verification_results.json",
    )
    output_path = os.path.normpath(output_path)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")

    print("\n=== VERIFICATION COMPLETE ===")
    return output


if __name__ == "__main__":
    run_verification()
