# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Domain Plugin System

Provides the DomainPlugin ABC for plugging any real-world domain into
the KOMPOSOS-IV math kernel. Each plugin loads domain data as a Category
and matches its structure against the mathematical reference manifold.

Usage:
    from domains import DomainPlugin, StructureFingerprint, StructureMatch
    from domains import MathKernel
"""

from .plugin_interface import (
    DomainPlugin,
    StructureFingerprint,
    StructureMatch,
)

__all__ = [
    "DomainPlugin",
    "StructureFingerprint",
    "StructureMatch",
]
