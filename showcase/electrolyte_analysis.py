# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular Electrolyte Analysis: Cross-scale molecule-to-electrode scoring.

Scores solvent pairs, salt-solvent combos, and full electrolyte
formulations against cathodes/anodes using the molecular bridge
and cross-bridge functor.

Usage:
    python -m showcase.electrolyte_analysis
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from molecular_bridge.molecule_properties import (
    ELECTROLYTE_SOLVENTS as MOL_SOLVENTS,
    SALT_ANIONS,
)
from molecular_bridge.interface_validator import MolecularInterfaceValidator
from cross_bridge.molecular_material import (
    score_molecule_material,
    score_electrolyte_formulation,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')

# Solvents and salts to test (names must match molecular_bridge keys)
SOLVENTS = ['EC', 'DMC', 'DEC', 'EMC', 'PC', 'FEC', 'VC']
SALTS = ['LiPF6', 'LiTFSI', 'LiBF4', 'LiClO4']
ELECTRODES = ['NMC811', 'LFP', 'LCO', 'Graphite', 'Si', 'Li_metal', 'LTO']

# Electrolyte formulations to test cross-bridge
FORMULATIONS = [
    {'solvents': ['EC', 'DMC'], 'salt': 'LiPF6', 'label': 'EC:DMC + LiPF6 (standard)'},
    {'solvents': ['EC', 'DEC'], 'salt': 'LiPF6', 'label': 'EC:DEC + LiPF6'},
    {'solvents': ['EC', 'EMC'], 'salt': 'LiPF6', 'label': 'EC:EMC + LiPF6'},
    {'solvents': ['EC', 'DMC'], 'salt': 'LiTFSI', 'label': 'EC:DMC + LiTFSI'},
    {'solvents': ['EC', 'PC'], 'salt': 'LiPF6', 'label': 'EC:PC + LiPF6'},
    {'solvents': ['EC', 'FEC'], 'salt': 'LiPF6', 'label': 'EC:FEC + LiPF6 (Si anode)'},
]


def run_solvent_pairs():
    """Score all solvent-solvent pairs using the molecular bridge."""
    validator = MolecularInterfaceValidator()
    results = []

    for i, s1 in enumerate(SOLVENTS):
        for s2 in SOLVENTS[i + 1:]:
            try:
                score = validator.validate(s1, s2)
                results.append({
                    'solvent_a': s1,
                    'solvent_b': s2,
                    'total_score': round(score.total, 4),
                    'electronic': round(score.electronic_compatibility, 4),
                    'thermodynamic': round(score.thermodynamic_stability, 4),
                    'steric': round(score.steric_compatibility, 4),
                    'solubility': round(score.solubility_compatibility, 4),
                    'reactivity_risk': round(score.reactivity_risk, 4),
                    'viable': score.viable,
                })
            except Exception as exc:
                results.append({
                    'solvent_a': s1,
                    'solvent_b': s2,
                    'total_score': None,
                    'viable': False,
                    'error': str(exc),
                })

    return results


def run_salt_solvent_pairs():
    """Score salt-solvent combinations."""
    validator = MolecularInterfaceValidator()
    results = []

    for salt in SALTS:
        for solvent in SOLVENTS:
            try:
                score = validator.validate(salt, solvent)
                results.append({
                    'salt': salt,
                    'solvent': solvent,
                    'total_score': round(score.total, 4),
                    'electronic': round(score.electronic_compatibility, 4),
                    'thermodynamic': round(score.thermodynamic_stability, 4),
                    'steric': round(score.steric_compatibility, 4),
                    'solubility': round(score.solubility_compatibility, 4),
                    'reactivity_risk': round(score.reactivity_risk, 4),
                    'viable': score.viable,
                })
            except Exception as exc:
                results.append({
                    'salt': salt,
                    'solvent': solvent,
                    'total_score': None,
                    'viable': False,
                    'error': str(exc),
                })

    return results


def run_electrode_cross():
    """Score electrolyte formulations against each electrode (cross-bridge)."""
    results = []

    for form in FORMULATIONS:
        for electrode in ELECTRODES:
            try:
                result = score_electrolyte_formulation(
                    form['solvents'], form['salt'], electrode
                )
                results.append({
                    'formulation': form['label'],
                    'electrode': electrode,
                    'overall_score': round(result['overall_score'], 4),
                    'viable': result['viable'],
                    'bottleneck': result.get('bottleneck', ''),
                    'warnings': '; '.join(result.get('warnings', [])),
                })
            except Exception as exc:
                results.append({
                    'formulation': form['label'],
                    'electrode': electrode,
                    'overall_score': None,
                    'viable': False,
                    'error': str(exc),
                })

    return results


def save_results(solvent_pairs, salt_solvents, electrode_cross):
    """Save all results."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Solvent pairs + salt-solvent as CSV
    csv_path = os.path.join(OUTPUT_DIR, 'electrolyte_compatibility.csv')
    all_rows = []
    for r in solvent_pairs:
        row = dict(r)
        row['pair_type'] = 'solvent-solvent'
        row['component_a'] = r.get('solvent_a', '')
        row['component_b'] = r.get('solvent_b', '')
        all_rows.append(row)
    for r in salt_solvents:
        row = dict(r)
        row['pair_type'] = 'salt-solvent'
        row['component_a'] = r.get('salt', '')
        row['component_b'] = r.get('solvent', '')
        all_rows.append(row)

    fieldnames = [
        'pair_type', 'component_a', 'component_b', 'total_score',
        'electronic', 'thermodynamic', 'steric', 'solubility',
        'reactivity_risk', 'viable',
    ]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        # Sort by score descending
        scored = [r for r in all_rows if r.get('total_score') is not None]
        scored.sort(key=lambda r: r['total_score'], reverse=True)
        writer.writerows(scored)

    # Electrode cross-bridge as JSON
    json_path = os.path.join(OUTPUT_DIR, 'electrolyte_electrode_cross.json')
    output = {
        'formulations_tested': len(FORMULATIONS),
        'electrodes_tested': ELECTRODES,
        'results': electrode_cross,
        'best_per_electrode': {},
    }
    for electrode in ELECTRODES:
        electrode_results = [
            r for r in electrode_cross
            if r['electrode'] == electrode and r.get('overall_score') is not None
        ]
        if electrode_results:
            best = max(electrode_results, key=lambda r: r['overall_score'])
            output['best_per_electrode'][electrode] = {
                'formulation': best['formulation'],
                'score': best['overall_score'],
                'viable': best['viable'],
            }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    return csv_path, json_path


def main():
    print("=" * 60)
    print("KOMPOSOS Molecular Electrolyte Analysis")
    print("=" * 60)
    print()

    print("Scoring solvent pairs...")
    solvent_pairs = run_solvent_pairs()
    scored_sp = [r for r in solvent_pairs if r.get('total_score') is not None]
    scored_sp.sort(key=lambda r: r['total_score'], reverse=True)
    print(f"  {len(scored_sp)} solvent pairs scored")
    for r in scored_sp[:5]:
        print(f"    {r['solvent_a']}+{r['solvent_b']}: {r['total_score']:.4f} "
              f"{'VIABLE' if r['viable'] else ''}")
    print()

    print("Scoring salt-solvent pairs...")
    salt_solvents = run_salt_solvent_pairs()
    scored_ss = [r for r in salt_solvents if r.get('total_score') is not None]
    scored_ss.sort(key=lambda r: r['total_score'], reverse=True)
    print(f"  {len(scored_ss)} salt-solvent pairs scored")
    for r in scored_ss[:5]:
        print(f"    {r['salt']}+{r['solvent']}: {r['total_score']:.4f} "
              f"{'VIABLE' if r['viable'] else ''}")
    print()

    print("Scoring formulations vs electrodes (cross-bridge)...")
    electrode_cross = run_electrode_cross()
    scored_ec = [r for r in electrode_cross if r.get('overall_score') is not None]
    print(f"  {len(scored_ec)} formulation-electrode combos scored")
    for r in sorted(scored_ec, key=lambda r: r['overall_score'], reverse=True)[:5]:
        compat = "OK" if r['viable'] else "FAIL"
        print(f"    {r['formulation']} + {r['electrode']}: "
              f"{r['overall_score']:.4f} [{compat}]")
    print()

    csv_path, json_path = save_results(solvent_pairs, salt_solvents, electrode_cross)
    print(f"CSV saved: {csv_path}")
    print(f"JSON saved: {json_path}")


if __name__ == '__main__':
    main()
