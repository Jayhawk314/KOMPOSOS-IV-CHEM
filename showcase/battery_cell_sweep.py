# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
"""
Battery Cell Sweep: Score all cathode-electrolyte-anode pairings.

Runs 100+ compatibility checks across all battery material combinations,
ranks them, and identifies known failure modes. No simulation required.

Usage:
    python -m showcase.battery_cell_sweep
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from battery_bridge.material_properties import (
    CATHODE_MATERIALS,
    ANODE_MATERIALS,
    ELECTROLYTE_SOLVENTS,
    ELECTROLYTE_SALTS,
    SOLID_ELECTROLYTES,
)
from battery_bridge.interface_validator import BatteryInterfaceValidator

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')


def run_pairwise_sweep():
    """Score every relevant battery material pairing."""
    validator = BatteryInterfaceValidator()

    cathodes = list(CATHODE_MATERIALS.keys())
    anodes = list(ANODE_MATERIALS.keys())
    # Combine liquid electrolytes (solvents + salts) and solid electrolytes
    electrolytes = list(ELECTROLYTE_SOLVENTS.keys()) + list(ELECTROLYTE_SALTS.keys()) + list(SOLID_ELECTROLYTES.keys())

    results = []

    # Cathode-Electrolyte pairings
    for c in cathodes:
        for e in electrolytes:
            try:
                score = validator.validate(c, e)
                results.append({
                    'material_a': c,
                    'material_b': e,
                    'pair_type': 'cathode-electrolyte',
                    'total_score': round(score.total, 4),
                    'ion_transport': round(score.ion_transport, 4),
                    'electrochemical_stability': round(score.electrochemical_stability, 4),
                    'interface_compatibility': round(score.interface_compatibility, 4),
                    'mechanical_compatibility': round(score.mechanical_compatibility, 4),
                    'degradation_penalty': round(score.degradation_penalty, 4),
                    'viable': score.viable,
                })
            except Exception as exc:
                results.append({
                    'material_a': c,
                    'material_b': e,
                    'pair_type': 'cathode-electrolyte',
                    'total_score': None,
                    'ion_transport': None,
                    'electrochemical_stability': None,
                    'interface_compatibility': None,
                    'mechanical_compatibility': None,
                    'degradation_penalty': None,
                    'viable': False,
                    'error': str(exc),
                })

    # Cathode-Anode pairings
    for c in cathodes:
        for a in anodes:
            try:
                score = validator.validate(c, a)
                results.append({
                    'material_a': c,
                    'material_b': a,
                    'pair_type': 'cathode-anode',
                    'total_score': round(score.total, 4),
                    'ion_transport': round(score.ion_transport, 4),
                    'electrochemical_stability': round(score.electrochemical_stability, 4),
                    'interface_compatibility': round(score.interface_compatibility, 4),
                    'mechanical_compatibility': round(score.mechanical_compatibility, 4),
                    'degradation_penalty': round(score.degradation_penalty, 4),
                    'viable': score.viable,
                })
            except Exception as exc:
                results.append({
                    'material_a': c,
                    'material_b': a,
                    'pair_type': 'cathode-anode',
                    'total_score': None,
                    'viable': False,
                    'error': str(exc),
                })

    # Anode-Electrolyte pairings
    for a in anodes:
        for e in electrolytes:
            try:
                score = validator.validate(a, e)
                results.append({
                    'material_a': a,
                    'material_b': e,
                    'pair_type': 'anode-electrolyte',
                    'total_score': round(score.total, 4),
                    'ion_transport': round(score.ion_transport, 4),
                    'electrochemical_stability': round(score.electrochemical_stability, 4),
                    'interface_compatibility': round(score.interface_compatibility, 4),
                    'mechanical_compatibility': round(score.mechanical_compatibility, 4),
                    'degradation_penalty': round(score.degradation_penalty, 4),
                    'viable': score.viable,
                })
            except Exception as exc:
                results.append({
                    'material_a': a,
                    'material_b': e,
                    'pair_type': 'anode-electrolyte',
                    'total_score': None,
                    'viable': False,
                    'error': str(exc),
                })

    return results


def save_results(results):
    """Save results as CSV and JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Sort by total_score descending (None at bottom)
    scored = [r for r in results if r.get('total_score') is not None]
    errored = [r for r in results if r.get('total_score') is None]
    scored.sort(key=lambda r: r['total_score'], reverse=True)
    all_sorted = scored + errored

    # CSV
    csv_path = os.path.join(OUTPUT_DIR, 'battery_pairwise_scores.csv')
    fieldnames = [
        'material_a', 'material_b', 'pair_type', 'total_score',
        'ion_transport', 'electrochemical_stability', 'interface_compatibility',
        'mechanical_compatibility', 'degradation_penalty', 'viable',
    ]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_sorted)

    # JSON with summary
    viable_count = sum(1 for r in scored if r['viable'])
    summary = {
        'total_pairs': len(results),
        'scored_pairs': len(scored),
        'viable_pairs': viable_count,
        'non_viable_pairs': len(scored) - viable_count,
        'error_pairs': len(errored),
        'top_10': scored[:10],
        'bottom_10': scored[-10:] if len(scored) >= 10 else scored,
        'cathodes_tested': list(CATHODE_MATERIALS.keys()),
        'anodes_tested': list(ANODE_MATERIALS.keys()),
        'electrolytes_tested': (
            list(ELECTROLYTE_SOLVENTS.keys()) +
            list(ELECTROLYTE_SALTS.keys()) +
            list(SOLID_ELECTROLYTES.keys())
        ),
    }

    json_path = os.path.join(OUTPUT_DIR, 'battery_sweep.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)

    return csv_path, json_path, summary


def main():
    print("=" * 60)
    print("KOMPOSOS Battery Cell Sweep")
    print("=" * 60)
    print()

    results = run_pairwise_sweep()
    csv_path, json_path, summary = save_results(results)

    print(f"Total pairings scored: {summary['scored_pairs']}")
    print(f"  Viable: {summary['viable_pairs']}")
    print(f"  Non-viable: {summary['non_viable_pairs']}")
    print()

    print("Top 10 pairings:")
    for i, r in enumerate(summary['top_10'], 1):
        status = "VIABLE" if r['viable'] else "CAUTION"
        print(f"  {i:2d}. {r['material_a']:10s} + {r['material_b']:10s}  "
              f"({r['pair_type']:20s})  score={r['total_score']:.4f}  [{status}]")

    print()
    print("Bottom 10 pairings:")
    for i, r in enumerate(summary['bottom_10'], 1):
        status = "VIABLE" if r['viable'] else "FAIL"
        print(f"  {i:2d}. {r['material_a']:10s} + {r['material_b']:10s}  "
              f"({r['pair_type']:20s})  score={r['total_score']:.4f}  [{status}]")

    print()
    print(f"CSV saved: {csv_path}")
    print(f"JSON saved: {json_path}")


if __name__ == '__main__':
    main()
