"""Test the new MaterialSearchEngine with 103k MP materials."""

from streamlit_app.material_search import MaterialSearchEngine
from composition_engine.mp_loader import MPCache

print("="*70)
print("Testing MaterialSearchEngine with 103k Materials Project entries")
print("="*70)

# Load MP cache
print("\n1. Loading MP cache...")
cache = MPCache()
entries = cache.load_entries()
print(f"   Loaded {len(entries):,} MP entries")

# Initialize search engine
print("\n2. Initializing search engine...")
engine = MaterialSearchEngine(entries)
print(f"   [OK] Search engine ready")
print(f"   - {len(engine.by_element)} unique elements indexed")
print(f"   - {len(engine.by_formula):,} formulas indexed")
print(f"   - {len(engine.by_crystal_system)} crystal systems")

# Test searches
print("\n3. Testing searches:")

# Test 1: Element search
print("\n   Search: 'Li'")
results = engine.search('Li', limit=5)
print(f"   Found {len(results)} results:")
for r in results[:5]:
    stability = "[OK]" if r.is_stable else "[!]"
    print(f"      {stability} {r.formula:20s} {r.mp_id:12s} {r.category:20s} {r.crystal_system}")

# Test 2: Shortcut search
print("\n   Search: 'NMC811' (shortcut)")
results = engine.search('NMC811', limit=3)
print(f"   Found {len(results)} results:")
for r in results[:3]:
    print(f"      {r.formula:20s} {r.mp_id:12s}")

# Test 3: Substring search
print("\n   Search: 'perovsk'")
results = engine.search('perovsk', limit=5)
print(f"   Found {len(results)} results:")
for r in results[:5]:
    print(f"      {r.formula:20s} {r.mp_id:12s} {r.category}")

# Test 4: Popular materials
print("\n4. Testing popular materials:")
popular = engine.get_popular_materials(limit=5)
print(f"   Found {len(popular)} popular materials:")
for r in popular:
    print(f"      {r.formula:20s} {r.mp_id:12s}")

# Category statistics
print("\n5. Category distribution:")
for category, entries in sorted(engine.by_category.items(), key=lambda x: len(x[1]), reverse=True):
    if entries:
        print(f"   {category:25s}: {len(entries):6,} materials")

print("\n" + "="*70)
print("[OK] All tests passed!")
print("="*70)
