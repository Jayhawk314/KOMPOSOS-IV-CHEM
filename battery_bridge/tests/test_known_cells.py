# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for known battery cell configurations.

Validates that KNOWN GOOD cells score high and KNOWN PROBLEMATIC cells
flag the correct issues. These are the ground-truth test cases specified
in the module requirements.

GOOD cells (should score high):
- LiFePO4 + Graphite + LiPF6/EC:DMC
- NMC811 + Graphite + LiPF6/EC:EMC

KNOWN PROBLEMS (should flag issues):
- Li metal + liquid carbonate -> dendrite risk
- NMC811 >4.3V + EC -> oxidative decomposition
- Si anode + standard electrolyte -> 300% volume expansion
- LGPS + high voltage cathode -> electrochemical instability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from battery_bridge.interface_validator import (
    BatteryInterfaceValidator, InterfaceConditions,
)
from battery_bridge.battery_flow import (
    BatteryFlowAnalyzer,
    CellConfiguration,
    STANDARD_LFP_CELL,
    STANDARD_NMC811_CELL,
    SOLID_STATE_CELL,
    PROBLEMATIC_SI_CELL,
    PROBLEMATIC_LGPS_CELL,
)
from battery_bridge.integration import (
    check_thermodynamic_coherence,
    run_battery_categorical_analysis,
)


class TestKnownGoodCells(unittest.TestCase):
    """Known good cell configurations should score high."""

    def setUp(self):
        self.analyzer = BatteryFlowAnalyzer()

    def test_standard_lfp_cell_viable(self):
        """
        LiFePO4 + Graphite + LiPF6/EC:DMC should be viable.
        This is the most mature, safest Li-ion chemistry (BYD Blade).
        """
        analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        self.assertTrue(analysis.viable,
                        f"Standard LFP cell should be viable (score={analysis.overall_viability:.3f})")
        self.assertGreater(analysis.overall_viability, 0.45,
                           "LFP cell viability should be > 0.45")

    def test_standard_nmc811_cell_viable(self):
        """
        NMC811 + Graphite + LiPF6/EC:EMC should be viable.
        This is the standard EV cell chemistry (Tesla, BMW, etc.).
        """
        analysis = self.analyzer.analyze_cell(STANDARD_NMC811_CELL)
        self.assertTrue(analysis.viable,
                        f"NMC811 EV cell should be viable (score={analysis.overall_viability:.3f})")
        self.assertGreater(analysis.overall_viability, 0.40,
                           "NMC811 cell viability should be > 0.40")

    def test_lfp_cell_voltage_correct(self):
        """LFP/Graphite cell voltage should be ~3.3V."""
        analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        self.assertIsNotNone(analysis.cell_voltage)
        self.assertAlmostEqual(analysis.cell_voltage, 3.3, delta=0.2,
                               msg="LFP/Graphite cell voltage should be ~3.3V")

    def test_nmc811_cell_voltage_correct(self):
        """NMC811/Graphite cell voltage should be ~3.7V."""
        analysis = self.analyzer.analyze_cell(STANDARD_NMC811_CELL)
        self.assertIsNotNone(analysis.cell_voltage)
        self.assertAlmostEqual(analysis.cell_voltage, 3.7, delta=0.2,
                               msg="NMC811/Graphite cell voltage should be ~3.7V")

    def test_lfp_better_than_problematic(self):
        """LFP cell should score higher than Si anode cell."""
        lfp_analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        si_analysis = self.analyzer.analyze_cell(PROBLEMATIC_SI_CELL)
        self.assertGreater(lfp_analysis.overall_viability,
                           si_analysis.overall_viability,
                           "LFP cell should outscore Si anode cell")


class TestKnownProblems(unittest.TestCase):
    """Known problematic configurations should flag issues."""

    def setUp(self):
        self.validator = BatteryInterfaceValidator()
        self.analyzer = BatteryFlowAnalyzer()

    def test_li_metal_liquid_carbonate_dendrite_risk(self):
        """
        Li metal anode + liquid carbonate electrolyte -> dendrite risk.
        Should flag interface compatibility issues.
        """
        result = self.validator.validate('Li_metal', 'EC')
        self.assertLess(result.interface_compatibility, 0.5,
                        "Li metal + EC interface should flag poor compatibility")
        self.assertLess(result.degradation_penalty, 0.5,
                        "Li metal + EC should trigger degradation penalty")

    def test_nmc811_high_voltage_ec_decomposition(self):
        """
        NMC811 at >4.3V + standard EC -> oxidative decomposition.
        Electrochemical stability score should be reduced.
        """
        result = self.validator.validate('NMC811', 'EC')
        # NMC811 upper voltage (4.3V) is close to EC oxidation (4.5V)
        # Should show at least marginal concern
        self.assertLess(result.electrochemical_stability, 0.95,
                        "NMC811 near EC oxidation limit should reduce stability score")

    def test_si_anode_volume_expansion(self):
        """
        Si anode + standard electrolyte -> 300% volume expansion.
        Mechanical compatibility score should tank.
        """
        result = self.validator.validate('Si', 'EC')
        self.assertLess(result.mechanical_compatibility, 0.3,
                        "Si 300% expansion should severely penalize mechanical score")

    def test_lgps_high_voltage_cathode_instability(self):
        """
        LGPS solid electrolyte + NMC811 -> electrochemical instability.
        LGPS stable only to 2.1V, NMC811 operates at 3.8V.
        """
        result = self.validator.validate('LGPS', 'NMC811')
        self.assertLess(result.electrochemical_stability, 0.3,
                        "LGPS + NMC811: massive voltage mismatch")
        self.assertLess(result.total, 0.5,
                        "LGPS + NMC811 should not be viable")

    def test_si_cell_degradation_cascades(self):
        """Si anode cell should predict volume expansion cascade."""
        analysis = self.analyzer.analyze_cell(PROBLEMATIC_SI_CELL)
        cascade_triggers = [dc.trigger_failure for dc in analysis.degradation_cascades]
        self.assertIn('volume_expansion', cascade_triggers,
                      "Si cell should predict volume expansion degradation cascade")

    def test_lgps_cell_low_viability(self):
        """LGPS + NMC811 cell should have low viability."""
        analysis = self.analyzer.analyze_cell(PROBLEMATIC_LGPS_CELL)
        # The cell config includes LiPF6 salt interfaces which score OK,
        # so overall is pulled up slightly. The LGPS<->NMC811 bottleneck
        # should still dominate and keep viability well below good cells.
        self.assertLess(analysis.overall_viability, 0.55,
                        f"LGPS + NMC811 cell should have low viability "
                        f"(score={analysis.overall_viability:.3f})")
        # Verify the bottleneck is the LGPS interface
        self.assertIsNotNone(analysis.bottleneck)
        self.assertIn('LGPS', [analysis.bottleneck.material_a, analysis.bottleneck.material_b],
                      "LGPS should be in the bottleneck interface")


class TestCellAnalysisStructure(unittest.TestCase):
    """Test that cell analysis returns proper structure."""

    def setUp(self):
        self.analyzer = BatteryFlowAnalyzer()

    def test_analysis_has_interfaces(self):
        """Cell analysis should enumerate multiple interfaces."""
        analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        self.assertGreater(len(analysis.interfaces), 0,
                           "Cell should have at least one interface")

    def test_analysis_identifies_bottleneck(self):
        """Cell analysis should identify a bottleneck interface."""
        analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        self.assertIsNotNone(analysis.bottleneck,
                             "Cell should identify a bottleneck")
        self.assertTrue(analysis.bottleneck.is_bottleneck)

    def test_to_dict_serialization(self):
        """CellAnalysis.to_dict() should produce valid dict."""
        analysis = self.analyzer.analyze_cell(STANDARD_LFP_CELL)
        d = analysis.to_dict()
        self.assertIn('cell_name', d)
        self.assertIn('overall_viability', d)
        self.assertIn('viable', d)
        self.assertIn('interface_scores', d)

    def test_cell_comparison_ranking(self):
        """compare_cells should rank cells by viability."""
        cells = [STANDARD_LFP_CELL, PROBLEMATIC_SI_CELL, STANDARD_NMC811_CELL]
        ranked = self.analyzer.compare_cells(cells)
        self.assertEqual(len(ranked), 3)
        # First should have highest viability
        self.assertGreaterEqual(ranked[0].overall_viability,
                                ranked[-1].overall_viability)


class TestConditionEffects(unittest.TestCase):
    """Test that operating conditions affect scores."""

    def setUp(self):
        self.validator = BatteryInterfaceValidator()

    def test_high_temperature_degrades(self):
        """High temperature should reduce degradation score."""
        result_25c = self.validator.validate('LFP', 'EC', InterfaceConditions(temperature_C=25))
        result_80c = self.validator.validate('LFP', 'EC', InterfaceConditions(temperature_C=80))
        self.assertGreaterEqual(result_25c.degradation_penalty,
                                result_80c.degradation_penalty,
                                "High temperature should degrade degradation score")

    def test_low_temperature_hurts_transport(self):
        """Low temperature should reduce ion transport score."""
        result_25c = self.validator.validate('LFP', 'EC', InterfaceConditions(temperature_C=25))
        result_neg20c = self.validator.validate('LFP', 'EC', InterfaceConditions(temperature_C=-20))
        self.assertGreaterEqual(result_25c.ion_transport,
                                result_neg20c.ion_transport,
                                "Low temperature should hurt ion transport")

    def test_high_c_rate_stresses_mechanics(self):
        """High C-rate should reduce mechanical compatibility."""
        result_1c = self.validator.validate('NMC811', 'EC', InterfaceConditions(c_rate=1.0))
        result_5c = self.validator.validate('NMC811', 'EC', InterfaceConditions(c_rate=5.0))
        self.assertGreaterEqual(result_1c.mechanical_compatibility,
                                result_5c.mechanical_compatibility,
                                "High C-rate should stress mechanical compatibility")


class TestIntegration(unittest.TestCase):
    """Test KOMPOSOS integration functions."""

    def test_thermodynamic_coherence_runs(self):
        """check_thermodynamic_coherence should return valid dict."""
        analyzer = BatteryFlowAnalyzer()
        analysis = analyzer.analyze_cell(STANDARD_LFP_CELL)
        coherence = check_thermodynamic_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)
        self.assertIn('violations', coherence)

    def test_full_categorical_analysis_runs(self):
        """run_battery_categorical_analysis should complete without error."""
        result = run_battery_categorical_analysis(STANDARD_LFP_CELL)
        self.assertIn('cell', result)
        self.assertIn('coherence', result)
        self.assertIn('overall_viability', result['cell'])


if __name__ == '__main__':
    unittest.main()
