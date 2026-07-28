# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
PFAS Compliance Screening: Check realistic BOMs for PFAS substances.

Screens battery, semiconductor, and coatings bills of materials against
the PFAS registry, identifies urgency levels, and generates a
replacement transition roadmap.

Usage:
    python -m showcase.pfas_screening
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge.replacement_scorer import UseCase, find_replacements

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

# Realistic BOMs for different industries
BATTERY_BOM = {
    'name': 'Li-ion Battery Cell',
    'use_case': UseCase.BATTERY_BINDER,
    'materials': [
        'PVDF', 'PTFE', 'NMP', 'EC', 'DMC', 'LiPF6',
        'CMC', 'SBR', 'Cu', 'Al', 'NMC811', 'Graphite',
    ],
}

SEMICONDUCTOR_BOM = {
    'name': 'Semiconductor Fab',
    'use_case': UseCase.CHEMICAL_RESISTANT_LINER,
    'materials': [
        'PTFE', 'PFA', 'Si', 'GaAs', 'PEEK', 'Epoxy',
        'Al2O3', 'SiO2', 'SiC', 'GaN',
    ],
}

COATINGS_BOM = {
    'name': 'Industrial Coatings',
    'use_case': UseCase.NON_STICK_COATING,
    'materials': [
        'PTFE', 'FEP', 'Nafion', 'EPDM', 'Silicone',
        'PVDF', 'PFA', 'Epoxy', 'Polyurethane',
    ],
}


def screen_bom(checker, bom_spec):
    """Screen a single BOM and return structured results."""
    batch = checker.check_batch(bom_spec['materials'], bom_spec['use_case'])

    pfas_items = []
    clean_items = []
    for result in batch.materials:
        entry = result.to_dict()
        entry['bom'] = bom_spec['name']
        if result.is_pfas:
            pfas_items.append(entry)
        else:
            clean_items.append(entry)

    return {
        'bom_name': bom_spec['name'],
        'total_materials': len(bom_spec['materials']),
        'pfas_count': batch.pfas_count,
        'max_urgency': batch.max_urgency,
        'has_pfas': batch.has_pfas,
        'pfas_materials': pfas_items,
        'clean_materials': [c['material_name'] for c in clean_items],
    }


def build_replacement_roadmap(checker, all_boms):
    """Build a transition roadmap for all PFAS materials found."""
    # Collect unique PFAS + use_case combos
    seen = set()
    roadmap = []

    for bom_spec in all_boms:
        batch = checker.check_batch(bom_spec['materials'], bom_spec['use_case'])
        for result in batch.materials:
            if not result.is_pfas:
                continue
            key = (result.material_name, bom_spec['use_case'].value)
            if key in seen:
                continue
            seen.add(key)

            replacements = result.replacements
            best = replacements[0] if replacements else None

            roadmap.append({
                'pfas_material': result.material_name,
                'use_case': bom_spec['use_case'].value,
                'bom': bom_spec['name'],
                'urgency': result.urgency,
                'category': result.pfas_category or 'unknown',
                'best_replacement': best.name if best else 'None available',
                'replacement_score': round(best.overall_score, 3) if best else None,
                'replacement_advantages': ', '.join(best.advantages[:2]) if best else '',
                'replacement_limitations': ', '.join(best.limitations[:2]) if best else '',
                'num_alternatives': len(replacements),
            })

    # Sort by urgency (critical first)
    urgency_order = {'critical': 0, 'high': 1, 'moderate': 2, 'low': 3, 'none': 4}
    roadmap.sort(key=lambda r: urgency_order.get(r['urgency'], 5))

    return roadmap


def save_results(bom_results, roadmap):
    """Save all results to JSON and CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Per-BOM JSON files
    for result in bom_results:
        safe_name = result['bom_name'].lower().replace(' ', '_').replace('-', '_')
        path = os.path.join(OUTPUT_DIR, f'pfas_{safe_name}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, default=str)

    # Replacement roadmap CSV
    csv_path = os.path.join(OUTPUT_DIR, 'pfas_replacement_roadmap.csv')
    if roadmap:
        fieldnames = [
            'pfas_material', 'use_case', 'bom', 'urgency', 'category',
            'best_replacement', 'replacement_score', 'replacement_advantages',
            'replacement_limitations', 'num_alternatives',
        ]
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(roadmap)

    return csv_path


def main():
    print("=" * 60)
    print("KOMPOSOS PFAS Compliance Screening")
    print("=" * 60)
    print()

    checker = PFASComplianceChecker()
    all_boms = [BATTERY_BOM, SEMICONDUCTOR_BOM, COATINGS_BOM]

    bom_results = []
    for bom_spec in all_boms:
        result = screen_bom(checker, bom_spec)
        bom_results.append(result)

        status = "PFAS FOUND" if result['has_pfas'] else "CLEAN"
        print(f"{result['bom_name']}:")
        print(f"  Materials checked: {result['total_materials']}")
        print(f"  PFAS found: {result['pfas_count']}  [{status}]")
        print(f"  Max urgency: {result['max_urgency']}")
        if result['pfas_materials']:
            for p in result['pfas_materials']:
                print(f"    - {p['material_name']}: urgency={p['urgency']}, "
                      f"category={p.get('pfas_category', 'N/A')}")
        print()

    roadmap = build_replacement_roadmap(checker, all_boms)
    csv_path = save_results(bom_results, roadmap)

    print("Replacement Roadmap:")
    for r in roadmap:
        print(f"  {r['pfas_material']} ({r['use_case']}): "
              f"urgency={r['urgency']}, "
              f"replace with {r['best_replacement']} "
              f"(score={r['replacement_score']})")

    print()
    print(f"Roadmap CSV saved: {csv_path}")
    print(f"BOM JSONs saved to: {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
