# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for known good/bad semiconductor heterostructure configurations.

Verifies the full pipeline: material properties -> scorers ->
validator -> heterostructure analyzer for known real-world cases.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from semiconductor_bridge.material_properties import get_semiconductor
from semiconductor_bridge.interface_validator import (
    SemiconductorInterfaceValidator, SemiconductorConditions, SemiconductorWeights,
    validate_interface,
)
from semiconductor_bridge.heterostructure_analyzer import (
    HeterostructureAnalyzer, HeterostructureConfiguration, HeterostructureAnalysis,
    GAAS_ALGAAS_HEMT, INGAAS_INP_TELECOM, GAN_ALGAN_POWER,
    SI_SIGE_BICMOS, MOS2_WS2_2D, SIC_GAN_POWER,
    PROBLEMATIC_GAAS_SI, PROBLEMATIC_INAS_GAP,
    PROBLEMATIC_GAN_GAAS, PROBLEMATIC_INSB_SI,
)
from semiconductor_bridge.integration import (
    check_heterostructure_coherence,
    run_semiconductor_categorical_analysis,
)


class TestKnownGoodHeterostructures(unittest.TestCase):
    """Known good heterostructures should score above viability threshold."""

    def setUp(self):
        self.validator = SemiconductorInterfaceValidator()

    def test_gaas_algaas_viable(self):
        """GaAs + AlGaAs: standard HEMT/laser heterostructure."""
        result = self.validator.validate('GaAs', 'AlGaAs')
        self.assertTrue(result.viable, f"GaAs+AlGaAs should be viable (total={result.total:.3f})")

    def test_ingaas_inp_viable(self):
        """InGaAs + InP: lattice-matched telecom system."""
        result = self.validator.validate('InGaAs', 'InP')
        self.assertTrue(result.viable, f"InGaAs+InP should be viable (total={result.total:.3f})")

    def test_gan_algan_viable(self):
        """GaN + AlGaN: power HEMT barrier."""
        result = self.validator.validate('GaN', 'AlGaN')
        self.assertTrue(result.viable, f"GaN+AlGaN should be viable (total={result.total:.3f})")

    def test_si_sige_viable(self):
        """Si + SiGe: standard BiCMOS process."""
        result = self.validator.validate('Si', 'SiGe')
        self.assertTrue(result.viable, f"Si+SiGe should be viable (total={result.total:.3f})")

    def test_mos2_ws2_viable(self):
        """MoS2 + WS2: 2D TMD heterostructure."""
        result = self.validator.validate('MoS2', 'WS2')
        self.assertTrue(result.viable, f"MoS2+WS2 should be viable (total={result.total:.3f})")


class TestKnownProblematicJunctions(unittest.TestCase):
    """Known bad junctions should flag issues."""

    def setUp(self):
        self.validator = SemiconductorInterfaceValidator()

    def test_gaas_si_low_score(self):
        """GaAs + Si: 4.1% lattice mismatch."""
        result = self.validator.validate('GaAs', 'Si')
        self.assertLess(result.total, 0.60,
                        f"GaAs+Si should score low (total={result.total:.3f})")
        self.assertLess(result.lattice_match, 0.45,
                        "GaAs+Si lattice match should be low")

    def test_inas_gap_low_score(self):
        """InAs + GaP: 11.1% lattice mismatch."""
        result = self.validator.validate('InAs', 'GaP')
        self.assertLess(result.total, 0.50,
                        f"InAs+GaP should score low (total={result.total:.3f})")
        self.assertLess(result.lattice_match, 0.15,
                        "InAs+GaP lattice match should be very low")

    def test_gan_gaas_low_score(self):
        """GaN + GaAs: incompatible crystal structures."""
        result = self.validator.validate('GaN', 'GaAs')
        self.assertLess(result.total, 0.45,
                        f"GaN+GaAs should score low (total={result.total:.3f})")

    def test_insb_si_low_score(self):
        """InSb + Si: 19.3% lattice mismatch."""
        result = self.validator.validate('InSb', 'Si')
        self.assertLess(result.total, 0.45,
                        f"InSb+Si should score low (total={result.total:.3f})")


class TestHeterostructureAnalysis(unittest.TestCase):
    """Full heterostructure analysis pipeline."""

    def setUp(self):
        self.analyzer = HeterostructureAnalyzer()

    def test_gaas_algaas_compatible(self):
        """GaAs/AlGaAs HEMT should be compatible."""
        analysis = self.analyzer.analyze_heterostructure(GAAS_ALGAAS_HEMT)
        self.assertTrue(analysis.compatible,
                        f"GaAs/AlGaAs should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_ingaas_inp_compatible(self):
        """InGaAs/InP telecom should be compatible."""
        analysis = self.analyzer.analyze_heterostructure(INGAAS_INP_TELECOM)
        self.assertTrue(analysis.compatible,
                        f"InGaAs/InP should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_gan_algan_compatible(self):
        """GaN/AlGaN power HEMT should be compatible."""
        analysis = self.analyzer.analyze_heterostructure(GAN_ALGAN_POWER)
        self.assertTrue(analysis.compatible,
                        f"GaN/AlGaN should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_si_sige_compatible(self):
        """Si/SiGe BiCMOS should be compatible."""
        analysis = self.analyzer.analyze_heterostructure(SI_SIGE_BICMOS)
        self.assertTrue(analysis.compatible,
                        f"Si/SiGe should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_gaas_si_problematic(self):
        """GaAs on Si should show low compatibility."""
        analysis = self.analyzer.analyze_heterostructure(PROBLEMATIC_GAAS_SI)
        self.assertLess(analysis.overall_compatibility, 0.55,
                        f"GaAs/Si should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_inas_gap_problematic(self):
        """InAs on GaP should show low compatibility."""
        analysis = self.analyzer.analyze_heterostructure(PROBLEMATIC_INAS_GAP)
        self.assertLess(analysis.overall_compatibility, 0.50,
                        f"InAs/GaP should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_gan_gaas_problematic(self):
        """GaN on GaAs should show low compatibility."""
        analysis = self.analyzer.analyze_heterostructure(PROBLEMATIC_GAN_GAAS)
        self.assertLess(analysis.overall_compatibility, 0.45,
                        f"GaN/GaAs should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_insb_si_problematic(self):
        """InSb on Si should show low compatibility."""
        analysis = self.analyzer.analyze_heterostructure(PROBLEMATIC_INSB_SI)
        self.assertLess(analysis.overall_compatibility, 0.45,
                        f"InSb/Si should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_sic_gan_multi_layer(self):
        """SiC/GaN/AlGaN multi-layer should be analyzable."""
        analysis = self.analyzer.analyze_heterostructure(SIC_GAN_POWER)
        self.assertIsNotNone(analysis)
        self.assertGreater(len(analysis.interfaces), 0)


class TestAnalysisStructure(unittest.TestCase):
    """Verify analysis result structure."""

    def setUp(self):
        self.analyzer = HeterostructureAnalyzer()
        self.analysis = self.analyzer.analyze_heterostructure(GAAS_ALGAAS_HEMT)

    def test_has_heterostructure_name(self):
        self.assertEqual(self.analysis.heterostructure_name, 'GaAs/AlGaAs HEMT')

    def test_viability_in_range(self):
        self.assertGreaterEqual(self.analysis.overall_compatibility, 0.0)
        self.assertLessEqual(self.analysis.overall_compatibility, 1.0)

    def test_has_interfaces(self):
        self.assertGreater(len(self.analysis.interfaces), 0)

    def test_has_bottleneck(self):
        if len(self.analysis.interfaces) > 0:
            self.assertIsNotNone(self.analysis.bottleneck)
            self.assertTrue(self.analysis.bottleneck.is_bottleneck)

    def test_to_dict_works(self):
        d = self.analysis.to_dict()
        self.assertIn('heterostructure_name', d)
        self.assertIn('overall_compatibility', d)
        self.assertIn('compatible', d)
        self.assertIn('interface_scores', d)


class TestConditionEffects(unittest.TestCase):
    """Verify operating condition modifiers work."""

    def setUp(self):
        self.validator = SemiconductorInterfaceValidator()

    def test_space_penalizes(self):
        """Space environment should penalize degradation."""
        normal = self.validator.validate('GaAs', 'AlGaAs')
        space_cond = SemiconductorConditions(environment="space", radiation_exposure=True)
        space_result = self.validator.validate('GaAs', 'AlGaAs', space_cond)
        self.assertLessEqual(space_result.total, normal.total + 0.01)

    def test_high_temp_effect(self):
        """High temperature should affect thermal and degradation scores."""
        normal = self.validator.validate('GaN', 'AlGaN')
        hot_cond = SemiconductorConditions(temperature_C=400, environment="high_temp")
        hot_result = self.validator.validate('GaN', 'AlGaN', hot_cond)
        self.assertLessEqual(hot_result.total, normal.total + 0.01)

    def test_outdoor_effect(self):
        """Outdoor should penalize moisture-sensitive materials."""
        normal = self.validator.validate('AlAs', 'GaAs')
        outdoor_cond = SemiconductorConditions(environment="outdoor", humidity_pct=90)
        outdoor_result = self.validator.validate('AlAs', 'GaAs', outdoor_cond)
        self.assertLessEqual(outdoor_result.total, normal.total + 0.01)


class TestWeightPresets(unittest.TestCase):
    """Verify weight presets work and produce different rankings."""

    def test_default_weights_valid(self):
        w = SemiconductorWeights.default()
        w.validate()

    def test_optoelectronic_focus_valid(self):
        w = SemiconductorWeights.optoelectronic_focus()
        w.validate()

    def test_power_focus_valid(self):
        w = SemiconductorWeights.power_focus()
        w.validate()

    def test_rf_focus_valid(self):
        w = SemiconductorWeights.rf_focus()
        w.validate()

    def test_invalid_weights_raise(self):
        w = SemiconductorWeights(lattice=0.5, band=0.5, thermal=0.5,
                                  process=0.5, degradation=0.5)
        with self.assertRaises(ValueError):
            w.validate()

    def test_rf_focus_emphasizes_lattice(self):
        w = SemiconductorWeights.rf_focus()
        self.assertEqual(w.lattice, 0.35)
        self.assertGreater(w.lattice, w.band)


class TestIntegration(unittest.TestCase):
    """Test KOMPOSOS integration layer."""

    def test_coherence_check(self):
        """Coherence check should work on heterostructure analysis."""
        analyzer = HeterostructureAnalyzer()
        analysis = analyzer.analyze_heterostructure(GAAS_ALGAAS_HEMT)
        coherence = check_heterostructure_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)

    def test_categorical_analysis_pipeline(self):
        """Full categorical analysis should return valid dict."""
        result = run_semiconductor_categorical_analysis(GAAS_ALGAAS_HEMT)
        self.assertIn('heterostructure', result)
        self.assertIn('coherence', result)
        hetero = result['heterostructure']
        self.assertIn('overall_compatibility', hetero)
        self.assertIn('compatible', hetero)

    def test_compare_heterostructures(self):
        """compare_heterostructures should rank by compatibility."""
        analyzer = HeterostructureAnalyzer()
        ranked = analyzer.compare_heterostructures([
            GAAS_ALGAAS_HEMT,
            INGAAS_INP_TELECOM,
            PROBLEMATIC_GAAS_SI,
        ])
        self.assertEqual(len(ranked), 3)
        self.assertGreaterEqual(ranked[0].overall_compatibility,
                                ranked[-1].overall_compatibility)


class TestConvenienceFunction(unittest.TestCase):
    """Test the convenience validate_interface function."""

    def test_validate_interface_works(self):
        result = validate_interface('GaAs', 'AlGaAs')
        self.assertGreater(result.total, 0)
        self.assertIsInstance(result.viable, bool)

    def test_validate_interface_unknown_raises(self):
        with self.assertRaises(ValueError):
            validate_interface('GaAs', 'NONEXISTENT')


class TestValidateAllInterfaces(unittest.TestCase):
    """Test pairwise validation."""

    def test_validate_all(self):
        validator = SemiconductorInterfaceValidator()
        results = validator.validate_all_interfaces(['GaAs', 'AlGaAs', 'InP', 'Si'])
        # C(4,2) = 6 pairs
        self.assertEqual(len(results), 6)
        for key, score in results.items():
            self.assertGreaterEqual(score.total, 0.0)
            self.assertLessEqual(score.total, 1.0)


if __name__ == "__main__":
    unittest.main()
