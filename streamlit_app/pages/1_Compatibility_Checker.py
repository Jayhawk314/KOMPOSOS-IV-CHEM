"""Material Compatibility Checker — check if two materials are compatible."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from utils.molecule_autocomplete import molecule_selector, show_molecule_reference
from streamlit_app.access_control import render_login_sidebar, require_access, consume_use
from streamlit_app.md_controls import render_md_input_controls, render_md_result

st.set_page_config(page_title="Compatibility Checker", page_icon="🔬", layout="wide")
st.title("Material Compatibility Checker")
st.markdown("Select two materials from the same domain to check compatibility.")

render_login_sidebar()

# ---------------------------------------------------------------------------
# Load materials per domain (cached)
# ---------------------------------------------------------------------------

DOMAIN_IMPORTS = {
    "battery": ("battery_bridge.material_properties", "ALL_MATERIALS"),
    "polymer": ("polymer_bridge.material_properties", "ALL_POLYMERS"),
    "metal": ("metal_bridge.material_properties", "ALL_METALS"),
    "ceramic": ("ceramic_bridge.material_properties", "ALL_CERAMICS"),
    "semiconductor": ("semiconductor_bridge.material_properties", "ALL_SEMICONDUCTORS"),
    "glass": ("glass_bridge.material_properties", "ALL_GLASSES"),
}

DOMAIN_VALIDATORS = {
    "battery": ("battery_bridge", "validate_interface"),
    "polymer": ("polymer_bridge", "validate_interface"),
    "metal": ("metal_bridge", "validate_interface"),
    "ceramic": ("ceramic_bridge", "validate_interface"),
    "semiconductor": ("semiconductor_bridge", "validate_interface"),
    "glass": ("glass_bridge", "validate_interface"),
}


@st.cache_data
def get_all_materials():
    """Load all materials grouped by domain."""
    import importlib
    result = {}
    for domain, (mod_path, attr) in DOMAIN_IMPORTS.items():
        mod = importlib.import_module(mod_path)
        mats = getattr(mod, attr)
        result[domain] = sorted(mats.keys())
    return result


def run_compatibility(domain, name_a, name_b):
    """Run compatibility check for a given domain."""
    import importlib
    mod_path, func_name = DOMAIN_VALIDATORS[domain]
    mod = importlib.import_module(mod_path)
    validate_fn = getattr(mod, func_name)
    return validate_fn(name_a, name_b)


def run_zfc_audit(domain, name_a, name_b, component_scores):
    """Run ZFC constraint verification on the scorer results.

    Returns a dict with:
        delta_type: AGREE | HOLLOW | ORPHAN | REJECT
        vetoes: list of scorer names that triggered a hard veto
        compatible: list of scorer names that passed threshold
        cat_says: bool (Category Theory result -- viable flag)
        zfc_says: bool (ZFC result -- no vetoes)
    """
    VETO_THRESHOLD = 0.20
    COMPAT_THRESHOLD = 0.45

    vetoes = []
    compatible = []
    for scorer_name, score_val in component_scores.items():
        if score_val < VETO_THRESHOLD:
            vetoes.append(scorer_name)
        if score_val >= COMPAT_THRESHOLD:
            compatible.append(scorer_name)

    zfc_says = len(vetoes) == 0
    return {
        "vetoes": vetoes,
        "compatible": compatible,
        "zfc_says": zfc_says,
    }


# ---------------------------------------------------------------------------
# UI: Material Compatibility
# ---------------------------------------------------------------------------

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
    # Default to a different material
    default_b = min(1, len(materials) - 1)
    mat_b = st.selectbox("Material B", materials, index=default_b)

# --- Active Verification Toggle ---
st.markdown("---")
col_md, col_help = st.columns([1, 3])
with col_md:
    md_verify = st.checkbox("Trigger Active Verification (MD)", help="Orchestrate a high-fidelity Molecular Dynamics simulation (GROMACS) for this interface.")
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
        
        # We need the API-style call for MD integration
        from oracle.md_integration import MDIntegrator
        
        with st.spinner("Running dual-engine analysis + Active Verification..."):
            result = run_compatibility(domain, mat_a, mat_b)
            
            # Integrated MD Logic
            md_results = None
            if md_verify:
                md_integrator = MDIntegrator()
                md_run = md_integrator.run_verification(mat_a, mat_b, domain, md_conditions)
                md_constraint_scores = md_run.constraint_scores()
                md_fusion = md_run.fuse_with_categorical(
                    result.total,
                    result.viable,
                    cat_confidence=0.4 if 0.4 < result.total < 0.6 else 0.8,
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
                    result.viable = bool(md_fusion["fused_viable"])
                elif md_run.confidence > 0.8:
                    result.viable = md_run.viable

        scores = result.to_dict()
        total = scores.get("total", 0)
        viable = scores.get("viable", False)

        component_scores = {
            k: v for k, v in scores.items()
            if k not in ("total", "viable") and isinstance(v, (int, float))
        }
        if md_results and md_results.get("constraint_scores"):
            component_scores.update(md_results["constraint_scores"])

        # --- ZFC Dual-Engine Audit ---
        zfc = run_zfc_audit(domain, mat_a, mat_b, component_scores)
        cat_says = viable
        zfc_says = zfc["zfc_says"]

        if cat_says and zfc_says:
            delta_type = "AGREE"
        elif cat_says and not zfc_says:
            delta_type = "HOLLOW"
        elif not cat_says and zfc_says:
            delta_type = "ORPHAN"
        else:
            delta_type = "REJECT"

        # --- Dual-Engine Verdict ---
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
            if zfc_says:
                st.success(f"Witness FOUND ({len(zfc['compatible'])}/{len(component_scores)} constraints pass)")
                st.caption("No constraint vetoes detected in the current rule set.")
            else:
                veto_names = ", ".join(
                    v.replace("_", " ").title() for v in zfc["vetoes"]
                )
                st.error(f"Witness EMPTY ({len(zfc['vetoes'])} veto(s): {veto_names})")
                st.caption("Hard constraint veto -- score below 0.20 on at least one axis.")

        # --- MD Verification Result ---
        if md_results:
            render_md_result(md_results)

        # --- Delta Classification ---
        if delta_type == "AGREE":
            st.success(
                f"**AGREE** -- The categorical score passes for **{mat_a} + {mat_b}** and "
                f"the ZFC constraint verifier finds no veto."
            )
        elif delta_type == "HOLLOW":
            st.warning(
                f"**HOLLOW STATE** -- The categorical oracle finds a compositional path "
                f"(score {total:.3f}), but the ZFC constraint verifier detected a hard "
                f"constraint veto. KOMPOSOS rejects it because the current constraint set "
                f"does not admit this interface."
            )
            with st.expander("Why this matters"):
                st.markdown(
                    "A **HOLLOW** state means the structural pattern *looks* like it should work "
                    "(the arrows compose in the category), but at least one explicit constraint "
                    "falls below the veto threshold. This is a logical/constraint warning, not "
                    "a standalone proof of physical truth.\n\n"
                    f"**Veto constraint(s):** {', '.join(zfc['vetoes'])}\n\n"
                    "These scorers returned values below 0.20, indicating a high-risk constraint "
                    "failure that needs external evidence before the pair should be trusted."
                )
        elif delta_type == "ORPHAN":
            st.info(
                f"**ORPHAN** -- The ZFC verifier finds no constraint veto, but the "
                f"categorical scorer composite falls below threshold (score {total:.3f}). "
                f"This pair is not ruled out by the current constraints, but it is structurally weak."
            )
        else:
            st.error(
                f"**REJECT** -- Both engines agree: **{mat_a} + {mat_b}** fails. "
                f"The categorical morphism does not compose AND the ZFC constraint set "
                f"contains vetoes."
            )

        # --- Score Breakdown ---
        st.subheader("Score Breakdown")

        if component_scores:
            import pandas as pd
            df = pd.DataFrame({
                "Scorer": [k.replace("_", " ").title() for k in component_scores.keys()],
                "Score": list(component_scores.values()),
            })
            df = df.set_index("Scorer")

            col_chart, col_table = st.columns([2, 1])

            with col_chart:
                st.bar_chart(df, horizontal=True)

            with col_table:
                st.dataframe(
                    df.style.format("{:.3f}").background_gradient(
                        cmap="RdYlGn", vmin=0, vmax=1
                    ),
                    use_container_width=True,
                )

            st.caption(
                "Viability threshold: 0.45 | "
                "Veto threshold: 0.20 (below this = ZFC hard constraint veto)"
            )

        # Raw data
        with st.expander("Raw score data"):
            st.json(scores)
            st.json({
                "delta_type": delta_type,
                "cat_says_viable": cat_says,
                "zfc_says_no_vetoes": zfc_says,
                "zfc_vetoes": zfc["vetoes"],
                "zfc_compatible_constraints": zfc["compatible"],
            })

# ---------------------------------------------------------------------------
# Molecule Constraint Search
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Molecule Constraint Search")
st.markdown(
    "KOMPOSOS doesn't generate text -- it searches real molecular data with "
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
            "**This is the correct answer** -- not a hallucination. "
            "KOMPOSOS never fabricates molecules."
        )

    # Show distribution
    with st.expander("Heavy atom count distribution (all 37 molecules)"):
        dist = get_atom_count_distribution()
        import pandas as pd
        rows = []
        for count, names in dist.items():
            rows.append({"Heavy Atoms": count, "Count": len(names), "Molecules": ", ".join(names)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Quick Molecule Selection
# ---------------------------------------------------------------------------

st.divider()
st.subheader("🧪 Quick Molecule Selection")
st.caption("Select a molecule directly to view details, or use constraint search above for advanced filtering")

selected_molecule = molecule_selector(
    label="Choose molecule",
    key="quick_molecule_select",
    help_text="Select from 37 available molecules"
)

if selected_molecule:
    from molecular_bridge.molecule_properties import ALL_MOLECULES
    mol = ALL_MOLECULES[selected_molecule]

    st.success(f"✅ Selected: **{selected_molecule}** ({mol.name})")

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
            st.markdown(f"- **Boiling Point:** {mol.boiling_point_C}°C")
        if mol.melting_point_C:
            st.markdown(f"- **Melting Point:** {mol.melting_point_C}°C")
        st.markdown(f"- **Hazard Class:** {mol.hazard_class}")

# Show molecule reference
show_molecule_reference()
