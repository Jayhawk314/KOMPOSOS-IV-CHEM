# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Kan Extension Machine Learning Wrapper

Connects Kan extensions to embeddings for ML-style learning tasks.
Left Kan extensions generalize from labeled training data to unlabeled
objects; right Kan extensions synthesize requirements from goals.

This module provides:
- KanLearner: supervised learning via Kan extension + embeddings
- predict: evaluate Kan extension at a specific object
- cross_validate: leave-k-out validation using Kan machinery
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import random

import numpy as np

from core.category import Category
from core.types import Object, Morphism


@dataclass
class KanLearner:
    """
    ML-specific layer on top of Kan extensions.

    Uses the category's morphism structure and optional embeddings
    to generalize from labeled training data to unlabeled objects.

    Usage:
        learner = KanLearner(category)
        learner.set_label("A", "positive")
        learner.set_label("B", "negative")
        learner.learn()
        prediction = learner.predict("C")
    """
    category: Category
    _labels: Dict[str, Any] = field(default_factory=dict)
    _predictions: Dict[str, Tuple[Any, float]] = field(default_factory=dict)
    _trained: bool = False

    def set_label(self, object_name: str, label: Any) -> None:
        """Assign a label to a training object."""
        self._labels[object_name] = label
        self._trained = False

    def set_labels(self, labels: Dict[str, Any]) -> None:
        """Assign multiple labels at once."""
        self._labels.update(labels)
        self._trained = False

    def learn(self) -> None:
        """
        Train the learner using Left Kan Extension logic.

        For each unlabeled object, aggregates labels from connected
        labeled objects weighted by morphism confidence (enriched
        hom-values), implementing a colimit-style combination.
        """
        self._predictions.clear()
        all_objects = self.category.objects()
        labeled_names = set(self._labels.keys())

        for obj in all_objects:
            if obj.name in labeled_names:
                self._predictions[obj.name] = (self._labels[obj.name], 1.0)
                continue

            # Collect labels from all paths to labeled objects
            values: List[Tuple[Any, float]] = []

            for labeled_name in labeled_names:
                # Forward paths: labeled -> obj
                paths = self.category.find_paths(labeled_name, obj.name, max_length=5)
                for path in paths:
                    values.append((self._labels[labeled_name], path.weight))

                # Reverse paths: obj -> labeled
                rev_paths = self.category.find_paths(obj.name, labeled_name, max_length=5)
                for path in rev_paths:
                    values.append((self._labels[labeled_name], path.weight))

            if values:
                result, conf = self._aggregate(values)
                self._predictions[obj.name] = (result, conf)

        self._trained = True

    def predict(self, object_name: str) -> Tuple[Optional[Any], float]:
        """
        Predict the label for an object.

        Returns:
            (predicted_label, confidence) or (None, 0.0) if no prediction.
        """
        if not self._trained:
            self.learn()
        return self._predictions.get(object_name, (None, 0.0))

    def cross_validate(self, k: int = 1) -> float:
        """
        Leave-k-out cross-validation.

        Removes k labeled objects at a time, trains on remaining,
        checks prediction accuracy on held-out.

        Returns:
            Accuracy (fraction correct).
        """
        if len(self._labels) < k + 1:
            return 0.0

        labeled_items = list(self._labels.items())
        correct = 0
        total = 0

        for i in range(0, len(labeled_items), k):
            held_out = labeled_items[i:i + k]
            if not held_out:
                continue

            # Temporarily remove held-out labels
            saved = dict(self._labels)
            for name, _ in held_out:
                del self._labels[name]

            self._trained = False
            self.learn()

            for name, true_label in held_out:
                pred, conf = self.predict(name)
                if pred == true_label:
                    correct += 1
                total += 1

            # Restore
            self._labels = saved

        self._trained = False
        return correct / total if total > 0 else 0.0

    def _aggregate(self, values: List[Tuple[Any, float]]) -> Tuple[Any, float]:
        """
        Aggregate labeled values via colimit-style combination.

        For categorical labels: majority vote weighted by confidence.
        For numeric labels: weighted average.
        """
        if not values:
            return None, 0.0

        labels, weights = zip(*values)

        # Numeric: weighted average
        if all(isinstance(l, (int, float)) for l in labels):
            total_w = sum(weights)
            if total_w == 0:
                return sum(labels) / len(labels), 0.0
            avg = sum(l * w for l, w in zip(labels, weights)) / total_w
            conf = min(1.0, total_w / max(1, len(self._labels)))
            return avg, conf

        # Categorical: weighted majority vote
        vote_weights: Dict[Any, float] = {}
        for label, w in zip(labels, weights):
            vote_weights[label] = vote_weights.get(label, 0.0) + w

        best = max(vote_weights, key=vote_weights.get)
        total_w = sum(vote_weights.values())
        conf = vote_weights[best] / total_w if total_w > 0 else 0.0
        return best, conf


# =====================================================================
# Phase 4c: Extended Kan Learning
# =====================================================================

def supervised_kan(
    category: Category,
    labels: Dict[str, Any],
) -> KanLearner:
    """
    Supervised learning via left Kan extension.

    Convenience function: creates a KanLearner, sets labels, and trains.

    Args:
        category: The categorical structure.
        labels: Object name -> label mapping for training data.

    Returns:
        Trained KanLearner.
    """
    learner = KanLearner(category=category)
    learner.set_labels(labels)
    learner.learn()
    return learner


def unsupervised_kan(
    category: Category,
    feature_fn: Callable[[Object], Any] = None,
) -> Dict[str, List[str]]:
    """
    Clustering via right Kan extension.

    Groups objects by connectivity structure in the category.
    Objects reachable from each other within short paths are clustered.

    Args:
        category: The categorical structure.
        feature_fn: Optional feature extractor for objects.

    Returns:
        Dict mapping cluster label -> list of object names.
    """
    objects = category.objects()
    if not objects:
        return {}

    # Build adjacency-based clusters using union-find
    parent: Dict[str, str] = {obj.name: obj.name for obj in objects}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Union objects connected by morphisms
    for mor in category.morphisms():
        if mor.source in parent and mor.target in parent:
            union(mor.source, mor.target)

    # Group by cluster
    clusters: Dict[str, List[str]] = {}
    for obj in objects:
        root = find(obj.name)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(obj.name)

    return clusters


def kan_classify(
    learner: KanLearner,
    object_name: str,
) -> Dict[Any, float]:
    """
    Classification with per-class confidence.

    Returns a distribution over possible labels for the given object.

    Args:
        learner: A trained KanLearner.
        object_name: The object to classify.

    Returns:
        Dict mapping label -> confidence score.
    """
    if not learner._trained:
        learner.learn()

    # Gather all evidence from paths to labeled objects
    values: List[Tuple[Any, float]] = []
    labeled_names = set(learner._labels.keys())
    category = learner.category

    for labeled_name in labeled_names:
        paths = category.find_paths(labeled_name, object_name, max_length=5)
        for path in paths:
            values.append((learner._labels[labeled_name], path.weight))

        rev_paths = category.find_paths(object_name, labeled_name, max_length=5)
        for path in rev_paths:
            values.append((learner._labels[labeled_name], path.weight))

    if not values:
        return {}

    # Build distribution over labels
    label_weights: Dict[Any, float] = {}
    for label, w in values:
        label_weights[label] = label_weights.get(label, 0.0) + w

    total = sum(label_weights.values())
    if total > 0:
        return {l: w / total for l, w in label_weights.items()}
    return label_weights


def kan_complete(category: Category) -> List[Tuple[str, str, float]]:
    """
    Knowledge graph completion via Kan extension.

    Finds pairs of objects that are indirectly connected (through paths)
    but lack a direct morphism, and suggests new connections.

    Returns:
        List of (source, target, predicted_confidence) tuples.
    """
    objects = category.objects()
    existing = {(m.source, m.target) for m in category.morphisms()}
    suggestions: List[Tuple[str, str, float]] = []

    for obj_a in objects:
        for obj_b in objects:
            if obj_a.name == obj_b.name:
                continue
            if (obj_a.name, obj_b.name) in existing:
                continue

            # Check if there's an indirect path
            paths = category.find_paths(obj_a.name, obj_b.name, max_length=4)
            if paths:
                # Use best path weight as predicted confidence
                best_weight = max(p.weight for p in paths)
                if best_weight > 0:
                    suggestions.append(
                        (obj_a.name, obj_b.name, best_weight)
                    )

    suggestions.sort(key=lambda x: x[2], reverse=True)
    return suggestions
