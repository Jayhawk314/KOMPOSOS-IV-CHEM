# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for glass_bridge material properties."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from glass_bridge.material_properties import (
    GlassMaterial, GlassClass, CompositionType, GlassFailureMode,
    ALL_GLASSES, SODA_LIME_GLASSES, BOROSILICATE_GLASSES,
    ALUMINOSILICATE_GLASSES, LEAD_GLASSES, FUSED_SILICA_GLASSES,
    OPTICAL_GLASSES, BIOACTIVE_GLASSES, CHALCOGENIDE_GLASSES,
    GLASS_CERAMIC_MATERIALS, PHOSPHATE_GLASSES, FLUORIDE_GLASSES,
    get_glass, get_glasses_by_class,
    KNOWN_GOOD_ASSEMBLIES, KNOWN_BAD_ASSEMBLIES,
)


class TestMaterialCounts(unittest.TestCase):
    """Test material database completeness."""

    def test_total_glasses_at_least_20(self):
        self.assertGreaterEqual(len(ALL_GLASSES), 20)

    def test_total_glasses_exact_23(self):
        self.assertEqual(len(ALL_GLASSES), 23)

    def test_soda_lime_count(self):
        self.assertEqual(len(SODA_LIME_GLASSES), 3)

    def test_borosilicate_count(self):
        self.assertEqual(len(BOROSILICATE_GLASSES), 3)

    def test_aluminosilicate_count(self):
        self.assertEqual(len(ALUMINOSILICATE_GLASSES), 2)

    def test_lead_count(self):
        self.assertEqual(len(LEAD_GLASSES), 2)

    def test_fused_silica_count(self):
        self.assertEqual(len(FUSED_SILICA_GLASSES), 2)

    def test_optical_count(self):
        self.assertEqual(len(OPTICAL_GLASSES), 3)

    def test_bioactive_count(self):
        self.assertEqual(len(BIOACTIVE_GLASSES), 2)

    def test_chalcogenide_count(self):
        self.assertEqual(len(CHALCOGENIDE_GLASSES), 2)

    def test_glass_ceramic_count(self):
        self.assertEqual(len(GLASS_CERAMIC_MATERIALS), 2)

    def test_phosphate_count(self):
        self.assertEqual(len(PHOSPHATE_GLASSES), 1)

    def test_fluoride_count(self):
        self.assertEqual(len(FLUORIDE_GLASSES), 1)

    def test_sum_of_categories_equals_total(self):
        cat_total = (
            len(SODA_LIME_GLASSES) + len(BOROSILICATE_GLASSES) +
            len(ALUMINOSILICATE_GLASSES) + len(LEAD_GLASSES) +
            len(FUSED_SILICA_GLASSES) + len(OPTICAL_GLASSES) +
            len(BIOACTIVE_GLASSES) + len(CHALCOGENIDE_GLASSES) +
            len(GLASS_CERAMIC_MATERIALS) + len(PHOSPHATE_GLASSES) +
            len(FLUORIDE_GLASSES)
        )
        self.assertEqual(cat_total, len(ALL_GLASSES))


class TestKeyGlassesExist(unittest.TestCase):
    """Test that key glasses are in the database."""

    def test_bk7(self):
        self.assertIsNotNone(get_glass('BK7'))

    def test_f2(self):
        self.assertIsNotNone(get_glass('F2'))

    def test_fused_silica(self):
        self.assertIsNotNone(get_glass('FusedSilica'))

    def test_sodalime_float(self):
        self.assertIsNotNone(get_glass('SodaLime_Float'))

    def test_boro_33(self):
        self.assertIsNotNone(get_glass('Boro_33'))

    def test_bioglass_45s5(self):
        self.assertIsNotNone(get_glass('Bioglass_45S5'))

    def test_as2s3(self):
        self.assertIsNotNone(get_glass('As2S3'))

    def test_zblan(self):
        self.assertIsNotNone(get_glass('ZBLAN'))

    def test_zerodur(self):
        self.assertIsNotNone(get_glass('LAS_Zerodur'))

    def test_laser_phosphate(self):
        self.assertIsNotNone(get_glass('LaserPhosphate'))

    def test_lead_crystal(self):
        self.assertIsNotNone(get_glass('Lead_Crystal'))

    def test_lak9(self):
        self.assertIsNotNone(get_glass('LAK9'))

    def test_unknown_returns_none(self):
        self.assertIsNone(get_glass('NotAGlass'))


class TestPropertyRanges(unittest.TestCase):
    """Test that all properties fall within physically reasonable ranges."""

    def test_tg_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.Tg_C is not None:
                self.assertGreaterEqual(mat.Tg_C, 150,
                    f"{name}: Tg={mat.Tg_C} below 150C")
                self.assertLessEqual(mat.Tg_C, 1300,
                    f"{name}: Tg={mat.Tg_C} above 1300C")

    def test_cte_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.cte_per_K is not None:
                self.assertGreaterEqual(mat.cte_per_K, 0.01,
                    f"{name}: CTE={mat.cte_per_K} below 0.01")
                self.assertLessEqual(mat.cte_per_K, 30.0,
                    f"{name}: CTE={mat.cte_per_K} above 30")

    def test_density_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.density_g_cm3 is not None:
                self.assertGreaterEqual(mat.density_g_cm3, 2.0,
                    f"{name}: density={mat.density_g_cm3} below 2.0")
                self.assertLessEqual(mat.density_g_cm3, 6.0,
                    f"{name}: density={mat.density_g_cm3} above 6.0")

    def test_refractive_index_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.refractive_index is not None:
                self.assertGreaterEqual(mat.refractive_index, 1.3,
                    f"{name}: nd={mat.refractive_index} below 1.3")
                self.assertLessEqual(mat.refractive_index, 3.0,
                    f"{name}: nd={mat.refractive_index} above 3.0")

    def test_modulus_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.elastic_modulus_GPa is not None:
                self.assertGreaterEqual(mat.elastic_modulus_GPa, 10.0,
                    f"{name}: E={mat.elastic_modulus_GPa} below 10")
                self.assertLessEqual(mat.elastic_modulus_GPa, 120.0,
                    f"{name}: E={mat.elastic_modulus_GPa} above 120")

    def test_fracture_toughness_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.fracture_toughness_MPa_m05 is not None:
                self.assertGreaterEqual(mat.fracture_toughness_MPa_m05, 0.1,
                    f"{name}: KIc={mat.fracture_toughness_MPa_m05} below 0.1")
                self.assertLessEqual(mat.fracture_toughness_MPa_m05, 2.0,
                    f"{name}: KIc={mat.fracture_toughness_MPa_m05} above 2.0")

    def test_hardness_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.hardness_HK is not None:
                self.assertGreaterEqual(mat.hardness_HK, 100,
                    f"{name}: HK={mat.hardness_HK} below 100")
                self.assertLessEqual(mat.hardness_HK, 700,
                    f"{name}: HK={mat.hardness_HK} above 700")

    def test_abbe_number_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.abbe_number is not None:
                self.assertGreaterEqual(mat.abbe_number, 15.0,
                    f"{name}: Vd={mat.abbe_number} below 15")
                self.assertLessEqual(mat.abbe_number, 200.0,
                    f"{name}: Vd={mat.abbe_number} above 200")

    def test_softening_above_tg(self):
        for name, mat in ALL_GLASSES.items():
            if mat.Tg_C is not None and mat.softening_point_C is not None:
                self.assertGreater(mat.softening_point_C, mat.Tg_C,
                    f"{name}: softening={mat.softening_point_C} <= Tg={mat.Tg_C}")

    def test_hydrolytic_class_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.hydrolytic_class is not None:
                self.assertGreaterEqual(mat.hydrolytic_class, 1,
                    f"{name}: hydrolytic class {mat.hydrolytic_class}")
                self.assertLessEqual(mat.hydrolytic_class, 5,
                    f"{name}: hydrolytic class {mat.hydrolytic_class}")

    def test_thermal_conductivity_range(self):
        for name, mat in ALL_GLASSES.items():
            if mat.thermal_conductivity_W_mK is not None:
                self.assertGreaterEqual(mat.thermal_conductivity_W_mK, 0.1,
                    f"{name}: k={mat.thermal_conductivity_W_mK} below 0.1")
                self.assertLessEqual(mat.thermal_conductivity_W_mK, 2.0,
                    f"{name}: k={mat.thermal_conductivity_W_mK} above 2.0")


class TestClassifications(unittest.TestCase):
    """Test correct classification of materials."""

    def test_bk7_is_optical(self):
        self.assertEqual(get_glass('BK7').glass_class, GlassClass.OPTICAL)

    def test_f2_is_optical(self):
        self.assertEqual(get_glass('F2').glass_class, GlassClass.OPTICAL)

    def test_fused_silica_class(self):
        self.assertEqual(get_glass('FusedSilica').glass_class, GlassClass.FUSED_SILICA)

    def test_sodalime_class(self):
        self.assertEqual(get_glass('SodaLime_Float').glass_class, GlassClass.SODA_LIME)

    def test_boro33_class(self):
        self.assertEqual(get_glass('Boro_33').glass_class, GlassClass.BOROSILICATE)

    def test_as2s3_class(self):
        self.assertEqual(get_glass('As2S3').glass_class, GlassClass.CHALCOGENIDE)

    def test_bioglass_class(self):
        self.assertEqual(get_glass('Bioglass_45S5').glass_class, GlassClass.BIOACTIVE)

    def test_zblan_class(self):
        self.assertEqual(get_glass('ZBLAN').glass_class, GlassClass.FLUORIDE)

    def test_zerodur_class(self):
        self.assertEqual(get_glass('LAS_Zerodur').glass_class, GlassClass.GLASS_CERAMIC)

    def test_lead_crystal_class(self):
        self.assertEqual(get_glass('Lead_Crystal').glass_class, GlassClass.LEAD_GLASS)

    def test_chalcogenide_composition(self):
        self.assertEqual(get_glass('As2S3').composition_type, CompositionType.CHALCOGENIDE)

    def test_zblan_composition(self):
        self.assertEqual(get_glass('ZBLAN').composition_type, CompositionType.FLUORIDE)

    def test_laser_phosphate_composition(self):
        self.assertEqual(get_glass('LaserPhosphate').composition_type, CompositionType.PHOSPHATE)

    def test_bk7_composition(self):
        self.assertEqual(get_glass('BK7').composition_type, CompositionType.SILICATE)


class TestPhysicalRelationships(unittest.TestCase):
    """Test physically correct relative orderings between materials."""

    def test_fused_silica_highest_tg(self):
        """Fused silica has the highest Tg of any common glass."""
        fused = get_glass('FusedSilica')
        sodalime = get_glass('SodaLime_Float')
        self.assertGreater(fused.Tg_C, sodalime.Tg_C)

    def test_fused_silica_lowest_cte(self):
        """Fused silica has among the lowest CTE of common glasses."""
        fused = get_glass('FusedSilica')
        sodalime = get_glass('SodaLime_Float')
        self.assertLess(fused.cte_per_K, sodalime.cte_per_K)

    def test_zerodur_ultra_low_cte(self):
        """Zerodur has near-zero CTE."""
        zerodur = get_glass('LAS_Zerodur')
        self.assertLess(zerodur.cte_per_K, 0.1)

    def test_lead_glass_highest_density(self):
        """Lead glass has higher density than soda-lime."""
        lead = get_glass('Lead_Dense_Flint')
        sodalime = get_glass('SodaLime_Float')
        self.assertGreater(lead.density_g_cm3, sodalime.density_g_cm3)

    def test_lead_flint_highest_refractive_index(self):
        """Dense flint (lead) has very high refractive index."""
        lead_flint = get_glass('Lead_Dense_Flint')
        bk7 = get_glass('BK7')
        self.assertGreater(lead_flint.refractive_index, bk7.refractive_index)

    def test_chalcogenide_highest_refractive_index(self):
        """Chalcogenide glasses have the highest refractive index."""
        ge_sb_se = get_glass('Ge28Sb12Se60')
        bk7 = get_glass('BK7')
        self.assertGreater(ge_sb_se.refractive_index, 2.0)
        self.assertGreater(ge_sb_se.refractive_index, bk7.refractive_index)

    def test_bk7_higher_abbe_than_f2(self):
        """Crown glass (BK7) has higher Abbe number than flint (F2)."""
        bk7 = get_glass('BK7')
        f2 = get_glass('F2')
        self.assertGreater(bk7.abbe_number, f2.abbe_number)

    def test_chalcogenide_low_tg(self):
        """Chalcogenide glasses have low Tg."""
        as2s3 = get_glass('As2S3')
        self.assertLess(as2s3.Tg_C, 300)

    def test_borosilicate_lower_cte_than_sodalime(self):
        """Borosilicate has lower CTE than soda-lime."""
        boro = get_glass('Boro_33')
        sodalime = get_glass('SodaLime_Float')
        self.assertLess(boro.cte_per_K, sodalime.cte_per_K)

    def test_fused_silica_best_hydrolytic(self):
        """Fused silica has hydrolytic class 1 (best)."""
        fused = get_glass('FusedSilica')
        self.assertEqual(fused.hydrolytic_class, 1)

    def test_bioglass_worst_hydrolytic(self):
        """Bioglass intentionally dissolves = worst hydrolytic class."""
        bioglass = get_glass('Bioglass_45S5')
        self.assertEqual(bioglass.hydrolytic_class, 5)

    def test_glass_ceramic_highest_toughness(self):
        """Glass-ceramics have higher fracture toughness than regular glasses."""
        cooktop = get_glass('LAS_Cooktop')
        sodalime = get_glass('SodaLime_Float')
        self.assertGreater(cooktop.fracture_toughness_MPa_m05,
                          sodalime.fracture_toughness_MPa_m05)

    def test_bioactive_high_cte(self):
        """Bioactive glasses have high CTE."""
        bio = get_glass('Bioglass_45S5')
        self.assertGreater(bio.cte_per_K, 14.0)


class TestGetGlassesByClass(unittest.TestCase):
    """Test get_glasses_by_class lookup function."""

    def test_optical_returns_3(self):
        result = get_glasses_by_class(GlassClass.OPTICAL)
        self.assertEqual(len(result), 3)

    def test_chalcogenide_returns_2(self):
        result = get_glasses_by_class(GlassClass.CHALCOGENIDE)
        self.assertEqual(len(result), 2)

    def test_fluoride_returns_1(self):
        result = get_glasses_by_class(GlassClass.FLUORIDE)
        self.assertEqual(len(result), 1)

    def test_result_contains_correct_class(self):
        result = get_glasses_by_class(GlassClass.BOROSILICATE)
        for name, mat in result.items():
            self.assertEqual(mat.glass_class, GlassClass.BOROSILICATE)


class TestDataclassMethods(unittest.TestCase):
    """Test GlassMaterial dataclass methods."""

    def test_to_dict_has_required_keys(self):
        bk7 = get_glass('BK7')
        d = bk7.to_dict()
        self.assertIn('name', d)
        self.assertIn('formula', d)
        self.assertIn('glass_class', d)
        self.assertIn('composition_type', d)

    def test_to_dict_optical_values(self):
        bk7 = get_glass('BK7')
        d = bk7.to_dict()
        self.assertAlmostEqual(d['refractive_index'], 1.5168, places=3)
        self.assertAlmostEqual(d['abbe_number'], 64.17, places=1)

    def test_failure_modes_list(self):
        sodalime = get_glass('SodaLime_Float')
        self.assertIsInstance(sodalime.failure_modes, list)
        self.assertIn(GlassFailureMode.THERMAL_SHOCK, sodalime.failure_modes)

    def test_sources_dict(self):
        bk7 = get_glass('BK7')
        self.assertIsInstance(bk7.sources, dict)
        self.assertGreater(len(bk7.sources), 0)


class TestKnownAssemblies(unittest.TestCase):
    """Test KNOWN_GOOD/BAD_ASSEMBLIES reference data."""

    def test_known_good_count(self):
        self.assertEqual(len(KNOWN_GOOD_ASSEMBLIES), 5)

    def test_known_bad_count(self):
        self.assertEqual(len(KNOWN_BAD_ASSEMBLIES), 4)

    def test_known_good_glasses_exist(self):
        for entry in KNOWN_GOOD_ASSEMBLIES:
            self.assertIsNotNone(get_glass(entry['glass_a']),
                f"Good assembly glass_a not found: {entry['glass_a']}")
            self.assertIsNotNone(get_glass(entry['glass_b']),
                f"Good assembly glass_b not found: {entry['glass_b']}")

    def test_known_bad_glasses_exist(self):
        for entry in KNOWN_BAD_ASSEMBLIES:
            self.assertIsNotNone(get_glass(entry['glass_a']),
                f"Bad assembly glass_a not found: {entry['glass_a']}")
            self.assertIsNotNone(get_glass(entry['glass_b']),
                f"Bad assembly glass_b not found: {entry['glass_b']}")


if __name__ == '__main__':
    unittest.main()
