# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Tests for known good/bad metal joint configurations.

Verifies the full pipeline: material properties -> scorers ->
validator -> joint analyzer for known real-world cases.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from metal_bridge.material_properties import get_metal
from metal_bridge.interface_validator import (
    MetalInterfaceValidator, MetalConditions, MetalWeights,
    validate_interface,
)
from metal_bridge.joint_analyzer import (
    MetalJointAnalyzer, JointConfiguration, JointAnalysis,
    STANDARD_SS_WELD, STEEL_STRUCTURE, ALUMINUM_AIRFRAME,
    TI_ASSEMBLY, BATTERY_CURRENT_COLLECTORS,
    PROBLEMATIC_CU_AL, PROBLEMATIC_MG_STEEL,
)
from metal_bridge.integration import (
    check_joint_coherence,
    run_metal_categorical_analysis,
)


class TestKnownGoodJoints(unittest.TestCase):
    """Known good joints should score above viability threshold."""

    def setUp(self):
        self.validator = MetalInterfaceValidator()

    def test_ss304_ss316_viable(self):
        """304SS + 316SS: same austenitic family."""
        result = self.validator.validate('SS_304', 'SS_316')
        self.assertTrue(result.viable, f"304SS+316SS should be viable (total={result.total:.3f})")

    def test_ti6al4v_cp_ti_viable(self):
        """Ti-6Al-4V + CP Ti: same base metal."""
        result = self.validator.validate('Ti6Al4V', 'CP_Ti_Gr2')
        self.assertTrue(result.viable, f"Ti6Al4V+CPTi should be viable (total={result.total:.3f})")

    def test_cu_ni_viable(self):
        """Cu + Ni: complete solid solution."""
        result = self.validator.validate('Cu', 'Ni')
        self.assertTrue(result.viable, f"Cu+Ni should be viable (total={result.total:.3f})")

    def test_al6061_al5052_viable(self):
        """6061 + 5052: both Al alloys."""
        result = self.validator.validate('Al_6061', 'Al_5052')
        self.assertTrue(result.viable, f"Al6061+Al5052 should be viable (total={result.total:.3f})")

    def test_inconel_625_718_viable(self):
        """Inconel 625 + 718: both Ni superalloys."""
        result = self.validator.validate('Inconel_625', 'Inconel_718')
        self.assertTrue(result.viable, f"Inconel625+718 should be viable (total={result.total:.3f})")


class TestKnownProblematicJoints(unittest.TestCase):
    """Known bad joints should flag issues."""

    def setUp(self):
        self.validator = MetalInterfaceValidator()

    def test_cu_al_low_score(self):
        """Cu + Al: large galvanic couple, intermetallics."""
        result = self.validator.validate('Cu', 'Al')
        self.assertLess(result.total, 0.65,
                        f"Cu+Al should score below 0.65 (total={result.total:.3f})")
        self.assertLess(result.galvanic_compatibility, 0.4,
                        "Cu+Al galvanic should be low")
        self.assertLess(result.corrosion_penalty, 0.5,
                        "Cu+Al corrosion should be low")

    def test_mg_cu_low_score(self):
        """Mg + Cu: extreme galvanic couple."""
        result = self.validator.validate('Mg', 'Cu')
        self.assertLess(result.total, 0.55,
                        f"Mg+Cu should score below 0.55 (total={result.total:.3f})")
        self.assertLess(result.galvanic_compatibility, 0.2,
                        "Mg+Cu galvanic should be very low")

    def test_mg_steel_low_score(self):
        """Mg + Steel: large galvanic couple."""
        result = self.validator.validate('Mg', 'Steel_1018')
        self.assertLess(result.total, 0.45,
                        f"Mg+Steel should score low (total={result.total:.3f})")

    def test_steel_al_galvanic(self):
        """Steel + Al: moderate galvanic couple."""
        result = self.validator.validate('Steel_1018', 'Al')
        self.assertLess(result.galvanic_compatibility, 0.8,
                        "Steel+Al galvanic should be below 0.8")
        self.assertLess(result.total, 0.7,
                        f"Steel+Al total should be moderate (total={result.total:.3f})")


class TestJointAnalysis(unittest.TestCase):
    """Full joint analysis pipeline."""

    def setUp(self):
        self.analyzer = MetalJointAnalyzer()

    def test_ss_weld_compatible(self):
        """304SS + 316SS weld should be compatible."""
        analysis = self.analyzer.analyze_joint(STANDARD_SS_WELD)
        self.assertTrue(analysis.compatible,
                        f"SS weld should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_steel_structure_compatible(self):
        """1018 + 4140 structure should be compatible."""
        analysis = self.analyzer.analyze_joint(STEEL_STRUCTURE)
        self.assertTrue(analysis.compatible,
                        f"Steel structure should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_al_airframe_compatible(self):
        """2024 + 7075 airframe should be compatible."""
        analysis = self.analyzer.analyze_joint(ALUMINUM_AIRFRAME)
        self.assertTrue(analysis.compatible,
                        f"Al airframe should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_ti_assembly_compatible(self):
        """Ti-6Al-4V + CP Ti should be compatible."""
        analysis = self.analyzer.analyze_joint(TI_ASSEMBLY)
        self.assertTrue(analysis.compatible,
                        f"Ti assembly should be compatible "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_cu_al_problematic(self):
        """Cu + Al joint should show below-average compatibility."""
        analysis = self.analyzer.analyze_joint(PROBLEMATIC_CU_AL)
        self.assertLess(analysis.overall_compatibility, 0.65,
                        f"Cu+Al should show below-average compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_mg_steel_problematic(self):
        """Mg + Steel should show very low compatibility."""
        analysis = self.analyzer.analyze_joint(PROBLEMATIC_MG_STEEL)
        self.assertLess(analysis.overall_compatibility, 0.45,
                        f"Mg+Steel should show low compatibility "
                        f"(score={analysis.overall_compatibility:.3f})")

    def test_battery_assembly_analysis(self):
        """Battery current collector assembly."""
        analysis = self.analyzer.analyze_joint(BATTERY_CURRENT_COLLECTORS)
        self.assertIsNotNone(analysis)
        self.assertGreater(len(analysis.interfaces), 0)


class TestJointAnalysisStructure(unittest.TestCase):
    """Verify analysis result structure."""

    def setUp(self):
        self.analyzer = MetalJointAnalyzer()
        self.analysis = self.analyzer.analyze_joint(STANDARD_SS_WELD)

    def test_has_joint_name(self):
        self.assertEqual(self.analysis.joint_name, '304SS + 316SS Weld')

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
        self.assertIn('joint_name', d)
        self.assertIn('overall_compatibility', d)
        self.assertIn('compatible', d)
        self.assertIn('interface_scores', d)


class TestConditionEffects(unittest.TestCase):
    """Verify operating condition modifiers work."""

    def setUp(self):
        self.validator = MetalInterfaceValidator()

    def test_marine_penalizes_galvanic(self):
        """Marine environment should penalize galvanic-susceptible pairs."""
        normal = self.validator.validate('Cu', 'Al')
        marine_cond = MetalConditions(environment="marine")
        marine_result = self.validator.validate('Cu', 'Al', marine_cond)
        self.assertLessEqual(marine_result.total, normal.total + 0.01)

    def test_high_temp_effect(self):
        """High temperature should affect corrosion and thermal scores."""
        normal = self.validator.validate('SS_304', 'Ni')
        hot_cond = MetalConditions(temperature_C=500)
        hot_result = self.validator.validate('SS_304', 'Ni', hot_cond)
        self.assertLessEqual(hot_result.total, normal.total + 0.01)

    def test_cyclic_loading_effect(self):
        """Cyclic loading should penalize fatigue-susceptible metals."""
        normal = self.validator.validate('Steel_1018', 'Steel_4140')
        cyclic_cond = MetalConditions(cyclic_loading=True)
        cyclic_result = self.validator.validate('Steel_1018', 'Steel_4140', cyclic_cond)
        self.assertLessEqual(cyclic_result.total, normal.total + 0.01)


class TestWeightPresets(unittest.TestCase):
    """Verify weight presets work and produce different rankings."""

    def test_default_weights_valid(self):
        w = MetalWeights.default()
        w.validate()

    def test_structural_focus_valid(self):
        w = MetalWeights.structural_focus()
        w.validate()

    def test_corrosion_focus_valid(self):
        w = MetalWeights.corrosion_focus()
        w.validate()

    def test_high_temp_focus_valid(self):
        w = MetalWeights.high_temp_focus()
        w.validate()

    def test_invalid_weights_raise(self):
        w = MetalWeights(galvanic=0.5, thermal=0.5, mechanical=0.5,
                         metallurgical=0.5, corrosion=0.5)
        with self.assertRaises(ValueError):
            w.validate()

    def test_corrosion_focus_emphasizes_galvanic(self):
        w = MetalWeights.corrosion_focus()
        self.assertEqual(w.galvanic, 0.35)
        self.assertGreater(w.galvanic, w.thermal)


class TestIntegration(unittest.TestCase):
    """Test KOMPOSOS integration layer."""

    def test_coherence_check(self):
        """Coherence check should work on joint analysis."""
        analyzer = MetalJointAnalyzer()
        analysis = analyzer.analyze_joint(STANDARD_SS_WELD)
        coherence = check_joint_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)

    def test_categorical_analysis_pipeline(self):
        """Full categorical analysis should return valid dict."""
        result = run_metal_categorical_analysis(STANDARD_SS_WELD)
        self.assertIn('joint', result)
        self.assertIn('coherence', result)
        joint = result['joint']
        self.assertIn('overall_compatibility', joint)
        self.assertIn('compatible', joint)

    def test_compare_joints(self):
        """compare_joints should rank joints by compatibility."""
        analyzer = MetalJointAnalyzer()
        ranked = analyzer.compare_joints([
            STANDARD_SS_WELD,
            ALUMINUM_AIRFRAME,
            PROBLEMATIC_CU_AL,
        ])
        self.assertEqual(len(ranked), 3)
        self.assertGreaterEqual(ranked[0].overall_compatibility,
                                ranked[-1].overall_compatibility)


class TestConvenienceFunction(unittest.TestCase):
    """Test the convenience validate_interface function."""

    def test_validate_interface_works(self):
        result = validate_interface('SS_304', 'SS_316')
        self.assertGreater(result.total, 0)
        self.assertIsInstance(result.viable, bool)

    def test_validate_interface_unknown_raises(self):
        with self.assertRaises(ValueError):
            validate_interface('SS_304', 'NONEXISTENT')


class TestValidateAllInterfaces(unittest.TestCase):
    """Test pairwise validation."""

    def test_validate_all(self):
        validator = MetalInterfaceValidator()
        results = validator.validate_all_interfaces(['SS_304', 'SS_316', 'Cu', 'Al'])
        # C(4,2) = 6 pairs
        self.assertEqual(len(results), 6)
        for key, score in results.items():
            self.assertGreaterEqual(score.total, 0.0)
            self.assertLessEqual(score.total, 1.0)


if __name__ == "__main__":
    unittest.main()
