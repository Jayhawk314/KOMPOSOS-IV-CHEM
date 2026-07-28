# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for CompositionIndex (KD-tree spatial index).

15 tests covering build, nearest_k, radius_search, sorting,
edge cases, max_distance, and brute-force verification.
"""

import unittest
from dataclasses import dataclass, field

import numpy as np

from composition_engine.spatial_index import CompositionIndex


@dataclass
class MockEntry:
    name: str
    vector: np.ndarray = field(default_factory=lambda: np.zeros(5))


class TestBuild(unittest.TestCase):
    """Test building a CompositionIndex."""

    def test_build_from_entries(self):
        entries = [MockEntry("a", np.array([1, 0, 0, 0, 0])),
                   MockEntry("b", np.array([0, 1, 0, 0, 0]))]
        idx = CompositionIndex(entries)
        self.assertEqual(idx.size, 2)

    def test_build_from_vectors(self):
        entries = [MockEntry("a"), MockEntry("b")]
        vectors = np.array([[1, 0, 0, 0, 0], [0, 1, 0, 0, 0]], dtype=float)
        idx = CompositionIndex(entries, vectors=vectors)
        self.assertEqual(idx.size, 2)

    def test_build_empty(self):
        idx = CompositionIndex([])
        self.assertEqual(idx.size, 0)

    def test_build_single_entry(self):
        idx = CompositionIndex([MockEntry("a", np.array([1, 2, 3, 4, 5]))])
        self.assertEqual(idx.size, 1)


class TestNearestK(unittest.TestCase):
    """Test nearest_k queries."""

    def setUp(self):
        self.entries = [
            MockEntry("origin", np.array([0, 0, 0, 0, 0], dtype=float)),
            MockEntry("one", np.array([1, 0, 0, 0, 0], dtype=float)),
            MockEntry("two", np.array([2, 0, 0, 0, 0], dtype=float)),
            MockEntry("three", np.array([3, 0, 0, 0, 0], dtype=float)),
            MockEntry("far", np.array([10, 0, 0, 0, 0], dtype=float)),
        ]
        self.index = CompositionIndex(self.entries)

    def test_basic_nearest(self):
        query = np.array([0.1, 0, 0, 0, 0], dtype=float)
        results = self.index.nearest_k(query, k=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0].name, "origin")
        self.assertEqual(results[1][0].name, "one")

    def test_results_sorted_by_distance(self):
        query = np.array([1.5, 0, 0, 0, 0], dtype=float)
        results = self.index.nearest_k(query, k=5)
        distances = [d for _, d in results]
        self.assertEqual(distances, sorted(distances))

    def test_exact_match_distance_zero(self):
        query = np.array([1, 0, 0, 0, 0], dtype=float)
        results = self.index.nearest_k(query, k=1)
        self.assertEqual(results[0][0].name, "one")
        self.assertAlmostEqual(results[0][1], 0.0)

    def test_max_distance_filter(self):
        query = np.array([0, 0, 0, 0, 0], dtype=float)
        results = self.index.nearest_k(query, k=5, max_distance=1.5)
        self.assertEqual(len(results), 2)  # origin (0) and one (1)

    def test_k_larger_than_entries(self):
        query = np.array([0, 0, 0, 0, 0], dtype=float)
        results = self.index.nearest_k(query, k=100)
        self.assertEqual(len(results), 5)

    def test_empty_index_returns_empty(self):
        idx = CompositionIndex([])
        results = idx.nearest_k(np.array([0, 0, 0, 0, 0], dtype=float), k=3)
        self.assertEqual(results, [])


class TestRadiusSearch(unittest.TestCase):
    """Test radius_search queries."""

    def setUp(self):
        self.entries = [
            MockEntry("a", np.array([0, 0, 0], dtype=float)),
            MockEntry("b", np.array([0.5, 0, 0], dtype=float)),
            MockEntry("c", np.array([1, 0, 0], dtype=float)),
            MockEntry("d", np.array([5, 0, 0], dtype=float)),
        ]
        self.index = CompositionIndex(self.entries)

    def test_radius_search_basic(self):
        results = self.index.radius_search(
            np.array([0, 0, 0], dtype=float), radius=0.6
        )
        names = {e.name for e, _ in results}
        self.assertIn("a", names)
        self.assertIn("b", names)
        self.assertNotIn("c", names)
        self.assertNotIn("d", names)

    def test_radius_search_sorted(self):
        results = self.index.radius_search(
            np.array([0, 0, 0], dtype=float), radius=2.0
        )
        distances = [d for _, d in results]
        self.assertEqual(distances, sorted(distances))

    def test_radius_search_empty(self):
        results = self.index.radius_search(
            np.array([100, 100, 100], dtype=float), radius=0.1
        )
        self.assertEqual(results, [])

    def test_radius_search_empty_index(self):
        idx = CompositionIndex([])
        results = idx.radius_search(np.array([0, 0, 0], dtype=float), radius=1.0)
        self.assertEqual(results, [])


class TestBruteForceVerification(unittest.TestCase):
    """Verify KD-tree results match brute-force computation."""

    def test_matches_brute_force(self):
        np.random.seed(42)
        n = 200
        dim = 10
        vectors = np.random.rand(n, dim)
        entries = [MockEntry(f"e{i}", vectors[i]) for i in range(n)]
        index = CompositionIndex(entries)

        query = np.random.rand(dim)
        k = 5

        # KD-tree result
        tree_results = index.nearest_k(query, k=k)

        # Brute force
        dists = [(entries[i], float(np.linalg.norm(vectors[i] - query))) for i in range(n)]
        dists.sort(key=lambda x: x[1])
        brute_results = dists[:k]

        for (tree_entry, tree_dist), (brute_entry, brute_dist) in zip(tree_results, brute_results):
            self.assertEqual(tree_entry.name, brute_entry.name)
            self.assertAlmostEqual(tree_dist, brute_dist, places=10)


if __name__ == "__main__":
    unittest.main()
