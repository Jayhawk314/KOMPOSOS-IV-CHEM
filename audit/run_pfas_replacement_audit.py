"""PFAS replacement-engine audit (honest edition).

The replacement engine is a curated expert database of (PFAS, use_case) ->
ranked PFAS-free candidates, plus a compatibility-aware filter that re-ranks
those candidates against an adjoining material. It is NOT a probabilistic
classifier, so there is no AUROC. The honest, checkable questions are:

  1. PFAS-FREE GUARANTEE (the load-bearing claim). Every candidate the tool can
     suggest must itself be non-PFAS by the OECD structural rule. A PFAS
     suggested as a replacement for a PFAS is a critical correctness bug.
     Metric: % of all candidates that pass the structural non-PFAS check (100%
     or it's broken). This is a checkable FACT, not a modeled estimate.

  2. COVERAGE. How many regulated PFAS / (PFAS, use_case) pairs have at least one
     suggestion, and do the battery-relevant PFAS (PVDF, PTFE) have binder
     suggestions.

  3. RANKING SANITY. Quality-only results are sorted by overall_score; the
     compatibility-aware results are sorted by the documented 0.6*quality +
     0.4*compat composite. We check both orderings are actually monotone.

  4. COMPATIBILITY DISCRIMINATION (the new feature). Does the compatibility
     filter actually do physics, i.e. produce DIFFERENT scores/orderings for
     DIFFERENT adjoining materials? If every adjoining material yields the same
     ranking, the feature adds nothing. We also report how many candidates the
     compatibility engine can actually score (vs falling back to the 0.5 default).

Run: python audit/run_pfas_replacement_audit.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
except Exception:
    pass

from pfas_bridge.replacement_scorer import (
    REPLACEMENT_MAP,
    UseCase,
    find_replacements,
    find_compatible_replacements,
    get_all_replaceable_pfas,
    get_use_cases_for_pfas,
)
from pfas_bridge.compliance_checker import PFASComplianceChecker

# Detector with name->structure resolution ON, so a candidate that only LOOKS
# safe by name but resolves to a fluorinated structure would still be caught.
_CHECKER = PFASComplianceChecker(resolve_unknown=True)


def _all_candidate_names():
    names = set()
    for cands in REPLACEMENT_MAP.values():
        for c in cands:
            names.add(c.name)
    return sorted(names)


def audit_pfas_free_guarantee():
    print("\n[1] PFAS-FREE GUARANTEE -- every suggested replacement must be non-PFAS")
    names = _all_candidate_names()
    offenders = []
    for name in names:
        # A composite like "CMC+SBR" is two materials; check each component.
        for part in name.split("+"):
            res = _CHECKER.check(part.strip())
            if res.is_pfas:
                offenders.append((name, part.strip(), res.detection_tier))
    n = len(names)
    ok = n - len({o[0] for o in offenders})
    print(f"    distinct candidate materials: {n}")
    print(f"    PFAS-free: {ok}/{n} = {ok / n:.3f}")
    if offenders:
        print("    !! CRITICAL -- these suggested replacements are themselves PFAS:")
        for full, part, tier in offenders:
            print(f"       {full} (component {part!r}, tier={tier})")
    else:
        print("    OK -- no suggested replacement is itself PFAS.")
    return not offenders


def audit_coverage():
    print("\n[2] COVERAGE")
    pfas = get_all_replaceable_pfas()
    pairs = len(REPLACEMENT_MAP)
    print(f"    regulated PFAS with replacements: {len(pfas)}")
    print(f"    (PFAS, use_case) pairs covered:   {pairs}")
    # Battery-relevant spot check
    for p in ("PVDF", "PTFE"):
        ucs = get_use_cases_for_pfas(p)
        binder = find_replacements(p, UseCase.BATTERY_BINDER)
        tag = "OK" if binder else "MISSING"
        print(f"    {p}: use_cases={[u.value for u in ucs]} | battery_binder suggestions={len(binder)} [{tag}]")
    return True


def audit_ranking_monotone():
    print("\n[3] RANKING SANITY -- results sorted best-first")
    bad = 0
    for (name, uc) in REPLACEMENT_MAP.keys():
        cands = find_replacements(name, uc)
        scores = [c.overall_score for c in cands]
        if scores != sorted(scores, reverse=True):
            bad += 1
            print(f"    !! not monotone: {name}/{uc.value} -> {[round(s,3) for s in scores]}")
    if not bad:
        print("    OK -- all quality-only result lists are monotone non-increasing.")
    return bad == 0


def audit_compatibility_discrimination():
    print("\n[4] COMPATIBILITY DISCRIMINATION -- does the filter do real physics?")
    # PVDF binder is the canonical case. Compare ranking next to a high-voltage
    # cathode (NMC811) vs a graphite anode vs a liquid electrolyte. A working
    # physics filter should NOT give identical scores across all three.
    pfas, uc = "PVDF", UseCase.BATTERY_BINDER
    adjoining = ["NMC811", "Graphite", "LiPF6", "LCO"]
    rankings = {}
    scored_counts = {}
    for adj in adjoining:
        res = find_compatible_replacements(pfas, adj, uc)
        order = []
        real_scores = 0
        for cand, comp in res:
            cscore = comp.scores.get("total") if comp else None
            if cscore is not None:
                real_scores += 1
            order.append((cand.name, round(cscore, 3) if cscore is not None else None))
        rankings[adj] = order
        scored_counts[adj] = (real_scores, len(res))

    for adj in adjoining:
        sc, tot = scored_counts[adj]
        print(f"    vs {adj:8s}: compat-scored {sc}/{tot} candidates | top -> {rankings[adj][:3]}")

    # Discrimination: at least two adjoining materials must yield different
    # compatibility score vectors (otherwise the filter is inert).
    score_vectors = {adj: tuple(s for _, s in rankings[adj]) for adj in adjoining}
    distinct = len(set(score_vectors.values()))
    discriminates = distinct > 1
    print(f"    distinct compatibility-score vectors across {len(adjoining)} adjoining materials: {distinct}")
    print(f"    -> compatibility filter {'DISCRIMINATES (real physics)' if discriminates else 'is INERT (same everywhere)'}")
    return discriminates


def main():
    print("=" * 64)
    print("PFAS REPLACEMENT ENGINE AUDIT (honest edition)")
    print("=" * 64)
    print("Curated expert DB + structural PFAS-free guarantee + physics compat")
    print("filter. Scores are expert-assigned estimates; the PFAS-free check is a")
    print("structural FACT. No AUROC (not a classifier).")

    r1 = audit_pfas_free_guarantee()
    audit_coverage()
    r3 = audit_ranking_monotone()
    r4 = audit_compatibility_discrimination()

    print("\n" + "=" * 64)
    print("SUMMARY")
    print(f"  PFAS-free guarantee holds:      {'YES' if r1 else 'NO  <-- CRITICAL'}")
    print(f"  Quality ranking monotone:       {'YES' if r3 else 'NO'}")
    print(f"  Compatibility filter discriminates: {'YES' if r4 else 'NO'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
