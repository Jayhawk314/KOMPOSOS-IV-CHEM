# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
"""
SIDE EXPERIMENT — NOT wired into any verdict path.

Compares two ways of scoring the Simplicial-Yoneda neighbour signal, on the
real domain categories, with everything shown so nothing is hidden:

  LEGACY  : unweighted set Jaccard over (neighbour, relation) pairs.
            This is what oracle/simplicial_strategies.score_simplicial_yoneda
            actually returns today (frozen so the 41/41 dev benchmark is not
            disturbed). Morphism confidences are thrown away.

  WEIGHTED: pharm-style confidence-weighted fingerprint + weighted (min/max)
            Jaccard — the same metric KOMPOSOS-IV-PHARM/oracle/yoneda_strategy.py
            uses for drug repurposing, and the same metric chem already computes
            inside _build_formal_yoneda_evidence (presheaf_overlap) but discards
            for scoring.

For every sampled pair we print BOTH scores, the chosen neighbour, and the
underlying shared keys *with their confidences* so you can see exactly why the
two metrics agree or diverge. No production import is modified.

Run:  python -m discovery.yoneda_weighted_experiment            # all domains, 6 pairs each
      python -m discovery.yoneda_weighted_experiment battery 12 # one domain, 12 pairs
"""

from __future__ import annotations

import itertools
import sys
from typing import Dict, List, Set, Tuple

# Reuse the production helpers verbatim — do NOT re-implement the legacy path,
# so this experiment can never silently drift from what ships.
from oracle.simplicial_strategies import (
    build_domain_category,
    _build_formal_yoneda_evidence,
    _compute_yoneda_fingerprint,   # unweighted set of (neighbour, relation)
    _find_compatible_with,
    _jaccard_similarity,           # unweighted Jaccard used by the shipped score
)

DOMAINS = ["battery", "polymer", "metal", "ceramic",
           "semiconductor", "glass", "mof", "molecular"]


# ── Confidence access (III-style category: .morphisms is a dict) ──────────────

def _morphism_conf(m) -> float:
    """Confidence for a III/IV-style morphism (mirrors the production readers)."""
    data = getattr(m, "data", None)
    if isinstance(data, dict):
        return float(data.get("score", data.get("confidence", 1.0)))
    return float(getattr(m, "confidence", 1.0))


def _weighted_fingerprint(obj_name: str, category) -> Dict[Tuple[str, str], float]:
    """Pharm-style presheaf: (neighbour, relation) -> max confidence seen.

    Same key set as _compute_yoneda_fingerprint, but keeps the strongest
    confidence on each edge instead of collapsing to set membership.
    """
    fp: Dict[Tuple[str, str], float] = {}
    morphs = getattr(category, "morphisms", None)
    if isinstance(morphs, dict):
        for m in morphs.values():
            s = m.source.name if hasattr(m.source, "name") else str(m.source)
            t = m.target.name if hasattr(m.target, "name") else str(m.target)
            c = _morphism_conf(m)
            if s == obj_name:
                k = (t, m.name); fp[k] = max(fp.get(k, 0.0), c)
            if t == obj_name:
                k = (s, m.name); fp[k] = max(fp.get(k, 0.0), c)
    return fp


def _weighted_jaccard_sim(fp1: Dict[Tuple[str, str], float],
                          fp2: Dict[Tuple[str, str], float]) -> float:
    """Weighted Jaccard SIMILARITY (1 - distance); identical to pharm's metric."""
    keys = set(fp1) | set(fp2)
    if not keys:
        return 0.0
    inter = sum(min(fp1.get(k, 0.0), fp2.get(k, 0.0)) for k in keys)
    union = sum(max(fp1.get(k, 0.0), fp2.get(k, 0.0)) for k in keys)
    return inter / union if union > 0 else 0.0


# ── Scorers (neighbour semantics identical; only the metric differs) ──────────

def _legacy_neighbour(a: str, b: str, category):
    """Exactly the shipped logic: unweighted Jaccard of A vs each neighbour of B."""
    best_sim, best_n = 0.0, ""
    fp_a = _compute_yoneda_fingerprint(a, category)
    for n in _find_compatible_with(b, category):
        if n == a:
            continue
        sim = _jaccard_similarity(fp_a, _compute_yoneda_fingerprint(n, category))
        if sim > best_sim:
            best_sim, best_n = sim, n
    return best_sim, best_n, (0.5 + 0.5 * best_sim if best_sim > 0 else 0.5)


def _weighted_neighbour(a: str, b: str, category):
    """Same neighbour loop, but confidence-weighted fingerprint + weighted Jaccard."""
    best_sim, best_n = 0.0, ""
    fp_a = _weighted_fingerprint(a, category)
    for n in _find_compatible_with(b, category):
        if n == a:
            continue
        sim = _weighted_jaccard_sim(fp_a, _weighted_fingerprint(n, category))
        if sim > best_sim:
            best_sim, best_n = sim, n
    return best_sim, best_n, (0.5 + 0.5 * best_sim if best_sim > 0 else 0.5)


def _shared_table(a: str, n: str, category) -> List[str]:
    """Show the shared (neighbour, relation) keys with both confidences — full transparency."""
    fa, fn = _weighted_fingerprint(a, category), _weighted_fingerprint(n, category)
    shared = sorted(set(fa) & set(fn))
    return [f"      ({k[0]}, {k[1]}): conf_{a}={fa[k]:.2f}  conf_{n}={fn[k]:.2f}"
            for k in shared]


# ── Object enumeration (III-style) ────────────────────────────────────────────

def _object_names(category) -> List[str]:
    oa = getattr(category, "objects", None)
    if isinstance(oa, dict):
        return list(oa.keys())
    if callable(oa):
        return [getattr(o, "name", str(o)) for o in category.objects()]
    return []


def run_domain(domain: str, n_pairs: int) -> None:
    cat = build_domain_category(domain)
    if cat is None:
        print(f"\n=== {domain}: no category ===")
        return
    names = _object_names(cat)
    pairs = list(itertools.combinations(names, 2))[:n_pairs]

    print(f"\n{'='*78}\nDOMAIN: {domain}   ({len(names)} objects)\n{'='*78}")
    print(f"{'A':12s} {'B':12s} | {'legacy':>7s} {'weighted':>8s}  d_score | neighbour (L / W)")
    print("-" * 78)

    diverged = []
    for a, b in pairs:
        lsim, ln, lscore = _legacy_neighbour(a, b, cat)
        wsim, wn, wscore = _weighted_neighbour(a, b, cat)
        # A-vs-B formal overlap that chem already computes but does not score on:
        try:
            ov = _build_formal_yoneda_evidence(a, b, cat).get("presheaf_overlap", 0.0)
        except Exception:
            ov = float("nan")
        delta = wscore - lscore
        flag = "  <-- diverge" if (ln != wn or abs(delta) >= 0.05) else ""
        print(f"{a:12.12s} {b:12.12s} | {lscore:7.3f} {wscore:8.3f}  {delta:+5.2f} "
              f"| {ln or '-'} / {wn or '-'}  (AB_overlap={ov:.2f}){flag}")
        if flag:
            diverged.append((a, b, ln, wn))

    # For the first couple of divergences, show the shared-key evidence in full.
    for a, b, ln, wn in diverged[:2]:
        print(f"\n  why ({a},{b}) diverges — weighted picked '{wn}':")
        rows = _shared_table(a, wn, cat) if wn else []
        if rows:
            print("    shared (neighbour, relation) keys with confidences:")
            print("\n".join(rows[:12]))
            if len(rows) > 12:
                print(f"      ... (+{len(rows)-12} more)")
        else:
            print("    (no shared keys — weighted score came from elsewhere)")


def main(argv: List[str]) -> None:
    if argv:
        domain = argv[0]
        n = int(argv[1]) if len(argv) > 1 else 12
        run_domain(domain, n)
    else:
        for d in DOMAINS:
            run_domain(d, 6)
    print("\nNote: this is a diagnostic only. Nothing here feeds scores['total'] "
          "or any verdict. Both columns use the SAME neighbour semantics; only "
          "the similarity metric differs (set Jaccard vs confidence-weighted).")


if __name__ == "__main__":
    main(sys.argv[1:])
