# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import sys
import asyncio
from pathlib import Path

# Ensure we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gray_coherence import SoftwareCategoryBuilder
from categorical.presheaf_topos import PresheafTopos
from cyber.topos_detector import ToposDetector

async def run_mythos_sovereign_test():
    print("=" * 80)
    print("MYTHOS SOVEREIGN: TOPOS-BASED LOGIC BYPASS DETECTION")
    print("Target: Threshold Bypass (Claude Code CVE-2026 Style)")
    print("=" * 80)

    # 1. Build the Software Category
    builder = SoftwareCategoryBuilder().from_source_file("KOMPOSOS-IV/examples/mythos_sovereign_victim.py")
    
    # NEW: Move builder data into a real Category object
    from core.category import Category
    cat = Category(db_path=":memory:")
    for obj_name, obj in builder.objects.items():
        cat.add(obj_name)
    for m in builder.morphisms:
        cat.connect(m.source, m.target, m.label, confidence=m.confidence)

    # 2. Lift to Presheaf Topos
    # This activates the Subobject Classifier math
    topos = PresheafTopos.from_enriched_category(cat)
    detector = ToposDetector(topos)
    
    # 3. Analyze 'executive_sink' Truth Values
    # We assess the threat to 'os.system' from the perspective of 'executive_sink'
    target = "os.system"
    assessments = detector.assess_threat(["mythos_sovereign_victim.executive_sink"])
    
    print(f"\n[Topos Audit] Analyzing Object: {target}")
    
    # 4. Multi-Perspective Truth Analysis
    # In a safe system, the 'Truth Value' of the security check should be 1.0.
    # If a bypass exists, the sieve Truth Value will collapse.
    found_collapse = False
    for assessment in assessments:
        if assessment.technique_id == target:
            print(f"  Perspective: {assessment.supporting_perspectives}")
            print(f"  Sieve Truth Value: {assessment.truth_value:.4f}")
            print(f"  Confidence: {assessment.confidence_level}")
            print(f"  Intuitionistic Note: {assessment.intuitionistic_note}")
            
            # THE DETECTION: A Truth Value < 1.0 on a sensitive sink 
            # while inside a supposedly 'Safe' executive function 
            # indicates a Subobject Classifier Failure (Sieve Collapse).
            if assessment.truth_value < 1.0:
                found_collapse = True
                print(f"\n[DETECTED] SIEVE COLLAPSE (Logic Bypass)")
                print(f"  Reason: The Sieve on {target} is not maximal.")
                print(f"  Mathematical Proof: chi_Security({target}) < 1.0")
                print(f"  Remediation: Ensure security morphisms cover ALL complexity branches.")

    print("\n" + "=" * 80)
    if found_collapse:
        print("[RESULT] SUCCESS: Topos-Logic autonomously identified the complexity bypass.")
    else:
        print("[RESULT] FAILED: The bypass was not detected by the topos layer.")

if __name__ == "__main__":
    asyncio.run(run_mythos_sovereign_test())
