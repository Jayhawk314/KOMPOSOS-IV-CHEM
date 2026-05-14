# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for semiconductor interaction scoring.

Verifies all five scorers return values in [0, 1] and correctly
identify known good/bad pairings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS, get_semiconductor
from semiconductor_bridge.interaction_scoring import (
    ScorerResult,
    score_lattice_match,
    score_band_alignment,
    score_thermal_compatibility,
    score_process_compatibility,
    score_degradation_penalty,
    score_all,
)


# Representative subset for pairwise tests
_TEST_SEMICONDUCTORS = ['Si', 'Ge', 'GaAs', 'AlGaAs', 'InP', 'InGaAs',
                        'GaN', 'AlGaN', 'SiC_4H', 'ZnO', 'CdTe',
                        'MoS2', 'WS2', 'InSb', 'Bi2Te3']


class TestScorerRange(unittest.TestCase):
    """All scorers must return values in [0, 1] for all material pairs."""

    def _check_score_range(self, scorer_fn, label):
        for name_a in _TEST_SEMICONDUCTORS:
            for name_b in _TEST_SEMICONDUCTORS:
                if name_a == name_b:
                    continue
                mat_a = get_semiconductor(name_a)
                mat_b = get_semiconductor(name_b)
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

    def test_lattice_match_range(self):
        self._check_score_range(score_lattice_match, 'lattice_match')

    def test_band_alignment_range(self):
        self._check_score_range(score_band_alignment, 'band_alignment')

    def test_thermal_compat_range(self):
        self._check_score_range(score_thermal_compatibility, 'thermal_compatibility')

    def test_process_compat_range(self):
        self._check_score_range(score_process_compatibility, 'process_compatibility')

    def test_degradation_range(self):
        self._check_score_range(score_degradation_penalty, 'degradation')


class TestLatticeMatchScoring(unittest.TestCase):
    """Lattice match scorer correctness."""

    def test_gaas_algaas_excellent(self):
        """GaAs + AlGaAs: 0.04% mismatch -> near-perfect."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        result = score_lattice_match(a, b)
        self.assertGreater(result.score, 0.9, "GaAs+AlGaAs should be excellent lattice match")

    def test_ingaas_inp_excellent(self):
        """InGaAs + InP: lattice-matched at In=0.53."""
        a = get_semiconductor('InGaAs')
        b = get_semiconductor('InP')
        result = score_lattice_match(a, b)
        self.assertGreater(result.score, 0.9, "InGaAs+InP should be lattice-matched")

    def test_gan_algan_good(self):
        """GaN + AlGaN: ~0.6% mismatch."""
        a = get_semiconductor('GaN')
        b = get_semiconductor('AlGaN')
        result = score_lattice_match(a, b)
        self.assertGreater(result.score, 0.7, "GaN+AlGaN should be good lattice match")

    def test_gaas_si_poor(self):
        """GaAs + Si: 4.1% mismatch -> poor."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('Si')
        result = score_lattice_match(a, b)
        self.assertLess(result.score, 0.45, "GaAs+Si should be poor lattice match")

    def test_inas_gap_terrible(self):
        """InAs + GaP: 11.1% mismatch -> incompatible."""
        a = get_semiconductor('InAs')
        b = get_semiconductor('GaP')
        result = score_lattice_match(a, b)
        self.assertLess(result.score, 0.15, "InAs+GaP should be incompatible")

    def test_insb_si_terrible(self):
        """InSb + Si: 19.3% mismatch -> incompatible."""
        a = get_semiconductor('InSb')
        b = get_semiconductor('Si')
        result = score_lattice_match(a, b)
        self.assertLess(result.score, 0.15, "InSb+Si should be incompatible")

    def test_mos2_ws2_2d_good(self):
        """MoS2 + WS2: 2D vdW heterostructure, relaxed matching."""
        a = get_semiconductor('MoS2')
        b = get_semiconductor('WS2')
        result = score_lattice_match(a, b)
        self.assertGreater(result.score, 0.8, "MoS2+WS2 should be good vdW match")

    def test_symmetric(self):
        """Score should be the same regardless of argument order."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('Si')
        r1 = score_lattice_match(a, b)
        r2 = score_lattice_match(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=5)


class TestBandAlignmentScoring(unittest.TestCase):
    """Band alignment scorer correctness."""

    def test_gaas_algaas_good(self):
        """GaAs (1.42) + AlGaAs (1.80): moderate offset, Type I."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        result = score_band_alignment(a, b)
        self.assertGreater(result.score, 0.7, "GaAs+AlGaAs should have good band alignment")

    def test_si_ge_moderate(self):
        """Si (1.12) + Ge (0.66): moderate gap difference."""
        a = get_semiconductor('Si')
        b = get_semiconductor('Ge')
        result = score_band_alignment(a, b)
        self.assertGreater(result.score, 0.6, "Si+Ge should have reasonable alignment")

    def test_extreme_gap_difference_penalized(self):
        """Diamond (5.47) + InSb (0.17): extreme gap difference."""
        a = get_semiconductor('C_diamond')
        b = get_semiconductor('InSb')
        result = score_band_alignment(a, b)
        self.assertLess(result.score, 0.6, "C_diamond+InSb extreme gap difference")


class TestThermalCompatibility(unittest.TestCase):
    """Thermal compatibility scorer correctness."""

    def test_gaas_algaas_good(self):
        """GaAs + AlGaAs: similar CTE and thermal properties."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        result = score_thermal_compatibility(a, b)
        self.assertGreater(result.score, 0.8, "GaAs+AlGaAs should have good thermal compat")

    def test_large_thermal_cond_mismatch(self):
        """Diamond (2200 W/mK) + HgCdTe (2 W/mK): extreme ratio."""
        a = get_semiconductor('C_diamond')
        b = get_semiconductor('HgCdTe')
        result = score_thermal_compatibility(a, b)
        self.assertLess(result.score, 0.7, "Diamond+HgCdTe extreme thermal mismatch")


class TestProcessCompatibility(unittest.TestCase):
    """Process compatibility scorer correctness."""

    def test_gaas_algaas_compatible(self):
        """GaAs + AlGaAs: same MBE/MOCVD growth conditions."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        result = score_process_compatibility(a, b)
        self.assertGreater(result.score, 0.8, "GaAs+AlGaAs known compatible process")

    def test_same_class_bonus(self):
        """Two III-Vs should get class match bonus."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('InP')
        result = score_process_compatibility(a, b)
        self.assertIn('class_match', result.details)
        self.assertTrue(result.details['class_match'])

    def test_gaas_si_difficult(self):
        """GaAs + Si: polar-on-nonpolar growth problem."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('Si')
        result = score_process_compatibility(a, b)
        self.assertLess(result.score, 0.5, "GaAs+Si known difficult process")

    def test_gan_gaas_difficult(self):
        """GaN + GaAs: different crystal structure, extreme mismatch."""
        a = get_semiconductor('GaN')
        b = get_semiconductor('GaAs')
        result = score_process_compatibility(a, b)
        self.assertLess(result.score, 0.5, "GaN+GaAs should be difficult process")


class TestDegradationPenalty(unittest.TestCase):
    """Degradation penalty scorer correctness."""

    def test_gaas_si_penalty(self):
        """GaAs + Si: known bad pairing."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('Si')
        result = score_degradation_penalty(a, b)
        self.assertLess(result.score, 0.8, "GaAs+Si known bad pairing")

    def test_moisture_sensitivity_penalty(self):
        """AlAs is moisture-sensitive; should get penalty."""
        a = get_semiconductor('AlAs')
        b = get_semiconductor('GaAs')
        result = score_degradation_penalty(a, b)
        self.assertLess(result.score, 0.9, "AlAs moisture sensitivity")

    def test_no_penalty_for_matched(self):
        """GaAs + AlGaAs: standard system, no degradation issues."""
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        result = score_degradation_penalty(a, b)
        self.assertGreater(result.score, 0.7, "GaAs+AlGaAs should have no major penalty")


class TestScoreAll(unittest.TestCase):
    """Test composite scorer."""

    def test_score_all_returns_five_scores(self):
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        results = score_all(a, b)
        self.assertEqual(len(results), 5)
        expected_keys = {'lattice_match', 'band_alignment',
                         'thermal_compatibility', 'process_compatibility',
                         'degradation_penalty'}
        self.assertEqual(set(results.keys()), expected_keys)

    def test_score_all_values_in_range(self):
        a = get_semiconductor('GaAs')
        b = get_semiconductor('AlGaAs')
        results = score_all(a, b)
        for name, result in results.items():
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
