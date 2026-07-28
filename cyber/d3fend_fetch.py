# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
D3FEND Cache Fetcher

Standalone script to populate the local D3FEND cache.
This is the ONLY code that makes network calls to the D3FEND API.

Usage:
    python -m cyber.d3fend_fetch            # Fetch all techniques
    python -m cyber.d3fend_fetch --force     # Force refresh even if cache exists
    python -m cyber.d3fend_fetch --check     # Check cache status only
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cyber.d3fend_mapper import D3FENDCache, D3FENDMapper, CACHE_FILE
from cyber.stealth_scoring import StealthScorer, TECHNIQUE_DETECTION_MAP


def progress(current: int, total: int, technique_id: str):
    """Print progress during fetch."""
    bar_len = 30
    filled = int(bar_len * current / total)
    bar = "=" * filled + "-" * (bar_len - filled)
    print(f"\r  [{bar}] {current}/{total} {technique_id:<15}", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Fetch D3FEND data for KOMPOSOS-III")
    parser.add_argument("--force", action="store_true", help="Force refresh even if cache exists")
    parser.add_argument("--check", action="store_true", help="Check cache status only")
    args = parser.parse_args()

    cache = D3FENDCache()

    if args.check:
        data = cache.load_cache()
        if data is None:
            print("No D3FEND cache found.")
            print(f"Run 'python -m cyber.d3fend_fetch' to populate.")
        else:
            import datetime
            fetched = datetime.datetime.fromtimestamp(data.get("fetched_at", 0))
            count = data.get("technique_count", 0)
            version = data.get("version", "unknown")
            stale = cache.is_stale()
            print(f"D3FEND Cache Status:")
            print(f"  Version:    {version}")
            print(f"  Fetched:    {fetched.isoformat()}")
            print(f"  Techniques: {count}")
            print(f"  Stale:      {'Yes (>30 days)' if stale else 'No'}")
            print(f"  Path:       {cache.cache_path}")

            # Show mapping stats
            mapper = D3FENDMapper(cache)
            d3fend_map = mapper.build_detection_map()
            print(f"\nMapping Statistics:")
            print(f"  D3FEND-mapped techniques: {len(d3fend_map)}")
            print(f"  Hand-coded techniques:    {len(TECHNIQUE_DETECTION_MAP)}")

            # Count overlaps
            overlap = set(d3fend_map.keys()) & set(TECHNIQUE_DETECTION_MAP.keys())
            d3fend_only = set(d3fend_map.keys()) - set(TECHNIQUE_DETECTION_MAP.keys())
            print(f"  Overlap:                  {len(overlap)}")
            print(f"  D3FEND-only:              {len(d3fend_only)}")
        return 0

    if not args.force and not cache.is_stale():
        print("D3FEND cache is up to date. Use --force to refresh.")
        return 0

    # Collect all technique IDs from StealthScorer
    technique_ids = list(StealthScorer.TECHNIQUE_STEALTH.keys())

    # Filter out custom technique IDs (TCRYPTO_*) — not in D3FEND
    attack_ids = [tid for tid in technique_ids if tid.startswith("T") and not tid.startswith("TCRYPTO")]

    print("=" * 60)
    print("D3FEND Cache Fetcher")
    print("=" * 60)
    print(f"\nFetching D3FEND data for {len(attack_ids)} ATT&CK techniques...")
    print(f"API: https://d3fend.mitre.org/api/offensive-technique/attack/")
    print(f"Cache: {CACHE_FILE}\n")

    data = cache.fetch_all_techniques(attack_ids, progress_callback=progress)
    print()  # Newline after progress bar

    cache.save_cache(data)

    mapped = data.get("technique_count", 0)
    print(f"\nFetched: {mapped}/{len(attack_ids)} techniques have D3FEND mappings")

    # Build and display detection map
    mapper = D3FENDMapper(cache)
    d3fend_map = mapper.build_detection_map()
    print(f"Mapped to DetectionCapabilities: {len(d3fend_map)} techniques")

    # Show sample mappings
    if d3fend_map:
        print(f"\nSample mappings:")
        for tid in list(d3fend_map.keys())[:5]:
            caps = [c.name for c in d3fend_map[tid]]
            print(f"  {tid}: [{', '.join(caps)}]")

    print(f"\nCache saved to: {CACHE_FILE}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
