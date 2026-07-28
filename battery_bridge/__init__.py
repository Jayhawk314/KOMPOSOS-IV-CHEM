# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Battery Bridge Module for KOMPOSOS-III
========================================

Physical-chemical bridge for battery and materials engineering,
built on the same architecture as the protein contact bridge.

Protein Bridge         ->  Battery Bridge
-------------------        --------------------
Amino acid properties  ->  Material properties (cathodes, anodes, electrolytes)
H-bond scoring         ->  Ion transport scoring
Salt bridge scoring    ->  Electrochemical stability scoring
Hydrophobic scoring    ->  Interface compatibility scoring
Van der Waals scoring  ->  Mechanical compatibility scoring
Electrostatic penalty  ->  Degradation penalty
Contact validation     ->  Interface validation
Protein structure      ->  Cell configuration analysis

Usage:
    from battery_bridge import BatteryInterfaceValidator, BatteryFlowAnalyzer
    from battery_bridge import CellConfiguration, STANDARD_LFP_CELL

    # Validate a single interface
    validator = BatteryInterfaceValidator()
    result = validator.validate('LFP', 'EC')
    print(f"Viable: {result.viable}, Score: {result.total:.2f}")

    # Analyze a complete cell
    analyzer = BatteryFlowAnalyzer()
    analysis = analyzer.analyze_cell(STANDARD_LFP_CELL)
    print(f"Cell viability: {analysis.overall_viability:.2f}")
"""

from battery_bridge.material_properties import (
    BatteryMaterial,
    MaterialClass,
    CrystalStructure,
    FailureMode,
    VoltageWindow,
    ALL_MATERIALS,
    CATHODE_MATERIALS,
    ANODE_MATERIALS,
    ELECTROLYTE_SOLVENTS,
    ELECTROLYTE_SALTS,
    SOLID_ELECTROLYTES,
    IONS,
    get_material,
    get_materials_by_class,
)

from battery_bridge.interaction_scoring import (
    ScorerResult,
    score_ion_transport,
    score_electrochemical_stability,
    score_interface_compatibility,
    score_mechanical_compatibility,
    score_degradation_penalty,
    score_all,
)

from battery_bridge.interface_validator import (
    BatteryInterfaceValidator,
    InterfaceScore,
    InterfaceWeights,
    InterfaceConditions,
    validate_interface,
)

from battery_bridge.battery_flow import (
    BatteryFlowAnalyzer,
    CellConfiguration,
    CellAnalysis,
    InterfaceResult,
    DegradationStep,
    STANDARD_LFP_CELL,
    STANDARD_NMC811_CELL,
    SOLID_STATE_CELL,
    PROBLEMATIC_SI_CELL,
    PROBLEMATIC_LGPS_CELL,
)

from battery_bridge.integration import (
    material_to_stored_object,
    InterfaceMorphism,
    create_interface_morphism,
    build_battery_category,
    compute_battery_curvature,
    analyze_cycling_topology,
    check_thermodynamic_coherence,
    run_battery_categorical_analysis,
)

__all__ = [
    # Material properties
    'BatteryMaterial', 'MaterialClass', 'CrystalStructure', 'FailureMode',
    'VoltageWindow', 'ALL_MATERIALS', 'get_material', 'get_materials_by_class',

    # Scoring
    'ScorerResult', 'score_ion_transport', 'score_electrochemical_stability',
    'score_interface_compatibility', 'score_mechanical_compatibility',
    'score_degradation_penalty', 'score_all',

    # Validation
    'BatteryInterfaceValidator', 'InterfaceScore', 'InterfaceWeights',
    'InterfaceConditions', 'validate_interface',

    # Flow analysis
    'BatteryFlowAnalyzer', 'CellConfiguration', 'CellAnalysis',
    'STANDARD_LFP_CELL', 'STANDARD_NMC811_CELL',

    # Integration
    'material_to_stored_object', 'InterfaceMorphism',
    'build_battery_category', 'run_battery_categorical_analysis',
]

__version__ = '1.0.0'
__author__ = 'James Ray Hawkins'
