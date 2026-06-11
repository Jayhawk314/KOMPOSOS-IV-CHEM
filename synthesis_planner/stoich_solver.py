# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Stoichiometric SMT Solver (SACE prototype)
==========================================

Element-balance audit for the curated synthesis routes using Z3.

For each route in ``route_graph`` the solver asks: does there exist a
non-negative stoichiometry (one coefficient per leaf precursor, plus allowed
volatile/soluble byproducts) such that every element balances between the
leaf precursors and one formula unit of the target?

Verdict semantics (evidence-provider rules, same as other bridges):

- ``BALANCED``   -- SAT: a balanced equation exists. The displayed equation is
  the *minimum-total-byproduct* witness, NOT a mechanism or yield claim.
- ``UNBALANCED`` -- UNSAT: no assignment balances; this is a hard veto. The Z3
  unsat core names the element(s) that cannot balance.
- ``SKIPPED``    -- target or an input is a composite/mixture (electrode,
  polymer film, coated stack) with no stoichiometric formula; element balance
  is not defined for it.

Scope honesty: element balance cannot check redox feasibility, kinetics,
phase purity, or yields. One heuristic warning is layered on top: if balance
*requires* net O2 release while every high-temperature step runs under inert
atmosphere, the route is flagged for a possibly missing reductant/oxygen sink.

Run the audit:

    python -m synthesis_planner.stoich_solver [--json out.json]
    python audit\\run_stoich_audit.py
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from fractions import Fraction
from math import lcm
from typing import Dict, List, Optional, Sequence, Tuple, Union

import z3

from .precursor_db import ALL_PRECURSORS
from .route_graph import ALL_ROUTES, SynthesisRoute

Composition = Dict[str, Fraction]


# ============================================================================
# Formula parsing
# ============================================================================

class FormulaError(ValueError):
    """Formula string is not a parseable stoichiometric composition."""


_ELEMENTS = frozenset((
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co "
    "Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb "
    "Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re "
    "Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es "
    "Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og"
).split())

_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def _read_count(s: str, i: int) -> Tuple[Fraction, int]:
    m = _NUM_RE.match(s, i)
    if m is None:
        return Fraction(1), i
    return Fraction(m.group(0)), m.end()


def _parse_group(s: str, i: int) -> Tuple[Composition, int]:
    counts: Dict[str, Fraction] = {}

    def _bump(el: str, n: Fraction) -> None:
        counts[el] = counts.get(el, Fraction(0)) + n

    while i < len(s):
        c = s[i]
        if c == "(":
            inner, i = _parse_group(s, i + 1)
            if i >= len(s) or s[i] != ")":
                raise FormulaError(f"unbalanced parentheses in {s!r}")
            mult, i = _read_count(s, i + 1)
            for el, n in inner.items():
                _bump(el, n * mult)
        elif c == ")":
            return counts, i
        elif c.isupper():
            sym = c
            if i + 1 < len(s) and s[i + 1].islower() and s[i:i + 2] in _ELEMENTS:
                sym = s[i:i + 2]
            if sym not in _ELEMENTS:
                raise FormulaError(f"unknown element {sym!r} in {s!r}")
            n, i = _read_count(s, i + len(sym))
            _bump(sym, n)
        else:
            raise FormulaError(f"unexpected character {c!r} in {s!r}")
    return counts, i


def parse_formula(formula: str) -> Composition:
    """Parse a formula (parens, decimal subscripts, ``*``/``·`` hydrates) into
    exact per-element Fraction counts. Raises FormulaError if not parseable."""
    s = formula.strip().replace("·", "*")
    if s.endswith("(aq)"):
        s = s[:-4]
    if not s:
        raise FormulaError("empty formula")
    total: Dict[str, Fraction] = {}
    for part in s.split("*"):
        part = part.strip()
        if not part:
            raise FormulaError(f"empty hydrate fragment in {formula!r}")
        mult, j = _read_count(part, 0)
        counts, end = _parse_group(part, j)
        if end != len(part) or not counts:
            raise FormulaError(f"could not parse {formula!r}")
        for el, n in counts.items():
            total[el] = total.get(el, Fraction(0)) + mult * n
    return total


# ============================================================================
# Material resolution (route names -> compositions)
# ============================================================================

# Targets with a defined stoichiometric formula. Everything else (electrodes,
# polymer films, coated stacks) is honestly SKIPPED, not force-balanced.
_F = Fraction
TARGETS: Dict[str, Tuple[Union[str, Composition], str]] = {
    "LFP": ("LiFePO4", "LiFePO4"),
    "NMC811": ("LiNi0.8Mn0.1Co0.1O2", "LiNi0.8Mn0.1Co0.1O2"),
    "NMC622": ("LiNi0.6Mn0.2Co0.2O2", "LiNi0.6Mn0.2Co0.2O2"),
    "NMC111": ({"Li": _F(1), "Ni": _F(1, 3), "Mn": _F(1, 3), "Co": _F(1, 3),
                "O": _F(2)}, "LiNi1/3Mn1/3Co1/3O2"),
    "NCA": ("LiNi0.8Co0.15Al0.05O2", "LiNi0.8Co0.15Al0.05O2"),
    "LCO": ("LiCoO2", "LiCoO2"),
    "LMO": ("LiMn2O4", "LiMn2O4"),
    "LLZO": ("Li7La3Zr2O12", "Li7La3Zr2O12"),
    "LGPS": ("Li10GeP2S12", "Li10GeP2S12"),
    "Li3PS4": ("Li3PS4", "Li3PS4"),
    "NASICON": ("Na3Zr2Si2PO12", "Na3Zr2Si2PO12"),
    "Al2O3": ("Al2O3", "Al2O3"),
    "Al2O3_coating": ("Al2O3", "Al2O3"),
    "TiN_coating": ("TiN", "TiN"),
    "SiC": ("SiC", "SiC"),
}

# Inputs that are processing media, not reagents of the target's composition.
PROCESS_AIDS: Dict[str, str] = {
    "DI_water": "process water (wash/dispersion)",
    "NMP": "solvent, evaporated",
    "acetonitrile": "solvent, evaporated",
    "acetone": "solvent, evaporated",
    "ethanol": "solvent, evaporated",
    "NaOH_solution": "Bayer liquor, regenerated in the cycle",
    "Ar_gas": "inert gas",
    "Cu_foil": "substrate",
    "Al_foil": "substrate",
    "substrate_metal": "substrate",
    "Inconel_substrate": "substrate",
    "MCrAlY_powder": "bond-coat layer, separate from target coating",
}

# Approximate compositions for industrial-grade inputs.
INPUT_OVERRIDES: Dict[str, Tuple[str, str]] = {
    "bauxite": ("Al2O3*3H2O", "bauxite approximated as gibbsite Al2O3*3H2O"),
    "petroleum_coke": ("C", "petroleum coke approximated as pure carbon"),
}

# Volatile / soluble escapes allowed on the product side. A species is only
# activated when ALL of its elements occur in the route's element universe,
# so e.g. Li2SO4 is available to the hydrothermal LFP route (Li+S present)
# but never to sulfur-free lithium routes.
AUX_OUTPUT_SPECIES: List[str] = [
    "H2O", "CO2", "CO", "O2", "N2", "NH3", "NO", "NO2",
    "SO2", "H2S", "Na2SO4", "Li2SO4", "(NH4)2SO4",
]

OXIDIZING_ATMOSPHERES = {"air", "O2", "dry_room"}
INERT_ATMOSPHERES = {"N2", "Ar", "vacuum"}
AQUEOUS_OPERATIONS = {"dissolve", "coprecipitate", "precipitate", "wash",
                      "hydrothermal", "gel"}
HIGH_T_CELSIUS = 150.0


def resolve_material(name: str) -> Optional[Tuple[Composition, str, str]]:
    """Resolve a route input name to (composition, approximation_note, display).

    Order: explicit override -> precursor DB formula -> the name itself as a
    formula. Returns None when nothing yields a stoichiometric composition.
    `display` is the formula actually balanced (e.g. the hydrate
    ``NiSO4*6H2O`` for the input name ``NiSO4``), so the shown equation and
    its water count are consistent.
    """
    if name in INPUT_OVERRIDES:
        formula, note = INPUT_OVERRIDES[name]
        return parse_formula(formula), note, name
    prec = ALL_PRECURSORS.get(name)
    if prec is not None:
        try:
            return parse_formula(prec.formula), "", prec.formula
        except FormulaError:
            pass
    try:
        return parse_formula(name), "", name
    except FormulaError:
        return None


# ============================================================================
# Z3 balance core
# ============================================================================

@dataclass
class BalanceResult:
    status: str                                   # sat | sat_unused | unsat
    coefficients: Dict[str, Fraction] = field(default_factory=dict)
    aux_in: Dict[str, Fraction] = field(default_factory=dict)
    aux_out: Dict[str, Fraction] = field(default_factory=dict)
    zero_inputs: List[str] = field(default_factory=list)
    unbalanced_elements: List[str] = field(default_factory=list)


def _rv(fr: Fraction):
    return z3.RealVal(f"{fr.numerator}/{fr.denominator}")


def _model_fraction(model: z3.ModelRef, var) -> Fraction:
    val = model.eval(var, model_completion=True)
    return Fraction(val.numerator_as_long(), val.denominator_as_long())


def solve_balance(precursors: Dict[str, Composition],
                  target: Composition,
                  aux_inputs: Sequence[str] = (),
                  aux_outputs: Sequence[str] = ()) -> BalanceResult:
    """Existence of a non-negative stoichiometry reaching 1 formula unit of
    `target` from `precursors`, with optional auxiliary species.

    Phase 1 requires every listed precursor to actually be consumed (> 0):
    a recipe should not list inert ingredients. If that is UNSAT, phase 2
    relaxes to >= 0 and reports which inputs were forced to zero. If still
    UNSAT the unsat core names the elements that cannot balance.
    """
    aux_in_comp = {f: parse_formula(f) for f in aux_inputs}
    aux_out_comp = {f: parse_formula(f) for f in aux_outputs}
    elements = sorted(set(target)
                      | {el for c in precursors.values() for el in c})

    def _build(solver, strict: bool):
        xs = {n: z3.Real(f"x[{n}]") for n in precursors}
        ai = {n: z3.Real(f"in[{n}]") for n in aux_in_comp}
        ao = {n: z3.Real(f"out[{n}]") for n in aux_out_comp}
        for v in xs.values():
            solver.add(v > 0 if strict else v >= 0)
        for v in list(ai.values()) + list(ao.values()):
            solver.add(v >= 0)
        eqs = {}
        for el in elements:
            lhs = z3.RealVal(0)
            for n, v in xs.items():
                lhs = lhs + v * _rv(precursors[n].get(el, Fraction(0)))
            for n, v in ai.items():
                lhs = lhs + v * _rv(aux_in_comp[n].get(el, Fraction(0)))
            rhs = _rv(target.get(el, Fraction(0)))
            for n, v in ao.items():
                rhs = rhs + v * _rv(aux_out_comp[n].get(el, Fraction(0)))
            eqs[el] = lhs == rhs
        return xs, ai, ao, eqs

    def _check(strict: bool) -> bool:
        s = z3.Solver()
        _, _, _, eqs = _build(s, strict)
        for el, eq in eqs.items():
            s.assert_and_track(eq, z3.Bool(f"balance[{el}]"))
        if s.check() == z3.sat:
            return True
        _check.core = [str(b)[len("balance["):-1] for b in s.unsat_core()]
        return False

    def _optimize(strict: bool) -> Tuple[Dict[str, Fraction],
                                         Dict[str, Fraction],
                                         Dict[str, Fraction]]:
        # Second pass: among the feasible stoichiometries pick a clean
        # witness, lexicographically: (1) minimize forced O2 release --
        # spontaneous O2 evolution is the least plausible escape, so it is
        # used only when balance truly demands it (this is also what the
        # redox warning keys on); (2) minimize total auxiliary moles to
        # avoid spurious in/out cycling of H2O or O2.
        opt = z3.Optimize()
        xs, ai, ao, eqs = _build(opt, strict)
        for eq in eqs.values():
            opt.add(eq)
        if "O2" in ao:
            opt.minimize(ao["O2"])
        total_aux = z3.RealVal(0)
        for v in list(ai.values()) + list(ao.values()):
            total_aux = total_aux + v
        opt.minimize(total_aux)
        assert opt.check() == z3.sat
        m = opt.model()
        return ({n: _model_fraction(m, v) for n, v in xs.items()},
                {n: _model_fraction(m, v) for n, v in ai.items()},
                {n: _model_fraction(m, v) for n, v in ao.items()})

    if _check(strict=True):
        coeffs, ain, aout = _optimize(strict=True)
        return BalanceResult("sat", coeffs, ain, aout)
    if _check(strict=False):
        coeffs, ain, aout = _optimize(strict=False)
        zeros = [n for n, c in coeffs.items() if c == 0]
        return BalanceResult("sat_unused", coeffs, ain, aout,
                             zero_inputs=zeros)
    return BalanceResult("unsat",
                         unbalanced_elements=sorted(_check.core))


# ============================================================================
# Route-level audit
# ============================================================================

@dataclass
class RouteAudit:
    route: str
    target: str
    status: str                                   # BALANCED | BALANCED_UNUSED_INPUTS | UNBALANCED | SKIPPED
    target_formula: str = ""
    reason: str = ""
    reaction: str = ""
    process_aids: List[str] = field(default_factory=list)
    approximations: List[str] = field(default_factory=list)
    unused_inputs: List[str] = field(default_factory=list)
    unbalanced_elements: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "route": self.route,
            "target": self.target,
            "status": self.status,
            "target_formula": self.target_formula,
            "reason": self.reason,
            "reaction": self.reaction,
            "process_aids": self.process_aids,
            "approximations": self.approximations,
            "unused_inputs": self.unused_inputs,
            "unbalanced_elements": self.unbalanced_elements,
            "warnings": self.warnings,
        }


def _leaf_inputs(route: SynthesisRoute) -> List[str]:
    produced = {step.output for step in route.steps}
    leaves: List[str] = []
    for step in route.steps:
        for inp in step.inputs:
            if inp not in produced and inp not in leaves:
                leaves.append(inp)
    return leaves


def _fmt_coeff(fr: Fraction) -> str:
    if fr.denominator == 1:
        return "" if fr == 1 else f"{fr.numerator} "
    return f"{fr.numerator}/{fr.denominator} "


def _format_reaction(coeffs: Dict[str, Fraction],
                     aux_in: Dict[str, Fraction],
                     aux_out: Dict[str, Fraction],
                     target_display: str,
                     input_display: Optional[Dict[str, str]] = None) -> str:
    shown = input_display or {}
    terms = ([c for c in coeffs.values() if c > 0]
             + [c for c in aux_in.values() if c > 0]
             + [c for c in aux_out.values() if c > 0]
             + [Fraction(1)])
    scale = Fraction(lcm(*(c.denominator for c in terms)))
    if scale > 48:
        scale = Fraction(1)
    lhs = [f"{_fmt_coeff(c * scale)}{shown.get(n, n)}"
           for n, c in list(coeffs.items()) + list(aux_in.items()) if c > 0]
    rhs = [f"{_fmt_coeff(scale)}{target_display}"]
    rhs += [f"{_fmt_coeff(c * scale)}{n}" for n, c in aux_out.items() if c > 0]
    return " + ".join(lhs) + " -> " + " + ".join(rhs)


def audit_route(route: SynthesisRoute) -> RouteAudit:
    """Element-balance audit of one curated route (leaf precursors -> target)."""
    if route.target not in TARGETS:
        return RouteAudit(route.name, route.target, "SKIPPED",
                          reason="composite/mixture target -- no single "
                                 "stoichiometric formula; balance undefined")
    spec, display = TARGETS[route.target]
    target_comp = parse_formula(spec) if isinstance(spec, str) else spec

    reactive: Dict[str, Composition] = {}
    input_display: Dict[str, str] = {}
    aids: List[str] = []
    approx: List[str] = []
    for name in _leaf_inputs(route):
        if name in PROCESS_AIDS:
            aids.append(f"{name} ({PROCESS_AIDS[name]})")
            continue
        resolved = resolve_material(name)
        if resolved is None:
            return RouteAudit(route.name, route.target, "SKIPPED",
                              target_formula=display,
                              reason=f"input '{name}' has no parseable "
                                     "stoichiometric formula")
        comp, note, shown = resolved
        if note:
            approx.append(note)
        reactive[name] = comp
        input_display[name] = shown
    if not reactive:
        return RouteAudit(route.name, route.target, "SKIPPED",
                          target_formula=display,
                          reason="no reactive stoichiometric inputs")

    universe = set(target_comp)
    for comp in reactive.values():
        universe |= set(comp)

    high_t = [s for s in route.steps
              if s.conditions.temperature_C >= HIGH_T_CELSIUS]
    oxidizing_high_t = any(s.conditions.atmosphere in OXIDIZING_ATMOSPHERES
                           for s in high_t)
    aqueous = any(s.operation in AQUEOUS_OPERATIONS for s in route.steps)

    reducing_context = (any("reduction" in s.operation for s in route.steps)
                        or (bool(high_t)
                            and all(s.conditions.atmosphere in INERT_ATMOSPHERES
                                    for s in high_t)))
    aux_out = [sp for sp in AUX_OUTPUT_SPECIES
               if set(parse_formula(sp)) <= universe]
    # Chemistry gates on implausible escapes: H2S only exists as an escape in
    # oxygen-free (sulfide) systems; CO only under a reducing context
    # (carbothermal step or inert high-temperature processing).
    if "O" in universe:
        aux_out = [sp for sp in aux_out if sp != "H2S"]
    if not reducing_context:
        aux_out = [sp for sp in aux_out if sp != "CO"]
    aux_in: List[str] = []
    if oxidizing_high_t and "O" in universe:
        aux_in.append("O2")
    if aqueous and {"H", "O"} <= universe:
        aux_in.append("H2O")

    result = solve_balance(reactive, target_comp, aux_in, aux_out)

    if result.status == "unsat":
        return RouteAudit(route.name, route.target, "UNBALANCED",
                          target_formula=display, process_aids=aids,
                          approximations=approx,
                          unbalanced_elements=result.unbalanced_elements)

    warnings: List[str] = []
    if (result.aux_out.get("O2", Fraction(0)) > 0 and high_t
            and all(s.conditions.atmosphere in INERT_ATMOSPHERES
                    for s in high_t)):
        warnings.append(
            "balance requires net O2 release while every high-temperature "
            "step is inert (N2/Ar/vacuum) -- check for a missing reductant "
            "or oxygen sink")
    status = "BALANCED" if result.status == "sat" else "BALANCED_UNUSED_INPUTS"
    return RouteAudit(route.name, route.target, status,
                      target_formula=display,
                      reaction=_format_reaction(result.coefficients,
                                                result.aux_in, result.aux_out,
                                                display, input_display),
                      process_aids=aids, approximations=approx,
                      unused_inputs=result.zero_inputs, warnings=warnings)


def run_balance_audit() -> List[RouteAudit]:
    """Audit every curated route in registry order."""
    return [audit_route(route)
            for routes in ALL_ROUTES.values() for route in routes]


# ============================================================================
# CLI
# ============================================================================

_STATUS_TAG = {
    "BALANCED": "[BALANCED]  ",
    "BALANCED_UNUSED_INPUTS": "[BAL/UNUSED]",
    "UNBALANCED": "[UNBALANCED]",
    "SKIPPED": "[SKIPPED]   ",
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Z3 element-balance audit of curated synthesis routes")
    parser.add_argument("--json", metavar="PATH",
                        help="also write the full report as JSON")
    args = parser.parse_args(argv)

    results = run_balance_audit()
    print("=" * 72)
    print(" Stoichiometric balance audit (Z3) -- curated synthesis routes")
    print("=" * 72)
    for r in results:
        head = f"{_STATUS_TAG[r.status]} {r.route} -> {r.target}"
        if r.target_formula and r.target_formula != r.target:
            head += f" ({r.target_formula})"
        print(head)
        if r.reaction:
            print(f"    reaction: {r.reaction}")
        if r.reason:
            print(f"    reason:   {r.reason}")
        if r.unbalanced_elements:
            print(f"    cannot balance: {', '.join(r.unbalanced_elements)}")
        if r.unused_inputs:
            print(f"    unused inputs:  {', '.join(r.unused_inputs)}")
        for note in r.approximations:
            print(f"    approx:   {note}")
        for w in r.warnings:
            print(f"    WARNING:  {w}")
    counts = {s: sum(1 for r in results if r.status == s) for s in _STATUS_TAG}
    print("-" * 72)
    print(f"{len(results)} routes: {counts['BALANCED']} balanced, "
          f"{counts['BALANCED_UNUSED_INPUTS']} balanced-with-unused-inputs, "
          f"{counts['UNBALANCED']} unbalanced, {counts['SKIPPED']} skipped")
    print("Balanced = element-balance feasibility evidence only; "
          "UNBALANCED = hard veto.")

    if args.json:
        report = {"audit": "stoichiometric_balance",
                  "solver": f"z3 {z3.get_version_string()}",
                  "results": [r.to_dict() for r in results],
                  "summary": counts}
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"JSON report written to {args.json}")

    return 1 if counts["UNBALANCED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
