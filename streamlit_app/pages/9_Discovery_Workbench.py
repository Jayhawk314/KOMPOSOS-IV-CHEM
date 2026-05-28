"""Autonomous Discovery Workbench - unified discovery pipeline."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import pandas as pd
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from discovery.workbench_service import DiscoveryWorkbenchService, DiscoveryGoal, DiscoveryCandidate
from composition_engine.designer import PropertyTarget

st.set_page_config(page_title="Discovery Workbench", page_icon="ðŸ”¬", layout="wide")
st.title("Autonomous Discovery Workbench")
st.markdown(
    "Unify all 8 KOMPOSOS-IV features into a single discovery pipeline. "
    "Set your discovery goal below to generate, screen, verify, and plan synthesis for novel materials."
)

render_login_sidebar()

# --- MATERIAL AUTOFILL (for compatibility context) ---
@st.cache_data
def get_material_options():
    """Return sorted material-name options and a name->domain map."""
    from cross_bridge.multi_domain import _build_domain_registry

    registry = _build_domain_registry()  # name -> domain
    names = sorted(registry.keys(), key=lambda s: s.lower())
    return names, registry

# --- TARGET PROPERTIES CONFIG ---
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

with st.sidebar:
    st.header("Discovery Configuration")
    
    st.subheader("1. Target Properties")
    if "workbench_targets" not in st.session_state:
        st.session_state.workbench_targets = [{
            "name": "ionic_conductivity",
            "use_min": True,
            "min": 0.01,
            "use_max": False,
            "max": 0.0,
            "weight": 1.0,
        }]

    def _add_target():
        st.session_state.workbench_targets.append({
            "name": "voltage",
            "use_min": False,
            "min": 0.0,
            "use_max": False,
            "max": 0.0,
            "weight": 1.0,
        })

    def _remove_target(idx):
        if len(st.session_state.workbench_targets) > 1:
            st.session_state.workbench_targets.pop(idx)

    for i, t in enumerate(st.session_state.workbench_targets):
        with st.expander(f"Target {i+1}: {t['name'].title()}", expanded=True):
            t["name"] = st.selectbox("Property", _PROP_NAMES, index=_PROP_NAMES.index(t["name"]), key=f"wb_prop_{i}")
            cols = st.columns(2)
            with cols[0]:
                t["use_min"] = st.checkbox("Use Min", value=bool(t.get("use_min", False)), key=f"wb_use_min_{i}")
                t["min"] = st.number_input(
                    "Min Value",
                    value=float(t.get("min", 0.0) or 0.0),
                    disabled=not t["use_min"],
                    key=f"wb_min_{i}",
                )
            with cols[1]:
                t["use_max"] = st.checkbox("Use Max", value=bool(t.get("use_max", False)), key=f"wb_use_max_{i}")
                t["max"] = st.number_input(
                    "Max Value",
                    value=float(t.get("max", 0.0) or 0.0),
                    disabled=not t["use_max"],
                    key=f"wb_max_{i}",
                )
            if st.button("Remove", key=f"wb_rem_{i}"):
                _remove_target(i)
                st.rerun()

    st.button("Add Property Target", on_click=_add_target)

    st.divider()
    st.subheader("2. Compatibility Context")
    material_names, material_registry = get_material_options()
    default_idx = material_names.index("Li_metal") if "Li_metal" in material_names else 0
    target_mat = st.selectbox(
        "Adjoining Material (Interface)",
        material_names,
        index=default_idx,
        help="Verify candidates against this material (type to search; sorted A-Z).",
        format_func=lambda n: f"{n} ({material_registry.get(n, 'unknown')})",
    )
    _role_options = sorted(
        {
            "anode_interface",
            "cathode_interface",
            "solid_electrolyte",
            "hybrid_electrolyte",
            "electrolyte",
            "separator",
            "binder",
            "cathode_binder",
            "anode_binder",
            "current_collector",
            "cathode_collector",
            "anode_collector",
            "coating",
            "hermetic_seal",
            "ohmic_contact",
        },
        key=lambda s: s.lower(),
    )
    _role_options = ["solid_electrolyte"] + [r for r in _role_options if r != "solid_electrolyte"] + ["Custom..."]
    selected_role = st.selectbox(
        "Interface Role",
        _role_options,
        index=0,
        help="Role/context for the interface (type to search; sorted A-Z).",
    )
    interface_role = (
        st.text_input("Custom Role", value="", placeholder="e.g. anode_interface")
        if selected_role == "Custom..."
        else selected_role
    )

    st.divider()
    st.subheader("3. Pipeline Limits")
    max_cands = st.slider("Max Candidates", 10, 100, 30)

# --- PIPELINE EXECUTION ---

if st.button("Start Discovery Pipeline", type="primary"):
    if not require_access():
        st.stop()
    consume_use()
    
    # 1. Build Goal
    targets = []
    for t in st.session_state.workbench_targets:
        min_val = float(t["min"]) if t.get("use_min") else None
        max_val = float(t["max"]) if t.get("use_max") else None
        targets.append(PropertyTarget(name=t["name"], min_value=min_val, max_value=max_val, weight=t["weight"]))
    
    goal = DiscoveryGoal(
        targets=targets,
        target_interface_material=target_mat if target_mat else None,
        interface_role=interface_role if interface_role else None,
        max_candidates=max_cands
    )
    
    service = DiscoveryWorkbenchService()
    
    # 2. Run with status
    with st.status("Executing Discovery Pipeline...", expanded=True) as status:
        st.write("Step 1: Inverse Design (Crystal Dreamer)...")
        # In real impl, we'd add callbacks to service, but here we just run
        candidates = service.run_discovery_pipeline(goal)
        status.update(label="Discovery Complete!", state="complete", expanded=False)
        
    if not candidates:
        st.error("No candidates found matching requirements.")
    else:
        st.success(f"Discovered {len(candidates)} candidates. Top results below.")
        
        # 3. Integrated Scorecard
        st.subheader("Integrated Discovery Scorecard")
        
        rows = []
        for c in candidates:
            rows.append({
                "Formula": c.formula,
                "Confidence": c.overall_confidence,
                "Depth": c.pipeline_depth,
                "Design": c.design_score,
                "Safe": "âœ…" if c.is_pfas_free else "â Œ",
                "Compatible": f"{c.compatibility_score:.3f}" if c.compatibility_viable else "FAIL",
                "Synth": f"{c.synthesizability_score:.3f}",
                "Cost": f"${c.estimated_cost:.2f}" if c.estimated_cost > 0 else "N/A"
            })
            
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({
                "Confidence": "{:.3f}",
                "Design": "{:.3f}"
            }).background_gradient(subset=["Confidence", "Design"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True
        )
        
        # 4. Deep Dive
        selected_formula = st.selectbox("Select Candidate for Deep Dive", [c.formula for c in candidates])
        if selected_formula:
            c = next(cand for cand in candidates if cand.formula == selected_formula)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Predicted Properties**")
                st.json(c.predicted_properties)
                if c.precursors:
                    st.write("**Suggested Precursors**")
                    st.write(", ".join(c.precursors))
            with col2:
                st.write("**Audit Trail**")
                if c.safety_vetoes:
                    st.warning(f"Safety Vetoes: {', '.join(c.safety_vetoes)}")
                st.json(c.compatibility_metadata)

else:
    st.info("Configure your discovery goal in the sidebar and click 'Start Discovery Pipeline'.")
