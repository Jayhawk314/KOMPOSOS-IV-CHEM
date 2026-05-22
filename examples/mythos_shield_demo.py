#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins / Komposos-Labs

"""
Mythos Shield Demo - Basic Vulnerability Scanning

Demonstrates the Gray coherence-based defense against Anthropic's Mythos model.

This shows how KOMPOSOS-IV finds structural vulnerabilities (3-cell coherence gaps)
that Mythos would exploit, before Mythos finds them.

Mathematical basis:
- Gray-category 3-cells: modifications between 2-cells
- When interchange law fails → structural vulnerability
- Gap types map directly to CVE classes (privilege escalation, sandbox escape, etc.)

Usage:
    python examples/mythos_shield_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.category import Category
from core.gray_coherence_bridge import build_shield
from oracle import CategoricalOracle
from data.embeddings import EmbeddingsEngine


async def main():
    print("=" * 70)
    print("MYTHOS SHIELD - Gray Coherence Defense Demo")
    print("=" * 70)
    print()

    # Initialize Category
    print("[1/4] Initializing Category...")
    category = Category(db_path=":memory:")

    # Build a sample software category (simulating a codebase)
    print("[2/4] Building software category from sample code...")

    # Example: Simple privilege escalation vulnerability
    category.add("user_read_config")
    category.add("admin_write_config")
    category.add("kernel_execute")

    # Valid composition: user → admin (via sudo)
    category.connect(
        "user_read_config",
        "admin_write_config",
        "sudo_escalate",
        confidence=0.9
    )

    # Invalid composition: user → kernel (privilege gap)
    category.connect(
        "user_read_config",
        "kernel_execute",
        "exploit_path",
        confidence=0.2  # Low confidence = structural gap
    )

    # Initialize embeddings
    print("[3/4] Initializing embeddings engine...")
    embeddings = EmbeddingsEngine()

    # Build Oracle
    oracle = CategoricalOracle(category, embeddings)

    # Build MythosShield
    print("[4/4] Building MythosShield...")
    shield = build_shield(oracle, category=category)

    print()
    print("=" * 70)
    print("SCANNING FOR VULNERABILITIES")
    print("=" * 70)
    print()

    # Run scan
    report = shield.scan(
        top_k=50,  # Evaluate top 50 conjectures
        min_confidence=0.3,
        hollow_only=True  # Only HOLLOW verdicts (CAT yes, ZFC no)
    )

    # Print report
    shield.print_report(report)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total gaps found: {len(report.findings)}")
    print(f"Critical gaps: {len(report.critical)}")
    print(f"Chainable gaps (Mythos target): {len(report.chainable)}")
    print()

    if report.chainable:
        print("⚠️  CHAINABLE VULNERABILITIES DETECTED")
        print("These are the gaps Mythos would chain together.")
        print("Patching ANY ONE of these breaks the chain.")
        print()
        for finding in report.chainable[:5]:
            print(f"  - {finding.conjecture_source} → {finding.conjecture_target}")
            print(f"    Type: {finding.vulnerability.vuln_class}")
            print(f"    Fix: {finding.vulnerability.remediation}")
            print()

    print("Scan complete. See report above for detailed findings.")


if __name__ == "__main__":
    asyncio.run(main())
