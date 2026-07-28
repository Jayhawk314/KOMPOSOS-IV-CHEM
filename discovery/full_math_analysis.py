#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Full Math Kernel Analysis - LeanDojo Corpus

This runs the complete topology, geometry, and spectral analysis
on 180K theorems and 645K dependencies from Lean/Mathlib.

Goal: Find the shape of mathematics itself.
"""

import sys
import json
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
from domains.mathematics.name_registry import NameRegistry

print("=" * 70)
print("  MATHEMATICS TOPOLOGY ANALYSIS")
print("  LeanDojo Corpus: 180K theorems, 645K dependencies")
print("=" * 70)

# =============================================================================
# STEP 1: Load the corpus
# =============================================================================
print("\n[1/5] Loading LeanDojo corpus...")
kernel = MathKernel(db_dir=":memory:")
ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
result = kernel.load_source("leandojo", ld_adapter)
print(f"      Loaded: {result['objects']} objects, {result['morphisms']} dependencies")

# =============================================================================
# STEP 2: Topology - Persistent Homology
# =============================================================================
print("\n[2/5] Running Persistent Homology (finding holes/loops)...")
print("      This finds gaps in mathematics - regions surrounded by theorems")
print("      but empty inside. These are potential unsolved problem clusters.")

try:
    topology = kernel.run_topology()
    for source, diagram in topology.items():
        betti = diagram.betti_numbers_at(1.0)
        print(f"\n      {source.upper()}:")
        print(f"        β₀ (connected components): {betti.get(0, 0)}")
        print(f"        β₁ (loops/holes):          {betti.get(1, 0)}")
        print(f"        β₂ (voids/cavities):       {betti.get(2, 0)}")
        
        if betti.get(1, 0) > 0:
            print(f"\n      ⚠ FOUND {betti.get(1, 0)} HOLES in theorem space")
            print("        These are regions where math is MISSING")
            print("        Potential unsolved conjectures live here")
except Exception as e:
    print(f"      Topology error: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# STEP 3: Geometry - Ricci Curvature
# =============================================================================
print("\n[3/5] Running Ricci Curvature (finding clusters vs bridges)...")
print("      Positive curvature = clusters (unification happening)")
print("      Negative curvature = bridges (divergence, knowledge spreading)")

try:
    geometry = kernel.run_geometry()
    for source, result in geometry.items():
        print(f"\n      {source.upper()}:")
        print(f"        Spherical regions (clusters):  {result.num_spherical}")
        print(f"        Hyperbolic regions (bridges):  {result.num_hyperbolic}")
        print(f"        Flat regions:                  {result.num_flat}")
        
        if result.num_hyperbolic > 0:
            print(f"\n      ⚠ FOUND {result.num_hyperbolic} BRIDGE regions")
            print("        These connect distant areas of mathematics")
            print("        High-value knowledge transfer points")
            
        if result.num_spherical > 0:
            print(f"\n      ✓ FOUND {result.num_spherical} CLUSTER regions")
            print("        These are unified, well-connected theorem groups")
            
except Exception as e:
    print(f"      Geometry error: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# STEP 4: Spectral Analysis
# =============================================================================
print("\n[4/5] Running Spectral Analysis (algebraic connectivity)...")
print("      Measures how hard it is to disconnect the theorem graph")

try:
    spectral = kernel.run_spectral()
    for source, info in spectral.items():
        alg_conn = info.get('algebraic_connectivity', 'N/A')
        print(f"\n      {source.upper()}:")
        print(f"        Algebraic connectivity: {alg_conn}")
        print(f"        Nodes: {info.get('num_nodes', 'N/A')}")
        print(f"        Edges: {info.get('num_edges', 'N/A')}")
        
        if isinstance(alg_conn, float):
            if alg_conn > 1.0:
                print(f"\n      ✓ HIGH connectivity - math is well-integrated")
            elif alg_conn > 0.1:
                print(f"      ~ MODERATE connectivity - some isolated clusters")
            else:
                print(f"      ⚠ LOW connectivity - math is fragmented")
                
except Exception as e:
    print(f"      Spectral error: {e}")

# =============================================================================
# STEP 5: Name Registry - Find Famous Theorems
# =============================================================================
print("\n[5/5] Searching Name Registry for famous theorems in corpus...")

registry = kernel.name_registry
print(f"      Registry size: {registry.size} canonical theorems")

# Search for some famous ones
famous = [
    "intermediate_value_theorem",
    "cauchy_schwarz_inequality", 
    "fundamental_theorem_of_calculus",
    "lagranges_theorem_groups",
    "yoneda_lemma",
]

print("\n      Looking for famous theorems:")
for name in famous:
    found = registry.lookup(name)
    if found:
        info = registry.get_info(name)
        leandojo_id = info.get('leandojo', 'N/A')
        field = info.get('field', 'unknown')
        print(f"        ✓ {name}: {leandojo_id} ({field})")
    else:
        print(f"        ? {name}: not in registry")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("  ANALYSIS COMPLETE")
print("=" * 70)

report = kernel.convergent_analysis()
print(f"""
  Corpus Statistics:
    Sources analyzed:     {report.sources_analyzed}
    Total objects:        {report.total_objects:,}
    Total morphisms:      {report.total_morphisms:,}
    
  Topological Features:
    Convergent holes:     {len(report.convergent_holes)}
    Convergent clusters:  {len(report.convergent_clusters)}
    Convergent bridges:   {len(report.convergent_bridges)}
""")

print("""
  What this means:
  
  • Holes (β₁ > 0)     = Gaps in mathematics, potential conjectures
  • Bridges (negative curvature) = Knowledge transfer points between domains
  • Clusters (positive curvature) = Unified theorem groups
  
  Next steps:
  • kernel.name_registry.search('topology') - find theorems by topic
  • kernel.anchor_proximity('theorem_name') - distance to anchor problems
  • kernel.find_structural_matches(plugin) - match external domains
""")

# Save results
output = {
    'statistics': {
        'objects': report.total_objects,
        'morphisms': report.total_morphisms,
        'sources': report.sources_analyzed,
    },
    'topology': 'computed',
    'geometry': 'computed', 
    'spectral': 'computed',
}

with open('math_topology_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print("  Results saved to: math_topology_results.json")
print("=" * 70)
