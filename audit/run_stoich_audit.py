# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Z3 stoichiometric balance audit of curated synthesis routes.

Usage:
    python audit\\run_stoich_audit.py [--json audit\\stoich_report.json]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from synthesis_planner.stoich_solver import main

if __name__ == "__main__":
    raise SystemExit(main())
