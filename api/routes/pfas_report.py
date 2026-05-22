"""PFAS compliance report API endpoint."""

from fastapi import APIRouter

from api.models import (
    PFASReportMaterialInput,
    PFASReportRequest,
    PFASReportResponse,
)
from reports.pfas_report import (
    MaterialInput,
    PFASComplianceReport,
    LI_ION_DEMO_BOM,
)

router = APIRouter(prefix="/api/v1", tags=["pfas"])


@router.post("/pfas-report", response_model=PFASReportResponse)
def generate_pfas_report(req: PFASReportRequest):
    """Generate a structured PFAS compliance report for a materials portfolio.

    Screens each material against the PFAS registry, finds PFAS-free
    replacements with provenance, builds a regulatory timeline with
    days-remaining, and produces a prioritized action plan.

    Use ``use_demo_bom=true`` to run with the built-in 15-material
    Li-Ion cell BOM for demonstration purposes.
    """
    gen = PFASComplianceReport()

    if req.use_demo_bom:
        materials = LI_ION_DEMO_BOM
    else:
        materials = [
            MaterialInput(
                name=m.name,
                cas_number=m.cas_number,
                function=m.function,
                quantity_kg=m.quantity_kg,
            )
            for m in req.materials
        ]

    report = gen.screen_portfolio(materials)
    d = report.to_dict()

    return PFASReportResponse(
        report_id=d["report_id"],
        summary=d["summary"],
        detections=d["detections"],
        clean_materials=d["clean_materials"],
        regulatory_timeline=d["regulatory_timeline"],
        action_plan=d["action_plan"],
        methodology=d["methodology"],
        audit_certificate=d["audit_certificate"],
    )
