#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial

"""Import pre-extracted MOF linker datasets into the KOMPOSOS cache.

Examples:
  python scripts/import_linker_dataset.py data/linkers.csv --source-name core-mof
  python scripts/import_linker_dataset.py data/linkers.json --source-name lse
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import argparse

from mof_bridge.mp_mof_loader import MOFLinkerCache


def main():
    parser = argparse.ArgumentParser(
        description="Import a pre-extracted linker CSV/JSON into the MOF linker cache.",
    )
    parser.add_argument(
        "dataset",
        help="Path to a CSV or JSON file containing linker SMILES",
    )
    parser.add_argument(
        "--source-name",
        help="Human-readable source label for metadata (e.g. core-mof-2025, lse)",
    )
    parser.add_argument(
        "--heavy-atoms",
        type=int,
        default=22,
        help="Exact heavy atom count to keep (default: 22)",
    )
    args = parser.parse_args()

    cache = MOFLinkerCache()
    summary = cache.import_linker_dataset(
        dataset_path=args.dataset,
        source_name=args.source_name,
        exact_heavy_atoms=args.heavy_atoms,
    )

    print("=" * 70)
    print("KOMPOSOS Pre-Extracted Linker Import")
    print("=" * 70)
    print(f"Dataset: {args.dataset}")
    print(f"Imported: {summary['imported']}")
    print(f"Records seen: {summary['records_seen']}")
    print(f"Skipped missing SMILES: {summary['skipped_missing_smiles']}")
    print(f"Skipped invalid SMILES: {summary['skipped_invalid_smiles']}")
    print(f"Skipped wrong heavy atom count: {summary['skipped_wrong_size']}")
    print(f"Cache DB: {cache.db_path}")
    print(f"Metadata: {cache.meta_path}")


if __name__ == "__main__":
    main()
