# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
"""Tests for the Z3 stoichiometric balance solver."""

from fractions import Fraction

import pytest

from synthesis_planner.stoich_solver import (
    FormulaError,
    audit_route,
    parse_formula,
    run_balance_audit,
    solve_balance,
)
from synthesis_planner.route_graph import get_route_by_name


# ---------------------------------------------------------------- parser ---

def test_parse_simple():
    assert parse_formula("Li2CO3") == {"Li": 2, "C": 1, "O": 3}


def test_parse_nested_hydrate():
    comp = parse_formula("Fe(NO3)3*9H2O")
    assert comp == {"Fe": 1, "N": 3, "O": 18, "H": 18}


def test_parse_ammonium_sulfate():
    assert parse_formula("(NH4)2SO4") == {"N": 2, "H": 8, "S": 1, "O": 4}


def test_parse_decimal_subscripts_exact():
    comp = parse_formula("LiNi0.8Mn0.1Co0.1O2")
    assert comp["Ni"] == Fraction(4, 5)
    assert comp["Mn"] == Fraction(1, 10)


@pytest.mark.parametrize("bad", ["SBR", "-(CH2CF2)n-", "CMC-Na", "various", ""])
def test_parse_rejects_non_stoichiometric(bad):
    with pytest.raises(FormulaError):
        parse_formula(bad)


# ---------------------------------------------------------------- solver ---

def test_lgps_exact_balance_no_byproducts():
    res = solve_balance(
        {"Li2S": parse_formula("Li2S"),
         "GeS2": parse_formula("GeS2"),
         "P2S5": parse_formula("P2S5")},
        parse_formula("Li10GeP2S12"))
    assert res.status == "sat"
    assert res.coefficients == {"Li2S": 5, "GeS2": 1, "P2S5": 1}
    assert all(v == 0 for v in res.aux_out.values())


def test_missing_element_is_unsat_with_core():
    res = solve_balance({"Li2S": parse_formula("Li2S")},
                        parse_formula("LiFePO4"),
                        aux_outputs=["H2S"])
    assert res.status == "unsat"
    assert "Fe" in res.unbalanced_elements


def test_llzo_route_balances_with_water_release():
    route = get_route_by_name("LLZO_solid_state")
    audit = audit_route(route)
    assert audit.status == "BALANCED"
    assert "H2O" in audit.reaction


def test_composite_targets_are_skipped_not_forced():
    route = get_route_by_name("PVDF_film_casting")
    audit = audit_route(route)
    assert audit.status == "SKIPPED"


def test_full_audit_has_no_unbalanced_routes():
    results = run_balance_audit()
    unbalanced = [r.route for r in results if r.status == "UNBALANCED"]
    assert unbalanced == [], f"curated routes failed balance: {unbalanced}"
    assert sum(1 for r in results if r.status == "BALANCED") >= 10


# ----------------------------------------------------- planner integration ---

def test_score_route_attaches_balanced_reaction():
    from synthesis_planner.route_planner import SynthesisPlanner
    planner = SynthesisPlanner()
    scored = planner.score_route(get_route_by_name("LLZO_solid_state"))
    assert scored.stoichiometry_status == "BALANCED"
    assert "Li7La3Zr2O12" in scored.balanced_reaction
    assert scored.composite_score > 0
    d = scored.to_dict()
    assert d["stoichiometry"] == "BALANCED"
    assert d["balanced_reaction"] == scored.balanced_reaction


def test_unbalanced_route_is_vetoed():
    from synthesis_planner.route_planner import SynthesisPlanner
    from synthesis_planner.route_graph import (
        SynthesisConditions, SynthesisStep, SynthesisRoute,
    )
    # LFP target but no phosphorus or iron source: balance is impossible.
    broken = SynthesisRoute(
        name="broken_LFP_no_P_source",
        target="LFP",
        steps=[SynthesisStep(
            operation="calcine",
            inputs=["Li2CO3"],
            output="LFP",
            conditions=SynthesisConditions(temperature_C=700, time_hours=10.0,
                                           atmosphere="N2"),
            success_probability=0.9,
        )],
        precursors=["Li2CO3"],
        overall_confidence=0.9,
        total_time_hours=10.0,
        max_temperature_C=700.0,
        risk_level="low",
    )
    scored = SynthesisPlanner().score_route(broken)
    assert scored.stoichiometry_status == "UNBALANCED"
    assert scored.composite_score == 0.0
    assert any("Fe" in n or "P" in n for n in scored.stoichiometry_notes)


def test_composite_targets_score_without_stoich_penalty():
    from synthesis_planner.route_planner import SynthesisPlanner
    scored = SynthesisPlanner().score_route(
        get_route_by_name("PVDF_film_casting"))
    assert scored.stoichiometry_status == "SKIPPED"
    assert scored.composite_score > 0
