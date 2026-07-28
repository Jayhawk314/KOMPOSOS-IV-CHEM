#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Test OpenTargets cancer disease filtering."""

import requests
import json

OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4/graphql"

# Test: get disease details for melanoma (EFO_0000756) to see therapeutic area structure
query = """
query {
  disease(efoId: "EFO_0000756") {
    id
    name
    therapeuticAreas {
      id
      name
    }
  }
}
"""

print("Test 1: Melanoma disease classification")
response = requests.post(OPENTARGETS_API, json={"query": query}, timeout=30)
print(json.dumps(response.json(), indent=2))

# Test: get AKT1 disease associations WITH therapeutic area info
query2 = """
query {
  target(ensemblId: "ENSG00000142208") {
    approvedSymbol
    associatedDiseases(page: {index: 0, size: 20}) {
      count
      rows {
        disease {
          id
          name
          therapeuticAreas {
            id
            name
          }
        }
        score
      }
    }
  }
}
"""

print("\n\nTest 2: AKT1 disease associations with therapeutic areas")
response2 = requests.post(OPENTARGETS_API, json={"query": query2}, timeout=30)
data = response2.json()

target = data.get('data', {}).get('target', {})
if target:
    assoc = target.get('associatedDiseases', {})
    print(f"Total associations: {assoc.get('count', 0)}")

    cancer_count = 0
    for row in assoc.get('rows', []):
        disease = row['disease']
        areas = [a['name'] for a in disease.get('therapeuticAreas', [])]
        is_cancer = any('neoplasm' in a.lower() or 'cancer' in a.lower() for a in areas)

        if is_cancer:
            cancer_count += 1

        marker = "[CANCER]" if is_cancer else "[other]"
        print(f"  {marker} {disease['name']} (score: {row['score']:.3f})")
        print(f"          Areas: {', '.join(areas)}")

    print(f"\nCancer associations: {cancer_count}/{len(assoc.get('rows', []))}")
