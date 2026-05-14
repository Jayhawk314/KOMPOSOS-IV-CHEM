# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer Bridge Module for KOMPOSOS-III
=========================================

Physical-chemical bridge for polymer blend and interface engineering,
built on the same architecture as the battery bridge.

Battery Bridge          ->  Polymer Bridge
-------------------         --------------------
Material properties     ->  Polymer properties (Tg, Tm, Hansen, chi)
Ion transport scoring   ->  Solubility compatibility scoring (Hansen/chi)
Echem stability scoring ->  Thermal compatibility scoring (Tg/Tm/processing)
Interface compatibility ->  Chemical resistance scoring
Mechanical compat.      ->  Mechanical compatibility scoring
Degradation penalty     ->  Aging penalty scoring
Cell configuration      ->  Blend configuration analysis

Usage:
    from polymer_bridge import PolymerInterfaceValidator, PolymerBlendAnalyzer
    from polymer_bridge import BlendConfiguration, STANDARD_PEO_ELECTROLYTE

    # Validate a single interface
    validator = PolymerInterfaceValidator()
    result = validator.validate('PVDF', 'PMMA')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete blend
    analyzer = PolymerBlendAnalyzer()
    analysis = analyzer.analyze_blend(STANDARD_PEO_ELECTROLYTE)
    print(f"Blend compatibility: {analysis.overall_compatibility:.2f}")
"""

from polymer_bridge.material_properties import (
    PolymerMaterial,
    PolymerClass,
    PolymerStructure,
    PolymerFailureMode,
    HansenParameters,
    ALL_POLYMERS,
    THERMOPLASTIC_POLYMERS,
    BATTERY_POLYMERS,
    ELASTOMER_POLYMERS,
    HIGH_PERFORMANCE_POLYMERS,
    THERMOSET_POLYMERS,
    POLYMER_SOLVENTS,
    get_polymer,
    get_polymers_by_class,
)

from polymer_bridge.interaction_scoring import (
    ScorerResult,
    score_solubility_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_chemical_resistance,
    score_aging_penalty,
    score_all,
)

from polymer_bridge.interface_validator import (
    PolymerInterfaceValidator,
    PolymerInterfaceScore,
    PolymerWeights,
    PolymerConditions,
    validate_interface,
)

from polymer_bridge.blend_analyzer import (
    PolymerBlendAnalyzer,
    BlendConfiguration,
    BlendAnalysis,
    InterfaceResult,
    DegradationRisk,
    STANDARD_PEO_ELECTROLYTE,
    STANDARD_PVDF_BINDER,
    STANDARD_CMC_SBR_BINDER,
    ENGINEERING_BLEND,
    PROBLEMATIC_PE_NYLON,
    PROBLEMATIC_PTFE_BLEND,
)

from polymer_bridge.integration import (
    polymer_to_stored_object,
    PolymerMorphism,
    create_polymer_morphism,
    build_polymer_category,
    compute_polymer_curvature,
    check_blend_coherence,
    run_polymer_categorical_analysis,
)

__all__ = [
    # Material properties
    'PolymerMaterial', 'PolymerClass', 'PolymerStructure', 'PolymerFailureMode',
    'HansenParameters', 'ALL_POLYMERS', 'get_polymer', 'get_polymers_by_class',

    # Scoring
    'ScorerResult', 'score_solubility_compatibility', 'score_thermal_compatibility',
    'score_mechanical_compatibility', 'score_chemical_resistance',
    'score_aging_penalty', 'score_all',

    # Validation
    'PolymerInterfaceValidator', 'PolymerInterfaceScore', 'PolymerWeights',
    'PolymerConditions', 'validate_interface',

    # Blend analysis
    'PolymerBlendAnalyzer', 'BlendConfiguration', 'BlendAnalysis',
    'STANDARD_PEO_ELECTROLYTE', 'STANDARD_PVDF_BINDER',

    # Integration
    'polymer_to_stored_object', 'PolymerMorphism',
    'build_polymer_category', 'run_polymer_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
