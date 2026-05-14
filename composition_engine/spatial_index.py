# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Spatial Index for Composition Vectors

KD-tree wrapper for O(log N) nearest-neighbor queries over composition
vectors. Replaces the O(N) linear scan in KnownCompositionDB.nearest_k()
when the database exceeds ~500 entries (i.e., when MP data is loaded).

Uses scipy.spatial.KDTree (scipy already in requirements.txt).
For 170K entries with 41-dimensional vectors:
- Build time: <5s
- Query time: <1ms
- Memory: ~56 MB

Usage:
    from composition_engine.spatial_index import CompositionIndex
    index = CompositionIndex(entries, vectors)
    results = index.nearest_k(query_vec, k=5)
    # results: [(entry, distance), ...]
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple

import numpy as np
from scipy.spatial import KDTree


class CompositionIndex:
    """
    KD-tree spatial index over composition vectors.

    Provides O(log N) nearest-neighbor queries instead of O(N) linear scan.

    Args:
        entries: List of objects (any type) to index.
        vectors: Optional pre-computed numpy vectors. If None, entries must
                 have a .vector attribute (np.ndarray).
    """

    def __init__(self, entries: Sequence[Any],
                 vectors: Optional[np.ndarray] = None):
        self._entries = list(entries)

        if vectors is not None:
            self._vectors = np.asarray(vectors, dtype=np.float64)
        else:
            self._vectors = np.array(
                [e.vector for e in self._entries], dtype=np.float64
            )

        if len(self._entries) == 0:
            self._tree = None
        else:
            self._tree = KDTree(self._vectors)

    @property
    def size(self) -> int:
        """Number of indexed entries."""
        return len(self._entries)

    def nearest_k(self, query_vec: np.ndarray, k: int = 5,
                   max_distance: float = float('inf')
                   ) -> List[Tuple[Any, float]]:
        """
        Find k nearest entries to query_vec.

        Args:
            query_vec: Query composition vector (same dimensionality as indexed vectors).
            k: Number of nearest neighbors to return.
            max_distance: Maximum distance threshold. Entries farther than this
                          are excluded from results.

        Returns:
            List of (entry, distance) sorted by ascending distance.
        """
        if self._tree is None or len(self._entries) == 0:
            return []

        # Clamp k to available entries
        k = min(k, len(self._entries))

        query = np.asarray(query_vec, dtype=np.float64)
        distances, indices = self._tree.query(query, k=k)

        # query() returns scalar for k=1, array for k>1
        if k == 1:
            distances = [distances]
            indices = [indices]
        else:
            distances = list(distances)
            indices = list(indices)

        results = []
        for dist, idx in zip(distances, indices):
            if dist <= max_distance and idx < len(self._entries):
                results.append((self._entries[idx], float(dist)))

        return results

    def radius_search(self, query_vec: np.ndarray, radius: float
                       ) -> List[Tuple[Any, float]]:
        """
        Find all entries within radius of query_vec.

        Args:
            query_vec: Query composition vector.
            radius: Search radius (Euclidean distance).

        Returns:
            List of (entry, distance) sorted by ascending distance.
        """
        if self._tree is None or len(self._entries) == 0:
            return []

        query = np.asarray(query_vec, dtype=np.float64)
        indices = self._tree.query_ball_point(query, r=radius)

        results = []
        for idx in indices:
            dist = float(np.linalg.norm(self._vectors[idx] - query))
            results.append((self._entries[idx], dist))

        results.sort(key=lambda x: x[1])
        return results
