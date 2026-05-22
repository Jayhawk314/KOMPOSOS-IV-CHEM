#!/usr/bin/env python3
"""
KOMPOSOS Treasure Detector — Systematic Search Tool

Combs through the 59K holes looking for genuine Mathlib gaps.
Uses type-checking filter to eliminate broken statements.
Ranks candidates by "treasure potential."

Usage:
    python treasure_detector.py --limit 1000 --output treasure_candidates.json
"""

import json
import time
import argparse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from core.category import Category
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
from discovery.graph_utils import validate_conjecture_candidate, is_synthetic_node


@dataclass
class TreasureCandidate:
    """A hole that might contain genuine new math."""
    hole_id: str
    priority_score: float
    nearby_anchors: List[str]
    neighbor_count: int
    cross_domain_count: int
    field: str
    type_checks: bool
    is_synthetic: bool
    treasure_score: float  # Combined score
    analysis: str


def compute_treasure_score(
    priority_score: float,
    neighbor_count: int,
    cross_domain_count: int,
    type_checks: bool,
    is_synthetic: bool,
    nearby_anchors: List[str]
) -> float:
    """
    Compute a combined 'treasure score' for a hole.
    
    Higher = more likely to be genuine new math.
    
    Factors:
    - Type-checks: Must pass (otherwise 0)
    - Not synthetic: Must pass (otherwise 0)
    - Cross-domain: More fields = more novel
    - Neighbor count: More neighbors = more central
    - Millennium proximity: More anchors = more important
    """
    if is_synthetic or not type_checks:
        return 0.0
    
    score = 0.0
    
    # Cross-domain bonus (up to 3 points)
    score += min(3.0, cross_domain_count / 3.0)
    
    # Neighbor count bonus (up to 2 points)
    if neighbor_count > 50:
        score += 2.0
    elif neighbor_count > 20:
        score += 1.0
    elif neighbor_count > 10:
        score += 0.5
    
    # Millennium proximity bonus (up to 3 points)
    score += min(3.0, len(nearby_anchors) / 3.0)
    
    # Priority score bonus (up to 2 points)
    score += min(2.0, priority_score / 3.0)
    
    return score


def analyze_hole_treasure_potential(
    hole_id: str,
    category: Category,
    objects: Dict[str, object],
    neighbors: Dict[str, set],
    priority_score: float = 0.0,
    nearby_anchors: List[str] = None
) -> Optional[TreasureCandidate]:
    """
    Analyze a single hole for treasure potential.
    """
    if nearby_anchors is None:
        nearby_anchors = []
    
    # Check 1: Synthetic node filter
    is_synthetic = is_synthetic_node(hole_id)
    
    # Check 2: Type-checking filter
    # Generate a minimal statement to type-check
    statement = f"""
-- Conjecture: {hole_id}
theorem conjecture_{hole_id.replace('.', '_').replace(' ', '_')} : True := by trivial
"""
    validation = validate_conjecture_candidate(
        hole_id=hole_id,
        statement=statement,
        timeout=5
    )
    
    type_checks = validation['type_checks']
    
    # Get hole object info
    obj = objects.get(hole_id)
    if not obj:
        # Try partial match
        candidates = [name for name in objects.keys() if hole_id in name]
        if candidates:
            obj = objects[candidates[0]]
        else:
            return None
    
    field = obj.metadata.get('field', 'unknown')
    
    # Get neighbor info
    hole_neighbors = neighbors.get(hole_id, set())
    neighbor_count = len(hole_neighbors)
    
    # Count cross-domain neighbors
    neighbor_fields = set()
    for n in list(hole_neighbors)[:50]:
        n_obj = objects.get(n)
        if n_obj:
            neighbor_fields.add(n_obj.metadata.get('field', 'unknown'))
    
    cross_domain_count = len(neighbor_fields)
    
    # Compute treasure score
    treasure_score = compute_treasure_score(
        priority_score=priority_score,
        neighbor_count=neighbor_count,
        cross_domain_count=cross_domain_count,
        type_checks=type_checks,
        is_synthetic=is_synthetic,
        nearby_anchors=nearby_anchors
    )
    
    # Generate analysis
    if is_synthetic:
        analysis = f"SYNTHETIC NODE (reserved keyword)"
    elif not type_checks:
        analysis = f"TYPE ERROR: {validation['error_message'][:100]}"
    elif treasure_score >= 7.0:
        analysis = f"🎯 HIGH POTENTIAL: {cross_domain_count} fields, {neighbor_count} neighbors, {len(nearby_anchors)} anchors"
    elif treasure_score >= 4.0:
        analysis = f"⚠️  MEDIUM POTENTIAL: {cross_domain_count} fields, {neighbor_count} neighbors"
    else:
        analysis = f"LOW POTENTIAL: {cross_domain_count} fields, {neighbor_count} neighbors"
    
    return TreasureCandidate(
        hole_id=hole_id,
        priority_score=priority_score,
        nearby_anchors=nearby_anchors,
        neighbor_count=neighbor_count,
        cross_domain_count=cross_domain_count,
        field=field,
        type_checks=type_checks,
        is_synthetic=is_synthetic,
        treasure_score=treasure_score,
        analysis=analysis,
    )


def run_treasure_detection(
    holes: List[Dict],
    category: Category,
    limit: int = 1000,
    min_treasure_score: float = 5.0
) -> Tuple[List[TreasureCandidate], Dict]:
    """
    Run treasure detection on a list of holes.
    
    Returns:
        Tuple of (candidates, summary_stats)
    """
    start_time = time.time()
    
    # Build graph structures
    objects = {obj.name: obj for obj in category.objects()}
    neighbors = defaultdict(set)
    for mor in category.morphisms():
        neighbors[mor.source].add(mor.target)
        neighbors[mor.target].add(mor.source)
    
    print(f"Loaded {len(objects)} objects, {sum(len(v) for v in neighbors.values())//2} edges")
    
    # Analyze holes
    candidates = []
    stats = {
        'total': 0,
        'synthetic': 0,
        'type_error': 0,
        'low_potential': 0,
        'medium_potential': 0,
        'high_potential': 0,
    }
    
    print(f"\nAnalyzing {min(len(holes), limit)} holes...")
    print(f"{'Rank':<5} {'Score':<7} {'Fields':<7} {'Neighbors':<10} {'Hole ID':<60}")
    print("-" * 95)
    
    for i, hole in enumerate(holes[:limit]):
        hole_id = hole.get('hole_id', f'hole_{i}')
        priority_score = hole.get('priority_score', 0.0)
        nearby_anchors = hole.get('nearby_anchors', [])
        
        stats['total'] += 1
        
        candidate = analyze_hole_treasure_potential(
            hole_id=hole_id,
            category=category,
            objects=objects,
            neighbors=neighbors,
            priority_score=priority_score,
            nearby_anchors=nearby_anchors,
        )
        
        if candidate:
            candidates.append(candidate)
            
            # Update stats
            if candidate.is_synthetic:
                stats['synthetic'] += 1
            elif not candidate.type_checks:
                stats['type_error'] += 1
            elif candidate.treasure_score >= 7.0:
                stats['high_potential'] += 1
            elif candidate.treasure_score >= 4.0:
                stats['medium_potential'] += 1
            else:
                stats['low_potential'] += 1
            
            # Print progress (only show potential candidates)
            if candidate.treasure_score >= min_treasure_score:
                hole_display = hole_id[:58] + '..' if len(hole_id) > 60 else hole_id
                print(f"{i+1:<5} {candidate.treasure_score:<7.1f} {candidate.cross_domain_count:<7} {candidate.neighbor_count:<10} {hole_display:<60}")
        
        # Progress update
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"\n... Processed {i+1}/{min(len(holes), limit)} holes ({rate:.1f} holes/sec)")
    
    elapsed = time.time() - start_time
    
    summary = {
        'computation_time_seconds': elapsed,
        'holes_analyzed': stats['total'],
        'synthetic_nodes': stats['synthetic'],
        'type_errors': stats['type_error'],
        'low_potential': stats['low_potential'],
        'medium_potential': stats['medium_potential'],
        'high_potential': stats['high_potential'],
        'treasure_candidates_found': len([c for c in candidates if c.treasure_score >= min_treasure_score]),
    }
    
    # Sort by treasure score
    candidates.sort(key=lambda x: x.treasure_score, reverse=True)
    
    return candidates, summary


def load_holes(filepath: str = 'millennium_anchor_priority.json') -> List[Dict]:
    """Load holes from priority JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get('top_priority_holes', [])


def save_results(
    candidates: List[TreasureCandidate],
    summary: Dict,
    output_json: str = 'treasure_candidates.json'
):
    """Save treasure detection results."""
    results = {
        'summary': summary,
        'top_candidates': [asdict(c) for c in candidates[:50]],  # Top 50
        'all_candidates': [asdict(c) for c in candidates if c.treasure_score >= 5.0],
    }
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_json}")


def main():
    parser = argparse.ArgumentParser(description='KOMPOSOS Treasure Detector')
    parser.add_argument('--limit', type=int, default=1000, help='Max holes to analyze')
    parser.add_argument('--min-score', type=float, default=5.0, help='Minimum treasure score to report')
    parser.add_argument('--output', type=str, default='treasure_candidates.json', help='Output JSON file')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  KOMPOSOS TREASURE DETECTOR")
    print("  Systematic search for genuine Mathlib gaps")
    print("=" * 70)
    
    # Load category
    print("\n[1/3] Loading LeanDojo corpus...")
    kernel = MathKernel(db_dir=":memory:")
    adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
    kernel.load_source("leandojo", adapter)
    category = kernel.leandojo
    print(f"      Loaded {len(list(category.objects()))} objects")
    
    # Load holes
    print("\n[2/3] Loading holes from millennium_anchor_priority.json...")
    holes = load_holes()
    print(f"      Loaded {len(holes)} holes")
    
    # Run detection
    print("\n[3/3] Running treasure detection...")
    candidates, summary = run_treasure_detection(
        holes=holes,
        category=category,
        limit=args.limit,
        min_treasure_score=args.min_score,
    )
    
    # Save results
    print("\n" + "=" * 70)
    print("  SAVING RESULTS")
    print("=" * 70)
    save_results(candidates, summary, args.output)
    
    # Print summary
    print("\n" + "=" * 70)
    print("  TREASURE DETECTION SUMMARY")
    print("=" * 70)
    print(f"""
  Holes analyzed:        {summary['holes_analyzed']}
  Computation time:      {summary['computation_time_seconds']:.1f} seconds
  
  Synthetic nodes:       {summary['synthetic_nodes']} ({summary['synthetic_nodes']*100//max(1,summary['holes_analyzed'])}%)
  Type errors:           {summary['type_errors']} ({summary['type_errors']*100//max(1,summary['holes_analyzed'])}%)
  Low potential:         {summary['low_potential']}
  Medium potential:      {summary['medium_potential']}
  HIGH POTENTIAL:        {summary['high_potential']} ⭐
  
  Treasure candidates:   {summary['treasure_candidates_found']} (score ≥ {args.min_score})
""")
    
    if candidates and candidates[0].treasure_score >= args.min_score:
        print("=" * 70)
        print("  TOP 10 TREASURE CANDIDATES")
        print("=" * 70)
        print()
        for i, c in enumerate(candidates[:10]):
            print(f"  #{i+1}: {c.hole_id}")
            print(f"      Treasure Score: {c.treasure_score:.1f}")
            print(f"      Fields: {c.cross_domain_count}, Neighbors: {c.neighbor_count}")
            print(f"      Anchors: {', '.join(c.nearby_anchors[:3])}")
            print(f"      {c.analysis}")
            print()
        
        print("=" * 70)
        print("""
  NEXT STEPS:
  1. Review top candidates in treasure_candidates.json
  2. Manually verify high-potential holes
  3. Check Mathlib for existing formalization
  4. Formalize and prove genuine gaps
""")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
