# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

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
