# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for battery-polymer cross-bridge functor."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from cross_bridge.battery_polymer import (
    score_polymer_electrode_compatibility,
    BatteryPolymerResult,
    KNOWN_GOOD_PAIRS,
    KNOWN_BAD_PAIRS,
)


class TestResultStructure(unittest.TestCase):
    """Test that results have correct structure."""

    def test_returns_battery_polymer_result(self):
        r = score_polymer_electrode_compatibility('PVDF', 'LFP')
        self.assertIsInstance(r, BatteryPolymerResult)

    def test_has_all_fields(self):
        r = score_polymer_electrode_compatibility('PVDF', 'LFP')
        self.assertIsInstance(r.compatible, bool)
        self.assertIsInstance(r.score, float)
        self.assertIsInstance(r.voltage_compatibility, float)
        self.assertIsInstance(r.thermal_compatibility, float)
        self.assertIsInstance(r.mechanical_compatibility, float)
        self.assertIsInstance(r.chemical_compatibility, float)
        self.assertIsInstance(r.polymer_name, str)
        self.assertIsInstance(r.battery_material_name, str)
        self.assertIsInstance(r.warnings, list)
        self.assertIsInstance(r.details, dict)

    def test_scores_in_range(self):
        r = score_polymer_electrode_compatibility('PVDF', 'LFP')
        for field_name in ['score', 'voltage_compatibility', 'thermal_compatibility',
                           'mechanical_compatibility', 'chemical_compatibility']:
            val = getattr(r, field_name)
            self.assertGreaterEqual(val, 0.0, f"{field_name}={val}")
            self.assertLessEqual(val, 1.0, f"{field_name}={val}")


class TestUnknownMaterials(unittest.TestCase):
    """Test graceful handling of unknown materials."""

    def test_unknown_polymer(self):
        r = score_polymer_electrode_compatibility('NONEXISTENT', 'LFP')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)
        self.assertTrue(any('Unknown polymer' in w for w in r.warnings))

    def test_unknown_battery_material(self):
        r = score_polymer_electrode_compatibility('PVDF', 'NONEXISTENT')
        self.assertFalse(r.compatible)
        self.assertEqual(r.score, 0.0)
        self.assertTrue(any('Unknown battery' in w for w in r.warnings))


class TestKnownGoodPairs(unittest.TestCase):
    """Test that known good pairs score well."""

    def test_pvdf_lfp(self):
        """PVDF is the standard cathode binder for LFP."""
        r = score_polymer_electrode_compatibility('PVDF', 'LFP')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.6)

    def test_pvdf_nmc811(self):
        """PVDF is also used with NMC811 cathodes."""
        r = score_polymer_electrode_compatibility('PVDF', 'NMC811')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.6)

    def test_pvdf_graphite(self):
        """PVDF as anode binder for graphite."""
        r = score_polymer_electrode_compatibility('PVDF', 'Graphite')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.6)

    def test_cmc_graphite(self):
        """CMC is the standard water-based anode binder."""
        r = score_polymer_electrode_compatibility('CMC', 'Graphite')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.6)

    def test_peo_lfp(self):
        """PEO polymer electrolyte works with LFP (3.4V, within PEO window)."""
        r = score_polymer_electrode_compatibility('PEO', 'LFP')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)

    def test_ptfe_lfp(self):
        """PTFE alternative binder, chemically inert."""
        r = score_polymer_electrode_compatibility('PTFE', 'LFP')
        self.assertTrue(r.compatible)
        self.assertGreater(r.score, 0.5)


class TestKnownBadPairs(unittest.TestCase):
    """Test that known bad pairs score poorly."""

    def test_peo_nmc811_voltage_problem(self):
        """PEO oxidizes above ~3.8V; NMC811 operates at 3.8V+."""
        r = score_polymer_electrode_compatibility('PEO', 'NMC811')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)

    def test_peo_lco_voltage_problem(self):
        """PEO voltage limit too low for LCO (3.9V nominal)."""
        r = score_polymer_electrode_compatibility('PEO', 'LCO')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)

    def test_cmc_nmc811_bad(self):
        """CMC water-based processing incompatible with high-V cathodes."""
        r = score_polymer_electrode_compatibility('CMC', 'NMC811')
        self.assertFalse(r.compatible)
        self.assertLess(r.score, 0.45)


class TestVoltageCompatibility(unittest.TestCase):
    """Test voltage compatibility scoring specifics."""

    def test_pvdf_high_voltage_ok(self):
        """PVDF stable to ~5V, so NMC811 at 4.3V is fine."""
        r = score_polymer_electrode_compatibility('PVDF', 'NMC811')
        self.assertGreater(r.voltage_compatibility, 0.7)

    def test_peo_low_voltage_ok(self):
        """PEO at LFP (3.4V) is within the 3.8V limit."""
        r = score_polymer_electrode_compatibility('PEO', 'LFP')
        self.assertGreater(r.voltage_compatibility, 0.4)

    def test_peo_high_voltage_marginal(self):
        """PEO limit (3.8V) equals NMC811 nominal (3.8V) - marginal at best."""
        r = score_polymer_electrode_compatibility('PEO', 'NMC811')
        self.assertLessEqual(r.voltage_compatibility, 0.5)


class TestWarnings(unittest.TestCase):
    """Test that appropriate warnings are generated."""

    def test_peo_nmc811_has_warning(self):
        """PEO + NMC811 should generate a veto warning (voltage or chemical)."""
        r = score_polymer_electrode_compatibility('PEO', 'NMC811')
        warning_text = ' '.join(r.warnings).lower()
        self.assertTrue(
            'voltage' in warning_text or 'chemical' in warning_text
            or 'incompatible' in warning_text,
            f"Expected veto warning, got: {r.warnings}"
        )


class TestAllKnownPairsScoreable(unittest.TestCase):
    """Test that all defined known pairs can be scored without errors."""

    def test_all_good_pairs(self):
        for poly, bat in KNOWN_GOOD_PAIRS:
            r = score_polymer_electrode_compatibility(poly, bat)
            self.assertIsInstance(r.score, float,
                                 f"Failed on good pair {poly}+{bat}")
            self.assertGreaterEqual(r.score, 0.0)

    def test_all_bad_pairs(self):
        for poly, bat in KNOWN_BAD_PAIRS:
            r = score_polymer_electrode_compatibility(poly, bat)
            self.assertIsInstance(r.score, float,
                                 f"Failed on bad pair {poly}+{bat}")
            self.assertGreaterEqual(r.score, 0.0)


if __name__ == '__main__':
    unittest.main()
