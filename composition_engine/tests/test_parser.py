# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for composition_engine.parser"""

import unittest
import numpy as np

from composition_engine.parser import (
    parse_formula, composition_vector, composition_distance,
    molar_mass, average_electronegativity, metal_fraction,
    SHORTHAND_MAP, ELEMENT_TABLE, ELEMENT_ORDER,
)


class TestParseFormula(unittest.TestCase):
    """Tests for chemical formula parsing."""

    def test_simple_oxide(self):
        comp = parse_formula("LiCoO2")
        self.assertAlmostEqual(comp["Li"], 1.0)
        self.assertAlmostEqual(comp["Co"], 1.0)
        self.assertAlmostEqual(comp["O"], 2.0)

    def test_decimal_stoichiometry(self):
        comp = parse_formula("LiNi0.8Mn0.1Co0.1O2")
        self.assertAlmostEqual(comp["Li"], 1.0)
        self.assertAlmostEqual(comp["Ni"], 0.8)
        self.assertAlmostEqual(comp["Mn"], 0.1)
        self.assertAlmostEqual(comp["Co"], 0.1)
        self.assertAlmostEqual(comp["O"], 2.0)

    def test_fraction_stoichiometry(self):
        comp = parse_formula("LiNi1/3Mn1/3Co1/3O2")
        self.assertAlmostEqual(comp["Ni"], 1/3, places=3)
        self.assertAlmostEqual(comp["Mn"], 1/3, places=3)
        self.assertAlmostEqual(comp["Co"], 1/3, places=3)

    def test_large_coefficients(self):
        comp = parse_formula("Li7La3Zr2O12")
        self.assertAlmostEqual(comp["Li"], 7.0)
        self.assertAlmostEqual(comp["La"], 3.0)
        self.assertAlmostEqual(comp["Zr"], 2.0)
        self.assertAlmostEqual(comp["O"], 12.0)

    def test_olivine(self):
        comp = parse_formula("LiFePO4")
        self.assertAlmostEqual(comp["Li"], 1.0)
        self.assertAlmostEqual(comp["Fe"], 1.0)
        self.assertAlmostEqual(comp["P"], 1.0)
        self.assertAlmostEqual(comp["O"], 4.0)

    def test_spinel(self):
        comp = parse_formula("LiMn2O4")
        self.assertAlmostEqual(comp["Mn"], 2.0)
        self.assertAlmostEqual(comp["O"], 4.0)

    def test_shorthand_nmc811(self):
        comp = parse_formula("NMC811")
        self.assertAlmostEqual(comp["Ni"], 0.8)
        self.assertAlmostEqual(comp["Mn"], 0.1)
        self.assertAlmostEqual(comp["Co"], 0.1)

    def test_shorthand_lfp(self):
        comp = parse_formula("LFP")
        self.assertIn("Fe", comp)
        self.assertIn("P", comp)

    def test_shorthand_lco(self):
        comp = parse_formula("LCO")
        self.assertAlmostEqual(comp["Co"], 1.0)

    def test_all_shorthands_parse(self):
        """Every shorthand should produce a non-empty composition."""
        for short, full in SHORTHAND_MAP.items():
            comp = parse_formula(short)
            self.assertTrue(len(comp) > 0, f"Shorthand {short} -> empty")

    def test_single_element(self):
        comp = parse_formula("Li")
        self.assertAlmostEqual(comp["Li"], 1.0)

    def test_graphite(self):
        comp = parse_formula("C6")
        self.assertAlmostEqual(comp["C"], 6.0)

    def test_lgps(self):
        comp = parse_formula("Li10GeP2S12")
        self.assertAlmostEqual(comp["Li"], 10.0)
        self.assertAlmostEqual(comp["Ge"], 1.0)
        self.assertAlmostEqual(comp["P"], 2.0)
        self.assertAlmostEqual(comp["S"], 12.0)


class TestCompositionVector(unittest.TestCase):
    """Tests for composition vector generation."""

    def test_vector_length(self):
        comp = parse_formula("LiCoO2")
        vec = composition_vector(comp)
        self.assertEqual(len(vec), len(ELEMENT_ORDER))

    def test_vector_values(self):
        comp = parse_formula("LiCoO2")
        vec = composition_vector(comp)
        li_idx = ELEMENT_ORDER.index("Li")
        co_idx = ELEMENT_ORDER.index("Co")
        o_idx = ELEMENT_ORDER.index("O")
        self.assertAlmostEqual(vec[li_idx], 1.0)
        self.assertAlmostEqual(vec[co_idx], 1.0)
        self.assertAlmostEqual(vec[o_idx], 2.0)

    def test_zero_elements(self):
        """Elements not in formula should be zero."""
        comp = parse_formula("LiCoO2")
        vec = composition_vector(comp)
        fe_idx = ELEMENT_ORDER.index("Fe")
        self.assertAlmostEqual(vec[fe_idx], 0.0)


class TestCompositionDistance(unittest.TestCase):
    """Tests for distance in composition space."""

    def test_self_distance_zero(self):
        comp = parse_formula("LiCoO2")
        self.assertAlmostEqual(composition_distance(comp, comp), 0.0)

    def test_symmetric(self):
        a = parse_formula("LiCoO2")
        b = parse_formula("LiNi0.8Mn0.1Co0.1O2")
        self.assertAlmostEqual(
            composition_distance(a, b),
            composition_distance(b, a),
        )

    def test_nmc_family_closer_than_lfp(self):
        """NMC811 should be closer to NMC622 than to LFP."""
        nmc811 = parse_formula("NMC811")
        nmc622 = parse_formula("NMC622")
        lfp = parse_formula("LFP")

        d_nmc = composition_distance(nmc811, nmc622)
        d_lfp = composition_distance(nmc811, lfp)
        self.assertLess(d_nmc, d_lfp)

    def test_triangle_inequality(self):
        a = parse_formula("LiCoO2")
        b = parse_formula("NMC811")
        c = parse_formula("LFP")
        d_ab = composition_distance(a, b)
        d_bc = composition_distance(b, c)
        d_ac = composition_distance(a, c)
        self.assertLessEqual(d_ac, d_ab + d_bc + 1e-9)

    def test_positive(self):
        a = parse_formula("LiCoO2")
        b = parse_formula("LiFePO4")
        self.assertGreater(composition_distance(a, b), 0.0)


class TestMolarMass(unittest.TestCase):

    def test_lico2(self):
        comp = parse_formula("LiCoO2")
        mm = molar_mass(comp)
        # Li=6.941, Co=58.933, 2*O=31.998 -> ~97.87
        self.assertAlmostEqual(mm, 97.872, places=0)

    def test_lifepo4(self):
        comp = parse_formula("LiFePO4")
        mm = molar_mass(comp)
        # Li=6.941, Fe=55.845, P=30.974, 4*O=63.996 -> ~157.76
        self.assertAlmostEqual(mm, 157.756, places=0)


class TestElectronegativity(unittest.TestCase):

    def test_positive(self):
        comp = parse_formula("LiCoO2")
        en = average_electronegativity(comp)
        self.assertGreater(en, 0.0)

    def test_higher_for_fluoride(self):
        """F has higher EN than O, so LiF should have higher avg EN than LiO."""
        en_lif = average_electronegativity({"Li": 1, "F": 1})
        en_lio = average_electronegativity({"Li": 1, "O": 1})
        self.assertGreater(en_lif, en_lio)


class TestMetalFraction(unittest.TestCase):

    def test_nmc811(self):
        comp = parse_formula("NMC811")
        fracs = metal_fraction(comp)
        self.assertAlmostEqual(fracs["Ni"], 0.8, places=2)
        self.assertAlmostEqual(fracs["Mn"], 0.1, places=2)
        self.assertAlmostEqual(fracs["Co"], 0.1, places=2)

    def test_sums_to_one(self):
        comp = parse_formula("NMC622")
        fracs = metal_fraction(comp)
        self.assertAlmostEqual(sum(fracs.values()), 1.0, places=5)


class TestElementTable(unittest.TestCase):

    def test_common_elements_present(self):
        for elem in ["Li", "C", "N", "O", "Fe", "Co", "Ni", "Mn", "Al", "Si"]:
            self.assertIn(elem, ELEMENT_TABLE)

    def test_atomic_mass_positive(self):
        for elem, data in ELEMENT_TABLE.items():
            self.assertGreater(data.atomic_mass, 0.0, f"{elem} mass <= 0")

    def test_element_order_sorted_by_z(self):
        for i in range(len(ELEMENT_ORDER) - 1):
            z_a = ELEMENT_TABLE[ELEMENT_ORDER[i]].atomic_number
            z_b = ELEMENT_TABLE[ELEMENT_ORDER[i + 1]].atomic_number
            self.assertLess(z_a, z_b)


if __name__ == "__main__":
    unittest.main()
