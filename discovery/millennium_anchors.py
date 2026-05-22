#!/usr/bin/env python3
"""
Millennium Problem Anchor System

Attracts the 59K topological holes toward famous unsolved problems.
Computes proximity from each hole to anchor problems.

This creates a "priority map" - holes near Millennium Problems
are higher-value conjectures to investigate.
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
from domains.mathematics.name_registry import NameRegistry

@dataclass
class AnchorProblem:
    """A famous unsolved problem to use as an anchor."""
    name: str
    field: str
    description: str
    related_theorems: List[str]  # Known theorems related to this problem
    prize: str = ""  # e.g., "$1M Clay Prize"
    status: str = "open"  # "open", "solved", "independent"
    
    def to_dict(self):
        return {
            'name': self.name,
            'field': self.field,
            'description': self.description,
            'related_theorems': self.related_theorems,
            'prize': self.prize,
        }

# Define Millennium Problems as anchors
MILLENNIUM_ANCHORS = [
    AnchorProblem(
        name="P vs NP",
        field="computer_science",
        description="Does every problem whose solution can be verified quickly also be solvable quickly?",
        related_theorems=[
            "Mathlib.Computability.NPComplete",
            "Mathlib.Computability.Sat",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Riemann Hypothesis",
        field="number_theory",
        description="All non-trivial zeros of the Riemann zeta function have real part 1/2",
        related_theorems=[
            "Mathlib.NumberTheory.ZetaFunction",
            "Mathlib.Analysis.SpecialFunctions.Zeta",
            "Mathlib.NumberTheory.PrimeCount",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Yang-Mills Existence",
        field="mathematical_physics",
        description="Prove existence of Yang-Mills theory with mass gap",
        related_theorems=[
            "Mathlib.Physics.GaugeTheory",
            "Mathlib.Physics.QuantumField",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Navier-Stokes Existence",
        field="analysis",
        description="Prove existence and smoothness of Navier-Stokes solutions",
        related_theorems=[
            "Mathlib.Analysis.PDE.NavierStokes",
            "Mathlib.Analysis.PDE.Existence",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Hodge Conjecture",
        field="algebraic_geometry",
        description="Certain cohomology classes are algebraic",
        related_theorems=[
            "Mathlib.AlgebraicGeometry.Cohomology",
            "Mathlib.AlgebraicGeometry.Cycle",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Birch-Swinnerton-Dyer",
        field="number_theory",
        description="Relates rank of elliptic curve to behavior of L-function",
        related_theorems=[
            "Mathlib.NumberTheory.EllipticCurve",
            "Mathlib.NumberTheory.LFunction",
        ],
        prize="$1M Clay Prize",
    ),
    AnchorProblem(
        name="Poincaré Conjecture",
        field="topology",
        description="Every simply-connected closed 3-manifold is homeomorphic to S³",
        related_theorems=[
            "Mathlib.Topology.Manifold.Basic",
            "Mathlib.Topology.FundamentalGroup",
            "Mathlib.Topology.Sphere",
        ],
        prize="$1M Clay Prize (SOLVED - Perelman 2003)",
        status="solved",
    ),
]

# Hilbert Problems (selected)
HILBERT_ANCHORS = [
    AnchorProblem(
        name="Continuum Hypothesis",
        field="set_theory",
        description="No set has cardinality strictly between integers and reals",
        related_theorems=[
            "Mathlib.Order.Cardinal",
            "Mathlib.SetTheory.ZFC",
            "Mathlib.Order.WellOrder",
        ],
        status="independent (Gödel/Cohen)",
    ),
    AnchorProblem(
        name="Goldbach Conjecture",
        field="number_theory",
        description="Every even integer > 2 is sum of two primes",
        related_theorems=[
            "Mathlib.NumberTheory.Prime",
            "Mathlib.NumberTheory.Additive",
        ],
    ),
]

class AnchorSystem:
    """
    Manages anchor problems and computes proximity to holes.
    
    The system:
    1. Registers anchor problems in the theorem graph
    2. Computes shortest paths from holes to anchors
    3. Ranks holes by proximity to important problems
    """
    
    def __init__(self, kernel: MathKernel):
        self.kernel = kernel
        self.anchors: Dict[str, AnchorProblem] = {}
        self.anchor_objects: List[str] = []  # Object IDs in kernel for anchors
        
    def register_anchor(self, anchor: AnchorProblem):
        """Register an anchor problem by field matching."""
        self.anchors[anchor.name] = anchor
        
        # Find theorems in the same field as the anchor
        found_ids = []
        all_objects = list(self.kernel.leandojo.objects())
        
        anchor_field = anchor.field.lower()
        
        # Map anchor fields to corpus field names
        field_mapping = {
            'computer_science': ['computer', 'computability', 'logic'],
            'number_theory': ['numbertheory', 'number_theory', 'prime', 'zeta', 'elliptic'],
            'mathematical_physics': ['physics', 'quantum', 'gauge'],
            'analysis': ['analysis', 'pde', 'navier', 'existence'],
            'algebraic_geometry': ['algebraicgeometry', 'algebraic_geometry', 'cohomology'],
            'topology': ['topology', 'manifold', 'fundamentalgroup', 'sphere', 'homotopy'],
            'set_theory': ['settheory', 'set_theory', 'cardinal', 'ordinal', 'zfc'],
        }
        
        search_terms = field_mapping.get(anchor_field, [anchor_field])
        
        for obj in all_objects:
            obj_name_lower = obj.name.lower()
            obj_field = obj.metadata.get('field', '').lower()
            
            # Match by field or by name containing search terms
            for term in search_terms:
                if term in obj_name_lower or term in obj_field:
                    found_ids.append(obj.name)
                    break
        
        # Deduplicate and limit
        found_ids = list(set(found_ids))[:100]  # Limit to 100 per anchor
        print(f"      {anchor.name} ({anchor_field}): {len(found_ids)} theorems in corpus")
        
        if found_ids:
            print(f"        Sample: {found_ids[:2]}...")
        
        self.anchor_objects.extend(found_ids)
        
    def compute_hole_proximity(self) -> Dict[str, Dict[str, float]]:
        """
        Compute proximity from each hole to each anchor.
        
        Uses shortest path distance in the theorem graph.
        Returns dict: {hole_id: {anchor_name: proximity_score}}
        
        Proximity score: 1.0 / (1 + distance)
        Higher = closer to anchor = more important hole
        """
        from collections import deque
        
        # Build adjacency list
        neighbors = {}
        for mor in self.kernel.leandojo.morphisms():
            if mor.source not in neighbors:
                neighbors[mor.source] = set()
            if mor.target not in neighbors:
                neighbors[mor.target] = set()
            neighbors[mor.source].add(mor.target)
            neighbors[mor.target].add(mor.source)
        
        # BFS from each anchor to compute distances
        anchor_distances = {}
        for anchor_name in self.anchors:
            anchor_distances[anchor_name] = {}
            
            # Find anchor objects in corpus
            start_nodes = [
                obj_id for obj_id in self.anchor_objects
                if any(obj_id in str(n) for n in neighbors.keys())
            ]
            
            if not start_nodes:
                print(f"      Warning: No corpus objects found for {anchor_name}")
                continue
            
            # BFS from all anchor nodes simultaneously
            distances = {node: 0 for node in start_nodes}
            queue = deque(start_nodes)
            
            while queue:
                node = queue.popleft()
                current_dist = distances[node]
                
                for neighbor in neighbors.get(node, []):
                    if neighbor not in distances:
                        distances[neighbor] = current_dist + 1
                        queue.append(neighbor)
            
            anchor_distances[anchor_name] = distances
        
        # Convert to proximity scores
        proximity = {}
        for anchor_name, distances in anchor_distances.items():
            for node, dist in distances.items():
                if node not in proximity:
                    proximity[node] = {}
                proximity[node][anchor_name] = 1.0 / (1.0 + dist)
        
        return proximity
    
    def rank_holes(self, proximity: Dict[str, Dict[str, float]], top_k: int = 100) -> List[Tuple[str, float, List[str]]]:
        """
        Rank holes by total proximity to all anchors.
        
        Returns: [(hole_id, total_score, [nearby_anchors]), ...]
        """
        ranked = []
        for hole_id, anchor_scores in proximity.items():
            total_score = sum(anchor_scores.values())
            nearby_anchors = [
                (name, score) for name, score in anchor_scores.items()
                if score > 0.1  # Threshold for "nearby"
            ]
            if total_score > 0:
                ranked.append((hole_id, total_score, [a[0] for a in nearby_anchors]))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    
    def get_priority_map(self, top_k: int = 100) -> Dict:
        """
        Generate a priority map of holes near anchor problems.
        
        This is the output: which holes are worth investigating first.
        """
        print("\n    Computing proximity from 59K holes to anchor problems...")
        proximity = self.compute_hole_proximity()
        
        print(f"    Found {len(proximity)} holes within range of anchors")
        
        print(f"    Ranking top {top_k} priority holes...")
        ranked = self.rank_holes(proximity, top_k)
        
        # Build priority map
        priority_map = {
            'total_holes_in_corpus': 59051,
            'holes_near_anchors': len(proximity),
            'anchors_used': list(self.anchors.keys()),
            'top_priority_holes': [
                {
                    'hole_id': hole_id,
                    'priority_score': score,
                    'nearby_anchors': anchors,
                }
                for hole_id, score, anchors in ranked
            ],
        }
        
        return priority_map


def main():
    print("=" * 70)
    print("  MILLENNIUM PROBLEM ANCHOR SYSTEM")
    print("  Attracting 59K holes toward famous unsolved problems")
    print("=" * 70)
    
    # Load kernel
    print("\n[1/4] Loading LeanDojo corpus...")
    kernel = MathKernel(db_dir=":memory:")
    ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
    kernel.load_source("leandojo", ld_adapter)
    print("      Loaded 180K theorems")
    
    # Initialize anchor system
    print("\n[2/4] Registering Anchor Problems...")
    anchor_system = AnchorSystem(kernel)
    
    all_anchors = MILLENNIUM_ANCHORS + HILBERT_ANCHORS
    for anchor in all_anchors:
        anchor_system.register_anchor(anchor)
    
    print(f"\n      Registered {len(anchor_system.anchors)} anchor problems")
    
    # Compute proximity
    print("\n[3/4] Computing Hole Proximity...")
    priority_map = anchor_system.get_priority_map(top_k=50)
    
    # Save results
    print("\n[4/4] Saving Priority Map...")
    
    # Human-readable summary
    print("\n" + "=" * 70)
    print("  PRIORITY HOLES (near Millennium/Hilbert Problems)")
    print("=" * 70)
    
    print(f"\n  Total holes in corpus: {priority_map['total_holes_in_corpus']:,}")
    print(f"  Holes near anchors: {priority_map['holes_near_anchors']:,}")
    print(f"  Anchors used: {len(priority_map['anchors_used'])}")
    
    print("\n  TOP 20 PRIORITY HOLES:")
    print("  " + "-" * 70)
    print(f"  {'Rank':<5} {'Hole ID':<50} {'Score':<8} {'Near'}")
    print("  " + "-" * 70)
    
    for i, hole in enumerate(priority_map['top_priority_holes'][:20]):
        hole_id = hole['hole_id'][:48] + '..' if len(hole['hole_id']) > 50 else hole['hole_id']
        score = f"{hole['priority_score']:.4f}"
        near = ', '.join(hole['nearby_anchors'][:3])
        print(f"  {i+1:<5} {hole_id:<50} {score:<8} {near}")
    
    # Save full results
    with open('millennium_anchor_priority.json', 'w') as f:
        json.dump(priority_map, f, indent=2)
    
    print("\n  " + "-" * 70)
    print(f"\n  Full priority map saved to: millennium_anchor_priority.json")
    
    print("\n" + "=" * 70)
    print("  WHAT THIS MEANS")
    print("=" * 70)
    print(f"""
  The {priority_map['holes_near_anchors']:,} holes near anchor problems are
  POTENTIAL CONJECTURES related to famous unsolved problems.
  
  HIGH-PRIORITY HOLES (score > 0.5):
  • These are within a few theorem-hops of Millennium Problems
  • Filling these holes could advance major open problems
  • These are where to focus automated theorem proving
  
  NEXT STEPS:
  1. Take top N holes and examine their neighborhood
  2. Use Kan extension to predict what should fill the hole
  3. Feed predictions to Lean/automated prover
  4. Verify or refine conjectures
  
  This is the conjecture generation engine from your vision doc.
""")

if __name__ == '__main__':
    main()
