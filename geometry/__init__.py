# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS-III Geometry Layer

Implements geometric analysis of knowledge graphs using:
- Ollivier-Ricci curvature for local geometry detection
- Discrete Ricci flow for structure revelation
- Thurston-style geometric decomposition

Key insight: Different regions of a knowledge graph have different
natural geometries (hyperbolic for hierarchies, spherical for clusters,
euclidean for chains). This layer reveals that structure.
"""

from .ricci import (
    OllivierRicciCurvature,
    CurvatureResult,
    GeometryType,
    compute_graph_curvature,
)

from .flow import (
    DiscreteRicciFlow,
    DecompositionResult,
    GeometricRegion,
    FlowStep,
    run_ricci_flow,
)

# Spectral analysis (if available)
try:
    from .spectral import (
        SpectralGraphAnalyzer,
        analyze_spectrum,
        Graph,
        GraphLaplacian,
        SpectralClustering,
        CheegerConstant,
        RandomWalkAnalysis,
        graph_from_adjacency,
        graph_from_edges,
        analyze_connectivity,
    )
    SPECTRAL_AVAILABLE = True
except ImportError:
    SPECTRAL_AVAILABLE = False

__all__ = [
    # Curvature
    "OllivierRicciCurvature",
    "CurvatureResult",
    "GeometryType",
    "compute_graph_curvature",
    # Ricci Flow
    "DiscreteRicciFlow",
    "DecompositionResult",
    "GeometricRegion",
    "FlowStep",
    "run_ricci_flow",
]

# Add spectral if available
if SPECTRAL_AVAILABLE:
    __all__.extend([
        "SpectralGraphAnalyzer",
        "analyze_spectrum",
        "Graph",
        "GraphLaplacian",
        "SpectralClustering",
        "CheegerConstant",
        "RandomWalkAnalysis",
        "graph_from_adjacency",
        "graph_from_edges",
        "analyze_connectivity",
    ])
