# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Tests for composition_engine.properties (rule-based estimation)."""

import unittest

from composition_engine.properties import estimate_properties


class TestEstimateProperties(unittest.TestCase):
    """Tests for rule-based property estimation."""

    def test_nmc811_voltage(self):
        """NMC811 voltage should be near 3.8-3.9V."""
        est = estimate_properties("NMC811")
        self.assertIn("voltage", est.properties)
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.6)
        self.assertLess(v, 4.1)

    def test_nmc811_capacity(self):
        """NMC811 capacity should be near 270-280 mAh/g."""
        est = estimate_properties("NMC811")
        self.assertIn("theoretical_capacity", est.properties)
        cap = est.properties["theoretical_capacity"].value
        self.assertGreater(cap, 240)
        self.assertLess(cap, 310)

    def test_nmc622_voltage(self):
        est = estimate_properties("NMC622")
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.6)
        self.assertLess(v, 4.1)

    def test_nmc111_voltage(self):
        est = estimate_properties("NMC111")
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.7)
        self.assertLess(v, 4.1)

    def test_lfp_voltage(self):
        """LFP should be ~3.4V."""
        est = estimate_properties("LFP")
        self.assertIn("voltage", est.properties)
        v = est.properties["voltage"].value
        self.assertAlmostEqual(v, 3.4, places=1)

    def test_lfp_capacity(self):
        """LFP capacity ~170 mAh/g."""
        est = estimate_properties("LFP")
        cap = est.properties["theoretical_capacity"].value
        self.assertGreater(cap, 140)
        self.assertLess(cap, 200)

    def test_lco_voltage(self):
        est = estimate_properties("LCO")
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.7)
        self.assertLess(v, 4.2)

    def test_lmo_voltage(self):
        est = estimate_properties("LMO")
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.8)
        self.assertLess(v, 4.5)

    def test_thermal_stability_nmc_family(self):
        """Higher Ni -> lower thermal stability."""
        est_811 = estimate_properties("NMC811")
        est_111 = estimate_properties("NMC111")
        if ("thermal_stability" in est_811.properties and
                "thermal_stability" in est_111.properties):
            self.assertLess(
                est_811.properties["thermal_stability"].value,
                est_111.properties["thermal_stability"].value,
            )

    def test_volume_expansion_ni_correlation(self):
        """Higher Ni -> higher volume expansion."""
        est_811 = estimate_properties("NMC811")
        est_111 = estimate_properties("NMC111")
        if ("volume_expansion" in est_811.properties and
                "volume_expansion" in est_111.properties):
            self.assertGreater(
                est_811.properties["volume_expansion"].value,
                est_111.properties["volume_expansion"].value,
            )

    def test_molar_mass_computed(self):
        est = estimate_properties("LCO")
        self.assertIn("molar_mass", est.properties)
        mm = est.properties["molar_mass"].value
        self.assertGreater(mm, 90)
        self.assertLess(mm, 110)

    def test_confidence_in_range(self):
        """All confidences should be 0-1."""
        for formula in ["NMC811", "LFP", "LCO", "NMC622"]:
            est = estimate_properties(formula)
            for name, prop in est.properties.items():
                self.assertGreaterEqual(prop.confidence, 0.0,
                                        f"{formula}.{name} conf < 0")
                self.assertLessEqual(prop.confidence, 1.0,
                                     f"{formula}.{name} conf > 1")

    def test_to_dict(self):
        est = estimate_properties("NMC811")
        d = est.to_dict()
        self.assertEqual(d["formula"], "NMC811")
        self.assertIn("properties", d)
        self.assertIn("voltage", d["properties"])

    def test_novel_nmc_produces_output(self):
        """A novel NMC composition should still produce estimates."""
        est = estimate_properties("LiNi0.7Mn0.15Co0.15O2")
        self.assertIn("voltage", est.properties)
        self.assertIn("theoretical_capacity", est.properties)

    def test_density_estimate(self):
        est = estimate_properties("NMC811")
        if "density" in est.properties:
            d = est.properties["density"].value
            self.assertGreater(d, 4.0)
            self.assertLess(d, 6.0)

    def test_empty_formula(self):
        est = estimate_properties("")
        self.assertEqual(len(est.properties), 0)

    def test_nca_produces_voltage(self):
        """NCA (LiNi0.8Co0.15Al0.05O2) should produce a voltage."""
        est = estimate_properties("NCA")
        self.assertIn("voltage", est.properties)
        v = est.properties["voltage"].value
        self.assertGreater(v, 3.5)
        self.assertLess(v, 4.2)

    def test_nmc532(self):
        """NMC532 (not in bridge DB) should still get estimates."""
        est = estimate_properties("NMC532")
        self.assertIn("voltage", est.properties)
        self.assertIn("theoretical_capacity", est.properties)

    def test_lfp_thermal_stability(self):
        est = estimate_properties("LFP")
        if "thermal_stability" in est.properties:
            self.assertGreater(est.properties["thermal_stability"].value, 350)


class TestEdgeCases(unittest.TestCase):

    def test_non_cathode_no_voltage(self):
        """A formula that isn't a cathode shouldn't produce voltage."""
        est = estimate_properties("NaCl")
        self.assertNotIn("voltage", est.properties)

    def test_high_ni_composition(self):
        """NMC955 should still work."""
        est = estimate_properties("NMC955")
        self.assertIn("voltage", est.properties)


if __name__ == "__main__":
    unittest.main()
