#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Quick validation that Mythos defense detects privilege escalation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.category import Category
from core.gray_coherence import GrayCategoryLayer, TwoCellProxy, CoherenceGapType

print("MYTHOS DEFENSE - Quick Validation")
print("=" * 60)
print()

# Simulate Mythos-style privilege escalation attack
print("Test: Linux kernel privilege escalation (Mythos found this)")
print("-" * 60)

# Build Category
category = Category(db_path=":memory:")

# Add objects representing privilege levels
category.add("user_code")        # Ring 3 - user space
category.add("kernel_code")      # Ring 0 - kernel space
category.add("intermediate")     # Should exist but doesn't

# Add morphisms
category.connect("user_code", "kernel_code", "exploit_path", confidence=0.3)  # Gap!
category.connect("user_code", "intermediate", "safe_syscall", confidence=0.9)
category.connect("intermediate", "kernel_code", "validated_transition", confidence=0.95)

print("Category built:")
print(f"  Objects: {len(list(category.objects()))}")
print(f"  Morphisms: {len(list(category.morphisms()))}")
print()

# Create Gray category layer
gray = GrayCategoryLayer(category)

# Create TwoCellProxy pair simulating the attack
# Alpha: the exploit path (low confidence - structural gap)
alpha = TwoCellProxy(
    source_morphism="user_code",
    target_morphism="kernel_code",
    label="exploit_direct_path",
    confidence=0.3,
    privilege_level=0,  # User
)

# Beta: the required safe path (should exist)
beta = TwoCellProxy(
    source_morphism="user_code",
    target_morphism="kernel_code",
    label="safe_validated_path",
    confidence=0.95,
    privilege_level=2,  # Kernel - crosses privilege boundary
)

print("Checking 3-cell coherence...")
modification = gray.check_modification_coherence(alpha, beta)

print()
if not modification.is_coherent:
    print("[SUCCESS] VULNERABILITY DETECTED!")
    print(f"  Gap Type: {modification.gap_type.value}")
    print(f"  Location: {modification.gap_location}")

    # Map to vulnerability
    from core.gray_coherence import CoherenceVulnerabilityMapper
    mapper = CoherenceVulnerabilityMapper()
    vuln = mapper.classify(modification, location="kernel_transition")

    print()
    print(f"  Vulnerability Class: {vuln.vuln_class}")
    print(f"  Severity: {vuln.severity:.2f}")
    print(f"  MITRE ATT&CK: {vuln.mitre_id}")
    print(f"  Chainable: {'Yes - Mythos would exploit this!' if vuln.is_chainable else 'No'}")
    print()
    print(f"  Remediation: {vuln.remediation}")
    print()
    print("[SUCCESS] DEFENSE WORKING - Gap found before Mythos could exploit it!")
else:
    print("[FAILED] System appears coherent (no vulnerability detected)")

print()
print("=" * 60)
