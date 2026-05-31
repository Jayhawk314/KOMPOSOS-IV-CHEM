import sys
from pathlib import Path
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

print("=== UI & CORE CHEMICAL FEATURES AUDIT ===")

def test_unified_service():
    print("\n--- Testing Unified Compatibility Service ---")
    try:
        from oracle.compatibility_service import run_compatibility_workflow
        print("✓ run_compatibility_workflow function located in compatibility_service.")
        return True
    except ImportError as e:
        print(f"✗ Failed to locate compatibility service: {e}")
        return False

def test_stt_strategies():
    print("\n--- Testing Simplicial Type Theory Strategies ---")
    try:
        from oracle.simplicial_strategies import SimplicialYonedaStrategy, FibrationTransportStrategy
        print("✓ Simplicial strategies (SimplicialYonedaStrategy, FibrationTransportStrategy) located.")
        return True
    except ImportError as e:
        print(f"✗ Failed to locate STT strategies: {e}")
        return False

def test_mof_designer_components():
    print("\n--- Testing MOF Designer Constraints ---")
    try:
        mof_dir = ROOT / "mof_bridge"
        if mof_dir.exists() and any(mof_dir.iterdir()):
             print("✓ mof_bridge directory located and populated.")
             return True
        else:
             print("✗ mof_bridge directory missing or empty.")
             return False
    except Exception as e:
        print(f"✗ Error checking MOF Bridge: {e}")
        return False

def test_ui_routing():
    print("\n--- Testing UI Page Definitions ---")
    ui_pages = ROOT / "streamlit_app/pages"
    if ui_pages.exists():
        files = [f.name for f in ui_pages.iterdir() if f.is_file() and f.name.endswith(".py")]
        expected = ["1_Compatibility_Checker.py", "2_PFAS_Scanner.py", "5_Crystal_Dreamer.py", "8_MOF_Designer.py"]
        found = [e for e in expected if any(e in f for f in files)]
        
        if found:
             print(f"✓ Found key UI pages: {', '.join(found)}")
             return True
        else:
             print(f"✗ Could not find expected UI pages in {ui_pages}")
             print(f"  Available: {files}")
             return False
    else:
        print("✗ UI pages directory not found.")
        return False

if __name__ == "__main__":
    success = 0
    total = 4
    
    if test_unified_service(): success += 1
    if test_stt_strategies(): success += 1
    if test_mof_designer_components(): success += 1
    if test_ui_routing(): success += 1
    
    print(f"\n=== UI AUDIT SUMMARY: {success}/{total} UI/CORE COMPONENTS VERIFIED ===")
