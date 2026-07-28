# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Typed compatibility morphisms for context-aware material scoring.

The same unordered material pair can mean different chemistry depending on
role and environment.  A typed morphism makes the relation explicit, e.g.
``Al_foil --cathode_collector_for[LiPF6]--> NMC622`` instead of a plain
``Al_foil + NMC622`` pair score.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from oracle.compatibility_context import CompatibilityContext


CATHODE_COLLECTOR_ROLES = {
    "cathode_collector",
    "positive_collector",
    "positive_current_collector",
}
ANODE_COLLECTOR_ROLES = {
    "anode_collector",
    "negative_collector",
    "negative_current_collector",
}
TAB_ROLES = {
    "tab",
    "tab_connector",
    "collector_tab",
    "cell_tab",
}


@dataclass(frozen=True)
class TypedCompatibilityMorphism:
    """A role/context-specific compatibility relation."""

    source: str
    target: str
    domain: str
    relation: str
    compatible: Optional[bool]
    score: Optional[float]
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    required_context: Tuple[str, ...] = ()
    reasons: Tuple[str, ...] = ()
    evidence_type: str = "rule"
    veto: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "domain": self.domain,
            "relation": self.relation,
            "compatible": self.compatible,
            "score": None if self.score is None else round(float(self.score), 4),
            "confidence": round(float(self.confidence), 4),
            "context": dict(self.context),
            "required_context": list(self.required_context),
            "reasons": list(self.reasons),
            "evidence_type": self.evidence_type,
            "veto": self.veto,
        }


@dataclass(frozen=True)
class TypedMorphismAdjustment:
    """Base score plus any typed-morphism adjustment."""

    score: float
    predicted_compatible: bool
    base_score: float
    base_predicted_compatible: bool
    action: str
    morphism: Optional[TypedCompatibilityMorphism] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(float(self.score), 4),
            "predicted_compatible": bool(self.predicted_compatible),
            "base_score": round(float(self.base_score), 4),
            "base_predicted_compatible": bool(self.base_predicted_compatible),
            "action": self.action,
            "morphism": self.morphism.to_dict() if self.morphism else None,
        }


def normalize_role(role: Optional[str]) -> str:
    """Normalize role labels from datasets, APIs, and UI inputs."""

    return (role or "").strip().lower().replace("-", "_").replace(" ", "_")


def infer_typed_morphism(
    material_a: str,
    material_b: str,
    domain: str,
    context: Optional[CompatibilityContext] = None,
) -> Optional[TypedCompatibilityMorphism]:
    """Infer a typed morphism for a pair when a supported domain is known."""

    domain_key = (domain or "").lower()
    context = context or CompatibilityContext()

    if domain_key == "battery-metal":
        return _infer_battery_metal_morphism(material_a, material_b, context)
    if domain_key == "ceramic":
        return _infer_ceramic_morphism(material_a, material_b, context)
    if domain_key == "semiconductor":
        return _infer_semiconductor_morphism(material_a, material_b, context)
    if domain_key == "glass":
        return _infer_glass_morphism(material_a, material_b, context)

    return None


def apply_typed_morphism_adjustment(
    base_score: float,
    base_predicted_compatible: bool,
    material_a: str,
    material_b: str,
    domain: str,
    context: Optional[CompatibilityContext] = None,
) -> TypedMorphismAdjustment:
    """Apply a typed-morphism prior/veto to an existing bridge score."""

    score = max(0.0, min(1.0, float(base_score)))
    base_predicted = bool(base_predicted_compatible)
    morphism = infer_typed_morphism(material_a, material_b, domain, context)
    if morphism is None or morphism.compatible is None or morphism.score is None:
        return TypedMorphismAdjustment(
            score=score,
            predicted_compatible=base_predicted,
            base_score=score,
            base_predicted_compatible=base_predicted,
            action="none",
            morphism=morphism,
        )

    morphism_score = max(0.0, min(1.0, float(morphism.score)))
    if morphism.veto or (morphism.compatible is False and morphism.confidence >= 0.70):
        adjusted = min(score, morphism_score)
        action = "veto" if morphism.veto else "negative_prior"
    elif morphism.compatible is True and morphism.confidence >= 0.70:
        adjusted = max(score, morphism_score)
        action = "positive_prior"
    else:
        adjusted = score
        action = "evidence_only"

    return TypedMorphismAdjustment(
        score=round(adjusted, 4),
        predicted_compatible=adjusted >= 0.50,
        base_score=score,
        base_predicted_compatible=base_predicted,
        action=action,
        morphism=morphism,
    )


def _infer_battery_metal_morphism(
    material_a: str,
    material_b: str,
    context: CompatibilityContext,
) -> Optional[TypedCompatibilityMorphism]:
    try:
        from battery_bridge.material_properties import MaterialClass, get_material as get_battery_material
        from metal_bridge.material_properties import get_metal
    except ImportError:
        return None

    metal_name = material_a if get_metal(material_a) is not None else material_b
    electrode_name = material_b if metal_name == material_a else material_a
    metal = get_metal(metal_name)
    electrode = get_battery_material(electrode_name)
    if metal is None or electrode is None:
        return None

    role = normalize_role(context.role)
    if not role:
        if metal_name.endswith("_tab"):
            role = "tab_connector"
        elif electrode.material_class == MaterialClass.CATHODE:
            role = "cathode_collector"
        elif electrode.material_class == MaterialClass.ANODE:
            role = "anode_collector"
        else:
            role = "current_collector"

    electrolyte = context.electrolyte
    base_metal = _base_metal(metal_name)
    morphism_context = context.to_dict()
    morphism_context["role"] = role

    if role in TAB_ROLES:
        return _battery_tab_morphism(metal_name, electrode_name, base_metal, morphism_context)

    if role in CATHODE_COLLECTOR_ROLES:
        if electrode.material_class != MaterialClass.CATHODE:
            return _battery_metal_morphism(
                metal_name,
                electrode_name,
                "not_cathode_collector_for",
                False,
                0.20,
                0.88,
                morphism_context,
                "Cathode-collector role was requested for a non-cathode battery material.",
                veto=True,
            )
        return _cathode_collector_morphism(
            metal_name,
            electrode_name,
            base_metal,
            electrolyte,
            context.coating,
            morphism_context,
        )

    if role in ANODE_COLLECTOR_ROLES:
        if electrode.material_class != MaterialClass.ANODE:
            return _battery_metal_morphism(
                metal_name,
                electrode_name,
                "not_anode_collector_for",
                False,
                0.20,
                0.88,
                morphism_context,
                "Anode-collector role was requested for a non-anode battery material.",
                veto=True,
            )
        return _anode_collector_morphism(
            metal_name,
            electrode_name,
            base_metal,
            morphism_context,
        )

    return _battery_metal_morphism(
        metal_name,
        electrode_name,
        "current_collector_for",
        None,
        None,
        0.35,
        morphism_context,
        "Collector role is too generic for a high-confidence typed morphism.",
        required_context=("role",),
    )


def _cathode_collector_morphism(
    metal_name: str,
    electrode_name: str,
    base_metal: str,
    electrolyte: Optional[str],
    coating: Optional[str],
    context: Dict[str, Any],
) -> TypedCompatibilityMorphism:
    if base_metal == "Al":
        if electrolyte == "LiTFSI":
            return _battery_metal_morphism(
                metal_name,
                electrode_name,
                "not_cathode_collector_for",
                False,
                0.18,
                0.90,
                context,
                "Al current collectors corrode in LiTFSI cathode service without protection.",
                veto=True,
            )
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "cathode_collector_for",
            True,
            0.93,
            0.86 if electrolyte else 0.72,
            context,
            "Al foil is the standard positive-electrode collector in passivating Li-ion electrolytes.",
            required_context=() if electrolyte else ("electrolyte",),
        )

    if base_metal == "Cu":
        if coating:
            return _battery_metal_morphism(
                metal_name,
                electrode_name,
                "coated_cathode_collector_for",
                True,
                0.72,
                0.66,
                context,
                "Protective coatings can extend Cu cathode-side stability, but this is context-dependent.",
                required_context=("coating",),
            )
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "not_cathode_collector_for",
            False,
            0.12,
            0.91,
            context,
            "Bare Cu is not a cathode current collector because it dissolves at positive-electrode potentials.",
            veto=True,
        )

    if base_metal in {"SS", "Steel", "Fe"}:
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "not_standard_cathode_collector_for",
            False,
            0.30,
            0.78,
            context,
            "Stainless/steel hardware is not a standard high-conductivity cathode coating collector foil.",
            veto=True,
        )

    return _battery_metal_morphism(
        metal_name,
        electrode_name,
        "nonstandard_cathode_collector_for",
        None,
        None,
        0.40,
        context,
        "Cathode collector role requires source-backed metal-specific evidence.",
        required_context=("source_evidence",),
    )


def _anode_collector_morphism(
    metal_name: str,
    electrode_name: str,
    base_metal: str,
    context: Dict[str, Any],
) -> TypedCompatibilityMorphism:
    if base_metal == "Cu":
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "anode_collector_for",
            True,
            0.93,
            0.86,
            context,
            "Cu foil is the standard low-potential collector for graphite, silicon, LTO, and lithium-metal anode work.",
        )

    if base_metal == "Al":
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "not_anode_collector_for",
            False,
            0.18,
            0.84,
            context,
            "Al foil is reserved for positive-electrode collector service; negative electrodes conventionally use Cu.",
            veto=True,
        )

    if base_metal in {"SS", "Steel", "Fe"}:
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "nonstandard_anode_collector_for",
            None,
            None,
            0.45,
            context,
            "Steel/stainless anode collector service is application-specific and should be source-backed.",
            required_context=("source_evidence",),
        )

    return _battery_metal_morphism(
        metal_name,
        electrode_name,
        "nonstandard_anode_collector_for",
        None,
        None,
        0.40,
        context,
        "Anode collector role requires source-backed metal-specific evidence.",
        required_context=("source_evidence",),
    )


def _battery_tab_morphism(
    metal_name: str,
    electrode_name: str,
    base_metal: str,
    context: Dict[str, Any],
) -> TypedCompatibilityMorphism:
    if base_metal == "Ni":
        return _battery_metal_morphism(
            metal_name,
            electrode_name,
            "tab_connector_for",
            True,
            0.78,
            0.76,
            context,
            "Ni tab hardware should be evaluated as a connector, not as a full current-collector foil.",
        )

    return _battery_metal_morphism(
        metal_name,
        electrode_name,
        "tab_connector_for",
        None,
        None,
        0.45,
        context,
        "Tab compatibility depends on weld stack, plating, and package details.",
        required_context=("interface_type",),
    )


def _battery_metal_morphism(
    metal_name: str,
    electrode_name: str,
    relation: str,
    compatible: Optional[bool],
    score: Optional[float],
    confidence: float,
    context: Dict[str, Any],
    reason: str,
    required_context: Tuple[str, ...] = (),
    veto: bool = False,
) -> TypedCompatibilityMorphism:
    return TypedCompatibilityMorphism(
        source=metal_name,
        target=electrode_name,
        domain="battery-metal",
        relation=relation,
        compatible=compatible,
        score=score,
        confidence=confidence,
        context=context,
        required_context=required_context,
        reasons=(reason,),
        evidence_type="typed_role_rule",
        veto=veto,
    )


def _infer_ceramic_morphism(
    material_a: str,
    material_b: str,
    context: CompatibilityContext,
) -> Optional[TypedCompatibilityMorphism]:
    try:
        from ceramic_bridge.material_properties import get_ceramic
    except ImportError:
        return None

    if get_ceramic(material_a) is None or get_ceramic(material_b) is None:
        return None

    pair = frozenset({material_a, material_b})
    morphism_context = context.to_dict()

    oxide_sulfide_pairs = {
        frozenset({"LLZO", "Li3PS4"}),
        frozenset({"NASICON", "Li3PS4"}),
        frozenset({"LLZO", "LGPS"}),
        frozenset({"NASICON", "LGPS"}),
    }
    if pair in oxide_sulfide_pairs:
        return _generic_morphism(
            material_a,
            material_b,
            "ceramic",
            "not_direct_solid_electrolyte_interface_with",
            False,
            0.18,
            0.90,
            morphism_context,
            "Oxide/sulfide solid-electrolyte interfaces commonly form high-impedance chemically mismatched contacts without engineered interlayers.",
            evidence_type="typed_interface_rule",
            veto=True,
        )

    if pair == frozenset({"PZT", "Al2O3"}):
        return _generic_morphism(
            material_a,
            material_b,
            "ceramic",
            "piezoelectric_ceramic_substrate_with",
            True,
            0.72,
            0.78,
            morphism_context,
            "PZT ceramics are commonly integrated with alumina substrates and packages under controlled processing.",
            evidence_type="typed_interface_rule",
        )

    if pair == frozenset({"AlN", "TiN"}):
        return _generic_morphism(
            material_a,
            material_b,
            "ceramic",
            "nitride_ceramic_composite_with",
            True,
            0.84,
            0.80,
            morphism_context,
            "AlN and TiN are compatible refractory nitride materials in coating, thermal-management, and hard-interface assemblies.",
            evidence_type="typed_interface_rule",
        )

    return None


def _infer_semiconductor_morphism(
    material_a: str,
    material_b: str,
    context: CompatibilityContext,
) -> Optional[TypedCompatibilityMorphism]:
    try:
        from semiconductor_bridge.material_properties import get_semiconductor
    except ImportError:
        return None

    if get_semiconductor(material_a) is None or get_semiconductor(material_b) is None:
        return None

    pair = frozenset({material_a, material_b})
    morphism_context = context.to_dict()
    if pair in {
        frozenset({"GaN", "SiC_4H"}),
        frozenset({"GaN", "SiC_6H"}),
        frozenset({"AlN", "SiC_4H"}),
        frozenset({"AlN", "SiC_6H"}),
    }:
        return _generic_morphism(
            material_a,
            material_b,
            "semiconductor",
            "wide_bandgap_epitaxy_with",
            True,
            0.76,
            0.86,
            morphism_context,
            "Nitride-on-SiC wide-bandgap heterostructures are standard RF/power semiconductor platforms when grown with suitable buffers/process control.",
            evidence_type="typed_epitaxy_rule",
        )

    return None


def _infer_glass_morphism(
    material_a: str,
    material_b: str,
    context: CompatibilityContext,
) -> Optional[TypedCompatibilityMorphism]:
    try:
        from glass_bridge.material_properties import get_glass
    except ImportError:
        return None

    if get_glass(material_a) is None or get_glass(material_b) is None:
        return None

    pair = frozenset({material_a, material_b})
    morphism_context = context.to_dict()
    environment = (context.environment or "").strip().lower()
    interface_type = (context.interface_type or "").strip().lower()
    furnace_or_seal = environment == "furnace" or "seal" in interface_type

    if pair == frozenset({"BK7", "FusedSilica"}) and not furnace_or_seal:
        return _generic_morphism(
            material_a,
            material_b,
            "glass",
            "optical_glass_assembly_with",
            True,
            0.70,
            0.78,
            morphism_context,
            "BK7 and fused silica are standard optical materials for controlled optical-contact or cemented assemblies; this does not imply high-temperature fusion-seal compatibility.",
            evidence_type="typed_optical_assembly_rule",
            required_context=() if interface_type else ("interface_type",),
        )

    return None


def _generic_morphism(
    source: str,
    target: str,
    domain: str,
    relation: str,
    compatible: Optional[bool],
    score: Optional[float],
    confidence: float,
    context: Dict[str, Any],
    reason: str,
    required_context: Tuple[str, ...] = (),
    evidence_type: str = "typed_rule",
    veto: bool = False,
) -> TypedCompatibilityMorphism:
    return TypedCompatibilityMorphism(
        source=source,
        target=target,
        domain=domain,
        relation=relation,
        compatible=compatible,
        score=score,
        confidence=confidence,
        context=context,
        required_context=required_context,
        reasons=(reason,),
        evidence_type=evidence_type,
        veto=veto,
    )


def _base_metal(metal_name: str) -> str:
    name = metal_name.replace("_foil", "").replace("_tab", "")
    if name.startswith("SS_"):
        return "SS"
    if name.startswith("Steel_"):
        return "Steel"
    return name
