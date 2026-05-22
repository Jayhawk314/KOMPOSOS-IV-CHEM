"""API routes for compositional property prediction."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter(prefix="/api/v1", tags=["prediction"])


# ── Request/Response models ─────────────────────────────────────────────────

class PredictRequest(BaseModel):
    """Predict properties from a chemical formula."""
    formula: str = Field(
        ..., description="Chemical formula or shorthand (e.g. 'NMC721', 'LiNi0.7Mn0.2Co0.1O2')"
    )

class PredictResponse(BaseModel):
    """Predicted properties with confidence and bounds."""
    formula: str
    composition: Dict[str, float]
    properties: Dict[str, Dict[str, Any]]
    nearest_known: List[Dict[str, Any]]
    method: str

class InterpolateRequest(BaseModel):
    """Interpolate between two compositions."""
    formula_a: str = Field(..., description="First endpoint formula")
    formula_b: str = Field(..., description="Second endpoint formula")
    fraction: float = Field(
        0.5, ge=0.0, le=1.0,
        description="Interpolation fraction (0=formula_a, 1=formula_b)"
    )


# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/predict-composition", response_model=PredictResponse)
def predict_composition(req: PredictRequest):
    """Predict material properties from chemical formula using Kan extension + D-S fusion."""
    from composition_engine.predictor import CompositionPredictor

    predictor = CompositionPredictor()
    try:
        result = predictor.predict(req.formula)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PredictResponse(**result.to_dict())


@router.post("/interpolate", response_model=PredictResponse)
def interpolate(req: InterpolateRequest):
    """Predict properties at an interpolated composition between two formulas."""
    from composition_engine.predictor import CompositionPredictor

    predictor = CompositionPredictor()
    try:
        result = predictor.interpolate(req.formula_a, req.formula_b, req.fraction)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PredictResponse(**result.to_dict())
