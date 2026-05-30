"""P4 — Run the benchmark and write the report.

Measures, on the frozen held-out eval reals vs. each decoy class:
  - per-gate recall on real synthesized linkers (the honesty check),
  - AUROC (reals vs. each decoy class), overall and restricted to 22 atoms,
  - the novelty-validity frontier for generated candidates.

The SAscore threshold (G3) is derived from SEED reals only (95th percentile),
never from eval. Nothing here tunes on eval.

Run:
    python -m mof_bridge.benchmark.run
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Dict, List

import sys, os
from mof_bridge.benchmark.funnel import evaluate, morgan_fp
from rdkit.Chem import RDConfig
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer
from rdkit import Chem

_ROOT = Path(__file__).resolve().parent.parent.parent
_DIR = _ROOT / "data" / "benchmark" / "mof_linkers"
_CORPUS = _DIR / "linker_corpus.json"
_SPLIT = _DIR / "seed_eval_split.json"
_DECOYS = _DIR / "decoys.json"
_REPORT_JSON = _DIR / "benchmark_report.json"
_REPORT_MD = _ROOT / "docs" / "MOF_LINKER_BENCHMARK_RESULTS.md"


def _auroc(pos: List[float], neg: List[float]) -> float:
    """Mann-Whitney AUROC with tie handling."""
    if not pos or not neg:
        return float("nan")
    data = [(s, 1) for s in pos] + [(s, 0) for s in neg]
    data.sort(key=lambda x: x[0])
    ranks = [0.0] * len(data)
    i = 0
    while i < len(data):
        j = i
        while j + 1 < len(data) and data[j + 1][0] == data[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_pos = sum(r for r, (_, lab) in zip(ranks, data) if lab == 1)
    n_pos, n_neg = len(pos), len(neg)
    return (rank_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _load():
    corpus = {lk["canonical_smiles"]: lk for lk in json.loads(_CORPUS.read_text())["linkers"]}
    split = json.loads(_SPLIT.read_text())
    decoys = json.loads(_DECOYS.read_text())
    seed = [corpus[s] for s in split["seed"]["smiles"] if s in corpus]
    eval_ = [corpus[s] for s in split["eval"]["smiles"] if s in corpus]
    return seed, eval_, decoys


def _sa_threshold(seed: List[dict]) -> float:
    scores = []
    for lk in seed:
        m = Chem.MolFromSmiles(lk["canonical_smiles"])
        if m:
            scores.append(sascorer.calculateScore(m))
    scores.sort()
    pct95 = scores[max(0, int(0.95 * len(scores)) - 1)] if scores else 6.0
    return round(pct95, 3)


def _recall_funnel(results: List[dict]) -> Dict[str, float]:
    n = len(results) or 1
    return {
        "G1_sanity": round(sum(r["gate_level"] >= 1 for r in results) / n, 4),
        "G2_coordination": round(sum(r["gate_level"] >= 2 for r in results) / n, 4),
        "G3_sascore": round(sum(r["gate_level"] >= 3 for r in results) / n, 4),
        "G4_geometry_passed_all": round(sum(r["passed_all"] for r in results) / n, 4),
    }


def main():
    seed, eval_, decoys = _load()
    sa_thr = _sa_threshold(seed)
    seed_fps = [fp for fp in (morgan_fp(lk["canonical_smiles"]) for lk in seed) if fp is not None]

    def run_set(records):
        return [evaluate(lk["canonical_smiles"], seed_fps, sa_thr) for lk in records]

    eval_res = run_set(eval_)
    decoy_res = {cls: run_set(recs) for cls, recs in decoys["classes"].items()}

    pos_scores = [r["score"] for r in eval_res]
    gold_res = [r for lk, r in zip(eval_, eval_res) if lk.get("tier") == "gold"]
    report = {
        "schema": "mof_linker_benchmark.v1_clean",
        "sa_threshold_from_seed_p95": sa_thr,
        "n_seed": len(seed), "n_eval_real": len(eval_),
        "n_eval_gold": len(gold_res),
        "recall_on_held_out_reals": _recall_funnel(eval_res),
        "recall_on_gold_tier": _recall_funnel(gold_res),
        "auroc_real_vs_decoy": {
            cls: round(_auroc(pos_scores, [r["score"] for r in res]), 4)
            for cls, res in decoy_res.items()
        },
        "decoy_pass_all_rate": {
            cls: round(sum(r["passed_all"] for r in res) / (len(res) or 1), 4)
            for cls, res in decoy_res.items()
        },
    }

    # 22-atom claim
    eval22 = [r for lk, r in zip(eval_, eval_res) if lk["heavy_atom_count"] == 22]
    pos22 = [r["score"] for r in eval22]
    report["claim_22_atom"] = {
        "n_eval_real_22": len(eval22),
        "recall_pass_all_22": round(sum(r["passed_all"] for r in eval22) / (len(eval22) or 1), 4),
        "auroc_22_vs_generator_raw": round(
            _auroc(pos22, [r["score"] for lk, r in zip(decoys["classes"]["generator_raw"], decoy_res["generator_raw"])
                           if lk["heavy_atom_count"] == 22]), 4),
    }

    # Novelty-validity frontier: generated candidates that pass all gates AND are novel
    gen = decoy_res["generator_raw"]
    passed_gen = [r for r in gen if r["passed_all"] and r["max_tanimoto"] is not None]
    novel_passed = [r for r in passed_gen if r["max_tanimoto"] < 0.4]
    report["novelty_frontier_generator"] = {
        "n_generated": len(gen),
        "n_passed_all_gates": len(passed_gen),
        "n_novel_and_passed": len(novel_passed),
        "median_tanimoto_of_passers": round(statistics.median([r["max_tanimoto"] for r in passed_gen]), 3) if passed_gen else None,
    }

    _REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_md(report)
    print(json.dumps(report, indent=2))


def _write_md(r: Dict):
    rc = r["recall_on_held_out_reals"]
    au = r["auroc_real_vs_decoy"]
    c22 = r["claim_22_atom"]
    nf = r["novelty_frontier_generator"]
    md = f"""# MOF Linker Benchmark — Results (v0)

Generated by `mof_bridge/benchmark/run.py`. Spec: `docs/MOF_LINKER_BENCHMARK_SPEC.md`.
Eval split is frozen (`data/benchmark/mof_linkers/seed_eval_split.sha256`).
SAscore gate threshold derived from **seed reals only** (95th pct = {r['sa_threshold_from_seed_p95']}).

## Per-gate recall on held-out REAL linkers ({r['n_eval_real']} eval reals)
A gate that rejects many real synthesized linkers is miscalibrated, not the linker.

| Gate | Recall |
|------|--------|
| G1 chemical sanity (PAINS/Brenk) | {rc['G1_sanity']:.1%} |
| G2 coordination (>=2 sites)      | {rc['G2_coordination']:.1%} |
| G3 SAscore <= {r['sa_threshold_from_seed_p95']}            | {rc['G3_sascore']:.1%} |
| G4 geometry -> passed all gates  | {rc['G4_geometry_passed_all']:.1%} |

## Discrimination (AUROC: real vs. decoy)
| Decoy class | AUROC | decoy pass-all rate |
|-------------|-------|---------------------|
| generator-raw (fair test) | {au['generator_raw']:.3f} | {r['decoy_pass_all_rate']['generator_raw']:.1%} |
| perturbed-real (hard)     | {au['perturbed_real']:.3f} | {r['decoy_pass_all_rate']['perturbed_real']:.1%} |
| random-valid (floor)      | {au['random_valid']:.3f} | {r['decoy_pass_all_rate']['random_valid']:.1%} |

## The 22-atom claim
- Held-out real 22-atom linkers: {c22['n_eval_real_22']}
- Recall (passed all gates): {c22['recall_pass_all_22']:.1%}
- AUROC vs. generator-raw @22: {c22['auroc_22_vs_generator_raw']:.3f}

## Novelty-validity frontier (generated candidates)
- Generated (generator-raw): {nf['n_generated']}
- Passed all gates: {nf['n_passed_all_gates']}
- **Novel (max Tanimoto < 0.4) AND passed all gates: {nf['n_novel_and_passed']}**
- Median nearest-real similarity of passers: {nf['median_tanimoto_of_passers']}

## What this proves / does not prove
- **Proves:** the funnel passes real synthesized linkers it never saw, and ranks
  them above decoys — so its verdicts track real-world synthesizability signals,
  not self-grading.
- **Does NOT prove:** that any specific novel candidate is wet-lab synthesizable.
  A high score means "indistinguishable from real linkers on every computable
  axis," not "guaranteed makeable." SAscore is itself a heuristic; geometry is a
  single conformer; decoys are constructed, not labelled negatives.
"""
    _REPORT_MD.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
