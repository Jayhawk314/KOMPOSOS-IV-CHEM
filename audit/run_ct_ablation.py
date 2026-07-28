# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Category-theory ablation for the chemistry compatibility path.

Question: does the categorical layer change PREDICTIVE ACCURACY, or is it
architecture/reporting only?

Two CT surfaces exist in the compatibility path and they have different causal
status, so they are ablated separately:

  A. typed morphisms  -- `_apply_typed_context_score` -> `apply_typed_morphism_adjustment`
     can overwrite score AND verdict (veto / negative_prior / positive_prior).
     Applied to ceramic, semiconductor, glass, ceramic-metal, battery-metal,
     metal-semiconductor, glass-metal, polymer-glass. IN the causal path.

  B. Yoneda transfer guard / strategy ensemble -- `build_compatibility_ensemble`
     is called only from `_compatibility_decision_metadata`, i.e. into REPORTING
     metadata. It never feeds back into score or verdict.

Datasets: development + spent diagnostics ONLY. The current blind set (Q12) is
NOT touched -- running it here would spend it.

Run:
    python audit/run_ct_ablation.py [--json audit/ct_ablation_report.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit import run_audit as RA  # noqa: E402


def _mcc(tp: int, tn: int, fp: int, fn: int) -> float:
    num = tp * tn - fp * fn
    den = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    return num / den if den else 0.0


def _load_pairs():
    """Development + spent-diagnostic pairs. Never the current blind set."""
    audit_dir = Path(__file__).parent
    registry = json.loads((audit_dir / "dataset_registry.json").read_text(encoding="utf-8"))
    blind_version = registry.get("current_blind_version")
    blocked = {
        Path(d["path"]).name
        for d in registry["datasets"]
        if d["version"] == blind_version
    }
    # also block the blind set's sibling files
    blocked |= {n.replace("_pairs_unlabeled", "") for n in blocked}

    pairs, sources = [], []
    dev_pairs, _ = RA._load_development_compatibility_pairs()
    for p in dev_pairs:
        p = dict(p)
        p["dataset_role"] = "development"
        pairs.append(p)
    sources.append(f"development ({len(dev_pairs)} pairs)")

    ext_dir = audit_dir / "external_blind"
    for path in sorted(ext_dir.glob("compatibility_*.json")):
        name = path.name
        if "labels_hidden" in name or "pairs_unlabeled" in name:
            continue
        if any(b in name or name in b for b in blocked):
            print(f"  SKIPPING current-blind dataset: {name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        got = 0
        for p in data.get("pairs", []):
            if "expected_compatible" not in p:
                continue
            p = dict(p)
            p["dataset_role"] = "spent_diagnostic"
            p["source_file"] = name
            pairs.append(p)
            got += 1
        if got:
            sources.append(f"{name} ({got} pairs)")
    return pairs, sources


def _evaluate(pairs, label: str):
    tp = tn = fp = fn = skipped = 0
    verdicts = {}
    for pair in pairs:
        mat_a, mat_b = pair["material_a"], pair["material_b"]
        expected = bool(pair["expected_compatible"])
        domain = pair.get("domain", "")
        key = (domain, mat_a, mat_b, pair.get("source_file", "dev"))
        try:
            context = RA.CompatibilityContext.from_pair(pair)
            score, predicted = RA._evaluate_pair(
                mat_a, mat_b, domain, pair.get("electrolyte"), pair.get("role"), context
            )
        except Exception:
            skipped += 1
            verdicts[key] = None
            continue
        verdicts[key] = (round(float(score), 6), bool(predicted))
        if predicted and expected:
            tp += 1
        elif not predicted and not expected:
            tn += 1
        elif predicted and not expected:
            fp += 1
        else:
            fn += 1
    evaluated = tp + tn + fp + fn
    return {
        "config": label,
        "evaluated": evaluated,
        "skipped": skipped,
        "TP": tp, "TN": tn, "FP": fp, "FN": fn,
        "accuracy": round((tp + tn) / evaluated, 4) if evaluated else 0.0,
        "mcc": round(_mcc(tp, tn, fp, fn), 4),
        "_verdicts": verdicts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    print("=" * 72)
    print("CATEGORY-THEORY ABLATION (chemistry compatibility path)")
    print("=" * 72)
    print("\nDatasets (development + spent diagnostics only; current blind excluded):")
    pairs, sources = _load_pairs()
    for s in sources:
        print(f"  - {s}")
    print(f"  TOTAL: {len(pairs)} pairs")

    # ---- Ablation B, established structurally -------------------------------
    # build_compatibility_ensemble (which carries the yoneda_transfer_guard vote)
    # is referenced ONLY inside _compatibility_decision_metadata, so it cannot
    # affect score or verdict. Verify that structurally rather than by rerunning.
    import inspect
    eval_src = inspect.getsource(RA._evaluate_pair_in_domain)
    ensemble_in_scoring = "build_compatibility_ensemble" in eval_src
    meta_src = inspect.getsource(RA._compatibility_decision_metadata)
    ensemble_in_metadata = "build_compatibility_ensemble" in meta_src

    print("\n" + "-" * 72)
    print("ABLATION B: Yoneda transfer guard / strategy ensemble")
    print("-" * 72)
    print(f"  ensemble called inside scoring path : {ensemble_in_scoring}")
    print(f"  ensemble called inside metadata only: {ensemble_in_metadata}")
    if not ensemble_in_scoring and ensemble_in_metadata:
        print("  => REPORTING ONLY. Cannot affect accuracy by construction;")
        print("     there is no numeric ablation to run for this surface.")

    # ---- Ablation A: typed morphisms ---------------------------------------
    print("\n" + "-" * 72)
    print("ABLATION A: typed-morphism adjustment (in the causal path)")
    print("-" * 72)

    baseline = _evaluate(pairs, "baseline (typed morphisms ON)")

    original = RA._apply_typed_context_score
    RA._apply_typed_context_score = lambda score, predicted, *a, **k: (score, predicted)
    try:
        ablated = _evaluate(pairs, "typed morphisms OFF")
    finally:
        RA._apply_typed_context_score = original

    changed = []
    for key, base_v in baseline["_verdicts"].items():
        abl_v = ablated["_verdicts"].get(key)
        if base_v != abl_v:
            changed.append({
                "domain": key[0], "material_a": key[1], "material_b": key[2],
                "source": key[3],
                "baseline": base_v, "ablated": abl_v,
            })

    hdr = f"{'config':32s} {'eval':>5} {'skip':>5} {'acc':>8} {'MCC':>8}"
    print("\n" + hdr)
    print("-" * len(hdr))
    for r in (baseline, ablated):
        print(f"{r['config']:32s} {r['evaluated']:5d} {r['skipped']:5d} "
              f"{r['accuracy']:8.4f} {r['mcc']:8.4f}")

    d_acc = ablated["accuracy"] - baseline["accuracy"]
    d_mcc = ablated["mcc"] - baseline["mcc"]
    print(f"\n  delta (ablated - baseline): accuracy {d_acc:+.4f}, MCC {d_mcc:+.4f}")
    print(f"  pairs whose (score, verdict) changed: {len(changed)} of {len(pairs)}")

    verdict_flips = [c for c in changed
                     if c["baseline"] and c["ablated"]
                     and c["baseline"][1] != c["ablated"][1]]
    print(f"  pairs whose VERDICT flipped:          {len(verdict_flips)}")
    for c in verdict_flips[:15]:
        print(f"    {c['domain']:20s} {c['material_a']}+{c['material_b']}: "
              f"{c['baseline']} -> {c['ablated']}")

    print("\n" + "=" * 72)
    if len(changed) == 0:
        print("RESULT: the typed-morphism layer changed NOTHING on this corpus.")
        print("No evidence it contributes to predictive accuracy here.")
    elif d_acc == 0 and d_mcc == 0 and not verdict_flips:
        print(f"RESULT: typed morphisms perturbed {len(changed)} score(s) but flipped")
        print("NO verdicts. Accuracy and MCC are IDENTICAL with and without.")
        print("No evidence it contributes to predictive accuracy on this corpus.")
    elif d_acc == 0 and verdict_flips:
        print("RESULT: typed morphisms flipped verdicts in both directions, but")
        print("net accuracy is UNCHANGED on this corpus.")
    elif d_acc < 0:
        print(f"RESULT: ablating typed morphisms HURT accuracy by {-d_acc:.4f}.")
        print("That is evidence the categorical typing layer contributes.")
    else:
        print(f"RESULT: ablating typed morphisms IMPROVED accuracy by {d_acc:.4f}.")
        print("The categorical typing layer is net-harmful on this corpus.")
    print("=" * 72)
    print("\nSCOPE: development + spent diagnostics only, so this is a")
    print("development-grade finding, NOT a blind result. It measures accuracy")
    print("contribution only -- not architectural value (typed composition,")
    print("provenance, transfer guards) which this experiment does not test.")

    if args.json:
        for r in (baseline, ablated):
            r.pop("_verdicts", None)
        args.json.write_text(json.dumps({
            "scope": "development + spent_diagnostic only; current blind excluded",
            "sources": sources,
            "pair_count": len(pairs),
            "ablation_B_ensemble_reporting_only": (not ensemble_in_scoring) and ensemble_in_metadata,
            "baseline": baseline,
            "typed_morphisms_off": ablated,
            "delta_accuracy": round(d_acc, 4),
            "delta_mcc": round(d_mcc, 4),
            "changed_pairs": changed,
            "verdict_flips": verdict_flips,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
