# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Ceramic Bridge Module for KOMPOSOS-III
=========================================

Physical-chemical bridge for ceramic/composite interface engineering,
built on the same architecture as the metal bridge and polymer bridge.

Metal Bridge             ->  Ceramic Bridge
-------------------          --------------------
Metal properties        ->  Ceramic properties (Tm, CTE, KIC, crystal)
Galvanic compat.        ->  Sintering compatibility scoring
Thermal compat.         ->  CTE match scoring (expansion mismatch)
Mechanical compat.      ->  Mechanical compatibility scoring
Metallurgical compat.   ->  Chemical compatibility scoring
Corrosion penalty       ->  Degradation penalty scoring
Joint configuration     ->  Assembly configuration analysis

Usage:
    from ceramic_bridge import CeramicInterfaceValidator, CeramicAssemblyAnalyzer
    from ceramic_bridge import AssemblyConfiguration, ALUMINA_ZIRCONIA_COMPOSITE

    # Validate a single interface
    validator = CeramicInterfaceValidator()
    result = validator.validate('Al2O3', 'ZrO2_YSZ')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete assembly
    analyzer = CeramicAssemblyAnalyzer()
    analysis = analyzer.analyze_assembly(ALUMINA_ZIRCONIA_COMPOSITE)
    print(f"Assembly compatibility: {analysis.overall_compatibility:.2f}")
"""

from ceramic_bridge.material_properties import (
    CeramicMaterial,
    CeramicClass,
    CrystalSystem,
    CeramicFailureMode,
    ALL_CERAMICS,
    OXIDE_CERAMICS,
    CARBIDE_CERAMICS,
    NITRIDE_CERAMICS,
    GLASS_CERAMICS,
    BIOCERAMICS,
    PIEZOELECTRIC_CERAMICS,
    SOLID_ELECTROLYTE_CERAMICS,
    get_ceramic,
    get_ceramics_by_class,
)

from ceramic_bridge.interaction_scoring import (
    ScorerResult,
    score_sintering_compatibility,
    score_cte_match,
    score_mechanical_compatibility,
    score_chemical_compatibility,
    score_degradation_penalty,
    score_all,
)

from ceramic_bridge.interface_validator import (
    CeramicInterfaceValidator,
    CeramicInterfaceScore,
    CeramicWeights,
    CeramicConditions,
    validate_interface,
)

from ceramic_bridge.assembly_analyzer import (
    CeramicAssemblyAnalyzer,
    AssemblyConfiguration,
    AssemblyAnalysis,
    InterfaceResult,
    DegradationRisk,
    ALUMINA_ZIRCONIA_COMPOSITE,
    SIC_SI3N4_COMPOSITE,
    ALUMINA_SUBSTRATE,
    DENTAL_ZIRCONIA,
    SOLID_STATE_BATTERY,
    PROBLEMATIC_SIO2_MGO,
    PROBLEMATIC_LGPS_OXIDE,
    PROBLEMATIC_BIOGLASS_SIC,
)

from ceramic_bridge.integration import (
    ceramic_to_stored_object,
    CeramicMorphism,
    create_ceramic_morphism,
    build_ceramic_category,
    compute_ceramic_curvature,
    check_assembly_coherence,
    run_ceramic_categorical_analysis,
)

__all__ = [
    # Material properties
    'CeramicMaterial', 'CeramicClass', 'CrystalSystem', 'CeramicFailureMode',
    'ALL_CERAMICS', 'get_ceramic', 'get_ceramics_by_class',

    # Scoring
    'ScorerResult', 'score_sintering_compatibility', 'score_cte_match',
    'score_mechanical_compatibility', 'score_chemical_compatibility',
    'score_degradation_penalty', 'score_all',

    # Validation
    'CeramicInterfaceValidator', 'CeramicInterfaceScore', 'CeramicWeights',
    'CeramicConditions', 'validate_interface',

    # Assembly analysis
    'CeramicAssemblyAnalyzer', 'AssemblyConfiguration', 'AssemblyAnalysis',
    'ALUMINA_ZIRCONIA_COMPOSITE', 'PROBLEMATIC_SIO2_MGO',

    # Integration
    'ceramic_to_stored_object', 'CeramicMorphism',
    'build_ceramic_category', 'run_ceramic_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
