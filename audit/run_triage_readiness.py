# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Measure functional and latency readiness of one triage workflow.

This is a development diagnostic. It does not measure predictive accuracy,
experimental success, or value relative to an external professional workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from composition_engine.designer import PropertyTarget
from discovery.workbench_service import DiscoveryGoal, DiscoveryWorkbenchService


DEFAULT_OUTPUT = ROOT / "audit" / "triage_readiness_report.json"


def _receipt(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run(max_candidates: int = 30):
    goal = DiscoveryGoal(
        targets=[
            PropertyTarget(
                name="voltage",
                min_value=3.0,
                max_value=4.5,
                weight=1.0,
            )
        ],
        required_elements=["Li"],
        max_candidates=max_candidates,
        apply_charge_balance_gate=True,
    )
    start = time.perf_counter()
    candidates = DiscoveryWorkbenchService().run_discovery_pipeline(goal)
    elapsed = time.perf_counter() - start

    report = {
        "schema": "komposos-triage-readiness.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "development_diagnostic",
        "claim_scope": (
            "Functional coverage and wall-clock latency for one local battery-triage "
            "scenario; not predictive accuracy, experimental validation, or a "
            "comparison with an external professional workflow."
        ),
        "command": f"python audit/run_triage_readiness.py --max-candidates {max_candidates}",
        "python": platform.python_version(),
        "scenario": {
            "property": "voltage",
            "minimum": 3.0,
            "maximum": 4.5,
            "required_elements": ["Li"],
            "requested_candidates": max_candidates,
        },
        "observed": {
            "elapsed_seconds": round(elapsed, 6),
            "returned_candidates": len(candidates),
            "unique_formulas": len({candidate.formula for candidate in candidates}),
            "hard_vetoed": sum(bool(candidate.hard_vetoes) for candidate in candidates),
            "charge_balance": {
                "pass": sum(candidate.zfc_witnessed is True for candidate in candidates),
                "veto": sum(candidate.zfc_witnessed is False for candidate in candidates),
                "not_assessed": sum(candidate.zfc_witnessed is None for candidate in candidates),
            },
            "pfas_formula_screen": {
                "assessed_pass": sum(candidate.is_pfas_free is True for candidate in candidates),
                "veto": sum(candidate.is_pfas_free is False for candidate in candidates),
                "not_assessed": sum(candidate.is_pfas_free is None for candidate in candidates),
            },
            "with_synthesis_route": sum(bool(candidate.precursors) for candidate in candidates),
            "top_candidates": [
                {
                    "formula": candidate.formula,
                    "overall_confidence": round(candidate.overall_confidence, 6),
                    "design_score": round(candidate.design_score, 6),
                    "charge_balance": candidate.zfc_witnessed,
                    "pfas_formula_status": candidate.compatibility_metadata.get("pfas_status"),
                    "hard_vetoes": candidate.hard_vetoes,
                }
                for candidate in candidates[:10]
            ],
        },
    }
    report["receipt_id"] = _receipt(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.max_candidates)
    rendered = json.dumps(report, indent=2)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
