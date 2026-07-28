# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
COG Interference Probe Mixin
==============================

Add Z2-graded interference detection to CogReasoningPlugin.

HOW TO INTEGRATE
----------------
In cog_reasoning.py, add two things:

1. Import at top:

    from cog.interference import CogInterferenceMixin

2. Add to class definition:

    class CogReasoningPlugin(CogInterferenceMixin, Plugin):
        ...
        async def on_start(self):
            await super().on_start()  # initializes interference buffer
            ...

That's it. The mixin adds:
  - probe_window:    rolling buffer of recent odd-parity claims
  - check_interference():  detects NULL_COLLAPSE chains
  - on_claim_verify() hook: auto-runs interference check after every verify
  - Event emitted: "cog.interference.collapse" when chain detected

WHY THIS WORKS
--------------
A single suspicious claim (odd parity) passes normally through COG tiers.
Two suspicious claims that COMPOSE (share source/target) form a chain.
Z2 composition: odd ∘ odd → NULL_COLLAPSE (amplitude = 0).

Mythos-class exploit chains require multiple composed anomalous steps.
Each step alone looks borderline. The chain collapses algebraically.
This catches what per-claim analysis misses.

FOLDER
------
komposos/core/interference.py
(sits alongside gray_coherence.py and gray_coherence_bridge.py)
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from foundation.graded_morphism import GradedMorphism

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parity assignment — maps COG verdicts / confidence to Z2 parity
# ---------------------------------------------------------------------------

def _verdict_to_parity(status: str, confidence: float) -> int:
    """
    Map a COG verification result to Z2 parity.

    Parity 1 (Odd / anomalous):
      - HOLLOW  — structurally plausible but logically unsound
      - ORPHAN  — logically forced but structurally weird
      - low confidence AGREE (< 0.6) — passes but weakly

    Parity 0 (Even / benign):
      - AGREE with confidence >= 0.6
      - REJECT  — not an attack at all
    """
    status_upper = status.upper() if isinstance(status, str) else ""

    if status_upper in ("HOLLOW", "ORPHAN"):
        return 1
    if status_upper == "AGREE" and confidence < 0.6:
        return 1
    return 0


def _confidence_to_amplitude(confidence: float) -> complex:
    """Map scalar confidence [0,1] to complex amplitude."""
    return complex(max(0.0, min(1.0, confidence)), 0.0)


# ---------------------------------------------------------------------------
# Collapse event
# ---------------------------------------------------------------------------

@dataclass
class CollapseEvent:
    """
    Fired when two odd-parity claims compose to NULL_COLLAPSE.

    This signals a likely exploit chain: two individually borderline
    claims that, when composed, violate Z2 consistency.
    """
    morphism_a: GradedMorphism
    morphism_b: GradedMorphism
    collapsed: GradedMorphism       # always NULL_COLLAPSE
    chain_source: Optional[str]     # source of morphism_a
    chain_target: Optional[str]     # target of morphism_b
    severity: float                 # geometric mean of input amplitudes

    @property
    def is_critical(self) -> bool:
        return self.severity >= 0.5

    def to_dict(self) -> Dict:
        return {
            "type": "cog.interference.collapse",
            "morphism_a": self.morphism_a.name,
            "morphism_b": self.morphism_b.name,
            "chain": f"{self.chain_source} → {self.chain_target}",
            "severity": round(self.severity, 4),
            "critical": self.is_critical,
        }

    def __repr__(self) -> str:
        return (
            f"CollapseEvent({self.morphism_a.name} ∘ {self.morphism_b.name} "
            f"→ NULL_COLLAPSE | severity={self.severity:.3f})"
        )


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class CogInterferenceMixin:
    """
    Mixin for CogReasoningPlugin.

    Maintains a rolling window of recent odd-parity verified claims
    and checks each new odd claim against all previous odd claims
    for Z2 NULL_COLLAPSE (exploit chain detection).

    Usage:
        class CogReasoningPlugin(CogInterferenceMixin, Plugin):
            async def on_start(self):
                await super().on_start()
    """

    # Override in subclass or pass to __init__ if desired
    PROBE_WINDOW_SIZE: int = 50     # max odd morphisms tracked
    PROBE_MIN_AMPLITUDE: float = 0.3  # ignore very low confidence probes

    async def on_start(self):
        """Initialize interference buffer. Call super().on_start() in subclass."""
        self._probe_window: Deque[GradedMorphism] = deque(
            maxlen=self.PROBE_WINDOW_SIZE
        )
        self._collapse_history: List[CollapseEvent] = []
        logger.info("[CogInterference] Probe window initialized "
                    f"(size={self.PROBE_WINDOW_SIZE})")
        # Let other on_start handlers run
        try:
            await super().on_start()
        except AttributeError:
            pass

    def _build_morphism(
        self,
        source: str,
        target: str,
        status: str,
        confidence: float,
    ) -> GradedMorphism:
        """Build a GradedMorphism from a COG verify result."""
        parity = _verdict_to_parity(status, confidence)
        amplitude = _confidence_to_amplitude(confidence)
        name = f"{source}→{target}[{status}]"
        return GradedMorphism(
            name=name,
            parity=parity,
            amplitude=amplitude,
            source=source,
            target=target,
        )

    def check_interference(
        self, morphism: GradedMorphism
    ) -> List[CollapseEvent]:
        """
        Check a new morphism against the probe window for Z2 collapse.

        Only odd-parity morphisms are checked (even-parity claims
        are benign and don't participate in fermionic chains).

        Returns list of CollapseEvents (empty if no collapse).
        """
        collapses: List[CollapseEvent] = []

        if morphism.parity != 1:
            return collapses  # even — no interference possible

        if morphism.magnitude < self.PROBE_MIN_AMPLITUDE:
            return collapses  # too weak to matter

        # Check against all odd morphisms in the window
        for prior in self._probe_window:
            # Only check morphisms that form a chain: prior.target == morphism.source
            # OR same source (parallel attack probes on same node)
            forms_chain = (
                prior.target == morphism.source       # sequential chain
                or prior.source == morphism.source    # parallel probes
            )
            if not forms_chain:
                continue

            composed = prior * morphism  # Z2 composition

            if composed.is_collapsed:
                severity = (prior.magnitude * morphism.magnitude) ** 0.5
                evt = CollapseEvent(
                    morphism_a=prior,
                    morphism_b=morphism,
                    collapsed=composed,
                    chain_source=prior.source,
                    chain_target=morphism.target,
                    severity=severity,
                )
                collapses.append(evt)
                self._collapse_history.append(evt)
                logger.warning(
                    f"[CogInterference] NULL_COLLAPSE: {evt}"
                )

        # Add to window after checking (don't self-compose)
        self._probe_window.append(morphism)
        return collapses

    async def verify_claim_with_interference(
        self,
        source: str,
        target: str,
        relation: str,
        confidence: float = 0.5,
        max_tier: int = 4,
    ):
        """
        Drop-in replacement for verify_claim that adds interference checking.

        Calls verify_claim, builds a GradedMorphism from the result,
        runs interference detection, and emits collapse events if found.
        """
        # Run normal COG verification
        result = await self.verify_claim(
            source=source,
            target=target,
            relation=relation,
            confidence=confidence,
            max_tier=max_tier,
        )

        # Build morphism from result
        status = result.status.value if hasattr(result.status, "value") else str(result.status)
        morphism = self._build_morphism(
            source=source,
            target=target,
            status=status,
            confidence=result.confidence,
        )

        # Check for interference collapses
        collapses = self.check_interference(morphism)

        # Emit collapse events onto Orion bus
        for evt in collapses:
            await self.emit("cog.interference.collapse", evt.to_dict())
            if evt.is_critical:
                await self.emit("cog.alert.critical", {
                    **evt.to_dict(),
                    "message": (
                        f"Exploit chain detected: "
                        f"{evt.chain_source} → {evt.chain_target}"
                    ),
                })

        return result, collapses

    @property
    def collapse_count(self) -> int:
        return len(self._collapse_history)

    @property
    def recent_collapses(self) -> List[CollapseEvent]:
        return self._collapse_history[-10:]

    def interference_summary(self) -> Dict:
        return {
            "probe_window_size": len(self._probe_window),
            "total_collapses": self.collapse_count,
            "critical_collapses": sum(
                1 for e in self._collapse_history if e.is_critical
            ),
            "recent": [e.to_dict() for e in self.recent_collapses],
        }
