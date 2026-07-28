# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Strict Yoneda/Kan-style transfer guard for compatibility cases.

This is intentionally conservative.  It does not hallucinate compatibility
from vague similarity.  It only allows transfer when sourced calibration/dev
cases have high structural/context overlap and agree on the outcome.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from oracle.compatibility_calibration import load_default_calibration
from oracle.compatibility_context import CompatibilityContext


TRANSFER_THRESHOLD = 0.82
MIN_SUPPORT = 2


@dataclass(frozen=True)
class TransferCase:
    """A source-backed compatibility case available for transfer."""

    material_a: str
    material_b: str
    domain: str
    score: float
    expected_compatible: bool
    source: str
    context: Dict[str, Any] = field(default_factory=dict)
    evidence_basis: str = ""

    def identity(self) -> tuple:
        return (
            self.domain,
            tuple(sorted((self.material_a, self.material_b))),
            self.context.get("role"),
            self.context.get("interface_type"),
            self.context.get("electrolyte"),
        )


@dataclass(frozen=True)
class TransferGuardResult:
    """Result from the strict transfer gate."""

    allowed: bool
    similarity: float
    support_n: int
    compatible: Optional[bool]
    score: Optional[float]
    threshold: float
    reason: str
    nearest_cases: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "similarity": round(self.similarity, 4),
            "support_n": self.support_n,
            "compatible": self.compatible,
            "score": None if self.score is None else round(self.score, 4),
            "threshold": self.threshold,
            "reason": self.reason,
            "nearest_cases": self.nearest_cases,
        }


def load_transfer_cases() -> List[TransferCase]:
    """Load transfer cases from the generated calibration artifact."""

    store = load_default_calibration()
    rows = store.artifact.get("rows", [])
    cases: List[TransferCase] = []
    for row in rows:
        if row.get("score") is None or row.get("expected_compatible") is None:
            continue
        cases.append(
            TransferCase(
                material_a=str(row.get("material_a", "")),
                material_b=str(row.get("material_b", "")),
                domain=str(row.get("domain", "")),
                score=float(row.get("score")),
                expected_compatible=bool(row.get("expected_compatible")),
                source=str(row.get("source", "")),
                context=dict(row.get("context") or {}),
                evidence_basis=str(row.get("evidence_basis") or ""),
            )
        )
    return cases


def guard_transfer(
    material_a: str,
    material_b: str,
    domain: str,
    context: Optional[CompatibilityContext] = None,
    cases: Optional[Iterable[TransferCase]] = None,
    threshold: float = TRANSFER_THRESHOLD,
    min_support: int = MIN_SUPPORT,
) -> TransferGuardResult:
    """Return a transfer vote only when structurally similar cases agree."""

    context = context or CompatibilityContext()
    query_identity = _identity(domain, material_a, material_b, context.to_dict())
    ranked = []
    for case in cases if cases is not None else load_transfer_cases():
        if case.domain != domain:
            continue
        if case.identity() == query_identity:
            continue
        similarity = _case_similarity(material_a, material_b, domain, context.to_dict(), case)
        if similarity <= 0:
            continue
        ranked.append((similarity, case))

    ranked.sort(key=lambda item: item[0], reverse=True)
    nearest = ranked[:5]
    support = [(sim, case) for sim, case in nearest if sim >= threshold]
    nearest_payload = [_case_payload(sim, case) for sim, case in nearest]

    if len(support) < min_support:
        return TransferGuardResult(
            allowed=False,
            similarity=nearest[0][0] if nearest else 0.0,
            support_n=len(support),
            compatible=None,
            score=None,
            threshold=threshold,
            reason="insufficient structurally similar sourced support",
            nearest_cases=nearest_payload,
        )

    labels = {case.expected_compatible for _, case in support}
    if len(labels) != 1:
        return TransferGuardResult(
            allowed=False,
            similarity=support[0][0],
            support_n=len(support),
            compatible=None,
            score=None,
            threshold=threshold,
            reason="similar sourced cases disagree",
            nearest_cases=nearest_payload,
        )

    weighted_score = sum(sim * case.score for sim, case in support) / sum(sim for sim, _ in support)
    compatible = next(iter(labels))
    return TransferGuardResult(
        allowed=True,
        similarity=support[0][0],
        support_n=len(support),
        compatible=compatible,
        score=weighted_score,
        threshold=threshold,
        reason="strict Yoneda/Kan transfer guard passed",
        nearest_cases=nearest_payload,
    )


def _case_similarity(
    material_a: str,
    material_b: str,
    domain: str,
    context: Dict[str, Any],
    case: TransferCase,
) -> float:
    query_features = _features(domain, material_a, material_b, context)
    case_features = _features(case.domain, case.material_a, case.material_b, case.context)
    if not query_features or not case_features:
        return 0.0
    intersection = len(query_features & case_features)
    union = len(query_features | case_features)
    base = intersection / union if union else 0.0

    context_match = _context_match_score(context, case.context)
    return 0.75 * base + 0.25 * context_match


def _features(domain: str, material_a: str, material_b: str, context: Dict[str, Any]) -> Set[str]:
    features = {f"domain:{domain}"}
    for material in (material_a, material_b):
        for token in _material_tokens(material):
            features.add(f"mat:{token}")
    for key in ("role", "interface_type", "electrolyte", "voltage_context", "coating", "environment"):
        value = context.get(key)
        if value not in (None, "", False):
            features.add(f"{key}:{str(value).lower()}")
    return features


def _material_tokens(material: str) -> Set[str]:
    name = str(material)
    lower = name.lower()
    tokens = {lower}
    for sep in ("_", "-", "/", "+"):
        tokens.update(part.lower() for part in name.split(sep) if part)
    if "sic" in lower:
        tokens.add("sic")
        tokens.add("wide_bandgap")
    if lower in {"gan", "aln", "algan"}:
        tokens.add("nitride")
        tokens.add("wide_bandgap")
    if lower in {"llzo", "nasicon"}:
        tokens.add("oxide_solid_electrolyte")
    if lower in {"li3ps4", "lgps"}:
        tokens.add("sulfide_solid_electrolyte")
    if lower in {"bk7", "fusedsilica", "fused_silica"}:
        tokens.add("optical_glass")
        tokens.add("silicate_glass")
    if lower in {"pzt", "batio3"}:
        tokens.add("piezoelectric_ceramic")
    if lower in {"al2o3", "alumina"}:
        tokens.add("alumina")
    return tokens


def _context_match_score(query: Dict[str, Any], case: Dict[str, Any]) -> float:
    keys = {"role", "interface_type", "electrolyte", "voltage_context", "coating", "environment"}
    present = [key for key in keys if query.get(key) or case.get(key)]
    if not present:
        return 0.5
    matches = sum(1 for key in present if query.get(key) == case.get(key) and query.get(key) is not None)
    return matches / len(present)


def _case_payload(similarity: float, case: TransferCase) -> Dict[str, Any]:
    return {
        "similarity": round(similarity, 4),
        "material_a": case.material_a,
        "material_b": case.material_b,
        "domain": case.domain,
        "score": round(case.score, 4),
        "expected_compatible": case.expected_compatible,
        "source": case.source,
        "context": dict(case.context),
    }


def _identity(domain: str, material_a: str, material_b: str, context: Dict[str, Any]) -> tuple:
    return (
        domain,
        tuple(sorted((material_a, material_b))),
        context.get("role"),
        context.get("interface_type"),
        context.get("electrolyte"),
    )
