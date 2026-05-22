# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>
"""
SIGMA Detectability Index

Provides empirical detectability weights based on SIGMA rule coverage
per MITRE ATT&CK technique. Techniques with more SIGMA rules have
more ready-made detection content and are empirically easier to detect.

Data source: MITRE Cyber Analytics Repository (CAR) coverage analysis
    https://car.mitre.org/coverage/

The weight function uses half-saturation normalization so that:
- 0 rules → 0.0 weight (no community detection content)
- 50 rules → 0.5 weight (moderate coverage)
- 181 rules → 0.784 weight (extensive coverage, diminishing returns)
"""

from typing import Dict


# =============================================================================
# SIGMA Rule Counts per ATT&CK Technique
# =============================================================================
# Approximate counts from MITRE CAR coverage analysis (January 2024).
# These represent the number of SIGMA detection rules that cover each
# technique or sub-technique.

SIGMA_RULE_COUNTS: Dict[str, int] = {
    # === HIGH COVERAGE (>50 rules) ===
    "T1059":     181,  # Command & Scripting Interpreter (all sub-techniques)
    "T1059.001": 160,  # PowerShell
    "T1059.004":  42,  # Unix Shell
    "T1059.006":  28,  # Python
    "T1218":      94,  # System Binary Proxy Execution (LOLBins)
    "T1027":      83,  # Obfuscated Files or Information
    "T1055":      78,  # Process Injection
    "T1003":      72,  # OS Credential Dumping
    "T1547":      65,  # Boot/Logon Autostart Execution
    "T1053":      58,  # Scheduled Task/Job
    "T1036":      55,  # Masquerading
    "T1070":      52,  # Indicator Removal

    # === MEDIUM COVERAGE (15-50 rules) ===
    "T1486":      48,  # Data Encrypted for Impact (Ransomware)
    "T1071":      45,  # Application Layer Protocol
    "T1021":      40,  # Remote Services
    "T1078":      38,  # Valid Accounts
    "T1566":      35,  # Phishing
    "T1190":      30,  # Exploit Public-Facing Application
    "T1068":      25,  # Exploitation for Privilege Escalation
    "T1046":      22,  # Network Service Discovery
    "T1106":      22,  # Native API
    "T1562":      20,  # Impair Defenses
    "T1005":      18,  # Data from Local System
    "T1505":      16,  # Server Software Component
    "T1041":      15,  # Exfiltration Over C2 Channel
    "T1558":      14,  # Steal or Forge Kerberos Tickets

    # === LOW COVERAGE (1-14 rules) ===
    "T1082":      12,  # System Information Discovery
    "T1133":      10,  # External Remote Services
    "T1197":       8,  # BITS Jobs
    "T1556":       6,  # Modify Authentication Process
    "T1072":       5,  # Software Deployment Tools
    "T1140":       5,  # Deobfuscate/Decode Files
    "T1049":       4,  # System Network Connections Discovery
    "T1057":       4,  # Process Discovery
    "T1083":       4,  # File and Directory Discovery
    "T1087":       4,  # Account Discovery
    "T1201":       3,  # Password Policy Discovery
    "T1018":       3,  # Remote System Discovery

    # === CLOUD/CONTAINER (sparse coverage) ===
    "T1078.004":   5,  # Cloud Accounts
    "T1610":       3,  # Deploy Container
    "T1611":       4,  # Escape to Host
    "T1609":       2,  # Container Administration Command
    "T1613":       2,  # Container and Resource Discovery
    "T1612":       1,  # Build Image on Host
    "T1525":       1,  # Implant Internal Image
    "T1580":       3,  # Cloud Infrastructure Discovery
    "T1530":       3,  # Data from Cloud Storage Object
    "T1537":       2,  # Transfer Data to Cloud Account
    "T1619":       2,  # Cloud Storage Object Discovery
    "T1648":       1,  # Serverless Execution
    "T1552.005":   2,  # Cloud Instance Metadata API
    "T1550.001":   3,  # Application Access Token
    "T1098.003":   3,  # Additional Cloud Roles
    "T1136.003":   2,  # Create Cloud Account
    "T1578":       1,  # Modify Cloud Compute Infrastructure
    "T1538":       1,  # Cloud Service Dashboard
    "T1562.007":   2,  # Disable or Modify Cloud Firewall

    # === IDENTITY/AUTH ===
    "T1556.001":   4,  # Domain Controller Authentication
    "T1556.002":   3,  # Password Filter DLL
    "T1556.003":   3,  # Pluggable Authentication Modules
    "T1556.004":   2,  # Network Device Authentication
    "T1556.005":   1,  # Reversible Encryption
    "T1556.006":   1,  # Multi-Factor Authentication
    "T1556.007":   2,  # Hybrid Identity
    "T1621":       6,  # Multi-Factor Authentication Request Generation
    "T1558.003":  10,  # Kerberoasting
    "T1098":       8,  # Account Manipulation
    "T1136":       7,  # Create Account
    "T1554":       2,  # Compromise Client Software Binary

    # === PERSISTENCE ===
    "T1578.002":   1,  # Create Cloud Instance
    "T1578.003":   1,  # Delete Cloud Instance
    "T1053.007":   1,  # Container Orchestration Job
    "T1204.003":   2,  # Malicious Image

    # === ATT&CK v18 NEW TECHNIQUES ===
    "T1059.013":   5,  # Container CLI/API — few container-specific rules
    "T1677":       2,  # Poisoned Pipeline — very new, minimal coverage
    "T1676":       0,  # Linked Devices — no SIGMA rules for messaging abuse

    # === NEAR-ZERO COVERAGE (supply chain, crypto) ===
    "T1195":       0,  # Supply Chain Compromise
    "T1195.001":   0,  # Compromise Software Dependencies
    "T1195.002":   0,  # Compromise Software Supply Chain
    "T1195.003":   0,  # Compromise Hardware Supply Chain

    # Cryptographic techniques — no SIGMA rules
    "TCRYPTO_001": 0,
    "TCRYPTO_002": 0,
    "TCRYPTO_003": 0,
    "TCRYPTO_004": 0,
    "TCRYPTO_005": 0,
    "TCRYPTO_006": 0,
    "TCRYPTO_007": 0,
    "TCRYPTO_008": 0,
}


# =============================================================================
# Detectability Weight Function
# =============================================================================

def sigma_detectability_weight(technique_id: str,
                                half_saturation: float = 50.0) -> float:
    """
    Normalize SIGMA rule count into a [0, 1] detectability weight.

    Uses half-saturation (Michaelis-Menten) curve:
        weight = count / (count + K)

    where K is the half-saturation constant (default 50).

    Properties:
    - weight(0) = 0.0 (no rules → no community detection content)
    - weight(K) = 0.5 (half-saturation point)
    - weight(∞) → 1.0 (diminishing returns)
    - Monotonically increasing, concave (realistic diminishing returns)

    Args:
        technique_id: MITRE ATT&CK technique ID
        half_saturation: Rule count at which weight = 0.5 (default: 50)

    Returns:
        Detectability weight in [0.0, 1.0]
    """
    count = SIGMA_RULE_COUNTS.get(technique_id, 0)
    if count <= 0:
        return 0.0
    return count / (count + half_saturation)
