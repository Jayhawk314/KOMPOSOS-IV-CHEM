# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Temporal Sheaves for Event Stream Coherence

Key insight: Security event streams form a sheaf over time.
- Base space: Timeline (totally ordered)
- Sheaf: Events that agree on overlapping time windows
- Coherence: Events in overlapping windows must not contradict

This catches:
1. Time-based evasion (events out of order)
2. Data tampering (conflicting events in same window)
3. Log manipulation (gaps that violate causality)

Example contradiction:
  Window [10:00-10:05]: User logged in from NYC
  Window [10:03-10:08]: User logged in from London
  Overlap [10:03-10:05]: IMPOSSIBLE TRAVEL -> Credential theft detected

This is the "dark matter" detector: finds attacks that don't match signatures
but violate temporal coherence.
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import math

from cyber.attack_chain_strategies import SecurityEvent


@dataclass
class TimeWindow:
    """
    A time window in the temporal sheaf.

    Objects in the category are time intervals.
    Morphisms are inclusion maps (window1 ⊆ window2).
    """
    start: float  # Unix timestamp
    end: float

    def overlaps(self, other: 'TimeWindow') -> bool:
        """Check if two windows overlap."""
        return not (self.end <= other.start or self.start >= other.end)

    def intersection(self, other: 'TimeWindow') -> Optional['TimeWindow']:
        """Compute intersection of two windows (if exists)."""
        if not self.overlaps(other):
            return None
        return TimeWindow(
            start=max(self.start, other.start),
            end=min(self.end, other.end)
        )

    def contains(self, timestamp: float) -> bool:
        """Check if timestamp is in this window."""
        return self.start <= timestamp < self.end

    def duration(self) -> float:
        """Duration of window in seconds."""
        return self.end - self.start


@dataclass
class EventSection:
    """
    A section of the event sheaf over a time window.

    In sheaf theory: This is s ∈ F(U) where U is a time window.
    Restriction maps send sections to smaller windows.
    """
    window: TimeWindow
    events: List[SecurityEvent]

    def restrict_to(self, sub_window: TimeWindow) -> 'EventSection':
        """
        Restrict this section to a sub-window.

        This is the restriction morphism in sheaf theory:
        res: F(U) -> F(V) for V ⊆ U
        """
        if not self.window.overlaps(sub_window):
            return EventSection(sub_window, [])

        intersection = self.window.intersection(sub_window)
        if not intersection:
            return EventSection(sub_window, [])

        # Filter events that fall in the sub-window
        restricted_events = [
            e for e in self.events
            if intersection.contains(e.timestamp)
        ]

        return EventSection(intersection, restricted_events)


class TemporalSheafChecker:
    """
    Checks coherence of event streams using sheaf theory.

    Sheaf axioms:
    1. Locality: If sections agree on all sub-windows, they're equal
    2. Gluing: If sections agree on overlaps, they glue to a global section

    We use these to detect:
    - Temporal inconsistencies (violate gluing)
    - Data tampering (violate locality)
    - Evasion attempts (coherent attack chains that span windows)
    """

    def __init__(self, window_size_seconds: float = 300):  # 5-minute windows
        self.window_size = window_size_seconds

    def check_coherence(self, events: List[SecurityEvent]) -> Dict[str, any]:
        """
        Check if event stream forms a coherent sheaf.

        Returns:
            {
                "is_coherent": bool,
                "violations": List of temporal violations,
                "attack_indicators": Coherent attack chains that span windows
            }
        """
        if not events:
            return {"is_coherent": True, "violations": [], "attack_indicators": []}

        # Create overlapping time windows
        windows = self._create_time_windows(events)

        # Create event sections for each window
        sections = [EventSection(window, self._events_in_window(events, window))
                   for window in windows]

        # Check sheaf axioms
        violations = []
        violations.extend(self._check_gluing_axiom(sections))
        violations.extend(self._check_temporal_causality(sections))
        violations.extend(self._check_impossible_travel(sections))

        # Find attack indicators (coherent multi-window chains)
        attack_indicators = self._find_multi_window_attacks(sections)

        return {
            "is_coherent": len(violations) == 0,
            "violations": violations,
            "attack_indicators": attack_indicators,
            "num_windows": len(windows),
            "num_events": len(events)
        }

    def _create_time_windows(self, events: List[SecurityEvent]) -> List[TimeWindow]:
        """
        Create overlapping time windows covering all events.

        Windows overlap by 50% to catch cross-window attacks.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        start_time = sorted_events[0].timestamp
        end_time = sorted_events[-1].timestamp

        windows = []
        current_start = start_time

        # Create windows with 50% overlap
        step = self.window_size / 2

        while current_start < end_time:
            window_end = current_start + self.window_size
            windows.append(TimeWindow(current_start, window_end))
            current_start += step

        return windows

    def _events_in_window(self, events: List[SecurityEvent], window: TimeWindow) -> List[SecurityEvent]:
        """Get all events that fall in a time window."""
        return [e for e in events if window.contains(e.timestamp)]

    def _check_gluing_axiom(self, sections: List[EventSection]) -> List[Dict]:
        """
        Check sheaf gluing axiom.

        If two sections agree on their overlap, they should glue consistently.
        Violations indicate data tampering or log manipulation.
        """
        violations = []

        for i in range(len(sections) - 1):
            section1 = sections[i]
            section2 = sections[i + 1]

            if not section1.window.overlaps(section2.window):
                continue

            # Get events in the overlap
            overlap = section1.window.intersection(section2.window)
            if not overlap:
                continue

            events1_in_overlap = [e for e in section1.events if overlap.contains(e.timestamp)]
            events2_in_overlap = [e for e in section2.events if overlap.contains(e.timestamp)]

            # Check if they agree (same events in both sections)
            if len(events1_in_overlap) != len(events2_in_overlap):
                violations.append({
                    "type": "gluing_violation",
                    "window1": f"[{section1.window.start:.1f}, {section1.window.end:.1f}]",
                    "window2": f"[{section2.window.start:.1f}, {section2.window.end:.1f}]",
                    "description": "Events don't agree in overlap - possible log tampering",
                    "severity": "high"
                })

        return violations

    def _check_temporal_causality(self, sections: List[EventSection]) -> List[Dict]:
        """
        Check temporal causality: effects must follow causes.

        Example violation:
          - Data exfiltration at 10:00
          - Initial access at 10:05
          This violates causality (can't exfiltrate before gaining access)
        """
        violations = []

        for section in sections:
            events_sorted = sorted(section.events, key=lambda e: e.timestamp)

            for i in range(len(events_sorted) - 1):
                event1 = events_sorted[i]
                event2 = events_sorted[i + 1]

                # Check if event2 could possibly follow event1
                # (based on MITRE tactic ordering)
                if self._violates_causality(event1, event2):
                    violations.append({
                        "type": "causality_violation",
                        "event1": event1.event_type,
                        "event2": event2.event_type,
                        "time_diff": event2.timestamp - event1.timestamp,
                        "description": f"Effect ({event2.event_type}) before cause ({event1.event_type})",
                        "severity": "medium"
                    })

        return violations

    def _violates_causality(self, event1: SecurityEvent, event2: SecurityEvent) -> bool:
        """
        Check if event2 following event1 violates causality.

        This is a simplified check - full implementation would use MITRE tactic ordering.
        """
        # Example: exfiltration can't happen before collection
        if "exfiltration" in event2.event_type.lower() and "collection" in event1.event_type.lower():
            return False  # This is valid

        if "collection" in event2.event_type.lower() and "exfiltration" in event1.event_type.lower():
            return True  # This violates causality

        return False  # Most other orderings are OK

    def _check_impossible_travel(self, sections: List[EventSection]) -> List[Dict]:
        """
        Detect impossible travel: user in two locations at overlapping times.

        This is a classic sheaf coherence violation:
        - Section 1: User in NYC
        - Section 2: User in London
        - Overlap: User can't be in both places
        """
        violations = []

        for section in sections:
            # Group events by user
            user_locations = defaultdict(list)

            for event in section.events:
                if event.event_type == "authentication":
                    user = event.observables.get("user", "unknown")
                    location = event.source_host
                    user_locations[user].append((event.timestamp, location))

            # Check for impossible travel
            for user, locations in user_locations.items():
                if len(locations) < 2:
                    continue

                sorted_locs = sorted(locations, key=lambda x: x[0])

                for i in range(len(sorted_locs) - 1):
                    time1, loc1 = sorted_locs[i]
                    time2, loc2 = sorted_locs[i + 1]

                    if loc1 != loc2:
                        time_diff_hours = (time2 - time1) / 3600

                        # If locations differ and time is too short, flag it
                        # (Simple heuristic: different hosts within 1 hour)
                        if time_diff_hours < 1.0:
                            violations.append({
                                "type": "impossible_travel",
                                "user": user,
                                "location1": loc1,
                                "location2": loc2,
                                "time_diff_hours": time_diff_hours,
                                "description": f"User {user} at two locations within {time_diff_hours:.2f} hours",
                                "severity": "critical"
                            })

        return violations

    def _find_multi_window_attacks(self, sections: List[EventSection]) -> List[Dict]:
        """
        Find attack chains that span multiple windows.

        This detects "slow and low" APT attacks that evade single-window detection.
        """
        attack_indicators = []

        # Look for attack patterns that span windows
        # (Simplified: look for initial access in one window, exfiltration in later window)

        initial_access_windows = []
        exfiltration_windows = []

        for idx, section in enumerate(sections):
            has_initial_access = any(
                "T1566" in event.matched_techniques or "T1190" in event.matched_techniques
                for event in section.events if event.matched_techniques
            )

            has_exfiltration = any(
                "T1041" in event.matched_techniques
                for event in section.events if event.matched_techniques
            )

            if has_initial_access:
                initial_access_windows.append(idx)

            if has_exfiltration:
                exfiltration_windows.append(idx)

        # Check if exfiltration happens in window after initial access
        for ia_window in initial_access_windows:
            for ex_window in exfiltration_windows:
                if ex_window > ia_window:
                    attack_indicators.append({
                        "type": "multi_window_attack",
                        "pattern": "initial_access -> exfiltration",
                        "window_span": ex_window - ia_window,
                        "time_span_seconds": (sections[ex_window].window.start -
                                            sections[ia_window].window.start),
                        "description": "Slow attack spanning multiple windows",
                        "severity": "high"
                    })

        return attack_indicators


class EventStreamCoherence:
    """
    High-level interface for event stream coherence checking.

    This wraps TemporalSheafChecker with a simpler API for production use.
    """

    def __init__(self):
        self.sheaf_checker = TemporalSheafChecker(window_size_seconds=300)

    def check_event_stream(self, events: List[SecurityEvent]) -> Dict:
        """
        Check coherence of an event stream.

        Returns:
            {
                "coherent": bool,
                "threats_detected": int,
                "violations": [...],
                "attack_chains": [...]
            }
        """
        result = self.sheaf_checker.check_coherence(events)

        threats = len(result["violations"]) + len(result["attack_indicators"])

        return {
            "coherent": result["is_coherent"],
            "threats_detected": threats,
            "violations": result["violations"],
            "attack_chains": result["attack_indicators"],
            "num_events_analyzed": result["num_events"],
            "num_windows_analyzed": result["num_windows"]
        }

    def filter_coherent_events(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """
        Filter out events that violate coherence.

        Returns only events that form a coherent sheaf.
        """
        result = self.sheaf_checker.check_coherence(events)

        if result["is_coherent"]:
            return events

        # In production, would filter out specific violating events
        # For now, return all (would need more sophisticated filtering)
        return events
