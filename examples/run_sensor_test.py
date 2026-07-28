# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import sys
import asyncio
from pathlib import Path

# Ensure we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gray_coherence import MythosRace, CoherenceGapType

async def run_mythos_sensor_test():
    print("=" * 60)
    print("RUNNING MYTHOS SENSOR VALIDATION")
    print("Target: mythos_victim.py")
    print("=" * 60)
    
    # Initialize the scanner
    race = MythosRace()
    
    # Scan the victim file
    # The upgraded SoftwareCategoryBuilder will:
    # 1. Detect os.system and subprocess.Popen as sinks (Confidence 0.2-0.3)
    # 2. Infer admin_root_handler as Privilege 2 (root/kernel)
    # 3. Detect the parallel paths in bypass_logic
    findings = race.scan_path("KOMPOSOS-IV/examples/mythos_victim_direct.py")
    
    print(f"\nScan complete. Found {len(findings)} vulnerability candidates.\n")
    
    if not findings:
        print("[FAIL] Sensors missed the vulnerabilities.")
        return
    
    for c in findings:
        print(f"[{c.gap_type.value}] Severity: {c.severity:.2f}")
        print(f"  Class: {c.vuln_class}")
        print(f"  MITRE: {c.mitre_id}")
        print(f"  Description: {c.description}")
        print(f"  Remediation: {c.remediation}\n")
        
    # Check if we caught the big ones
    gap_types = [c.gap_type for c in findings]
    if CoherenceGapType.FUNCTOR_ESCAPE in gap_types or CoherenceGapType.PRIVILEGE_NON_COMMUTE in gap_types:
        print("[SUCCESS] The new sensors autonomously detected the Mythos exploit chain!")
    else:
        print("[PARTIAL] Found gaps, but not the expected critical ones.")

if __name__ == "__main__":
    asyncio.run(run_mythos_sensor_test())
