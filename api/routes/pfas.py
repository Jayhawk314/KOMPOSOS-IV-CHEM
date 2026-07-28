# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""PFAS compliance API endpoints."""

from fastapi import APIRouter, HTTPException

from api.models import (
    PFASAlternativesRequest,
    PFASAlternativesResponse,
    PFASCheckRequest,
    PFASCheckResponse,
    PFASSubstanceListResponse,
)
from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge.pfas_registry import (
    PFASCategory,
    get_pfas_by_category,
)
from pfas_bridge.replacement_scorer import UseCase

router = APIRouter(prefix="/api/v1", tags=["pfas"])

_checker = PFASComplianceChecker()


@router.post("/pfas-check", response_model=PFASCheckResponse)
def check_pfas(req: PFASCheckRequest):
    """Check a single material for PFAS compliance.

    Returns PFAS status, urgency level, applicable regulations,
    and suggested PFAS-free alternatives.
    """
    result = _checker.check(req.material_name)

    alternatives = [r.name for r in result.replacements[:5]]
    warnings = []
    if result.heuristic_match:
        warnings.append(
            f"'{req.material_name}' detected as potential PFAS by heuristic "
            "(not in curated registry). Verify manually."
        )
    if result.urgency == "critical":
        warnings.append("This substance is BANNED. Immediate action required.")
    elif result.urgency == "high":
        warnings.append("Ban/restriction takes effect within 12 months.")

    return PFASCheckResponse(
        material_name=req.material_name,
        is_pfas=result.is_pfas,
        pfas_category=result.pfas_category,
        restricted_eu=any(
            v["jurisdiction"] == "EU" for v in result.regulations_violated
        ),
        restricted_us=any(
            v["jurisdiction"] == "US" for v in result.regulations_violated
        ),
        restriction_date=(
            result.pfas_substance.restriction_date().isoformat()
            if result.pfas_substance and result.pfas_substance.restriction_date()
            else None
        ),
        alternatives=alternatives,
        warnings=warnings,
    )


@router.get("/pfas-substances", response_model=PFASSubstanceListResponse)
def list_pfas_substances():
    """List all PFAS substances grouped by category."""
    categories = {}
    total = 0
    for cat in PFASCategory:
        members = get_pfas_by_category(cat)
        if members:
            categories[cat.value] = sorted(members.keys())
            total += len(members)

    return PFASSubstanceListResponse(
        total=total,
        categories=categories,
    )


@router.post("/pfas-alternatives", response_model=PFASAlternativesResponse)
def suggest_pfas_alternatives(req: PFASAlternativesRequest):
    """Suggest PFAS-free replacement candidates for a given substance.

    Optionally specify a use case (battery_binder, seal_gasket, membrane,
    wire_insulation, non_stick_coating, chemical_resistant_liner, general)
    for more targeted suggestions.
    """
    # Parse use case
    try:
        use_case = UseCase(req.use_case) if req.use_case else UseCase.GENERAL
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown use_case '{req.use_case}'. Valid: "
                   f"{[uc.value for uc in UseCase]}",
        )

    alternatives = _checker.suggest_alternatives(req.material_name, use_case)

    return PFASAlternativesResponse(
        material_name=req.material_name,
        use_case=use_case.value,
        num_alternatives=len(alternatives),
        alternatives=[a.to_dict() for a in alternatives],
    )
