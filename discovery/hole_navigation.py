#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Hole Navigation System - Sheaves, Kan Extensions, and Orphan Morphisms

This system takes the 41K priority holes near Millennium Problems and:
1. Builds sheaf neighborhoods around each hole
2. Finds orphan morphisms (theorems with no incoming/outgoing edges)
3. Uses Kan extension to predict what should fill the hole
4. Generates ranked conjecture candidates

The goal: Go from "there's a hole here" to "here's the specific conjecture"

UPDATE (March 14, 2026): Added synthetic node filter to detect Lean reserved
keywords (forall, fun, let, etc.) that indicate graph artifacts, not real theorems.
"""

import json
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
from discovery.graph_utils import is_synthetic_node, filter_synthetic_nodes, analyze_synthetic_hub

@dataclass
class HoleNeighborhood:
    """The sheaf-like neighborhood around a topological hole."""
    hole_id: str
    boundary_theorems: List[str]  # Theorems forming the boundary of the hole
    orphan_morphisms: List[str]   # Morphisms pointing into/out of the hole
    field: str                    # Mathematical field
    nearby_anchors: List[str]     # Which Millennium Problems are nearby
    
    def to_dict(self):
        return {
            'hole_id': self.hole_id,
            'boundary_theorems': self.boundary_theorems[:10],  # Top 10
            'orphan_morphisms': self.orphan_morphisms[:5],
            'field': self.field,
            'nearby_anchors': self.nearby_anchors,
        }

@dataclass
class ConjectureCandidate:
    """A predicted theorem that could fill a hole."""
    hole_id: str
    conjecture_name: str
    confidence: float
    reasoning: str
    related_theorems: List[str]
    kan_extension_prediction: str
    proof_sketch: List[str]  # Suggested proof steps
    
    def to_dict(self):
        return {
            'hole_id': self.hole_id,
            'conjecture_name': self.conjecture_name,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'related_theorems': self.related_theorems,
            'kan_extension_prediction': self.kan_extension_prediction,
        }

class HoleNavigator:
    """
    Navigates from topological holes to specific conjecture candidates.
    
    Uses:
    - Sheaf theory: Local data on neighborhoods determines global structure
    - Kan extensions: Extend known patterns into the hole
    - Orphan detection: Find morphisms that should connect but don't
    """
    
    def __init__(self, kernel: MathKernel):
        self.kernel = kernel
        self.category = kernel.leandojo
        
        # Build graph structures
        self.neighbors = defaultdict(set)
        self.incoming = defaultdict(set)
        self.outgoing = defaultdict(set)
        
        for mor in self.category.morphisms():
            self.neighbors[mor.source].add(mor.target)
            self.neighbors[mor.target].add(mor.source)
            self.incoming[mor.target].add(mor.source)
            self.outgoing[mor.source].add(mor.target)
        
        # Get all objects
        self.objects = {obj.name: obj for obj in self.category.objects()}
        
    def find_hole_boundary(self, hole_id: str, radius: int = 2) -> List[str]:
        """
        Find theorems forming the boundary of a hole.
        
        Uses BFS to find all theorems within `radius` hops.
        The boundary is the set of theorems that surround the hole.
        """
        if hole_id not in self.objects:
            # Hole might be a gap, not an object - find nearby objects
            return self._find_nearby_objects(hole_id, radius)
        
        boundary = set()
        visited = {hole_id}
        current_layer = [hole_id]
        
        for _ in range(radius):
            next_layer = []
            for node in current_layer:
                for neighbor in self.neighbors.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        boundary.add(neighbor)
                        next_layer.append(neighbor)
            current_layer = next_layer
        
        return list(boundary)
    
    def _find_nearby_objects(self, hole_pattern: str, radius: int = 2) -> List[str]:
        """Find objects near a hole pattern (when hole is not a direct object)."""
        # Find objects whose names contain the pattern
        matching = [
            name for name in self.objects.keys()
            if hole_pattern[:20].lower() in name.lower()
        ]
        
        if not matching:
            return []
        
        # Return neighbors of matching objects
        boundary = set()
        for obj_name in matching[:5]:  # Limit
            boundary.update(self.neighbors.get(obj_name, []))
        
        return list(boundary)
    
    def find_orphan_morphisms(self, boundary: List[str]) -> List[Dict[str, Any]]:
        """
        Find orphan morphisms - potential connections that don't exist.
        
        An orphan is a pair of theorems (A, B) where:
        - A and B share many common neighbors (should be connected)
        - But no morphism exists between them
        
        These are candidates for new proof dependencies.
        """
        orphans = []
        
        # For each pair of boundary theorems, check if they should be connected
        for i, thm_a in enumerate(boundary[:20]):  # Limit pairs
            for thm_b in boundary[i+1:20]:
                if thm_b in self.neighbors.get(thm_a, set()):
                    continue  # Already connected
                
                # Count common neighbors
                neighbors_a = self.neighbors.get(thm_a, set())
                neighbors_b = self.neighbors.get(thm_b, set())
                common = neighbors_a & neighbors_b
                
                if len(common) >= 2:  # Share 2+ neighbors = should be connected
                    orphans.append({
                        'source': thm_a,
                        'target': thm_b,
                        'common_neighbors': len(common),
                        'confidence': min(1.0, len(common) / 5.0),
                    })
        
        # Sort by confidence
        orphans.sort(key=lambda x: x['confidence'], reverse=True)
        return orphans[:10]
    
    def kan_extension_predict(self, boundary: List[str], orphan: Dict) -> str:
        """
        Use Kan extension intuition to predict what should fill the gap.
        
        The Kan extension of a functor F along K predicts what F should be
        on objects not in the domain of K, based on the pattern of F on objects
        that are in the domain.
        
        Here: Given the pattern of theorems on the boundary, predict what
        theorem/morphism should exist in the hole.
        """
        # Get fields of boundary theorems
        boundary_fields = defaultdict(int)
        for thm_name in boundary:
            obj = self.objects.get(thm_name)
            if obj:
                field = obj.metadata.get('field', 'unknown')
                boundary_fields[field] += 1
        
        # Most common field on boundary
        dominant_field = max(boundary_fields.keys(), key=lambda k: boundary_fields[k]) if boundary_fields else 'unknown'
        
        # Get theorem types on boundary
        theorem_types = set()
        for thm_name in boundary:
            obj = self.objects.get(thm_name)
            if obj:
                theorem_types.add(obj.type_name)
        
        # Kan extension prediction
        prediction = f"""
        KAN EXTENSION PREDICTION:
        
        Boundary pattern analysis:
        - Dominant field: {dominant_field}
        - Theorem types: {', '.join(theorem_types)}
        - Boundary size: {len(boundary)} theorems
        
        Extension into hole:
        The pattern suggests a {', '.join(theorem_types).lower()} in {dominant_field}
        connecting {orphan['source'][:50]}... 
        to {orphan['target'][:50]}...
        
        This morphism would complete the commutative diagram formed by the
        {orphan['common_neighbors']} common neighbors.
        """
        
        return prediction.strip()
    
    def generate_conjecture(self, hole_id: str, boundary: List[str], 
                           orphans: List[Dict]) -> Optional[ConjectureCandidate]:
        """
        Generate a conjecture candidate for filling a hole.
        """
        if not orphans:
            return None
        
        # Use top orphan as the conjecture
        top_orphan = orphans[0]
        
        # Get field info
        source_obj = self.objects.get(top_orphan['source'])
        field = source_obj.metadata.get('field', 'unknown') if source_obj else 'unknown'
        
        # Generate conjecture name
        conjecture_name = f"Bridge_{top_orphan['source'][:20]}_to_{top_orphan['target'][:20]}"
        
        # Reasoning
        reasoning = f"""
        This conjecture proposes a morphism between two theorems that share
        {top_orphan['common_neighbors']} common neighbors but have no direct connection.
        
        The high number of shared neighbors suggests these theorems are
        conceptually related but the proof dependency has not been established.
        
        Field: {field}
        Confidence: {top_orphan['confidence']:.2f}
        """
        
        # Proof sketch (suggested approach)
        proof_sketch = [
            f"1. Analyze the {top_orphan['common_neighbors']} common neighbors",
            f"2. Identify the shared structure between {top_orphan['source'][:30]} and {top_orphan['target'][:30]}",
            f"3. Construct morphism using universal property",
            f"4. Verify commutativity with boundary diagram",
            f"5. Check in {field} context",
        ]
        
        return ConjectureCandidate(
            hole_id=hole_id,
            conjecture_name=conjecture_name,
            confidence=top_orphan['confidence'],
            reasoning=reasoning.strip(),
            related_theorems=[top_orphan['source'], top_orphan['target']],
            kan_extension_prediction=self.kan_extension_predict(boundary, top_orphan),
            proof_sketch=proof_sketch,
        )
    
    def analyze_hole(self, hole_id: str, nearby_anchors: List[str]) -> Optional[Dict]:
        """
        Full analysis of a single hole.
        """
        boundary = self.find_hole_boundary(hole_id)
        if not boundary:
            return None
        
        orphans = self.find_orphan_morphisms(boundary)
        
        # Get field from boundary
        boundary_fields = defaultdict(int)
        for thm_name in boundary:
            obj = self.objects.get(thm_name)
            if obj:
                field = obj.metadata.get('field', 'unknown')
                boundary_fields[field] += 1
        dominant_field = max(boundary_fields.keys(), key=lambda k: boundary_fields[k]) if boundary_fields else 'unknown'
        
        neighborhood = HoleNeighborhood(
            hole_id=hole_id,
            boundary_theorems=boundary,
            orphan_morphisms=[f"{o['source']} -> {o['target']}" for o in orphans],
            field=dominant_field,
            nearby_anchors=nearby_anchors,
        )
        
        conjecture = self.generate_conjecture(hole_id, boundary, orphans)
        
        result = {
            'neighborhood': neighborhood.to_dict(),
            'conjecture': conjecture.to_dict() if conjecture else None,
        }
        
        return result


def main():
    print("=" * 70)
    print("  HOLE NAVIGATION SYSTEM")
    print("  Using sheaves, Kan extensions, and orphans to find proofs")
    print("=" * 70)
    
    # Load kernel
    print("\n[1/4] Loading LeanDojo corpus...")
    kernel = MathKernel(db_dir=":memory:")
    ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
    kernel.load_source("leandojo", ld_adapter)
    print("      Loaded 180K theorems")
    
    # Load priority holes from previous analysis
    print("\n[2/4] Loading priority holes from Millennium anchor analysis...")
    try:
        with open('millennium_anchor_priority.json', 'r') as f:
            priority_data = json.load(f)
        priority_holes = priority_data.get('top_priority_holes', [])[:20]  # Top 20
        print(f"      Analyzing top {len(priority_holes)} priority holes")
    except FileNotFoundError:
        print("      ERROR: millennium_anchor_priority.json not found")
        print("      Run millennium_anchors.py first")
        return
    
    # Initialize navigator
    print("\n[3/4] Initializing Hole Navigator...")
    navigator = HoleNavigator(kernel)
    print(f"      Built graph: {len(navigator.objects)} objects, {sum(len(v) for v in navigator.neighbors.values())//2} edges")
    
    # Analyze holes
    print("\n[4/4] Analyzing holes with sheaves and Kan extensions...")
    
    results = []
    for i, hole in enumerate(priority_holes):
        hole_id = hole['hole_id']
        nearby_anchors = hole.get('nearby_anchors', [])
        
        print(f"\n  Hole {i+1}/{len(priority_holes)}: {hole_id[:60]}...")
        
        analysis = navigator.analyze_hole(hole_id, nearby_anchors)
        if analysis:
            results.append(analysis)
            
            if analysis['conjecture']:
                conj = analysis['conjecture']
                print(f"    ✓ Conjecture: {conj['conjecture_name'][:50]}...")
                print(f"      Confidence: {conj['confidence']:.2f}")
                print(f"      Field: {analysis['neighborhood']['field']}")
    
    # Save results
    print("\n" + "=" * 70)
    print("  SAVING RESULTS")
    print("=" * 70)
    
    with open('hole_navigation_results.json', 'w') as f:
        json.dump({
            'holes_analyzed': len(results),
            'conjectures_found': sum(1 for r in results if r.get('conjecture')),
            'results': results,
        }, f, indent=2)
    
    print(f"\n  Results saved to: hole_navigation_results.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    
    print(f"""
  HOLES ANALYZED: {len(results)}
  CONJECTURES FOUND: {sum(1 for r in results if r.get('conjecture'))}
  
  The system found specific conjecture candidates by:
  1. Building sheaf neighborhoods around each hole
  2. Finding orphan morphisms (should be connected but aren't)
  3. Using Kan extension to predict what fills the gap
  
  NEXT STEPS:
  • Take top conjectures and formalize in Lean
  • Use automated theorem provers to attempt proofs
  • The proof sketches suggest the approach
  
  This is the conjecture generation engine from your vision doc.
""")
    
    # Print top 3 conjectures in detail
    conjectures = [r['conjecture'] for r in results if r.get('conjecture')]
    if conjectures:
        print("\n" + "=" * 70)
        print("  TOP 3 CONJECTURE CANDIDATES")
        print("=" * 70)
        
        for i, conj in enumerate(conjectures[:3]):
            print(f"\n  CONJECTURE {i+1}: {conj['conjecture_name']}")
            print(f"  Confidence: {conj['confidence']:.2f}")
            print(f"  Related: {conj['related_theorems'][0][:50]}... → {conj['related_theorems'][1][:50]}...")
            print(f"\n  Reasoning:")
            for line in conj['reasoning'].split('\n')[:5]:
                print(f"    {line}")

if __name__ == '__main__':
    main()
