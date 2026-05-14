# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Known Compositions Database

Extracts compositions + measured properties from existing material bridges
and builds a queryable database for Kan extension nearest-neighbour lookup.

This is the "known" category: objects are real materials with real data.
The predictor extends from this to unknown compositions.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

from .parser import parse_formula, composition_vector, composition_distance

if TYPE_CHECKING:
    from .spatial_index import CompositionIndex

logger = logging.getLogger(__name__)


@dataclass
class KnownComposition:
    """A known material with parsed composition and measured properties."""
    name: str
    formula: str
    composition: Dict[str, float]
    vector: np.ndarray
    properties: Dict[str, float]   # property_name -> measured value
    domain: str                    # "battery", "ceramic", "semiconductor"


class KnownCompositionDB:
    """
    Database of known compositions from existing bridges.

    Supports nearest-k queries in composition space for
    Kan extension neighbourhood construction.
    """

    def __init__(self):
        self.entries: List[KnownComposition] = []
        self._loaded = False
        self._index: Optional["CompositionIndex"] = None
        self._has_mp_data = False

    def add(self, name: str, formula: str,
            properties: Dict[str, float], domain: str):
        """Add a known composition to the database."""
        comp = parse_formula(formula)
        vec = composition_vector(comp)
        self.entries.append(KnownComposition(
            name=name, formula=formula,
            composition=comp, vector=vec,
            properties=properties, domain=domain,
        ))

    def load_all(self):
        """Load all known compositions from existing bridges + MP data."""
        if self._loaded:
            return
        self._load_battery_materials()
        self._load_ceramic_materials()
        self._load_semiconductor_materials()
        self._load_polymer_materials()
        self._load_metal_materials()
        self._load_glass_materials()
        self._load_mof_materials()
        self._load_mp_materials()
        self._loaded = True

    def nearest_k(self, query_comp: Dict[str, float], k: int = 5,
                  domain: Optional[str] = None,
                  exclude_names: Optional[List[str]] = None
                  ) -> List[Tuple[KnownComposition, float]]:
        """
        Find k nearest known compositions by Euclidean distance.

        Uses KD-tree fast path when entries > 500 and no domain filter
        or excludes are set. Falls back to linear scan otherwise.

        Args:
            query_comp: Parsed composition dict
            k: Number of neighbours
            domain: Optional filter to single domain
            exclude_names: Names to exclude (for leave-one-out)

        Returns:
            List of (KnownComposition, distance) sorted by distance.
        """
        if not self._loaded:
            self.load_all()

        exclude = set(exclude_names or [])
        query_vec = composition_vector(query_comp)

        # KD-tree fast path: no domain filter and no excludes
        if not domain and not exclude and self._index is not None:
            return self._index.nearest_k(query_vec, k=k)

        # KD-tree with over-fetch + post-filter when we have filters
        if self._index is not None and len(self.entries) > 500:
            # Over-fetch to compensate for filtering
            over_k = k * 5
            candidates = self._index.nearest_k(query_vec, k=over_k)
            filtered = []
            for entry, dist in candidates:
                if domain and entry.domain != domain:
                    continue
                if entry.name in exclude:
                    continue
                filtered.append((entry, dist))
                if len(filtered) >= k:
                    break
            return filtered

        # Linear scan fallback (original behavior)
        distances = []
        for entry in self.entries:
            if domain and entry.domain != domain:
                continue
            if entry.name in exclude:
                continue
            dist = float(np.linalg.norm(query_vec - entry.vector))
            distances.append((entry, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:k]

    def get_by_name(self, name: str) -> Optional[KnownComposition]:
        """Look up a known composition by name."""
        if not self._loaded:
            self.load_all()
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    @property
    def size(self) -> int:
        if not self._loaded:
            self.load_all()
        return len(self.entries)

    @property
    def has_mp_data(self) -> bool:
        """Whether Materials Project data is loaded."""
        if not self._loaded:
            self.load_all()
        return self._has_mp_data

    def _build_index(self):
        """Build KD-tree spatial index over all entries."""
        if len(self.entries) > 0:
            from .spatial_index import CompositionIndex
            self._index = CompositionIndex(self.entries)

    # ── Bridge loaders ──────────────────────────────────────────────────

    def _load_battery_materials(self):
        """Extract battery bridge materials with parseable formulas."""
        try:
            from battery_bridge.material_properties import ALL_MATERIALS
        except ImportError:
            return

        for name, mat in ALL_MATERIALS.items():
            props: Dict[str, float] = {}

            if mat.voltage_window:
                props["voltage"] = mat.voltage_window.nominal
            if mat.theoretical_capacity is not None:
                props["theoretical_capacity"] = mat.theoretical_capacity
            if mat.density is not None:
                props["density"] = mat.density
            if mat.thermal_stability_max is not None:
                props["thermal_stability"] = mat.thermal_stability_max
            if mat.volume_expansion is not None:
                props["volume_expansion"] = mat.volume_expansion
            if mat.ionic_conductivity is not None:
                props["ionic_conductivity"] = mat.ionic_conductivity

            if not props:
                continue

            self.add(name, mat.formula, props, "battery")

    def _load_ceramic_materials(self):
        """Extract ceramic bridge materials."""
        try:
            from ceramic_bridge.material_properties import ALL_CERAMICS
        except ImportError:
            return

        for name, mat in ALL_CERAMICS.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'density_g_cm3') and mat.density_g_cm3 is not None:
                props["density"] = mat.density_g_cm3
            if hasattr(mat, 'melting_point_C') and mat.melting_point_C is not None:
                props["melting_point"] = mat.melting_point_C
            if hasattr(mat, 'thermal_conductivity_W_mK') and mat.thermal_conductivity_W_mK is not None:
                props["thermal_conductivity"] = mat.thermal_conductivity_W_mK
            if hasattr(mat, 'hardness_HV') and mat.hardness_HV is not None:
                props["hardness"] = float(mat.hardness_HV)
            if hasattr(mat, 'fracture_toughness_MPa_m05') and mat.fracture_toughness_MPa_m05 is not None:
                props["fracture_toughness"] = mat.fracture_toughness_MPa_m05
            if hasattr(mat, 'cte_per_K') and mat.cte_per_K is not None:
                props["cte"] = mat.cte_per_K
            if hasattr(mat, 'elastic_modulus_GPa') and mat.elastic_modulus_GPa is not None:
                props["youngs_modulus"] = mat.elastic_modulus_GPa

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "ceramic")

    def _load_semiconductor_materials(self):
        """Extract semiconductor bridge materials."""
        try:
            from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS
        except ImportError:
            return

        for name, mat in ALL_SEMICONDUCTORS.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'band_gap_eV') and mat.band_gap_eV is not None:
                props["band_gap"] = mat.band_gap_eV
            if hasattr(mat, 'density_g_cm3') and mat.density_g_cm3 is not None:
                props["density"] = mat.density_g_cm3
            if hasattr(mat, 'electron_mobility_cm2_Vs') and mat.electron_mobility_cm2_Vs is not None:
                props["electron_mobility"] = mat.electron_mobility_cm2_Vs
            if hasattr(mat, 'lattice_constant_A') and mat.lattice_constant_A is not None:
                props["lattice_constant"] = mat.lattice_constant_A
            if hasattr(mat, 'melting_point_C') and mat.melting_point_C is not None:
                props["melting_point"] = mat.melting_point_C

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "semiconductor")

    def _load_polymer_materials(self):
        """Extract polymer bridge materials."""
        try:
            from polymer_bridge.material_properties import ALL_POLYMERS
        except ImportError:
            return

        for name, mat in ALL_POLYMERS.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'density_g_cm3') and mat.density_g_cm3 is not None:
                props["density"] = mat.density_g_cm3
            if hasattr(mat, 'glass_transition_C') and mat.glass_transition_C is not None:
                props["tg"] = mat.glass_transition_C
            if hasattr(mat, 'melting_point_C') and mat.melting_point_C is not None:
                props["tm"] = mat.melting_point_C
            if hasattr(mat, 'tensile_strength_MPa') and mat.tensile_strength_MPa is not None:
                props["tensile_strength"] = mat.tensile_strength_MPa
            if hasattr(mat, 'elongation_at_break_pct') and mat.elongation_at_break_pct is not None:
                props["elongation_at_break"] = mat.elongation_at_break_pct

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "polymer")

    def _load_metal_materials(self):
        """Extract metal bridge materials."""
        try:
            from metal_bridge.material_properties import ALL_METALS
        except ImportError:
            return

        for name, mat in ALL_METALS.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'density_g_cm3') and mat.density_g_cm3 is not None:
                props["density"] = mat.density_g_cm3
            if hasattr(mat, 'melting_point_C') and mat.melting_point_C is not None:
                props["melting_point"] = mat.melting_point_C
            if hasattr(mat, 'thermal_conductivity_W_mK') and mat.thermal_conductivity_W_mK is not None:
                props["thermal_conductivity"] = mat.thermal_conductivity_W_mK
            if hasattr(mat, 'elastic_modulus_GPa') and mat.elastic_modulus_GPa is not None:
                props["youngs_modulus"] = mat.elastic_modulus_GPa
            if hasattr(mat, 'yield_strength_MPa') and mat.yield_strength_MPa is not None:
                props["yield_strength"] = mat.yield_strength_MPa

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "metal")

    def _load_glass_materials(self):
        """Extract glass bridge materials."""
        try:
            from glass_bridge.material_properties import ALL_GLASSES
        except ImportError:
            return

        for name, mat in ALL_GLASSES.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'density_g_cm3') and mat.density_g_cm3 is not None:
                props["density"] = mat.density_g_cm3
            if hasattr(mat, 'softening_point_C') and mat.softening_point_C is not None:
                props["softening_point"] = mat.softening_point_C
            if hasattr(mat, 'thermal_conductivity_W_mK') and mat.thermal_conductivity_W_mK is not None:
                props["thermal_conductivity"] = mat.thermal_conductivity_W_mK
            if hasattr(mat, 'elastic_modulus_GPa') and mat.elastic_modulus_GPa is not None:
                props["youngs_modulus"] = mat.elastic_modulus_GPa

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "glass")

    def _load_mof_materials(self):
        """Extract MOF bridge materials."""
        try:
            from mof_bridge.material_properties import ALL_MOFS
        except ImportError:
            return

        for name, mat in ALL_MOFS.items():
            props: Dict[str, float] = {}

            if hasattr(mat, 'pore_diameter_angstrom') and mat.pore_diameter_angstrom is not None:
                props["pore_size"] = mat.pore_diameter_angstrom
            if hasattr(mat, 'bet_surface_area_m2g') and mat.bet_surface_area_m2g is not None:
                props["surface_area"] = mat.bet_surface_area_m2g
            if hasattr(mat, 'thermal_stability_C') and mat.thermal_stability_C is not None:
                props["thermal_stability"] = mat.thermal_stability_C

            if not props:
                continue

            formula = getattr(mat, 'formula', name)
            self.add(name, formula, props, "mof")

    def _load_mp_materials(self):
        """Load Materials Project data from cache (if available)."""
        try:
            from .mp_loader import MPCache, classify_mp_domain
        except ImportError:
            return

        cache = MPCache()
        if not cache.is_available():
            # Build index over bridge-only entries
            if len(self.entries) > 0:
                self._build_index()
            return

        try:
            mp_entries = cache.load_entries()
        except Exception as e:
            logger.debug(f"Failed to load MP data: {e}")
            if len(self.entries) > 0:
                self._build_index()
            return

        # Existing entry names for dedup
        existing_names = {e.name for e in self.entries}

        added = 0
        for mp_entry in mp_entries:
            # Use mp_id as name to avoid collisions
            name = mp_entry.mp_id
            if name in existing_names:
                continue

            # Build properties dict from MP data
            props: Dict[str, float] = {}
            if mp_entry.formation_energy_per_atom != 0:
                props["formation_energy"] = mp_entry.formation_energy_per_atom
            if mp_entry.band_gap > 0:
                props["band_gap"] = mp_entry.band_gap
            if mp_entry.density > 0:
                props["density"] = mp_entry.density

            if not props:
                continue

            # Classify domain from composition
            domain = classify_mp_domain(mp_entry.composition)

            self.entries.append(KnownComposition(
                name=name,
                formula=mp_entry.formula,
                composition=mp_entry.composition,
                vector=mp_entry.vector,
                properties=props,
                domain=domain,
            ))
            existing_names.add(name)
            added += 1

        if added > 0:
            self._has_mp_data = True
            logger.info(f"Loaded {added} MP materials (total: {len(self.entries)})")

        # Build spatial index over all entries
        self._build_index()


# Module-level singleton
_db: Optional[KnownCompositionDB] = None

def get_db() -> KnownCompositionDB:
    """Get or create the global KnownCompositionDB singleton."""
    global _db
    if _db is None:
        _db = KnownCompositionDB()
        _db.load_all()
    return _db


if __name__ == "__main__":
    db = get_db()
    print(f"Known compositions: {db.size}")
    print()

    # Show battery cathode neighbours for a query
    query = parse_formula("LiNi0.7Mn0.15Co0.15O2")
    neighbours = db.nearest_k(query, k=5, domain="battery")
    print(f"Nearest 5 to LiNi0.7Mn0.15Co0.15O2:")
    for entry, dist in neighbours:
        print(f"  {entry.name:10s} ({entry.formula:25s}) dist={dist:.3f}")
        for p, v in entry.properties.items():
            print(f"    {p}: {v}")
