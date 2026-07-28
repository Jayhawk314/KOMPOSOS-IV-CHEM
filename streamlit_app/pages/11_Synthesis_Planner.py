# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Synthesis Planner — ranked literature routes with Z3 stoichiometric validation."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.validation_status import render_feature_status

st.set_page_config(page_title="Synthesis Planner", page_icon="⚗️", layout="wide")
st.title("Synthesis Planner")

render_login_sidebar()
st.markdown(
    "Pick a target material and get **ranked literature synthesis routes** "
    "(feasibility, cost, time, safety) — each one **stoichiometrically "
    "checked by a Z3 SMT solver**: checked routes show a formal element-"
    "balance witness; encodings with no balance witness are hard-vetoed. "
    "This does not prove reaction mechanism, redox, yield, or phase purity."
)
render_feature_status("synthesis_planner")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from synthesis_planner.route_graph import list_all_targets
from synthesis_planner.route_planner import SynthesisPlanner

_STOICH_BADGE = {
    "BALANCED": ("✅ Balanced", "green"),
    "BALANCED_UNUSED_INPUTS": ("✅ Balanced (unused inputs)", "orange"),
    "UNBALANCED": ("⛔ UNBALANCED — vetoed", "red"),
    "SKIPPED": ("◻️ Balance N/A (composite/mixture)", "gray"),
    "UNAVAILABLE": ("◻️ Not checked (z3 unavailable)", "gray"),
}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

targets = list_all_targets()
target = st.selectbox("Target material", targets,
                      index=targets.index("LFP") if "LFP" in targets else 0)

if st.button("Plan synthesis", type="primary"):
    if not require_access():
        st.stop()
    consume_use()

    with st.spinner("Scoring routes + running Z3 stoichiometric validation..."):
        analysis = SynthesisPlanner().plan_synthesis(target)

    if not analysis.routes:
        st.error(f"No synthesis routes found for target: {target}")
        st.stop()

    for w in analysis.warnings:
        st.warning(w)

    c1, c2, c3 = st.columns(3)
    c1.metric("Routes found", len(analysis.routes))
    c2.metric("Best-route precursor cost", f"${analysis.precursor_cost_usd:,.2f}")
    c3.metric("Best-route total time", f"{analysis.total_time_hours:.1f} h")

    for i, sr in enumerate(analysis.routes):
        label, color = _STOICH_BADGE.get(sr.stoichiometry_status,
                                         (sr.stoichiometry_status, "gray"))
        crown = "👑 " if sr is analysis.best_route else ""
        with st.expander(
            f"{crown}{sr.route.name} — composite {sr.composite_score:.3f} — {label}",
            expanded=(i == 0),
        ):
            if sr.stoichiometry_status == "UNBALANCED":
                st.error("Stoichiometric hard veto: no element-balanced "
                         "equation exists for this route as written.")
            if sr.balanced_reaction:
                st.markdown("**Formal element-balance witness (Z3):**")
                st.code(sr.balanced_reaction, language=None)
                st.caption(
                    "This witness proves only that atoms can be conserved using the solver's "
                    "allowed auxiliary species. It is not the cited paper's reaction equation "
                    "and does not establish redox plausibility, mechanism, yield, or phase purity."
                )
            for note in sr.stoichiometry_notes:
                st.caption(f"⚠️ {note}")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Feasibility", f"{sr.feasibility_score:.2f}")
            s2.metric("Cost", f"{sr.cost_score:.2f}")
            s3.metric("Time", f"{sr.time_score:.2f}")
            s4.metric("Safety", f"{sr.safety_score:.2f}")

            if sr.missing_precursors:
                st.caption(f"Missing precursors: {', '.join(sr.missing_precursors)}")
            if sr.bottleneck_step is not None:
                bn = sr.bottleneck_step
                st.caption(f"Bottleneck step: {bn.operation} "
                           f"(p={bn.success_probability:.2f})")

            st.markdown("**Steps**")
            rows = []
            for n, step in enumerate(sr.route.steps, 1):
                rows.append({
                    "#": n,
                    "operation": step.operation,
                    "inputs": ", ".join(step.inputs),
                    "output": step.output,
                    "T (°C)": step.conditions.temperature_C,
                    "time (h)": step.conditions.time_hours,
                    "atmosphere": step.conditions.atmosphere,
                    "equipment": step.conditions.equipment,
                    "p(success)": step.success_probability,
                    "hazards": ", ".join(step.hazards),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
            if sr.route.citation:
                st.caption(f"Citation: {sr.route.citation}")
