# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Semiconductor Bridge Module for KOMPOSOS-III
===============================================

Physical-chemical bridge for semiconductor heterostructure engineering,
built on the same architecture as the ceramic bridge and metal bridge.

Ceramic Bridge            ->  Semiconductor Bridge
-------------------           -------------------------
Ceramic properties       ->  Semiconductor properties (Eg, lattice, mobility)
Sintering compat.        ->  Lattice match scoring
CTE match                ->  Band alignment scoring
Mechanical compat.       ->  Thermal compatibility scoring
Chemical compat.         ->  Process compatibility scoring
Degradation penalty      ->  Degradation penalty scoring
Assembly configuration   ->  Heterostructure configuration analysis

Usage:
    from semiconductor_bridge import SemiconductorInterfaceValidator
    from semiconductor_bridge import HeterostructureAnalyzer, GAAS_ALGAAS_HEMT

    # Validate a single interface
    validator = SemiconductorInterfaceValidator()
    result = validator.validate('GaAs', 'AlGaAs')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete heterostructure
    analyzer = HeterostructureAnalyzer()
    analysis = analyzer.analyze_heterostructure(GAAS_ALGAAS_HEMT)
    print(f"Compatibility: {analysis.overall_compatibility:.2f}")
"""

from semiconductor_bridge.material_properties import (
    SemiconductorMaterial,
    SemiconductorClass,
    CrystalSystem,
    BandGapType,
    SemiconductorFailureMode,
    ALL_SEMICONDUCTORS,
    ELEMENTAL_SEMICONDUCTORS,
    IV_IV_SEMICONDUCTORS,
    III_V_SEMICONDUCTORS,
    NITRIDE_SEMICONDUCTORS,
    II_VI_SEMICONDUCTORS,
    OXIDE_SEMICONDUCTORS,
    TWO_D_SEMICONDUCTORS,
    THERMOELECTRIC_SEMICONDUCTORS,
    get_semiconductor,
    get_semiconductors_by_class,
)

from semiconductor_bridge.interaction_scoring import (
    ScorerResult,
    score_lattice_match,
    score_band_alignment,
    score_thermal_compatibility,
    score_process_compatibility,
    score_degradation_penalty,
    score_all,
)

from semiconductor_bridge.interface_validator import (
    SemiconductorInterfaceValidator,
    SemiconductorInterfaceScore,
    SemiconductorWeights,
    SemiconductorConditions,
    validate_interface,
)

from semiconductor_bridge.heterostructure_analyzer import (
    HeterostructureAnalyzer,
    HeterostructureConfiguration,
    HeterostructureAnalysis,
    InterfaceResult,
    DegradationRisk,
    GAAS_ALGAAS_HEMT,
    INGAAS_INP_TELECOM,
    GAN_ALGAN_POWER,
    SI_SIGE_BICMOS,
    MOS2_WS2_2D,
    SIC_GAN_POWER,
    PROBLEMATIC_GAAS_SI,
    PROBLEMATIC_INAS_GAP,
    PROBLEMATIC_GAN_GAAS,
    PROBLEMATIC_INSB_SI,
)

from semiconductor_bridge.integration import (
    semiconductor_to_stored_object,
    SemiconductorMorphism,
    create_semiconductor_morphism,
    build_semiconductor_category,
    compute_semiconductor_curvature,
    check_heterostructure_coherence,
    run_semiconductor_categorical_analysis,
)

__all__ = [
    # Material properties
    'SemiconductorMaterial', 'SemiconductorClass', 'CrystalSystem', 'BandGapType',
    'SemiconductorFailureMode', 'ALL_SEMICONDUCTORS', 'get_semiconductor',
    'get_semiconductors_by_class',

    # Scoring
    'ScorerResult', 'score_lattice_match', 'score_band_alignment',
    'score_thermal_compatibility', 'score_process_compatibility',
    'score_degradation_penalty', 'score_all',

    # Validation
    'SemiconductorInterfaceValidator', 'SemiconductorInterfaceScore',
    'SemiconductorWeights', 'SemiconductorConditions', 'validate_interface',

    # Heterostructure analysis
    'HeterostructureAnalyzer', 'HeterostructureConfiguration', 'HeterostructureAnalysis',
    'GAAS_ALGAAS_HEMT', 'PROBLEMATIC_GAAS_SI',

    # Integration
    'semiconductor_to_stored_object', 'SemiconductorMorphism',
    'build_semiconductor_category', 'run_semiconductor_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
