# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for synthesis route graph and curated routes."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from synthesis_planner.route_graph import (
    SynthesisConditions, SynthesisStep, SynthesisRoute,
    build_route, compute_route_confidence, compute_total_time,
    compute_max_temp, derive_precursors,
    get_routes, get_route_by_name, list_all_targets, list_all_routes,
    ALL_ROUTES,
    LFP_SOLID_STATE, LFP_SOL_GEL, LFP_HYDROTHERMAL,
    NMC811_COPRECIPITATION, LLZO_SOLID_STATE, LGPS_BALL_MILL,
)


class TestDataclasses(unittest.TestCase):
    """Test core dataclass creation."""

    def test_synthesis_conditions(self):
        c = SynthesisConditions(temperature_C=700, time_hours=10.0, atmosphere="N2")
        self.assertEqual(c.temperature_C, 700)
        self.assertEqual(c.atmosphere, "N2")
        self.assertEqual(c.pressure_atm, 1.0)  # default

    def test_synthesis_step(self):
        s = SynthesisStep(
            operation="calcine",
            inputs=["A", "B"],
            output="C",
            conditions=SynthesisConditions(temperature_C=500, time_hours=5.0),
            success_probability=0.85,
        )
        self.assertEqual(s.operation, "calcine")
        self.assertEqual(s.inputs, ["A", "B"])
        self.assertEqual(s.output, "C")
        self.assertEqual(s.success_probability, 0.85)


class TestHelperFunctions(unittest.TestCase):
    """Test compute_route_confidence, total_time, max_temp, derive_precursors."""

    def test_confidence_formula(self):
        steps = [
            SynthesisStep("a", ["X"], "Y",
                          SynthesisConditions(100, 1.0), 0.80),
            SynthesisStep("b", ["Y"], "Z",
                          SynthesisConditions(200, 2.0), 0.90),
        ]
        conf = compute_route_confidence(steps)
        expected = 0.75 * 0.80 + 0.25 * (0.80 + 0.90) / 2
        self.assertAlmostEqual(conf, expected, places=4)

    def test_confidence_empty(self):
        self.assertEqual(compute_route_confidence([]), 0.0)

    def test_total_time(self):
        steps = [
            SynthesisStep("a", ["X"], "Y",
                          SynthesisConditions(100, 3.0), 0.9),
            SynthesisStep("b", ["Y"], "Z",
                          SynthesisConditions(200, 7.0), 0.9),
        ]
        self.assertAlmostEqual(compute_total_time(steps), 10.0)

    def test_max_temp(self):
        steps = [
            SynthesisStep("a", ["X"], "Y",
                          SynthesisConditions(100, 1.0), 0.9),
            SynthesisStep("b", ["Y"], "Z",
                          SynthesisConditions(700, 1.0), 0.9),
        ]
        self.assertEqual(compute_max_temp(steps), 700)

    def test_derive_precursors(self):
        steps = [
            SynthesisStep("mix", ["A", "B"], "AB",
                          SynthesisConditions(25, 1.0), 0.95),
            SynthesisStep("calcine", ["AB"], "C",
                          SynthesisConditions(700, 10.0), 0.85),
        ]
        prec = derive_precursors(steps)
        self.assertEqual(prec, ["A", "B"])

    def test_derive_precursors_multi_step(self):
        """Intermediates should not appear as precursors."""
        steps = [
            SynthesisStep("mix", ["A", "B"], "AB",
                          SynthesisConditions(25, 1.0), 0.95),
            SynthesisStep("add", ["AB", "C"], "ABC",
                          SynthesisConditions(25, 1.0), 0.95),
            SynthesisStep("fire", ["ABC"], "D",
                          SynthesisConditions(800, 10.0), 0.85),
        ]
        prec = derive_precursors(steps)
        self.assertIn("A", prec)
        self.assertIn("B", prec)
        self.assertIn("C", prec)
        self.assertNotIn("AB", prec)
        self.assertNotIn("ABC", prec)


class TestBuildRoute(unittest.TestCase):
    """Test the build_route helper."""

    def test_build_route_basic(self):
        steps = [
            SynthesisStep("mix", ["A", "B"], "AB",
                          SynthesisConditions(25, 2.0), 0.95),
            SynthesisStep("fire", ["AB"], "C",
                          SynthesisConditions(700, 10.0), 0.85),
        ]
        r = build_route("test_route", "C", steps)
        self.assertEqual(r.name, "test_route")
        self.assertEqual(r.target, "C")
        self.assertEqual(r.precursors, ["A", "B"])
        self.assertAlmostEqual(r.total_time_hours, 12.0)
        self.assertEqual(r.max_temperature_C, 700)
        self.assertEqual(r.risk_level, "low")

    def test_build_route_high_risk(self):
        steps = [
            SynthesisStep("mill", ["X"], "Y",
                          SynthesisConditions(25, 10.0), 0.80,
                          hazards=["H2S_release"]),
        ]
        r = build_route("risky", "Y", steps)
        self.assertEqual(r.risk_level, "high")


class TestCuratedRoutes(unittest.TestCase):
    """Test that all curated routes are valid."""

    def test_route_count(self):
        all_routes = list_all_routes()
        self.assertGreaterEqual(len(all_routes), 20, "Need at least 20 routes")

    def test_all_routes_have_steps(self):
        for route in list_all_routes():
            self.assertGreater(len(route.steps), 0,
                               f"{route.name} has no steps")

    def test_all_confidences_in_range(self):
        for route in list_all_routes():
            self.assertGreaterEqual(route.overall_confidence, 0.0,
                                    f"{route.name} confidence < 0")
            self.assertLessEqual(route.overall_confidence, 1.0,
                                 f"{route.name} confidence > 1")

    def test_all_step_probabilities_in_range(self):
        for route in list_all_routes():
            for step in route.steps:
                self.assertGreaterEqual(step.success_probability, 0.0,
                                        f"{route.name}/{step.operation} prob < 0")
                self.assertLessEqual(step.success_probability, 1.0,
                                     f"{route.name}/{step.operation} prob > 1")

    def test_all_temperatures_positive(self):
        for route in list_all_routes():
            for step in route.steps:
                self.assertGreaterEqual(step.conditions.temperature_C, 0,
                                        f"{route.name}/{step.operation} temp < 0")

    def test_all_times_positive(self):
        for route in list_all_routes():
            for step in route.steps:
                self.assertGreater(step.conditions.time_hours, 0,
                                   f"{route.name}/{step.operation} time <= 0")

    def test_all_precursors_non_empty(self):
        for route in list_all_routes():
            self.assertGreater(len(route.precursors), 0,
                               f"{route.name} has no precursors")

    def test_confidence_matches_formula(self):
        """Verify overall_confidence = 0.75*min + 0.25*avg for each route."""
        for route in list_all_routes():
            probs = [s.success_probability for s in route.steps]
            expected = 0.75 * min(probs) + 0.25 * (sum(probs) / len(probs))
            self.assertAlmostEqual(route.overall_confidence, expected, places=3,
                                   msg=f"{route.name} confidence mismatch")

    def test_total_time_matches_sum(self):
        for route in list_all_routes():
            expected = sum(s.conditions.time_hours for s in route.steps)
            self.assertAlmostEqual(route.total_time_hours, expected, places=1,
                                   msg=f"{route.name} time mismatch")


class TestSpecificRoutes(unittest.TestCase):
    """Test specific well-known routes."""

    def test_lfp_solid_state(self):
        r = LFP_SOLID_STATE
        self.assertEqual(r.target, "LFP")
        self.assertIn("Li2CO3", r.precursors)
        self.assertIn("Fe2O3", r.precursors)
        self.assertGreater(r.overall_confidence, 0.7)

    def test_lfp_has_three_routes(self):
        routes = get_routes("LFP")
        self.assertEqual(len(routes), 3)

    def test_nmc811_coprecipitation(self):
        r = NMC811_COPRECIPITATION
        self.assertEqual(r.target, "NMC811")
        self.assertIn("NiSO4", r.precursors)
        self.assertIn("MnSO4", r.precursors)
        self.assertIn("CoSO4", r.precursors)

    def test_llzo_solid_state(self):
        r = LLZO_SOLID_STATE
        self.assertEqual(r.target, "LLZO")
        self.assertIn("LiOH", r.precursors)
        self.assertIn("La2O3", r.precursors)
        self.assertIn("ZrO2", r.precursors)

    def test_lgps_is_high_risk(self):
        r = LGPS_BALL_MILL
        self.assertEqual(r.risk_level, "high")


class TestRouteLookup(unittest.TestCase):
    """Test route lookup functions."""

    def test_get_routes_by_target(self):
        routes = get_routes("LFP")
        self.assertGreater(len(routes), 0)
        for r in routes:
            self.assertEqual(r.target, "LFP")

    def test_get_routes_unknown(self):
        routes = get_routes("NONEXISTENT")
        self.assertEqual(len(routes), 0)

    def test_get_route_by_name(self):
        r = get_route_by_name("LFP_solid_state")
        self.assertIsNotNone(r)
        self.assertEqual(r.target, "LFP")

    def test_get_route_by_name_unknown(self):
        r = get_route_by_name("NONEXISTENT_ROUTE")
        self.assertIsNone(r)

    def test_list_all_targets(self):
        targets = list_all_targets()
        self.assertIn("LFP", targets)
        self.assertIn("NMC811", targets)

    def test_alias_lookup(self):
        routes = get_routes("LiFePO4")
        self.assertGreater(len(routes), 0)


if __name__ == '__main__':
    unittest.main()
