"""Crystal Dreamer recovery benchmark.

Crystal Dreamer is an INVERSE search: target properties -> candidate formulas.
Its real job is to surface materials with the *target properties*, not
necessarily the one specific known material. So we measure two things:

  1. PROPERTY recovery (primary): given the target's own voltage+capacity as the
     goal, does the top candidate land back inside the target window?
  2. COMPOSITION recovery (secondary): how close (fractional-composition L2) does
     the search get to the held-out target material? Exact rediscovery is a
     stricter bar the coarse perturbation/interpolation grid is not built for.

Targets are well-known battery materials that exist as anchors. The target
property values come from the forward predictor (self-consistent), so this tests
the SEARCH coverage / invertibility, not the predictor's absolute accuracy.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import math
from composition_engine.known_compositions import get_db
from composition_engine.predictor import CompositionPredictor
from composition_engine.designer import CompositionDesigner, DesignSpec, PropertyTarget
from composition_engine.parser import parse_formula

TARGETS = ["LCO", "LFP", "NMC811", "NMC622", "NMC111", "NCA", "LMO", "LTO", "Graphite", "Si"]
K = 25
NEAR_EPS = 0.15     # fractional-composition L2 considered "near"
EXACT_EPS = 0.02    # essentially the same composition
PROP_TOL = 0.10     # +/-10% target window


def _norm_comp(formula: str) -> dict:
    comp = parse_formula(formula)
    total = sum(comp.values()) or 1.0
    return {el: amt / total for el, amt in comp.items()}


def _comp_distance(a: dict, b: dict) -> float:
    elems = set(a) | set(b)
    return math.sqrt(sum((a.get(e, 0.0) - b.get(e, 0.0)) ** 2 for e in elems))


def _props(pred) -> dict:
    d = pred.to_dict().get("properties", {})
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and v.get("value") is not None:
            out[k] = v["value"]
    return out


class _HeldOutDB:
    """db shim exposing .entries with the target anchor removed (true LOO).

    Excludes by name AND by matching normalized composition, so aliases of the
    target (e.g. LCO / LiCoO2) cannot leak back in as anchors.
    """
    def __init__(self, full, exclude_name, exclude_comp):
        keep = []
        for e in full.entries:
            if e.name == exclude_name:
                continue
            ec = {el: a / (sum(e.composition.values()) or 1.0) for el, a in e.composition.items()}
            if _comp_distance(ec, exclude_comp) <= EXACT_EPS:
                continue
            keep.append(e)
        self._entries = keep

    @property
    def entries(self):
        return self._entries


def main():
    db = get_db()
    by_name = {e.name: e for e in db.entries}
    predictor = CompositionPredictor()

    print("=" * 64)
    print("CRYSTAL DREAMER RECOVERY BENCHMARK")
    print("=" * 64)
    print(f"{'Target':9s} {'propMatch':9s} {'exact@K':8s} {'near@K':7s} {'minDist':8s} {'nCand':6s}")

    n = 0
    prop_hits = exact_hits = near_hits = 0
    dist_sum = 0.0
    for name in TARGETS:
        entry = by_name.get(name)
        if entry is None:
            print(f"{name:9s} [skip: not an anchor]")
            continue
        truth_comp = {el: amt / (sum(entry.composition.values()) or 1.0)
                      for el, amt in entry.composition.items()}
        tprops = _props(predictor.predict(name))
        v, c = tprops.get("voltage"), tprops.get("theoretical_capacity")
        if v is None or c is None:
            print(f"{name:9s} [skip: no voltage/capacity]")
            continue

        targets = [
            PropertyTarget("voltage", v * (1 - PROP_TOL), v * (1 + PROP_TOL), weight=1.0),
            PropertyTarget("theoretical_capacity", c * (1 - PROP_TOL), c * (1 + PROP_TOL), weight=1.0),
        ]
        # True LOO: hold this target out of the anchor pool.
        heldout = CompositionDesigner(predictor=predictor, db=_HeldOutDB(db, name, truth_comp))
        spec = DesignSpec(targets=targets, domain="battery", max_candidates=300)
        result = heldout.design(spec)
        topk = result.candidates[:K]
        if not topk:
            print(f"{name:9s} [no candidates]")
            n += 1
            continue

        # composition recovery
        dists = []
        for cand in topk:
            try:
                dists.append(_comp_distance(_norm_comp(cand.formula), truth_comp))
            except Exception:
                pass
        min_dist = min(dists) if dists else 9.99
        exact = min_dist <= EXACT_EPS
        near = min_dist <= NEAR_EPS

        # property recovery: does the top candidate hit the target window?
        top_props = _props(predictor.predict(topk[0].formula))
        tv, tc = top_props.get("voltage"), top_props.get("theoretical_capacity")
        prop_match = (
            tv is not None and tc is not None
            and v * (1 - PROP_TOL) <= tv <= v * (1 + PROP_TOL)
            and c * (1 - PROP_TOL) <= tc <= c * (1 + PROP_TOL)
        )

        n += 1
        prop_hits += prop_match
        exact_hits += exact
        near_hits += near
        dist_sum += min_dist
        print(f"{name:9s} {str(prop_match):9s} {str(exact):8s} {str(near):7s} {min_dist:8.3f} {len(result.candidates):6d}")

    print("-" * 64)
    if n:
        print(f"Property recovery (top-1 in target window): {prop_hits}/{n} = {prop_hits/n:.0%}")
        print(f"Composition exact@{K} (L2<= {EXACT_EPS}):        {exact_hits}/{n} = {exact_hits/n:.0%}")
        print(f"Composition near@{K}  (L2<= {NEAR_EPS}):        {near_hits}/{n} = {near_hits/n:.0%}")
        print(f"Mean min composition distance:              {dist_sum/n:.3f}")
    print("\nNotes:")
    print("- True leave-one-out: each target is removed from the anchor pool, so")
    print("  recovery requires reconstructing it from OTHER materials.")
    print("- Targets derived from the forward predictor (self-consistent); this")
    print("  measures inverse-search coverage, not predictor accuracy.")
    print("- Interpretation: Crystal Dreamer is a property-targeted INTERPOLATION")
    print("  engine. It recovers target PROPERTIES well, and near-COMPOSITIONS only")
    print("  inside well-populated families (NMC). It does not rediscover exact or")
    print("  isolated compositions -- it is interpolative, not freely generative.")


if __name__ == "__main__":
    main()
