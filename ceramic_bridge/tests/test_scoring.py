# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for ceramic interaction scoring.

Verifies all five scorers return values in [0, 1] and correctly
identify known good/bad pairings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from ceramic_bridge.material_properties import ALL_CERAMICS, get_ceramic
from ceramic_bridge.interaction_scoring import (
    ScorerResult,
    score_sintering_compatibility,
    score_cte_match,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    score_all,
)


# Representative subset for pairwise tests
_TEST_CERAMICS = ['Al2O3', 'ZrO2_YSZ', 'SiC', 'Si3N4', 'AlN', 'WC',
                  'Borosilicate', 'SiO2', 'MgO', 'Hydroxyapatite',
                  'PZT', 'LLZO', 'LGPS', 'BN_hex', 'TiN']


class TestScorerRange(unittest.TestCase):
    """All scorers must return values in [0, 1] for all material pairs."""

    def _check_score_range(self, scorer_fn, label):
        for name_a in _TEST_CERAMICS:
            for name_b in _TEST_CERAMICS:
                if name_a == name_b:
                    continue
                mat_a = get_ceramic(name_a)
                mat_b = get_ceramic(name_b)
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

    def test_sintering_range(self):
        self._check_score_range(score_sintering_compatibility, 'sintering')

    def test_cte_range(self):
        self._check_score_range(score_cte_match, 'cte')

    def test_mechanical_range(self):
        self._check_score_range(score_mechanical_compatibility, 'mechanical')

    def test_chemical_range(self):
        self._check_score_range(score_chemical_compatibility, 'chemical')

    def test_degradation_range(self):
        self._check_score_range(score_degradation_penalty, 'degradation')


class TestSinteringScoring(unittest.TestCase):
    """Sintering compatibility scorer correctness."""

    def test_al2o3_zro2_compatible(self):
        """Al2O3 (1600C) + ZrO2_YSZ (1450C): close sintering temps."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('ZrO2_YSZ')
        result = score_sintering_compatibility(a, b)
        self.assertGreater(result.score, 0.7, "Al2O3+ZrO2 should sinter compatibly")

    def test_sic_si3n4_decomposition_flag(self):
        """SiC (2100C) + Si3N4 (1750C): SiC sinter temp > Si3N4 decomp temp."""
        a = get_ceramic('SiC')
        b = get_ceramic('Si3N4')
        result = score_sintering_compatibility(a, b)
        # Si3N4 decomposes at ~1900C, SiC sinters at 2100C -> decomposition conflict
        # In practice these composites use lower-temp sintering aids
        self.assertLess(result.score, 0.5, "SiC+Si3N4 should flag sintering conflict")

    def test_bioglass_sic_incompatible(self):
        """Bioglass (1050C melt) + SiC (2100C sinter): extreme gap."""
        a = get_ceramic('Bioglass')
        b = get_ceramic('SiC')
        result = score_sintering_compatibility(a, b)
        self.assertLess(result.score, 0.3, "Bioglass+SiC extreme sintering mismatch")

    def test_similar_sintering_temps_high(self):
        """Hydroxyapatite (1250C) + TCP (1100C): close temps."""
        a = get_ceramic('Hydroxyapatite')
        b = get_ceramic('TCP')
        result = score_sintering_compatibility(a, b)
        self.assertGreater(result.score, 0.7, "HA+TCP close sintering temps")


class TestCTEScoring(unittest.TestCase):
    """CTE match scorer correctness."""

    def test_al2o3_zro2_good_match(self):
        """Al2O3 (8.1) + ZrO2_YSZ (10.5): close CTE."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('ZrO2_YSZ')
        result = score_cte_match(a, b)
        self.assertGreater(result.score, 0.7, "Al2O3+ZrO2 should have good CTE match")

    def test_sio2_mgo_extreme_mismatch(self):
        """SiO2 (0.55) + MgO (13.5): extreme CTE mismatch."""
        a = get_ceramic('SiO2')
        b = get_ceramic('MgO')
        result = score_cte_match(a, b)
        self.assertLess(result.score, 0.2, "SiO2+MgO extreme CTE mismatch")

    def test_sic_si3n4_close(self):
        """SiC (4.0) + Si3N4 (3.2): very close CTE."""
        a = get_ceramic('SiC')
        b = get_ceramic('Si3N4')
        result = score_cte_match(a, b)
        self.assertGreater(result.score, 0.9, "SiC+Si3N4 very close CTE")

    def test_symmetric(self):
        """Score should be the same regardless of argument order."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('SiC')
        r1 = score_cte_match(a, b)
        r2 = score_cte_match(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=5)


class TestMechanicalScoring(unittest.TestCase):
    """Mechanical compatibility scorer correctness."""

    def test_similar_modulus_good(self):
        """Al2O3 (380) + Si3N4 (310): similar modulus."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('Si3N4')
        result = score_mechanical_compatibility(a, b)
        self.assertGreater(result.score, 0.7)

    def test_extreme_modulus_mismatch(self):
        """BN (30 GPa) + WC (700 GPa): extreme mismatch (ratio ~23x)."""
        bn = get_ceramic('BN_hex')
        wc = get_ceramic('WC')
        result = score_mechanical_compatibility(bn, wc)
        self.assertLess(result.score, 0.4, "BN+WC extreme modulus mismatch")

    def test_lgps_al2o3_mismatch(self):
        """LGPS (20 GPa) + Al2O3 (380 GPa): extreme mismatch."""
        a = get_ceramic('LGPS')
        b = get_ceramic('Al2O3')
        result = score_mechanical_compatibility(a, b)
        self.assertLess(result.score, 0.4, "LGPS+Al2O3 extreme modulus mismatch")


class TestChemicalScoring(unittest.TestCase):
    """Chemical compatibility scorer correctness."""

    def test_al2o3_zro2_compatible(self):
        """Al2O3 + ZrO2: known compatible composite."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('ZrO2_YSZ')
        result = score_chemical_compatibility(a, b)
        self.assertGreater(result.score, 0.7, "Al2O3+ZrO2 known compatible")

    def test_same_class_bonus(self):
        """Two oxides should get class match bonus."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('MgO')
        result = score_chemical_compatibility(a, b)
        self.assertIn('class_match', result.details)
        self.assertTrue(result.details['class_match'])

    def test_reactive_pair_penalty(self):
        """SiO2 + MgO: known to form forsterite."""
        a = get_ceramic('SiO2')
        b = get_ceramic('MgO')
        result = score_chemical_compatibility(a, b)
        self.assertLess(result.score, 0.5, "SiO2+MgO reactive pair")


class TestDegradationPenalty(unittest.TestCase):
    """Degradation penalty scorer correctness."""

    def test_lgps_al2o3_bad(self):
        """LGPS + Al2O3: known bad pairing."""
        a = get_ceramic('LGPS')
        b = get_ceramic('Al2O3')
        result = score_degradation_penalty(a, b)
        self.assertLess(result.score, 0.5, "LGPS+Al2O3 known bad pair")

    def test_hygroscopic_penalty(self):
        """MgO is hygroscopic; should get penalty."""
        a = get_ceramic('MgO')
        b = get_ceramic('Al2O3')
        result = score_degradation_penalty(a, b)
        self.assertLess(result.score, 0.85, "Hygroscopic MgO should get penalty")

    def test_no_penalty_for_inert(self):
        """Al2O3 + SiC: both stable, no degradation issues."""
        a = get_ceramic('Al2O3')
        b = get_ceramic('SiC')
        result = score_degradation_penalty(a, b)
        self.assertGreater(result.score, 0.8, "Stable ceramics should have no penalty")

    def test_both_reactive_penalty(self):
        """LGPS + Li3PS4: both reactive (both sulfide SEs)."""
        a = get_ceramic('LGPS')
        b = get_ceramic('Li3PS4')
        result = score_degradation_penalty(a, b)
        self.assertLess(result.score, 0.8, "Both reactive should get penalty")


class TestScoreAll(unittest.TestCase):
    """Test composite scorer."""

    def test_score_all_returns_five_scores(self):
        a = get_ceramic('Al2O3')
        b = get_ceramic('ZrO2_YSZ')
        results = score_all(a, b)
        self.assertEqual(len(results), 5)
        expected_keys = {'sintering_compatibility', 'cte_match',
                         'mechanical_compatibility', 'chemical_compatibility',
                         'degradation_penalty'}
        self.assertEqual(set(results.keys()), expected_keys)

    def test_score_all_values_in_range(self):
        a = get_ceramic('Al2O3')
        b = get_ceramic('ZrO2_YSZ')
        results = score_all(a, b)
        for name, result in results.items():
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
