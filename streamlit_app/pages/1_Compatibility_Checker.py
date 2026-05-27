"""Material Compatibility Checker - check if two materials are compatible."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from utils.molecule_autocomplete import molecule_selector, show_molecule_reference
from oracle.compatibility_service import run_compatibility_workflow
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.md_controls import render_md_input_controls, render_md_result

st.set_page_config(page_title="Compatibility Checker", page_icon="chem", layout="wide")
st.title("Material Compatibility Checker")
st.markdown("Select two materials from the same domain to check compatibility.")

render_login_sidebar()

DOMAIN_IMPORTS = {
    "battery": ("battery_bridge.material_properties", "ALL_MATERIALS"),
    "polymer": ("polymer_bridge.material_properties", "ALL_POLYMERS"),
    "metal": ("metal_bridge.material_properties", "ALL_METALS"),
    "ceramic": ("ceramic_bridge.material_properties", "ALL_CERAMICS"),
    "semiconductor": ("semiconductor_bridge.material_properties", "ALL_SEMICONDUCTORS"),
    "glass": ("glass_bridge.material_properties", "ALL_GLASSES"),
    "bio": ("domains.bio.loader", "BioDomainLoader"),
}


@st.cache_data
def get_all_materials():
    """Load all materials grouped by domain."""
    import importlib

    result = {}
    for domain, (mod_path, attr) in DOMAIN_IMPORTS.items():
        if domain == "bio":
            # Bio loader needs instantiation
            loader = importlib.import_module(mod_path).BioDomainLoader()
            result[domain] = sorted([obj.name for obj in loader.get_objects()])
            continue
            
        mod = importlib.import_module(mod_path)


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
            st.caption(
                "Calibrated compatibility probability: "
                f"{calibration.get('calibrated_probability', total):.3f} "
                f"via {calibration.get('calibrator', 'unknown')}"
            )

        ensemble = scores.get("ensemble", {})
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

            ensemble = scores.get("ensemble", {})
            if ensemble and ensemble.get("votes"):
                with st.expander("Detailed Ensemble Votes (Audit Trail)", expanded=True):
                    vote_rows = []
                    for vote in ensemble["votes"]:
                        vote_rows.append({
                            "Strategy": vote["strategy"].replace("_", " ").title(),
                            "Score": vote["score"],
                            "Confidence": vote["confidence"],
                            "Verdict": "PASS" if vote["compatible"] else "FAIL",
                            "Reasoning": vote["reason"]
                        })
                    import pandas as pd
                    vote_df = pd.DataFrame(vote_rows)
                    st.dataframe(
                        vote_df.style.format({"Score": "{:.3f}", "Confidence": "{:.3f}"}),
                        use_container_width=True,
                        hide_index=True
                    )

                    # Simplicial Yoneda Visualization (Presheaf Fingerprint)
                    for vote in ensemble["votes"]:
                        if vote["strategy"] == "simplicial_yoneda" and vote.get("metadata", {}).get("fingerprint_a"):
                            st.markdown("---")
                            st.subheader("Simplicial Presheaf Overlap")
                            meta = vote["metadata"]
                            neighbor = meta["neighbor"]
                            
                            col_a, col_n = st.columns(2)
                            
                            def format_fp(fp):
                                if not fp: return "Empty"
                                return "\n".join([f"- {target} ({rel})" for target, rel in fp])

                            with col_a:
                                st.markdown(f"**{mat_a} Fingerprint**")
                                st.code(format_fp(meta["fingerprint_a"]), language="markdown")
                            with col_n:
                                st.markdown(f"**{neighbor} Fingerprint** (known compatible with {mat_b})")
                                st.code(format_fp(meta["fingerprint_n"]), language="markdown")
                            
                            fp_a = set(tuple(x) for x in meta["fingerprint_a"])
                            fp_n = set(tuple(x) for x in meta["fingerprint_n"])
                            overlap = fp_a & fp_n
                            if overlap:
                                st.success(f"Structural overlap detected: {len(overlap)} shared relations.")
                                with st.expander("Show shared relations"):
                                    st.code(format_fp(list(overlap)), language="markdown")

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


