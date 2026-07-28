# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for ceramic-metal cross-bridge functor."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from cross_bridge.ceramic_metal import (
    score_coating_compatibility,
    CeramicMetalResult,
    DepositionMethod,
    KNOWN_GOOD_PAIRS,
    KNOWN_BAD_PAIRS,
)


class TestResultStructure(unittest.TestCase):
    """Test that results have correct structure."""

    def test_returns_ceramic_metal_result(self):
        r = score_coating_compatibility('Al2O3', 'SS_304')
        self.assertIsInstance(r, CeramicMetalResult)

    def test_has_all_fields(self):
        r = score_coating_compatibility('Al2O3', 'SS_304')
        self.assertIsInstance(r.compatible, bool)
        self.assertIsInstance(r.score, float)
        self.assertIsInstance(r.cte_compatibility, float)
        self.assertIsInstance(r.thermal_processing, float)
        self.assertIsInstance(r.mechanical_compatibility, float)
        self.assertIsInstance(r.chemical_interaction, float)
        self.assertIsInstance(r.ceramic_name, str)
        self.assertIsInstance(r.metal_name, str)

    def test_scores_in_range(self):
        r = score_coating_compatibility('Al2O3', 'SS_304')
        for field_name in ['score', 'cte_compatibility', 'thermal_processing',
                           'mechanical_compatibility', 'chemical_interaction']:
            val = getattr(r, field_name)
            self.assertGreaterEqual(val, 0.0, f"{field_name}={val}")
            self.assertLessEqual(val, 1.0, f"{field_name}={val}")


class TestUnknownMaterials(unittest.TestCase):
    """Test graceful handling of unknown materials."""

    def test_unknown_ceramic(self):
        r = score_coating_compatibility('NONEXISTENT', 'SS_304')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)
        self.assertTrue(any('Unknown ceramic' in w for w in r.warnings))

    def test_unknown_metal(self):
        r = score_coating_compatibility('Al2O3', 'NONEXISTENT')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)
        self.assertTrue(any('Unknown metal' in w for w in r.warnings))


class TestKnownGoodPairs(unittest.TestCase):
    """Test known good ceramic-metal combinations."""

    def test_al2o3_ss304(self):
        """Alumina on stainless steel - common industrial coating."""
        r = score_coating_compatibility('Al2O3', 'SS_304')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_tin_ti6al4v(self):
        """TiN on Ti alloy - excellent CTE match (9.4 vs 8.6)."""
        r = score_coating_compatibility('TiN', 'Ti6Al4V')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.6)

    def test_tin_steel4140(self):
        """TiN hard coating on tool steel - standard tooling."""
        r = score_coating_compatibility('TiN', 'Steel_4140')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_ysz_inconel(self):
        """YSZ thermal barrier on Inconel - aerospace standard."""
        r = score_coating_compatibility('ZrO2_YSZ', 'Inconel_718')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_sic_steel(self):
        """SiC coating on tool steel."""
        r = score_coating_compatibility('SiC', 'Steel_4140')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)


class TestKnownBadPairs(unittest.TestCase):
    """Test known problematic ceramic-metal combinations."""

    def test_sio2_al_extreme_cte(self):
        """SiO2 on Al: CTE 0.55 vs 23.1 - extreme mismatch."""
        r = score_coating_compatibility('SiO2', 'Al')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.4)

    def test_al2o3_mg_bad(self):
        """Alumina on Mg: CTE mismatch + reactivity."""
        r = score_coating_compatibility('Al2O3', 'Mg')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)

    def test_sio2_al6061_extreme_cte(self):
        """SiO2 on Al alloy: same extreme CTE mismatch."""
        r = score_coating_compatibility('SiO2', 'Al_6061')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.4)


class TestCTECompatibility(unittest.TestCase):
    """Test CTE matching specifics."""

    def test_tin_ti_excellent_cte_match(self):
        """TiN (9.4) vs Ti6Al4V (8.6) - only 0.8 difference."""
        r = score_coating_compatibility('TiN', 'Ti6Al4V')
        self.assertGreater(r.cte_compatibility, 0.8)

    def test_sio2_al_terrible_cte_match(self):
        """SiO2 (0.55) vs Al (23.1) - 22.5 difference."""
        r = score_coating_compatibility('SiO2', 'Al')
        self.assertLess(r.cte_compatibility, 0.2)

    def test_al2o3_ni_moderate_cte(self):
        """Al2O3 (8.1) vs Ni (13.4) - 5.3 difference, manageable."""
        r = score_coating_compatibility('Al2O3', 'Ni')
        self.assertGreater(r.cte_compatibility, 0.5)


class TestThermalProcessing(unittest.TestCase):
    """Test thermal processing window scoring."""

    def test_al2o3_on_tungsten_ok(self):
        """Al2O3 sinters at 1600C, W melts at 3422C - huge margin."""
        r = score_coating_compatibility('Al2O3', 'W')
        self.assertGreater(r.thermal_processing, 0.8)

    def test_al2o3_on_al_sintering_impossible(self):
        """Al2O3 sinters at 1600C, Al melts at 660C - bulk sintering impossible.
        But PVD/CVD route exists (substrate stays below 500C, Al melts at 660C)."""
        r = score_coating_compatibility('Al2O3', 'Al')
        # PVD route is available so thermal_processing isn't zero
        # But bulk sintering is impossible
        self.assertIn('bulk_sintering_impossible', r.details.get('thermal_processing', {}))


class TestWarnings(unittest.TestCase):
    """Test warning generation."""

    def test_cte_veto_warning(self):
        r = score_coating_compatibility('SiO2', 'Al')
        warning_text = ' '.join(r.warnings).lower()
        self.assertTrue('cte' in warning_text or 'thermal' in warning_text,
                        f"Expected CTE warning, got: {r.warnings}")

    def test_cte_warning_for_extreme_mismatch(self):
        """Al2O3 on Al: CTE 8.1 vs 23.1 triggers CTE veto."""
        r = score_coating_compatibility('Al2O3', 'Al')
        warning_text = ' '.join(r.warnings).lower()
        self.assertTrue('cte' in warning_text,
                        f"Expected CTE warning, got: {r.warnings}")


class TestDepositionMethod(unittest.TestCase):
    """Test deposition-method-aware scoring."""

    def test_bn_hex_cvd_on_ss304_nonzero(self):
        """BN_hex via CVD on stainless steel should score non-zero.
        CTE diff 1.0 vs 17.3 = 16.3, but CVD compliance factor 0.5
        makes effective diff 8.15, avoiding the CTE veto."""
        r = score_coating_compatibility('BN_hex', 'SS_304',
                                         deposition_method=DepositionMethod.CVD)
        self.assertGreater(r.score, 0.0)
        self.assertGreater(r.cte_compatibility, 0.15)  # No CTE veto

    def test_bn_hex_pvd_on_ti6al4v_nonzero(self):
        """BN_hex via PVD on Ti alloy should score non-zero."""
        r = score_coating_compatibility('BN_hex', 'Ti6Al4V',
                                         deposition_method=DepositionMethod.PVD)
        self.assertGreater(r.score, 0.0)

    def test_al2o3_bulk_sintering_on_al_still_impossible(self):
        """Al2O3 bulk sintering on Al: sintering temp exceeds melting (regression)."""
        r = score_coating_compatibility('Al2O3', 'Al',
                                         deposition_method=DepositionMethod.BULK_SINTERING)
        self.assertIn('bulk_sintering_impossible',
                      r.details.get('thermal_processing', {}))


class TestAllKnownPairsScoreable(unittest.TestCase):
    """Test that all defined known pairs score without errors."""

    def test_all_good_pairs(self):
        for ceramic, metal in KNOWN_GOOD_PAIRS:
            r = score_coating_compatibility(ceramic, metal)
            self.assertIsInstance(r.score, float,
                                 f"Failed on {ceramic}+{metal}")

    def test_all_bad_pairs(self):
        for ceramic, metal in KNOWN_BAD_PAIRS:
            r = score_coating_compatibility(ceramic, metal)
            self.assertIsInstance(r.score, float,
                                 f"Failed on {ceramic}+{metal}")


if __name__ == '__main__':
    unittest.main()
