"""Stable JSON export contracts for external monitors such as noesis.

The exporter preserves CHEM's native decisions.  It does not re-judge a result
or turn heuristic evidence into measurement.  Every payload is content-addressed
so a monitor can validate and deduplicate it without importing CHEM internals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

from audit.prediction_drift import evaluate as evaluate_prediction_drift
from composition_engine.predictor import CompositionPredictor
from oracle.compatibility_service import run_compatibility_workflow

SCHEMA = 'komposos-chem-monitor.v1'


def _with_receipt(kind: str, evidence_role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    body = {
        'schema': SCHEMA,
        'kind': kind,
        'evidence_role': evidence_role,
        'payload': payload,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return {**body, 'receipt_id': hashlib.sha256(canonical.encode('utf-8')).hexdigest()}


def export_prediction(formula: str, domain: str | None = None) -> Dict[str, Any]:
    prediction = CompositionPredictor().predict(formula, domain=domain)
    return _with_receipt(
        'composition_prediction',
        'screening_model_estimate',
        {
            **prediction.to_dict(),
            'scope_note': (
                'Model estimate with provenance anchors; not DFT, measurement, or synthesis proof.'
            ),
        },
    )


def export_compatibility(
    material_a: str,
    material_b: str,
    domain: str | None = None,
    role: str | None = None,
) -> Dict[str, Any]:
    workflow = run_compatibility_workflow(
        material_a,
        material_b,
        domain=domain,
        role=role,
    )
    payload = workflow.to_dict()
    payload['scope_note'] = (
        'Pairwise screening decision. ZFC summary constraints derive from the same '
        'bridge score output and are not independent physical measurements.'
    )
    return _with_receipt('compatibility_workflow', 'screening_decision', payload)


def export_prediction_drift(baseline: Path | None = None) -> Dict[str, Any]:
    result = evaluate_prediction_drift(baseline) if baseline else evaluate_prediction_drift()
    return _with_receipt('prediction_drift', 'development_drift_monitor', result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pred = sub.add_parser('prediction')
    pred.add_argument('--formula', required=True)
    pred.add_argument('--domain')
    compat = sub.add_parser('compatibility')
    compat.add_argument('--material-a', required=True)
    compat.add_argument('--material-b', required=True)
    compat.add_argument('--domain')
    compat.add_argument('--role')
    drift = sub.add_parser('prediction-drift')
    drift.add_argument('--baseline', type=Path)
    args = parser.parse_args()

    if args.command == 'prediction':
        result = export_prediction(args.formula, args.domain)
    elif args.command == 'compatibility':
        result = export_compatibility(
            args.material_a, args.material_b, args.domain, args.role
        )
    else:
        result = export_prediction_drift(args.baseline)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
