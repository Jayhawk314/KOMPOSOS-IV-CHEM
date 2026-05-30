# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""PHARM-style strategy ensemble for compatibility scoring."""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional

from oracle.compatibility_calibration import load_default_calibration
from oracle.compatibility_capabilities import capability_report
from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_failure_memory import classify_failure_pattern
from oracle.compatibility_gray_coherence import check_gray_coherence
from oracle.compatibility_transfer import guard_transfer
from oracle.typed_morphisms import infer_typed_morphism
from oracle.simplicial_strategies import (
    SimplicialYonedaStrategy,
    FibrationTransportStrategy,
    build_domain_category,
)
from categorical.dempster_shafer import MassFunction, combine, discount


_DS_VIABLE = frozenset({"viable"})
_DS_INCOMPATIBLE = frozenset({"incompatible"})
_DS_THETA = frozenset({"viable", "incompatible"})


GRAY_ACTIVE_SEVERITY_THRESHOLD = 0.35

DEFAULT_STRATEGY_WEIGHTS = {
    "rule_scorer": 1.00,
    "typed_morphism": 1.35,
    "calibration": 0.65,
    "yoneda_transfer_guard": 0.75,
    "zfc_constraint": 1.10,
    "failure_memory_gate": 0.90,
    "real_tool_evidence": 1.50,
    "gray_coherence": 0.80,
    "simplicial_yoneda": 0.75,
    "fibration_transport": 0.25,
    "rezk_equivalence": 1.25,
}


@dataclass(frozen=True)
class StrategyVote:
    """A single strategy vote in the compatibility ensemble."""

    strategy: str
    score: float
    compatible: bool
    confidence: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "score": round(self.score, 4),
            "compatible": self.compatible,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CompatibilityEnsembleResult:
    """Combined compatibility result with path features and guard decisions."""

    score: float
    compatible: bool
    confidence: float
    votes: List[StrategyVote]
    path_features: Dict[str, Any]
    failure_gate: Dict[str, Any]
    transfer_guard: Dict[str, Any]
    gray_coherence: Dict[str, Any]
    gray_policy: Dict[str, Any]
    capabilities: Dict[str, Any]
    action: str = "metadata_only"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "compatible": self.compatible,
            "confidence": round(self.confidence, 4),
            "action": self.action,
            "votes": [vote.to_dict() for vote in self.votes],
            "path_features": dict(self.path_features),
            "failure_gate": dict(self.failure_gate),
            "transfer_guard": dict(self.transfer_guard),
            "gray_coherence": dict(self.gray_coherence),
            "gray_policy": dict(self.gray_policy),
            "capabilities": dict(self.capabilities),
        }


def build_compatibility_ensemble(
    material_a: str,
    material_b: str,
    domain: str,
    base_score: float,
    base_predicted: bool,
    context: Optional[CompatibilityContext] = None,
    md_results: Optional[Dict[str, Any]] = None,
    strategy_weights: Optional[Dict[str, float]] = None,
) -> CompatibilityEnsembleResult:
    """Build the bounded compatibility strategy ensemble."""

    context = context or CompatibilityContext()
    weights = strategy_weights or DEFAULT_STRATEGY_WEIGHTS
    votes: List[StrategyVote] = [
        StrategyVote(
            strategy="rule_scorer",
            score=_clamp(base_score),
            compatible=bool(base_predicted),
            confidence=_heuristic_confidence(base_score),
            reason="base bridge scorer",
        )
    ]

    morphism = infer_typed_morphism(material_a, material_b, domain, context)
    if morphism is not None and morphism.score is not None and morphism.compatible is not None:
        votes.append(
            StrategyVote(
                strategy="typed_morphism",
                score=_clamp(morphism.score),
                compatible=bool(morphism.compatible),
                confidence=_clamp(morphism.confidence),
                reason=morphism.reasons[0] if morphism.reasons else morphism.relation,
                metadata=morphism.to_dict(),
            )
        )

    calibration_vote = _calibration_vote(base_score, domain)
    if calibration_vote is not None:
        votes.append(calibration_vote)

    transfer = guard_transfer(material_a, material_b, domain, context)
    if transfer.allowed and transfer.score is not None and transfer.compatible is not None:
        votes.append(
            StrategyVote(
                strategy="yoneda_transfer_guard",
                score=_clamp(transfer.score),
                compatible=bool(transfer.compatible),
                confidence=min(0.90, 0.45 + 0.12 * transfer.support_n + 0.25 * transfer.similarity),
                reason=transfer.reason,
                metadata=transfer.to_dict(),
            )
        )

    failure_gate = _failure_memory_gate(material_a, material_b, domain, base_score, base_predicted, context)
    if failure_gate["applied"]:
        votes.append(
            StrategyVote(
                strategy="failure_memory_gate",
                score=failure_gate["score"],
                compatible=failure_gate["compatible"],
                confidence=failure_gate["confidence"],
                reason=failure_gate["reason"],
                metadata=failure_gate,
            )
        )

    if md_results:
        md_vote = _real_tool_vote(md_results)
        if md_vote is not None:
            votes.append(md_vote)

    zfc_vote = _zfc_constraint_vote(material_a, material_b, base_score, morphism)
    if zfc_vote is not None:
        votes.append(zfc_vote)

    from oracle.simplicial_strategies import (
        score_simplicial_yoneda,
        score_fibration_transport,
        score_rezk_equivalence,
    )

    # Build domain category once; pass to all three STT strategies so we do not
    # repeat the O(n²) pairwise validation on every call.
    _domain_cat = build_domain_category(domain)

    sy = score_simplicial_yoneda(material_a, material_b, domain, category=_domain_cat)
    votes.append(
        StrategyVote(
            strategy="simplicial_yoneda",
            score=sy["score"],
            compatible=sy["compatible"],
            confidence=sy["confidence"],
            reason=sy["reason"],
            metadata=sy["metadata"],
        )
    )

    ft = score_fibration_transport(material_a, material_b, domain, category=_domain_cat)
    votes.append(
        StrategyVote(
            strategy="fibration_transport",
            score=ft["score"],
            compatible=ft["compatible"],
            confidence=ft["confidence"],
            reason=ft["reason"],
            metadata=ft["metadata"],
        )
    )

    re = score_rezk_equivalence(material_a, material_b, domain, category=_domain_cat)
    votes.append(
        StrategyVote(
            strategy="rezk_equivalence",
            score=re["score"],
            compatible=re["compatible"],
            confidence=re["confidence"],
            reason=re["reason"],
            metadata=re["metadata"],
        )
    )

    gray = check_gray_coherence(material_a, material_b, domain, votes, context)
    if gray.gap_count:
        votes.append(
            StrategyVote(
                strategy="gray_coherence",
                score=0.50,
                compatible=bool(base_predicted),
                confidence=min(0.88, max(0.35, gray.max_gap_severity)),
                reason=gray.reason,
                metadata=gray.to_dict(),
            )
        )

    path_features = _path_features(votes)
    score = _combine_votes(votes, path_features, weights)
    gray_policy = _apply_gray_policy(votes, gray.to_dict(), score)
    score = gray_policy["score"]
    compatible = bool(gray_policy["compatible"])
    confidence = _combined_confidence(votes, path_features)

    action = "ensemble_candidate"
    if failure_gate["applied"]:
        action = "failure_gated"
    elif morphism is not None and morphism.veto:
        action = "typed_veto"
    elif transfer.allowed:
        action = "transfer_supported"
    elif gray_policy["applied"]:
        action = "gray_coherence_guarded"
    elif gray.gap_count:
        action = "gray_coherence_metadata"

    return CompatibilityEnsembleResult(
        score=score,
        compatible=compatible,
        confidence=confidence,
        votes=votes,
        path_features=path_features,
        failure_gate=failure_gate,
        transfer_guard=transfer.to_dict(),
        gray_coherence=gray.to_dict(),
        gray_policy=gray_policy,
        capabilities=capability_report(domain),
        action=action,
    )


def _calibration_vote(base_score: float, domain: str) -> Optional[StrategyVote]:
    try:
        calibration = load_default_calibration().calibrate(base_score, domain)
    except Exception:
        return None
    probability = calibration.get("calibrated_probability")
    if probability is None:
        return None
    support_n = int(calibration.get("support_n") or 0)
    confidence = min(0.82, 0.35 + min(support_n, 30) / 60.0)
    return StrategyVote(
        strategy="calibration",
        score=_clamp(float(probability)),
        compatible=float(probability) >= 0.50,
        confidence=confidence,
        reason=f"score-bin reliability calibration ({calibration.get('calibrator')})",
        metadata=calibration,
    )


def _failure_memory_gate(
    material_a: str,
    material_b: str,
    domain: str,
    base_score: float,
    base_predicted: bool,
    context: CompatibilityContext,
) -> Dict[str, Any]:
    synthetic_row = {
        "material_a": material_a,
        "material_b": material_b,
        "domain": domain,
        "score": base_score,
        "predicted_compatible": base_predicted,
        "expected_compatible": False if base_predicted else True,
        "verdict": "FP" if base_predicted else "FN",
        "decision_status": "compatible" if base_predicted else "incompatible",
        "context": context.to_dict(),
    }
    candidate_pattern = classify_failure_pattern(synthetic_row)
    try:
        memory = load_default_calibration().artifact.get("failure_memory", {})
    except Exception:
        memory = {}
    count = int(memory.get("pattern_counts", {}).get(candidate_pattern, 0))
    if not count:
        return {
            "applied": False,
            "pattern": candidate_pattern,
            "historical_count": 0,
            "reason": "no matching historical failure pattern",
        }

    if base_predicted:
        gated_score = min(_clamp(base_score), 0.42)
        compatible = False
        reason = "historical false-positive family gate lowered score"
    else:
        gated_score = max(_clamp(base_score), 0.58)
        compatible = True
        reason = "historical false-negative family gate raised score"
    return {
        "applied": True,
        "pattern": candidate_pattern,
        "historical_count": count,
        "score": gated_score,
        "compatible": compatible,
        "confidence": min(0.86, 0.50 + 0.08 * count),
        "reason": reason,
    }


def _real_tool_vote(md_results: Dict[str, Any]) -> Optional[StrategyVote]:
    if not md_results.get("measured_md"):
        return None
    score = md_results.get("score")
    if score is None:
        return None
    return StrategyVote(
        strategy="real_tool_evidence",
        score=_clamp(float(score)),
        compatible=bool(md_results.get("viable")),
        confidence=_clamp(float(md_results.get("confidence") or 0.0)),
        reason="measured MD/real-tool evidence",
        metadata=md_results,
    )


def _zfc_constraint_vote(material_a: str, material_b: str, base_score: float, morphism: Any) -> Optional[StrategyVote]:
    if morphism is not None and morphism.veto:
        return StrategyVote(
            strategy="zfc_constraint",
            score=min(_clamp(base_score), _clamp(morphism.score or 0.0)),
            compatible=False,
            confidence=_clamp(morphism.confidence),
            reason="typed morphism veto is a logical constraint veto",
            metadata={"relation": morphism.relation, "logical_verifier": "constraint_veto"},
        )
    return None


def _path_features(votes: List[StrategyVote]) -> Dict[str, Any]:
    confidences = [vote.confidence for vote in votes]
    strategies = {vote.strategy for vote in votes}
    compatible_votes = sum(1 for vote in votes if vote.compatible)
    agreement = max(compatible_votes, len(votes) - compatible_votes) / max(len(votes), 1)
    direct = any(v.strategy in {"rule_scorer", "typed_morphism", "real_tool_evidence"} for v in votes)
    return {
        "chain_length": 1 if direct else 2,
        "min_confidence": min(confidences) if confidences else 0.0,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        "num_strategies": len(strategies),
        "strategy_agreement": round(agreement, 4),
        "has_direct_evidence": direct,
    }


def _apply_gray_policy(votes: List[StrategyVote], gray: Dict[str, Any], score: float) -> Dict[str, Any]:
    """Use Gray gaps as a guard against incoherent indirect ensemble flips."""

    direct_votes = [
        vote for vote in votes
        if vote.strategy in {"real_tool_evidence", "zfc_constraint", "typed_morphism", "rule_scorer"}
    ]
    compatible = score >= 0.50
    base = {
        "applied": False,
        "score": round(_clamp(score), 4),
        "compatible": compatible,
        "threshold": GRAY_ACTIVE_SEVERITY_THRESHOLD,
        "reason": "gray coherence did not change the ensemble verdict",
    }

    if not gray.get("gap_count") or not direct_votes:
        return base
    if float(gray.get("max_gap_severity") or 0.0) < GRAY_ACTIVE_SEVERITY_THRESHOLD:
        return {
            **base,
            "reason": "gray coherence gap below active guard threshold",
        }

    direct_side = _direct_evidence_side(direct_votes)
    if direct_side is None:
        return {
            **base,
            "reason": "direct evidence did not have a stable side to guard",
        }

    direct_score = _direct_guard_score(direct_votes, direct_side)
    if direct_side == compatible:
        guarded = max(score, direct_score) if direct_side else min(score, direct_score)
        return {
            **base,
            "score": round(_clamp(guarded), 4),
            "compatible": direct_side,
            "direct_side": direct_side,
            "direct_score": round(direct_score, 4),
            "reason": "gray gap confirmed but direct evidence already controlled verdict",
        }

    guarded = max(0.51, direct_score) if direct_side else min(0.49, direct_score)
    return {
        "applied": True,
        "score": round(_clamp(guarded), 4),
        "compatible": direct_side,
        "threshold": GRAY_ACTIVE_SEVERITY_THRESHOLD,
        "direct_side": direct_side,
        "direct_score": round(direct_score, 4),
        "reason": "Gray 3-cell gap blocked incoherent indirect ensemble flip",
    }


def _direct_evidence_side(votes: List[StrategyVote]) -> Optional[bool]:
    weighted: Dict[bool, float] = {True: 0.0, False: 0.0}
    for vote in votes:
        weighted[vote.compatible] += _direct_authority(vote.strategy) * vote.confidence
    if weighted[True] == weighted[False]:
        return None
    return weighted[True] > weighted[False]


def _direct_guard_score(votes: List[StrategyVote], direct_side: bool) -> float:
    supporting = [vote for vote in votes if vote.compatible == direct_side]
    if not supporting:
        return 0.5
    total_weight = sum(_direct_authority(vote.strategy) * vote.confidence for vote in supporting)
    if not total_weight:
        return 0.5
    weighted_score = sum(
        _direct_authority(vote.strategy) * vote.confidence * vote.score
        for vote in supporting
    ) / total_weight
    if direct_side:
        return max(0.51, weighted_score)
    return min(0.49, weighted_score)


def _direct_authority(strategy: str) -> float:
    return {
        "real_tool_evidence": 4.0,
        "zfc_constraint": 3.0,
        "typed_morphism": 2.5,
        "rule_scorer": 1.5,
    }.get(strategy, 1.0)


def _vote_mass(vote: StrategyVote) -> MassFunction:
    """Map a strategy vote to a Dempster-Shafer mass function over {viable, incompatible}.

    Confidence becomes belief commitment; the remainder (1 - confidence) is mass on
    the full frame (ignorance). The score splits the committed mass between viable
    and incompatible.
    """
    c = max(0.0, min(1.0, float(vote.confidence)))
    s = max(0.0, min(1.0, float(vote.score)))
    return MassFunction({
        _DS_VIABLE: s * c,
        _DS_INCOMPATIBLE: (1.0 - s) * c,
        _DS_THETA: 1.0 - c,
    })


def _combine_votes(votes: List[StrategyVote], features: Dict[str, Any], weights: Dict[str, float]) -> float:
    """Dempster-Shafer fusion of the strategy votes.

    Each vote is discounted by its per-strategy reliability (the strategy weight,
    normalized to [0, 1]) and combined with Dempster's rule. The returned score is
    the pignistic probability of "viable"; belief/plausibility/conflict are stashed
    in ``features`` for the uncertainty display.
    """
    if not votes:
        return 0.0

    max_w = max(weights.values()) if weights else 1.0
    if max_w <= 0:
        max_w = 1.0

    discounted = [
        discount(_vote_mass(vote), weights.get(vote.strategy, 1.0) / max_w)
        for vote in votes
    ]

    fused = discounted[0]
    max_conflict = 0.0
    for mass in discounted[1:]:
        try:
            fused, conflict = combine(fused, mass)
            max_conflict = max(max_conflict, conflict)
        except ValueError:
            # Total contradiction (K=1) between this source and the running fusion;
            # keep the accumulated belief and flag the conflict honestly.
            max_conflict = 1.0
            continue

    belief = fused.belief(_DS_VIABLE)
    plausibility = fused.plausibility(_DS_VIABLE)
    pignistic = fused.pignistic_probability("viable")

    features["dempster_shafer"] = {
        "method": "dempster_shafer",
        "pignistic_viable": round(pignistic, 4),
        "belief_viable": round(belief, 4),
        "plausibility_viable": round(plausibility, 4),
        "uncertainty": round(plausibility - belief, 4),
        "max_conflict": round(max_conflict, 4),
        "num_sources": len(discounted),
    }
    return round(pignistic, 4)


def _combined_confidence(votes: List[StrategyVote], features: Dict[str, Any]) -> float:
    if not votes:
        return 0.0
    avg = float(features.get("avg_confidence", 0.0))
    agreement = float(features.get("strategy_agreement", 0.0))
    support_bonus = min(0.12, 0.02 * len(votes))
    return round(min(0.95, 0.55 * avg + 0.35 * agreement + support_bonus), 4)


def _heuristic_confidence(score: float) -> float:
    return max(0.25, min(0.95, 0.35 + 1.2 * abs(float(score) - 0.5)))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
