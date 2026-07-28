# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Master runner: generate all showcase content.

Executes all 6 content generators in sequence and saves results
to showcase/outputs/.

Usage:
    python -m showcase.generate_all
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_module(name, func):
    """Run a content generator with timing."""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        print(f"\n  Completed in {elapsed:.1f}s")
        return True
    except Exception as exc:
        elapsed = time.time() - start
        print(f"\n  FAILED after {elapsed:.1f}s: {exc}")
        return False


def main():
    print("KOMPOSOS-III Showcase Content Generator")
    print("=" * 60)
    print("Generating all 6 content pieces...")

    results = {}

    # 1. Battery Cell Sweep
    from showcase.battery_cell_sweep import main as battery_main
    results['battery_sweep'] = run_module("1/6: Battery Cell Sweep", battery_main)

    # 2. Solid-State Battery Design
    from showcase.solid_state_design import main as solid_main
    results['solid_state'] = run_module("2/6: Solid-State Battery Design", solid_main)

    # 3. PFAS Compliance Screening
    from showcase.pfas_screening import main as pfas_main
    results['pfas_screening'] = run_module("3/6: PFAS Compliance Screening", pfas_main)

    # 4. Molecular Electrolyte Analysis
    from showcase.electrolyte_analysis import main as electrolyte_main
    results['electrolyte'] = run_module("4/6: Molecular Electrolyte Analysis", electrolyte_main)

    # 5. Synthesis Cost Comparison
    from showcase.synthesis_comparison import main as synthesis_main
    results['synthesis'] = run_module("5/6: Synthesis Cost Comparison", synthesis_main)

    # 6. Cross-Domain Discovery
    from showcase.cross_domain_discovery import main as cross_main
    results['cross_domain'] = run_module("6/6: Cross-Domain Discovery", cross_main)

    # Summary
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"  Passed: {passed}/6")
    if failed:
        print(f"  Failed: {failed}/6")
        for name, ok in results.items():
            if not ok:
                print(f"    - {name}")

    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
    if os.path.isdir(output_dir):
        files = os.listdir(output_dir)
        print(f"\n  Output files ({len(files)}):")
        for f in sorted(files):
            size = os.path.getsize(os.path.join(output_dir, f))
            print(f"    {f} ({size:,} bytes)")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
