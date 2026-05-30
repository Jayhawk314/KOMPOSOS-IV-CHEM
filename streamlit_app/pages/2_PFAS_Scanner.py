"""PFAS Compliance Scanner - screen materials and find replacements."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

st.set_page_config(page_title="PFAS Scanner", page_icon="🛡️", layout="wide")
st.title("PFAS Compliance Scanner")
st.markdown(
    "Check materials against PFAS regulations (EU REACH, US EPA, Stockholm Convention) "
    "and find drop-in replacements scored for your specific application."
)

# ---------------------------------------------------------------------------
# Imports (cached)
# ---------------------------------------------------------------------------

from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge.pfas_registry import (
    PFAS_REGISTRY,
    PFASCategory,
    get_pfas_by_category,
    get_epa_registry,
)
from pfas_bridge.replacement_scorer import UseCase, find_replacements
from reports.pfas_report import PFASComplianceReport, MaterialInput, LI_ION_DEMO_BOM
from reports.pfas_pdf import generate_pfas_pdf
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.validation_status import render_feature_status
from streamlit_app.utils.material_library import get_all_material_names, get_materials_by_domain

render_feature_status("pfas")
render_login_sidebar()


URGENCY_COLORS = {
    "critical": "🔴",
    "high": "🟠",
    "moderate": "🟡",
    "low": "🔵",
    "none": "🟢",
}

USE_CASE_OPTIONS = {
    "General": None,
    "Battery Binder": "battery_binder",
    "Seal / Gasket": "seal_gasket",
    "Membrane": "membrane",
    "Wire Insulation": "wire_insulation",
    "Non-Stick Coating": "non_stick_coating",
    "Chemical-Resistant Liner": "chemical_resistant_liner",
}

# ---------------------------------------------------------------------------
# Tab 1: Single Material Check
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(["Single Check", "Batch Scan", "Compliance Report", "PFAS Registry"])

with tab1:
    st.subheader("Check a Single Material")

    # Aggregate material names for autofill
    all_known_materials = get_all_material_names()
    material_options = ["Other..."] + all_known_materials

    col1, col2 = st.columns(2)
    with col1:
        material_choice = st.selectbox(
            "Material name",
            options=material_options,
            index=material_options.index("PVDF") if "PVDF" in material_options else 0,
            help="Select a known material or choose 'Other...' to type a custom name.",
        )
        if material_choice == "Other...":
            material_name = st.text_input("Enter custom material name", value="")
        else:
            material_name = material_choice
            
    with col2:
        use_case_label = st.selectbox("Application context", list(USE_CASE_OPTIONS.keys()))

    adjoining_material = st.text_input(
        "Adjoining material (optional compatibility check)",
        value="",
        help="Enter a material to check compatibility with replacements (e.g., LiPF6 if checking a binder).",
    )

    if st.button("Check PFAS Status", type="primary", key="single_check"):
        if not require_access():
            st.stop()
        consume_use()

        checker = PFASComplianceChecker()
        use_case = USE_CASE_OPTIONS[use_case_label]
        result = checker.check(material_name, use_case=use_case, adjoining_material=adjoining_material)
        d = result.to_dict()

        # Status banner
        icon = URGENCY_COLORS.get(d.get("urgency", "none"), "")
        if d["is_pfas"]:
            st.error(f"{icon} **{material_name}** is a PFAS substance - urgency: **{d.get('urgency', 'unknown')}**")
        else:
            st.success(f"{icon} **{material_name}** is **not** a PFAS substance")

        # Details
        col_info, col_regs = st.columns(2)
        with col_info:
            st.markdown("**Details**")
            if d.get("pfas_category"):
                st.write(f"- Category: {d['pfas_category']}")
            if d.get("cas_number"):
                st.write(f"- CAS: {d['cas_number']}")
            st.write(f"- Urgency: {d.get('urgency', 'none')}")

        with col_regs:
            st.markdown("**Regulatory Status**")
            regs = d.get("regulations_violated", [])
            if regs:
                for reg in regs:
                    st.write(f"- {reg}")
            else:
                st.write("- No regulations violated")
            if d.get("heuristic_match"):
                st.info("Detected via heuristic pattern matching (not in registry)")

        # Replacements
        replacements = d.get("replacements", [])
        if replacements:
            st.subheader(f"Replacement Alternatives ({len(replacements)} found)")
            import pandas as pd
            rows = []
            
            # Map compatibility results by material name
            comp_map = {res["material_a"]: res for res in d.get("compatibility_results", [])}
            
            for r in replacements:
                name = r.get("name", r.get("replacement", "?"))
                # Match "CMC+SBR" to "CMC" compatibility check
                bridge_name = name.split("+")[0] if "+" in name else name
                comp = comp_map.get(bridge_name)
                
                rows.append({
                    "Replacement": name,
                    "Compatibility": comp.get("total") if comp else (None if adjoining_material else "N/A"),
                    "Score": r.get("overall_score", r.get("score", 0)),
                    "Performance": r.get("performance_match", 0),
                    "Processability": r.get("processability", 0),
                    "Cost Factor": r.get("cost_factor", 0),
                    "Availability": r.get("availability", 0),
                })
            df = pd.DataFrame(rows).sort_values("Score", ascending=False)
            
            # If compatibility is checked, sort by a composite
            if adjoining_material:
                df["Rank"] = 0.6 * df["Score"] + 0.4 * df["Compatibility"].fillna(0.5)
                df = df.sort_values("Rank", ascending=False).drop(columns=["Rank"])

            st.dataframe(
                df.style.format({
                    "Compatibility": "{:.2f}" if adjoining_material else "{}",
                    "Score": "{:.2f}",
                    "Performance": "{:.2f}",
                    "Processability": "{:.2f}",
                    "Cost Factor": "{:.2f}",
                    "Availability": "{:.2f}",
                }).background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=1)
                .background_gradient(subset=["Compatibility"], cmap="RdYlGn", vmin=0, vmax=1) if adjoining_material else df.style,
                use_container_width=True,
                hide_index=True,
            )
            st.caption("Evidence Levels: 'Literature Backed' (high confidence) | 'Cross-Bridge Analysis' (physics-interpolated) | 'Heuristic Prediction' (rules of thumb)")

        # Warnings
        warnings = d.get("warnings", [])
        if warnings:
            for w in warnings:
                st.warning(w)

        with st.expander("Raw data"):
            st.json(d)

# ---------------------------------------------------------------------------
# Tab 2: Batch Scan
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Batch PFAS Scan")
    st.markdown(
        "Enter material names (one per line) to scan an entire BOM. "
        "Accepts exact names (PVDF), commercial brands (Kynar), or any text."
    )

    # Quick-Fill Section
    with st.expander("Batch Quick-Fill (Browse Materials)", expanded=False):
        def _on_quick_fill(domain_key):
            selected = st.session_state[domain_key]
            if not selected:
                return
            current = st.session_state.get("batch_input_text", "")
            added = ""
            for m in selected:
                if m not in current:
                    added += f"{m}\n"
            st.session_state["batch_input_text"] = current + added
            # Clear multiselect after adding
            st.session_state[domain_key] = []

        domains = get_materials_by_domain()
        cols = st.columns(len(domains))
        for i, (domain, mats) in enumerate(domains.items()):
            with cols[i]:
                st.markdown(f"**{domain}**")
                st.multiselect(
                    f"Select {domain}",
                    options=mats,
                    key=f"qf_{domain}",
                    on_change=_on_quick_fill,
                    args=(f"qf_{domain}",),
                    label_visibility="collapsed"
                )

    materials_text = st.text_area(
        "Materials (one per line)",
        value="PVDF\nKynar PVDF 741\nPTFE\nTeflon tape\nPEO\nNafion\nCMC\nSBR\nPEEK\nMystery Binder X",
        height=200,
        key="batch_input_text"
    )

    if st.button("Scan All", type="primary", key="batch_scan"):
        if not require_access():
            st.stop()
        consume_use()

        names = [n.strip() for n in materials_text.strip().split("\n") if n.strip()]
        if not names:
            st.warning("Enter at least one material name.")
        else:
            checker = PFASComplianceChecker()
            batch = checker.check_batch(names)
            bd = batch.to_dict()

            # Summary with detection tiers
            pfas_count = bd.get("pfas_count", 0)
            total = len(names)
            mats = bd.get("materials", [])
            n_exact = sum(1 for m in mats if m.get("detection_tier") == "exact" and m.get("is_pfas"))
            n_heuristic = sum(1 for m in mats if m.get("detection_tier") == "heuristic")
            n_unknown = sum(1 for m in mats if m.get("detection_tier") == "unknown")

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Scanned", total)
            col_s2.metric("PFAS Found", pfas_count)
            col_s3.metric("Max Urgency", bd.get("max_urgency", "none"))
            col_s4.metric("Manual Review", n_unknown)

            if pfas_count > 0:
                st.error(f"Found {pfas_count} PFAS substance(s) in your BOM!")
            else:
                st.success("No PFAS substances detected.")

            if n_heuristic > 0:
                st.info(f"{n_heuristic} material(s) detected via brand/keyword matching.")
            if n_unknown > 0:
                st.warning(f"{n_unknown} material(s) not recognized -- manual review required.")

            # Per-material results with detection tier
            import pandas as pd
            rows = []
            for m in mats:
                icon = URGENCY_COLORS.get(m.get("urgency", "none"), "")
                tier = m.get("detection_tier", "unknown")
                tier_label = {"exact": "Exact", "heuristic": "Brand/Keyword", "unknown": "Unknown"}.get(tier, tier)
                resolved = m.get("resolved_base", "")
                rows.append({
                    "Material": m.get("material_name", "?"),
                    "PFAS": "Yes" if m.get("is_pfas") else "No",
                    "Detection": tier_label,
                    "Resolved As": resolved if resolved else "-",
                    "Urgency": f"{icon} {m.get('urgency', 'none')}",
                    "Category": m.get("pfas_category") or "-",
                    "Replacements": len(m.get("replacements", [])),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tab 3: Compliance Report Generator
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("PFAS Compliance Report Generator")
    st.markdown(
        "Generate a structured, auditable compliance report for enterprise buyers. "
        "Includes PFAS detections, scored replacements with provenance, regulatory "
        "timeline with days-remaining, and a prioritized action plan."
    )

    client_name = st.text_input(
        "Client / Company Name",
        value="",
        placeholder="e.g. Acme Battery Corp",
        key="client_name",
    )

    report_mode = st.radio(
        "Report input",
        ["Demo: Li-Ion Cell BOM (15 materials)", "Custom materials list"],
        horizontal=True,
        key="report_mode",
    )

    custom_materials = []
    if report_mode.startswith("Custom"):
        st.markdown("Enter materials (one per line, format: `name | function | quantity_kg`)")
        custom_text = st.text_area(
            "Materials",
            value="PVDF | cathode binder | 50\nPTFE | gasket seal | 10\nNMC811 | cathode | 200\nCu foil | collector | 80",
            height=150,
            key="custom_report_materials",
        )
        for line in custom_text.strip().split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if parts and parts[0]:
                name = parts[0]
                func = parts[1] if len(parts) > 1 else None
                qty = float(parts[2]) if len(parts) > 2 and parts[2] else None
                custom_materials.append(MaterialInput(name=name, function=func, quantity_kg=qty))

    if st.button("Generate Compliance Report", type="primary", key="gen_report"):
        if not require_access():
            st.stop()
        consume_use()

        with st.spinner("Screening portfolio and building report..."):
            gen = PFASComplianceReport()
            if report_mode.startswith("Demo"):
                materials = LI_ION_DEMO_BOM
            else:
                materials = custom_materials

            if not materials:
                st.warning("Enter at least one material.")
            else:
                report = gen.screen_portfolio(materials, client_name=client_name)

                # Report header
                st.success(f"Report **{report.report_id}** generated successfully")

                # PDF download button
                pdf_bytes = generate_pfas_pdf(report)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"{report.report_id}.pdf",
                    mime="application/pdf",
                    type="primary",
                )

                # Summary metrics
                import pandas as pd
                s = report.summary
                cols = st.columns(4)
                cols[0].metric("Screened", s["screened"])
                cols[1].metric("PFAS Found", s["detected"])
                cols[2].metric("Clean", s["clean"])
                cols[3].metric("Risk Level", s["risk_level"])

                # Detections
                if report.detections:
                    st.subheader(f"PFAS Detections ({len(report.detections)})")
                    for det in report.detections:
                        with st.expander(
                            f"{URGENCY_COLORS.get(det.urgency, '')} **{det.material}** "
                            f"({det.pfas_substance}) - Urgency: {det.urgency}"
                        ):
                            st.write(f"- Function: {det.function or 'N/A'}")
                            st.write(f"- Category: {det.pfas_category}")
                            regulations = ", ".join(
                                f"{r['jurisdiction']} ({r['status']})"
                                for r in det.regulations
                            )
                            st.write(f"- Regulations: {regulations}")

                            if det.replacements:
                                st.markdown("**Scored Replacements:**")
                                rows = []
                                for r in det.replacements:
                                    rows.append({
                                        "Replacement": r.name,
                                        "Evidence Level": r.evidence_tier,
                                        "Score": r.overall_score,
                                        "Verdict": r.verdict,
                                        "Provenance": len(r.provenance),
                                    })
                                df = pd.DataFrame(rows)
                                st.dataframe(
                                    df.style.format({"Score": "{:.2f}"}).background_gradient(
                                        subset=["Score"], cmap="RdYlGn", vmin=0, vmax=1
                                    ),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                                st.caption("Evidence: 'Literature Backed' (experimental) | 'Cross-Bridge' (physics) | 'Heuristic' (rules)")

                # Regulatory timeline
                if report.regulatory_timeline:
                    st.subheader("Regulatory Timeline")
                    tl_rows = []
                    for t in report.regulatory_timeline:
                        status_icon = URGENCY_COLORS.get(
                            "critical" if (t.days_remaining is not None and t.days_remaining < 0) else
                            "high" if (t.days_remaining is not None and t.days_remaining < 180) else
                            "moderate", ""
                        )
                        tl_rows.append({
                            "": status_icon,
                            "Jurisdiction": t.jurisdiction,
                            "Regulation": t.regulation,
                            "Effective": t.effective_date or "TBD",
                            "Days Remaining": t.days_remaining if t.days_remaining is not None else "N/A",
                        })
                    st.dataframe(pd.DataFrame(tl_rows), use_container_width=True, hide_index=True)

                # Action plan
                if report.action_plan:
                    st.subheader("Action Plan")
                    for a in report.action_plan:
                        prio_icon = {1: "1.", 2: "2.", 3: "3."}.get(a.priority, f"{a.priority}.")
                        st.markdown(
                            f"**{prio_icon}** {a.task} "
                            f"(deadline: {a.deadline_days} days, "
                            f"materials: {', '.join(a.materials_affected)})"
                        )
                        st.caption(a.rationale)

                # Audit certificate
                with st.expander("Audit Certificate"):
                    st.json(report.audit_certificate)

                # Full raw data
                with st.expander("Full Report Data (JSON)"):
                    st.json(report.to_dict())

# ---------------------------------------------------------------------------
# Tab 4: PFAS Registry
# ---------------------------------------------------------------------------

with tab4:
    st.subheader("PFAS Substance Registry")
    
    reg_tab1, reg_tab2 = st.tabs(["Curated Registry (Top 35)", "EPA Structural Dataset (10,776)"])
    
    with reg_tab1:
        st.markdown(f"**{len(PFAS_REGISTRY)}** PFAS substances across **{len(PFASCategory)}** categories.")

        for cat in PFASCategory:
            if cat == PFASCategory.EPA_STRUCTURAL:
                continue
            substances = get_pfas_by_category(cat)
            if not substances:
                continue
            with st.expander(f"{cat.value.replace('_', ' ').title()} ({len(substances)} substances)"):
                import pandas as pd
                rows = []
                for name, pfas in sorted(substances.items()):
                    banned = "BANNED" if pfas.is_banned() else ""
                    restricted = "RESTRICTED" if pfas.is_restricted() else ""
                    status = banned or restricted or "Under review"
                    rows.append({
                        "Name": pfas.name,
                        "CAS": pfas.cas_number or "-",
                        "Formula": pfas.formula or "-",
                        "Status": status,
                    })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with reg_tab2:
        st.markdown(
            "The **EPA PFASSTRUCT v4** dataset contains 10,776 substances identified by the US EPA "
            "as matching their structural definition of PFAS. This list is used by the scanner "
            "to provide 'Structural Match' validation for novel or non-standard substances."
        )
        epa_data = get_epa_registry()
        if epa_data:
            import pandas as pd
            df_epa = pd.DataFrame(epa_data)
            st.dataframe(
                df_epa.rename(columns={"smiles": "Structure (SMILES)", "id": "DTXSID", "fw": "Mol Weight"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("EPA Dataset (data/EPA_PFASSTRUCTV4.txt) not found or empty.")
