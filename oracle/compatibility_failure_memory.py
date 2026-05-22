# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""MetaKan-style failure memory for compatibility audits."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha1
from typing import Any, Dict, Iterable, List, Optional

from zfc.meta_kan import DeltaType, Episode, EpisodeCategory, Resolution


FAILURE_DECISION_STATUSES = {"needs_context", "no_verdict"}
FAILURE_VERDICTS = {"FP", "FN", "SKIP", "ABSTAIN"}


@dataclass(frozen=True)
class CompatibilityEpisodeRecord:
    """Serializable wrapper around a MetaKan episode and its audit context."""

    episode: Episode
    pattern: str
    source_row_id: Any
    verdict: str
    decision_status: str
    context: Dict[str, Any]
    missing_context: List[str]
    score: Optional[float]
    expected_compatible: Optional[bool]
    predicted_compatible: Optional[bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode.id,
            "source_row_id": self.source_row_id,
            "material_a": self.episode.source,
            "material_b": self.episode.target,
            "domain": self.episode.domain,
            "relation": self.episode.relation,
            "pattern": self.pattern,
            "verdict": self.verdict,
            "decision_status": self.decision_status,
            "delta_type": self.episode.delta_type.name,
            "resolution": self.episode.resolution.name,
            "resolution_notes": self.episode.resolution_notes,
            "score": self.score,
            "expected_compatible": self.expected_compatible,
            "predicted_compatible": self.predicted_compatible,
            "cat_confidence": round(self.episode.cat_confidence, 4),
            "evidence_confidence": round(self.episode.zfc_confidence, 4),
            "context": self.context,
            "missing_context": self.missing_context,
        }


def should_record_episode(row: Dict[str, Any], include_correct: bool = False) -> bool:
    """Return true if an audit row should be recorded as a memory episode."""

    if include_correct and row.get("verdict") in {"TP", "TN", "FP", "FN"}:
        return True
    if row.get("verdict") in FAILURE_VERDICTS:
        return True
    return row.get("decision_status") in FAILURE_DECISION_STATUSES


def row_to_episode_record(
    row: Dict[str, Any],
    dataset_name: str = "compatibility",
) -> CompatibilityEpisodeRecord:
    """Convert an audit result row into a MetaKan episode record."""

    verdict = row.get("verdict", "")
    decision = row.get("decision") or {}
    decision_status = row.get("decision_status") or decision.get("status") or ""
    context = row.get("context") or {}
    missing_context = list(
        row.get("missing_context")
        or decision.get("missing_context")
        or decision.get("metadata", {}).get("missing_context")
        or []
    )
    expected = row.get("expected_compatible")
    predicted = row.get("predicted_compatible")
    score = row.get("score")
    domain = row.get("domain", "")
    material_a = row.get("material_a", "")
    material_b = row.get("material_b", "")

    delta = _delta_from_row(verdict, decision_status, predicted, expected)
    resolution = _resolution_from_row(verdict, decision_status)
    pattern = classify_failure_pattern(row)
    relation = _relation_from_row(row)
    cat_confidence = _decision_confidence(row)
    evidence_confidence = 1.0 if expected is not None else 0.0

    episode = Episode(
        id=_episode_id(dataset_name, row),
        source=material_a,
        target=material_b,
        relation=relation,
        domain=domain,
        cat_says=bool(predicted) if predicted is not None else False,
        cat_confidence=cat_confidence,
        cat_strategy="compatibility_bridge",
        cat_path_count=1 if score is not None else 0,
        cat_path_lengths=[1] if score is not None else [],
        zfc_says=bool(expected) if expected is not None else False,
        zfc_confidence=evidence_confidence,
        zfc_method="external_evidence",
        zfc_witness=row.get("citation") or row.get("source"),
        delta_type=delta,
        resolution=resolution,
        resolution_notes=_resolution_notes(row, pattern),
    )
    if decision_status in FAILURE_DECISION_STATUSES:
        episode.delta_type = DeltaType.UNKNOWN
    episode._features = _episode_features(row, delta, resolution, pattern)

    return CompatibilityEpisodeRecord(
        episode=episode,
        pattern=pattern,
        source_row_id=row.get("id"),
        verdict=verdict,
        decision_status=decision_status,
        context=context,
        missing_context=missing_context,
        score=float(score) if score is not None else None,
        expected_compatible=expected,
        predicted_compatible=predicted,
    )


def build_failure_memory(
    results: Iterable[Dict[str, Any]],
    dataset_name: str = "compatibility",
    include_correct: bool = False,
) -> Dict[str, Any]:
    """Build a serializable failure-memory summary from audit results."""

    category = EpisodeCategory(f"{dataset_name}_failure_memory")
    records: List[CompatibilityEpisodeRecord] = []

    for row in results:
        if not should_record_episode(row, include_correct=include_correct):
            continue
        record = row_to_episode_record(row, dataset_name=dataset_name)
        category.add(record.episode)
        records.append(record)

    pattern_counts = Counter(record.pattern for record in records)
    verdict_counts = Counter(record.verdict for record in records)
    decision_counts = Counter(record.decision_status for record in records if record.decision_status)

    return {
        "dataset": dataset_name,
        "episode_count": len(records),
        "include_correct": include_correct,
        "pattern_counts": dict(sorted(pattern_counts.items())),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "decision_status_counts": dict(sorted(decision_counts.items())),
        "delta_distribution": {
            delta.name: count for delta, count in category.delta_distribution().items()
        },
        "resolution_distribution": {
            resolution.name: count
            for resolution, count in category.resolution_distribution().items()
        },
        "episodes": [record.to_dict() for record in records],
    }


def classify_failure_pattern(row: Dict[str, Any]) -> str:
    """Coarse source-backed failure taxonomy for compatibility misses."""

    verdict = row.get("verdict", "")
    domain = row.get("domain", "")
    decision_status = row.get("decision_status", "")
    decision = row.get("decision") or {}
    missing_context = (
        row.get("missing_context")
        or decision.get("missing_context")
        or decision.get("metadata", {}).get("missing_context")
        or []
    )

    if decision_status == "needs_context":
        missing = "+".join(sorted(str(item) for item in missing_context)) or "unknown"
        return f"abstention:missing_{missing}"
    if decision_status == "no_verdict" or verdict == "SKIP":
        return "no_verdict:scorer_unavailable_or_error"
    if verdict == "FP":
        if domain == "battery-polymer":
            return "false_positive:battery_polymer_context"
        if domain == "battery-metal":
            return "false_positive:battery_metal_context"
        if domain == "polymer":
            return "false_positive:polymer_miscibility"
        return f"false_positive:{domain or 'unknown'}"
    if verdict == "FN":
        materials = {str(row.get("material_a", "")), str(row.get("material_b", ""))}
        if domain == "glass" or materials & {"Soda_Lime", "FusedSilica", "Borosilicate"}:
            return "false_negative:glass_family_rule_gap"
        if domain == "semiconductor":
            return "false_negative:semiconductor_family_rule_gap"
        if domain == "battery-metal":
            return "false_negative:battery_metal_role_context"
        if domain == "battery-polymer":
            return "false_negative:battery_polymer_role_context"
        return f"false_negative:{domain or 'unknown'}"
    if verdict in {"TP", "TN"}:
        return f"confirmed:{domain or 'unknown'}"
    return f"unclassified:{domain or 'unknown'}"


def _delta_from_row(
    verdict: str,
    decision_status: str,
    predicted: Optional[bool],
    expected: Optional[bool],
) -> DeltaType:
    if decision_status in FAILURE_DECISION_STATUSES:
        return DeltaType.UNKNOWN
    if verdict == "TP":
        return DeltaType.AGREE
    if verdict == "TN":
        return DeltaType.REJECT
    if verdict == "FP":
        return DeltaType.HOLLOW
    if verdict == "FN":
        return DeltaType.ORPHAN
    if predicted is not None and expected is not None:
        if predicted and expected:
            return DeltaType.AGREE
        if not predicted and not expected:
            return DeltaType.REJECT
        if predicted and not expected:
            return DeltaType.HOLLOW
        return DeltaType.ORPHAN
    return DeltaType.UNKNOWN


def _resolution_from_row(verdict: str, decision_status: str) -> Resolution:
    if verdict in {"TP", "TN"}:
        return Resolution.CONFIRMED
    if verdict in {"FP", "FN"}:
        return Resolution.REFUTED
    if decision_status == "needs_context":
        return Resolution.REFRAMED
    return Resolution.UNRESOLVED


def _relation_from_row(row: Dict[str, Any]) -> str:
    context = row.get("context") or {}
    role = context.get("role") or row.get("role")
    if role:
        return f"compatible_as:{role}"
    interface_type = context.get("interface_type")
    if interface_type:
        return f"compatible_interface:{interface_type}"
    return "compatible_with"


def _decision_confidence(row: Dict[str, Any]) -> float:
    decision = row.get("decision") or {}
    if decision.get("confidence") is not None:
        return float(decision["confidence"])
    score = row.get("score")
    if score is None:
        return 0.0
    return max(0.25, min(0.95, 0.35 + 1.2 * abs(float(score) - 0.5)))


def _resolution_notes(row: Dict[str, Any], pattern: str) -> str:
    basis = row.get("evidence_basis") or row.get("citation") or ""
    if basis:
        return f"{pattern}: {basis}"
    return pattern


def _episode_id(dataset_name: str, row: Dict[str, Any]) -> str:
    payload = "|".join(
        str(item)
        for item in (
            dataset_name,
            row.get("id"),
            row.get("domain"),
            row.get("material_a"),
            row.get("material_b"),
            row.get("verdict"),
            row.get("decision_status"),
        )
    )
    return "compat-" + sha1(payload.encode("utf-8")).hexdigest()[:16]


def _episode_features(
    row: Dict[str, Any],
    delta: DeltaType,
    resolution: Resolution,
    pattern: str,
) -> List[float]:
    score = row.get("score")
    expected = row.get("expected_compatible")
    predicted = row.get("predicted_compatible")
    decision = row.get("decision") or {}
    missing_context = (
        row.get("missing_context")
        or decision.get("missing_context")
        or decision.get("metadata", {}).get("missing_context")
        or []
    )
    return [
        1.0 if predicted else 0.0,
        float(score) if score is not None else 0.0,
        1.0 if expected else 0.0,
        min(len(missing_context) / 5.0, 1.0),
        float(delta.value) / 5.0,
        float(resolution.value) / 5.0,
        _stable_unit(row.get("domain", "")),
        _stable_unit(row.get("material_a", "")),
        _stable_unit(row.get("material_b", "")),
        _stable_unit(pattern),
    ]


def _stable_unit(value: Any) -> float:
    digest = sha1(str(value).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF
