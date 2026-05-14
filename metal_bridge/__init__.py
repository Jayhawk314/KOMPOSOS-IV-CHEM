# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Metal Bridge Module for KOMPOSOS-III
=========================================

Physical-chemical bridge for metal/alloy joint and interface engineering,
built on the same architecture as the polymer bridge.

Polymer Bridge          ->  Metal Bridge
-------------------         --------------------
Polymer properties     ->  Metal properties (Tm, CTE, galvanic, crystal)
Solubility scoring     ->  Galvanic compatibility scoring
Thermal compat.        ->  Thermal compatibility scoring (CTE mismatch)
Chemical resistance    ->  Metallurgical compatibility scoring
Mechanical compat.     ->  Mechanical compatibility scoring
Aging penalty          ->  Corrosion penalty scoring
Blend configuration    ->  Joint configuration analysis

Usage:
    from metal_bridge import MetalInterfaceValidator, MetalJointAnalyzer
    from metal_bridge import JointConfiguration, STANDARD_SS_WELD

    # Validate a single interface
    validator = MetalInterfaceValidator()
    result = validator.validate('SS_304', 'SS_316')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete joint
    analyzer = MetalJointAnalyzer()
    analysis = analyzer.analyze_joint(STANDARD_SS_WELD)
    print(f"Joint compatibility: {analysis.overall_compatibility:.2f}")
"""

from metal_bridge.material_properties import (
    MetalMaterial,
    MetalClass,
    CrystalSystem,
    MetalFailureMode,
    ALL_METALS,
    PURE_METALS,
    FERROUS_ALLOYS,
    ALUMINUM_ALLOYS,
    COPPER_ALLOYS,
    TITANIUM_ALLOYS,
    NICKEL_ALLOYS,
    BATTERY_METALS,
    get_metal,
    get_metals_by_class,
)

from metal_bridge.interaction_scoring import (
    ScorerResult,
    score_galvanic_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_metallurgical_compatibility,
    score_corrosion_penalty,
    score_all,
)

from metal_bridge.interface_validator import (
    MetalInterfaceValidator,
    MetalInterfaceScore,
    MetalWeights,
    MetalConditions,
    validate_interface,
)

from metal_bridge.joint_analyzer import (
    MetalJointAnalyzer,
    JointConfiguration,
    JointAnalysis,
    InterfaceResult,
    DegradationRisk,
    STANDARD_SS_WELD,
    STEEL_STRUCTURE,
    ALUMINUM_AIRFRAME,
    TI_ASSEMBLY,
    BATTERY_CURRENT_COLLECTORS,
    PROBLEMATIC_CU_AL,
    PROBLEMATIC_MG_STEEL,
)

from metal_bridge.integration import (
    metal_to_stored_object,
    MetalMorphism,
    create_metal_morphism,
    build_metal_category,
    compute_metal_curvature,
    check_joint_coherence,
    run_metal_categorical_analysis,
)

__all__ = [
    # Material properties
    'MetalMaterial', 'MetalClass', 'CrystalSystem', 'MetalFailureMode',
    'ALL_METALS', 'get_metal', 'get_metals_by_class',

    # Scoring
    'ScorerResult', 'score_galvanic_compatibility', 'score_thermal_compatibility',
    'score_mechanical_compatibility', 'score_metallurgical_compatibility',
    'score_corrosion_penalty', 'score_all',

    # Validation
    'MetalInterfaceValidator', 'MetalInterfaceScore', 'MetalWeights',
    'MetalConditions', 'validate_interface',

    # Joint analysis
    'MetalJointAnalyzer', 'JointConfiguration', 'JointAnalysis',
    'STANDARD_SS_WELD', 'STEEL_STRUCTURE', 'PROBLEMATIC_CU_AL',

    # Integration
    'metal_to_stored_object', 'MetalMorphism',
    'build_metal_category', 'run_metal_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
