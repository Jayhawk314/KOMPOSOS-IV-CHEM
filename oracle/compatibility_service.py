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
    domain: Optional[str] = None,
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
    domain = domain or resolve_workflow_domain(material_a, material_b)
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
    # Most validators take (a, b) or (a, b, context)
    # We'll normalize to a standard call
    result = _call_validator(validate, material_a, material_b, domain, context)

    # Robust field extraction for total score and viability
    total_score = getattr(result, "total", getattr(result, "score", 0.0))
    is_viable = getattr(result, "viable", getattr(result, "compatible", False))

    md_results = _run_md_verification(
        material_a,
        material_b,
        domain,
        total_score,
        is_viable,
        md_verify=md_verify,
        md_conditions=md_conditions,
    )
    if md_results is not None:
        fusion = md_results.get("fusion", {})
        if fusion.get("used"):
            is_viable = bool(fusion["fused_viable"])
        elif md_results.get("confidence", 0.0) > 0.8:
            is_viable = bool(md_results.get("viable", is_viable))

    scores = _result_to_dict(result)
    scores["context"] = context.to_dict()
    scores["total"] = total_score  # Ensure standardized field
    scores["viable"] = is_viable

    morphism = infer_typed_morphism(material_a, material_b, domain, context)
    if morphism is not None:
        scores["typed_morphism"] = morphism.to_dict()

    morphism_adjustment = apply_typed_morphism_adjustment(
        total_score,
        is_viable,
        material_a,
        material_b,
        domain,
        context,
    )
    if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
        scores["typed_morphism_adjustment"] = morphism_adjustment.to_dict()
        scores["total"] = morphism_adjustment.score
        scores["viable"] = morphism_adjustment.predicted_compatible
        is_viable = morphism_adjustment.predicted_compatible

    try:
        scores["calibration"] = load_default_calibration().calibrate(
            scores.get("total", total_score), domain
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
        is_viable,
        context,
        md_results=md_results,
    ).to_dict()

    return CompatibilityWorkflowResult(
        material_a=material_a,
        material_b=material_b,
        domain=domain,
        scores=scores,
        viable=is_viable,
        md_results=md_results,
    )


def resolve_workflow_domain(material_a: str, material_b: str) -> str:
    """Resolve the domain(s) for a material pair, supporting cross-domain."""
    domain_a = _REGISTRY.get(material_a)
    domain_b = _REGISTRY.get(material_b)

    if domain_a is None:
        raise ValueError(f"Unknown material: '{material_a}'")
    if domain_b is None:
        raise ValueError(f"Unknown material: '{material_b}'")

    if domain_a == domain_b:
        return domain_a

    # Cross-domain resolution
    domains = {domain_a, domain_b}
    if "battery" in domains and "metal" in domains:
        return "battery-metal"
    if "battery" in domains and "polymer" in domains:
        return "battery-polymer"
    if "ceramic" in domains and "metal" in domains:
        return "ceramic-metal"
    if "metal" in domains and "semiconductor" in domains:
        return "metal-semiconductor"
    if "polymer" in domains and "metal" in domains:
        return "polymer-metal"
    if "ceramic" in domains and "battery" in domains:
        return "ceramic-battery"

    # Default: composite string
    return f"{domain_a}-{domain_b}"


def _get_validator(domain: str):
    if domain in _VALIDATORS:
        return _VALIDATORS[domain]

    import importlib
    if "-" in domain:
        # Cross-domain validator
        parts = domain.split("-")
        mod_name = f"cross_bridge.{parts[0]}_{parts[1]}"
        try:
            mod = importlib.import_module(mod_name)
            # Find the scorer function
            for attr in dir(mod):
                if attr.startswith("score_") and attr.endswith("_compatibility"):
                    _VALIDATORS[domain] = getattr(mod, attr)
                    return _VALIDATORS[domain]
                if attr == "score_collector_compatibility":
                    _VALIDATORS[domain] = getattr(mod, attr)
                    return _VALIDATORS[domain]
        except ImportError:
            pass

    # Fallback: try individual domain bridges
    domains_to_try = domain.split("-") if "-" in domain else [domain]
    for d in domains_to_try:
        try:
            mod = importlib.import_module(f"{d}_bridge")
            if hasattr(mod, "validate_interface"):
                _VALIDATORS[domain] = mod.validate_interface
                return _VALIDATORS[domain]
        except (ImportError, ModuleNotFoundError):
            pass

    raise ValueError(f"No validator found for domain '{domain}'")


def _call_validator(validate: Any, material_a: str, material_b: str, domain: str, context: CompatibilityContext):
    """Normalize validator call across different bridge signatures."""
    import inspect
    sig = inspect.signature(validate)

    kwargs = {}
    if "role" in sig.parameters:
        kwargs["role"] = context.role
    if "polymer_role" in sig.parameters:
        kwargs["polymer_role"] = context.role
    if "interface_role" in sig.parameters:
        kwargs["interface_role"] = context.role
    if "operating_temp_C" in sig.parameters:
        kwargs["operating_temp_C"] = context.temperature_C or 25.0

    # Some cross-domain scorers are symmetric, some are not
    # We might need to swap a/b based on expected types if they differ
    return validate(material_a, material_b, **kwargs)


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

    # Try to load single-domain bridge first
    bridge_domain = domain.split("-")[0] if "-" in domain else domain
    try:
        bridge_mod = importlib.import_module(f"{bridge_domain}_bridge")
    except (ImportError, ModuleNotFoundError):
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
            "note": f"Domain '{bridge_domain}' bridge not found",
        }

    if not hasattr(bridge_mod, "score_all"):
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
            "note": f"Domain '{bridge_domain}' does not support score_all",
        }

    mat_a = _get_bridge_material(bridge_mod, bridge_domain, material_a)
    mat_b = _get_bridge_material(bridge_mod, bridge_domain, material_b)
    if mat_a is None or mat_b is None:
        # Try swapping if cross-domain
        if "-" in domain:
            other_domain = domain.split("-")[1]
            try:
                other_mod = importlib.import_module(f"{other_domain}_bridge")
                if mat_a is None: mat_a = _get_bridge_material(other_mod, other_domain, material_a)
                if mat_b is None: mat_b = _get_bridge_material(other_mod, other_domain, material_b)
            except: pass

    if mat_a is None or mat_b is None:
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
            "note": "Material(s) not found for ZFC",
        }

    try:
        raw_scores = bridge_mod.score_all(mat_a, mat_b)
    except:
        return {
            "available": False,
            "num_constraints": 0,
            "constraints": [],
            "has_vetoes": False,
            "interface_viable": None,
            "compatible_constraints": [],
            "veto_constraints": [],
            "note": "ZFC scoring failed",
        }

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


def _result_to_dict(result: Any) -> Dict[str, Any]:
    """Robust conversion of bridge results to dictionaries."""
    if hasattr(result, "to_dict"):
        return result.to_dict()

    from dataclasses import is_dataclass, asdict
    if is_dataclass(result):
        return asdict(result)

    if isinstance(result, dict):
        return result

    # Manual extraction as fallback
    res = {}
    for attr in dir(result):
        if not attr.startswith("_"):
            val = getattr(result, attr)
            if isinstance(val, (int, float, str, bool, list, dict)) or val is None:
                res[attr] = val
    return res
