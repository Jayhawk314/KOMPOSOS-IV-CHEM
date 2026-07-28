# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
MOF Bridge Module for KOMPOSOS-III
=====================================

Physical-chemical bridge for Metal-Organic Framework compatibility
and application screening, built on the same architecture as the
battery, polymer, ceramic, metal, semiconductor, and glass bridges.

MOF Bridge Mapping:
-------------------
Battery Bridge         ->  MOF Bridge
-------------------        --------------------
Material properties    ->  MOF properties (BET, pore vol, topology, stability)
Ion transport scoring  ->  Pore accessibility scoring
Echem stability scoring -> Chemical stability scoring
Interface scoring      ->  Thermal compatibility scoring
Mechanical scoring     ->  Mechanical compatibility scoring
Degradation penalty    ->  Application suitability scoring

Usage:
    from mof_bridge import MOFInterfaceValidator, ALL_MOFS, get_mof
    from mof_bridge import MOFConditions

    # Validate a MOF for a target application
    validator = MOFInterfaceValidator()
    result = validator.validate_mof('ZIF-8', target_molecule_diameter=3.4,
                                     operating_temp_C=200, operating_pressure_bar=10)
    print(f"Suitable: {result.suitable}, Score: {result.total:.2f}")
"""

from mof_bridge.material_properties import (
    MOF,
    MOFTopology,
    MOFApplication,
    ALL_MOFS,
    get_mof,
    get_mofs_by_topology,
    get_mofs_by_application,
)

from mof_bridge.interaction_scoring import (
    ScorerResult,
    score_pore_accessibility,
    score_chemical_stability,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_application_suitability,
    score_all,
)

from mof_bridge.interface_validator import (
    MOFInterfaceValidator,
    MOFInterfaceScore,
    MOFWeights,
    MOFConditions,
    validate_mof,
)

from mof_bridge.integration import (
    mof_to_stored_object,
    MOFMorphism,
    create_mof_morphism,
    build_mof_category,
)

__all__ = [
    # Material properties
    'MOF', 'MOFTopology', 'MOFApplication',
    'ALL_MOFS', 'get_mof', 'get_mofs_by_topology', 'get_mofs_by_application',

    # Scoring
    'ScorerResult', 'score_pore_accessibility', 'score_chemical_stability',
    'score_thermal_compatibility', 'score_mechanical_compatibility',
    'score_application_suitability', 'score_all',

    # Validation
    'MOFInterfaceValidator', 'MOFInterfaceScore', 'MOFWeights',
    'MOFConditions', 'validate_mof',

    # Integration
    'mof_to_stored_object', 'MOFMorphism',
    'build_mof_category',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
