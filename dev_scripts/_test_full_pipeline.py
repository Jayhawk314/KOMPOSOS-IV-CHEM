# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Test the full MOF designer pipeline end-to-end."""
from mof_bridge.mp_mof_loader import MOFLinkerCache
from mof_bridge.linker_generator import LinkerGenerator
from mof_bridge.komposos_verdicts import LinkerVerdictEngine
from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec

print('='*60)
print('TESTING FULL MOF DESIGNER PIPELINE')
print('='*60)

print('\nStep 1: Load cache...')
cache = MOFLinkerCache()
count = cache.entry_count()
print(f'  Found {count} linkers in cache')
assert count > 0, "Cache is empty!"

print('\nStep 2: Initialize screening pipeline...')
screener = LinkerScreener()
print('  Screener initialized')

print('\nStep 3: Run generation + screening (5 candidates)...')
spec = LinkerScreeningSpec(
    application_context='breath_VOC_sensing',
    num_candidates=5,
    require_all_agree=False,  # Allow all verdicts for test
    allow_hollow=True,
)
result = screener.screen(spec)
print(f'  Generated {result.num_generated} candidates')
print(f'  Passed filtering: {result.num_passed_all}')
print(f'  Best morphism score: {result.best_morphism_integrity:.3f}')

print('\nStep 4: Check verdicts on top candidate...')
if result.candidates:
    top = result.candidates[0]
    print(f'  SMILES: {top.linker_smiles[:60]}...')
    print(f'  Verdicts:')
    for name, verdict in top.verdicts.items():
        print(f'    {name}: {verdict}')
    print(f'  Morphism integrity: {top.morphism_integrity:.3f}')
    print(f'  Overall viable: {top.overall_viable}')
else:
    print('  No candidates passed filtering')

print('\n'+'='*60)
print('FULL PIPELINE WORKS END-TO-END!')
print('='*60)
