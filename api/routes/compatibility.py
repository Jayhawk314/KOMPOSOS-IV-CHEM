"""Two-material compatibility endpoint + ZFC verification."""

from fastapi import APIRouter, HTTPException

from api.models import (
    CompatibilityRequest, CompatibilityResponse,
    ZFCVerifyRequest, ZFCVerifyResponse,
)
from cross_bridge.multi_domain import _build_domain_registry

router = APIRouter(prefix="/api/v1", tags=["compatibility"])

# Build once at import time
_REGISTRY = _build_domain_registry()

# Domain -> validate_interface function (lazy loaded)
_VALIDATORS = {}


def _get_validator(domain: str):
    """Lazily import the validate_interface function for a domain."""
    if domain not in _VALIDATORS:
        import importlib

        mod = importlib.import_module(f"{domain}_bridge")
        _VALIDATORS[domain] = mod.validate_interface
    return _VALIDATORS[domain]


@router.post("/compatibility", response_model=CompatibilityResponse)
def check_compatibility(req: CompatibilityRequest):
    """Check compatibility between two materials.

    Auto-detects which bridge to use based on the materials' domains.
    Both materials must belong to the same domain.
    """
    domain_a = _REGISTRY.get(req.material_a)
    domain_b = _REGISTRY.get(req.material_b)

    if domain_a is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown material: '{req.material_a}'",
        )
    if domain_b is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown material: '{req.material_b}'",
        )
    if domain_a != domain_b:
        raise HTTPException(
            status_code=400,
            detail=f"Materials are in different domains ({domain_a} vs {domain_b}). "
            f"Use /api/v1/multi-domain for cross-domain queries.",
        )

    from oracle.compatibility_context import CompatibilityContext
    from oracle.compatibility_ensemble import build_compatibility_ensemble
    from oracle.typed_morphisms import apply_typed_morphism_adjustment, infer_typed_morphism

    context = CompatibilityContext(
        role=req.role,
        electrolyte=req.electrolyte,
        voltage_context=req.voltage_context,
        coating=req.coating,
        processing_route=req.processing_route,
        compatibilizer=req.compatibilizer,
        interface_type=req.interface_type,
        environment=req.environment,
        temperature_C=req.temperature_C,
    )

    validate = _get_validator(domain_a)
    result = validate(req.material_a, req.material_b)

    # --- Molecular Dynamics Integration (Phase 14) ---
    from oracle.md_integration import MDIntegrator
    md_integrator = MDIntegrator()
    
    md_results = None
    # Confidence can be estimated from scores or returned by validator
    # Most validators don't return confidence yet, so we look at score spread
    # Heuristic confidence: 0.8 if extreme, 0.4 if borderline
    heuristic_conf = 0.8
    if 0.4 < result.total < 0.6:
        heuristic_conf = 0.4

    if req.md_verify or md_integrator.should_verify(result.total, heuristic_conf, domain_a):
        md_run = md_integrator.run_verification(
            req.material_a, req.material_b, domain_a, req.md_conditions
        )
        constraint_scores = md_run.constraint_scores()
        fusion = md_run.fuse_with_categorical(
            result.total,
            result.viable,
            cat_confidence=heuristic_conf,
        )
        md_results = {
            'verdict': md_run.verdict,
            'measured_md': md_run.measured_md,
            'viable': md_run.viable,
            'score': md_run.score,
            'confidence': md_run.confidence,
            'detail': md_run.detail,
            'energy_diff': md_run.potential_energy_diff,
            'diffusion': md_run.diffusion_coefficient,
            'constraint_scores': constraint_scores,
            'fusion': fusion,
            'metadata': md_run.simulation_metadata
        }
        if fusion.get("used"):
            result.viable = bool(fusion["fused_viable"])
        elif md_run.confidence > 0.8:
            result.viable = md_run.viable

    scores = result.to_dict()
    scores["context"] = context.to_dict()
    morphism = infer_typed_morphism(req.material_a, req.material_b, domain_a, context)
    if morphism is not None:
        scores["typed_morphism"] = morphism.to_dict()
    morphism_adjustment = apply_typed_morphism_adjustment(
        scores.get("total", result.total),
        result.viable,
        req.material_a,
        req.material_b,
        domain_a,
        context,
    )
    if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
        scores["typed_morphism_adjustment"] = morphism_adjustment.to_dict()
        scores["total"] = morphism_adjustment.score
        scores["viable"] = morphism_adjustment.predicted_compatible
        result.viable = morphism_adjustment.predicted_compatible
    try:
        from oracle.compatibility_calibration import load_default_calibration
        scores["calibration"] = load_default_calibration().calibrate(scores.get("total", 0.0), domain_a)
    except Exception as exc:
        scores["calibration"] = {
            "raw_score": scores.get("total"),
            "calibrated_probability": scores.get("total"),
            "calibrator": "unavailable",
            "note": str(exc),
        }
    scores["ensemble"] = build_compatibility_ensemble(
        req.material_a,
        req.material_b,
        domain_a,
        scores.get("total", 0.0),
        result.viable,
        context,
        md_results=md_results,
    ).to_dict()

    return CompatibilityResponse(
        material_a=req.material_a,
        material_b=req.material_b,
        domain=domain_a,
        scores=scores,
        viable=result.viable,
        md_results=md_results,
    )


@router.post("/zfc-verify", response_model=ZFCVerifyResponse)
def zfc_verify(req: ZFCVerifyRequest):
    """Run ZFC constraint verification on a material pair.

    Converts bridge scorer results into ZFC logical constraints and
    checks for vetoes and viability assertions.
    """
    from oracle.material_zfc_constraints import MaterialZFCBridge, ZFC_LOGIC_AVAILABLE

    if not ZFC_LOGIC_AVAILABLE:
        return ZFCVerifyResponse(
            material_a=req.material_a,
            material_b=req.material_b,
            available=False,
            num_constraints=0,
            constraints=[],
            has_vetoes=False,
        )

    # Find domain and run scorer
    domain_a = _REGISTRY.get(req.material_a)
    domain_b = _REGISTRY.get(req.material_b)

    if domain_a is None:
        raise HTTPException(status_code=404, detail=f"Unknown material: '{req.material_a}'")
    if domain_b is None:
        raise HTTPException(status_code=404, detail=f"Unknown material: '{req.material_b}'")

    # Get scorer results via the bridge's score_all
    import importlib
    bridge_mod = importlib.import_module(f"{domain_a}_bridge")
    if not hasattr(bridge_mod, 'score_all'):
        raise HTTPException(
            status_code=400,
            detail=f"Domain '{domain_a}' does not support score_all",
        )

    mat_a = bridge_mod.get_material(req.material_a)
    mat_b = bridge_mod.get_material(req.material_b)
    if mat_a is None or mat_b is None:
        raise HTTPException(status_code=404, detail="Material not found")

    scores = bridge_mod.score_all(mat_a, mat_b)

    zfc_bridge = MaterialZFCBridge()
    constraints = zfc_bridge.score_constraints(req.material_a, req.material_b, scores)

    has_vetoes = any(
        c.source_prediction.get("relation", "").endswith("_veto")
        for c in constraints
    )
    viable = any(
        c.source_prediction.get("relation") == "interface_viable"
        for c in constraints
    )

    return ZFCVerifyResponse(
        material_a=req.material_a,
        material_b=req.material_b,
        available=True,
        num_constraints=len(constraints),
        constraints=[
            {
                "relation": c.source_prediction.get("relation", ""),
                "confidence": round(c.confidence, 4),
                "strategy": c.strategy,
            }
            for c in constraints
        ],
        has_vetoes=has_vetoes,
        interface_viable=viable if not has_vetoes else False,
    )
