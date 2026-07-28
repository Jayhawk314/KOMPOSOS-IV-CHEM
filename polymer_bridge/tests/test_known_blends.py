# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for known good/bad polymer blend configurations.

Verifies the full pipeline: material properties -> scorers ->
validator -> blend analyzer for known real-world cases.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from polymer_bridge.material_properties import get_polymer
from polymer_bridge.interface_validator import (
    PolymerInterfaceValidator, PolymerConditions, PolymerWeights,
    validate_interface,
)
from polymer_bridge.blend_analyzer import (
    PolymerBlendAnalyzer, BlendConfiguration, BlendAnalysis,
    STANDARD_PEO_ELECTROLYTE, STANDARD_PVDF_BINDER,
    STANDARD_CMC_SBR_BINDER, ENGINEERING_BLEND,
    PROBLEMATIC_PE_NYLON, PROBLEMATIC_PTFE_BLEND,
)
from polymer_bridge.integration import (
    check_blend_coherence,
    run_polymer_categorical_analysis,
)


class TestKnownGoodBlends(unittest.TestCase):
    """Known good blends should score above viability threshold."""

    def setUp(self):
        self.validator = PolymerInterfaceValidator()
        self.analyzer = PolymerBlendAnalyzer()

    def test_pvdf_pmma_viable(self):
        """PVDF + PMMA: known miscible blend."""
        result = self.validator.validate('PVDF', 'PMMA')
        self.assertTrue(result.viable, f"PVDF+PMMA should be viable (total={result.total:.3f})")

    def test_pvdf_nmp_viable(self):
        """PVDF + NMP: standard battery binder solution."""
        result = self.validator.validate('PVDF', 'NMP')
        self.assertTrue(result.viable, f"PVDF+NMP should be viable (total={result.total:.3f})")

    def test_peo_pmma_viable(self):
        """PEO + PMMA: known miscible blend."""
        result = self.validator.validate('PEO', 'PMMA')
        self.assertTrue(result.viable, f"PEO+PMMA should be viable (total={result.total:.3f})")

    def test_hdpe_pp_chic_veto(self):
        """HDPE + PP: low chi, but high-MW blend still exceeds chi_c."""
        result = self.validator.validate('HDPE', 'PP')
        self.assertFalse(result.viable, f"HDPE+PP should phase-separate (total={result.total:.3f})")
        self.assertIn('flory_huggins', result.details)
        self.assertEqual(result.details['flory_huggins']['reason'], 'chi_above_critical')

    def test_ps_toluene_viable(self):
        """PS + Toluene: PS dissolves in toluene."""
        result = self.validator.validate('PS', 'Toluene')
        self.assertTrue(result.viable, f"PS+Toluene should be viable (total={result.total:.3f})")

    def test_pc_abs_viable(self):
        """PC + ABS: common engineering blend."""
        result = self.validator.validate('PC', 'ABS')
        self.assertTrue(result.viable, f"PC+ABS should be viable (total={result.total:.3f})")
        self.assertEqual(result.details['flory_huggins']['chi_source'], 'empirical_compatibility_override')

    def test_ptfe_peek_viable(self):
        """PTFE + PEEK: compatible tribological composite interface."""
        result = self.validator.validate('PTFE', 'PEEK')
        self.assertTrue(result.viable, f"PTFE+PEEK should be viable (total={result.total:.3f})")

    def test_pps_ptfe_viable(self):
        """PPS + PTFE: compatible self-lubricating composite interface."""
        result = self.validator.validate('PPS', 'PTFE')
        self.assertTrue(result.viable, f"PPS+PTFE should be viable (total={result.total:.3f})")


class TestKnownProblematicBlends(unittest.TestCase):
    """Known bad blends should flag issues."""

    def setUp(self):
        self.validator = PolymerInterfaceValidator()

    def test_hdpe_pa6_low_score(self):
        """HDPE + PA6: immiscible (chi ~2.0)."""
        result = self.validator.validate('HDPE', 'PA6')
        self.assertLessEqual(result.total, 0.5,
                             f"HDPE+PA6 should score low (total={result.total:.3f})")

    def test_water_hdpe_low_score(self):
        """Water + HDPE: extreme polarity mismatch."""
        result = self.validator.validate('Water', 'HDPE')
        self.assertLess(result.total, 0.7,
                        f"Water+HDPE should score below viable (total={result.total:.3f})")
        # Solubility should be very low even if other scores are moderate
        self.assertLess(result.solubility_compatibility, 0.1,
                        "Water+HDPE solubility should be near zero")

    def test_pp_pa6_low_score(self):
        """PP + PA6: immiscible (chi ~1.5). Scores marginal because mechanical/thermal
        are compatible — only solubility fails (needs compatibilizer in practice)."""
        result = self.validator.validate('PP', 'PA6')
        self.assertLess(result.total, 0.65,
                        f"PP+PA6 should score below good blends (total={result.total:.3f})")
        # Solubility should be clearly low
        self.assertLess(result.solubility_compatibility, 0.3,
                        "PP+PA6 solubility should be low")

    def test_abs_pvdf_chic_veto_from_hansen(self):
        """ABS + PVDF: HSP-estimated chi exceeds chi_c, so it must veto."""
        result = self.validator.validate('ABS', 'PVDF')
        self.assertFalse(result.viable)
        self.assertEqual(result.details['flory_huggins']['chi_source'], 'hansen_estimate')
        self.assertEqual(result.details['flory_huggins']['reason'], 'chi_above_critical')

    def test_pa66_peo_chic_veto_from_hansen(self):
        """PA66 + PEO: polymer false positive should be rejected."""
        result = self.validator.validate('PA66', 'PEO')
        self.assertFalse(result.viable)
        self.assertEqual(result.details['flory_huggins']['reason'], 'chi_above_critical')

    def test_ps_ppo_empirical_override(self):
        """PS + PPO: empirical favorable chi prevents an HSP-only false veto."""
        result = self.validator.validate('PS', 'PPO')
        self.assertTrue(result.viable, f"PS+PPO should remain viable (total={result.total:.3f})")
        self.assertEqual(result.details['flory_huggins']['reason'], 'negative_empirical_chi')


class TestBlendAnalysis(unittest.TestCase):
    """Full blend analysis pipeline."""

    def setUp(self):
        self.analyzer = PolymerBlendAnalyzer()

    def test_peo_electrolyte_analysis(self):
        """PEO electrolyte blend should be compatible."""
        analysis = self.analyzer.analyze_blend(STANDARD_PEO_ELECTROLYTE)
        self.assertTrue(analysis.compatible,
                        f"PEO electrolyte should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_pvdf_binder_analysis(self):
        """PVDF + NMP binder should be compatible."""
        analysis = self.analyzer.analyze_blend(STANDARD_PVDF_BINDER)
        self.assertTrue(analysis.compatible,
                        f"PVDF binder should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_pe_nylon_problematic(self):
        """HDPE + Nylon blend should show low compatibility."""
        analysis = self.analyzer.analyze_blend(PROBLEMATIC_PE_NYLON)
        self.assertLessEqual(analysis.overall_compatibility, 0.5,
                             f"PE+Nylon should show low compatibility "
                             f"(score={analysis.overall_compatibility:.3f})")

    def test_ptfe_blend_problematic(self):
        """PTFE + PS should show poor compatibility."""
        analysis = self.analyzer.analyze_blend(PROBLEMATIC_PTFE_BLEND)
        self.assertLess(analysis.overall_compatibility, 0.7,
                        f"PTFE+PS should show poor compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_engineering_blend_analysis(self):
        """PC + ABS engineering blend should work."""
        analysis = self.analyzer.analyze_blend(ENGINEERING_BLEND)
        self.assertGreater(analysis.overall_compatibility, 0.3)

    def test_cmcsb_binder_analysis(self):
        """CMC + SBR + Water binder system."""
        analysis = self.analyzer.analyze_blend(STANDARD_CMC_SBR_BINDER)
        self.assertIsNotNone(analysis)
        self.assertGreater(len(analysis.interfaces), 0)


class TestBlendAnalysisStructure(unittest.TestCase):
    """Verify analysis result structure."""

    def setUp(self):
        self.analyzer = PolymerBlendAnalyzer()
        self.analysis = self.analyzer.analyze_blend(STANDARD_PEO_ELECTROLYTE)

    def test_has_blend_name(self):
        self.assertEqual(self.analysis.blend_name, 'PEO Polymer Electrolyte')

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
        self.assertIn('blend_name', d)
        self.assertIn('overall_compatibility', d)
        self.assertIn('compatible', d)
        self.assertIn('interface_scores', d)

    def test_estimated_tg(self):
        """Blend with PEO (Tg=-60) + PMMA (Tg=105) should estimate Tg between them."""
        if self.analysis.estimated_tg_C is not None:
            self.assertGreaterEqual(self.analysis.estimated_tg_C, -60)
            self.assertLessEqual(self.analysis.estimated_tg_C, 105)


class TestConditionEffects(unittest.TestCase):
    """Verify operating condition modifiers work."""

    def setUp(self):
        self.validator = PolymerInterfaceValidator()

    def test_uv_exposure_penalizes_uv_sensitive(self):
        """UV exposure should penalize UV-sensitive polymers."""
        normal = self.validator.validate('HDPE', 'PP')
        uv_cond = PolymerConditions(uv_exposure=True)
        uv_result = self.validator.validate('HDPE', 'PP', uv_cond)
        # Both are UV-sensitive, so UV exposure should lower the score
        self.assertLessEqual(uv_result.total, normal.total + 0.01)

    def test_water_environment_penalizes_hygroscopic(self):
        """Aqueous environment should penalize hygroscopic materials."""
        normal = self.validator.validate('PA6', 'PET')
        water_cond = PolymerConditions(chemical_environment="water")
        water_result = self.validator.validate('PA6', 'PET', water_cond)
        self.assertLessEqual(water_result.total, normal.total + 0.01)

    def test_high_temp_effect(self):
        """High temperature should affect aging scores."""
        normal = self.validator.validate('PMMA', 'PS')
        hot_cond = PolymerConditions(temperature_C=150)
        hot_result = self.validator.validate('PMMA', 'PS', hot_cond)
        self.assertLessEqual(hot_result.total, normal.total + 0.01)


class TestWeightPresets(unittest.TestCase):
    """Verify weight presets work and produce different rankings."""

    def test_default_weights_valid(self):
        w = PolymerWeights.default()
        w.validate()  # Should not raise

    def test_blend_focus_valid(self):
        w = PolymerWeights.blend_focus()
        w.validate()

    def test_structural_focus_valid(self):
        w = PolymerWeights.structural_focus()
        w.validate()

    def test_durability_focus_valid(self):
        w = PolymerWeights.durability_focus()
        w.validate()

    def test_invalid_weights_raise(self):
        w = PolymerWeights(solubility=0.5, thermal=0.5, mechanical=0.5,
                           chemical_resistance=0.5, aging=0.5)
        with self.assertRaises(ValueError):
            w.validate()

    def test_blend_focus_emphasizes_solubility(self):
        w = PolymerWeights.blend_focus()
        self.assertEqual(w.solubility, 0.40)
        self.assertGreater(w.solubility, w.thermal)


class TestIntegration(unittest.TestCase):
    """Test KOMPOSOS integration layer."""

    def test_coherence_check(self):
        """Coherence check should work on blend analysis."""
        analyzer = PolymerBlendAnalyzer()
        analysis = analyzer.analyze_blend(STANDARD_PEO_ELECTROLYTE)
        coherence = check_blend_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)

    def test_categorical_analysis_pipeline(self):
        """Full categorical analysis should return valid dict."""
        result = run_polymer_categorical_analysis(STANDARD_PEO_ELECTROLYTE)
        self.assertIn('blend', result)
        self.assertIn('coherence', result)
        blend = result['blend']
        self.assertIn('overall_compatibility', blend)
        self.assertIn('compatible', blend)

    def test_compare_blends(self):
        """compare_blends should rank blends by compatibility."""
        analyzer = PolymerBlendAnalyzer()
        ranked = analyzer.compare_blends([
            STANDARD_PEO_ELECTROLYTE,
            STANDARD_PVDF_BINDER,
            PROBLEMATIC_PE_NYLON,
        ])
        self.assertEqual(len(ranked), 3)
        # Best should be first
        self.assertGreaterEqual(ranked[0].overall_compatibility,
                                ranked[-1].overall_compatibility)


class TestConvenienceFunction(unittest.TestCase):
    """Test the convenience validate_interface function."""

    def test_validate_interface_works(self):
        result = validate_interface('PVDF', 'PMMA')
        self.assertGreater(result.total, 0)
        self.assertIsInstance(result.viable, bool)

    def test_validate_interface_unknown_raises(self):
        with self.assertRaises(ValueError):
            validate_interface('PVDF', 'NONEXISTENT')


class TestValidateAllInterfaces(unittest.TestCase):
    """Test pairwise validation."""

    def test_validate_all(self):
        validator = PolymerInterfaceValidator()
        results = validator.validate_all_interfaces(['HDPE', 'PP', 'PS', 'PMMA'])
        # C(4,2) = 6 pairs
        self.assertEqual(len(results), 6)
        for key, score in results.items():
            self.assertGreaterEqual(score.total, 0.0)
            self.assertLessEqual(score.total, 1.0)


if __name__ == "__main__":
    unittest.main()
