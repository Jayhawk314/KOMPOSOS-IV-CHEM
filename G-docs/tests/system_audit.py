"""
KOMPOSOS-IV-CHEM System Audit
Verifies the architectural mandates and feature coverage.
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

def audit_report():
    print("="*60)
    print("KOMPOSOS-IV-CHEM ARCHITECTURAL AUDIT")
    print("="*60)

    # 1. Core Runtime
    print("\n[1] CORE RUNTIME CHECK")
    core_files = ["core/cosmos.py", "core/bridge.py", "optimus_core.py"]
    for f in core_files:
        status = "✓" if (ROOT / f).exists() else "✗"
        print(f"  {status} {f}")

    # 2. Domain Bridges
    print("\n[2] DOMAIN BRIDGE COVERAGE")
    bridges = [
        "battery_bridge", "polymer_bridge", "metal_bridge", 
        "ceramic_bridge", "glass_bridge", "mof_bridge", 
        "semiconductor_bridge", "molecular_bridge", "pfas_bridge"
    ]
    for b in bridges:
        status = "✓" if (ROOT / b).exists() else "✗"
        print(f"  {status} {b}")

    # 3. Features & UI
    print("\n[3] UI FEATURE MAPPING")
    ui_app = ROOT / "streamlit_app/app.py"
    if ui_app.exists():
        with open(ui_app, 'r', encoding='utf-8') as f:
            content = f.read()
            features = [
                "Compatibility Checker", "PFAS Scanner", "Composition Predictor",
                "Cell Designer", "Crystal Dreamer", "MP Explorer",
                "MOF Explorer", "MOF Designer", "Discovery Workbench"
            ]
            for feat in features:
                status = "✓" if feat in content else "✗"
                print(f"  {status} {feat}")
    else:
        print("  ✗ streamlit_app/app.py not found")

    # 4. Math & AIMO
    print("\n[4] MATHEMATICAL REASONING (AIMO)")
    aimo_root = ROOT / "aimo"
    if aimo_root.exists():
        print(f"  ✓ aimo/ directory present")
        solver = aimo_root / "komposos_solver.py"
        print(f"  {'✓' if solver.exists() else '✗'} komposos_solver.py (AIMO interface)")
    else:
        print("  ✗ aimo/ directory missing")

    # 5. Data & Verification
    print("\n[5] DATA & VERIFICATION")
    zfc = ROOT / "zfc"
    print(f"  {'✓' if zfc.exists() else '✗'} zfc/ (Dual-Engine Logic)")
    
    comp_engine = ROOT / "composition_engine"
    print(f"  {'✓' if comp_engine.exists() else '✗'} composition_engine/ (Local Database)")

    print("\n" + "="*60)
    print("AUDIT COMPLETE")
    print("="*60)

if __name__ == "__main__":
    audit_report()
