# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Chem-system-only audit / regression harness
============================================

Runs ONLY the in-scope chemistry/materials product shards, so out-of-scope
suites (aimo, cyber/Mythos, OpenTargets/drug-repurposing, root debug scripts,
generic categorical/math tests not wired into the chem product) can never
define chem-system status or pull failures into the signal.

This is the regression gate for compatibility / coverage / calibration work.
It deliberately does NOT invoke the monolithic pytest tree.

Usage
-----
    python audit/chem_audit.py              # tests + audit shards (default)
    python audit/chem_audit.py --tests      # in-scope pytest shards only
    python audit/chem_audit.py --audits     # audit shards only (dev + Q8 diag + computational)
    python audit/chem_audit.py --q8         # Q8 diagnostic only (spent_diagnostic, NEVER a blind claim)

Scope is an explicit allowlist. Editing it is intentional and reviewable.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- In-scope test shards (explicit allowlist) -----------------------------
# Compatibility / Cell Design / cross-bridge / per-domain bridges / composition
# (formation energy, structure) / PFAS / MOF / molecular / chem-wired oracle.
IN_SCOPE_TESTS = [
    "battery_bridge/tests",
    "polymer_bridge/tests",
    "metal_bridge/tests",
    "ceramic_bridge/tests",
    "semiconductor_bridge/tests",
    "glass_bridge/tests",
    "cross_bridge/tests",
    "composition_engine/tests",
    "pfas_bridge/tests",
    "mof_bridge/tests",
    "molecular_bridge/tests",
    "synthesis_planner/tests",
    "discovery/tests",
    "audit/tests",
    # chem-wired oracle / calibration / contract tests (NOT generic math)
    "tests/test_compatibility_decision_calibration.py",
    "tests/test_material_zfc.py",
    "tests/test_oracle_strategies.py",
    "tests/test_pfas_report.py",
    "tests/test_pfas_pdf.py",
    "api/tests/compatibility_workflow_contract_test.py",
    "api/tests/test_monitoring_export.py",
]

# Explicitly OUT of scope (documented so the boundary is auditable):
#   aimo/**, tests/test_mythos_*, tests/test_repurposing_benchmark.py,
#   test_opentargets_*, root test_*.py debug scripts, tests/test_cog_iv.py,
#   tests/test_infinity_cosmos.py, tests/test_higher_order_yoneda.py,
#   tests/test_full_defense_pipeline.py, tests/test_optimus_integration.py,
#   generic categorical/math: tests/test_enriched_category.py,
#   tests/test_dempster_shafer.py, tests/test_cat_engine.py,
#   tests/test_streaming_kan.py, tests/test_zfc_integration.py,
#   tests/test_md_integration.py.

Q8_PATH = "audit/external_blind/compatibility_2026_q8.json"


def _run(cmd: list[str], label: str) -> bool:
    print("\n" + "=" * 78)
    print(f"RUN: {label}")
    print("    " + " ".join(cmd))
    print("=" * 78)
    result = subprocess.run(cmd, cwd=str(ROOT))
    ok = result.returncode == 0
    print(f"  -> {'PASS' if ok else 'FAIL'} ({label})")
    return ok


def run_tests() -> bool:
    existing = [p for p in IN_SCOPE_TESTS if (ROOT / p).exists()]
    missing = [p for p in IN_SCOPE_TESTS if not (ROOT / p).exists()]
    if missing:
        print(f"  NOTE: skipping non-existent in-scope paths: {missing}")
    # importlib mode prevents an unrelated installed `tests` package from
    # shadowing this repository's namespace when many shards are collected.
    cmd = [
        sys.executable, "-m", "pytest", "-q", "--no-header",
        "--import-mode=importlib", *existing,
    ]
    return _run(cmd, "in-scope chem pytest shards")


def run_audits(q8_only: bool = False) -> bool:
    results = []
    if not q8_only:
        results.append(_run(
            [sys.executable, "audit/run_audit.py", "--module", "development"],
            "development compatibility (expect 41/41; regression gate)",
        ))
        results.append(_run(
            [sys.executable, "audit/run_audit.py", "--module", "computational"],
            "computational integrity (incl. formation-energy Phase16)",
        ))
    # Q8 is spent_diagnostic: coverage/error-family regression only, NEVER a blind claim.
    results.append(_run(
        [sys.executable, "audit/run_audit.py", "--module", "external",
         "--external-path", Q8_PATH],
        "Q8 diagnostic (spent_diagnostic — NOT a blind claim)",
    ))
    return all(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", action="store_true", help="in-scope pytest shards only")
    parser.add_argument("--audits", action="store_true", help="audit shards only")
    parser.add_argument("--q8", action="store_true", help="Q8 diagnostic only")
    args = parser.parse_args()

    ok = True
    if args.q8:
        ok = run_audits(q8_only=True)
    elif args.tests:
        ok = run_tests()
    elif args.audits:
        ok = run_audits()
    else:
        ok_tests = run_tests()
        ok_audits = run_audits()
        ok = ok_tests and ok_audits

    print("\n" + "=" * 78)
    print(f"CHEM AUDIT OVERALL: {'PASS' if ok else 'FAIL'}")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
