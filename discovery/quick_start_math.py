#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Quick start: Math Kernel with LeanDojo only

This demonstrates the math kernel using just the LeanDojo corpus.
180K theorems, 645K dependencies - enough for serious topology analysis.
"""

import sys
from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter

print("=" * 60)
print("Math Kernel - LeanDojo Only")
print("=" * 60)

# Initialize kernel
print("\nInitializing kernel...")
kernel = MathKernel(db_dir=":memory:")

# Load LeanDojo (full corpus)
print("Loading LeanDojo corpus (this takes ~30 seconds)...")
ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
result = kernel.load_source("leandojo", ld_adapter)
print(f"Loaded: {result}")

# Statistics
print("\n" + "=" * 60)
print("Kernel Statistics")
print("=" * 60)
stats = kernel.statistics()
for source, counts in stats.items():
    print(f"  {source}: {counts}")

# Run topology analysis
print("\n" + "=" * 60)
print("Running Topology Analysis (Persistent Homology)")
print("=" * 60)
try:
    topology = kernel.run_topology()
    for source, diagram in topology.items():
        betti = diagram.betti_numbers_at(1.0)
        print(f"  {source}: Betti numbers = {betti}")
except Exception as e:
    print(f"  Topology error: {e}")

# Run geometry analysis
print("\n" + "=" * 60)
print("Running Geometry Analysis (Ollivier-Ricci Curvature)")
print("=" * 60)
try:
    geometry = kernel.run_geometry()
    for source, result in geometry.items():
        print(f"  {source}:")
        print(f"    Spherical (clusters): {result.num_spherical}")
        print(f"    Hyperbolic (bridges): {result.num_hyperbolic}")
        print(f"    Flat: {result.num_flat}")
except Exception as e:
    print(f"  Geometry error: {e}")

# Run spectral analysis
print("\n" + "=" * 60)
print("Running Spectral Analysis")
print("=" * 60)
try:
    spectral = kernel.run_spectral()
    for source, info in spectral.items():
        print(f"  {source}:")
        print(f"    Algebraic connectivity: {info.get('algebraic_connectivity', 'N/A')}")
        print(f"    Nodes: {info.get('num_nodes', 'N/A')}")
        print(f"    Edges: {info.get('num_edges', 'N/A')}")
except Exception as e:
    print(f"  Spectral error: {e}")

# Convergent analysis (single source = self-consistency)
print("\n" + "=" * 60)
print("Convergent Analysis Report")
print("=" * 60)
report = kernel.convergent_analysis()
print(f"  Sources analyzed: {report.sources_analyzed}")
print(f"  Total objects: {report.total_objects}")
print(f"  Total morphisms: {report.total_morphisms}")
print(f"  Convergent holes: {len(report.convergent_holes)}")
print(f"  Convergent clusters: {len(report.convergent_clusters)}")
print(f"  Convergent bridges: {len(report.convergent_bridges)}")

print("\n" + "=" * 60)
print("Done! The math kernel is ready.")
print("=" * 60)
print("\nNext steps:")
print("  - kernel.find_structural_matches(plugin) - match domains to math")
print("  - kernel.run_topology() - persistent homology")
print("  - kernel.run_geometry() - Ricci curvature")
print("  - kernel.name_registry.search('topology') - find theorems")
