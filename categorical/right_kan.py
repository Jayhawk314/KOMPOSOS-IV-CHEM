# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Right Kan structural priors for seeding streaming categorical prediction."""

import math
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Set, Tuple


class RightKanExtension:
    """
    Structural right Kan extension: Ran_K(F)(e) = lim_{(e downarrow K)} F.

    This complements the streaming left Kan by computing topology-only priors
    before observations arrive. It is intentionally independent of chemistry,
    drug, or cyber domain types.
    """

    def __init__(
        self,
        objects: List[str],
        compositions: List[Tuple[str, str]],
        entry_objects: Optional[Set[str]] = None,
        weight_fn: Optional[Callable[[str, str], float]] = None,
        successor_fn: Optional[Callable[[str], List[Tuple[str, float]]]] = None,
    ):
        self._objects = set(objects)
        self._weight_fn = weight_fn
        self._successor_fn = successor_fn
        self._entry_objects = entry_objects or set()
        self._structural_scores: Dict[str, float] = {}
        self._predecessor_map: Dict[str, Set[str]] = defaultdict(set)

        for src, tgt in compositions:
            self._predecessor_map[tgt].add(src)

        self._compute_structural_priors()

    def _compute_structural_priors(self) -> None:
        n_objects = len(self._objects)
        norm = max(1.0, math.sqrt(n_objects))

        for obj_id in self._objects:
            predecessors = self._predecessor_map.get(obj_id, set())
            if not predecessors:
                self._structural_scores[obj_id] = 0.0
                continue

            total = 0.0
            for pred in predecessors:
                total += self._weight_fn(pred, obj_id) if self._weight_fn else 0.5

            score = min(1.0, total / norm)
            if obj_id in self._entry_objects:
                score = min(1.0, score + 0.1)
            self._structural_scores[obj_id] = score

    def predict(self, top_k: int = 10) -> List[Dict]:
        sorted_objs = sorted(
            self._structural_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        return [
            {
                "object": obj_id,
                "structural_score": round(score, 6),
                "n_predecessors": len(self._predecessor_map.get(obj_id, set())),
                "is_entry": obj_id in self._entry_objects,
            }
            for obj_id, score in sorted_objs
        ]

    def get_priors_for_seeding(
        self,
        entry_points: Optional[List[str]] = None,
        prior_weight: float = 0.15,
    ) -> List[Tuple[str, float]]:
        entries = entry_points or list(self._entry_objects)

        if self._successor_fn is not None:
            prior_dict: Dict[str, float] = {}
            for entry in entries:
                for succ_id, succ_weight in self._successor_fn(entry):
                    structural = self._structural_scores.get(succ_id, 0.1)
                    weight = prior_weight * succ_weight * structural
                    if weight > 0.001 and weight > prior_dict.get(succ_id, 0.0):
                        prior_dict[succ_id] = weight
            return sorted(prior_dict.items(), key=lambda item: item[1], reverse=True)

        prior_dict = {
            obj_id: prior_weight * score
            for obj_id, score in self._structural_scores.items()
            if prior_weight * score > 0.001
        }
        return sorted(prior_dict.items(), key=lambda item: item[1], reverse=True)

    def get_structural_score(self, object_id: str) -> float:
        return self._structural_scores.get(object_id, 0.0)

    def is_entry(self, object_id: str) -> bool:
        return object_id in self._entry_objects
