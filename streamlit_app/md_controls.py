"""Shared Streamlit controls for GROMACS active verification."""

from typing import Dict, Optional

import streamlit as st


def render_md_input_controls(key_prefix: str) -> Dict:
    """Render GROMACS input controls and return md_conditions."""
    st.caption(
        "Real MD requires a prepared GROMACS input bundle. Provide a .gro structure "
        "and .top topology, or let KOMPOSOS search data/gromacs_inputs for this pair."
    )
    mode = st.radio(
        "GROMACS inputs",
        ["Auto-discover library", "Input directory", "Explicit file paths"],
        horizontal=True,
        key=f"{key_prefix}_input_mode",
    )

    conditions: Dict = {}
    if mode == "Input directory":
        input_dir = st.text_input(
            "Input directory",
            help="Directory containing a .gro structure and .top topology. Optional: .mdp and .ndx.",
            key=f"{key_prefix}_input_dir",
        )
        if input_dir.strip():
            conditions["input_dir"] = input_dir.strip()
    elif mode == "Explicit file paths":
        col_gro, col_top = st.columns(2)
        with col_gro:
            gro_path = st.text_input(
                ".gro structure path",
                key=f"{key_prefix}_gro_path",
            )
        with col_top:
            top_path = st.text_input(
                ".top topology path",
                key=f"{key_prefix}_top_path",
            )
        col_mdp, col_ndx = st.columns(2)
        with col_mdp:
            mdp_path = st.text_input(
                ".mdp path (optional)",
                key=f"{key_prefix}_mdp_path",
            )
        with col_ndx:
            index_path = st.text_input(
                ".ndx path (optional)",
                key=f"{key_prefix}_index_path",
            )
        if gro_path.strip():
            conditions["gro_path"] = gro_path.strip()
        if top_path.strip():
            conditions["top_path"] = top_path.strip()
        if mdp_path.strip():
            conditions["mdp_path"] = mdp_path.strip()
        if index_path.strip():
            conditions["index_path"] = index_path.strip()

    col_temp, col_timeout, col_threads, col_warn = st.columns(4)
    with col_temp:
        conditions["temperature_C"] = st.number_input(
            "Temperature (C)",
            min_value=-273.0,
            max_value=2000.0,
            value=25.0,
            step=5.0,
            key=f"{key_prefix}_temperature",
        )
    with col_timeout:
        conditions["timeout_s"] = st.number_input(
            "Timeout (s)",
            min_value=30,
            max_value=7200,
            value=300,
            step=30,
            key=f"{key_prefix}_timeout",
        )
    with col_threads:
        conditions["nt"] = st.number_input(
            "Threads",
            min_value=1,
            max_value=64,
            value=1,
            step=1,
            key=f"{key_prefix}_threads",
        )
    with col_warn:
        conditions["maxwarn"] = st.number_input(
            "Maxwarn",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key=f"{key_prefix}_maxwarn",
        )
    return conditions


def render_md_result(md_results: Dict, title: str = "Active Verification: GROMACS MD Runner") -> None:
    """Render measured MD, no-verdict, and setup-failure states honestly."""
    st.markdown(f"**{title}**")
    verdict = md_results.get("verdict", "no_verdict")
    measured_md = bool(md_results.get("measured_md"))
    confidence = float(md_results.get("confidence", 0.0))

    if measured_md and verdict == "stable":
        st.success(f"Measured MD STABLE (confidence {confidence:.2f})")
    elif measured_md and verdict == "unstable":
        st.error(f"Measured MD UNSTABLE (confidence {confidence:.2f})")
    elif verdict == "execution_failed":
        st.warning("GROMACS setup or execution failed; no material verdict was produced.")
    else:
        st.warning("No measured MD verdict was produced.")

    st.info(md_results.get("detail", "No MD detail returned."))
    if md_results.get("fusion", {}).get("used"):
        fusion = md_results["fusion"]
        st.caption(
            "Dempster-Shafer CAT+MD fusion: "
            f"score={fusion['fused_score']:.3f}, "
            f"conflict={fusion['conflict']:.3f}, "
            f"belief={fusion['belief_viable']:.3f}, "
            f"plausibility={fusion['plausibility_viable']:.3f}"
        )

    with st.expander("Simulation Metadata"):
        st.json(md_results.get("metadata", {}))
        if measured_md:
            st.write(f"Potential Energy Diff: {md_results.get('energy_diff', 0.0):.3f} eV/atom")
            st.write(f"Diffusion Coefficient: {md_results.get('diffusion', 0.0):.2e} cm^2/s")
        if md_results.get("constraint_scores"):
            st.write("MD ZFC constraint scores:")
            st.json(md_results["constraint_scores"])
