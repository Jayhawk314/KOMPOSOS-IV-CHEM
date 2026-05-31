"""Solid-State Cell Designer — design multi-domain battery cells."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.md_controls import render_md_input_controls, render_md_result
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="Cell Designer", page_icon="🔋", layout="wide")
st.title("Solid-State Cell Designer")

render_login_sidebar()
st.markdown(
    "Design a battery cell spanning multiple material domains. "
    "The cross-bridge analyzer evaluates every interface and finds the bottleneck."
)
render_feature_status("cell_designer")

# ---------------------------------------------------------------------------
# Load materials
# ---------------------------------------------------------------------------

from battery_bridge.material_properties import ALL_MATERIALS as BATTERY_MATS
from polymer_bridge.material_properties import ALL_POLYMERS
from metal_bridge.material_properties import ALL_METALS
from ceramic_bridge.material_properties import ALL_CERAMICS
from cross_bridge.multi_domain import MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent
from battery_bridge.optimizer import BatteryOptimizer

# Categorize battery materials
CATHODES = sorted([n for n, m in BATTERY_MATS.items() if m.material_class.name in ("CATHODE",)])
ANODES = sorted([n for n, m in BATTERY_MATS.items() if m.material_class.name in ("ANODE",)])
ELECTROLYTES_LIQUID = sorted([n for n, m in BATTERY_MATS.items() if m.material_class.name in ("ELECTROLYTE_SOLVENT", "ELECTROLYTE_SALT")])
ELECTROLYTES_SOLID = sorted([n for n, m in BATTERY_MATS.items() if m.material_class.name in ("SOLID_ELECTROLYTE",)])
BINDERS = sorted([n for n, m in ALL_POLYMERS.items()])
COLLECTORS = sorted([n for n, m in ALL_METALS.items()])
CERAMIC_ELECTROLYTES = sorted([n for n, m in ALL_CERAMICS.items()])

# Presets
PRESETS = {
    "Custom": {},
    "Standard Liquid Cell (LFP + EC)": {
        "cathode": "LFP",
        "electrolyte": "EC",
        "binder": "PVDF",
        "collector": "Al",
        "cell_type": "liquid",
    },
    "Solid-State (NMC811 + LLZO)": {
        "cathode": "NMC811",
        "electrolyte": "LLZO",
        "binder": "PEO",
        "collector": "Cu",
        "cell_type": "solid",
    },
    "Solid-State (LFP + LGPS)": {
        "cathode": "LFP",
        "electrolyte": "LGPS",
        "binder": "PEO",
        "collector": "Al",
        "cell_type": "solid",
    },
    "High-Voltage (NMC622 + LLZO)": {
        "cathode": "NMC622",
        "electrolyte": "LLZO",
        "binder": "PVDF",
        "collector": "Al",
        "cell_type": "solid",
    },
}

# ---------------------------------------------------------------------------
# UI Tabs
# ---------------------------------------------------------------------------

tab1, tab2 = st.tabs(["Manual Designer", "Battery Optimizer"])

with tab1:
    preset = st.selectbox("Start from a preset", list(PRESETS.keys()))
    p = PRESETS.get(preset, {})

    st.subheader("Cell Configuration")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cathode = st.selectbox(
            "Cathode (battery)",
            CATHODES,
            index=CATHODES.index(p["cathode"]) if p.get("cathode") in CATHODES else 0,
        )

    with col2:
        cell_type = st.radio(
            "Electrolyte type",
            ["Solid", "Liquid"],
            index=0 if p.get("cell_type") == "solid" else 1,
            key="manual_cell_type"
        )
        if cell_type == "Solid":
            electrolyte_options = ELECTROLYTES_SOLID
        else:
            electrolyte_options = ELECTROLYTES_LIQUID

        default_e = p.get("electrolyte", electrolyte_options[0] if electrolyte_options else "")
        e_idx = electrolyte_options.index(default_e) if default_e in electrolyte_options else 0
        electrolyte = st.selectbox("Electrolyte", electrolyte_options, index=e_idx, key="manual_elec")

    with col3:
        default_b = p.get("binder", BINDERS[0] if BINDERS else "")
        b_idx = BINDERS.index(default_b) if default_b in BINDERS else 0
        binder = st.selectbox("Binder (polymer)", BINDERS, index=b_idx, key="manual_binder")

    with col4:
        default_c = p.get("collector", COLLECTORS[0] if COLLECTORS else "")
        c_idx = COLLECTORS.index(default_c) if default_c in COLLECTORS else 0
        collector = st.selectbox("Collector (metal)", COLLECTORS, index=c_idx, key="manual_collector")

    # Advanced options
    with st.expander("Advanced options"):
        scoring_mode = st.selectbox(
            "Scoring mode",
            ["Auto", "Bottleneck (0.75*min + 0.25*avg)", "Weighted (bottleneck de-emphasized)"],
        )
        viability_threshold = st.slider("Viability threshold", 0.0, 1.0, 0.50, 0.05)
        md_verify = st.checkbox("Trigger Active Verification for Bottleneck", help="Run GROMACS simulation for the weakest interface identified in the cell stack.")
        md_conditions = {}
        if md_verify:
            md_conditions = render_md_input_controls("cell_md")

    # ---------------------------------------------------------------------------
    # Run analysis
    # ---------------------------------------------------------------------------

    if st.button("Analyze Cell Design", type="primary"):
        if not require_access():
            st.stop()
        consume_use()
        components = [
            MultiDomainComponent(name=cathode, role="cathode"),
            MultiDomainComponent(name=electrolyte, role="electrolyte"),
            MultiDomainComponent(name=binder, role="binder"),
            MultiDomainComponent(name=collector, role="collector"),
        ]

        # Map scoring mode
        if scoring_mode.startswith("Bottleneck"):
            mode = "bottleneck"
        elif scoring_mode.startswith("Weighted"):
            mode = "weighted"
        else:
            mode = None  # auto

        query = MultiDomainQuery(
            name=f"{cathode} + {electrolyte} + {binder} + {collector}",
            components=components,
            electrolyte=electrolyte,
            scoring_mode=mode,
        )

        analyzer = MultiDomainAnalyzer(viability_threshold=viability_threshold)

        with st.spinner("Evaluating cross-domain interfaces..."):
            analysis = analyzer.analyze(query)

        # --- Integrated MD for Bottleneck ---
        md_results = None
        if md_verify and analysis.bottleneck:
            from oracle.md_integration import MDIntegrator
            bn = analysis.bottleneck
            md_integrator = MDIntegrator()
            
            with st.spinner(f"Simulating Bottleneck MD: {bn.component_a} <-> {bn.component_b}..."):
                md_run = md_integrator.run_verification(bn.component_a, bn.component_b, "battery", md_conditions)
                md_constraint_scores = md_run.constraint_scores()
                md_fusion = md_run.fuse_with_categorical(
                    bn.score,
                    bn.compatible,
                    cat_confidence=0.4 if 0.4 < bn.score < 0.6 else 0.8,
                )
                md_results = {
                    'verdict': md_run.verdict,
                    'measured_md': md_run.measured_md,
                    'viable': md_run.viable,
                    'score': md_run.score,
                    'confidence': md_run.confidence,
                    'detail': md_run.detail,
                    'energy_diff': md_run.potential_energy_diff,
                    'diffusion': md_run.diffusion_coefficient,
                    'constraint_scores': md_constraint_scores,
                    'fusion': md_fusion,
                    'metadata': md_run.simulation_metadata
                }
                if md_fusion.get("used"):
                    bn.compatible = bool(md_fusion["fused_viable"])
                elif md_run.confidence > 0.8:
                    bn.compatible = md_run.viable
                    # Re-check overall viability
                    # (Simple check: if bottleneck is not compatible, cell is likely not viable)
                    if not md_run.viable:
                        analysis.viable = False

        # Overall result
        st.divider()
        if analysis.viable:
            st.success(
                f"**Cell Design Viable** — Overall score: **{analysis.overall_score:.3f}** "
                f"(threshold: {viability_threshold})"
            )
        else:
            st.error(
                f"**Cell Design Not Viable** — Overall score: **{analysis.overall_score:.3f}** "
                f"(threshold: {viability_threshold})"
            )

        # Metrics row
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Overall Score", f"{analysis.overall_score:.3f}")
        col_m2.metric("Domains", ", ".join(analysis.domains_involved))
        col_m3.metric("Interfaces", len(analysis.cross_domain_scores))
        if analysis.bottleneck:
            col_m4.metric(
                "Bottleneck",
                f"{analysis.bottleneck.component_a}-{analysis.bottleneck.component_b}",
            )

        # Interface scores table
        st.subheader("Cross-Domain Interface Scores")

        import pandas as pd
        rows = []
        for s in analysis.cross_domain_scores:
            rows.append({
                "Interface": f"{s.component_a} <-> {s.component_b}",
                "Functor": s.functor_used,
                "Score": s.score,
                "Compatible": "Yes" if s.compatible else "No",
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(
                df.style.format({"Score": "{:.3f}"}).background_gradient(
                    subset=["Score"], cmap="RdYlGn", vmin=0, vmax=1
                ),
                use_container_width=True,
                hide_index=True,
            )

            # Bar chart
            chart_df = pd.DataFrame({
                "Interface": [r["Interface"] for r in rows],
                "Score": [r["Score"] for r in rows],
            }).set_index("Interface")
            st.bar_chart(chart_df, horizontal=True)

        # Bottleneck detail
        if analysis.bottleneck:
            bn = analysis.bottleneck
            st.subheader("Bottleneck Analysis")
            st.warning(
                f"The weakest interface is **{bn.component_a} <-> {bn.component_b}** "
                f"(functor: {bn.functor_used}, score: {bn.score:.3f}). "
                f"Improving this interface would have the largest impact on overall cell viability."
            )
            
            if md_results:
                render_md_result(md_results, "Active Verification for Bottleneck (GROMACS)")

        # Warnings
        if analysis.warnings:
            st.subheader("Warnings")
            for w in analysis.warnings:
                st.warning(w)

        # Raw data
        with st.expander("Raw analysis data"):
            st.json(analysis.to_dict())


with tab2:
    st.subheader("Evolutionary Battery Optimizer")
    st.markdown(
        "Automatically sweep material combinations to find the best cell stack for your application. "
        "Stage 1 finds 'Elite' designs from known materials; Stage 2 evolves them using the 103K MP cache."
    )

    col_o1, col_o2 = st.columns(2)
    with col_o1:
        opt_cell_type = st.radio("Electrolyte Type", ["Solid", "Liquid"], key="opt_cell_type")
        opt_pfas = st.checkbox("PFAS-Free Only", value=True, help="Exclude PVDF, PTFE, and other regulated polymers.")
        opt_discovery = st.checkbox("Enable 103K Discovery", value=False, help="Evolve designs using chemical neighbors from the Materials Project.")
    
    with col_o2:
        st.markdown("**Lock Components (optional)**")
        opt_fixed_elec = st.selectbox("Fixed Electrolyte", ["Any"] + (ELECTROLYTES_SOLID if opt_cell_type == "Solid" else ELECTROLYTES_LIQUID))
        opt_fixed_col = st.selectbox("Fixed Collector", ["Any"] + COLLECTORS)

    if st.button("Run Optimization Sweep", type="primary"):
        if not require_access():
            st.stop()
        consume_use()
        
        optimizer = BatteryOptimizer()
        fixed = {"cell_type": opt_cell_type.lower()}
        if opt_fixed_elec != "Any":
            fixed["electrolyte"] = opt_fixed_elec
        if opt_fixed_col != "Any":
            fixed["collector"] = opt_fixed_col
            
        with st.spinner("Optimizing cell stacks (Stage 1 + Stage 2)..."):
            results = optimizer.optimize(
                fixed_components=fixed,
                pfas_free_only=opt_pfas,
                enable_discovery=opt_discovery
            )
            
        if not results:
            st.warning("No viable designs found with the current constraints.")
        else:
            st.success(f"Found **{len(results)}** optimized cell configurations.")
            
            import pandas as pd
            df_opt = pd.DataFrame([r.to_dict() for r in results])
            
            st.dataframe(
                df_opt.drop(columns=["mp_id", "notes"]).style.format({
                    "energy_density": "{:.1f}",
                    "viability": "{:.3f}"
                }).background_gradient(subset=["energy_density"], cmap="viridis")
                .background_gradient(subset=["viability"], cmap="RdYlGn", vmin=0, vmax=1),
                use_container_width=True,
                hide_index=True
            )
            
            st.caption("Energy Density is a theoretical estimate ($V \times C$). Viability is the cross-bridge compatibility score.")
            
            if opt_discovery:
                st.info("💡 'Discovery' results suggest novel cathode variants from the 103K cache with higher predicted energy density.")

# ---------------------------------------------------------------------------
# Info section
# ---------------------------------------------------------------------------

st.divider()
with st.expander("How does multi-domain analysis work?"):
    st.markdown("""
    The cell designer uses **cross-bridge functors** to evaluate interfaces between
    materials from different domains:

    - **battery_polymer functor**: Evaluates cathode/electrolyte + binder compatibility
      (voltage window, chemical stability, wetting)
    - **battery_metal functor**: Evaluates cathode/electrolyte + current collector
      (anodic limit, corrosion, CTE matching)
    - **ceramic_metal functor**: Evaluates ceramic electrolyte + metal collector
      (CTE mismatch, thermal processing, chemical reactivity)

    The overall score uses either:
    - **Bottleneck mode** (default for <=2 interfaces): `0.75 * min + 0.25 * avg`
    - **Weighted mode** (default for >2 interfaces): bottleneck gets 0.5x weight
      to avoid single-interface domination

    A cell design is viable if the overall score exceeds the viability threshold (default 0.50).
    """)
