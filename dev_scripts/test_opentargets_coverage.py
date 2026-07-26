#!/usr/bin/env python3
"""
Test OpenTargets coverage for latent proteins.

Queries OpenTargets Platform API for target-disease associations
for our 366 proteins and reports:
- How many latent proteins have disease associations
- What % map to our existing 20 diseases
- How many new diseases would be added
"""

import sqlite3
import requests
import json
import time
from typing import Set, Dict, List
from collections import defaultdict

# OpenTargets GraphQL endpoint
OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4/graphql"

# Our 20 existing diseases (mapped to EFO/MONDO IDs where possible)
EXISTING_DISEASES = {
    'AML': ['acute myeloid leukemia', 'acute myeloid leukaemia'],
    'Breast_Cancer': ['breast cancer', 'breast carcinoma'],
    'CLL': ['chronic lymphocytic leukemia', 'chronic lymphocytic leukaemia'],
    'CML': ['chronic myeloid leukemia', 'chronic myeloid leukaemia'],
    'Colorectal_Cancer': ['colorectal cancer', 'colorectal carcinoma'],
    'Ewing_Sarcoma': ['ewing sarcoma', 'ewing\'s sarcoma'],
    'GIST': ['gastrointestinal stromal tumor', 'gist'],
    'Glioblastoma': ['glioblastoma', 'glioblastoma multiforme'],
    'HCC': ['hepatocellular carcinoma', 'liver cancer'],
    'Li_Fraumeni_Syndrome': ['li-fraumeni syndrome', 'li fraumeni'],
    'Melanoma': ['melanoma', 'malignant melanoma'],
    'Multiple_Myeloma': ['multiple myeloma', 'plasma cell myeloma'],
    'Myelofibrosis': ['myelofibrosis', 'primary myelofibrosis'],
    'NSCLC': ['non-small cell lung cancer', 'non-small cell lung carcinoma'],
    'Ovarian_Cancer': ['ovarian cancer', 'ovarian carcinoma'],
    'Pancreatic_Cancer': ['pancreatic cancer', 'pancreatic carcinoma'],
    'Prostate_Cancer': ['prostate cancer', 'prostate carcinoma'],
    'RCC': ['renal cell carcinoma', 'kidney cancer'],
    'Soft_Tissue_Sarcoma': ['soft tissue sarcoma', 'sarcoma'],
    'Type2_Diabetes': ['type 2 diabetes', 'diabetes mellitus type 2'],
}


def get_latent_proteins(db_path='data/drugs/tier1.db') -> Set[str]:
    """Get list of latent proteins (no Disease edges)."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get all proteins with Disease edges
    c.execute('''
        SELECT DISTINCT source_name
        FROM morphisms
        WHERE target_name IN (SELECT name FROM objects WHERE type_name = "Disease")
    ''')
    proteins_with_disease = {row[0] for row in c.fetchall()}

    # Get all proteins
    c.execute('SELECT name FROM objects WHERE type_name NOT IN ("Drug", "Disease")')
    all_proteins = {row[0] for row in c.fetchall()}

    return all_proteins - proteins_with_disease


def query_opentargets_for_gene(gene_symbol: str, min_score: float = 0.5) -> List[Dict]:
    """
    Query OpenTargets for disease associations for a gene.

    Returns list of {"disease_name": str, "disease_id": str, "score": float}
    """
    query = """
    query targetDiseases($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        approvedSymbol
        associatedDiseases(page: {index: 0, size: 100}) {
          count
          rows {
            disease {
              id
              name
            }
            score
          }
        }
      }
    }
    """

    # First, need to get ENSG ID from gene symbol
    symbol_query = """
    query geneSearch($queryString: String!) {
      search(queryString: $queryString, entityNames: ["target"], page: {index: 0, size: 1}) {
        hits {
          id
          name
          entity
        }
      }
    }
    """

    try:
        # Get ENSG ID
        response = requests.post(
            OPENTARGETS_API,
            json={"query": symbol_query, "variables": {"queryString": gene_symbol}},
            timeout=30
        )

        if response.status_code != 200:
            return []

        data = response.json()
        hits = data.get('data', {}).get('search', {}).get('hits', [])

        if not hits:
            return []

        ensembl_id = hits[0]['id']

        # Get disease associations
        response = requests.post(
            OPENTARGETS_API,
            json={"query": query, "variables": {"ensemblId": ensembl_id}},
            timeout=30
        )

        if response.status_code != 200:
            return []

        data = response.json()
        target_data = data.get('data', {}).get('target', {})

        if not target_data:
            return []

        rows = target_data.get('associatedDiseases', {}).get('rows', [])

        associations = []
        for row in rows:
            score = row.get('score', 0)
            if score >= min_score:
                disease = row['disease']
                associations.append({
                    'disease_name': disease['name'],
                    'disease_id': disease['id'],
                    'score': score
                })

        return associations

    except Exception as e:
        print(f"Error querying {gene_symbol}: {e}")
        return []


def disease_matches_existing(disease_name: str) -> str:
    """Check if a disease name matches one of our existing 20 diseases."""
    disease_name_lower = disease_name.lower()

    for our_disease, aliases in EXISTING_DISEASES.items():
        for alias in aliases:
            if alias in disease_name_lower or disease_name_lower in alias:
                return our_disease

    return None


def main():
    print("OpenTargets Coverage Test for Latent Proteins")
    print("=" * 60)

    # Get latent proteins
    print("\nLoading latent proteins from tier1.db...")
    latent_proteins = get_latent_proteins()
    print(f"Found {len(latent_proteins)} latent proteins (no Disease edges)")

    # Sample first 50 proteins for quick test (full run would take ~2 hours)
    test_sample = sorted(latent_proteins)[:50]
    print(f"\n**Testing first {len(test_sample)} proteins (quick test)**")
    print("(Full 313 protein scan would take ~2 hours)")

    # Query OpenTargets
    print("\nQuerying OpenTargets Platform API...")
    print("(Rate limited to ~2 requests/sec to avoid throttling)\n")

    proteins_with_diseases = 0
    proteins_without_diseases = 0
    total_associations = 0
    associations_to_existing_diseases = 0
    new_diseases = set()

    protein_results = {}

    for i, gene in enumerate(test_sample, 1):
        print(f"[{i}/{len(test_sample)}] {gene}...", end=' ')

        associations = query_opentargets_for_gene(gene, min_score=0.5)

        if associations:
            proteins_with_diseases += 1
            total_associations += len(associations)
            protein_results[gene] = associations

            matches_existing = 0
            for assoc in associations:
                disease_name = assoc['disease_name']
                match = disease_matches_existing(disease_name)

                if match:
                    associations_to_existing_diseases += 1
                    matches_existing += 1
                else:
                    new_diseases.add(disease_name)

            print(f"OK {len(associations)} diseases ({matches_existing} match existing)")
        else:
            proteins_without_diseases += 1
            print("NONE")

        # Rate limiting
        time.sleep(0.5)

    # Analysis
    print("\n" + "=" * 60)
    print("COVERAGE ANALYSIS")
    print("=" * 60)

    coverage_pct = (proteins_with_diseases / len(test_sample)) * 100
    print(f"\n+ Proteins with disease associations: {proteins_with_diseases}/{len(test_sample)} ({coverage_pct:.1f}%)")
    print(f"- Proteins without disease associations: {proteins_without_diseases}/{len(test_sample)}")

    existing_match_pct = 0.0
    if total_associations > 0:
        existing_match_pct = (associations_to_existing_diseases / total_associations) * 100
        print(f"\n+ Total disease associations found: {total_associations}")
        print(f"+ Associations matching existing 20 diseases: {associations_to_existing_diseases} ({existing_match_pct:.1f}%)")
        print(f"+ New diseases that would be added: {len(new_diseases)}")
    else:
        print(f"\n- No disease associations found")

    print("\n" + "=" * 60)
    print("DECISION CRITERIA")
    print("=" * 60)

    # Decision thresholds from implementation plan
    deploy_criteria = coverage_pct >= 50 and existing_match_pct >= 30

    print(f"\n{'[PASS]' if coverage_pct >= 50 else '[FAIL]'} Coverage >= 50%: {coverage_pct:.1f}%")
    print(f"{'[PASS]' if existing_match_pct >= 30 else '[FAIL]'} Match existing diseases >= 30%: {existing_match_pct:.1f}%")

    print(f"\n**Decision**: {'DEPLOY' if deploy_criteria else 'DO NOT DEPLOY'}")

    if deploy_criteria:
        print("\n[OK] OpenTargets meets deployment criteria!")
        print("Next step: Estimate AUROC impact with test sample")
    else:
        print("\n[WARNING] OpenTargets does not meet deployment criteria")
        if coverage_pct < 50:
            print(f"   - Coverage too low: {coverage_pct:.1f}% < 50%")
        if existing_match_pct < 30:
            print(f"   - Existing disease match too low: {existing_match_pct:.1f}% < 30%")
        print("\nConsider alternatives:")
        print("   - DisGeNET (gene-disease associations)")
        print("   - Manual curation of high-value proteins")
        print("   - Focus on provenance instead")

    # Extrapolation
    print("\n" + "=" * 60)
    print("EXTRAPOLATION TO FULL 313 LATENT PROTEINS")
    print("=" * 60)

    estimated_coverage = int(313 * (coverage_pct / 100))
    estimated_associations = int((total_associations / len(test_sample)) * 313)
    estimated_existing_matches = int((associations_to_existing_diseases / len(test_sample)) * 313)
    estimated_new_diseases = int((len(new_diseases) / len(test_sample)) * 313)

    print(f"\nEstimated proteins that would be wired in: {estimated_coverage}/313")
    print(f"Estimated total associations: {estimated_associations}")
    print(f"Estimated associations to existing 20 diseases: {estimated_existing_matches}")
    print(f"Estimated new diseases to add: {estimated_new_diseases}")

    # Save results
    output = {
        'test_sample_size': len(test_sample),
        'total_latent_proteins': len(latent_proteins),
        'proteins_with_diseases': proteins_with_diseases,
        'proteins_without_diseases': proteins_without_diseases,
        'coverage_pct': round(coverage_pct, 1),
        'total_associations': total_associations,
        'associations_to_existing_diseases': associations_to_existing_diseases,
        'existing_match_pct': round(existing_match_pct, 1),
        'new_diseases_count': len(new_diseases),
        'new_diseases': sorted(list(new_diseases)),
        'meets_criteria': deploy_criteria,
        'extrapolated_coverage': estimated_coverage,
        'protein_results': protein_results
    }

    with open('opentargets_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n[OK] Results saved to opentargets_test_results.json")


if __name__ == '__main__':
    main()
