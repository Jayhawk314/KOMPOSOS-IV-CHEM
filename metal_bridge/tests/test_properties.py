# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for metal material properties.

Verifies material existence, property ranges, classification, and data integrity.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from metal_bridge.material_properties import (
    ALL_METALS, PURE_METALS, FERROUS_ALLOYS, ALUMINUM_ALLOYS,
    COPPER_ALLOYS, TITANIUM_ALLOYS, NICKEL_ALLOYS, BATTERY_METALS,
    MetalMaterial, MetalClass, CrystalSystem, MetalFailureMode,
    get_metal, get_metals_by_class, list_pure_metals, list_ferrous_alloys,
    KNOWN_GOOD_JOINTS, KNOWN_BAD_JOINTS,
)


class TestMaterialCount(unittest.TestCase):
    """Verify expected number of materials."""

    def test_total_materials_at_least_30(self):
        self.assertGreaterEqual(len(ALL_METALS), 30)

    def test_pure_metals_exist(self):
        self.assertGreaterEqual(len(PURE_METALS), 10)

    def test_ferrous_alloys_exist(self):
        self.assertGreaterEqual(len(FERROUS_ALLOYS), 5)

    def test_aluminum_alloys_exist(self):
        self.assertGreaterEqual(len(ALUMINUM_ALLOYS), 3)

    def test_copper_alloys_exist(self):
        self.assertGreaterEqual(len(COPPER_ALLOYS), 2)

    def test_titanium_alloys_exist(self):
        self.assertGreaterEqual(len(TITANIUM_ALLOYS), 2)

    def test_nickel_alloys_exist(self):
        self.assertGreaterEqual(len(NICKEL_ALLOYS), 2)

    def test_battery_metals_exist(self):
        self.assertGreaterEqual(len(BATTERY_METALS), 2)


class TestKeyMetalsExist(unittest.TestCase):
    """Verify key metals are in the database."""

    def test_all_key_metals_exist(self):
        key_metals = [
            'Fe', 'Al', 'Cu', 'Ti', 'Ni', 'Zn', 'Mg', 'W', 'Au', 'Ag', 'Pt',
            'SS_304', 'SS_316', 'Steel_1018', 'Steel_4140',
            'Al_6061', 'Al_7075',
            'Ti6Al4V', 'CP_Ti_Gr2',
            'Inconel_625', 'Inconel_718', 'Hastelloy_C276',
            'Al_foil', 'Cu_foil', 'Ni_tab',
        ]
        for name in key_metals:
            mat = get_metal(name)
            self.assertIsNotNone(mat, f"Metal '{name}' should exist in database")


class TestMaterialLookup(unittest.TestCase):
    """Test lookup functions."""

    def test_get_metal_by_name(self):
        fe = get_metal('Fe')
        self.assertIsNotNone(fe)
        self.assertEqual(fe.formula, 'Fe')

    def test_get_metal_returns_none_for_unknown(self):
        result = get_metal('Unobtanium')
        self.assertIsNone(result)

    def test_get_metals_by_class(self):
        ferrous = get_metals_by_class(MetalClass.FERROUS_ALLOY)
        self.assertGreater(len(ferrous), 0)
        for mat in ferrous.values():
            self.assertEqual(mat.metal_class, MetalClass.FERROUS_ALLOY)

    def test_list_functions(self):
        self.assertGreater(len(list_pure_metals()), 0)
        self.assertGreater(len(list_ferrous_alloys()), 0)


class TestPropertyRanges(unittest.TestCase):
    """Verify all properties are in physically reasonable ranges."""

    def test_melting_point_range(self):
        """Melting point should be between 100C (In) and 4000C (W)."""
        for name, mat in ALL_METALS.items():
            if mat.melting_point_C is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.melting_point_C, 100.0)
                    self.assertLessEqual(mat.melting_point_C, 4000.0)

    def test_density_range(self):
        """Density should be between 1.0 (Mg) and 22 (Os/Ir/Pt)."""
        for name, mat in ALL_METALS.items():
            if mat.density_g_cm3 is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.density_g_cm3, 1.0)
                    self.assertLessEqual(mat.density_g_cm3, 22.0)

    def test_modulus_range(self):
        """Elastic modulus should be between 10 (Pb) and 500 (W)."""
        for name, mat in ALL_METALS.items():
            if mat.elastic_modulus_GPa is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.elastic_modulus_GPa, 10.0)
                    self.assertLessEqual(mat.elastic_modulus_GPa, 500.0)

    def test_yield_strength_range(self):
        """Yield strength should be between 1 (Pb) and 3000 MPa."""
        for name, mat in ALL_METALS.items():
            if mat.yield_strength_MPa is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.yield_strength_MPa, 1.0)
                    self.assertLessEqual(mat.yield_strength_MPa, 3000.0)

    def test_elongation_range(self):
        """Elongation should be between 0 and 100%."""
        for name, mat in ALL_METALS.items():
            if mat.elongation_pct is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.elongation_pct, 0.0)
                    self.assertLessEqual(mat.elongation_pct, 100.0)

    def test_cte_range(self):
        """CTE should be between 1 and 35 x10^-6/K."""
        for name, mat in ALL_METALS.items():
            if mat.cte_per_K is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.cte_per_K, 1.0)
                    self.assertLessEqual(mat.cte_per_K, 35.0)

    def test_galvanic_potential_range(self):
        """Galvanic potential should be between -2.0V and +0.5V vs SCE."""
        for name, mat in ALL_METALS.items():
            if mat.galvanic_potential_V is not None:
                with self.subTest(metal=name):
                    self.assertGreaterEqual(mat.galvanic_potential_V, -2.0)
                    self.assertLessEqual(mat.galvanic_potential_V, 0.5)


class TestGalvanicSeriesOrdering(unittest.TestCase):
    """Verify galvanic series is correctly ordered for key metals."""

    def test_noble_above_active(self):
        """Noble metals should have higher (more positive) potential than active metals."""
        pt = get_metal('Pt')
        au = get_metal('Au')
        fe = get_metal('Fe')
        zn = get_metal('Zn')
        mg = get_metal('Mg')

        self.assertGreater(pt.galvanic_potential_V, au.galvanic_potential_V)
        self.assertGreater(au.galvanic_potential_V, fe.galvanic_potential_V)
        self.assertGreater(fe.galvanic_potential_V, zn.galvanic_potential_V)
        self.assertGreater(zn.galvanic_potential_V, mg.galvanic_potential_V)

    def test_ss_noble_than_carbon_steel(self):
        """Stainless steel should be more noble than carbon steel."""
        ss304 = get_metal('SS_304')
        steel1018 = get_metal('Steel_1018')
        self.assertGreater(ss304.galvanic_potential_V, steel1018.galvanic_potential_V)

    def test_cu_noble_than_al(self):
        """Copper should be more noble than aluminum."""
        cu = get_metal('Cu')
        al = get_metal('Al')
        self.assertGreater(cu.galvanic_potential_V, al.galvanic_potential_V)

    def test_ti_noble_than_steel(self):
        """Titanium (passive) should be more noble than carbon steel."""
        ti = get_metal('Ti6Al4V')
        steel = get_metal('Steel_1018')
        self.assertGreater(ti.galvanic_potential_V, steel.galvanic_potential_V)


class TestClassification(unittest.TestCase):
    """Verify material classifications."""

    def test_fe_is_pure_metal(self):
        self.assertEqual(get_metal('Fe').metal_class, MetalClass.PURE_METAL)

    def test_ss304_is_ferrous(self):
        self.assertEqual(get_metal('SS_304').metal_class, MetalClass.FERROUS_ALLOY)

    def test_al6061_is_aluminum_alloy(self):
        self.assertEqual(get_metal('Al_6061').metal_class, MetalClass.ALUMINUM_ALLOY)

    def test_ti6al4v_is_titanium_alloy(self):
        self.assertEqual(get_metal('Ti6Al4V').metal_class, MetalClass.TITANIUM_ALLOY)

    def test_inconel_is_nickel_alloy(self):
        self.assertEqual(get_metal('Inconel_625').metal_class, MetalClass.NICKEL_ALLOY)

    def test_al_foil_is_battery_metal(self):
        self.assertEqual(get_metal('Al_foil').metal_class, MetalClass.BATTERY_METAL)

    def test_ss304_is_fcc(self):
        self.assertEqual(get_metal('SS_304').crystal_system, CrystalSystem.FCC)

    def test_steel_1018_is_bcc(self):
        self.assertEqual(get_metal('Steel_1018').crystal_system, CrystalSystem.BCC)

    def test_ti_is_hcp(self):
        self.assertEqual(get_metal('Ti').crystal_system, CrystalSystem.HCP)


class TestDataIntegrity(unittest.TestCase):
    """Verify data integrity of all materials."""

    def test_all_have_name(self):
        for name, mat in ALL_METALS.items():
            self.assertTrue(len(mat.name) > 0, f"{name} missing name")

    def test_all_have_formula(self):
        for name, mat in ALL_METALS.items():
            self.assertTrue(len(mat.formula) > 0, f"{name} missing formula")

    def test_all_have_class(self):
        for name, mat in ALL_METALS.items():
            self.assertIsInstance(mat.metal_class, MetalClass, f"{name} bad class")

    def test_all_have_crystal_system(self):
        for name, mat in ALL_METALS.items():
            self.assertIsInstance(mat.crystal_system, CrystalSystem, f"{name} bad crystal")

    def test_known_good_joints_exist(self):
        self.assertGreater(len(KNOWN_GOOD_JOINTS), 0)

    def test_known_bad_joints_exist(self):
        self.assertGreater(len(KNOWN_BAD_JOINTS), 0)

    def test_to_dict_works(self):
        fe = get_metal('Fe')
        d = fe.to_dict()
        self.assertIn('name', d)
        self.assertIn('formula', d)
        self.assertIn('metal_class', d)
        self.assertIn('crystal_system', d)


if __name__ == "__main__":
    unittest.main()
