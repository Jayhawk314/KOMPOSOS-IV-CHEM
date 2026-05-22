# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Attack Chain Detection Strategies

Core insight: Attack chains are composed morphisms in a category.
Unlike signature-based detection (pattern matching), this detects attacks
via compositional structure.

Example:
  Signature-based: Look for "mimikatz.exe" → 90% of APTs evade this
  Compositional: Look for initial_access ∘ privilege_escalation ∘ credential_dump
                 → Can't evade because attack MUST compose this way

This is why KOMPOSOS-SEC detects zero-days: the compositional structure
is invariant even if the specific technique changes.
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import time

from cyber.mitre_integration import MITREDatabase, ATTACKTechnique, MITRETactic
from oracle.prediction import Prediction


@dataclass
class SecurityEvent:
    """
    A single security event (log entry, alert, observation).

    In category theory: This is a morphism in the temporal sheaf.
    Events must satisfy local coherence: events that agree on time windows.
    """
    timestamp: float  # Unix timestamp
    event_type: str   # "process", "network", "file", "authentication"
    observables: Dict[str, str]  # Key-value pairs (e.g., {"process": "powershell.exe"})
    source_host: str
    destination_host: Optional[str] = None

    # Inferred MITRE mapping
    matched_techniques: List[str] = None  # ATT&CK technique IDs
    confidence: float = 0.0

    def __post_init__(self):
        if self.matched_techniques is None:
            self.matched_techniques = []


class AttackChainStrategy:
    """
    Detects attack chains by composing observed events into MITRE ATT&CK sequences.

    This is the core KOMPOSOS-SEC strategy:
    1. Map observed events to MITRE techniques (with uncertainty)
    2. Find valid compositions (attack chains)
    3. Score by compositional coherence

    Unlike traditional SIEM correlation, this uses category theory to ensure
    detected chains satisfy compositional constraints.
    """

    def __init__(self, store=None, use_semantic_matching: bool = False,
                 semantic_model: str = "all-mpnet-base-v2"):
        self.store = store
        self.name = "attack_chain_composition"
        self.mitre_db = MITREDatabase()
        self.event_buffer: List[SecurityEvent] = []
        self.time_window_seconds = 3600  # 1 hour sliding window
        self.use_semantic_matching = use_semantic_matching
        self._semantic_matcher = None
        self._semantic_model = semantic_model

    def predict(self, source_obj) -> List[Prediction]:
        """
        Given a sequence of security events, predict attack chains.

        Args:
            source_obj: Should contain security events in metadata["events"]

        Returns:
            Predictions for possible attack chains
        """
        if not hasattr(source_obj, "metadata") or "events" not in source_obj.metadata:
            return []

        events = source_obj.metadata["events"]

        # Step 1: Map events to MITRE techniques
        mapped_events = self._map_events_to_techniques(events)

        # Step 2: Find valid attack chains
        attack_chains = self._find_attack_chains(mapped_events)

        # Step 3: Generate predictions
        predictions = []
        for chain, score in attack_chains:
            pred = self._create_chain_prediction(chain, score)
            predictions.append(pred)

        return predictions

    def _map_events_to_techniques(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """
        Map security events to MITRE ATT&CK techniques.

        This is fuzzy matching with confidence scores.
        Multiple techniques may match a single event.
        """
        mapped = []

        for event in events:
            matched_techniques = []

            # Check each MITRE technique for observable matches
            for tech_id, technique in self.mitre_db.techniques.items():
                match_score = self._compute_match_score(event, technique)
                if match_score > 0.3:  # Threshold for considering a match
                    matched_techniques.append(tech_id)

            event.matched_techniques = matched_techniques
            event.confidence = 0.7 if matched_techniques else 0.0  # Base confidence
            mapped.append(event)

        return mapped

    def _compute_match_score(self, event: SecurityEvent, technique: ATTACKTechnique) -> float:
        """
        Compute how well an event matches a MITRE technique.

        If semantic matching is enabled, delegates to SemanticEventMatcher.
        Otherwise uses symbolic observable matching.
        """
        if self.use_semantic_matching:
            return self._compute_semantic_match_score(event, technique)

        if event.event_type not in technique.observables:
            return 0.0

        expected_observables = technique.observables[event.event_type]

        # Check for substring matches
        matches = 0
        for expected in expected_observables:
            for obs_value in event.observables.values():
                if expected.lower() in obs_value.lower():
                    matches += 1
                    break

        return matches / len(expected_observables) if expected_observables else 0.0

    def _compute_semantic_match_score(self, event: SecurityEvent, technique: ATTACKTechnique) -> float:
        """Compute match score using semantic embeddings."""
        if self._semantic_matcher is None:
            from cyber.semantic_event_matcher import SemanticEventMatcher
            self._semantic_matcher = SemanticEventMatcher(
                model_name=self._semantic_model,
                mitre_db=self.mitre_db
            )
        return self._semantic_matcher.compute_semantic_match_score(
            event.observables, technique
        )

    def _find_attack_chains(self, events: List[SecurityEvent]) -> List[Tuple[List[str], float]]:
        """
        Find valid attack chains from mapped events.

        This is the key compositional step:
        - Group events by time window
        - Find sequences where techniques compose
        - Score by coherence + completeness

        Returns list of (technique_sequence, confidence_score)
        """
        if not events:
            return []

        # Sort events by time
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Sliding window to find chains
        chains = []
        window_start = sorted_events[0].timestamp
        window_end = window_start + self.time_window_seconds

        i = 0
        while i < len(sorted_events):
            # Collect events in current window
            window_events = []
            j = i
            while j < len(sorted_events) and sorted_events[j].timestamp < window_end:
                window_events.append(sorted_events[j])
                j += 1

            # Find chains within this window
            window_chains = self._extract_chains_from_window(window_events)
            chains.extend(window_chains)

            # Slide window
            window_start = window_end
            window_end = window_start + self.time_window_seconds
            i = j

        # Deduplicate and rank
        return self._rank_chains(chains)

    def _extract_chains_from_window(self, events: List[SecurityEvent]) -> List[Tuple[List[str], float]]:
        """
        Extract valid technique chains from events in a time window.

        Uses dynamic programming to find maximal valid chains.
        """
        if not events:
            return []

        # Collect all candidate techniques
        all_techniques = []
        for event in events:
            all_techniques.extend(event.matched_techniques)

        if not all_techniques:
            return []

        # Remove duplicates while preserving order
        seen = set()
        unique_techniques = []
        for tech in all_techniques:
            if tech not in seen:
                unique_techniques.append(tech)
                seen.add(tech)

        # Find all valid chains (sequences where each step composes)
        chains = []

        # Check all subsequences
        for start_idx in range(len(unique_techniques)):
            current_chain = [unique_techniques[start_idx]]

            for next_idx in range(start_idx + 1, len(unique_techniques)):
                next_tech = unique_techniques[next_idx]
                current_tech = current_chain[-1]

                # Check if composition is valid
                if self.mitre_db.can_compose(current_tech, next_tech):
                    current_chain.append(next_tech)

            if len(current_chain) >= 2:  # Only keep chains with 2+ steps
                score = self._score_chain(current_chain, events)
                chains.append((current_chain, score))

        return chains

    def _score_chain(self, technique_chain: List[str], events: List[SecurityEvent]) -> float:
        """
        Score an attack chain by compositional coherence.

        Higher score for:
        - Longer chains (more complete attack)
        - Strong event evidence
        - Valid compositions throughout
        """
        if not technique_chain:
            return 0.0

        # Base score: chain length (normalized)
        length_score = min(1.0, len(technique_chain) / 5.0)  # Chains of 5+ get max score

        # Composition validity score
        valid_compositions = sum(
            1 for i in range(len(technique_chain) - 1)
            if self.mitre_db.can_compose(technique_chain[i], technique_chain[i+1])
        )
        composition_score = valid_compositions / (len(technique_chain) - 1) if len(technique_chain) > 1 else 0.0

        # Event evidence score (how strong is the observable evidence?)
        evidence_score = sum(event.confidence for event in events) / len(events) if events else 0.5

        # Weighted combination
        total_score = (
            0.3 * length_score +
            0.5 * composition_score +
            0.2 * evidence_score
        )

        return total_score

    def _rank_chains(self, chains: List[Tuple[List[str], float]]) -> List[Tuple[List[str], float]]:
        """Deduplicate and rank attack chains by score."""
        if not chains:
            return []

        # Deduplicate by chain content
        unique_chains = {}
        for chain, score in chains:
            chain_key = tuple(chain)
            if chain_key not in unique_chains or unique_chains[chain_key] < score:
                unique_chains[chain_key] = score

        # Convert back to list and sort by score
        ranked = [(list(chain), score) for chain, score in unique_chains.items()]
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def _create_chain_prediction(self, technique_chain: List[str], score: float) -> Prediction:
        """Create a Prediction object for an attack chain."""
        # Get technique names for readability
        technique_names = [
            self.mitre_db.get_technique(tid).name if self.mitre_db.get_technique(tid) else tid
            for tid in technique_chain
        ]

        chain_str = " -> ".join(technique_names)

        explanation = self.mitre_db.explain_composition(technique_chain)

        return Prediction(
            source=technique_chain[0],
            target=technique_chain[-1],
            predicted_relation=f"attack_chain_{len(technique_chain)}_steps",
            prediction_type="COMPOSITION",
            strategy_name=self.name,
            confidence=score,
            reasoning=f"Detected {len(technique_chain)}-step attack chain: {chain_str}",
            evidence={
                "chain": technique_chain,
                "chain_names": technique_names,
                "length": len(technique_chain),
                "explanation": explanation
            }
        )


class MITRECompositionStrategy:
    """
    Validates if a proposed attack chain satisfies MITRE ATT&CK composition rules.

    This is a "checker" strategy: given a sequence of techniques, verify if
    they compose validly. Used for:
    - Validating threat intelligence
    - Scoring incident reports
    - Training data quality checks
    """

    def __init__(self, store=None):
        self.store = store
        self.name = "mitre_composition_validator"
        self.mitre_db = MITREDatabase()

    def predict(self, source_obj) -> List[Prediction]:
        """
        Validate if source_obj contains a valid MITRE attack chain.

        Args:
            source_obj: Should contain technique chain in metadata["technique_chain"]

        Returns:
            Single prediction indicating if chain is valid
        """
        if not hasattr(source_obj, "metadata") or "technique_chain" not in source_obj.metadata:
            return []

        chain = source_obj.metadata["technique_chain"]

        if not isinstance(chain, list) or len(chain) < 2:
            return []

        # Check each composition in the chain
        valid = True
        violations = []

        for i in range(len(chain) - 1):
            tech1 = chain[i]
            tech2 = chain[i + 1]

            if not self.mitre_db.can_compose(tech1, tech2):
                valid = False
                violations.append(f"{tech1} -> {tech2}")

        confidence = 1.0 if valid else 0.2  # Low confidence if violations exist

        reasoning = "Valid MITRE ATT&CK composition" if valid else f"Invalid compositions: {', '.join(violations)}"

        return [
            Prediction(
                source=chain[0],
                target=chain[-1],
                predicted_relation="valid_attack_chain" if valid else "invalid_attack_chain",
                prediction_type="COMPOSITION",
                strategy_name=self.name,
                confidence=confidence,
                reasoning=reasoning,
                evidence={
                    "chain": chain,
                    "valid": valid,
                    "violations": violations if violations else None,
                    "explanation": self.mitre_db.explain_composition(chain)
                }
            )
        ]
