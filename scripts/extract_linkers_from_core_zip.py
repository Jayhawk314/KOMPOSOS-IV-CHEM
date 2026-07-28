#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Extract linker candidates directly from CoRE MOF CIF files in a ZIP archive."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import argparse
import json
import zipfile

from pymatgen.io.cif import CifParser

from mof_bridge.mp_mof_loader import MOFLinkerCache


def main():
    parser = argparse.ArgumentParser(
        description="Extract linker candidates from CoRE MOF CIFs inside a ZIP file.",
    )
    parser.add_argument("zip_path", help="Path to a CoRE MOF ZIP archive")
    parser.add_argument(
        "--max-cifs",
        type=int,
        default=200,
        help="Maximum number of CIFs to process for this run (default: 200)",
    )
    parser.add_argument(
        "--heavy-min",
        type=int,
        default=18,
        help="Minimum heavy atom count accepted from structure extraction",
    )
    parser.add_argument(
        "--heavy-max",
        type=int,
        default=26,
        help="Maximum heavy atom count accepted from structure extraction",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing cache instead of resetting it",
    )
    args = parser.parse_args()

    cache = MOFLinkerCache()
    if not args.append:
        cache._reset_cache()
    cache._init_database()

    import_count = 0
    processed = 0
    errors = 0

    intermediate = []

    with zipfile.ZipFile(args.zip_path) as zf:
        cif_names = [
            name for name in zf.namelist()
            if name.lower().endswith(".cif") and "/CR/" in name.replace("\\", "/")
        ]

        for name in cif_names:
            if processed >= args.max_cifs:
                break
            processed += 1

            try:
                with zf.open(name) as fh:
                    cif_text = fh.read().decode("utf-8", errors="ignore")
                parser = CifParser.from_str(cif_text)
                structure = parser.parse_structures(primitive=False)[0]
                smiles_list = cache._extract_linkers_from_structure(
                    structure,
                    Path(name).stem,
                )
                for idx, smiles in enumerate(smiles_list):
                    intermediate.append({
                        "mof_id": f"{Path(name).stem}#ciffrag{idx+1}",
                        "linker_smiles": smiles,
                    })
            except Exception:
                errors += 1

    temp_json = Path("data/external/core_mof/extracted_linkers_from_cif.json")
    temp_json.parent.mkdir(parents=True, exist_ok=True)
    temp_json.write_text(json.dumps(intermediate, indent=2), encoding="utf-8")

    summary = cache.import_linker_dataset(
        dataset_path=str(temp_json),
        source_name=f"core-cif:{Path(args.zip_path).stem}",
        exact_heavy_atoms=22,
        reset=not args.append,
    )
    import_count = summary["imported"]

    print("=" * 70)
    print("KOMPOSOS CoRE MOF CIF Extraction")
    print("=" * 70)
    print(f"ZIP: {args.zip_path}")
    print(f"CIFs processed: {processed}")
    print(f"CIF parse errors: {errors}")
    print(f"Extracted fragments: {len(intermediate)}")
    print(f"Imported exact-22 linkers: {import_count}")
    print(f"Total cache rows: {summary['total_cache_rows']}")
    print(f"Intermediate JSON: {temp_json}")


if __name__ == "__main__":
    main()
