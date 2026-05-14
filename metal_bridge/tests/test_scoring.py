# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for metal interaction scoring.

Verifies all five scorers return values in [0, 1] and correctly
identify known good/bad pairings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from metal_bridge.material_properties import ALL_METALS, get_metal
from metal_bridge.interaction_scoring import (
    ScorerResult,
    score_galvanic_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_metallurgical_compatibility,
    score_corrosion_penalty,
    score_all,
)


# Representative subset for pairwise tests
_TEST_METALS = ['Fe', 'Al', 'Cu', 'Ti', 'Ni', 'Zn', 'Mg', 'W', 'Au',
                'SS_304', 'SS_316', 'Steel_1018', 'Al_6061', 'Al_7075',
                'Ti6Al4V', 'Inconel_625', 'Brass_C260']


class TestScorerRange(unittest.TestCase):
    """All scorers must return values in [0, 1] for all material pairs."""

    def _check_score_range(self, scorer_fn, label):
        for name_a in _TEST_METALS:
            for name_b in _TEST_METALS:
                if name_a == name_b:
                    continue
                mat_a = get_metal(name_a)
                mat_b = get_metal(name_b)
                if mat_a is None or mat_b is None:
                    continue
                result = scorer_fn(mat_a, mat_b)
                with self.subTest(pair=f"{name_a}-{name_b}", scorer=label):
                    self.assertGreaterEqual(result.score, 0.0,
                        f"{label}({name_a},{name_b})={result.score} < 0")
                    self.assertLessEqual(result.score, 1.0,
                        f"{label}({name_a},{name_b})={result.score} > 1")
                    self.assertIsInstance(result.label, str)
                    self.assertIsInstance(result.details, dict)

    def test_galvanic_range(self):
        self._check_score_range(score_galvanic_compatibility, 'galvanic')

    def test_thermal_range(self):
        self._check_score_range(score_thermal_compatibility, 'thermal')

    def test_mechanical_range(self):
        self._check_score_range(score_mechanical_compatibility, 'mechanical')

    def test_metallurgical_range(self):
        self._check_score_range(score_metallurgical_compatibility, 'metallurgical')

    def test_corrosion_range(self):
        self._check_score_range(score_corrosion_penalty, 'corrosion')


class TestGalvanicScoring(unittest.TestCase):
    """Galvanic compatibility scorer correctness."""

    def test_ss304_ss316_compatible(self):
        """304SS + 316SS: nearly identical potential."""
        a = get_metal('SS_304')
        b = get_metal('SS_316')
        result = score_galvanic_compatibility(a, b)
        self.assertGreater(result.score, 0.8, "304SS+316SS should score high (same family)")

    def test_cu_al_incompatible(self):
        """Cu + Al: large potential difference."""
        cu = get_metal('Cu')
        al = get_metal('Al')
        result = score_galvanic_compatibility(cu, al)
        self.assertLess(result.score, 0.4, "Cu+Al should score low (galvanic couple)")

    def test_mg_cu_very_bad(self):
        """Mg + Cu: extreme potential difference."""
        mg = get_metal('Mg')
        cu = get_metal('Cu')
        result = score_galvanic_compatibility(mg, cu)
        self.assertLess(result.score, 0.2, "Mg+Cu should score very low")

    def test_ti_ss316_compatible(self):
        """Ti6Al4V + 316SS: both passive, close potentials."""
        ti = get_metal('Ti6Al4V')
        ss = get_metal('SS_316')
        result = score_galvanic_compatibility(ti, ss)
        self.assertGreater(result.score, 0.8, "Ti+316SS should be galvanically compatible")

    def test_symmetric(self):
        """Score should be the same regardless of argument order."""
        cu = get_metal('Cu')
        al = get_metal('Al')
        r1 = score_galvanic_compatibility(cu, al)
        r2 = score_galvanic_compatibility(al, cu)
        self.assertAlmostEqual(r1.score, r2.score, places=5)


class TestThermalScoring(unittest.TestCase):
    """Thermal compatibility scorer correctness."""

    def test_similar_cte_good(self):
        """304SS (17.3) + Ni (13.4): similar CTE."""
        ss = get_metal('SS_304')
        ni = get_metal('Ni')
        result = score_thermal_compatibility(ss, ni)
        self.assertGreater(result.score, 0.7)

    def test_extreme_cte_mismatch(self):
        """W (4.5) + Al (23.1): extreme CTE mismatch (ratio ~5.1x)."""
        w = get_metal('W')
        al = get_metal('Al')
        result = score_thermal_compatibility(w, al)
        self.assertLess(result.score, 0.5, "W+Al extreme CTE mismatch should penalize")

    def test_ti_al_cte_mismatch(self):
        """Ti (8.6) + Al (23.1): CTE ratio ~2.7x."""
        ti = get_metal('Ti')
        al = get_metal('Al')
        result = score_thermal_compatibility(ti, al)
        self.assertLess(result.score, 0.8, "Ti+Al CTE mismatch should penalize")


class TestMechanicalScoring(unittest.TestCase):
    """Mechanical compatibility scorer correctness."""

    def test_similar_modulus_good(self):
        """SS_304 (193 GPa) + SS_316 (193 GPa): identical modulus."""
        a = get_metal('SS_304')
        b = get_metal('SS_316')
        result = score_mechanical_compatibility(a, b)
        self.assertGreater(result.score, 0.8)

    def test_extreme_modulus_mismatch(self):
        """Pb (16 GPa) + W (411 GPa): extreme mismatch (ratio ~25x)."""
        pb = get_metal('Pb')
        w = get_metal('W')
        result = score_mechanical_compatibility(pb, w)
        self.assertLess(result.score, 0.5, "Pb+W extreme modulus mismatch")

    def test_strength_mismatch(self):
        """Pb (8 MPa yield) + Maraging_300 (2000 MPa): extreme."""
        pb = get_metal('Pb')
        mar = get_metal('Maraging_300')
        result = score_mechanical_compatibility(pb, mar)
        self.assertLess(result.score, 0.5, "Extreme strength mismatch should penalize")


class TestMetallurgicalScoring(unittest.TestCase):
    """Metallurgical compatibility scorer correctness."""

    def test_cu_ni_solid_solution(self):
        """Cu + Ni: known complete solid solution."""
        cu = get_metal('Cu')
        ni = get_metal('Ni')
        result = score_metallurgical_compatibility(cu, ni)
        self.assertGreater(result.score, 0.8, "Cu+Ni solid solution should score high")

    def test_same_class_bonus(self):
        """SS_304 + SS_316: same metal class."""
        a = get_metal('SS_304')
        b = get_metal('SS_316')
        result = score_metallurgical_compatibility(a, b)
        self.assertGreater(result.score, 0.8, "Same class should score high")

    def test_fe_al_intermetallics(self):
        """Fe + Al: known to form brittle intermetallics."""
        fe = get_metal('Fe')
        al = get_metal('Al')
        result = score_metallurgical_compatibility(fe, al)
        self.assertLess(result.score, 0.5, "Fe+Al intermetallics should penalize")


class TestCorrosionPenalty(unittest.TestCase):
    """Corrosion penalty scorer correctness."""

    def test_cu_al_known_bad(self):
        """Cu + Al is a known bad galvanic pair."""
        cu = get_metal('Cu')
        al = get_metal('Al')
        result = score_corrosion_penalty(cu, al)
        self.assertLess(result.score, 0.5, "Cu+Al known bad pair")

    def test_mg_cu_known_bad(self):
        """Mg + Cu is a known extreme galvanic pair."""
        mg = get_metal('Mg')
        cu = get_metal('Cu')
        result = score_corrosion_penalty(mg, cu)
        self.assertLess(result.score, 0.3, "Mg+Cu extreme galvanic pair")

    def test_no_penalty_for_noble(self):
        """Au + Pt: both noble, no corrosion issues."""
        au = get_metal('Au')
        pt = get_metal('Pt')
        result = score_corrosion_penalty(au, pt)
        self.assertGreater(result.score, 0.8, "Noble metals should have no corrosion penalty")

    def test_high_corrosion_rate_penalty(self):
        """Steel_1018 has high corrosion rate."""
        steel = get_metal('Steel_1018')
        al = get_metal('Al')
        result = score_corrosion_penalty(steel, al)
        self.assertLess(result.score, 0.7, "High corrosion rate should penalize")


class TestScoreAll(unittest.TestCase):
    """Test composite scorer."""

    def test_score_all_returns_five_scores(self):
        a = get_metal('SS_304')
        b = get_metal('SS_316')
        results = score_all(a, b)
        self.assertEqual(len(results), 5)
        expected_keys = {'galvanic_compatibility', 'thermal_compatibility',
                         'mechanical_compatibility', 'metallurgical_compatibility',
                         'corrosion_penalty'}
        self.assertEqual(set(results.keys()), expected_keys)

    def test_score_all_values_in_range(self):
        a = get_metal('SS_304')
        b = get_metal('SS_316')
        results = score_all(a, b)
        for name, result in results.items():
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
