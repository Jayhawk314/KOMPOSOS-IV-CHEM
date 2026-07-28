# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Math Discovery Strategy — Oracle strategy backed by MathKernel.

Uses the MathKernel's 3-source convergence to predict missing morphisms.
When the kernel's topology/geometry/spectral analysis detect convergent
signals across independent sources, those signals become predictions.

This wires MathKernel into the Oracle's 8-strategy prediction pipeline
so that math discovery becomes a first-class inference method alongside
Kan extensions, Yoneda patterns, and composition paths.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from oracle.strategies import InferenceStrategy
from oracle.prediction import Prediction, PredictionType, ConfidenceLevel
from core.category import Category

if TYPE_CHECKING:
    from domains.mathematics.kernel import MathKernel


class MathDiscoveryStrategy(InferenceStrategy):
    """
    Oracle strategy that uses MathKernel convergent analysis.

    For a given (source, target) pair, checks whether multiple
    independent math sources (LeanDojo, MMLKG, NaturalProofs) show
    structural evidence for a relationship. Convergent signals from
    2+ sources yield high-confidence predictions.

    Also uses the kernel's anchor problem proximity to boost
    predictions near Millennium Prize problems.
    """

    name = "math_discovery"

    def __init__(self, category: Category, kernel: Optional[MathKernel] = None):
        super().__init__(category)
        self._kernel = kernel

    @property
    def kernel(self) -> Optional[MathKernel]:
        if self._kernel is None:
            try:
                from domains.mathematics.kernel import MathKernel
                self._kernel = MathKernel(db_dir=":memory:")
            except Exception:
                pass
        return self._kernel

    def predict(self, source: str, target: str) -> List[Prediction]:
        """
        Predict relationship between source and target using MathKernel.

        Checks:
        1. Whether both objects exist in multiple sources (cross-source evidence)
        2. Whether there's a structural path in any source
        3. Whether anchor problem proximity suggests a connection
        """
        if self.kernel is None:
            return []

        predictions = []

        # Strategy 1: Cross-source evidence
        # If both objects appear in 2+ independent graphs, there's structural
        # evidence for a relationship
        source_appearances = self._count_source_appearances(source)
        target_appearances = self._count_source_appearances(target)

        if source_appearances >= 2 and target_appearances >= 2:
            # Both objects confirmed in multiple independent sources
            confidence = min(source_appearances, target_appearances) / 3.0
            predictions.append(Prediction(
                source=source,
                target=target,
                relation="cross_source_convergent",
                confidence=min(confidence, 0.95),
                prediction_type=PredictionType.STRUCTURAL,
                strategy="math_discovery:cross_source",
                explanation=(
                    f"Both objects appear in {source_appearances}/{target_appearances} "
                    f"independent math sources (convergent evidence)"
                ),
            ))

        # Strategy 2: Path existence in any source
        for name, cat in self.kernel.sources.items():
            if len(cat.objects()) == 0:
                continue

            src_obj = cat.get(source)
            tgt_obj = cat.get(target)
            if src_obj and tgt_obj:
                paths = cat.find_paths(source, target, max_length=4)
                if paths:
                    shortest = min(p.length for p in paths)
                    path_confidence = 0.9 / shortest  # shorter path = higher confidence
                    predictions.append(Prediction(
                        source=source,
                        target=target,
                        relation=f"path_in_{name}",
                        confidence=min(path_confidence, 0.9),
                        prediction_type=PredictionType.COMPOSITIONAL,
                        strategy=f"math_discovery:path_{name}",
                        explanation=(
                            f"Path of length {shortest} found in {name} source"
                        ),
                    ))

        # Strategy 3: Anchor proximity boost
        try:
            source_anchors = self.kernel.anchor_proximity(source)
            target_anchors = self.kernel.anchor_proximity(target)

            # If both are near the same anchor problem, boost prediction
            shared_anchors = set(source_anchors.keys()) & set(target_anchors.keys())
            for anchor in shared_anchors:
                s_dist = source_anchors[anchor]
                t_dist = target_anchors[anchor]
                if s_dist > 0 and t_dist > 0:
                    anchor_confidence = (s_dist + t_dist) / 2.0
                    predictions.append(Prediction(
                        source=source,
                        target=target,
                        relation=f"anchor:{anchor}",
                        confidence=min(anchor_confidence, 0.8),
                        prediction_type=PredictionType.STRUCTURAL,
                        strategy="math_discovery:anchor",
                        explanation=(
                            f"Both near anchor problem '{anchor}' "
                            f"(proximity {s_dist:.2f}/{t_dist:.2f})"
                        ),
                    ))
        except Exception:
            pass

        return predictions

    def _count_source_appearances(self, obj_name: str) -> int:
        """Count how many independent sources contain this object."""
        if self.kernel is None:
            return 0
        count = 0
        for cat in self.kernel.sources.values():
            if cat.get(obj_name) is not None:
                count += 1
        return count
