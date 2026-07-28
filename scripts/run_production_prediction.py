# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import json
import sys
from pathlib import Path

# Add project root to path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from mof_bridge.linker_screening import LinkerScreeningSpec, LinkerScreener

def run_prediction_pipeline():
    print("="*70)
    print("KOMPOSOS-MOF PRODUCTION PIPELINE")
    print("="*70)

    # 1. Initialize Screener (which loads cache and generator)
    screener = LinkerScreener()
    
    # 2. Configure Screening Specification
    # Focus on 18-26 range (generator defaults to 18-30, but we can override if needed)
    # The generator in screener uses known_linkers from cache.
    
    spec = LinkerScreeningSpec(
        application_context="breath_VOC_sensing",
        num_candidates=50,
        require_all_agree=False, 
        allow_hollow=True, # Explicitly allow hollow
        ranking_mode="morphism_integrity"
    )

    # 3. Run Pipeline
    result = screener.screen(spec)
    
    # 4. Save results to master history file
    import time
    history_file = Path("data/linker_history.json")
    
    # Load existing history
    history = []
    seen_smiles = set()
    if history_file.exists():
        with open(history_file, "r") as f:
            try:
                history = json.load(f)
                seen_smiles = {item['smiles'] for item in history}
            except json.JSONDecodeError:
                pass

    # Append new results (deduplicating)
    new_results = 0
    for c in result.candidates:
        if c.linker_smiles not in seen_smiles:
            history.append({
                "smiles": c.linker_smiles,
                "verdicts": c.verdicts,
                "scores": c.verdict_scores,
                "viable": c.overall_viable,
                "timestamp": time.time()
            })
            seen_smiles.add(c.linker_smiles)
            new_results += 1
        
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
        
    print(f"\nPipeline complete!")
    print(f"  New candidates added to history: {new_results}")
    print(f"  Total historical candidates: {len(history)}")

if __name__ == "__main__":
    run_prediction_pipeline()
