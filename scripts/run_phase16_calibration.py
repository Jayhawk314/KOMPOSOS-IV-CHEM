# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Run Phase 16 external calibration for formation-energy uncertainty."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from composition_engine.phase16_calibration import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_REPORT_PATH,
    format_report,
    run_phase16_calibration,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 16 external calibration")
    parser.add_argument("--max-entries", type=int, default=5000,
                        help="Maximum frozen external validation entries to use")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH,
                        help="Frozen validation manifest path")
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_PATH,
                        help="Calibration model output path")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_PATH,
                        help="Calibration report output path")
    parser.add_argument("--force-manifest", action="store_true",
                        help="Regenerate the frozen manifest from cached MP data")
    args = parser.parse_args()

    report = run_phase16_calibration(
        max_entries=args.max_entries,
        manifest_path=args.manifest,
        model_path=args.model_out,
        report_path=args.report_out,
        force_manifest=args.force_manifest,
    )
    print(format_report(report))
    print(f"\nManifest: {args.manifest}")
    print(f"Model:    {args.model_out}")
    print(f"Report:   {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

