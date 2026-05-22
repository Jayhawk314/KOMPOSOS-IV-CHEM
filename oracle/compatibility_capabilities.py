# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Typed capability declarations for compatibility scoring modules."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set


@dataclass(frozen=True)
class CompatibilityCapability:
    """A math/evidence capability provided by a compatibility domain."""

    name: str
    structure: str
    operations: List[str] = field(default_factory=list)
    quantale: str | None = None
    description: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "structure": self.structure,
            "operations": list(self.operations),
            "quantale": self.quantale,
            "description": self.description,
        }


@dataclass(frozen=True)
class CapabilityCheck:
    """Result of checking required capabilities for a domain."""

    domain: str
    required: List[str]
    provided: List[str]
    missing: List[str]

    @property
    def compatible(self) -> bool:
        return not self.missing

    def to_dict(self) -> Dict[str, object]:
        return {
            "domain": self.domain,
            "compatible": self.compatible,
            "required": list(self.required),
            "provided": list(self.provided),
            "missing": list(self.missing),
        }


BASE_CAPABILITIES = {
    "rule_scorer": CompatibilityCapability(
        "rule_scorer",
        "Category",
        ["score_pair", "explain_components"],
        description="Domain bridge rule/physics scorer.",
    ),
    "typed_context": CompatibilityCapability(
        "typed_context",
        "TypedSchema",
        ["role", "electrolyte", "environment", "interface_type", "temperature_C"],
        description="Application context schema for non-pair-only compatibility.",
    ),
    "calibration": CompatibilityCapability(
        "calibration",
        "ReliabilityCalibrator",
        ["brier", "ece", "score_bins", "domain_bins"],
        description="Binned score reliability calibration.",
    ),
    "failure_memory": CompatibilityCapability(
        "failure_memory",
        "MetaKanEpisodeStore",
        ["record_episode", "classify_failure_pattern", "gate_recurrent_failure"],
        description="MetaKan-style memory for false positives, false negatives, and abstentions.",
    ),
    "ensemble": CompatibilityCapability(
        "ensemble",
        "StrategyCombiner",
        ["combine_votes", "weighted_average", "logistic_features"],
        description="PHARM-style strategy vote combiner.",
    ),
    "zfc_constraints": CompatibilityCapability(
        "zfc_constraints",
        "LogicalVerifier",
        ["constraint_vote", "veto_detection"],
        description="ZFC/ZFC-like logical constraint verifier; checks consistency, not physical truth.",
    ),
    "real_tool_evidence": CompatibilityCapability(
        "real_tool_evidence",
        "ExternalMeasurement",
        ["md", "dft", "external_source_vote"],
        description="Evidence from real external tools or explicit source-backed observations.",
    ),
}

DOMAIN_CAPABILITY_NAMES: Dict[str, Set[str]] = {
    "battery-metal": {
        "rule_scorer",
        "typed_context",
        "typed_morphisms",
        "quantale_bottleneck",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "battery-polymer": {
        "rule_scorer",
        "typed_context",
        "typed_morphisms",
        "quantale_bottleneck",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "ceramic": {
        "rule_scorer",
        "typed_context",
        "typed_morphisms",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "semiconductor": {
        "rule_scorer",
        "typed_context",
        "typed_morphisms",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "glass": {
        "rule_scorer",
        "typed_context",
        "typed_morphisms",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "polymer": {
        "rule_scorer",
        "typed_context",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
    "metal": {
        "rule_scorer",
        "typed_context",
        "calibration",
        "failure_memory",
        "ensemble",
        "zfc_constraints",
        "real_tool_evidence",
        "yoneda_transfer_guard",
    },
}

EXTRA_CAPABILITIES = {
    "typed_morphisms": CompatibilityCapability(
        "typed_morphisms",
        "TypedMorphismCategory",
        ["infer_relation", "apply_prior", "apply_veto"],
        description="Role/interface-specific compatibility morphisms.",
    ),
    "quantale_bottleneck": CompatibilityCapability(
        "quantale_bottleneck",
        "EnrichedCategory",
        ["min_bottleneck", "probabilistic_or", "multiplicative_confidence"],
        quantale="min/probabilistic_or/multiplicative",
        description="Quantale diagnostics for bottleneck and compounded risk.",
    ),
    "yoneda_transfer_guard": CompatibilityCapability(
        "yoneda_transfer_guard",
        "YonedaTransferGuard",
        ["case_similarity", "strict_threshold", "conflict_check"],
        description="Strict structural-transfer gate over source-backed compatibility cases.",
    ),
}


def capabilities_for_domain(domain: str) -> List[CompatibilityCapability]:
    """Return typed capabilities advertised by a compatibility domain."""

    names = DOMAIN_CAPABILITY_NAMES.get(domain, {"rule_scorer", "calibration", "ensemble"})
    registry = {**BASE_CAPABILITIES, **EXTRA_CAPABILITIES}
    return [registry[name] for name in sorted(names) if name in registry]


def check_capabilities(domain: str, required: Iterable[str]) -> CapabilityCheck:
    """Check whether a domain provides all required math/evidence capabilities."""

    required_list = sorted(set(required))
    provided = sorted(cap.name for cap in capabilities_for_domain(domain))
    provided_set = set(provided)
    missing = [name for name in required_list if name not in provided_set]
    return CapabilityCheck(
        domain=domain,
        required=required_list,
        provided=provided,
        missing=missing,
    )


def capability_report(domain: str) -> Dict[str, object]:
    """Serializable capability report for API/audit metadata."""

    return {
        "domain": domain,
        "capabilities": [cap.to_dict() for cap in capabilities_for_domain(domain)],
    }
