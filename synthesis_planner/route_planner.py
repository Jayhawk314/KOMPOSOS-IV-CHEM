# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Synthesis Route Planner
========================

The main analyzer for Phase 2: given a target material or a specification,
find and rank synthesis routes. This is the "HOW do you make it?" engine.

Usage:
    planner = SynthesisPlanner()
    analysis = planner.plan_synthesis("LFP")
    print(analysis.best_route.route.name)

    spec = MaterialSpec(target_type="cathode", required_properties={"voltage_min": 3.0})
    analysis = planner.plan_from_spec(spec)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from synthesis_planner.route_graph import (
    SynthesisRoute, SynthesisStep, SynthesisConditions,
    get_routes, list_all_targets, list_all_routes,
)
from synthesis_planner.precursor_db import (
    get_precursor, estimate_route_cost, find_missing_precursors,
    find_hazardous_precursors, check_availability,
)

# Z3 stoichiometric validation is an optional evidence layer: the planner
# stays fully functional without z3-solver installed (status UNAVAILABLE).
try:
    from synthesis_planner.stoich_solver import audit_route as _stoich_audit_route
except ImportError:
    _stoich_audit_route = None

# Routes are static module data, so one Z3 solve per route name is enough.
_STOICH_CACHE: Dict[str, object] = {}


def _stoichiometry_check(route: "SynthesisRoute"):
    if _stoich_audit_route is None:
        return None
    if route.name not in _STOICH_CACHE:
        _STOICH_CACHE[route.name] = _stoich_audit_route(route)
    return _STOICH_CACHE[route.name]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MaterialSpec:
    """User specification for what they want to make."""
    target_type: str                              # "cathode", "anode", "electrolyte", "coating"
    required_properties: Dict = field(default_factory=dict)  # e.g. {"voltage_min": 3.0}
    budget_usd: Optional[float] = None
    max_time_hours: Optional[float] = None
    available_equipment: List[str] = field(default_factory=list)


@dataclass
class ScoredRoute:
    """A synthesis route with scoring breakdown."""
    route: SynthesisRoute
    feasibility_score: float             # 0-1 (route confidence)
    cost_score: float                    # 0-1 (lower cost = higher)
    time_score: float                    # 0-1 (shorter = higher)
    safety_score: float                  # 0-1 (fewer hazards = higher)
    composite_score: float               # Weighted combination
    bottleneck_step: Optional[SynthesisStep]
    missing_precursors: List[str] = field(default_factory=list)
    missing_equipment: List[str] = field(default_factory=list)
    # Z3 stoichiometric validation (see stoich_solver):
    # BALANCED | BALANCED_UNUSED_INPUTS | UNBALANCED | SKIPPED | UNAVAILABLE
    stoichiometry_status: str = "UNAVAILABLE"
    balanced_reaction: str = ""
    stoichiometry_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'route_name': self.route.name,
            'target': self.route.target,
            'feasibility': self.feasibility_score,
            'cost': self.cost_score,
            'time': self.time_score,
            'safety': self.safety_score,
            'composite': self.composite_score,
            'bottleneck': self.bottleneck_step.operation if self.bottleneck_step else None,
            'missing_precursors': self.missing_precursors,
            'missing_equipment': self.missing_equipment,
            'stoichiometry': self.stoichiometry_status,
            'balanced_reaction': self.balanced_reaction,
            'stoichiometry_notes': self.stoichiometry_notes,
        }


@dataclass
class SynthesisAnalysis:
    """Result of synthesis planning."""
    target: str
    routes: List[ScoredRoute]
    best_route: Optional[ScoredRoute]
    precursor_cost_usd: float
    total_time_hours: float
    equipment_needed: List[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'target': self.target,
            'num_routes': len(self.routes),
            'best_route': self.best_route.to_dict() if self.best_route else None,
            'precursor_cost_usd': self.precursor_cost_usd,
            'total_time_hours': self.total_time_hours,
            'equipment_needed': self.equipment_needed,
            'warnings': self.warnings,
            'all_routes': [r.to_dict() for r in self.routes],
        }


# ============================================================================
# Equipment Registry
# ============================================================================

# Map from route equipment names to human-readable + availability info
COMMON_EQUIPMENT = {
    'furnace', 'ball_mill', 'stirrer', 'oven', 'mixer', 'mortar',
    'filter', 'doctor_blade', 'calender_rolls', 'hot_press',
}
SPECIALIZED_EQUIPMENT = {
    'autoclave', 'reactor', 'glovebox', 'PVD_chamber', 'plasma_spray',
    'Acheson_furnace', 'rotary_kiln', 'crystallizer', 'ultrasonic_bath',
    'grit_blaster', 'spray_dryer', 'press',
}

# Target type -> material mapping for spec-based planning
TARGET_TYPE_MATERIALS = {
    'cathode': ['LFP', 'NMC811', 'NMC622', 'NMC111', 'LCO', 'LMO', 'NCA'],
    'anode': ['Graphite_anode_electrode', 'Graphite_anode_electrode_water'],
    'electrolyte_solid': ['LLZO', 'LGPS', 'Li3PS4', 'NASICON'],
    'electrolyte_polymer': ['PEO_electrolyte'],
    'coating_ceramic': ['Al2O3_coating', 'TiN_coating', 'YSZ_coating'],
    'coating_pvd': ['Al2O3_coating', 'TiN_coating'],
    'electrode_lfp': ['LFP_cathode_electrode'],
    'electrode_nmc': ['NMC811_cathode_electrode'],
    'ceramic': ['Al2O3', 'SiC'],
    'polymer_film': ['PVDF_film'],
}

# Material property lookup for spec matching
MATERIAL_PROPERTIES = {
    'LFP': {'voltage_nominal': 3.4, 'capacity': 170, 'cost': 'low', 'safety': 'high'},
    'NMC811': {'voltage_nominal': 3.8, 'capacity': 200, 'cost': 'medium', 'safety': 'medium'},
    'NMC622': {'voltage_nominal': 3.7, 'capacity': 180, 'cost': 'medium', 'safety': 'medium'},
    'NMC111': {'voltage_nominal': 3.7, 'capacity': 160, 'cost': 'medium', 'safety': 'high'},
    'LCO': {'voltage_nominal': 3.9, 'capacity': 140, 'cost': 'high', 'safety': 'low'},
    'LMO': {'voltage_nominal': 4.0, 'capacity': 120, 'cost': 'low', 'safety': 'high'},
    'NCA': {'voltage_nominal': 3.7, 'capacity': 200, 'cost': 'medium', 'safety': 'medium'},
}


# ============================================================================
# Scoring Functions
# ============================================================================

def _score_feasibility(route: SynthesisRoute) -> float:
    """Score based on route confidence (0.75*min + 0.25*avg already computed)."""
    return route.overall_confidence


def _score_cost(route: SynthesisRoute) -> float:
    """Score inversely proportional to estimated precursor cost."""
    cost = estimate_route_cost(route.precursors)
    # Normalize: $0 = 1.0, $1/g = 0.5, $5/g = 0.1
    if cost <= 0:
        return 1.0
    elif cost <= 0.05:
        return 0.95
    elif cost <= 0.10:
        return 0.85
    elif cost <= 0.50:
        return 0.70
    elif cost <= 1.0:
        return 0.50
    elif cost <= 5.0:
        return 0.30
    else:
        return 0.10


def _score_time(route: SynthesisRoute) -> float:
    """Score inversely proportional to total synthesis time."""
    hours = route.total_time_hours
    if hours <= 4:
        return 1.0
    elif hours <= 12:
        return 0.85
    elif hours <= 24:
        return 0.70
    elif hours <= 48:
        return 0.55
    elif hours <= 100:
        return 0.35
    else:
        return 0.15


def _score_safety(route: SynthesisRoute) -> float:
    """Score based on hazard count and severity."""
    all_hazards = []
    for step in route.steps:
        all_hazards.extend(step.hazards)

    if not all_hazards:
        return 1.0

    severe = sum(1 for h in all_hazards if h in
                 {'toxic_gas', 'H2S_release', 'pyrophoric', 'CO_gas'})
    moderate = sum(1 for h in all_hazards if h in
                   {'exothermic', 'moisture_sensitive', 'corrosive', 'NMP_toxic', 'high_pressure'})

    score = 1.0 - (severe * 0.2 + moderate * 0.08)
    return max(0.1, min(1.0, score))


def _find_bottleneck(route: SynthesisRoute) -> Optional[SynthesisStep]:
    """Find the step with lowest success probability."""
    if not route.steps:
        return None
    return min(route.steps, key=lambda s: s.success_probability)


def _collect_equipment(route: SynthesisRoute) -> List[str]:
    """Collect all unique equipment needed for a route."""
    seen = set()
    result = []
    for step in route.steps:
        eq = step.conditions.equipment
        if eq not in seen:
            seen.add(eq)
            result.append(eq)
    return result


# ============================================================================
# SynthesisPlanner
# ============================================================================

class SynthesisPlanner:
    """
    Main synthesis planning engine.

    Given a target material or a specification, finds and ranks
    synthesis routes by feasibility, cost, time, and safety.
    """

    def __init__(
        self,
        feasibility_weight: float = 0.35,
        cost_weight: float = 0.20,
        time_weight: float = 0.20,
        safety_weight: float = 0.25,
    ):
        self._w_feas = feasibility_weight
        self._w_cost = cost_weight
        self._w_time = time_weight
        self._w_safe = safety_weight

    def score_route(
        self,
        route: SynthesisRoute,
        available_equipment: Optional[List[str]] = None,
    ) -> ScoredRoute:
        """Score a single synthesis route."""
        feas = _score_feasibility(route)
        cost = _score_cost(route)
        time = _score_time(route)
        safe = _score_safety(route)

        composite = (
            self._w_feas * feas +
            self._w_cost * cost +
            self._w_time * time +
            self._w_safe * safe
        )

        bottleneck = _find_bottleneck(route)
        missing_prec = find_missing_precursors(route.precursors)
        needed_eq = _collect_equipment(route)

        # Check missing equipment
        missing_eq = []
        if available_equipment is not None:
            avail_set = set(available_equipment)
            missing_eq = [eq for eq in needed_eq if eq not in avail_set]
            # Penalize for missing equipment
            if missing_eq:
                penalty = min(len(missing_eq) * 0.1, 0.3)
                composite = max(0.0, composite - penalty)

        # Penalize for missing precursors
        if missing_prec:
            penalty = min(len(missing_prec) * 0.05, 0.2)
            composite = max(0.0, composite - penalty)

        # Stoichiometric validation (Z3). UNBALANCED means no element balance
        # exists between precursors and target: a true physical block, so it
        # annihilates the composite instead of being diluted by other merit.
        stoich_status = "UNAVAILABLE"
        balanced_reaction = ""
        stoich_notes: List[str] = []
        stoich = _stoichiometry_check(route)
        if stoich is not None:
            stoich_status = stoich.status
            balanced_reaction = stoich.reaction
            stoich_notes = list(stoich.warnings)
            if stoich.status == "SKIPPED":
                stoich_notes.append(stoich.reason)
            elif stoich.status == "UNBALANCED":
                stoich_notes.append(
                    "element balance impossible for: "
                    + ", ".join(stoich.unbalanced_elements))
                composite = 0.0

        return ScoredRoute(
            route=route,
            feasibility_score=round(feas, 4),
            cost_score=round(cost, 4),
            time_score=round(time, 4),
            safety_score=round(safe, 4),
            composite_score=round(composite, 4),
            bottleneck_step=bottleneck,
            missing_precursors=missing_prec,
            missing_equipment=missing_eq,
            stoichiometry_status=stoich_status,
            balanced_reaction=balanced_reaction,
            stoichiometry_notes=stoich_notes,
        )

    def plan_synthesis(
        self,
        target: str,
        available_equipment: Optional[List[str]] = None,
    ) -> SynthesisAnalysis:
        """
        Given a target material, find and rank synthesis routes.

        Args:
            target: Target material name (e.g., 'LFP', 'NMC811')
            available_equipment: Optional list of available equipment

        Returns:
            SynthesisAnalysis with ranked routes
        """
        warnings = []
        routes = get_routes(target)

        if not routes:
            return SynthesisAnalysis(
                target=target,
                routes=[],
                best_route=None,
                precursor_cost_usd=0.0,
                total_time_hours=0.0,
                equipment_needed=[],
                warnings=[f"No synthesis routes found for target: {target}"],
            )

        scored = []
        for route in routes:
            sr = self.score_route(route, available_equipment)
            scored.append(sr)

        # Sort by composite score (highest first)
        scored.sort(key=lambda s: s.composite_score, reverse=True)

        best = scored[0]

        # Collect warnings
        if best.missing_precursors:
            warnings.append(
                f"Missing precursors for best route: {best.missing_precursors}"
            )
        if best.missing_equipment:
            warnings.append(
                f"Missing equipment for best route: {best.missing_equipment}"
            )
        if best.route.risk_level == "high":
            warnings.append(
                f"Best route has HIGH risk level (hazardous materials)"
            )
        if best.stoichiometry_status == "UNBALANCED":
            warnings.append(
                "Best route FAILED stoichiometric validation (element "
                "balance impossible) -- all routes for this target are "
                "vetoed or unscored; do not synthesize as written"
            )

        precursor_cost = estimate_route_cost(best.route.precursors)
        equipment = _collect_equipment(best.route)

        return SynthesisAnalysis(
            target=target,
            routes=scored,
            best_route=best,
            precursor_cost_usd=precursor_cost,
            total_time_hours=best.route.total_time_hours,
            equipment_needed=equipment,
            warnings=warnings,
        )

    def plan_from_spec(
        self,
        spec: MaterialSpec,
    ) -> SynthesisAnalysis:
        """
        Given a specification, find the best target material + route.

        Args:
            spec: MaterialSpec with target_type, required_properties, etc.

        Returns:
            SynthesisAnalysis for the best matching target
        """
        warnings = []

        # Find candidate target materials
        candidates = TARGET_TYPE_MATERIALS.get(spec.target_type, [])
        if not candidates:
            return SynthesisAnalysis(
                target=spec.target_type,
                routes=[],
                best_route=None,
                precursor_cost_usd=0.0,
                total_time_hours=0.0,
                equipment_needed=[],
                warnings=[f"Unknown target type: {spec.target_type}"],
            )

        # Filter by required properties
        matching = []
        for mat in candidates:
            props = MATERIAL_PROPERTIES.get(mat, {})
            ok = True
            for key, req_val in spec.required_properties.items():
                if key.endswith('_min') and key[:-4] in props:
                    if props[key[:-4]] < req_val:
                        ok = False
                elif key.endswith('_max') and key[:-4] in props:
                    if props[key[:-4]] > req_val:
                        ok = False
                elif key in props:
                    if props[key] != req_val:
                        ok = False
            if ok:
                matching.append(mat)

        if not matching:
            matching = candidates
            warnings.append(
                "No materials match all required properties; showing all candidates"
            )

        # Score routes for all matching targets
        all_scored = []
        for mat in matching:
            routes = get_routes(mat)
            for route in routes:
                sr = self.score_route(route, spec.available_equipment)

                # Apply spec constraints
                if spec.budget_usd is not None:
                    cost = estimate_route_cost(route.precursors)
                    if cost > spec.budget_usd:
                        sr = ScoredRoute(
                            route=sr.route,
                            feasibility_score=sr.feasibility_score,
                            cost_score=sr.cost_score * 0.5,
                            time_score=sr.time_score,
                            safety_score=sr.safety_score,
                            composite_score=sr.composite_score * 0.7,
                            bottleneck_step=sr.bottleneck_step,
                            missing_precursors=sr.missing_precursors,
                            missing_equipment=sr.missing_equipment,
                        )

                if spec.max_time_hours is not None:
                    if route.total_time_hours > spec.max_time_hours:
                        sr = ScoredRoute(
                            route=sr.route,
                            feasibility_score=sr.feasibility_score,
                            cost_score=sr.cost_score,
                            time_score=sr.time_score * 0.5,
                            safety_score=sr.safety_score,
                            composite_score=sr.composite_score * 0.7,
                            bottleneck_step=sr.bottleneck_step,
                            missing_precursors=sr.missing_precursors,
                            missing_equipment=sr.missing_equipment,
                        )

                all_scored.append(sr)

        if not all_scored:
            return SynthesisAnalysis(
                target=spec.target_type,
                routes=[],
                best_route=None,
                precursor_cost_usd=0.0,
                total_time_hours=0.0,
                equipment_needed=[],
                warnings=warnings + [f"No synthesis routes found for matching materials"],
            )

        all_scored.sort(key=lambda s: s.composite_score, reverse=True)
        best = all_scored[0]

        precursor_cost = estimate_route_cost(best.route.precursors)
        equipment = _collect_equipment(best.route)

        return SynthesisAnalysis(
            target=best.route.target,
            routes=all_scored,
            best_route=best,
            precursor_cost_usd=precursor_cost,
            total_time_hours=best.route.total_time_hours,
            equipment_needed=equipment,
            warnings=warnings,
        )


# ============================================================================
# Demo
# ============================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("Synthesis Planner Demo")
    print("=" * 65)
    print()

    planner = SynthesisPlanner()

    # Demo 1: Plan synthesis for specific targets
    targets = ["LFP", "NMC811", "LLZO", "LGPS"]
    for target in targets:
        analysis = planner.plan_synthesis(target)
        if analysis.best_route:
            br = analysis.best_route
            print(f"  {target}: {len(analysis.routes)} routes found")
            print(f"    Best: {br.route.name} (score={br.composite_score:.3f})")
            print(f"    Steps: {len(br.route.steps)}, Time: {br.route.total_time_hours}h")
            print(f"    Temp: {br.route.max_temperature_C}C, Risk: {br.route.risk_level}")
            print(f"    Precursors: {br.route.precursors}")
            print(f"    Cost: ${analysis.precursor_cost_usd:.2f}/g")
            if br.bottleneck_step:
                print(f"    Bottleneck: {br.bottleneck_step.operation} "
                      f"(p={br.bottleneck_step.success_probability})")
            if analysis.warnings:
                for w in analysis.warnings:
                    print(f"    WARNING: {w}")
        else:
            print(f"  {target}: No routes found")
            for w in analysis.warnings:
                print(f"    WARNING: {w}")
        print()

    # Demo 2: Plan from specification
    print("-" * 65)
    print("Spec-based planning: 'Make me a cathode with voltage >= 3.0V'")
    print("-" * 65)
    spec = MaterialSpec(
        target_type="cathode",
        required_properties={"voltage_nominal_min": 3.0},
        available_equipment=["furnace", "ball_mill", "stirrer", "oven", "mixer",
                            "mortar", "filter"],
    )
    analysis = planner.plan_from_spec(spec)
    if analysis.best_route:
        br = analysis.best_route
        print(f"  Recommended target: {analysis.target}")
        print(f"  Best route: {br.route.name} (score={br.composite_score:.3f})")
        print(f"  Precursors: {br.route.precursors}")
        print(f"  Steps:")
        for i, step in enumerate(br.route.steps, 1):
            print(f"    {i}. {step.operation}: {step.inputs} -> {step.output}")
            print(f"       T={step.conditions.temperature_C}C, "
                  f"t={step.conditions.time_hours}h, "
                  f"atm={step.conditions.atmosphere}")
    print()
