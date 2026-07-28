# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Cross-Domain Material Discovery: Systematic sweep across domain boundaries.

Runs all feasible cross-domain pairings (polymer-battery, metal-battery,
ceramic-metal), identifies surprising high/low scorers, and builds
multi-domain 3-4 component designs.

Usage:
    python -m showcase.cross_domain_discovery
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cross_bridge.battery_polymer import score_polymer_electrode_compatibility
from cross_bridge.battery_metal import score_collector_compatibility
from cross_bridge.ceramic_metal import score_coating_compatibility
from cross_bridge.multi_domain import (
    MultiDomainAnalyzer,
    MultiDomainQuery,
    MultiDomainComponent,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

# Materials to sweep for each cross-domain functor
BATTERY_POLYMERS_SWEEP = {
    'polymers': ['PVDF', 'PEO', 'CMC', 'PTFE', 'PAN', 'SBR', 'EPDM', 'PEEK'],
    'battery_materials': ['NMC811', 'LFP', 'LCO', 'Graphite', 'Si', 'LTO', 'LMO'],
}

BATTERY_METALS_SWEEP = {
    'metals': ['Al_foil', 'Cu_foil', 'Ni_foil', 'SS_304', 'Ti_pure'],
    'electrodes': ['NMC811', 'LFP', 'LCO', 'Graphite', 'Si', 'Li_metal'],
    'electrolytes': ['LiPF6', 'LiTFSI'],
}

CERAMIC_METALS_SWEEP = {
    'ceramics': ['Al2O3', 'ZrO2_YSZ', 'TiN', 'SiC', 'Si3N4', 'BN_hex'],
    'metals': ['SS_304', 'Ti6Al4V', 'Inconel_718', 'Al_6061', 'Cu_C11000'],
}

# Multi-domain designs to try
MULTI_DOMAIN_DESIGNS = [
    MultiDomainQuery(
        name="Full NMC811 cell: NMC811+PVDF+Al+LiPF6",
        components=[
            MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
            MultiDomainComponent(name='PVDF', role='binder', domain='polymer'),
            MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
        ],
        electrolyte='LiPF6',
    ),
    MultiDomainQuery(
        name="Eco LFP cell: LFP+CMC+Al",
        components=[
            MultiDomainComponent(name='LFP', role='cathode', domain='battery'),
            MultiDomainComponent(name='CMC', role='binder', domain='polymer'),
            MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
        ],
        electrolyte='LiPF6',
    ),
    MultiDomainQuery(
        name="Si anode cell: Si+PAN+Cu",
        components=[
            MultiDomainComponent(name='Si', role='anode', domain='battery'),
            MultiDomainComponent(name='PAN', role='binder', domain='polymer'),
            MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
        ],
        electrolyte='LiPF6',
    ),
    MultiDomainQuery(
        name="TBC: YSZ on Inconel 718",
        components=[
            MultiDomainComponent(name='ZrO2_YSZ', role='coating', domain='ceramic'),
            MultiDomainComponent(name='Inconel_718', role='substrate', domain='metal'),
        ],
    ),
    MultiDomainQuery(
        name="Ceramic-coated electrode: Al2O3+NMC811+Al",
        components=[
            MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
            MultiDomainComponent(name='Al2O3', role='coating', domain='ceramic'),
            MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
        ],
        electrolyte='LiPF6',
    ),
    MultiDomainQuery(
        name="PEO+LFP+Cu (solid polymer cell)",
        components=[
            MultiDomainComponent(name='PEO', role='electrolyte', domain='polymer'),
            MultiDomainComponent(name='LFP', role='cathode', domain='battery'),
            MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
        ],
        electrolyte='LiTFSI',
    ),
]


def run_cross_domain_sweep():
    """Run all cross-domain pairings."""
    results = []

    # Battery-Polymer sweep
    for poly in BATTERY_POLYMERS_SWEEP['polymers']:
        for bat in BATTERY_POLYMERS_SWEEP['battery_materials']:
            try:
                r = score_polymer_electrode_compatibility(poly, bat)
                results.append({
                    'functor': 'battery_polymer',
                    'material_a': poly,
                    'material_b': bat,
                    'score': round(r.score, 4),
                    'compatible': r.compatible,
                    'warnings': '; '.join(r.warnings) if r.warnings else '',
                })
            except Exception as exc:
                results.append({
                    'functor': 'battery_polymer',
                    'material_a': poly,
                    'material_b': bat,
                    'score': None,
                    'compatible': False,
                    'error': str(exc),
                })

    # Battery-Metal sweep
    for metal in BATTERY_METALS_SWEEP['metals']:
        for elec in BATTERY_METALS_SWEEP['electrodes']:
            for elyte in BATTERY_METALS_SWEEP['electrolytes']:
                try:
                    r = score_collector_compatibility(metal, elec, elyte)
                    results.append({
                        'functor': 'battery_metal',
                        'material_a': metal,
                        'material_b': f"{elec}+{elyte}",
                        'score': round(r.score, 4),
                        'compatible': r.compatible,
                        'warnings': '; '.join(r.warnings) if r.warnings else '',
                    })
                except Exception as exc:
                    results.append({
                        'functor': 'battery_metal',
                        'material_a': metal,
                        'material_b': f"{elec}+{elyte}",
                        'score': None,
                        'compatible': False,
                        'error': str(exc),
                    })

    # Ceramic-Metal sweep
    for cer in CERAMIC_METALS_SWEEP['ceramics']:
        for met in CERAMIC_METALS_SWEEP['metals']:
            try:
                r = score_coating_compatibility(cer, met)
                results.append({
                    'functor': 'ceramic_metal',
                    'material_a': cer,
                    'material_b': met,
                    'score': round(r.score, 4),
                    'compatible': r.compatible,
                    'warnings': '; '.join(r.warnings) if r.warnings else '',
                })
            except Exception as exc:
                results.append({
                    'functor': 'ceramic_metal',
                    'material_a': cer,
                    'material_b': met,
                    'score': None,
                    'compatible': False,
                    'error': str(exc),
                })

    return results


def find_surprises(results):
    """Identify surprisingly high and low scores."""
    scored = [r for r in results if r.get('score') is not None]
    if not scored:
        return [], []

    scored.sort(key=lambda r: r['score'], reverse=True)

    # Top 10 highest (potential surprises)
    top = scored[:10]
    # Bottom 10 lowest (potential warnings)
    bottom = scored[-10:]

    return top, bottom


def flag_unexpected_high(results, threshold=0.75):
    """
    Flag pairings that score above threshold but are NOT in any functor's
    KNOWN_GOOD_PAIRS list.  These are candidate discoveries worth
    experimental validation.
    """
    from cross_bridge.battery_metal import KNOWN_GOOD_PAIRS as BM_GOOD
    from cross_bridge.ceramic_metal import KNOWN_GOOD_PAIRS as CM_GOOD
    from cross_bridge.battery_polymer import KNOWN_GOOD_PAIRS as BP_GOOD

    known = set()
    for metal, electrode, _elyte in BM_GOOD:
        known.add((metal, electrode))
    for ceramic, metal in CM_GOOD:
        known.add((ceramic, metal))
    for polymer, bat_mat in BP_GOOD:
        known.add((polymer, bat_mat))

    unexpected = []
    for r in results:
        if r.get('score') is not None and r['score'] >= threshold:
            # Normalise material_b (battery_metal sweep stores "Graphite+LiPF6")
            mat_b = r['material_b'].split('+')[0]
            pair = (r['material_a'], mat_b)
            reverse_pair = (mat_b, r['material_a'])
            if pair not in known and reverse_pair not in known:
                r['flag'] = 'UNEXPECTED_HIGH'
                unexpected.append(r)

    unexpected.sort(key=lambda r: r['score'], reverse=True)
    return unexpected


def run_multi_domain_designs():
    """Run multi-domain design queries."""
    analyzer = MultiDomainAnalyzer()
    designs = []

    for query in MULTI_DOMAIN_DESIGNS:
        try:
            analysis = analyzer.analyze(query)
            designs.append({
                'name': analysis.query_name,
                'domains': analysis.domains_involved,
                'overall_score': round(analysis.overall_score, 4),
                'viable': analysis.viable,
                'bottleneck': (
                    f"{analysis.bottleneck.component_a}<->{analysis.bottleneck.component_b} "
                    f"({analysis.bottleneck.functor_used}: {analysis.bottleneck.score:.3f})"
                    if analysis.bottleneck else None
                ),
                'warnings': analysis.warnings,
                'interfaces': {
                    f"{s.component_a}<->{s.component_b}": {
                        'functor': s.functor_used,
                        'score': round(s.score, 3),
                        'compatible': s.compatible,
                    }
                    for s in analysis.cross_domain_scores
                },
            })
        except Exception as exc:
            designs.append({
                'name': query.name,
                'error': str(exc),
            })

    return designs


def save_results(cross_results, top_surprises, bottom_surprises, designs,
                  candidate_discoveries=None):
    """Save results to CSV and JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cross-domain pairings CSV
    csv_path = os.path.join(OUTPUT_DIR, 'cross_domain_surprises.csv')
    scored = [r for r in cross_results if r.get('score') is not None]
    scored.sort(key=lambda r: r['score'], reverse=True)
    fieldnames = ['functor', 'material_a', 'material_b', 'score', 'compatible',
                  'warnings', 'flag']
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(scored)

    # Multi-domain designs JSON
    json_path = os.path.join(OUTPUT_DIR, 'multi_domain_designs.json')
    output = {
        'total_cross_pairs': len(scored),
        'top_10_surprises': top_surprises,
        'bottom_10_warnings': bottom_surprises,
        'candidate_discoveries': candidate_discoveries or [],
        'multi_domain_designs': sorted(
            designs,
            key=lambda d: d.get('overall_score', 0),
            reverse=True,
        ),
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    return csv_path, json_path


def main():
    print("=" * 60)
    print("KOMPOSOS Cross-Domain Material Discovery")
    print("=" * 60)
    print()

    print("Running cross-domain sweep...")
    cross_results = run_cross_domain_sweep()
    scored = [r for r in cross_results if r.get('score') is not None]
    print(f"  {len(scored)} cross-domain pairings scored")
    print()

    top, bottom = find_surprises(cross_results)

    print("Top 10 highest-scoring cross-domain pairs:")
    for r in top:
        compat = "OK" if r['compatible'] else "CAUTION"
        print(f"  {r['material_a']:12s} + {r['material_b']:20s} "
              f"({r['functor']:15s}) = {r['score']:.4f} [{compat}]")
    print()

    # Flag candidate discoveries (high score + not in known pairs)
    discoveries = flag_unexpected_high(cross_results, threshold=0.75)
    if discoveries:
        print(f"Candidate Discoveries ({len(discoveries)} unexpected high scores):")
        for r in discoveries:
            print(f"  ** {r['material_a']:12s} + {r['material_b']:20s} "
                  f"({r['functor']:15s}) = {r['score']:.4f}")
        print()

    print("Bottom 10 lowest-scoring cross-domain pairs:")
    for r in bottom:
        compat = "OK" if r['compatible'] else "FAIL"
        print(f"  {r['material_a']:12s} + {r['material_b']:20s} "
              f"({r['functor']:15s}) = {r['score']:.4f} [{compat}]")
    print()

    print("Running multi-domain designs...")
    designs = run_multi_domain_designs()

    print("Multi-domain design rankings:")
    for d in sorted(designs, key=lambda x: x.get('overall_score', 0), reverse=True):
        if 'error' in d:
            print(f"  {d['name']}: ERROR - {d['error']}")
        else:
            status = "VIABLE" if d['viable'] else "NOT VIABLE"
            print(f"  {d['name']}")
            print(f"    Score: {d['overall_score']:.4f} [{status}]")
            if d['bottleneck']:
                print(f"    Bottleneck: {d['bottleneck']}")

    print()
    csv_path, json_path = save_results(cross_results, top, bottom, designs,
                                        candidate_discoveries=discoveries)
    print(f"CSV saved: {csv_path}")
    print(f"JSON saved: {json_path}")


if __name__ == '__main__':
    main()
