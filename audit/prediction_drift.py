# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Versioned drift gate for the formation-energy prediction contract.

This turns a benchmark from prose into a monitored object.  It compares the
current strict-formula LOO metrics and calibration artifacts with a frozen
development baseline and emits a content-addressed receipt.  AGREE means the
implementation still behaves like the frozen baseline; it does not mean the
model is externally or experimentally validated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from audit.run_predictor_accuracy import measure

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = ROOT / 'audit' / 'baselines' / 'prediction_baseline_2026-07-17.json'
SCHEMA = 'komposos-chem-prediction-drift.v1'


def _sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def evaluate(
    baseline_path: Path = DEFAULT_BASELINE,
    *,
    observed: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not baseline_path.exists():
        payload = {
            'schema': SCHEMA,
            'verdict': 'ORPHAN',
            'baseline_path': str(baseline_path),
            'reasons': ['frozen baseline is missing'],
        }
        payload['receipt_id'] = _receipt(payload)
        return payload

    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    current = observed or measure()
    expected = baseline['expected']
    tolerances = baseline['tolerances']
    reasons = []
    differences: Dict[str, Any] = {}

    if current['n'] != expected['n']:
        reasons.append(f"reference count changed: {expected['n']} -> {current['n']}")
    if current['skipped'] != expected['skipped']:
        reasons.append(f"skipped count changed: {expected['skipped']} -> {current['skipped']}")

    for key in ('mae_eV_per_atom', 'rmse_eV_per_atom', 'median_abs_error_eV_per_atom'):
        delta = float(current[key]) - float(expected[key])
        differences[key] = delta
        if abs(delta) > float(tolerances[key]):
            reasons.append(f'{key} drift {delta:+.6f} exceeds ±{tolerances[key]}')

    coverage_deltas = {}
    for level, expected_rate in expected['interval_coverage'].items():
        actual_rate = float(current['interval_coverage'][level])
        delta = actual_rate - float(expected_rate)
        coverage_deltas[level] = delta
        if abs(delta) > float(tolerances['interval_coverage_absolute']):
            reasons.append(
                f'{level}% interval coverage drift {delta:+.3f} exceeds '
                f"±{tolerances['interval_coverage_absolute']}"
            )
    differences['interval_coverage'] = coverage_deltas

    artifact_actual = {
        rel: _sha256(ROOT / rel) for rel in baseline.get('artifact_sha256', {})
    }
    artifact_changes = {
        rel: {'expected': digest, 'actual': artifact_actual.get(rel)}
        for rel, digest in baseline.get('artifact_sha256', {}).items()
        if artifact_actual.get(rel) != digest
    }

    verdict = 'CLASH' if reasons else ('TENSION' if artifact_changes else 'AGREE')
    if artifact_changes and not reasons:
        reasons.append('calibration/model artifact hash changed while metrics remain within tolerance')

    receipt_body = {
        'schema': SCHEMA,
        'verdict': verdict,
        'baseline_id': baseline['baseline_id'],
        'evidence_role': baseline['evidence_role'],
        'observed': current,
        'differences': differences,
        'artifact_sha256': artifact_actual,
        'artifact_changes': artifact_changes,
        'reasons': reasons,
        'scope_note': (
            'Drift against a frozen development benchmark; not external blind or lab validation.'
        ),
    }
    return {**receipt_body, 'receipt_id': _receipt(receipt_body)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    parser.add_argument('--json', type=Path, help='optional output path')
    args = parser.parse_args()
    result = evaluate(args.baseline)
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.json:
        args.json.write_text(rendered + '\n', encoding='utf-8')
    return 0 if result['verdict'] in {'AGREE', 'TENSION'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
