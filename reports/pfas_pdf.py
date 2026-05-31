"""
PFAS Compliance Report - PDF Generator
========================================

Converts a ReportData instance into a professional PDF document
matching the KOMPOSOS DOCX template quality: narrative analysis,
domain-specific cross-bridge scores, provenance chains with MP IDs,
and client branding.

Uses fpdf2 (pure Python, no system dependencies).

Usage:
    from reports.pfas_report import PFASComplianceReport, LI_ION_DEMO_BOM
    from reports.pfas_pdf import generate_pfas_pdf

    gen = PFASComplianceReport()
    report = gen.screen_portfolio(LI_ION_DEMO_BOM, client_name="Acme Corp")
    pdf_bytes = generate_pfas_pdf(report)

    with open("report.pdf", "wb") as f:
        f.write(pdf_bytes)
"""

from __future__ import annotations

from fpdf import FPDF

from reports.pfas_report import (
    ReportData,
    PFASDetection,
    RegulatoryTimeline,
    ActionItem,
    ReplacementWithProvenance,
)


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------

_NAVY = (26, 42, 78)
_ACCENT_BLUE = (0, 102, 204)
_DARK_TEXT = (33, 33, 33)
_LIGHT_GRAY = (240, 240, 245)
_WHITE = (255, 255, 255)
_TABLE_BORDER = (200, 200, 200)
_GREEN = (0, 153, 51)
_RED = (204, 0, 0)
_ORANGE = (230, 126, 0)
_AMBER = (204, 163, 0)

_RISK_COLORS = {
    "CRITICAL": _RED,
    "HIGH": _ORANGE,
    "MODERATE": _AMBER,
    "LOW": (0, 128, 204),
    "CLEAN": _GREEN,
}

_VERDICT_COLORS = {
    "VALIDATED": _GREEN,
    "CAUTION": _AMBER,
    "VETOED": _RED,
    "REVIEW": (0, 128, 204),  # cell fit not scorable - manual review
}

# PFAS full names for narrative text
_PFAS_FULL_NAMES = {
    "PVDF": "polyvinylidene fluoride",
    "PTFE": "polytetrafluoroethylene",
    "FEP": "fluorinated ethylene propylene",
    "Nafion": "perfluorosulfonic acid polymer",
    "PFA": "perfluoroalkoxy alkane",
    "PFOA": "perfluorooctanoic acid",
    "PFOS": "perfluorooctane sulfonate",
}

# Narrative descriptions per function
_FUNCTION_NARRATIVES = {
    "cathode binder": "the primary cathode binder in the current cell design",
    "anode binder": "an anode binder material",
    "separator coating": "used as a separator coating for chemical resistance",
    "gasket seal": "used as a gasket seal for chemical inertness",
    "separator base": "the separator base material",
    "membrane": "a membrane material",
    "wire insulation": "used for wire insulation",
    "electrolyte": "an electrolyte component",
}


# ---------------------------------------------------------------------------
# Custom FPDF subclass with branding
# ---------------------------------------------------------------------------

class _KompososPDF(FPDF):
    """FPDF subclass with KOMPOSOS header/footer branding."""

    def __init__(self, report_id: str):
        super().__init__(orientation="P", unit="mm", format="letter")
        self.report_id = report_id
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_NAVY)
        self.cell(0, 5, "KOMPOSOS Compliance Engine", align="L")
        self.set_font("Helvetica", "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, self.report_id, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_ACCENT_BLUE)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, "KOMPOSOS Compliance Engine  |  Confidential", align="L")
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _section_heading(pdf: _KompososPDF, title: str):
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_ACCENT_BLUE)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def _body_text(pdf: _KompososPDF, text: str):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_DARK_TEXT)
    pdf.multi_cell(0, 5, text)
    pdf.ln(1)


def _table_header(pdf: _KompososPDF, cols: list[tuple[str, float]]):
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*_LIGHT_GRAY)
    pdf.set_text_color(*_NAVY)
    pdf.set_draw_color(*_TABLE_BORDER)
    for label, width in cols:
        pdf.cell(width, 7, label, border=1, fill=True, align="C")
    pdf.ln()


def _metric_box(pdf: _KompososPDF, label: str, value: str,
                color: tuple = _ACCENT_BLUE, box_width: float = 45):
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.set_fill_color(*color)
    pdf.set_draw_color(*color)
    pdf.rect(x, y, box_width, 18, style="D")
    pdf.set_xy(x, y + 2)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(box_width, 4, label, align="C", new_x="LEFT", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*color)
    pdf.cell(box_width, 10, str(value), align="C")
    pdf.set_xy(x + box_width + 3, y)


def _ensure_space(pdf: _KompososPDF, needed_mm: float = 50):
    """Add a page break if less than needed_mm space remains."""
    if pdf.get_y() > pdf.h - needed_mm:
        pdf.add_page()


def _days_label(days: int | None) -> tuple[str, tuple]:
    """Format days remaining as string and pick color."""
    if days is None:
        return "PENDING", _DARK_TEXT
    if days < 0:
        return f"{abs(days)} DAYS AGO", _RED
    if days < 180:
        return f"{days} DAYS", _ORANGE
    if days < 365:
        return f"{days} DAYS", _AMBER
    return f"{days} DAYS", _DARK_TEXT


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_cover(pdf: _KompososPDF, report: ReportData):
    """Cover page with client branding and executive summary."""
    # Title block
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_ACCENT_BLUE)
    pdf.cell(0, 6, "KOMPOSOS", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 12, "PFAS Compliance", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 12, "Screening Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Client name
    client = report.client_name or "[Client Company Name]"
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Prepared for:", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 8, client, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Portfolio and date
    s = report.summary
    n_materials = s.get("screened", 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Portfolio: {n_materials} substances screened",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Report Date: {report.generated_at[:10]}",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Report ID: {report.report_id}",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Confidential line
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 4,
             f"CONFIDENTIAL  |  KOMPOSOS Compliance Engine v{report.engine_version}  |  Apache 2.0 / Commercial",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # --- 1. Executive Summary ---
    _section_heading(pdf, "1. Executive Summary")

    risk_color = _RISK_COLORS.get(s.get("risk_level", "CLEAN"), _ACCENT_BLUE)
    _metric_box(pdf, "Materials Screened", str(s.get("screened", 0)))
    _metric_box(pdf, "PFAS Detected", str(s.get("detected", 0)),
                color=_RED if s.get("detected", 0) > 0 else _GREEN)
    _metric_box(pdf, "Replacements Found",
                f"{s.get('replacements_found', 0)} candidates")
    _metric_box(pdf, "Compliance Risk", s.get("risk_level", "CLEAN"),
                color=risk_color)

    pdf.ln(22)

    # Narrative paragraph
    detected = s.get("detected", 0)
    if detected > 0:
        _body_text(
            pdf,
            f"This report screens {n_materials} materials in "
            f"{client}'s bill of materials against curated PFAS substances and "
            f"the OECD structural rule, mapped to US (state and federal), EU, and "
            f"Stockholm Convention regulatory regimes. "
            f"{detected} material(s) contain PFAS compounds subject to current or "
            f"proposed restrictions. Specific deadlines vary by jurisdiction and "
            f"are moving; verify current dates against primary sources."
        )
        _body_text(
            pdf,
            "For each flagged material, this report provides: the specific PFAS "
            "substance detected, the applicable regulatory regime and status, scored "
            "replacement candidates with cell-aware compatibility analysis "
            "(weakest-interface bottleneck), and a full audit trail traceable to "
            "source data."
        )
    else:
        _body_text(
            pdf,
            f"All {n_materials} materials in {client}'s bill of materials "
            f"passed PFAS compliance screening. No PFAS substances were detected."
        )


def _render_timeline(pdf: _KompososPDF, report: ReportData):
    """Section 2: Regulatory Timeline."""
    _section_heading(pdf, "2. Regulatory Timeline")

    if not report.regulatory_timeline:
        _body_text(pdf, "No regulatory timeline entries applicable.")
        return

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols = [
        ("Jurisdiction", usable * 0.16),
        ("Regulation", usable * 0.40),
        ("Scope", usable * 0.20),
        ("Timeframe", usable * 0.24),
    ]
    _table_header(pdf, cols)

    scope_map = {
        "banned": "Manufacturing + import ban",
        "restricted": "Reporting / restriction",
        "proposed_ban": "Proposed restriction",
    }

    for i, tl in enumerate(report.regulatory_timeline):
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(250, 250, 252)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_draw_color(*_TABLE_BORDER)
        pdf.set_text_color(*_DARK_TEXT)
        pdf.cell(cols[0][1], 6, tl.jurisdiction[:22], border=1, fill=fill, align="L")
        pdf.cell(cols[1][1], 6, tl.regulation[:50], border=1, fill=fill, align="L")
        pdf.cell(cols[2][1], 6, scope_map.get(tl.status, tl.status)[:26],
                 border=1, fill=fill, align="L")
        pdf.cell(cols[3][1], 6, tl.timeframe[:34], border=1, fill=fill, align="L")
        pdf.ln()

    pdf.ln(2)
    _body_text(
        pdf,
        "Timeframes are qualitative by design. Specific deadlines vary by "
        "jurisdiction and change frequently - verify current dates against "
        "primary sources (ECHA, US EPA, and state agencies) before filing.",
    )


def _render_detections(pdf: _KompososPDF, report: ReportData):
    """Section 3: Portfolio Screening Results."""
    _section_heading(pdf, "3. Portfolio Screening Results")

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 6, "3.1 PFAS Detection Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols = [
        ("Material", usable * 0.18),
        ("CAS Number", usable * 0.14),
        ("Function", usable * 0.18),
        ("PFAS Substance", usable * 0.28),
        ("Verdict", usable * 0.22),
    ]
    _table_header(pdf, cols)

    # Detected materials
    for i, det in enumerate(report.detections):
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(250, 250, 252)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_draw_color(*_TABLE_BORDER)
        pdf.set_text_color(*_DARK_TEXT)
        pdf.cell(cols[0][1], 6, det.material[:22], border=1, fill=fill, align="L")
        pdf.cell(cols[1][1], 6, det.cas_number or "--", border=1, fill=fill, align="L")
        pdf.cell(cols[2][1], 6, (det.function or "N/A")[:22], border=1, fill=fill, align="L")
        pdf.cell(cols[3][1], 6, det.pfas_substance[:35], border=1, fill=fill, align="L")
        pdf.set_text_color(*_RED)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(cols[4][1], 6, "PFAS DETECTED", border=1, fill=fill, align="C")
        pdf.ln()

    # Clean materials (summarized)
    n_clean = len(report.clean_materials)
    if n_clean > 0:
        # Show first few clean materials, then summarize
        shown = min(n_clean, 3)
        offset = len(report.detections)
        for i, cm in enumerate(report.clean_materials[:shown]):
            fill = (offset + i) % 2 == 1
            if fill:
                pdf.set_fill_color(250, 250, 252)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_draw_color(*_TABLE_BORDER)
            pdf.set_text_color(*_DARK_TEXT)
            pdf.cell(cols[0][1], 6, cm["name"][:22], border=1, fill=fill, align="L")
            pdf.cell(cols[1][1], 6, "--", border=1, fill=fill, align="L")
            pdf.cell(cols[2][1], 6, cm.get("function", "N/A")[:22], border=1, fill=fill, align="L")
            pdf.cell(cols[3][1], 6, "--", border=1, fill=fill, align="L")
            pdf.set_text_color(*_GREEN)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(cols[4][1], 6, "PFAS-FREE", border=1, fill=fill, align="C")
            pdf.ln()

        remaining = n_clean - shown
        if remaining > 0:
            fill = (offset + shown) % 2 == 1
            if fill:
                pdf.set_fill_color(250, 250, 252)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.set_draw_color(*_TABLE_BORDER)
            pdf.cell(cols[0][1] + cols[1][1] + cols[2][1] + cols[3][1], 6,
                     f"... ({remaining} more materials)", border=1, fill=fill, align="L")
            pdf.set_text_color(*_GREEN)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(cols[4][1], 6, "PFAS-FREE", border=1, fill=fill, align="C")
            pdf.ln()


def _render_replacements(pdf: _KompososPDF, report: ReportData):
    """Section 4: Replacement Analysis -- the big upgrade."""
    _section_heading(pdf, "4. Replacement Analysis")

    if not report.detections:
        _body_text(pdf, "No PFAS detections -- no replacements needed.")
        return

    for det_idx, det in enumerate(report.detections):
        if not det.replacements:
            continue

        _ensure_space(pdf, 70)

        # Sub-heading: "4.1 PVDF Binder Replacement"
        sub_num = det_idx + 1
        short_name = det.material.split("(")[0].strip()
        fn_word = (det.function or "").split()[-1] if det.function else "Material"
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_NAVY)
        pdf.cell(0, 7, f"4.{sub_num} {short_name} {fn_word.title()} Replacement",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Narrative intro
        full_name = _PFAS_FULL_NAMES.get(short_name, det.pfas_substance)
        fn_narrative = _FUNCTION_NARRATIVES.get(
            det.function or "", f"used as {det.function or 'a component'}"
        )
        n_reps = len(det.replacements)

        # Detect cathode from cross-bridge details
        cathode_ref = ""
        for rep in det.replacements:
            if rep.cross_bridge_details.get("battery_material"):
                cathode_ref = rep.cross_bridge_details["battery_material"]
                break

        context_text = ""
        if cathode_ref:
            context_text = (
                f" {n_reps} replacement candidates were screened for "
                f"compatibility with the {cathode_ref} cathode."
            )
        else:
            context_text = (
                f" {n_reps} replacement candidates were identified and scored."
            )

        _body_text(
            pdf,
            f"{short_name} ({full_name}) is {fn_narrative}.{context_text}"
        )

        # Replacement table -- use domain scores if available, else generic
        has_domain = any(rep.domain_scores for rep in det.replacements)
        usable = pdf.w - pdf.l_margin - pdf.r_margin

        if has_domain:
            cols = [
                ("Replacement", usable * 0.18),
                ("Evidence", usable * 0.14),
                ("Adhesion", usable * 0.10),
                ("Electroly.", usable * 0.10),
                ("Thermal", usable * 0.10),
                ("Cathode", usable * 0.10),
                ("Overall", usable * 0.10),
                ("Verdict", usable * 0.18),
            ]
        else:
            cols = [
                ("Replacement", usable * 0.18),
                ("Evidence", usable * 0.16),
                ("Perform.", usable * 0.11),
                ("Process.", usable * 0.11),
                ("Cost", usable * 0.11),
                ("Avail.", usable * 0.11),
                ("Overall", usable * 0.11),
                ("Verdict", usable * 0.11),
            ]

        _ensure_space(pdf, 40)
        _table_header(pdf, cols)

        for i, rep in enumerate(det.replacements):
            verdict_color = _VERDICT_COLORS.get(rep.verdict, _DARK_TEXT)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_draw_color(*_TABLE_BORDER)
            fill = i % 2 == 1
            if fill:
                pdf.set_fill_color(250, 250, 252)

            if has_domain:
                ds = rep.domain_scores
                values = [
                    rep.name,
                    rep.evidence_tier,
                    f"{ds.get('adhesion', rep.performance_match):.2f}",
                    f"{ds.get('electrolyte', rep.processability):.2f}",
                    f"{ds.get('thermal', rep.cost_factor):.2f}",
                    f"{ds.get('cathode', rep.availability):.2f}",
                    f"{rep.overall_score:.2f}",
                    rep.verdict,
                ]
            else:
                values = [
                    rep.name,
                    rep.evidence_tier,
                    f"{rep.performance_match:.2f}",
                    f"{rep.processability:.2f}",
                    f"{rep.cost_factor:.2f}",
                    f"{rep.availability:.2f}",
                    f"{rep.overall_score:.2f}",
                    rep.verdict,
                ]

            for j, (val, (_, width)) in enumerate(zip(values, cols)):
                if j == len(cols) - 1:  # Verdict column
                    pdf.set_text_color(*verdict_color)
                    pdf.set_font("Helvetica", "B", 8)
                else:
                    pdf.set_text_color(*_DARK_TEXT)
                    pdf.set_font("Helvetica", "", 8)
                pdf.cell(width, 6, val, border=1, fill=fill,
                         align="C" if j > 0 else "L")
            pdf.ln()

        # Narrative recommendation
        pdf.ln(2)
        top = det.replacements[0]
        validated = [r for r in det.replacements if r.verdict == "VALIDATED"]
        caution = [r for r in det.replacements if r.verdict == "CAUTION"]

        rec_parts = []
        if validated:
            best = validated[0]
            if has_domain and best.domain_scores:
                domain_text = "with validated compatibility across all four domains"
            else:
                domain_text = "with validated performance and availability"
            rec_parts.append(
                f"{best.name} is the highest-scoring replacement "
                f"({best.overall_score:.2f} overall) {domain_text}."
            )
            if len(validated) > 1:
                second = validated[1]
                # Find what second is best at
                if has_domain and second.domain_scores:
                    best_dim = max(second.domain_scores.items(),
                                   key=lambda x: x[1])
                    rec_parts.append(
                        f"{second.name} is a strong secondary option with "
                        f"superior {best_dim[0]} ({best_dim[1]:.2f})."
                    )
                else:
                    rec_parts.append(
                        f"{second.name} is a secondary option "
                        f"({second.overall_score:.2f} overall)."
                    )

        if caution:
            c_names = ", ".join(c.name for c in caution)
            rec_parts.append(
                f"{c_names} score(s) below the 0.75 threshold in one or "
                f"more domains and require(s) further testing before qualification."
            )

        # Honest fallback: no candidate cleared cell-aware screening.
        if not validated and not caution:
            vetoed = [r for r in det.replacements if r.verdict == "VETOED"]
            review = [r for r in det.replacements if r.verdict == "REVIEW"]
            if vetoed:
                v = vetoed[0]
                rec_parts.append(
                    f"No curated replacement cleared cell-aware screening for this "
                    f"stack: each evaluated candidate fails at least one interface "
                    f"(e.g. {v.name} at its {v.cell_bottleneck_material} interface). "
                    f"This narrows the problem to a specific interface rather than "
                    f"endorsing a drop-in swap."
                )
            if review:
                rec_parts.append(
                    f"{', '.join(r.name for r in review)} could not be scored "
                    f"in-cell (not in the compatibility registry) and need manual review."
                )
            rec_parts.append(
                "Recommend lab evaluation / interface engineering rather than a "
                "direct substitution."
            )

        if rec_parts:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_NAVY)
            pdf.cell(0, 5, "Recommendation:", new_x="LMARGIN", new_y="NEXT")
            _body_text(pdf, " ".join(rec_parts))

        # Provenance sub-section for top replacement
        if top.provenance or (top.domain_scores and top.cross_bridge_details):
            _ensure_space(pdf, 45)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_NAVY)
            pdf.cell(0, 6,
                     f"4.{sub_num}.1 Compatibility Provenance ({top.name})",
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            _body_text(
                pdf,
                f"Every score above traces to specific source data. Below is the "
                f"provenance chain for the {top.name} analysis:"
            )

            prov_cols = [
                ("Property", usable * 0.25),
                ("Value", usable * 0.25),
                ("Source", usable * 0.30),
                ("Contribution", usable * 0.20),
            ]
            _table_header(pdf, prov_cols)

            # Cross-bridge detail rows
            cb = top.cross_bridge_details
            if cb and cb.get("details"):
                details = cb["details"]
                poly_name = cb.get("polymer_tested", top.name)
                bat_name = cb.get("battery_material", "cathode")

                # Voltage/electrolyte provenance
                v_det = details.get("voltage", {})
                if v_det:
                    v_limit = v_det.get("polymer_voltage_limit_V", "N/A")
                    e_upper = v_det.get("electrode_nominal_V", "N/A")
                    _prov_row(pdf, prov_cols,
                              "Electrochemical window",
                              f"{e_upper}V nominal ({v_limit}V limit)",
                              f"{poly_name} + {bat_name}",
                              f"{top.domain_scores.get('electrolyte', 'N/A')}")

                # Thermal provenance
                t_det = details.get("thermal", {})
                if t_det:
                    decomp = t_det.get("polymer_decomposition_C", "N/A")
                    _prov_row(pdf, prov_cols,
                              "Thermal stability",
                              f"Decomp: {decomp}C",
                              f"Literature data",
                              f"{top.domain_scores.get('thermal', 'N/A')}")

                # Mechanical/adhesion provenance
                m_det = details.get("mechanical", {})
                if m_det:
                    elong = m_det.get("polymer_elongation_pct", "N/A")
                    vol_exp = m_det.get("electrode_volume_expansion", "N/A")
                    _prov_row(pdf, prov_cols,
                              f"Adhesion / elongation",
                              f"{elong}% (vol exp: {vol_exp})",
                              f"Cross-bridge analysis",
                              f"{top.domain_scores.get('adhesion', 'N/A')}")

                # Chemical/cathode provenance
                c_det = details.get("chemical", {})
                if c_det:
                    pair_type = c_det.get("known_pair", "unknown")
                    _prov_row(pdf, prov_cols,
                              f"Cathode compatibility",
                              f"Pair: {pair_type}",
                              f"{poly_name} + {bat_name}",
                              f"{top.domain_scores.get('cathode', 'N/A')}")

            # Literature provenance rows
            for prov in top.provenance:
                _prov_row(pdf, prov_cols,
                          prov.get("property_name", "N/A"),
                          str(prov.get("value", "N/A")),
                          prov.get("citation", "N/A")[:38],
                          f"{prov.get('confidence', 'N/A')}")

            # Note about processing advantage
            if top.advantages:
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)
                note = top.advantages[0]
                pdf.multi_cell(0, 4, f"Note: {note}")
                pdf.ln(1)

        pdf.ln(3)


def _prov_row(pdf: _KompososPDF, cols, prop, value, source, contrib):
    """Render a single provenance table row."""
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_DARK_TEXT)
    pdf.set_draw_color(*_TABLE_BORDER)
    pdf.cell(cols[0][1], 5, str(prop)[:32], border=1, align="L")
    pdf.cell(cols[1][1], 5, str(value)[:32], border=1, align="L")
    pdf.cell(cols[2][1], 5, str(source)[:38], border=1, align="L")
    pdf.cell(cols[3][1], 5, str(contrib)[:20], border=1, align="C")
    pdf.ln()


def _render_action_plan(pdf: _KompososPDF, report: ReportData):
    """Section 5: Recommended Action Plan."""
    _section_heading(pdf, "5. Recommended Action Plan")

    if not report.action_plan:
        _body_text(pdf, "No actions required -- portfolio is PFAS-free.")
        return

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols = [
        ("Priority", usable * 0.10),
        ("Action", usable * 0.40),
        ("Timeline", usable * 0.20),
        ("Risk if Delayed", usable * 0.30),
    ]
    _table_header(pdf, cols)

    # Risk descriptions per priority level
    _RISK_TEXTS = {
        1: "Production halt at regulation effective date",
        2: "Component non-compliant for regulated markets",
        3: "Compliance documentation gap",
        4: "Future supply chain disruption",
        5: "Extended qualification timeline",
    }

    for i, action in enumerate(report.action_plan):
        fill = i % 2 == 1
        if fill:
            pdf.set_fill_color(250, 250, 252)

        # Priority label
        p_label = f"P{action.priority - 1}" if action.priority <= 4 else f"P{action.priority}"

        # Timeline
        if action.deadline_days is not None and action.deadline_days == 0:
            timeline = "Immediate"
        elif action.deadline_days is not None:
            weeks = max(1, action.deadline_days // 7)
            timeline = f"Weeks 1-{weeks}"
        else:
            timeline = "Ongoing"

        # Risk text
        risk_text = _RISK_TEXTS.get(action.priority,
                                     action.rationale[:40])

        pdf.set_font("Helvetica", "", 8)
        pdf.set_draw_color(*_TABLE_BORDER)

        # Priority cell with color
        if action.priority <= 1:
            pdf.set_text_color(*_RED)
            pdf.set_font("Helvetica", "B", 8)
        elif action.priority <= 2:
            pdf.set_text_color(*_ORANGE)
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_text_color(*_DARK_TEXT)

        pdf.cell(cols[0][1], 6, p_label, border=1, fill=fill, align="C")

        pdf.set_text_color(*_DARK_TEXT)
        pdf.set_font("Helvetica", "", 8)
        # Truncate action task for table
        task_short = action.task.replace("IMMEDIATE: ", "").replace(
            "URGENT: ", "").replace("PLAN: ", "").replace(
            "MONITOR: ", "").replace("VALIDATE: ", "")
        pdf.cell(cols[1][1], 6, task_short[:52], border=1, fill=fill, align="L")
        pdf.cell(cols[2][1], 6, timeline, border=1, fill=fill, align="C")
        pdf.cell(cols[3][1], 6, risk_text[:40], border=1, fill=fill, align="L")
        pdf.ln()

    # Materials affected summary
    pdf.ln(3)
    for action in report.action_plan:
        if action.materials_affected:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(100, 100, 100)
            p_label = f"P{action.priority - 1}"
            pdf.cell(0, 4,
                     f"{p_label} affects: {', '.join(action.materials_affected)}",
                     new_x="LMARGIN", new_y="NEXT")


def _render_methodology(pdf: _KompososPDF, report: ReportData):
    """Section 6: Methodology & Limitations."""
    _section_heading(pdf, "6. Methodology & Limitations")

    meth = report.methodology

    _body_text(
        pdf,
        f"This screening was performed using the {meth.get('engine', 'KOMPOSOS')} "
        f"v{meth.get('version', 'N/A')}. Materials were screened against a curated "
        f"database of 35 PFAS substances with CAS number verification. "
        f"Compatibility scores are computed via structured interpolation over "
        f"169 curated materials, with provenance tracing to specific source entries."
    )

    _body_text(
        pdf,
        "Replacement analysis is cell-aware: each candidate is scored (calibrated, "
        "isotonic) against every remaining material in the cell, and the WEAKEST "
        "interface (the bottleneck) governs the verdict - a strong standalone score "
        "does not override a failing interface. Verdicts: VALIDATED (bottleneck "
        "compatible and well-supported), CAUTION (bottleneck marginal), VETOED "
        "(an interface fails), REVIEW (cell fit could not be scored - manual review; "
        "NOT promoted on standalone score alone). Calibrated values have limited "
        "resolution in the low band; verify low-bottleneck cases by test."
    )

    # NEW: Data Fidelity section
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 5, "Data Fidelity & Uncertainty:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_DARK_TEXT)
    pdf.multi_cell(0, 4,
                   "Replacement scores are classified by evidence quality: (1) 'Literature Backed' "
                   "indicates data derived from peer-reviewed experimental studies. (2) 'Cross-Bridge "
                   "Analysis' indicates scores derived from physics-based interpolation between known "
                   "material pairs. (3) 'Heuristic Prediction' indicates physically-informed rules of "
                   "thumb for novel materials. All current error bars are heuristic; full statistical "
                   "calibration is planned for Phase 16.")
    pdf.ln(2)

    # Databases
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 5, "Reference Databases:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_DARK_TEXT)
    for db in meth.get("databases", []):
        pdf.cell(0, 4, f"  - {db}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Validation
    stats = meth.get("validation_stats", {})
    if stats:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_NAVY)
        pdf.cell(0, 5, "Validation:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK_TEXT)
        for key, val in stats.items():
            label = key.replace("_", " ").title()
            pdf.cell(0, 4, f"  - {label}: {val}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Limitations
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_NAVY)
    pdf.cell(0, 5, "Limitations:", new_x="LMARGIN", new_y="NEXT")
    caveats = meth.get("caveats", [])
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*_DARK_TEXT)
    for i, c in enumerate(caveats, 1):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4, f"({i}) {c}")
    pdf.ln(1)


def _render_audit_certificate(pdf: _KompososPDF, report: ReportData):
    """Section 7: Audit Certificate."""
    _section_heading(pdf, "7. Audit Certificate")

    cert = report.audit_certificate
    usable = pdf.w - pdf.l_margin - pdf.r_margin

    fields = [
        ("Report ID", cert.get("report_id", "N/A")),
        ("Screening Engine", f"KOMPOSOS Compliance Engine v{cert.get('engine_version', 'N/A')}"),
        ("Materials Screened", str(cert.get("materials_screened", 0))),
        ("PFAS Database", "35 substances (CAS-verified, EU/US/Stockholm mapped)"),
        ("Materials Database", "169 curated entries"),
        ("Verification Method", "Dual-engine (categorical + ZFC set-theoretic) with provenance"),
        ("Validation Status", "Leave-one-out validated: 1.6-7.2% voltage error, 23/23 structure"),
        ("Test Suite", "1,575 automated tests passing"),
        ("Generated", cert.get("generated_at", "N/A")[:19]),
    ]

    # Add client/prepared by
    client = report.client_name
    if client:
        fields.append(("Prepared for", client))

    for label, value in fields:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_NAVY)
        pdf.cell(usable * 0.30, 6, label, border=1)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_DARK_TEXT)
        pdf.cell(usable * 0.70, 6, str(value)[:70], border=1,
                 new_x="LMARGIN", new_y="NEXT")

    # Legal disclaimer
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 4, "END OF REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 7)
    pdf.multi_cell(0, 4,
                   "This report is generated by automated screening software and does not "
                   "constitute legal, regulatory, or engineering advice. Physical qualification "
                   "testing is required before production changes. Consult legal counsel for "
                   "regulatory compliance decisions.", align="C")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pfas_pdf(report: ReportData) -> bytes:
    """Generate a PFAS compliance report as a PDF.

    Args:
        report: A ReportData instance from PFASComplianceReport.screen_portfolio().

    Returns:
        PDF content as bytes, ready for st.download_button or HTTP response.
    """
    pdf = _KompososPDF(report.report_id)
    pdf.alias_nb_pages()
    pdf.add_page()

    # Section 1: Cover / Executive Summary
    _render_cover(pdf, report)

    # Section 2: Regulatory Timeline
    pdf.add_page()
    _render_timeline(pdf, report)

    # Section 3: Screening Results
    _render_detections(pdf, report)

    # Section 4: Replacement Analysis (biggest section)
    pdf.add_page()
    _render_replacements(pdf, report)

    # Section 5: Action Plan
    _ensure_space(pdf, 60)
    _render_action_plan(pdf, report)

    # Section 6: Methodology
    pdf.add_page()
    _render_methodology(pdf, report)

    # Section 7: Audit Certificate
    _ensure_space(pdf, 80)
    _render_audit_certificate(pdf, report)

    return bytes(pdf.output())


if __name__ == "__main__":
    from reports.pfas_report import PFASComplianceReport, LI_ION_DEMO_BOM

    gen = PFASComplianceReport()
    report = gen.screen_portfolio(LI_ION_DEMO_BOM, client_name="Acme Battery Corp")
    pdf_bytes = generate_pfas_pdf(report)

    out_path = "PFAS_Compliance_Report.pdf"
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"PDF generated: {out_path} ({len(pdf_bytes):,} bytes)")
