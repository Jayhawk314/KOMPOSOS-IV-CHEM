# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Synthesis Planner (Phase 2)
============================

Answers "HOW do you make it?" — synthesis routes as morphism chains.

Given a target material, returns ranked synthesis routes with precursors,
conditions, equipment, hazards, cost, and time estimates. All data is
curated from published literature with citations.

Quick start:
    from synthesis_planner import SynthesisPlanner, MaterialSpec

    planner = SynthesisPlanner()

    # Plan by target
    analysis = planner.plan_synthesis("LFP")
    print(analysis.best_route.route.name)

    # Plan by specification
    spec = MaterialSpec(target_type="cathode",
                       required_properties={"voltage_nominal_min": 3.0})
    analysis = planner.plan_from_spec(spec)
"""

__version__ = "1.0.0"

from synthesis_planner.route_graph import (
    SynthesisConditions,
    SynthesisStep,
    SynthesisRoute,
    build_route,
    compute_route_confidence,
    get_routes,
    get_route_by_name,
    list_all_targets,
    list_all_routes,
    ALL_ROUTES,
)

from synthesis_planner.precursor_db import (
    Precursor,
    get_precursor,
    list_precursors,
    estimate_route_cost,
    find_missing_precursors,
    ALL_PRECURSORS,
)

from synthesis_planner.route_planner import (
    SynthesisPlanner,
    MaterialSpec,
    SynthesisAnalysis,
    ScoredRoute,
)

__all__ = [
    # Route graph
    'SynthesisConditions',
    'SynthesisStep',
    'SynthesisRoute',
    'build_route',
    'compute_route_confidence',
    'get_routes',
    'get_route_by_name',
    'list_all_targets',
    'list_all_routes',
    'ALL_ROUTES',
    # Precursor DB
    'Precursor',
    'get_precursor',
    'list_precursors',
    'estimate_route_cost',
    'find_missing_precursors',
    'ALL_PRECURSORS',
    # Planner
    'SynthesisPlanner',
    'MaterialSpec',
    'SynthesisAnalysis',
    'ScoredRoute',
]
