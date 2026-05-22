#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Download 22-Atom MOF Linkers from Materials Project
=====================================================

CLI tool to download MOF structures, extract organic linkers,
and cache 22-atom molecules to SQLite.

Usage:
    python scripts/download_mof_linkers.py --api-key YOUR_MP_API_KEY
    python scripts/download_mof_linkers.py --api-key YOUR_KEY --include-unstable

Pattern follows: scripts/download_mp_data.py
"""

import sys
from pathlib import Path

# Add project root to path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import argparse
from mof_bridge.mp_mof_loader import MOFLinkerCache


def main():
    parser = argparse.ArgumentParser(
        description="Download 22-atom MOF linkers from Materials Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download stable MOFs only
  python scripts/download_mof_linkers.py --api-key YOUR_KEY

  # Include unstable MOFs
  python scripts/download_mof_linkers.py --api-key YOUR_KEY --include-unstable

  # Test with limited set
  python scripts/download_mof_linkers.py --api-key YOUR_KEY --max-mofs 100

Notes:
  - Requires mp-api, rdkit, pymatgen (pip install mp-api rdkit pymatgen)
  - API key from https://materialsproject.org/api
  - Downloaded data cached to data/cache/mof_linkers/
  - After download, linkers can be loaded without API key
        """
    )

    parser.add_argument(
        "--api-key",
        required=True,
        help="Materials Project API key (get from https://materialsproject.org/api)"
    )
    parser.add_argument(
        "--include-unstable",
        action="store_true",
        help="Include unstable MOFs (energy_above_hull > 0.1 eV/atom)"
    )
    parser.add_argument(
        "--max-mofs",
        type=int,
        help="Maximum number of MOFs to process (for testing)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing cache without prompting"
    )

    args = parser.parse_args()

    # Initialize cache
    cache = MOFLinkerCache()

    print("="*70)
    print("KOMPOSOS-MOF Linker Downloader")
    print("="*70)
    print(f"Cache directory: {cache.cache_dir}")
    print(f"Include unstable: {args.include_unstable}")
    if args.max_mofs:
        print(f"Max MOFs: {args.max_mofs}")
    print("="*70)
    print()

    # Check if cache already exists
    if cache.is_available() and not args.force:
        count = cache.entry_count()
        print(f"WARNING: Cache already exists with {count} linkers.")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    elif cache.is_available() and args.force:
        count = cache.entry_count()
        print(f"Overwriting existing cache ({count} linkers)...")

    # Download
    try:
        cache.download(
            api_key=args.api_key,
            include_unstable=args.include_unstable,
            max_mofs=args.max_mofs,
        )

        print("\n" + "="*70)
        print("Download complete!")
        print("="*70)
        print(f"Total linkers: {cache.entry_count()}")
        print(f"Database: {cache.db_path}")
        print(f"Metadata: {cache.meta_path}")
        print()
        print("To load linkers:")
        print("  from mof_bridge.mp_mof_loader import MOFLinkerCache")
        print("  cache = MOFLinkerCache()")
        print("  linkers = cache.load_linkers()")
        print()

    except ImportError as e:
        print(f"\nError: {e}")
        print("\nInstall required packages:")
        print("  pip install mp-api rdkit pymatgen")
        sys.exit(1)

    except Exception as e:
        print(f"\nError during download: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
