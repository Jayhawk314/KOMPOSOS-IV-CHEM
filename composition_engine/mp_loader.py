# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Materials Project Data Loader + Cache

Downloads, caches, and loads Materials Project data for use with the
composition engine. The mp-api package is ONLY required for the initial
download (scripts/download_mp_data.py). Once cached, everything runs
on pure Python + numpy + scipy.

Cache format: gzipped JSON at data/cache/materials_project/mp_summaries.json.gz
with a companion mp_meta.json for metadata.

Without cached MP data, the system degrades gracefully to the existing
169-material baseline from the bridge loaders.

Usage:
    cache = MPCache()
    if cache.is_available():
        entries = cache.load_entries()
        print(f"Loaded {len(entries)} MP materials")
    else:
        print("No MP data cached. Run scripts/download_mp_data.py")
"""

from __future__ import annotations

import gzip
import json
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .parser import parse_formula, composition_vector, ELEMENT_TABLE

logger = logging.getLogger(__name__)

# Default cache directory
_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "materials_project"


@dataclass
class MPEntry:
    """A single Materials Project entry with computed properties.

    Fields mirror the most useful MP summary fields for compositional
    reasoning. Lattice parameters are stored for structure derivation.
    """
    mp_id: str
    formula: str
    composition: Dict[str, float] = field(default_factory=dict)
    vector: np.ndarray = field(default_factory=lambda: np.array([]))

    # Thermodynamic
    formation_energy_per_atom: float = 0.0  # eV/atom
    energy_above_hull: float = 0.0          # eV/atom (0 = on hull = stable)
    is_stable: bool = False                 # energy_above_hull == 0
    is_metal: bool = False

    # Electronic
    band_gap: float = 0.0                   # eV

    # Structural
    density: float = 0.0                    # g/cm^3
    volume: float = 0.0                     # Angstrom^3 per unit cell
    crystal_system: str = ""                # cubic, hexagonal, etc.
    space_group_symbol: str = ""            # Fm-3m, R-3m, etc.
    space_group_number: int = 0             # 1-230

    # Lattice parameters
    lattice_a: float = 0.0                  # Angstrom
    lattice_b: float = 0.0
    lattice_c: float = 0.0
    lattice_alpha: float = 90.0             # degrees
    lattice_beta: float = 90.0
    lattice_gamma: float = 90.0

    # Metadata
    theoretical: bool = False               # theoretically predicted (not experimental)

    def __post_init__(self):
        if not self.composition and self.formula:
            try:
                self.composition = parse_formula(self.formula)
            except Exception:
                self.composition = {}
        if len(self.vector) == 0 and self.composition:
            self.vector = composition_vector(self.composition)

    @property
    def volume_per_atom(self) -> float:
        """Volume per atom in Angstrom^3."""
        total_atoms = sum(self.composition.values()) if self.composition else 1
        if total_atoms > 0 and self.volume > 0:
            # volume is per unit cell; need to know Z (formula units per cell)
            # Approximate: use density and molar mass
            return self.volume / max(total_atoms, 1)
        return 0.0

    def to_dict(self) -> Dict:
        """Serialize to JSON-safe dict (no numpy arrays)."""
        return {
            "mp_id": self.mp_id,
            "formula": self.formula,
            "formation_energy_per_atom": self.formation_energy_per_atom,
            "energy_above_hull": self.energy_above_hull,
            "is_stable": self.is_stable,
            "is_metal": self.is_metal,
            "band_gap": self.band_gap,
            "density": self.density,
            "volume": self.volume,
            "crystal_system": self.crystal_system,
            "space_group_symbol": self.space_group_symbol,
            "space_group_number": self.space_group_number,
            "lattice_a": self.lattice_a,
            "lattice_b": self.lattice_b,
            "lattice_c": self.lattice_c,
            "lattice_alpha": self.lattice_alpha,
            "lattice_beta": self.lattice_beta,
            "lattice_gamma": self.lattice_gamma,
            "theoretical": self.theoretical,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "MPEntry":
        """Deserialize from dict (as stored in cache)."""
        return cls(
            mp_id=d.get("mp_id", ""),
            formula=d.get("formula", ""),
            formation_energy_per_atom=d.get("formation_energy_per_atom", 0.0),
            energy_above_hull=d.get("energy_above_hull", 0.0),
            is_stable=d.get("is_stable", False),
            is_metal=d.get("is_metal", False),
            band_gap=d.get("band_gap", 0.0),
            density=d.get("density", 0.0),
            volume=d.get("volume", 0.0),
            crystal_system=d.get("crystal_system", ""),
            space_group_symbol=d.get("space_group_symbol", ""),
            space_group_number=d.get("space_group_number", 0),
            lattice_a=d.get("lattice_a", 0.0),
            lattice_b=d.get("lattice_b", 0.0),
            lattice_c=d.get("lattice_c", 0.0),
            lattice_alpha=d.get("lattice_alpha", 90.0),
            lattice_beta=d.get("lattice_beta", 90.0),
            lattice_gamma=d.get("lattice_gamma", 90.0),
            theoretical=d.get("theoretical", False),
        )


class MPCache:
    """
    Cache manager for Materials Project data.

    Downloads MP data via mp-api (one-time), stores as gzipped JSON,
    and loads entries without needing mp-api installed.

    Usage:
        cache = MPCache()
        if not cache.is_available():
            # Only place needing mp-api
            count = cache.download(api_key="your_key")
            print(f"Downloaded {count} materials")

        entries = cache.load_entries()
    """

    SUMMARY_FILE = "mp_summaries.json.gz"
    META_FILE = "mp_meta.json"

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR

    @property
    def summary_path(self) -> Path:
        return self.cache_dir / self.SUMMARY_FILE

    @property
    def meta_path(self) -> Path:
        return self.cache_dir / self.META_FILE

    def is_available(self) -> bool:
        """Check if cached MP data exists."""
        return self.summary_path.exists() and self.meta_path.exists()

    def entry_count(self) -> int:
        """Read entry count from metadata without loading all entries."""
        if not self.meta_path.exists():
            return 0
        try:
            with open(self.meta_path, 'r') as f:
                meta = json.load(f)
            return meta.get("count", 0)
        except (json.JSONDecodeError, OSError):
            return 0

    def download(self, api_key: Optional[str] = None,
                 include_unstable: bool = False) -> int:
        """
        Download materials from Materials Project API and cache locally.

        This is the ONLY function that imports mp-api. All other operations
        work from the cached file.

        Args:
            api_key: Materials Project API key. If None, reads MP_API_KEY env var.
            include_unstable: If True, include materials above convex hull.

        Returns:
            Number of materials downloaded.

        Raises:
            ImportError: If mp-api is not installed.
            ValueError: If no API key provided.
        """
        try:
            from mp_api.client import MPRester
        except ImportError:
            raise ImportError(
                "mp-api is required for downloading MP data. "
                "Install with: pip install mp-api\n"
                "This is only needed once for the initial download."
            )

        api_key = api_key or os.environ.get("MP_API_KEY")
        if not api_key:
            raise ValueError(
                "Materials Project API key required. "
                "Set MP_API_KEY env var or pass api_key parameter. "
                "Get a key at https://materialsproject.org/api"
            )

        logger.info("Downloading Materials Project data...")

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        entries_data = []

        with MPRester(api_key) as mpr:
            # Query for all materials with key fields
            fields = [
                "material_id", "formula_pretty",
                "formation_energy_per_atom", "energy_above_hull",
                "is_stable", "is_metal", "band_gap",
                "density", "volume",
                "symmetry",
                "structure",
                "theoretical",
            ]

            # Build query filters
            kwargs = {}
            if not include_unstable:
                kwargs["energy_above_hull"] = (None, 0.1)  # Stable or near-stable

            docs = mpr.summary.search(
                fields=fields,
                **kwargs,
            )

            logger.info(f"Retrieved {len(docs)} materials from MP API")

            for doc in docs:
                try:
                    entry_dict = self._doc_to_dict(doc)
                    if entry_dict:
                        entries_data.append(entry_dict)
                except Exception as e:
                    logger.debug(f"Skipping {getattr(doc, 'material_id', '?')}: {e}")
                    continue

        # Write gzipped JSON
        logger.info(f"Caching {len(entries_data)} entries to {self.summary_path}")
        with gzip.open(self.summary_path, 'wt', encoding='utf-8') as f:
            json.dump(entries_data, f)

        # Write metadata
        import datetime
        meta = {
            "count": len(entries_data),
            "downloaded": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "include_unstable": include_unstable,
            "version": "1.0",
        }
        with open(self.meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        logger.info(f"MP data cached: {len(entries_data)} materials")
        return len(entries_data)

    def _doc_to_dict(self, doc) -> Optional[Dict]:
        """Convert an MP summary document to a serializable dict."""
        mp_id = str(getattr(doc, 'material_id', ''))
        formula = getattr(doc, 'formula_pretty', '')
        if not mp_id or not formula:
            return None

        # Extract symmetry info
        symmetry = getattr(doc, 'symmetry', None)
        crystal_system = ""
        space_group_symbol = ""
        space_group_number = 0
        if symmetry:
            crystal_system = getattr(symmetry, 'crystal_system', '') or ''
            if hasattr(crystal_system, 'value'):
                crystal_system = crystal_system.value
            crystal_system = str(crystal_system).lower()
            space_group_symbol = getattr(symmetry, 'symbol', '') or ''
            space_group_number = getattr(symmetry, 'number', 0) or 0

        # Extract lattice parameters from structure
        lattice_a = lattice_b = lattice_c = 0.0
        lattice_alpha = lattice_beta = lattice_gamma = 90.0
        structure = getattr(doc, 'structure', None)
        if structure and hasattr(structure, 'lattice'):
            lattice = structure.lattice
            lattice_a = getattr(lattice, 'a', 0.0) or 0.0
            lattice_b = getattr(lattice, 'b', 0.0) or 0.0
            lattice_c = getattr(lattice, 'c', 0.0) or 0.0
            lattice_alpha = getattr(lattice, 'alpha', 90.0) or 90.0
            lattice_beta = getattr(lattice, 'beta', 90.0) or 90.0
            lattice_gamma = getattr(lattice, 'gamma', 90.0) or 90.0

        return {
            "mp_id": mp_id,
            "formula": formula,
            "formation_energy_per_atom": getattr(doc, 'formation_energy_per_atom', 0.0) or 0.0,
            "energy_above_hull": getattr(doc, 'energy_above_hull', 0.0) or 0.0,
            "is_stable": bool(getattr(doc, 'is_stable', False)),
            "is_metal": bool(getattr(doc, 'is_metal', False)),
            "band_gap": getattr(doc, 'band_gap', 0.0) or 0.0,
            "density": getattr(doc, 'density', 0.0) or 0.0,
            "volume": getattr(doc, 'volume', 0.0) or 0.0,
            "crystal_system": crystal_system,
            "space_group_symbol": space_group_symbol,
            "space_group_number": space_group_number,
            "lattice_a": lattice_a,
            "lattice_b": lattice_b,
            "lattice_c": lattice_c,
            "lattice_alpha": lattice_alpha,
            "lattice_beta": lattice_beta,
            "lattice_gamma": lattice_gamma,
            "theoretical": bool(getattr(doc, 'theoretical', False)),
        }

    def load_entries(self) -> List[MPEntry]:
        """
        Load all MP entries from cache. No mp-api needed.

        Returns:
            List of MPEntry with composition vectors computed.

        Raises:
            FileNotFoundError: If cache doesn't exist.
        """
        if not self.is_available():
            raise FileNotFoundError(
                f"MP cache not found at {self.cache_dir}. "
                "Run: python scripts/download_mp_data.py"
            )

        logger.info(f"Loading MP data from {self.summary_path}")

        with gzip.open(self.summary_path, 'rt', encoding='utf-8') as f:
            raw_entries = json.load(f)

        entries = []
        skipped = 0
        for d in raw_entries:
            try:
                entry = MPEntry.from_dict(d)
                # Skip entries with unparseable formulas
                if not entry.composition:
                    skipped += 1
                    continue
                entries.append(entry)
            except Exception:
                skipped += 1
                continue

        if skipped > 0:
            logger.debug(f"Skipped {skipped} entries with unparseable formulas")

        logger.info(f"Loaded {len(entries)} MP entries")
        return entries

    def load_entries_with_lattice(self) -> List[MPEntry]:
        """Load only entries that have valid lattice parameters."""
        entries = self.load_entries()
        return [e for e in entries if e.lattice_a > 0 and e.lattice_b > 0 and e.lattice_c > 0]

    def clear(self):
        """Remove cached MP data."""
        if self.summary_path.exists():
            self.summary_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()


def classify_mp_domain(comp: Dict[str, float]) -> str:
    """
    Classify an MP material into a KOMPOSOS domain from composition.

    Used to assign domains to MP entries so they integrate with
    existing bridge-based nearest_k queries.

    Returns one of: "battery", "ceramic", "semiconductor", "metal", "other"
    """
    elements = set(comp.keys())
    has_li = "Li" in comp
    has_o = "O" in comp
    has_s = "S" in comp

    tm_elements = {"Ni", "Mn", "Co", "Fe", "Ti", "Cr", "V"}
    tms_present = elements & tm_elements
    tm_total = sum(comp.get(m, 0) for m in tm_elements)

    # Battery: Li + transition metal + O/S (cathodes, electrolytes)
    if has_li and (has_o or has_s) and (tms_present or "P" in comp or "La" in comp or "Zr" in comp or "Ge" in comp):
        return "battery"

    # Semiconductor: band gap materials, III-V, II-VI
    semiconductor_elements = {"Ga", "In", "As", "Ge", "Se", "Te", "Cd"}
    if elements & semiconductor_elements:
        return "semiconductor"
    if elements == {"Si"} or (len(elements) <= 2 and "Si" in comp and not has_o):
        return "semiconductor"

    # Metal: pure elements or simple alloys without anions
    anion_elements = {"O", "S", "F", "Cl", "Br", "N"}
    if not (elements & anion_elements) and len(elements) <= 3:
        return "metal"

    # Ceramic: oxides, nitrides, carbides without Li
    if (has_o or "N" in comp) and not has_li:
        return "ceramic"

    return "other"


if __name__ == "__main__":
    cache = MPCache()
    if cache.is_available():
        count = cache.entry_count()
        print(f"MP cache available: {count} entries")
        entries = cache.load_entries()
        print(f"Loaded {len(entries)} entries")

        # Show some stats
        stable = sum(1 for e in entries if e.is_stable)
        with_lattice = sum(1 for e in entries if e.lattice_a > 0)
        print(f"  Stable (on hull): {stable}")
        print(f"  With lattice data: {with_lattice}")

        # Show first 5
        for e in entries[:5]:
            print(f"  {e.mp_id:12s} {e.formula:20s} Ef={e.formation_energy_per_atom:+.3f} "
                  f"{e.crystal_system:10s} {e.space_group_symbol:8s} "
                  f"a={e.lattice_a:.3f}")
    else:
        print("MP cache not available.")
        print("Run: python scripts/download_mp_data.py")
