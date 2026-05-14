# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for known good/bad ceramic assembly configurations.

Verifies the full pipeline: material properties -> scorers ->
validator -> assembly analyzer for known real-world cases.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from ceramic_bridge.material_properties import get_ceramic
from ceramic_bridge.interface_validator import (
    CeramicInterfaceValidator, CeramicConditions, CeramicWeights,
    validate_interface,
)
from ceramic_bridge.assembly_analyzer import (
    CeramicAssemblyAnalyzer, AssemblyConfiguration, AssemblyAnalysis,
    ALUMINA_ZIRCONIA_COMPOSITE, SIC_SI3N4_COMPOSITE,
    ALUMINA_SUBSTRATE, DENTAL_ZIRCONIA, SOLID_STATE_BATTERY,
    PROBLEMATIC_SIO2_MGO, PROBLEMATIC_LGPS_OXIDE, PROBLEMATIC_BIOGLASS_SIC,
)
from ceramic_bridge.integration import (
    check_assembly_coherence,
    run_ceramic_categorical_analysis,
)


class TestKnownGoodComposites(unittest.TestCase):
    """Known good composites should score above viability threshold."""

    def setUp(self):
        self.validator = CeramicInterfaceValidator()

    def test_al2o3_zro2_viable(self):
        """Al2O3 + ZrO2_YSZ: standard toughened composite."""
        result = self.validator.validate('Al2O3', 'ZrO2_YSZ')
        self.assertTrue(result.viable, f"Al2O3+ZrO2 should be viable (total={result.total:.3f})")

    def test_sic_si3n4_viable(self):
        """SiC + Si3N4: non-oxide composite."""
        result = self.validator.validate('SiC', 'Si3N4')
        self.assertTrue(result.viable, f"SiC+Si3N4 should be viable (total={result.total:.3f})")

    def test_al2o3_mullite_viable(self):
        """Al2O3 + Mullite: refractory composite."""
        result = self.validator.validate('Al2O3', 'Mullite')
        self.assertTrue(result.viable, f"Al2O3+Mullite should be viable (total={result.total:.3f})")

    def test_al2o3_spinel_viable(self):
        """Al2O3 + Spinel: oxide composite."""
        result = self.validator.validate('Al2O3', 'Spinel')
        self.assertTrue(result.viable, f"Al2O3+Spinel should be viable (total={result.total:.3f})")

    def test_ha_tcp_viable(self):
        """Hydroxyapatite + TCP: bioceramic composite."""
        result = self.validator.validate('Hydroxyapatite', 'TCP')
        self.assertTrue(result.viable, f"HA+TCP should be viable (total={result.total:.3f})")


class TestKnownProblematicComposites(unittest.TestCase):
    """Known bad composites should flag issues."""

    def setUp(self):
        self.validator = CeramicInterfaceValidator()

    def test_sio2_mgo_low_score(self):
        """SiO2 + MgO: extreme CTE mismatch + hygroscopic."""
        result = self.validator.validate('SiO2', 'MgO')
        self.assertLess(result.total, 0.55,
                        f"SiO2+MgO should score low (total={result.total:.3f})")
        self.assertLess(result.cte_match, 0.2,
                        "SiO2+MgO CTE match should be very low")

    def test_lgps_al2o3_low_score(self):
        """LGPS + Al2O3: decomposition + mechanical mismatch."""
        result = self.validator.validate('LGPS', 'Al2O3')
        self.assertLess(result.total, 0.55,
                        f"LGPS+Al2O3 should score low (total={result.total:.3f})")
        self.assertLess(result.mechanical_compatibility, 0.4,
                        "LGPS+Al2O3 mechanical should be low")

    def test_bioglass_sic_low_score(self):
        """Bioglass + SiC: incompatible sintering."""
        result = self.validator.validate('Bioglass', 'SiC')
        self.assertLess(result.total, 0.55,
                        f"Bioglass+SiC should score low (total={result.total:.3f})")
        self.assertLess(result.sintering_compatibility, 0.3,
                        "Bioglass+SiC sintering should be very low")


class TestAssemblyAnalysis(unittest.TestCase):
    """Full assembly analysis pipeline."""

    def setUp(self):
        self.analyzer = CeramicAssemblyAnalyzer()

    def test_alumina_zirconia_compatible(self):
        """Al2O3 + ZrO2 composite should be compatible."""
        analysis = self.analyzer.analyze_assembly(ALUMINA_ZIRCONIA_COMPOSITE)
        self.assertTrue(analysis.compatible,
                        f"Al2O3+ZrO2 should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_sic_si3n4_compatible(self):
        """SiC + Si3N4 should be compatible."""
        analysis = self.analyzer.analyze_assembly(SIC_SI3N4_COMPOSITE)
        self.assertTrue(analysis.compatible,
                        f"SiC+Si3N4 should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_alumina_substrate_compatible(self):
        """Al2O3 + TiN coating should be compatible."""
        analysis = self.analyzer.analyze_assembly(ALUMINA_SUBSTRATE)
        self.assertTrue(analysis.compatible,
                        f"Al2O3+TiN should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_dental_zirconia_compatible(self):
        """Dental ZrO2 + Al2O3 should be compatible."""
        analysis = self.analyzer.analyze_assembly(DENTAL_ZIRCONIA)
        self.assertTrue(analysis.compatible,
                        f"Dental zirconia should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_sio2_mgo_problematic(self):
        """SiO2 + MgO should show low compatibility."""
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_SIO2_MGO)
        self.assertLess(analysis.overall_compatibility, 0.55,
                        f"SiO2+MgO should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_lgps_oxide_problematic(self):
        """LGPS + Al2O3 should show low compatibility."""
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_LGPS_OXIDE)
        self.assertLess(analysis.overall_compatibility, 0.55,
                        f"LGPS+Al2O3 should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_bioglass_sic_problematic(self):
        """Bioglass + SiC should show low compatibility."""
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_BIOGLASS_SIC)
        self.assertLess(analysis.overall_compatibility, 0.55,
                        f"Bioglass+SiC should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_solid_state_battery_analysis(self):
        """Solid-state battery assembly."""
        analysis = self.analyzer.analyze_assembly(SOLID_STATE_BATTERY)
        self.assertIsNotNone(analysis)
        self.assertGreater(len(analysis.interfaces), 0)


class TestAssemblyAnalysisStructure(unittest.TestCase):
    """Verify analysis result structure."""

    def setUp(self):
        self.analyzer = CeramicAssemblyAnalyzer()
        self.analysis = self.analyzer.analyze_assembly(ALUMINA_ZIRCONIA_COMPOSITE)

    def test_has_assembly_name(self):
        self.assertEqual(self.analysis.assembly_name, 'Alumina + Zirconia Composite (ZTA)')

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
        self.assertIn('assembly_name', d)
        self.assertIn('overall_compatibility', d)
        self.assertIn('compatible', d)
        self.assertIn('interface_scores', d)


class TestConditionEffects(unittest.TestCase):
    """Verify operating condition modifiers work."""

    def setUp(self):
        self.validator = CeramicInterfaceValidator()

    def test_corrosive_penalizes(self):
        """Corrosive environment should penalize degradation."""
        normal = self.validator.validate('Al2O3', 'ZrO2_YSZ')
        corr_cond = CeramicConditions(environment="corrosive")
        corr_result = self.validator.validate('Al2O3', 'ZrO2_YSZ', corr_cond)
        self.assertLessEqual(corr_result.total, normal.total + 0.01)

    def test_high_temp_effect(self):
        """High temperature should affect CTE and degradation scores."""
        normal = self.validator.validate('Al2O3', 'SiC')
        hot_cond = CeramicConditions(temperature_C=800)
        hot_result = self.validator.validate('Al2O3', 'SiC', hot_cond)
        self.assertLessEqual(hot_result.total, normal.total + 0.01)

    def test_thermal_cycling_effect(self):
        """Thermal cycling should penalize thermal-shock-susceptible ceramics."""
        normal = self.validator.validate('Al2O3', 'MgO')
        cycle_cond = CeramicConditions(thermal_cycling=True)
        cycle_result = self.validator.validate('Al2O3', 'MgO', cycle_cond)
        self.assertLessEqual(cycle_result.total, normal.total + 0.01)


class TestWeightPresets(unittest.TestCase):
    """Verify weight presets work and produce different rankings."""

    def test_default_weights_valid(self):
        w = CeramicWeights.default()
        w.validate()

    def test_structural_focus_valid(self):
        w = CeramicWeights.structural_focus()
        w.validate()

    def test_thermal_focus_valid(self):
        w = CeramicWeights.thermal_focus()
        w.validate()

    def test_biomedical_focus_valid(self):
        w = CeramicWeights.biomedical_focus()
        w.validate()

    def test_invalid_weights_raise(self):
        w = CeramicWeights(sintering=0.5, cte=0.5, mechanical=0.5,
                           chemical=0.5, degradation=0.5)
        with self.assertRaises(ValueError):
            w.validate()

    def test_thermal_focus_emphasizes_cte(self):
        w = CeramicWeights.thermal_focus()
        self.assertEqual(w.cte, 0.35)
        self.assertGreater(w.cte, w.sintering)


class TestIntegration(unittest.TestCase):
    """Test KOMPOSOS integration layer."""

    def test_coherence_check(self):
        """Coherence check should work on assembly analysis."""
        analyzer = CeramicAssemblyAnalyzer()
        analysis = analyzer.analyze_assembly(ALUMINA_ZIRCONIA_COMPOSITE)
        coherence = check_assembly_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)

    def test_categorical_analysis_pipeline(self):
        """Full categorical analysis should return valid dict."""
        result = run_ceramic_categorical_analysis(ALUMINA_ZIRCONIA_COMPOSITE)
        self.assertIn('assembly', result)
        self.assertIn('coherence', result)
        assembly = result['assembly']
        self.assertIn('overall_compatibility', assembly)
        self.assertIn('compatible', assembly)

    def test_compare_assemblies(self):
        """compare_assemblies should rank by compatibility."""
        analyzer = CeramicAssemblyAnalyzer()
        ranked = analyzer.compare_assemblies([
            ALUMINA_ZIRCONIA_COMPOSITE,
            ALUMINA_SUBSTRATE,
            PROBLEMATIC_SIO2_MGO,
        ])
        self.assertEqual(len(ranked), 3)
        self.assertGreaterEqual(ranked[0].overall_compatibility,
                                ranked[-1].overall_compatibility)


class TestConvenienceFunction(unittest.TestCase):
    """Test the convenience validate_interface function."""

    def test_validate_interface_works(self):
        result = validate_interface('Al2O3', 'ZrO2_YSZ')
        self.assertGreater(result.total, 0)
        self.assertIsInstance(result.viable, bool)

    def test_validate_interface_unknown_raises(self):
        with self.assertRaises(ValueError):
            validate_interface('Al2O3', 'NONEXISTENT')


class TestValidateAllInterfaces(unittest.TestCase):
    """Test pairwise validation."""

    def test_validate_all(self):
        validator = CeramicInterfaceValidator()
        results = validator.validate_all_interfaces(['Al2O3', 'ZrO2_YSZ', 'SiC', 'Si3N4'])
        # C(4,2) = 6 pairs
        self.assertEqual(len(results), 6)
        for key, score in results.items():
            self.assertGreaterEqual(score.total, 0.0)
            self.assertLessEqual(score.total, 1.0)


if __name__ == "__main__":
    unittest.main()
