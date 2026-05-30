# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for polymer material properties.

Verifies all polymer materials exist, have valid properties,
and are correctly classified.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from polymer_bridge.material_properties import (
    PolymerMaterial, PolymerClass, PolymerStructure, PolymerFailureMode,
    HansenParameters, ALL_POLYMERS, get_polymer, get_polymers_by_class,
    THERMOPLASTIC_POLYMERS, BATTERY_POLYMERS, ELASTOMER_POLYMERS,
    HIGH_PERFORMANCE_POLYMERS, THERMOSET_POLYMERS, POLYMER_SOLVENTS,
    KNOWN_GOOD_BLENDS, KNOWN_BAD_BLENDS,
    list_thermoplastics, list_elastomers, list_thermosets, list_battery_polymers,
)


class TestMaterialCount(unittest.TestCase):
    """Verify expected material counts."""

    def test_total_materials_at_least_30(self):
        self.assertGreaterEqual(len(ALL_POLYMERS), 30)

    def test_thermoplastics_exist(self):
        self.assertGreaterEqual(len(THERMOPLASTIC_POLYMERS), 10)

    def test_battery_polymers_exist(self):
        self.assertGreaterEqual(len(BATTERY_POLYMERS), 4)

    def test_elastomers_exist(self):
        self.assertGreaterEqual(len(ELASTOMER_POLYMERS), 4)

    def test_high_performance_exist(self):
        self.assertGreaterEqual(len(HIGH_PERFORMANCE_POLYMERS), 3)

    def test_thermosets_exist(self):
        self.assertGreaterEqual(len(THERMOSET_POLYMERS), 3)

    def test_solvents_exist(self):
        self.assertGreaterEqual(len(POLYMER_SOLVENTS), 3)


class TestMaterialLookup(unittest.TestCase):
    """Verify material lookup functions work."""

    def test_get_polymer_by_name(self):
        mat = get_polymer('PVDF')
        self.assertIsNotNone(mat)
        self.assertEqual(mat.abbreviation, 'PVDF')

    def test_get_polymer_returns_none_for_unknown(self):
        self.assertIsNone(get_polymer('NONEXISTENT'))

    def test_get_polymers_by_class(self):
        thermos = get_polymers_by_class(PolymerClass.THERMOPLASTIC)
        self.assertGreater(len(thermos), 0)
        for name, mat in thermos.items():
            self.assertEqual(mat.polymer_class, PolymerClass.THERMOPLASTIC)

    def test_list_functions(self):
        self.assertGreater(len(list_thermoplastics()), 0)
        self.assertGreater(len(list_elastomers()), 0)
        self.assertGreater(len(list_thermosets()), 0)
        self.assertGreater(len(list_battery_polymers()), 0)


class TestKeyPolymersExist(unittest.TestCase):
    """Verify essential polymers are in the database."""

    KEY_POLYMERS = [
        'HDPE', 'PP', 'PS', 'PPO', 'PMMA', 'PVC', 'PET', 'PA6', 'PA66',
        'PC', 'PEEK', 'POM', 'ABS',
        'PVDF', 'PEO', 'PTFE', 'CMC', 'PAN',
        'SBR', 'NR', 'NBR', 'PDMS', 'EPDM',
        'PI', 'PPS', 'PPSU', 'LCP',
        'Epoxy', 'Phenolic', 'UPE',
        'NMP', 'Water', 'Toluene', 'Acetone',
    ]

    def test_all_key_polymers_exist(self):
        for name in self.KEY_POLYMERS:
            with self.subTest(polymer=name):
                mat = get_polymer(name)
                self.assertIsNotNone(mat, f"Missing polymer: {name}")


class TestPropertyRanges(unittest.TestCase):
    """Verify property values are in physically reasonable ranges."""

    def test_tg_range(self):
        """Tg should be between -200C and 500C."""
        for name, mat in ALL_POLYMERS.items():
            if mat.glass_transition_C is not None:
                with self.subTest(polymer=name):
                    self.assertGreaterEqual(mat.glass_transition_C, -200)
                    self.assertLessEqual(mat.glass_transition_C, 500)

    def test_tm_range(self):
        """Tm should be between -100C and 500C."""
        for name, mat in ALL_POLYMERS.items():
            if mat.melting_point_C is not None:
                with self.subTest(polymer=name):
                    self.assertGreaterEqual(mat.melting_point_C, -100)
                    self.assertLessEqual(mat.melting_point_C, 500)

    def test_density_range(self):
        """Density should be between 0.5 and 3.0 g/cm3."""
        for name, mat in ALL_POLYMERS.items():
            if mat.density_g_cm3 is not None:
                with self.subTest(polymer=name):
                    self.assertGreater(mat.density_g_cm3, 0.5)
                    self.assertLess(mat.density_g_cm3, 3.0)

    def test_tensile_strength_range(self):
        """Tensile strength should be between 1 and 500 MPa."""
        for name, mat in ALL_POLYMERS.items():
            if mat.tensile_strength_MPa is not None:
                with self.subTest(polymer=name):
                    self.assertGreater(mat.tensile_strength_MPa, 0)
                    self.assertLess(mat.tensile_strength_MPa, 500)

    def test_modulus_range(self):
        """Elastic modulus should be between 0.0005 and 20 GPa."""
        for name, mat in ALL_POLYMERS.items():
            if mat.elastic_modulus_GPa is not None:
                with self.subTest(polymer=name):
                    self.assertGreater(mat.elastic_modulus_GPa, 0)
                    self.assertLess(mat.elastic_modulus_GPa, 20)

    def test_elongation_range(self):
        """Elongation at break should be between 0 and 1000%."""
        for name, mat in ALL_POLYMERS.items():
            if mat.elongation_at_break_pct is not None:
                with self.subTest(polymer=name):
                    self.assertGreater(mat.elongation_at_break_pct, 0)
                    self.assertLessEqual(mat.elongation_at_break_pct, 1000)


class TestHansenParameters(unittest.TestCase):
    """Verify Hansen solubility parameter calculations."""

    def test_hansen_distance_self_is_zero(self):
        h = HansenParameters(delta_d=18.0, delta_p=5.0, delta_h=3.0)
        self.assertAlmostEqual(h.distance(h), 0.0)

    def test_hansen_distance_symmetric(self):
        h1 = HansenParameters(delta_d=18.0, delta_p=5.0, delta_h=3.0)
        h2 = HansenParameters(delta_d=16.0, delta_p=10.0, delta_h=7.0)
        self.assertAlmostEqual(h1.distance(h2), h2.distance(h1))

    def test_hansen_distance_positive(self):
        h1 = HansenParameters(delta_d=18.0, delta_p=0.0, delta_h=2.0)
        h2 = HansenParameters(delta_d=15.5, delta_p=16.0, delta_h=42.3)
        self.assertGreater(h1.distance(h2), 0)

    def test_hansen_total(self):
        h = HansenParameters(delta_d=3.0, delta_p=4.0, delta_h=0.0)
        self.assertAlmostEqual(h.delta_total, 5.0)

    def test_most_polymers_have_hansen(self):
        """At least 80% of polymers should have Hansen parameters."""
        has_hansen = sum(1 for m in ALL_POLYMERS.values() if m.hansen is not None)
        ratio = has_hansen / len(ALL_POLYMERS)
        self.assertGreater(ratio, 0.8)

    def test_pvdf_nmp_compatible(self):
        """PVDF and NMP should have small Hansen distance (known soluble)."""
        pvdf = get_polymer('PVDF')
        nmp = get_polymer('NMP')
        ra = pvdf.hansen.distance(nmp.hansen)
        self.assertLess(ra, 6.0, f"PVDF-NMP Ra={ra} should be < 6 (known good solvent)")

    def test_hdpe_water_incompatible(self):
        """HDPE and Water should have large Hansen distance."""
        hdpe = get_polymer('HDPE')
        water = get_polymer('Water')
        ra = hdpe.hansen.distance(water.hansen)
        self.assertGreater(ra, 30, f"HDPE-Water Ra={ra} should be >> 10")


class TestClassification(unittest.TestCase):
    """Verify materials are correctly classified."""

    def test_pvdf_is_thermoplastic(self):
        mat = get_polymer('PVDF')
        self.assertEqual(mat.polymer_class, PolymerClass.THERMOPLASTIC)

    def test_peo_is_electrolyte(self):
        mat = get_polymer('PEO')
        self.assertEqual(mat.polymer_class, PolymerClass.ELECTROLYTE)

    def test_sbr_is_elastomer(self):
        mat = get_polymer('SBR')
        self.assertEqual(mat.polymer_class, PolymerClass.ELASTOMER)

    def test_epoxy_is_thermoset(self):
        mat = get_polymer('Epoxy')
        self.assertEqual(mat.polymer_class, PolymerClass.THERMOSET)

    def test_epoxy_is_crosslinked(self):
        mat = get_polymer('Epoxy')
        self.assertEqual(mat.structure, PolymerStructure.CROSSLINKED)

    def test_ps_is_amorphous(self):
        mat = get_polymer('PS')
        self.assertEqual(mat.structure, PolymerStructure.AMORPHOUS)
        self.assertIsNone(mat.melting_point_C)

    def test_pet_is_semicrystalline(self):
        mat = get_polymer('PET')
        self.assertEqual(mat.structure, PolymerStructure.SEMI_CRYSTALLINE)
        self.assertIsNotNone(mat.melting_point_C)


class TestDataIntegrity(unittest.TestCase):
    """Verify data integrity across all materials."""

    def test_all_have_name(self):
        for name, mat in ALL_POLYMERS.items():
            self.assertTrue(len(mat.name) > 0)

    def test_all_have_abbreviation(self):
        for name, mat in ALL_POLYMERS.items():
            self.assertTrue(len(mat.abbreviation) > 0)

    def test_all_have_class(self):
        for name, mat in ALL_POLYMERS.items():
            self.assertIsInstance(mat.polymer_class, PolymerClass)

    def test_all_have_structure(self):
        for name, mat in ALL_POLYMERS.items():
            self.assertIsInstance(mat.structure, PolymerStructure)

    def test_to_dict_works(self):
        for name, mat in ALL_POLYMERS.items():
            with self.subTest(polymer=name):
                d = mat.to_dict()
                self.assertIn('name', d)
                self.assertIn('abbreviation', d)

    def test_key_polymers_have_chain_length_data(self):
        for name in ['HDPE', 'PP', 'PS', 'PPO', 'PMMA', 'PC', 'ABS', 'PVDF', 'PEO']:
            mat = get_polymer(name)
            with self.subTest(polymer=name):
                self.assertIsNotNone(mat.repeat_unit_mw_g_mol)
                self.assertIsNotNone(mat.typical_mw_g_mol)
                self.assertGreater(mat.typical_mw_g_mol, mat.repeat_unit_mw_g_mol)

    def test_known_good_blends_exist(self):
        for blend in KNOWN_GOOD_BLENDS:
            a = get_polymer(blend['polymer_a'])
            b = get_polymer(blend['polymer_b'])
            self.assertIsNotNone(a, f"Missing polymer: {blend['polymer_a']}")
            self.assertIsNotNone(b, f"Missing polymer: {blend['polymer_b']}")

    def test_known_bad_blends_exist(self):
        for blend in KNOWN_BAD_BLENDS:
            a = get_polymer(blend['polymer_a'])
            b = get_polymer(blend['polymer_b'])
            self.assertIsNotNone(a, f"Missing polymer: {blend['polymer_a']}")
            self.assertIsNotNone(b, f"Missing polymer: {blend['polymer_b']}")


if __name__ == "__main__":
    unittest.main()
