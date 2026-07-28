# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Generate 100 viable 22-atom MOF linkers for Heather Kulik demo.

Outputs a CSV with SMILES, formulas, donor atom counts, and all 5 KOMPOSOS verdicts.
All linkers have exactly 22 heavy atoms and all verdicts = AGREE.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
import pandas as pd

try:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors, Descriptors
    RDKIT_AVAILABLE = True
except ImportError:
    print("Warning: RDKit not available, some features will be limited")
    RDKIT_AVAILABLE = False


def generate_kulik_linkers(num_linkers: int = 100, output_file: str = "kulik_22atom_linkers_100.csv"):
    """
    Generate exactly 100 viable 22-atom linkers with all verdicts = AGREE.

    Args:
        num_linkers: Target number of viable linkers to generate (default 100)
        output_file: Output CSV filename
    """
    print("=" * 80)
    print("KOMPOSOS MOF Linker Generator - Heather Kulik 22-Atom Challenge")
    print("=" * 80)
    print()

    # Configure screening spec
    print("Configuring screening parameters...")
    spec = LinkerScreeningSpec(
        application_context="CO2_capture",     # Good general application
        num_candidates=1000,                    # Generate many to get 100 AGREE
        require_all_agree=True,                # Only all-AGREE verdicts
        ranking_mode="morphism_integrity",     # Rank by compositional integrity
    )

    # Initialize screener and set exact atom count
    print("Initializing linker screener...")
    screener = LinkerScreener()
    screener.generator.min_atoms = 22
    screener.generator.max_atoms = 22

    print(f"Generating candidates (exact atom count: 22)...")
    print(f"Target: {num_linkers} viable linkers with all verdicts = AGREE")
    print()

    # Run screening
    result = screener.screen(spec)

    print(f"Screening complete!")
    print(f"  Total candidates evaluated: {len(result.candidates)}")
    print(f"  Viable candidates (all AGREE): {sum(1 for c in result.candidates if c.overall_viable)}")
    print()

    # Filter to viable only and take top N
    viable = [c for c in result.candidates if c.overall_viable][:num_linkers]

    if len(viable) < num_linkers:
        print(f"Warning: Only found {len(viable)} viable linkers (target was {num_linkers})")
    else:
        print(f"Selected top {len(viable)} viable linkers")

    # Build CSV data
    print()
    print("Building CSV output...")
    rows = []

    for i, c in enumerate(viable, 1):
        row_data = {
            "rank": i,
            "SMILES": c.linker_smiles,
        }

        # Add RDKit-derived properties if available
        if RDKIT_AVAILABLE:
            mol = Chem.MolFromSmiles(c.linker_smiles)
            if mol:
                row_data.update({
                    "formula": rdMolDescriptors.CalcMolFormula(mol),
                    "heavy_atoms": mol.GetNumHeavyAtoms(),
                    "MW": round(Descriptors.MolWt(mol), 2),
                    "N_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "N"),
                    "O_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "O"),
                    "S_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "S"),
                })
            else:
                row_data.update({
                    "formula": "?",
                    "heavy_atoms": 0,
                    "MW": 0,
                    "N_count": 0,
                    "O_count": 0,
                    "S_count": 0,
                })
        else:
            # Fallback without RDKit
            row_data.update({
                "formula": "N/A",
                "heavy_atoms": 22,  # We know this from generator constraints
                "MW": "N/A",
                "N_count": "N/A",
                "O_count": "N/A",
                "S_count": "N/A",
            })

        # Add KOMPOSOS verdict data
        row_data.update({
            "morphism_integrity": round(c.morphism_integrity, 4),
            "zfc_constraints_passed": c.zfc_constraints_passed,
            "synthesizability": c.verdicts["synthesizability"],
            "synthesizability_score": round(c.verdict_scores["synthesizability"], 4),
            "toxicity": c.verdicts["toxicity"],
            "toxicity_score": round(c.verdict_scores["toxicity"], 4),
            "stability": c.verdicts["stability"],
            "stability_score": round(c.verdict_scores["stability"], 4),
            "activity": c.verdicts["activity"],
            "activity_score": round(c.verdict_scores["activity"], 4),
            "conductivity": c.verdicts["conductivity"],
            "conductivity_score": round(c.verdict_scores["conductivity"], 4),
            "overall_viable": c.overall_viable,
        })

        rows.append(row_data)

    # Create DataFrame and save
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)

    print(f"✓ CSV saved to: {output_file}")
    print()

    # Print summary statistics
    print("Summary Statistics:")
    print("-" * 80)
    if RDKIT_AVAILABLE and "heavy_atoms" in df.columns:
        print(f"  Heavy atoms (all should be 22): min={df['heavy_atoms'].min()}, max={df['heavy_atoms'].max()}")
        print(f"  Molecular weight: min={df['MW'].min():.1f}, max={df['MW'].max():.1f}, mean={df['MW'].mean():.1f}")
        print(f"  Nitrogen donor atoms: min={df['N_count'].min()}, max={df['N_count'].max()}, mean={df['N_count'].mean():.1f}")
        print(f"  Oxygen donor atoms: min={df['O_count'].min()}, max={df['O_count'].max()}, mean={df['O_count'].mean():.1f}")
        print(f"  Sulfur donor atoms: min={df['S_count'].min()}, max={df['S_count'].max()}, mean={df['S_count'].mean():.1f}")

    print(f"  Morphism integrity: min={df['morphism_integrity'].min():.4f}, max={df['morphism_integrity'].max():.4f}")
    print(f"  ZFC constraints passed: {df['zfc_constraints_passed'].sum()} / {len(df)}")
    print(f"  Overall viable: {df['overall_viable'].sum()} / {len(df)} (should be {len(df)})")
    print()

    # Verify all verdicts are AGREE
    verdict_cols = ["synthesizability", "toxicity", "stability", "activity", "conductivity"]
    all_agree = True
    for col in verdict_cols:
        non_agree = df[df[col] != "AGREE"]
        if len(non_agree) > 0:
            print(f"  WARNING: {len(non_agree)} linkers have {col} != AGREE")
            all_agree = False

    if all_agree:
        print("  ✓ All verdicts = AGREE (as expected)")

    print()
    print("=" * 80)
    print("Generation complete! CSV ready to attach to email.")
    print("=" * 80)

    return df


if __name__ == "__main__":
    # Generate default 100 linkers
    df = generate_kulik_linkers(num_linkers=100, output_file="kulik_22atom_linkers_100.csv")

    # Print first few examples
    print()
    print("First 5 linkers:")
    print(df.head().to_string())
