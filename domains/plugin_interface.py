# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Domain Plugin Interface

Extends the Bridge ABC with structure fingerprinting and matching.
Any real-world domain implements DomainPlugin to:
  1. Load domain data into a Category (inherited from Bridge)
  2. Compute its structural fingerprint (topology + geometry + spectral)
  3. Match against the math kernel to find governing mathematics
  4. Interpret matches in domain-specific terms

The MathKernel is not defined here -- it lives in domains.mathematics.kernel.
This module defines only the plugin side of the interface.
"""

from __future__ import annotations

import math
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from core.bridge import Bridge

if TYPE_CHECKING:
    pass


@dataclass
class StructureFingerprint:
    """
    Structural signature of a category, computed from topology + geometry + spectral.

    Used for cheap, fast comparison between a domain and math subgraphs.
    Two categories with similar fingerprints likely share mathematical structure.
    """

    # From persistent homology
    betti_numbers: Dict[int, int] = field(default_factory=dict)

    # From Ricci curvature
    curvature_stats: Dict[str, float] = field(default_factory=dict)
    # Expected keys: mean, std, num_spherical, num_hyperbolic, num_euclidean

    # From spectral analysis
    spectral_data: Dict[str, float] = field(default_factory=dict)
    # Expected keys: algebraic_connectivity, spectral_gap, cheeger_estimate

    # Summary counts
    community_count: int = 0
    object_count: int = 0
    morphism_count: int = 0

    def distance(self, other: StructureFingerprint) -> float:
        """
        Weighted L2 distance between two fingerprints.

        Normalizes each feature by scale before computing distance.
        Returns 0.0 for identical fingerprints.
        """
        terms = []

        # Betti number comparison (weight: 3.0 -- topology is primary signal)
        all_dims = set(self.betti_numbers) | set(other.betti_numbers)
        for dim in all_dims:
            a = self.betti_numbers.get(dim, 0)
            b = other.betti_numbers.get(dim, 0)
            scale = max(abs(a), abs(b), 1)
            terms.append(3.0 * ((a - b) / scale) ** 2)

        # Curvature stats comparison (weight: 2.0)
        all_keys = set(self.curvature_stats) | set(other.curvature_stats)
        for key in all_keys:
            a = self.curvature_stats.get(key, 0.0)
            b = other.curvature_stats.get(key, 0.0)
            scale = max(abs(a), abs(b), 1.0)
            terms.append(2.0 * ((a - b) / scale) ** 2)

        # Spectral comparison (weight: 2.0)
        all_keys = set(self.spectral_data) | set(other.spectral_data)
        for key in all_keys:
            a = self.spectral_data.get(key, 0.0)
            b = other.spectral_data.get(key, 0.0)
            scale = max(abs(a), abs(b), 1.0)
            terms.append(2.0 * ((a - b) / scale) ** 2)

        # Community count comparison (weight: 1.0)
        scale = max(self.community_count, other.community_count, 1)
        terms.append(1.0 * ((self.community_count - other.community_count) / scale) ** 2)

        # Graph size ratio (weight: 0.5 -- size matters less than shape)
        for attr in ("object_count", "morphism_count"):
            a = getattr(self, attr)
            b = getattr(other, attr)
            scale = max(a, b, 1)
            terms.append(0.5 * ((a - b) / scale) ** 2)

        return math.sqrt(sum(terms)) if terms else 0.0


@dataclass
class StructureMatch:
    """
    A match between a domain plugin and a math subgraph.

    Represents the finding: "this domain's structure corresponds to
    this region of mathematics with this confidence."
    """

    domain_name: str
    math_region: str  # e.g., "mmlkg/topology_cluster_3"
    fingerprint_distance: float
    functor_verification: Dict[str, bool] = field(default_factory=dict)
    confidence: float = 0.0
    predictions: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"StructureMatch(domain={self.domain_name!r}, "
            f"math={self.math_region!r}, "
            f"confidence={self.confidence:.3f})"
        )


class DomainPlugin(Bridge):
    """
    Domain plugin for the KOMPOSOS-IV math kernel.

    Extends Bridge with structural fingerprinting and match interpretation.
    Subclass this to plug any real-world domain into the system.

    Inherited from Bridge:
        get_objects() -> List[Object]        (abstract)
        get_morphisms() -> List[Morphism]    (abstract)
        score_pair(source, target) -> Dict   (abstract)
        load() -> Dict[str, int]             (concrete -- calls bulk_add)
        as_functor() -> Functor              (concrete -- reifies load mapping)

    New abstract methods:
        structure_fingerprint() -> StructureFingerprint
        interpret_match(match) -> str

    Usage:
        class PhysicsPlugin(DomainPlugin):
            def get_objects(self): return [...]
            def get_morphisms(self): return [...]
            def score_pair(self, s, t): return {...}
            def structure_fingerprint(self): return StructureFingerprint(...)
            def interpret_match(self, match): return "Physics matches ..."

        plugin = PhysicsPlugin("physics")
        plugin.load()
        matches = plugin.match_against(kernel, top_k=5)
    """

    @abstractmethod
    def structure_fingerprint(self) -> StructureFingerprint:
        """
        Compute the structural signature of this domain.

        Should use the domain's loaded Category to compute topology,
        geometry, and spectral features via the existing KOMPOSOS-IV
        analysis modules.
        """
        ...

    @abstractmethod
    def interpret_match(self, match: StructureMatch) -> str:
        """
        Provide a domain-specific interpretation of a structural match.

        Given a match against a math subgraph, explain what it means
        for this domain in human-readable terms.
        """
        ...

    def match_against(self, kernel, top_k: int = 5) -> List[StructureMatch]:
        """
        Match this domain against the math kernel.

        Delegates to kernel.find_structural_matches().
        Must call load() first.

        Args:
            kernel: A MathKernel instance with loaded math data.
            top_k: Number of top matches to return.

        Returns:
            List of StructureMatch, sorted by confidence descending.
        """
        if not self.is_loaded:
            raise RuntimeError("Plugin must be loaded before matching. Call load() first.")
        return kernel.find_structural_matches(self, top_k=top_k)
