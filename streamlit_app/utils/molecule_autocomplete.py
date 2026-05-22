"""
Molecule autocomplete utilities for Streamlit UI.
Provides native Streamlit autocomplete for molecule selection.
"""
import streamlit as st
from typing import Optional, Dict
from molecular_bridge.molecule_properties import ALL_MOLECULES, MoleculeClass


@st.cache_data
def get_molecule_options() -> Dict[str, str]:
    """
    Get all available molecules formatted for dropdown.

    Returns:
        Dict mapping display name to molecule key
    """
    options = {}
    for mol_key, mol in ALL_MOLECULES.items():
        # Format: "EC (Ethylene Carbonate) [CID: 7303]"
        display_name = f"{mol_key} ({mol.name})"
        if mol.pubchem_cid:
            display_name += f" [CID: {mol.pubchem_cid}]"
        options[display_name] = mol_key

    return options


def molecule_selector(
    label: str = "Select molecule",
    key: str = "molecule_select",
    help_text: Optional[str] = None
) -> Optional[str]:
    """
    Render a molecule selector dropdown.

    Args:
        label: Dropdown label
        key: Unique Streamlit key
        help_text: Optional help text

    Returns:
        Selected molecule key (e.g., "EC") or None
    """
    options = get_molecule_options()
    display_names = ["-- Select a molecule --"] + sorted(options.keys())

    selection = st.selectbox(
        label,
        options=display_names,
        key=key,
        help=help_text or f"Choose from {len(options)} available molecules"
    )

    if selection == "-- Select a molecule --":
        return None

    return options[selection]


def show_molecule_reference():
    """Display expandable reference of all available molecules."""
    with st.expander("🧪 Available Molecules Reference"):
        st.caption(f"{len(ALL_MOLECULES)} molecules in database")

        # Group by molecular class
        by_class = {}
        for mol_key, mol in ALL_MOLECULES.items():
            mol_class = mol.molecule_class.value if hasattr(mol.molecule_class, 'value') else str(mol.molecule_class)
            if mol_class not in by_class:
                by_class[mol_class] = []
            by_class[mol_class].append((mol_key, mol))

        # Display by class
        for mol_class in sorted(by_class.keys()):
            st.markdown(f"### {mol_class.replace('_', ' ').title()}")
            mols = sorted(by_class[mol_class], key=lambda x: x[0])

            cols = st.columns(2)
            for i, (mol_key, mol) in enumerate(mols):
                with cols[i % 2]:
                    st.markdown(f"**{mol_key}** - {mol.name}")
                    if mol.pubchem_cid:
                        st.caption(f"CID: {mol.pubchem_cid}")
