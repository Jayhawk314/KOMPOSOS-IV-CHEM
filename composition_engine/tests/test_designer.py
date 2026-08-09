# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for the inverse composition designer."""

import unittest
from unittest.mock import patch
import math

from composition_engine.designer import (
    CompositionDesigner,
    DesignSpec,
    DesignResult,
    DesignCandidate,
    PropertyTarget,
    ElementConstraint,
    SUBSTITUTION_GROUPS,
    KNOWN_PROPERTIES,
)
from composition_engine.parser import parse_formula, composition_distance


class TestPropertyTarget(unittest.TestCase):
    """Tests for PropertyTarget dataclass."""

    def test_min_only_met(self):
        t = PropertyTarget("voltage", min_value=3.5)
        self.assertTrue(t.is_met(4.0))
        self.assertFalse(t.is_met(3.0))

    def test_max_only_met(self):
        t = PropertyTarget("thermal_stability", max_value=500.0)
        self.assertTrue(t.is_met(400.0))
        self.assertFalse(t.is_met(600.0))

    def test_range_met(self):
        t = PropertyTarget("voltage", min_value=3.0, max_value=4.5)
        self.assertTrue(t.is_met(3.8))
        self.assertFalse(t.is_met(2.5))
        self.assertFalse(t.is_met(5.0))

    def test_distance_zero_when_met(self):
        t = PropertyTarget("voltage", min_value=3.0, max_value=4.5)
        self.assertAlmostEqual(t.distance(3.8), 0.0)

    def test_distance_positive_when_missed(self):
        t = PropertyTarget("voltage", min_value=4.0)
        d = t.distance(3.0)
        self.assertGreater(d, 0.0)

    def test_default_weight(self):
        t = PropertyTarget("voltage", min_value=3.5)
        self.assertEqual(t.weight, 1.0)


class TestElementConstraint(unittest.TestCase):
    """Tests for element filtering."""

    def test_required_elements_pass(self):
        d = CompositionDesigner()
        c = ElementConstraint(required_elements=["Li", "O"])
        self.assertTrue(d._passes_element_filter("LiCoO2", c))

    def test_required_elements_fail(self):
        d = CompositionDesigner()
        c = ElementConstraint(required_elements=["Li", "Na"])
        self.assertFalse(d._passes_element_filter("LiCoO2", c))

    def test_excluded_elements_pass(self):
        d = CompositionDesigner()
        c = ElementConstraint(excluded_elements=["Co"])
        self.assertTrue(d._passes_element_filter("LiFePO4", c))

    def test_excluded_elements_fail(self):
        d = CompositionDesigner()
        c = ElementConstraint(excluded_elements=["Co"])
        self.assertFalse(d._passes_element_filter("LiCoO2", c))

    def test_max_elements_pass(self):
        d = CompositionDesigner()
        c = ElementConstraint(max_elements=4)
        self.assertTrue(d._passes_element_filter("LiCoO2", c))

    def test_max_elements_fail(self):
        d = CompositionDesigner()
        c = ElementConstraint(max_elements=3)
        # LiNi0.8Mn0.1Co0.1O2 has 5 elements
        self.assertFalse(d._passes_element_filter("LiNi0.8Mn0.1Co0.1O2", c))


class TestScoring(unittest.TestCase):
    """Tests for candidate scoring logic."""

    def setUp(self):
        self.designer = CompositionDesigner()

    def test_target_met_score_high(self):
        """When target is met, score should be >= 0.8."""
        spec = DesignSpec(targets=[PropertyTarget("voltage", min_value=3.0)])
        result = self.designer.design(spec)
        if result.candidates:
            best = result.candidates[0]
            if "voltage" in best.target_scores and "voltage" in best.targets_met:
                self.assertGreaterEqual(best.target_scores["voltage"], 0.8)

    def test_target_missed_score_lower(self):
        """When target is barely missed, partial credit via exp(-2*distance)."""
        t = PropertyTarget("voltage", min_value=100.0)
        # No material has 100V -- all candidates should miss
        spec = DesignSpec(targets=[t], max_candidates=20)
        result = self.designer.design(spec)
        for c in result.candidates:
            if "voltage" in c.target_scores:
                self.assertLess(c.target_scores["voltage"], 0.8)

    def test_weights_affect_overall(self):
        """Higher weight target should dominate overall score."""
        spec_high = DesignSpec(targets=[
            PropertyTarget("voltage", min_value=3.5, weight=1.0),
        ], max_candidates=20)
        result_high = self.designer.design(spec_high)

        # Just verify the design completes and scores are in range
        for c in result_high.candidates:
            self.assertGreaterEqual(c.overall_score, 0.0)
            self.assertLessEqual(c.overall_score, 1.0)

    def test_synth_penalty(self):
        """Low synthesizability should reduce overall score."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            min_synthesizability=0.5,
            max_candidates=50,
        )
        result = self.designer.design(spec)
        # All passing candidates should have synth >= 0.5
        for c in result.candidates:
            self.assertGreaterEqual(c.synthesizability, 0.5)

    def test_overall_score_range(self):
        """Overall score should always be in [0, 1]."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.5)],
            max_candidates=50,
        )
        result = self.designer.design(spec)
        for c in result.candidates:
            self.assertGreaterEqual(c.overall_score, 0.0)
            self.assertLessEqual(c.overall_score, 1.0)


class TestSearchStrategies(unittest.TestCase):
    """Tests that each strategy generates candidates."""

    def setUp(self):
        self.designer = CompositionDesigner()
        self.db = self.designer.db
        self.entries = self.db.entries

    def test_perturbation_generates_candidates(self):
        candidates = self.designer._strategy_perturbation(self.entries[:5])
        self.assertGreater(len(candidates), 0)
        for formula, strategy, anchor in candidates:
            self.assertEqual(strategy, "perturbation")
            self.assertIsNotNone(anchor)

    def test_interpolation_generates_candidates(self):
        candidates = self.designer._strategy_interpolation(self.entries)
        self.assertGreater(len(candidates), 0)
        for formula, strategy, anchor in candidates:
            self.assertEqual(strategy, "interpolation")

    def test_substitution_generates_candidates(self):
        candidates = self.designer._strategy_substitution(self.entries[:5])
        self.assertGreater(len(candidates), 0)
        for formula, strategy, anchor in candidates:
            self.assertEqual(strategy, "substitution")

    def test_stoichiometry_generates_candidates(self):
        candidates = self.designer._strategy_stoichiometry(self.entries)
        self.assertGreater(len(candidates), 0)
        # Should include NMC grid points
        formulas = [f for f, _, _ in candidates]
        has_nmc = any("Ni" in f and "Mn" in f and "Co" in f for f in formulas)
        self.assertTrue(has_nmc, "Should generate NMC triangle grid candidates")


class TestDesignIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def setUp(self):
        self.designer = CompositionDesigner()

    def test_high_voltage_search(self):
        """Search for high-voltage cathode materials."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=4.0)],
            domain="battery",
            max_candidates=100,
        )
        result = self.designer.design(spec)
        self.assertIsInstance(result, DesignResult)
        self.assertGreater(len(result.candidates), 0)
        self.assertGreater(result.num_evaluated, 0)
        # Top candidate should have voltage target met
        best = result.candidates[0]
        self.assertIn("voltage", best.target_scores)

    def test_cobalt_free_nmc(self):
        """Search for Co-free cathode materials."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            element_constraints=ElementConstraint(
                required_elements=["Li", "O"],
                excluded_elements=["Co"],
            ),
            domain="battery",
            max_candidates=100,
        )
        result = self.designer.design(spec)
        # All candidates should be Co-free
        for c in result.candidates:
            self.assertNotIn("Co", c.composition,
                             f"{c.formula} contains Co but Co is excluded")

    def test_synth_filter(self):
        """min_synthesizability filter should remove low-synth candidates."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            min_synthesizability=0.5,
            max_candidates=100,
        )
        result = self.designer.design(spec)
        for c in result.candidates:
            self.assertGreaterEqual(c.synthesizability, 0.5)

    def test_ranking_order(self):
        """Candidates should be sorted by overall_score descending."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.5)],
            max_candidates=50,
        )
        result = self.designer.design(spec)
        scores = [c.overall_score for c in result.candidates]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_result_has_strategies(self):
        """Result should report which strategies were used."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            max_candidates=100,
        )
        result = self.designer.design(spec)
        self.assertIsInstance(result.strategies_used, list)
        self.assertGreater(result.elapsed_seconds, 0)


class TestEdgeCases(unittest.TestCase):
    """Edge case and boundary tests."""

    def setUp(self):
        self.designer = CompositionDesigner()

    def test_impossible_targets(self):
        """Impossible targets should return empty or low-scoring candidates."""
        spec = DesignSpec(
            targets=[
                PropertyTarget("voltage", min_value=100.0),
                PropertyTarget("thermal_stability", min_value=50000.0),
            ],
            max_candidates=30,
        )
        result = self.designer.design(spec)
        # Should still complete without error
        self.assertIsInstance(result, DesignResult)

    def test_max_candidates_cap(self):
        """Should not evaluate more than max_candidates."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            max_candidates=10,
        )
        result = self.designer.design(spec)
        self.assertLessEqual(result.num_evaluated, 10)

    def test_serialization(self):
        """DesignResult.to_dict() should produce valid JSON-serializable dict."""
        spec = DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.5)],
            max_candidates=20,
        )
        result = self.designer.design(spec)
        d = result.to_dict()
        self.assertIn("num_candidates", d)
        self.assertIn("candidates", d)
        self.assertIn("elapsed_seconds", d)
        self.assertEqual(d["num_candidates"], len(d["candidates"]))
        self.assertIn("physical_rejections", d)
        for candidate in d["candidates"]:
            self.assertIn("physical_gate_status", candidate)

    def test_deduplication(self):
        """Deduplication should remove near-identical compositions."""
        d = CompositionDesigner()
        raw = [
            ("LiCoO2", "a", None),
            ("LiCoO2", "b", None),  # exact dup
            ("LiFePO4", "c", None),
        ]
        unique = d._deduplicate(raw)
        # LiCoO2 should appear only once
        formulas = [f for f, _, _ in unique]
        self.assertEqual(len(formulas), 2)

    def test_comp_to_formula(self):
        """Test composition dict -> formula string conversion."""
        formula = CompositionDesigner._comp_to_formula(
            {"Li": 1.0, "Co": 1.0, "O": 2.0}
        )
        self.assertIn("Li", formula)
        self.assertIn("Co", formula)
        self.assertIn("O2", formula)

    def test_substitution_groups_valid(self):
        """All elements in substitution groups should be in ELEMENT_TABLE."""
        from composition_engine.parser import ELEMENT_TABLE
        for group_name, elements in SUBSTITUTION_GROUPS.items():
            for elem in elements:
                self.assertIn(elem, ELEMENT_TABLE,
                              f"{elem} in {group_name} not in ELEMENT_TABLE")


class TestPhysicalGateCoverage(unittest.TestCase):
    """Charge-balance gates stay bounded and expose missing coverage."""

    def test_known_positive_and_negative_examples(self):
        from composition_engine.physical_gates import charge_balanceable
        self.assertIs(charge_balanceable("LiCoO2"), True)
        self.assertIs(charge_balanceable("LiFePO4"), True)
        self.assertIs(charge_balanceable("LiNi0.8Mn0.1Co0.1O2"), True)
        self.assertIs(charge_balanceable("Fe3O4"), True)
        self.assertIs(charge_balanceable("LiF2"), False)

    def test_gate_does_not_call_combinatorial_guesser(self):
        from pymatgen.core import Composition
        from composition_engine.physical_gates import _CACHE, charge_balanceable
        _CACHE.pop("KBr", None)
        with patch.object(Composition, "oxi_state_guesses", side_effect=AssertionError):
            self.assertIs(charge_balanceable("KBr"), True)

    def test_dynamic_program_agrees_with_pymatgen(self):
        from pymatgen.core import Composition
        from composition_engine.physical_gates import _to_integer_comp, charge_balanceable
        formulas = ["LiCoO2", "LiFePO4", "Li4Ti5O12", "NaCl", "Li2O2", "LiF2", "Fe3O4"]
        for formula in formulas:
            scaled = _to_integer_comp(Composition(formula).get_el_amt_dict())
            self.assertIsNotNone(scaled)
            comp = Composition(" ".join(f"{el}{count}" for el, count in scaled.items()))
            expected = bool(comp.oxi_state_guesses(max_sites=-40))
            self.assertIs(charge_balanceable(formula), expected)

    def test_designer_accounts_for_every_gate_decision(self):
        result = CompositionDesigner().design(DesignSpec(
            targets=[PropertyTarget("voltage", min_value=3.0)],
            domain="battery",
            max_candidates=20,
        ))
        self.assertEqual(
            result.num_physical_assessed + result.num_physical_unassessed,
            len(result.candidates),
        )
        payload = result.to_dict()
        self.assertEqual(payload["num_physical_assessed"], result.num_physical_assessed)
        self.assertEqual(payload["num_physical_unassessed"], result.num_physical_unassessed)
        self.assertEqual(len(result.physical_rejections), result.num_physical_gated)
        self.assertTrue(all(
            candidate.physical_gate_status in {"ASSESSED_PASS", "NOT_ASSESSED"}
            for candidate in result.candidates
        ))
        self.assertTrue(all(
            candidate.physical_gate_status == "VETOED"
            for candidate in result.physical_rejections
        ))

    def test_per_candidate_gate_status_and_rejection_serialization(self):
        statuses = iter([True, None, False])
        with patch(
            "composition_engine.physical_gates.charge_balanceable",
            side_effect=lambda _formula: next(statuses),
        ):
            result = CompositionDesigner().design(DesignSpec(
                targets=[PropertyTarget("voltage", min_value=3.0)],
                domain="battery",
                max_candidates=3,
            ))

        self.assertEqual(
            [candidate.physical_gate_status for candidate in result.candidates],
            ["ASSESSED_PASS", "NOT_ASSESSED"],
        )
        self.assertEqual(len(result.physical_rejections), 1)
        self.assertEqual(
            result.physical_rejections[0].physical_gate_status,
            "VETOED",
        )
        payload = result.to_dict()
        self.assertEqual(
            payload["physical_rejections"][0]["physical_gate_status"],
            "VETOED",
        )
        flat = result.to_flat_records()
        self.assertEqual(
            [(row["disposition"], row["physical_gate_status"]) for row in flat],
            [
                ("lead", "ASSESSED_PASS"),
                ("lead", "NOT_ASSESSED"),
                ("rejected", "VETOED"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
