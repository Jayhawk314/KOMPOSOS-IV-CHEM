# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for synthesis route planner."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from synthesis_planner.route_planner import (
    SynthesisPlanner, MaterialSpec, SynthesisAnalysis, ScoredRoute,
)


class TestPlannerSetup(unittest.TestCase):
    """Test planner initialization."""

    def test_creates_planner(self):
        p = SynthesisPlanner()
        self.assertIsNotNone(p)

    def test_custom_weights(self):
        p = SynthesisPlanner(feasibility_weight=0.5, cost_weight=0.1,
                             time_weight=0.1, safety_weight=0.3)
        self.assertIsNotNone(p)


class TestPlanSynthesis(unittest.TestCase):
    """Test plan_synthesis for specific targets."""

    def setUp(self):
        self.planner = SynthesisPlanner()

    def test_lfp_returns_routes(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertIsInstance(a, SynthesisAnalysis)
        self.assertEqual(len(a.routes), 3)

    def test_lfp_has_best_route(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertIsNotNone(a.best_route)
        self.assertIsInstance(a.best_route, ScoredRoute)

    def test_lfp_best_route_is_highest_score(self):
        a = self.planner.plan_synthesis("LFP")
        scores = [r.composite_score for r in a.routes]
        self.assertEqual(a.best_route.composite_score, max(scores))

    def test_nmc811_returns_routes(self):
        a = self.planner.plan_synthesis("NMC811")
        self.assertGreater(len(a.routes), 0)
        self.assertEqual(a.routes[0].route.target, "NMC811")

    def test_llzo_returns_routes(self):
        a = self.planner.plan_synthesis("LLZO")
        self.assertGreater(len(a.routes), 0)

    def test_unknown_target(self):
        a = self.planner.plan_synthesis("NONEXISTENT")
        self.assertEqual(len(a.routes), 0)
        self.assertIsNone(a.best_route)
        self.assertGreater(len(a.warnings), 0)
        self.assertTrue(any("No synthesis routes" in w for w in a.warnings))


class TestScoredRouteStructure(unittest.TestCase):
    """Test scored route fields."""

    def setUp(self):
        self.planner = SynthesisPlanner()
        self.analysis = self.planner.plan_synthesis("LFP")

    def test_scores_in_range(self):
        for sr in self.analysis.routes:
            for field_name in ['feasibility_score', 'cost_score',
                               'time_score', 'safety_score', 'composite_score']:
                val = getattr(sr, field_name)
                self.assertGreaterEqual(val, 0.0, f"{field_name}={val}")
                self.assertLessEqual(val, 1.0, f"{field_name}={val}")

    def test_has_bottleneck(self):
        for sr in self.analysis.routes:
            self.assertIsNotNone(sr.bottleneck_step)

    def test_bottleneck_is_weakest_step(self):
        for sr in self.analysis.routes:
            min_prob = min(s.success_probability for s in sr.route.steps)
            self.assertEqual(sr.bottleneck_step.success_probability, min_prob)

    def test_to_dict(self):
        sr = self.analysis.routes[0]
        d = sr.to_dict()
        self.assertIn('route_name', d)
        self.assertIn('composite', d)
        self.assertIn('bottleneck', d)


class TestAnalysisStructure(unittest.TestCase):
    """Test analysis output structure."""

    def setUp(self):
        self.planner = SynthesisPlanner()

    def test_has_all_fields(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertIsInstance(a.target, str)
        self.assertIsInstance(a.routes, list)
        self.assertIsInstance(a.precursor_cost_usd, float)
        self.assertIsInstance(a.total_time_hours, float)
        self.assertIsInstance(a.equipment_needed, list)
        self.assertIsInstance(a.warnings, list)

    def test_precursor_cost_positive(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertGreater(a.precursor_cost_usd, 0.0)

    def test_total_time_positive(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertGreater(a.total_time_hours, 0.0)

    def test_equipment_non_empty(self):
        a = self.planner.plan_synthesis("LFP")
        self.assertGreater(len(a.equipment_needed), 0)

    def test_to_dict(self):
        a = self.planner.plan_synthesis("LFP")
        d = a.to_dict()
        self.assertIn('target', d)
        self.assertIn('num_routes', d)
        self.assertIn('best_route', d)


class TestEquipmentConstraints(unittest.TestCase):
    """Test equipment availability constraints."""

    def setUp(self):
        self.planner = SynthesisPlanner()

    def test_no_equipment_constraint(self):
        a = self.planner.plan_synthesis("LFP")
        for sr in a.routes:
            self.assertEqual(len(sr.missing_equipment), 0)

    def test_limited_equipment_flags_missing(self):
        a = self.planner.plan_synthesis("LFP",
            available_equipment=["stirrer"])
        # At least some routes need equipment not in the list
        some_missing = any(len(sr.missing_equipment) > 0 for sr in a.routes)
        self.assertTrue(some_missing)

    def test_limited_equipment_lowers_score(self):
        full = self.planner.plan_synthesis("LFP")
        limited = self.planner.plan_synthesis("LFP",
            available_equipment=["stirrer"])
        # Best score with full equipment >= best score with limited
        self.assertGreaterEqual(
            full.best_route.composite_score,
            limited.best_route.composite_score,
        )


class TestHighRiskRoutes(unittest.TestCase):
    """Test routes with hazardous materials."""

    def setUp(self):
        self.planner = SynthesisPlanner()

    def test_lgps_has_warnings(self):
        a = self.planner.plan_synthesis("LGPS")
        self.assertGreater(len(a.warnings), 0)
        self.assertTrue(any("HIGH risk" in w for w in a.warnings))

    def test_lgps_safety_score_low(self):
        a = self.planner.plan_synthesis("LGPS")
        self.assertLess(a.best_route.safety_score, 0.8)


class TestPlanFromSpec(unittest.TestCase):
    """Test specification-based planning."""

    def setUp(self):
        self.planner = SynthesisPlanner()

    def test_cathode_spec(self):
        spec = MaterialSpec(target_type="cathode")
        a = self.planner.plan_from_spec(spec)
        self.assertIsNotNone(a.best_route)
        self.assertGreater(len(a.routes), 0)

    def test_cathode_spec_with_voltage(self):
        spec = MaterialSpec(
            target_type="cathode",
            required_properties={"voltage_nominal_min": 3.5},
        )
        a = self.planner.plan_from_spec(spec)
        self.assertIsNotNone(a.best_route)

    def test_electrolyte_spec(self):
        spec = MaterialSpec(target_type="electrolyte_solid")
        a = self.planner.plan_from_spec(spec)
        self.assertIsNotNone(a.best_route)

    def test_unknown_target_type(self):
        spec = MaterialSpec(target_type="NONEXISTENT_TYPE")
        a = self.planner.plan_from_spec(spec)
        self.assertIsNone(a.best_route)
        self.assertGreater(len(a.warnings), 0)

    def test_spec_with_equipment(self):
        spec = MaterialSpec(
            target_type="cathode",
            available_equipment=["furnace", "ball_mill", "stirrer",
                                "oven", "mixer", "mortar", "filter"],
        )
        a = self.planner.plan_from_spec(spec)
        self.assertIsNotNone(a.best_route)


class TestMultipleTargets(unittest.TestCase):
    """Test that all defined targets can be planned."""

    def test_all_targets_scoreable(self):
        from synthesis_planner.route_graph import list_all_targets
        planner = SynthesisPlanner()
        for target in list_all_targets():
            a = planner.plan_synthesis(target)
            self.assertGreater(len(a.routes), 0,
                               f"No routes for {target}")
            self.assertIsNotNone(a.best_route,
                                 f"No best route for {target}")


if __name__ == '__main__':
    unittest.main()
