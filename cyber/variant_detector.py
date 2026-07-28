# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Zero-Day Variant Detection Engine

Uses natural transformations between attack functors to detect
zero-day variants of known APT campaigns.

Construction 3 wrapper: given an observed sequence of MITRE ATT&CK
technique IDs, the engine lifts the sequence to an attack functor and
checks for the existence of a natural transformation to every known
campaign functor. A match (similarity > threshold) triggers a
VariantAlert indicating the observed activity is structurally
equivalent to a catalogued threat -- even if every individual
technique is different from the original campaign.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from categorical.natural_transformations import (
    NaturalTransformationDetector,
    AttackFunctor,
)
from cyber.mitre_integration import MITREDatabase


# -----------------------------------------------------------------------
# Known campaign database
#
# Each entry maps a human-readable campaign label to the ordered list of
# MITRE ATT&CK technique IDs observed in that campaign's canonical kill
# chain.  These are the "reference functors" against which new
# observations are compared.
# -----------------------------------------------------------------------

KNOWN_CAMPAIGNS: Dict[str, List[str]] = {
    # Russian state-sponsored -- phishing to exfiltration
    "APT28_standard": [
        "T1566", "T1059", "T1068", "T1003", "T1021", "T1005", "T1041",
    ],
    # SolarWinds supply-chain compromise
    "APT29_sunburst": [
        "T1195", "T1059", "T1078", "T1003", "T1071", "T1005", "T1041",
    ],
    # North Korean cryptocurrency theft
    "Lazarus_crypto": [
        "T1566", "T1059", "T1055", "T1005", "T1071", "T1041",
    ],
    # Financial crime -- point-of-sale
    "FIN7_pos": [
        "T1566", "T1059", "T1055", "T1003", "T1021", "T1005", "T1041",
    ],
    # Ransomware via phishing
    "Conti_ransom": [
        "T1566", "T1059", "T1068", "T1003", "T1021", "T1486",
    ],
    # Ransomware via exploit
    "DarkSide_ransom": [
        "T1190", "T1059", "T1068", "T1003", "T1021", "T1486",
    ],
    # Exchange server exploitation
    "Hafnium_exchange": [
        "T1190", "T1059", "T1505", "T1003", "T1005", "T1041",
    ],
    # Chinese living-off-the-land espionage
    "Volt_Typhoon": [
        "T1190", "T1059", "T1078", "T1082", "T1021", "T1005",
    ],
}


@dataclass
class VariantAlert:
    """Alert for a detected attack variant."""
    observed_chain: List[str]
    matched_campaign: str
    similarity_score: float
    is_strict_natural: bool
    components: Dict
    commuting_squares: List[bool]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    severity: str = ""

    def __post_init__(self):
        if not self.severity:
            self.severity = self._compute_severity()

    def _compute_severity(self) -> str:
        """Derive severity from the similarity score."""
        if self.is_strict_natural:
            return "CRITICAL"
        if self.similarity_score >= 0.9:
            return "HIGH"
        if self.similarity_score >= 0.75:
            return "MEDIUM"
        return "LOW"

    def summary(self) -> str:
        """Return a one-line human-readable summary."""
        return (
            f"[{self.severity}] Variant of {self.matched_campaign} detected "
            f"(score={self.similarity_score:.2f}, "
            f"strict_natural={self.is_strict_natural})"
        )


class VariantDetectionEngine:
    """
    Production engine for zero-day variant detection.

    Wraps NaturalTransformationDetector with:
      - Pre-loaded APT campaign database
      - Alert generation with severity classification
      - Runtime campaign registration
    """

    def __init__(self):
        """Initialise the engine with the MITRE database and known campaigns."""
        self.mitre_db = MITREDatabase()
        self.detector = NaturalTransformationDetector(self.mitre_db)

        # Register the full production campaign set (the detector already
        # registers a core subset; add the extra campaigns here).
        for name, chain in KNOWN_CAMPAIGNS.items():
            if name not in self.detector.known_patterns:
                self.detector.register_campaign(name, chain)

    def analyze_chain(self, observed_chain: List[str]) -> List[VariantAlert]:
        """
        Analyze an observed technique chain for variant matches.

        Args:
            observed_chain: Ordered list of MITRE technique IDs observed
                            in real-time telemetry.

        Returns:
            List of VariantAlert objects for every campaign whose
            similarity exceeds the 0.6 threshold, sorted by score
            descending.
        """
        raw_matches = self.detector.detect_variant(observed_chain)

        alerts: List[VariantAlert] = []
        for match in raw_matches:
            alert = VariantAlert(
                observed_chain=list(observed_chain),
                matched_campaign=match["campaign"],
                similarity_score=match["similarity_score"],
                is_strict_natural=match["is_natural"],
                components=match["components"],
                commuting_squares=match["commuting_squares"],
            )
            alerts.append(alert)

        return alerts

    def get_campaign_database(self) -> Dict[str, List[str]]:
        """
        Return the known campaign database.

        Returns:
            Dict mapping campaign name to its canonical technique chain.
        """
        return {
            name: list(functor.instance)
            for name, functor in self.detector.known_patterns.items()
        }

    def add_campaign(self, name: str, chain: List[str]):
        """
        Add a new campaign to the detection database at runtime.

        Args:
            name:  Campaign identifier (must be unique).
            chain: Ordered list of MITRE technique IDs.

        Raises:
            ValueError: If a campaign with the given name already exists.
        """
        if name in self.detector.known_patterns:
            raise ValueError(
                f"Campaign '{name}' already registered. "
                f"Use a unique name or remove the existing campaign first."
            )
        self.detector.register_campaign(name, chain)
