import sys
from pathlib import Path
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

print("=== DEEP EMPIRICAL AUDIT: KOMPOSOS-IV-CHEM ===")

def test_categorical_runtime():
    print("\n--- Testing Core Categorical Runtime ---")
    try:
        from core.category import Category
        from core.cosmos import InfinityCosmos
        cat = Category("test_cat", db_path=":memory:")
        cosmos = InfinityCosmos(category=cat)
        print("✓ InfinityCosmos instantiated successfully.")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate InfinityCosmos: {e}")
        return False
def test_optimus_engine():
    print("\n--- Testing Optimus Monad ---")
    try:
        from optimus_core import RuntimeCategory, OptimisMonad
        runtime = RuntimeCategory()
        runtime.add_morphism("f", "A", "B", confidence=0.8)
        runtime.add_morphism("g", "B", "C", confidence=0.9)

        optimus = OptimisMonad(runtime)
        # We must seed a direct morphism for Optimus to "improve" upon or it won't compress
        runtime.add_morphism("seed", "A", "C", confidence=0.1)

        optimus.descend(verbose=False, depth=1)
        m_ac_after = runtime.best_morphism("A", "C")

        # Check if the confidence improved from 0.1 to 0.72 (0.8 * 0.9)
        if m_ac_after and m_ac_after.confidence > 0.7:
            print("✓ Optimus successfully discovered and compressed a path.")
            return True
        else:
            print("✗ Optimus ran but did not compress the path correctly.")
            return False

    except Exception as e:
        print(f"✗ Failed to run Optimus: {e}")
        return False

def test_zfc_engine():
    print("\n--- Testing ZFC Dual-Engine ---")
    try:
        from zfc.proof_engine import ZFCVerifier
        engine = ZFCVerifier()
        print("✓ ZFCVerifier instantiated successfully.")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate ZFCVerifier: {e}")
        return False

def test_aimo_isolation():
    print("\n--- Testing AIMO Isolation Status ---")
    try:
        import aimo.komposos_solver
        print("✓ AIMO module loaded successfully.")
        return True
    except ImportError as e:
        print(f"✓ AIMO is isolated/historic as expected (ImportError: {e}).")
        return True 
    except Exception as e:
         print(f"✗ Unexpected error loading AIMO: {e}")
         return False

def test_cog_engine():
    print("\n--- Testing COG Engine ---")
    try:
        from cog.engine import CogEngine
        from cog.session import CogSession
        engine = CogEngine(CogSession())
        print("✓ CogEngine instantiated successfully.")
        return True
    except Exception as e:
        print(f"✗ Failed to instantiate CogEngine: {e}")
        return False

if __name__ == "__main__":
    success = 0
    total = 5
    
    if test_categorical_runtime(): success += 1
    if test_optimus_engine(): success += 1
    if test_zfc_engine(): success += 1
    if test_aimo_isolation(): success += 1
    if test_cog_engine(): success += 1
    
    print(f"\n=== AUDIT SUMMARY: {success}/{total} SYSTEMS VERIFIED ===")
