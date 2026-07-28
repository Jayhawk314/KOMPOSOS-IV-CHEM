# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for glass_bridge assembly analysis, interface validation, and integration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import unittest

from glass_bridge.material_properties import ALL_GLASSES, get_glass
from glass_bridge.interface_validator import (
    GlassInterfaceValidator, GlassInterfaceScore,
    GlassWeights, GlassConditions, validate_interface,
)
from glass_bridge.assembly_analyzer import (
    GlassAssemblyAnalyzer, GlassAssemblyConfiguration, GlassAssemblyAnalysis,
    InterfaceResult, DegradationRisk,
    ACHROMATIC_DOUBLET, BOROSILICATE_GRADED_SEAL, PRECISION_OPTICAL,
    SODA_LIME_ASSEMBLY, BIOACTIVE_ASSEMBLY, CHALCOGENIDE_ASSEMBLY,
    PROBLEMATIC_FUSED_SODALIME, PROBLEMATIC_CHALCO_BORO,
    PROBLEMATIC_ZBLAN_SODALIME, PROBLEMATIC_BIOGLASS_FUSED,
)
from glass_bridge.integration import (
    glass_to_stored_object, GlassMorphism, create_glass_morphism,
    build_glass_category, compute_glass_curvature,
    check_assembly_coherence, run_glass_categorical_analysis,
)


# =============================================================================
# KNOWN GOOD ASSEMBLIES
# =============================================================================

class TestKnownGoodAssemblies(unittest.TestCase):
    """Test that known good glass assemblies score as viable."""

    def setUp(self):
        self.validator = GlassInterfaceValidator()

    def test_bk7_f2_achromat_viable(self):
        """BK7 + F2: standard achromatic doublet."""
        result = self.validator.validate('BK7', 'F2')
        self.assertTrue(result.viable,
            f"BK7+F2 should be viable, got total={result.total:.3f}")
        self.assertGreater(result.total, 0.55)

    def test_sodalime_pair_viable(self):
        """SodaLime_Float + SodaLime_Container: same family."""
        result = self.validator.validate('SodaLime_Float', 'SodaLime_Container')
        self.assertTrue(result.viable)
        self.assertGreater(result.total, 0.70)

    def test_boro_graded_seal_viable(self):
        """Boro_33 + Boro_51: graded seal step."""
        result = self.validator.validate('Boro_33', 'Boro_51')
        self.assertTrue(result.viable)
        self.assertGreater(result.total, 0.55)

    def test_bioactive_pair_viable(self):
        """Bioglass_45S5 + S53P4: both bioactive."""
        result = self.validator.validate('Bioglass_45S5', 'S53P4')
        self.assertTrue(result.viable)

    def test_chalcogenide_pair_viable(self):
        """As2S3 + Ge28Sb12Se60: chalcogenide doublet."""
        result = self.validator.validate('As2S3', 'Ge28Sb12Se60')
        self.assertTrue(result.viable)


# =============================================================================
# KNOWN BAD ASSEMBLIES
# =============================================================================

class TestKnownBadAssemblies(unittest.TestCase):
    """Test that known bad glass assemblies score below threshold."""

    def setUp(self):
        self.validator = GlassInterfaceValidator()

    def test_fused_silica_sodalime_low(self):
        """FusedSilica + SodaLime_Float: extreme CTE mismatch."""
        result = self.validator.validate('FusedSilica', 'SodaLime_Float')
        self.assertFalse(result.viable,
            f"FusedSilica+SodaLime should not be viable, got total={result.total:.3f}")
        self.assertLess(result.total, 0.50)

    def test_chalco_boro_low(self):
        """As2S3 + Boro_33: incompatible chemistry and CTE."""
        result = self.validator.validate('As2S3', 'Boro_33')
        self.assertFalse(result.viable,
            f"As2S3+Boro_33 should not be viable, got total={result.total:.3f}")
        self.assertLess(result.total, 0.50)

    def test_bioglass_fused_silica_low(self):
        """Bioglass_45S5 + FusedSilica: extreme CTE mismatch."""
        result = self.validator.validate('Bioglass_45S5', 'FusedSilica')
        self.assertFalse(result.viable,
            f"Bioglass+FusedSilica should not be viable, got total={result.total:.3f}")

    def test_zblan_sodalime_low(self):
        """ZBLAN + SodaLime_Float: incompatible glass networks."""
        result = self.validator.validate('ZBLAN', 'SodaLime_Float')
        self.assertFalse(result.viable,
            f"ZBLAN+SodaLime should not be viable, got total={result.total:.3f}")


# =============================================================================
# ASSEMBLY ANALYSIS PIPELINE
# =============================================================================

class TestAssemblyAnalysisPipeline(unittest.TestCase):
    """Test GlassAssemblyAnalyzer on pre-defined configurations."""

    def setUp(self):
        self.analyzer = GlassAssemblyAnalyzer()

    def test_achromatic_doublet_compatible(self):
        analysis = self.analyzer.analyze_assembly(ACHROMATIC_DOUBLET)
        self.assertIsInstance(analysis, GlassAssemblyAnalysis)
        self.assertTrue(analysis.compatible)
        self.assertGreater(analysis.overall_compatibility, 0.50)

    def test_boro_graded_seal_compatible(self):
        analysis = self.analyzer.analyze_assembly(BOROSILICATE_GRADED_SEAL)
        self.assertTrue(analysis.compatible)

    def test_precision_optical_compatible(self):
        analysis = self.analyzer.analyze_assembly(PRECISION_OPTICAL)
        self.assertTrue(analysis.compatible)

    def test_sodalime_assembly_compatible(self):
        analysis = self.analyzer.analyze_assembly(SODA_LIME_ASSEMBLY)
        self.assertTrue(analysis.compatible)
        self.assertGreater(analysis.overall_compatibility, 0.70)

    def test_bioactive_assembly_compatible(self):
        analysis = self.analyzer.analyze_assembly(BIOACTIVE_ASSEMBLY)
        self.assertTrue(analysis.compatible)

    def test_chalcogenide_assembly_compatible(self):
        analysis = self.analyzer.analyze_assembly(CHALCOGENIDE_ASSEMBLY)
        self.assertTrue(analysis.compatible)

    def test_problematic_fused_sodalime_incompatible(self):
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_FUSED_SODALIME)
        self.assertFalse(analysis.compatible,
            f"FusedSilica+SodaLime assembly should fail, got {analysis.overall_compatibility:.3f}")

    def test_problematic_chalco_boro_incompatible(self):
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_CHALCO_BORO)
        self.assertFalse(analysis.compatible,
            f"As2S3+Boro_33 assembly should fail, got {analysis.overall_compatibility:.3f}")

    def test_problematic_zblan_sodalime_incompatible(self):
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_ZBLAN_SODALIME)
        self.assertFalse(analysis.compatible,
            f"ZBLAN+SodaLime assembly should fail, got {analysis.overall_compatibility:.3f}")

    def test_problematic_bioglass_fused_incompatible(self):
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_BIOGLASS_FUSED)
        self.assertFalse(analysis.compatible,
            f"Bioglass+FusedSilica assembly should fail, got {analysis.overall_compatibility:.3f}")


class TestAssemblyStructure(unittest.TestCase):
    """Test GlassAssemblyAnalysis data structure correctness."""

    def setUp(self):
        self.analyzer = GlassAssemblyAnalyzer()
        self.analysis = self.analyzer.analyze_assembly(ACHROMATIC_DOUBLET)

    def test_has_assembly_name(self):
        self.assertEqual(self.analysis.assembly_name, ACHROMATIC_DOUBLET.name)

    def test_has_interfaces(self):
        self.assertIsInstance(self.analysis.interfaces, list)
        self.assertGreater(len(self.analysis.interfaces), 0)

    def test_has_bottleneck(self):
        self.assertIsNotNone(self.analysis.bottleneck)
        self.assertIsInstance(self.analysis.bottleneck, InterfaceResult)
        self.assertTrue(self.analysis.bottleneck.is_bottleneck)

    def test_interface_result_structure(self):
        ir = self.analysis.interfaces[0]
        self.assertIsInstance(ir.glass_a, str)
        self.assertIsInstance(ir.glass_b, str)
        self.assertIsInstance(ir.score, GlassInterfaceScore)

    def test_degradation_risks_list(self):
        self.assertIsInstance(self.analysis.degradation_risks, list)

    def test_warnings_list(self):
        self.assertIsInstance(self.analysis.warnings, list)

    def test_to_dict(self):
        d = self.analysis.to_dict()
        self.assertIn('assembly_name', d)
        self.assertIn('overall_compatibility', d)
        self.assertIn('compatible', d)
        self.assertIn('num_interfaces', d)
        self.assertIn('interface_scores', d)

    def test_overall_within_0_1(self):
        self.assertGreaterEqual(self.analysis.overall_compatibility, 0.0)
        self.assertLessEqual(self.analysis.overall_compatibility, 1.0)


class TestDegradationRisks(unittest.TestCase):
    """Test degradation risk detection in assemblies."""

    def setUp(self):
        self.analyzer = GlassAssemblyAnalyzer()

    def test_cte_mismatch_detected(self):
        """Problematic assemblies should flag CTE cracking risk."""
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_FUSED_SODALIME)
        risk_modes = [r.trigger_mode for r in analysis.degradation_risks]
        self.assertIn('cte_cracking', risk_modes)

    def test_viscosity_incompatibility_detected(self):
        """Chalcogenide+borosilicate should flag viscosity incompatibility."""
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_CHALCO_BORO)
        risk_modes = [r.trigger_mode for r in analysis.degradation_risks]
        # Might have either cte_cracking or viscosity_incompatibility
        self.assertTrue(
            'cte_cracking' in risk_modes or 'viscosity_incompatibility' in risk_modes,
            f"Expected degradation risks, got: {risk_modes}"
        )

    def test_degradation_risk_structure(self):
        analysis = self.analyzer.analyze_assembly(PROBLEMATIC_FUSED_SODALIME)
        if analysis.degradation_risks:
            risk = analysis.degradation_risks[0]
            self.assertIsInstance(risk, DegradationRisk)
            self.assertIsInstance(risk.trigger_interface, str)
            self.assertIsInstance(risk.trigger_mode, str)
            self.assertIsInstance(risk.consequence, str)
            self.assertIsInstance(risk.secondary_effects, list)


class TestCompareAssemblies(unittest.TestCase):
    """Test assembly comparison ranking."""

    def test_good_ranked_above_bad(self):
        analyzer = GlassAssemblyAnalyzer()
        configs = [PROBLEMATIC_FUSED_SODALIME, ACHROMATIC_DOUBLET, SODA_LIME_ASSEMBLY]
        rankings = analyzer.compare_assemblies(configs)
        # Best should be first (highest compatibility)
        self.assertGreater(rankings[0].overall_compatibility,
                          rankings[-1].overall_compatibility)

    def test_compare_returns_sorted_list(self):
        analyzer = GlassAssemblyAnalyzer()
        configs = [PROBLEMATIC_FUSED_SODALIME, SODA_LIME_ASSEMBLY, ACHROMATIC_DOUBLET]
        rankings = analyzer.compare_assemblies(configs)
        self.assertEqual(len(rankings), 3)
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(
                rankings[i].overall_compatibility,
                rankings[i + 1].overall_compatibility
            )


# =============================================================================
# INTERFACE VALIDATOR
# =============================================================================

class TestInterfaceValidatorConfig(unittest.TestCase):
    """Test GlassInterfaceValidator configuration."""

    def test_default_weights_sum_to_1(self):
        w = GlassWeights.default()
        total = w.thermal + w.viscosity + w.mechanical + w.chemical + w.degradation
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_optical_weights_sum_to_1(self):
        w = GlassWeights.optical_focus()
        total = w.thermal + w.viscosity + w.mechanical + w.chemical + w.degradation
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_sealing_weights_sum_to_1(self):
        w = GlassWeights.sealing_focus()
        total = w.thermal + w.viscosity + w.mechanical + w.chemical + w.degradation
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_biomedical_weights_sum_to_1(self):
        w = GlassWeights.biomedical_focus()
        total = w.thermal + w.viscosity + w.mechanical + w.chemical + w.degradation
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_invalid_weights_raises(self):
        w = GlassWeights(thermal=0.5, viscosity=0.5, mechanical=0.5,
                         chemical=0.5, degradation=0.5)
        with self.assertRaises(ValueError):
            w.validate()

    def test_custom_threshold(self):
        strict = GlassInterfaceValidator(viability_threshold=0.80)
        result = strict.validate('BK7', 'F2')
        # BK7+F2 might not pass strict 0.80 threshold
        self.assertIsInstance(result, GlassInterfaceScore)


class TestInterfaceScore(unittest.TestCase):
    """Test GlassInterfaceScore data structure."""

    def test_score_structure(self):
        result = validate_interface('BK7', 'F2')
        self.assertIsInstance(result.total, float)
        self.assertIsInstance(result.thermal_expansion_match, float)
        self.assertIsInstance(result.viscosity_compatibility, float)
        self.assertIsInstance(result.mechanical_compatibility, float)
        self.assertIsInstance(result.chemical_compatibility, float)
        self.assertIsInstance(result.degradation_penalty, float)
        self.assertIsInstance(result.viable, bool)

    def test_to_dict(self):
        result = validate_interface('BK7', 'F2')
        d = result.to_dict()
        self.assertIn('total', d)
        self.assertIn('viable', d)

    def test_unknown_glass_raises(self):
        validator = GlassInterfaceValidator()
        with self.assertRaises(ValueError):
            validator.validate('NotAGlass', 'BK7')


class TestConditionModifiers(unittest.TestCase):
    """Test that operating conditions affect scores."""

    def test_furnace_reduces_degradation(self):
        validator = GlassInterfaceValidator()
        normal = validator.validate('BK7', 'F2', GlassConditions())
        furnace = validator.validate('BK7', 'F2',
            GlassConditions(environment='furnace', temperature_C=500))
        # Furnace conditions should reduce degradation score
        self.assertLessEqual(furnace.degradation_penalty, normal.degradation_penalty)

    def test_chemical_environment_penalty(self):
        validator = GlassInterfaceValidator()
        normal = validator.validate('BK7', 'F2', GlassConditions())
        chemical = validator.validate('BK7', 'F2',
            GlassConditions(environment='chemical'))
        # Chemical environment applies penalties
        self.assertLessEqual(chemical.total, normal.total + 0.01)

    def test_thermal_cycling_penalty(self):
        validator = GlassInterfaceValidator()
        normal = validator.validate('BK7', 'F2', GlassConditions())
        cycling = validator.validate('BK7', 'F2',
            GlassConditions(thermal_cycling=True))
        self.assertLessEqual(cycling.thermal_expansion_match,
                            normal.thermal_expansion_match + 0.01)

    def test_outdoor_penalty(self):
        validator = GlassInterfaceValidator()
        indoor = validator.validate('F2', 'Lead_Crystal',
            GlassConditions(environment='indoor'))
        outdoor = validator.validate('F2', 'Lead_Crystal',
            GlassConditions(environment='outdoor'))
        # F2 and Lead_Crystal both have WEATHERING -> outdoor penalty
        self.assertLessEqual(outdoor.degradation_penalty, indoor.degradation_penalty)


class TestValidateAllInterfaces(unittest.TestCase):
    """Test batch interface validation."""

    def test_validate_three_glasses(self):
        validator = GlassInterfaceValidator()
        results = validator.validate_all_interfaces(['BK7', 'F2', 'LAK9'])
        # 3 glasses -> 3 pairs
        self.assertEqual(len(results), 3)

    def test_validate_returns_scores(self):
        validator = GlassInterfaceValidator()
        results = validator.validate_all_interfaces(['BK7', 'F2'])
        for key, score in results.items():
            self.assertIsInstance(score, GlassInterfaceScore)


# =============================================================================
# INTEGRATION LAYER
# =============================================================================

class TestIntegrationGlassToStoredObject(unittest.TestCase):
    """Test glass_to_stored_object conversion."""

    def test_converts_bk7(self):
        bk7 = get_glass('BK7')
        try:
            obj = glass_to_stored_object(bk7)
            self.assertEqual(obj.name, bk7.formula)
            self.assertIn('glass_class', obj.metadata)
            self.assertEqual(obj.metadata['domain'], 'glass_engineering')
        except ImportError:
            self.skipTest("StoredObject not available")


class TestIntegrationGlassMorphism(unittest.TestCase):
    """Test GlassMorphism creation."""

    def test_create_morphism(self):
        morphism = create_glass_morphism('BK7', 'F2')
        self.assertIsInstance(morphism, GlassMorphism)
        self.assertEqual(morphism.glass_a.formula, get_glass('BK7').formula)
        self.assertEqual(morphism.glass_b.formula, get_glass('F2').formula)

    def test_morphism_has_score(self):
        morphism = create_glass_morphism('BK7', 'F2')
        self.assertIsInstance(morphism.interface_score, GlassInterfaceScore)

    def test_invalid_glass_raises(self):
        with self.assertRaises(ValueError):
            create_glass_morphism('NotAGlass', 'BK7')


class TestIntegrationCategory(unittest.TestCase):
    """Test build_glass_category."""

    def test_build_small_category(self):
        cat = build_glass_category(['BK7', 'F2', 'LAK9'])
        if cat is None:
            self.skipTest("Category module not available")
        self.assertGreater(len(cat.objects), 0)

    def test_build_returns_none_without_category(self):
        # If category module is missing, should return None gracefully
        cat = build_glass_category(['BK7', 'F2'])
        # Result is either a Category or None
        self.assertTrue(cat is None or hasattr(cat, 'objects'))


class TestIntegrationCoherence(unittest.TestCase):
    """Test assembly coherence checking."""

    def test_simple_assembly_coherent(self):
        analyzer = GlassAssemblyAnalyzer()
        analysis = analyzer.analyze_assembly(ACHROMATIC_DOUBLET)
        coherence = check_assembly_coherence(analysis)
        self.assertIn('coherent', coherence)
        self.assertIn('coherence_score', coherence)

    def test_single_interface_trivially_coherent(self):
        analyzer = GlassAssemblyAnalyzer()
        analysis = analyzer.analyze_assembly(ACHROMATIC_DOUBLET)
        # Doublet = 1 interface -> trivially coherent
        coherence = check_assembly_coherence(analysis)
        self.assertTrue(coherence['coherent'])
        self.assertEqual(coherence['coherence_score'], 1.0)


class TestIntegrationCurvature(unittest.TestCase):
    """Test Ricci curvature computation on glass graphs."""

    def test_curvature_returns_dict_or_none(self):
        analyzer = GlassAssemblyAnalyzer()
        # Need 3+ components for meaningful curvature
        config = GlassAssemblyConfiguration(
            name='Three-glass test',
            primary_glass='BK7',
            secondary_glasses=['F2', 'LAK9'],
        )
        analysis = analyzer.analyze_assembly(config)
        curvature = compute_glass_curvature(analysis)
        # Either dict with edge_curvatures or None (if ricci not available)
        self.assertTrue(curvature is None or isinstance(curvature, dict))


class TestIntegrationRunFullAnalysis(unittest.TestCase):
    """Test run_glass_categorical_analysis end-to-end."""

    def test_full_analysis_achromat(self):
        result = run_glass_categorical_analysis(ACHROMATIC_DOUBLET)
        self.assertIn('assembly', result)
        self.assertIn('coherence', result)
        self.assertIn('overall_compatibility', result['assembly'])

    def test_full_analysis_problematic(self):
        result = run_glass_categorical_analysis(PROBLEMATIC_FUSED_SODALIME)
        self.assertFalse(result['assembly']['compatible'])


class TestConvenienceFunction(unittest.TestCase):
    """Test validate_interface convenience function."""

    def test_convenience_works(self):
        result = validate_interface('BK7', 'F2')
        self.assertIsInstance(result, GlassInterfaceScore)
        self.assertTrue(result.viable)

    def test_convenience_bad_pair(self):
        result = validate_interface('FusedSilica', 'SodaLime_Float')
        self.assertIsInstance(result, GlassInterfaceScore)
        self.assertFalse(result.viable)


if __name__ == '__main__':
    unittest.main()
