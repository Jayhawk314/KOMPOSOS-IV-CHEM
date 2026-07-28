# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""PFAS screening tool - screen materials and triage replacements."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

st.set_page_config(page_title="PFAS Scanner", page_icon="🛡️", layout="wide")
st.title("PFAS Screening & Replacement Triage")
st.markdown(
    "Check materials against PFAS regulations (EU REACH, US EPA, Stockholm Convention) "
    "and find drop-in replacements scored for your specific application."
)

# ---------------------------------------------------------------------------
# Imports (cached)
# ---------------------------------------------------------------------------

from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge import (
    PFAS_REGISTRY,
    PFASCategory,
    get_pfas_by_category,
    get_epa_registry,
)
from pfas_bridge.replacement_scorer import UseCase, find_replacements, find_replacements_for_cell
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

    col1, col2 = st.columns(2)
    with col1:
        # Hierarchical Selection
        domains = get_materials_by_domain()
        domain_choice = st.selectbox(
            "Filter by Domain / Category", 
            ["All Domains"] + list(domains.keys()),
            help="Narrow down the material list by chemical domain."
        )
        
        if domain_choice == "All Domains":
            all_known = get_all_material_names()
            material_options = ["Other..."] + all_known
        else:
            material_options = ["Other..."] + domains[domain_choice]

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

    adjoining_text = st.text_area(
        "Adjoining materials in your cell (optional — one per line)",
        value="",
        height=80,
        help="List the materials each replacement would touch (e.g. LiPF6, NMC811, "
             "Graphite for a binder). Each PFAS-free replacement is scored for "
             "compatibility against ALL of them — a replacement is only as good as "
             "its weakest interface ('compatible with your cell').",
    )
    adjoining_materials = [m.strip() for m in adjoining_text.replace(",", "\n").split("\n") if m.strip()]

    if st.button("Check PFAS Status", type="primary", key="single_check"):
        if not require_access():
            st.stop()
        consume_use()

        checker = PFASComplianceChecker()
        use_case = USE_CASE_OPTIONS[use_case_label]
        result = checker.check(material_name, use_case=use_case)
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
            import pandas as pd

            if adjoining_materials:
                # Cell-aware: score each replacement against EVERY adjoining material,
                # surfacing the calibrated bottleneck ("compatible with your cell").
                st.subheader(
                    f"PFAS-free AND cell-compatible alternatives "
                    f"({len(replacements)} candidates × {len(adjoining_materials)} interfaces)"
                )
                key = d.get("replacement_key") or d.get("resolved_base") or material_name
                cell_rows = find_replacements_for_cell(key, adjoining_materials, use_case)

                rows = []
                for cr in cell_rows:
                    c = cr["candidate"]
                    bn = cr["bottleneck_calibrated"]
                    row = {
                        "Replacement": c.name,
                        "Full-stack probability": bn,
                        "Coverage": cr["coverage_fraction"],
                        "Bottleneck": cr["bottleneck_material"] or "—",
                        "Quality": c.overall_score,
                    }
                    # One calibrated-probability column per adjoining material.
                    for mat, e in cr["interfaces"].items():
                        row[f"vs {mat}"] = e["calibrated"] if e["evaluated"] else None
                    rows.append(row)

                df = pd.DataFrame(rows)
                pct_cols = ["Full-stack probability", "Coverage"] + [c for c in df.columns if c.startswith("vs ")]
                fmt = {c: (lambda v: "—" if pd.isna(v) else f"{v:.0%}") for c in pct_cols}
                fmt["Quality"] = "{:.2f}"
                st.dataframe(
                    df.style.format(fmt)
                    .background_gradient(subset=["Full-stack probability"], cmap="RdYlGn", vmin=0, vmax=1),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "**Full-stack probability** is shown only when every requested contact "
                    "was evaluated. Per-interface values use the pairwise development/spent "
                    "calibration artifact; they are not qualification evidence. A dash means "
                    "coverage is incomplete. Ranking discounts the covered bottleneck by coverage."
                )
                if any(not cr["coverage_complete"] for cr in cell_rows):
                    st.info(
                        "Some replacements have one or more unscored contacts. They may be "
                        "PFAS-free, but no full-stack compatibility verdict is emitted."
                    )
            else:
                st.subheader(f"Replacement Alternatives ({len(replacements)} found)")
                rows = []
                for r in replacements:
                    rows.append({
                        "Replacement": r.get("name", r.get("replacement", "?")),
                        "Score": r.get("overall_score", r.get("score", 0)),
                        "Performance": r.get("performance_match", 0),
                        "Processability": r.get("processability", 0),
                        "Cost Factor": r.get("cost_factor", 0),
                        "Availability": r.get("availability", 0),
                    })
                df = pd.DataFrame(rows).sort_values("Score", ascending=False)
                st.dataframe(
                    df.style.format({
                        "Score": "{:.2f}", "Performance": "{:.2f}",
                        "Processability": "{:.2f}", "Cost Factor": "{:.2f}",
                        "Availability": "{:.2f}",
                    }).background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=1),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "Add your cell's adjoining materials above to also rank these by "
                    "calibrated compatibility with your specific stack."
                )

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
# Tab 3: Screening Report Generator
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("PFAS Screening Report Generator")
    st.markdown(
        "Generate a structured first-pass screening report. It includes PFAS "
        "detections, replacement triage with provenance, a qualitative regulatory "
        "landscape, and follow-up actions. It is not a legal compliance determination; "
        "verify current primary sources before filing or making a market-access decision."
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
        st.markdown(
            "Paste your bill of materials — CSV (with or without a header row), "
            "`name | function | qty` lines, or just one material name per line. "
            "Brand names (e.g. `Kynar 2801`, `Teflon tape`) and free text "
            "(`copper foil`, `alumina`) are resolved automatically; anything "
            "unrecognized is flagged, never guessed."
        )
        custom_text = st.text_area(
            "Materials",
            value=(
                "Material,Function,Qty (kg)\n"
                "Kynar 2801,cathode binder,50\n"
                "Teflon tape,gasket seal,10\n"
                "NMC811,cathode,200\n"
                "copper foil,collector,80"
            ),
            height=150,
            key="custom_report_materials",
        )
        from ingest import ingest_bom

        ingest_result = ingest_bom(custom_text)
        summ = ingest_result.summary()
        c1, c2, c3 = st.columns(3)
        c1.metric("Recognized", summ["matched"] + summ["pfas_only"])
        c2.metric("Unrecognized", summ["unrecognized"])
        c3.metric("Total lines", summ["lines"])
        if ingest_result.parse_warnings:
            for w in ingest_result.parse_warnings:
                st.warning(w)
        if ingest_result.unrecognized:
            st.warning(
                "Unrecognized materials stay in the report as UNKNOWN — they are "
                "neither cleared nor flagged. If a suggestion below is what you "
                "meant, edit the input; suggestions are never auto-applied."
            )
            for r in ingest_result.unrecognized:
                sugg = f" — did you mean: {', '.join(r.suggestions)}?" if r.suggestions else ""
                st.markdown(f"- `{r.line.raw_name}`{sugg}")
        with st.expander("Resolution detail", expanded=False):
            st.table([
                {
                    "input": r.line.raw_name,
                    "resolved to": r.canonical or ("(PFAS registry only)" if r.status == "pfas_only" else "—"),
                    "status": r.status,
                    "PFAS signal": "yes" if r.pfas_flag else "",
                    "qty (kg)": r.line.quantity_kg,
                }
                for r in ingest_result.resolved
            ])
        custom_materials = ingest_result.to_material_inputs()

    if st.button("Generate Screening Report", type="primary", key="gen_report"):
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

                # Regulatory landscape (date-free by design)
                if report.regulatory_timeline:
                    st.subheader("Regulatory Landscape")
                    _STATUS_ICON = {
                        "banned": URGENCY_COLORS.get("critical", ""),
                        "proposed_ban": URGENCY_COLORS.get("high", ""),
                        "restricted": URGENCY_COLORS.get("moderate", ""),
                    }
                    tl_rows = []
                    for t in report.regulatory_timeline:
                        tl_rows.append({
                            "": _STATUS_ICON.get(t.status, ""),
                            "Jurisdiction": t.jurisdiction,
                            "Regulation": t.regulation,
                            "Status": t.status.replace("_", " ").title(),
                            "Timeframe": t.timeframe,
                        })
                    st.dataframe(pd.DataFrame(tl_rows), use_container_width=True, hide_index=True)
                    st.caption(
                        "Timeframes are qualitative. Specific deadlines vary by "
                        "jurisdiction and change frequently — verify current dates "
                        "against primary sources before filing."
                    )

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
            
            # Force reload if stale cache detected (missing family column)
            if "family" not in df_epa.columns:
                epa_data = get_epa_registry(force_reload=True)
                df_epa = pd.DataFrame(epa_data)

            # Filter UI
            st.markdown("---")
            col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
            
            # Ensure family column exists before unique()
            family_col = "family" if "family" in df_epa.columns else None
            
            with col_f1:
                search_q = st.text_input("🔍 Search SMILES or DTXSID", key="epa_search_q")
            with col_f2:
                if family_col:
                    family_options = sorted(df_epa[family_col].unique())
                    selected_families = st.multiselect("🧬 Chemical Family", family_options, key="epa_family_filter")
                else:
                    selected_families = []
                    st.info("Family detection initializing...")
            with col_f3:
                # Use columns that actually exist
                fw_col = "fw" if "fw" in df_epa.columns else None
                if fw_col:
                    min_fw = float(df_epa[fw_col].min() or 0)
                    max_fw = float(df_epa[fw_col].max() or 2000)
                    mw_range = st.slider("⚖️ Molecular Weight", min_fw, max_fw, (min_fw, max_fw), key="epa_mw_filter")
                else:
                    mw_range = (0.0, 2000.0)

            # Apply Filters
            filtered_df = df_epa.copy()
            if search_q:
                filtered_df = filtered_df[
                    filtered_df["smiles"].str.contains(search_q, case=False, na=False) | 
                    filtered_df["id"].str.contains(search_q, case=False, na=False)
                ]
            if selected_families and family_col:
                filtered_df = filtered_df[filtered_df[family_col].isin(selected_families)]
            
            if fw_col:
                filtered_df = filtered_df[
                    (filtered_df[fw_col].fillna(0) >= mw_range[0]) & 
                    (filtered_df[fw_col].fillna(0) <= mw_range[1])
                ]

            st.write(f"Showing **{len(filtered_df)}** of {len(df_epa)} substances")
            
            # Rename for display
            display_cols = {
                "smiles": "Structure (SMILES)", 
                "id": "DTXSID", 
                "fw": "Mol Weight",
                "family": "Chemical Family"
            }
            # Only rename columns that exist
            rename_map = {k: v for k, v in display_cols.items() if k in filtered_df.columns}
            
            st.dataframe(
                filtered_df.rename(columns=rename_map),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("EPA Dataset (data/EPA_PFASSTRUCTV4.txt) not found or empty.")
