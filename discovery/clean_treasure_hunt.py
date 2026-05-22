#!/usr/bin/env python3
"""
Clean Treasure Hunt — With Synthetic Node Filter

Re-runs the treasure hunt analysis with the reserved keyword filter applied.
This filters out graph artifacts (forall, fun, let, etc.) and shows only
real theorem candidates.
"""

import json
from collections import defaultdict
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
from discovery.graph_utils import is_synthetic_node, filter_synthetic_nodes, analyze_synthetic_hub

print("=" * 70)
print("  CLEAN TREASURE HUNT — With Synthetic Node Filter")
print("=" * 70)

print("""
  This analysis filters out Lean reserved keyword artifacts:
  • forall, fun, let, have, match, do, if, then, else...
  
  These indicate proof pattern fingerprints, not real theorems.
  
  After filtering, we examine the orphan pairs — those are the
  real conjecture candidates.
""")

# Load kernel
print("\n[1/4] Loading LeanDojo corpus...")
kernel = MathKernel(db_dir=":memory:")
ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
kernel.load_source("leandojo", ld_adapter)
print("      Loaded 180K theorems")

# Build graph
print("\n[2/4] Building neighborhood graph...")
category = kernel.leandojo
neighbors = defaultdict(set)
for mor in category.morphisms():
    neighbors[mor.source].add(mor.target)
    neighbors[mor.target].add(mor.source)

objects = {obj.name: obj for obj in category.objects()}
print(f"      Built graph: {len(objects)} objects")

# Load priority holes
print("\n[3/4] Loading priority holes and filtering...")
with open('millennium_anchor_priority.json', 'r') as f:
    priority_data = json.load(f)

top_holes = priority_data['top_priority_holes'][:20]

# Filter synthetic nodes
real_holes = []
synthetic_holes = []
synthetic_hubs = {}

for hole in top_holes:
    hole_id = hole['hole_id']
    if is_synthetic_node(hole_id):
        synthetic_holes.append(hole)
        # Analyze the synthetic hub
        hole_neighbors = neighbors.get(hole_id, set())
        analysis = analyze_synthetic_hub(hole_id, hole_neighbors)
        synthetic_hubs[hole_id] = analysis
    else:
        real_holes.append(hole)

print(f"\n      Top 20 holes breakdown:")
print(f"        Real theorems: {len(real_holes)}")
print(f"        Synthetic artifacts: {len(synthetic_holes)}")

if synthetic_holes:
    print(f"\n      SYNTHETIC NODES FOUND:")
    for hole in synthetic_holes:
        hole_id = hole['hole_id']
        synth_type = hole_id.split('.')[-1].lower()
        print(f"        • {hole_id} (type: {synth_type})")
        print(f"          Real neighbors: {synthetic_hubs[hole_id]['real_neighbors']}")
        print(f"          Orphan pairs: {len(synthetic_hubs[hole_id]['orphan_pairs'])}")

# Analyze real holes
print("\n[4/4] Analyzing real hole candidates...")

real_results = []
for hole in real_holes[:10]:  # Top 10 real holes
    hole_id = hole['hole_id']
    obj = objects.get(hole_id)
    
    if not obj:
        continue
    
    hole_neighbors = neighbors.get(hole_id, set())
    
    # Field distribution
    field_counts = defaultdict(int)
    for n in hole_neighbors:
        n_obj = objects.get(n)
        if n_obj:
            field_counts[n_obj.metadata.get('field', 'unknown')] += 1
    
    # Treasure score
    treasure_score = 0
    if len(hole['nearby_anchors']) >= 7: treasure_score += 3
    elif len(hole['nearby_anchors']) >= 4: treasure_score += 2
    elif len(hole['nearby_anchors']) >= 1: treasure_score += 1
    
    if len(hole_neighbors) > 50: treasure_score += 2
    elif len(hole_neighbors) > 20: treasure_score += 1
    
    if len(field_counts) >= 5: treasure_score += 2
    elif len(field_counts) >= 3: treasure_score += 1
    
    real_results.append({
        'hole_id': hole_id,
        'field': obj.metadata.get('field', 'unknown'),
        'neighbors': len(hole_neighbors),
        'fields': len(field_counts),
        'score': treasure_score,
        'anchors': len(hole['nearby_anchors']),
    })

# Sort by score
real_results.sort(key=lambda x: x['score'], reverse=True)

print("\n" + "=" * 70)
print("  CLEAN TREASURE CANDIDATES (Real Theorems Only)")
print("=" * 70)

print("\n  TOP 10 REAL HOLES:")
print(f"  {'Rank':<5} {'Hole ID':<55} {'Score':<7} {'Neighbors':<10} {'Fields'}")
print("  " + "-" * 90)

for i, r in enumerate(real_results[:10]):
    hole_display = r['hole_id'][:53] + '..' if len(r['hole_id']) > 55 else r['hole_id']
    print(f"  {i+1:<5} {hole_display:<55} {r['score']:<7} {r['neighbors']:<10} {r['fields']}")

# Synthetic hub analysis
if synthetic_hubs:
    print("\n" + "=" * 70)
    print("  SYNTHETIC HUB ANALYSIS — Orphan Pairs as Conjectures")
    print("=" * 70)
    
    for hub_id, analysis in synthetic_hubs.items():
        print(f"\n  HUB: {hub_id}")
        print(f"  Type: {analysis['synthetic_type']}")
        print(f"  Real neighbors: {analysis['real_neighbors']}")
        print(f"  Orphan pairs: {len(analysis['orphan_pairs'])}")
        
        if analysis['orphan_pairs']:
            print(f"\n  TOP 5 ORPHAN PAIRS (real conjectures):")
            for i, pair in enumerate(analysis['orphan_pairs'][:5]):
                src = pair['source'][:40] + '..' if len(pair['source']) > 42 else pair['source']
                tgt = pair['target'][:40] + '..' if len(pair['target']) > 42 else pair['target']
                print(f"    {i+1}. {src} → {tgt}")

# Save results
results = {
    'summary': {
        'total_holes_examined': len(top_holes),
        'real_holes': len(real_holes),
        'synthetic_holes': len(synthetic_holes),
    },
    'real_candidates': real_results,
    'synthetic_hubs': {
        k: {
            'type': v['synthetic_type'],
            'real_neighbors': v['real_neighbors'],
            'orphan_pair_count': len(v['orphan_pairs']),
            'top_orphan_pairs': v['orphan_pairs'][:10],
        }
        for k, v in synthetic_hubs.items()
    },
}

with open('clean_treasure_hunt_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n  Results saved to: clean_treasure_hunt_results.json")

print("\n" + "=" * 70)
print("  RECOMMENDATIONS")
print("=" * 70)

if real_results:
    best_real = real_results[0]
    print(f"""
  BEST REAL CANDIDATE:
    #{best_real['hole_id']}
    Score: {best_real['score']}/7
    Neighbors: {best_real['neighbors']}
    Fields: {best_real['fields']}
  
  This is a genuine theorem candidate (not a synthetic artifact).
  Deep dive recommended.
""")

if synthetic_hubs:
    print("""
  SYNTHETIC HUBS:
  The orphan pairs from synthetic hubs are the real signal.
  Each orphan pair (A, B) means:
    • A and B share a proof pattern (both connect to synthetic node)
    • But A and B have no direct edge
    • A bridge theorem connecting A → B is likely missing from Mathlib
  
  Focus on orphan pairs with:
    • High common neighbor count
    • Cross-domain (different fields)
    • Near Millennium Problems
""")

print("=" * 70)
