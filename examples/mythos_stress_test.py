#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Mythos Defense Stress Test

Tests the Gray coherence defense against real Mythos-style attack patterns
documented in Anthropic's Glasswing announcement:

1. Multi-step privilege escalation (Linux kernel chain)
2. Ancient bugs (27-year-old OpenBSD vulnerability)
3. Type confusion attacks
4. Sandbox/container escape
5. Authentication bypass
6. Memory corruption chains

This simulates vulnerable code patterns that Mythos Preview found autonomously.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.category import Category
from core.gray_coherence import SoftwareCategoryBuilder, CoherenceGapType
from core.gray_coherence_bridge import build_shield, GapFinding
from bridges.cyber_security_bridge import build_cyber_bridge
from oracle import CategoricalOracle
from data.embeddings import EmbeddingsEngine


# ============================================================================
# MYTHOS-STYLE VULNERABLE CODE PATTERNS
# ============================================================================

# Pattern 1: Linux kernel privilege escalation chain (Mythos found this)
VULN_PATTERN_1_PRIV_ESCALATION = """
def user_read_config(user_id):
    # User-level read - ring 3
    config = open(f"/home/{user_id}/.config").read()
    return config

def validate_user_input(data):
    # Missing validation - structural gap
    return data  # Should sanitize but doesn't

def kernel_write_memory(addr, value):
    # Kernel-level write - ring 0
    # Should require privilege check
    mem[addr] = value  # Direct write without validation
    return True

def exploit_chain(user_input):
    # Mythos-style attack: chain user→kernel without proper elevation
    data = validate_user_input(user_input)  # Gap: no real validation
    # Type confusion: user_input contains kernel address
    kernel_write_memory(data['addr'], data['val'])  # Privilege escalation!
"""

# Pattern 2: Authentication bypass (sieve collapse)
VULN_PATTERN_2_AUTH_BYPASS = """
def unauthenticated_request(endpoint):
    # Public endpoint - no auth required
    return fetch(endpoint)

def authenticated_admin_panel(token):
    # Should require valid token
    if token:  # Weak check - any truthy value passes
        return admin_data
    return None

def bypass_exploit():
    # Sieve collapse: auth→unauth path exists
    result = unauthenticated_request("/admin")  # Should fail but doesn't
    # Type confusion: empty object is truthy
    admin = authenticated_admin_panel({})  # Bypass!
"""

# Pattern 3: Use-after-free (lifetime violation)
VULN_PATTERN_3_UAF = """
def allocate_buffer(size):
    buf = malloc(size)
    return buf

def free_buffer(buf):
    free(buf)
    # Buffer freed but pointer not nulled

def read_buffer(buf):
    # No lifetime check - use after free
    return buf.read()  # Vulnerability!

def uaf_exploit():
    buf = allocate_buffer(1024)
    free_buffer(buf)
    # Lifetime violation: buf still accessible after free
    data = read_buffer(buf)  # Use-after-free!
"""

# Pattern 4: Container escape (functor escape)
VULN_PATTERN_4_CONTAINER_ESCAPE = """
def container_user_code():
    # Code running in container - ring 3 sandboxed
    return execute_in_sandbox()

def host_privileged_operation():
    # Host system operation - requires escape
    return host.execute_privileged()

def container_mount_api(path):
    # Container API - should be sandboxed
    # Missing security policy functor
    return mount(path)  # No validation!

def escape_exploit():
    # Functor escape: container→host without policy
    container_mount_api("/host/root")  # Escapes sandbox!
    host_privileged_operation()  # Now running on host
"""

# Pattern 5: Race condition (modification missing)
VULN_PATTERN_5_RACE = """
def check_privilege(user):
    # Check if user has admin privilege
    return user.is_admin

def grant_access(user):
    # Grant access based on privilege
    if user.has_access:
        return sensitive_data

def toctou_exploit(user):
    # Time-of-check time-of-use race
    if check_privilege(user):  # Check happens here
        # Race window: user.is_admin could change
        time.sleep(0.001)  # Attacker changes user.is_admin
        grant_access(user)  # Use happens here - no sync!
"""

# Pattern 6: Type confusion (interchange failure)
VULN_PATTERN_6_TYPE_CONFUSION = """
def process_int(value: int):
    # Expects integer
    return value * 2

def process_string(value: str):
    # Expects string
    return value.upper()

def confused_handler(value):
    # Type confusion: treats all types the same
    result = process_int(value)  # Assumes int but could be string
    # Interchange failure: int path ≠ string path
    return result

def type_confusion_exploit():
    # Pass string where int expected
    confused_handler("AAAA")  # Type confusion → memory corruption
"""


# ============================================================================
# STRESS TEST RUNNER
# ============================================================================

async def run_stress_test():
    print("=" * 70)
    print("MYTHOS DEFENSE STRESS TEST")
    print("Testing against real Mythos-style attack patterns")
    print("=" * 70)
    print()

    # Initialize systems
    print("[1/5] Initializing Category and Oracle...")
    category = Category(db_path=":memory:")
    embeddings = EmbeddingsEngine()
    oracle = CategoricalOracle(category, embeddings)

    print("[2/5] Building MythosShield...")
    shield = build_shield(oracle, category=category)

    print("[3/5] Loading cyber threat intelligence...")
    cyber_bridge = build_cyber_bridge(category)

    print("[4/5] Building software categories from vulnerable code...")
    print()

    # Test each vulnerability pattern
    patterns = [
        ("Linux Kernel Privilege Escalation Chain", VULN_PATTERN_1_PRIV_ESCALATION,
         CoherenceGapType.PRIVILEGE_NON_COMMUTE, "T1068"),
        ("Authentication Bypass (Sieve Collapse)", VULN_PATTERN_2_AUTH_BYPASS,
         CoherenceGapType.SIEVE_COLLAPSE, "T1556"),
        ("Use-After-Free (Lifetime Violation)", VULN_PATTERN_3_UAF,
         CoherenceGapType.LIFETIME_VIOLATION, "T1203"),
        ("Container Escape (Functor Escape)", VULN_PATTERN_4_CONTAINER_ESCAPE,
         CoherenceGapType.FUNCTOR_ESCAPE, "T1611"),
        ("Race Condition (TOCTOU)", VULN_PATTERN_5_RACE,
         CoherenceGapType.MODIFICATION_MISSING, "T1race"),
        ("Type Confusion (Interchange Failure)", VULN_PATTERN_6_TYPE_CONFUSION,
         CoherenceGapType.INTERCHANGE_FAILURE, "T1203"),
    ]

    results = []

    for i, (name, code, expected_gap_type, expected_mitre) in enumerate(patterns, 1):
        print(f"Test {i}/6: {name}")
        print("-" * 70)

        # Write vulnerable code to temp file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name

        # Build category from vulnerable code
        builder = SoftwareCategoryBuilder()
        builder.from_source_file(temp_path)

        print(f"  Objects: {len(builder.objects)}")
        print(f"  Morphisms: {len(builder.morphisms)}")

        # Add to main category
        for obj_name, obj in builder.objects.items():
            if obj_name not in [o.name for o in category.objects()]:
                category.add(obj_name)

        for morph in builder.morphisms:
            if morph.source in [o.name for o in category.objects()] and \
               morph.target in [o.name for o in category.objects()]:
                category.connect(
                    morph.source,
                    morph.target,
                    morph.label,
                    confidence=morph.confidence
                )

        # Clean up temp file
        import os
        os.unlink(temp_path)

        # Enumerate 2-cell pairs from this builder
        pairs = builder.enumerate_2cell_pairs()
        print(f"  2-cell pairs to check: {len(pairs)}")

        # Check for coherence gaps
        gaps_found = []
        for alpha, beta in pairs:
            mod = shield.gray_layer.check_modification_coherence(alpha, beta)
            if not mod.is_coherent:
                gaps_found.append(mod)

        detected = any(g.gap_type == expected_gap_type for g in gaps_found)

        if detected:
            print(f"  ✓ DETECTED: {expected_gap_type.value}")
            matching_gap = next(g for g in gaps_found if g.gap_type == expected_gap_type)
            vuln = shield.mapper.classify(matching_gap)
            print(f"    Vulnerability: {vuln.vuln_class}")
            print(f"    Severity: {vuln.severity:.2f}")
            print(f"    MITRE: {vuln.mitre_id}")
            print(f"    Fix: {vuln.remediation}")
            results.append((name, True, expected_gap_type.value, vuln.mitre_id))
        else:
            print(f"  ✗ MISSED: Expected {expected_gap_type.value}")
            if gaps_found:
                print(f"    Found instead: {[g.gap_type.value for g in gaps_found]}")
            results.append((name, False, expected_gap_type.value, "N/A"))

        print()

    # Run full MythosShield scan
    print("[5/5] Running complete MythosShield scan...")
    print()

    report = shield.scan(top_k=200, min_confidence=0.2, hollow_only=True)

    print()
    print("=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)
    print()

    # Summary table
    print("Detection Results:")
    print()
    print(f"{'Attack Pattern':<45} {'Detected':<10} {'Gap Type':<25} {'MITRE'}")
    print("-" * 70)
    for name, detected, gap_type, mitre in results:
        status = "✓ YES" if detected else "✗ NO"
        print(f"{name:<45} {status:<10} {gap_type:<25} {mitre}")

    print()
    detection_rate = sum(1 for _, d, _, _ in results if d) / len(results) * 100
    print(f"Overall Detection Rate: {detection_rate:.1f}% ({sum(1 for _, d, _, _ in results if d)}/{len(results)})")
    print()

    # Full scan results
    print("Complete MythosShield Scan:")
    print(f"  Total gaps found: {len(report.findings)}")
    print(f"  Critical: {len(report.critical)}")
    print(f"  Chainable (Mythos target): {len(report.chainable)}")
    print()

    if report.chainable:
        print("⚠️  CHAINABLE ATTACK PATHS DETECTED")
        print("These gaps can be chained for multi-step exploits (like Mythos does):")
        print()
        for finding in report.chainable[:10]:
            print(f"  • {finding.conjecture_source} → {finding.conjecture_target}")
            print(f"    Type: {finding.vulnerability.vuln_class}")
            print(f"    Severity: {finding.combined_severity:.2f}")
            print()

    # Threat intelligence enrichment
    if report.findings:
        print("Enriching with threat intelligence...")
        threat_intel = cyber_bridge.enrich_findings(report.findings[:20])

        print()
        print("Attack Chain Predictions (top 5):")
        for i, intel in enumerate(threat_intel[:5], 1):
            if intel.attack_chains:
                print(f"\n{i}. {intel.gap_finding.vulnerability.vuln_class}")
                for chain in intel.attack_chains[:2]:
                    print(f"   → {chain}")

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    if detection_rate >= 80:
        print("✓ STRESS TEST PASSED")
        print(f"  Gray coherence defense detected {detection_rate:.1f}% of Mythos-style attacks")
        print("  System is effective against known attack patterns")
    elif detection_rate >= 50:
        print("⚠ STRESS TEST PARTIAL")
        print(f"  Detected {detection_rate:.1f}% - needs tuning")
    else:
        print("✗ STRESS TEST FAILED")
        print(f"  Only detected {detection_rate:.1f}% - significant gaps in defense")

    print()
    print("Recommendations:")
    print("  1. Review missed patterns and improve gap classification heuristics")
    print("  2. Test against real-world CVEs from Mythos findings")
    print("  3. Continuous scan mode to race Mythos to new gaps")
    print("  4. Integrate with Glasswing partners for validation")


if __name__ == "__main__":
    asyncio.run(run_stress_test())
