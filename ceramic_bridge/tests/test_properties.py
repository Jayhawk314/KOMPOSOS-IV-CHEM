# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for ceramic material properties.

Verifies material existence, property ranges, classification, and data integrity.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from ceramic_bridge.material_properties import (
    ALL_CERAMICS, OXIDE_CERAMICS, CARBIDE_CERAMICS, NITRIDE_CERAMICS,
    GLASS_CERAMICS, BIOCERAMICS, PIEZOELECTRIC_CERAMICS, SOLID_ELECTROLYTE_CERAMICS,
    CeramicMaterial, CeramicClass, CrystalSystem, CeramicFailureMode,
    get_ceramic, get_ceramics_by_class, list_oxides, list_carbides,
    list_nitrides, list_glasses,
    KNOWN_GOOD_COMPOSITES, KNOWN_BAD_COMPOSITES,
)


class TestMaterialCount(unittest.TestCase):
    """Verify expected number of materials."""

    def test_total_materials_at_least_25(self):
        self.assertGreaterEqual(len(ALL_CERAMICS), 25)

    def test_oxide_ceramics_exist(self):
        self.assertGreaterEqual(len(OXIDE_CERAMICS), 5)

    def test_carbide_ceramics_exist(self):
        self.assertGreaterEqual(len(CARBIDE_CERAMICS), 3)

    def test_nitride_ceramics_exist(self):
        self.assertGreaterEqual(len(NITRIDE_CERAMICS), 3)

    def test_glass_ceramics_exist(self):
        self.assertGreaterEqual(len(GLASS_CERAMICS), 2)

    def test_bioceramics_exist(self):
        self.assertGreaterEqual(len(BIOCERAMICS), 2)

    def test_piezoelectric_ceramics_exist(self):
        self.assertGreaterEqual(len(PIEZOELECTRIC_CERAMICS), 1)

    def test_solid_electrolyte_ceramics_exist(self):
        self.assertGreaterEqual(len(SOLID_ELECTROLYTE_CERAMICS), 3)


class TestKeyCeramicsExist(unittest.TestCase):
    """Verify key ceramics are in the database."""

    def test_all_key_ceramics_exist(self):
        key_ceramics = [
            'Al2O3', 'ZrO2_YSZ', 'MgO', 'TiO2', 'SiO2',
            'SiC', 'WC', 'B4C',
            'Si3N4', 'AlN', 'BN_hex', 'TiN',
            'Borosilicate', 'Soda_Lime',
            'Hydroxyapatite', 'TCP',
            'PZT',
            'LLZO', 'LGPS', 'Li3PS4',
        ]
        for name in key_ceramics:
            mat = get_ceramic(name)
            self.assertIsNotNone(mat, f"Ceramic '{name}' should exist in database")


class TestMaterialLookup(unittest.TestCase):
    """Test lookup functions."""

    def test_get_ceramic_by_name(self):
        al2o3 = get_ceramic('Al2O3')
        self.assertIsNotNone(al2o3)
        self.assertEqual(al2o3.formula, 'Al2O3')

    def test_get_ceramic_returns_none_for_unknown(self):
        result = get_ceramic('Unobtanium')
        self.assertIsNone(result)

    def test_get_ceramics_by_class(self):
        oxides = get_ceramics_by_class(CeramicClass.OXIDE)
        self.assertGreater(len(oxides), 0)
        for mat in oxides.values():
            self.assertEqual(mat.ceramic_class, CeramicClass.OXIDE)

    def test_list_functions(self):
        self.assertGreater(len(list_oxides()), 0)
        self.assertGreater(len(list_carbides()), 0)
        self.assertGreater(len(list_nitrides()), 0)
        self.assertGreater(len(list_glasses()), 0)


class TestPropertyRanges(unittest.TestCase):
    """Verify all properties are in physically reasonable ranges."""

    def test_melting_point_range(self):
        """Melting point should be between 500C and 4000C."""
        for name, mat in ALL_CERAMICS.items():
            if mat.melting_point_C is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.melting_point_C, 500.0)
                    self.assertLessEqual(mat.melting_point_C, 4000.0)

    def test_density_range(self):
        """Density should be between 1.5 and 20 g/cm3."""
        for name, mat in ALL_CERAMICS.items():
            if mat.density_g_cm3 is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.density_g_cm3, 1.5)
                    self.assertLessEqual(mat.density_g_cm3, 20.0)

    def test_modulus_range(self):
        """Elastic modulus should be between 15 and 800 GPa."""
        for name, mat in ALL_CERAMICS.items():
            if mat.elastic_modulus_GPa is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.elastic_modulus_GPa, 15.0)
                    self.assertLessEqual(mat.elastic_modulus_GPa, 800.0)

    def test_fracture_toughness_range(self):
        """Fracture toughness should be between 0.1 and 15 MPa*sqrt(m)."""
        for name, mat in ALL_CERAMICS.items():
            if mat.fracture_toughness_MPa_m05 is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.fracture_toughness_MPa_m05, 0.1)
                    self.assertLessEqual(mat.fracture_toughness_MPa_m05, 15.0)

    def test_cte_range(self):
        """CTE should be between 0.1 and 20 x10^-6/K."""
        for name, mat in ALL_CERAMICS.items():
            if mat.cte_per_K is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.cte_per_K, 0.1)
                    self.assertLessEqual(mat.cte_per_K, 20.0)

    def test_hardness_range(self):
        """Hardness should be between 10 and 5000 HV."""
        for name, mat in ALL_CERAMICS.items():
            if mat.hardness_HV is not None:
                with self.subTest(ceramic=name):
                    self.assertGreaterEqual(mat.hardness_HV, 10)
                    self.assertLessEqual(mat.hardness_HV, 5000)


class TestClassification(unittest.TestCase):
    """Verify material classifications."""

    def test_al2o3_is_oxide(self):
        self.assertEqual(get_ceramic('Al2O3').ceramic_class, CeramicClass.OXIDE)

    def test_sic_is_carbide(self):
        self.assertEqual(get_ceramic('SiC').ceramic_class, CeramicClass.CARBIDE)

    def test_si3n4_is_nitride(self):
        self.assertEqual(get_ceramic('Si3N4').ceramic_class, CeramicClass.NITRIDE)

    def test_borosilicate_is_glass(self):
        self.assertEqual(get_ceramic('Borosilicate').ceramic_class, CeramicClass.GLASS)

    def test_hydroxyapatite_is_bioceramic(self):
        self.assertEqual(get_ceramic('Hydroxyapatite').ceramic_class, CeramicClass.BIOCERAMIC)

    def test_pzt_is_piezoelectric(self):
        self.assertEqual(get_ceramic('PZT').ceramic_class, CeramicClass.PIEZOELECTRIC)

    def test_llzo_is_solid_electrolyte(self):
        self.assertEqual(get_ceramic('LLZO').ceramic_class, CeramicClass.SOLID_ELECTROLYTE)

    def test_al2o3_is_rhombohedral(self):
        self.assertEqual(get_ceramic('Al2O3').crystal_system, CrystalSystem.RHOMBOHEDRAL)

    def test_sic_is_hexagonal(self):
        self.assertEqual(get_ceramic('SiC').crystal_system, CrystalSystem.HEXAGONAL)

    def test_sio2_is_amorphous(self):
        self.assertEqual(get_ceramic('SiO2').crystal_system, CrystalSystem.AMORPHOUS)


class TestDataIntegrity(unittest.TestCase):
    """Verify data integrity of all materials."""

    def test_all_have_name(self):
        for name, mat in ALL_CERAMICS.items():
            self.assertTrue(len(mat.name) > 0, f"{name} missing name")

    def test_all_have_formula(self):
        for name, mat in ALL_CERAMICS.items():
            self.assertTrue(len(mat.formula) > 0, f"{name} missing formula")

    def test_all_have_class(self):
        for name, mat in ALL_CERAMICS.items():
            self.assertIsInstance(mat.ceramic_class, CeramicClass, f"{name} bad class")

    def test_all_have_crystal_system(self):
        for name, mat in ALL_CERAMICS.items():
            self.assertIsInstance(mat.crystal_system, CrystalSystem, f"{name} bad crystal")

    def test_known_good_composites_exist(self):
        self.assertGreater(len(KNOWN_GOOD_COMPOSITES), 0)

    def test_known_bad_composites_exist(self):
        self.assertGreater(len(KNOWN_BAD_COMPOSITES), 0)

    def test_to_dict_works(self):
        al2o3 = get_ceramic('Al2O3')
        d = al2o3.to_dict()
        self.assertIn('name', d)
        self.assertIn('formula', d)
        self.assertIn('ceramic_class', d)
        self.assertIn('crystal_system', d)


class TestPhysicalRelationships(unittest.TestCase):
    """Verify known physical relationships between materials."""

    def test_sic_higher_modulus_than_glass(self):
        """SiC (410 GPa) >> soda-lime glass (72 GPa)."""
        sic = get_ceramic('SiC')
        glass = get_ceramic('Soda_Lime')
        self.assertGreater(sic.elastic_modulus_GPa, glass.elastic_modulus_GPa)

    def test_ysz_tougher_than_alumina(self):
        """YSZ (8 MPa*m^0.5) >> Al2O3 (3.5 MPa*m^0.5)."""
        ysz = get_ceramic('ZrO2_YSZ')
        al2o3 = get_ceramic('Al2O3')
        self.assertGreater(ysz.fracture_toughness_MPa_m05, al2o3.fracture_toughness_MPa_m05)

    def test_aln_higher_thermal_conductivity_than_alumina(self):
        """AlN (180 W/mK) >> Al2O3 (35 W/mK)."""
        aln = get_ceramic('AlN')
        al2o3 = get_ceramic('Al2O3')
        self.assertGreater(aln.thermal_conductivity_W_mK, al2o3.thermal_conductivity_W_mK)

    def test_fused_silica_lowest_cte(self):
        """Fused silica should have very low CTE."""
        sio2 = get_ceramic('SiO2')
        self.assertLess(sio2.cte_per_K, 1.0)

    def test_wc_densest_ceramic(self):
        """WC (15.63 g/cm3) should be densest ceramic in database."""
        wc = get_ceramic('WC')
        for name, mat in ALL_CERAMICS.items():
            if mat.density_g_cm3 is not None:
                self.assertGreaterEqual(
                    wc.density_g_cm3, mat.density_g_cm3 - 0.01,
                    f"WC should be denser than {name}"
                )


if __name__ == "__main__":
    unittest.main()
