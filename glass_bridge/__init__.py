# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Glass Bridge Module for KOMPOSOS-III
=======================================

Physical-chemical bridge for glass interface/assembly engineering,
built on the same architecture as the ceramic bridge and semiconductor bridge.

Ceramic Bridge           ->  Glass Bridge
-------------------          --------------------
Ceramic properties      ->  Glass properties (Tg, CTE, nd, Vd, durability)
Sintering compat.       ->  Viscosity compatibility scoring
CTE match               ->  Thermal expansion match scoring
Mechanical compat.      ->  Mechanical compatibility scoring
Chemical compat.        ->  Chemical compatibility scoring
Degradation penalty     ->  Degradation penalty scoring
Assembly configuration  ->  Glass assembly configuration analysis

Usage:
    from glass_bridge import GlassInterfaceValidator, GlassAssemblyAnalyzer
    from glass_bridge import GlassAssemblyConfiguration, ACHROMATIC_DOUBLET

    # Validate a single interface
    validator = GlassInterfaceValidator()
    result = validator.validate('BK7', 'F2')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete assembly
    analyzer = GlassAssemblyAnalyzer()
    analysis = analyzer.analyze_assembly(ACHROMATIC_DOUBLET)
    print(f"Assembly compatibility: {analysis.overall_compatibility:.2f}")
"""

from glass_bridge.material_properties import (
    GlassMaterial,
    GlassClass,
    CompositionType,
    GlassFailureMode,
    ALL_GLASSES,
    SODA_LIME_GLASSES,
    BOROSILICATE_GLASSES,
    ALUMINOSILICATE_GLASSES,
    LEAD_GLASSES,
    FUSED_SILICA_GLASSES,
    OPTICAL_GLASSES,
    BIOACTIVE_GLASSES,
    CHALCOGENIDE_GLASSES,
    GLASS_CERAMIC_MATERIALS,
    PHOSPHATE_GLASSES,
    FLUORIDE_GLASSES,
    get_glass,
    get_glasses_by_class,
)

from glass_bridge.interaction_scoring import (
    ScorerResult,
    score_thermal_expansion_match,
    score_viscosity_compatibility,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    score_all,
)

from glass_bridge.interface_validator import (
    GlassInterfaceValidator,
    GlassInterfaceScore,
    GlassWeights,
    GlassConditions,
    validate_interface,
)

from glass_bridge.assembly_analyzer import (
    GlassAssemblyAnalyzer,
    GlassAssemblyConfiguration,
    GlassAssemblyAnalysis,
    InterfaceResult,
    DegradationRisk,
    ACHROMATIC_DOUBLET,
    BOROSILICATE_GRADED_SEAL,
    PRECISION_OPTICAL,
    SODA_LIME_ASSEMBLY,
    BIOACTIVE_ASSEMBLY,
    CHALCOGENIDE_ASSEMBLY,
    PROBLEMATIC_FUSED_SODALIME,
    PROBLEMATIC_CHALCO_BORO,
    PROBLEMATIC_ZBLAN_SODALIME,
    PROBLEMATIC_BIOGLASS_FUSED,
)

from glass_bridge.integration import (
    glass_to_stored_object,
    GlassMorphism,
    create_glass_morphism,
    build_glass_category,
    compute_glass_curvature,
    check_assembly_coherence,
    run_glass_categorical_analysis,
)

__all__ = [
    'GlassMaterial', 'GlassClass', 'CompositionType', 'GlassFailureMode',
    'ALL_GLASSES', 'get_glass', 'get_glasses_by_class',
    'ScorerResult', 'score_thermal_expansion_match', 'score_viscosity_compatibility',
    'score_mechanical_compatibility', 'score_chemical_compatibility',
    'score_degradation_penalty', 'score_all',
    'GlassInterfaceValidator', 'GlassInterfaceScore', 'GlassWeights',
    'GlassConditions', 'validate_interface',
    'GlassAssemblyAnalyzer', 'GlassAssemblyConfiguration', 'GlassAssemblyAnalysis',
    'ACHROMATIC_DOUBLET', 'PROBLEMATIC_FUSED_SODALIME',
    'glass_to_stored_object', 'GlassMorphism',
    'build_glass_category', 'run_glass_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
