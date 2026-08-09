# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import json
from types import SimpleNamespace

from mof_bridge.review_exports import build_review_exports, geometry_status, grounded_funnel_status


def _candidate(smiles):
    return SimpleNamespace(linker_smiles=smiles)


def _funnel(**overrides):
    result = {
        "score": 0.9, "passed_all": True, "died_at": None, "gate_level": 4,
        "n_coord": 2, "sascore": 2.5, "geometry_ok": True,
        "pains_brenk_flag": False, "max_tanimoto": 0.25,
    }
    result.update(overrides)
    return result


def test_status_preserves_unassessed_geometry():
    assert grounded_funnel_status(_funnel()) == "ASSESSED_PASS"
    assert grounded_funnel_status(_funnel(geometry_ok=None)) == "PARTIAL_PASS"
    assert grounded_funnel_status(_funnel(passed_all=False)) == "VETOED"
    assert grounded_funnel_status(None) == "NOT_ASSESSED"
    assert geometry_status(_funnel(geometry_ok=None)) == "NOT_ASSESSED"


def test_paired_exports_have_same_candidates_and_order():
    scored = [
        (_candidate("first"), _funnel()),
        (_candidate("second"), _funnel(geometry_ok=None)),
        (_candidate("third"), _funnel(passed_all=False, died_at="G2_coordination",
                                      gate_level=1, n_coord=1, geometry_ok=None,
                                      sascore=None, max_tanimoto=None)),
        (_candidate("fourth"), None),
    ]
    conventional, evidence = build_review_exports(
        scored, lambda value: "F-" + value, len, lambda value: float(len(value))
    )
    assert [row["SMILES"] for row in conventional] == [row["SMILES"] for row in evidence]
    assert [row["rank"] for row in conventional] == [1, 2, 3, 4]
    assert [row["grounded_funnel_status"] for row in evidence] == [
        "ASSESSED_PASS", "PARTIAL_PASS", "VETOED", "NOT_ASSESSED"
    ]
    assert evidence[0]["novelty_coordinate"] == 0.75
    assert evidence[1]["geometry_status"] == "NOT_ASSESSED"
    assert evidence[2]["died_at"] == "G2_coordination"
    assert evidence[3]["experimental_status"] == "NOT_ASSESSED"
    assert "toxicity" not in evidence[0]
    json.dumps({"conventional": conventional, "evidence": evidence})
