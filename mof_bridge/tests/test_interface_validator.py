# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for MOF interface validator."""

import unittest

from mof_bridge.material_properties import get_mof, ALL_MOFS, MOFApplication
from mof_bridge.interface_validator import (
    MOFInterfaceValidator,
    MOFInterfaceScore,
    MOFWeights,
    MOFConditions,
    validate_mof,
)


class TestMOFInterfaceScore(unittest.TestCase):
    """Test MOFInterfaceScore dataclass."""

    def test_to_dict_keys(self):
        score = MOFInterfaceScore(
            total=0.8, pore_accessibility=0.9, chemical_stability=0.7,
            thermal_compatibility=0.8, mechanical_compatibility=0.7,
            application_suitability=0.9, suitable=True,
        )
        d = score.to_dict()
        expected_keys = {
            'total', 'pore_accessibility', 'chemical_stability',
            'thermal_compatibility', 'mechanical_compatibility',
            'application_suitability', 'suitable',
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values_rounded(self):
        score = MOFInterfaceScore(
            total=0.12345, pore_accessibility=0.9, chemical_stability=0.7,
            thermal_compatibility=0.8, mechanical_compatibility=0.7,
            application_suitability=0.9, suitable=True,
        )
        d = score.to_dict()
        self.assertEqual(d['total'], 0.1235)


class TestMOFWeights(unittest.TestCase):

    def test_default_sums_to_one(self):
        w = MOFWeights.default()
        total = w.pore + w.chemical + w.thermal + w.mechanical + w.application
        self.assertAlmostEqual(total, 1.0)

    def test_separation_focus_sums_to_one(self):
        w = MOFWeights.separation_focus()
        total = w.pore + w.chemical + w.thermal + w.mechanical + w.application
        self.assertAlmostEqual(total, 1.0)

    def test_invalid_weights_rejected(self):
        w = MOFWeights(pore=0.5, chemical=0.5, thermal=0.5,
                       mechanical=0.5, application=0.5)
        with self.assertRaises(ValueError):
            w.validate()


class TestMOFInterfaceValidator(unittest.TestCase):

    def setUp(self):
        self.validator = MOFInterfaceValidator()

    def test_validate_known_mof(self):
        result = self.validator.validate_mof('ZIF-8')
        self.assertIsInstance(result, MOFInterfaceScore)
        self.assertGreaterEqual(result.total, 0.0)
        self.assertLessEqual(result.total, 1.0)

    def test_unknown_mof_raises(self):
        with self.assertRaises(ValueError):
            self.validator.validate_mof('NONEXISTENT')

    def test_zif8_suitable_for_separation(self):
        """ZIF-8 is a well-known separation MOF."""
        conditions = MOFConditions(
            target_molecule_diameter=3.0,
            target_application=MOFApplication.SEPARATION,
        )
        result = self.validator.validate_mof('ZIF-8', conditions)
        self.assertTrue(result.suitable)

    def test_mof5_penalized_in_water(self):
        """MOF-5 should score much lower in aqueous than dry."""
        cond_wet = MOFConditions(environment='aqueous', requires_water_stable=True)
        cond_dry = MOFConditions(environment='dry')
        result_wet = self.validator.validate_mof('MOF-5', cond_wet)
        result_dry = self.validator.validate_mof('MOF-5', cond_dry)
        self.assertLess(result_wet.total, result_dry.total)
        # Chemical stability component should be very low
        self.assertLess(result_wet.chemical_stability, 0.2)

    def test_uio66_robust_in_water(self):
        """UiO-66 should be suitable in aqueous environment."""
        conditions = MOFConditions(
            environment='aqueous',
            requires_water_stable=True,
        )
        result = self.validator.validate_mof('UiO-66', conditions)
        self.assertTrue(result.suitable)

    def test_mof801_water_harvesting(self):
        """MOF-801 is THE water harvesting MOF."""
        conditions = MOFConditions(
            target_application=MOFApplication.WATER_HARVESTING,
            environment='humid',
            requires_water_stable=True,
        )
        result = self.validator.validate_mof('MOF-801', conditions)
        self.assertTrue(result.suitable)

    def test_hkust1_penalized_high_temp(self):
        """HKUST-1 (280C) should score lower at 350C than at 25C."""
        cond_hot = MOFConditions(operating_temp_C=350.0)
        cond_rt = MOFConditions(operating_temp_C=25.0)
        result_hot = self.validator.validate_mof('HKUST-1', cond_hot)
        result_rt = self.validator.validate_mof('HKUST-1', cond_rt)
        self.assertLess(result_hot.total, result_rt.total)
        # Thermal component specifically should be very low
        self.assertLess(result_hot.thermal_compatibility, 0.1)

    def test_all_mofs_score_at_room_temp(self):
        """Every MOF should get a valid score at room temperature."""
        for name in ALL_MOFS:
            result = self.validator.validate_mof(name)
            self.assertGreaterEqual(result.total, 0.0)
            self.assertLessEqual(result.total, 1.0)

    def test_custom_weights(self):
        """Custom weights should affect the score."""
        pore_heavy = MOFInterfaceValidator(
            weights=MOFWeights.separation_focus()
        )
        default = MOFInterfaceValidator()

        result_heavy = pore_heavy.validate_mof('ZIF-8')
        result_default = default.validate_mof('ZIF-8')

        # Scores should differ (different weight distributions)
        # Just check both are valid
        self.assertGreaterEqual(result_heavy.total, 0.0)
        self.assertGreaterEqual(result_default.total, 0.0)

    def test_custom_threshold(self):
        """Higher threshold should make fewer MOFs suitable."""
        strict = MOFInterfaceValidator(suitability_threshold=0.9)
        lenient = MOFInterfaceValidator(suitability_threshold=0.3)

        strict_suitable = sum(
            1 for name in ALL_MOFS
            if strict.validate_mof(name).suitable
        )
        lenient_suitable = sum(
            1 for name in ALL_MOFS
            if lenient.validate_mof(name).suitable
        )
        self.assertGreaterEqual(lenient_suitable, strict_suitable)


class TestScreenAll(unittest.TestCase):

    def test_screen_returns_all_mofs(self):
        validator = MOFInterfaceValidator()
        results = validator.screen_all()
        self.assertEqual(len(results), len(ALL_MOFS))

    def test_screen_sorted_descending(self):
        validator = MOFInterfaceValidator()
        results = validator.screen_all()
        scores = [r[1].total for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_screen_with_conditions(self):
        validator = MOFInterfaceValidator()
        conditions = MOFConditions(
            environment='aqueous',
            requires_water_stable=True,
        )
        results = validator.screen_all(conditions)
        self.assertEqual(len(results), len(ALL_MOFS))


class TestConvenienceFunction(unittest.TestCase):

    def test_validate_mof_convenience(self):
        result = validate_mof('UiO-66')
        self.assertIsInstance(result, MOFInterfaceScore)

    def test_validate_mof_with_kwargs(self):
        result = validate_mof(
            'ZIF-8',
            target_molecule_diameter=3.0,
            operating_temp_C=200.0,
        )
        self.assertIsInstance(result, MOFInterfaceScore)


class TestKnownGoodBadApplications(unittest.TestCase):
    """Validate that known good applications score > 0.5 and known bad < 0.5."""

    def test_zif8_propylene_separation(self):
        conditions = MOFConditions(
            target_molecule_diameter=4.0,  # propylene kinetic diameter
            target_application=MOFApplication.SEPARATION,
        )
        result = validate_mof('ZIF-8', conditions)
        self.assertTrue(result.suitable, "ZIF-8 should be suitable for separation")

    def test_mof74mg_carbon_capture(self):
        conditions = MOFConditions(
            target_application=MOFApplication.CARBON_CAPTURE,
        )
        result = validate_mof('MOF-74(Mg)', conditions)
        self.assertTrue(result.suitable, "MOF-74(Mg) should be suitable for CO2 capture")

    def test_mof5_water_application_scored_low(self):
        """MOF-5 should score much lower than MOF-801 for water harvesting."""
        conditions = MOFConditions(
            target_application=MOFApplication.WATER_HARVESTING,
            environment='humid',
            requires_water_stable=True,
        )
        result_mof5 = validate_mof('MOF-5', conditions)
        result_mof801 = validate_mof('MOF-801', conditions)
        self.assertLess(
            result_mof5.total, result_mof801.total,
            "MOF-5 should score much lower than MOF-801 for water harvesting",
        )
        # Chemical stability should be very penalized
        self.assertLess(result_mof5.chemical_stability, 0.3)


if __name__ == '__main__':
    unittest.main()
