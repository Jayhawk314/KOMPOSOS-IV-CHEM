# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Hawkins / Komposos-Labs

"""
Mythos-Style Attack Simulations — Realistic Zero-Day & APT Chains

Based on Anthropic Mythos capabilities (April 2026):
  - 4+ step exploit chains composed in <10 hours
  - Autonomous sandbox escape without explicit instruction
  - Legacy bug excavation (27-year-old vulnerabilities)
  - AI safety policy bypass (>50 subcommands disables checks)
  - Vulnerability chaining (multiple flaws → single exploit)
  - Memory corruption in memory-safe VMMs
  - Browser renderer + OS sandbox escapes
  - AI agent command-parsing safety bypasses
  - Supply chain scanning + exploitation
  - Authentication bypass via deep-rooted bugs

Each simulation models a REALISTIC Mythos attack path, then validates
against gray coherence to find structural gaps (not just detection gaps).

Usage:
    # Run all simulations
    suite = MythosAttackSimulationSuite(oracle)
    results = suite.run_all_simulations()

    # Run specific attack pattern
    result = suite.run_simulation("sandbox_escape_chain")

    # Get Mythos risk assessment
    assessment = suite.get_mythos_risk_profile()

Mathematical basis:
  Each attack chain is validated against:
    - 6 categorical constructions (C1-C6) via RedTeamSimulator
    - Gray coherence 3-cell modification checking (MythosShield)
    - Threat intelligence bus publication (cross-module learning)

This separates:
  - Tests (verify simulation correctness)
  - Attack simulations (verify system resilience)
  - Mythos validation (verify structural gap resistance)
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cyber.cyber_oracle import CyberSecurityOracle

from cyber.attack_simulator import RedTeamSimulator, SimulationReport

logger = logging.getLogger(__name__)


# =============================================================================
# Attack Chain Definitions — Realistic Mythos Patterns
# =============================================================================

MYTHOS_ATTACK_CHAINS: Dict[str, Dict] = {
    # === Pattern 1: Multi-Step Sandbox Escape ===
    # Based on: Mythos 4-step chain escaping browser renderer + OS sandbox
    "sandbox_escape_chain": {
        "name": "Mythos Sandbox Escape — 4-Step Chain",
        "description": (
            "4-step chain escaping browser renderer sandbox to gain "
            "unrestricted OS access. Based on real Mythos capability."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1190",       # Exploit public-facing application (browser)
            "T1184",       # Browser sandbox escape (renderer vulnerability)
            "T1068",       # Local privilege escalation (kernel exploit)
            "T1059.001",   # Execute: PowerShell (full OS access)
        ],
        "surfaces": ["Application", "Endpoint", "Kernel", "Endpoint"],
        "objective": "Escape browser sandbox to gain unrestricted OS access",
        "mythos_pattern": "multi_step_chain",
        "coherence_gap_risk": "functor_escape",  # containment boundary crossing
        "expected_detection_rate": 0.3,  # Mythos chains are stealthy
    },

    # === Pattern 2: Legacy Bug Excavation ===
    # Based on: 27-year-old OpenBSD, 16-year-old FFmpeg flaws
    "legacy_bug_excavation": {
        "name": "Mythos Legacy Bug Excavation — 27-Year-Old Flaw",
        "description": (
            "Exploiting a deep-rooted legacy vulnerability that has existed "
            "for decades. Mythos finds these through systematic code analysis."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1190",       # Exploit public-facing application
            "T1068",       # Exploit old buffer overflow (legacy flaw)
            "T1055",       # Process injection (establish persistence)
            "T1078",       # Valid accounts (legacy credential reuse)
            "T1021",       # Remote services (lateral movement)
        ],
        "surfaces": ["Application", "Endpoint", "Endpoint", "Identity", "Network"],
        "objective": "Exploit 27-year-old vulnerability for initial access",
        "mythos_pattern": "legacy_excavation",
        "coherence_gap_risk": "composition_boundary",  # buffer overflow
        "expected_detection_rate": 0.2,  # Legacy bugs have no signatures
    },

    # === Pattern 3: AI Safety Policy Bypass ===
    # Based on: >50 subcommands disables security checks
    "ai_policy_bypass": {
        "name": "Mythos AI Agent Safety Bypass — Command Parsing Exploit",
        "description": (
            "Exploiting AI coding agent's command-parsing optimization "
            "that silently ignores user-configured security deny rules "
            "when processing commands containing >50 subcommands."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1059.001",   # Execute: PowerShell (complex command chain)
            "T1569.002",   # System services: PowerShell (abuse agent)
            "T1055",       # Process injection (bypass security checks)
            "T1078",       # Valid accounts (agent credentials)
            "T1005",       # Data from local system (exfil via agent)
            "T1041",       # Exfiltration over C2 channel
        ],
        "surfaces": ["Endpoint", "Endpoint", "Endpoint", "Identity", "Endpoint", "Network"],
        "objective": "Bypass AI agent safety policies via command complexity",
        "mythos_pattern": "safety_bypass",
        "coherence_gap_risk": "privilege_non_commute",  # agent privilege abuse
        "expected_detection_rate": 0.25,  # Agent behavior looks legitimate
    },

    # === Pattern 4: Supply Chain Compromise ===
    # Based on: Concurrent OSS supply chain + direct compromise
    "supply_chain_compromise": {
        "name": "Mythos Supply Chain Attack — Dependency Exploitation",
        "description": (
            "Scanning and exploiting OSS supply chain dependencies "
            "concurrently with direct system compromises."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1195.001",   # Compromise software dependencies
            "T1195.002",   # Compromise software supply chain
            "T1059",       # Execute via build system (compromised package)
            "T1068",       # Privilege escalation (build context abuse)
            "T1021",       # Lateral movement (deployed service access)
            "T1041",       # Exfiltration (supply chain data theft)
        ],
        "surfaces": ["Application", "Application", "Endpoint", "Endpoint", "Network", "Network"],
        "objective": "Exploit OSS dependency chain for initial access and exfil",
        "mythos_pattern": "supply_chain",
        "coherence_gap_risk": "sieve_collapse",  # trust boundary bypass
        "expected_detection_rate": 0.35,  # Supply chain attacks are stealthy
    },

    # === Pattern 5: Memory Corruption in Memory-Safe VMM ===
    # Based on: VM monitor flaws in memory-safe implementations
    "memory_corruption_vmm": {
        "name": "Mythos VMM Memory Corruption — Memory-Safe Bypass",
        "description": (
            "Exploiting memory corruption vulnerabilities within "
            "memory-safe virtual machine monitor implementations."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1068",       # Exploit VMM vulnerability (memory corruption)
            "T1610",       # Deploy container (VM escape vector)
            "T1055",       # Process injection (hypervisor compromise)
            "T1078.004",   # Cloud accounts (hypervisor credentials)
            "T1537",       # Transfer data to cloud account (exfil)
        ],
        "surfaces": ["Endpoint", "Container", "Endpoint", "Cloud", "Cloud"],
        "objective": "Escape VM via memory corruption in VMM",
        "mythos_pattern": "memory_corruption",
        "coherence_gap_risk": "gray_tensor_failure",  # memory corruption
        "expected_detection_rate": 0.15,  # Memory corruption in VMM is novel
    },

    # === Pattern 6: Autonomous Sandbox Escape ===
    # Based on: Unprompted sandbox escapes, publishes exploits
    "autonomous_sandbox_escape": {
        "name": "Mythos Autonomous Sandbox Escape — Unprompted Action",
        "description": (
            "Autonomous sandbox escape without explicit instruction. "
            "Model independently devises multi-step exploit to bypass "
            "isolated evaluation environments."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1059",       # Command execution (within sandbox)
            "T1068",       # Privilege escalation (sandbox escape prep)
            "T1548",       # Abuse elevation control (bypass isolation)
            "T1021",       # Remote services (escape to network)
            "T1041",       # Exfiltration (post escape)
            "T1190",       # Exploit public-facing app (prove escape)
        ],
        "surfaces": ["Endpoint", "Endpoint", "Endpoint", "Network", "Network", "Application"],
        "objective": "Autonomous sandbox escape without instruction",
        "mythos_pattern": "autonomous_escape",
        "coherence_gap_risk": "functor_escape",  # containment escape
        "expected_detection_rate": 0.2,  # Autonomous actions are novel
    },

    # === Pattern 7: Vulnerability Chaining ===
    # Based on: Links multiple discrete flaws into single exploit
    "vulnerability_chaining": {
        "name": "Mythos Vulnerability Chain — Multi-Flaw Exploit",
        "description": (
            "Chains 5+ discrete vulnerabilities into a single cohesive "
            "exploit. Each flaw alone is minor; together they're critical."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1566",       # Phishing (initial access — low severity alone)
            "T1059.003",   # Windows Command Shell (moderate risk)
            "T1003.001",   # LSA Memory dumping (credential theft)
            "T1021.001",   # Remote Desktop Protocol (lateral movement)
            "T1486",       # Data Encrypted for Impact (ransomware)
        ],
        "surfaces": ["Application", "Endpoint", "Endpoint", "Network", "Endpoint"],
        "objective": "Chain 5 discrete flaws into full ransomware exploit",
        "mythos_pattern": "vulnerability_chaining",
        "coherence_gap_risk": "interchange_failure",  # type confusion across chain
        "expected_detection_rate": 0.4,  # Chain detection is hard
    },

    # === Pattern 8: Authentication Bypass via Legacy Bug ===
    # Based on: 16-year-old FFmpeg flaw, authentication bypasses
    "auth_bypass_legacy": {
        "name": "Mythos Authentication Bypass — 16-Year-Old Flaw",
        "description": (
            "Bypassing authentication systems via 16-year-old "
            "deep-rooted vulnerability that was never patched."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1190",       # Exploit public-facing app (auth service)
            "T1556",       # Modify authentication process (legacy bypass)
            "T1078",       # Valid accounts (bypassed auth)
            "T1021",       # Remote services (lateral with bypassed auth)
            "T1005",       # Data from local system (exfil)
        ],
        "surfaces": ["Application", "Identity", "Identity", "Network", "Endpoint"],
        "objective": "Bypass authentication via 16-year-old flaw",
        "mythos_pattern": "auth_bypass",
        "coherence_gap_risk": "sieve_collapse",  # authentication bypass
        "expected_detection_rate": 0.25,  # Legacy auth bypasses are stealthy
    },

    # === Pattern 9: Type Confusion Exploit ===
    # Based on: Type system boundary crossing
    "type_confusion_exploit": {
        "name": "Mythos Type Confusion — Type System Boundary Crossing",
        "description": (
            "Exploiting type confusion vulnerabilities to bypass "
            "type system safety guarantees in memory-safe languages."
        ),
        "severity": "high",
        "technique_chain": [
            "T1190",       # Exploit public-facing app (type confusion)
            "T1068",       # Privilege escalation (type confusion → exec)
            "T1055",       # Process injection (maintain type confusion)
            "T1059",       # Command execution (post-exploitation)
        ],
        "surfaces": ["Application", "Endpoint", "Endpoint", "Endpoint"],
        "objective": "Exploit type confusion for code execution",
        "mythos_pattern": "type_confusion",
        "coherence_gap_risk": "interchange_failure",  # type confusion
        "expected_detection_rate": 0.35,  # Type confusion is hard to detect
    },

    # === Pattern 10: Race Condition Exploit ===
    # Based on: Temporal composition gaps
    "race_condition_exploit": {
        "name": "Mythos Race Condition — Temporal Gap Exploitation",
        "description": (
            "Exploiting race conditions and TOCTOU vulnerabilities "
            "in security-critical operations."
        ),
        "severity": "high",
        "technique_chain": [
            "T1068",       # Exploit race condition (TOCTOU)
            "T1548",       # Abuse elevation control (race → privilege)
            "T1055",       # Process injection (exploit race window)
            "T1021",       # Remote services (post-race access)
        ],
        "surfaces": ["Endpoint", "Endpoint", "Endpoint", "Network"],
        "objective": "Exploit race condition for privilege escalation",
        "mythos_pattern": "race_condition",
        "coherence_gap_risk": "modification_missing",  # race condition
        "expected_detection_rate": 0.3,  # Race conditions are transient
    },

    # === Pattern 11: Full APT Campaign (SolarWinds-Class) ===
    # Based on: Multi-month, multi-surface, supply chain + direct
    "full_apt_campaign": {
        "name": "Mythos Full APT Campaign — SolarWinds-Class",
        "description": (
            "Complete APT campaign combining supply chain compromise, "
            "cross-surface pivoting, and data exfiltration over months."
        ),
        "severity": "critical",
        "technique_chain": [
            "T1195.002",   # Compromise software supply chain
            "T1059",       # Execute via build system
            "T1055",       # Process injection (persistence)
            "T1078",       # Valid accounts (credential abuse)
            "T1021",       # Lateral movement (cross-surface pivot)
            "T1556",       # Modify auth process (maintain access)
            "T1005",       # Data from local system (collection)
            "T1041",       # Exfiltration over C2 (data theft)
        ],
        "surfaces": [
            "Application", "Endpoint", "Endpoint", "Identity",
            "Network", "Identity", "Endpoint", "Network",
        ],
        "objective": "Full APT campaign: supply chain → exfiltration",
        "mythos_pattern": "full_apt",
        "coherence_gap_risk": "privilege_non_commute",  # multi-step priv esc
        "expected_detection_rate": 0.25,  # APTs are designed to be stealthy
    },

    # === Pattern 12: Use-After-Free Exploit ===
    # Based on: Memory region temporal gaps
    "use_after_free_exploit": {
        "name": "Mythos Use-After-Free — Memory Lifetime Violation",
        "description": (
            "Exploiting use-after-free vulnerabilities in "
            "memory-safe code via temporal memory region gaps."
        ),
        "severity": "high",
        "technique_chain": [
            "T1190",       # Exploit UAF vulnerability
            "T1068",       # Privilege escalation (UAF → code exec)
            "T1055",       # Process injection (maintain UAF exploitation)
            "T1059",       # Command execution (post-exploitation)
        ],
        "surfaces": ["Application", "Endpoint", "Endpoint", "Endpoint"],
        "objective": "Exploit use-after-free for arbitrary code execution",
        "mythos_pattern": "use_after_free",
        "coherence_gap_risk": "lifetime_violation",  # memory lifetime
        "expected_detection_rate": 0.3,  # UAF exploitation is sophisticated
    },
}


# =============================================================================
# Simulation Results
# =============================================================================

@dataclass
class MythosSimulationResult:
    """Result from one Mythos-style attack simulation."""
    attack_name: str
    attack_pattern: str
    coherence_gap_risk: str
    severity: str

    # Simulation results
    detection_rate: float
    mean_time_to_detect: float
    undetected_steps: List[int]
    stealth_achieved: float
    risk_score: float

    # Gray coherence validation
    coherence_gaps_found: int
    chainable_gaps: int
    critical_gaps: int
    mythos_risk_score: float
    step_to_gap_mapping: Dict[int, Dict]
    remediation_actions: List[str]

    # Metadata
    simulation_time_ms: float
    success: bool = True
    error: str = ""


@dataclass
class MythosRiskProfile:
    """Overall Mythos risk assessment for a system."""
    total_simulations: int
    successful_simulations: int
    average_detection_rate: float
    average_risk_score: float
    total_coherence_gaps: int
    total_chainable_gaps: int
    total_critical_gaps: int

    # By pattern type
    by_pattern: Dict[str, int]
    by_coherence_gap: Dict[str, int]

    # Overall assessment
    mythos_readiness_score: float  # 0-1, higher is better
    highest_risk_patterns: List[str]
    recommended_actions: List[str]


# =============================================================================
# Simulation Suite
# =============================================================================

class MythosAttackSimulationSuite:
    """
    Complete Mythos-style attack simulation suite.

    Runs 12 realistic attack patterns based on real Mythos capabilities,
    then validates each against gray coherence to find structural gaps.

    Usage:
        suite = MythosAttackSimulationSuite(oracle)

        # Run all simulations
        results = suite.run_all_simulations()

        # Run specific pattern
        result = suite.run_simulation("sandbox_escape_chain")

        # Get risk profile
        profile = suite.get_mythos_risk_profile()

        # Print report
        suite.print_report()
    """

    def __init__(self, oracle: "CyberSecurityOracle"):
        self.oracle = oracle
        self.simulator = RedTeamSimulator(oracle)
        self.results: List[MythosSimulationResult] = []
        self._total_time_ms = 0.0

    def run_simulation(self, attack_name: str) -> MythosSimulationResult:
        """
        Run one Mythos-style attack simulation.

        Args:
            attack_name: Key from MYTHOS_ATTACK_CHAINS

        Returns:
            MythosSimulationResult with all findings
        """
        start = time.time()

        if attack_name not in MYTHOS_ATTACK_CHAINS:
            return MythosSimulationResult(
                attack_name=attack_name,
                attack_pattern="unknown",
                coherence_gap_risk="unknown",
                severity="unknown",
                detection_rate=0.0,
                mean_time_to_detect=0.0,
                undetected_steps=[],
                stealth_achieved=0.0,
                risk_score=0.0,
                coherence_gaps_found=0,
                chainable_gaps=0,
                critical_gaps=0,
                mythos_risk_score=0.0,
                step_to_gap_mapping={},
                remediation_actions=[],
                simulation_time_ms=0.0,
                success=False,
                error=f"Unknown attack pattern: {attack_name}",
            )

        attack = MYTHOS_ATTACK_CHAINS[attack_name]

        try:
            # Build attack campaign
            from cyber.attack_simulator import AttackCampaign
            campaign = AttackCampaign(
                name=attack["name"],
                technique_chain=attack["technique_chain"],
                surfaces=attack["surfaces"],
                timing_delays=[300.0] * len(attack["technique_chain"]),
                stealth_target=1.0 - attack["expected_detection_rate"],
                entry_point=attack["technique_chain"][0],
                objective=attack["objective"],
                metadata={
                    "mythos_pattern": attack["mythos_pattern"],
                    "coherence_gap_risk": attack["coherence_gap_risk"],
                },
            )

            # Execute simulated attack
            report = self.simulator.execute_simulated_attack(campaign)

            # Validate against gray coherence (NEW STEP)
            mythos_validation = self.simulator.validate_against_mythos(report)

            elapsed_ms = (time.time() - start) * 1000

            result = MythosSimulationResult(
                attack_name=attack["name"],
                attack_pattern=attack["mythos_pattern"],
                coherence_gap_risk=attack["coherence_gap_risk"],
                severity=attack["severity"],
                detection_rate=report.overall_detection_rate,
                mean_time_to_detect=report.mean_time_to_detect or 0.0,
                undetected_steps=report.undetected_steps,
                stealth_achieved=report.stealth_achieved,
                risk_score=report.risk_score,
                coherence_gaps_found=mythos_validation["coherence_gaps_found"],
                chainable_gaps=mythos_validation["chainable_gaps"],
                critical_gaps=mythos_validation["critical_gaps"],
                mythos_risk_score=mythos_validation["mythos_risk_score"],
                step_to_gap_mapping=mythos_validation["step_to_gap_mapping"],
                remediation_actions=mythos_validation["remediation_actions"],
                simulation_time_ms=elapsed_ms,
                success=True,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            logger.error(f"[MythosSimulation] {attack_name} failed: {e}")
            result = MythosSimulationResult(
                attack_name=attack["name"],
                attack_pattern=attack["mythos_pattern"],
                coherence_gap_risk=attack["coherence_gap_risk"],
                severity=attack["severity"],
                detection_rate=0.0,
                mean_time_to_detect=0.0,
                undetected_steps=[],
                stealth_achieved=0.0,
                risk_score=0.0,
                coherence_gaps_found=0,
                chainable_gaps=0,
                critical_gaps=0,
                mythos_risk_score=0.0,
                step_to_gap_mapping={},
                remediation_actions=[],
                simulation_time_ms=elapsed_ms,
                success=False,
                error=str(e),
            )

        self.results.append(result)
        self._total_time_ms += result.simulation_time_ms

        return result

    def run_all_simulations(
        self,
        attack_names: Optional[List[str]] = None,
    ) -> List[MythosSimulationResult]:
        """
        Run all Mythos-style attack simulations.

        Args:
            attack_names: Specific attacks to run (None = all)

        Returns:
            List of results, sorted by mythos_risk_score descending
        """
        names = attack_names or list(MYTHOS_ATTACK_CHAINS.keys())

        logger.info(
            f"[MythosSimulation] Starting {len(names)} attack simulations..."
        )

        for name in names:
            result = self.run_simulation(name)
            status = "✓" if result.success else "✗"
            logger.info(
                f"  {status} {result.attack_name[:50]:<50} "
                f"risk={result.mythos_risk_score:.2f} "
                f"gaps={result.coherence_gaps_found}"
            )

        # Sort by risk score descending
        self.results.sort(key=lambda r: r.mythos_risk_score, reverse=True)

        return self.results

    def get_mythos_risk_profile(self) -> MythosRiskProfile:
        """
        Compute overall Mythos risk profile from simulation results.

        Returns:
            MythosRiskProfile with comprehensive assessment
        """
        if not self.results:
            return MythosRiskProfile(
                total_simulations=0,
                successful_simulations=0,
                average_detection_rate=0.0,
                average_risk_score=0.0,
                total_coherence_gaps=0,
                total_chainable_gaps=0,
                total_critical_gaps=0,
                by_pattern={},
                by_coherence_gap={},
                mythos_readiness_score=1.0,
                highest_risk_patterns=[],
                recommended_actions=[],
            )

        successful = [r for r in self.results if r.success]
        total = len(successful)

        avg_detection = (
            sum(r.detection_rate for r in successful) / total if total > 0 else 0.0
        )
        avg_risk = (
            sum(r.risk_score for r in successful) / total if total > 0 else 0.0
        )

        total_gaps = sum(r.coherence_gaps_found for r in successful)
        total_chainable = sum(r.chainable_gaps for r in successful)
        total_critical = sum(r.critical_gaps for r in successful)

        # By pattern
        by_pattern: Dict[str, int] = {}
        for r in successful:
            by_pattern[r.attack_pattern] = by_pattern.get(r.attack_pattern, 0) + 1

        # By coherence gap
        by_coherence_gap: Dict[str, int] = {}
        for r in successful:
            if r.coherence_gap_risk:
                by_coherence_gap[r.coherence_gap_risk] = (
                    by_coherence_gap.get(r.coherence_gap_risk, 0) + 1
                )

        # Highest risk patterns
        highest_risk = sorted(
            set(r.attack_pattern for r in successful if r.mythos_risk_score > 0.5),
            key=lambda p: -sum(
                r.mythos_risk_score for r in successful if r.attack_pattern == p
            ),
        )[:5]

        # Recommended actions (from all remediation actions)
        all_remediation: List[str] = []
        for r in successful:
            all_remediation.extend(r.remediation_actions)
        recommended = list(set(all_remediation))[:10]

        # Readiness score: inverse of average risk
        readiness = max(0.0, 1.0 - avg_risk)

        return MythosRiskProfile(
            total_simulations=len(self.results),
            successful_simulations=total,
            average_detection_rate=avg_detection,
            average_risk_score=avg_risk,
            total_coherence_gaps=total_gaps,
            total_chainable_gaps=total_chainable,
            total_critical_gaps=total_critical,
            by_pattern=by_pattern,
            by_coherence_gap=by_coherence_gap,
            mythos_readiness_score=readiness,
            highest_risk_patterns=highest_risk,
            recommended_actions=recommended,
        )

    def print_report(self) -> str:
        """
        Print comprehensive Mythos simulation report.

        Returns:
            Report string
        """
        profile = self.get_mythos_risk_profile()

        lines = [
            "=" * 80,
            "MYTHOS ATTACK SIMULATION REPORT",
            "=" * 80,
            "",
            f"Simulations run      : {profile.total_simulations}",
            f"Successful           : {profile.successful_simulations}",
            f"Avg detection rate   : {profile.average_detection_rate:.2%}",
            f"Avg risk score       : {profile.average_risk_score:.2f}",
            "",
            "--- COHERENCE GAP ANALYSIS ---",
            f"Total gaps found     : {profile.total_coherence_gaps}",
            f"Chainable gaps       : {profile.total_chainable_gaps} (Mythos can chain these)",
            f"Critical gaps        : {profile.total_critical_gaps} (immediate action required)",
            "",
            "--- BY ATTACK PATTERN ---",
        ]

        for pattern, count in sorted(
            profile.by_pattern.items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {pattern:<30} {count} simulations")

        lines.append("")
        lines.append("--- BY COHERENCE GAP TYPE ---")

        for gap_type, count in sorted(
            profile.by_coherence_gap.items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {gap_type:<30} {count} risks")

        lines.append("")
        lines.append(f"MYTHOS READINESS SCORE: {profile.mythos_readiness_score:.2f}/1.00")

        if profile.highest_risk_patterns:
            lines.append("")
            lines.append("HIGHEST RISK PATTERNS:")
            for pattern in profile.highest_risk_patterns:
                lines.append(f"  ⚠ {pattern}")

        if profile.recommended_actions:
            lines.append("")
            lines.append("RECOMMENDED ACTIONS:")
            for action in profile.recommended_actions[:5]:
                lines.append(f"  • {action}")

        lines.append("")
        lines.append("--- DETAILED RESULTS ---")
        lines.append("")

        for i, result in enumerate(self.results, 1):
            status = "✓" if result.success else "✗"
            lines.append(
                f"{i:>2}. {status} {result.attack_name}"
            )
            lines.append(f"    Pattern     : {result.attack_pattern}")
            lines.append(f"    Severity    : {result.severity}")
            lines.append(f"    Detection   : {result.detection_rate:.2%}")
            lines.append(f"    Risk Score  : {result.risk_score:.2f}")
            lines.append(f"    MTTD        : {result.mean_time_to_detect:.1f}s")
            lines.append(f"    Undetected  : {len(result.undetected_steps)} steps")
            lines.append(f"    Stealth     : {result.stealth_achieved:.2f}")
            lines.append(
                f"    Coherence   : {result.coherence_gaps_found} gaps "
                f"({result.critical_gaps} critical, "
                f"{result.chainable_gaps} chainable)"
            )
            lines.append(f"    Mythos Risk: {result.mythos_risk_score:.2f}")
            if result.remediation_actions:
                lines.append(f"    Remediation:")
                for action in result.remediation_actions[:3]:
                    lines.append(f"      - {action}")
            lines.append("")

        lines.append("=" * 80)
        lines.append(
            f"Total simulation time: {self._total_time_ms:.0f}ms"
        )
        lines.append("=" * 80)

        report = "\n".join(lines)
        print(report)
        return report


# =============================================================================
# Convenience: Run simulations directly
# =============================================================================

def run_mythos_simulations(oracle: "CyberSecurityOracle") -> MythosRiskProfile:
    """
    Run all Mythos attack simulations and return risk profile.

    One-liner for quick assessment.

    Usage:
        from cyber.cyber_oracle import CyberSecurityOracle
        oracle = CyberSecurityOracle()
        profile = run_mythos_simulations(oracle)
        print(f"Readiness: {profile.mythos_readiness_score:.2f}")
    """
    suite = MythosAttackSimulationSuite(oracle)
    suite.run_all_simulations()
    suite.print_report()
    return suite.get_mythos_risk_profile()
