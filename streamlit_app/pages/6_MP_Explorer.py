"""MP Explorer — browse Materials Project data and derive crystal structures."""

import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

st.set_page_config(page_title="MP Explorer", page_icon="🔬", layout="wide")
st.title("Materials Project Explorer")

# ---------------------------------------------------------------------------
# Check MP availability
# ---------------------------------------------------------------------------

from composition_engine.known_compositions import get_db
from composition_engine.mp_loader import MPCache

db = get_db()
cache = MPCache()

mp_available = cache.is_available()

# Load search engine if MP available
_search_engine = None
if mp_available:
    try:
        from streamlit_app.material_search import MaterialSearchEngine
        entries = cache.load_entries()
        _search_engine = MaterialSearchEngine(entries)
    except Exception as e:
        st.error(f"Failed to initialize search engine: {e}")

if mp_available:
    # ---------------------------------------------------------------------------
    # MP Status
    # ---------------------------------------------------------------------------

    import json

    meta_path = Path(cache.cache_dir) / cache.META_FILE
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Materials", f"{db.size:,}")
    m2.metric("MP Entries", f"{meta.get('count', '?'):,}")
    m3.metric("Downloaded", meta.get("downloaded", "?")[:10])

    st.divider()

    # ---------------------------------------------------------------------------
    # Smart Material Search
    # ---------------------------------------------------------------------------

    if _search_engine:
        st.subheader("🔍 Smart Material Search")
        st.markdown(
            "Search 103K+ materials by formula, element, MP ID, or common name. "
            "Try: `Li`, `NMC811`, `mp-1234`, `perovskite`"
        )

        from streamlit_app.material_search import render_material_search, render_category_browser

        tab_search, tab_category = st.tabs(["Search", "Browse by Category"])

        with tab_search:
            selected_material = render_material_search(
                _search_engine,
                key="mp_explorer_search",
                label="Search for any material",
                category_filter=True,
                stable_filter=True,
            )

            if selected_material:
                st.success(f"Selected: **{selected_material.formula}** ({selected_material.mp_id})")

                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Crystal System:** {selected_material.crystal_system}")
                    st.write(f"**Category:** {selected_material.category.replace('_', ' ').title()}")
                with col_info2:
                    st.write(f"**Formation Energy:** {selected_material.formation_energy:.3f} eV/atom")
                    stability = "On hull (stable)" if selected_material.is_stable else f"{selected_material.above_hull:.3f} eV above hull"
                    st.write(f"**Stability:** {stability}")

                # Quick action: derive structure
                if st.button("📐 Derive Crystal Structure", key="quick_derive"):
                    st.session_state.mp_explorer_formula = selected_material.formula
                    st.info(f"Jump to Structure Derivation section below and click 'Derive Structure'")

        with tab_category:
            selected_material = render_category_browser(_search_engine, key="mp_category_browser")

            if selected_material:
                st.success(f"Selected: **{selected_material.formula}** ({selected_material.mp_id})")

        st.divider()

    else:
        st.warning("Search engine not available. Using basic interface below.")
        st.divider()

    # ---------------------------------------------------------------------------
    # Structure Derivation Tool
    # ---------------------------------------------------------------------------

    st.subheader("Structure Derivation")
    st.markdown(
        "Enter any chemical formula to derive its crystal structure from the nearest "
        "Materials Project entries via **Kan extension**. Every parameter traces back "
        "to specific MP structures with exact weights."
    )

    # Pre-fill from search if available
    default_formula = st.session_state.get("mp_explorer_formula", "LiNi0.8Mn0.1Co0.1O2")

    formula = st.text_input(
        "Chemical formula",
        value=default_formula,
        key="derive_formula",
        help="Tip: Select a material from Smart Search above to auto-fill this field",
    )

    if st.button("Derive Structure", type="primary"):
        import pandas as pd
        from composition_engine.structure_deriver import StructureDeriver

        with st.spinner("Loading MP data and deriving structure..."):
            entries = cache.load_entries_with_lattice()
            deriver = StructureDeriver(entries)
            ds = deriver.derive(formula)

        if ds is None:
            st.error("Could not derive structure for this formula.")
        else:
            d = ds.to_dict()

            col_cs, col_conf = st.columns([3, 1])
            with col_cs:
                sg_num = d.get("space_group_number", "")
                st.write(f"**Crystal system:** {d['crystal_system']}")
                st.write(f"**Space group:** {d['space_group']} (#{sg_num})")
            with col_conf:
                st.metric("Confidence", f"{d['confidence']:.1%}")

            # Lattice parameters
            col_lat, col_vol = st.columns([3, 1])
            with col_lat:
                lat_rows = [
                    {"Parameter": "a", "Value": d["lattice_a"], "Unit": "\u00c5"},
                    {"Parameter": "b", "Value": d["lattice_b"], "Unit": "\u00c5"},
                    {"Parameter": "c", "Value": d["lattice_c"], "Unit": "\u00c5"},
                    {"Parameter": "\u03b1", "Value": d["lattice_alpha"], "Unit": "\u00b0"},
                    {"Parameter": "\u03b2", "Value": d["lattice_beta"], "Unit": "\u00b0"},
                    {"Parameter": "\u03b3", "Value": d["lattice_gamma"], "Unit": "\u00b0"},
                ]
                st.dataframe(
                    pd.DataFrame(lat_rows).style.format({"Value": "{:.4f}"}),
                    use_container_width=True,
                    hide_index=True,
                )
            with col_vol:
                st.metric("Volume/atom", f'{d["volume_per_atom"]:.2f} \u00c5\u00b3')

            st.info(f'**Provenance:** {d["provenance"]}')

            # Nearest MP entries
            mp_neighbours = d.get("nearest_mp", [])
            if mp_neighbours:
                st.markdown(f"**Nearest MP structures** ({len(mp_neighbours)} entries)")
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

            with st.expander("Raw derivation data"):
                st.json(d)

    # ---------------------------------------------------------------------------
    # Nearest MP Search
    # ---------------------------------------------------------------------------

    st.divider()
    st.subheader("Nearest MP Search")
    st.markdown("Find the closest Materials Project entries to any composition.")

    search_formula = st.text_input(
        "Search formula",
        value="LiFePO4",
        key="search_formula",
    )

    if st.button("Search", key="search_btn"):
        import pandas as pd
        from composition_engine.parser import parse_formula, composition_vector
        from composition_engine.spatial_index import CompositionIndex

        try:
            comp = parse_formula(search_formula)
            query_vec = composition_vector(comp)
        except Exception as e:
            st.error(f"Cannot parse formula: {e}")
            st.stop()

        with st.spinner("Searching..."):
            entries = cache.load_entries()
            index = CompositionIndex(entries)
            results = index.nearest_k(query_vec, k=10)

        if not results:
            st.warning("No results found.")
        else:
            rows = []
            for entry, dist in results:
                rows.append({
                    "MP ID": entry.mp_id,
                    "Formula": entry.formula,
                    "Distance": dist,
                    "Ef (eV/atom)": entry.formation_energy_per_atom,
                    "E above hull": entry.energy_above_hull,
                    "Crystal System": entry.crystal_system or "\u2014",
                    "Space Group": entry.space_group_symbol or "\u2014",
                    "Stable": "Yes" if entry.is_stable else "No",
                })
            df = pd.DataFrame(rows)
            st.dataframe(
                df.style.format({
                    "Distance": "{:.4f}",
                    "Ef (eV/atom)": "{:.3f}",
                    "E above hull": "{:.3f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

    # ---------------------------------------------------------------------------
    # Dataset Statistics
    # ---------------------------------------------------------------------------

    st.divider()
    st.subheader("Dataset Statistics")

    with st.expander("Crystal system distribution"):
        import pandas as pd
        entries = cache.load_entries()
        cs_counts = {}
        for e in entries:
            cs = e.crystal_system or "unknown"
            cs_counts[cs] = cs_counts.get(cs, 0) + 1
        cs_df = pd.DataFrame({
            "Crystal System": list(cs_counts.keys()),
            "Count": list(cs_counts.values()),
        }).sort_values("Count", ascending=False).set_index("Crystal System")
        st.bar_chart(cs_df)

    with st.expander("Domain distribution"):
        from composition_engine.mp_loader import classify_mp_domain
        domain_counts = {}
        for e in entries:
            dom = classify_mp_domain(e.composition)
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
        dom_df = pd.DataFrame({
            "Domain": list(domain_counts.keys()),
            "Count": list(domain_counts.values()),
        }).sort_values("Count", ascending=False).set_index("Domain")
        st.bar_chart(dom_df)

else:
    # ---------------------------------------------------------------------------
    # No MP data -- explain what this page offers
    # ---------------------------------------------------------------------------

    st.metric("KOMPOSOS Materials", f"{db.size:,}")

    st.divider()

    st.info(
        "**Materials Project data is not cached on this server.**\n\n"
        "The MP Explorer requires a local download of ~103,000 Materials Project entries "
        "(9.7 MB compressed). This data is too large for the free-tier deployment.\n\n"
        "All other KOMPOSOS features (Compatibility Checker, PFAS Scanner, Composition "
        "Predictor, Cell Designer, Crystal Dreamer) work fully without MP data."
    )

    st.subheader("What MP Explorer Provides (with data)")

    st.markdown(
        "When the Materials Project cache is available, this page offers three tools:\n\n"
        "1. **Structure Derivation** -- Enter any chemical formula and derive its crystal "
        "structure (lattice parameters, space group, crystal system) from the nearest MP "
        "entries via Kan extension. Every parameter traces back to specific MP structures "
        "with exact weights.\n\n"
        "2. **Nearest MP Search** -- Find the 10 closest Materials Project entries to any "
        "composition. See formation energies, energy above hull, stability, and space groups.\n\n"
        "3. **Dataset Statistics** -- Crystal system and domain distributions across the full "
        "103,000+ MP dataset."
    )

    st.subheader("How to Enable (Self-Hosted)")

    st.code(
        "# Requires a Materials Project API key (free at materialsproject.org)\n"
        "pip install mp-api\n"
        "python scripts/download_mp_data.py --api-key YOUR_MP_API_KEY\n\n"
        "# Then restart the Streamlit app\n"
        "streamlit run streamlit_app/app.py",
        language="bash",
    )

    st.markdown(
        "The download takes 5-10 minutes and creates a 9.7 MB cache file at "
        "`data/cache/materials_project/mp_summaries.json.gz`. Once cached, "
        "no further API calls are needed."
    )
