# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Topological Data Analysis Module

Provides persistent homology and TDA tools for detecting:
- Feedback loops (H₁ features)
- Multi-variable cascades (H₂ features)
- Regime transitions
- Topological signatures of complex systems
"""

from .persistent_homology import PersistentHomologyComputer

# Public compatibility names retained after the implementation was consolidated
# into persistent_homology.py.
PersistentHomologyAnalyzer = PersistentHomologyComputer


def analyze_persistence(complex):
    """Compute a persistence diagram for a filtered simplicial complex."""
    return PersistentHomologyComputer().compute(complex)

# Backwards-compatible alias: several geometry modules import PersistenceComputer
PersistenceComputer = PersistentHomologyAnalyzer

__all__ = [
    'PersistentHomologyAnalyzer',
    'PersistenceComputer',
    'analyze_persistence'
]
