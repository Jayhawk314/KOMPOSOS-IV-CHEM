# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""MOF Explorer -- Screen Metal-Organic Frameworks for target applications."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="MOF Explorer", page_icon="🧊", layout="wide")
st.title("MOF Explorer")
st.markdown(
    "Screen 30 Metal-Organic Frameworks against operating conditions. "
    "MOFs are modular frameworks where metal nodes + organic linkers = tunable porosity."
)
render_feature_status("mof_explorer")

from mof_bridge.material_properties import ALL_MOFS, MOFTopology, MOFApplication, get_mof
from mof_bridge.interface_validator import (
    MOFInterfaceValidator,
    MOFConditions,
    MOFWeights,
    validate_mof,
)

# ---------------------------------------------------------------------------
# Tab 1: Screen MOFs
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(["Screen MOFs", "Single MOF Detail", "MOF Database"])

with tab1:
    st.subheader("Application Screening")
    st.markdown("Set your operating conditions and find the best MOFs.")

    col_app, col_env = st.columns(2)
    with col_app:
        target_app = st.selectbox(
            "Target application",
            [a.value for a in MOFApplication],
            format_func=lambda x: x.replace("_", " ").title(),
        )
    with col_env:
        environment = st.selectbox(
            "Operating environment",
            ["dry", "humid", "aqueous", "acidic", "basic"],
        )

    col_temp, col_pres, col_mol = st.columns(3)
    with col_temp:
        op_temp = st.number_input("Operating temp (C)", value=25, min_value=-50, max_value=800)
    with col_pres:
        op_pres = st.number_input("Operating pressure (bar)", value=1.0, min_value=0.01, max_value=500.0)
    with col_mol:
        mol_dia = st.number_input(
            "Target molecule diameter (A)",
            value=0.0, min_value=0.0, max_value=50.0,
            help="Set to 0 to skip pore size filtering",
        )

    col_ws, col_acid = st.columns(2)
    with col_ws:
        req_water = st.checkbox("Require water stability", value=(environment in ("aqueous", "humid")))
    with col_acid:
        req_acid = st.checkbox("Require acid stability", value=(environment == "acidic"))

    if st.button("Screen All MOFs", type="primary", key="screen_mofs"):
        conditions = MOFConditions(
            target_molecule_diameter=mol_dia if mol_dia > 0 else None,
            operating_temp_C=op_temp,
            operating_pressure_bar=op_pres,
            environment=environment,
            target_application=MOFApplication(target_app),
            requires_water_stable=req_water,
            requires_acid_stable=req_acid,
        )

        validator = MOFInterfaceValidator()
        results = validator.screen_all(conditions)

        suitable = [(n, s) for n, s in results if s.suitable]
        unsuitable = [(n, s) for n, s in results if not s.suitable]

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Suitable", len(suitable))
        col_m2.metric("Unsuitable", len(unsuitable))
        col_m3.metric("Best Score", f"{results[0][1].total:.3f}" if results else "N/A")

        import pandas as pd
        rows = []
        for name, score in results:
            mof = get_mof(name)
            rows.append({
                "MOF": name,
                "Score": round(score.total, 3),
                "Suitable": "Yes" if score.suitable else "No",
                "Pore": round(score.pore_accessibility, 3),
                "Chemical": round(score.chemical_stability, 3),
                "Thermal": round(score.thermal_compatibility, 3),
                "Mechanical": round(score.mechanical_compatibility, 3),
                "Application": round(score.application_suitability, 3),
                "Topology": mof.topology.value,
                "Water": mof.water_stability,
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({
                "Score": "{:.3f}", "Pore": "{:.3f}", "Chemical": "{:.3f}",
                "Thermal": "{:.3f}", "Mechanical": "{:.3f}", "Application": "{:.3f}",
            }).background_gradient(subset=["Score"], cmap="RdYlGn", vmin=0, vmax=1),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        import json
        import datetime
        bundle = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "software_version": "KOMPOSOS-IV-CHEM (Triage-Grade Explorer)",
            "screening_conditions": conditions.to_dict() if hasattr(conditions, "to_dict") else str(conditions),
            "mofs_audit": [
                {
                    "mof": get_mof(name).to_dict() if hasattr(get_mof(name), "to_dict") else name,
                    "score_audit": score.to_dict() if hasattr(score, "to_dict") else str(score)
                }
                for name, score in results
            ]
        }
        st.download_button(
            "📥 Download Reproducibility Bundle (JSON)",
            json.dumps(bundle, indent=2),
            "mofs_screening_audit.json",
            "application/json",
            use_container_width=True,
            help="Download an auditable JSON bundle containing the MOF properties, screening context, and 5-scorer verdicts."
        )

# ---------------------------------------------------------------------------
# Tab 2: Single MOF Detail
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("MOF Detail View")

    mof_name = st.selectbox("Select MOF", sorted(ALL_MOFS.keys()), key="detail_mof")
    mof = get_mof(mof_name)

    if mof:
        col_props, col_stab = st.columns(2)

        with col_props:
            st.markdown("**Structural Properties**")
            st.write(f"- Metal node: {mof.metal_node}")
            st.write(f"- Linker: {mof.linker}")
            st.write(f"- Topology: {mof.topology.value}")
            st.write(f"- Formula: {mof.formula}")
            st.write(f"- BET surface area: {mof.bet_surface_area_m2g:.0f} m2/g")
            st.write(f"- Pore volume: {mof.pore_volume_cm3g:.2f} cm3/g")
            st.write(f"- Pore diameter: {mof.pore_diameter_angstrom:.1f} A")
            if mof.bulk_modulus_GPa is not None:
                st.write(f"- Bulk modulus: {mof.bulk_modulus_GPa:.1f} GPa")

        with col_stab:
            st.markdown("**Stability & Application**")
            st.write(f"- Thermal stability: {mof.thermal_stability_C:.0f} C")
            st.write(f"- Water stability: {mof.water_stability}")
            st.write(f"- Chemical stability: {mof.chemical_stability}")
            st.write(f"- Primary application: {mof.primary_application.value}")
            st.write(f"- DOI: {mof.doi}")
            if mof.csd_code:
                st.write(f"- CSD code: {mof.csd_code}")

        # Literature sources
        if mof.sources:
            with st.expander("Literature Sources"):
                for key, citation in mof.sources.items():
                    st.write(f"- **{key}**: {citation}")

        # Quick suitability check
        st.markdown("---")
        st.markdown("**Quick Suitability Check**")
        detail_app = st.selectbox(
            "Application",
            [a.value for a in MOFApplication],
            format_func=lambda x: x.replace("_", " ").title(),
            key="detail_app",
        )
        if st.button("Check Suitability", key="detail_check"):
            conditions = MOFConditions(target_application=MOFApplication(detail_app))
            result = validate_mof(mof_name, conditions)
            d = result.to_dict()

            if result.suitable:
                st.success(f"**{mof_name}** is suitable for {detail_app} (score: {result.total:.3f})")
            else:
                st.warning(f"**{mof_name}** may not be suitable for {detail_app} (score: {result.total:.3f})")

            with st.expander("Score breakdown"):
                st.json(d)

# ---------------------------------------------------------------------------
# Tab 3: MOF Database
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("MOF Database Overview")
    st.markdown(f"**{len(ALL_MOFS)}** MOFs with published experimental data and DOI references.")

    # Group by topology
    st.markdown("**By Topology:**")
    import pandas as pd
    topo_rows = []
    for topo in MOFTopology:
        members = [n for n, m in ALL_MOFS.items() if m.topology == topo]
        if members:
            topo_rows.append({
                "Topology": topo.value,
                "Count": len(members),
                "MOFs": ", ".join(sorted(members)),
            })
    if topo_rows:
        st.dataframe(pd.DataFrame(topo_rows), use_container_width=True, hide_index=True)

    # Group by application
    st.markdown("**By Primary Application:**")
    app_rows = []
    for app in MOFApplication:
        members = [n for n, m in ALL_MOFS.items() if m.primary_application == app]
        if members:
            app_rows.append({
                "Application": app.value.replace("_", " ").title(),
                "Count": len(members),
                "MOFs": ", ".join(sorted(members)),
            })
    if app_rows:
        st.dataframe(pd.DataFrame(app_rows), use_container_width=True, hide_index=True)

    # Surface area leaderboard
    st.markdown("**Top 10 by BET Surface Area:**")
    sorted_mofs = sorted(ALL_MOFS.values(), key=lambda m: m.bet_surface_area_m2g, reverse=True)
    sa_rows = []
    for mof in sorted_mofs[:10]:
        sa_rows.append({
            "MOF": mof.name,
            "BET (m2/g)": f"{mof.bet_surface_area_m2g:.0f}",
            "Pore Vol (cm3/g)": f"{mof.pore_volume_cm3g:.2f}",
            "Water Stable": mof.water_stability,
            "DOI": mof.doi,
        })
    st.dataframe(pd.DataFrame(sa_rows), use_container_width=True, hide_index=True)
