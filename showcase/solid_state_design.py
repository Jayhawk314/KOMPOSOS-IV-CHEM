# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Solid-State Battery Multi-Domain Design Comparison.

Compares 4+ solid-state cell designs across battery, ceramic, polymer,
and metal domains using the multi-domain analyzer. Includes synthesis
planning for solid electrolytes.

Usage:
    python -m showcase.solid_state_design
"""

import json
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cross_bridge.multi_domain import (
    MultiDomainAnalyzer,
    MultiDomainQuery,
    MultiDomainComponent,
)
from synthesis_planner.route_planner import SynthesisPlanner

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

# Define 4 solid-state cell designs to compare
CELL_DESIGNS = [
    MultiDomainQuery(
        name="Design A: NMC811 + LLZO + PEO + Cu",
        components=[
            MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
            MultiDomainComponent(name='LLZO', role='solid_electrolyte', domain='ceramic'),
            MultiDomainComponent(name='PEO', role='interlayer', domain='polymer'),
            MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
        ],
        electrolyte='LLZO',
    ),
    MultiDomainQuery(
        name="Design B: LFP + LLZO + PEO + Cu",
        components=[
            MultiDomainComponent(name='LFP', role='cathode', domain='battery'),
            MultiDomainComponent(name='LLZO', role='solid_electrolyte', domain='ceramic'),
            MultiDomainComponent(name='PEO', role='interlayer', domain='polymer'),
            MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
        ],
        electrolyte='LLZO',
    ),
    MultiDomainQuery(
        name="Design C: NMC811 + LGPS + PVDF + Al",
        components=[
            MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
            MultiDomainComponent(name='LGPS', role='solid_electrolyte', domain='battery'),
            MultiDomainComponent(name='PVDF', role='binder', domain='polymer'),
            MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
        ],
        electrolyte='LGPS',
    ),
    MultiDomainQuery(
        name="Design D: LFP + Li3PS4 + PEO + Cu",
        components=[
            MultiDomainComponent(name='LFP', role='cathode', domain='battery'),
            MultiDomainComponent(name='Li3PS4', role='solid_electrolyte', domain='battery'),
            MultiDomainComponent(name='PEO', role='interlayer', domain='polymer'),
            MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
        ],
        electrolyte='Li3PS4',
    ),
]

# Solid electrolytes to synthesize
SOLID_ELECTROLYTE_TARGETS = ['LLZO', 'LGPS', 'Li3PS4']


def run_design_comparison():
    """Analyze all cell designs and compare."""
    analyzer = MultiDomainAnalyzer()
    designs = []

    for query in CELL_DESIGNS:
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
            'interfaces': {
                f"{s.component_a}<->{s.component_b}": {
                    'functor': s.functor_used,
                    'score': round(s.score, 3),
                    'compatible': s.compatible,
                }
                for s in analysis.cross_domain_scores
            },
            'warnings': analysis.warnings,
        })

    return designs


def run_synthesis_comparison():
    """Plan synthesis for each solid electrolyte and compare."""
    planner = SynthesisPlanner()
    synthesis_results = []

    for target in SOLID_ELECTROLYTE_TARGETS:
        try:
            analysis = planner.plan_synthesis(target)
            for route in analysis.routes:
                synthesis_results.append({
                    'target': target,
                    'route_name': route.route.name,
                    'feasibility': round(route.feasibility_score, 3),
                    'cost_score': round(route.cost_score, 3),
                    'time_score': round(route.time_score, 3),
                    'safety_score': round(route.safety_score, 3),
                    'composite': round(route.composite_score, 3),
                    'precursor_cost_usd': round(analysis.precursor_cost_usd, 2),
                    'total_time_hours': round(analysis.total_time_hours, 1),
                    'equipment': ', '.join(analysis.equipment_needed),
                    'bottleneck_step': (
                        route.bottleneck_step.operation if route.bottleneck_step else None
                    ),
                })
        except Exception as exc:
            synthesis_results.append({
                'target': target,
                'route_name': 'ERROR',
                'error': str(exc),
            })

    return synthesis_results


def save_results(designs, synthesis):
    """Save results to JSON and CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Designs JSON
    json_path = os.path.join(OUTPUT_DIR, 'solid_state_designs.json')
    output = {
        'designs': designs,
        'ranking': sorted(
            [{'name': d['name'], 'score': d['overall_score'], 'viable': d['viable']}
             for d in designs],
            key=lambda x: x['score'],
            reverse=True,
        ),
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    # Synthesis CSV
    csv_path = os.path.join(OUTPUT_DIR, 'solid_state_synthesis.csv')
    if synthesis:
        fieldnames = [
            'target', 'route_name', 'feasibility', 'cost_score',
            'time_score', 'safety_score', 'composite',
            'precursor_cost_usd', 'total_time_hours', 'equipment',
            'bottleneck_step',
        ]
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(synthesis)

    return json_path, csv_path


def main():
    print("=" * 60)
    print("KOMPOSOS Solid-State Battery Design Comparison")
    print("=" * 60)
    print()

    designs = run_design_comparison()
    synthesis = run_synthesis_comparison()
    json_path, csv_path = save_results(designs, synthesis)

    # Print design comparison
    print("Cell Design Rankings:")
    ranked = sorted(designs, key=lambda d: d['overall_score'], reverse=True)
    for i, d in enumerate(ranked, 1):
        status = "VIABLE" if d['viable'] else "NOT VIABLE"
        print(f"  {i}. {d['name']}")
        print(f"     Score: {d['overall_score']:.4f}  [{status}]")
        if d['bottleneck']:
            print(f"     Bottleneck: {d['bottleneck']}")
        if d['warnings']:
            for w in d['warnings'][:2]:
                print(f"     Warning: {w}")
        print()

    # Print synthesis comparison
    print("Solid Electrolyte Synthesis Comparison:")
    for s in synthesis:
        if 'error' not in s:
            print(f"  {s['target']} via {s['route_name']}: "
                  f"composite={s['composite']:.3f}, "
                  f"cost=${s['precursor_cost_usd']:.2f}/g, "
                  f"time={s['total_time_hours']:.0f}h, "
                  f"safety={s['safety_score']:.3f}")

    print()
    print(f"JSON saved: {json_path}")
    print(f"CSV saved: {csv_path}")


if __name__ == '__main__':
    main()
