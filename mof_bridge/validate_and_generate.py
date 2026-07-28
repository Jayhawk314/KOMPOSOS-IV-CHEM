# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS MOF Linker System - Full Validation + Production Pipeline

Part A: Validate KOMPOSOS verdicts against MOFSimplify experimental data
Part B: Generate novel 22-atom linkers and screen with verdicts

Usage:
    python mof_bridge/validate_and_generate.py
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from mof_bridge.mp_mof_loader import MOFLinkerCache, MOFLinker
from mof_bridge.linker_generator import LinkerGenerator
from mof_bridge.komposos_verdicts import LinkerVerdictEngine


def part_a_validation():
    """Validate KOMPOSOS verdicts against MOFSimplify experimental data."""

    print("="*70)
    print("PART A: VALIDATION - KOMPOSOS vs MOFSimplify Experimental Data")
    print("="*70)

    # Load MOFSimplify stability data
    mofsimplify_path = Path("data/cache/mofsimplify_stability.json")

    if not mofsimplify_path.exists():
        print(f"\n❌ MOFSimplify data not found at {mofsimplify_path}")
        print("   Download from: https://zenodo.org/records/5737968")
        print("   File: all_solvent_removal_MOFs.json")
        return None

    print(f"\n📥 Loading MOFSimplify data from {mofsimplify_path}...")
    with open(mofsimplify_path) as f:
        mofsimplify_data = json.load(f)

    print(f"   Loaded {len(mofsimplify_data)} MOFs with stability labels")

    # Extract linkers and stability labels
    print("\n🔍 Extracting linkers and stability labels...")
    linker_data = []

    for mof_id, mof_info in list(mofsimplify_data.items())[:100]:  # Sample first 100
        if 'linker' in mof_info and 'stability' in mof_info:
            linker_smiles = mof_info.get('linker')
            is_stable = mof_info.get('stability', False)

            if linker_smiles:
                linker_data.append({
                    'mof_id': mof_id,
                    'smiles': linker_smiles,
                    'experimental_stable': is_stable
                })

    print(f"   Extracted {len(linker_data)} linkers with stability labels")

    if not linker_data:
        print("   ⚠️  No linker data found - checking data structure...")
        print(f"   Sample keys: {list(mofsimplify_data.keys())[:5]}")
        if mofsimplify_data:
            first_mof = list(mofsimplify_data.values())[0]
            print(f"   Sample MOF structure: {first_mof.keys() if isinstance(first_mof, dict) else type(first_mof)}")
        return None

    # Run KOMPOSOS verdicts
    print("\n⚙️  Running KOMPOSOS verdicts on extracted linkers...")

    engine = LinkerVerdictEngine()
    results = []
    for i, data in enumerate(linker_data[:50]):  # Test on first 50
        smiles = data['smiles']

        try:
            # Run all 5 verdicts
            result = engine.score_verdicts(smiles, "stability_check")
            
            # Count AGREE verdicts
            agree_count = sum(1 for v in result.verdicts.values() if v == 'AGREE')

            komposos_stable = agree_count >= 4  # 4+ AGREE = stable
            experimental_stable = data['experimental_stable']

            results.append({
                'mof_id': data['mof_id'],
                'komposos_stable': komposos_stable,
                'experimental_stable': experimental_stable,
                'agree_count': agree_count,
                'correct': komposos_stable == experimental_stable
            })

            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(linker_data[:50])} linkers...")

        except Exception as e:
            print(f"   ⚠️  Error on {data['mof_id']}: {e}")
            continue

    # Calculate accuracy
    if results:
        accuracy = sum(1 for r in results if r['correct']) / len(results) * 100

        print(f"\n📊 VALIDATION RESULTS:")
        print(f"   Total tested: {len(results)}")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Correct predictions: {sum(1 for r in results if r['correct'])}/{len(results)}")

        # Breakdown
        true_pos = sum(1 for r in results if r['komposos_stable'] and r['experimental_stable'])
        true_neg = sum(1 for r in results if not r['komposos_stable'] and not r['experimental_stable'])
        false_pos = sum(1 for r in results if r['komposos_stable'] and not r['experimental_stable'])
        false_neg = sum(1 for r in results if not r['komposos_stable'] and r['experimental_stable'])

        print(f"\n   True Positives (stable correctly): {true_pos}")
        print(f"   True Negatives (unstable correctly): {true_neg}")
        print(f"   False Positives (predicted stable, actually unstable): {false_pos}")
        print(f"   False Negatives (predicted unstable, actually stable): {false_neg}")

    return results


def part_b_production():
    """Generate novel 22-atom linkers and screen with KOMPOSOS verdicts."""

    print("\n" + "="*70)
    print("PART B: PRODUCTION - Generate Novel 22-Atom Linkers")
    print("="*70)

    # Load seed linkers
    print("\n📚 Loading seed linkers...")
    cache = MOFLinkerCache()
    seed_linkers = cache.load_linkers()
    print(f"   Loaded {len(seed_linkers)} seed linkers:")
    for i, l in enumerate(seed_linkers):
        print(f"   {i+1}. {l.formula} ({l.heavy_atom_count} atoms)")

    # Generate candidates
    print(f"\n🧬 Generating novel linker candidates...")
    gen = LinkerGenerator(seed_linkers)

    n_candidates = 20
    print(f"   Target: {n_candidates} candidates")
    print(f"   Application: gas_separation")

    candidates = gen.generate_candidates(
        n_candidates=n_candidates,
        application_context='gas_separation'
    )

    print(f"   ✓ Generated {len(candidates)} candidates")

    # Screen with KOMPOSOS verdicts
    print(f"\n⚙️  Screening with 5 KOMPOSOS verdicts...")

    engine = LinkerVerdictEngine()
    screened = []
    for i, smiles in enumerate(candidates):
        try:
            # Run all 5 verdicts
            result = engine.score_verdicts(smiles, 'gas_separation')

            # Count AGREE
            agree_count = sum(1 for v in result.verdicts.values() if v == 'AGREE')
            all_agree = agree_count == 5

            screened.append({
                'smiles': smiles,
                'verdicts': result.verdicts,
                'agree_count': agree_count,
                'all_agree': all_agree,
                'morphism_integrity': result.morphism_integrity
            })

            if (i + 1) % 5 == 0:
                print(f"   Screened {i + 1}/{len(candidates)} candidates...")

        except Exception as e:
            print(f"   ⚠️  Error screening candidate {i+1}: {e}")
            continue

    # Filter and rank
    agree_only = [s for s in screened if s['all_agree']]
    agree_only.sort(key=lambda x: x['morphism_integrity'], reverse=True)

    print(f"\n📊 SCREENING RESULTS:")
    print(f"   Total candidates: {len(screened)}")
    print(f"   AGREE across all 5 verdicts: {len(agree_only)}")
    print(f"   Pass rate: {len(agree_only)/len(screened)*100:.1f}%")

    # Show top 5
    print(f"\n🏆 TOP 5 NOVEL LINKERS (all verdicts AGREE):")
    for i, candidate in enumerate(agree_only[:5]):
        from rdkit import Chem
        mol = Chem.MolFromSmiles(candidate['smiles'])
        if mol:
            formula = Chem.rdMolDescriptors.CalcMolFormula(mol)
            heavy = mol.GetNumHeavyAtoms()
            integrity = candidate['morphism_integrity']

            print(f"\n   {i+1}. {formula} ({heavy} atoms) - Integrity: {integrity:.3f}")
            print(f"      {candidate['smiles'][:70]}")
            verdicts_str = ", ".join(f"{k[:4]}={v}" for k, v in candidate['verdicts'].items())
            print(f"      Verdicts: {verdicts_str}")

    # Save results
    output_file = Path("data/cache/novel_linkers_screened.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            'total_generated': len(candidates),
            'total_screened': len(screened),
            'agree_only': len(agree_only),
            'pass_rate': len(agree_only)/len(screened) if screened else 0,
            'top_candidates': agree_only[:10]
        }, f, indent=2)

    print(f"\n💾 Results saved to {output_file}")

    return agree_only


def main():
    """Run both validation and production pipelines."""

    print("\n" + "🔬"*35)
    print("KOMPOSOS MOF Linker System - Full Pipeline")
    print("🔬"*35)

    # Part A: Validation
    validation_results = part_a_validation()

    # Part B: Production
    production_results = part_b_production()

    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETE")
    print("="*70)

    if validation_results:
        accuracy = sum(1 for r in validation_results if r['correct']) / len(validation_results) * 100
        print(f"\n✓ Validation: {accuracy:.1f}% accuracy vs MOFSimplify data")

    if production_results:
        print(f"✓ Production: {len(production_results)} novel linkers passed all verdicts")

    print("\n📁 Output files:")
    print("   - data/cache/novel_linkers_screened.json")
    print("\n")


if __name__ == "__main__":
    main()
