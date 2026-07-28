# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""API route for inverse composition design."""

from fastapi import APIRouter, HTTPException

from api.models import (
    DesignRequest,
    DesignResponse,
    DesignCandidateOutput,
)

router = APIRouter(prefix="/api/v1", tags=["designer"])


# Known properties that the predictor can produce
_VALID_PROPERTIES = {
    "voltage", "theoretical_capacity", "thermal_stability",
    "ionic_conductivity", "density", "volume_expansion",
    "formation_energy", "synthesizability",
    "band_gap", "electron_mobility", "lattice_constant",
    "melting_point", "thermal_conductivity", "hardness",
    "fracture_toughness", "cte", "youngs_modulus",
    "molar_mass", "avg_electronegativity",
}


@router.post("/design-composition", response_model=DesignResponse)
def design_composition(req: DesignRequest):
    """Inverse design: find compositions matching target properties.

    Searches composition space using 4 strategies (perturbation,
    interpolation, substitution, stoichiometry variation) and scores
    candidates against the target spec using the forward predictor.
    """
    # Validate property names
    for target in req.targets:
        if target.name not in _VALID_PROPERTIES:
            suggestions = sorted(_VALID_PROPERTIES)
            raise HTTPException(
                status_code=400,
                detail=f"Unknown property '{target.name}'. "
                       f"Valid properties: {suggestions}",
            )

    from composition_engine.designer import (
        CompositionDesigner,
        DesignSpec,
        PropertyTarget,
        ElementConstraint,
    )

    # Convert Pydantic models to dataclasses
    targets = [
        PropertyTarget(
            name=t.name,
            min_value=t.min_value,
            max_value=t.max_value,
            weight=t.weight,
        )
        for t in req.targets
    ]

    element_constraints = None
    if req.element_constraints is not None:
        element_constraints = ElementConstraint(
            required_elements=req.element_constraints.required_elements,
            excluded_elements=req.element_constraints.excluded_elements,
            max_elements=req.element_constraints.max_elements,
        )

    spec = DesignSpec(
        targets=targets,
        element_constraints=element_constraints,
        min_synthesizability=req.min_synthesizability,
        require_stable=req.require_stable,
        pfas_free=req.pfas_free,
        domain=req.domain,
        max_candidates=req.max_candidates,
    )

    try:
        designer = CompositionDesigner()
        result = designer.design(spec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return DesignResponse(
        num_candidates=len(result.candidates),
        num_evaluated=result.num_evaluated,
        elapsed_seconds=round(result.elapsed_seconds, 3),
        strategies_used=result.strategies_used,
        candidates=[
            DesignCandidateOutput(**c.to_dict())
            for c in result.candidates
        ],
    )
