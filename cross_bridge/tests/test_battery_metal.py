# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for battery-metal cross-bridge functor."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from cross_bridge.battery_metal import (
    score_collector_compatibility,
    BatteryMetalResult,
    KNOWN_GOOD_PAIRS,
    KNOWN_BAD_PAIRS,
)


class TestResultStructure(unittest.TestCase):
    """Test that results have correct structure."""

    def test_returns_battery_metal_result(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        self.assertIsInstance(r, BatteryMetalResult)

    def test_has_all_fields(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        self.assertIsInstance(r.compatible, bool)
        self.assertIsInstance(r.score, float)
        self.assertIsInstance(r.electrochemical_stability, float)
        self.assertIsInstance(r.galvanic_risk, float)
        self.assertIsInstance(r.cte_compatibility, float)
        self.assertIsInstance(r.conductivity_score, float)
        self.assertIsInstance(r.corrosion_risk, float)

    def test_scores_in_range(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        for field_name in ['score', 'electrochemical_stability', 'galvanic_risk',
                           'cte_compatibility', 'conductivity_score', 'corrosion_risk']:
            val = getattr(r, field_name)
            self.assertGreaterEqual(val, 0.0, f"{field_name}={val}")
            self.assertLessEqual(val, 1.0, f"{field_name}={val}")

    def test_works_without_electrolyte(self):
        r = score_collector_compatibility('Al_foil', 'LFP')
        self.assertIsInstance(r, BatteryMetalResult)


class TestUnknownMaterials(unittest.TestCase):
    """Test graceful handling of unknown materials."""

    def test_unknown_metal(self):
        r = score_collector_compatibility('NONEXISTENT', 'LFP', 'LiPF6')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)

    def test_unknown_electrode(self):
        r = score_collector_compatibility('Al_foil', 'NONEXISTENT', 'LiPF6')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)

    def test_unknown_electrolyte_warns(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'NONEXISTENT')
        self.assertTrue(any('Unknown electrolyte' in w for w in r.warnings))


class TestKnownGoodPairs(unittest.TestCase):
    """Test standard good collector-electrode-electrolyte combinations."""

    def test_al_lfp_lipf6(self):
        """Al foil + LFP cathode + LiPF6: industry standard."""
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_al_nmc811_lipf6(self):
        """Al foil + NMC811 cathode + LiPF6: standard high-energy cell."""
        r = score_collector_compatibility('Al_foil', 'NMC811', 'LiPF6')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_cu_graphite_lipf6(self):
        """Cu foil + graphite anode + LiPF6: industry standard."""
        r = score_collector_compatibility('Cu_foil', 'Graphite', 'LiPF6')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_cu_si_lipf6(self):
        """Cu foil + Si anode: standard Si anode collector."""
        r = score_collector_compatibility('Cu_foil', 'Si', 'LiPF6')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)


class TestKnownBadPairs(unittest.TestCase):
    """Test known problematic combinations."""

    def test_al_litfsi_corrosion(self):
        """Al corrodes in LiTFSI above 3.7V - known issue."""
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiTFSI')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.4)

    def test_cu_at_cathode_voltage(self):
        """Cu dissolves above ~3V, so it can't collect cathodes."""
        r = score_collector_compatibility('Cu_foil', 'NMC811', 'LiPF6')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)

    def test_cu_at_lfp_cathode_voltage(self):
        """Cu dissolves at LFP cathode voltage (3.4V)."""
        r = score_collector_compatibility('Cu_foil', 'LFP', 'LiPF6')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)


class TestElectrochemicalStability(unittest.TestCase):
    """Test electrochemical stability scoring."""

    def test_al_stable_at_cathode(self):
        """Al is anodically stable enough for cathode collection."""
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        self.assertGreater(r.electrochemical_stability, 0.5)

    def test_cu_stable_at_anode(self):
        """Cu is cathodically stable for anode collection."""
        r = score_collector_compatibility('Cu_foil', 'Graphite', 'LiPF6')
        self.assertGreater(r.electrochemical_stability, 0.5)


class TestConductivity(unittest.TestCase):
    """Test conductivity scoring."""

    def test_al_excellent_conductor(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiPF6')
        self.assertGreater(r.conductivity_score, 0.8)

    def test_cu_excellent_conductor(self):
        r = score_collector_compatibility('Cu_foil', 'Graphite', 'LiPF6')
        self.assertGreater(r.conductivity_score, 0.8)


class TestWarnings(unittest.TestCase):
    """Test warning generation."""

    def test_corrosion_warning(self):
        r = score_collector_compatibility('Al_foil', 'LFP', 'LiTFSI')
        warning_text = ' '.join(r.warnings).lower()
        self.assertTrue('corros' in warning_text or 'bad' in warning_text,
                        f"Expected corrosion warning, got: {r.warnings}")


class TestCoatedSubstrates(unittest.TestCase):
    """Test coating-aware electrochemical stability."""

    def test_carbon_coated_cu_at_cathode(self):
        """Carbon-coated Cu should pass at cathode voltage (boost to ~4.5V)."""
        r = score_collector_compatibility('Cu_foil', 'NMC811', 'LiPF6',
                                          metal_coating='carbon')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_al2o3_coated_cu_at_cathode(self):
        """ALD Al2O3-coated Cu should pass at LFP cathode voltage."""
        r = score_collector_compatibility('Cu_foil', 'LFP', 'LiPF6',
                                          metal_coating='Al2O3')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_bare_cu_still_fails_at_cathode(self):
        """Bare Cu at cathode must still fail (regression check)."""
        r = score_collector_compatibility('Cu_foil', 'NMC811', 'LiPF6')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)


class TestAllKnownPairsScoreable(unittest.TestCase):
    """Test that all defined known pairs score without errors."""

    def test_all_good_triples(self):
        for metal, electrode, elyte in KNOWN_GOOD_PAIRS:
            r = score_collector_compatibility(metal, electrode, elyte)
            self.assertIsInstance(r.score, float,
                                 f"Failed on {metal}+{electrode}+{elyte}")

    def test_all_bad_triples(self):
        for metal, electrode, elyte in KNOWN_BAD_PAIRS:
            r = score_collector_compatibility(metal, electrode, elyte)
            self.assertIsInstance(r.score, float,
                                 f"Failed on {metal}+{electrode}+{elyte}")


if __name__ == '__main__':
    unittest.main()
