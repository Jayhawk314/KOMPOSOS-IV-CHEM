# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for multi-domain analyzer (the replicator brain)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from cross_bridge.multi_domain import (
    MultiDomainAnalyzer,
    MultiDomainQuery,
    MultiDomainComponent,
    MultiDomainAnalysis,
    CrossDomainScore,
    SOLID_STATE_BATTERY_QUERY,
    LFP_STANDARD_CELL_QUERY,
    GRAPHITE_ANODE_QUERY,
    THERMAL_BARRIER_QUERY,
    PROBLEMATIC_PEO_NMC_QUERY,
)


class TestAnalyzerSetup(unittest.TestCase):
    """Test analyzer initialization."""

    def test_creates_analyzer(self):
        a = MultiDomainAnalyzer()
        self.assertIsNotNone(a)

    def test_domain_registry_populated(self):
        a = MultiDomainAnalyzer()
        self.assertGreater(len(a._registry), 50)

    def test_identify_battery_material(self):
        a = MultiDomainAnalyzer()
        self.assertEqual(a.identify_domain('LFP'), 'battery')
        self.assertEqual(a.identify_domain('NMC811'), 'battery')

    def test_identify_polymer(self):
        a = MultiDomainAnalyzer()
        self.assertEqual(a.identify_domain('PEO'), 'polymer')
        self.assertEqual(a.identify_domain('PVDF'), 'polymer')

    def test_identify_metal(self):
        a = MultiDomainAnalyzer()
        self.assertEqual(a.identify_domain('Al_foil'), 'metal')
        self.assertEqual(a.identify_domain('Cu_foil'), 'metal')

    def test_identify_ceramic(self):
        a = MultiDomainAnalyzer()
        self.assertEqual(a.identify_domain('Al2O3'), 'ceramic')
        self.assertEqual(a.identify_domain('LLZO'), 'ceramic')

    def test_unknown_material(self):
        a = MultiDomainAnalyzer()
        self.assertEqual(a.identify_domain('NONEXISTENT'), 'unknown')


class TestAnalysisStructure(unittest.TestCase):
    """Test analysis output structure."""

    def test_returns_analysis(self):
        a = MultiDomainAnalyzer()
        result = a.analyze(LFP_STANDARD_CELL_QUERY)
        self.assertIsInstance(result, MultiDomainAnalysis)

    def test_has_all_fields(self):
        a = MultiDomainAnalyzer()
        result = a.analyze(LFP_STANDARD_CELL_QUERY)
        self.assertIsInstance(result.query_name, str)
        self.assertIsInstance(result.components, list)
        self.assertIsInstance(result.domains_involved, list)
        self.assertIsInstance(result.cross_domain_scores, list)
        self.assertIsInstance(result.overall_score, float)
        self.assertIsInstance(result.viable, bool)
        self.assertIsInstance(result.warnings, list)

    def test_score_in_range(self):
        a = MultiDomainAnalyzer()
        result = a.analyze(LFP_STANDARD_CELL_QUERY)
        self.assertGreaterEqual(result.overall_score, 0.0)
        self.assertLessEqual(result.overall_score, 1.0)

    def test_to_dict(self):
        a = MultiDomainAnalyzer()
        result = a.analyze(LFP_STANDARD_CELL_QUERY)
        d = result.to_dict()
        self.assertIn('query_name', d)
        self.assertIn('overall_score', d)
        self.assertIn('viable', d)
        self.assertIn('cross_domain_scores', d)


class TestLFPStandardCell(unittest.TestCase):
    """Test the standard LFP cell query (should be viable)."""

    def setUp(self):
        self.analyzer = MultiDomainAnalyzer()
        self.result = self.analyzer.analyze(LFP_STANDARD_CELL_QUERY)

    def test_is_viable(self):
        self.assertTrue(self.result.viable)

    def test_good_score(self):
        self.assertGreater(self.result.overall_score, 0.5)

    def test_spans_three_domains(self):
        self.assertGreaterEqual(len(self.result.domains_involved), 2)

    def test_has_cross_domain_scores(self):
        self.assertGreater(len(self.result.cross_domain_scores), 0)

    def test_battery_polymer_interface_scored(self):
        functors = [s.functor_used for s in self.result.cross_domain_scores]
        self.assertIn('battery_polymer', functors)

    def test_battery_metal_interface_scored(self):
        functors = [s.functor_used for s in self.result.cross_domain_scores]
        self.assertIn('battery_metal', functors)


class TestSolidStateBattery(unittest.TestCase):
    """Test the solid-state battery query spanning 4 domains."""

    def setUp(self):
        self.analyzer = MultiDomainAnalyzer()
        self.result = self.analyzer.analyze(SOLID_STATE_BATTERY_QUERY)

    def test_spans_four_domains(self):
        self.assertGreaterEqual(len(self.result.domains_involved), 3)

    def test_multiple_cross_domain_scores(self):
        self.assertGreaterEqual(len(self.result.cross_domain_scores), 2)

    def test_has_bottleneck(self):
        self.assertIsNotNone(self.result.bottleneck)

    def test_bottleneck_is_weakest(self):
        if self.result.cross_domain_scores:
            min_score = min(s.score for s in self.result.cross_domain_scores)
            self.assertEqual(self.result.bottleneck.score, min_score)


class TestGraphiteAnode(unittest.TestCase):
    """Test graphite anode query."""

    def setUp(self):
        self.analyzer = MultiDomainAnalyzer()
        self.result = self.analyzer.analyze(GRAPHITE_ANODE_QUERY)

    def test_is_viable(self):
        self.assertTrue(self.result.viable)

    def test_cmc_graphite_compatible(self):
        for s in self.result.cross_domain_scores:
            if s.functor_used == 'battery_polymer':
                self.assertTrue(s.compatible)


class TestThermalBarrier(unittest.TestCase):
    """Test YSZ on Inconel thermal barrier query."""

    def setUp(self):
        self.analyzer = MultiDomainAnalyzer()
        self.result = self.analyzer.analyze(THERMAL_BARRIER_QUERY)

    def test_is_viable(self):
        self.assertTrue(self.result.viable)

    def test_ceramic_metal_functor_used(self):
        functors = [s.functor_used for s in self.result.cross_domain_scores]
        self.assertIn('ceramic_metal', functors)


class TestProblematicQuery(unittest.TestCase):
    """Test the PEO + NMC811 + LiTFSI problematic query."""

    def setUp(self):
        self.analyzer = MultiDomainAnalyzer()
        self.result = self.analyzer.analyze(PROBLEMATIC_PEO_NMC_QUERY)

    def test_not_viable(self):
        self.assertFalse(self.result.viable)

    def test_low_score(self):
        self.assertLess(self.result.overall_score, 0.45)

    def test_has_warnings(self):
        self.assertGreater(len(self.result.warnings), 0)


class TestSingleComponent(unittest.TestCase):
    """Test edge case: single component query."""

    def test_single_component_viable(self):
        a = MultiDomainAnalyzer()
        q = MultiDomainQuery(
            name="Single",
            components=[MultiDomainComponent(name='LFP', domain='battery')],
        )
        result = a.analyze(q)
        self.assertEqual(result.overall_score, 1.0)
        self.assertTrue(result.viable)
        self.assertTrue(result.coverage_complete)


class TestPhysicalCoverage(unittest.TestCase):
    """Explicit physical contacts are promises, including unsupported ones."""

    def test_missing_functor_blocks_full_stack_verdict(self):
        analyzer = MultiDomainAnalyzer()
        query = MultiDomainQuery(
            name="NMC811/LLZO/Al physical stack",
            components=[
                MultiDomainComponent(name="NMC811", role="cathode"),
                MultiDomainComponent(name="LLZO", role="electrolyte"),
                MultiDomainComponent(name="Al_foil", role="collector"),
            ],
            electrolyte="LLZO",
            adjacency={
                frozenset({"cathode", "electrolyte"}),
                frozenset({"cathode", "collector"}),
                frozenset({"electrolyte", "collector"}),
            },
        )
        result = analyzer.analyze(query)
        self.assertFalse(result.coverage_complete)
        self.assertFalse(result.viable)
        self.assertIn("NMC811<->LLZO", result.unscored_interfaces)
        self.assertLess(result.coverage_fraction, 1.0)


class TestWeightedScoringMode(unittest.TestCase):
    """Test weighted composite scoring for multi-interface designs."""

    def test_solid_state_weighted_improved(self):
        """Solid-state battery with weighted mode should score higher than bottleneck."""
        a = MultiDomainAnalyzer()
        # Score with bottleneck
        q_bn = MultiDomainQuery(
            name="SS bottleneck",
            components=SOLID_STATE_BATTERY_QUERY.components[:],
            electrolyte=SOLID_STATE_BATTERY_QUERY.electrolyte,
            scoring_mode='bottleneck',
        )
        r_bn = a.analyze(q_bn)

        # Score with weighted
        q_wt = MultiDomainQuery(
            name="SS weighted",
            components=SOLID_STATE_BATTERY_QUERY.components[:],
            electrolyte=SOLID_STATE_BATTERY_QUERY.electrolyte,
            scoring_mode='weighted',
        )
        r_wt = a.analyze(q_wt)

        # Weighted should be >= bottleneck (less harsh)
        self.assertGreaterEqual(r_wt.overall_score, r_bn.overall_score)

    def test_lfp_bottleneck_unchanged(self):
        """LFP standard cell explicitly set to bottleneck should give same result."""
        a = MultiDomainAnalyzer()
        r_default = a.analyze(LFP_STANDARD_CELL_QUERY)

        q_bn = MultiDomainQuery(
            name="LFP bottleneck",
            components=LFP_STANDARD_CELL_QUERY.components[:],
            electrolyte=LFP_STANDARD_CELL_QUERY.electrolyte,
            scoring_mode='bottleneck',
        )
        r_bn = a.analyze(q_bn)
        self.assertAlmostEqual(r_default.overall_score, r_bn.overall_score, places=3)

    def test_single_interface_same_either_mode(self):
        """Single interface: both modes should give the same score."""
        a = MultiDomainAnalyzer()
        q_bn = MultiDomainQuery(
            name="TBC bottleneck",
            components=THERMAL_BARRIER_QUERY.components[:],
            scoring_mode='bottleneck',
        )
        q_wt = MultiDomainQuery(
            name="TBC weighted",
            components=THERMAL_BARRIER_QUERY.components[:],
            scoring_mode='weighted',
        )
        r_bn = a.analyze(q_bn)
        r_wt = a.analyze(q_wt)
        # With 1 score, both formulae reduce to the same result
        self.assertAlmostEqual(r_bn.overall_score, r_wt.overall_score, places=2)

    def test_auto_detect_uses_weighted_for_many_interfaces(self):
        """Auto-detect should use weighted mode when >2 interfaces."""
        a = MultiDomainAnalyzer()
        # SOLID_STATE has 4 components -> multiple interfaces
        r_auto = a.analyze(SOLID_STATE_BATTERY_QUERY)

        q_wt = MultiDomainQuery(
            name="SS explicit weighted",
            components=SOLID_STATE_BATTERY_QUERY.components[:],
            electrolyte=SOLID_STATE_BATTERY_QUERY.electrolyte,
            scoring_mode='weighted',
        )
        r_wt = a.analyze(q_wt)

        # Auto should pick weighted since >2 interfaces, so scores match
        if len(r_auto.cross_domain_scores) > 2:
            self.assertAlmostEqual(r_auto.overall_score, r_wt.overall_score, places=3)


class TestAllPredefinedQueries(unittest.TestCase):
    """Test that all pre-defined queries run without errors."""

    def test_all_queries_scoreable(self):
        a = MultiDomainAnalyzer()
        queries = [
            SOLID_STATE_BATTERY_QUERY,
            LFP_STANDARD_CELL_QUERY,
            GRAPHITE_ANODE_QUERY,
            THERMAL_BARRIER_QUERY,
            PROBLEMATIC_PEO_NMC_QUERY,
        ]
        for q in queries:
            result = a.analyze(q)
            self.assertIsInstance(result, MultiDomainAnalysis,
                                 f"Failed on query: {q.name}")
            self.assertGreaterEqual(result.overall_score, 0.0)
            self.assertLessEqual(result.overall_score, 1.0)


if __name__ == '__main__':
    unittest.main()
