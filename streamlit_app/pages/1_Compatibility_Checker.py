"""Material Compatibility Checker - check if two materials are compatible."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import json
import streamlit as st
from utils.molecule_autocomplete import molecule_selector, show_molecule_reference
from oracle.compatibility_service import run_compatibility_workflow
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.md_controls import render_md_input_controls, render_md_result
from streamlit_app.validation_status import render_feature_status
from reports.compatibility_report import (
    build_compatibility_report,
    render_markdown,
    report_to_dict,
)

st.set_page_config(page_title="Compatibility Checker", page_icon="chem", layout="wide")
st.title("Material Compatibility Checker")
st.markdown("Select two materials from the same domain to check compatibility.")
render_feature_status("compatibility")

render_login_sidebar()

DOMAIN_IMPORTS = {
    "battery": ("battery_bridge.material_properties", "ALL_MATERIALS"),
    "polymer": ("polymer_bridge.material_properties", "ALL_POLYMERS"),
    "metal": ("metal_bridge.material_properties", "ALL_METALS"),
    "ceramic": ("ceramic_bridge.material_properties", "ALL_CERAMICS"),
    "semiconductor": ("semiconductor_bridge.material_properties", "ALL_SEMICONDUCTORS"),
    "glass": ("glass_bridge.material_properties", "ALL_GLASSES"),
}


@st.cache_data
def get_all_materials():
    """Load all materials grouped by domain."""
    import importlib

    result = {}
    for domain, (mod_path, attr) in DOMAIN_IMPORTS.items():
        mod = importlib.import_module(mod_path)
        materials = getattr(mod, attr)
        result[domain] = sorted(materials.keys())

    return result


def extract_component_scores(scores, md_results=None):
    """Extract flat numeric scorer values for visualization."""
    component_scores = {
        key: value
        for key, value in scores.items()
        if key not in {
            "total", "viable", "context", "typed_morphism", "typed_morphism_adjustment",
            "calibration", "ensemble", "zfc"
        }
        and isinstance(value, (int, float))
    }
    if md_results and md_results.get("constraint_scores"):
        component_scores.update(md_results["constraint_scores"])
    return component_scores


all_materials = get_all_materials()

col1, col2 = st.columns(2)

with col1:
    domain = st.selectbox(
        "Domain",
        list(all_materials.keys()),
        format_func=lambda d: f"{d.title()} ({len(all_materials[d])} materials)",
    )

materials = all_materials[domain]

with col1:
    mat_a = st.selectbox("Material A", materials, index=0)

with col2:
    default_b = min(1, len(materials) - 1)
    mat_b = st.selectbox("Material B", materials, index=default_b)

st.markdown("---")
col_md, col_help = st.columns([1, 3])
with col_md:
    md_verify = st.checkbox(
        "Trigger Active Verification (MD)",
        help="Orchestrate a high-fidelity Molecular Dynamics simulation (GROMACS) for this interface.",
    )
with col_help:
    if md_verify:
        st.info(
            "Active Verification runs GROMACS only when a real structure/topology bundle "
            "is available. Missing inputs return a no-verdict readiness report."
        )

md_conditions = {}
if md_verify:
    with st.expander("GROMACS input bundle", expanded=True):
        md_conditions = render_md_input_controls("compat_md")

if mat_a == mat_b:
    st.warning("Select two different materials.")
else:
    if st.button("Check Compatibility", type="primary"):
        if not require_access():
            st.stop()
        consume_use()

        with st.spinner("Running shared compatibility workflow..."):
            workflow = run_compatibility_workflow(
                mat_a,
                mat_b,
                md_verify=md_verify,
                md_conditions=md_conditions,
            )

        scores = workflow.scores
        md_results = workflow.md_results
        total = scores.get("total", 0.0)
        cat_says = bool(workflow.viable)
        zfc = scores.get("zfc", {})
        zfc_available = bool(zfc.get("available"))
        zfc_says = bool(zfc.get("interface_viable")) if zfc_available else False
        component_scores = extract_component_scores(scores, md_results)

        if cat_says and zfc_says:
            delta_type = "AGREE"
        elif cat_says and zfc_available and not zfc_says:
            delta_type = "HOLLOW"
        elif not cat_says and zfc_says:
            delta_type = "ORPHAN"
        else:
            delta_type = "REJECT"

        st.subheader("Dual-Engine Verdict")

        col_cat, col_zfc = st.columns(2)
        with col_cat:
            st.markdown("**System 2: Categorical Oracle**")
            if cat_says:
                st.success(f"Morphism EXISTS (score {total:.3f})")
                st.caption("The compositional structure admits a path between these materials.")
            else:
                st.error(f"Morphism BLOCKED (score {total:.3f})")
                st.caption("Weighted scorer composition falls below viability threshold.")

        with col_zfc:
            st.markdown("**System 1: ZFC Logic Oracle**")
            if not zfc_available:
                st.info("ZFC summary unavailable for this environment.")
            elif zfc_says:
                st.success(
                    f"Witness FOUND ({len(zfc.get('compatible_constraints', []))}/"
                    f"{zfc.get('num_constraints', 0)} constraints pass)"
                )
                st.caption("No constraint vetoes detected in the current rule set.")
            else:
                veto_names = ", ".join(
                    v.replace("_", " ").title() for v in zfc.get("veto_constraints", [])
                ) or "no viable witness"
                st.error(
                    f"Witness EMPTY ({len(zfc.get('veto_constraints', []))} veto(s): {veto_names})"
                )
                st.caption("Hard constraint veto or failed viability witness in the ZFC layer.")

        if md_results:
            render_md_result(md_results)

        calibration = scores.get("calibration", {})
        if calibration:
            _cal_prob = calibration.get("calibrated_probability", total)
            _calibrator = calibration.get("calibrator", "unknown")
            _oos_ece = calibration.get("oos_ece")
            if _calibrator == "isotonic_global" and _oos_ece is not None:
                st.caption(
                    f"**Calibrated probability of compatibility: {_cal_prob:.0%}** "
                    f"(isotonic calibration, held-out ECE {_oos_ece:.3f}). "
                    "This is now a real probability — a 70% here means roughly 7 in 10 "
                    "such pairs are compatible — not just a ranking signal."
                )
            else:
                st.caption(
                    "Calibrated compatibility score: "
                    f"{_cal_prob:.3f} via {_calibrator} "
                    "— a ranking signal; calibration artifact unavailable, treat as approximate."
                )

        ensemble = scores.get("ensemble", {})

        # ── Evidence fusion (Dempster-Shafer) uncertainty interval ──────────
        ds = (
            ensemble.get("path_features", {}).get("dempster_shafer", {})
            if isinstance(ensemble, dict) else {}
        )
        if ds:
            st.markdown("**Evidence Fusion (Dempster–Shafer)**")
            d1, d2, d3 = st.columns(3)
            d1.metric(
                "Belief (viable)", f"{ds.get('belief_viable', 0.0):.2f}",
                help="Lower bound — mass that positively supports compatibility.",
            )
            d2.metric(
                "Plausibility (viable)", f"{ds.get('plausibility_viable', 0.0):.2f}",
                help="Upper bound — belief plus unresolved (ignorance) mass.",
            )
            d3.metric(
                "Ignorance band", f"{ds.get('uncertainty', 0.0):.2f}",
                help="Plausibility − Belief. A wide band means thin/uncommitted evidence.",
            )
            conflict = float(ds.get("max_conflict", 0.0))
            if conflict >= 0.4:
                st.warning(
                    f"Evidence conflict {conflict:.2f}: the reasoning strategies disagree "
                    "(e.g. categorical vs. physics). Treat this verdict as **contested** — "
                    "inspect the votes below before relying on it."
                )
            else:
                st.caption(
                    f"True compatibility lies in [{ds.get('belief_viable', 0.0):.2f}, "
                    f"{ds.get('plausibility_viable', 0.0):.2f}]; evidence conflict {conflict:.2f} "
                    f"across {ds.get('num_sources', 0)} sources (low = sources agree)."
                )

        gray = ensemble.get("gray_coherence", {}) if isinstance(ensemble, dict) else {}
        if gray.get("checked"):
            if gray.get("coherent", True):
                st.info(
                    f"Gray coherence checked {gray.get('pairs_checked', 0)} contradictory strategy path pair(s); "
                    "no active 3-cell gap guard fired."
                )
            else:
                st.warning(
                    f"Gray coherence found {gray.get('gap_count', 0)} contradictory 3-cell gap(s); "
                    f"max severity {gray.get('max_gap_severity', 0.0):.3f}."
                )

        if delta_type == "AGREE":
            st.success(
                f"**AGREE** - The categorical score passes for **{mat_a} + {mat_b}** and "
                "the ZFC constraint verifier finds no veto."
            )
        elif delta_type == "HOLLOW":
            st.warning(
                f"**HOLLOW STATE** - The categorical oracle finds a compositional path "
                f"(score {total:.3f}), but the ZFC constraint verifier rejects the pair."
            )
            with st.expander("Why this matters"):
                st.markdown(
                    "A **HOLLOW** state means the structural pattern looks viable, but the logical "
                    "constraint layer does not admit the interface as currently grounded.\n\n"
                    f"**Veto constraint(s):** {', '.join(zfc.get('veto_constraints', [])) or 'none recorded'}"
                )
        elif delta_type == "ORPHAN":
            st.info(
                f"**ORPHAN** - The ZFC verifier finds no hard veto, but the categorical scorer "
                f"composite falls below threshold (score {total:.3f})."
            )
        else:
            st.error(
                f"**REJECT** - Both engines reject **{mat_a} + {mat_b}**. "
                "The categorical morphism does not compose and the logical layer does not validate it."
            )

        st.subheader("Score Breakdown")
        if component_scores:
            import pandas as pd

            df = pd.DataFrame({
                "Scorer": [k.replace("_", " ").title() for k in component_scores.keys()],
                "Score": list(component_scores.values()),
            }).set_index("Scorer")

            col_chart, col_table = st.columns([2, 1])
            with col_chart:
                st.bar_chart(df, horizontal=True)
            with col_table:
                st.dataframe(
                    df.style.format("{:.3f}").background_gradient(cmap="RdYlGn", vmin=0, vmax=1),
                    use_container_width=True,
                )

            # ── Audit Report download ──────────────────────────────────────
            try:
                _report = build_compatibility_report(
                    mat_a=mat_a, mat_b=mat_b, domain=workflow.domain,
                    scores=scores, viable=workflow.viable,
                )
                _report_md   = render_markdown(_report)
                _report_json = json.dumps(report_to_dict(_report), indent=2, default=str)
                _fname_stem  = f"compat_{mat_a}_{mat_b}_{workflow.domain}".replace(" ", "_")

                st.markdown("#### Audit Report")
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    st.download_button(
                        label="Download Report (Markdown)",
                        data=_report_md,
                        file_name=f"{_fname_stem}.md",
                        mime="text/markdown",
                        help="Human-readable report with chemistry narrative + mathematical backing",
                    )
                with dl_col2:
                    st.download_button(
                        label="Download Audit Trail (JSON)",
                        data=_report_json,
                        file_name=f"{_fname_stem}.json",
                        mime="application/json",
                        help="Full machine-readable audit trail for programmatic verification",
                    )
                st.caption(f"Report ID: `{_report.report_id}`")
            except Exception as _rpt_err:
                st.caption(f"Report generation unavailable: {_rpt_err}")

            st.divider()

            ensemble = scores.get("ensemble", {})
            if ensemble and ensemble.get("votes"):
                with st.expander("Ensemble Votes & Categorical Evidence Chain", expanded=True):
                    import pandas as pd

                    # ── Evidence quality summary ───────────────────────────
                    _EQ_LABEL = {
                        "formal":               "✓ Formal proof",
                        "formal_with_neighbor": "✓ Formal proof",
                        "structural":           "~ Structural",
                        "none":                 "✗ No category",
                    }
                    _EQ_COLOR = {
                        "formal":               "green",
                        "formal_with_neighbor": "green",
                        "structural":           "orange",
                        "none":                 "gray",
                    }

                    n_formal     = sum(
                        1 for v in ensemble["votes"]
                        if v.get("metadata", {}).get("evidence_quality", "").startswith("formal")
                    )
                    n_structural = sum(
                        1 for v in ensemble["votes"]
                        if v.get("metadata", {}).get("evidence_quality") == "structural"
                    )
                    n_none = sum(
                        1 for v in ensemble["votes"]
                        if v.get("metadata", {}).get("evidence_quality") == "none"
                        or "evidence_quality" not in v.get("metadata", {})
                    )
                    total_votes = len(ensemble["votes"])

                    eq_col1, eq_col2, eq_col3, eq_col4 = st.columns(4)
                    eq_col1.metric("Total votes", total_votes)
                    eq_col2.metric("Formal proof", n_formal,
                                   help="Votes backed by formal Yoneda/categorical evidence")
                    eq_col3.metric("Structural only", n_structural,
                                   help="Votes with structural comparison but no formal proof")
                    eq_col4.metric("No category", n_none,
                                   help="Neutral fallback — domain category unavailable")

                    st.caption(
                        f"Evidence coverage: "
                        f"{n_formal}/{total_votes} votes carry formal mathematical proof chains."
                    )
                    st.divider()

                    # ── Vote summary table ─────────────────────────────────
                    vote_rows = []
                    for vote in ensemble["votes"]:
                        eq = vote.get("metadata", {}).get("evidence_quality", "")
                        vote_rows.append({
                            "Strategy":   vote["strategy"].replace("_", " ").title(),
                            "Score":      vote["score"],
                            "Confidence": vote["confidence"],
                            "Verdict":    "PASS" if vote["compatible"] else "FAIL",
                            "Evidence":   _EQ_LABEL.get(eq, eq or "—"),
                            "Reasoning":  vote["reason"],
                        })
                    vote_df = pd.DataFrame(vote_rows)
                    st.dataframe(
                        vote_df.style.format({"Score": "{:.3f}", "Confidence": "{:.3f}"}),
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.divider()

                    # ── Categorical evidence chains ────────────────────────
                    st.markdown("#### Categorical Evidence Chains")
                    st.caption(
                        "Chemistry interpretation first — mathematical backing in italics below each entry. "
                        "Download the Markdown report above for the full version."
                    )

                    # Pull domain-aware labels from the report module
                    from reports.compatibility_report import (
                        _strategy_label as _slabel,
                        _chemistry_narrative as _cnar,
                        _nar,
                    )
                    _domain = workflow.domain

                    def _format_fp_lines(fp):
                        if not fp:
                            return "Empty fingerprint"
                        return "\n".join(f"  ({t}, {r})" for t, r in fp)

                    for vote in ensemble["votes"]:
                        meta = vote.get("metadata", {})
                        eq   = meta.get("evidence_quality", "")
                        strategy = vote["strategy"]

                        # ── Simplicial Yoneda ──────────────────────────────
                        if strategy == "simplicial_yoneda":
                            yp = meta.get("yoneda_proof")
                            _chem_label = _slabel(strategy, _domain)
                            with st.expander(
                                f"**{_chem_label}** — score {vote['score']:.3f}  "
                                f"| {_EQ_LABEL.get(eq, eq or '—')}",
                                expanded=bool(yp),
                            ):
                                if yp:
                                    # Chemistry narrative first
                                    _narr = _cnar(vote, _domain, mat_a, mat_b)
                                    if _narr:
                                        st.info(_narr)
                                    st.markdown(
                                        f"**Formal proof** *(Yoneda sieve distance — "
                                        f"measures how different {mat_a} and {mat_b} are "
                                        f"in terms of what {_nar(_domain, 'objects')} "
                                        f"they can interface with)*"
                                    )
                                    for step in yp.get("proof_steps", []):
                                        st.markdown(f"&nbsp;&nbsp;{step}")

                                    if yp.get("shared_sources"):
                                        st.markdown(
                                            f"**{_nar(_domain, 'shared_partners').title()}** — "
                                            f"{len(yp['shared_sources'])} {_nar(_domain, 'objects')} "
                                            f"that can interface with both {mat_a} and {mat_b}"
                                        )
                                        ss_df = pd.DataFrame(yp["shared_sources"]).rename(columns={
                                            "source":    "Material",
                                            "conf_to_a": f"Conf→{mat_a}",
                                            "conf_to_b": f"Conf→{mat_b}",
                                        })
                                        st.dataframe(
                                            ss_df.style.format({
                                                f"Conf→{mat_a}": "{:.4f}",
                                                f"Conf→{mat_b}": "{:.4f}",
                                            }),
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                    else:
                                        st.info(
                                            f"No shared sources: {mat_a} and {mat_b} have "
                                            "disjoint incoming morphism sets."
                                        )

                                    iso = yp.get("is_isomorphic", False)
                                    if iso:
                                        st.success(
                                            f"**Isomorphic** — "
                                            f"d(y(A),y(B)) = {yp['sieve_distance']:.4f}; "
                                            f"A ≅ B (Yoneda fully faithful)"
                                        )
                                    else:
                                        st.info(
                                            f"Yoneda distance d = {yp['sieve_distance']:.4f}  |  "
                                            f"Overlap = {yp['presheaf_overlap']:.4f}  |  "
                                            f"Max transfer threshold = {yp['max_transfer_threshold']:.4f}"
                                        )

                                    if meta.get("fingerprint_a") and meta.get("neighbor"):
                                        st.markdown(
                                            f"**Neighbour comparison** "
                                            f"(similarity {meta.get('similarity', 0):.4f} "
                                            f"to {meta['neighbor']})"
                                        )
                                        fp_a_set = set(tuple(x) for x in meta["fingerprint_a"])
                                        fp_n_set = set(tuple(x) for x in meta["fingerprint_n"])
                                        overlap  = fp_a_set & fp_n_set
                                        if overlap:
                                            st.success(
                                                f"{len(overlap)} shared morphism relations "
                                                f"between {mat_a} and {meta['neighbor']}"
                                            )
                                            with st.expander("Show shared relations"):
                                                st.code(
                                                    _format_fp_lines(list(overlap)),
                                                    language="text",
                                                )
                                else:
                                    st.info(vote["reason"])

                        # ── Fibration Transport ────────────────────────────
                        elif strategy == "fibration_transport":
                            paths = meta.get("transport_paths", [])
                            _chem_label = _slabel(strategy, _domain)
                            with st.expander(
                                f"**{_chem_label}** — score {vote['score']:.3f}  "
                                f"| {_EQ_LABEL.get(eq, eq or '—')}",
                                expanded=bool(paths),
                            ):
                                _narr = _cnar(vote, _domain, mat_a, mat_b)
                                if _narr:
                                    st.info(_narr)
                                if paths:
                                    st.markdown(
                                        f"**{len(paths)} transport route(s)** — "
                                        f"{_nar(_domain, 'transport_via')}"
                                    )
                                    path_rows = []
                                    for p in paths:
                                        path_rows.append({
                                            "Via material":       p["via"],
                                            "Transport strength": p["strength"],
                                            "Shared properties":  len(p.get("shared_properties", [])),
                                            "Reasoning":          p.get("reasoning", ""),
                                        })
                                    path_df = pd.DataFrame(path_rows)
                                    st.dataframe(
                                        path_df.style.format({"Transport strength": "{:.4f}"}),
                                        use_container_width=True,
                                        hide_index=True,
                                    )
                                    st.caption(
                                        f"Total transport strength: "
                                        f"{meta.get('total_strength', 0):.4f}  "
                                        f"(sum of per-path Jaccard property similarities)"
                                    )
                                    with st.expander("Shared properties per path"):
                                        for p in paths:
                                            props = p.get("shared_properties", [])
                                            if props:
                                                st.markdown(f"**{p['via']}** ({len(props)} props)")
                                                st.code("\n".join(f"  {pr}" for pr in props),
                                                        language="text")
                                else:
                                    st.info(vote["reason"])

                        # ── Rezk Equivalence ──────────────────────────────
                        elif strategy == "rezk_equivalence":
                            witness = meta.get("isomorphism_witness")
                            _chem_label = _slabel(strategy, _domain)
                            with st.expander(
                                f"**{_chem_label}** — score {vote['score']:.3f}  "
                                f"| {_EQ_LABEL.get(eq, eq or '—')}",
                                expanded=bool(witness),
                            ):
                                _narr = _cnar(vote, _domain, mat_a, mat_b)
                                if _narr:
                                    st.info(_narr)
                                if witness:
                                    eq_mat = witness.get("equivalent", "")
                                    st.success(
                                        f"**{_nar(_domain, 'interchangeable').title()} found**: "
                                        f"{mat_a} ≅ {eq_mat}"
                                    )
                                    st.markdown(
                                        f"**Logic chain** *(substitution principle: "
                                        f"if A has the same {_nar(_domain, 'profile')} as A', "
                                        f"then A can substitute for A' in any interface)*:"
                                    )
                                    st.markdown(witness.get("logic", ""))

                                    shared_rels = witness.get("shared_relations", [])
                                    if shared_rels:
                                        st.markdown(
                                            f"**Presheaf isomorphism evidence** — "
                                            f"{len(shared_rels)} shared relations "
                                            f"prove Hom(−,{mat_a}) = Hom(−,{eq_mat})"
                                        )
                                        st.code(
                                            "\n".join(
                                                f"  ({r[0]}, {r[1]})" if len(r) == 2 else f"  {r}"
                                                for r in shared_rels[:20]
                                            )
                                            + ("\n  ..." if len(shared_rels) > 20 else ""),
                                            language="text",
                                        )

                                    transport_m = witness.get("transport_morphisms", [])
                                    if transport_m:
                                        st.markdown(
                                            f"**Transport morphisms** — "
                                            f"{eq_mat} → {mat_b} "
                                            f"({len(transport_m)} morphism(s))"
                                        )
                                        tm_df = pd.DataFrame(transport_m)
                                        st.dataframe(
                                            tm_df.style.format({"confidence": "{:.4f}"}),
                                            use_container_width=True,
                                            hide_index=True,
                                        )
                                elif meta.get("equivalents_found", 0) > 0:
                                    st.info(
                                        f"{meta['equivalents_found']} equivalent(s) found for "
                                        f"{mat_a}, but none are compatible with {mat_b}."
                                    )
                                else:
                                    st.info(vote["reason"])

            with st.expander("Raw score data"):
                st.json(scores)
                if md_results:
                    st.json({"md_results": md_results})

st.divider()
st.subheader("Molecule Constraint Search")
st.markdown(
    "KOMPOSOS doesn't generate text - it searches real molecular data with "
    "**exact** constraint satisfaction. Enter a target heavy atom count below."
)

from molecular_bridge.constraint_search import (
    search_by_constraints,
    get_heavy_atom_count,
    get_atom_count_distribution,
)
from molecular_bridge.molecule_properties import MoleculeClass

col_atom, col_class, col_elem = st.columns(3)

with col_atom:
    target_count = st.number_input(
        "Exact heavy atom count",
        min_value=0, max_value=100, value=22,
        help="Non-hydrogen atoms. The famous Kulik challenge uses 22.",
        key="kulik_count",
    )
with col_class:
    class_filter = st.selectbox(
        "Molecule class (optional)",
        ["Any"] + [mc.value for mc in MoleculeClass],
        key="kulik_class",
    )
with col_elem:
    exclude_str = st.text_input(
        "Exclude elements (comma-separated)",
        value="",
        help="e.g. 'F,Cl' to exclude fluorine and chlorine",
        key="kulik_exclude",
    )

if st.button("Search Molecules", type="primary", key="kulik_search"):
    kwargs = {"heavy_atom_count": target_count}
    if class_filter != "Any":
        kwargs["molecule_class"] = MoleculeClass(class_filter)
    if exclude_str.strip():
        kwargs["exclude_elements"] = [e.strip() for e in exclude_str.split(",") if e.strip()]

    results = search_by_constraints(**kwargs)

    if results:
        st.success(f"Found **{len(results)}** molecule(s) with exactly **{target_count}** heavy atoms")
        import pandas as pd
        rows = []
        for mol in results:
            rows.append({
                "Name": mol.name,
                "Formula": mol.formula,
                "MW (g/mol)": mol.molecular_weight,
                "Heavy Atoms": get_heavy_atom_count(mol),
                "Class": mol.molecule_class.value,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info(
            f"No molecules with exactly **{target_count}** heavy atoms in the database. "
            "**This is the correct answer** - not a hallucination. "
            "KOMPOSOS never fabricates molecules."
        )

    with st.expander("Heavy atom count distribution (all 37 molecules)"):
        dist = get_atom_count_distribution()
        import pandas as pd
        rows = []
        for count, names in dist.items():
            rows.append({"Heavy Atoms": count, "Count": len(names), "Molecules": ", ".join(names)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Quick Molecule Selection")
st.caption("Select a molecule directly to view details, or use constraint search above for advanced filtering")

selected_molecule = molecule_selector(
    label="Choose molecule",
    key="quick_molecule_select",
    help_text="Select from 37 available molecules"
)

if selected_molecule:
    from molecular_bridge.molecule_properties import ALL_MOLECULES
    mol = ALL_MOLECULES[selected_molecule]

    st.success(f"Selected: **{selected_molecule}** ({mol.name})")

    col_details, col_props = st.columns([1, 1])

    with col_details:
        st.markdown("**Molecule Details:**")
        st.markdown(f"- **Formula:** {mol.formula}")
        st.markdown(f"- **CAS Number:** {mol.cas_number}")
        st.markdown(f"- **PubChem CID:** {mol.pubchem_cid if mol.pubchem_cid else 'N/A'}")
        st.markdown(f"- **SMILES:** `{mol.smiles}`")
        st.markdown(f"- **Class:** {mol.molecule_class.value if hasattr(mol.molecule_class, 'value') else str(mol.molecule_class)}")

    with col_props:
        st.markdown("**Physical Properties:**")
        st.markdown(f"- **Molecular Weight:** {mol.molecular_weight:.2f} g/mol")
        if mol.boiling_point_C:
            st.markdown(f"- **Boiling Point:** {mol.boiling_point_C} deg C")
        if mol.melting_point_C:
            st.markdown(f"- **Melting Point:** {mol.melting_point_C} deg C")
        st.markdown(f"- **Hazard Class:** {mol.hazard_class}")

show_molecule_reference()


