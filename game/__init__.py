# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS-III Game Engine (Layer D)

Game-theoretic foundations:
- Open games as categorical morphisms
- Nash equilibrium finding (not gradient descent)
- Backward induction from goals
- Encoder/Decoder minimax game
"""

from .open_games import OpenGame, OpenGameCategory
from .nash import Strategy, NashEquilibrium, find_nash_equilibria

__all__ = [
    "OpenGame",
    "OpenGameCategory",
    "Strategy",
    "NashEquilibrium",
    "find_nash_equilibria",
]
