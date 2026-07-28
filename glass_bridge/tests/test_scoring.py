# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for glass_bridge interaction scoring."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from glass_bridge.material_properties import ALL_GLASSES, get_glass
from glass_bridge.interaction_scoring import (
    ScorerResult,
    score_thermal_expansion_match,
    score_viscosity_compatibility,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    score_all,
)


class TestScorerResultStructure(unittest.TestCase):
    """Test that all scorers return valid ScorerResult objects."""

    def setUp(self):
        self.bk7 = get_glass('BK7')
        self.f2 = get_glass('F2')

    def test_thermal_returns_scorer_result(self):
        r = score_thermal_expansion_match(self.bk7, self.f2)
        self.assertIsInstance(r, ScorerResult)
        self.assertIsInstance(r.score, float)
        self.assertIsInstance(r.label, str)
        self.assertIsInstance(r.details, dict)

    def test_viscosity_returns_scorer_result(self):
        r = score_viscosity_compatibility(self.bk7, self.f2)
        self.assertIsInstance(r, ScorerResult)

    def test_mechanical_returns_scorer_result(self):
        r = score_mechanical_compatibility(self.bk7, self.f2)
        self.assertIsInstance(r, ScorerResult)

    def test_chemical_returns_scorer_result(self):
        r = score_chemical_compatibility(self.bk7, self.f2)
        self.assertIsInstance(r, ScorerResult)

    def test_degradation_returns_scorer_result(self):
        r = score_degradation_penalty(self.bk7, self.f2)
        self.assertIsInstance(r, ScorerResult)


class TestScorerRanges(unittest.TestCase):
    """Test that all scorers produce values in [0, 1] for all pairs."""

    def test_all_pairwise_scores_in_range(self):
        glasses = list(ALL_GLASSES.values())
        # Test a representative subset (first 15)
        subset = glasses[:15]
        for i, mat_a in enumerate(subset):
            for mat_b in subset[i+1:]:
                results = score_all(mat_a, mat_b)
                for name, r in results.items():
                    self.assertGreaterEqual(r.score, 0.0,
                        f"{mat_a.formula}<->{mat_b.formula} {name}={r.score}")
                    self.assertLessEqual(r.score, 1.0,
                        f"{mat_a.formula}<->{mat_b.formula} {name}={r.score}")


class TestThermalExpansionMatch(unittest.TestCase):
    """Test CTE matching scorer specifics."""

    def test_same_glass_excellent(self):
        """Same glass -> CTE diff = 0 -> near 1.0."""
        sl = get_glass('SodaLime_Float')
        r = score_thermal_expansion_match(sl, sl)
        self.assertGreater(r.score, 0.95)

    def test_sodalime_pair_high(self):
        """SodaLime_Float (9.0) vs SodaLime_Container (9.3) -> close CTE."""
        a = get_glass('SodaLime_Float')
        b = get_glass('SodaLime_Container')
        r = score_thermal_expansion_match(a, b)
        self.assertGreater(r.score, 0.8)

    def test_bk7_f2_moderate(self):
        """BK7 (7.1) vs F2 (8.2) -> moderate CTE diff of 1.1."""
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_thermal_expansion_match(a, b)
        self.assertGreater(r.score, 0.75)

    def test_fused_silica_sodalime_bad(self):
        """FusedSilica (0.55) vs SodaLime (9.0) -> extreme CTE mismatch."""
        a = get_glass('FusedSilica')
        b = get_glass('SodaLime_Float')
        r = score_thermal_expansion_match(a, b)
        self.assertLess(r.score, 0.25)

    def test_zerodur_fused_silica_good(self):
        """Zerodur (0.05) vs FusedSilica (0.55) -> both ultra-low CTE, small absolute diff."""
        a = get_glass('LAS_Zerodur')
        b = get_glass('FusedSilica')
        r = score_thermal_expansion_match(a, b)
        self.assertGreater(r.score, 0.75)

    def test_bioglass_fused_silica_bad(self):
        """Bioglass (15.1) vs FusedSilica (0.55) -> extreme mismatch."""
        a = get_glass('Bioglass_45S5')
        b = get_glass('FusedSilica')
        r = score_thermal_expansion_match(a, b)
        self.assertLess(r.score, 0.15)

    def test_chalcogenide_boro_bad(self):
        """As2S3 (24.6) vs Boro_33 (3.3) -> huge CTE diff (21.3)."""
        a = get_glass('As2S3')
        b = get_glass('Boro_33')
        r = score_thermal_expansion_match(a, b)
        self.assertLess(r.score, 0.15)

    def test_boro_pair_good(self):
        """Boro_33 (3.3) vs Boro_51 (5.1) -> moderate 1.8 diff."""
        a = get_glass('Boro_33')
        b = get_glass('Boro_51')
        r = score_thermal_expansion_match(a, b)
        self.assertGreater(r.score, 0.6)

    def test_details_contain_cte_values(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_thermal_expansion_match(a, b)
        self.assertIn('cte_a', r.details)
        self.assertIn('cte_b', r.details)
        self.assertIn('cte_difference', r.details)


class TestViscosityCompatibility(unittest.TestCase):
    """Test viscosity (working temperature) compatibility scorer."""

    def test_same_family_good(self):
        """Soda-lime pair -> very similar softening points."""
        a = get_glass('SodaLime_Float')
        b = get_glass('SodaLime_Container')
        r = score_viscosity_compatibility(a, b)
        self.assertGreater(r.score, 0.8)

    def test_fused_silica_sodalime_low(self):
        """FusedSilica (sp=1665) vs SodaLime (sp=726) -> large gap."""
        a = get_glass('FusedSilica')
        b = get_glass('SodaLime_Float')
        r = score_viscosity_compatibility(a, b)
        self.assertLess(r.score, 0.35)

    def test_chalcogenide_silicate_penalty(self):
        """Chalcogenide + silicate -> composition type penalty."""
        a = get_glass('As2S3')
        b = get_glass('Boro_33')
        r = score_viscosity_compatibility(a, b)
        self.assertLess(r.score, 0.40)

    def test_fluoride_silicate_penalty(self):
        """ZBLAN (fluoride) + SodaLime (silicate) -> composition penalty."""
        a = get_glass('ZBLAN')
        b = get_glass('SodaLime_Float')
        r = score_viscosity_compatibility(a, b)
        self.assertLess(r.score, 0.40)

    def test_bk7_f2_reasonable(self):
        """BK7 (sp=719) vs F2 (sp=592) -> 127C gap, acceptable."""
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_viscosity_compatibility(a, b)
        self.assertGreater(r.score, 0.6)

    def test_bioactive_pair_good(self):
        """Bioglass (sp=600) vs S53P4 (sp=610) -> close."""
        a = get_glass('Bioglass_45S5')
        b = get_glass('S53P4')
        r = score_viscosity_compatibility(a, b)
        self.assertGreater(r.score, 0.8)


class TestMechanicalCompatibility(unittest.TestCase):
    """Test mechanical compatibility scorer."""

    def test_similar_glasses_high(self):
        """Same-family glasses -> similar modulus, toughness, hardness."""
        a = get_glass('SodaLime_Float')
        b = get_glass('SodaLime_Container')
        r = score_mechanical_compatibility(a, b)
        self.assertGreater(r.score, 0.85)

    def test_chalcogenide_vs_glassceramic_lower(self):
        """As2S3 (E=15.8, HK=130) vs LAS_Cooktop (E=92, HK=640) -> mismatch."""
        a = get_glass('As2S3')
        b = get_glass('LAS_Cooktop')
        r = score_mechanical_compatibility(a, b)
        self.assertLess(r.score, 0.40)

    def test_details_contain_ratios(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_mechanical_compatibility(a, b)
        self.assertIn('modulus_ratio', r.details)


class TestChemicalCompatibility(unittest.TestCase):
    """Test chemical compatibility scorer."""

    def test_known_good_pair_high(self):
        """BK7 + F2 -> known compatible pair bonus."""
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_chemical_compatibility(a, b)
        self.assertGreater(r.score, 0.75)

    def test_same_class_bonus(self):
        """Soda-lime pair -> same class bonus."""
        a = get_glass('SodaLime_Float')
        b = get_glass('SodaLime_Container')
        r = score_chemical_compatibility(a, b)
        self.assertGreater(r.score, 0.85)

    def test_known_bad_pair_penalty(self):
        """Bioglass + FusedSilica -> known incompatible pair."""
        a = get_glass('Bioglass_45S5')
        b = get_glass('FusedSilica')
        r = score_chemical_compatibility(a, b)
        self.assertLess(r.score, 0.60)

    def test_durability_mismatch_penalty(self):
        """Bioglass (hydro=5) vs FusedSilica (hydro=1) -> durability gap."""
        a = get_glass('Bioglass_45S5')
        b = get_glass('FusedSilica')
        r = score_chemical_compatibility(a, b)
        # Extreme hydrolytic difference (5 vs 1) should lower score
        self.assertLess(r.score, 0.60)

    def test_chalcogenide_pair_good(self):
        """As2S3 + Ge28Sb12Se60 -> same class, known compatible."""
        a = get_glass('As2S3')
        b = get_glass('Ge28Sb12Se60')
        r = score_chemical_compatibility(a, b)
        self.assertGreater(r.score, 0.85)


class TestDegradationPenalty(unittest.TestCase):
    """Test degradation penalty scorer."""

    def test_clean_pair_high(self):
        """BK7 + F2 -> no major degradation concerns."""
        a = get_glass('BK7')
        b = get_glass('F2')
        r = score_degradation_penalty(a, b)
        self.assertGreater(r.score, 0.7)

    def test_known_bad_pair_penalty(self):
        """As2S3 + Boro_33 -> known bad pairing."""
        a = get_glass('As2S3')
        b = get_glass('Boro_33')
        r = score_degradation_penalty(a, b)
        self.assertLess(r.score, 0.60)

    def test_weathering_penalty(self):
        """F2 has WEATHERING failure mode -> penalty applied."""
        a = get_glass('F2')
        b = get_glass('BK7')
        r = score_degradation_penalty(a, b)
        # F2 has weathering susceptibility
        self.assertIn('weathering', str(r.details.get('reasons', [])).lower())

    def test_poor_hydrolytic_penalty(self):
        """LaserPhosphate (hydro=4) -> poor hydrolytic penalty."""
        a = get_glass('LaserPhosphate')
        b = get_glass('BK7')
        r = score_degradation_penalty(a, b)
        self.assertLess(r.score, 0.85)

    def test_shared_crystallization_penalty(self):
        """Two glasses both prone to crystallization."""
        a = get_glass('Bioglass_45S5')
        b = get_glass('As2S3')
        r = score_degradation_penalty(a, b)
        # Both have CRYSTALLIZATION failure mode
        self.assertLess(r.score, 0.90)


class TestScoreAll(unittest.TestCase):
    """Test the composite score_all function."""

    def test_returns_all_five_scorers(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        results = score_all(a, b)
        self.assertIn('thermal_expansion_match', results)
        self.assertIn('viscosity_compatibility', results)
        self.assertIn('mechanical_compatibility', results)
        self.assertIn('chemical_compatibility', results)
        self.assertIn('degradation_penalty', results)

    def test_all_scores_are_scorer_results(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        results = score_all(a, b)
        for name, r in results.items():
            self.assertIsInstance(r, ScorerResult, f"{name} not ScorerResult")

    def test_good_pair_all_above_0_5(self):
        """BK7 + F2 -> all scores should be reasonable."""
        a = get_glass('BK7')
        b = get_glass('F2')
        results = score_all(a, b)
        for name, r in results.items():
            self.assertGreater(r.score, 0.5,
                f"BK7+F2 {name}={r.score:.3f} below 0.5")


class TestScorerSymmetry(unittest.TestCase):
    """Test that scorers are approximately symmetric: score(A,B) ~ score(B,A)."""

    def test_thermal_symmetric(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r1 = score_thermal_expansion_match(a, b)
        r2 = score_thermal_expansion_match(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=2)

    def test_viscosity_symmetric(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r1 = score_viscosity_compatibility(a, b)
        r2 = score_viscosity_compatibility(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=2)

    def test_mechanical_symmetric(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r1 = score_mechanical_compatibility(a, b)
        r2 = score_mechanical_compatibility(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=2)

    def test_chemical_symmetric(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r1 = score_chemical_compatibility(a, b)
        r2 = score_chemical_compatibility(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=2)

    def test_degradation_symmetric(self):
        a = get_glass('BK7')
        b = get_glass('F2')
        r1 = score_degradation_penalty(a, b)
        r2 = score_degradation_penalty(b, a)
        self.assertAlmostEqual(r1.score, r2.score, places=2)


if __name__ == '__main__':
    unittest.main()
