"""Material Search & Autocomplete Components
===========================================

Reusable Streamlit components for searching and filtering 103k+ materials.
"""

import streamlit as st
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MaterialMatch:
    """A search result match."""
    formula: str
    mp_id: str
    crystal_system: str
    formation_energy: float
    above_hull: float
    is_stable: bool
    category: str  # battery, semiconductor, perovskite, etc.

    def display_name(self) -> str:
        """Format for display in dropdown."""
        stability = "✓" if self.is_stable else "⚠"
        return f"{self.formula} ({self.mp_id}) {stability} | {self.crystal_system} | {self.category}"


class MaterialSearchEngine:
    """Smart search engine for 103k+ materials with autocomplete."""

    # Common shortcuts/aliases
    SHORTCUTS = {
        "NMC": "LiNi0.8Mn0.1Co0.1O2",
        "NMC811": "LiNi0.8Mn0.1Co0.1O2",
        "NMC622": "LiNi0.6Mn0.2Co0.2O2",
        "NMC111": "LiNi0.33Mn0.33Co0.33O2",
        "NCA": "LiNi0.8Co0.15Al0.05O2",
        "LFP": "LiFePO4",
        "LCO": "LiCoO2",
        "LMO": "LiMn2O4",
        "LLZO": "Li7La3Zr2O12",
        "LAGP": "Li1.5Al0.5Ge1.5(PO4)3",
        "LGPS": "Li10GeP2S12",
        "LNMO": "LiNi0.5Mn1.5O4",
        "LSC": "La0.6Sr0.4CoO3",
        "LSCO": "La2SrCo2O7",
        "YSZ": "Y0.08Zr0.92O2",
        "GDC": "Gd0.1Ce0.9O1.95",
        "CIGS": "CuInGaSe2",
    }

    # Category patterns (element-based heuristics)
    CATEGORY_PATTERNS = {
        "battery_cathode": ["Li", "Na", "Mg", "O"],  # Alkali + O
        "battery_electrolyte": ["Li", "P", "S", "Ge"],  # Solid electrolytes
        "battery_anode": ["C", "Si", "Sn", "Li"],  # Anodes
        "semiconductor_iii_v": ["Ga", "As", "In", "P", "N", "Al"],  # III-V
        "semiconductor_ii_vi": ["Zn", "Cd", "Hg", "S", "Se", "Te"],  # II-VI
        "perovskite": ["Ba", "Sr", "Pb", "Cs", "Ti", "O"],  # Perovskite
        "oxide": ["O"],  # Generic oxides
        "metal": [],  # Pure elements (handled separately)
        "mof": ["C", "N", "O", "H"],  # Organic frameworks
    }

    def __init__(self, mp_entries: List):
        """Initialize with Materials Project entries.

        Args:
            mp_entries: List of MPEntry objects from MPCache
        """
        self.entries = mp_entries
        self._build_indices()

    def _build_indices(self):
        """Build search indices for fast lookup."""
        # Element index: element -> [entry, ...]
        self.by_element = {}

        # Formula index: formula -> entry
        self.by_formula = {}

        # MP ID index: mp_id -> entry
        self.by_mp_id = {}

        # Crystal system index: system -> [entry, ...]
        self.by_crystal_system = {}

        # Category index: category -> [entry, ...]
        self.by_category = {cat: [] for cat in self.CATEGORY_PATTERNS.keys()}
        self.by_category["unknown"] = []

        for entry in self.entries:
            # Formula index
            self.by_formula[entry.formula] = entry

            # MP ID index
            self.by_mp_id[entry.mp_id] = entry

            # Crystal system index
            cs = entry.crystal_system or "unknown"
            if cs not in self.by_crystal_system:
                self.by_crystal_system[cs] = []
            self.by_crystal_system[cs].append(entry)

            # Element index
            comp = entry.composition
            for elem in comp.keys():
                if elem not in self.by_element:
                    self.by_element[elem] = []
                self.by_element[elem].append(entry)

            # Category classification
            category = self._classify_category(comp)
            self.by_category[category].append(entry)

    def _classify_category(self, composition: Dict[str, float]) -> str:
        """Classify material into category based on composition."""
        elements = set(composition.keys())

        # Check for pure element (metal)
        if len(elements) == 1:
            return "metal"

        # Check category patterns (score by overlap)
        best_category = "unknown"
        best_score = 0

        for category, required_elems in self.CATEGORY_PATTERNS.items():
            if not required_elems:  # Skip empty patterns
                continue

            # Score: how many required elements are present
            overlap = len(set(required_elems) & elements)
            if overlap > best_score:
                best_score = overlap
                best_category = category

        return best_category if best_score > 0 else "unknown"

    def search(
        self,
        query: str,
        limit: int = 20,
        category: Optional[str] = None,
        stable_only: bool = False,
    ) -> List[MaterialMatch]:
        """Search for materials matching query.

        Args:
            query: Search string (formula, element, MP ID, or shortcut)
            limit: Maximum number of results
            category: Filter by category (battery, semiconductor, etc.)
            stable_only: Only return stable materials (energy_above_hull == 0)

        Returns:
            List of MaterialMatch objects
        """
        if not query:
            return []

        query = query.strip()

        # Check for shortcuts
        query_upper = query.upper()
        if query_upper in self.SHORTCUTS:
            query = self.SHORTCUTS[query_upper]

        matches = []

        # Strategy 1: Exact formula match
        if query in self.by_formula:
            entry = self.by_formula[query]
            matches.append(self._entry_to_match(entry))

        # Strategy 2: MP ID match
        if query.startswith("mp-") or query.startswith("mvc-"):
            if query in self.by_mp_id:
                entry = self.by_mp_id[query]
                matches.append(self._entry_to_match(entry))

        # Strategy 3: Element search (contains element)
        if len(query) <= 2 and query.capitalize() in self.by_element:
            elem = query.capitalize()
            for entry in self.by_element[elem][:limit]:
                matches.append(self._entry_to_match(entry))

        # Strategy 4: Substring search in formula
        if not matches or len(matches) < limit:
            for formula, entry in self.by_formula.items():
                if len(matches) >= limit:
                    break
                if query.lower() in formula.lower():
                    match = self._entry_to_match(entry)
                    if match not in matches:
                        matches.append(match)

        # Filter by category if specified
        if category and category != "all":
            matches = [m for m in matches if m.category == category]

        # Filter by stability if requested
        if stable_only:
            matches = [m for m in matches if m.is_stable]

        return matches[:limit]

    def _entry_to_match(self, entry) -> MaterialMatch:
        """Convert MPEntry to MaterialMatch."""
        comp = entry.composition
        category = self._classify_category(comp)

        return MaterialMatch(
            formula=entry.formula,
            mp_id=entry.mp_id,
            crystal_system=entry.crystal_system or "unknown",
            formation_energy=entry.formation_energy_per_atom,
            above_hull=entry.energy_above_hull,
            is_stable=(entry.energy_above_hull == 0.0),
            category=category,
        )

    def get_popular_materials(self, limit: int = 10) -> List[MaterialMatch]:
        """Get popular/common materials for quick selection.

        Returns:
            List of MaterialMatch for well-known materials
        """
        popular_formulas = [
            "LiFePO4",  # LFP battery cathode
            "LiCoO2",  # LCO battery cathode
            "LiNi0.8Mn0.1Co0.1O2",  # NMC811
            "Li7La3Zr2O12",  # LLZO solid electrolyte
            "TiO2",  # Titania (photocatalyst, pigment)
            "Al2O3",  # Alumina (ceramic)
            "Si",  # Silicon (semiconductor)
            "GaAs",  # Gallium arsenide (III-V semiconductor)
            "CsPbBr3",  # Perovskite solar cell
            "SrTiO3",  # Strontium titanate (perovskite)
        ]

        matches = []
        for formula in popular_formulas:
            if formula in self.by_formula:
                entry = self.by_formula[formula]
                matches.append(self._entry_to_match(entry))
            if len(matches) >= limit:
                break

        return matches


def render_material_search(
    search_engine: MaterialSearchEngine,
    key: str = "material_search",
    label: str = "Search materials",
    category_filter: bool = True,
    stable_filter: bool = True,
) -> Optional[MaterialMatch]:
    """Render material search UI component.

    Args:
        search_engine: MaterialSearchEngine instance
        key: Unique key for Streamlit component
        label: Label for search box
        category_filter: Show category filter dropdown
        stable_filter: Show stable-only checkbox

    Returns:
        Selected MaterialMatch, or None if nothing selected
    """
    col_search, col_category, col_stable = st.columns([3, 1, 1])

    with col_search:
        query = st.text_input(
            label,
            placeholder="Type formula, element, or shortcut (e.g., Li, NMC811, mp-1234)",
            key=f"{key}_query",
        )

    category = "all"
    stable_only = False

    if category_filter:
        with col_category:
            category = st.selectbox(
                "Category",
                ["all", "battery_cathode", "battery_electrolyte", "semiconductor_iii_v",
                 "semiconductor_ii_vi", "perovskite", "oxide", "metal"],
                key=f"{key}_category",
            )

    if stable_filter:
        with col_stable:
            st.markdown("<br>", unsafe_allow_html=True)  # Align with search box
            stable_only = st.checkbox("Stable only", key=f"{key}_stable")

    # Search and display results
    if query:
        matches = search_engine.search(query, limit=20, category=category, stable_only=stable_only)

        if matches:
            st.caption(f"Found {len(matches)} matches")

            # Display as selectbox
            selected_idx = st.selectbox(
                "Select material",
                range(len(matches)),
                format_func=lambda i: matches[i].display_name(),
                key=f"{key}_select",
            )

            return matches[selected_idx]
        else:
            st.warning(f"No matches found for '{query}'")
            return None
    else:
        # Show popular materials when no query
        st.markdown("**Popular materials:**")
        popular = search_engine.get_popular_materials(limit=10)

        if popular:
            selected_idx = st.selectbox(
                "Quick select",
                range(len(popular)),
                format_func=lambda i: popular[i].display_name(),
                key=f"{key}_popular",
            )

            return popular[selected_idx]

    return None


def render_category_browser(
    search_engine: MaterialSearchEngine,
    key: str = "category_browser",
) -> Optional[MaterialMatch]:
    """Render category-based browser UI.

    Args:
        search_engine: MaterialSearchEngine instance
        key: Unique key for component

    Returns:
        Selected MaterialMatch or None
    """
    st.subheader("Browse by Category")

    # Show category counts
    category_counts = {
        cat: len(entries)
        for cat, entries in search_engine.by_category.items()
        if entries  # Only non-empty categories
    }

    # Sort by count
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    # Display category buttons
    selected_category = None
    cols = st.columns(4)

    category_icons = {
        "battery_cathode": "🔋",
        "battery_electrolyte": "⚡",
        "battery_anode": "🔌",
        "semiconductor_iii_v": "💎",
        "semiconductor_ii_vi": "🔬",
        "perovskite": "🧊",
        "oxide": "🌐",
        "metal": "🔧",
        "mof": "🧬",
        "unknown": "❓",
    }

    for i, (cat, count) in enumerate(sorted_categories[:8]):
        with cols[i % 4]:
            icon = category_icons.get(cat, "📦")
            label = cat.replace("_", " ").title()
            if st.button(f"{icon} {label}\n({count:,})", key=f"{key}_{cat}", use_container_width=True):
                selected_category = cat

    # If category selected, show materials from that category
    if selected_category:
        st.markdown(f"**{selected_category.replace('_', ' ').title()}** ({category_counts[selected_category]:,} materials)")

        entries = search_engine.by_category[selected_category][:50]  # Limit to 50
        matches = [search_engine._entry_to_match(e) for e in entries]

        if matches:
            selected_idx = st.selectbox(
                "Select material",
                range(len(matches)),
                format_func=lambda i: matches[i].display_name(),
                key=f"{key}_category_select",
            )

            return matches[selected_idx]

    return None
