# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for polymer interaction scoring.

Verifies all five scorers return values in [0, 1] and correctly
identify known good/bad pairings.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from polymer_bridge.material_properties import (
    ALL_POLYMERS, get_polymer, KNOWN_GOOD_BLENDS, KNOWN_BAD_BLENDS,
)
from polymer_bridge.interaction_scoring import (
    ScorerResult,
    score_solubility_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_chemical_resistance,
    score_aging_penalty,
    score_all,
)
from polymer_bridge.flory_huggins import assess_flory_huggins, critical_chi


# Select representative subset for pairwise tests
_TEST_POLYMERS = ['HDPE', 'PP', 'PS', 'PMMA', 'PET', 'PC', 'PVDF', 'PEO',
                  'PTFE', 'SBR', 'PDMS', 'Epoxy', 'PI', 'NMP', 'Water']


class TestScorerRange(unittest.TestCase):
    """All scorers must return values in [0, 1] for all material pairs."""

    def _check_score_range(self, scorer_fn, label):
        for name_a in _TEST_POLYMERS:
            for name_b in _TEST_POLYMERS:
                if name_a == name_b:
                    continue
                mat_a = get_polymer(name_a)
                mat_b = get_polymer(name_b)
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

    def test_solubility_range(self):
        self._check_score_range(score_solubility_compatibility, 'solubility')

    def test_thermal_range(self):
        self._check_score_range(score_thermal_compatibility, 'thermal')

    def test_mechanical_range(self):
        self._check_score_range(score_mechanical_compatibility, 'mechanical')

    def test_chemical_resistance_range(self):
        self._check_score_range(score_chemical_resistance, 'chemical')

    def test_aging_range(self):
        self._check_score_range(score_aging_penalty, 'aging')


class TestSolubilityScoring(unittest.TestCase):
    """Solubility scorer correctness."""

    def test_pvdf_pmma_miscible(self):
        """PVDF + PMMA: known miscible blend (negative chi)."""
        pvdf = get_polymer('PVDF')
        pmma = get_polymer('PMMA')
        result = score_solubility_compatibility(pvdf, pmma)
        self.assertGreater(result.score, 0.8, "PVDF+PMMA should score high (miscible)")

    def test_hdpe_pa6_immiscible(self):
        """HDPE + PA6: known immiscible (chi ~2.0)."""
        hdpe = get_polymer('HDPE')
        pa6 = get_polymer('PA6')
        result = score_solubility_compatibility(hdpe, pa6)
        self.assertLess(result.score, 0.3, "HDPE+PA6 should score low (immiscible)")

    def test_peo_pmma_miscible(self):
        """PEO + PMMA: known miscible (negative chi)."""
        peo = get_polymer('PEO')
        pmma = get_polymer('PMMA')
        result = score_solubility_compatibility(peo, pmma)
        self.assertGreater(result.score, 0.8, "PEO+PMMA should score high (miscible)")

    def test_hdpe_pp_chic_immiscible(self):
        """HDPE + PP: low chi still exceeds high-MW critical chi."""
        hdpe = get_polymer('HDPE')
        pp = get_polymer('PP')
        result = score_solubility_compatibility(hdpe, pp)
        self.assertLess(result.score, 0.4, "HDPE+PP should score low once chi_c is applied")
        self.assertEqual(result.details.get('flory_huggins_reason'), 'chi_above_critical')

    def test_ps_ppo_empirical_override(self):
        """PS + PPO: known favorable interaction should override HSP-only rejection."""
        ps = get_polymer('PS')
        ppo = get_polymer('PPO')
        result = score_solubility_compatibility(ps, ppo)
        self.assertGreater(result.score, 0.8, "PS+PPO should score high from empirical chi")
        self.assertEqual(result.details.get('flory_huggins_reason'), 'negative_empirical_chi')

    def test_pc_abs_empirical_compatibility_override(self):
        """PC + ABS should not be rejected by a pure HSP chi estimate."""
        pc = get_polymer('PC')
        abs_polymer = get_polymer('ABS')
        result = score_solubility_compatibility(pc, abs_polymer)
        self.assertGreater(result.score, 0.7)
        self.assertEqual(result.details.get('chi_source'), 'empirical_compatibility_override')

    def test_water_hdpe_incompatible(self):
        """Water + HDPE: extreme polarity mismatch."""
        water = get_polymer('Water')
        hdpe = get_polymer('HDPE')
        result = score_solubility_compatibility(water, hdpe)
        self.assertLess(result.score, 0.2, "Water+HDPE should score very low")

    def test_ps_toluene_compatible(self):
        """PS dissolves readily in toluene."""
        ps = get_polymer('PS')
        tol = get_polymer('Toluene')
        result = score_solubility_compatibility(ps, tol)
        self.assertGreater(result.score, 0.7, "PS+Toluene should score well")

    def test_symmetric(self):
        """Score should be the same regardless of argument order."""
        pvdf = get_polymer('PVDF')
        pmma = get_polymer('PMMA')
        r1 = score_solubility_compatibility(pvdf, pmma)
        r2 = score_solubility_compatibility(pmma, pvdf)
        self.assertAlmostEqual(r1.score, r2.score, places=5)


class TestFloryHugginsCriticalChi(unittest.TestCase):
    """Chain-length-aware Flory-Huggins logic."""

    def test_critical_chi_is_small_for_high_mw_polymers(self):
        hdpe = get_polymer('HDPE')
        pp = get_polymer('PP')
        chi_c = critical_chi(hdpe, pp)
        self.assertIsNotNone(chi_c)
        self.assertLess(chi_c, 0.005)

    def test_hdpe_pp_chi_exceeds_critical(self):
        assessment = assess_flory_huggins(get_polymer('HDPE'), get_polymer('PP'))
        self.assertFalse(assessment.miscible)
        self.assertEqual(assessment.reason, 'chi_above_critical')
        self.assertGreater(assessment.chi, assessment.critical_chi)

    def test_ps_ppo_negative_chi_override(self):
        assessment = assess_flory_huggins(get_polymer('PS'), get_polymer('PPO'))
        self.assertTrue(assessment.miscible)
        self.assertLess(assessment.chi, 0.0)
        self.assertEqual(assessment.reason, 'negative_empirical_chi')

    def test_ptfe_peek_empirical_interface_override(self):
        assessment = assess_flory_huggins(get_polymer('PTFE'), get_polymer('PEEK'))
        self.assertTrue(assessment.miscible)
        self.assertEqual(assessment.chi_source, 'empirical_compatibility_override')


class TestThermalScoring(unittest.TestCase):
    """Thermal compatibility scorer correctness."""

    def test_similar_tg_good(self):
        """PS (Tg=100) + PMMA (Tg=105): similar Tg = good."""
        ps = get_polymer('PS')
        pmma = get_polymer('PMMA')
        result = score_thermal_compatibility(ps, pmma)
        self.assertGreater(result.score, 0.7)

    def test_extreme_tg_mismatch(self):
        """PDMS (Tg=-125) + PI (Tg=360): extreme mismatch."""
        pdms = get_polymer('PDMS')
        pi = get_polymer('PI')
        result = score_thermal_compatibility(pdms, pi)
        self.assertLess(result.score, 0.6, "Extreme Tg mismatch should penalize")

    def test_both_thermosets_penalty(self):
        """Two crosslinked polymers can't be melt-blended."""
        epoxy = get_polymer('Epoxy')
        phenolic = get_polymer('Phenolic')
        result = score_thermal_compatibility(epoxy, phenolic)
        self.assertLess(result.score, 0.4, "Both crosslinked should penalize heavily")


class TestMechanicalScoring(unittest.TestCase):
    """Mechanical compatibility scorer correctness."""

    def test_similar_modulus_good(self):
        """PS (3.0 GPa) + PMMA (3.3 GPa): similar modulus = good."""
        ps = get_polymer('PS')
        pmma = get_polymer('PMMA')
        result = score_mechanical_compatibility(ps, pmma)
        self.assertGreater(result.score, 0.7)

    def test_extreme_modulus_mismatch(self):
        """PDMS (0.001 GPa) + PEEK (3.6 GPa): extreme mismatch."""
        pdms = get_polymer('PDMS')
        peek = get_polymer('PEEK')
        result = score_mechanical_compatibility(pdms, peek)
        self.assertLess(result.score, 0.5, "Extreme modulus mismatch should penalize")


class TestChemicalResistance(unittest.TestCase):
    """Chemical resistance scorer correctness."""

    def test_both_hydrophobic_good(self):
        """HDPE + PP: both hydrophobic, low water absorption."""
        hdpe = get_polymer('HDPE')
        pp = get_polymer('PP')
        result = score_chemical_resistance(hdpe, pp)
        self.assertGreater(result.score, 0.8)

    def test_hygroscopic_penalty(self):
        """PA6 (9.5% water abs) + PEO (water-soluble): moisture risk."""
        pa6 = get_polymer('PA6')
        peo = get_polymer('PEO')
        result = score_chemical_resistance(pa6, peo)
        self.assertLessEqual(result.score, 0.4, "Highly hygroscopic pair should penalize")


class TestAgingPenalty(unittest.TestCase):
    """Aging/degradation penalty scorer correctness."""

    def test_hdpe_pa6_known_bad(self):
        """HDPE + PA6 is in the known bad pairings."""
        hdpe = get_polymer('HDPE')
        pa6 = get_polymer('PA6')
        result = score_aging_penalty(hdpe, pa6)
        self.assertLess(result.score, 0.7, "Known bad blend should penalize")

    def test_no_penalty_for_compatible(self):
        """PS + PMMA: no known bad pairing."""
        ps = get_polymer('PS')
        pmma = get_polymer('PMMA')
        result = score_aging_penalty(ps, pmma)
        self.assertGreater(result.score, 0.5)

    def test_water_ptfe_penalty(self):
        """Water + PTFE is known bad."""
        water = get_polymer('Water')
        ptfe = get_polymer('PTFE')
        result = score_aging_penalty(water, ptfe)
        self.assertLess(result.score, 0.5)


class TestScoreAll(unittest.TestCase):
    """Test composite scorer."""

    def test_score_all_returns_five_scores(self):
        pvdf = get_polymer('PVDF')
        pmma = get_polymer('PMMA')
        results = score_all(pvdf, pmma)
        self.assertEqual(len(results), 5)
        expected_keys = {'solubility_compatibility', 'thermal_compatibility',
                         'mechanical_compatibility', 'chemical_resistance',
                         'aging_penalty'}
        self.assertEqual(set(results.keys()), expected_keys)

    def test_score_all_values_in_range(self):
        pvdf = get_polymer('PVDF')
        pmma = get_polymer('PMMA')
        results = score_all(pvdf, pmma)
        for name, result in results.items():
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
