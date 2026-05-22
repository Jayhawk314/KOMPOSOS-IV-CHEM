"""Synthesis planning endpoint."""

from fastapi import APIRouter, HTTPException

from api.models import SynthesisRequest, SynthesisResponse
from synthesis_planner import SynthesisPlanner, list_all_targets

router = APIRouter(prefix="/api/v1", tags=["synthesis"])


@router.get("/synthesis/targets", response_model=list[str])
def list_targets():
    """List all target materials with synthesis routes."""
    return list_all_targets()


@router.post("/synthesis", response_model=SynthesisResponse)
def plan_synthesis(req: SynthesisRequest):
    """Plan synthesis routes for a target material.

    Returns ranked routes with feasibility, cost, time, and safety scores.
    """
    targets = list_all_targets()
    if req.target not in targets:
        raise HTTPException(
            status_code=404,
            detail=f"No synthesis routes for '{req.target}'. "
            f"Available: {', '.join(targets)}",
        )

    planner = SynthesisPlanner()
    equipment = req.available_equipment if req.available_equipment else None
    analysis = planner.plan_synthesis(req.target, available_equipment=equipment)
    d = analysis.to_dict()

    return SynthesisResponse(**d)
