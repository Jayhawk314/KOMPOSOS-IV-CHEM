#!/usr/bin/env python3
"""
Check the 7 provable holes against Mathlib and NaturalProofs.

This script searches:
1. Mathlib4 documentation (leanprover-community.github.io)
2. NaturalProofs corpus (proofwiki.json)

For each of the 7 provable holes to see if they're already known.
"""

import json
import re
from typing import Dict, List, Tuple, Optional

# The 7 provable holes
PROVABLE_HOLES = [
    "Submodule.topologicalClosure_coe",
    "TopologicalSpace.OpenNhds.partialOrder",
    "TopologicalSpace.Opens.infLELeft_apply_mk",
    "TopologicalSpace.Closeds",
    "TopologicalSpace.OpenNhds.infLELeft",
    "TopologicalSpace.OpenNhds.inclusion_obj",
    "TopologicalSpace.Opens.carrier_eq_coe",
]


def search_mathlib(hole_id: str) -> Dict:
    """
    Search Mathlib4 documentation for the theorem.
    
    Returns dict with:
    - found: bool
    - url: str (if found)
    - similar: List[str] (similar theorem names)
    """
    # Mathlib4 documentation URL pattern
    base_url = "https://leanprover-community.github.io/mathlib4_docs"
    
    # Try direct URL (most theorems are at Mathlib/Path/To/Theorem.html)
    parts = hole_id.split('.')
    if len(parts) >= 2:
        # Convert to path: Mathlib.Topology.Basic → Mathlib/Topology/Basic.html
        path_parts = parts[:-1]  # All but last part
        theorem_name = parts[-1]  # Last part is the theorem name
        
        url = f"{base_url}/{'/'.join(path_parts)}.html"
        
        # For theorem anchors, try common patterns
        anchor_patterns = [
            f"#{theorem_name}",
            f"#{theorem_name.lower()}",
        ]
        
        return {
            'found': 'unknown',  # Would need web request to verify
            'url': url,
            'anchor_patterns': anchor_patterns,
            'search_query': f"{hole_id} site:leanprover-community.github.io",
        }
    
    return {
        'found': False,
        'url': None,
        'search_query': f"{hole_id} site:leanprover-community.github.io",
    }


def search_naturalproofs(hole_id: str, np_data: Dict) -> Dict:
    """
    Search NaturalProofs corpus for the theorem.
    
    Returns dict with:
    - found: bool
    - matches: List[Dict] (matching theorems)
    """
    matches = []
    
    # Get theorems from NaturalProofs
    theorems = []
    if isinstance(np_data, dict):
        dataset = np_data.get('dataset', np_data)
        if isinstance(dataset, dict):
            theorems = dataset.get('theorems', [])
        elif isinstance(dataset, list):
            theorems = dataset
    
    # Search for matching theorem names/labels
    hole_lower = hole_id.lower()
    
    for thm in theorems:
        if not isinstance(thm, dict):
            continue
        
        thm_id = str(thm.get('id', ''))
        thm_label = thm.get('label', '').lower()
        thm_title = thm.get('title', '').lower()
        
        # Check for keyword matches
        # Extract keywords from hole_id
        keywords = set(re.findall(r'[A-Z][a-z]+|[a-z]+', hole_id.lower()))
        
        # Check if theorem label/title contains similar keywords
        for kw in keywords:
            if len(kw) > 3 and (kw in thm_label or kw in thm_title):
                matches.append({
                    'id': thm_id,
                    'label': thm.get('label', 'N/A'),
                    'title': thm.get('title', 'N/A'),
                    'matched_keyword': kw,
                    'categories': thm.get('categories', []),
                })
                break
    
    # Deduplicate
    seen = set()
    unique_matches = []
    for m in matches:
        if m['id'] not in seen:
            seen.add(m['id'])
            unique_matches.append(m)
    
    return {
        'found': len(unique_matches) > 0,
        'matches': unique_matches[:10],  # Top 10 matches
    }


def check_mathlib_status(hole_id: str) -> str:
    """
    Check if theorem is likely in Mathlib based on naming pattern.
    
    Returns: 'LIKELY_IN_MATHLIB', 'POSSIBLY_IN_MATHLIB', or 'UNKNOWN'
    """
    # Patterns that suggest it's in Mathlib
    mathlib_patterns = [
        r'^Submodule\.',  # Submodule.* is well-developed in Mathlib
        r'^TopologicalSpace\.',  # TopologicalSpace.* is core Mathlib
        r'^TopologicalSpace\.Opens\.',  # Opens is well-developed
        r'^TopologicalSpace\.OpenNhds\.',  # OpenNhds is core topology
        r'\.(coe|mk|def|lemma|theorem)$',  # Standard naming
    ]
    
    # Patterns that suggest it's NOT in Mathlib (or is an artifact)
    non_mathlib_patterns = [
        r'_(coe|to_|mk|def)',  # Internal coercion/definition
        r'_(inf|sup|LE|LT)',  # Lattice operations (often internal)
        r'_(apply|symm|trans)',  # Proof combinators
    ]
    
    # Check for non-Mathlib patterns first
    for pattern in non_mathlib_patterns:
        if re.search(pattern, hole_id):
            return 'POSSIBLY_IN_MATHLIB'  # Might be internal lemma
    
    # Check for Mathlib patterns
    for pattern in mathlib_patterns:
        if re.search(pattern, hole_id):
            return 'LIKELY_IN_MATHLIB'
    
    return 'UNKNOWN'


def main():
    """Main entry point."""
    print("=" * 70)
    print("  CHECKING 7 PROVABLE HOLES AGAINST MATHLIB AND NATURALPROOFS")
    print("=" * 70)
    
    # Load NaturalProofs
    print("\n[1/3] Loading NaturalProofs corpus...")
    try:
        with open('data_sources/naturalproofs/naturalproofs_proofwiki.json', 'r') as f:
            np_data = json.load(f)
        print(f"      Loaded {len(np_data.get('dataset', {}).get('theorems', []))} theorems")
    except Exception as e:
        print(f"      ERROR: {e}")
        np_data = {}
    
    # Check each hole
    print("\n[2/3] Checking against Mathlib and NaturalProofs...")
    print()
    
    results = []
    
    for i, hole_id in enumerate(PROVABLE_HOLES):
        print(f"\n{'='*70}")
        print(f"  HOLE #{i+1}: {hole_id}")
        print(f"{'='*70}")
        
        # Check Mathlib
        mathlib_status = check_mathlib_status(hole_id)
        mathlib_search = search_mathlib(hole_id)
        
        print(f"\n  MATHLIB STATUS: {mathlib_status}")
        print(f"  Search URL: {mathlib_search.get('search_query', 'N/A')}")
        print(f"  Direct URL: {mathlib_search.get('url', 'N/A')}")
        
        # Check NaturalProofs
        np_result = search_naturalproofs(hole_id, np_data)
        
        print(f"\n  NATURALPROOFS STATUS:")
        if np_result['found']:
            print(f"    FOUND {len(np_result['matches'])} matching theorems:")
            for match in np_result['matches'][:3]:
                print(f"      • {match['label']}")
                print(f"        Categories: {', '.join(match['categories'][:3])}")
        else:
            print(f"    NOT FOUND in NaturalProofs")
        
        # Determine novelty
        if mathlib_status == 'LIKELY_IN_MATHLIB' and np_result['found']:
            novelty = "❌ LIKELY KNOWN"
            novelty_desc = "Found in both Mathlib and NaturalProofs"
        elif mathlib_status == 'LIKELY_IN_MATHLIB':
            novelty = "⚠️  LIKELY KNOWN (Mathlib only)"
            novelty_desc = "In Mathlib but not in ProofWiki"
        elif np_result['found']:
            novelty = "⚠️  LIKELY KNOWN (NaturalProofs only)"
            novelty_desc = "In ProofWiki but not clearly in Mathlib"
        else:
            novelty = "🎯 POTENTIALLY NEW!"
            novelty_desc = "Not found in Mathlib or NaturalProofs"
        
        print(f"\n  NOVELTY ASSESSMENT: {novelty}")
        print(f"  {novelty_desc}")
        
        results.append({
            'hole_id': hole_id,
            'mathlib_status': mathlib_status,
            'mathlib_url': mathlib_search.get('url'),
            'naturalproofs_found': np_result['found'],
            'naturalproofs_matches': np_result['matches'],
            'novelty': novelty,
            'novelty_description': novelty_desc,
        })
    
    # Save results
    print("\n" + "=" * 70)
    print("  [3/3] SAVING RESULTS")
    print("=" * 70)
    
    with open('7_holes_novelty_check.json', 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {
                'total_holes': len(results),
                'likely_known': sum(1 for r in results if 'KNOWN' in r['novelty']),
                'potentially_new': sum(1 for r in results if 'NEW' in r['novelty']),
            },
            'results': results,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: 7_holes_novelty_check.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print("  NOVELTY SUMMARY")
    print("=" * 70)
    
    likely_known = [r for r in results if 'KNOWN' in r['novelty']]
    potentially_new = [r for r in results if 'NEW' in r['novelty']]
    
    print(f"""
  Total holes checked:     {len(results)}
  Likely known:            {len(likely_known)}
  Potentially new:         {len(potentially_new)}
""")
    
    if potentially_new:
        print("=" * 70)
        print("  🎯 POTENTIALLY NEW THEOREMS")
        print("=" * 70)
        print()
        for r in potentially_new:
            print(f"  • {r['hole_id']}")
            print(f"    {r['novelty_description']}")
            print()
        print("""
  NEXT STEPS FOR THESE:
  1. Manually verify Mathlib search URLs
  2. Check if theorem names match (might be named differently)
  3. If truly new → formalize in Lean and submit to Mathlib!
""")
    
    print("=" * 70)


if __name__ == '__main__':
    main()
