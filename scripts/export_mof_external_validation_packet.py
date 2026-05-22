"""Export a MOF linker packet for external molSimplify/DFT validation.

The output intentionally includes blank external-result columns. KOMPOSOS
scores are inputs to the audit, not labels to be optimized against.
"""

import argparse
import csv
import hashlib
from pathlib import Path


EXTERNAL_COLUMNS = [
    "external_partner",
    "metal_node",
    "target_topology",
    "molsimplify_build_status",
    "molsimplify_structure_id",
    "dft_code",
    "functional",
    "basis_or_pseudopotential",
    "charge_state",
    "spin_state",
    "relaxation_status",
    "final_energy_eV",
    "formation_energy_eV",
    "max_force_eV_A",
    "imaginary_frequency_count",
    "external_verdict",
    "external_notes",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_packet(input_csv: Path, output_csv: Path, count: int) -> Path:
    with input_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"No rows found in {input_csv}")

    selected = rows[:count]
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    base_columns = [
        "packet_id",
        "candidate_id",
        "source_file",
        "selection_policy",
        "komposos_rank",
        "SMILES",
        "formula",
        "heavy_atoms",
        "MW",
        "N_count",
        "O_count",
        "S_count",
        "morphism_integrity",
        "zfc_constraints_passed",
        "synthesizability_score",
        "toxicity_score",
        "stability_score",
        "activity_score",
        "conductivity_score",
        "overall_viable",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=base_columns + EXTERNAL_COLUMNS)
        writer.writeheader()
        for idx, row in enumerate(selected, 1):
            packet_row = {
                "packet_id": "mof_linker_external_validation_2026_q2",
                "candidate_id": f"MOFEXT2026Q2-{idx:03d}",
                "source_file": str(input_csv),
                "selection_policy": "top ranked KOMPOSOS 22-heavy-atom AGREE candidates; external columns intentionally blank",
                "komposos_rank": row.get("rank", idx),
                "SMILES": row.get("SMILES", ""),
                "formula": row.get("formula", ""),
                "heavy_atoms": row.get("heavy_atoms", ""),
                "MW": row.get("MW", ""),
                "N_count": row.get("N_count", ""),
                "O_count": row.get("O_count", ""),
                "S_count": row.get("S_count", ""),
                "morphism_integrity": row.get("morphism_integrity", ""),
                "zfc_constraints_passed": row.get("zfc_constraints_passed", ""),
                "synthesizability_score": row.get("synthesizability_score", ""),
                "toxicity_score": row.get("toxicity_score", ""),
                "stability_score": row.get("stability_score", ""),
                "activity_score": row.get("activity_score", ""),
                "conductivity_score": row.get("conductivity_score", ""),
                "overall_viable": row.get("overall_viable", ""),
            }
            for col in EXTERNAL_COLUMNS:
                packet_row[col] = ""
            writer.writerow(packet_row)

    manifest_path = output_csv.with_suffix(".sha256")
    manifest_path.write_text(f"{_sha256(output_csv)}  {output_csv.name}\n", encoding="utf-8")
    return output_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a 50-linker external validation packet.")
    parser.add_argument("--input", type=Path, default=Path("kulik_22atom_linkers_100.csv"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit/external_blind/mof_linker_validation_2026_q2.csv"),
    )
    parser.add_argument("--count", type=int, default=50)
    args = parser.parse_args()

    output = export_packet(args.input, args.output, args.count)
    print(f"Exported {args.count} candidates to {output}")
    print(f"SHA256 manifest: {output.with_suffix('.sha256')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
