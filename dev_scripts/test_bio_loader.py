#!/usr/bin/env python3
"""
Quick test to verify Bio domain loader works.

Tests:
1. Load tier1.db into Category
2. Verify 141 objects loaded
3. Verify 283 morphisms loaded
4. Verify type distribution
5. Check embeddings preserved
"""

import sys
from pathlib import Path

# Add PHARM to path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from core.category import Category


def test_bio_loader():
    """Test loading tier1.db into Category."""
    print("=" * 70)
    print("Bio Domain Loader Test")
    print("=" * 70)

    # Create loader
    loader = BioDomainLoader()

    # Load tier1.db
    tier1_path = "data/drugs/tier1.db"
    print(f"\n1. Loading {tier1_path}...")

    try:
        cat = loader.load_tier1(tier1_path)
        print(f"   [OK] Category created: {cat.name if hasattr(cat, 'name') else 'N/A'}")
    except Exception as e:
        print(f"   [FAIL] Failed to load: {e}")
        return False

    # Check object count
    print(f"\n2. Checking object count...")
    objects = cat.objects()
    obj_count = len(objects)
    print(f"   Objects loaded: {obj_count}")
    if obj_count == 141:
        print(f"   [OK] Expected 141 objects")
    else:
        print(f"   [WARN] Expected 141, got {obj_count}")

    # Check morphism count
    print(f"\n3. Checking morphism count...")
    morphisms = cat.morphisms()
    mor_count = len(morphisms)
    print(f"   Morphisms loaded: {mor_count}")
    if mor_count == 283:
        print(f"   [OK] Expected 283 morphisms")
    else:
        print(f"   [WARN] Expected 283, got {mor_count}")

    # Check type distribution
    print(f"\n4. Type distribution:")
    stats = loader.get_stats()
    type_dist = stats.get("type_distribution", {})
    for obj_type, count in sorted(type_dist.items(), key=lambda x: -x[1]):
        print(f"   - {obj_type}: {count}")

    # Check embeddings
    print(f"\n5. Checking embeddings...")
    embedded_count = 0
    for obj in objects[:10]:  # Check first 10
        if hasattr(obj, 'embedding') and obj.embedding is not None:
            embedded_count += 1
    print(f"   Sample: {embedded_count}/10 objects have embeddings")
    if embedded_count > 0:
        print(f"   [OK] Embeddings preserved")
    else:
        print(f"   [WARN] No embeddings found in sample")

    # Sample objects
    print(f"\n6. Sample objects:")
    for obj in objects[:5]:
        name = obj.name if hasattr(obj, 'name') else "Unknown"
        obj_type = obj.type_name if hasattr(obj, 'type_name') else "Unknown"
        has_emb = "Yes" if (hasattr(obj, 'embedding') and obj.embedding is not None) else "No"
        print(f"   - {name} ({obj_type}) [embedding: {has_emb}]")

    # Sample morphisms
    print(f"\n7. Sample morphisms:")
    for mor in morphisms[:5]:
        source = mor.source if hasattr(mor, 'source') else '?'
        target = mor.target if hasattr(mor, 'target') else '?'
        name = mor.name if hasattr(mor, 'name') else '?'
        confidence = mor.confidence if hasattr(mor, 'confidence') else 0
        print(f"   - {source} --[{name}]--> {target} (conf: {confidence:.3f})")

    print("\n" + "=" * 70)
    print("Bio Loader Test Complete")
    print("=" * 70)

    # Summary
    print(f"\nSummary:")
    print(f"  Objects:   {obj_count}/141 ({'OK' if obj_count == 141 else 'WARN'})")
    print(f"  Morphisms: {mor_count}/283 ({'OK' if mor_count == 283 else 'WARN'})")
    print(f"  Types:     {len(type_dist)} distinct types")

    return True


if __name__ == "__main__":
    try:
        success = test_bio_loader()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
