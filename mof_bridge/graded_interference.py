# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2026 James Ray Hawkins
"""
Z2-Graded Linker Interference Detection
=======================================

Applies Z2-graded morphism chain detection to MOF linker design.

Maps KOMPOSOS MOF verdicts to Z2 parities:
  - AGREE (stable, known) → Parity 0 (Even/Benign)
  - HOLLOW/ORPHAN (novel, unsupported) → Parity 1 (Odd/Anomalous)

Detects "Synthesizability Exploit Chains":
  Where a sequence of novel modifications (Odd ∘ Odd) collapses into structural 
  instability (NULL_COLLAPSE).
"""

from __future__ import annotations
from typing import Dict, List, Optional
from mof_bridge.komposos_verdicts import LinkerVerdictResult

# Maps verdict types to Z2 parities
_VERDICT_PARITY = {
    "AGREE": 0,
    "REJECT": 0,
    "HOLLOW": 1,
    "ORPHAN": 1,
}

def _verdict_to_parity(verdicts: Dict[str, str]) -> int:
    """If any verdict is HOLLOW or ORPHAN, the whole morphism is Odd (Parity 1)."""
    for v in verdicts.values():
        if _VERDICT_PARITY.get(v, 1) == 1:
            return 1
    return 0

def verdict_to_amplitude(result: LinkerVerdictResult) -> complex:
    """Map verdict scores to amplitude."""
    # Use morphism_integrity as the base confidence signal
    return complex(max(0.0, min(1.0, result.morphism_integrity)), 0.0)

def grade_linker_result(result: LinkerVerdictResult) -> GradedMorphism:
    """Convert a screened linker result into a Z2 GradedMorphism."""
    parity = _verdict_to_parity(result.verdicts)
    amplitude = verdict_to_amplitude(result)
    
    return GradedMorphism(
        name=f"Linker[{result.linker_smiles[:10]}...]",
        parity=parity,
        amplitude=amplitude,
        source="linker_gen",
        target="mof_framework"
    )

def check_linker_chain_interference(
    results: List[LinkerVerdictResult],
) -> List[Dict]:
    """Check a chain of linker modifications for NULL_COLLAPSE."""
    graded = [grade_linker_result(r) for r in results]
    collapses = []
    
    for i in range(len(graded) - 1):
        a = graded[i]
        b = graded[i+1]
        
        composed = a * b
        if composed.is_collapsed:
            collapses.append({
                "chain_index": i,
                "morphism_a": a.name,
                "morphism_b": b.name,
                "severity": (a.magnitude * b.magnitude) ** 0.5
            })
            
    return collapses
