# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Two-material compatibility endpoint + ZFC verification."""

from fastapi import APIRouter, HTTPException

from api.models import (
    CompatibilityRequest, CompatibilityResponse,
    ZFCVerifyRequest, ZFCVerifyResponse,
)
from oracle.compatibility_service import (
    resolve_same_domain,
    run_compatibility_workflow,
    run_zfc_summary,
)

router = APIRouter(prefix="/api/v1", tags=["compatibility"])


@router.post("/compatibility", response_model=CompatibilityResponse)
def check_compatibility(req: CompatibilityRequest):
    """Check compatibility between two materials.

    Auto-detects which bridge to use based on the materials' domains.
    Both materials must belong to the same domain.
    """
    try:
        domain = resolve_same_domain(req.material_a, req.material_b)
        workflow = run_compatibility_workflow(
            req.material_a,
            req.material_b,
            domain=domain,
            role=req.role,
            electrolyte=req.electrolyte,
            voltage_context=req.voltage_context,
            coating=req.coating,
            processing_route=req.processing_route,
            compatibilizer=req.compatibilizer,
            interface_type=req.interface_type,
            environment=req.environment,
            temperature_C=req.temperature_C,
            md_verify=req.md_verify,
            md_conditions=req.md_conditions,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("Unknown material:"):
            raise HTTPException(status_code=404, detail=detail)
        if "different domains" in detail:
            raise HTTPException(
                status_code=400,
                detail=f"{detail} Use /api/v1/multi-domain for cross-domain queries.",
            )
        raise HTTPException(status_code=400, detail=detail)

    return CompatibilityResponse(
        material_a=workflow.material_a,
        material_b=workflow.material_b,
        domain=workflow.domain,
        scores=workflow.scores,
        viable=workflow.viable,
        md_results=workflow.md_results,
    )


@router.post("/zfc-verify", response_model=ZFCVerifyResponse)
def zfc_verify(req: ZFCVerifyRequest):
    """Run ZFC constraint verification on a material pair."""
    try:
        domain = resolve_same_domain(req.material_a, req.material_b)
        summary = run_zfc_summary(req.material_a, req.material_b, domain)
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("Unknown material:"):
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)

    return ZFCVerifyResponse(
        material_a=req.material_a,
        material_b=req.material_b,
        available=summary["available"],
        num_constraints=summary["num_constraints"],
        constraints=summary["constraints"],
        has_vetoes=summary["has_vetoes"],
        interface_viable=summary["interface_viable"],
    )
