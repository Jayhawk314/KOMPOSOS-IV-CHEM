# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Topos-Based Attack Detector: Multi-Valued Truth Classification

Production wrapper for presheaf topos logic applied to cybersecurity.
Provides multi-valued truth (sieve-based) attack classification that
goes beyond binary detection.

Key capabilities:
  - Multi-perspective threat assessment (which sensors see the attack?)
  - Conditional threat inference (if A then B, via internal implication)
  - Technique similarity clustering (Yoneda distance metric)
  - Partial observability handling (intuitionistic logic, not classical)

Mathematical basis:
  - Subobject classifier Omega gives multi-valued truth
  - Sieves capture "from which perspectives is this true?"
  - Internal logic (intuitionistic) handles partial observability
  - Yoneda distance clusters functionally similar techniques
"""

from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass, field

from categorical.presheaf_topos import PresheafTopos, Sieve, SieveMorphism


@dataclass
class ThreatClassification:
    """Result of topos-based threat classification."""
    technique_id: str
    truth_value: float              # [0, 1] sieve truth
    supporting_perspectives: Set[str]  # Which techniques provide evidence
    evidence_paths: List[str]       # Named paths/morphisms
    confidence_level: str           # "high", "medium", "low", "none"
    intuitionistic_note: str        # Caveat about partial observability

    @property
    def is_significant(self) -> bool:
        return self.truth_value >= 0.3


@dataclass
class ConditionalThreat:
    """Result of conditional threat inference via internal implication."""
    if_technique: str
    then_technique: str
    implication_strength: float
    explanation: str


class ToposDetector:
    """
    Multi-valued truth attack detector using presheaf topos logic.

    Instead of binary detection, provides sieve-based truth values
    that capture partial observability and multi-sensor perspectives.

    Usage:
        detector = ToposDetector.from_enriched_category(enriched_cat)
        result = detector.assess_threat(["T1566", "T1059"])
        # Returns per-technique truth values from all perspectives
    """

    def __init__(self, topos: PresheafTopos):
        self.topos = topos

    @classmethod
    def from_enriched_category(cls, enriched_cat) -> 'ToposDetector':
        """Build detector from enriched attack category."""
        topos = PresheafTopos.from_enriched_category(enriched_cat)
        return cls(topos)

    def assess_threat(self, observed_techniques: List[str],
                      top_k: int = 10) -> List[ThreatClassification]:
        """
        Full threat assessment using topos logic.

        Args:
            observed_techniques: Techniques currently observed in the environment
            top_k: Return top-k most likely next techniques

        Returns:
            List of ThreatClassification, sorted by truth value descending
        """
        assessments = self.topos.threat_assessment(observed_techniques, top_k)

        results = []
        for tech_id, truth, perspectives in assessments:
            # Determine confidence level
            if truth >= 0.7:
                confidence = "high"
                note = "Strong evidence from multiple perspectives"
            elif truth >= 0.4:
                confidence = "medium"
                note = "Moderate evidence; some perspectives support this"
            elif truth >= 0.15:
                confidence = "low"
                note = ("Weak evidence; intuitionistic caveat: "
                        "absence of evidence is not evidence of absence")
            else:
                confidence = "none"
                note = "Minimal supporting evidence from current observations"

            # Get evidence paths
            sieve = self.topos.classify_attack(observed_techniques, tech_id)
            evidence = [m.name for m in sieve.morphisms]

            results.append(ThreatClassification(
                technique_id=tech_id,
                truth_value=truth,
                supporting_perspectives=perspectives,
                evidence_paths=evidence[:10],  # Cap at 10 for readability
                confidence_level=confidence,
                intuitionistic_note=note
            ))

        return results

    def conditional_inference(self, observed: List[str],
                              if_technique: str,
                              then_technique: str) -> ConditionalThreat:
        """
        Compute conditional threat: "If we see if_tech, does then_tech follow?"

        Measures how much the evidence for if_technique implies evidence
        for then_technique by comparing overlapping perspectives.

        "If evidence points to if_tech, then evidence also points to then_tech."
        """
        sieve_if = self.topos.classify_attack(observed, if_technique)
        sieve_then = self.topos.classify_attack(observed, then_technique)

        # Compare perspectives: how many sources that support if_tech
        # also support then_tech (via transitive paths)?
        perspectives_if = sieve_if.from_perspectives()
        perspectives_then = sieve_then.from_perspectives()

        if not perspectives_if:
            strength = 0.0
        else:
            # Fraction of if-perspectives that also support then
            overlap = perspectives_if & perspectives_then
            strength = len(overlap) / len(perspectives_if)

        if strength >= 0.8:
            explanation = (f"Strong implication: observing {if_technique} "
                          f"strongly predicts {then_technique}")
        elif strength >= 0.5:
            explanation = (f"Moderate implication: {if_technique} "
                          f"somewhat predicts {then_technique}")
        else:
            explanation = (f"Weak implication: {if_technique} "
                          f"does not strongly predict {then_technique}")

        return ConditionalThreat(
            if_technique=if_technique,
            then_technique=then_technique,
            implication_strength=strength,
            explanation=explanation
        )

    def find_technique_clusters(self, threshold: float = 0.3) -> List[List[str]]:
        """
        Cluster techniques by Yoneda similarity.

        Techniques with yoneda_distance < threshold are in the same cluster.
        These are functionally interchangeable from a categorical perspective.
        """
        techniques = list(self.topos.objects)
        visited = set()
        clusters = []

        for tech in techniques:
            if tech in visited:
                continue

            cluster = [tech]
            visited.add(tech)

            for other in techniques:
                if other in visited:
                    continue
                if self.topos.yoneda_distance(tech, other) < threshold:
                    cluster.append(other)
                    visited.add(other)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters

    def multi_sensor_fusion(self, sensor_observations: Dict[str, List[str]],
                            target: str) -> Dict:
        """
        Fuse observations from multiple sensors/perspectives.

        Each sensor provides a list of observed techniques.
        The topos naturally handles disagreement between sensors
        via sieve intersection/union.

        Args:
            sensor_observations: Dict mapping sensor_name -> observed techniques
            target: Technique to assess

        Returns:
            Dict with per-sensor sieves, fused sieve, and truth values
        """
        sensor_sieves = {}
        for sensor_name, observations in sensor_observations.items():
            sieve = self.topos.classify_attack(observations, target)
            total = self.topos.incoming_count(target)
            if total == 0:
                total = 1
            sensor_sieves[sensor_name] = {
                "sieve": sieve,
                "truth": sieve.truth_value(total),
                "perspectives": sieve.from_perspectives()
            }

        # Fuse via union (any sensor seeing it counts)
        all_morphisms = set()
        for info in sensor_sieves.values():
            all_morphisms |= info["sieve"].morphisms

        fused_sieve = Sieve(target, all_morphisms)
        total = self.topos.incoming_count(target)
        if total == 0:
            total = 1

        # Also compute intersection (all sensors agree)
        if sensor_sieves:
            consensus_morphisms = None
            for info in sensor_sieves.values():
                if consensus_morphisms is None:
                    consensus_morphisms = info["sieve"].morphisms.copy()
                else:
                    consensus_morphisms &= info["sieve"].morphisms
            consensus_sieve = Sieve(target, consensus_morphisms or set())
        else:
            consensus_sieve = self.topos.empty_sieve(target)

        return {
            "target": target,
            "per_sensor": {k: {"truth": v["truth"],
                              "perspectives": v["perspectives"]}
                          for k, v in sensor_sieves.items()},
            "fused_truth": fused_sieve.truth_value(total),
            "consensus_truth": consensus_sieve.truth_value(total),
            "fused_perspectives": fused_sieve.from_perspectives(),
            "consensus_perspectives": consensus_sieve.from_perspectives(),
            "sensor_agreement": (
                consensus_sieve.truth_value(total) / max(fused_sieve.truth_value(total), 1e-10)
                if fused_sieve.truth_value(total) > 0 else 1.0
            )
        }

    def attack_narrative(self, observed: List[str]) -> Dict:
        """
        Build a narrative of the attack using topos reasoning.

        Combines threat assessment, conditional inference, and
        Yoneda similarity to produce a structured story of what's
        happening, what's likely next, and what's similar.
        """
        # Current threat assessment
        threats = self.assess_threat(observed, top_k=5)

        # For top threats, compute conditional chains
        chains = []
        for threat in threats[:3]:
            if threat.is_significant:
                for other_threat in threats[:3]:
                    if other_threat.technique_id != threat.technique_id:
                        cond = self.conditional_inference(
                            observed,
                            threat.technique_id,
                            other_threat.technique_id
                        )
                        if cond.implication_strength >= 0.5:
                            chains.append(cond)

        # Find similar techniques to observed ones
        similar = {}
        for obs in observed[:5]:  # Limit for performance
            if obs in self.topos.objects:
                sim = self.topos.find_similar_techniques(obs, top_k=3)
                similar[obs] = sim

        return {
            "observed": observed,
            "threat_assessment": [
                {
                    "technique": t.technique_id,
                    "truth": t.truth_value,
                    "confidence": t.confidence_level,
                    "perspectives": list(t.supporting_perspectives)
                }
                for t in threats
            ],
            "conditional_chains": [
                {
                    "if": c.if_technique,
                    "then": c.then_technique,
                    "strength": c.implication_strength,
                    "explanation": c.explanation
                }
                for c in chains
            ],
            "similar_techniques": {
                k: [(t, d) for t, d in v]
                for k, v in similar.items()
            },
            "topos_summary": (
                f"Observed {len(observed)} techniques. "
                f"Top {len([t for t in threats if t.is_significant])} threats "
                f"have significant evidence (truth >= 0.3). "
                f"{len(chains)} conditional chains detected."
            )
        }
