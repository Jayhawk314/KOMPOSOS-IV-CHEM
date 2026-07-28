# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Cyber Security Bridge for KOMPOSOS-IV

Integrates the cyber/ threat detection modules with the gray coherence
Mythos defense layer. This bridge:

1. Maps MITRE ATT&CK techniques to Category objects/morphisms
2. Feeds attack chain detection into MythosShield
3. Uses cyber modules to enrich vulnerability reports with threat intelligence

Unlike other bridges, this is standalone (no Orion dependency) since the
Mythos defense needs to work in research/standalone contexts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

if TYPE_CHECKING:
    from core.category import Category
    from core.gray_coherence_bridge import MythosShield, GapFinding

logger = logging.getLogger(__name__)


@dataclass
class ThreatIntelligence:
    """Enriched vulnerability with threat intelligence from cyber modules."""
    gap_finding: Any  # GapFinding from gray_coherence_bridge
    mitre_techniques: List[str]  # Mapped MITRE ATT&CK IDs
    attack_chains: List[str]  # Likely attack chains exploiting this gap
    severity_boost: float  # Severity adjustment based on threat intel
    d3fend_countermeasures: List[str]  # D3FEND defensive techniques


class CyberSecurityBridge:
    """
    Bridges cyber threat detection with gray coherence vulnerability scanning.

    Workflow:
    1. MythosShield finds structural vulnerabilities (Gray 3-cell gaps)
    2. CyberSecurityBridge maps gaps to MITRE techniques
    3. Cyber modules predict likely attack chains
    4. D3FEND mapper suggests countermeasures
    5. Returns enriched threat intelligence

    Usage:
        bridge = CyberSecurityBridge(category)
        shield = build_shield(oracle, category=category)
        report = shield.scan(top_k=100)
        threat_intel = bridge.enrich_findings(report.findings)
    """

    def __init__(self, category: Category):
        self.category = category
        self._mitre_loaded = False
        self._d3fend_loaded = False

        # Lazy-load cyber modules
        self._mitre_mapper = None
        self._d3fend_mapper = None
        self._attack_chain_detector = None

    def load_mitre_attack(self) -> None:
        """Load MITRE ATT&CK framework into Category."""
        if self._mitre_loaded:
            return

        try:
            from cyber.mitre_integration import MITREIntegration

            integration = MITREIntegration(self.category)
            integration.load_attack_framework()
            self._mitre_mapper = integration
            self._mitre_loaded = True
            logger.info("MITRE ATT&CK framework loaded into Category")

        except ImportError as e:
            logger.warning(f"Could not load MITRE integration: {e}")
            self._mitre_loaded = False

    def load_d3fend(self) -> None:
        """Load D3FEND defensive countermeasures."""
        if self._d3fend_loaded:
            return

        try:
            from cyber.d3fend_mapper import D3FENDMapper

            self._d3fend_mapper = D3FENDMapper()
            self._d3fend_loaded = True
            logger.info("D3FEND countermeasures loaded")

        except ImportError as e:
            logger.warning(f"Could not load D3FEND mapper: {e}")
            self._d3fend_loaded = False

    def load_attack_chain_detector(self) -> None:
        """Load attack chain detection from cyber modules."""
        try:
            from cyber.attack_chain_strategies import AttackChainDetector

            self._attack_chain_detector = AttackChainDetector(self.category)
            logger.info("Attack chain detector loaded")

        except ImportError as e:
            logger.warning(f"Could not load attack chain detector: {e}")

    def map_gap_to_mitre(self, gap_finding: Any) -> List[str]:
        """
        Map a Gray coherence gap to MITRE ATT&CK techniques.

        Mapping logic:
        - privilege_non_commute → T1068 (Privilege Escalation)
        - functor_escape → T1611 (Escape to Host)
        - sieve_collapse → T1556 (Modify Authentication)
        - composition_boundary → T1190 (Exploit Public-Facing Application)
        - etc.
        """
        if not self._mitre_loaded:
            self.load_mitre_attack()

        # Map gap types to MITRE techniques
        gap_to_mitre = {
            "privilege_non_commute": ["T1068", "T1548"],  # Privilege Escalation
            "functor_escape": ["T1611", "T1610"],  # Container/VM Escape
            "sieve_collapse": ["T1556", "T1078"],  # Auth Bypass
            "composition_boundary": ["T1190", "T1203"],  # Memory Corruption
            "lifetime_violation": ["T1203", "T1499"],  # Memory Safety
            "interchange_failure": ["T1203"],  # Type Confusion
            "gray_tensor_failure": ["T1203", "T1559"],  # Memory Corruption
            "modification_missing": ["T1race"],  # Race Condition
        }

        gap_type = gap_finding.vulnerability.gap_type.value
        return gap_to_mitre.get(gap_type, [])

    def predict_attack_chains(
        self,
        gap_finding: Any,
        mitre_techniques: List[str]
    ) -> List[str]:
        """
        Predict likely attack chains that would exploit this gap.

        Uses attack_chain_strategies from cyber/ to find compositional
        attack paths through the MITRE technique graph.
        """
        if not self._attack_chain_detector:
            self.load_attack_chain_detector()
            if not self._attack_chain_detector:
                return []

        chains = []
        for technique in mitre_techniques:
            # Find attack chains that include this technique
            paths = self._attack_chain_detector.find_chains_through(technique)
            chains.extend([" → ".join(path) for path in paths[:3]])  # Top 3

        return chains

    def get_countermeasures(self, mitre_techniques: List[str]) -> List[str]:
        """Get D3FEND defensive countermeasures for MITRE techniques."""
        if not self._d3fend_loaded:
            self.load_d3fend()
            if not self._d3fend_mapper:
                return []

        countermeasures = set()
        for technique in mitre_techniques:
            defenses = self._d3fend_mapper.get_defenses(technique)
            countermeasures.update(defenses)

        return sorted(countermeasures)

    def calculate_severity_boost(
        self,
        gap_finding: Any,
        attack_chains: List[str]
    ) -> float:
        """
        Boost severity based on threat intelligence.

        - More attack chains = higher boost
        - Chainable gaps = higher boost
        - Critical gaps already at 1.0 = no boost
        """
        base_severity = gap_finding.combined_severity

        if base_severity >= 1.0:
            return 0.0  # Already maximum

        boost = 0.0

        # Each attack chain adds 0.05
        boost += min(len(attack_chains) * 0.05, 0.15)

        # Chainable gaps get 0.10 boost
        if gap_finding.is_chainable:
            boost += 0.10

        # Don't exceed 1.0 total
        return min(boost, 1.0 - base_severity)

    def enrich_finding(self, gap_finding: Any) -> ThreatIntelligence:
        """Enrich a single GapFinding with threat intelligence."""
        # Map to MITRE
        mitre_techniques = self.map_gap_to_mitre(gap_finding)

        # Predict attack chains
        attack_chains = self.predict_attack_chains(gap_finding, mitre_techniques)

        # Get countermeasures
        countermeasures = self.get_countermeasures(mitre_techniques)

        # Calculate severity boost
        severity_boost = self.calculate_severity_boost(gap_finding, attack_chains)

        return ThreatIntelligence(
            gap_finding=gap_finding,
            mitre_techniques=mitre_techniques,
            attack_chains=attack_chains,
            severity_boost=severity_boost,
            d3fend_countermeasures=countermeasures,
        )

    def enrich_findings(
        self,
        findings: List[Any]
    ) -> List[ThreatIntelligence]:
        """Enrich all findings from a MythosShield scan."""
        return [self.enrich_finding(f) for f in findings]

    def print_threat_report(self, threat_intel: List[ThreatIntelligence]):
        """Pretty-print enriched threat intelligence."""
        print("=" * 70)
        print("MYTHOS DEFENSE - THREAT INTELLIGENCE REPORT")
        print("=" * 70)

        critical = [t for t in threat_intel
                   if t.gap_finding.combined_severity + t.severity_boost >= 0.90]

        print(f"\nTotal Findings: {len(threat_intel)}")
        print(f"Critical (after threat intel): {len(critical)}")
        print()

        # Sort by boosted severity
        sorted_intel = sorted(
            threat_intel,
            key=lambda t: t.gap_finding.combined_severity + t.severity_boost,
            reverse=True
        )

        for i, intel in enumerate(sorted_intel[:20], 1):
            gap = intel.gap_finding
            boosted_severity = gap.combined_severity + intel.severity_boost

            tag = " [CRITICAL]" if boosted_severity >= 0.90 else ""
            if gap.is_chainable:
                tag += " [CHAINABLE]"

            print(f"{i:>2}. {gap.conjecture_source} → {gap.conjecture_target}{tag}")
            print(f"    Vulnerability: {gap.vulnerability.vuln_class}")
            print(f"    Base Severity: {gap.combined_severity:.2f}")
            print(f"    Threat Intel Boost: +{intel.severity_boost:.2f}")
            print(f"    Final Severity: {boosted_severity:.2f}")

            if intel.mitre_techniques:
                print(f"    MITRE ATT&CK: {', '.join(intel.mitre_techniques)}")

            if intel.attack_chains:
                print(f"    Attack Chains:")
                for chain in intel.attack_chains[:2]:  # Show top 2
                    print(f"      - {chain}")

            if intel.d3fend_countermeasures:
                print(f"    D3FEND Countermeasures:")
                for cm in intel.d3fend_countermeasures[:3]:  # Show top 3
                    print(f"      - {cm}")

            print(f"    Remediation: {gap.vulnerability.remediation}")
            print()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def build_cyber_bridge(category: Category) -> CyberSecurityBridge:
    """
    Build CyberSecurityBridge with all modules loaded.

    Usage:
        bridge = build_cyber_bridge(category)
        threat_intel = bridge.enrich_findings(shield_report.findings)
        bridge.print_threat_report(threat_intel)
    """
    bridge = CyberSecurityBridge(category)
    bridge.load_mitre_attack()
    bridge.load_d3fend()
    bridge.load_attack_chain_detector()
    return bridge
