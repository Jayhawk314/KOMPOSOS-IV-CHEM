# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Hawkins / Komposos-Labs

"""
Threat Intelligence Bus — Cross-Module Event System

Simple publish/subscribe bus that connects:
  - Cyber Oracle (threat detections)
  - Gray Coherence (MythosShield gap findings)
  - COG Security (vulnerability checks)
  - OPTIMUS Engine (structural improvements)
  - Attack Simulator (red team results)

Events flow through the bus so all modules can:
  1. React to findings from other modules
  2. Update their models based on new intelligence
  3. Trigger complementary analyses

Usage:
    bus = ThreatIntelligenceBus.get_instance()
    bus.subscribe("coherence.gap.found", my_handler)
    bus.publish("attack.pattern.detected", {"chain": [...]})

Event Types:
  - "threat.detected"           → from cyber_oracle
  - "attack.pattern.detected"   → from attack_simulator
  - "coherence.gap.found"       → from gray_coherence/MythosShield
  - "vulnerability.found"       → from cog_security
  - "patch.applied"             → from any module
  - "mythos.shield.scan"        → from MythosShield
  - "optimus.rewrite"           → from OPTIMUS Engine
  - "variant.matched"           → from variant_detector
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BusEvent:
    """An event on the threat intelligence bus."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source_module: str = ""

    def __repr__(self) -> str:
        return f"BusEvent({self.event_type}, src={self.source_module})"


class ThreatIntelligenceBus:
    """
    Cross-module threat intelligence event bus.

    Publishers emit events; subscribers receive them asynchronously.
    This decouples modules while enabling Bayesian learning across all of them.

    Thread-safe: subscribers are called sequentially in publication order.
    """

    _instance: Optional["ThreatIntelligenceBus"] = None

    @classmethod
    def get_instance(cls) -> "ThreatIntelligenceBus":
        """Singleton access — all modules share one bus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[BusEvent] = []
        self._max_history = 10000

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Event name (e.g., "coherence.gap.found")
            callback: Function(event: BusEvent) -> None
        """
        self._subscribers.setdefault(event_type, []).append(callback)
        logger.debug(f"[ThreatBus] Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Remove a subscription."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event_type: str, payload: Dict[str, Any],
                source: str = "") -> BusEvent:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Event name
            payload: Event data
            source: Module name (for tracing)

        Returns:
            The published BusEvent
        """
        event = BusEvent(
            event_type=event_type,
            payload=payload,
            source_module=source,
        )

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Notify subscribers
        subscribers = self._subscribers.get(event_type, [])
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"[ThreatBus] Subscriber error for {event_type}: {e}")

        logger.debug(
            f"[ThreatBus] Published {event_type} to {len(subscribers)} subscribers"
        )
        return event

    def get_history(self, event_type: Optional[str] = None,
                    limit: int = 100) -> List[BusEvent]:
        """
        Get recent event history.

        Args:
            event_type: Filter by event type (None = all)
            limit: Maximum events to return

        Returns:
            List of recent BusEvents
        """
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_statistics(self) -> Dict[str, int]:
        """Get event counts by type."""
        stats: Dict[str, int] = {}
        for event in self._event_history:
            stats[event.event_type] = stats.get(event.event_type, 0) + 1
        return stats


# ============================================================================
# Convenience: Pre-built event type constants
# ============================================================================

# From cyber oracle
EVENT_THREAT_DETECTED = "threat.detected"
EVENT_THREAT_PREDICTED = "threat.predicted"

# From attack simulator
EVENT_ATTACK_PATTERN_DETECTED = "attack.pattern.detected"
EVENT_SIMULATION_COMPLETE = "simulation.complete"
EVENT_MYTHOS_VALIDATION = "mythos.validation"

# From gray coherence
EVENT_COHERENCE_GAP_FOUND = "coherence.gap.found"
EVENT_MYTHOS_SHIELD_SCAN = "mythos.shield.scan"
EVENT_GAP_PATCHED = "gap.patched"

# From COG security
EVENT_VULNERABILITY_FOUND = "vulnerability.found"
EVENT_OWASP_VIOLATION = "owasp.violation"
EVENT_SUPPLY_CHAIN_RISK = "supply_chain.risk"

# From OPTIMUS
EVENT_OPTIMUS_REWRITE = "optimus.rewrite"
EVENT_STRUCTURAL_IMPROVEMENT = "structural.improvement"

# From variant detector
EVENT_VARIANT_MATCHED = "variant.matched"
EVENT_CAMPAIGN_DETECTED = "campaign.detected"

# From general system
EVENT_PATCH_APPLIED = "patch.applied"
EVENT_SYSTEM_SCAN_COMPLETE = "system.scan.complete"
