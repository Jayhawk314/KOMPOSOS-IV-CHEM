"""Multi-domain analysis endpoint."""

from fastapi import APIRouter

from api.models import MultiDomainRequest, MultiDomainResponse
from cross_bridge.multi_domain import (
    MultiDomainAnalyzer,
    MultiDomainComponent,
    MultiDomainQuery,
)

router = APIRouter(prefix="/api/v1", tags=["multi-domain"])


@router.post("/multi-domain", response_model=MultiDomainResponse)
def analyze_multi_domain(req: MultiDomainRequest):
    """Analyze a multi-domain material combination.

    Spans battery, polymer, metal, ceramic, semiconductor, and glass bridges.
    Auto-detects domains and applies the appropriate cross-domain functors.
    """
    components = [
        MultiDomainComponent(name=c.name, role=c.role)
        for c in req.components
    ]

    query = MultiDomainQuery(
        name=req.name,
        components=components,
        electrolyte=req.electrolyte,
        viability_threshold=req.viability_threshold,
    )

    analyzer = MultiDomainAnalyzer(viability_threshold=req.viability_threshold)
    result = analyzer.analyze(query)
    d = result.to_dict()

    return MultiDomainResponse(**d)
