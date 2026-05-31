"""Build compatibility score calibration from non-blind compatibility datasets.

The builder reads audit/dataset_registry.json and uses only datasets marked
development or spent_diagnostic with used_for_calibration=true.  Current blind
datasets, such as Q4, are excluded by design.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from audit.run_audit import (  # noqa: E402
    _benchmark_identity,
    _compute_classification_metrics,
    _evaluate_pair,
    _file_sha256,
    _normalize_pair_provenance,
)
from oracle.compatibility_calibration import BinnedCompatibilityCalibrator  # noqa: E402
from oracle.compatibility_context import CompatibilityContext  # noqa: E402
from oracle.compatibility_decision import CompatibilityDecision  # noqa: E402
from oracle.compatibility_failure_memory import build_failure_memory  # noqa: E402


ALLOWED_ROLES = {"development", "spent_diagnostic"}
EXCLUDED_ROLES = {"current_blind"}


def _load_registry(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_dataset_pairs(project_root: Path, dataset: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    dataset_path = (project_root / dataset["path"]).resolve()
    with dataset_path.open(encoding="utf-8") as f:
        payload = json.load(f)

    pairs = []
    for pair in payload.get("pairs", []):
        loaded = _normalize_pair_provenance(pair)
        loaded["source"] = str(dataset_path.relative_to(project_root))
        loaded["dataset_version"] = payload.get("version") or dataset.get("version")
        loaded["dataset_role"] = dataset["role"]
        pairs.append(loaded)

    metadata = {
        "version": payload.get("version") or dataset.get("version"),
        "path": str(dataset_path.relative_to(project_root)),
        "role": dataset["role"],
        "sha256": _file_sha256(dataset_path),
        "registry_sha256": dataset.get("sha256"),
        "pair_count": len(pairs),
        "used_for_calibration": dataset.get("used_for_calibration"),
    }
    metadata["sha256_matches_registry"] = metadata["sha256"] == metadata["registry_sha256"]
    return pairs, metadata


def _verdict(predicted: bool, expected: bool) -> str:
    if predicted and expected:
        return "TP"
    if not predicted and not expected:
        return "TN"
    if predicted and not expected:
        return "FP"
    return "FN"


def _evaluate_pairs(pairs: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for pair in pairs:
        mat_a = pair["material_a"]
        mat_b = pair["material_b"]
        domain = pair["domain"]
        expected = bool(pair["expected_compatible"])
        context = CompatibilityContext.from_pair(pair)

        try:
            score, predicted = _evaluate_pair(
                mat_a,
                mat_b,
                domain,
                pair.get("electrolyte"),
                pair.get("role"),
                context,
            )
            decision = CompatibilityDecision.from_prediction(
                score,
                predicted,
                metadata={
                    "missing_context": context.missing_required_fields(domain, mat_a, mat_b),
                },
            )
            verdict = _verdict(predicted, expected)
            rows.append({
                "id": pair.get("id"),
                "dataset_version": pair.get("dataset_version"),
                "dataset_role": pair.get("dataset_role"),
                "source": pair.get("source"),
                "domain": domain,
                "material_a": mat_a,
                "material_b": mat_b,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "context": context.to_dict(),
                "score": round(score, 4),
                "predicted_compatible": bool(predicted),
                "expected_compatible": expected,
                "decision_status": decision.status,
                "decision": decision.to_dict(),
                "verdict": verdict,
                "correct": verdict in {"TP", "TN"},
            })
        except Exception as exc:  # Keep calibration build auditable if a scorer fails.
            rows.append({
                "id": pair.get("id"),
                "dataset_version": pair.get("dataset_version"),
                "dataset_role": pair.get("dataset_role"),
                "source": pair.get("source"),
                "domain": domain,
                "material_a": mat_a,
                "material_b": mat_b,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "context": context.to_dict(),
                "score": None,
                "predicted_compatible": None,
                "expected_compatible": expected,
                "decision_status": "no_verdict",
                "decision": CompatibilityDecision.no_verdict(str(exc)).to_dict(),
                "verdict": "SKIP",
                "correct": None,
                "error": str(exc),
            })
    return rows


def _dedupe_rows(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Deduplicate exact pair identities so calibration is not dominated by repeated Q misses."""

    role_priority = {"development": 2, "spent_diagnostic": 1}
    selected: Dict[tuple, Dict[str, Any]] = {}
    duplicates = []

    for row in rows:
        key = _benchmark_identity(row)
        existing = selected.get(key)
        if existing is None:
            selected[key] = row
            continue

        old_priority = role_priority.get(existing.get("dataset_role"), 0)
        new_priority = role_priority.get(row.get("dataset_role"), 0)
        if new_priority > old_priority:
            duplicates.append(existing)
            selected[key] = row
        else:
            duplicates.append(row)

    return list(selected.values()), duplicates


def _isotonic_ece(scores, labels, n_bins: int = 10) -> float:
    import numpy as np

    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=float)
    n = len(scores) or 1
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        mask = (scores >= lo) & (scores < hi if b < n_bins - 1 else scores <= hi)
        if mask.any():
            ece += mask.mean() * abs(scores[mask].mean() - labels[mask].mean())
    return float(ece)


def _fit_isotonic_calibrator(rows: List[Dict[str, Any]], n_folds: int = 5) -> Dict[str, Any]:
    """Fit a global isotonic score->probability calibrator.

    Stored as monotonic (x, y) breakpoints so the runtime can interpolate
    without sklearn. Includes honest k-fold OUT-OF-SAMPLE ECE/Brier so the
    deployed calibration claim is the held-out number, not the in-pool fit.
    Isotonic beat raw/Platt out-of-sample (see audit/fit_compat_calibration.py).
    """
    import numpy as np
    from sklearn.isotonic import IsotonicRegression

    data = [
        (float(r["score"]), 1.0 if r["expected_compatible"] else 0.0)
        for r in rows
        if r.get("score") is not None and r.get("expected_compatible") is not None
    ]
    if len(data) < 10:
        return {"method": "isotonic", "available": False, "reason": "insufficient labeled rows", "n": len(data)}

    S = np.array([d[0] for d in data])
    Y = np.array([d[1] for d in data])

    def brier(scores, labels):
        return float(np.mean((np.asarray(scores) - np.asarray(labels)) ** 2))

    idx = np.arange(len(S))
    oos_e, oos_b = [], []
    for k in range(n_folds):
        test = idx[idx % n_folds == k]
        train = idx[idx % n_folds != k]
        if len(test) == 0 or len(train) == 0 or len(set(Y[train])) < 2:
            continue
        iso = IsotonicRegression(out_of_bounds="clip").fit(S[train], Y[train])
        p = iso.predict(S[test])
        oos_e.append(_isotonic_ece(p, Y[test]))
        oos_b.append(brier(p, Y[test]))

    full = IsotonicRegression(out_of_bounds="clip").fit(S, Y)
    xs = [round(float(x), 6) for x in full.X_thresholds_]
    ys = [round(float(y), 6) for y in full.y_thresholds_]
    return {
        "method": "isotonic",
        "available": True,
        "n": len(data),
        "x": xs,
        "y": ys,
        "oos_ece": round(sum(oos_e) / len(oos_e), 4) if oos_e else None,
        "oos_brier": round(sum(oos_b) / len(oos_b), 4) if oos_b else None,
        "in_pool_ece": round(_isotonic_ece(full.predict(S), Y), 4),
        "raw_ece": round(_isotonic_ece(S, Y), 4),
        "note": "Maps a raw compatibility score to a calibrated probability. "
                "Runtime interpolates linearly between (x, y) breakpoints.",
    }


def _build_domain_calibrators(rows: List[Dict[str, Any]], min_bin_count: int) -> Dict[str, Any]:
    domains: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domains[row["domain"]].append(row)

    payload = {}
    for domain, domain_rows in sorted(domains.items()):
        calibrator = BinnedCompatibilityCalibrator(min_bin_count=min_bin_count).fit(domain_rows)
        payload[domain] = {
            "metrics": _compute_classification_metrics(domain_rows),
            "calibrator": calibrator.to_dict(),
        }
    return payload


def build_calibration(
    registry_path: Path,
    output_path: Path,
    min_bin_count: int = 3,
    dedupe_identities: bool = True,
) -> Dict[str, Any]:
    project_root = registry_path.resolve().parent.parent
    registry = _load_registry(registry_path)

    included_sources = []
    excluded_sources = []
    raw_pairs = []

    for dataset in registry.get("datasets", []):
        role = dataset.get("role")
        if role in EXCLUDED_ROLES or not dataset.get("used_for_calibration", False):
            excluded_sources.append({
                "version": dataset.get("version"),
                "path": dataset.get("path"),
                "role": role,
                "reason": "current blind or not marked for calibration",
            })
            continue
        if role not in ALLOWED_ROLES:
            excluded_sources.append({
                "version": dataset.get("version"),
                "path": dataset.get("path"),
                "role": role,
                "reason": "unsupported calibration role",
            })
            continue

        pairs, metadata = _load_dataset_pairs(project_root, dataset)
        included_sources.append(metadata)
        raw_pairs.extend(pairs)

    raw_rows = _evaluate_pairs(raw_pairs)
    calibration_rows, duplicate_rows = _dedupe_rows(raw_rows) if dedupe_identities else (raw_rows, [])

    global_calibrator = BinnedCompatibilityCalibrator(min_bin_count=min_bin_count).fit(calibration_rows)
    artifact = {
        "version": "compatibility_calibration.2026_q4_dev.v1",
        "created_at": date.today().isoformat(),
        "registry_version": registry.get("version"),
        "purpose": "Binned reliability calibration for compatibility scores using development and spent diagnostic data only.",
        "method": "domain-specific binned reliability with global fallback",
        "exclusion_policy": "Current-blind datasets and datasets with used_for_calibration=false are excluded. Q4 is diagnostic and is not used for calibration.",
        "dedupe_identities": dedupe_identities,
        "min_bin_count": min_bin_count,
        "included_sources": included_sources,
        "excluded_sources": excluded_sources,
        "raw_pair_count": len(raw_pairs),
        "raw_row_count": len(raw_rows),
        "calibration_row_count": len(calibration_rows),
        "duplicate_identity_count": len(duplicate_rows),
        "metrics": _compute_classification_metrics(calibration_rows),
        "failure_memory": build_failure_memory(calibration_rows, dataset_name="compatibility_calibration_2026_q4_dev"),
        "isotonic_calibrator": _fit_isotonic_calibrator(calibration_rows),
        "global_calibrator": global_calibrator.to_dict(),
        "domain_calibrators": _build_domain_calibrators(calibration_rows, min_bin_count),
        "rows": calibration_rows,
        "duplicate_rows_excluded": duplicate_rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2)
        f.write("\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compatibility score calibration from allowed datasets.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).resolve().parent / "dataset_registry.json",
        help="Dataset registry JSON path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "calibration" / "compatibility_calibration_2026_q4_dev.json",
        help="Output calibration artifact path",
    )
    parser.add_argument("--min-bin-count", type=int, default=3)
    parser.add_argument("--no-dedupe", action="store_true", help="Keep duplicate exact pair identities")
    args = parser.parse_args()

    artifact = build_calibration(
        registry_path=args.registry,
        output_path=args.output,
        min_bin_count=args.min_bin_count,
        dedupe_identities=not args.no_dedupe,
    )
    metrics = artifact["metrics"]
    print(f"Wrote calibration artifact: {args.output}")
    print(f"Included sources: {len(artifact['included_sources'])}")
    print(f"Excluded sources: {len(artifact['excluded_sources'])}")
    print(f"Calibration rows: {artifact['calibration_row_count']}")
    print(f"Duplicate identities excluded: {artifact['duplicate_identity_count']}")
    print(
        "Metrics: "
        f"accuracy={metrics['accuracy']:.1%}, "
        f"balanced={metrics['balanced_accuracy']:.1%}, "
        f"brier={metrics['brier_score']:.3f}, "
        f"ece={metrics['expected_calibration_error']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
