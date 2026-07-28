# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Streaming Kan Extensions via Comma Categories

The left Kan extension: Lan_K(F)(e) = colim_{(K downarrow e)} F

Key insight for streaming: When a new event arrives (new object in the comma
category), we don't recompute the entire colimit. We compute the pushout
of the existing colimit with the new contribution -- O(1) per event.

For KOMPOSOS chemistry: streaming observations of material interactions
(e.g. lab results, simulation outputs) update predictions in real time.

Mathematical basis:
  - Milewski, "Pointwise Kan Extensions"
  - Perrone & Tholen, "Kan Extensions are Partial Colimits" (2022)
  - Shiebler, "Kan Extensions in Data Science" (2022)

Ported from KOMPOSOS-III-ARC. Pure stdlib, zero dependencies.
"""

import math
import time
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .right_kan import RightKanExtension


@dataclass
class CommaObject:
    """Object in comma category (K downarrow e): pair (c, f: K(c) -> e)"""
    source_object: str       # c in C (observed entity)
    morphism_to_target: str  # f: K(c) -> e (the composition path)
    target: str              # e (prediction target)
    timestamp: float         # When observed
    weight: float            # Weight from enriched category


class StreamingCommaCategory:
    """
    Incrementally maintained comma category for real-time Kan extensions.

    As new events arrive:
    1. Map event to a categorical object
    2. Find morphisms to prediction targets (composable successors)
    3. Add to comma category
    4. Incrementally update colimit (O(1) per event)

    The colimit is the prediction: weighted sum of contributions.
    Temporal decay ensures older observations contribute less.
    """

    def __init__(self, decay_rate: float = 0.001):
        self.objects: List[CommaObject] = []
        self.colimit_cache: Dict[str, float] = {}
        self.decay_rate = decay_rate
        self.observation_count: int = 0
        self._target_index: Dict[str, List[int]] = defaultdict(list)

    def add_observation(self, source_id: str, timestamp: float,
                        composable_targets: List[Tuple[str, float]]) -> Dict[str, float]:
        """
        New event observed. Update comma category incrementally.

        Args:
            source_id: The observed entity ID.
            timestamp: Event timestamp (seconds since epoch).
            composable_targets: List of (target_id, weight) tuples.

        Returns:
            Dictionary of updated prediction scores (only changed targets).
        """
        new_objects: List[CommaObject] = []

        for target_id, weight in composable_targets:
            if target_id == source_id:
                continue

            morphism_label = f"{source_id}->{target_id}"
            obj = CommaObject(
                source_object=source_id,
                morphism_to_target=morphism_label,
                target=target_id,
                timestamp=timestamp,
                weight=weight,
            )
            idx = len(self.objects)
            self.objects.append(obj)
            self._target_index[target_id].append(idx)
            new_objects.append(obj)

        self.observation_count += 1

        updated = self._update_colimit_incremental(new_objects, timestamp)
        return updated

    def _update_colimit_incremental(self, new_objects: List[CommaObject],
                                    current_time: float) -> Dict[str, float]:
        """Update colimit without full recomputation."""
        updated: Dict[str, float] = {}

        for obj in new_objects:
            age = max(0.0, current_time - obj.timestamp)
            contribution = obj.weight * math.exp(-self.decay_rate * age)

            if obj.target in self.colimit_cache:
                self.colimit_cache[obj.target] += contribution
            else:
                self.colimit_cache[obj.target] = contribution

            updated[obj.target] = self.colimit_cache[obj.target]

        return updated

    def get_predictions(self, top_k: int = 5,
                        current_time: float = None) -> List[Tuple[str, float]]:
        """
        Get current top-k predictions with temporal decay applied.

        Args:
            top_k: Number of top predictions to return.
            current_time: Reference time for decay. Defaults to now.

        Returns:
            List of (target_id, score) sorted by score descending.
        """
        if current_time is None:
            current_time = time.time()

        # Full recomputation every 100 observations to correct decay drift
        if self.observation_count % 100 == 0 and self.objects:
            scores: Dict[str, float] = defaultdict(float)
            for obj in self.objects:
                age = max(0.0, current_time - obj.timestamp)
                decayed_weight = obj.weight * math.exp(-self.decay_rate * age)
                scores[obj.target] += decayed_weight
            self.colimit_cache = dict(scores)

        sorted_predictions = sorted(
            self.colimit_cache.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_predictions[:top_k]

    def get_confidence(self, target: str) -> float:
        """
        Confidence for a specific prediction target.

        Based on number of independent source observations.
        Saturates via exponential: 1 - exp(-0.5 * n_contributors)
        """
        if target not in self._target_index:
            return 0.0

        source_ids: Set[str] = set()
        for idx in self._target_index[target]:
            if idx < len(self.objects):
                source_ids.add(self.objects[idx].source_object)

        n_contributors = len(source_ids)
        if n_contributors == 0:
            return 0.0

        return 1.0 - math.exp(-0.5 * n_contributors)

    def prune_old(self, max_age_seconds: float = 3600):
        """Remove observations older than max_age to save memory."""
        cutoff = time.time() - max_age_seconds
        surviving: List[CommaObject] = []
        new_target_index: Dict[str, List[int]] = defaultdict(list)

        for obj in self.objects:
            if obj.timestamp >= cutoff:
                idx = len(surviving)
                surviving.append(obj)
                new_target_index[obj.target].append(idx)

        self.objects = surviving
        self._target_index = new_target_index

        current_time = time.time()
        self.colimit_cache.clear()
        for obj in self.objects:
            age = max(0.0, current_time - obj.timestamp)
            contribution = obj.weight * math.exp(-self.decay_rate * age)
            if obj.target in self.colimit_cache:
                self.colimit_cache[obj.target] += contribution
            else:
                self.colimit_cache[obj.target] = contribution

    def get_contributor_count(self, target: str) -> int:
        """Get the number of distinct sources contributing to a target."""
        if target not in self._target_index:
            return 0
        source_ids: Set[str] = set()
        for idx in self._target_index[target]:
            if idx < len(self.objects):
                source_ids.add(self.objects[idx].source_object)
        return len(source_ids)

    def get_supporting_evidence(self, target: str) -> List[str]:
        """Get source IDs that support a prediction target."""
        if target not in self._target_index:
            return []
        source_ids: Set[str] = set()
        for idx in self._target_index[target]:
            if idx < len(self.objects):
                source_ids.add(self.objects[idx].source_object)
        return sorted(source_ids)


class StreamingKanExtension:
    """
    Left Kan extension computed incrementally from streaming events.

    Lan_K(F)(e) = colim_{(K downarrow e)} F

    Where:
    - K: ObservedEvents -> Category (maps events to objects)
    - F: ObservedEvents -> Scores (maps events to values)
    - e: candidate prediction target

    The colimit aggregates all observations that have morphisms pointing
    toward e, weighted and decayed over time.
    """

    def __init__(self, decay_rate: float = 0.001):
        self.comma_cat = StreamingCommaCategory(decay_rate=decay_rate)
        self.event_history: List[Tuple[str, float]] = []

    def observe(self, source_id: str, timestamp: float,
                composable_targets: List[Tuple[str, float]]) -> Dict[str, float]:
        """
        Process new observation. Returns updated prediction map.

        Args:
            source_id: The observed entity ID.
            timestamp: Event timestamp.
            composable_targets: List of (target_id, weight) tuples.

        Returns:
            Dictionary of updated prediction scores.
        """
        self.event_history.append((source_id, timestamp))
        return self.comma_cat.add_observation(
            source_id, timestamp, composable_targets
        )

    def predict(self, top_k: int = 5) -> List[Dict]:
        """
        Get current top predictions with confidence and metadata.

        Returns list of prediction dictionaries.
        """
        current_time = time.time()
        if self.event_history:
            current_time = max(current_time, self.event_history[-1][1])

        raw_predictions = self.comma_cat.get_predictions(top_k, current_time)

        results = []
        for target, score in raw_predictions:
            confidence = self.comma_cat.get_confidence(target)
            n_contributors = self.comma_cat.get_contributor_count(target)
            evidence = self.comma_cat.get_supporting_evidence(target)

            results.append({
                "target": target,
                "score": round(score, 6),
                "confidence": round(confidence, 4),
                "n_contributors": n_contributors,
                "supporting_evidence": evidence,
            })

        return results

    def multi_step_forecast(self, steps: int = 3,
                            composable_fn=None) -> List[List[Dict]]:
        """
        Multi-step forecast using iterated Kan extension.

        Args:
            steps: Number of forecast steps (default 3).
            composable_fn: Callable(source_id) -> List[(target_id, weight)].

        Returns:
            List of lists, where forecast[i] is predictions for step i+1.
        """
        forecast: List[List[Dict]] = []
        confidence_decay = 0.7
        hypothetical_markers: List[Tuple[str, float]] = []

        for step in range(steps):
            step_num = step + 1

            if step == 0:
                preds = self.predict(top_k=5)
            else:
                if not forecast[step - 1]:
                    break

                top_prev = forecast[step - 1][0]
                top_source = top_prev["target"]

                if composable_fn is not None:
                    targets = composable_fn(top_source)
                    hypothetical_time = time.time() + 1000000.0 + step
                    hypothetical_markers.append((top_source, hypothetical_time))
                    self.comma_cat.add_observation(
                        top_source, hypothetical_time, targets
                    )
                    self.event_history.append((top_source, hypothetical_time))
                    preds = self.predict(top_k=5)
                else:
                    break

            step_preds = []
            for pred in preds:
                adjusted = dict(pred)
                adjusted["step"] = step_num
                adjusted["confidence"] = round(
                    pred["confidence"] * (confidence_decay ** step), 4
                )
                step_preds.append(adjusted)

            forecast.append(step_preds)

        # Roll back hypothetical observations
        if hypothetical_markers:
            hypo_set = set(hypothetical_markers)
            surviving: List[CommaObject] = []
            new_index: Dict[str, List[int]] = defaultdict(list)
            for obj in self.comma_cat.objects:
                if (obj.source_object, obj.timestamp) in hypo_set:
                    continue
                idx = len(surviving)
                surviving.append(obj)
                new_index[obj.target].append(idx)
            self.comma_cat.objects = surviving
            self.comma_cat._target_index = new_index

            current_time = time.time()
            self.comma_cat.colimit_cache.clear()
            for obj in self.comma_cat.objects:
                age = max(0.0, current_time - obj.timestamp)
                contribution = obj.weight * math.exp(
                    -self.comma_cat.decay_rate * age
                )
                if obj.target in self.comma_cat.colimit_cache:
                    self.comma_cat.colimit_cache[obj.target] += contribution
                else:
                    self.comma_cat.colimit_cache[obj.target] = contribution

            self.event_history = [
                (t, ts) for t, ts in self.event_history
                if (t, ts) not in hypo_set
            ]

        return forecast

    def get_event_count(self) -> int:
        """Return the number of events observed so far."""
        return len(self.event_history)

    def get_comma_category_size(self) -> int:
        """Return the number of objects in the comma category."""
        return len(self.comma_cat.objects)

    def prune(self, max_age_seconds: float = 3600):
        """Prune old observations."""
        cutoff = time.time() - max_age_seconds
        self.event_history = [
            (t, ts) for t, ts in self.event_history if ts >= cutoff
        ]
        self.comma_cat.prune_old(max_age_seconds)
