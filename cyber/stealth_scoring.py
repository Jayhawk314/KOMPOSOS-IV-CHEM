# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Stealth Scoring for MITRE ATT&CK Techniques

Assigns detectability scores to MITRE techniques and computes
stealth-optimal attack paths via enriched category composition.

Score interpretation:
  0.0 = always detected (signature-based, well-known)
  0.5 = sometimes detected (behavioral, some EDR coverage)
  1.0 = never detected (novel, no signatures, no behavioral rules)

Stealth of a chain = product of individual stealth scores.
This uses the enriched category over ([0,1], ×, 1).

Stealth data sources:
  - Picus Red Report 2026 (1.15M files, 15.5M adversarial actions)
  - MITRE ATT&CK detection coverage analysis
  - CurvGAD (ICML 2025) detection difficulty correlations

Mathematical basis:
  - DPERO log transform: max ∏ stealth_i ↔ min ∑ (-log stealth_i)
  - Source: arxiv:2510.04050
"""

import math
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

from categorical.enriched_category import (
    EnrichedCategory, MonoidalStructure, STEALTH_QUANTALE
)


# === Environment-Aware Stealth Types ===

class DetectionCapability(Enum):
    """Detection capabilities that an environment may possess."""
    EDR = auto()           # CrowdStrike, SentinelOne, Defender ATP
    SIEM = auto()          # Splunk, Elastic, QRadar
    NDR = auto()           # Zeek, Darktrace, ExtraHop
    CSPM = auto()          # Prisma Cloud, Wiz, Orca
    CONTAINER_SEC = auto() # Aqua, Sysdig, Falco
    IDENTITY = auto()      # Ping, Okta, Azure AD P2
    EMAIL_SEC = auto()     # Proofpoint, Mimecast, Defender for O365
    DECEPTION = auto()     # Attivo, Illusive, honeypots


@dataclass(frozen=True)
class EnvironmentProfile:
    """
    Describes what detection capabilities a target environment has.

    Each capability maps to a coverage level in [0, 1]:
      0.0 = not deployed / ineffective
      1.0 = fully deployed, well-tuned, comprehensive coverage
    """
    name: str
    capabilities: Dict[DetectionCapability, float] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self):
        for cap, val in self.capabilities.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(
                    f"Coverage for {cap.name} must be in [0,1], got {val}"
                )


# === Preset Environment Profiles ===

PROFILE_BARE_WINDOWS = EnvironmentProfile(
    name="bare_windows",
    capabilities={},
    description="Unmanaged workstation, no security tools",
)

PROFILE_ENTERPRISE_STANDARD = EnvironmentProfile(
    name="enterprise_standard",
    capabilities={
        DetectionCapability.EDR: 0.6,
        DetectionCapability.SIEM: 0.5,
    },
    description="Basic corporate with Defender + basic SIEM",
)

PROFILE_CROWDSTRIKE_SPLUNK = EnvironmentProfile(
    name="crowdstrike_splunk",
    capabilities={
        DetectionCapability.EDR: 0.9,
        DetectionCapability.SIEM: 0.8,
        DetectionCapability.NDR: 0.6,
        DetectionCapability.IDENTITY: 0.7,
    },
    description="Well-funded SOC with CrowdStrike, Splunk, NDR, and identity monitoring",
)

PROFILE_CLOUD_NATIVE = EnvironmentProfile(
    name="cloud_native",
    capabilities={
        DetectionCapability.CSPM: 0.8,
        DetectionCapability.CONTAINER_SEC: 0.7,
        DetectionCapability.SIEM: 0.6,
        DetectionCapability.IDENTITY: 0.8,
    },
    description="AWS/GCP with cloud-native tools (Wiz, Falco, etc.)",
)

PROFILE_AIRGAPPED_OT = EnvironmentProfile(
    name="airgapped_ot",
    capabilities={
        DetectionCapability.NDR: 0.4,
    },
    description="ICS/SCADA with minimal monitoring",
)


# === Technique → Detection Capability Mapping ===
# Maps each technique to the capabilities that can detect it.
# If a technique is not listed, no capability specifically detects it.

TECHNIQUE_DETECTION_MAP: Dict[str, List[DetectionCapability]] = {
    # Low stealth (well-detected)
    "T1059":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1059.004": [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1059.006": [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1055":     [DetectionCapability.EDR],
    "T1003":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1486":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1547":     [DetectionCapability.EDR, DetectionCapability.SIEM],

    # Medium stealth
    "T1566":     [DetectionCapability.EMAIL_SEC, DetectionCapability.EDR],
    "T1068":     [DetectionCapability.EDR],
    "T1021":     [DetectionCapability.NDR, DetectionCapability.SIEM, DetectionCapability.IDENTITY],
    "T1071":     [DetectionCapability.NDR, DetectionCapability.SIEM],
    "T1005":     [DetectionCapability.EDR],
    "T1041":     [DetectionCapability.NDR, DetectionCapability.SIEM],
    "T1190":     [DetectionCapability.NDR, DetectionCapability.SIEM],
    "T1046":     [DetectionCapability.NDR, DetectionCapability.SIEM],
    "T1053":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1082":     [DetectionCapability.EDR],
    "T1133":     [DetectionCapability.NDR, DetectionCapability.IDENTITY],
    "T1072":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1049":     [DetectionCapability.EDR],
    "T1057":     [DetectionCapability.EDR],
    "T1083":     [DetectionCapability.EDR],
    "T1087":     [DetectionCapability.EDR, DetectionCapability.IDENTITY],
    "T1201":     [DetectionCapability.EDR],
    "T1018":     [DetectionCapability.NDR],

    # High stealth
    "T1218":     [DetectionCapability.EDR],
    "T1036":     [DetectionCapability.EDR],
    "T1027":     [DetectionCapability.EDR],
    "T1140":     [DetectionCapability.EDR],
    "T1070":     [DetectionCapability.SIEM, DetectionCapability.EDR],
    "T1078":     [DetectionCapability.IDENTITY, DetectionCapability.SIEM],
    "T1197":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1562":     [DetectionCapability.EDR, DetectionCapability.SIEM],
    "T1556":     [DetectionCapability.IDENTITY, DetectionCapability.EDR],
    "T1558":     [DetectionCapability.IDENTITY, DetectionCapability.SIEM],
    "T1195":     [],  # Supply chain — nothing detects it well
    "T1106":     [DetectionCapability.EDR],
    "T1505":     [DetectionCapability.EDR, DetectionCapability.SIEM],

    # Cloud techniques
    "T1078.004": [DetectionCapability.CSPM, DetectionCapability.IDENTITY],
    "T1580":     [DetectionCapability.CSPM],
    "T1530":     [DetectionCapability.CSPM, DetectionCapability.SIEM],
    "T1537":     [DetectionCapability.CSPM, DetectionCapability.SIEM],
    "T1619":     [DetectionCapability.CSPM],
    "T1648":     [DetectionCapability.CSPM, DetectionCapability.SIEM],
    "T1552.005": [DetectionCapability.CSPM],
    "T1550.001": [DetectionCapability.IDENTITY],
    "T1098.003": [DetectionCapability.CSPM, DetectionCapability.IDENTITY],
    "T1136.003": [DetectionCapability.CSPM, DetectionCapability.IDENTITY],
    "T1578":     [DetectionCapability.CSPM],
    "T1578.002": [DetectionCapability.CSPM],
    "T1578.003": [DetectionCapability.CSPM],
    "T1562.007": [DetectionCapability.CSPM, DetectionCapability.SIEM],
    "T1538":     [DetectionCapability.CSPM],

    # Container techniques
    "T1610":     [DetectionCapability.CONTAINER_SEC],
    "T1611":     [DetectionCapability.CONTAINER_SEC, DetectionCapability.EDR],
    "T1609":     [DetectionCapability.CONTAINER_SEC],
    "T1613":     [DetectionCapability.CONTAINER_SEC],
    "T1612":     [DetectionCapability.CONTAINER_SEC],
    "T1525":     [DetectionCapability.CONTAINER_SEC],
    "T1552.007": [DetectionCapability.CONTAINER_SEC],
    "T1053.007": [DetectionCapability.CONTAINER_SEC],
    "T1204.003": [DetectionCapability.CONTAINER_SEC],

    # Identity/Auth techniques
    "T1556.001": [DetectionCapability.IDENTITY, DetectionCapability.EDR],
    "T1556.002": [DetectionCapability.IDENTITY, DetectionCapability.EDR],
    "T1556.003": [DetectionCapability.IDENTITY, DetectionCapability.EDR],
    "T1556.004": [DetectionCapability.IDENTITY, DetectionCapability.NDR],
    "T1556.005": [DetectionCapability.IDENTITY],
    "T1556.006": [DetectionCapability.IDENTITY],
    "T1556.007": [DetectionCapability.IDENTITY, DetectionCapability.SIEM],
    "T1621":     [DetectionCapability.IDENTITY],
    "T1558.003": [DetectionCapability.IDENTITY, DetectionCapability.SIEM],

    # Persistence
    "T1098":     [DetectionCapability.IDENTITY, DetectionCapability.SIEM],
    "T1136":     [DetectionCapability.IDENTITY, DetectionCapability.SIEM],
    "T1554":     [DetectionCapability.EDR],

    # ATT&CK v18 new techniques
    "T1059.013": [DetectionCapability.CONTAINER_SEC, DetectionCapability.EDR],
    "T1677":     [DetectionCapability.SIEM],  # CI/CD logs go to SIEM if collected
    "T1676":     [],  # No standard detection for messaging sync

    # Supply chain
    "T1195.001": [],  # Nothing detects well
    "T1195.002": [],
    "T1195.003": [],

    # Deception catches lateral movement and discovery
    "T1046":     [DetectionCapability.NDR, DetectionCapability.SIEM, DetectionCapability.DECEPTION],

    # Crypto techniques — mostly passive, hard to detect
    "TCRYPTO_001": [],
    "TCRYPTO_002": [],
    "TCRYPTO_003": [DetectionCapability.NDR],
    "TCRYPTO_004": [],
    "TCRYPTO_005": [DetectionCapability.SIEM],
    "TCRYPTO_006": [],  # Passive capture — undetectable
    "TCRYPTO_007": [DetectionCapability.SIEM],
    "TCRYPTO_008": [DetectionCapability.NDR],
}


@dataclass
class StealthProfile:
    """Complete stealth profile for a technique."""
    technique_id: str
    stealth_score: float         # Overall stealth [0,1]
    detection_sources: List[str] # What can detect this
    evasion_methods: List[str]   # How to evade detection
    prevalence: float            # How common in the wild [0,1]
    edr_bypass_rate: float       # Rate of EDR bypass [0,1]


class StealthScorer:
    """
    Assigns detectability scores to MITRE techniques.

    When an EnvironmentProfile is provided, baseline stealth is adjusted
    downward based on which detection capabilities the environment has
    that can detect each technique. With environment=None, scores are
    identical to the static baseline (backward compatible).

    Scores calibrated from:
    - Picus Red Report 2026: 1,153,683 files analyzed, 15.5M adversarial actions
    - 80% of top techniques are Defense Evasion / Persistence / C2
    - "Silent Residency" trend: attackers choose stealth over destruction
    """

    # Stealth scores based on Picus Red Report 2026 + detection analysis
    TECHNIQUE_STEALTH: Dict[str, float] = {
        # === LOW STEALTH (well-detected, high signature coverage) ===
        "T1059":     0.25,  # Command & Scripting — most signatured technique
        "T1059.004": 0.30,  # Unix Shell — slightly harder to detect
        "T1059.006": 0.35,  # Python — harder than PowerShell
        "T1055":     0.30,  # Process Injection — 30% prevalence, EDR watches
        "T1003":     0.20,  # Credential Dumping — LSASS access = instant alert
        "T1486":     0.15,  # Data Encrypted for Impact — ransomware = obvious
        "T1547":     0.45,  # Boot/Logon Autostart — registry monitoring catches

        # === MEDIUM STEALTH (sometimes detected) ===
        "T1566":     0.50,  # Phishing — depends on sophistication
        "T1068":     0.45,  # Exploitation for Priv Esc — depends on exploit
        "T1021":     0.55,  # Remote Services — normal traffic cover
        "T1071":     0.60,  # Application Layer Protocol — blends with C2
        "T1005":     0.65,  # Data from Local System — normal file access
        "T1041":     0.50,  # Exfil Over C2 — depends on volume/timing
        "T1190":     0.60,  # Exploit Public-Facing — depends on vuln
        "T1046":     0.55,  # Network Service Discovery — normal admin activity
        "T1053":     0.70,  # Scheduled Task — persistence via legit mechanism
        "T1082":     0.70,  # System Info Discovery — benign-looking
        "T1133":     0.55,  # External Remote Services — VPN/RDP
        "T1072":     0.50,  # Software Deployment Tools — SCCM, Puppet
        "T1049":     0.65,  # System Network Connections — netstat
        "T1057":     0.65,  # Process Discovery — tasklist
        "T1083":     0.65,  # File and Directory Discovery
        "T1087":     0.60,  # Account Discovery — net user
        "T1201":     0.65,  # Password Policy Discovery
        "T1018":     0.55,  # Remote System Discovery — ARP scan

        # === HIGH STEALTH (hard to detect) ===
        "T1218":     0.85,  # LOLBins — living off the land, legit binaries
        "T1036":     0.80,  # Masquerading — looks legitimate
        "T1027":     0.65,  # Obfuscated Files — defeats static analysis
        "T1140":     0.70,  # Deobfuscate/Decode — certutil decode
        "T1070":     0.90,  # Indicator Removal — anti-forensics
        "T1078":     0.88,  # Valid Accounts — legitimate credentials
        "T1197":     0.82,  # BITS Jobs — stealthy transfer
        "T1562":     0.40,  # Impair Defenses — risky but powerful
        "T1556":     0.85,  # Modify Auth Process — golden ticket
        "T1558":     0.80,  # Kerberos Tickets — silver/golden ticket
        "T1195":     0.95,  # Supply Chain — SolarWinds-class stealth
        "T1106":     0.78,  # Native API — direct syscalls bypass EDR
        "T1505":     0.75,  # Server Software Component — web shells

        # === CLOUD TECHNIQUES (generally higher stealth) ===
        "T1078.004": 0.85,  # Cloud Accounts — legitimate access
        "T1580":     0.75,  # Cloud Infrastructure Discovery
        "T1530":     0.72,  # Data from Cloud Storage
        "T1537":     0.78,  # Transfer Data to Cloud Account
        "T1619":     0.70,  # Cloud Storage Object Discovery
        "T1648":     0.80,  # Serverless Execution — Lambda
        "T1552.005": 0.82,  # Cloud Instance Metadata API — IMDS
        "T1550.001": 0.80,  # Application Access Token
        "T1098.003": 0.70,  # Additional Cloud Roles
        "T1136.003": 0.65,  # Create Cloud Account
        "T1578":     0.72,  # Modify Cloud Compute Infrastructure
        "T1578.002": 0.70,  # Create Cloud Instance
        "T1578.003": 0.75,  # Delete Cloud Instance — evidence destruction
        "T1562.007": 0.60,  # Disable Cloud Firewall
        "T1538":     0.68,  # Cloud Service Dashboard

        # === CONTAINER TECHNIQUES ===
        "T1610":     0.75,  # Deploy Container — unusual image
        "T1611":     0.70,  # Escape to Host — container escape
        "T1609":     0.65,  # Container Admin Command — kubectl
        "T1613":     0.68,  # Container Discovery
        "T1612":     0.72,  # Build Image on Host
        "T1525":     0.80,  # Implant Internal Image — backdoor
        "T1552.007": 0.75,  # Container API credentials
        "T1053.007": 0.72,  # Container Orchestration Job
        "T1204.003": 0.60,  # User Execution: Malicious Image

        # === IDENTITY/AUTH TECHNIQUES ===
        "T1556.001": 0.88,  # DC Authentication mod — skeleton key
        "T1556.002": 0.82,  # Password Filter DLL
        "T1556.003": 0.85,  # PAM modification
        "T1556.004": 0.80,  # Network Device Auth
        "T1556.005": 0.78,  # Reversible Encryption
        "T1556.006": 0.75,  # MFA bypass/disable
        "T1556.007": 0.82,  # Hybrid Identity — AAD Connect
        "T1621":     0.45,  # MFA Fatigue — noisy, user notices
        "T1558.003": 0.72,  # Kerberoasting

        # === PERSISTENCE ===
        "T1098":     0.65,  # Account Manipulation
        "T1136":     0.55,  # Create Account — audit log
        "T1554":     0.78,  # Compromise Client Software Binary

        # === ATT&CK v18 NEW TECHNIQUES ===
        "T1059.013": 0.62,  # Container CLI — kubectl exec is logged but common
        "T1677":     0.88,  # Poisoned Pipeline — CI/CD pipelines rarely monitored deeply
        "T1676":     0.82,  # Linked Devices — messaging sync is normal activity

        # === SUPPLY CHAIN ===
        "T1195.001": 0.93,  # Compromise Dependencies
        "T1195.002": 0.95,  # Compromise Software Supply Chain
        "T1195.003": 0.97,  # Compromise Hardware Supply Chain

        # === CRYPTOGRAPHIC TECHNIQUES ===
        "TCRYPTO_001": 0.85,  # Weak RSA Key — exploiting public certs, no network activity
        "TCRYPTO_002": 0.90,  # RSA Common Factor — pure math on public moduli, passive
        "TCRYPTO_003": 0.80,  # ECDSA Nonce Reuse — requires signature collection
        "TCRYPTO_004": 0.75,  # Weak Elliptic Curve — public params, may trigger alerts
        "TCRYPTO_005": 0.70,  # Certificate Forgery — cert issuance creates audit trail
        "TCRYPTO_006": 0.95,  # Quantum Harvest — passive capture, no target interaction
        "TCRYPTO_007": 0.65,  # CA/PKI Compromise — leaves evidence in CT logs
        "TCRYPTO_008": 0.60,  # Crypto Downgrade — visible in TLS handshake logs
    }

    def __init__(self, environment: Optional[EnvironmentProfile] = None,
                 detection_map: Optional[Dict[str, List[DetectionCapability]]] = None):
        self.environment = environment
        self._detection_map = detection_map if detection_map is not None else self._load_detection_map()

    @staticmethod
    def _load_detection_map() -> Dict[str, List[DetectionCapability]]:
        """
        Load detection map from D3FEND cache, falling back to hand-coded.

        Strategy: Start with hand-coded map, overlay D3FEND-derived data.
        If D3FEND cache doesn't exist or fails, hand-coded map is used as-is.
        """
        try:
            from cyber.d3fend_mapper import D3FENDMapper
            mapper = D3FENDMapper()
            d3fend_map = mapper.build_detection_map()
            if d3fend_map:
                merged = dict(TECHNIQUE_DETECTION_MAP)
                merged.update(d3fend_map)
                return merged
        except Exception:
            pass
        return TECHNIQUE_DETECTION_MAP

    def get_stealth(self, technique_id: str) -> float:
        """Get stealth score for technique, adjusted for environment."""
        baseline = self.TECHNIQUE_STEALTH.get(technique_id, 0.5)
        return self._adjust_for_environment(baseline, technique_id)

    def _adjust_for_environment(self, baseline: float, technique_id: str) -> float:
        """
        Adjust baseline stealth downward based on environment detection capabilities.

        Each detector that can detect this technique reduces stealth by up to 30%
        (multiplicative). Multiple independent detectors compound realistically.

        SIGMA boost: techniques with more community detection rules (SIGMA) are
        empirically easier to detect. The sigma_boost amplifies the detection
        coefficient from 0.3 up to 0.45 for heavily-covered techniques.

        Formula:
            sigma_boost = 1.0 + sigma_weight * 0.5   (in [1.0, 1.5])
            adjusted = baseline * product((1 - coverage * 0.3 * sigma_boost))
            Floor at 0.01 — nothing is 100% detected.
        """
        if self.environment is None:
            return baseline

        from cyber.sigma_index import sigma_detectability_weight

        detectors = self._detection_map.get(technique_id, [])
        adjusted = baseline

        # SIGMA detectability amplifies environment detection
        sigma_weight = sigma_detectability_weight(technique_id)
        sigma_boost = 1.0 + sigma_weight * 0.5  # [1.0, 1.5]

        for cap in detectors:
            coverage = self.environment.capabilities.get(cap, 0.0)
            reduction_factor = coverage * 0.3 * sigma_boost
            adjusted *= (1.0 - min(reduction_factor, 0.95))

        return max(0.01, adjusted)

    def set_environment(self, environment: Optional[EnvironmentProfile]):
        """Change the environment profile. Subsequent calls to get_stealth use the new profile."""
        self.environment = environment

    def get_profile(self, technique_id: str) -> StealthProfile:
        """Get complete stealth profile for technique."""
        score = self.get_stealth(technique_id)

        # Derive detection sources and evasion methods from score
        if score < 0.3:
            detection = ["Signature-based", "Behavioral", "EDR", "SIEM"]
            evasion = ["Obfuscation", "Custom tooling"]
        elif score < 0.6:
            detection = ["Behavioral", "Heuristic", "EDR (partial)"]
            evasion = ["LOLBins", "Timing", "Volume control"]
        elif score < 0.8:
            detection = ["Advanced behavioral", "Threat hunting"]
            evasion = ["Living off the land", "Legitimate credentials"]
        else:
            detection = ["Threat hunting only", "Anomaly-based"]
            evasion = ["Normal operations", "Legitimate tools", "Supply chain"]

        return StealthProfile(
            technique_id=technique_id,
            stealth_score=score,
            detection_sources=detection,
            evasion_methods=evasion,
            prevalence=0.0,  # Would come from threat intel
            edr_bypass_rate=score  # Approximation
        )

    def chain_stealth(self, chain: List[str]) -> float:
        """
        Compute total stealth of attack chain (product of scores).

        Uses enriched category composition: stealth(A→C) = stealth(A→B) × stealth(B→C)
        """
        stealth = 1.0
        for tech_id in chain:
            stealth *= self.get_stealth(tech_id)
        return stealth

    def composition_stealth(self, tech1_id: str, tech2_id: str) -> float:
        """
        Compute stealth of a single composition step.

        The stealth of transitioning from tech1 to tech2 is the
        geometric mean of their individual stealth scores, modified
        by a transition penalty for cross-tactic jumps.
        """
        s1 = self.get_stealth(tech1_id)
        s2 = self.get_stealth(tech2_id)

        # Base composition stealth is geometric mean
        base = math.sqrt(s1 * s2)

        return min(1.0, base)

    def rank_by_stealth(self) -> List[Tuple[str, float]]:
        """Rank all known techniques by stealth (highest first)."""
        ranked = sorted(
            self.TECHNIQUE_STEALTH.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return ranked


class StealthOptimalPathFinder:
    """
    Find the stealthiest valid attack path between tactics.

    Uses enriched category composition + DPERO-style log transform:
      max ∏ stealth_i ↔ min ∑ (-log stealth_i)

    This transforms multiplicative stealth optimization into
    additive shortest-path, solvable by Dijkstra.

    Mathematical basis:
      - DPERO (2025): arxiv:2510.04050
      - Enriched category theory: composition in ([0,1], ×, 1)
    """

    def __init__(self, enriched_cat: EnrichedCategory):
        self.cat = enriched_cat
        self.scorer = StealthScorer()

    def find_stealthiest_path(self, start: str, end: str,
                              max_length: int = 7) -> Optional[Tuple[List[str], float, float]]:
        """
        Find the attack chain from start to end that maximizes stealth.

        Returns: (path, stealth_score, log_cost) or None
        """
        result = self.cat.optimal_path(start, end, maximize=True, max_length=max_length)
        if result is None:
            return None

        path, stealth = result
        log_cost = -math.log(stealth) if stealth > 0 else float('inf')
        return (path, stealth, log_cost)

    def find_top_k_paths(self, start: str, end: str,
                         k: int = 5) -> List[Tuple[List[str], float]]:
        """Return top-k stealthiest paths."""
        return self.cat.top_k_paths(start, end, k=k, maximize=True)

    def compare_paths(self, path1: List[str], path2: List[str]) -> Dict:
        """
        Compare two attack paths by stealth.

        Returns dict with stealth scores, per-step breakdown, and winner.
        """
        s1 = self.cat.path_weight(path1)
        s2 = self.cat.path_weight(path2)

        breakdown1 = []
        for i in range(len(path1) - 1):
            w = self.cat.get_hom(path1[i], path1[i + 1])
            breakdown1.append((path1[i], path1[i + 1], w))

        breakdown2 = []
        for i in range(len(path2) - 1):
            w = self.cat.get_hom(path2[i], path2[i + 1])
            breakdown2.append((path2[i], path2[i + 1], w))

        return {
            "path1": {"chain": path1, "stealth": s1, "steps": breakdown1},
            "path2": {"chain": path2, "stealth": s2, "steps": breakdown2},
            "winner": "path1" if (s1 or 0) >= (s2 or 0) else "path2",
            "ratio": (s1 or 0) / (s2 or 1e-10)
        }

    def defense_priority(self) -> List[Tuple[str, float, int]]:
        """
        For each technique, compute how much blocking it reduces max stealth.

        Delegates to enriched category's defense_priority method.

        Returns: List of (technique_id, impact_score, path_count)
        """
        return self.cat.defense_priority()

    def suggest_mitigations(self, top_n: int = 10) -> List[Dict]:
        """
        Suggest which techniques to prioritize for defense.

        Combines defense_priority with stealth scores to recommend
        which techniques, if mitigated, most degrade attacker stealth.
        """
        priorities = self.defense_priority()

        suggestions = []
        for tech_id, impact, count in priorities[:top_n]:
            profile = self.scorer.get_profile(tech_id)
            suggestions.append({
                "technique_id": tech_id,
                "impact_score": impact,
                "appears_in_paths": count,
                "stealth_score": profile.stealth_score,
                "detection_sources": profile.detection_sources,
                "recommendation": (
                    f"Mitigating {tech_id} degrades attacker stealth by {impact:.3f} "
                    f"across {count} optimal paths. "
                    f"Current detection: {', '.join(profile.detection_sources)}"
                )
            })

        return suggestions
