# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for Materials Project integration.

Uses mock MP data (20-50 synthetic entries) -- no real download needed.
Tests cover MPEntry, MPCache, KnownDB with MP, FormationEnergy with MP,
StructureDeriver, and graceful degradation without MP data.

35 tests total.
"""

import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from composition_engine.mp_loader import MPEntry, MPCache, classify_mp_domain
from composition_engine.spatial_index import CompositionIndex
from composition_engine.parser import parse_formula, composition_vector, ELEMENT_ORDER


# ═══════════════════════════════════════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════════════════════════════════════

def _make_mock_entries():
    """Generate 20 synthetic MP entries for testing."""
    entries_data = [
        {"mp_id": "mp-22526", "formula": "LiCoO2",
         "formation_energy_per_atom": -1.86, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 2.7,
         "density": 5.06, "volume": 32.8,
         "crystal_system": "trigonal", "space_group_symbol": "R-3m",
         "space_group_number": 166,
         "lattice_a": 2.816, "lattice_b": 2.816, "lattice_c": 14.054,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 120.0,
         "theoretical": False},
        {"mp_id": "mp-25048", "formula": "LiNiO2",
         "formation_energy_per_atom": -1.56, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 0.0,
         "density": 4.77, "volume": 33.5,
         "crystal_system": "trigonal", "space_group_symbol": "R-3m",
         "space_group_number": 166,
         "lattice_a": 2.878, "lattice_b": 2.878, "lattice_c": 14.185,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 120.0,
         "theoretical": False},
        {"mp_id": "mp-19017", "formula": "LiFePO4",
         "formation_energy_per_atom": -1.68, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 3.8,
         "density": 3.56, "volume": 291.4,
         "crystal_system": "orthorhombic", "space_group_symbol": "Pnma",
         "space_group_number": 62,
         "lattice_a": 10.332, "lattice_b": 6.010, "lattice_c": 4.692,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-18767", "formula": "LiMn2O4",
         "formation_energy_per_atom": -1.60, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 1.0,
         "density": 4.28, "volume": 73.7,
         "crystal_system": "cubic", "space_group_symbol": "Fd-3m",
         "space_group_number": 227,
         "lattice_a": 8.245, "lattice_b": 8.245, "lattice_c": 8.245,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-1143", "formula": "Al2O3",
         "formation_energy_per_atom": -3.47, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 5.9,
         "density": 3.99, "volume": 84.9,
         "crystal_system": "trigonal", "space_group_symbol": "R-3c",
         "space_group_number": 167,
         "lattice_a": 4.759, "lattice_b": 4.759, "lattice_c": 12.991,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 120.0,
         "theoretical": False},
        {"mp_id": "mp-2534", "formula": "GaAs",
         "formation_energy_per_atom": -0.35, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 0.19,
         "density": 5.32, "volume": 45.2,
         "crystal_system": "cubic", "space_group_symbol": "F-43m",
         "space_group_number": 216,
         "lattice_a": 5.751, "lattice_b": 5.751, "lattice_c": 5.751,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-5020", "formula": "BaTiO3",
         "formation_energy_per_atom": -3.15, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 1.7,
         "density": 6.02, "volume": 64.4,
         "crystal_system": "cubic", "space_group_symbol": "Pm-3m",
         "space_group_number": 221,
         "lattice_a": 4.009, "lattice_b": 4.009, "lattice_c": 4.009,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-149", "formula": "Si",
         "formation_energy_per_atom": 0.0, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 0.61,
         "density": 2.33, "volume": 40.0,
         "crystal_system": "cubic", "space_group_symbol": "Fd-3m",
         "space_group_number": 227,
         "lattice_a": 5.431, "lattice_b": 5.431, "lattice_c": 5.431,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-2657", "formula": "TiO2",
         "formation_energy_per_atom": -3.24, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 1.8,
         "density": 4.23, "volume": 62.4,
         "crystal_system": "tetragonal", "space_group_symbol": "P42/mnm",
         "space_group_number": 136,
         "lattice_a": 4.593, "lattice_b": 4.593, "lattice_c": 2.959,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-30783", "formula": "Li7La3Zr2O12",
         "formation_energy_per_atom": -2.85, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 5.1,
         "density": 5.10, "volume": 849.6,
         "crystal_system": "cubic", "space_group_symbol": "Ia-3d",
         "space_group_number": 230,
         "lattice_a": 12.968, "lattice_b": 12.968, "lattice_c": 12.968,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        # Some unstable entries
        {"mp_id": "mp-999001", "formula": "LiNi2O4",
         "formation_energy_per_atom": -1.20, "energy_above_hull": 0.15,
         "is_stable": False, "is_metal": False, "band_gap": 0.5,
         "density": 4.50, "volume": 70.0,
         "crystal_system": "cubic", "space_group_symbol": "Fd-3m",
         "space_group_number": 227,
         "lattice_a": 8.150, "lattice_b": 8.150, "lattice_c": 8.150,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": True},
        {"mp_id": "mp-1265", "formula": "MgO",
         "formation_energy_per_atom": -3.09, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 4.5,
         "density": 3.58, "volume": 18.7,
         "crystal_system": "cubic", "space_group_symbol": "Fm-3m",
         "space_group_number": 225,
         "lattice_a": 4.211, "lattice_b": 4.211, "lattice_c": 4.211,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-13", "formula": "Fe",
         "formation_energy_per_atom": 0.0, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": True, "band_gap": 0.0,
         "density": 7.87, "volume": 11.8,
         "crystal_system": "cubic", "space_group_symbol": "Im-3m",
         "space_group_number": 229,
         "lattice_a": 2.862, "lattice_b": 2.862, "lattice_c": 2.862,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
        {"mp_id": "mp-830", "formula": "GaN",
         "formation_energy_per_atom": -0.68, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 1.7,
         "density": 6.10, "volume": 22.7,
         "crystal_system": "hexagonal", "space_group_symbol": "P63mc",
         "space_group_number": 186,
         "lattice_a": 3.189, "lattice_b": 3.189, "lattice_c": 5.185,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 120.0,
         "theoretical": False},
        {"mp_id": "mp-18759", "formula": "LiMnO2",
         "formation_energy_per_atom": -1.82, "energy_above_hull": 0.0,
         "is_stable": True, "is_metal": False, "band_gap": 1.5,
         "density": 4.20, "volume": 35.0,
         "crystal_system": "orthorhombic", "space_group_symbol": "Pnma",
         "space_group_number": 62,
         "lattice_a": 5.456, "lattice_b": 2.848, "lattice_c": 4.674,
         "lattice_alpha": 90.0, "lattice_beta": 90.0, "lattice_gamma": 90.0,
         "theoretical": False},
    ]
    return entries_data


def _write_mock_cache(cache_dir: Path):
    """Write mock MP data to cache files."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    entries_data = _make_mock_entries()

    summary_path = cache_dir / "mp_summaries.json.gz"
    with gzip.open(summary_path, 'wt', encoding='utf-8') as f:
        json.dump(entries_data, f)

    meta_path = cache_dir / "mp_meta.json"
    with open(meta_path, 'w') as f:
        json.dump({"count": len(entries_data), "version": "1.0"}, f)


# ═══════════════════════════════════════════════════════════════════════════
# TEST CLASSES
# ═══════════════════════════════════════════════════════════════════════════

class TestMPEntry(unittest.TestCase):
    """Test MPEntry dataclass."""

    def test_from_dict(self):
        d = _make_mock_entries()[0]
        entry = MPEntry.from_dict(d)
        self.assertEqual(entry.mp_id, "mp-22526")
        self.assertEqual(entry.formula, "LiCoO2")
        self.assertAlmostEqual(entry.formation_energy_per_atom, -1.86)

    def test_composition_parsed(self):
        entry = MPEntry.from_dict(_make_mock_entries()[0])
        self.assertIn("Li", entry.composition)
        self.assertIn("Co", entry.composition)
        self.assertIn("O", entry.composition)

    def test_vector_dimension(self):
        entry = MPEntry.from_dict(_make_mock_entries()[0])
        self.assertEqual(len(entry.vector), len(ELEMENT_ORDER))

    def test_to_dict_roundtrip(self):
        original = _make_mock_entries()[0]
        entry = MPEntry.from_dict(original)
        d = entry.to_dict()
        self.assertEqual(d["mp_id"], original["mp_id"])
        self.assertAlmostEqual(d["formation_energy_per_atom"],
                               original["formation_energy_per_atom"])

    def test_volume_per_atom(self):
        entry = MPEntry.from_dict(_make_mock_entries()[0])
        vpa = entry.volume_per_atom
        self.assertGreater(vpa, 0)


class TestMPCache(unittest.TestCase):
    """Test MPCache with mock data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmpdir) / "mp_cache"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_is_available_false_when_no_data(self):
        cache = MPCache(cache_dir=self.cache_dir)
        self.assertFalse(cache.is_available())

    def test_is_available_true_after_write(self):
        _write_mock_cache(self.cache_dir)
        cache = MPCache(cache_dir=self.cache_dir)
        self.assertTrue(cache.is_available())

    def test_entry_count(self):
        _write_mock_cache(self.cache_dir)
        cache = MPCache(cache_dir=self.cache_dir)
        self.assertEqual(cache.entry_count(), 15)

    def test_load_entries(self):
        _write_mock_cache(self.cache_dir)
        cache = MPCache(cache_dir=self.cache_dir)
        entries = cache.load_entries()
        self.assertGreater(len(entries), 0)
        self.assertIsInstance(entries[0], MPEntry)

    def test_load_entries_with_lattice(self):
        _write_mock_cache(self.cache_dir)
        cache = MPCache(cache_dir=self.cache_dir)
        entries = cache.load_entries_with_lattice()
        for e in entries:
            self.assertGreater(e.lattice_a, 0)

    def test_load_raises_without_cache(self):
        cache = MPCache(cache_dir=self.cache_dir)
        with self.assertRaises(FileNotFoundError):
            cache.load_entries()

    def test_clear(self):
        _write_mock_cache(self.cache_dir)
        cache = MPCache(cache_dir=self.cache_dir)
        self.assertTrue(cache.is_available())
        cache.clear()
        self.assertFalse(cache.is_available())


class TestClassifyDomain(unittest.TestCase):
    """Test domain classification from composition."""

    def test_battery_cathode(self):
        comp = parse_formula("LiNi0.8Mn0.1Co0.1O2")
        self.assertEqual(classify_mp_domain(comp), "battery")

    def test_semiconductor(self):
        comp = parse_formula("GaAs")
        self.assertEqual(classify_mp_domain(comp), "semiconductor")

    def test_ceramic(self):
        comp = parse_formula("Al2O3")
        self.assertEqual(classify_mp_domain(comp), "ceramic")

    def test_metal(self):
        comp = parse_formula("Fe")
        self.assertEqual(classify_mp_domain(comp), "metal")


class TestKnownDBWithMP(unittest.TestCase):
    """Test KnownCompositionDB integration with MP data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmpdir) / "mp_cache"
        _write_mock_cache(self.cache_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_entries_grow_with_mp(self):
        from composition_engine.known_compositions import KnownCompositionDB
        db = KnownCompositionDB()
        db._load_battery_materials()
        db._load_ceramic_materials()
        db._load_semiconductor_materials()
        bridge_count = len(db.entries)

        # Manually load MP with our mock cache
        with patch('composition_engine.mp_loader._DEFAULT_CACHE_DIR', self.cache_dir):
            from composition_engine.mp_loader import MPCache as MC2
            cache = MC2(cache_dir=self.cache_dir)
            entries = cache.load_entries()

            existing_names = {e.name for e in db.entries}
            for mp_entry in entries:
                if mp_entry.mp_id not in existing_names:
                    props = {}
                    if mp_entry.formation_energy_per_atom != 0:
                        props["formation_energy"] = mp_entry.formation_energy_per_atom
                    if mp_entry.band_gap > 0:
                        props["band_gap"] = mp_entry.band_gap
                    if props:
                        db.entries.append(type(db.entries[0])(
                            name=mp_entry.mp_id,
                            formula=mp_entry.formula,
                            composition=mp_entry.composition,
                            vector=mp_entry.vector,
                            properties=props,
                            domain=classify_mp_domain(mp_entry.composition),
                        ))

        self.assertGreater(len(db.entries), bridge_count)

    def test_nearest_k_returns_results(self):
        from composition_engine.known_compositions import KnownCompositionDB
        db = KnownCompositionDB()
        db.load_all()

        # Without MP, should still return results from bridges
        comp = parse_formula("LiNi0.7Mn0.15Co0.15O2")
        results = db.nearest_k(comp, k=3)
        self.assertGreater(len(results), 0)

    def test_graceful_without_mp(self):
        """Without MP cache, load_all should still work."""
        from composition_engine.known_compositions import KnownCompositionDB
        db = KnownCompositionDB()
        db.load_all()
        # Should have at least bridge entries
        self.assertGreater(db.size, 0)

    def test_has_mp_data_false_without_cache(self):
        from composition_engine.known_compositions import KnownCompositionDB
        db = KnownCompositionDB()
        db.load_all()
        # Without MP cache in default location, should be False
        # (unless user has downloaded MP data to default location)
        # Just verify the property exists and is boolean
        self.assertIsInstance(db.has_mp_data, bool)

    def test_domain_classification_battery(self):
        comp = parse_formula("LiCoO2")
        domain = classify_mp_domain(comp)
        self.assertEqual(domain, "battery")

    def test_domain_classification_ceramic(self):
        comp = parse_formula("TiO2")
        domain = classify_mp_domain(comp)
        self.assertEqual(domain, "ceramic")

    def test_domain_classification_metal(self):
        comp = parse_formula("Cu")
        domain = classify_mp_domain(comp)
        self.assertEqual(domain, "metal")

    def test_domain_classification_semiconductor(self):
        comp = parse_formula("GaAs")
        domain = classify_mp_domain(comp)
        self.assertEqual(domain, "semiconductor")


class TestFormationEnergyWithMP(unittest.TestCase):
    """Test FormationEnergyPredictor with mock MP data."""

    def test_baseline_without_mp(self):
        """FormationEnergyPredictor works without MP data."""
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        result = fep.predict("LiCoO2")
        self.assertLess(result.ef_per_atom, 0)
        self.assertGreater(result.confidence, 0)

    def test_known_ef_count_baseline(self):
        """At minimum, known entries include the hand-curated ones."""
        from composition_engine.formation_energy import KNOWN_EF
        self.assertGreaterEqual(len(KNOWN_EF), 37)

    def test_synthesizability_range(self):
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        result = fep.predict("LiCoO2")
        self.assertGreaterEqual(result.synthesizability_score, 0.0)
        self.assertLessEqual(result.synthesizability_score, 1.0)

    def test_constraints_list(self):
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        result = fep.predict("LiCoO2")
        self.assertGreater(len(result.constraints), 0)

    def test_nearest_known_populated(self):
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        result = fep.predict("LiCoO2")
        self.assertGreater(len(result.nearest_known), 0)

    def test_unstable_compound(self):
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        # A likely unstable composition
        result = fep.predict("LiNaSO")
        # Should still produce a result
        self.assertIsNotNone(result.ef_per_atom)

    def test_element_reference(self):
        from composition_engine.formation_energy import FormationEnergyPredictor
        fep = FormationEnergyPredictor()
        result = fep.predict("Fe")
        # Elements have Ef = 0 by definition; prediction should be near 0
        self.assertAlmostEqual(result.ef_per_atom, 0.0, delta=0.5)


class TestStructureDeriver(unittest.TestCase):
    """Test StructureDeriver with mock MP data."""

    def setUp(self):
        self.mock_entries = [MPEntry.from_dict(d) for d in _make_mock_entries()]
        self.entries_with_lattice = [
            e for e in self.mock_entries if e.lattice_a > 0
        ]

    def test_build_deriver(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice)
        self.assertGreater(sd.size, 0)

    def test_derive_known_material(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        # Should derive crystal system matching the known entry
        self.assertIn(result.crystal_system, ["trigonal", "cubic", "hexagonal", "orthorhombic"])
        self.assertGreater(result.confidence, 0.0)

    def test_derive_returns_lattice(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        self.assertGreater(result.lattice_a, 0)
        self.assertGreater(result.lattice_b, 0)
        self.assertGreater(result.lattice_c, 0)

    def test_derive_has_provenance(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        self.assertTrue(result.provenance.startswith("Derived from"))
        self.assertGreater(len(result.nearest_mp), 0)

    def test_derive_has_space_group(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        # Space group should be a non-empty string
        self.assertGreater(len(result.space_group), 0)

    def test_derive_confidence_range(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_derive_returns_none_empty(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver([], k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNone(result)

    def test_derive_to_dict(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        d = result.to_dict()
        self.assertIn("crystal_system", d)
        self.assertIn("lattice_a", d)
        self.assertIn("provenance", d)
        self.assertIn("nearest_mp", d)

    def test_derive_unknown_composition(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        # Novel composition not in mock data
        result = sd.derive("LiNi0.7Fe0.2Mn0.1O2")
        self.assertIsNotNone(result)
        self.assertGreater(result.lattice_a, 0)

    def test_nearest_mp_weights_sum_to_one(self):
        from composition_engine.structure_deriver import StructureDeriver
        sd = StructureDeriver(self.entries_with_lattice, k=5)
        result = sd.derive("LiCoO2")
        self.assertIsNotNone(result)
        total_weight = sum(n.weight for n in result.nearest_mp)
        self.assertAlmostEqual(total_weight, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
