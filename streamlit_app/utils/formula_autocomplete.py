"""
Formula autocomplete utilities for Streamlit UI.
Provides native Streamlit autocomplete for chemical formulas.
"""
import streamlit as st
from typing import Optional, List, Tuple
from composition_engine.parser import SHORTHAND_MAP
from composition_engine.known_compositions import get_db


@st.cache_data
def get_formula_suggestions(include_mp: bool = True) -> Tuple[List[str], List[str], List[str]]:
    """
    Get all available formula suggestions.

    Args:
        include_mp: Include Materials Project formulas (103k+ entries)

    Returns:
        (shorthands, known_formulas, all_suggestions)
    """
    # Shorthands (27 entries)
    shorthands = sorted(SHORTHAND_MAP.keys())

    # Known formulas from KOMPOSOS database (169+ entries)
    db = get_db()
    known_formulas = sorted([entry.formula for entry in db.entries])

    # Try to include MP formulas if available
    mp_formulas = []
    if include_mp:
        try:
            from composition_engine.mp_loader import MPCache
            cache = MPCache()
            if cache.is_available():
                mp_entries = cache.load_entries()
                mp_formulas = sorted(list(set([e.formula for e in mp_entries])))
                # Limit to 1000 most common for UI performance
                mp_formulas = mp_formulas[:1000]
        except Exception:
            pass  # MP not available, skip

    # Combined list for autocomplete
    all_suggestions = sorted(set(shorthands + known_formulas + mp_formulas))

    return shorthands, known_formulas, all_suggestions


def formula_input_with_autocomplete(
    label: str,
    key: str,
    default_value: str = "",
    help_text: Optional[str] = None,
    placeholder: str = "e.g., NMC811 or LiNi0.8Mn0.1Co0.1O2"
) -> Optional[str]:
    """
    Render a formula input with autocomplete support.

    Uses two-column layout:
    - Left: selectbox with suggestions
    - Right: text input for custom formulas

    Args:
        label: Input label
        key: Unique key for Streamlit state
        default_value: Default formula value
        help_text: Optional help text
        placeholder: Placeholder for custom input

    Returns:
        Selected or entered formula (None if empty)
    """
    shorthands, known_formulas, all_suggestions = get_formula_suggestions()

    # Add "Custom formula..." option at the top
    suggestions_with_custom = ["📝 Enter custom formula..."] + all_suggestions

    col1, col2 = st.columns([1, 1])

    with col1:
        # Find default index
        default_idx = 0
        if default_value and default_value in all_suggestions:
            default_idx = all_suggestions.index(default_value) + 1  # +1 for custom option

        selection = st.selectbox(
            f"{label} (select from library)",
            options=suggestions_with_custom,
            index=default_idx,
            key=f"{key}_select",
            help=f"Select from {len(all_suggestions)} known materials/shorthands"
        )

    with col2:
        custom_formula = st.text_input(
            f"{label} (or enter custom)",
            value=default_value if default_value and default_value not in all_suggestions else "",
            placeholder=placeholder,
            key=f"{key}_custom",
            help=help_text or "Enter any valid chemical formula"
        )

    # Determine which input to use
    if custom_formula.strip():
        # Custom input takes precedence
        return custom_formula.strip()
    elif selection and selection != "📝 Enter custom formula...":
        # Use selected suggestion
        return selection
    else:
        return None


def show_formula_reference():
    """Display expandable reference of available shorthands and known materials."""
    shorthands, known_formulas, _ = get_formula_suggestions()

    with st.expander("📚 Formula Reference"):
        st.markdown("### Available Shorthands")
        st.caption(f"{len(shorthands)} shorthands available")

        # Display shorthands in 3 columns
        cols = st.columns(3)
        for i, shorthand in enumerate(shorthands):
            formula = SHORTHAND_MAP[shorthand]
            with cols[i % 3]:
                st.markdown(f"**{shorthand}** → `{formula}`")

        st.markdown("### Known Materials")
        st.caption(f"{len(known_formulas)} materials in database")

        # Display known formulas in 4 columns (just first 40 to avoid clutter)
        display_formulas = known_formulas[:40] if len(known_formulas) > 40 else known_formulas
        cols = st.columns(4)
        for i, formula in enumerate(display_formulas):
            with cols[i % 4]:
                st.code(formula, language=None)

        if len(known_formulas) > 40:
            st.caption(f"... and {len(known_formulas) - 40} more formulas (use autocomplete to see all)")
