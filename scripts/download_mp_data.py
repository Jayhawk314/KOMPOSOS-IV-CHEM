#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Download Materials Project Data

One-time download script. This is the ONLY place that requires mp-api.
After running, the cached data is used by the composition engine without
needing mp-api installed.

Prerequisites:
    pip install mp-api

Usage:
    export MP_API_KEY="your_key_here"
    python scripts/download_mp_data.py                    # Stable only (~154K)
    python scripts/download_mp_data.py --include-unstable  # All (~170K+)

Get an API key at: https://materialsproject.org/api
"""

import argparse
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from composition_engine.mp_loader import MPCache


def main():
    parser = argparse.ArgumentParser(
        description="Download Materials Project data for KOMPOSOS composition engine"
    )
    parser.add_argument(
        "--api-key",
        help="Materials Project API key (default: MP_API_KEY env var)",
        default=None,
    )
    parser.add_argument(
        "--include-unstable",
        action="store_true",
        help="Include materials above the convex hull (adds ~16K entries)",
    )
    parser.add_argument(
        "--cache-dir",
        help="Override default cache directory",
        default=None,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    cache = MPCache(cache_dir=args.cache_dir) if args.cache_dir else MPCache()

    if cache.is_available():
        existing = cache.entry_count()
        print(f"Existing cache found: {existing} entries")
        response = input("Overwrite? [y/N] ").strip().lower()
        if response != 'y':
            print("Aborted.")
            return

    try:
        count = cache.download(
            api_key=args.api_key,
            include_unstable=args.include_unstable,
        )
        print(f"\nDownload complete: {count} materials cached")
        print(f"Cache location: {cache.cache_dir}")
        print("\nVerify with:")
        print('  python -c "from composition_engine.mp_loader import MPCache; '
              'c = MPCache(); print(f\'Available: {c.is_available()}, '
              'Count: {c.entry_count()}\')"')

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nInstall mp-api first:")
        print("  pip install mp-api")
        sys.exit(1)

    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}")
        logging.exception("Download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
