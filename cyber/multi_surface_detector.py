# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>
"""
Multi-Surface APT Detection Engine

Uses Grothendieck construction (Construction 5) to detect attacks that pivot
across network surfaces. Designed for SolarWinds-class APT detection where
adversaries traverse Application -> Endpoint -> Identity -> Cloud -> Network.

This module is the production wrapper around the categorical machinery:
  - GrothendieckConstruction provides the mathematical framework
  - MultiSurfaceDetector provides the operational detection API

Key capability: Detecting attack chains that no single-surface monitor
can see. Each surface (EDR, IAM, CSPM, NDR, K8s) sees fragments;
the Grothendieck total category unifies them into complete chains.

References:
  - MITRE ATT&CK v18.1 cross-platform mappings
  - SolarWinds post-mortem (CISA AA21-008A)
  - Kaseya VSA incident analysis (CISA AA21-188A)
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import time
import math

from categorical.grothendieck import (
    GrothendieckConstruction,
    FiberedObject,
    ATTACK_SURFACES,
    SURFACE_PIVOTS,
    SURFACE_CLASSIFICATION,
)
from cyber.mitre_integration import MITREDatabase


# Known APT cross-surface patterns.
# Each pattern is a list of (surface, representative_techniques) describing
# the canonical kill chain for that APT group.
APT_PATTERNS: Dict[str, List[Tuple[str, List[str]]]] = {
    "SolarWinds (APT29/Cozy Bear)": [
        ("Application", ["T1195.002", "T1195"]),       # Supply chain compromise
        ("Endpoint", ["T1059", "T1055", "T1027"]),      # Execution + evasion
        ("Identity", ["T1078", "T1556"]),                # Valid accounts + auth mod
        ("Cloud", ["T1078.004", "T1530", "T1537"]),     # Cloud pivot + exfil
    ],
    "Kaseya (REvil)": [
        ("Application", ["T1190", "T1195.002"]),        # Exploit public-facing + supply chain
        ("Endpoint", ["T1059", "T1486"]),                # Execution + ransomware
        ("Network", ["T1021"]),                          # Lateral movement
    ],
    "Log4Shell exploitation": [
        ("Application", ["T1190"]),                      # Exploit public-facing app
        ("Endpoint", ["T1059", "T1068"]),                # RCE + priv esc
        ("Cloud", ["T1552.005", "T1078.004"]),           # IMDS credential theft
        ("Network", ["T1071", "T1041"]),                 # C2 + exfiltration
    ],
    "Cloud-native lateral (UNC2903-style)": [
        ("Cloud", ["T1078.004", "T1580"]),               # Cloud account + discovery
        ("Identity", ["T1098.003"]),                      # Additional cloud roles
        ("Cloud", ["T1578.002", "T1530"]),               # New instance + data access
        ("Network", ["T1041"]),                          # Exfiltration
    ],
    "Container escape to cloud": [
        ("Container", ["T1610", "T1611"]),               # Deploy container + escape
        ("Endpoint", ["T1059", "T1003"]),                # Execution + cred dump
        ("Identity", ["T1078"]),                          # Valid accounts
        ("Cloud", ["T1078.004", "T1537"]),               # Cloud pivot + exfil
    ],
    "Identity-driven APT": [
        ("Application", ["T1566"]),                      # Phishing
        ("Endpoint", ["T1059", "T1003"]),                # Execution + cred dump
        ("Identity", ["T1558.003", "T1558", "T1556"]),   # Kerberoast + ticket forge + auth mod
        ("Network", ["T1021"]),                          # Lateral movement
        ("Cloud", ["T1078.004"]),                        # Cloud pivot
    ],
    # Crypto-unified APT patterns
    "PKI Compromise (APT-style)": [
        ("Application", ["T1190"]),                                      # Exploit app
        ("Cryptographic", ["TCRYPTO_001", "TCRYPTO_002", "TCRYPTO_005"]),# Weak key + forgery
        ("Identity", ["T1078"]),                                         # Valid accounts
        ("Cloud", ["T1078.004", "T1530"]),                              # Cloud pivot + data
    ],
    "Quantum Harvest Campaign": [
        ("Network", ["T1071"]),                                          # Network capture
        ("Cryptographic", ["TCRYPTO_006", "TCRYPTO_008"]),              # Harvest + downgrade
        ("Endpoint", ["T1059", "T1005"]),                               # Execution + collect
        ("Network", ["T1041"]),                                          # Exfiltration
    ],
    "Certificate Supply Chain": [
        ("Application", ["T1195", "T1190"]),                            # Supply chain / exploit
        ("Cryptographic", ["TCRYPTO_007", "TCRYPTO_005"]),              # CA compromise + forgery
        ("Identity", ["T1078", "T1556"]),                               # Auth abuse
        ("Network", ["T1021", "T1041"]),                                # Lateral + exfil
    ],
}


@dataclass
class SurfacePivotAlert:
    """Alert for cross-surface attack pivot."""
    source_surface: str
    target_surface: str
    source_technique: str
    target_technique: str
    pivot_stealth: float
    timestamp: float
    alert_level: str  # "critical", "high", "medium", "low"

    def __repr__(self):
        return (
            f"PivotAlert({self.source_surface}->{self.target_surface}, "
            f"{self.source_technique}->{self.target_technique}, "
            f"level={self.alert_level})"
        )


@dataclass
class CrossSurfaceChain:
    """Complete cross-surface attack chain detection."""
    surfaces_crossed: List[str]
    techniques: List[str]
    total_stealth: float
    pivot_count: int
    matching_apt: str  # Known APT pattern match or "Unknown"

    def __repr__(self):
        surfaces_str = " -> ".join(self.surfaces_crossed)
        return (
            f"CrossSurfaceChain({surfaces_str}, "
            f"pivots={self.pivot_count}, "
            f"stealth={self.total_stealth:.3f}, "
            f"match={self.matching_apt})"
        )


class MultiSurfaceDetector:
    """
    Production engine for cross-surface APT detection.

    Wraps the Grothendieck construction to provide:
      1. Real-time pivot detection from event streams
      2. APT pattern matching against known cross-surface kill chains
      3. Attack surface coverage reporting
      4. Cross-surface chain discovery for threat hunting

    Usage:
        detector = MultiSurfaceDetector()
        result = detector.analyze_events(["T1190", "T1059", "T1003", "T1078", "T1078.004"])
        # Returns pivot alerts, chain matches, and risk assessment
    """

    def __init__(self, environment=None):
        self.environment = environment
        self.mitre_db = MITREDatabase(environment=environment)

        # Build Grothendieck construction from surface classification
        base_objects = list(SURFACE_CLASSIFICATION.keys())
        fiber_classification = SURFACE_CLASSIFICATION

        # Parse pivot keys like "Application->Endpoint" into transition tuples
        base_transitions = {}
        for pivot_key in SURFACE_PIVOTS.keys():
            parts = pivot_key.split("->")
            if len(parts) == 2:
                src, dst = parts[0].strip(), parts[1].strip()
                base_transitions[(src, dst)] = 0.7

        self.grothendieck = GrothendieckConstruction(
            base_objects=base_objects,
            fiber_classification=fiber_classification,
            base_transitions=base_transitions,
        )
        self._build_apt_signatures()

    def _build_apt_signatures(self):
        """
        Pre-process known APT patterns into surface-transition signatures.

        Each APT pattern is reduced to a sequence of surface transitions
        that can be matched against observed pivot sequences.
        """
        self._apt_surface_signatures: Dict[str, List[str]] = {}
        self._apt_technique_sets: Dict[str, Set] = {}

        for apt_name, stages in APT_PATTERNS.items():
            surface_seq = [stage[0] for stage in stages]
            self._apt_surface_signatures[apt_name] = surface_seq

            tech_set = set()
            for _, techs in stages:
                tech_set.update(techs)
            self._apt_technique_sets[apt_name] = tech_set

    def analyze_events(self, technique_sequence: List[str]) -> Dict:
        """
        Full analysis of event sequence for cross-surface attacks.

        Takes a sequence of MITRE technique IDs (as observed in the event
        stream) and returns a comprehensive analysis including:
          - Pivot alerts for each surface transition
          - APT pattern matches
          - Risk assessment
          - Surface coverage of the observed chain
          - Recommended response actions

        Args:
            technique_sequence: Ordered list of MITRE technique IDs.

        Returns:
            Dict with keys: pivots, chain, apt_match, risk_score,
            surface_coverage, recommendations.
        """
        if not technique_sequence:
            return {
                "pivots": [],
                "chain": None,
                "apt_match": None,
                "risk_score": 0.0,
                "surface_coverage": {},
                "recommendations": [],
            }

        # Detect pivot events
        pivot_alerts = self.detect_pivots(technique_sequence)

        # Build the surface chain
        surfaces_in_chain = []
        for tech_id in technique_sequence:
            surfaces = self.grothendieck.classify_technique_surface(tech_id)
            if surfaces:
                # Pick the surface that continues from the previous one if possible
                if surfaces_in_chain:
                    prev = surfaces_in_chain[-1]
                    if prev in surfaces:
                        surfaces_in_chain.append(prev)
                    else:
                        surfaces_in_chain.append(surfaces[0])
                else:
                    surfaces_in_chain.append(surfaces[0])

        # Deduplicate consecutive surfaces for the chain summary
        unique_surfaces = []
        for s in surfaces_in_chain:
            if not unique_surfaces or unique_surfaces[-1] != s:
                unique_surfaces.append(s)

        # Compute total stealth
        from cyber.stealth_scoring import StealthScorer
        scorer = StealthScorer(environment=self.environment)
        total_stealth = scorer.chain_stealth(technique_sequence)

        # Match against known APT patterns
        apt_match = self.identify_apt_pattern(technique_sequence)

        # Build chain object
        chain = CrossSurfaceChain(
            surfaces_crossed=unique_surfaces,
            techniques=technique_sequence,
            total_stealth=total_stealth,
            pivot_count=len(pivot_alerts),
            matching_apt=apt_match if apt_match else "Unknown",
        )

        # Risk score: higher pivots + higher stealth + APT match = higher risk
        risk_score = self._compute_risk_score(
            pivot_count=len(pivot_alerts),
            total_stealth=total_stealth,
            chain_length=len(technique_sequence),
            apt_matched=apt_match is not None,
            surfaces_count=len(unique_surfaces),
        )

        # Surface coverage
        coverage = self._compute_surface_coverage(technique_sequence)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            pivot_alerts, chain, risk_score, apt_match
        )

        return {
            "pivots": pivot_alerts,
            "chain": chain,
            "apt_match": apt_match,
            "risk_score": round(risk_score, 4),
            "surface_coverage": coverage,
            "recommendations": recommendations,
        }

    def detect_pivots(self, technique_sequence: List[str]) -> List[SurfacePivotAlert]:
        """
        Detect surface pivots in event sequence.

        Delegates to the Grothendieck construction's detect_pivot method,
        then wraps results as SurfacePivotAlert objects with alert levels.
        """
        raw_pivots = self.grothendieck.detect_pivot(technique_sequence)
        alerts = []

        for pivot in raw_pivots:
            alert_level = self._classify_alert_level(
                pivot["source_surface"],
                pivot["target_surface"],
                pivot["pivot_stealth"],
                pivot["valid_pivot"],
            )

            alert = SurfacePivotAlert(
                source_surface=pivot["source_surface"],
                target_surface=pivot["target_surface"],
                source_technique=pivot["source_technique"],
                target_technique=pivot["target_technique"],
                pivot_stealth=pivot["pivot_stealth"],
                timestamp=time.time(),
                alert_level=alert_level,
            )
            alerts.append(alert)

        return alerts

    def _classify_alert_level(self, source_surface: str, target_surface: str,
                              stealth: float, valid_pivot: bool) -> str:
        """
        Classify pivot alert level based on surface transition and stealth.

        Critical: High-stealth pivots involving Identity or Cloud surfaces.
        High: Any cross-surface pivot with stealth > 0.6.
        Medium: Known pivot patterns with moderate stealth.
        Low: Well-known transitions with low stealth.
        """
        # Identity or Cloud involvement raises severity
        high_value_surfaces = {"Identity", "Cloud"}
        involves_high_value = (
            source_surface in high_value_surfaces or
            target_surface in high_value_surfaces
        )

        if involves_high_value and stealth > 0.5:
            return "critical"
        elif stealth > 0.6:
            return "high"
        elif valid_pivot and stealth > 0.3:
            return "medium"
        else:
            return "low"

    def identify_apt_pattern(self, chain: List[str]) -> Optional[str]:
        """
        Match cross-surface chain to known APT patterns.

        Matching is based on:
          1. Surface transition sequence similarity
          2. Technique overlap with known APT tool sets

        Returns the name of the best-matching APT pattern, or None.
        """
        chain_set = set(chain)

        # Build the observed surface sequence
        observed_surfaces = []
        for tech_id in chain:
            surfaces = self.grothendieck.classify_technique_surface(tech_id)
            if surfaces:
                if observed_surfaces:
                    prev = observed_surfaces[-1]
                    if prev in surfaces:
                        observed_surfaces.append(prev)
                    else:
                        observed_surfaces.append(surfaces[0])
                else:
                    observed_surfaces.append(surfaces[0])

        # Deduplicate consecutive surfaces
        observed_unique = []
        for s in observed_surfaces:
            if not observed_unique or observed_unique[-1] != s:
                observed_unique.append(s)

        best_match = None
        best_score = 0.0

        for apt_name, apt_surface_seq in self._apt_surface_signatures.items():
            # Surface sequence similarity (subsequence matching)
            surface_score = self._subsequence_similarity(
                observed_unique, apt_surface_seq
            )

            # Technique overlap (Jaccard-like)
            apt_techs = self._apt_technique_sets[apt_name]
            overlap = len(chain_set & apt_techs)
            tech_score = overlap / max(len(apt_techs), 1)

            # Combined score: weighted average
            combined = 0.6 * surface_score + 0.4 * tech_score

            if combined > best_score and combined >= 0.3:
                best_score = combined
                best_match = apt_name

        return best_match

    def _subsequence_similarity(self, observed: List[str],
                                pattern: List[str]) -> float:
        """
        Compute how well the observed surface sequence matches the pattern.

        Uses longest common subsequence (LCS) normalized by pattern length.
        """
        if not pattern or not observed:
            return 0.0

        n = len(observed)
        m = len(pattern)

        # LCS dynamic programming
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if observed[i - 1] == pattern[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        lcs_length = dp[n][m]
        return lcs_length / m

    def get_attack_surface_coverage(self) -> Dict[str, int]:
        """
        Get technique count per surface from the Grothendieck construction.

        Returns a dict mapping each surface name to the number of techniques
        classified in that surface's fiber.
        """
        stats = self.grothendieck.get_surface_stats()
        return stats["surface_object_counts"]

    def _compute_surface_coverage(self, technique_sequence: List[str]) -> Dict[str, int]:
        """
        Count how many techniques in the sequence fall in each surface.
        """
        coverage: Dict[str, int] = {s: 0 for s in ATTACK_SURFACES}
        for tech_id in technique_sequence:
            surfaces = self.grothendieck.classify_technique_surface(tech_id)
            for s in surfaces:
                coverage[s] = coverage.get(s, 0) + 1
        return coverage

    def _compute_risk_score(self, pivot_count: int, total_stealth: float,
                            chain_length: int, apt_matched: bool,
                            surfaces_count: int) -> float:
        """
        Compute overall risk score for a cross-surface chain.

        Risk factors:
          - Number of pivots (more pivots = more sophisticated = higher risk)
          - Total stealth (higher stealth = harder to detect = higher risk)
          - Chain length (longer chains = more complete kill chain)
          - APT pattern match (known APT = confirmed threat)
          - Number of surfaces (more surfaces = broader compromise)

        Returns a score in [0, 1].
        """
        # Pivot factor: each pivot adds risk, diminishing returns
        pivot_factor = 1.0 - math.exp(-0.5 * pivot_count)

        # Stealth factor: direct mapping
        stealth_factor = total_stealth

        # Chain length factor: longer chains are riskier (up to a point)
        length_factor = min(1.0, chain_length / 8.0)

        # APT match factor: binary boost
        apt_factor = 1.0 if apt_matched else 0.0

        # Surface breadth factor
        surface_factor = min(1.0, surfaces_count / 4.0)

        # Weighted combination
        risk = (
            0.25 * pivot_factor +
            0.20 * stealth_factor +
            0.15 * length_factor +
            0.25 * apt_factor +
            0.15 * surface_factor
        )

        return min(1.0, risk)

    def _generate_recommendations(self, pivots: List[SurfacePivotAlert],
                                  chain: CrossSurfaceChain,
                                  risk_score: float,
                                  apt_match: Optional[str]) -> List[str]:
        """
        Generate actionable response recommendations based on analysis.
        """
        recommendations = []

        if risk_score >= 0.7:
            recommendations.append(
                "CRITICAL: Initiate incident response. Multi-surface attack "
                "chain detected with high confidence."
            )
        elif risk_score >= 0.4:
            recommendations.append(
                "HIGH: Escalate to SOC Tier 2. Cross-surface activity "
                "requires investigation."
            )

        if apt_match:
            recommendations.append(
                f"APT MATCH: Chain matches known pattern '{apt_match}'. "
                f"Review associated IOCs and TTPs."
            )

        # Surface-specific recommendations
        surfaces_involved = set(chain.surfaces_crossed)
        if "Identity" in surfaces_involved:
            recommendations.append(
                "IDENTITY: Review authentication logs, check for "
                "credential abuse, MFA bypass, or Kerberos ticket anomalies."
            )
        if "Cloud" in surfaces_involved:
            recommendations.append(
                "CLOUD: Audit IAM role changes, check for unauthorized "
                "cloud resource creation, review cross-account access."
            )
        if "Container" in surfaces_involved:
            recommendations.append(
                "CONTAINER: Check for container escapes, review pod "
                "security policies, audit image provenance."
            )

        # Pivot-specific recommendations
        critical_pivots = [p for p in pivots if p.alert_level == "critical"]
        if critical_pivots:
            for pivot in critical_pivots:
                recommendations.append(
                    f"PIVOT: Investigate {pivot.source_surface} -> "
                    f"{pivot.target_surface} transition "
                    f"({pivot.source_technique} -> {pivot.target_technique}). "
                    f"Stealth: {pivot.pivot_stealth:.3f}."
                )

        if not recommendations:
            recommendations.append(
                "LOW: Activity appears routine. Continue monitoring."
            )

        return recommendations

    def hunt_cross_surface_chains(self, max_pivots: int = 3,
                                  max_length: int = 8) -> List[CrossSurfaceChain]:
        """
        Proactive threat hunting: discover possible cross-surface attack chains.

        Delegates to the Grothendieck construction's find_cross_surface_chains
        and wraps results as CrossSurfaceChain objects with APT matching.

        Useful for:
          - Purple team exercises (test detection coverage)
          - Attack surface analysis (which pivots are possible)
          - Detection engineering (build rules for discovered chains)
        """
        from cyber.stealth_scoring import StealthScorer
        scorer = StealthScorer(environment=self.environment)

        raw_chains = self.grothendieck.find_cross_surface_chains(
            max_pivots=max_pivots, max_length=max_length
        )

        results = []
        seen_signatures = set()

        for fibered_chain in raw_chains:
            techniques = [obj.technique for obj in fibered_chain]
            surfaces = [obj.surface for obj in fibered_chain]

            # Deduplicate consecutive surfaces
            unique_surfaces = []
            for s in surfaces:
                if not unique_surfaces or unique_surfaces[-1] != s:
                    unique_surfaces.append(s)

            # Skip chains that do not actually cross surfaces
            if len(unique_surfaces) < 2:
                continue

            # Deduplicate by technique signature
            sig = tuple(techniques)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            total_stealth = scorer.chain_stealth(techniques)
            pivot_count = len(unique_surfaces) - 1
            apt_match = self.identify_apt_pattern(techniques)

            chain = CrossSurfaceChain(
                surfaces_crossed=unique_surfaces,
                techniques=techniques,
                total_stealth=total_stealth,
                pivot_count=pivot_count,
                matching_apt=apt_match if apt_match else "Unknown",
            )
            results.append(chain)

        # Sort by risk: more pivots and higher stealth first
        results.sort(
            key=lambda c: (c.pivot_count, c.total_stealth),
            reverse=True,
        )

        return results

    def get_summary(self) -> Dict:
        """
        Get a summary of the detector's state and capabilities.
        """
        stats = self.grothendieck.get_surface_stats()
        return {
            "engine": "MultiSurfaceDetector (Grothendieck Construction 5)",
            "mitre_techniques_loaded": len(self.mitre_db.techniques),
            "total_fibered_objects": stats["total_objects"],
            "total_fibered_morphisms": stats["total_morphisms"],
            "within_surface_morphisms": stats["within_surface_morphisms"],
            "pivot_morphisms": stats["pivot_morphisms"],
            "attack_surfaces": ATTACK_SURFACES,
            "known_apt_patterns": list(APT_PATTERNS.keys()),
            "surface_coverage": stats["surface_object_counts"],
        }

    def __repr__(self):
        stats = self.grothendieck.get_surface_stats()
        return (
            f"MultiSurfaceDetector(surfaces={len(ATTACK_SURFACES)}, "
            f"objects={stats['total_objects']}, "
            f"morphisms={stats['total_morphisms']}, "
            f"apt_patterns={len(APT_PATTERNS)})"
        )
