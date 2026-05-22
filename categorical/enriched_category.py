# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Enriched Category Theory: Categories over Monoidal Categories

A V-enriched category C replaces hom-SETS with hom-OBJECTS in V:
  - Hom(A,B) in V instead of Hom(A,B) in Set
  - Composition is a V-morphism: Hom(B,C) (x) Hom(A,B) -> Hom(A,C)
  - Identity is a V-morphism: I -> Hom(A,A)

Key instances for KOMPOSOS chemistry:
  - V = ([0,inf], +, 0): Energy quantale -- additive activation energy
  - V = ([0,1], *, 1): Yield quantale -- multiplicative yield composition
  - V = ([0,1], min, 1): Compatibility quantale -- bottleneck compatibility

Mathematical basis:
  - Lawvere, "Metric spaces, generalized logic, and closed categories" (1973)
  - Fong & Spivak, "Seven Sketches in Compositionality", Def 2.46

Ported from KOMPOSOS-III-ARC with chemistry-specific quantales added.
"""

import math
import heapq
from typing import TypeVar, Generic, Dict, Tuple, Callable, List, Optional, Any
from dataclasses import dataclass, field


V = TypeVar('V')


@dataclass
class MonoidalStructure(Generic[V]):
    """
    Defines (V, (x), I) -- the monoidal category we enrich over.

    For a quantale (complete lattice with associative binary operation):
      tensor: V x V -> V (the (x) operation, must be associative)
      unit: V            (identity for (x): I (x) a = a = a (x) I)
      compare: V x V -> bool (the <= ordering for enrichment axioms)

    Examples:
      Energy: ([0,inf], +, 0, <=)  -- additive, lower is better
      Yield:  ([0,1], *, 1, >=)    -- multiplicative, higher is better
      Compat: ([0,1], min, 1, >=)  -- bottleneck, higher is better
    """
    tensor: Callable[[Any, Any], Any]
    unit: Any
    compare: Callable[[Any, Any], bool] = field(default=lambda: lambda a, b: a <= b)
    name: str = "V"

    def __post_init__(self):
        if callable(self.compare) and not isinstance(self.compare, type(lambda: None)):
            pass  # Already a callable


# Pre-built monoidal structures for chemistry

ENERGY_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a + b,
    unit=0.0,
    compare=lambda a, b: a <= b,  # Lower energy is "better"
    name="Energy([0,inf], +, 0)"
)

YIELD_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a * b,
    unit=1.0,
    compare=lambda a, b: a >= b,  # Higher yield is "better"
    name="Yield([0,1], x, 1)"
)

COMPATIBILITY_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: min(a, b),
    unit=1.0,
    compare=lambda a, b: a >= b,  # Higher compatibility is "better"
    name="Compatibility([0,1], min, 1)"
)

COST_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a + b,
    unit=0.0,
    compare=lambda a, b: a <= b,  # Lower cost is "better"
    name="Cost([0,inf], +, 0)"
)

RISK_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: 1 - (1 - a) * (1 - b),  # Probabilistic OR
    unit=0.0,
    compare=lambda a, b: a <= b,  # Lower risk is "better"
    name="Risk([0,1], P-OR, 0)"
)

SUCCESS_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a * b,  # Joint probability
    unit=1.0,
    compare=lambda a, b: a >= b,  # Higher success is "better"
    name="Success([0,1], x, 1)"
)

ACTIVITY_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: min(a, b),  # Bottleneck: weakest link
    unit=1.0,
    compare=lambda a, b: a >= b,  # Higher = better
    name="Activity([0,1], min, 1)"
)

# Generic MATH/CYBER aliases.  Keep the chemistry names above as the primary
# domain vocabulary, but expose the source-repo generic quantales for copied
# reusable modules that are not chemistry-specific.
MULTIPLICATIVE_QUANTALE = YIELD_QUANTALE
ADDITIVE_QUANTALE = COST_QUANTALE
PROBABILISTIC_QUANTALE = RISK_QUANTALE
MIN_QUANTALE = COMPATIBILITY_QUANTALE
STEALTH_QUANTALE = MULTIPLICATIVE_QUANTALE


class EnrichedCategory:
    """
    Category enriched over monoidal category (V, (x), I).

    Instead of Hom-SETS, we have Hom-OBJECTS in V.
    Composition is a V-morphism, not a set function.

    Axioms satisfied:
      1. Identity: I <= Hom(A,A) for all objects A
      2. Composition: Hom(A,B) (x) Hom(B,C) <= Hom(A,C) for all A,B,C
    """

    def __init__(self, monoidal: MonoidalStructure):
        self.monoidal = monoidal
        self.objects: Dict[str, dict] = {}
        self.hom_objects: Dict[Tuple[str, str], Any] = {}
        self._adjacency: Dict[str, List[str]] = {}

    def add_object(self, name: str, metadata: dict = None) -> str:
        """Add an object to the enriched category."""
        self.objects[name] = metadata or {}
        if name not in self._adjacency:
            self._adjacency[name] = []
        # Identity axiom: I <= Hom(A,A)
        self.hom_objects[(name, name)] = self.monoidal.unit
        return name

    def set_hom(self, source: str, target: str, value: Any):
        """
        Set the hom-object Hom(source, target) = value in V.

        For energy: value in [0,inf] is the activation energy.
        For yield: value in [0,1] is the reaction yield.
        For compatibility: value in [0,1] is the interface compatibility.
        """
        if source not in self.objects:
            self.add_object(source)
        if target not in self.objects:
            self.add_object(target)

        self.hom_objects[(source, target)] = value

        if target not in self._adjacency.get(source, []):
            self._adjacency.setdefault(source, []).append(target)

    def get_hom(self, source: str, target: str) -> Optional[Any]:
        """Get the hom-object Hom(source, target)."""
        return self.hom_objects.get((source, target))

    def compose(self, A: str, B: str, C: str) -> Optional[Any]:
        """
        Compute enriched composition: Hom(A,B) (x) Hom(B,C) -> Hom(A,C).

        Returns the (x)-product, or None if either hom-object doesn't exist.
        """
        h_ab = self.hom_objects.get((A, B))
        h_bc = self.hom_objects.get((B, C))
        if h_ab is None or h_bc is None:
            return None
        return self.monoidal.tensor(h_ab, h_bc)

    def path_weight(self, path: List[str]) -> Optional[Any]:
        """
        Compute total weight along a path via iterated (x).

        For energy: sum of individual activation energies.
        For yield: product of individual yields.
        For compatibility: minimum of individual scores.
        """
        if len(path) < 2:
            return self.monoidal.unit

        weight = self.monoidal.unit
        for i in range(len(path) - 1):
            h = self.hom_objects.get((path[i], path[i + 1]))
            if h is None:
                return None
            weight = self.monoidal.tensor(weight, h)
        return weight

    def verify_composition_axiom(self, A: str, B: str, C: str) -> bool:
        """
        Verify: Hom(A,B) (x) Hom(B,C) <= Hom(A,C).

        If Hom(A,C) doesn't exist, the axiom is trivially satisfied.
        """
        composed = self.compose(A, B, C)
        if composed is None:
            return True

        direct = self.hom_objects.get((A, C))
        if direct is None:
            return True

        return self.monoidal.compare(composed, direct)

    def check_commutativity(self, path1: List[str], path2: List[str]) -> Dict[str, Any]:
        """
        Check whether two paths between the same endpoints yield the same
        enriched hom-value. Non-commutativity = contradiction.
        """
        w1 = self.path_weight(path1)
        w2 = self.path_weight(path2)

        result: Dict[str, Any] = {
            "commutes": False,
            "path1_weight": w1,
            "path2_weight": w2,
            "tension": 0.0,
        }

        if w1 is None or w2 is None:
            result["tension"] = 0.0
            return result

        try:
            diff = abs(float(w1) - float(w2))
            result["commutes"] = diff < 1e-9

            if diff < 1e-9:
                result["tension"] = 0.0
            else:
                fw1, fw2 = float(w1), float(w2)
                if fw1 > 0 and fw2 > 0:
                    result["tension"] = abs(math.log(fw1) - math.log(fw2))
                else:
                    result["tension"] = diff
        except (TypeError, ValueError):
            result["commutes"] = w1 == w2
            result["tension"] = 0.0 if result["commutes"] else 1.0

        return result

    def optimal_path(self, source: str, target: str,
                     maximize: bool = True,
                     max_length: int = 10) -> Optional[Tuple[List[str], Any]]:
        """
        Find optimal path from source to target.

        For yield (V = [0,1], (x) = *, maximize=True):
          Highest-yield path: max prod yield_i
          Uses log transform: max prod w_i <-> min sum (-log w_i)

        For energy (V = [0,inf], (x) = +, maximize=False):
          Lowest-energy path: min sum energy_i (standard Dijkstra)

        Args:
            source: Start node
            target: End node
            maximize: True for max-product (yield), False for min-sum (energy)
            max_length: Maximum path length

        Returns:
            (path, total_weight) or None if no path exists
        """
        if source not in self.objects or target not in self.objects:
            return None

        if source == target:
            return ([source], self.monoidal.unit)

        def edge_cost(s: str, t: str) -> float:
            w = self.hom_objects.get((s, t))
            if w is None:
                return float('inf')
            if maximize:
                if w <= 0:
                    return float('inf')
                return -math.log(w)
            else:
                return float(w)

        # Dijkstra's algorithm on transformed weights
        dist: Dict[str, float] = {obj: float('inf') for obj in self.objects}
        prev: Dict[str, Optional[str]] = {obj: None for obj in self.objects}
        path_len: Dict[str, int] = {obj: 0 for obj in self.objects}
        dist[source] = 0.0

        pq = [(0.0, source)]

        while pq:
            d, u = heapq.heappop(pq)

            if d > dist[u]:
                continue

            if u == target:
                break

            if path_len[u] >= max_length:
                continue

            for v in self._adjacency.get(u, []):
                cost = edge_cost(u, v)
                if cost == float('inf'):
                    continue

                new_dist = dist[u] + cost
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    path_len[v] = path_len[u] + 1
                    heapq.heappush(pq, (new_dist, v))

        if dist[target] == float('inf'):
            return None

        path = []
        current = target
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()

        total_weight = self.path_weight(path)
        return (path, total_weight)

    def top_k_paths(self, source: str, target: str,
                    k: int = 5, maximize: bool = True,
                    max_length: int = 10) -> List[Tuple[List[str], Any]]:
        """
        Find top-k optimal paths using Yen's algorithm variant.

        Returns list of (path, weight) tuples sorted by optimality.
        """
        results = []

        best = self.optimal_path(source, target, maximize, max_length)
        if best is None:
            return []
        results.append(best)

        for block_idx in range(1, len(best[0]) - 1):
            blocked_node = best[0][block_idx]

            saved = self._adjacency.get(blocked_node, [])
            saved_incoming = []
            for obj in self.objects:
                if blocked_node in self._adjacency.get(obj, []):
                    saved_incoming.append(obj)

            self._adjacency[blocked_node] = []
            for obj in saved_incoming:
                self._adjacency[obj] = [n for n in self._adjacency[obj] if n != blocked_node]

            alt = self.optimal_path(source, target, maximize, max_length)
            if alt and alt[0] not in [r[0] for r in results]:
                results.append(alt)

            self._adjacency[blocked_node] = saved
            for obj in saved_incoming:
                self._adjacency[obj].append(blocked_node)

            if len(results) >= k:
                break

        if maximize:
            results.sort(key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
        else:
            results.sort(key=lambda x: x[1] if x[1] is not None else float('inf'))

        return results[:k]

    def get_composable_successors(self, node: str) -> List[Tuple[str, Any]]:
        """
        Get all objects reachable from node with their hom-weights.

        Returns: List of (successor, hom_weight) tuples.
        """
        successors = []
        for target in self._adjacency.get(node, []):
            weight = self.hom_objects.get((node, target))
            if weight is not None:
                successors.append((target, weight))
        return successors

    def __repr__(self):
        return (f"EnrichedCategory(V={self.monoidal.name}, "
                f"|Ob|={len(self.objects)}, "
                f"|Hom|={len(self.hom_objects)})")


VEnrichedCategory = EnrichedCategory
