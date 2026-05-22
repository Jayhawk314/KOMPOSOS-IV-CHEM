# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Bridge Scoring -- Five-Layer Composite Scoring

Ranks cross-domain bridges by combining five independent signals:
  Layer 1: Edge scoring (confidence * fan-out * age-gap penalty)
  Layer 2: Anchor problem proximity (distance to Millennium/Hilbert)
  Layer 3: Functor match strength (functorial correspondence)
  Layer 4: Topology gap signal (persistent homology holes nearby)
  Layer 5: Granger break-point signal (temporal causality)

A bridge scoring high on ALL layers simultaneously is the real signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING

from core.category import Category

if TYPE_CHECKING:
    from domains.plugin_interface import DomainPlugin
    from domains.mathematics.kernel import MathKernel


@dataclass
class ScoringConfig:
    """Weights for each scoring layer."""

    edge_weight: float = 0.25
    anchor_weight: float = 0.20
    functor_weight: float = 0.25
    topology_weight: float = 0.15
    granger_weight: float = 0.15
    age_gap_decay: float = 0.01  # per-year decay factor


@dataclass
class BridgeScore:
    """Composite score for a cross-domain bridge."""

    source: str
    target: str
    raw_score: float
    layer_scores: Dict[str, float]
    confidence: float

    def __repr__(self) -> str:
        layers = ", ".join(f"{k}={v:.3f}" for k, v in self.layer_scores.items())
        return (
            f"BridgeScore({self.source} -> {self.target}, "
            f"conf={self.confidence:.3f}, [{layers}])"
        )


class BridgeScorer:
    """
    Computes composite bridge scores using five analysis layers.

    Each layer produces a score in [0, 1]. The composite score is
    a weighted sum of all layers, normalized to [0, 1].
    """

    def __init__(
        self,
        kernel: MathKernel,
        config: Optional[ScoringConfig] = None,
    ):
        self.kernel = kernel
        self.config = config or ScoringConfig()

    def score_edge(
        self,
        source: str,
        target: str,
        category: Category,
    ) -> float:
        """
        Layer 1: Edge scoring with fan-out and age-gap penalty.

        Score = confidence * sqrt(fan_out) / max_fan_out * age_factor

        High fan-out = structurally important (many theorems depend on this).
        Large age gap = bridge was hard to see (higher value).
        """
        # Get morphism confidence
        hom_val = category.hom(source, target)
        if hom_val <= 0:
            return 0.0

        # Fan-out of target (how many things depend on it)
        fan_out = len(category.morphisms_from(target))
        max_fan = max(
            len(category.morphisms_from(obj.name))
            for obj in category.objects()
        ) if category.objects() else 1
        fan_score = math.sqrt(fan_out) / math.sqrt(max(max_fan, 1))

        # Age gap penalty/bonus
        age_factor = 1.0
        src_obj = category.get(source)
        tgt_obj = category.get(target)
        if src_obj and tgt_obj:
            src_year = src_obj.metadata.get("year")
            tgt_year = tgt_obj.metadata.get("year")
            if src_year is not None and tgt_year is not None:
                gap = abs(int(src_year) - int(tgt_year))
                # Larger gap = harder bridge = more valuable
                age_factor = 1.0 + self.config.age_gap_decay * gap

        score = hom_val * fan_score * min(age_factor, 2.0)
        return min(1.0, score)

    def score_anchor_proximity(
        self,
        obj_name: str,
        source_name: str,
    ) -> float:
        """
        Layer 2: How close is this object to an anchor problem?

        Uses optimal_path() via the multiplicative quantale.
        Closer to anchor = higher score.
        """
        from domains.mathematics.anchor_problems import AnchorProblems

        source_cat = self.kernel.sources.get(source_name)
        if source_cat is None:
            return 0.0

        anchors = AnchorProblems(source_cat)
        nearest = anchors.nearest_anchor(obj_name)
        if nearest is None:
            return 0.0

        # Path weight is in [0, 1] for multiplicative quantale
        return nearest[1]

    def score_functor_match(
        self,
        plugin: DomainPlugin,
        math_category: Category,
    ) -> float:
        """
        Layer 3: Strength of functorial correspondence.

        Attempts to build a Functor from plugin.category to math_category.
        Score based on how much structure is preserved.
        """
        try:
            plugin_objs = plugin.category.objects()
            math_objs = math_category.objects()

            if not plugin_objs or not math_objs:
                return 0.0

            # Simple type-based object map
            from domains.mathematics.structure_match import StructureMatcher
            object_map = StructureMatcher._build_object_map(plugin_objs, math_objs)

            if not object_map:
                return 0.0

            functor = plugin.category.functor_to(math_category, object_map=object_map)
            verification = functor.verify()
            return sum(1 for v in verification.values() if v) / max(len(verification), 1)
        except Exception:
            return 0.0

    def score_topology_gap(
        self,
        obj_name: str,
        category: Category,
    ) -> float:
        """
        Layer 4: Proximity to persistent homology holes.

        H1 features (loops) near this object indicate unsolved clusters.
        Score is higher when the object is in a topologically interesting region.
        """
        try:
            from topology.persistent_homology import SimplicialComplex, PersistentHomologyComputer

            edges = category.as_edges()
            if not edges:
                return 0.0

            # Build complex
            node_to_idx: Dict[str, int] = {}
            idx_edges = []
            for s, t, w in edges:
                for n in (s, t):
                    if n not in node_to_idx:
                        node_to_idx[n] = len(node_to_idx)
                idx_edges.append((node_to_idx[s], node_to_idx[t]))

            sc = SimplicialComplex()
            sc.build_flag_complex(idx_edges, max_dim=2)
            computer = PersistentHomologyComputer()
            diagram = computer.compute(sc)

            # Count H1 features (loops)
            h1_features = [p for p in diagram.pairs if p.dimension == 1]
            if not h1_features:
                return 0.0

            # Score based on total H1 persistence
            total_persistence = sum(p.persistence for p in h1_features)
            # Normalize by number of edges
            score = min(1.0, total_persistence / max(len(edges), 1))

            return score
        except Exception:
            return 0.0

    def score_granger(
        self,
        obj_name: str,
        category: Category,
    ) -> float:
        """
        Layer 5: Granger break-point signal.

        Higher score if the object's field shows Granger causality
        breakpoints (periods of unusual activity).
        """
        try:
            from domains.mathematics.granger import GrangerAnalyzer

            obj = category.get(obj_name)
            if obj is None:
                return 0.0

            field = obj.metadata.get("field", "")
            if not field:
                return 0.0

            analyzer = GrangerAnalyzer(category)
            breakpoints = analyzer.find_breakpoints(field_filter=field, z_threshold=1.5)

            if not breakpoints:
                return 0.0

            # Score based on number and magnitude of breakpoints
            max_mag = max(bp.magnitude for bp in breakpoints)
            score = min(1.0, max_mag / 5.0)  # z=5 maps to 1.0
            return score
        except Exception:
            return 0.0

    def composite_score(
        self,
        source: str,
        target: str,
        category: Category,
        source_name: str = "",
        plugin: Optional[DomainPlugin] = None,
    ) -> BridgeScore:
        """
        Compute weighted composite of all 5 layers.

        Returns BridgeScore with per-layer breakdown.
        """
        scores: Dict[str, float] = {}

        # Layer 1: Edge scoring
        scores["edge"] = self.score_edge(source, target, category)

        # Layer 2: Anchor proximity (on target side)
        scores["anchor"] = self.score_anchor_proximity(target, source_name)

        # Layer 3: Functor match
        if plugin is not None:
            scores["functor"] = self.score_functor_match(plugin, category)
        else:
            scores["functor"] = 0.0

        # Layer 4: Topology gap
        scores["topology"] = self.score_topology_gap(target, category)

        # Layer 5: Granger
        scores["granger"] = self.score_granger(target, category)

        # Weighted sum
        raw = (
            self.config.edge_weight * scores["edge"]
            + self.config.anchor_weight * scores["anchor"]
            + self.config.functor_weight * scores["functor"]
            + self.config.topology_weight * scores["topology"]
            + self.config.granger_weight * scores["granger"]
        )

        return BridgeScore(
            source=source,
            target=target,
            raw_score=raw,
            layer_scores=scores,
            confidence=min(1.0, raw),
        )

    def rank_bridges(
        self,
        category: Category,
        source_name: str = "",
        plugin: Optional[DomainPlugin] = None,
        top_k: int = 20,
    ) -> list:
        """
        Score all edges in a category and return top-k bridges.

        Returns list of BridgeScore sorted by confidence descending.
        """
        edges = category.as_edges()
        scores = []
        for source, target, weight in edges:
            score = self.composite_score(
                source, target, category,
                source_name=source_name,
                plugin=plugin,
            )
            scores.append(score)

        scores.sort(key=lambda s: s.confidence, reverse=True)
        return scores[:top_k]
