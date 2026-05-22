# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS-III Cubical Engine (Layer C)

Cubical Type Theory foundations:
- Paths as computational objects (not just proofs)
- Kan operations (hcomp, hfill) for gap-filling
- Higher Inductive Types (HITs) for structured data
- Parallel path exploration (the cube structure)
"""

from .paths import Interval, PathType, path_apply
from .kan_ops import hcomp, hfill, comp, inv

__all__ = [
    "Interval",
    "PathType",
    "path_apply",
    "hcomp",
    "hfill",
    "comp",
    "inv",
]
