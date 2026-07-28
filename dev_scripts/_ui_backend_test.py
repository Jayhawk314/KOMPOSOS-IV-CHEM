# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Manual UI backend smoke-test helpers; excluded from pytest collection."""

__test__ = False

import sys, traceback
results = []
def record_test(name, fn):
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
