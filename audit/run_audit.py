"""
KOMPOSOS-III Scientific & Computational Audit Runner
=====================================================

Runs audit modules and generates a structured report:
  Module 1: Scientific Accuracy (blind test)
  Module 2: Computational Integrity (math verification)
  Module 3: Data Provenance (spot-check)
  Module 4: External Blind Compatibility Validation

Usage:
    python audit/run_audit.py --module all
    python audit/run_audit.py --module scientific
    python audit/run_audit.py --module computational
    python audit/run_audit.py --module provenance
    python audit/run_audit.py --module external
    python audit/run_audit.py --module external --external-path audit/external_blind/compatibility_2026_q6.json
"""

import argparse
import hashlib
import json
import sys
import random
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root on path
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_decision import CompatibilityDecision
from oracle.compatibility_calibration import (
    compute_classification_metrics as _shared_compute_classification_metrics,
)
from oracle.compatibility_ensemble import build_compatibility_ensemble
from oracle.compatibility_failure_memory import build_failure_memory
from oracle.typed_morphisms import apply_typed_morphism_adjustment, infer_typed_morphism


# ---------------------------------------------------------------------------
# Module 1: Scientific Accuracy (Blind Test)
# ---------------------------------------------------------------------------

def _benchmark_identity(pair: Dict[str, Any]) -> tuple:
    """Canonical identity for duplicate detection in symmetric compatibility tests."""
    materials = tuple(sorted((pair.get("material_a"), pair.get("material_b"))))
    return (
        pair.get("domain"),
        materials,
        pair.get("electrolyte"),
    )


def _summarize_benchmark(pairs: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Return protocol-level diagnostics for the loaded benchmark."""
    identities = Counter(_benchmark_identity(pair) for pair in pairs)
    duplicate_groups = [
        {"domain": key[0], "materials": list(key[1]), "electrolyte": key[2], "count": count}
        for key, count in identities.items()
        if count > 1
    ]

    labels_by_identity: dict[tuple, set[bool]] = defaultdict(set)
    for pair in pairs:
        labels_by_identity[_benchmark_identity(pair)].add(bool(pair.get("expected_compatible")))
    conflicting_labels = [
        {"domain": key[0], "materials": list(key[1]), "electrolyte": key[2]}
        for key, labels in labels_by_identity.items()
        if len(labels) > 1
    ]

    def has_any_source_identifier(pair: Dict[str, Any]) -> bool:
        return any(
            pair.get(key)
            for key in ("doi", "isbn", "standard_id", "url", "manual_source")
        )

    return {
        "loaded_pairs": len(pairs),
        "unique_pair_identities": len(identities),
        "duplicate_pair_groups": len(duplicate_groups),
        "duplicate_pair_records": sum(group["count"] - 1 for group in duplicate_groups),
        "duplicate_examples": duplicate_groups[:25],
        "conflicting_label_groups": len(conflicting_labels),
        "conflicting_label_examples": conflicting_labels[:25],
        "missing_citation_count": sum(1 for pair in pairs if not pair.get("citation")),
        "missing_doi_count": sum(1 for pair in pairs if not pair.get("doi")),
        "missing_isbn_count": sum(1 for pair in pairs if not pair.get("isbn")),
        "missing_standard_id_count": sum(1 for pair in pairs if not pair.get("standard_id")),
        "missing_url_count": sum(1 for pair in pairs if not pair.get("url")),
        "missing_manual_source_count": sum(1 for pair in pairs if not pair.get("manual_source")),
        "missing_any_source_identifier_count": sum(
            1 for pair in pairs if not has_any_source_identifier(pair)
        ),
        "source_identifier_coverage": round(
            sum(1 for pair in pairs if has_any_source_identifier(pair))
            / max(len(pairs), 1),
            4,
        ),
        "doi_count": sum(1 for pair in pairs if pair.get("doi")),
        "isbn_count": sum(1 for pair in pairs if pair.get("isbn")),
        "standard_id_count": sum(1 for pair in pairs if pair.get("standard_id")),
        "url_count": sum(1 for pair in pairs if pair.get("url")),
        "manual_source_count": sum(1 for pair in pairs if pair.get("manual_source")),
    }


def _normalize_pair_provenance(pair: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize source identifier fields without requiring every source to have a DOI."""
    normalized = dict(pair)
    for key in ("doi", "isbn", "standard_id", "url", "manual_source"):
        normalized.setdefault(key, None)

    has_structured_source = any(
        normalized.get(key)
        for key in ("doi", "isbn", "standard_id", "url", "manual_source")
    )
    if not has_structured_source and normalized.get("citation"):
        normalized["manual_source"] = normalized["citation"]
        normalized.setdefault("source_type", "manual_citation")
    return normalized


def _compute_classification_metrics(results: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute binary and score-calibration metrics for compatibility results."""
    return _shared_compute_classification_metrics(results)


def _compatibility_decision_metadata(
    domain: str,
    mat_a: str,
    mat_b: str,
    context: CompatibilityContext,
    score: Optional[float] = None,
    predicted: Optional[bool] = None,
) -> Dict[str, Any]:
    """Shared decision metadata for audits and status-aware evaluation."""

    metadata = {
        "domain": domain,
        "material_a": mat_a,
        "material_b": mat_b,
        "context": context.to_dict(),
        "missing_context": context.missing_required_fields(domain, mat_a, mat_b),
    }
    morphism = infer_typed_morphism(mat_a, mat_b, domain, context)
    if morphism is not None:
        metadata["typed_morphism"] = morphism.to_dict()
    if score is not None and predicted is not None:
        metadata["ensemble"] = build_compatibility_ensemble(
            mat_a,
            mat_b,
            domain,
            score,
            predicted,
            context,
        ).to_dict()
    return metadata


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _default_external_blind_path() -> Path:
    """Resolve the current blind dataset from the registry."""
    audit_dir = Path(__file__).parent
    registry_path = audit_dir / "dataset_registry.json"
    fallback = audit_dir / "external_blind" / "compatibility_2026_q6.json"

    if not registry_path.exists():
        return fallback

    with open(registry_path, encoding="utf-8") as f:
        registry = json.load(f)

    current_version = registry.get("current_blind_version")
    for dataset in registry.get("datasets", []):
        if dataset.get("version") == current_version:
            return (audit_dir.parent / dataset["path"]).resolve()

    return fallback


def _load_external_blind_pairs(path: Optional[Path] = None) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    """Load frozen external blind compatibility pairs."""
    dataset_path = (path or _default_external_blind_path()).resolve()
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    pairs = []
    for pair in data.get("pairs", []):
        loaded = _normalize_pair_provenance(pair)
        loaded["source"] = str(dataset_path.relative_to(Path(__file__).parent.parent))
        loaded["used_for_tuning"] = False
        pairs.append(loaded)
    metadata = {k: v for k, v in data.items() if k != "pairs"}
    metadata["path"] = str(dataset_path)
    metadata["sha256"] = _file_sha256(dataset_path)
    metadata["pair_count"] = len(pairs)
    return pairs, metadata


def _load_development_compatibility_pairs() -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    """Load non-blind contextual development compatibility datasets."""
    dev_dir = Path(__file__).parent / "dev_compatibility"
    pairs = []
    sources = []
    if not dev_dir.exists():
        return pairs, sources

    for dataset_path in sorted(dev_dir.glob("*.json")):
        with open(dataset_path, encoding="utf-8") as f:
            data = json.load(f)
        for pair in data.get("pairs", []):
            loaded = _normalize_pair_provenance(pair)
            loaded["source"] = str(dataset_path.relative_to(Path(__file__).parent.parent))
            loaded["dataset_version"] = data.get("version")
            pairs.append(loaded)
        sources.append({
            "path": str(dataset_path),
            "version": data.get("version"),
            "frozen": data.get("frozen", False),
            "pairs": len(data.get("pairs", [])),
        })
    return pairs, sources


def _load_existing_benchmark_identities(exclude_paths: Optional[set[Path]] = None) -> set[tuple]:
    """Load identities from prior benchmark files for external-overlap checks."""
    audit_dir = Path(__file__).parent
    exclude_paths = {path.resolve() for path in (exclude_paths or set())}
    identities: set[tuple] = set()

    legacy_path = audit_dir / "blind_test_pairs.json"
    if legacy_path.exists() and legacy_path.resolve() not in exclude_paths:
        with open(legacy_path, encoding="utf-8") as f:
            legacy = json.load(f)
        for pair in legacy.get("pairs", []):
            identities.add(_benchmark_identity(pair))

    ground_truth_dir = audit_dir / "ground_truth"
    if ground_truth_dir.exists():
        for path in ground_truth_dir.glob("*.json"):
            if path.resolve() in exclude_paths:
                continue
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for pair in data.get("pairs", []):
                loaded = dict(pair)
                loaded["domain"] = path.stem
                identities.add(_benchmark_identity(loaded))

    for benchmark_dir in (audit_dir / "external_blind", audit_dir / "dev_compatibility"):
        if not benchmark_dir.exists():
            continue
        for path in benchmark_dir.glob("*.json"):
            if path.resolve() in exclude_paths:
                continue
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for pair in data.get("pairs", []):
                identities.add(_benchmark_identity(pair))

    return identities


def run_scientific_audit():
    """Run blind test pairs and literature ground truth through KOMPOSOS."""
    print("\n" + "=" * 70)
    print("MODULE 1: Scientific Accuracy (Extended Validation)")
    print("=" * 70)

    from audit.literature_ground_truth import LiteratureGroundTruth
    loader = LiteratureGroundTruth()
    
    # Load legacy blind test pairs first
    pairs_path = Path(__file__).parent / "blind_test_pairs.json"
    with open(pairs_path) as f:
        legacy_data = json.load(f)
    
    all_pairs = []
    for pair in legacy_data["pairs"]:
        loaded = dict(pair)
        loaded["source"] = "audit/blind_test_pairs.json"
        loaded.setdefault("used_for_tuning", pair.get("used_for_tuning"))
        all_pairs.append(_normalize_pair_provenance(loaded))
    print(f"Loaded {len(all_pairs)} legacy blind test pairs")
    
    # Load domain-specific ground truth
    domain_data = loader.load_all()
    for domain, pairs in domain_data.items():
        print(f"Loaded {len(pairs)} ground truth pairs for domain: {domain}")
        # Convert to dict format expected by loop
        for p in pairs:
            all_pairs.append(_normalize_pair_provenance({
                "id": p.id,
                "material_a": p.material_a,
                "material_b": p.material_b,
                "domain": p.domain,
                "expected_compatible": p.expected_compatible,
                "electrolyte": p.electrolyte,
                "citation": p.citation,
                "doi": p.doi,
                "isbn": p.isbn,
                "standard_id": p.standard_id,
                "url": p.url,
                "manual_source": p.manual_source,
                "source_type": p.source_type,
                "evidence_basis": p.evidence_basis,
                "source": f"audit/ground_truth/{domain}.json",
                "notes": p.notes,
                "used_for_tuning": p.used_for_tuning,
                "role": p.role,
                "voltage_context": p.voltage_context,
                "coating": p.coating,
                "processing_route": p.processing_route,
                "compatibilizer": p.compatibilizer,
                "interface_type": p.interface_type,
                "environment": p.environment,
                "temperature_C": p.temperature_C,
            }))

    print(f"Total pairs to evaluate: {len(all_pairs)}")
    benchmark_summary = _summarize_benchmark(all_pairs)
    print(f"Unique pair identities: {benchmark_summary['unique_pair_identities']}")
    print(f"Duplicate pair groups: {benchmark_summary['duplicate_pair_groups']}")
    print(f"Missing DOI fields: {benchmark_summary['missing_doi_count']}")

    results = []
    tp = tn = fp = fn = skipped = 0

    for pair in all_pairs:
        mat_a = pair["material_a"]
        mat_b = pair["material_b"]
        expected = pair["expected_compatible"]
        domain = pair["domain"]
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
                metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context, score, predicted),
            )

            # Classify
            if predicted and expected:
                tp += 1
                verdict = "TP"
            elif not predicted and not expected:
                tn += 1
                verdict = "TN"
            elif predicted and not expected:
                fp += 1
                verdict = "FP"
            else:
                fn += 1
                verdict = "FN"

            icon = "PASS" if verdict in ("TP", "TN") else "FAIL"
            print(f"  [{pair['id']:2d}] {icon} {mat_a} + {mat_b}: "
                  f"score={score:.3f} predicted={predicted} expected={expected} ({verdict})")

            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "citation": pair.get("citation"),
                "doi": pair.get("doi"),
                "isbn": pair.get("isbn"),
                "standard_id": pair.get("standard_id"),
                "url": pair.get("url"),
                "manual_source": pair.get("manual_source"),
                "source_type": pair.get("source_type"),
                "evidence_basis": pair.get("evidence_basis"),
                "source": pair.get("source"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "context": context.to_dict(),
                "decision_status": decision.status,
                "decision": decision.to_dict(),
                "score": round(score, 4),
                "predicted_compatible": predicted,
                "expected_compatible": expected,
                "correct": verdict in ("TP", "TN"),
                "verdict": verdict,
            })

        except Exception as e:
            print(f"  [{pair['id']:2d}] SKIP {mat_a} + {mat_b}: {e}")
            skipped += 1
            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "citation": pair.get("citation"),
                "doi": pair.get("doi"),
                "isbn": pair.get("isbn"),
                "standard_id": pair.get("standard_id"),
                "url": pair.get("url"),
                "manual_source": pair.get("manual_source"),
                "source_type": pair.get("source_type"),
                "evidence_basis": pair.get("evidence_basis"),
                "source": pair.get("source"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "context": context.to_dict(),
                "decision_status": "no_verdict",
                "decision": CompatibilityDecision.no_verdict(str(e)).to_dict(),
                "score": None,
                "predicted_compatible": None,
                "expected_compatible": expected,
                "correct": None,
                "verdict": "SKIP",
                "error": str(e),
            })
            continue

    # Compute metrics
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n  Results: {total} evaluated, {skipped} skipped")
    print(f"  TP={tp} TN={tn} FP={fp} FN={fn}")
    print(f"  Accuracy:  {accuracy:.1%}  (threshold: 80%)")
    print(f"  Precision: {precision:.1%}  (threshold: 75%)")
    print(f"  Recall:    {recall:.1%}  (threshold: 75%)")
    print(f"  F1 Score:  {f1:.1%}  (threshold: 75%)")
    calibration_metrics = _compute_classification_metrics(results)
    print(f"  Specificity: {calibration_metrics['specificity']:.1%}")
    print(f"  NPV:         {calibration_metrics['negative_predictive_value']:.1%}")
    print(f"  MCC:         {calibration_metrics['matthews_correlation_coefficient']:.3f}")
    print(f"  Brier score: {calibration_metrics['brier_score']:.3f}")
    print(f"  ECE:         {calibration_metrics['expected_calibration_error']:.3f}")

    # ── Per-domain breakdown ──────────────────────────────────────────
    domain_stats = defaultdict(lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "skip": 0})
    for r in results:
        d = r["domain"]
        v = r["verdict"]
        if v == "TP":
            domain_stats[d]["tp"] += 1
        elif v == "TN":
            domain_stats[d]["tn"] += 1
        elif v == "FP":
            domain_stats[d]["fp"] += 1
        elif v == "FN":
            domain_stats[d]["fn"] += 1
        elif v == "SKIP":
            domain_stats[d]["skip"] += 1

    domain_breakdown = {}
    print("\n  Per-domain breakdown:")
    for d_name, stats in sorted(domain_stats.items()):
        d_total = stats["tp"] + stats["tn"] + stats["fp"] + stats["fn"]
        d_acc = (stats["tp"] + stats["tn"]) / d_total if d_total > 0 else 0
        domain_breakdown[d_name] = {
            "evaluated": d_total, "skipped": stats["skip"],
            "tp": stats["tp"], "tn": stats["tn"],
            "fp": stats["fp"], "fn": stats["fn"],
            "accuracy": round(d_acc, 4),
        }
        print(f"    {d_name:20s}: {d_total:3d} pairs, acc={d_acc:.1%} "
              f"(TP={stats['tp']} TN={stats['tn']} FP={stats['fp']} FN={stats['fn']})")

    # ── Held-out vs tuning split ──────────────────────────────────────
    tuning_results = [r for r in results if r.get("used_for_tuning") is True]
    heldout_results = [r for r in results if r.get("used_for_tuning") is False]

    split_metrics = {}
    print("\n  Tuning / held-out split:")
    for label, subset in [("tuning", tuning_results), ("held-out", heldout_results)]:
        s_tp = sum(1 for r in subset if r["verdict"] == "TP")
        s_tn = sum(1 for r in subset if r["verdict"] == "TN")
        s_fp = sum(1 for r in subset if r["verdict"] == "FP")
        s_fn = sum(1 for r in subset if r["verdict"] == "FN")
        s_total = s_tp + s_tn + s_fp + s_fn
        s_acc = (s_tp + s_tn) / s_total if s_total > 0 else 0
        s_prec = s_tp / (s_tp + s_fp) if (s_tp + s_fp) > 0 else 0
        s_rec = s_tp / (s_tp + s_fn) if (s_tp + s_fn) > 0 else 0
        s_f1 = 2 * s_prec * s_rec / (s_prec + s_rec) if (s_prec + s_rec) > 0 else 0
        split_metrics[label] = {
            "evaluated": s_total, "tp": s_tp, "tn": s_tn,
            "fp": s_fp, "fn": s_fn,
            "accuracy": round(s_acc, 4), "f1": round(s_f1, 4),
        }
        print(f"    {label:10s}: {s_total:3d} pairs, acc={s_acc:.1%}, F1={s_f1:.3f}")

    # ── Protocol pass ─────────────────────────────────────────────────
    # DOI coverage is informational (standards/handbooks don't have DOIs)
    doi_coverage = 1.0 - benchmark_summary["missing_doi_count"] / max(benchmark_summary["loaded_pairs"], 1)
    metric_pass = accuracy >= 0.80 and f1 >= 0.75
    protocol_pass = (
        skipped == 0
        and benchmark_summary["missing_citation_count"] == 0
        and benchmark_summary["duplicate_pair_groups"] == 0
        and benchmark_summary["conflicting_label_groups"] == 0
    )
    module_pass = metric_pass and protocol_pass

    print(f"\n  DOI coverage: {doi_coverage:.0%} (informational)")
    print(f"  Metric pass: {metric_pass}")
    print(f"  Protocol pass: {protocol_pass}")
    print(f"  PASS: {module_pass}")

    return {
        "pairs_total": len(all_pairs),
        "pairs_evaluated": total,
        "pairs_skipped": skipped,
        "benchmark_summary": benchmark_summary,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "doi_coverage": round(doi_coverage, 4),
        "source_identifier_coverage": benchmark_summary["source_identifier_coverage"],
        "calibration_metrics": calibration_metrics,
        "domain_breakdown": domain_breakdown,
        "split_metrics": split_metrics,
        "metric_pass": metric_pass,
        "protocol_pass": protocol_pass,
        "pass": module_pass,
        "details": results,
    }


def run_external_blind_audit(external_path: Optional[Path] = None):
    """Run the frozen external blind compatibility benchmark."""
    print("\n" + "=" * 70)
    print("MODULE 4: External Blind Compatibility Validation")
    print("=" * 70)

    pairs, metadata = _load_external_blind_pairs(external_path)
    print(f"Loaded {len(pairs)} frozen external blind pairs")
    print(f"Dataset version: {metadata.get('version', 'unknown')}")
    print(f"Dataset path: {metadata['path']}")
    print(f"Dataset SHA256: {metadata['sha256']}")

    benchmark_summary = _summarize_benchmark(pairs)
    print(f"Unique pair identities: {benchmark_summary['unique_pair_identities']}")
    print(f"Duplicate pair groups: {benchmark_summary['duplicate_pair_groups']}")
    print(f"Source identifier coverage: {benchmark_summary['source_identifier_coverage']:.0%}")

    dataset_path = Path(metadata["path"])
    # Exclude the dataset itself AND its same-period sibling files (the unlabeled
    # pair list and hidden label file a sealed holdout is merged from). Without
    # this, a split-format holdout counts its own twin as a prior benchmark and
    # reports 100% spurious overlap.
    period_prefix = dataset_path.stem.split(".")[0]
    self_family = {
        sibling.resolve()
        for sibling in dataset_path.parent.iterdir()
        if sibling.is_file()
        and (
            sibling.name == f"{period_prefix}.json"
            or sibling.name.startswith(f"{period_prefix}_")
            or sibling.name.startswith(f"{period_prefix}.")
        )
    }
    self_family.add(dataset_path.resolve())
    existing_identities = _load_existing_benchmark_identities(self_family)
    existing_overlaps = [
        pair for pair in pairs
        if _benchmark_identity(pair) in existing_identities
    ]
    print(f"Overlap with existing benchmark identities: {len(existing_overlaps)}")

    manifest_path = dataset_path.with_suffix(".sha256")
    manifest_ok = False
    if manifest_path.exists():
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_ok = metadata["sha256"] in manifest_text
    print(f"Frozen manifest present: {manifest_ok}")

    results = []
    skipped = 0
    for pair in pairs:
        mat_a = pair["material_a"]
        mat_b = pair["material_b"]
        expected = pair["expected_compatible"]
        domain = pair["domain"]
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
                metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context, score, predicted),
            )
            if predicted and expected:
                verdict = "TP"
            elif not predicted and not expected:
                verdict = "TN"
            elif predicted and not expected:
                verdict = "FP"
            else:
                verdict = "FN"

            icon = "PASS" if verdict in ("TP", "TN") else "FAIL"
            print(
                f"  [{pair['id']}] {icon} {mat_a} + {mat_b}: "
                f"score={score:.3f} predicted={predicted} expected={expected} ({verdict})"
            )

            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "citation": pair.get("citation"),
                "doi": pair.get("doi"),
                "isbn": pair.get("isbn"),
                "standard_id": pair.get("standard_id"),
                "url": pair.get("url"),
                "manual_source": pair.get("manual_source"),
                "source_type": pair.get("source_type"),
                "evidence_basis": pair.get("evidence_basis"),
                "source": pair.get("source"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "context": context.to_dict(),
                "decision_status": decision.status,
                "decision": decision.to_dict(),
                "score": round(score, 4),
                "predicted_compatible": predicted,
                "expected_compatible": expected,
                "correct": verdict in ("TP", "TN"),
                "verdict": verdict,
            })
        except Exception as e:
            print(f"  [{pair['id']}] SKIP {mat_a} + {mat_b}: {e}")
            skipped += 1
            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "electrolyte": pair.get("electrolyte"),
                "role": pair.get("role"),
                "citation": pair.get("citation"),
                "doi": pair.get("doi"),
                "isbn": pair.get("isbn"),
                "standard_id": pair.get("standard_id"),
                "url": pair.get("url"),
                "manual_source": pair.get("manual_source"),
                "source_type": pair.get("source_type"),
                "evidence_basis": pair.get("evidence_basis"),
                "source": pair.get("source"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "context": context.to_dict(),
                "decision_status": "no_verdict",
                "decision": CompatibilityDecision.no_verdict(str(e)).to_dict(),
                "score": None,
                "predicted_compatible": None,
                "expected_compatible": expected,
                "correct": None,
                "verdict": "SKIP",
                "error": str(e),
            })

    metrics = _compute_classification_metrics(results)
    print(f"\n  Results: {metrics['evaluated']} evaluated, {skipped} skipped")
    print(f"  TP={metrics['tp']} TN={metrics['tn']} FP={metrics['fp']} FN={metrics['fn']}")
    print(f"  Accuracy:  {metrics['accuracy']:.1%}  (external blind)")
    print(f"  Balanced:  {metrics['balanced_accuracy']:.1%}")
    print(f"  Specificity: {metrics['specificity']:.1%}")
    print(f"  NPV:         {metrics['negative_predictive_value']:.1%}")
    print(f"  MCC:         {metrics['matthews_correlation_coefficient']:.3f}")
    print(f"  Brier score: {metrics['brier_score']:.3f}")
    print(f"  ECE:         {metrics['expected_calibration_error']:.3f}")
    failure_memory = build_failure_memory(
        results,
        dataset_name=metadata.get("version", dataset_path.stem),
    )
    print(f"  Failure-memory episodes: {failure_memory['episode_count']}")
    for pattern, count in failure_memory["pattern_counts"].items():
        print(f"    {pattern}: {count}")

    protocol_pass = (
        metadata.get("frozen") is True
        and 30 <= len(pairs) <= 50
        and manifest_ok
        and skipped == 0
        and benchmark_summary["missing_citation_count"] == 0
        and benchmark_summary["missing_any_source_identifier_count"] == 0
        and benchmark_summary["duplicate_pair_groups"] == 0
        and benchmark_summary["conflicting_label_groups"] == 0
        and len(existing_overlaps) == 0
        and all(pair.get("used_for_tuning") is False for pair in pairs)
    )
    metric_pass = (
        metrics["evaluated"] == len(pairs)
        and metrics["accuracy"] >= 0.65
        and metrics["balanced_accuracy"] >= 0.60
        and metrics["matthews_correlation_coefficient"] >= 0.25
    )
    module_pass = protocol_pass and metric_pass
    print(f"\n  Protocol pass: {protocol_pass}")
    print(f"  Metric pass: {metric_pass}")
    print(f"  PASS: {module_pass}")

    return {
        "metadata": metadata,
        "pairs_total": len(pairs),
        "pairs_evaluated": metrics["evaluated"],
        "pairs_skipped": skipped,
        "benchmark_summary": benchmark_summary,
        "existing_benchmark_overlap_count": len(existing_overlaps),
        "existing_benchmark_overlap_examples": [
            {
                "id": pair.get("id"),
                "domain": pair.get("domain"),
                "material_a": pair.get("material_a"),
                "material_b": pair.get("material_b"),
                "electrolyte": pair.get("electrolyte"),
            }
            for pair in existing_overlaps[:25]
        ],
        "source_identifier_coverage": benchmark_summary["source_identifier_coverage"],
        "calibration_metrics": metrics,
        "failure_memory": failure_memory,
        "protocol_pass": protocol_pass,
        "metric_pass": metric_pass,
        "pass": module_pass,
        "details": results,
    }


def run_development_compatibility_audit():
    """Run contextual development compatibility cases used for bridge tuning."""
    print("\n" + "=" * 70)
    print("MODULE 5: Contextual Development Compatibility Checks")
    print("=" * 70)
    print("Note: this is a tuning/development set, not a blind validation claim.")

    pairs, sources = _load_development_compatibility_pairs()
    print(f"Loaded {len(pairs)} development pairs from {len(sources)} file(s)")

    results = []
    skipped = 0
    for pair in pairs:
        mat_a = pair["material_a"]
        mat_b = pair["material_b"]
        expected = pair["expected_compatible"]
        domain = pair["domain"]
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
                metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context, score, predicted),
            )
            if predicted and expected:
                verdict = "TP"
            elif not predicted and not expected:
                verdict = "TN"
            elif predicted and not expected:
                verdict = "FP"
            else:
                verdict = "FN"

            icon = "PASS" if verdict in ("TP", "TN") else "FAIL"
            print(
                f"  [{pair['id']}] {icon} {mat_a} + {mat_b}: "
                f"score={score:.3f} predicted={predicted} expected={expected} ({verdict})"
            )
            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "context": context.to_dict(),
                "source": pair.get("source"),
                "dataset_version": pair.get("dataset_version"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "decision_status": decision.status,
                "decision": decision.to_dict(),
                "score": round(score, 4),
                "predicted_compatible": predicted,
                "expected_compatible": expected,
                "correct": verdict in ("TP", "TN"),
                "verdict": verdict,
            })
        except Exception as e:
            print(f"  [{pair['id']}] SKIP {mat_a} + {mat_b}: {e}")
            skipped += 1
            results.append({
                "id": pair["id"],
                "material_a": mat_a,
                "material_b": mat_b,
                "domain": domain,
                "context": context.to_dict(),
                "source": pair.get("source"),
                "dataset_version": pair.get("dataset_version"),
                "used_for_tuning": pair.get("used_for_tuning"),
                "decision_status": "no_verdict",
                "decision": CompatibilityDecision.no_verdict(str(e)).to_dict(),
                "score": None,
                "predicted_compatible": None,
                "expected_compatible": expected,
                "correct": None,
                "verdict": "SKIP",
                "error": str(e),
            })

    metrics = _compute_classification_metrics(results)
    print(f"\n  Results: {metrics['evaluated']} evaluated, {skipped} skipped")
    print(f"  TP={metrics['tp']} TN={metrics['tn']} FP={metrics['fp']} FN={metrics['fn']}")
    print(f"  Accuracy:  {metrics['accuracy']:.1%}")
    print(f"  Balanced:  {metrics['balanced_accuracy']:.1%}")
    print(f"  Brier score: {metrics['brier_score']:.3f}")
    failure_memory = build_failure_memory(results, dataset_name="contextual_dev_2026_q2")
    print(f"  Failure-memory episodes: {failure_memory['episode_count']}")
    for pattern, count in failure_memory["pattern_counts"].items():
        print(f"    {pattern}: {count}")

    protocol_pass = (
        len(pairs) > 0
        and skipped == 0
        and all(pair.get("used_for_tuning") is True for pair in pairs)
        and all(source.get("frozen") is False for source in sources)
    )
    metric_pass = metrics["evaluated"] == len(pairs) and metrics["accuracy"] >= 0.80
    module_pass = protocol_pass and metric_pass
    print(f"\n  Protocol pass: {protocol_pass}")
    print(f"  Metric pass: {metric_pass}")
    print(f"  PASS: {module_pass}")

    return {
        "validation_type": "development_tuning_set",
        "sources": sources,
        "pairs_total": len(pairs),
        "pairs_evaluated": metrics["evaluated"],
        "pairs_skipped": skipped,
        "calibration_metrics": metrics,
        "failure_memory": failure_memory,
        "protocol_pass": protocol_pass,
        "metric_pass": metric_pass,
        "pass": module_pass,
        "details": results,
    }


def _evaluate_pair_decision(
    mat_a: str,
    mat_b: str,
    domain: str,
    electrolyte: Optional[str] = None,
    role: Optional[str] = None,
    context: Optional[CompatibilityContext] = None,
    allow_abstention: bool = False,
) -> CompatibilityDecision:
    """Evaluate a pair and return a status-aware compatibility decision."""

    context = context or CompatibilityContext(role=role, electrolyte=electrolyte)
    missing = context.missing_required_fields(domain, mat_a, mat_b)
    if allow_abstention and missing:
        return CompatibilityDecision.needs_context(
            missing,
            metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context),
        )

    try:
        score, predicted = _evaluate_pair(mat_a, mat_b, domain, electrolyte, role, context)
    except Exception as exc:
        return CompatibilityDecision.no_verdict(
            str(exc),
            metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context),
        )

    decision = CompatibilityDecision.from_prediction(
        score,
        predicted,
        metadata=_compatibility_decision_metadata(domain, mat_a, mat_b, context, score, predicted),
    )
    return decision


def _evaluate_pair(
    mat_a: str,
    mat_b: str,
    domain: str,
    electrolyte: Optional[str] = None,
    role: Optional[str] = None,
    context: Optional[CompatibilityContext] = None,
):
    """
    Evaluate a single pair using the appropriate bridge/functor.

    Returns:
        (score: float, predicted_compatible: bool)
    """
    context = context or CompatibilityContext(role=role, electrolyte=electrolyte)
    electrolyte = context.electrolyte or electrolyte
    role = context.role or role

    if domain == "battery":
        from battery_bridge.interface_validator import BatteryInterfaceValidator, BatteryInterfaceScore
        validator = BatteryInterfaceValidator()
        result = validator.validate(mat_a, mat_b)
        return result.total, result.viable


    elif domain == "ceramic-metal":
        from cross_bridge.ceramic_metal import score_ceramic_metal_compatibility, InterfaceRole
        # Use role from benchmark data if provided, otherwise default to COATING
        iface_role = InterfaceRole[role] if role else InterfaceRole.COATING
        result = score_ceramic_metal_compatibility(mat_a, mat_b, role=iface_role)
        return result.score, result.compatible

    elif domain == "battery-metal":
        from cross_bridge.battery_metal import score_collector_compatibility
        # For cathode collectors like Al, need an electrolyte for passivation in standard Li-ion
        if electrolyte is None and (mat_a == "Al_foil" or mat_b == "Al_foil"):
            electrolyte = "LiPF6"
        result = score_collector_compatibility(
            mat_a,
            mat_b,
            electrolyte_name=electrolyte,
            metal_coating=context.coating,
            interface_role=role,
        )
        return _apply_typed_context_score(result.score, result.compatible, mat_a, mat_b, domain, context)

    elif domain == "battery-polymer":
        from cross_bridge.battery_polymer import score_polymer_electrode_compatibility
        result = score_polymer_electrode_compatibility(
            mat_a,
            mat_b,
            operating_temp_C=context.temperature_C or 25.0,
            polymer_role=role,
        )
        return result.score, result.compatible

    elif domain == "ceramic":
        from ceramic_bridge.interface_validator import CeramicInterfaceValidator, CeramicConditions
        validator = CeramicInterfaceValidator()
        conditions = CeramicConditions(
            temperature_C=context.temperature_C or 25.0,
            environment=context.environment or "indoor",
        )
        result = validator.validate(mat_a, mat_b, conditions)
        return _apply_typed_context_score(result.total, result.viable, mat_a, mat_b, domain, context)

    elif domain == "semiconductor":
        from semiconductor_bridge.interface_validator import SemiconductorInterfaceValidator, SemiconductorConditions
        validator = SemiconductorInterfaceValidator()
        conditions = SemiconductorConditions(
            temperature_C=context.temperature_C or 25.0,
            environment=context.environment or "cleanroom",
        )
        result = validator.validate(mat_a, mat_b, conditions)
        return _apply_typed_context_score(result.total, result.viable, mat_a, mat_b, domain, context)

    elif domain == "glass":
        from glass_bridge.interface_validator import GlassInterfaceValidator
        validator = GlassInterfaceValidator()
        result = validator.validate(mat_a, mat_b)
        return _apply_typed_context_score(result.total, result.viable, mat_a, mat_b, domain, context)

    elif domain == "polymer":
        from polymer_bridge.interface_validator import PolymerInterfaceValidator, PolymerConditions
        validator = PolymerInterfaceValidator()
        conditions = PolymerConditions(
            temperature_C=context.temperature_C or 25.0,
            chemical_environment=context.environment or "air",
        )
        result = validator.validate(mat_a, mat_b, conditions)
        return result.total, result.viable

    elif domain == "metal":
        from metal_bridge.interface_validator import MetalInterfaceValidator, MetalConditions
        validator = MetalInterfaceValidator()
        conditions = MetalConditions(
            temperature_C=context.temperature_C or 25.0,
            environment=context.environment or "indoor",
        )
        result = validator.validate(mat_a, mat_b, conditions)
        return result.total, result.viable

    elif domain == "metal-semiconductor":
        from cross_bridge.metal_semiconductor import score_metal_semiconductor_compatibility
        result = score_metal_semiconductor_compatibility(mat_a, mat_b, role=role)
        return _apply_typed_context_score(result.score, result.compatible, mat_a, mat_b, domain, context)

    elif domain == "glass-metal":
        from cross_bridge.glass_metal import score_glass_metal_compatibility
        result = score_glass_metal_compatibility(mat_a, mat_b, role=role)
        return _apply_typed_context_score(result.score, result.compatible, mat_a, mat_b, domain, context)

    elif domain == "polymer-glass":
        from cross_bridge.polymer_glass import score_polymer_glass_compatibility
        result = score_polymer_glass_compatibility(mat_a, mat_b, role=role)
        return _apply_typed_context_score(result.score, result.compatible, mat_a, mat_b, domain, context)

    elif domain == "cross-bridge":
        from cross_bridge.multi_domain import (
            MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent
        )
        analyzer = MultiDomainAnalyzer()
        query = MultiDomainQuery(
            name=f"{mat_a}+{mat_b}",
            components=[
                MultiDomainComponent(name=mat_a),
                MultiDomainComponent(name=mat_b),
            ],
        )
        result = analyzer.analyze(query)
        return result.overall_score, result.viable

    else:
        raise ValueError(f"Unknown domain: {domain}")


def _apply_typed_context_score(
    score: float,
    predicted: bool,
    mat_a: str,
    mat_b: str,
    domain: str,
    context: CompatibilityContext,
) -> tuple[float, bool]:
    """Apply full audit/API context to typed morphism priors and vetoes."""

    adjustment = apply_typed_morphism_adjustment(
        score,
        predicted,
        mat_a,
        mat_b,
        domain,
        context,
    )
    if adjustment.action in {"veto", "negative_prior", "positive_prior"}:
        return adjustment.score, adjustment.predicted_compatible
    return score, predicted


# ---------------------------------------------------------------------------
# Module 2: Computational Integrity
# ---------------------------------------------------------------------------

def run_computational_audit():
    """Verify category theory axioms, ZFC, and D-S fusion math."""
    print("\n" + "=" * 70)
    print("MODULE 2: Computational Integrity")
    print("=" * 70)

    checks = []

    # 2A: Category theory axioms
    print("\n  2A: Category Theory Axioms")
    from categorical.category import Category, Object, Morphism

    cat = Category("test")
    a = Object("A", {"type": "test"})
    b = Object("B", {"type": "test"})
    c = Object("C", {"type": "test"})
    d = Object("D", {"type": "test"})
    cat.add_object(a)
    cat.add_object(b)
    cat.add_object(c)
    cat.add_object(d)

    f = Morphism("f", a, b, {"score": 0.8})
    g = Morphism("g", b, c, {"score": 0.7})
    h = Morphism("h", c, d, {"score": 0.9})
    cat.add_morphism(f)
    cat.add_morphism(g)
    cat.add_morphism(h)

    # Identity
    id_a = cat.identity(a)
    identity_ok = id_a is not None
    checks.append(("identity_exists", identity_ok))
    print(f"    Identity morphism exists: {identity_ok}")

    # Composition
    fg = cat.compose(f, g)
    composition_ok = fg is not None
    checks.append(("composition_exists", composition_ok))
    print(f"    Composition f.g exists: {composition_ok}")

    # Associativity: (f.g).h == f.(g.h)
    fg_h = cat.compose(fg, h) if fg else None
    gh = cat.compose(g, h)
    f_gh = cat.compose(f, gh) if gh else None
    assoc_ok = (
        fg_h is not None
        and f_gh is not None
        and fg_h.source == f_gh.source
        and fg_h.target == f_gh.target
        and fg_h.data.get("composed_from") == f_gh.data.get("composed_from")
    )
    checks.append(("associativity", assoc_ok))
    print(f"    Associativity (f.g).h and f.(g.h): {assoc_ok}")

    # 2B: ZFC Dual Engine
    print("\n  2B: ZFC Dual Engine")
    try:
        from oracle.material_zfc_constraints import MaterialZFCBridge
        from zfc.category_bridge import DualEngineBridge
        from zfc.meta_kan import DeltaType
        
        zfc = MaterialZFCBridge()
        scores = {"ion_transport": 0.9, "electrochemical_stability": 0.8,
                  "interface_compatibility": 0.85, "mechanical_compatibility": 1.0,
                  "degradation_penalty": 1.0}
        zfc_result = zfc.score_constraints("NMC811", "EC", scores)
        zfc_ok = zfc_result is not None
        checks.append(("zfc_bridge_runs", zfc_ok))
        print(f"    ZFC bridge executes: {zfc_ok}")
        
        if zfc_result:
            # Use standardized classification logic from bridge
            # CAT says yes (0.85 > 0.4), ZFC says yes (no vetoes)
            has_vetoes = any(c.source_prediction.get("relation", "").endswith("_veto") for c in zfc_result)
            classification = DualEngineBridge.classify_dual_result(cat_says=True, zfc_says=not has_vetoes)
            
            valid_classes = {DeltaType.AGREE, DeltaType.HOLLOW, DeltaType.ORPHAN, DeltaType.REJECT}
            class_ok = classification in valid_classes
            checks.append(("zfc_valid_classification", class_ok))
            print(f"    ZFC classification valid ({classification.name}): {class_ok}")
    except Exception as e:
        checks.append(("zfc_bridge_runs", False))
        checks.append(("zfc_valid_classification", False))
        print(f"    ZFC bridge error: {e}")

    # 2C: Dempster-Shafer
    print("\n  2C: Dempster-Shafer Fusion")
    try:
        from categorical.dempster_shafer import MassFunction, combine
        theta = frozenset({"compatible", "incompatible"})
        m1 = MassFunction({
            frozenset({"compatible"}): 0.8,
            frozenset({"incompatible"}): 0.1,
            theta: 0.1,
        })
        m2 = MassFunction({
            frozenset({"compatible"}): 0.6,
            frozenset({"incompatible"}): 0.2,
            theta: 0.2,
        })
        fused, conflict = combine(m1, m2)

        # Verify mass function sums to 1
        mass_sum = sum(fused.masses.values())
        mass_ok = abs(mass_sum - 1.0) < 1e-6
        checks.append(("ds_mass_sums_to_1", mass_ok))
        print(f"    Mass function sums to 1: {mass_ok} (sum={mass_sum:.6f})")

        # All masses non-negative
        all_positive = all(v >= 0 for v in fused.masses.values())
        checks.append(("ds_masses_non_negative", all_positive))
        print(f"    All masses non-negative: {all_positive}")

        # Conflict is bounded [0, 1)
        conflict_ok = 0 <= conflict < 1
        checks.append(("ds_conflict_bounded", conflict_ok))
        print(f"    Conflict bounded [0,1): {conflict_ok} (conflict={conflict:.4f})")

        # Commutativity: combine(m1,m2) == combine(m2,m1)
        fused_rev, conflict_rev = combine(m2, m1)
        commutative_ok = abs(conflict - conflict_rev) < 1e-6
        checks.append(("ds_commutativity", commutative_ok))
        print(f"    Commutativity holds: {commutative_ok}")
    except Exception as e:
        checks.append(("ds_fusion", False))
        print(f"    D-S fusion error: {e}")

    # 2D: Reproducibility - Crystal structure prediction
    print("\n  2D: Reproducibility Checks")
    try:
        from composition_engine.structure_predictor import StructureTypePredictor
        predictor = StructureTypePredictor()
        from composition_engine.formation_energy import KNOWN_EF
        known_structures = []
        seen_formulas = set()
        for entry in KNOWN_EF:
            if entry.formula in seen_formulas:
                continue
            if entry.structure_type:
                known_structures.append((entry.formula, entry.structure_type))
                seen_formulas.add(entry.formula)
            if len(known_structures) == 23:
                break

        correct = 0
        for formula, expected in known_structures:
            result = predictor.predict(formula)
            if result and result.predicted_type == expected:
                correct += 1
                print(f"    {formula}: {result.predicted_type} == {expected} PASS")
            else:
                actual = result.predicted_type if result else "None"
                print(f"    {formula}: {actual} != {expected} FAIL")

        struct_ok = len(known_structures) == 23 and correct == len(known_structures)
        checks.append(("structure_prediction", struct_ok))
        print(f"    Structure prediction: {correct}/{len(known_structures)}")
    except Exception as e:
        checks.append(("structure_prediction", False))
        print(f"    Structure prediction error: {e}")

    # 2E: Formation energy reproducibility
    print("\n  2E: Formation Energy Predictions")
    try:
        from composition_engine.formation_energy import FormationEnergyPredictor, KNOWN_EF
        fe_predictor = FormationEnergyPredictor(use_mp_cache=False)
        # Evaluate true leave-one-out behavior against the curated source-backed
        # values. The calibrated intervals are the pass criterion; the old 20%
        # band is still reported as a diagnostic because it is useful to see.
        test_entries = [
            entry for entry in KNOWN_EF
            if entry.mp_id and entry.mp_id != "computed"
        ][:37]
        fe_correct = 0
        within_50 = within_80 = within_95 = 0
        abs_errors = []
        missing_intervals = 0
        for entry in test_entries:
            formula = entry.formula
            result = fe_predictor.predict(formula, exclude_formula=formula)
            if result and result.ef_per_atom is not None:
                error = abs(result.ef_per_atom - entry.ef_per_atom)
                abs_errors.append(error)
                relative = error / abs(entry.ef_per_atom) if entry.ef_per_atom != 0 else error
                ok = relative <= 0.20
                fe_correct += int(ok)
                intervals = result.calibrated_intervals_eV
                if {"50", "80", "95"}.issubset(intervals):
                    within_50 += int(error <= intervals["50"])
                    within_80 += int(error <= intervals["80"])
                    within_95 += int(error <= intervals["95"])
                    interval_note = (
                        f"CI50={intervals['50']:.3f} CI80={intervals['80']:.3f} "
                        f"CI95={intervals['95']:.3f}"
                    )
                else:
                    missing_intervals += 1
                    interval_note = f"calibration={result.calibration_status}"
                print(
                    f"    {formula}: predicted={result.ef_per_atom:.3f} "
                    f"known={entry.ef_per_atom:.3f} abs_err={error:.3f} "
                    f"rel_err={relative:.1%} {interval_note}"
                )

        n = len(test_entries)
        mae = sum(abs_errors) / len(abs_errors) if abs_errors else float("inf")
        rmse = (sum(e * e for e in abs_errors) / len(abs_errors)) ** 0.5 if abs_errors else float("inf")
        cov50 = within_50 / n if n else 0.0
        cov80 = within_80 / n if n else 0.0
        cov95 = within_95 / n if n else 0.0
        interval_ok = n == 37 and missing_intervals == 0
        checks.append(("formation_energy_intervals_available", interval_ok))
        print(f"    Formation energy diagnostic: {fe_correct}/{n} within 20% relative error")
        print(f"    Formation energy MAE={mae:.3f} eV/atom RMSE={rmse:.3f} eV/atom")
        print(f"    Calibrated interval coverage: 50%={cov50:.1%} 80%={cov80:.1%} 95%={cov95:.1%}")
        print(f"    Internal LOO interval diagnostic only; intervals available: {interval_ok}")

        report_path = Path(__file__).resolve().parent.parent / "data" / "calibration" / "phase16_calibration_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            validation = report["global"]["validation"]
            entries = report["entries"]
            global_cov = validation["coverage"]
            class_checks = []
            for class_name, class_report in report["by_class"].items():
                class_validation = class_report["validation"]
                class_cov = class_validation["coverage"]
                class_ok = (
                    class_validation["n"] >= 100
                    and class_cov["80"] >= 0.70
                    and class_cov["95"] >= 0.88
                )
                class_checks.append(class_ok)
                print(
                    f"    Phase16 external {class_name:14s}: "
                    f"n={class_validation['n']:4d} "
                    f"MAE={class_validation['mae']:.3f} "
                    f"RMSE={class_validation['rmse']:.3f} "
                    f"C50={class_cov['50']:.1%} "
                    f"C80={class_cov['80']:.1%} "
                    f"C95={class_cov['95']:.1%}"
                )

            external_ok = (
                entries["validation"] >= 1000
                and 0.45 <= global_cov["50"] <= 0.55
                and 0.75 <= global_cov["80"] <= 0.85
                and 0.90 <= global_cov["95"] <= 0.98
                and all(class_checks)
            )
            print(
                f"    Phase16 external global: n={validation['n']} "
                f"MAE={validation['mae']:.3f} RMSE={validation['rmse']:.3f} "
                f"C50={global_cov['50']:.1%} C80={global_cov['80']:.1%} "
                f"C95={global_cov['95']:.1%}"
            )
        else:
            external_ok = False
            print(f"    Phase16 external report missing: {report_path}")
        checks.append(("phase16_external_validation", external_ok))
        print(f"    Phase16 external validation pass: {external_ok}")
    except Exception as e:
        checks.append(("formation_energy_reproducible", False))
        print(f"    Formation energy error: {e}")

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    all_pass = passed == total
    print(f"\n  Checks: {passed}/{total} passed")
    print(f"  PASS: {all_pass}")

    return {
        "checks_total": total,
        "checks_passed": passed,
        "pass": all_pass,
        "details": [{"check": name, "pass": ok} for name, ok in checks],
    }


# ---------------------------------------------------------------------------
# Module 3: Data Provenance Spot-Check
# ---------------------------------------------------------------------------

def run_provenance_audit():
    """Spot-check material property data against sources."""
    print("\n" + "=" * 70)
    print("MODULE 3: Data Provenance Spot-Check")
    print("=" * 70)

    checks = []

    # Check battery materials have required fields
    print("\n  3A: Battery Materials")
    from battery_bridge.material_properties import ALL_MATERIALS as bat_mats
    sample = random.sample(list(bat_mats.keys()), min(5, len(bat_mats)))
    for name in sample:
        mat = bat_mats[name]
        has_props = hasattr(mat, 'voltage_window') or hasattr(mat, 'ionic_conductivity')
        checks.append((f"battery_{name}_has_properties", has_props))
        print(f"    {name}: has properties = {has_props}")

    # Check PFAS registry has CAS numbers and regulations
    print("\n  3B: PFAS Registry")
    from pfas_bridge.pfas_registry import PFAS_REGISTRY
    sample_pfas = random.sample(list(PFAS_REGISTRY.keys()), min(5, len(PFAS_REGISTRY)))
    for name in sample_pfas:
        sub = PFAS_REGISTRY[name]
        has_cas = sub.cas_number is not None and len(sub.cas_number) > 0
        has_regs = len(sub.regulations) > 0
        checks.append((f"pfas_{name}_cas", has_cas))
        checks.append((f"pfas_{name}_regulations", has_regs))
        print(f"    {name}: CAS={sub.cas_number} ({has_cas}), "
              f"regulations={len(sub.regulations)} ({has_regs})")

    # Check molecular bridge has PubChem CIDs
    print("\n  3C: Molecular Bridge")
    from molecular_bridge.molecule_properties import ALL_MOLECULES
    sample_mol = random.sample(list(ALL_MOLECULES.keys()), min(5, len(ALL_MOLECULES)))
    for name in sample_mol:
        mol = ALL_MOLECULES[name]
        has_cid = hasattr(mol, 'pubchem_cid') and mol.pubchem_cid is not None
        has_cas = hasattr(mol, 'cas_number') and mol.cas_number is not None
        checks.append((f"mol_{name}_cid", has_cid))
        print(f"    {name}: PubChem CID={getattr(mol, 'pubchem_cid', 'N/A')} ({has_cid}), "
              f"CAS={getattr(mol, 'cas_number', 'N/A')}")

    # Check formation energy values exist and are reasonable
    print("\n  3D: Formation Energies")
    from composition_engine.formation_energy import KNOWN_EF
    print(f"    {len(KNOWN_EF)} known DFT formation energies")
    sample_fe = random.sample(KNOWN_EF, min(5, len(KNOWN_EF)))
    for entry in sample_fe:
        ef = entry.ef_per_atom
        valid = isinstance(ef, (int, float)) and -10 < ef < 5  # reasonable range eV/atom
        checks.append((f"fe_{entry.formula}", valid))
        print(f"    {entry.formula} ({entry.name}): Ef = {ef:.3f} eV/atom (valid: {valid})")

    # Check ceramic bridge materials have CTE values
    print("\n  3E: Ceramic Materials (CTE values)")
    from ceramic_bridge.material_properties import ALL_CERAMICS as cer_mats
    sample_cer = random.sample(list(cer_mats.keys()), min(5, len(cer_mats)))
    for name in sample_cer:
        mat = cer_mats[name]
        has_cte = hasattr(mat, 'cte_per_K') and mat.cte_per_K is not None
        checks.append((f"ceramic_{name}_cte", has_cte))
        cte_val = getattr(mat, 'cte_per_K', None)
        print(f"    {name}: CTE = {cte_val} (has value: {has_cte})")

    # 3F: Value verification against published data
    print("\n  3F: Property Value Verification (hardcoded expected values)")
    _value_checks = [
        # (label, module, key, attr_path, expected, tolerance_pct, source)
        ("NMC811_voltage_upper", "battery", "NMC811", "voltage_window",
         lambda v: hasattr(v, 'upper') and abs(v.upper - 4.3) < 0.3,
         "Noh et al., J. Power Sources 2013"),
        ("HDPE_melting_point", "polymer", "HDPE", "melting_point_C",
         lambda v: v is not None and abs(v - 130.0) / 130.0 <= 0.05,
         "Brandrup, Polymer Handbook 4th ed."),
        ("PVDF_density", "polymer", "PVDF", "density_g_cm3",
         lambda v: v is not None and abs(v - 1.78) / 1.78 <= 0.05,
         "Brandrup, Polymer Handbook 4th ed."),
        ("Al2O3_CTE", "ceramic", "Al2O3", "cte_per_K",
         lambda v: v is not None and (
             abs(v - 7.4e-6) / 7.4e-6 <= 0.15  # stored in /K
             or abs(v - 7.4) / 7.4 <= 0.15      # stored in ppm/K
         ),
         "ASM Handbook Vol 4"),
        ("GaAs_bandgap", "semiconductor", "GaAs", "band_gap_eV",
         lambda v: v is not None and abs(v - 1.42) / 1.42 <= 0.05,
         "Vurgaftman et al., J. Appl. Phys. 2001"),
        ("Si_bandgap", "semiconductor", "Si", "band_gap_eV",
         lambda v: v is not None and abs(v - 1.12) / 1.12 <= 0.05,
         "Sze, Physics of Semiconductor Devices"),
        ("PFOS_CAS", "pfas", "PFOS", "cas_number",
         lambda v: v == "1763-23-1",
         "EPA CompTox Dashboard"),
        ("Cu_galvanic", "metal", "Cu", "galvanic_potential_V",
         lambda v: v is not None and abs(v - (-0.35)) < 0.15,
         "MIL-STD-889D"),
    ]
    _registries = {
        "battery": bat_mats,
        "polymer": None,  # loaded below
        "ceramic": cer_mats,
        "semiconductor": None,
        "pfas": None,
        "metal": None,
    }
    # Lazy-load registries not yet imported
    try:
        from polymer_bridge.material_properties import ALL_POLYMERS
        _registries["polymer"] = ALL_POLYMERS
    except Exception:
        pass
    try:
        from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS
        _registries["semiconductor"] = ALL_SEMICONDUCTORS
    except Exception:
        pass
    try:
        _registries["pfas"] = PFAS_REGISTRY
    except Exception:
        pass
    try:
        from metal_bridge.material_properties import ALL_METALS
        _registries["metal"] = ALL_METALS
    except Exception:
        pass

    for label, module, key, attr, check_fn, source in _value_checks:
        try:
            registry = _registries.get(module)
            if registry is None:
                checks.append((f"value_{label}", False))
                print(f"    {label}: SKIP (registry not loaded)")
                continue
            mat = registry.get(key)
            if mat is None:
                checks.append((f"value_{label}", False))
                print(f"    {label}: SKIP ({key} not in {module} registry)")
                continue
            val = getattr(mat, attr, None)
            ok = check_fn(val)
            checks.append((f"value_{label}", ok))
            print(f"    {label}: {attr}={val} ok={ok} [{source}]")
        except Exception as e:
            checks.append((f"value_{label}", False))
            print(f"    {label}: ERROR {e}")

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    pct = passed / total if total > 0 else 0
    all_pass = pct >= 0.95
    print(f"\n  Checks: {passed}/{total} ({pct:.0%})")
    print(f"  PASS: {all_pass} (threshold: 95%)")

    return {
        "checks_total": total,
        "checks_passed": passed,
        "pass_rate": round(pct, 4),
        "pass": all_pass,
        "details": [{"check": name, "pass": ok} for name, ok in checks],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="KOMPOSOS Audit Runner")
    parser.add_argument("--module", default="all",
                        choices=[
                            "all",
                            "scientific",
                            "computational",
                            "provenance",
                            "external",
                            "development",
                        ])
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible provenance spot-checks")
    parser.add_argument("--external-path", type=Path, default=None,
                        help="Path to a frozen external blind compatibility JSON")
    args = parser.parse_args()

    random.seed(args.seed)

    print("=" * 70)
    print("KOMPOSOS-III Scientific & Computational Audit")
    print(f"Date: {date.today().isoformat()}")
    print(f"Engine version: 1.2.0")
    print(f"Random seed: {args.seed}")
    print("=" * 70)

    report = {
        "audit_id": f"AUDIT-{date.today().strftime('%Y-%m%d')}-0001",
        "date": date.today().isoformat(),
        "engine_version": "1.2.0",
        "random_seed": args.seed,
        "modules": {},
    }

    if args.module in ("all", "scientific"):
        report["modules"]["scientific_accuracy"] = run_scientific_audit()

    if args.module in ("all", "computational"):
        report["modules"]["computational_integrity"] = run_computational_audit()

    if args.module in ("all", "provenance"):
        report["modules"]["data_provenance"] = run_provenance_audit()

    if args.module in ("all", "external"):
        report["modules"]["external_blind_compatibility"] = run_external_blind_audit(args.external_path)

    if args.module == "development":
        report["modules"]["development_compatibility"] = run_development_compatibility_audit()

    # Overall pass
    module_results = report["modules"]
    report["overall_pass"] = all(m.get("pass", False) for m in module_results.values())

    # Save report
    out_path = Path(__file__).parent / f"audit_report_{date.today().isoformat()}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {'PASS' if report['overall_pass'] else 'FAIL'}")
    print(f"Report saved to: {out_path}")
    print(f"{'=' * 70}")

    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
