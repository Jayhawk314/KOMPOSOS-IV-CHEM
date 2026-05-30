"""Crystal Dreamer — inverse composition design.

Give it target properties, it dreams candidate crystals.
"""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="Crystal Dreamer", page_icon="💎", layout="wide")
st.title("Crystal Dreamer")

render_login_sidebar()
from composition_engine.known_compositions import get_db as _get_db
_mat_count = _get_db().size
_has_mp = _get_db().has_mp_data
_scale = f"{_mat_count:,} materials" if _has_mp else "169 materials"
st.markdown(
    f"Describe the material you want — target properties, element constraints — "
    f"and the engine searches composition space for candidates that match. "
    f"Searching over **{_scale}** via Kan extension."
)
render_feature_status("crystal_dreamer")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from composition_engine.designer import (
    CompositionDesigner,
    DesignSpec,
    PropertyTarget,
    ElementConstraint,
    KNOWN_PROPERTIES,
)
from composition_engine.parser import ELEMENT_ORDER

# ---------------------------------------------------------------------------
# Property catalogue (user-friendly names and units)
# ---------------------------------------------------------------------------

_PROP_META = {
    "voltage": ("Voltage", "V"),
    "theoretical_capacity": ("Theoretical Capacity", "mAh/g"),
    "thermal_stability": ("Thermal Stability", "C"),
    "ionic_conductivity": ("Ionic Conductivity", "S/cm"),
    "density": ("Density", "g/cm3"),
    "volume_expansion": ("Volume Expansion", "%"),
    "formation_energy": ("Formation Energy", "eV/atom"),
    "synthesizability": ("Synthesizability", "0-1"),
    "band_gap": ("Band Gap", "eV"),
    "electron_mobility": ("Electron Mobility", "cm2/Vs"),
    "lattice_constant": ("Lattice Constant", "A"),
    "melting_point": ("Melting Point", "C"),
    "thermal_conductivity": ("Thermal Conductivity", "W/mK"),
    "hardness": ("Hardness", "GPa"),
    "fracture_toughness": ("Fracture Toughness", "MPa*m^0.5"),
    "cte": ("CTE", "ppm/K"),
    "youngs_modulus": ("Young's Modulus", "GPa"),
}

_PROP_NAMES = sorted(_PROP_META.keys())

# ---------------------------------------------------------------------------
# Target builder
# ---------------------------------------------------------------------------

st.subheader("Target Properties")
st.markdown("Add one or more target properties with min/max bounds.")

if "targets" not in st.session_state:
    st.session_state.targets = [{"name": "voltage", "min": 4.0, "max": None, "weight": 1.0}]


def _add_target():
    st.session_state.targets.append({"name": "voltage", "min": None, "max": None, "weight": 1.0})


def _remove_target(idx):
    if len(st.session_state.targets) > 1:
        st.session_state.targets.pop(idx)


for i, t in enumerate(st.session_state.targets):
    cols = st.columns([2, 1.5, 1.5, 1, 0.5])
    with cols[0]:
        prop_idx = _PROP_NAMES.index(t["name"]) if t["name"] in _PROP_NAMES else 0
        label, unit = _PROP_META.get(t["name"], (t["name"], ""))
        t["name"] = st.selectbox(
            "Property",
            _PROP_NAMES,
            index=prop_idx,
            format_func=lambda p: f"{_PROP_META.get(p, (p, ''))[0]} ({_PROP_META.get(p, (p, ''))[1]})",
            key=f"prop_{i}",
        )
    with cols[1]:
        t["min"] = st.number_input(
            "Min", value=t["min"], format="%.3f", key=f"min_{i}",
            help="Leave at 0 for no minimum",
        )
        if t["min"] == 0.0:
            t["min"] = None
    with cols[2]:
        t["max"] = st.number_input(
            "Max", value=t["max"] if t["max"] is not None else 0.0,
            format="%.3f", key=f"max_{i}",
            help="Leave at 0 for no maximum",
        )
        if t["max"] == 0.0:
            t["max"] = None
    with cols[3]:
        t["weight"] = st.slider(
            "Weight", 0.0, 1.0, t["weight"], 0.1, key=f"w_{i}",
        )
    with cols[4]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("X", key=f"rm_{i}", help="Remove this target"):
            _remove_target(i)
            st.rerun()

st.button("+ Add Target", on_click=_add_target)

# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Constraints")

col_elem, col_opts = st.columns(2)

with col_elem:
    # Element autocomplete with validation
    available_elements = sorted([e for e in ELEMENT_ORDER if e])

    required_elements = st.multiselect(
        "Required elements",
        options=available_elements,
        default=[],
        help="Elements that MUST be in the composition",
    )

    excluded_elements = st.multiselect(
        "Excluded elements",
        options=available_elements,
        default=[],
        help="Elements that MUST NOT be in the composition",
    )

    # Validation: check for overlap
    overlap = set(required_elements) & set(excluded_elements)
    if overlap:
        st.error(f"⚠️ Elements cannot be both required and excluded: {', '.join(sorted(overlap))}")
        st.stop()

with col_opts:
    domain = st.selectbox(
        "Restrict to domain",
        ["Any", "battery", "ceramic", "semiconductor"],
        index=0,
    )
    max_candidates = st.slider(
        "Max candidates to evaluate",
        min_value=20, max_value=2000, value=500, step=20,
        help="More = slower but more thorough",
    )
    min_synth = st.slider(
        "Min synthesizability",
        0.0, 1.0, 0.0, 0.1,
        help="Filter out compositions below this synthesizability score",
    )
    require_stable = st.checkbox(
        "Require thermodynamic stability (negative formation energy)",
        value=False,
    )

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

st.divider()

if st.button("Dream Crystals", type="primary"):
    if not require_access():
        st.stop()
    consume_use()
    # Build targets
    targets = []
    for t in st.session_state.targets:
        min_v = t["min"] if t["min"] is not None else None
        max_v = t["max"] if t["max"] is not None else None
        if min_v is None and max_v is None:
            st.warning(f"Target '{t['name']}' has no min or max — skipping.")
            continue
        targets.append(PropertyTarget(
            name=t["name"],
            min_value=min_v,
            max_value=max_v,
            weight=t["weight"],
        ))

    if not targets:
        st.error("Add at least one target with a min or max value.")
        st.stop()

    # Build element constraints (direct usage - no parsing needed)
    elem_constraint = None
    if required_elements or excluded_elements:
        elem_constraint = ElementConstraint(
            required_elements=required_elements if required_elements else None,
            excluded_elements=excluded_elements if excluded_elements else None,
        )

    spec = DesignSpec(
        targets=targets,
        element_constraints=elem_constraint,
        min_synthesizability=min_synth,
        require_stable=require_stable,
        domain=domain if domain != "Any" else None,
        max_candidates=max_candidates,
    )

    designer = CompositionDesigner()

    with st.spinner("Searching composition space..."):
        result = designer.design(spec)

    # ── Results ────────────────────────────────────────────────────────

    st.subheader(f"Results: {len(result.candidates)} candidates found")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidates", len(result.candidates))
    m2.metric("Evaluated", result.num_evaluated)
    m3.metric("Strategies", len(result.strategies_used))
    m4.metric("Time", f"{result.elapsed_seconds:.1f}s")

    if not result.candidates:
        st.warning(
            "No candidates found. Try relaxing constraints: lower min values, "
            "remove excluded elements, or increase max candidates."
        )
        st.stop()

    # Top candidates table
    import pandas as pd

    rows = []
    for c in result.candidates[:50]:
        row = {
            "Formula": c.formula,
            "Score": c.overall_score,
            "Confidence": c.confidence,
            "Synthesizability": c.synthesizability,
            "Strategy": c.strategy,
        }
        # Add target property values
        for t in targets:
            label = _PROP_META.get(t.name, (t.name, ""))[0]
            row[label] = c.predicted_properties.get(t.name, None)
        # Structure type
        if c.structure_type:
            row["Structure"] = c.structure_type
        rows.append(row)

    df = pd.DataFrame(rows)

    # Style: gradient on Score and Confidence columns
    style_cols = ["Score", "Confidence", "Synthesizability"]
    format_dict = {"Score": "{:.3f}", "Confidence": "{:.1%}", "Synthesizability": "{:.2f}"}
    for t in targets:
        label = _PROP_META.get(t.name, (t.name, ""))[0]
        format_dict[label] = "{:.3f}"

    styled = df.style.format(format_dict, na_rep="—")
    for col in style_cols:
        if col in df.columns:
            styled = styled.background_gradient(
                subset=[col], cmap="RdYlGn", vmin=0, vmax=1
            )

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Bar chart: top 20 scores
    st.subheader("Top Candidates by Score")
    chart_df = pd.DataFrame({
        "Formula": [c.formula for c in result.candidates[:20]],
        "Score": [c.overall_score for c in result.candidates[:20]],
    }).set_index("Formula")
    st.bar_chart(chart_df, horizontal=True)

    # Detailed view of top candidate
    best = result.candidates[0]
    st.subheader(f"Top Pick: {best.formula}")

    col_detail, col_targets = st.columns(2)

    with col_detail:
        st.markdown("**Composition**")
        comp_df = pd.DataFrame({
            "Element": list(best.composition.keys()),
            "Amount": list(best.composition.values()),
        })
        st.dataframe(
            comp_df.style.format({"Amount": "{:.3f}"}),
            use_container_width=True,
            hide_index=True,
        )

        if best.structure_type:
            st.info(f"Predicted structure: **{best.structure_type}**")
        if best.formation_energy is not None:
            if best.formation_energy < 0:
                st.success(f"Formation energy: {best.formation_energy:.3f} eV/atom (stable)")
            else:
                st.warning(f"Formation energy: {best.formation_energy:.3f} eV/atom (metastable)")

    with col_targets:
        st.markdown("**Target Scores**")
        target_rows = []
        for t in targets:
            label = _PROP_META.get(t.name, (t.name, ""))[0]
            score = best.target_scores.get(t.name, 0)
            met = t.name in best.targets_met
            value = best.predicted_properties.get(t.name, None)
            target_rows.append({
                "Property": label,
                "Value": value if value is not None else "—",
                "Target Score": score,
                "Met": "Yes" if met else "No",
            })
        target_df = pd.DataFrame(target_rows)
        st.dataframe(
            target_df.style.format({
                "Value": "{:.3f}",
                "Target Score": "{:.3f}",
            }, na_rep="—").background_gradient(
                subset=["Target Score"], cmap="RdYlGn", vmin=0, vmax=1
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(f"**Strategy:** {best.strategy} | **Anchor:** {best.anchor or '—'}")

    # Derived crystal structure for top pick (single predict call, ~1ms cached)
    try:
        from composition_engine.predictor import CompositionPredictor
        _pred = CompositionPredictor()
        _top_result = _pred.predict(best.formula)
        if _top_result.derived_structure:
            ds = _top_result.derived_structure.to_dict()
            st.subheader("Derived Crystal Structure")
            st.markdown(
                f"Structure derived from nearest Materials Project entries "
                f"via Kan extension (confidence {ds['confidence']:.0%})."
            )
            col_sg, col_lat = st.columns(2)
            with col_sg:
                sg_num = ds.get("space_group_number", "")
                st.write(f"**Crystal system:** {ds['crystal_system']}")
                st.write(f"**Space group:** {ds['space_group']} (#{sg_num})")
                st.write(f"**Volume/atom:** {ds['volume_per_atom']:.2f} \u00c5\u00b3")
            with col_lat:
                st.write(f"**a** = {ds['lattice_a']:.4f} \u00c5 &nbsp; "
                         f"**b** = {ds['lattice_b']:.4f} \u00c5 &nbsp; "
                         f"**c** = {ds['lattice_c']:.4f} \u00c5")
                st.write(f"**\u03b1** = {ds['lattice_alpha']:.2f}\u00b0 &nbsp; "
                         f"**\u03b2** = {ds['lattice_beta']:.2f}\u00b0 &nbsp; "
                         f"**\u03b3** = {ds['lattice_gamma']:.2f}\u00b0")
            st.info(f"**Provenance:** {ds['provenance']}")
    except Exception:
        pass

    # Strategy distribution
    st.subheader("Strategy Distribution")
    strategy_counts = {}
    for c in result.candidates:
        strategy_counts[c.strategy] = strategy_counts.get(c.strategy, 0) + 1
    strat_df = pd.DataFrame({
        "Strategy": list(strategy_counts.keys()),
        "Candidates": list(strategy_counts.values()),
    }).set_index("Strategy")
    st.bar_chart(strat_df)

    # Raw data
    with st.expander("Raw result data"):
        st.json(result.to_dict())
