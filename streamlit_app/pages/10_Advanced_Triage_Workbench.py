"""Advanced Discovery Workbench - High-Fidelity Triage + Verification.

This page extends the standard Discovery Workbench with high-precision 
logical verification and full-stack multi-domain checks.
"""

import sys
from pathlib import Path
import pandas as pd
import streamlit as st

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from discovery.workbench_service import DiscoveryWorkbenchService, DiscoveryGoal, DiscoveryCandidate
from composition_engine.designer import PropertyTarget
from streamlit_app.validation_status import render_feature_status

# --- High Fidelity Integrations ---
from composition_engine.physical_gates import charge_balanceable
from cross_bridge.multi_domain import MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent

st.set_page_config(page_title="Advanced Triage Workbench", page_icon="🧬", layout="wide")
st.title("Advanced Triage Workbench")
st.markdown(
    "A **Mixed-Fidelity** evolution of the Discovery Workbench. It combines fast "
    "triage-grade generation with high-precision ZFC logical gates and full-stack "
    "device compatibility verification."
)

render_feature_status("workbench")
render_login_sidebar()

# --- Shared UI Helpers (Mirrored from 9_Discovery_Workbench for consistency) ---

@st.cache_data
def get_material_options():
    from cross_bridge.multi_domain import _build_domain_registry
    registry = _build_domain_registry()
    names = sorted(registry.keys(), key=lambda s: s.lower())
    return names, registry

@st.cache_data
def get_element_options():
    return sorted([
        "Ac", "Ag", "Al", "Am", "Ar", "As", "At", "Au", "B", "Ba", "Be", "Bh",
        "Bi", "Bk", "Br", "C", "Ca", "Cd", "Ce", "Cf", "Cl", "Cm", "Cn", "Co",
        "Cr", "Cs", "Cu", "Db", "Ds", "Dy", "Er", "Es", "Eu", "F", "Fe", "Fl",
        "Fm", "Fr", "Ga", "Gd", "Ge", "H", "He", "Hf", "Hg", "Ho", "Hs", "I",
        "In", "Ir", "K", "Kr", "La", "Li", "Lr", "Lu", "Lv", "Mc", "Md", "Mg",
        "Mn", "Mo", "Mt", "N", "Na", "Nb", "Nd", "Ne", "Nh", "Ni", "No", "Np",
        "O", "Og", "Os", "P", "Pa", "Pb", "Pd", "Pm", "Po", "Pr", "Pt", "Pu",
        "Ra", "Rb", "Re", "Rf", "Rg", "Rh", "Rn", "Ru", "S", "Sb", "Sc", "Se",
        "Sg", "Si", "Sm", "Sn", "Sr", "Ta", "Tb", "Tc", "Te", "Th", "Ti", "Tl",
        "Tm", "Ts", "U", "V", "W", "Xe", "Y", "Yb", "Zn", "Zr",
    ], key=lambda s: s.lower())

_PROP_META = {
    "voltage": ("Voltage", "V"),
    "theoretical_capacity": ("Theoretical Capacity", "mAh/g"),
    "thermal_stability": ("Thermal Stability", "C"),
    "ionic_conductivity": ("Ionic Conductivity", "S/cm"),
    "density": ("Density", "g/cm3"),
    "formation_energy": ("Formation Energy", "eV/atom"),
    "synthesizability": ("Synthesizability", "0-1"),
    "melting_point": ("Melting Point", "C"),
}
_PROP_NAMES = sorted(_PROP_META.keys())

# --- Sidebar Configuration ---

with st.sidebar:
    st.header("1. Triage Goals")
    if "adv_wb_targets" not in st.session_state:
        st.session_state.adv_wb_targets = [{
            "name": "voltage",
            "use_min": True,
            "min": 3.0,
            "use_max": True,
            "max": 4.5,
            "weight": 1.0,
        }]

    def _add_target():
        st.session_state.adv_wb_targets.append({
            "name": "voltage", "use_min": False, "min": 0.0,
            "use_max": False, "max": 0.0, "weight": 1.0,
        })

    for i, t in enumerate(st.session_state.adv_wb_targets):
        with st.expander(f"Target {i+1}: {t['name'].title()}", expanded=True):
            t["name"] = st.selectbox("Property", _PROP_NAMES, index=_PROP_NAMES.index(t["name"]), key=f"adv_wb_prop_{i}")
            cols = st.columns(2)
            with cols[0]:
                t["use_min"] = st.checkbox("Use Min", value=bool(t.get("use_min", False)), key=f"adv_wb_use_min_{i}")
                t["min"] = st.number_input("Min", value=float(t.get("min", 0.0)), disabled=not t["use_min"], key=f"adv_wb_min_{i}")
            with cols[1]:
                t["use_max"] = st.checkbox("Use Max", value=bool(t.get("use_max", False)), key=f"adv_wb_use_max_{i}")
                t["max"] = st.number_input("Max", value=float(t.get("max", 0.0)), disabled=not t["use_max"], key=f"adv_wb_max_{i}")

    st.button("Add Property Target", on_click=_add_target)

    st.divider()
    st.header("2. High-Precision Verification")
    use_zfc = st.checkbox("ZFC Physical Gates", value=True, help="Enable charge-balance verification.")
    use_multi_domain = st.checkbox("Multi-Domain Cell Check", value=True, help="Verify candidate in a full-cell context.")

    if use_multi_domain:
        material_names, material_registry = get_material_options()
        st.subheader("Reference System")
        ref_electrolyte = st.selectbox("Electrolyte", material_names, index=material_names.index("LLZO") if "LLZO" in material_names else 0)
        ref_collector = st.selectbox("Collector", material_names, index=material_names.index("Al_foil") if "Al_foil" in material_names else 0)

    st.divider()
    st.header("3. Constraints")
    element_options = get_element_options()
    req_elems = st.multiselect("Required Elements", element_options, default=[])
    max_cands = st.slider("Triage Batch Size", 10, 100, 30)

# --- EXECUTION ENGINE ---

if st.button("Run Advanced Discovery Pipeline", type="primary"):
    if not require_access():
        st.stop()
    consume_use()

    service = DiscoveryWorkbenchService()
    analyzer = MultiDomainAnalyzer()

    # 1. Build Triage Goal
    targets = [PropertyTarget(name=t["name"], min_value=float(t["min"]) if t.get("use_min") else None, 
                              max_value=float(t["max"]) if t.get("use_max") else None, weight=t["weight"]) 
               for t in st.session_state.adv_wb_targets]
    
    goal = DiscoveryGoal(targets=targets, required_elements=req_elems, max_candidates=max_cands)

    with st.status("Executing Mixed-Fidelity Pipeline...", expanded=True) as status:
        # STEP 1: Fast Triage Generation
        st.write("Step 1: Running Triage (Inverse Design)...")
        candidates = service.run_discovery_pipeline(goal)
        
        # STEP 2: ZFC Verification (High Precision)
        if use_zfc and candidates:
            st.write(f"Step 2: Applying ZFC Physical Gates to {len(candidates)} candidates...")
            for c in candidates:
                c.compatibility_metadata["zfc_charge_balance"] = charge_balanceable(c.formula)
                if c.compatibility_metadata["zfc_charge_balance"] is False:
                    c.overall_confidence *= 0.1 # Severe penalty for unphysical results
                    c.safety_vetoes.append("ZFC: Charge Imbalance")

        # STEP 3: Multi-Domain Context (High Precision)
        if use_multi_domain and candidates:
            st.write(f"Step 3: Running Multi-Domain Context Analysis...")
            for c in candidates:
                try:
                    # Multi-domain bridges rely on known material properties.
                    # We must resolve the nearest known 'proxy' material to avoid UnknownMaterialError.
                    proxy_name = service._resolve_known_proxy(c)
                    if not proxy_name:
                        c.compatibility_metadata["error"] = "No known proxy material for context check."
                        continue

                    query_components = [
                        MultiDomainComponent(name=proxy_name, role="cathode", domain="battery"),
                        MultiDomainComponent(name=ref_electrolyte, role="electrolyte"),
                        MultiDomainComponent(name=ref_collector, role="collector")
                    ]
                    query = MultiDomainQuery(name=f"Context:{c.formula}", components=query_components, electrolyte=ref_electrolyte)
                    analysis = analyzer.analyze(query)
                    c.compatibility_score = analysis.overall_score
                    c.compatibility_viable = analysis.viable
                    c.compatibility_metadata["proxy_used"] = proxy_name
                    if analysis.bottleneck:
                        c.compatibility_metadata["bottleneck"] = f"{analysis.bottleneck.functor_used} ({analysis.bottleneck.score:.2f})"
                except Exception as e:
                    c.compatibility_metadata["context_error"] = str(e)

        status.update(label="Advanced Discovery Complete!", state="complete", expanded=False)

    if not candidates:
        st.error("No candidates survived the triage phase.")
    else:
        st.success(f"Processed {len(candidates)} candidates through mixed-fidelity verification.")

        # --- SCORECARD ---
        rows = []
        for c in candidates:
            zfc_status = "✅" if c.compatibility_metadata.get("zfc_charge_balance") is True else ("❌" if c.compatibility_metadata.get("zfc_charge_balance") is False else "❔")
            rows.append({
                "Formula": c.formula,
                "Integrity (ZFC)": zfc_status,
                "Confidence": c.overall_confidence,
                "Cell Viability": c.compatibility_score if c.compatibility_viable else 0.0,
                "Bottleneck": c.compatibility_metadata.get("bottleneck", "N/A"),
                "Design": c.design_score,
                "Safe": "✅" if c.is_pfas_free else "❌",
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({
                "Confidence": "{:.3f}", 
                "Design": "{:.3f}",
                "Cell Viability": lambda v: f"{v:.3f}" if v > 0 else "FAIL"
            })
            .background_gradient(subset=["Confidence", "Cell Viability"], cmap="RdYlGn"),
            use_container_width=True, hide_index=True
        )

        # --- DEEP DIVE ---
        selected_formula = st.selectbox("Candidate Deep Dive", [c.formula for c in candidates])
        if selected_formula:
            c = next(cand for cand in candidates if cand.formula == selected_formula)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Predicted Properties (Triage)**")
                st.json(c.predicted_properties)
            with col2:
                st.write("**Verification Metadata (Precision)**")
                st.json(c.compatibility_metadata)
                if c.safety_vetoes:
                    st.error(f"Vetoes: {', '.join(c.safety_vetoes)}")

else:
    st.info("Configure your triage goals and verification levels to start.")
