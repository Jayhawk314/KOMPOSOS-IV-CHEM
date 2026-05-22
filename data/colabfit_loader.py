"""
ColabFit Exchange REST API Client + Empirical Bond Statistics
=============================================================

Provides empirical bond-length distributions for ZFC physical constraints.

Primary source: Literature-derived Gaussian CDFs from crystallographic
statistics (Gagne & Hawthorne 2015, ICSD 2020, Vurgaftman 2001).

Secondary source (future): ColabFit Exchange REST API for live data.

Includes SQLite caching for offline use and improved performance.
"""

import math
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from data.empirical_bond_statistics import EMPIRICAL_BOND_STATS, get_stats


def _norm_cdf(x: float, mean: float, std: float) -> float:
    """Gaussian CDF using the built-in math.erf (no scipy needed)."""
    if std <= 0:
        return 1.0 if x >= mean else 0.0
    z = (x - mean) / (std * math.sqrt(2))
    return 0.5 * (1.0 + math.erf(z))


@dataclass
class BondDistribution:
    distances: List[float]
    probabilities: List[float]

    def cdf(self, distance: float) -> float:
        """Return the cumulative probability at a given distance."""
        if not self.distances:
            return 0.0
        if distance < self.distances[0]:
            return 0.0
        if distance > self.distances[-1]:
            return 1.0

        # Linear interpolation
        for i in range(len(self.distances) - 1):
            if self.distances[i] <= distance <= self.distances[i + 1]:
                d0, d1 = self.distances[i], self.distances[i + 1]
                p0, p1 = self.probabilities[i], self.probabilities[i + 1]
                return p0 + (p1 - p0) * (distance - d0) / (d1 - d0)
        return 1.0


class SQLiteCache:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bond_cache (
                    pair TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def get(self, pair: str) -> Optional[BondDistribution]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data FROM bond_cache WHERE pair = ?", (pair,))
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return BondDistribution(distances=data["distances"], probabilities=data["probabilities"])
        return None

    def set(self, pair: str, dist: BondDistribution):
        with sqlite3.connect(self.db_path) as conn:
            data = json.dumps({"distances": dist.distances, "probabilities": dist.probabilities})
            conn.execute("INSERT OR REPLACE INTO bond_cache (pair, data) VALUES (?, ?)", (pair, data))


class ColabFitClient:
    """
    Bond-length distribution provider.

    Lookup order:
    1. SQLite cache (sub-ms)
    2. Empirical statistics from crystallographic literature (43 pairs)
    3. ColabFit Exchange REST API (when available)
    4. Triangular CDF from BOND_LENGTH_BOUNDS (last resort)
    """

    def __init__(self, cache_path: Optional[Path] = None):
        self.base_url = "https://materials.colabfit.org/api"
        if cache_path is None:
            cache_path = Path("data/cache/colabfit_cache.db")
        self.cache = SQLiteCache(cache_path)

        # ColabFit dataset IDs for future live API integration
        self.standard_datasets = {
            ("O", "Si"): "2022--Erhard-L-C-Rohrer-J-Albe-K-Deringer-V-L--Si-O",
        }

    def get_bond_distribution(self, elem_a: str, elem_b: str,
                              bounds: Optional[Tuple[float, float]] = None) -> BondDistribution:
        """
        Get empirical CDF of bond lengths for (elem_a, elem_b).

        Args:
            elem_a, elem_b: Element symbols.
            bounds: Optional (min_angstrom, max_angstrom) from BOND_LENGTH_BOUNDS.
                Used as last-resort fallback.
        """
        sorted_pair = tuple(sorted([elem_a, elem_b]))
        pair_str = "-".join(sorted_pair)

        # 1. Check cache
        cached = self.cache.get(pair_str)
        if cached:
            return cached

        # 2. Build from empirical crystallographic statistics (primary source)
        dist = self._empirical_distribution(elem_a, elem_b)
        if dist is not None:
            self.cache.set(pair_str, dist)
            return dist

        # 3. Try ColabFit API (secondary, for future expansion)
        ds_id = self.standard_datasets.get(sorted_pair)
        if ds_id:
            api_dist = self._fetch_from_api(ds_id, pair_str)
            if api_dist is not None:
                self.cache.set(pair_str, api_dist)
                return api_dist

        # 4. Construct from BOND_LENGTH_BOUNDS if provided
        if bounds is not None:
            dist = self._distribution_from_bounds(bounds)
            self.cache.set(pair_str, dist)
            return dist

        # 5. Generic fallback (should rarely reach here)
        dist = self._generic_fallback()
        self.cache.set(pair_str, dist)
        return dist

    def _empirical_distribution(self, elem_a: str, elem_b: str) -> Optional[BondDistribution]:
        """
        Build a 21-point Gaussian CDF from published crystallographic statistics.

        Uses mean and std from Gagne & Hawthorne 2015, ICSD 2020, etc.
        The CDF spans mean +/- 4*std to capture 99.99% of the distribution.
        """
        stats = get_stats(elem_a, elem_b)
        if stats is None:
            return None

        mean = stats["mean"]
        std = stats["std"]
        n_points = 21
        start = mean - 4 * std
        end = mean + 4 * std
        step = (end - start) / (n_points - 1)

        distances = [start + i * step for i in range(n_points)]
        probabilities = [_norm_cdf(d, mean, std) for d in distances]
        return BondDistribution(distances=distances, probabilities=probabilities)

    def _fetch_from_api(self, ds_id: str, pair_str: str) -> Optional[BondDistribution]:
        """Attempt to fetch from ColabFit Exchange REST API."""
        try:
            import requests
            url = f"{self.base_url}/dataset/{ds_id}/bond-length-distribution"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                bins = data["bins"]
                counts = data["counts"]
                total = sum(counts)
                probabilities = []
                acc = 0
                for c in counts:
                    acc += c
                    probabilities.append(acc / total if total > 0 else 0)
                distances = bins[:-1]
                return BondDistribution(distances=distances, probabilities=probabilities)
        except Exception:
            pass  # Silently fall through to next source
        return None

    def _distribution_from_bounds(self, bounds: Tuple[float, float]) -> BondDistribution:
        """
        Construct a triangular CDF from known min/max bounds.
        CDF rises from 0 at min to 0.5 at midpoint to 1.0 at max.
        """
        min_d, max_d = bounds
        mid = (min_d + max_d) / 2.0
        margin = 0.2
        start = min_d - margin
        end = max_d + margin
        n = 11
        step = (end - start) / (n - 1)
        distances = [start + i * step for i in range(n)]

        probabilities = []
        for d in distances:
            if d <= min_d:
                probabilities.append(0.0)
            elif d >= max_d:
                probabilities.append(1.0)
            elif d <= mid:
                probabilities.append(0.5 * (d - min_d) / (mid - min_d))
            else:
                probabilities.append(0.5 + 0.5 * (d - mid) / (max_d - mid))
        return BondDistribution(distances=distances, probabilities=probabilities)

    def _generic_fallback(self) -> BondDistribution:
        """Generic fallback for completely unknown pairs (low confidence)."""
        return BondDistribution(
            distances=[1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
            probabilities=[0.0, 0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95, 0.98, 1.0, 1.0]
        )


if __name__ == "__main__":
    client = ColabFitClient()

    # Verify empirical distributions work
    pairs_to_test = [("Li", "O"), ("Si", "O"), ("Ga", "As"), ("Fe", "O"), ("P", "O")]
    for a, b in pairs_to_test:
        stats = get_stats(a, b)
        dist = client.get_bond_distribution(a, b)
        mean = stats["mean"]
        p_at_mean = dist.cdf(mean)
        print(f"{a}-{b}: mean={mean:.2f}A, CDF(mean)={p_at_mean:.3f}, "
              f"source={stats['source']}, N={stats['n_obs']}")
