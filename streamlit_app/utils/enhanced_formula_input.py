# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Enhanced Formula Input with Smart Search for 103k+ Materials
================================================================

Provides intelligent autocomplete that searches across:
- 27 shorthands (NMC811, LFP, etc.)
- 169 KOMPOSOS materials
- 103k+ Materials Project entries (if available)
"""

import streamlit as st
from typing import Optional
from composition_engine.parser import SHORTHAND_MAP
from composition_engine.known_compositions import get_db


def enhanced_formula_input(
    label: str = "Chemical Formula",
    key: str = "enhanced_formula",
    default_value: str = "",
    placeholder: str = "Type to search: Li, NMC811, perovskite, mp-1234",
    help_text: Optional[str] = None,
    show_quick_select: bool = True,
) -> Optional[str]:
    """
    Render enhanced formula input with smart search across all databases.

    Features:
    - Real-time search as you type
    - Searches shortcuts, KOMPOSOS DB, and MP cache (103k+)
    - Shows category labels (battery, semiconductor, etc.)
    - Popular materials quick-select
    - Custom formula entry

    Args:
        label: Input label
        key: Unique Streamlit key
        default_value: Default formula
        placeholder: Search placeholder text
        help_text: Optional help text
        show_quick_select: Show popular materials buttons

    Returns:
        Selected or entered formula (None if empty)
    """
    # Try to load MaterialSearchEngine if MP available
    search_engine = None
    try:
        from composition_engine.mp_loader import MPCache
        cache = MPCache()
        if cache.is_available():
            from streamlit_app.material_search import MaterialSearchEngine
            entries = cache.load_entries()
            search_engine = MaterialSearchEngine(entries)
    except Exception:
        pass  # MP not available

    st.markdown(f"**{label}**")

    if help_text:
        st.caption(help_text)

    # Quick select buttons (popular materials)
    if show_quick_select:
        quick_materials = {
            "NMC811": "LiNi0.8Mn0.1Co0.1O2",
            "LFP": "LiFePO4",
            "LLZO": "Li7La3Zr2O12",
            "TiO2": "TiO2",
            "GaAs": "GaAs",
            "Custom": None,
        }

        cols = st.columns(len(quick_materials))
        selected_quick = None

        for i, (name, formula) in enumerate(quick_materials.items()):
            with cols[i]:
                if st.button(name, key=f"{key}_quick_{name}", use_container_width=True):
                    selected_quick = formula
                    if formula:
                        st.session_state[f"{key}_selected"] = formula

    # Search box
    query = st.text_input(
        "Search or enter formula",
        value=default_value,
        placeholder=placeholder,
        key=f"{key}_query",
        label_visibility="collapsed",
    )

    # If search engine available and user typed something, show search results
    if search_engine and query and len(query) >= 2:
        # Check if it's a shorthand first
        query_upper = query.upper()
        if query_upper in SHORTHAND_MAP:
            st.success(f"✓ **{query_upper}** → `{SHORTHAND_MAP[query_upper]}`")
            return SHORTHAND_MAP[query_upper]

        # Search MP database
        matches = search_engine.search(query, limit=10, stable_only=False)

        if matches:
            st.caption(f"Found {len(matches)} matches:")

            # Show matches as buttons
            for i, match in enumerate(matches):
                stability_icon = "✓" if match.is_stable else "⚠"
                category_short = match.category.replace("_", " ").title()[:15]

                button_label = f"{stability_icon} {match.formula} | {category_short}"

                if st.button(
                    button_label,
                    key=f"{key}_match_{i}",
                    help=f"{match.mp_id} | {match.crystal_system} | Ef={match.formation_energy:.3f} eV/atom",
                    use_container_width=True,
                ):
                    st.session_state[f"{key}_selected"] = match.formula
                    return match.formula

    # Check if user selected something
    if f"{key}_selected" in st.session_state:
        selected = st.session_state[f"{key}_selected"]
        if selected != query:
            # User selected but then changed query - clear selection
            if query.strip():
                return query.strip()
        return selected

    # Return typed query if it looks valid
    if query and query.strip():
        # Basic validation: contains letters and maybe numbers
        if any(c.isalpha() for c in query):
            return query.strip()

    return None


def show_enhanced_reference():
    """Display reference with shortcuts, KOMPOSOS materials, and MP stats."""
    st.markdown("### Available Resources")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Shortcuts", f"{len(SHORTHAND_MAP)}")
        st.caption("NMC811, LFP, LLZO, etc.")

    with col2:
        db = get_db()
        st.metric("KOMPOSOS DB", f"{db.size}")
        st.caption("Curated materials")

    with col3:
        try:
            from composition_engine.mp_loader import MPCache
            cache = MPCache()
            if cache.is_available():
                import json
                from pathlib import Path
                meta_path = Path(cache.cache_dir) / cache.META_FILE
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    count = meta.get('count', 0)
                    st.metric("Materials Project", f"{count:,}")
                    st.caption("DFT-computed structures")
                else:
                    st.metric("Materials Project", "Available")
            else:
                st.metric("Materials Project", "Not loaded")
        except Exception:
            st.metric("Materials Project", "Not loaded")

    # Show shortcuts in expander
    with st.expander("📝 Shortcut Reference"):
        cols = st.columns(3)
        shortcuts = sorted(SHORTHAND_MAP.items())
        for i, (short, formula) in enumerate(shortcuts):
            with cols[i % 3]:
                st.markdown(f"**{short}** → `{formula}`")
