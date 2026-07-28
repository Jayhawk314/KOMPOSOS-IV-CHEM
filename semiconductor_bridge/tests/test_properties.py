# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for semiconductor material properties.

Verifies material existence, property ranges, classification, and data integrity.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from semiconductor_bridge.material_properties import (
    ALL_SEMICONDUCTORS, ELEMENTAL_SEMICONDUCTORS, IV_IV_SEMICONDUCTORS,
    III_V_SEMICONDUCTORS, NITRIDE_SEMICONDUCTORS, II_VI_SEMICONDUCTORS,
    OXIDE_SEMICONDUCTORS, TWO_D_SEMICONDUCTORS, THERMOELECTRIC_SEMICONDUCTORS,
    SemiconductorMaterial, SemiconductorClass, CrystalSystem, BandGapType,
    SemiconductorFailureMode,
    get_semiconductor, get_semiconductors_by_class,
    list_elemental, list_iii_v, list_nitrides, list_ii_vi, list_2d,
    KNOWN_GOOD_JUNCTIONS, KNOWN_BAD_JUNCTIONS,
)


class TestMaterialCount(unittest.TestCase):
    """Verify expected number of materials."""

    def test_total_materials_at_least_25(self):
        self.assertGreaterEqual(len(ALL_SEMICONDUCTORS), 25)

    def test_elemental_exist(self):
        self.assertGreaterEqual(len(ELEMENTAL_SEMICONDUCTORS), 2)

    def test_iv_iv_exist(self):
        self.assertGreaterEqual(len(IV_IV_SEMICONDUCTORS), 2)

    def test_iii_v_exist(self):
        self.assertGreaterEqual(len(III_V_SEMICONDUCTORS), 5)

    def test_nitride_exist(self):
        self.assertGreaterEqual(len(NITRIDE_SEMICONDUCTORS), 3)

    def test_ii_vi_exist(self):
        self.assertGreaterEqual(len(II_VI_SEMICONDUCTORS), 3)

    def test_oxide_exist(self):
        self.assertGreaterEqual(len(OXIDE_SEMICONDUCTORS), 1)

    def test_2d_exist(self):
        self.assertGreaterEqual(len(TWO_D_SEMICONDUCTORS), 2)

    def test_thermoelectric_exist(self):
        self.assertGreaterEqual(len(THERMOELECTRIC_SEMICONDUCTORS), 1)


class TestKeySemiconductorsExist(unittest.TestCase):
    """Verify key semiconductors are in the database."""

    def test_all_key_semiconductors_exist(self):
        key_sc = [
            'Si', 'Ge', 'C_diamond',
            'SiGe', 'SiC_4H', 'SiC_6H',
            'GaAs', 'AlAs', 'AlGaAs', 'InP', 'InAs', 'InGaAs', 'GaP', 'InSb',
            'GaN', 'AlN', 'AlGaN', 'InN',
            'ZnO', 'CdTe', 'ZnSe', 'HgCdTe',
            'Ga2O3', 'IGZO',
            'MoS2', 'WS2',
            'Bi2Te3',
        ]
        for name in key_sc:
            mat = get_semiconductor(name)
            self.assertIsNotNone(mat, f"Semiconductor '{name}' should exist")


class TestMaterialLookup(unittest.TestCase):
    """Test lookup functions."""

    def test_get_semiconductor_by_name(self):
        si = get_semiconductor('Si')
        self.assertIsNotNone(si)
        self.assertEqual(si.formula, 'Si')

    def test_get_semiconductor_returns_none_for_unknown(self):
        result = get_semiconductor('Unobtanium')
        self.assertIsNone(result)

    def test_get_semiconductors_by_class(self):
        iii_vs = get_semiconductors_by_class(SemiconductorClass.III_V)
        self.assertGreater(len(iii_vs), 0)
        for mat in iii_vs.values():
            self.assertEqual(mat.semiconductor_class, SemiconductorClass.III_V)

    def test_list_functions(self):
        self.assertGreater(len(list_elemental()), 0)
        self.assertGreater(len(list_iii_v()), 0)
        self.assertGreater(len(list_nitrides()), 0)
        self.assertGreater(len(list_ii_vi()), 0)
        self.assertGreater(len(list_2d()), 0)


class TestPropertyRanges(unittest.TestCase):
    """Verify all properties are in physically reasonable ranges."""

    def test_band_gap_range(self):
        """Band gap should be between 0.0 and 7.0 eV."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.band_gap_eV is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.band_gap_eV, 0.0)
                    self.assertLessEqual(mat.band_gap_eV, 7.0)

    def test_lattice_constant_range(self):
        """Lattice constant should be between 2.5 and 15 Angstroms."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.lattice_constant_A is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.lattice_constant_A, 2.5)
                    self.assertLessEqual(mat.lattice_constant_A, 15.0)

    def test_electron_mobility_range(self):
        """Electron mobility should be between 1 and 100000 cm2/Vs."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.electron_mobility_cm2_Vs is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.electron_mobility_cm2_Vs, 1.0)
                    self.assertLessEqual(mat.electron_mobility_cm2_Vs, 100000.0)

    def test_density_range(self):
        """Density should be between 1.0 and 10.0 g/cm3."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.density_g_cm3 is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.density_g_cm3, 1.0)
                    self.assertLessEqual(mat.density_g_cm3, 10.0)

    def test_cte_range(self):
        """CTE should be between 0.5 and 20 x10^-6/K."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.cte_per_K is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.cte_per_K, 0.5)
                    self.assertLessEqual(mat.cte_per_K, 20.0)

    def test_melting_point_range(self):
        """Melting point should be between 200 and 4000 C."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.melting_point_C is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.melting_point_C, 200.0)
                    self.assertLessEqual(mat.melting_point_C, 4000.0)

    def test_dielectric_constant_range(self):
        """Dielectric constant should be between 1 and 60."""
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.dielectric_constant is not None:
                with self.subTest(semiconductor=name):
                    self.assertGreaterEqual(mat.dielectric_constant, 1.0)
                    self.assertLessEqual(mat.dielectric_constant, 60.0)


class TestClassification(unittest.TestCase):
    """Verify material classifications."""

    def test_si_is_elemental(self):
        self.assertEqual(get_semiconductor('Si').semiconductor_class, SemiconductorClass.ELEMENTAL)

    def test_gaas_is_iii_v(self):
        self.assertEqual(get_semiconductor('GaAs').semiconductor_class, SemiconductorClass.III_V)

    def test_gan_is_nitride(self):
        self.assertEqual(get_semiconductor('GaN').semiconductor_class, SemiconductorClass.NITRIDE)

    def test_cdte_is_ii_vi(self):
        self.assertEqual(get_semiconductor('CdTe').semiconductor_class, SemiconductorClass.II_VI)

    def test_ga2o3_is_oxide(self):
        self.assertEqual(get_semiconductor('Ga2O3').semiconductor_class, SemiconductorClass.OXIDE)

    def test_mos2_is_2d(self):
        self.assertEqual(get_semiconductor('MoS2').semiconductor_class, SemiconductorClass.TWO_D)

    def test_bi2te3_is_thermoelectric(self):
        self.assertEqual(get_semiconductor('Bi2Te3').semiconductor_class, SemiconductorClass.THERMOELECTRIC)

    def test_si_is_diamond_cubic(self):
        self.assertEqual(get_semiconductor('Si').crystal_system, CrystalSystem.DIAMOND_CUBIC)

    def test_gaas_is_zincblende(self):
        self.assertEqual(get_semiconductor('GaAs').crystal_system, CrystalSystem.ZINCBLENDE)

    def test_gan_is_wurtzite(self):
        self.assertEqual(get_semiconductor('GaN').crystal_system, CrystalSystem.WURTZITE)

    def test_si_is_indirect(self):
        self.assertEqual(get_semiconductor('Si').band_gap_type, BandGapType.INDIRECT)

    def test_gaas_is_direct(self):
        self.assertEqual(get_semiconductor('GaAs').band_gap_type, BandGapType.DIRECT)


class TestDataIntegrity(unittest.TestCase):
    """Verify data integrity of all materials."""

    def test_all_have_name(self):
        for name, mat in ALL_SEMICONDUCTORS.items():
            self.assertTrue(len(mat.name) > 0, f"{name} missing name")

    def test_all_have_formula(self):
        for name, mat in ALL_SEMICONDUCTORS.items():
            self.assertTrue(len(mat.formula) > 0, f"{name} missing formula")

    def test_all_have_class(self):
        for name, mat in ALL_SEMICONDUCTORS.items():
            self.assertIsInstance(mat.semiconductor_class, SemiconductorClass, f"{name} bad class")

    def test_all_have_crystal_system(self):
        for name, mat in ALL_SEMICONDUCTORS.items():
            self.assertIsInstance(mat.crystal_system, CrystalSystem, f"{name} bad crystal")

    def test_all_have_band_gap(self):
        for name, mat in ALL_SEMICONDUCTORS.items():
            self.assertIsNotNone(mat.band_gap_eV, f"{name} missing band_gap_eV")

    def test_known_good_junctions_exist(self):
        self.assertGreater(len(KNOWN_GOOD_JUNCTIONS), 0)

    def test_known_bad_junctions_exist(self):
        self.assertGreater(len(KNOWN_BAD_JUNCTIONS), 0)

    def test_to_dict_works(self):
        si = get_semiconductor('Si')
        d = si.to_dict()
        self.assertIn('name', d)
        self.assertIn('formula', d)
        self.assertIn('semiconductor_class', d)
        self.assertIn('crystal_system', d)


class TestPhysicalRelationships(unittest.TestCase):
    """Verify known physical relationships between materials."""

    def test_gaas_higher_mobility_than_si(self):
        """GaAs (8500) >> Si (1400) electron mobility."""
        gaas = get_semiconductor('GaAs')
        si = get_semiconductor('Si')
        self.assertGreater(gaas.electron_mobility_cm2_Vs, si.electron_mobility_cm2_Vs)

    def test_insb_highest_mobility(self):
        """InSb (78000) should have highest electron mobility."""
        insb = get_semiconductor('InSb')
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.electron_mobility_cm2_Vs is not None and name != 'InSb':
                self.assertGreaterEqual(
                    insb.electron_mobility_cm2_Vs, mat.electron_mobility_cm2_Vs - 1,
                    f"InSb should have highest mobility (vs {name})"
                )

    def test_diamond_highest_thermal_conductivity(self):
        """Diamond (2200 W/mK) should be highest."""
        diamond = get_semiconductor('C_diamond')
        for name, mat in ALL_SEMICONDUCTORS.items():
            if mat.thermal_conductivity_W_mK is not None:
                self.assertGreaterEqual(
                    diamond.thermal_conductivity_W_mK, mat.thermal_conductivity_W_mK - 1,
                    f"Diamond should have highest thermal conductivity (vs {name})"
                )

    def test_gan_wider_gap_than_gaas(self):
        """GaN (3.44 eV) >> GaAs (1.42 eV)."""
        gan = get_semiconductor('GaN')
        gaas = get_semiconductor('GaAs')
        self.assertGreater(gan.band_gap_eV, gaas.band_gap_eV)

    def test_gaas_algaas_lattice_matched(self):
        """GaAs and AlGaAs should have very close lattice constants."""
        gaas = get_semiconductor('GaAs')
        algaas = get_semiconductor('AlGaAs')
        mismatch = abs(gaas.lattice_constant_A - algaas.lattice_constant_A) / gaas.lattice_constant_A * 100
        self.assertLess(mismatch, 0.1, "GaAs/AlGaAs should be nearly lattice-matched")

    def test_ingaas_inp_lattice_matched(self):
        """InGaAs (In=0.53) and InP should be lattice-matched."""
        ingaas = get_semiconductor('InGaAs')
        inp = get_semiconductor('InP')
        mismatch = abs(ingaas.lattice_constant_A - inp.lattice_constant_A) / inp.lattice_constant_A * 100
        self.assertLess(mismatch, 0.1, "InGaAs/InP should be lattice-matched")

    def test_sic_higher_breakdown_than_si(self):
        """SiC (2.2 MV/cm) >> Si (0.3 MV/cm) breakdown field."""
        sic = get_semiconductor('SiC_4H')
        si = get_semiconductor('Si')
        self.assertGreater(sic.breakdown_field_MV_cm, si.breakdown_field_MV_cm)


if __name__ == "__main__":
    unittest.main()
