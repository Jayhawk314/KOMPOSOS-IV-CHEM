# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for MOF interaction scoring."""

import unittest

from mof_bridge.material_properties import get_mof, MOFApplication, ALL_MOFS
from mof_bridge.interaction_scoring import (
    ScorerResult,
    score_pore_accessibility,
    score_chemical_stability,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_application_suitability,
    score_all,
)


class TestScorerResultRange(unittest.TestCase):
    """All scorers must return scores in [0, 1]."""

    def test_all_scorers_return_valid_range(self):
        for name, mof in ALL_MOFS.items():
            results = score_all(mof)
            for label, result in results.items():
                self.assertIsInstance(result, ScorerResult)
                self.assertGreaterEqual(
                    result.score, 0.0,
                    f"{name}/{label}: score {result.score} < 0",
                )
                self.assertLessEqual(
                    result.score, 1.0,
                    f"{name}/{label}: score {result.score} > 1",
                )


class TestPoreAccessibility(unittest.TestCase):

    def test_zif8_small_molecule_passes(self):
        """ZIF-8 pore (3.4A) should pass H2 (2.9A)."""
        mof = get_mof('ZIF-8')
        result = score_pore_accessibility(mof, target_molecule_diameter=2.9)
        self.assertGreater(result.score, 0.5)

    def test_zif8_large_molecule_blocked(self):
        """ZIF-8 pore (3.4A) should block large molecule (10A)."""
        mof = get_mof('ZIF-8')
        result = score_pore_accessibility(mof, target_molecule_diameter=10.0)
        self.assertLess(result.score, 0.5)

    def test_mil101_large_pore_accessible(self):
        """MIL-101(Cr) mesopores (34A) should accept most molecules."""
        mof = get_mof('MIL-101(Cr)')
        result = score_pore_accessibility(mof, target_molecule_diameter=5.0)
        self.assertGreater(result.score, 0.5)

    def test_no_molecule_default_high(self):
        """Without target molecule, score should be high."""
        mof = get_mof('MOF-5')
        result = score_pore_accessibility(mof)
        self.assertGreater(result.score, 0.8)

    def test_min_surface_area_penalty(self):
        """Low BET MOF should be penalized for high SA requirement."""
        mof = get_mof('MIL-140A')  # 415 m2/g
        result = score_pore_accessibility(mof, min_surface_area=2000.0)
        self.assertLess(result.score, 0.5)

    def test_min_pore_volume_penalty(self):
        """MOF with low pore volume should be penalized."""
        mof = get_mof('ZIF-7')  # 0.18 cm3/g
        result = score_pore_accessibility(mof, min_pore_volume=1.0)
        self.assertLess(result.score, 0.5)


class TestChemicalStability(unittest.TestCase):

    def test_uio66_water_excellent(self):
        """UiO-66 (excellent water stability) scores high in aqueous."""
        mof = get_mof('UiO-66')
        result = score_chemical_stability(mof, environment='aqueous')
        self.assertGreater(result.score, 0.5)

    def test_mof5_water_poor(self):
        """MOF-5 (poor water stability) scores low in humid conditions."""
        mof = get_mof('MOF-5')
        result = score_chemical_stability(mof, environment='humid')
        self.assertLess(result.score, 0.5)

    def test_dry_environment_lenient(self):
        """Even water-unstable MOFs score okay in dry conditions."""
        mof = get_mof('MOF-5')
        result = score_chemical_stability(mof, environment='dry')
        self.assertGreater(result.score, 0.3)

    def test_water_requirement_veto(self):
        """Requiring water stability with poor MOF triggers veto."""
        mof = get_mof('MOF-177')
        result = score_chemical_stability(mof, requires_water_stable=True)
        self.assertLess(result.score, 0.3)

    def test_pcn222_acid_stable(self):
        """PCN-222 is famous for HCl stability."""
        mof = get_mof('PCN-222')
        result = score_chemical_stability(mof, environment='acidic')
        self.assertGreater(result.score, 0.5)


class TestThermalCompatibility(unittest.TestCase):

    def test_zif8_room_temp(self):
        """ZIF-8 (550C stability) at room temp should score high."""
        mof = get_mof('ZIF-8')
        result = score_thermal_compatibility(mof, operating_temp_C=25.0)
        self.assertGreater(result.score, 0.9)

    def test_above_decomposition(self):
        """Operating above decomposition temp should score near zero."""
        mof = get_mof('HKUST-1')  # 280C stability
        result = score_thermal_compatibility(mof, operating_temp_C=350.0)
        self.assertLess(result.score, 0.1)

    def test_tight_margin(self):
        """Operating 30C below decomposition should score low."""
        mof = get_mof('MOF-74(Mg)')  # 300C
        result = score_thermal_compatibility(mof, operating_temp_C=275.0)
        self.assertLess(result.score, 0.5)

    def test_regeneration_impossible(self):
        """Regeneration above decomposition should fail."""
        mof = get_mof('HKUST-1')  # 280C stability
        result = score_thermal_compatibility(
            mof, operating_temp_C=100.0,
            requires_regeneration=True, regeneration_temp_C=350.0,
        )
        self.assertLess(result.score, 0.2)


class TestMechanicalCompatibility(unittest.TestCase):

    def test_hkust1_robust(self):
        """HKUST-1 (30.7 GPa) should be mechanically robust."""
        mof = get_mof('HKUST-1')
        result = score_mechanical_compatibility(mof, operating_pressure_bar=1.0)
        self.assertGreater(result.score, 0.8)

    def test_cof300_soft(self):
        """COF-300 (5 GPa) is a soft framework — lower than robust MOFs."""
        mof = get_mof('COF-300')
        result = score_mechanical_compatibility(mof, operating_pressure_bar=1.0)
        # Soft but not useless at 1 bar — just lower than robust MOFs
        robust = get_mof('HKUST-1')  # 30.7 GPa
        result_robust = score_mechanical_compatibility(robust, operating_pressure_bar=1.0)
        self.assertLess(result.score, result_robust.score)

    def test_high_pressure_penalty(self):
        """High pressure should penalize all MOFs."""
        mof = get_mof('ZIF-8')
        low_p = score_mechanical_compatibility(mof, operating_pressure_bar=1.0)
        high_p = score_mechanical_compatibility(mof, operating_pressure_bar=200.0)
        self.assertGreater(low_p.score, high_p.score)

    def test_missing_modulus_conservative(self):
        """MOF without bulk modulus measured should get conservative score."""
        from mof_bridge.material_properties import MOF, MOFTopology, MOFApplication
        fake = MOF(
            name='Fake', metal_node='X', linker='Y',
            topology=MOFTopology.PCU, formula='X',
            bet_surface_area_m2g=1000, pore_volume_cm3g=0.5,
            pore_diameter_angstrom=10, thermal_stability_C=300,
            water_stability='good', chemical_stability='stable',
            bulk_modulus_GPa=None,
        )
        result = score_mechanical_compatibility(fake)
        self.assertAlmostEqual(result.score, 0.5)


class TestApplicationSuitability(unittest.TestCase):

    def test_primary_match_high_score(self):
        """MOF scored for its primary application should get high score."""
        mof = get_mof('ZIF-8')  # primary = SEPARATION
        result = score_application_suitability(
            mof, target_application=MOFApplication.SEPARATION
        )
        self.assertGreater(result.score, 0.7)

    def test_secondary_lower_score(self):
        """Non-primary application should score lower."""
        mof = get_mof('ZIF-8')  # primary = SEPARATION
        result = score_application_suitability(
            mof, target_application=MOFApplication.DRUG_DELIVERY
        )
        self.assertLess(result.score, 0.7)

    def test_water_harvesting_needs_water_stability(self):
        """MOF-5 (poor water) should score low for water harvesting."""
        mof = get_mof('MOF-5')
        result = score_application_suitability(
            mof, target_application=MOFApplication.WATER_HARVESTING
        )
        self.assertLess(result.score, 0.3)

    def test_gas_storage_low_surface_area(self):
        """Low-SA MOF should score lower for gas storage."""
        mof = get_mof('ZIF-7')  # 312 m2/g
        result = score_application_suitability(
            mof, target_application=MOFApplication.GAS_STORAGE
        )
        low_sa = result.score

        mof_high = get_mof('DUT-49')  # 5476 m2/g
        result_high = score_application_suitability(
            mof_high, target_application=MOFApplication.GAS_STORAGE
        )
        self.assertGreater(result_high.score, low_sa)


class TestScoreAll(unittest.TestCase):

    def test_returns_five_scorers(self):
        mof = get_mof('UiO-66')
        results = score_all(mof)
        self.assertEqual(len(results), 5)
        expected = {
            'pore_accessibility', 'chemical_stability',
            'thermal_compatibility', 'mechanical_compatibility',
            'application_suitability',
        }
        self.assertEqual(set(results.keys()), expected)

    def test_score_all_with_conditions(self):
        mof = get_mof('ZIF-8')
        results = score_all(
            mof,
            target_molecule_diameter=3.0,
            operating_temp_C=200.0,
            operating_pressure_bar=10.0,
            environment='humid',
            target_application=MOFApplication.SEPARATION,
        )
        for label, result in results.items():
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)


if __name__ == '__main__':
    unittest.main()
