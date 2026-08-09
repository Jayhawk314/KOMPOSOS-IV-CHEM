# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Paired review exports for grounded MOF linker screening."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Tuple

EVIDENCE_ROLE = "structural_screening_estimate"
EXPERIMENTAL_STATUS = "NOT_ASSESSED"
CLAIM_SCOPE = (
    "The grounded funnel was benchmarked for retention/ranking of recorded real "
    "linkers versus constructed decoys. It does not establish synthesis, metal "
    "coordination, framework topology, stability, toxicity, conductivity, or "
    "application performance for a generated candidate."
)
MISSING_EVIDENCE = (
    "expert chemistry review; metal/node compatibility; framework topology; "
    "phase formation; synthesis route and yield; application measurements"
)


def grounded_funnel_status(funnel: Optional[Dict]) -> str:
    """Preserve missing geometry instead of converting it into a full pass."""
    if funnel is None:
        return "NOT_ASSESSED"
    if not funnel.get("passed_all", False):
        return "VETOED"
    if funnel.get("geometry_ok") is None:
        return "PARTIAL_PASS"
    return "ASSESSED_PASS"


def geometry_status(funnel: Optional[Dict]) -> str:
    if funnel is None or funnel.get("geometry_ok") is None:
        return "NOT_ASSESSED"
    return "ASSESSED_PASS" if funnel["geometry_ok"] else "VETOED"


def build_review_exports(
    scored: Iterable[Tuple[object, Optional[Dict]]],
    formula_fn: Callable[[str], str],
    heavy_fn: Callable[[str], int],
    mw_fn: Callable[[str], float],
) -> Tuple[List[Dict], List[Dict]]:
    """Return same-order conventional and evidence-governed records."""
    conventional, evidence = [], []
    for rank, (candidate, funnel) in enumerate(scored, start=1):
        smiles = candidate.linker_smiles
        core = {
            "rank": rank,
            "formula": formula_fn(smiles),
            "heavy_atoms": heavy_fn(smiles),
            "molecular_weight": mw_fn(smiles),
            "SMILES": smiles,
            "rank_score": funnel.get("score") if funnel else None,
        }
        conventional.append(dict(core))
        novelty = None
        if funnel and funnel.get("max_tanimoto") is not None:
            novelty = round(1 - funnel["max_tanimoto"], 3)
        row = dict(core)
        row.update({
            "grounded_funnel_status": grounded_funnel_status(funnel),
            "evidence_role": EVIDENCE_ROLE,
            "experimental_status": EXPERIMENTAL_STATUS,
            "passed_all_implemented_gates": funnel.get("passed_all") if funnel else None,
            "died_at": funnel.get("died_at") if funnel else None,
            "gate_level": funnel.get("gate_level") if funnel else None,
            "recognized_coordination_sites": funnel.get("n_coord") if funnel else None,
            "sascore": funnel.get("sascore") if funnel else None,
            "geometry_status": geometry_status(funnel),
            "pains_brenk_soft_flag": funnel.get("pains_brenk_flag") if funnel else None,
            "max_seed_tanimoto": funnel.get("max_tanimoto") if funnel else None,
            "novelty_coordinate": novelty,
            "claim_scope": CLAIM_SCOPE,
            "missing_evidence": MISSING_EVIDENCE,
        })
        evidence.append(row)
    return conventional, evidence
