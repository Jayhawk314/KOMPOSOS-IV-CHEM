"""Shared compatibility reasoning workflow for API and UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from cross_bridge.multi_domain import _build_domain_registry
from oracle.compatibility_calibration import load_default_calibration
from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_ensemble import build_compatibility_ensemble
from oracle.md_integration import MDIntegrator
from oracle.typed_morphisms import (
    apply_typed_morphism_adjustment,
    infer_typed_morphism,
)

_REGISTRY = _build_domain_registry()
_VALIDATORS: Dict[str, Any] = {}


@dataclass
class CompatibilityWorkflowResult:
    material_a: str
    material_b: str
    domain: str
    scores: Dict[str, Any]
    viable: bool
    md_results: Optional[Dict[str, Any]] = None


def run_compatibility_workflow(
    material_a: str,
    material_b: str,
    *,
    role: Optional[str] = None,
    electrolyte: Optional[str] = None,
    voltage_context: Optional[str] = None,
    coating: Optional[str] = None,
    processing_route: Optional[str] = None,
    compatibilizer: Optional[str] = None,
    interface_type: Optional[str] = None,
    environment: Optional[str] = None,
    temperature_C: Optional[float] = None,
    md_verify: bool = False,
    md_conditions: Optional[Dict[str, Any]] = None,
) -> CompatibilityWorkflowResult:
    """Run the full compatibility reasoning workflow for one material pair."""
    domain = resolve_same_domain(material_a, material_b)
    context = CompatibilityContext(
        role=role,
        electrolyte=electrolyte,
        voltage_context=voltage_context,
        coating=coating,
        processing_route=processing_route,
        compatibilizer=compatibilizer,
        interface_type=interface_type,
        environment=environment,
        temperature_C=temperature_C,
    )

    validate = _get_validator(domain)
    result = validate(material_a, material_b)

    md_results = _run_md_verification(
        material_a,
        material_b,
        domain,
        result.total,
        result.viable,
        md_verify=md_verify,
        md_conditions=md_conditions,
    )
    if md_results is not None:
        fusion = md_results.get("fusion", {})
        if fusion.get("used"):
            result.viable = bool(fusion["fused_viable"])
        elif md_results.get("confidence", 0.0) > 0.8:
            result.viable = bool(md_results.get("viable", result.viable))

    scores = result.to_dict()
    scores["context"] = context.to_dict()

    morphism = infer_typed_morphism(material_a, material_b, domain, context)
    if morphism is not None:
        scores["typed_morphism"] = morphism.to_dict()

    morphism_adjustment = apply_typed_morphism_adjustment(
        scores.get("total", result.total),
        result.viable,
        material_a,
        material_b,
        domain,
        context,
    )
    if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
        scores["typed_morphism_adjustment"] = morphism_adjustment.to_dict()
        scores["total"] = morphism_adjustment.score
        scores["viable"] = morphism_adjustment.predicted_compatible
        result.viable = morphism_adjustment.predicted_compatible

    try:
        scores["calibration"] = load_default_calibration().calibrate(
            scores.get("total", 0.0), domain
        )
    except Exception as exc:
        scores["calibration"] = {
            "raw_score": scores.get("total"),
            "calibrated_probability": scores.get("total"),
            "calibrator": "unavailable",
            "note": str(exc),
        }

    zfc_summary = run_zfc_summary(material_a, material_b, domain)
    scores["zfc"] = zfc_summary

    scores["ensemble"] = build_compatibility_ensemble(
        material_a,
        material_b,
        domain,
        scores.get("total", 0.0),
        result.viable,
        context,
        md_results=md_results,
    ).to_dict()

    return CompatibilityWorkflowResult(
        material_a=material_a,
        material_b=material_b,
        domain=domain,
        scores=scores,
        viable=result.viable,
        md_results=md_results,
    )


def resolve_same_domain(material_a: str, material_b: str) -> str:
    """Return the shared domain for a material pair or raise ValueError."""
    domain_a = _REGISTRY.get(material_a)
    domain_b = _REGISTRY.get(material_b)

    if domain_a is None:
        raise ValueError(f"Unknown material: '{material_a}'")
    if domain_b is None:
        raise ValueError(f"Unknown material: '{material_b}'")
    if domain_a != domain_b:
        raise ValueError(
            f"Materials are in different domains ({domain_a} vs {domain_b}). "
            "Use multi-domain analysis for cross-domain queries."
        )
    return domain_a


def run_zfc_summary(material_a: str, material_b: str, domain: str) -> Dict[str, Any]:
    """Run real ZFC constraint scoring for a compatibility pair."""
    from oracle.material_zfc_constraints import MaterialZFCBridge, ZFC_LOGIC_AVAILABLE

    if not ZFC_LOGIC_AVAILABLE:
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
        }

    import importlib

    bridge_mod = importlib.import_module(f"{domain}_bridge")
    if not hasattr(bridge_mod, "score_all"):
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
            "note": f"Domain '{domain}' does not support score_all",
        }

    mat_a = _get_bridge_material(bridge_mod, domain, material_a)
    mat_b = _get_bridge_material(bridge_mod, domain, material_b)
    if mat_a is None or mat_b is None:
        raise ValueError("Material not found")

    raw_scores = bridge_mod.score_all(mat_a, mat_b)
    constraints = MaterialZFCBridge().score_constraints(material_a, material_b, raw_scores)

    serial_constraints = []
    compatible = []
    vetoes = []
    for constraint in constraints:
        relation = constraint.source_prediction.get("relation", "")
        serial_constraints.append(
            {
                "relation": relation,
                "confidence": round(constraint.confidence, 4),
                "strategy": constraint.strategy,
            }
        )
        if relation.endswith("_veto"):
            vetoes.append(relation)
        else:
            compatible.append(relation)

    has_vetoes = bool(vetoes)
    interface_viable = (
        any(c["relation"] == "interface_viable" for c in serial_constraints)
        if not has_vetoes
        else False
    )
    return {
        "available": True,
        "num_constraints": len(serial_constraints),
        "constraints": serial_constraints,
        "has_vetoes": has_vetoes,
        "interface_viable": interface_viable,
        "compatible_constraints": compatible,
        "veto_constraints": vetoes,
    }



def _get_bridge_material(bridge_mod: Any, domain: str, name: str) -> Any:
    getter_names = {
        "battery": "get_material",
        "polymer": "get_polymer",
        "metal": "get_metal",
        "ceramic": "get_ceramic",
        "semiconductor": "get_semiconductor",
        "glass": "get_glass",
    }
    getter_name = getter_names.get(domain)
    if getter_name and hasattr(bridge_mod, getter_name):
        return getattr(bridge_mod, getter_name)(name)

    material_dict_names = {
        "battery": "ALL_MATERIALS",
        "polymer": "ALL_POLYMERS",
        "metal": "ALL_METALS",
        "ceramic": "ALL_CERAMICS",
        "semiconductor": "ALL_SEMICONDUCTORS",
        "glass": "ALL_GLASSES",
    }
    dict_name = material_dict_names.get(domain)
    if dict_name and hasattr(bridge_mod, dict_name):
        return getattr(bridge_mod, dict_name).get(name)
    return None
def _get_validator(domain: str):
    if domain not in _VALIDATORS:
        import importlib

        mod = importlib.import_module(f"{domain}_bridge")
        _VALIDATORS[domain] = mod.validate_interface
    return _VALIDATORS[domain]


def _run_md_verification(
    material_a: str,
    material_b: str,
    domain: str,
    total_score: float,
    viable: bool,
    *,
    md_verify: bool,
    md_conditions: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    md_integrator = MDIntegrator()
    heuristic_conf = 0.4 if 0.4 < total_score < 0.6 else 0.8
    if not (md_verify or md_integrator.should_verify(total_score, heuristic_conf, domain)):
        return None

    md_run = md_integrator.run_verification(
        material_a,
        material_b,
        domain,
        md_conditions,
    )
    return {
        "verdict": md_run.verdict,
        "measured_md": md_run.measured_md,
        "viable": md_run.viable,
        "score": md_run.score,
        "confidence": md_run.confidence,
        "detail": md_run.detail,
        "energy_diff": md_run.potential_energy_diff,
        "diffusion": md_run.diffusion_coefficient,
        "constraint_scores": md_run.constraint_scores(),
        "fusion": md_run.fuse_with_categorical(
            total_score,
            viable,
            cat_confidence=heuristic_conf,
        ),
        "metadata": md_run.simulation_metadata,
    }


