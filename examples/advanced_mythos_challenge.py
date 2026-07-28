#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Advanced Mythos Challenge - Real-World Attack Patterns

Based on actual CVEs and attack techniques discovered in 2025-2026:
- CVE-2026-4747: FreeBSD NFS RCE (17-year-old bug, Mythos autonomous)
- CVE-2026-5281: Chrome WebGPU zero-day
- CVE-2025-37899: Linux kernel SMB 0-day (found by ChatGPT o3)
- CVE-2025-38352: Linux POSIX CPU timers race condition
- Spectre/Meltdown/Foreshadow: Microarchitectural side-channels
- XZ Utils backdoor: Multi-year supply chain social engineering
- ROP chains with JIT heap spray
- SGX enclave attacks

This simulation tests KOMPOSOS-IV against attacks that are HARD to detect:
- Side-channel attacks (timing, cache, speculative execution)
- Social engineering (multi-year, subtle, no code execution initially)
- Hardware/microarchitectural vulnerabilities
- Novel exploitation techniques (heap spray + ROP + kernel exploit chains)
- Cryptographic attacks

NOT fitting the software - testing its LIMITS.

Sources:
- https://red.anthropic.com/2026/mythos-preview/
- https://thehackernews.com/2026/04/anthropics-claude-mythos-finds.html
- https://linuxsecurity.com/news/security-vulnerabilities/7-linux-kernel-vulnerabilities-exploited-in-2025
- https://cyberspit.com/chrome-dawn-webgpu-zero-day-cve-2026-5281.html
- https://www.upwind.io/feed/linux-kernel-smb-0-day-vulnerability-cve-2025-37899-uncovered-using-chatgpt-o3
- https://spectreattack.com/spectre.pdf
- https://foreshadowattack.eu/foreshadow.pdf
- https://www.invicti.com/blog/web-security/xz-utils-backdoor-supply-chain-rce-that-got-caught
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.category import Category
from core.gray_coherence import GrayCategoryLayer, TwoCellProxy, CoherenceGapType
from cyber.cyber_oracle import CyberSecurityOracle
from dataclasses import dataclass
from typing import List, Tuple, Optional
import time


@dataclass
class AdvancedAttack:
    """Real-world attack pattern that challenges categorical detection."""
    name: str
    cve_or_reference: str
    description: str
    techniques: List[str]  # MITRE ATT&CK
    attack_class: str  # What makes this hard to detect
    severity: str
    # Gray coherence cells (may be empty for attacks that don't fit the model)
    gray_cells: List[Tuple[str, str, str, float, int, str, float, int]]
    expected_gap_type: Optional[CoherenceGapType]
    why_hard_to_detect: str  # What challenges this poses


# === 20+ Real-World Advanced Attack Patterns ===
ADVANCED_ATTACK_SUITE = [
    # === Mythos Autonomous Discoveries ===
    AdvancedAttack(
        name="FreeBSD NFS Remote Code Execution (Mythos Autonomous)",
        cve_or_reference="CVE-2026-4747",
        description="17-year-old bug in FreeBSD NFS implementation. Fully autonomously discovered by Mythos. Unauthenticated attacker gets complete root access.",
        techniques=["T1190", "T1068", "T1078.003"],  # Exploit public app, privilege esc, local accounts
        attack_class="Ancient vulnerability (17 years)",
        severity="critical",
        gray_cells=[
            ("nfs_unauth", "root_access", "ancient_rce", 0.15, 0, "nfs_auth", 0.95, 2),
        ],
        expected_gap_type=CoherenceGapType.PRIVILEGE_NON_COMMUTE,
        why_hard_to_detect="17-year-old code path, rare usage pattern, pre-modern security practices",
    ),

    AdvancedAttack(
        name="Chrome WebGPU Zero-Day (GPU Boundary)",
        cve_or_reference="CVE-2026-5281",
        description="Chrome Dawn WebGPU implementation crosses GPU boundary, allowing renderer to access GPU memory and escape sandbox via driver vulnerability.",
        techniques=["T1203", "T1611", "T1068"],  # Exploitation, container escape, privilege esc
        attack_class="Hardware boundary crossing",
        severity="critical",
        gray_cells=[
            ("renderer", "gpu_driver", "webgpu_boundary", 0.2, 0, "sandboxed_gpu", 0.9, 1),
            ("gpu_driver", "kernel", "driver_vuln", 0.25, 1, "isolated_driver", 0.85, 2),
        ],
        expected_gap_type=CoherenceGapType.FUNCTOR_ESCAPE,
        why_hard_to_detect="Novel attack surface (WebGPU), crosses hardware/software boundary, GPU driver complexity",
    ),

    AdvancedAttack(
        name="Linux Kernel SMB 0-Day (AI-Discovered)",
        cve_or_reference="CVE-2025-37899",
        description="Found by ChatGPT o3 in ksmbd module. Stack-based buffer overflow in SMB2_TREE_CONNECT handling leads to kernel code execution.",
        techniques=["T1190", "T1203", "T1068"],
        attack_class="AI-discovered kernel vulnerability",
        severity="critical",
        gray_cells=[
            ("smb_input", "kernel_stack", "buffer_overflow", 0.25, 0, "bounds_check", 0.95, 2),
        ],
        expected_gap_type=CoherenceGapType.COMPOSITION_BOUNDARY,
        why_hard_to_detect="Recent kernel module (ksmbd), complex protocol parsing, AI found what humans missed",
    ),

    # === Speculative Execution Attacks (VERY HARD TO DETECT) ===
    AdvancedAttack(
        name="Spectre v2 - Branch Target Injection",
        cve_or_reference="CVE-2017-5715 (variants in 2025)",
        description="Training Solo self-training attack. Attacker trains indirect branch predictor to speculatively execute attacker-chosen code, leaking secrets via side channels.",
        techniques=["T1203", "T1530"],  # Exploitation, data from cloud storage
        attack_class="Microarchitectural side-channel",
        severity="high",
        gray_cells=[],  # NO direct control flow visible to category theory
        expected_gap_type=None,
        why_hard_to_detect="Transient execution leaves no trace. Side-channel timing attack. Microarchitectural state not modeled in software categories.",
    ),

    AdvancedAttack(
        name="Meltdown - Rogue Data Cache Load",
        cve_or_reference="CVE-2017-5754",
        description="Out-of-order execution allows user-space to read kernel memory via cache timing side-channel. No privilege escalation in traditional sense - speculative execution bypasses checks.",
        techniques=["T1005", "T1530"],  # Data from local system, data from cloud
        attack_class="Microarchitectural side-channel",
        severity="critical",
        gray_cells=[],  # Timing attack - no visible privilege change
        expected_gap_type=None,
        why_hard_to_detect="No actual privilege escalation. Speculative execution is CPU-internal. Cache timing side-channel. Architectural vs microarchitectural boundary.",
    ),

    AdvancedAttack(
        name="Foreshadow - SGX Enclave Extraction",
        cve_or_reference="L1 Terminal Fault (CVE-2018-3615)",
        description="Speculative execution attack on Intel SGX. Extracts seal keys and attestation keys from Intel-signed enclaves, completely breaking SGX confidentiality guarantees.",
        techniques=["T1555", "T1552.004"],  # Credentials from password stores, private keys
        attack_class="Hardware security mechanism bypass",
        severity="critical",
        gray_cells=[],  # Hardware enclave - not modeled in software categories
        expected_gap_type=None,
        why_hard_to_detect="Attacks hardware security features (SGX). Speculative execution at L1 cache level. Requires no software vulnerability - CPU design flaw.",
    ),

    # === Supply Chain & Social Engineering (VERY HARD TO DETECT) ===
    AdvancedAttack(
        name="XZ Utils Backdoor - Multi-Year Social Engineering",
        cve_or_reference="CVE-2024-3094 (CVSS 10.0)",
        description="Multi-year social engineering campaign. Attacker gained maintainer access, inserted backdoor in test files that reassembles during build. Targets OpenSSH authentication. Discovered by accident (500ms SSH delay).",
        techniques=["T1195.002", "T1554", "T1098"],  # Compromise software supply chain, compromise host software binary, account manipulation
        attack_class="Long-term social engineering",
        severity="critical",
        gray_cells=[],  # Social engineering - no technical exploit chain visible
        expected_gap_type=None,
        why_hard_to_detect="Multi-year trusted contributor. Code hidden in test files. Only visible during compilation. No exploit chain - legitimate maintainer access. Detection was luck (timing anomaly).",
    ),

    AdvancedAttack(
        name="SolarWinds SUNBURST Supply Chain",
        cve_or_reference="SolarWinds Orion (2020, still relevant)",
        description="Nation-state supply chain attack. Trojanized updates to 18,000+ organizations. Used steganography, rotating infrastructure, memory-only execution, code obfuscation.",
        techniques=["T1195.002", "T1554", "T1027", "T1027.010", "T1071"],  # Supply chain, compromise binary, obfuscation, command obfuscation, app layer protocol
        attack_class="Nation-state supply chain",
        severity="critical",
        gray_cells=[
            ("trusted_update", "backdoor_deployed", "supply_chain", 0.05, 2, "signed_update", 0.99, 2),  # Both have high privilege - hard to distinguish
        ],
        expected_gap_type=None,  # Privilege levels are SAME
        why_hard_to_detect="Signed by trusted vendor. High privilege from start. Steganography. Memory-only execution. Mimics normal network traffic. Multi-year operation.",
    ),

    # === Multi-Stage Browser Exploitation (REAL CHAINS) ===
    AdvancedAttack(
        name="Chrome Renderer → ANGLE → Linux Kernel Chain",
        cve_or_reference="CVE-2025-5419 + CVE-2025-6558 + CVE-2025-38352",
        description="Documented in-the-wild chain. Chrome renderer vuln → ANGLE sandbox escape → Linux kernel POSIX CPU timers race condition → full system compromise.",
        techniques=["T1203", "T1611", "T1068", "T1055"],
        attack_class="Multi-stage exploitation chain",
        severity="critical",
        gray_cells=[
            ("renderer", "sandbox", "chrome_vuln", 0.3, 0, "isolated_renderer", 0.9, 1),
            ("sandbox", "host_user", "angle_escape", 0.25, 1, "contained", 0.85, 1),
            ("host_user", "kernel_root", "race_condition", 0.2, 1, "user_boundary", 0.9, 2),
        ],
        expected_gap_type=CoherenceGapType.MODIFICATION_MISSING,  # Race condition
        why_hard_to_detect="Three distinct vulnerabilities chained. Race condition is temporal (not spatial). Requires precise timing. Each stage has different detection signature.",
    ),

    AdvancedAttack(
        name="JIT Heap Spray + ROP Chain + Kernel Exploit",
        cve_or_reference="Mythos technique",
        description="Mythos-generated multi-stage: JIT compile attacker-controlled code to spray heap with ROP gadgets, trigger use-after-free, pivot stack to ROP chain, exploit kernel vulnerability for privilege escalation.",
        techniques=["T1203", "T1055", "T1068"],
        attack_class="Advanced exploitation technique",
        severity="critical",
        gray_cells=[
            ("jit_code", "rop_gadgets", "heap_spray", 0.2, 0, "jit_hardened", 0.9, 1),
            ("rop_chain", "kernel_exploit", "stack_pivot", 0.25, 1, "stack_canary", 0.85, 2),
        ],
        expected_gap_type=CoherenceGapType.LIFETIME_VIOLATION,
        why_hard_to_detect="JIT-compiled code looks legitimate. Heap spray is gradual. ROP uses existing code gadgets (no new code injection). Stack pivot bypasses ASLR. Multi-technique chain.",
    ),

    # === Kernel Exploitation Chains ===
    AdvancedAttack(
        name="Linux Kernel nftables Heap OOB Write",
        cve_or_reference="CVE-2021-22555 (exploited in 2025)",
        description="Heap out-of-bounds write in nftables component allows local users to gain root via arbitrary kernel code execution.",
        techniques=["T1068", "T1548.001"],  # Privilege escalation, setuid/setgid
        attack_class="Kernel memory corruption",
        severity="critical",
        gray_cells=[
            ("user_space", "kernel_heap", "oob_write", 0.3, 0, "bounds_checked", 0.95, 2),
        ],
        expected_gap_type=CoherenceGapType.COMPOSITION_BOUNDARY,
        why_hard_to_detect="Heap corruption is subtle. Out-of-bounds by small offset. Kernel memory corruption hard to observe from userspace. Nftables is complex subsystem.",
    ),

    AdvancedAttack(
        name="UNIX Domain Socket MSG_OOB Use-After-Free",
        cve_or_reference="Sandbox → Kernel chain (2025)",
        description="Sandboxed process exploits MSG_OOB on UNIX socket to trigger kernel UAF, leaking kernel pointers for KASLR bypass, then full privilege escalation.",
        techniques=["T1611", "T1068"],
        attack_class="Sandbox escape via kernel bug",
        severity="critical",
        gray_cells=[
            ("sandbox", "kernel_memory", "socket_uaf", 0.25, 0, "sandbox_contained", 0.9, 1),
            ("kernel_memory", "kernel_exec", "kaslr_bypass", 0.3, 1, "aslr_protected", 0.85, 2),
        ],
        expected_gap_type=CoherenceGapType.LIFETIME_VIOLATION,
        why_hard_to_detect="Use-after-free is temporal. Socket operations look normal. KASLR bypass via memory leak requires two-stage exploitation. Sandboxed process has legitimate socket access.",
    ),

    # === Cryptographic & Protocol Attacks ===
    AdvancedAttack(
        name="TLS 1.3 State Machine Confusion",
        cve_or_reference="Protocol-level attack",
        description="Out-of-order TLS handshake messages cause state machine confusion, allowing authentication bypass or downgrade attacks. No code vulnerability - protocol implementation flaw.",
        techniques=["T1557.002", "T1071.001"],  # Man-in-the-middle, web protocols
        attack_class="Protocol-level attack",
        severity="high",
        gray_cells=[],  # Protocol state machine - not software bug
        expected_gap_type=None,
        why_hard_to_detect="No code vulnerability. Protocol state machine logic flaw. Requires deep protocol understanding. Looks like normal TLS traffic. Subtle ordering dependency.",
    ),

    AdvancedAttack(
        name="Bluetooth Link Key Extraction",
        cve_or_reference="KNOB attack variants",
        description="Force Bluetooth to negotiate 1-byte encryption key, allowing brute-force in real-time. Extract link key from encrypted connection via cryptographic weakness.",
        techniques=["T1557", "T1040", "T1602"],  # MITM, network sniffing, data from network shared drive
        attack_class="Cryptographic weakness",
        severity="medium",
        gray_cells=[],  # Crypto protocol weakness - not software vulnerability
        expected_gap_type=None,
        why_hard_to_detect="Protocol-level cryptographic flaw. No software exploit. Legitimate Bluetooth traffic. Downgrade attack during pairing. Requires physical proximity.",
    ),

    # === Container & Orchestration Escapes ===
    AdvancedAttack(
        name="Kubernetes API Server Privilege Escalation",
        cve_or_reference="CVE-2024-3177 variants",
        description="Misconfigured RBAC allows pod to access API server, escalate privileges, and deploy privileged containers with host filesystem access.",
        techniques=["T1611", "T1610", "T1548"],  # Container escape, deploy container, privilege escalation
        attack_class="Orchestration misconfiguration",
        severity="critical",
        gray_cells=[
            ("pod", "api_server", "rbac_bypass", 0.3, 1, "rbac_locked", 0.9, 1),
            ("api_server", "host_node", "privileged_pod", 0.35, 1, "pod_security", 0.85, 2),
        ],
        expected_gap_type=CoherenceGapType.PRIVILEGE_NON_COMMUTE,
        why_hard_to_detect="Configuration flaw, not code bug. RBAC complexity. Legitimate API calls. Privileged pods sometimes needed. No exploit code - just API manipulation.",
    ),

    AdvancedAttack(
        name="Docker runC Container Escape",
        cve_or_reference="CVE-2024-21626",
        description="File descriptor leak in runC allows container to access host filesystem via /proc/self/fd/. Container can write to host and escape.",
        techniques=["T1611", "T1068"],
        attack_class="Container runtime vulnerability",
        severity="critical",
        gray_cells=[
            ("container", "host_fs", "fd_leak", 0.25, 0, "namespace_isolated", 0.95, 1),
        ],
        expected_gap_type=CoherenceGapType.FUNCTOR_ESCAPE,
        why_hard_to_detect="File descriptor leak is subtle. /proc filesystem complexity. Container has legitimate /proc access. Race condition during exec. Namespace isolation bypassed at FD level.",
    ),

    # === AI/ML System Attacks ===
    AdvancedAttack(
        name="LLM Prompt Injection → Tool Use → RCE",
        cve_or_reference="Emerging attack class (2025-2026)",
        description="Indirect prompt injection in AI agent context causes model to execute malicious tool calls, leading to remote code execution via command injection in shell tool.",
        techniques=["T1059", "T1203", "T1071"],  # Command execution, exploitation, application layer protocol
        attack_class="AI/ML system attack",
        severity="high",
        gray_cells=[
            ("user_input", "model_output", "prompt_injection", 0.15, 0, "input_sanitized", 0.8, 1),
            ("model_output", "shell_exec", "tool_misuse", 0.25, 1, "sandboxed_tools", 0.85, 2),
        ],
        expected_gap_type=CoherenceGapType.SIEVE_COLLAPSE,
        why_hard_to_detect="Indirect injection (via context, not direct input). Model behavior hard to predict. Tool use looks legitimate. No traditional vulnerability - design flaw. Prompt content not code.",
    ),

    # === Firmware & Hardware Attacks ===
    AdvancedAttack(
        name="UEFI Bootkit Persistence",
        cve_or_reference="BlackLotus variants (2025)",
        description="Bypass Secure Boot via UEFI vulnerability, install bootkit in ESP partition. Survives OS reinstall, disk wipe. Pre-OS execution with ring 0 privileges.",
        techniques=["T1542.001", "T1542.003", "T1547.001"],  # System firmware, bootkit, registry run keys
        attack_class="Firmware-level persistence",
        severity="critical",
        gray_cells=[],  # Pre-OS, firmware level - outside OS category model
        expected_gap_type=None,
        why_hard_to_detect="Pre-OS execution. Firmware-level (below OS). Survives reinstalls. Secure Boot bypass. No software-level detection possible once installed. Signed bootloader exploitation.",
    ),

    AdvancedAttack(
        name="Intel Management Engine Backdoor",
        cve_or_reference="IME vulnerabilities (ongoing)",
        description="Exploit in Intel ME firmware allows persistent access with ring -3 privileges (below OS, hypervisor, SMM). Complete system access independent of OS state.",
        techniques=["T1542.001", "T1557", "T1205.002"],  # System firmware, MITM, sockets
        attack_class="Hardware-level backdoor",
        severity="critical",
        gray_cells=[],  # Ring -3 - hardware level, not modeled in software
        expected_gap_type=None,
        why_hard_to_detect="Ring -3 (below everything). Independent processor. Persistent across power cycles. OS cannot observe. Signed firmware. Requires hardware-level detection.",
    ),

    # === Network & Protocol Exploitation ===
    AdvancedAttack(
        name="BGP Route Hijacking",
        cve_or_reference="Routing protocol attack",
        description="Announce more-specific BGP routes to hijack traffic. MITM attack at internet routing level. No software vulnerability - protocol design allows it.",
        techniques=["T1557", "T1590.004"],  # MITM, gather victim network info
        attack_class="Network protocol attack",
        severity="medium",
        gray_cells=[],  # Network routing - not application-level
        expected_gap_type=None,
        why_hard_to_detect="Protocol-level attack. No software bug. Requires AS ownership or compromise. Legitimate BGP announcements. Internet-scale routing. Detection requires global view.",
    ),

    AdvancedAttack(
        name="DNS Cache Poisoning with Fragments",
        cve_or_reference="Kaminsky attack variants (2025)",
        description="Use IP fragmentation to evade DNS response validation. Poison resolver cache with attacker-controlled records, enabling phishing and MITM.",
        techniques=["T1584.002", "T1557.002"],  # Compromise DNS server, ARP cache poisoning
        attack_class="Protocol-level attack",
        severity="high",
        gray_cells=[],  # Network protocol - not application vulnerability
        expected_gap_type=None,
        why_hard_to_detect="Protocol-level. IP fragmentation complexity. Legitimate DNS queries. Timing-dependent. Cache poisoning is transient. No code execution - just data corruption.",
    ),

    # === Advanced Persistent Threats ===
    AdvancedAttack(
        name="Living Off The Land - Fileless Malware",
        cve_or_reference="APT29 (Cozy Bear) techniques",
        description="Use only built-in Windows tools (PowerShell, WMI, regsvr32, certutil). No custom malware. Memory-only execution. Registry persistence. Mimics legitimate admin activity.",
        techniques=["T1059.001", "T1047", "T1218.010", "T1218.011", "T1547.001"],  # PowerShell, WMI, regsvr32, rundll32, registry persistence
        attack_class="Living off the land",
        severity="high",
        gray_cells=[],  # No exploit - legitimate tools used maliciously
        expected_gap_type=None,
        why_hard_to_detect="Legitimate system tools. No malware file. Memory-only. Looks like admin activity. Signed binaries. Behavioral detection required, not signature.",
    ),
]


def run_advanced_challenge():
    """Run advanced Mythos challenge with real-world attacks."""

    print("=" * 80)
    print("ADVANCED MYTHOS CHALLENGE - TESTING KOMPOSOS-IV LIMITS")
    print("Real-World Attacks That Challenge Categorical Detection")
    print("=" * 80)
    print()
    print("This simulation uses REAL CVEs and attack techniques:")
    print("  • Speculative execution (Spectre, Meltdown, Foreshadow)")
    print("  • Supply chain social engineering (XZ Utils, SolarWinds)")
    print("  • Multi-stage exploitation chains (3+ vulnerabilities)")
    print("  • Microarchitectural side-channels")
    print("  • Hardware/firmware attacks (UEFI, Intel ME)")
    print("  • Protocol-level attacks (TLS, BGP, DNS)")
    print("  • AI/ML system attacks (prompt injection)")
    print()
    print("Sources:")
    print("  • Anthropic Mythos Preview: https://red.anthropic.com/2026/mythos-preview/")
    print("  • Linux CVEs 2025: https://linuxsecurity.com/news/security-vulnerabilities/7-linux-kernel-vulnerabilities-exploited-in-2025")
    print("  • Chrome WebGPU CVE-2026-5281: https://cyberspit.com/chrome-dawn-webgpu-zero-day-cve-2026-5281.html")
    print("  • Spectre/Meltdown: https://spectreattack.com/spectre.pdf")
    print("  • Foreshadow (SGX): https://foreshadowattack.eu/foreshadow.pdf")
    print("  • XZ backdoor: https://www.invicti.com/blog/web-security/xz-utils-backdoor-supply-chain-rce-that-got-caught")
    print()

    # Initialize FULL KOMPOSOS system
    print("Initializing FULL KOMPOSOS-IV system...")
    start_time = time.time()
    oracle = CyberSecurityOracle()
    init_time = time.time() - start_time

    print(f"  ✓ CyberSecurityOracle loaded ({init_time:.2f}s)")
    print(f"  ✓ MITRE ATT&CK: {len(oracle.mitre_db.techniques)} techniques")
    print(f"  ✓ Valid compositions: {len(oracle.mitre_db.valid_compositions):,}")
    print(f"  ✓ 6 Categorical constructions active")
    print()

    results = []
    detected_count = 0
    missed_count = 0
    oracle_only = 0
    gray_only = 0
    both_detected = 0
    neither_detected = 0

    total_gaps = 0
    attack_class_stats = {}

    print("=" * 80)
    print("RUNNING ADVANCED ATTACK SIMULATIONS")
    print("=" * 80)
    print()

    for i, attack in enumerate(ADVANCED_ATTACK_SUITE, 1):
        print(f"{i:2d}. {attack.name}")
        print(f"    CVE/Ref: {attack.cve_or_reference}")
        print(f"    Class: {attack.attack_class} | Severity: {attack.severity.upper()}")
        print(f"    Challenge: {attack.why_hard_to_detect}")
        print(f"    MITRE: {' → '.join(attack.techniques)}")

        # Track attack class
        if attack.attack_class not in attack_class_stats:
            attack_class_stats[attack.attack_class] = {"total": 0, "detected": 0}
        attack_class_stats[attack.attack_class]["total"] += 1

        # Build attack in category
        category = Category(db_path=":memory:")
        gray = GrayCategoryLayer(category)

        for tech in attack.techniques:
            category.add(tech)

        for j in range(len(attack.techniques) - 1):
            src = attack.techniques[j]
            tgt = attack.techniques[j + 1]
            category.connect(src, tgt, f"step_{j}", confidence=0.7)

        # === Oracle Detection ===
        oracle_detected = False
        known_count = sum(1 for t in attack.techniques if t in oracle.mitre_db.techniques)
        oracle_conf = known_count / len(attack.techniques) if attack.techniques else 0
        oracle_detected = oracle_conf >= 0.75

        # === Gray Coherence Detection ===
        gray_detected = False
        gaps_found = 0

        if attack.gray_cells:  # Only check if attack has categorical representation
            for gray_cell in attack.gray_cells:
                src, tgt, exploit_label, exploit_conf, exploit_priv, safe_label, safe_conf, safe_priv = gray_cell

                alpha = TwoCellProxy(
                    source_morphism=src,
                    target_morphism=tgt,
                    label=exploit_label,
                    confidence=exploit_conf,
                    privilege_level=exploit_priv,
                )

                beta = TwoCellProxy(
                    source_morphism=src,
                    target_morphism=tgt,
                    label=safe_label,
                    confidence=safe_conf,
                    privilege_level=safe_priv,
                )

                mod = gray.check_modification_coherence(alpha, beta)

                if mod and not mod.is_coherent:
                    gray_detected = True
                    gaps_found += 1
                    total_gaps += 1

        # === Combined Detection ===
        detected = oracle_detected or gray_detected

        if detected:
            detected_count += 1
            attack_class_stats[attack.attack_class]["detected"] += 1
        else:
            missed_count += 1

        if oracle_detected and gray_detected:
            both_detected += 1
        elif oracle_detected:
            oracle_only += 1
        elif gray_detected:
            gray_only += 1
        else:
            neither_detected += 1

        # Print results
        if detected:
            status = "✅ DETECTED"
        else:
            status = "❌ EVADED DETECTION"

        print(f"    {status}")

        if oracle_detected:
            print(f"      🔍 Oracle: {oracle_conf:.0%} technique coverage")
        if gray_detected:
            print(f"      🧠 Gray Coherence: {gaps_found} gap(s)")
        if not detected:
            print(f"      💀 EVASION SUCCESS: {attack.why_hard_to_detect[:80]}...")

        print()

        results.append({
            "attack": attack.name,
            "cve": attack.cve_or_reference,
            "detected": detected,
            "oracle": oracle_detected,
            "gray": gray_detected,
            "class": attack.attack_class,
            "severity": attack.severity,
        })

    # === Summary Report ===
    print("=" * 80)
    print("ADVANCED CHALLENGE RESULTS")
    print("=" * 80)
    print()

    total_attacks = len(ADVANCED_ATTACK_SUITE)
    detection_rate = detected_count / total_attacks

    print(f"Total attacks simulated  : {total_attacks}")
    print(f"Attacks detected         : {detected_count}/{total_attacks} ({100*detection_rate:.1f}%)")
    print(f"Attacks evaded detection : {missed_count}/{total_attacks} ({100*missed_count/total_attacks:.1f}%)")
    print()
    print(f"Oracle-only detections   : {oracle_only}")
    print(f"Gray-only detections     : {gray_only}")
    print(f"Both systems detected    : {both_detected}")
    print(f"Neither system detected  : {neither_detected}")
    print(f"Total coherence gaps     : {total_gaps}")
    print()

    # Attack class breakdown
    print("Detection Rate by Attack Class:")
    for attack_class, stats in sorted(attack_class_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        total = stats["total"]
        detected = stats["detected"]
        rate = 100 * detected / total if total > 0 else 0
        print(f"  • {attack_class:35s}: {detected}/{total} ({rate:.0f}%)")
    print()

    # Severity breakdown
    severity_stats = {"critical": 0, "high": 0, "medium": 0}
    detected_by_severity = {"critical": 0, "high": 0, "medium": 0}
    for result in results:
        severity = result["severity"]
        severity_stats[severity] += 1
        if result["detected"]:
            detected_by_severity[severity] += 1

    print("Detection by Severity:")
    for sev in ["critical", "high", "medium"]:
        if severity_stats[sev] > 0:
            rate = 100 * detected_by_severity[sev] / severity_stats[sev]
            print(f"  • {sev.upper():8s}: {detected_by_severity[sev]}/{severity_stats[sev]} ({rate:.1f}%)")
    print()

    # Overall assessment
    if detection_rate >= 0.9:
        assessment = "🏆 EXCELLENT: System handles advanced attacks well (>90%)"
    elif detection_rate >= 0.75:
        assessment = "✅ GOOD: System detects most advanced attacks (75-90%)"
    elif detection_rate >= 0.6:
        assessment = "⚠️  MODERATE: System struggles with some attack classes (60-75%)"
    else:
        assessment = "❌ GAPS FOUND: Multiple attack classes evade detection (<60%)"

    print(assessment)
    print()

    # Missed attacks analysis
    if missed_count > 0:
        print("=" * 80)
        print(f"ATTACKS THAT EVADED DETECTION ({missed_count} total):")
        print("=" * 80)
        for result in results:
            if not result["detected"]:
                print(f"  ❌ {result['attack']}")
                print(f"     CVE: {result['cve']}")
                print(f"     Class: {result['class']}")
        print()

    print("=" * 80)
    print("KEY FINDINGS - LIMITS OF CATEGORICAL DETECTION")
    print("=" * 80)
    print()
    print("Attacks that challenge categorical AI:")
    print("  • Side-channel attacks (Spectre, Meltdown) - no control flow visible")
    print("  • Social engineering (XZ Utils) - no technical exploit chain")
    print("  • Hardware/firmware attacks - below OS abstraction level")
    print("  • Protocol-level attacks - no code vulnerability")
    print("  • Timing attacks - transient, no spatial trace")
    print("  • Cryptographic weaknesses - mathematical, not structural")
    print()
    print("Gray coherence excels at:")
    print("  • Privilege escalation (privilege_non_commute)")
    print("  • Container escapes (functor_escape)")
    print("  • Memory corruption (composition_boundary, lifetime_violation)")
    print("  • Authentication bypasses (sieve_collapse)")
    print()
    print("Complementary detection needed for:")
    print("  • Behavioral analysis (living off the land)")
    print("  • Anomaly detection (supply chain)")
    print("  • Hardware monitoring (microarchitectural)")
    print("  • Network analysis (protocol-level)")
    print()
    print(f"Simulation completed in {time.time() - start_time:.2f}s")
    print("=" * 80)

    return results


if __name__ == "__main__":
    results = run_advanced_challenge()
