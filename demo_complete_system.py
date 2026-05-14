#!/usr/bin/env python3
"""
COMPLETE SYSTEM DEMO - Drug Repurposing with Structure Validation

Shows the full KOMPOSOS-IV-PHARM pipeline:
1. Load bio data (tier1.db)
2. Oracle generates Drug->Disease predictions (6 strategies)
3. Find compositional Drug->Protein->Disease paths
4. Validate with structure-based binding (Boltz-2/chemistry)
5. Rank by combined score (categorical + structural)

This is the complete working system.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from domains.bio import BioDomainLoader
from core.category import Category
from oracle.strategies import (
    KanExtensionStrategy,
    CompositionStrategy,
    YonedaPatternStrategy,
    FibrationLiftStrategy,
    TypeHeuristicStrategy,
    StructuralHoleStrategy
)
from boltz2_bridge import Boltz2Bridge

def main():
    print("=" * 80)
    print("KOMPOSOS-IV-PHARM: Complete Drug Repurposing Pipeline")
    print("=" * 80)

    # Step 1: Load bio data
    print("\n[STEP 1] Loading biological data...")
    loader = BioDomainLoader()
    cat = Category(name="BioTier1", db_path=":memory:")
    loader.load_tier1("data/drugs/tier1.db", cat)
    stats = loader.get_stats()
    print(f"  Objects: {stats['objects_loaded']}")
    print(f"  Morphisms: {stats['morphisms_loaded']}")
    print(f"  Types: {', '.join(list(stats['type_distribution'].keys())[:5])}...")

    # Step 2: Initialize oracle strategies
    print("\n[STEP 2] Initializing oracle (6 strategies)...")
    strategies = [
        KanExtensionStrategy(cat),
        CompositionStrategy(cat),
        YonedaPatternStrategy(cat),
        FibrationLiftStrategy(cat),
        TypeHeuristicStrategy(cat),
        StructuralHoleStrategy(cat),
    ]
    for s in strategies:
        print(f"  - {s.name}")

    # Step 3: Initialize structure validator
    print("\n[STEP 3] Initializing structure validator...")
    boltz = Boltz2Bridge()
    print(f"  Boltz-2 available: {boltz.available}")
    print(f"  Chemistry fallback: {boltz.chemistry_available}")

    # Step 4: Find drugs and diseases
    print("\n[STEP 4] Identifying drugs and diseases...")
    drugs = [obj for obj in cat.objects() if obj.type_name == "Drug"]
    diseases = [obj for obj in cat.objects() if obj.type_name == "Disease"]
    proteins = [obj for obj in cat.objects() if obj.type_name not in ["Drug", "Disease", "Object"]]

    print(f"  Drugs: {len(drugs)}")
    print(f"  Diseases: {len(diseases)}")
    print(f"  Proteins: {len(proteins)}")

    # Step 5: Generate predictions
    print("\n[STEP 5] Generating Drug->Disease predictions...")
    print("  (Using 6 categorical strategies)")

    predictions = []

    for drug in drugs[:10]:  # Top 10 drugs
        for disease in diseases:  # All diseases
            # Skip existing edges
            if cat.hom(drug.name, disease.name) is not None:
                continue

            # Run oracle strategies
            votes = []
            for strategy in strategies:
                try:
                    preds = strategy.predict(drug.name, disease.name)
                    if len(preds) > 0:
                        votes.append((strategy.name, preds[0].confidence))
                except:
                    pass

            if len(votes) >= 3:  # Require 3+ strategies
                oracle_conf = sum(v[1] for v in votes) / len(votes)

                # Find paths
                paths = cat.find_paths(drug.name, disease.name, max_length=3)

                predictions.append({
                    'drug': drug.name,
                    'disease': disease.name,
                    'oracle_confidence': oracle_conf,
                    'n_strategies': len(votes),
                    'strategies': [v[0] for v in votes],
                    'n_paths': len(paths),
                    'paths': paths[:3]  # Top 3 paths
                })

    print(f"  Generated {len(predictions)} predictions")

    # Step 6: Validate top predictions with structure
    print("\n[STEP 6] Validating with structure-based binding...")
    validated_predictions = []

    for pred in predictions[:20]:  # Top 20 for validation
        # Find proteins in paths
        proteins_in_path = set()
        for path in pred['paths']:
            for mid in path.morphism_ids:
                mor = cat.get_morphism(mid)
                if mor:
                    obj = cat.get(mor.target)
                    if obj and obj.type_name not in ["Drug", "Disease"]:
                        proteins_in_path.add(mor.target)

        # Validate drug-protein binding for each protein in path
        binding_scores = []
        for protein in proteins_in_path:
            enhanced_conf, binding = boltz.enhance_oracle_prediction(
                pred['drug'],
                protein,
                pred['oracle_confidence']
            )
            binding_scores.append({
                'protein': protein,
                'binding_score': binding.binding_score,
                'confidence': binding.confidence
            })

        # Combined score: oracle + average binding
        if len(binding_scores) > 0:
            avg_binding = sum(b['binding_score'] for b in binding_scores) / len(binding_scores)
            combined_score = 0.6 * pred['oracle_confidence'] + 0.4 * avg_binding
        else:
            combined_score = pred['oracle_confidence']
            avg_binding = 0

        validated_predictions.append({
            **pred,
            'binding_scores': binding_scores,
            'avg_binding': avg_binding,
            'combined_score': combined_score
        })

    # Step 7: Rank and present results
    print("\n[STEP 7] Top 10 Drug Repurposing Candidates:")
    print("  (Ranked by combined categorical + structural score)\n")

    validated_predictions.sort(key=lambda x: -x['combined_score'])

    for i, pred in enumerate(validated_predictions[:10], 1):
        drug = pred['drug']
        disease = pred['disease']
        oracle = pred['oracle_confidence']
        binding = pred['avg_binding']
        combined = pred['combined_score']
        n_strat = pred['n_strategies']
        n_paths = pred['n_paths']

        print(f"  {i:2d}. {drug:15s} -> {disease:20s}")
        print(f"      Combined Score: {combined:.3f}")
        print(f"      - Oracle: {oracle:.3f} ({n_strat} strategies)")
        print(f"      - Binding: {binding:.3f}")
        print(f"      - Paths: {n_paths}")

        # Show best path
        if len(pred['paths']) > 0:
            best_path = pred['paths'][0]
            path_names = [drug]
            for mid in best_path.morphism_ids:
                mor = cat.get_morphism(mid)
                if mor:
                    path_names.append(mor.target)
            print(f"      - Best Path: {' -> '.join(path_names)}")

        # Show binding details
        if len(pred['binding_scores']) > 0:
            best_binding = max(pred['binding_scores'], key=lambda x: x['binding_score'])
            print(f"      - Best Target: {best_binding['protein']} (binding: {best_binding['binding_score']:.3f})")

        print()

    print("=" * 80)
    print("COMPLETE PIPELINE DEMONSTRATION")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Categorical reasoning: {len(predictions)} drug-disease predictions")
    print(f"  - Structure validation: Top {min(20, len(predictions))} validated")
    print(f"  - Final candidates: {min(10, len(validated_predictions))} ranked")
    print(f"\nThis combines:")
    print(f"  ✓ Category theory (Kan extensions, fibrations)")
    print(f"  ✓ Graph reasoning (composition, structural holes)")
    print(f"  ✓ Physical chemistry (binding, interactions)")
    print(f"  ✓ Path analysis (drug->protein->disease)")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
