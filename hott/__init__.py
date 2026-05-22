# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS-III HoTT Engine (Layer B)

Homotopy Type Theory foundations:
- Identity types and paths
- Univalence axiom (equivalence ↔ equality)
- Path induction (J eliminator)
- Transport along paths
- Path homotopy (2-paths between paths)
- Geometric homotopy (curvature-aware path equivalence)
- Rate reduction integration
"""

from .identity import IdentityType, Path, refl
from .path_induction import J, based_path_induction
from .homotopy import (
    PathHomotopyChecker,
    HomotopyResult,
    Homotopy,
    HomotopyType,
    check_path_homotopy
)
from .geometric_homotopy import (
    GeometricHomotopyChecker,
    GeometricHomotopyResult,
    GeometricHomotopy,
    GeometricHomotopyType,
    GeometricSignature,
    check_geometric_homotopy
)

__all__ = [
    # Identity types
    "IdentityType",
    "Path",
    "refl",
    # Path induction
    "J",
    "based_path_induction",
    # Standard homotopy
    "PathHomotopyChecker",
    "HomotopyResult",
    "Homotopy",
    "HomotopyType",
    "check_path_homotopy",
    # Geometric homotopy (Thurston-aware)
    "GeometricHomotopyChecker",
    "GeometricHomotopyResult",
    "GeometricHomotopy",
    "GeometricHomotopyType",
    "GeometricSignature",
    "check_geometric_homotopy",
]
