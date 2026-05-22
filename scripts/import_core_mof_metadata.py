#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial

"""Extract linker-like fragments from CoRE MOF metadata and import them.

This script uses the `mofid-v1` field found in CoRE MOF metadata JSON files.
It extracts the preamble before `MOFid-v1`, splits disconnected fragments, drops
metal-containing pieces, and keeps the largest organic component per MOF.

It is heuristic, not a full linker decomposition pipeline, but it is enough to
seed the KOMPOSOS linker cache from real CoRE MOF metadata without CIF parsing.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import argparse
import json

from rdkit import Chem

from mof_bridge.mp_mof_loader import MOFLinkerCache


METAL_SYMBOLS = {
    "Li", "Na", "K", "Rb", "Cs", "Fr",
    "Be", "Mg", "Ca", "Sr", "Ba", "Ra",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy",
    "Ho", "Er", "Tm", "Yb", "Lu",
    "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf",
    "Es", "Fm", "Md", "No", "Lr",
    "Al", "Ga", "In", "Sn", "Tl", "Pb", "Bi", "Po",
    "B", "Si", "Ge", "As", "Sb", "Te",
}


def extract_fragments(mofid_v1: str) -> list[str]:
    """Return all organic non-metal fragments from mofid-v1 text."""
    prefix = mofid_v1.split(" MOFid-v1", 1)[0].strip()
    if not prefix:
        return []

    fragments = []
    for part in prefix.split("."):
        part = part.strip()
        if not part or part == "*":
            continue
        mol = Chem.MolFromSmiles(part)
        if not mol:
            continue

        elements = {atom.GetSymbol() for atom in mol.GetAtoms()}
        if "C" not in elements:
            continue
        if elements & METAL_SYMBOLS:
            continue

        fragments.append(Chem.MolToSmiles(mol))

    return list(dict.fromkeys(fragments))


def main():
    parser = argparse.ArgumentParser(
        description="Import 22-heavy-atom linker candidates from CoRE MOF metadata JSON.",
    )
    parser.add_argument(
        "metadata_json",
        help="Path to CoRE MOF metadata JSON such as CR_meta_data_SI.json",
    )
    parser.add_argument(
        "--source-name",
        default="core-mof-metadata",
        help="Source label stored in cache metadata",
    )
    parser.add_argument(
        "--heavy-atoms",
        type=int,
        default=22,
        help="Exact heavy atom count to keep (default: 22)",
    )
    parser.add_argument(
        "--intermediate-json",
        help="Optional path to save extracted linker records before import",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append into the existing linker cache instead of resetting it",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.metadata_json).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected top-level dict for CoRE metadata JSON")

    extracted_records = []
    scanned = 0
    extracted = 0
    for mof_id, record in payload.items():
        scanned += 1
        mofid_v1 = record.get("id", {}).get("mofid-v1", "")
        if not mofid_v1:
            continue
        fragments = extract_fragments(mofid_v1)
        if not fragments:
            continue
        extracted += len(fragments)
        for idx, smiles in enumerate(fragments):
            extracted_records.append({
                "mof_id": f"{mof_id}#frag{idx+1}",
                "linker_smiles": smiles,
            })

    if args.intermediate_json:
        Path(args.intermediate_json).write_text(
            json.dumps(extracted_records, indent=2),
            encoding="utf-8",
        )

    cache = MOFLinkerCache()
    summary = cache.import_linker_dataset(
        dataset_path=args.intermediate_json or _write_temp_json(extracted_records),
        source_name=args.source_name,
        exact_heavy_atoms=args.heavy_atoms,
        reset=not args.append,
    )

    print("=" * 70)
    print("KOMPOSOS CoRE MOF Metadata Import")
    print("=" * 70)
    print(f"Metadata file: {args.metadata_json}")
    print(f"MOFs scanned: {scanned}")
    print(f"Organic fragments extracted: {extracted}")
    print(f"Imported exact-{args.heavy_atoms} linkers: {summary['imported']}")
    print(f"Skipped invalid SMILES: {summary['skipped_invalid_smiles']}")
    print(f"Skipped wrong heavy atom count: {summary['skipped_wrong_size']}")
    print(f"Total cache rows: {summary['total_cache_rows']}")
    print(f"Cache DB: {cache.db_path}")


def _write_temp_json(records: list[dict]) -> str:
    """Persist extracted records to a stable temporary file inside the repo."""
    temp_path = Path("data/external/core_mof/extracted_linkers_from_metadata.json")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return str(temp_path)


if __name__ == "__main__":
    main()
