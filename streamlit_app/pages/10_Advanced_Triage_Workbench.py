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

# --- Verification integrations ---
from cross_bridge.multi_domain import MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent

st.set_page_config(page_title="Advanced Triage Workbench", page_icon="🧬", layout="wide")
st.title("Advanced Triage Workbench")
st.markdown(
    "A **Mixed-Fidelity** evolution of the Discovery Workbench. It combines fast "
    "triage-grade generation with a deterministic charge-balance gate and "
    "coverage-aware device-interface screening."
)

with st.expander("ℹ️ How the pipeline works (mechanics)"):
    st.markdown("""
    A **Mixed-Fidelity** pipeline that balances speed and rigor:

    1. **Triage Phase (The Generator)** — inverse design + stoichiometry search proposes
       candidate formulas from your target properties. These are *suggestions* (hallucinations
       are possible). Scorecard: `Triage Confidence`, `Design Score`.
    2. **Precision Phase (The Filter)** — strict checks that veto bad guesses:
       - **Charge-Balance Gate** — rejects formulas with no common oxidation-state assignment.
       - **Cell Interface Screen** — scores the candidate's *nearest known analog* inside the
         chosen reference cell. The scorecard shows
         the **proxy distance**; a far proxy is a weak stand-in. Non-battery candidates are
         not cell-scored. Missing native interface functors are reported as incomplete coverage,
         never silently averaged away.
       Scorecard: `Charge Balance`, `Cell Interface Score`, `Coverage`, `Proxy (dist)`.

    **How to use:** trust the *vetoes* (Precision Phase) more than the *suggestions*. See the
    accuracy banner below for the honest, sourced numbers.
    """)

render_feature_status("advanced_workbench")
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

@st.cache_resource
def get_cached_predictor():
    from composition_engine.predictor import CompositionPredictor
    return CompositionPredictor()

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
    use_zfc = st.checkbox("Charge-Balance Gate", value=True, help="Use pymatgen oxidation-state feasibility; unassessable formulas receive no verdict.")
    use_multi_domain = st.checkbox("Multi-Domain Interface Check", value=True, help="Screen covered proxy interfaces and expose missing coverage.")

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

if "adv_wb_candidates" not in st.session_state:
    st.session_state.adv_wb_candidates = None

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
    
    goal = DiscoveryGoal(
        targets=targets,
        required_elements=req_elems,
        max_candidates=max_cands,
        apply_charge_balance_gate=use_zfc,
    )

    with st.status("Executing Mixed-Fidelity Pipeline...", expanded=True) as status:
        # STEP 1: Fast Triage Generation
        st.write("Step 1: Running Triage (Inverse Design)...")
        candidates = service.run_discovery_pipeline(goal)
        
        # STEP 2: deterministic charge-balance verification
        if use_zfc and candidates:
            st.write(f"Step 2: Applying charge-balance gates to {len(candidates)} candidates...")
            for c in candidates:
                c.compatibility_metadata['charge_balance_status'] = c.zfc_witnessed
                if c.zfc_witnessed is False:
                    c.overall_confidence = 0.0

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

                    # The reference cell is battery-only. Scoring a non-battery proxy as a
                    # "cathode" would be meaningless, so gate the cell check on proxy domain.
                    proxy_domain = material_registry.get(proxy_name)
                    if proxy_domain != "battery":
                        c.compatibility_metadata["proxy_used"] = proxy_name
                        c.compatibility_metadata["cell_check_skipped"] = (
                            f"proxy '{proxy_name}' is {proxy_domain or 'unknown'}-domain; "
                            "reference cell is battery-only"
                        )
                        continue

                    query_components = [
                        MultiDomainComponent(name=proxy_name, role="cathode", domain="battery"),
                        MultiDomainComponent(name=ref_electrolyte, role="electrolyte"),
                        MultiDomainComponent(name=ref_collector, role="collector")
                    ]
                    adjacency = {
                        frozenset({'cathode', 'electrolyte'}),
                        frozenset({'cathode', 'collector'}),
                        frozenset({'electrolyte', 'collector'}),
                    }
                    query = MultiDomainQuery(
                        name=f"Context:{c.formula}",
                        components=query_components,
                        electrolyte=ref_electrolyte,
                        adjacency=adjacency,
                    )
                    analysis = analyzer.analyze(query)

                    # This is an aggregate of cross-domain functor scores, not a
                    # pairwise score from the compatibility calibrator. Do not
                    # launder it into a calibrated probability.
                    c.compatibility_score = analysis.overall_score
                    c.compatibility_viable = analysis.viable and analysis.coverage_complete
                    c.compatibility_metadata["proxy_used"] = proxy_name
                    c.compatibility_metadata["raw_multidomain_score"] = round(analysis.overall_score, 4)
                    c.compatibility_metadata['interface_coverage'] = round(analysis.coverage_fraction, 4)
                    c.compatibility_metadata['coverage_complete'] = analysis.coverage_complete
                    c.compatibility_metadata['unscored_interfaces'] = analysis.unscored_interfaces
                    if analysis.bottleneck:
                        c.compatibility_metadata["bottleneck"] = f"{analysis.bottleneck.functor_used} ({analysis.bottleneck.score:.2f})"
                except Exception as e:
                    c.compatibility_metadata["context_error"] = str(e)

        st.session_state.adv_wb_candidates = candidates
        status.update(label="Advanced Discovery Complete!", state="complete", expanded=False)

if st.session_state.adv_wb_candidates is not None:
    candidates = st.session_state.adv_wb_candidates
    if not candidates:
        st.error("No candidates survived the triage phase.")
    else:
        st.success(f"Processed {len(candidates)} candidates through mixed-fidelity verification.")

        # --- SCORECARD ---
        _FAR_PROXY = 0.5  # composition-space distance above which a proxy is a weak stand-in
        rows = []
        for c in candidates:
            meta = c.compatibility_metadata
            charge_status = meta.get('charge_balance_status')
            charge_display = 'PASS' if charge_status is True else ('VETO' if charge_status is False else 'UNASSESSED')

            # Aggregate cross-domain score with explicit coverage; it is not a
            # calibrated pairwise compatibility probability.
            if meta.get("cell_check_skipped"):
                cell_display = "n/a"
            elif meta.get('coverage_complete') is False and 'raw_multidomain_score' in meta:
                cell_display = f"PARTIAL {c.compatibility_score:.3f}"
            elif c.compatibility_viable:
                cell_display = round(float(c.compatibility_score), 3)
            else:
                cell_display = "FAIL"

            coverage = meta.get('interface_coverage')
            coverage_display = f'{coverage:.0%}' if isinstance(coverage, (int, float)) else 'n/a'

            # Proxy + distance (flag far proxies whose cell score is a weak signal).
            proxy = meta.get("proxy_used")
            dist = meta.get("proxy_distance")
            if proxy is None:
                proxy_display = "—"
            elif dist is None:
                proxy_display = proxy
            else:
                flag = " ⚠️far" if dist > _FAR_PROXY else ""
                proxy_display = f"{proxy} ({dist:.2f}){flag}"

            rows.append({
                "Formula": c.formula,
                "Charge Balance": charge_display,
                "Triage Confidence": round(float(c.overall_confidence), 3),
                "Cell Interface Score": cell_display,
                "Coverage": coverage_display,
                "Proxy (dist)": proxy_display,
                "Bottleneck": meta.get("bottleneck", "N/A"),
                "Design Score": round(float(c.design_score), 3),
                "Safe": "✅" if c.is_pfas_free else "❌",
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.background_gradient(subset=["Triage Confidence"], cmap="RdYlGn"),
            use_container_width=True, hide_index=True
        )
        st.caption(
            "**Cell Interface Score** is an uncalibrated aggregate over the native cross-domain "
            "functors that were available for the candidate's nearest known analog. `PARTIAL` "
            "means at least one requested physical interface had no native scorer; it is not a "
            "full-cell verdict. `n/a` means the battery-only context was not applicable. "
            "**Proxy (dist)** is that analog and its composition-space distance; ⚠️far (>"
            f"{_FAR_PROXY}) means the cell score is a weak stand-in for the novel formula."
        )

        # --- DEEP DIVE ---
        st.divider()
        st.subheader("Candidate Deep Dive")
        selected_formula = st.selectbox("Select a candidate to view precise prediction bounds and logical metadata:", [c.formula for c in candidates])
        if selected_formula:
            c = next(cand for cand in candidates if cand.formula == selected_formula)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Predicted Properties (With Uncertainty)**")
                st.caption("Shows the central triage estimate and the model's [Lower to Upper] bounds. Formation-energy intervals are calibrated separately; other property bounds remain heuristic and should not be read as guaranteed coverage.")
                
                # Re-run predictor on the selected candidate to get full uncertainty bounds
                # (Designer strips bounds for speed, we need them for transparency)
                predictor = get_cached_predictor()
                try:
                    full_prediction = predictor.predict(c.formula, domain=c.domain)
                    display_props = {}
                    for prop_name, prop_data in full_prediction.properties.items():
                        val = prop_data.value
                        lower = prop_data.lower_bound
                        upper = prop_data.upper_bound
                        conf = prop_data.confidence
                        
                # Format as Value [Lower - Upper] (Conf: X%)
                        if lower is not None and upper is not None:
                            display_props[prop_name] = f"{val:.3f}  [{lower:.3f} to {upper:.3f}]  (conf: {conf:.2f})"
                        else:
                            display_props[prop_name] = f"{val:.3f}  (conf: {conf:.2f})"
                    st.json(display_props)
                    
                    # --- REPRODUCIBILITY BUNDLE EXPORT ---
                    import json
                    import datetime
                    
                    bundle = {
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                        "software_version": "KOMPOSOS-IV-CHEM (Triage-Grade)",
                        "candidate": {
                            "formula": c.formula,
                            "design_score": c.design_score,
                            "triage_confidence": c.overall_confidence
                        },
                        "prediction_audit": {
                            "method": full_prediction.method,
                            "nearest_known_anchors": full_prediction.nearest_known,
                            "raw_properties": {
                                k: {"value": v.value, "lower": v.lower_bound, "upper": v.upper_bound, "confidence": v.confidence} 
                                for k, v in full_prediction.properties.items()
                            }
                        },
                        "physical_gate_audit": {
                            "charge_balance_status": c.compatibility_metadata.get("charge_balance_status"),
                            "pfas_free_status": c.is_pfas_free,
                            "hard_vetoes": c.hard_vetoes,
                            "safety_vetoes": c.safety_vetoes,
                            "multi_domain_context": c.compatibility_metadata
                        }
                    }
                    
                    st.download_button(
                        label="📥 Download Reproducibility Bundle (JSON)",
                        data=json.dumps(bundle, indent=2),
                        file_name=f"komposos_audit_{c.formula}.json",
                        mime="application/json",
                        help="Download the model bounds, data anchors, charge-balance status, interface coverage, and proxy trace used for this prediction."
                    )
                    
                except Exception as e:
                    st.warning(f"Could not retrieve full uncertainty bounds: {e}")
                    st.json(c.predicted_properties)
            with col2:
                st.write("**Verification Metadata**")
                st.caption("Shows the deterministic charge-balance result, proxy identity/distance, scored interfaces, missing coverage, and bottleneck. None of these are wet-lab verification.")
                st.json(c.compatibility_metadata)
                if c.safety_vetoes:
                    st.error(f"Vetoes: {', '.join(c.safety_vetoes)}")

else:
    st.info("Configure your triage goals and verification levels to start.")
