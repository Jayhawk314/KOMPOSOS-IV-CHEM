# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for precursor database."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from synthesis_planner.precursor_db import (
    Precursor, ALL_PRECURSORS,
    get_precursor, list_precursors,
    estimate_route_cost, check_availability,
    find_missing_precursors, find_hazardous_precursors,
)


class TestPrecursorStructure(unittest.TestCase):
    """Test precursor dataclass structure."""

    def test_precursor_creation(self):
        p = Precursor("test", "H2O", cost_usd_per_kg=1.0)
        self.assertEqual(p.name, "test")
        self.assertEqual(p.formula, "H2O")
        self.assertEqual(p.purity_pct, 99.0)  # default
        self.assertTrue(p.available)  # default

    def test_all_precursors_have_required_fields(self):
        for name, p in ALL_PRECURSORS.items():
            self.assertIsInstance(p.name, str, f"{name} bad name")
            self.assertIsInstance(p.formula, str, f"{name} bad formula")
            self.assertIsInstance(p.cost_usd_per_kg, float, f"{name} bad cost")
            self.assertGreater(p.cost_usd_per_kg, 0.0, f"{name} cost <= 0")
            self.assertGreater(p.purity_pct, 0.0, f"{name} purity <= 0")
            self.assertLessEqual(p.purity_pct, 100.0, f"{name} purity > 100")


class TestPrecursorCount(unittest.TestCase):
    """Test we have enough precursors."""

    def test_at_least_45_precursors(self):
        self.assertGreaterEqual(len(ALL_PRECURSORS), 45)

    def test_precursor_list_matches_dict(self):
        names = list_precursors()
        self.assertEqual(len(names), len(ALL_PRECURSORS))


class TestCommonPrecursorsExist(unittest.TestCase):
    """Test that essential precursors are in the database."""

    def test_lithium_sources(self):
        self.assertIsNotNone(get_precursor("Li2CO3"))
        self.assertIsNotNone(get_precursor("LiOH"))

    def test_transition_metals(self):
        self.assertIsNotNone(get_precursor("NiSO4"))
        self.assertIsNotNone(get_precursor("MnSO4"))
        self.assertIsNotNone(get_precursor("CoSO4"))

    def test_iron_sources(self):
        self.assertIsNotNone(get_precursor("Fe2O3"))
        self.assertIsNotNone(get_precursor("FePO4"))

    def test_solvents(self):
        self.assertIsNotNone(get_precursor("NMP"))
        self.assertIsNotNone(get_precursor("DI_water"))
        self.assertIsNotNone(get_precursor("ethanol"))

    def test_polymer_precursors(self):
        self.assertIsNotNone(get_precursor("PVDF_powder"))
        self.assertIsNotNone(get_precursor("PEO_powder"))
        self.assertIsNotNone(get_precursor("CMC_powder"))

    def test_carbon_additives(self):
        self.assertIsNotNone(get_precursor("carbon_black"))
        self.assertIsNotNone(get_precursor("graphite_powder"))

    def test_metal_foils(self):
        self.assertIsNotNone(get_precursor("Cu_foil"))
        self.assertIsNotNone(get_precursor("Al_foil"))

    def test_sulfide_precursors(self):
        self.assertIsNotNone(get_precursor("Li2S"))
        self.assertIsNotNone(get_precursor("P2S5"))
        self.assertIsNotNone(get_precursor("GeS2"))


class TestLookupFunctions(unittest.TestCase):
    """Test lookup and utility functions."""

    def test_get_precursor_known(self):
        p = get_precursor("Li2CO3")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Li2CO3")

    def test_get_precursor_unknown(self):
        p = get_precursor("NONEXISTENT")
        self.assertIsNone(p)

    def test_estimate_cost(self):
        cost = estimate_route_cost(["Li2CO3", "Fe2O3"], quantity_kg=0.001)
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0.0)

    def test_estimate_cost_unknown_precursor(self):
        cost = estimate_route_cost(["UNKNOWN_MATERIAL"], quantity_kg=0.001)
        self.assertGreater(cost, 0.0)  # Uses default cost

    def test_check_availability(self):
        avail = check_availability(["Li2CO3", "NONEXISTENT"])
        self.assertTrue(avail["Li2CO3"])
        self.assertFalse(avail["NONEXISTENT"])

    def test_find_missing(self):
        missing = find_missing_precursors(["Li2CO3", "NONEXISTENT"])
        self.assertIn("NONEXISTENT", missing)
        self.assertNotIn("Li2CO3", missing)

    def test_find_hazardous(self):
        haz = find_hazardous_precursors(["NMP", "DI_water", "NiSO4"])
        self.assertIn("NMP", haz)
        self.assertEqual(haz["NMP"], "toxic")
        self.assertNotIn("DI_water", haz)  # DI water has no hazard


class TestHazardClasses(unittest.TestCase):
    """Test hazard classifications are valid."""

    VALID_HAZARDS = {"none", "irritant", "toxic", "flammable", "corrosive", "oxidizer"}

    def test_all_hazards_valid(self):
        for name, p in ALL_PRECURSORS.items():
            self.assertIn(p.hazard_class, self.VALID_HAZARDS,
                          f"{name} has invalid hazard: {p.hazard_class}")


if __name__ == '__main__':
    unittest.main()
