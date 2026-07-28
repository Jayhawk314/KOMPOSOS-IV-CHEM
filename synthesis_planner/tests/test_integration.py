# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for synthesis planner integration with KOMPOSOS categorical layer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from synthesis_planner.route_graph import (
    SynthesisStep, SynthesisConditions,
    LFP_SOLID_STATE, NMC811_COPRECIPITATION, list_all_routes,
)
from synthesis_planner.precursor_db import get_precursor
from synthesis_planner.integration import (
    step_to_stored_morphism,
    route_to_stored_path,
    precursor_to_stored_object,
    build_synthesis_category,
    compute_synthesis_curvature,
    STORE_AVAILABLE,
    CATEGORY_AVAILABLE,
)


@unittest.skipUnless(STORE_AVAILABLE, "data.store not available")
class TestStepToMorphism(unittest.TestCase):
    """Test converting SynthesisStep to StoredMorphism."""

    def test_basic_step(self):
        step = SynthesisStep(
            operation="calcine",
            inputs=["A", "B"],
            output="C",
            conditions=SynthesisConditions(700, 10.0, atmosphere="N2"),
            success_probability=0.85,
            citation="10.1234/test",
        )
        m = step_to_stored_morphism(step)
        self.assertEqual(m.source_name, "A")
        self.assertEqual(m.target_name, "C")
        self.assertEqual(m.confidence, 0.85)
        self.assertIn("synthesis", m.name)

    def test_metadata_populated(self):
        step = LFP_SOLID_STATE.steps[0]
        m = step_to_stored_morphism(step)
        self.assertEqual(m.metadata['operation'], 'mix')
        self.assertIn('temperature_C', m.metadata)
        self.assertIn('equipment', m.metadata)
        self.assertEqual(m.metadata['domain'], 'synthesis')

    def test_morphism_id_format(self):
        step = LFP_SOLID_STATE.steps[0]
        m = step_to_stored_morphism(step)
        self.assertIn("->", m.id)

    def test_all_lfp_steps_convert(self):
        for step in LFP_SOLID_STATE.steps:
            m = step_to_stored_morphism(step)
            self.assertIsNotNone(m.source_name)
            self.assertIsNotNone(m.target_name)


@unittest.skipUnless(STORE_AVAILABLE, "data.store not available")
class TestRouteToPath(unittest.TestCase):
    """Test converting SynthesisRoute to StoredPath."""

    def test_lfp_route_to_path(self):
        p = route_to_stored_path(LFP_SOLID_STATE)
        self.assertEqual(p.target_name, "LFP")
        self.assertEqual(len(p.morphism_ids), len(LFP_SOLID_STATE.steps))
        self.assertGreater(p.length, 0)

    def test_path_confidence(self):
        p = route_to_stored_path(LFP_SOLID_STATE)
        self.assertEqual(p.confidence, LFP_SOLID_STATE.overall_confidence)

    def test_path_metadata(self):
        p = route_to_stored_path(NMC811_COPRECIPITATION)
        self.assertEqual(p.metadata['route_name'], 'NMC811_coprecipitation')
        self.assertEqual(p.metadata['domain'], 'synthesis')
        self.assertIn('total_time_hours', p.metadata)

    def test_all_routes_convert(self):
        for route in list_all_routes():
            p = route_to_stored_path(route)
            self.assertIsNotNone(p.target_name, f"Failed on {route.name}")
            self.assertEqual(len(p.morphism_ids), len(route.steps))


@unittest.skipUnless(STORE_AVAILABLE, "data.store not available")
class TestPrecursorToObject(unittest.TestCase):
    """Test converting Precursor to StoredObject."""

    def test_li2co3(self):
        p = get_precursor("Li2CO3")
        obj = precursor_to_stored_object(p)
        self.assertEqual(obj.name, "Li2CO3")
        self.assertEqual(obj.type_name, "Precursor")
        self.assertEqual(obj.metadata['domain'], 'synthesis')

    def test_metadata_populated(self):
        p = get_precursor("NMP")
        obj = precursor_to_stored_object(p)
        self.assertIn('cost_usd_per_kg', obj.metadata)
        self.assertIn('hazard_class', obj.metadata)
        self.assertIn('formula', obj.metadata)


@unittest.skipUnless(CATEGORY_AVAILABLE, "categorical.category not available")
class TestBuildCategory(unittest.TestCase):
    """Test building a Category from synthesis routes."""

    def test_builds_without_error(self):
        cat = build_synthesis_category()
        self.assertIsNotNone(cat)

    def test_category_has_objects(self):
        cat = build_synthesis_category()
        # Should have many objects (all materials mentioned in routes)
        self.assertGreater(len(cat.objects), 20)

    def test_category_from_subset(self):
        cat = build_synthesis_category([LFP_SOLID_STATE])
        self.assertIsNotNone(cat)
        # LFP solid state has: Li2CO3, Fe2O3, NH4H2PO4, intermediates, LFP
        self.assertGreater(len(cat.objects), 3)


class TestBuildCategoryFallback(unittest.TestCase):
    """Test category building when categorical module not available."""

    def test_returns_none_if_not_available(self):
        if not CATEGORY_AVAILABLE:
            cat = build_synthesis_category()
            self.assertIsNone(cat)


class TestCurvature(unittest.TestCase):
    """Test curvature computation on route graph."""

    def test_returns_dict(self):
        result = compute_synthesis_curvature()
        self.assertIsInstance(result, dict)

    def test_has_expected_keys(self):
        result = compute_synthesis_curvature()
        if 'error' not in result:
            self.assertIn('num_materials', result)
            self.assertIn('num_edges', result)
            self.assertIn('edges', result)


if __name__ == '__main__':
    unittest.main()
