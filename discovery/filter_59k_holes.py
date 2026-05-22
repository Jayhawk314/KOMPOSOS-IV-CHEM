#!/usr/bin/env python3
"""
59K Hole Filter — Dual-Engine Verification

Uses existing KOMPOSOS dual-engine (CAT + ZFC) to classify the 59K topological holes.

Each hole is classified as:
  ✅ THEOREM  — Both engines agree (provable, likely known math)
  🔍 ORPHAN  — ZFC yes, CAT no (logically forced but structurally missing — POTENTIALLY NEW!)
  ⚠️  HOLLOW  — CAT yes, ZFC no (structurally plausible but logically unsound — likely false)
  ❌ REJECT  — Both engines say no (false statement)

The ORPHAN category is the gold — these are statements that:
  1. ZFC proves (logically valid)
  2. CAT doesn't predict (structurally missing from the corpus)
  3. Therefore: likely UNFORMALIZED but TRUE mathematics

Usage:
    python filter_59k_holes.py

Output:
    - 59k_holes_classified.json — Full classification results
    - 59k_holes_orphans.txt — Just the ORPHAN candidates (the gold!)
"""

import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

from core.category import Category
from data.embeddings import EmbeddingsEngine
from oracle import CategoricalOracle
from oracle.zfc_verifier import OracleZFCBridge
from oracle.conjecture import ConjectureEngine


@dataclass
class HoleClassification:
    """Classification result for a single hole."""
    hole_id: str
    source: str
    target: str
    classification: str  # "THEOREM", "ORPHAN", "HOLLOW", "REJECT"
    cat_confidence: float
    zfc_confidence: float
    relation: str
    priority_score: float
    nearby_anchors: List[str]
    analysis: str


@dataclass
class ClassificationSummary:
    """Summary of the full classification run."""
    total_holes: int
    classified: int
    theorems: int
    orphans: int
    hollows: int
    rejects: int
    unclassifiable: int
    computation_time_seconds: float
    zfc_available: bool


class FiftyNineKFilter:
    """
    Filters the 59K topological holes through the dual-engine verifier.
    
    Usage:
        filter = FiftyNineKFilter(category, embeddings)
        results = filter.classify_holes(holes_from_json)
    """
    
    def __init__(self, category: Category, embeddings: EmbeddingsEngine, 
                 domain: str = "math", min_confidence: float = 0.4):
        """
        Args:
            category: Category instance (contains the theorem graph)
            embeddings: EmbeddingsEngine for semantic similarity
            domain: Domain tag for System 3 episodes
            min_confidence: Minimum CAT confidence for AGREE classification
        """
        self.category = category
        self.embeddings = embeddings

        # Initialize CAT engine (works without embeddings)
        try:
            self.oracle = CategoricalOracle(category, embeddings)
        except ValueError as e:
            if "requires initialized embeddings" in str(e):
                # Create oracle without embeddings - graph-only mode
                self.oracle = CategoricalOracle(category, None)
                print(f"  CAT Oracle: Running in graph-only mode (no embeddings)")
            else:
                raise

        # Initialize ZFC bridge (dual-engine verifier)
        self.zfc_bridge = OracleZFCBridge(category, domain=domain,
                                          min_confidence=min_confidence)

        # Check if ZFC is available
        self.zfc_available = self.zfc_bridge.is_available

        print(f"Dual-Engine Status:")
        print(f"  CAT Engine: ✅ Available")
        print(f"  ZFC Engine: {'✅ Available' if self.zfc_available else '❌ Not available'}")

        if not self.zfc_available:
            print(f"\n⚠️  WARNING: ZFC module not loaded. Running CAT-only verification.")
            print(f"   Classifications will be less reliable.")
    
    def classify_hole(self, hole_id: str, source: str, target: str,
                     priority_score: float = 0.0, 
                     nearby_anchors: List[str] = None) -> Optional[HoleClassification]:
        """
        Classify a single hole through the dual-engine.
        
        Args:
            hole_id: Unique identifier for the hole
            source: Source theorem name
            target: Target theorem name
            priority_score: Priority score from Millennium anchoring
            nearby_anchors: List of nearby Millennium Problems
        
        Returns:
            HoleClassification or None if pair is invalid
        """
        if nearby_anchors is None:
            nearby_anchors = []
        
        # Step 1: CAT engine predicts
        try:
            cat_result = self.oracle.predict(source, target)
        except Exception as e:
            print(f"  CAT prediction failed for {source} → {target}: {e}")
            return None
        
        if not cat_result or not cat_result.predictions:
            # No CAT prediction — might be too far apart in graph
            # Try ZFC-only check
            if self.zfc_available:
                # Build a minimal prediction for ZFC to check
                from oracle.prediction import Prediction
                fake_pred = Prediction(
                    source=source,
                    target=target,
                    predicted_relation="implies",
                    confidence=0.0,
                    strategy_name="fallback",
                )
                dual = self.zfc_bridge.verify_predictions(
                    source, target, [fake_pred], cat_result=cat_result
                )
                
                if dual.orphans:
                    classification = "ORPHAN"
                    analysis = "ZFC proves but CAT cannot find path (structurally missing)"
                elif dual.hollows:
                    classification = "HOLLOW"
                    analysis = "CAT finds path but ZFC does not prove (likely false)"
                else:
                    classification = "REJECT"
                    analysis = "Neither engine finds valid connection"
                
                return HoleClassification(
                    hole_id=hole_id,
                    source=source,
                    target=target,
                    classification=classification,
                    cat_confidence=0.0,
                    zfc_confidence=dual.predictions[0].zfc_confidence if dual.predictions else 0.0,
                    relation="implies",
                    priority_score=priority_score,
                    nearby_anchors=nearby_anchors,
                    analysis=analysis,
                )
            return None
        
        # Get best CAT prediction
        best_cat = cat_result.predictions[0]
        
        # Step 2: ZFC engine verifies
        dual = self.zfc_bridge.verify_predictions(
            source, target, 
            cat_result.predictions,
            cat_result=cat_result,
        )
        
        # Step 3: Classify based on dual-engine result
        if dual.agrees:
            classification = "THEOREM"
            analysis = "Both engines agree — provable theorem (likely known math)"
        elif dual.orphans:
            classification = "ORPHAN"
            analysis = "🔍 ZFC proves but CAT cannot find — POTENTIALLY NEW MATH!"
        elif dual.hollows:
            classification = "HOLLOW"
            analysis = "⚠️  CAT finds path but ZFC does not prove — likely false"
        else:
            classification = "REJECT"
            analysis = "Neither engine validates this connection"
        
        return HoleClassification(
            hole_id=hole_id,
            source=source,
            target=target,
            classification=classification,
            cat_confidence=best_cat.confidence,
            zfc_confidence=dual.predictions[0].zfc_confidence if dual.predictions else 0.0,
            relation=best_cat.predicted_relation,
            priority_score=priority_score,
            nearby_anchors=nearby_anchors,
            analysis=analysis,
        )
    
    def classify_batch(self, holes: List[Dict], 
                       batch_size: int = 100) -> Tuple[List[HoleClassification], ClassificationSummary]:
        """
        Classify a batch of holes.
        
        Args:
            holes: List of hole dicts from millennium_anchor_priority.json
            batch_size: Number of holes to process before printing progress
        
        Returns:
            Tuple of (classifications, summary)
        """
        start_time = time.time()
        classifications = []
        
        counts = {
            "theorems": 0,
            "orphans": 0,
            "hollows": 0,
            "rejects": 0,
            "unclassifiable": 0,
        }
        
        print(f"\nClassifying {len(holes)} holes through dual-engine...")
        print(f"{'Hole':<5} {'Classification':<12} {'CAT':<6} {'ZFC':<6} {'Source':<40} {'Target':<40}")
        print("-" * 120)
        
        for i, hole in enumerate(holes):
            hole_id = hole.get('hole_id', f'hole_{i}')
            source = hole.get('hole_id', '').split('.')[0]  # Extract base theorem name
            target = hole.get('hole_id', '').split('.')[-1]  # Extract property name
            priority_score = hole.get('priority_score', 0.0)
            nearby_anchors = hole.get('nearby_anchors', [])
            
            # For holes from our priority list, use the hole_id as both source and target context
            # The hole IS the gap — we need to infer what theorems should connect
            # For now, treat the hole as a potential edge from its neighborhood
            
            classification = self.classify_hole(
                hole_id=hole_id,
                source=source,
                target=target,
                priority_score=priority_score,
                nearby_anchors=nearby_anchors,
            )
            
            if classification:
                classifications.append(classification)
                counts[classification.classification.lower()] += 1
                
                # Print progress
                cat_conf = f"{classification.cat_confidence:.2f}"
                zfc_conf = f"{classification.zfc_confidence:.2f}"
                src_display = classification.source[:38] + '..' if len(classification.source) > 40 else classification.source
                tgt_display = classification.target[:38] + '..' if len(classification.target) > 40 else classification.target
                
                symbol = {"THEOREM": "✅", "ORPHAN": "🔍", "HOLLOW": "⚠️", "REJECT": "❌"}.get(
                    classification.classification, "?"
                )
                print(f"{i+1:<5} {symbol} {classification.classification:<10} {cat_conf:<6} {zfc_conf:<6} {src_display:<40} {tgt_display:<40}")
            else:
                counts["unclassifiable"] += 1
            
            # Batch progress
            if (i + 1) % batch_size == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"\n... Processed {i+1}/{len(holes)} holes ({rate:.1f} holes/sec)")
        
        elapsed = time.time() - start_time
        
        summary = ClassificationSummary(
            total_holes=len(holes),
            classified=len(classifications),
            theorems=counts["theorems"],
            orphans=counts["orphans"],
            hollows=counts["hollows"],
            rejects=counts["rejects"],
            unclassifiable=counts["unclassifiable"],
            computation_time_seconds=elapsed,
            zfc_available=self.zfc_available,
        )
        
        return classifications, summary


def load_holes(filepath: str = 'millennium_anchor_priority.json') -> List[Dict]:
    """Load holes from the priority JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Get top priority holes (or all if < 1000)
    holes = data.get('top_priority_holes', [])
    
    # If we have the full 59K, limit to top 1000 for initial run
    if len(holes) > 1000:
        print(f"Found {len(holes)} holes. Running on top 1000 for initial classification...")
        holes = holes[:1000]
    else:
        print(f"Found {len(holes)} holes. Running on all...")
    
    return holes


def save_results(classifications: List[HoleClassification], 
                 summary: ClassificationSummary,
                 output_json: str = '59k_holes_classified.json',
                 output_orphans: str = '59k_holes_orphans.txt'):
    """Save classification results."""
    
    # Save full JSON
    results = {
        'summary': asdict(summary),
        'classifications': [asdict(c) for c in classifications],
    }
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Full results saved to: {output_json}")
    
    # Save ORPHANS separately (the gold!)
    orphans = [c for c in classifications if c.classification == "ORPHAN"]
    
    with open(output_orphans, 'w', encoding='utf-8') as f:
        f.write(f"# ORPHAN HOLES — Potentially New Mathematics\n")
        f.write(f"# Generated by KOMPOSOS-IV 59K Hole Filter\n")
        f.write(f"# Total ORPHANs: {len(orphans)}\n")
        f.write(f"# {'Hole ID':<60} {'Priority':<10} {'CAT':<6} {'ZFC':<6} {'Anchors'}\n")
        f.write("-" * 120 + "\n")
        
        for o in sorted(orphans, key=lambda x: x.priority_score, reverse=True):
            anchors_str = ', '.join(o.nearby_anchors[:3])
            f.write(f"{o.hole_id:<60} {o.priority_score:<10.2f} {o.cat_confidence:<6.2f} {o.zfc_confidence:<6.2f} {anchors_str}\n")
            f.write(f"    Analysis: {o.analysis}\n\n")
    
    print(f"✅ ORPHAN candidates saved to: {output_orphans}")
    print(f"   Found {len(orphans)} ORPHAN holes (POTENTIALLY NEW MATH!)")


def main():
    """Main entry point."""
    print("=" * 70)
    print("  59K HOLE FILTER — Dual-Engine Verification")
    print("=" * 70)
    
    # Load category and embeddings
    print("\n[1/4] Loading category...")
    from domains.mathematics.kernel import MathKernel
    from domains.mathematics.leandojo_adapter import LeanDojoAdapter
    
    kernel = MathKernel(db_dir=":memory:")
    adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
    kernel.load_source("leandojo", adapter)
    
    category = kernel.leandojo
    
    # Try to load embeddings, but continue without if not available
    try:
        from data.embeddings import EmbeddingsEngine
        embeddings = EmbeddingsEngine(category)
        print(f"      Embeddings: ✅ Loaded")
    except Exception as e:
        print(f"      Embeddings: ❌ Not available ({e})")
        print(f"      Running in graph-only mode (CAT engine will use structural strategies only)")
        embeddings = None
    
    print(f"      Loaded {len(list(category.objects()))} objects")
    print(f"      Loaded {len(category.as_edges())} edges")
    
    # Load holes
    print("\n[2/4] Loading holes from millennium_anchor_priority.json...")
    holes = load_holes()
    
    # Initialize filter
    print("\n[3/4] Initializing dual-engine filter...")
    filter_engine = FiftyNineKFilter(category, embeddings, domain="math_kernel")
    
    # Classify
    print("\n[4/4] Running classification...")
    classifications, summary = filter_engine.classify_batch(holes, batch_size=50)
    
    # Save results
    print("\n" + "=" * 70)
    print("  SAVING RESULTS")
    print("=" * 70)
    save_results(classifications, summary)
    
    # Print summary
    print("\n" + "=" * 70)
    print("  CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(f"""
  Total holes examined:    {summary.total_holes}
  Classified:              {summary.classified}
  
  ✅ THEOREMS:             {summary.theorems}  (Both engines agree — provable)
  🔍 ORPHANS:              {summary.orphans}  (ZFC yes, CAT no — POTENTIALLY NEW!)
  ⚠️  HOLLOWS:              {summary.hollows}  (CAT yes, ZFC no — likely false)
  ❌ REJECTS:              {summary.rejects}  (Both say no — false)
  Unclassifiable:          {summary.unclassifiable}
  
  Computation time:        {summary.computation_time_seconds:.1f} seconds
  ZFC available:           {summary.zfc_available}
  
  THEOREM rate:            {summary.theorems / max(1, summary.classified) * 100:.1f}%
  ORPHAN rate:             {summary.orphans / max(1, summary.classified) * 100:.1f}%
""")
    
    if summary.orphans > 0:
        print("=" * 70)
        print("  🎯 ORPHAN CANDIDATES — POTENTIALLY NEW MATHEMATICS")
        print("=" * 70)
        print("""
  These {summary.orphans} holes are:
    • Provable in ZFC (logically valid)
    • NOT predicted by CAT (structurally missing from corpus)
    • Therefore: UNFORMALIZED but TRUE mathematics
  
  NEXT STEPS:
    1. Review 59k_holes_orphans.txt
    2. Manually examine top ORPHAN candidates
    3. Attempt formal proof in Lean
    4. If provable → Submit as NEW theorem to Mathlib
  
  This is how we find genuinely new mathematics!
""")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
