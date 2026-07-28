# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import pathlib

SCRIPT = chr(34)*3 + "KOMPOSOS UI Backend Functional Test." + chr(34)*3 + chr(10)
SCRIPT += """
import sys, traceback

results = []

def test(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
        print(f"  PASS: {name}")
    except Exception as e:
        results.append((name, "FAIL", str(e)))
        print(f"  FAIL: {name} -- {e}")
        traceback.print_exc()

print("=" * 70)
print("KOMPOSOS UI BACKEND FUNCTIONAL TEST")
print("=" * 70)
"""
pathlib.Path("_ui_backend_test.py").write_text(SCRIPT)
print("wrote generator")
