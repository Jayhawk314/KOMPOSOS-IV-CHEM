# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Real-Time Attack Prediction Engine

Production API wrapping StreamingKanExtension with:
- Event ingestion from SIEM
- Prediction output as alerts
- Performance monitoring (< 10ms per event)

This module bridges the categorical mathematics (streaming Kan extensions
over comma categories) with operational cybersecurity workflows. Each
ingested event is mapped to a MITRE technique, fed through the streaming
Kan extension, and compared against configurable alert thresholds.

Mathematical foundation:
  Left Kan extension Lan_K(F)(e) = colim_{(K downarrow e)} F provides
  the prediction score for each candidate next-technique e.
"""

import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from categorical.streaming_kan import StreamingKanExtension, RightKanExtension
from cyber.stealth_scoring import StealthScorer
from cyber.mitre_integration import MITREDatabase

logger = logging.getLogger(__name__)


@dataclass
class PredictionAlert:
    """Alert generated when prediction confidence exceeds threshold."""
    predicted_technique: str
    technique_name: str
    confidence: float
    stealth_score: float
    supporting_evidence: List[str]
    timestamp: float
    alert_level: str  # "info", "warning", "critical"

    def to_dict(self) -> Dict:
        """Serialize alert to dictionary for JSON output or SIEM integration."""
        return {
            "predicted_technique": self.predicted_technique,
            "technique_name": self.technique_name,
            "confidence": self.confidence,
            "stealth_score": self.stealth_score,
            "supporting_evidence": self.supporting_evidence,
            "timestamp": self.timestamp,
            "alert_level": self.alert_level,
        }


def _classify_alert_level(confidence: float, stealth: float) -> str:
    """
    Determine alert severity from confidence and stealth.

    High confidence + high stealth = critical (stealthy attack predicted
    with strong evidence). Lower confidence or lower stealth produce
    correspondingly lower severity levels.

    Args:
        confidence: Prediction confidence in [0, 1].
        stealth: Stealth score of the predicted technique in [0, 1].

    Returns:
        One of "critical", "warning", or "info".
    """
    combined = confidence * 0.6 + stealth * 0.4
    if combined >= 0.75:
        return "critical"
    elif combined >= 0.50:
        return "warning"
    return "info"


class FirstMoveDetector:
    """
    Instant campaign matching on first observed technique.

    Solves the first-move problem by checking every observed technique
    against the first step of all known APT campaigns. When the very
    first event arrives, the system immediately knows: "This matches
    the opening move of APT29/Lazarus/Conti with confidence C."

    Confidence is computed as: steps_matched / total_chain_length.
    Seeing step 1 of a 7-step campaign gives confidence 1/7 = 0.14.
    Seeing steps 1-3 of a 7-step campaign gives confidence 3/7 = 0.43.

    This bridges the gap before the streaming Kan extension has enough
    observations to build meaningful colimit-based predictions.
    """

    def __init__(self, variant_detector):
        self.first_move_lookup: Dict[str, List[Dict]] = defaultdict(list)
        self._build_lookup(variant_detector)

    def _build_lookup(self, detector):
        """Build first-move → campaign lookup table."""
        for name, functor in detector.known_patterns.items():
            if not functor.instance:
                continue
            first_tech = functor.instance[0]
            chain_length = len(functor.instance)
            self.first_move_lookup[first_tech].append({
                "campaign": name,
                "full_chain": list(functor.instance),
                "confidence": 1.0 / chain_length,
                "predicted_next": (
                    functor.instance[1] if chain_length > 1 else None
                ),
                "predicted_chain": functor.instance[1:],
            })

    def check_first_move(self, technique_id: str) -> List[Dict]:
        """
        Check if a technique matches any known campaign's first move.

        Args:
            technique_id: The observed MITRE technique ID.

        Returns:
            List of matching campaign dicts, sorted by confidence descending.
        """
        return list(self.first_move_lookup.get(technique_id, []))

    def check_partial_chain(self, chain: List[str]) -> List[Dict]:
        """
        Check if a partial chain matches the prefix of any known campaign.

        This extends first-move matching to the first N steps. As more
        steps are observed, confidence increases proportionally.

        Args:
            chain: Ordered list of observed technique IDs.

        Returns:
            List of matching campaign dicts with updated confidence.
        """
        if not chain:
            return []

        matches = []
        for first_tech_matches in self.first_move_lookup.values():
            for match in first_tech_matches:
                full_chain = match["full_chain"]
                if len(chain) <= len(full_chain):
                    if full_chain[:len(chain)] == chain:
                        confidence = len(chain) / len(full_chain)
                        remaining = full_chain[len(chain):]
                        matches.append({
                            "campaign": match["campaign"],
                            "matched_steps": len(chain),
                            "total_steps": len(full_chain),
                            "confidence": confidence,
                            "predicted_next": (
                                remaining[0] if remaining else None
                            ),
                            "predicted_remaining": remaining,
                        })

        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return matches


class RealTimeAttackPredictor:
    """
    Production API for real-time attack prediction.

    Wraps StreamingKanExtension with event ingestion, alert generation,
    and performance monitoring. Designed for integration with SIEM systems
    and SOC dashboards.

    Usage:
        predictor = RealTimeAttackPredictor(alert_threshold=0.6)
        alert = predictor.ingest_event("T1566")      # Phishing observed
        alert = predictor.ingest_event("T1059")      # Scripting observed
        forecast = predictor.get_attack_forecast(3)   # 3-step lookahead
    """

    def __init__(self, alert_threshold: float = 0.7, decay_rate: float = 0.001,
                 environment=None):
        self.mitre_db = MITREDatabase(environment=environment)
        self.scorer = StealthScorer(environment=environment)
        self.streaming_kan = StreamingKanExtension(decay_rate=decay_rate)
        self.alert_threshold = alert_threshold
        self.alerts: List[PredictionAlert] = []
        self.event_count: int = 0
        self.total_processing_time: float = 0.0
        self._latency_samples: List[float] = []

        # First-move detection components
        try:
            self.right_kan = RightKanExtension(
                self.mitre_db,
                self.mitre_db.valid_compositions if hasattr(self.mitre_db, 'valid_compositions') else {}
            )
        except Exception:
            # Fallback if RightKanExtension signature differs
            self.right_kan = None
        self._first_move_detector: Optional[FirstMoveDetector] = None
        self._observed_chain: List[str] = []
        self._first_move_matches: List[Dict] = []
        self._priors_seeded: bool = False

    def seed_structural_priors(self, target_type: str = "server",
                               prior_weight: float = 0.15):
        """
        Pre-seed the streaming Kan extension with structural priors.

        Uses the right Kan extension to inject weighted structural
        observations into the left Kan's comma category BEFORE any
        real event arrives. This ensures the system never starts from
        zero — it always has non-zero predictions based on the attack
        graph topology.

        The prior_weight is kept low (0.15 default) so that real
        observations quickly dominate the priors via the colimit.

        Args:
            target_type: Asset type to compute priors for.
            prior_weight: Base weight for structural priors.
        """
        if self._priors_seeded:
            return

        if self.right_kan is None:
            # RightKanExtension not available, skip structural priors
            self._priors_seeded = True
            logger.warning("RightKanExtension unavailable, skipping structural priors")
            return

        priors = self.right_kan.get_priors_for_seeding(
            target_type, prior_weight
        )

        prior_time = time.time() - 1.0  # Slightly in the past

        for tech_id, weight in priors:
            # Each prior creates a single comma object in the category
            self.streaming_kan.comma_cat.add_observation(
                technique_id=f"_prior_{tech_id}",
                timestamp=prior_time,
                composable_targets=[(tech_id, weight)],
            )

        self._priors_seeded = True
        logger.info(
            "Seeded %d structural priors for target_type=%s",
            len(priors), target_type,
        )

    def set_first_move_detector(self, variant_detector):
        """
        Attach a FirstMoveDetector built from known APT campaigns.

        Args:
            variant_detector: NaturalTransformationDetector instance
                with known_patterns populated.
        """
        self._first_move_detector = FirstMoveDetector(variant_detector)

    def ingest_event(self, technique_id: str,
                     timestamp: float = None) -> Optional[PredictionAlert]:
        """
        Ingest one event. Return alert if confidence exceeds threshold.

        This is the main entry point for SIEM integration. Each call:
        1. Looks up composable successors from the MITRE database
        2. Feeds the observation to the streaming Kan extension
        3. Checks whether any prediction exceeds the alert threshold
        4. If so, constructs and returns a PredictionAlert

        Performance target: < 10ms per event.

        Args:
            technique_id: The observed MITRE ATT&CK technique ID.
            timestamp: Event timestamp in seconds since epoch. If None,
                uses the current wall clock time.

        Returns:
            A PredictionAlert if any prediction exceeds the configured
            alert_threshold, otherwise None.
        """
        start_time = time.perf_counter()

        if timestamp is None:
            timestamp = time.time()

        self.event_count += 1

        # Step 1: Look up composable successors for this technique
        try:
            composable_targets = self.mitre_db.get_composable_successors(
                technique_id
            )
        except Exception as exc:
            logger.warning(
                "Failed to get composable successors for %s: %s",
                technique_id, exc,
            )
            composable_targets = []

        # Step 2: Feed observation into the streaming Kan extension
        self.streaming_kan.observe(technique_id, timestamp, composable_targets)

        # Step 3: Get current top prediction
        predictions = self.streaming_kan.predict(top_k=1)

        # Record latency
        elapsed = time.perf_counter() - start_time
        elapsed_ms = elapsed * 1000.0
        self.total_processing_time += elapsed_ms
        self._latency_samples.append(elapsed_ms)

        if not predictions:
            return None

        top = predictions[0]

        # Step 3b: First-move campaign matching
        self._observed_chain.append(technique_id)
        if self._first_move_detector is not None:
            fm_matches = self._first_move_detector.check_partial_chain(
                self._observed_chain
            )
            if fm_matches:
                self._first_move_matches = fm_matches
                # Boost confidence if campaign match found —
                # the first-move detector provides structural evidence
                # that supplements the Kan extension's colimit
                best_match = fm_matches[0]
                boosted_confidence = max(
                    top["confidence"],
                    best_match["confidence"] * 0.8,
                )
                top = dict(top)
                top["confidence"] = boosted_confidence
                top["first_move_match"] = best_match["campaign"]

        # Step 4: Check if the top prediction exceeds the alert threshold
        if top["confidence"] < self.alert_threshold:
            return None

        # Build alert
        technique_obj = self.mitre_db.get_technique(top["technique"])
        technique_name = (
            technique_obj.name if technique_obj else top["technique"]
        )
        stealth = self.scorer.get_stealth(top["technique"])
        alert_level = _classify_alert_level(top["confidence"], stealth)

        alert = PredictionAlert(
            predicted_technique=top["technique"],
            technique_name=technique_name,
            confidence=top["confidence"],
            stealth_score=stealth,
            supporting_evidence=top.get("supporting_evidence", []),
            timestamp=timestamp,
            alert_level=alert_level,
        )

        self.alerts.append(alert)

        logger.info(
            "ALERT [%s] Predicted %s (%s) confidence=%.3f stealth=%.3f",
            alert_level.upper(),
            technique_name,
            top["technique"],
            top["confidence"],
            stealth,
        )

        return alert

    def get_attack_forecast(self, horizon_steps: int = 3) -> List[Dict]:
        """
        Multi-step forecast of likely attack progression.

        Uses iterated Kan extension: at each step, the top prediction is
        treated as a hypothetical observation, and the Kan extension is
        re-evaluated. Confidence decays geometrically across steps.

        Args:
            horizon_steps: Number of steps to forecast (default 3).

        Returns:
            List of dictionaries, one per forecast step, each containing:
            - step: the forecast step number (1-indexed)
            - predictions: list of predicted techniques with scores
        """
        def composable_fn(tech_id: str):
            return self.mitre_db.get_composable_successors(tech_id)

        raw_forecast = self.streaming_kan.multi_step_forecast(
            steps=horizon_steps,
            composable_fn=composable_fn,
        )

        result = []
        for step_idx, step_preds in enumerate(raw_forecast):
            enriched_preds = []
            for pred in step_preds:
                technique_obj = self.mitre_db.get_technique(pred["technique"])
                stealth = self.scorer.get_stealth(pred["technique"])
                enriched_preds.append({
                    "technique": pred["technique"],
                    "technique_name": (
                        technique_obj.name if technique_obj
                        else pred["technique"]
                    ),
                    "score": pred["score"],
                    "confidence": pred["confidence"],
                    "stealth_score": stealth,
                    "n_contributors": pred.get("n_contributors", 0),
                    "supporting_evidence": pred.get(
                        "supporting_evidence", []
                    ),
                })
            result.append({
                "step": step_idx + 1,
                "predictions": enriched_preds,
            })

        return result

    def get_current_predictions(self, top_k: int = 5) -> List[Dict]:
        """
        Get current prediction state without generating alerts.

        Useful for dashboard display where you want to show the full
        prediction landscape regardless of threshold.

        Args:
            top_k: Number of top predictions to return.

        Returns:
            List of prediction dictionaries enriched with technique names
            and stealth scores.
        """
        raw = self.streaming_kan.predict(top_k=top_k)

        results = []
        for pred in raw:
            technique_obj = self.mitre_db.get_technique(pred["technique"])
            stealth = self.scorer.get_stealth(pred["technique"])
            results.append({
                "technique": pred["technique"],
                "technique_name": (
                    technique_obj.name if technique_obj
                    else pred["technique"]
                ),
                "score": pred["score"],
                "confidence": pred["confidence"],
                "stealth_score": stealth,
                "n_contributors": pred.get("n_contributors", 0),
                "supporting_evidence": pred.get("supporting_evidence", []),
                "alert_level": _classify_alert_level(
                    pred["confidence"], stealth
                ),
            })

        return results

    def get_performance_stats(self) -> Dict:
        """
        Get performance metrics for monitoring and SLA compliance.

        Returns:
            Dictionary with event count, total processing time, average
            latency per event, peak latency, and the p95 latency. All
            latency values are in milliseconds.
        """
        stats: Dict = {
            "event_count": self.event_count,
            "total_processing_time_ms": round(self.total_processing_time, 3),
            "alert_count": len(self.alerts),
            "comma_category_size": self.streaming_kan.get_comma_category_size(),
        }

        if self._latency_samples:
            stats["avg_latency_ms"] = round(
                self.total_processing_time / len(self._latency_samples), 3
            )
            stats["max_latency_ms"] = round(max(self._latency_samples), 3)

            # p95 latency
            sorted_samples = sorted(self._latency_samples)
            p95_idx = int(len(sorted_samples) * 0.95)
            p95_idx = min(p95_idx, len(sorted_samples) - 1)
            stats["p95_latency_ms"] = round(sorted_samples[p95_idx], 3)

            # Check SLA compliance (< 10ms per event)
            violations = sum(
                1 for s in self._latency_samples if s > 10.0
            )
            stats["sla_violations"] = violations
            stats["sla_compliance_pct"] = round(
                100.0 * (1 - violations / len(self._latency_samples)), 2
            )
        else:
            stats["avg_latency_ms"] = 0.0
            stats["max_latency_ms"] = 0.0
            stats["p95_latency_ms"] = 0.0
            stats["sla_violations"] = 0
            stats["sla_compliance_pct"] = 100.0

        return stats

    def reset(self):
        """
        Reset predictor state.

        Clears all accumulated observations, alerts, and performance
        counters. The MITRE database, stealth scorer, right Kan extension,
        and first-move detector are preserved since they are static.
        """
        self.streaming_kan = StreamingKanExtension(
            decay_rate=self.streaming_kan.comma_cat.decay_rate
        )
        self.alerts.clear()
        self.event_count = 0
        self.total_processing_time = 0.0
        self._latency_samples.clear()
        self._observed_chain.clear()
        self._first_move_matches.clear()
        self._priors_seeded = False
        logger.info("RealTimeAttackPredictor state has been reset.")

    def get_recent_alerts(self, max_count: int = 10) -> List[Dict]:
        """
        Get the most recent alerts as dictionaries.

        Args:
            max_count: Maximum number of alerts to return.

        Returns:
            List of alert dictionaries, most recent first.
        """
        recent = self.alerts[-max_count:]
        recent.reverse()
        return [a.to_dict() for a in recent]
