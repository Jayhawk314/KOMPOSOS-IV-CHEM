#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Quick test of OpenTargets API"""

import requests
import json

# Test 1: Search for BRAF gene
print("Test 1: Search for BRAF...")
query = """
query {
  search(queryString: "BRAF", entityNames: ["target"], page: {index: 0, size: 1}) {
    hits {
      id
      name
      entity
    }
  }
}
"""

response = requests.post(
    "https://api.platform.opentargets.org/api/v4/graphql",
    json={"query": query},
    timeout=30
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print(f"Error: {response.text}")

# Test 2: Get disease associations for BRAF (ENSG00000157764)
print("\n\nTest 2: Get disease associations for BRAF (ENSG00000157764)...")
query2 = """
query {
  target(ensemblId: "ENSG00000157764") {
    approvedSymbol
    associatedDiseases(page: {index: 0, size: 10}) {
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

response2 = requests.post(
    "https://api.platform.opentargets.org/api/v4/graphql",
    json={"query": query2},
    timeout=30
)

print(f"Status: {response2.status_code}")
if response2.status_code == 200:
    data2 = response2.json()
    print(json.dumps(data2, indent=2)[:1000])

    # Count associations
    target_data = data2.get('data', {}).get('target', {})
    if target_data:
        assoc = target_data.get('associatedDiseases', {})
        count = assoc.get('count', 0)
        rows = assoc.get('rows', [])
        print(f"\nTotal associations: {count}")
        print(f"Returned rows: {len(rows)}")
else:
    print(f"Error: {response2.text}")
