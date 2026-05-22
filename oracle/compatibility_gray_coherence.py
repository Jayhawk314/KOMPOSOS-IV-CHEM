# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Gray 3-cell coherence adapter for compatibility strategy votes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from core.gray_coherence import GrayCategoryLayer, TwoCellProxy
from oracle.compatibility_context import CompatibilityContext


@dataclass(frozen=True)
class GrayCoherenceVote:
    """Serializable Gray coherence result over ensemble strategy paths."""

    checked: bool
    coherent: bool
    gap_count: int
    pairs_checked: int
    max_gap_severity: float
    reason: str
    gaps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checked": self.checked,
            "coherent": self.coherent,
            "gap_count": self.gap_count,
            "pairs_checked": self.pairs_checked,
            "max_gap_severity": round(self.max_gap_severity, 4),
            "reason": self.reason,
            "gaps": [dict(gap) for gap in self.gaps],
        }


def check_gray_coherence(
    material_a: str,
    material_b: str,
    domain: str,
    votes: Iterable[Any],
    context: Optional[CompatibilityContext] = None,
    min_vote_confidence: float = 0.35,
) -> GrayCoherenceVote:
    """
    Interpret conflicting strategy votes as parallel 2-cells and check for
    missing Gray 3-cell coherence.

    The copied MATH Gray layer was written for structural software paths.  This
    adapter maps chemistry votes into the same shape without importing the full
    scanner stack: each strategy path starts at the same material-interface
    query and ends at either a compatible or incompatible verdict object.
    """

    vote_list = list(votes)
    if len(vote_list) < 2:
        return GrayCoherenceVote(
            checked=False,
            coherent=True,
            gap_count=0,
            pairs_checked=0,
            max_gap_severity=0.0,
            reason="fewer than two strategy paths",
        )

    context = context or CompatibilityContext()
    query = _query_label(material_a, material_b, domain, context)
    layer = GrayCategoryLayer()
    gaps: List[Dict[str, Any]] = []
    pairs_checked = 0

    for i, left in enumerate(vote_list):
        for right in vote_list[i + 1 :]:
            if _compatible(left) == _compatible(right):
                continue
            if min(_confidence(left), _confidence(right)) < min_vote_confidence:
                continue

            pairs_checked += 1
            alpha = _vote_to_two_cell(query, left)
            beta = _vote_to_two_cell(query, right)
            modification = layer.check_modification_coherence(alpha, beta)
            if modification.is_coherent:
                continue

            severity = _gap_severity(left, right)
            gaps.append(
                {
                    "left_strategy": _strategy(left),
                    "right_strategy": _strategy(right),
                    "left_compatible": _compatible(left),
                    "right_compatible": _compatible(right),
                    "left_score": round(_score(left), 4),
                    "right_score": round(_score(right), 4),
                    "left_confidence": round(_confidence(left), 4),
                    "right_confidence": round(_confidence(right), 4),
                    "gap_type": modification.gap_type.value,
                    "gap_location": modification.gap_location,
                    "proof_type": modification.proof_type,
                    "gray_tensor_witness": modification.gray_tensor_witness,
                    "severity": round(severity, 4),
                }
            )

    if not pairs_checked:
        return GrayCoherenceVote(
            checked=True,
            coherent=True,
            gap_count=0,
            pairs_checked=0,
            max_gap_severity=0.0,
            reason="no confident contradictory strategy paths",
        )

    if not gaps:
        return GrayCoherenceVote(
            checked=True,
            coherent=True,
            gap_count=0,
            pairs_checked=pairs_checked,
            max_gap_severity=0.0,
            reason="all contradictory strategy paths had coherent Gray modifications",
        )

    return GrayCoherenceVote(
        checked=True,
        coherent=False,
        gap_count=len(gaps),
        pairs_checked=pairs_checked,
        max_gap_severity=max(gap["severity"] for gap in gaps),
        reason="Gray 3-cell coherence gaps found between contradictory strategy paths",
        gaps=gaps,
    )


def _vote_to_two_cell(query: str, vote: Any) -> TwoCellProxy:
    verdict = "compatible" if _compatible(vote) else "incompatible"
    strategy = _strategy(vote)
    vote_confidence = _confidence(vote)

    # This is the confidence that the two-cell can be glued coherently, not the
    # strategy's evidence confidence. High-confidence contradictions imply a
    # low-confidence modification witness.
    glue_confidence = max(0.0, min(1.0, 1.0 - vote_confidence))
    return TwoCellProxy(
        source_morphism=query,
        target_morphism=query if _compatible(vote) else f"{query}:verdict",
        label=f"{strategy}:{verdict}",
        confidence=glue_confidence,
        privilege_level=0,
        memory_regions=(query,),
    )


def _query_label(
    material_a: str,
    material_b: str,
    domain: str,
    context: CompatibilityContext,
) -> str:
    role = context.role or context.interface_type or "pair"
    pair = "|".join(sorted((material_a, material_b)))
    return f"{domain}:{role}:{pair}"


def _gap_severity(left: Any, right: Any) -> float:
    score_gap = abs(_score(left) - _score(right))
    confidence = min(_confidence(left), _confidence(right))
    return max(0.0, min(1.0, 0.55 * confidence + 0.45 * score_gap))


def _strategy(vote: Any) -> str:
    return str(_field(vote, "strategy", "unknown"))


def _score(vote: Any) -> float:
    return _clamp(_field(vote, "score", 0.5))


def _confidence(vote: Any) -> float:
    return _clamp(_field(vote, "confidence", 0.0))


def _compatible(vote: Any) -> bool:
    return bool(_field(vote, "compatible", False))


def _field(vote: Any, name: str, default: Any) -> Any:
    if isinstance(vote, dict):
        return vote.get(name, default)
    return getattr(vote, name, default)


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
