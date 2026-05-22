# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Compatibility decision states shared by audits, APIs, and UI surfaces."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


COMPATIBLE = "compatible"
INCOMPATIBLE = "incompatible"
NEEDS_CONTEXT = "needs_context"
NO_VERDICT = "no_verdict"

EVALUATED_STATUSES = {COMPATIBLE, INCOMPATIBLE}


@dataclass(frozen=True)
class CompatibilityDecision:
    """A compatibility score plus the honesty state for that score."""

    status: str
    score: Optional[float] = None
    predicted_compatible: Optional[bool] = None
    confidence: float = 0.0
    missing_context: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def evaluated(self) -> bool:
        """True when the decision is a forced compatible/incompatible verdict."""

        return self.status in EVALUATED_STATUSES

    @classmethod
    def from_prediction(
        cls,
        score: float,
        predicted_compatible: bool,
        confidence: Optional[float] = None,
        reasons: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CompatibilityDecision":
        """Create a binary evaluated decision from an existing scorer."""

        return cls(
            status=COMPATIBLE if predicted_compatible else INCOMPATIBLE,
            score=round(float(score), 4),
            predicted_compatible=bool(predicted_compatible),
            confidence=_heuristic_confidence(score) if confidence is None else confidence,
            reasons=reasons or [],
            metadata=metadata or {},
        )

    @classmethod
    def needs_context(
        cls,
        missing_context: List[str],
        reasons: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CompatibilityDecision":
        """Create an abstention caused by missing required context."""

        return cls(
            status=NEEDS_CONTEXT,
            score=None,
            predicted_compatible=None,
            confidence=0.0,
            missing_context=missing_context,
            reasons=reasons or ["Required application context is missing."],
            metadata=metadata or {},
        )

    @classmethod
    def no_verdict(
        cls,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CompatibilityDecision":
        """Create a no-verdict result for missing tools, errors, or unavailable scorers."""

        return cls(
            status=NO_VERDICT,
            score=None,
            predicted_compatible=None,
            confidence=0.0,
            reasons=[reason],
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the decision for audit reports and API responses."""

        return {
            "status": self.status,
            "score": self.score,
            "predicted_compatible": self.predicted_compatible,
            "confidence": round(self.confidence, 4),
            "missing_context": list(self.missing_context),
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


def _heuristic_confidence(score: float) -> float:
    """Confidence is lower near the 0.50 decision boundary."""

    distance = abs(float(score) - 0.5)
    return max(0.25, min(0.95, 0.35 + 1.2 * distance))

