# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Temporal Granger Causality Analyzer

Tests whether the discovery timeline of mathematical field A
Granger-causes changes in field B. Uses arXiv publication timelines
and Object metadata (year fields).

Granger causality: A Granger-causes B if past values of A improve
prediction of B beyond what past values of B alone provide.

Implementation uses OLS regression and F-test (no external deps).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.category import Category


@dataclass
class GrangerResult:
    """Result of a Granger causality test between two time series."""

    source_field: str
    target_field: str
    f_statistic: float
    p_value: float
    optimal_lag: int
    is_causal: bool  # p_value < threshold
    direction: str = ""  # "A -> B", "B -> A", or "bidirectional"

    def __repr__(self) -> str:
        arrow = "->" if self.is_causal else "-/>"
        return (
            f"GrangerResult({self.source_field} {arrow} {self.target_field}, "
            f"F={self.f_statistic:.2f}, p={self.p_value:.4f}, lag={self.optimal_lag})"
        )


@dataclass
class BreakpointResult:
    """A detected breakpoint in a timeline."""

    year: int
    field: str
    magnitude: float  # z-score of the change
    direction: str  # "surge" or "decline"

    def __repr__(self) -> str:
        return f"Breakpoint({self.field}, {self.year}, {self.direction}, z={self.magnitude:.2f})"


class GrangerAnalyzer:
    """
    Granger causality on mathematical discovery timelines.

    Analyzes whether activity in one mathematical field predicts
    future activity in another. Requires Objects with year metadata.
    """

    def __init__(self, category: Category, time_field: str = "year"):
        self.category = category
        self.time_field = time_field

    def build_timeline(
        self, field_filter: Optional[str] = None
    ) -> Dict[int, int]:
        """
        Count objects per year, optionally filtered by mathematical field.

        Returns dict of {year: count}, sorted by year.
        """
        counts: Dict[int, int] = defaultdict(int)
        for obj in self.category.objects():
            year = obj.metadata.get(self.time_field)
            if year is None:
                continue
            year = int(year)
            if field_filter is not None:
                obj_field = obj.metadata.get("field", "")
                if obj_field != field_filter:
                    continue
            counts[year] += 1
        return dict(sorted(counts.items()))

    def available_fields(self) -> List[str]:
        """Return all mathematical fields present in the category."""
        fields = set()
        for obj in self.category.objects():
            f = obj.metadata.get("field", "")
            if f:
                fields.add(f)
        return sorted(fields)

    def granger_test(
        self,
        series_a: List[float],
        series_b: List[float],
        max_lag: int = 5,
        significance: float = 0.05,
    ) -> GrangerResult:
        """
        Granger causality test: does series A Granger-cause series B?

        Uses F-test comparing restricted model (only B lags) vs
        unrestricted model (A + B lags).

        Args:
            series_a: Time series for potential cause.
            series_b: Time series for potential effect.
            max_lag: Maximum lag to test.
            significance: P-value threshold for significance.

        Returns:
            GrangerResult with best lag.
        """
        n = min(len(series_a), len(series_b))
        if n < max_lag + 3:
            return GrangerResult(
                source_field="A", target_field="B",
                f_statistic=0.0, p_value=1.0, optimal_lag=1, is_causal=False,
            )

        best_f = 0.0
        best_p = 1.0
        best_lag = 1

        for lag in range(1, max_lag + 1):
            f_stat, p_val = self._f_test_at_lag(series_a, series_b, lag, n)
            if f_stat > best_f:
                best_f = f_stat
                best_p = p_val
                best_lag = lag

        return GrangerResult(
            source_field="A",
            target_field="B",
            f_statistic=best_f,
            p_value=best_p,
            optimal_lag=best_lag,
            is_causal=best_p < significance,
        )

    def _f_test_at_lag(
        self,
        series_a: List[float],
        series_b: List[float],
        lag: int,
        n: int,
    ) -> Tuple[float, float]:
        """
        F-test for Granger causality at a specific lag.

        Restricted model: B_t = sum(beta_i * B_{t-i}) + e
        Unrestricted model: B_t = sum(beta_i * B_{t-i}) + sum(alpha_i * A_{t-i}) + e

        F = ((RSS_r - RSS_u) / lag) / (RSS_u / (n - 2*lag - 1))
        """
        effective_n = n - lag

        # Build lagged matrices
        y = [series_b[t] for t in range(lag, n)]
        x_restricted = []
        x_unrestricted = []

        for t in range(lag, n):
            row_r = [series_b[t - i - 1] for i in range(lag)]
            row_u = row_r + [series_a[t - i - 1] for i in range(lag)]
            x_restricted.append(row_r)
            x_unrestricted.append(row_u)

        # OLS via normal equations
        rss_r = self._ols_rss(x_restricted, y)
        rss_u = self._ols_rss(x_unrestricted, y)

        # F-statistic
        df_num = lag
        df_den = effective_n - 2 * lag - 1
        if df_den <= 0 or rss_u <= 0:
            return 0.0, 1.0

        f_stat = ((rss_r - rss_u) / df_num) / (rss_u / df_den)
        f_stat = max(0.0, f_stat)

        # Approximate p-value using F-distribution CDF
        p_value = self._f_distribution_p(f_stat, df_num, df_den)

        return f_stat, p_value

    def _ols_rss(self, x_matrix: List[List[float]], y: List[float]) -> float:
        """
        Compute residual sum of squares for OLS regression.

        Uses normal equations: beta = (X'X)^-1 X'y, RSS = ||y - X*beta||^2
        Falls back to mean model if matrix is singular.
        """
        n = len(y)
        p = len(x_matrix[0]) if x_matrix and x_matrix[0] else 0

        if p == 0 or n <= p:
            mean_y = sum(y) / n if n > 0 else 0
            return sum((yi - mean_y) ** 2 for yi in y)

        # X'X
        xtx = [[0.0] * p for _ in range(p)]
        for i in range(p):
            for j in range(p):
                for k in range(n):
                    xtx[i][j] += x_matrix[k][i] * x_matrix[k][j]

        # X'y
        xty = [0.0] * p
        for i in range(p):
            for k in range(n):
                xty[i] += x_matrix[k][i] * y[k]

        # Solve via Gaussian elimination
        beta = self._solve_linear(xtx, xty)
        if beta is None:
            mean_y = sum(y) / n
            return sum((yi - mean_y) ** 2 for yi in y)

        # RSS = sum((y_i - x_i . beta)^2)
        rss = 0.0
        for k in range(n):
            pred = sum(x_matrix[k][j] * beta[j] for j in range(p))
            rss += (y[k] - pred) ** 2

        return rss

    @staticmethod
    def _solve_linear(
        a: List[List[float]], b: List[float]
    ) -> Optional[List[float]]:
        """Solve Ax = b via Gaussian elimination with partial pivoting."""
        n = len(b)
        # Augmented matrix
        aug = [row[:] + [b[i]] for i, row in enumerate(a)]

        for col in range(n):
            # Partial pivoting
            max_row = col
            for row in range(col + 1, n):
                if abs(aug[row][col]) > abs(aug[max_row][col]):
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            if abs(aug[col][col]) < 1e-12:
                return None  # Singular

            # Eliminate below
            for row in range(col + 1, n):
                factor = aug[row][col] / aug[col][col]
                for j in range(col, n + 1):
                    aug[row][j] -= factor * aug[col][j]

        # Back substitution
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            x[i] = aug[i][n]
            for j in range(i + 1, n):
                x[i] -= aug[i][j] * x[j]
            x[i] /= aug[i][i]

        return x

    @staticmethod
    def _f_distribution_p(f_stat: float, df1: int, df2: int) -> float:
        """
        Approximate p-value from F-distribution.

        Uses the approximation: for large df2, F * df1 ~ chi-squared(df1).
        For smaller df, uses a rougher heuristic based on the beta function.
        """
        if f_stat <= 0 or df1 <= 0 or df2 <= 0:
            return 1.0

        # Use the regularized incomplete beta function approximation
        # P(F > f) = I_x(df2/2, df1/2) where x = df2 / (df2 + df1 * f)
        x = df2 / (df2 + df1 * f_stat)

        # Simple series approximation of regularized incomplete beta
        a = df2 / 2.0
        b = df1 / 2.0

        # For large df2, use chi-squared approximation
        if df2 > 30:
            chi2 = f_stat * df1
            # Chi-squared CDF via Wilson-Hilferty approximation
            z = ((chi2 / df1) ** (1 / 3) - (1 - 2 / (9 * df1))) / math.sqrt(
                2 / (9 * df1)
            )
            # Normal CDF approximation
            p = 0.5 * (1.0 + math.erf(-z / math.sqrt(2)))
            return max(0.0, min(1.0, p))

        # Rough heuristic for smaller samples
        # F > 4 is usually significant at 0.05, F > 7 at 0.01
        if f_stat > 10:
            return 0.001
        elif f_stat > 7:
            return 0.01
        elif f_stat > 4:
            return 0.05
        elif f_stat > 2.5:
            return 0.10
        elif f_stat > 1.5:
            return 0.25
        else:
            return 0.50

    def analyze_field_causality(
        self,
        field_a: str,
        field_b: str,
        max_lag: int = 5,
        significance: float = 0.05,
    ) -> GrangerResult:
        """
        Test if field A Granger-causes field B.

        Builds publication timelines from Object metadata, aligns them,
        and runs the Granger test.
        """
        timeline_a = self.build_timeline(field_a)
        timeline_b = self.build_timeline(field_b)

        if not timeline_a or not timeline_b:
            return GrangerResult(
                source_field=field_a,
                target_field=field_b,
                f_statistic=0.0,
                p_value=1.0,
                optimal_lag=1,
                is_causal=False,
            )

        # Align timelines to common year range
        all_years = sorted(set(timeline_a) | set(timeline_b))
        if len(all_years) < max_lag + 3:
            return GrangerResult(
                source_field=field_a,
                target_field=field_b,
                f_statistic=0.0,
                p_value=1.0,
                optimal_lag=1,
                is_causal=False,
            )

        series_a = [float(timeline_a.get(y, 0)) for y in all_years]
        series_b = [float(timeline_b.get(y, 0)) for y in all_years]

        result = self.granger_test(series_a, series_b, max_lag, significance)
        result.source_field = field_a
        result.target_field = field_b
        result.direction = f"{field_a} -> {field_b}" if result.is_causal else ""
        return result

    def all_pairwise(
        self,
        fields: Optional[List[str]] = None,
        max_lag: int = 5,
        significance: float = 0.05,
    ) -> List[GrangerResult]:
        """
        Run Granger tests for all pairs of fields.

        Returns only significant (causal) results, sorted by F-statistic.
        """
        if fields is None:
            fields = self.available_fields()

        results = []
        for i, fa in enumerate(fields):
            for j, fb in enumerate(fields):
                if i == j:
                    continue
                result = self.analyze_field_causality(fa, fb, max_lag, significance)
                if result.is_causal:
                    results.append(result)

        results.sort(key=lambda r: r.f_statistic, reverse=True)
        return results

    def find_breakpoints(
        self,
        field_filter: Optional[str] = None,
        window: int = 5,
        z_threshold: float = 2.0,
    ) -> List[BreakpointResult]:
        """
        Detect breakpoints (sudden changes) in a timeline.

        A breakpoint is a year where the count changes by more than
        z_threshold standard deviations from the rolling mean.
        """
        timeline = self.build_timeline(field_filter)
        if len(timeline) < window + 1:
            return []

        years = sorted(timeline.keys())
        counts = [timeline[y] for y in years]
        breakpoints = []

        for i in range(window, len(counts)):
            window_vals = counts[i - window : i]
            mean = sum(window_vals) / len(window_vals)
            variance = sum((v - mean) ** 2 for v in window_vals) / len(window_vals)
            std = math.sqrt(variance) if variance > 0 else 1.0

            z_score = (counts[i] - mean) / std
            if abs(z_score) > z_threshold:
                breakpoints.append(
                    BreakpointResult(
                        year=years[i],
                        field=field_filter or "all",
                        magnitude=abs(z_score),
                        direction="surge" if z_score > 0 else "decline",
                    )
                )

        breakpoints.sort(key=lambda b: b.magnitude, reverse=True)
        return breakpoints

    def causal_chain(
        self, fields: Optional[List[str]] = None, max_lag: int = 5
    ) -> Dict[str, List[str]]:
        """
        Build causal chain: for each field, list fields it Granger-causes.

        Returns adjacency dict of the causal DAG.
        """
        if fields is None:
            fields = self.available_fields()

        results = self.all_pairwise(fields, max_lag)
        chain: Dict[str, List[str]] = defaultdict(list)
        for r in results:
            chain[r.source_field].append(r.target_field)
        return dict(chain)
