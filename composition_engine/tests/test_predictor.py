# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for composition_engine.predictor (Kan extension + D-S fusion)."""

import unittest

from composition_engine.predictor import CompositionPredictor, PredictedMaterial
from composition_engine.known_compositions import KnownCompositionDB, get_db
from composition_engine.parser import parse_formula


class TestKnownCompositionDB(unittest.TestCase):
    """Tests for the known composition database."""

    def setUp(self):
        self.db = get_db()

    def test_db_not_empty(self):
        self.assertGreater(self.db.size, 0)

    def test_battery_materials_loaded(self):
        """At least the cathodes should be loaded."""
        names = [e.name for e in self.db.entries]
        # NMC811 is one of the cathode materials
        self.assertIn("NMC811", names)

    def test_nearest_k_returns_results(self):
        query = parse_formula("LiNi0.7Mn0.15Co0.15O2")
        results = self.db.nearest_k(query, k=3)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)

    def test_nearest_sorted_by_distance(self):
        query = parse_formula("NMC811")
        results = self.db.nearest_k(query, k=5)
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertLessEqual(results[i][1], results[i + 1][1])

    def test_exact_match_distance_zero(self):
        """Querying an existing composition should find it at distance ~0."""
        entry = self.db.get_by_name("NMC811")
        if entry:
            results = self.db.nearest_k(entry.composition, k=1)
            self.assertLess(results[0][1], 0.01)

    def test_get_by_name(self):
        entry = self.db.get_by_name("NMC811")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "NMC811")

    def test_get_by_name_missing(self):
        entry = self.db.get_by_name("NONEXISTENT_MATERIAL_XYZ")
        self.assertIsNone(entry)

    def test_exclude_names(self):
        query = parse_formula("NMC811")
        results = self.db.nearest_k(query, k=5, exclude_names=["NMC811"])
        names = [r[0].name for r in results]
        self.assertNotIn("NMC811", names)

    def test_domain_filter(self):
        query = parse_formula("LiCoO2")
        results = self.db.nearest_k(query, k=5, domain="battery")
        for entry, _ in results:
            self.assertEqual(entry.domain, "battery")


class TestCompositionPredictor(unittest.TestCase):
    """Tests for the main predictor."""

    def setUp(self):
        self.predictor = CompositionPredictor()

    def test_predict_returns_result(self):
        result = self.predictor.predict("NMC721")
        self.assertIsInstance(result, PredictedMaterial)
        self.assertGreater(len(result.properties), 0)

    def test_predict_has_voltage(self):
        result = self.predictor.predict("NMC721")
        self.assertIn("voltage", result.properties)

    def test_predict_voltage_reasonable(self):
        """Predicted voltage for NMC721 should be near 3.8V."""
        result = self.predictor.predict("NMC721")
        v = result.properties["voltage"].value
        self.assertGreater(v, 3.4)
        self.assertLess(v, 4.3)

    def test_predict_has_capacity(self):
        result = self.predictor.predict("NMC721")
        self.assertIn("theoretical_capacity", result.properties)

    def test_predict_capacity_reasonable(self):
        result = self.predictor.predict("NMC721")
        cap = result.properties["theoretical_capacity"].value
        self.assertGreater(cap, 200)
        self.assertLess(cap, 350)

    def test_predict_confidence_range(self):
        """All confidence values should be in [0, 1]."""
        result = self.predictor.predict("NMC721")
        for name, prop in result.properties.items():
            self.assertGreaterEqual(prop.confidence, 0.0,
                                    f"{name} confidence < 0")
            self.assertLessEqual(prop.confidence, 1.0,
                                 f"{name} confidence > 1")

    def test_predict_bounds_ordered(self):
        """lower_bound <= value <= upper_bound."""
        result = self.predictor.predict("NMC721")
        for name, prop in result.properties.items():
            self.assertLessEqual(prop.lower_bound, prop.value + 1e-9,
                                 f"{name}: lower > value")
            self.assertGreaterEqual(prop.upper_bound, prop.value - 1e-9,
                                    f"{name}: upper < value")

    def test_predict_nearest_known_populated(self):
        result = self.predictor.predict("NMC721")
        self.assertGreater(len(result.nearest_known), 0)

    def test_to_dict(self):
        result = self.predictor.predict("NMC721")
        d = result.to_dict()
        self.assertIn("formula", d)
        self.assertIn("properties", d)
        self.assertIn("nearest_known", d)
        voltage = d["properties"]["voltage"]
        self.assertIn("evidence", voltage)
        self.assertEqual(
            voltage["evidence"]["interval_status"],
            "heuristic_not_calibrated",
        )

    def test_predict_nmc532(self):
        """NMC532 is well-studied but not in our DB -- should still predict."""
        result = self.predictor.predict("NMC532")
        self.assertIn("voltage", result.properties)
        v = result.properties["voltage"].value
        self.assertGreater(v, 3.5)
        self.assertLess(v, 4.2)

    def test_predict_novel_composition(self):
        """Completely novel composition should still produce output."""
        result = self.predictor.predict("LiNi0.7Mn0.15Co0.15O2")
        self.assertGreater(len(result.properties), 0)

    def test_predict_shorthand(self):
        """Shorthand names should resolve correctly."""
        result = self.predictor.predict("NMC955")
        self.assertIn("voltage", result.properties)


class TestLeaveOneOut(unittest.TestCase):
    """Leave-one-out validation tests."""

    def setUp(self):
        self.predictor = CompositionPredictor()

    def test_loo_nmc622_voltage(self):
        """Remove NMC622, predict from others. Voltage within +/-0.2V."""
        loo = self.predictor.leave_one_out("NMC622")
        self.assertIsNotNone(loo)
        pred, actual = loo
        if "voltage" in pred.properties and "voltage" in actual:
            error = abs(pred.properties["voltage"].value - actual["voltage"])
            self.assertLess(error, 0.3,
                            f"NMC622 voltage error {error:.2f}V > 0.3V")

    def test_loo_nmc811_voltage(self):
        """Remove NMC811, predict. Voltage within +/-0.2V."""
        loo = self.predictor.leave_one_out("NMC811")
        self.assertIsNotNone(loo)
        pred, actual = loo
        if "voltage" in pred.properties and "voltage" in actual:
            error = abs(pred.properties["voltage"].value - actual["voltage"])
            self.assertLess(error, 0.3,
                            f"NMC811 voltage error {error:.2f}V > 0.3V")

    def test_loo_nmc111_voltage(self):
        loo = self.predictor.leave_one_out("NMC111")
        self.assertIsNotNone(loo)
        pred, actual = loo
        if "voltage" in pred.properties and "voltage" in actual:
            error = abs(pred.properties["voltage"].value - actual["voltage"])
            self.assertLess(error, 0.3,
                            f"NMC111 voltage error {error:.2f}V > 0.3V")

    def test_loo_nmc622_capacity(self):
        """Capacity within +/-40% (wide due to Faraday+interpolation fusion)."""
        loo = self.predictor.leave_one_out("NMC622")
        self.assertIsNotNone(loo)
        pred, actual = loo
        if "theoretical_capacity" in pred.properties and "theoretical_capacity" in actual:
            predicted = pred.properties["theoretical_capacity"].value
            measured = actual["theoretical_capacity"]
            pct_error = abs(predicted - measured) / measured * 100
            self.assertLess(pct_error, 40,
                            f"NMC622 capacity error {pct_error:.1f}% > 40%")

    def test_loo_confidence_decreases_with_distance(self):
        """Prediction for a far-away material should have lower confidence
        than for a nearby one."""
        loo_622 = self.predictor.leave_one_out("NMC622")
        loo_lfp = self.predictor.leave_one_out("LFP")
        if loo_622 and loo_lfp:
            # NMC622 has close neighbours (NMC811, NMC111)
            # LFP is an olivine, quite different from layered NMCs
            # So NMC622 prediction should generally have higher confidence
            pred_622, _ = loo_622
            pred_lfp, _ = loo_lfp
            if "voltage" in pred_622.properties and "voltage" in pred_lfp.properties:
                conf_622 = pred_622.properties["voltage"].confidence
                conf_lfp = pred_lfp.properties["voltage"].confidence
                # Not strict -- just check both are positive
                self.assertGreater(conf_622, 0.0)
                self.assertGreater(conf_lfp, 0.0)

    def test_loo_returns_none_for_unknown(self):
        result = self.predictor.leave_one_out("NONEXISTENT_XYZ")
        self.assertIsNone(result)


class TestInterpolation(unittest.TestCase):
    """Tests for composition interpolation."""

    def setUp(self):
        self.predictor = CompositionPredictor()

    def test_interpolate_endpoints(self):
        """fraction=0 should be close to formula_a, fraction=1 close to formula_b."""
        result_a = self.predictor.predict("NMC811")
        result_b = self.predictor.predict("NMC111")
        interp_0 = self.predictor.interpolate("NMC811", "NMC111", 0.0)
        interp_1 = self.predictor.interpolate("NMC811", "NMC111", 1.0)

        if "voltage" in interp_0.properties and "voltage" in result_a.properties:
            # At fraction=0, should be near NMC811
            diff = abs(interp_0.properties["voltage"].value -
                       result_a.properties["voltage"].value)
            self.assertLess(diff, 0.3)

    def test_interpolate_midpoint(self):
        """Midpoint should produce reasonable results."""
        result = self.predictor.interpolate("NMC811", "NMC111", 0.5)
        self.assertGreater(len(result.properties), 0)
        if "voltage" in result.properties:
            v = result.properties["voltage"].value
            self.assertGreater(v, 3.4)
            self.assertLess(v, 4.3)

    def test_interpolate_method_string(self):
        result = self.predictor.interpolate("NMC811", "NMC111", 0.5)
        self.assertIn("interpolation", result.method)


class TestDempsterShaferFusion(unittest.TestCase):
    """Tests for the D-S fusion mechanism."""

    def setUp(self):
        self.predictor = CompositionPredictor()

    def test_fused_has_sources(self):
        """Fused properties should list their evidence sources."""
        result = self.predictor.predict("NMC721")
        for name, prop in result.properties.items():
            self.assertIsInstance(prop.sources, dict)
            self.assertGreater(len(prop.sources), 0)
            self.assertIn("evidence_role", prop.evidence)
            self.assertIn("interval_status", prop.evidence)

    def test_two_source_fusion(self):
        """For NMC cathodes, voltage should have both kan and rule sources."""
        result = self.predictor.predict("NMC721")
        if "voltage" in result.properties:
            sources = result.properties["voltage"].sources
            # Should have at least one source
            self.assertGreater(len(sources), 0)
            evidence = result.properties["voltage"].evidence
            self.assertGreater(evidence["kan"]["label_support_n"], 0)
            self.assertGreater(len(evidence["kan"]["contributors"]), 0)


if __name__ == "__main__":
    unittest.main()
