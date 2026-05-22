#!/usr/bin/env python3
"""Run geometry analysis and save results."""

from domains.mathematics.kernel import MathKernel
from domains.mathematics.leandojo_adapter import LeanDojoAdapter
import json

print('Loading LeanDojo (this takes ~30s)...')
kernel = MathKernel(db_dir=':memory:')
ld_adapter = LeanDojoAdapter('data_sources/leandojo/leandojo_benchmark_4')
kernel.load_source('leandojo', ld_adapter)
print('Loaded.')

print('Running Ricci curvature geometry...')
geom = kernel.run_geometry()

results = {}
for src, result in geom.items():
    results[src] = {
        'num_spherical': result.num_spherical,
        'num_hyperbolic': result.num_hyperbolic,
        'num_flat': result.num_flat,
    }
    print(f'\n{src.upper()}:')
    print(f'  Clusters (spherical):    {result.num_spherical}')
    print(f'  Bridges (hyperbolic):    {result.num_hyperbolic}')
    print(f'  Flat regions:            {result.num_flat}')

with open('geometry_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\nResults saved to geometry_results.json')
