#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Treasure Hunt: Analyze Top 20 Priority Holes

This script examines the top 20 holes from the Millennium anchor analysis
and identifies which ones are most likely to contain "treasure" —
genuinely new, true, and interesting mathematical conjectures.
"""

import json
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter

print("=" * 70)
print("  TREASURE HUNT: TOP 20 PRIORITY HOLES")
print("=" * 70)

# Load kernel
print("\n[1/3] Loading LeanDojo corpus...")
kernel = MathKernel(db_dir=":memory:")
ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
kernel.load_source("leandojo", ld_adapter)
print("      Loaded 180K theorems")

# Load priority holes
print("\n[2/3] Loading priority holes...")
with open('millennium_anchor_priority.json', 'r') as f:
    priority_data = json.load(f)

top_holes = priority_data['top_priority_holes'][:20]
print(f"      Analyzing top {len(top_holes)} holes")

# Build neighbor graph for analysis
print("\n[3/3] Building neighborhood graph...")
from collections import defaultdict
neighbors = defaultdict(set)
for mor in kernel.leandojo.morphisms():
    neighbors[mor.source].add(mor.target)
    neighbors[mor.target].add(mor.source)

objects = {obj.name: obj for obj in kernel.leandojo.objects()}
print(f"      Built graph: {len(objects)} objects, {sum(len(v) for v in neighbors.values())//2} edges")

# Analyze each hole
print("\n" + "=" * 70)
print("  TOP 20 HOLES — TREASURE ANALYSIS")
print("=" * 70)

# Group by field for pattern detection
field_counts = defaultdict(list)
anchor_patterns = defaultdict(list)

for i, hole in enumerate(top_holes):
    hole_id = hole['hole_id']
    score = hole['priority_score']
    anchors = hole['nearby_anchors']
    
    # Find the object in corpus
    obj = objects.get(hole_id)
    field = obj.metadata.get('field', 'unknown') if obj else 'unknown'
    type_name = obj.type_name if obj else 'unknown'
    
    # Get neighborhood info
    neighbor_count = len(neighbors.get(hole_id, set()))
    
    # Collect for analysis
    field_counts[field].append(hole_id)
    
    # Anchor pattern (which Millennium problems it's near)
    anchor_key = tuple(sorted(anchors))
    anchor_patterns[anchor_key].append(hole_id)
    
    # Treasure indicators
    treasure_score = 0
    indicators = []
    
    # Indicator 1: Many anchors nearby (important region)
    if len(anchors) >= 7:
        treasure_score += 3
        indicators.append("★★★ Near MANY Millennium Problems")
    elif len(anchors) >= 4:
        treasure_score += 2
        indicators.append("★★ Near several Millennium Problems")
    elif len(anchors) >= 1:
        treasure_score += 1
        indicators.append("★ Near Millennium Problem")
    
    # Indicator 2: High degree (structurally important)
    if neighbor_count > 50:
        treasure_score += 2
        indicators.append("★★ High connectivity (structurally important)")
    elif neighbor_count > 20:
        treasure_score += 1
        indicators.append("★ Moderate connectivity")
    
    # Indicator 3: Cross-field neighbors
    neighbor_fields = set()
    for n in list(neighbors.get(hole_id, set()))[:20]:
        n_obj = objects.get(n)
        if n_obj:
            neighbor_fields.add(n_obj.metadata.get('field', 'unknown'))
    
    if len(neighbor_fields) >= 5:
        treasure_score += 2
        indicators.append(f"★★ Cross-domain ({len(neighbor_fields)} fields)")
    elif len(neighbor_fields) >= 3:
        treasure_score += 1
        indicators.append(f"★ Some cross-domain ({len(neighbor_fields)} fields)")
    
    # Print analysis
    print(f"\n{'='*70}")
    print(f"  HOLE #{i+1}: {hole_id[:60]}{'...' if len(hole_id) > 60 else ''}")
    print(f"{'='*70}")
    print(f"  Priority Score: {score}")
    print(f"  Field: {field}")
    print(f"  Type: {type_name}")
    print(f"  Neighbors: {neighbor_count}")
    print(f"  Nearby Anchors ({len(anchors)}):")
    for anchor in anchors[:5]:
        print(f"    • {anchor}")
    if len(anchors) > 5:
        print(f"    • ... and {len(anchors) - 5} more")
    
    print(f"\n  TREASURE INDICATORS:")
    if indicators:
        for ind in indicators:
            print(f"    {ind}")
    else:
        print(f"    (no strong indicators)")
    
    print(f"\n  TREASURE SCORE: {'★' * treasure_score} ({treasure_score}/7)")
    
    if neighbor_fields:
        print(f"\n  NEIGHBOR FIELDS: {', '.join(sorted(neighbor_fields))}")

# Summary
print("\n" + "=" * 70)
print("  TREASURE HUNT SUMMARY")
print("=" * 70)

print("\n  BY FIELD:")
for field, holes in sorted(field_counts.items(), key=lambda x: -len(x[1])):
    print(f"    {field}: {len(holes)} holes")
    for h in holes[:3]:
        print(f"      • {h[:50]}...")

print("\n  BY ANCHOR PATTERN:")
for pattern, holes in sorted(anchor_patterns.items(), key=lambda x: -len(x[1]))[:5]:
    anchor_str = ', '.join(pattern[:3])
    if len(pattern) > 3:
        anchor_str += f" (+ {len(pattern)-3} more)"
    print(f"    Near [{anchor_str}]: {len(holes)} holes")

print("\n  TOP TREASURE CANDIDATES (score ≥ 5):")
top_treasure = []
for hole in top_holes:
    hole_id = hole['hole_id']
    obj = objects.get(hole_id)
    if not obj:
        continue
    field = obj.metadata.get('field', 'unknown')
    neighbor_count = len(neighbors.get(hole_id, set()))
    neighbor_fields = set()
    for n in list(neighbors.get(hole_id, set()))[:20]:
        n_obj = objects.get(n)
        if n_obj:
            neighbor_fields.add(n_obj.metadata.get('field', 'unknown'))
    
    score = 0
    if len(hole['nearby_anchors']) >= 7: score += 3
    elif len(hole['nearby_anchors']) >= 4: score += 2
    elif len(hole['nearby_anchors']) >= 1: score += 1
    
    if neighbor_count > 50: score += 2
    elif neighbor_count > 20: score += 1
    
    if len(neighbor_fields) >= 5: score += 2
    elif len(neighbor_fields) >= 3: score += 1
    
    if score >= 5:
        top_treasure.append((hole_id, score, field, len(neighbor_fields)))

for hole_id, score, field, nfields in sorted(top_treasure, key=lambda x: -x[1])[:10]:
    print(f"    ★×{score} {hole_id[:50]}... ({field}, {nfields} neighbor fields)")

print("\n" + "=" * 70)
print("  NEXT STEPS")
print("=" * 70)
print("""
  1. Pick top 3-5 treasure candidates (score ≥ 5)
  
  2. For each:
     a. Examine the neighborhood manually
     b. Ask: "What theorem should live here?"
     c. Generate conjecture using hole_navigation.py
     d. Try to prove in Lean
  
  3. If it proves easily → known math (but confirms system works)
     If it won't prove → potentially new!
  
  4. For promising ones:
     - Check Mathlib (is it already there?)
     - Check literature (has anyone stated this?)
     - Ask a mathematician (is this interesting?)
  
  The treasure is in the holes that:
  • Are near Millennium Problems (important)
  • Have many cross-domain neighbors (novel connection)
  • Won't prove easily (not already known)
""")

# Save analysis
with open('treasure_hunt_analysis.json', 'w') as f:
    json.dump({
        'top_holes': top_holes,
        'field_counts': {k: len(v) for k, v in field_counts.items()},
        'treasure_candidates': [
            {'hole_id': h, 'score': s, 'field': f, 'neighbor_fields': n}
            for h, s, f, n in top_treasure
        ]
    }, f, indent=2)

print("\n  Analysis saved to: treasure_hunt_analysis.json")
print("=" * 70)
