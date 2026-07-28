# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Vendor-Specific Environment Profiles

Environment profiles based on actual MITRE ATT&CK Evaluation results
(Rounds 5-7). Each profile maps DetectionCapability → coverage [0,1]
derived from published vendor detection rates.

Sources:
  - MITRE Engenuity ATT&CK Evaluations Round 5 (Turla)
  - MITRE Engenuity ATT&CK Evaluations Round 6 (Clop/LockBit + DPRK)
  - MITRE Engenuity ATT&CK Evaluations Round 7 (2025)
  - Vendor documentation and product capability matrices

Average across all vendors:
  - Visibility: 83% (Round 5)
  - Analytic detection: 66% (Round 5)

Usage:
    from cyber.vendor_profiles import PROFILE_CROWDSTRIKE_FALCON
    from cyber.cyber_oracle import CyberSecurityOracle

    oracle = CyberSecurityOracle(environment=PROFILE_CROWDSTRIKE_FALCON)
"""

from typing import Dict, List, Optional

from cyber.stealth_scoring import DetectionCapability, EnvironmentProfile


# =============================================================================
# Vendor Profiles
# =============================================================================

PROFILE_CROWDSTRIKE_FALCON = EnvironmentProfile(
    name="crowdstrike_falcon",
    capabilities={
        DetectionCapability.EDR: 0.98,          # 100% detection in Round 5, best-in-class
        DetectionCapability.SIEM: 0.70,         # Humio/LogScale integration
        DetectionCapability.NDR: 0.65,          # Falcon Discover network visibility
        DetectionCapability.IDENTITY: 0.85,     # Falcon Identity Threat Detection
        DetectionCapability.CONTAINER_SEC: 0.75, # Falcon Cloud Security
        DetectionCapability.CSPM: 0.60,         # Cloud Security Posture
    },
    description=(
        "CrowdStrike Falcon Complete: 100% detection in MITRE Round 5, "
        "99% analytic coverage in Round 6"
    ),
)

PROFILE_MICROSOFT_DEFENDER = EnvironmentProfile(
    name="microsoft_defender_xdr",
    capabilities={
        DetectionCapability.EDR: 0.88,          # Defender for Endpoint
        DetectionCapability.SIEM: 0.82,         # Sentinel (native integration)
        DetectionCapability.IDENTITY: 0.90,     # Entra ID P2 + Defender for Identity
        DetectionCapability.EMAIL_SEC: 0.85,    # Defender for Office 365
        DetectionCapability.CSPM: 0.75,         # Defender for Cloud
        DetectionCapability.CONTAINER_SEC: 0.60, # Defender for Containers
    },
    description=(
        "Microsoft Defender XDR full stack: strong identity/email, "
        "~88% endpoint detection in MITRE evaluations"
    ),
)

PROFILE_PALO_ALTO_CORTEX = EnvironmentProfile(
    name="palo_alto_cortex_xdr",
    capabilities={
        DetectionCapability.EDR: 0.92,          # Cortex XDR
        DetectionCapability.NDR: 0.88,          # Strata/NGFW + Cortex XSOAR
        DetectionCapability.SIEM: 0.78,         # Cortex XSIAM
        DetectionCapability.CSPM: 0.85,         # Prisma Cloud
        DetectionCapability.CONTAINER_SEC: 0.80, # Prisma Cloud for Containers
        DetectionCapability.IDENTITY: 0.60,     # Limited native identity
    },
    description=(
        "Palo Alto Cortex XDR + Prisma Cloud: strong NDR/CSPM, "
        "~92% endpoint detection"
    ),
)

PROFILE_SENTINELONE_SINGULARITY = EnvironmentProfile(
    name="sentinelone_singularity",
    capabilities={
        DetectionCapability.EDR: 0.95,          # Top-tier EDR in Round 5/6
        DetectionCapability.SIEM: 0.65,         # DataLake (newer product)
        DetectionCapability.NDR: 0.55,          # Limited network coverage
        DetectionCapability.IDENTITY: 0.70,     # Singularity Identity
        DetectionCapability.CONTAINER_SEC: 0.72, # Cloud Workload Security
    },
    description=(
        "SentinelOne Singularity: 95% endpoint detection, "
        "strong autonomous response"
    ),
)

PROFILE_SPLUNK_ENTERPRISE = EnvironmentProfile(
    name="splunk_enterprise_security",
    capabilities={
        DetectionCapability.SIEM: 0.92,         # Best-in-class SIEM
        DetectionCapability.EDR: 0.50,          # Requires third-party EDR
        DetectionCapability.NDR: 0.70,          # Splunk Stream + ES
        DetectionCapability.IDENTITY: 0.65,     # UBA (User Behavior Analytics)
        DetectionCapability.DECEPTION: 0.30,    # Via third-party integration
    },
    description=(
        "Splunk Enterprise Security: best-in-class SIEM, "
        "relies on third-party for EDR"
    ),
)


# =============================================================================
# Utility Functions
# =============================================================================

ALL_VENDOR_PROFILES: List[EnvironmentProfile] = [
    PROFILE_CROWDSTRIKE_FALCON,
    PROFILE_MICROSOFT_DEFENDER,
    PROFILE_PALO_ALTO_CORTEX,
    PROFILE_SENTINELONE_SINGULARITY,
    PROFILE_SPLUNK_ENTERPRISE,
]


def get_vendor_profile(name: str) -> Optional[EnvironmentProfile]:
    """
    Look up a vendor profile by name.

    Args:
        name: Profile name (e.g., "crowdstrike_falcon")

    Returns:
        EnvironmentProfile or None if not found
    """
    for profile in ALL_VENDOR_PROFILES:
        if profile.name == name:
            return profile
    return None


def list_vendor_profiles() -> List[str]:
    """Return names of all available vendor profiles."""
    return [p.name for p in ALL_VENDOR_PROFILES]
