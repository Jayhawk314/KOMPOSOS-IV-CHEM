# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Composition Predictor — predict properties from any chemical formula."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="Composition Predictor", page_icon="🧪", layout="wide")
st.title("Composition Predictor")

render_login_sidebar()
from composition_engine.known_compositions import get_db as _get_db
_mat_count = _get_db().size
st.markdown(
    f"Enter any chemical formula to predict material properties using "
    f"**Kan extension + Dempster-Shafer fusion** over {_mat_count:,} known materials."
)
render_feature_status("composition_predictor")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from composition_engine.predictor import CompositionPredictor
from composition_engine.parser import SHORTHAND_MAP
from utils.formula_autocomplete import (
    formula_input_with_autocomplete,
    show_formula_reference
)

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

formula = formula_input_with_autocomplete(
    label="Chemical formula",
    key="main_formula",
    default_value="LiNi0.7Mn0.15Co0.15O2",
    help_text="Select from library or enter any valid chemical formula",
    placeholder="e.g., NMC811 or LiNi0.8Mn0.1Co0.1O2"
)

# Show formula reference
show_formula_reference()

if st.button("Predict Properties", type="primary"):
    if not require_access():
        st.stop()
    consume_use()
    predictor = CompositionPredictor()

    try:
        with st.spinner("Running Kan extension + D-S fusion..."):
            result = predictor.predict(formula)
        d = result.to_dict()
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    # Formula and composition
    st.subheader(f"Results for: {d['formula']}")

    # Composition pie chart
    composition = d.get("composition", {})
    if composition:
        import pandas as pd
        comp_df = pd.DataFrame({
            "Element": list(composition.keys()),
            "Fraction": list(composition.values()),
        })
        col_comp, col_props = st.columns([1, 2])
        with col_comp:
            st.markdown("**Elemental Composition**")
            st.dataframe(
                comp_df.style.format({"Fraction": "{:.3f}"}),
                use_container_width=True,
                hide_index=True,
            )

    # Predicted properties
    properties = d.get("properties", {})
    if properties:
        with col_props:
            st.markdown("**Predicted Properties**")
            rows = []
            for prop_name, prop_data in properties.items():
                if isinstance(prop_data, dict):
                    rows.append({
                        "Property": prop_name.replace("_", " ").title(),
                        "Value": prop_data.get("value", "—"),
                        "Confidence": prop_data.get("confidence", 0),
                        "Lower": prop_data.get("lower_bound", "—"),
                        "Upper": prop_data.get("upper_bound", "—"),
                    })
            if rows:
                prop_df = pd.DataFrame(rows)
                st.dataframe(
                    prop_df.style.format({
                        "Value": "{:.3f}",
                        "Confidence": "{:.1%}",
                        "Lower": "{:.3f}",
                        "Upper": "{:.3f}",
                    }).background_gradient(
                        subset=["Confidence"], cmap="RdYlGn", vmin=0, vmax=1
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    # Nearest known materials
    nearest = d.get("nearest_known", [])
    if nearest:
        st.subheader("Nearest Known Materials")
        st.markdown("These are the materials in our database closest to your composition (used for Kan extension).")
        import pandas as pd
        near_rows = []
        for n in nearest[:10]:
            if isinstance(n, dict):
                near_rows.append({
                    "Material": n.get("name", "?"),
                    "Distance": n.get("distance", 0),
                })
            elif isinstance(n, (list, tuple)) and len(n) >= 2:
                near_rows.append({
                    "Material": n[0],
                    "Distance": n[1],
                })
        if near_rows:
            near_df = pd.DataFrame(near_rows)
            st.dataframe(
                near_df.style.format({"Distance": "{:.4f}"}),
                use_container_width=True,
                hide_index=True,
            )

    # --- REPRODUCIBILITY BUNDLE EXPORT ---
    st.divider()
    import json
    import datetime
    
    bundle = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "software_version": "KOMPOSOS-IV-CHEM (Triage-Grade Predictor)",
        "prediction_audit": d
    }
    
    st.download_button(
        label="📥 Download Reproducibility Bundle (JSON)",
        data=json.dumps(bundle, indent=2),
        file_name=f"komposos_prediction_{d['formula']}.json",
        mime="application/json",
        help="Download an auditable JSON bundle containing the exact mathematical bounds, dataset anchors, and structural proofs used for this prediction."
    )

    # Structure prediction
    if hasattr(result, "predicted_structure") and result.predicted_structure:
        sp = result.predicted_structure
        st.subheader("Predicted Crystal Structure")
        st.write(f"- Type: **{sp.predicted_type}**")
        st.write(f"- Confidence: {sp.confidence:.1%}")
        if sp.goldschmidt_t is not None:
            st.write(f"- Goldschmidt tolerance factor: {sp.goldschmidt_t:.3f}")
        if sp.sources:
            src_parts = [f"{k}={v}" for k, v in sp.sources.items()]
            st.write(f"- Sources: {', '.join(src_parts)}")

    # Derived crystal structure (from Materials Project)
    ds = d.get("derived_structure")
    if ds:
        st.subheader("Derived Crystal Structure (Materials Project)")
        st.markdown(
            "Crystal structure parameters derived via **Kan extension** over nearest "
            "Materials Project entries. Every parameter traces back to specific MP structures."
        )

        col_cs, col_conf = st.columns([3, 1])
        with col_cs:
            sg_num = ds.get("space_group_number", "")
            sg_label = f'{ds["crystal_system"]} — {ds["space_group"]}'
            if sg_num:
                sg_label += f' (#{sg_num})'
            st.write(f"**Crystal system / Space group:** {sg_label}")
        with col_conf:
            st.metric("Confidence", f"{ds['confidence']:.1%}")

        # Lattice parameters table
        col_lat, col_vol = st.columns([3, 1])
        with col_lat:
            import pandas as pd
            lat_rows = [
                {"Parameter": "a", "Value": ds["lattice_a"], "Unit": "\u00c5"},
                {"Parameter": "b", "Value": ds["lattice_b"], "Unit": "\u00c5"},
                {"Parameter": "c", "Value": ds["lattice_c"], "Unit": "\u00c5"},
                {"Parameter": "\u03b1", "Value": ds["lattice_alpha"], "Unit": "\u00b0"},
                {"Parameter": "\u03b2", "Value": ds["lattice_beta"], "Unit": "\u00b0"},
                {"Parameter": "\u03b3", "Value": ds["lattice_gamma"], "Unit": "\u00b0"},
            ]
            lat_df = pd.DataFrame(lat_rows)
            st.dataframe(
                lat_df.style.format({"Value": "{:.4f}"}),
                use_container_width=True,
                hide_index=True,
            )
        with col_vol:
            st.metric("Volume/atom", f'{ds["volume_per_atom"]:.2f} \u00c5\u00b3')

        # Provenance (key differentiator)
        st.info(f'**Provenance:** {ds["provenance"]}')

        # Nearest MP entries
        mp_neighbours = ds.get("nearest_mp", [])
        if mp_neighbours:
            with st.expander(f"Nearest MP structures ({len(mp_neighbours)} entries)"):
                mp_rows = []
                for n in mp_neighbours:
                    mp_rows.append({
                        "MP ID": n["mp_id"],
                        "Formula": n["formula"],
                        "Distance": n["distance"],
                        "Weight": n["weight"],
                        "Crystal System": n["crystal_system"],
                        "Space Group": n["space_group"],
                    })
                mp_df = pd.DataFrame(mp_rows)
                st.dataframe(
                    mp_df.style.format({
                        "Distance": "{:.4f}",
                        "Weight": "{:.1%}",
                    }).background_gradient(
                        subset=["Weight"], cmap="YlGn", vmin=0, vmax=0.5,
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    # Formation energy / synthesizability
    props = d.get("properties", {})
    fe = props.get("formation_energy", {})
    synth = props.get("synthesizability", {})
    tier = d.get("uncertainty_tier", "Heuristic Estimate")

    if fe or synth:
        st.subheader("Stability & Synthesizability")
        
        # Uncertainty Tier Indicator
        tier_colors = {
            "Categorical Ground Truth": "green",
            "Dense Interpolation": "green",
            "Moderate Extrapolation": "orange",
            "Sparse Discovery": "red",
            "Heuristic Estimate": "red"
        }
        tier_color = tier_colors.get(tier, "blue")
        st.markdown(f"**Evidence Level:** :{tier_color}[{tier}]")
        
        col_fe, col_sy = st.columns(2)
        with col_fe:
            if isinstance(fe, dict) and fe.get("value") is not None:
                val = fe["value"]
                intervals = d.get("calibrated_intervals_eV") or {}
                err = intervals.get("80", d.get("error_estimate_eV", 0.15))
                if intervals:
                    help_text = (
                        "Phase 16 calibrated interval half-widths: "
                        f"50%={intervals.get('50', 0):.3f}, "
                        f"80%={intervals.get('80', 0):.3f}, "
                        f"95%={intervals.get('95', 0):.3f} eV/atom. "
                        f"Calibration: {d.get('calibration_status', 'unknown')}."
                    )
                else:
                    help_text = (
                        "Uncalibrated error estimate based on neighbor distance "
                        "and local estimator disagreement."
                    )
                st.metric("Formation Energy", f"{val:.3f} \u00b1 {err:.3f} eV/atom",
                          help=help_text)
                if val < 0:
                    st.success("Negative Ef: thermodynamically favorable")
                else:
                    st.warning("Positive Ef: may be metastable")
        with col_sy:
            if isinstance(synth, dict) and synth.get("value") is not None:
                val = synth["value"]
                st.metric("Synthesizability Score", f"{val:.2f}")
                if val >= 0.7:
                    st.success("High synthesizability")
                elif val >= 0.4:
                    st.info("Moderate synthesizability")
                else:
                    st.warning("Low synthesizability")

    # Raw data
    with st.expander("Raw prediction data"):
        st.json(d)

# ---------------------------------------------------------------------------
# Strict leave-one-out development diagnostic
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Strict Leave-One-Out Development Diagnostic")
st.markdown(
    "Verify the system's accuracy for yourself. This mode forces the engine to **forget** "
    "the selected material and same-formula anchors before predicting. This is a useful "
    "leave-one-out development diagnostic, **not a fresh blind test**: the reference set "
    "and model have already been inspected during development."
)

loo_formula = formula_input_with_autocomplete(
    label="Select known material to test",
    key="loo_formula",
    default_value="NMC811",
    help_text="Choose a known material for a leave-one-out development diagnostic."
)

if st.button("Run LOO Diagnostic", type="secondary"):
    if not require_access():
        st.stop()
    consume_use()
    
    try:
        # Run prediction EXCLUDING the formula itself
        with st.spinner(f"Predicting {loo_formula} without using its known data..."):
            from composition_engine.formation_energy import FormationEnergyPredictor, KNOWN_EF
            from composition_engine.parser import SHORTHAND_MAP
            res_blind = FormationEnergyPredictor(use_mp_cache=False).predict(
                loo_formula, exclude_formula=loo_formula
            )
            
        # Get ground truth
        resolved_loo = SHORTHAND_MAP.get(loo_formula, loo_formula)
        truth = next(
            (
                e for e in KNOWN_EF
                if e.name == loo_formula or e.formula == loo_formula or e.formula == resolved_loo
            ),
            None,
        )
        
        if truth:
            st.success(f"Self-excluded prediction for **{loo_formula}**")
            
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.metric("Predicted Ef", f"{res_blind.ef_per_atom:.3f} eV")
            with col_b2:
                st.metric("Ground Truth Ef", f"{truth.ef_per_atom:.3f} eV")
            with col_b3:
                err = abs(res_blind.ef_per_atom - truth.ef_per_atom)
                rel = (err / abs(truth.ef_per_atom)) if truth.ef_per_atom != 0 else 0
                st.metric("Relative LOO Error", f"{rel:.1%}")
                
            st.info(f"Uncertainty Tier: **{res_blind.uncertainty_tier.value}**")
            st.caption(
                "This measures self-excluded behavior on an already inspected development "
                "reference set. It is not a fresh blind or external generalization result."
            )
            
            with st.expander("Show nearest neighbors (self excluded)"):
                n_rows = [{"Neighbor": n, "Distance": d, "Known Ef": ef} 
                          for n, d, ef in res_blind.nearest_known]
                st.table(n_rows)
        else:
            st.warning(f"Material '{loo_formula}' not found in ground-truth database for comparison.")
            
    except Exception as e:
        st.error(f"Audit failed: {e}")

# ---------------------------------------------------------------------------
# Interpolation section
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Composition Interpolation")
st.markdown("Interpolate properties between two compositions.")

col_frac_container = st.container()

formula_a = formula_input_with_autocomplete(
    label="Formula A",
    key="interp_formula_a",
    default_value="LiCoO2",
    placeholder="e.g., LFP"
)

formula_b = formula_input_with_autocomplete(
    label="Formula B",
    key="interp_formula_b",
    default_value="LiNiO2",
    placeholder="e.g., NMC811"
)

with col_frac_container:
    fraction = st.slider("Fraction (0=A, 1=B)", 0.0, 1.0, 0.5, 0.05, key="interp_frac")

if st.button("Interpolate", key="interp_btn"):
    predictor = CompositionPredictor()
    try:
        with st.spinner("Interpolating..."):
            result = predictor.interpolate(formula_a, formula_b, fraction)
        d = result.to_dict()

        st.success(f"Interpolated formula: **{d['formula']}**")

        properties = d.get("properties", {})
        if properties:
            import pandas as pd
            rows = []
            for prop_name, prop_data in properties.items():
                if isinstance(prop_data, dict) and prop_data.get("value") is not None:
                    rows.append({
                        "Property": prop_name.replace("_", " ").title(),
                        "Value": prop_data["value"],
                        "Confidence": prop_data.get("confidence", 0),
                    })
            if rows:
                st.dataframe(
                    pd.DataFrame(rows).style.format({
                        "Value": "{:.3f}", "Confidence": "{:.1%}"
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

        with st.expander("Raw interpolation data"):
            st.json(d)

    except Exception as e:
        st.error(f"Error: {e}")
