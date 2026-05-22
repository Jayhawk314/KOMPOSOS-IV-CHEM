# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
"""
Synthesis Cost Comparison: Rank all synthesis routes by cost, time, safety.

Plans synthesis for every available target material, compares routes,
and identifies the cheapest/fastest/safest paths. Includes equipment
overlap analysis.

Usage:
    python -m showcase.synthesis_comparison
"""

import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthesis_planner.route_planner import SynthesisPlanner
from synthesis_planner.route_graph import list_all_targets, list_all_routes

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')


def run_all_targets():
    """Plan synthesis for every available target."""
    planner = SynthesisPlanner()
    targets = list_all_targets()
    all_routes = []
    target_summaries = []

    for target in targets:
        try:
            analysis = planner.plan_synthesis(target)
            best = analysis.best_route

            target_summaries.append({
                'target': target,
                'num_routes': len(analysis.routes),
                'best_route': best.route.name if best else None,
                'best_composite': round(best.composite_score, 3) if best else None,
                'precursor_cost_usd': round(analysis.precursor_cost_usd, 2),
                'total_time_hours': round(analysis.total_time_hours, 1),
                'equipment_needed': analysis.equipment_needed,
                'warnings': analysis.warnings,
            })

            for route in analysis.routes:
                all_routes.append({
                    'target': target,
                    'route_name': route.route.name,
                    'num_steps': len(route.route.steps),
                    'feasibility': round(route.feasibility_score, 3),
                    'cost_score': round(route.cost_score, 3),
                    'time_score': round(route.time_score, 3),
                    'safety_score': round(route.safety_score, 3),
                    'composite': round(route.composite_score, 3),
                    'bottleneck_step': (
                        route.bottleneck_step.operation if route.bottleneck_step else None
                    ),
                    'missing_precursors': ', '.join(route.missing_precursors) if route.missing_precursors else '',
                    'missing_equipment': ', '.join(route.missing_equipment) if route.missing_equipment else '',
                })
        except Exception as exc:
            target_summaries.append({
                'target': target,
                'num_routes': 0,
                'error': str(exc),
            })

    return all_routes, target_summaries


def analyze_equipment(all_routes, target_summaries):
    """Analyze equipment overlap -- which equipment serves the most routes?"""
    equipment_counter = Counter()
    equipment_targets = {}

    for summary in target_summaries:
        equip_list = summary.get('equipment_needed', [])
        for eq in equip_list:
            equipment_counter[eq] += 1
            if eq not in equipment_targets:
                equipment_targets[eq] = []
            equipment_targets[eq].append(summary['target'])

    return {
        'equipment_frequency': dict(equipment_counter.most_common()),
        'equipment_targets': {
            k: sorted(v) for k, v in equipment_targets.items()
        },
    }


def find_extremes(all_routes):
    """Find cheapest, fastest, safest routes."""
    scored = [r for r in all_routes if r.get('composite') is not None]
    if not scored:
        return {}

    return {
        'highest_composite': max(scored, key=lambda r: r['composite']),
        'lowest_composite': min(scored, key=lambda r: r['composite']),
        'highest_feasibility': max(scored, key=lambda r: r['feasibility']),
        'cheapest': max(scored, key=lambda r: r['cost_score']),
        'fastest': max(scored, key=lambda r: r['time_score']),
        'safest': max(scored, key=lambda r: r['safety_score']),
    }


def save_results(all_routes, target_summaries, equipment, extremes):
    """Save results to CSV and JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # All routes CSV
    csv_path = os.path.join(OUTPUT_DIR, 'synthesis_all_targets.csv')
    fieldnames = [
        'target', 'route_name', 'num_steps', 'feasibility', 'cost_score',
        'time_score', 'safety_score', 'composite', 'bottleneck_step',
        'missing_precursors', 'missing_equipment',
    ]
    scored = [r for r in all_routes if r.get('composite') is not None]
    scored.sort(key=lambda r: r['composite'], reverse=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(scored)

    # Summary JSON
    json_path = os.path.join(OUTPUT_DIR, 'synthesis_comparison.json')
    output = {
        'total_targets': len(target_summaries),
        'total_routes': len(all_routes),
        'target_summaries': target_summaries,
        'equipment_analysis': equipment,
        'extremes': extremes,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    return csv_path, json_path


def main():
    print("=" * 60)
    print("KOMPOSOS Synthesis Cost Comparison")
    print("=" * 60)
    print()

    all_routes, target_summaries = run_all_targets()
    equipment = analyze_equipment(all_routes, target_summaries)
    extremes = find_extremes(all_routes)
    csv_path, json_path = save_results(all_routes, target_summaries, equipment, extremes)

    print(f"Targets analyzed: {len(target_summaries)}")
    print(f"Total routes scored: {len(all_routes)}")
    print()

    # Print per-target summary
    print("Per-target summary:")
    for s in sorted(target_summaries, key=lambda x: x.get('best_composite') or 0, reverse=True):
        if 'error' in s:
            print(f"  {s['target']}: ERROR - {s['error']}")
        else:
            print(f"  {s['target']}: {s['num_routes']} routes, "
                  f"best={s['best_composite']}, "
                  f"cost=${s['precursor_cost_usd']}/g, "
                  f"time={s['total_time_hours']}h")
    print()

    # Print extremes
    if extremes:
        print("Notable routes:")
        for label, route in extremes.items():
            print(f"  {label}: {route['target']} via {route['route_name']} "
                  f"(composite={route['composite']})")
        print()

    # Equipment analysis
    print("Equipment frequency (most useful first):")
    for eq, count in sorted(equipment['equipment_frequency'].items(),
                            key=lambda x: x[1], reverse=True):
        targets = equipment['equipment_targets'][eq]
        print(f"  {eq}: used by {count} target(s) -- {', '.join(targets[:5])}")

    print()
    print(f"CSV saved: {csv_path}")
    print(f"JSON saved: {json_path}")


if __name__ == '__main__':
    main()
