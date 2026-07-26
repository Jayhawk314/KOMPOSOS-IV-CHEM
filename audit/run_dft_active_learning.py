# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Audit: DFT active-learning selector vs real Materials Project DFT ground truth.

Reproducible measurement that the active-learning acquisition signal
(``oracle.dft_integration.select_for_dft``) concentrates DFT spend on real
high-error materials better than random selection. Uses the offline MP DFT cache
as ground truth -- no quantum-chemistry backend required.

Run:  python audit/run_dft_active_learning.py [n_samples] [budget_fraction]
"""

import json
import sys

from composition_engine.dft_calibration import run_active_learning_calibration


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 0.20
    report = run_active_learning_calibration(n_samples=n, budget_fraction=budget,
                                             verbose=True)
    print("\nJSON:")
    print(json.dumps(report.to_dict(), indent=2))
    # exit non-zero if the selector is not clearly better than random
    return 0 if (report.selector_lift or 0) > 1.15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
