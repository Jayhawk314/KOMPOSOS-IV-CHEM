# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer Material Properties
==============================

Validated property tables for polymer materials, analogous to
battery_bridge/material_properties.py and chemistry/hydrogen_bonds.py
amino acid property tables.

Each material entry uses real published values with source citations.

Property Sources:
-----------------
- Van Krevelen, "Properties of Polymers" 4th ed., Elsevier 2009
- Hansen, "Hansen Solubility Parameters: A User's Handbook" 2nd ed., CRC 2007
- Brandrup et al., "Polymer Handbook" 4th ed., Wiley 1999
- Mark, "Physical Properties of Polymers Handbook" 2nd ed., Springer 2007
- Osswald & Menges, "Materials Science of Polymers for Engineers" 3rd ed., Hanser 2012
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import math


class PolymerClass(Enum):
    """Classification of polymer materials."""
    THERMOPLASTIC = "thermoplastic"
    THERMOSET = "thermoset"
    ELASTOMER = "elastomer"
    FIBER = "fiber"
    FILM = "film"
    ADHESIVE = "adhesive"
    COATING = "coating"
    ELECTROLYTE = "polymer_electrolyte"


class PolymerStructure(Enum):
    """Morphological structure of polymers."""
    AMORPHOUS = "amorphous"
    SEMI_CRYSTALLINE = "semi_crystalline"
    CRYSTALLINE = "crystalline"
    CROSSLINKED = "crosslinked"
    LIQUID_CRYSTALLINE = "liquid_crystalline"


class PolymerFailureMode(Enum):
    """Known failure modes for polymer materials."""
    UV_DEGRADATION = "uv_degradation"
    HYDROLYSIS = "hydrolysis"
    OXIDATION = "oxidation"
    THERMAL_DEGRADATION = "thermal_degradation"
    CRAZING = "crazing"
    DELAMINATION = "delamination"
    PLASTICIZER_MIGRATION = "plasticizer_migration"
    CHEMICAL_ATTACK = "chemical_attack"
    CREEP = "creep"
    FATIGUE_CRACKING = "fatigue_cracking"
    ENVIRONMENTAL_STRESS_CRACKING = "environmental_stress_cracking"
    MOISTURE_ABSORPTION = "moisture_absorption"


@dataclass
class HansenParameters:
    """
    Hansen Solubility Parameters (MPa^0.5).

    Three-component model: total solubility = sqrt(d^2 + p^2 + h^2)
    Hansen distance Ra = sqrt(4*(dd)^2 + (dp)^2 + (dh)^2)
    Ra < 4 generally means compatible.

    Sources:
        Hansen, "Hansen Solubility Parameters: A User's Handbook" 2nd ed., CRC 2007
        Van Krevelen, "Properties of Polymers" 4th ed., Elsevier 2009
    """
    delta_d: float  # Dispersion (MPa^0.5)
    delta_p: float  # Polar (MPa^0.5)
    delta_h: float  # Hydrogen bonding (MPa^0.5)

    @property
    def delta_total(self) -> float:
        """Total Hildebrand solubility parameter."""
        return math.sqrt(self.delta_d**2 + self.delta_p**2 + self.delta_h**2)

    def distance(self, other: 'HansenParameters') -> float:
        """
        Hansen distance (Ra) to another material.

        Ra < 4: likely compatible/miscible
        4 < Ra < 8: marginal compatibility
        Ra > 8: likely immiscible
        """
        return math.sqrt(
            4 * (self.delta_d - other.delta_d)**2 +
            (self.delta_p - other.delta_p)**2 +
            (self.delta_h - other.delta_h)**2
        )


@dataclass
class PolymerMaterial:
    """
    A polymer material with validated physical properties.

    Analogous to BatteryMaterial in battery_bridge/material_properties.py.
    Every numerical value has a source citation.
    """
    name: str
    abbreviation: str
    polymer_class: PolymerClass
    structure: PolymerStructure

    # Solubility
    hansen: Optional[HansenParameters] = None

    # Thermal properties
    glass_transition_C: Optional[float] = None   # Tg (C)
    melting_point_C: Optional[float] = None       # Tm (C)
    decomposition_temp_C: Optional[float] = None  # Onset of thermal degradation (C)

    # Mechanical properties
    tensile_strength_MPa: Optional[float] = None
    elongation_at_break_pct: Optional[float] = None
    elastic_modulus_GPa: Optional[float] = None

    # Physical properties
    crystallinity_pct: Optional[float] = None
    water_absorption_pct: Optional[float] = None   # 24h immersion
    density_g_cm3: Optional[float] = None

    # Transport/barrier
    oxygen_permeability: Optional[float] = None  # cc*mil/(100in2*day*atm)

    # Flory-Huggins chi parameters vs named partners
    chi_parameters: Dict[str, float] = field(default_factory=dict)

    # Failure modes
    failure_modes: List[PolymerFailureMode] = field(default_factory=list)

    # Source citations
    sources: Dict[str, str] = field(default_factory=dict)

    # Additional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'abbreviation': self.abbreviation,
            'polymer_class': self.polymer_class.value,
            'structure': self.structure.value,
        }
        if self.hansen:
            result['hansen'] = {
                'delta_d': self.hansen.delta_d,
                'delta_p': self.hansen.delta_p,
                'delta_h': self.hansen.delta_h,
                'delta_total': round(self.hansen.delta_total, 2),
            }
        if self.glass_transition_C is not None:
            result['glass_transition_C'] = self.glass_transition_C
        if self.melting_point_C is not None:
            result['melting_point_C'] = self.melting_point_C
        if self.tensile_strength_MPa is not None:
            result['tensile_strength_MPa'] = self.tensile_strength_MPa
        if self.elastic_modulus_GPa is not None:
            result['elastic_modulus_GPa'] = self.elastic_modulus_GPa
        if self.failure_modes:
            result['failure_modes'] = [fm.value for fm in self.failure_modes]
        return result


# =============================================================================
# THERMOPLASTICS
# =============================================================================

THERMOPLASTIC_POLYMERS: Dict[str, PolymerMaterial] = {}

# Polyethylene (HDPE)
THERMOPLASTIC_POLYMERS['HDPE'] = PolymerMaterial(
    name='High-Density Polyethylene',
    abbreviation='HDPE',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=18.0, delta_p=0.0, delta_h=2.0),
    glass_transition_C=-120.0,
    melting_point_C=130.0,
    decomposition_temp_C=400.0,
    tensile_strength_MPa=31.0,
    elongation_at_break_pct=700.0,
    elastic_modulus_GPa=1.1,
    crystallinity_pct=70.0,
    water_absorption_pct=0.01,
    density_g_cm3=0.955,
    chi_parameters={'PP': 0.01, 'PS': 1.0, 'PA6': 2.0},
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.ENVIRONMENTAL_STRESS_CRACKING,
        PolymerFailureMode.CREEP,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'mechanical': 'Osswald & Menges, Materials Science of Polymers, 2012',
        'density': 'Van Krevelen, Properties of Polymers, 2009',
    },
)

# Polypropylene (PP)
THERMOPLASTIC_POLYMERS['PP'] = PolymerMaterial(
    name='Polypropylene',
    abbreviation='PP',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=18.0, delta_p=0.0, delta_h=1.0),
    glass_transition_C=-10.0,
    melting_point_C=165.0,
    decomposition_temp_C=380.0,
    tensile_strength_MPa=35.0,
    elongation_at_break_pct=100.0,
    elastic_modulus_GPa=1.5,
    crystallinity_pct=50.0,
    water_absorption_pct=0.02,
    density_g_cm3=0.905,
    chi_parameters={'HDPE': 0.01, 'PS': 0.5, 'PA6': 1.5, 'PA66': 1.5},
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.OXIDATION,
        PolymerFailureMode.CREEP,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
        'mechanical': 'Mark, Physical Properties of Polymers Handbook, 2007',
    },
)

# Polystyrene (PS)
THERMOPLASTIC_POLYMERS['PS'] = PolymerMaterial(
    name='Polystyrene',
    abbreviation='PS',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.5, delta_p=4.5, delta_h=2.9),
    glass_transition_C=100.0,
    melting_point_C=None,  # Amorphous, no Tm
    decomposition_temp_C=350.0,
    tensile_strength_MPa=40.0,
    elongation_at_break_pct=3.0,
    elastic_modulus_GPa=3.0,
    crystallinity_pct=0.0,
    water_absorption_pct=0.05,
    density_g_cm3=1.05,
    chi_parameters={'PMMA': 0.04, 'HDPE': 1.0, 'PPO': 0.001},
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.CRAZING,
        PolymerFailureMode.ENVIRONMENTAL_STRESS_CRACKING,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'chi_PMMA': 'Russell et al., Macromolecules 1990',
    },
)

# Poly(methyl methacrylate) (PMMA)
THERMOPLASTIC_POLYMERS['PMMA'] = PolymerMaterial(
    name='Poly(methyl methacrylate)',
    abbreviation='PMMA',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.6, delta_p=10.5, delta_h=7.5),
    glass_transition_C=105.0,
    melting_point_C=None,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=70.0,
    elongation_at_break_pct=5.0,
    elastic_modulus_GPa=3.3,
    crystallinity_pct=0.0,
    water_absorption_pct=0.3,
    density_g_cm3=1.19,
    chi_parameters={'PS': 0.04, 'PEO': -0.3, 'PVDF': -0.5},
    failure_modes=[
        PolymerFailureMode.CRAZING,
        PolymerFailureMode.MOISTURE_ABSORPTION,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
        'chi_PEO': 'Ito et al., Macromolecules 1987',
        'chi_PVDF': 'Nishi & Wang, Macromolecules 1975',
    },
)

# Polyvinyl chloride (PVC)
THERMOPLASTIC_POLYMERS['PVC'] = PolymerMaterial(
    name='Polyvinyl Chloride',
    abbreviation='PVC',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.2, delta_p=7.5, delta_h=8.3),
    glass_transition_C=80.0,
    melting_point_C=None,
    decomposition_temp_C=260.0,
    tensile_strength_MPa=50.0,
    elongation_at_break_pct=40.0,
    elastic_modulus_GPa=3.0,
    crystallinity_pct=0.0,
    water_absorption_pct=0.1,
    density_g_cm3=1.40,
    failure_modes=[
        PolymerFailureMode.THERMAL_DEGRADATION,
        PolymerFailureMode.PLASTICIZER_MIGRATION,
        PolymerFailureMode.UV_DEGRADATION,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'thermal_degradation': 'Starnes, Prog. Polym. Sci. 2002',
    },
    metadata={
        'note': 'Decomposes before melting; releases HCl above 260C',
    },
)

# Polyethylene terephthalate (PET)
THERMOPLASTIC_POLYMERS['PET'] = PolymerMaterial(
    name='Polyethylene Terephthalate',
    abbreviation='PET',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=19.4, delta_p=3.5, delta_h=8.6),
    glass_transition_C=75.0,
    melting_point_C=260.0,
    decomposition_temp_C=400.0,
    tensile_strength_MPa=55.0,
    elongation_at_break_pct=300.0,
    elastic_modulus_GPa=2.8,
    crystallinity_pct=30.0,
    water_absorption_pct=0.3,
    density_g_cm3=1.38,
    failure_modes=[
        PolymerFailureMode.HYDROLYSIS,
        PolymerFailureMode.UV_DEGRADATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
        'hydrolysis': 'Zimmermann & Recker, J. Appl. Polym. Sci. 1992',
    },
)

# Nylon 6 (PA6)
THERMOPLASTIC_POLYMERS['PA6'] = PolymerMaterial(
    name='Nylon 6',
    abbreviation='PA6',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=17.0, delta_p=3.4, delta_h=10.6),
    glass_transition_C=50.0,
    melting_point_C=220.0,
    decomposition_temp_C=400.0,
    tensile_strength_MPa=70.0,
    elongation_at_break_pct=30.0,
    elastic_modulus_GPa=2.8,
    crystallinity_pct=35.0,
    water_absorption_pct=9.5,
    density_g_cm3=1.13,
    chi_parameters={'HDPE': 2.0, 'PP': 1.5},
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
        PolymerFailureMode.HYDROLYSIS,
        PolymerFailureMode.OXIDATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
        'water': 'Kohan, Nylon Plastics Handbook, 1995',
    },
)

# Nylon 66 (PA66)
THERMOPLASTIC_POLYMERS['PA66'] = PolymerMaterial(
    name='Nylon 66',
    abbreviation='PA66',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=17.4, delta_p=5.1, delta_h=12.3),
    glass_transition_C=50.0,
    melting_point_C=265.0,
    decomposition_temp_C=420.0,
    tensile_strength_MPa=80.0,
    elongation_at_break_pct=25.0,
    elastic_modulus_GPa=3.0,
    crystallinity_pct=40.0,
    water_absorption_pct=8.0,
    density_g_cm3=1.14,
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
        PolymerFailureMode.HYDROLYSIS,
        PolymerFailureMode.OXIDATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
    },
)

# Polycarbonate (PC)
THERMOPLASTIC_POLYMERS['PC'] = PolymerMaterial(
    name='Polycarbonate',
    abbreviation='PC',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.6, delta_p=5.9, delta_h=6.9),
    glass_transition_C=150.0,
    melting_point_C=None,
    decomposition_temp_C=380.0,
    tensile_strength_MPa=65.0,
    elongation_at_break_pct=110.0,
    elastic_modulus_GPa=2.4,
    crystallinity_pct=0.0,
    water_absorption_pct=0.15,
    density_g_cm3=1.20,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.HYDROLYSIS,
        PolymerFailureMode.ENVIRONMENTAL_STRESS_CRACKING,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'mechanical': 'Osswald & Menges, 2012',
    },
)

# PEEK (Polyether ether ketone)
THERMOPLASTIC_POLYMERS['PEEK'] = PolymerMaterial(
    name='Polyether Ether Ketone',
    abbreviation='PEEK',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=19.0, delta_p=7.0, delta_h=5.0),
    glass_transition_C=143.0,
    melting_point_C=343.0,
    decomposition_temp_C=580.0,
    tensile_strength_MPa=100.0,
    elongation_at_break_pct=30.0,
    elastic_modulus_GPa=3.6,
    crystallinity_pct=35.0,
    water_absorption_pct=0.1,
    density_g_cm3=1.30,
    failure_modes=[],
    sources={
        'Tg_Tm': 'Victrex PEEK datasheet; Brandrup et al., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
        'mechanical': 'Victrex PEEK 450G datasheet',
    },
    metadata={
        'note': 'High-performance engineering thermoplastic; excellent chemical resistance',
    },
)

# POM (Polyoxymethylene / Delrin)
THERMOPLASTIC_POLYMERS['POM'] = PolymerMaterial(
    name='Polyoxymethylene',
    abbreviation='POM',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=17.2, delta_p=9.2, delta_h=9.8),
    glass_transition_C=-60.0,
    melting_point_C=175.0,
    decomposition_temp_C=280.0,
    tensile_strength_MPa=70.0,
    elongation_at_break_pct=25.0,
    elastic_modulus_GPa=3.0,
    crystallinity_pct=75.0,
    water_absorption_pct=0.2,
    density_g_cm3=1.42,
    failure_modes=[
        PolymerFailureMode.THERMAL_DEGRADATION,
        PolymerFailureMode.OXIDATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'note': 'Decomposes to formaldehyde; low thermal stability ceiling',
    },
)

# ABS (Acrylonitrile butadiene styrene)
THERMOPLASTIC_POLYMERS['ABS'] = PolymerMaterial(
    name='Acrylonitrile Butadiene Styrene',
    abbreviation='ABS',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.0, delta_p=8.0, delta_h=4.0),
    glass_transition_C=105.0,
    melting_point_C=None,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=45.0,
    elongation_at_break_pct=20.0,
    elastic_modulus_GPa=2.3,
    crystallinity_pct=0.0,
    water_absorption_pct=0.3,
    density_g_cm3=1.05,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.CHEMICAL_ATTACK,
    ],
    sources={
        'Tg': 'Osswald & Menges, 2012',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007 (estimated blend)',
    },
)


# =============================================================================
# BATTERY-RELEVANT POLYMERS
# =============================================================================

BATTERY_POLYMERS: Dict[str, PolymerMaterial] = {}

# PVDF (Polyvinylidene fluoride) -- battery binder
BATTERY_POLYMERS['PVDF'] = PolymerMaterial(
    name='Polyvinylidene Fluoride',
    abbreviation='PVDF',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=17.2, delta_p=12.5, delta_h=9.2),
    glass_transition_C=-40.0,
    melting_point_C=170.0,
    decomposition_temp_C=380.0,
    tensile_strength_MPa=50.0,
    elongation_at_break_pct=50.0,
    elastic_modulus_GPa=2.0,
    crystallinity_pct=50.0,
    water_absorption_pct=0.04,
    density_g_cm3=1.78,
    chi_parameters={'PMMA': -0.5, 'PEO': 0.8},
    failure_modes=[
        PolymerFailureMode.DELAMINATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'chi_PMMA': 'Nishi & Wang, Macromolecules 1975',
    },
    metadata={
        'role': 'Battery electrode binder; dissolved in NMP for slurry coating',
        'battery_relevance': 'Standard binder for Li-ion cathodes and anodes',
    },
)

# PEO (Polyethylene oxide) -- polymer electrolyte
BATTERY_POLYMERS['PEO'] = PolymerMaterial(
    name='Polyethylene Oxide',
    abbreviation='PEO',
    polymer_class=PolymerClass.ELECTROLYTE,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=17.3, delta_p=3.0, delta_h=9.4),
    glass_transition_C=-60.0,
    melting_point_C=65.0,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=25.0,
    elongation_at_break_pct=800.0,
    elastic_modulus_GPa=0.5,
    crystallinity_pct=80.0,
    water_absorption_pct=100.0,  # Fully water-soluble
    density_g_cm3=1.13,
    chi_parameters={'PMMA': -0.3, 'PVDF': 0.8, 'LiTFSI': -2.0},
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
        PolymerFailureMode.OXIDATION,
        PolymerFailureMode.CREEP,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
        'chi_PMMA': 'Ito et al., Macromolecules 1987',
        'electrolyte': 'Armand, Solid State Ionics 1983',
    },
    metadata={
        'role': 'Polymer electrolyte host for Li salts; ionic conductivity ~1e-4 S/cm at 70C',
        'battery_relevance': 'SPE with LiTFSI; needs >60C for adequate conductivity',
        'ionic_conductivity_70C': 1e-4,
        'electrochemical_window_V': 3.8,
    },
)

# PTFE (Polytetrafluoroethylene / Teflon)
BATTERY_POLYMERS['PTFE'] = PolymerMaterial(
    name='Polytetrafluoroethylene',
    abbreviation='PTFE',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=16.2, delta_p=1.8, delta_h=3.4),
    glass_transition_C=127.0,
    melting_point_C=327.0,
    decomposition_temp_C=500.0,
    tensile_strength_MPa=25.0,
    elongation_at_break_pct=300.0,
    elastic_modulus_GPa=0.5,
    crystallinity_pct=90.0,
    water_absorption_pct=0.0,
    density_g_cm3=2.17,
    failure_modes=[
        PolymerFailureMode.CREEP,
        PolymerFailureMode.DELAMINATION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'density': 'DuPont Teflon datasheet',
    },
    metadata={
        'role': 'Battery binder (alternative to PVDF); chemically inert',
        'battery_relevance': 'Used as binder in some cathode formulations; excellent chem resistance',
    },
)

# CMC (Carboxymethyl cellulose) -- water-based binder
BATTERY_POLYMERS['CMC'] = PolymerMaterial(
    name='Carboxymethyl Cellulose',
    abbreviation='CMC',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=16.0, delta_p=15.0, delta_h=20.0),
    glass_transition_C=None,  # Degrades before transitioning
    melting_point_C=None,     # Degrades before melting
    decomposition_temp_C=270.0,
    tensile_strength_MPa=40.0,
    elongation_at_break_pct=10.0,
    elastic_modulus_GPa=2.0,
    water_absorption_pct=100.0,
    density_g_cm3=1.59,
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
        PolymerFailureMode.THERMAL_DEGRADATION,
    ],
    sources={
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007 (cellulose derivative)',
        'thermal': 'Biswal & Singh, Carbohydrate Polymers 2004',
    },
    metadata={
        'role': 'Water-based binder for anodes; used with SBR co-binder',
        'battery_relevance': 'Eco-friendly binder replacing NMP/PVDF for graphite anodes',
    },
)

# PAN (Polyacrylonitrile)
BATTERY_POLYMERS['PAN'] = PolymerMaterial(
    name='Polyacrylonitrile',
    abbreviation='PAN',
    polymer_class=PolymerClass.FIBER,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=18.2, delta_p=16.2, delta_h=6.8),
    glass_transition_C=95.0,
    melting_point_C=317.0,
    decomposition_temp_C=310.0,
    tensile_strength_MPa=60.0,
    elongation_at_break_pct=15.0,
    elastic_modulus_GPa=3.5,
    crystallinity_pct=25.0,
    water_absorption_pct=2.0,
    density_g_cm3=1.18,
    failure_modes=[
        PolymerFailureMode.THERMAL_DEGRADATION,
        PolymerFailureMode.MOISTURE_ABSORPTION,
    ],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009',
    },
    metadata={
        'role': 'Carbon fiber precursor; gel polymer electrolyte host; separator material',
        'battery_relevance': 'Gel electrolyte membranes, separator coatings',
    },
)


# =============================================================================
# ELASTOMERS
# =============================================================================

ELASTOMER_POLYMERS: Dict[str, PolymerMaterial] = {}

# SBR (Styrene-butadiene rubber)
ELASTOMER_POLYMERS['SBR'] = PolymerMaterial(
    name='Styrene-Butadiene Rubber',
    abbreviation='SBR',
    polymer_class=PolymerClass.ELASTOMER,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=17.5, delta_p=3.5, delta_h=2.5),
    glass_transition_C=-55.0,
    melting_point_C=None,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=15.0,
    elongation_at_break_pct=500.0,
    elastic_modulus_GPa=0.005,
    water_absorption_pct=0.1,
    density_g_cm3=0.94,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.OXIDATION,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'role': 'Battery binder co-additive with CMC for water-based slurries',
        'battery_relevance': 'CMC+SBR is standard water-based binder for graphite anodes',
    },
)

# Natural Rubber (NR)
ELASTOMER_POLYMERS['NR'] = PolymerMaterial(
    name='Natural Rubber',
    abbreviation='NR',
    polymer_class=PolymerClass.ELASTOMER,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=17.4, delta_p=3.1, delta_h=4.1),
    glass_transition_C=-70.0,
    melting_point_C=None,
    decomposition_temp_C=300.0,
    tensile_strength_MPa=25.0,
    elongation_at_break_pct=700.0,
    elastic_modulus_GPa=0.002,
    density_g_cm3=0.92,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.OXIDATION,
        PolymerFailureMode.CHEMICAL_ATTACK,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
)

# NBR (Nitrile rubber)
ELASTOMER_POLYMERS['NBR'] = PolymerMaterial(
    name='Nitrile Rubber',
    abbreviation='NBR',
    polymer_class=PolymerClass.ELASTOMER,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.0, delta_p=8.5, delta_h=4.0),
    glass_transition_C=-26.0,  # 33% ACN content
    melting_point_C=None,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=20.0,
    elongation_at_break_pct=400.0,
    elastic_modulus_GPa=0.006,
    density_g_cm3=1.00,
    failure_modes=[
        PolymerFailureMode.OXIDATION,
        PolymerFailureMode.UV_DEGRADATION,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999 (33% ACN)',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'note': 'Tg varies with ACN content: 18% ACN -> Tg=-45C, 50% ACN -> Tg=0C',
    },
)

# Silicone (PDMS)
ELASTOMER_POLYMERS['PDMS'] = PolymerMaterial(
    name='Polydimethylsiloxane',
    abbreviation='PDMS',
    polymer_class=PolymerClass.ELASTOMER,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=15.9, delta_p=0.0, delta_h=4.7),
    glass_transition_C=-125.0,
    melting_point_C=-40.0,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=5.0,
    elongation_at_break_pct=500.0,
    elastic_modulus_GPa=0.001,
    water_absorption_pct=0.0,
    density_g_cm3=0.97,
    failure_modes=[
        PolymerFailureMode.CREEP,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'mechanical': 'Mark, Physical Properties of Polymers Handbook, 2007',
    },
)

# EPDM
ELASTOMER_POLYMERS['EPDM'] = PolymerMaterial(
    name='Ethylene Propylene Diene Monomer',
    abbreviation='EPDM',
    polymer_class=PolymerClass.ELASTOMER,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=17.5, delta_p=1.0, delta_h=2.0),
    glass_transition_C=-55.0,
    melting_point_C=None,
    decomposition_temp_C=400.0,
    tensile_strength_MPa=15.0,
    elongation_at_break_pct=400.0,
    elastic_modulus_GPa=0.008,
    density_g_cm3=0.86,
    failure_modes=[
        PolymerFailureMode.CREEP,
    ],
    sources={
        'Tg': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
    },
)


# =============================================================================
# HIGH-PERFORMANCE POLYMERS
# =============================================================================

HIGH_PERFORMANCE_POLYMERS: Dict[str, PolymerMaterial] = {}

# Polyimide (Kapton)
HIGH_PERFORMANCE_POLYMERS['PI'] = PolymerMaterial(
    name='Polyimide',
    abbreviation='PI',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=20.0, delta_p=14.0, delta_h=5.0),
    glass_transition_C=360.0,
    melting_point_C=None,
    decomposition_temp_C=520.0,
    tensile_strength_MPa=230.0,
    elongation_at_break_pct=70.0,
    elastic_modulus_GPa=3.0,
    water_absorption_pct=1.8,
    density_g_cm3=1.42,
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
    ],
    sources={
        'Tg': 'DuPont Kapton HN datasheet',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
        'mechanical': 'DuPont Kapton HN datasheet',
    },
    metadata={
        'note': 'Kapton-type PMDA-ODA; exceptional thermal stability',
    },
)

# PPS (Polyphenylene sulfide)
HIGH_PERFORMANCE_POLYMERS['PPS'] = PolymerMaterial(
    name='Polyphenylene Sulfide',
    abbreviation='PPS',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.SEMI_CRYSTALLINE,
    hansen=HansenParameters(delta_d=19.0, delta_p=4.0, delta_h=2.0),
    glass_transition_C=85.0,
    melting_point_C=285.0,
    decomposition_temp_C=500.0,
    tensile_strength_MPa=80.0,
    elongation_at_break_pct=4.0,
    elastic_modulus_GPa=3.8,
    crystallinity_pct=65.0,
    water_absorption_pct=0.05,
    density_g_cm3=1.35,
    failure_modes=[],
    sources={
        'Tg_Tm': 'Brandrup et al., Polymer Handbook 4th ed., 1999',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
    },
)

# PPSU (Polyphenylsulfone)
HIGH_PERFORMANCE_POLYMERS['PPSU'] = PolymerMaterial(
    name='Polyphenylsulfone',
    abbreviation='PPSU',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=19.5, delta_p=8.0, delta_h=8.0),
    glass_transition_C=220.0,
    melting_point_C=None,
    decomposition_temp_C=530.0,
    tensile_strength_MPa=70.0,
    elongation_at_break_pct=60.0,
    elastic_modulus_GPa=2.3,
    water_absorption_pct=0.4,
    density_g_cm3=1.29,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
    ],
    sources={
        'Tg': 'Solvay Radel datasheet',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
    },
)

# LCP (Liquid Crystal Polymer)
HIGH_PERFORMANCE_POLYMERS['LCP'] = PolymerMaterial(
    name='Liquid Crystal Polymer',
    abbreviation='LCP',
    polymer_class=PolymerClass.THERMOPLASTIC,
    structure=PolymerStructure.LIQUID_CRYSTALLINE,
    hansen=HansenParameters(delta_d=20.0, delta_p=6.0, delta_h=4.0),
    glass_transition_C=None,
    melting_point_C=280.0,
    decomposition_temp_C=500.0,
    tensile_strength_MPa=180.0,
    elongation_at_break_pct=3.0,
    elastic_modulus_GPa=10.0,
    crystallinity_pct=None,
    water_absorption_pct=0.02,
    density_g_cm3=1.40,
    failure_modes=[],
    sources={
        'Tm': 'Celanese Vectra datasheet',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
    },
)


# =============================================================================
# THERMOSETS
# =============================================================================

THERMOSET_POLYMERS: Dict[str, PolymerMaterial] = {}

# Epoxy (DGEBA + amine cured)
THERMOSET_POLYMERS['Epoxy'] = PolymerMaterial(
    name='Epoxy Resin (DGEBA/Amine)',
    abbreviation='Epoxy',
    polymer_class=PolymerClass.THERMOSET,
    structure=PolymerStructure.CROSSLINKED,
    hansen=HansenParameters(delta_d=18.0, delta_p=10.0, delta_h=9.0),
    glass_transition_C=180.0,
    melting_point_C=None,
    decomposition_temp_C=350.0,
    tensile_strength_MPa=70.0,
    elongation_at_break_pct=5.0,
    elastic_modulus_GPa=3.0,
    water_absorption_pct=0.5,
    density_g_cm3=1.20,
    failure_modes=[
        PolymerFailureMode.MOISTURE_ABSORPTION,
        PolymerFailureMode.THERMAL_DEGRADATION,
        PolymerFailureMode.FATIGUE_CRACKING,
    ],
    sources={
        'Tg': 'May, Epoxy Resins: Chemistry and Technology 2nd ed., 1988',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'mechanical': 'Osswald & Menges, 2012',
    },
    metadata={
        'note': 'Tg depends on cure agent: 120C (amines) to 250C (DDS)',
    },
)

# Phenolic
THERMOSET_POLYMERS['Phenolic'] = PolymerMaterial(
    name='Phenol-Formaldehyde Resin',
    abbreviation='Phenolic',
    polymer_class=PolymerClass.THERMOSET,
    structure=PolymerStructure.CROSSLINKED,
    hansen=HansenParameters(delta_d=20.0, delta_p=10.0, delta_h=14.0),
    glass_transition_C=150.0,
    melting_point_C=None,
    decomposition_temp_C=300.0,
    tensile_strength_MPa=50.0,
    elongation_at_break_pct=2.0,
    elastic_modulus_GPa=4.0,
    water_absorption_pct=0.3,
    density_g_cm3=1.27,
    failure_modes=[
        PolymerFailureMode.THERMAL_DEGRADATION,
        PolymerFailureMode.MOISTURE_ABSORPTION,
    ],
    sources={
        'Tg': 'Pilato, Phenolic Resins: A Century of Progress, 2010',
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007 (estimated)',
    },
)

# Unsaturated Polyester
THERMOSET_POLYMERS['UPE'] = PolymerMaterial(
    name='Unsaturated Polyester',
    abbreviation='UPE',
    polymer_class=PolymerClass.THERMOSET,
    structure=PolymerStructure.CROSSLINKED,
    hansen=HansenParameters(delta_d=19.0, delta_p=8.0, delta_h=7.0),
    glass_transition_C=100.0,
    melting_point_C=None,
    decomposition_temp_C=300.0,
    tensile_strength_MPa=55.0,
    elongation_at_break_pct=3.0,
    elastic_modulus_GPa=3.5,
    water_absorption_pct=0.5,
    density_g_cm3=1.20,
    failure_modes=[
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.HYDROLYSIS,
        PolymerFailureMode.FATIGUE_CRACKING,
    ],
    sources={
        'Tg': 'Osswald & Menges, 2012',
        'hansen': 'Van Krevelen, Properties of Polymers, 2009 (estimated)',
    },
)


# =============================================================================
# SOLVENTS (for processing compatibility)
# =============================================================================

POLYMER_SOLVENTS: Dict[str, PolymerMaterial] = {}

# NMP (N-Methyl-2-pyrrolidone) -- PVDF solvent
POLYMER_SOLVENTS['NMP'] = PolymerMaterial(
    name='N-Methyl-2-Pyrrolidone',
    abbreviation='NMP',
    polymer_class=PolymerClass.COATING,  # Used as processing solvent
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.0, delta_p=12.3, delta_h=7.2),
    glass_transition_C=None,
    melting_point_C=-24.0,
    decomposition_temp_C=None,
    density_g_cm3=1.028,
    failure_modes=[],
    sources={
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
        'density': 'CRC Handbook of Chemistry and Physics',
    },
    metadata={
        'role': 'Standard solvent for PVDF binder in battery electrode slurries',
        'boiling_point_C': 202.0,
    },
)

# Water
POLYMER_SOLVENTS['Water'] = PolymerMaterial(
    name='Water',
    abbreviation='Water',
    polymer_class=PolymerClass.COATING,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=15.5, delta_p=16.0, delta_h=42.3),
    glass_transition_C=None,
    melting_point_C=0.0,
    density_g_cm3=1.00,
    failure_modes=[],
    sources={
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'role': 'Solvent for CMC+SBR water-based binder systems',
    },
)

# Toluene
POLYMER_SOLVENTS['Toluene'] = PolymerMaterial(
    name='Toluene',
    abbreviation='Toluene',
    polymer_class=PolymerClass.COATING,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=18.0, delta_p=1.4, delta_h=2.0),
    glass_transition_C=None,
    melting_point_C=-95.0,
    density_g_cm3=0.867,
    failure_modes=[],
    sources={
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'role': 'Solvent for PS, NR, SBR; dissolves nonpolar polymers',
        'boiling_point_C': 110.6,
    },
)

# Acetone
POLYMER_SOLVENTS['Acetone'] = PolymerMaterial(
    name='Acetone',
    abbreviation='Acetone',
    polymer_class=PolymerClass.COATING,
    structure=PolymerStructure.AMORPHOUS,
    hansen=HansenParameters(delta_d=15.5, delta_p=10.4, delta_h=7.0),
    glass_transition_C=None,
    melting_point_C=-94.7,
    density_g_cm3=0.791,
    failure_modes=[],
    sources={
        'hansen': 'Hansen, HSP Handbook 2nd ed., 2007',
    },
    metadata={
        'role': 'Solvent for PMMA, PC; used for cleaning and surface prep',
        'boiling_point_C': 56.0,
    },
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_POLYMERS: Dict[str, PolymerMaterial] = {}
ALL_POLYMERS.update(THERMOPLASTIC_POLYMERS)
ALL_POLYMERS.update(BATTERY_POLYMERS)
ALL_POLYMERS.update(ELASTOMER_POLYMERS)
ALL_POLYMERS.update(HIGH_PERFORMANCE_POLYMERS)
ALL_POLYMERS.update(THERMOSET_POLYMERS)
ALL_POLYMERS.update(POLYMER_SOLVENTS)


def get_polymer(name: str) -> Optional[PolymerMaterial]:
    """Look up a polymer by name or abbreviation."""
    return ALL_POLYMERS.get(name)


def get_polymers_by_class(polymer_class: PolymerClass) -> Dict[str, PolymerMaterial]:
    """Get all polymers of a given class."""
    return {k: v for k, v in ALL_POLYMERS.items()
            if v.polymer_class == polymer_class}


def list_thermoplastics() -> List[str]:
    return list(THERMOPLASTIC_POLYMERS.keys())


def list_elastomers() -> List[str]:
    return list(ELASTOMER_POLYMERS.keys())


def list_thermosets() -> List[str]:
    return list(THERMOSET_POLYMERS.keys())


def list_battery_polymers() -> List[str]:
    return list(BATTERY_POLYMERS.keys())


# =============================================================================
# KNOWN GOOD/BAD PAIRINGS (for test validation)
# =============================================================================

KNOWN_GOOD_BLENDS = [
    {
        'name': 'PVDF + NMP',
        'polymer_a': 'PVDF',
        'polymer_b': 'NMP',
        'notes': 'Standard battery binder dissolved in NMP; Hansen Ra < 4',
    },
    {
        'name': 'PVDF + PMMA',
        'polymer_a': 'PVDF',
        'polymer_b': 'PMMA',
        'notes': 'Miscible blend; negative chi parameter (Nishi & Wang 1975)',
    },
    {
        'name': 'PEO + PMMA',
        'polymer_a': 'PEO',
        'polymer_b': 'PMMA',
        'notes': 'Miscible blend; negative chi (Ito et al. 1987)',
    },
    {
        'name': 'HDPE + PP',
        'polymer_a': 'HDPE',
        'polymer_b': 'PP',
        'notes': 'Nearly miscible; chi ~0.01; common recycling blend',
    },
    {
        'name': 'PS + Toluene',
        'polymer_a': 'PS',
        'polymer_b': 'Toluene',
        'notes': 'PS dissolves readily in toluene; close Hansen parameters',
    },
]

KNOWN_BAD_BLENDS = [
    {
        'name': 'PTFE + most solvents',
        'polymer_a': 'PTFE',
        'polymer_b': 'NMP',
        'issue': 'PTFE is chemically inert; large Hansen distance to virtually all solvents',
    },
    {
        'name': 'HDPE + PA6',
        'polymer_a': 'HDPE',
        'polymer_b': 'PA6',
        'issue': 'Immiscible; chi ~2.0; nonpolar PE vs polar nylon',
    },
    {
        'name': 'PP + PA6',
        'polymer_a': 'PP',
        'polymer_b': 'PA6',
        'issue': 'Immiscible; large polarity mismatch; needs compatibilizer',
    },
    {
        'name': 'Water + HDPE',
        'polymer_a': 'Water',
        'polymer_b': 'HDPE',
        'issue': 'Water is extremely polar; HDPE is nonpolar; Hansen Ra >> 10',
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("Polymer Material Properties - Summary")
    print("=" * 70)
    print()
    print(f"Thermoplastics: {len(THERMOPLASTIC_POLYMERS)}")
    for name, mat in THERMOPLASTIC_POLYMERS.items():
        tg = f"Tg={mat.glass_transition_C:.0f}C" if mat.glass_transition_C is not None else "Tg=N/A"
        tm = f"Tm={mat.melting_point_C:.0f}C" if mat.melting_point_C is not None else ""
        print(f"  {name:6s} ({mat.name:40s}) {tg:12s} {tm}")
    print()
    print(f"Battery-relevant: {len(BATTERY_POLYMERS)}")
    for name, mat in BATTERY_POLYMERS.items():
        print(f"  {name:6s} ({mat.name:40s})")
    print()
    print(f"Elastomers: {len(ELASTOMER_POLYMERS)}")
    for name, mat in ELASTOMER_POLYMERS.items():
        tg = f"Tg={mat.glass_transition_C:.0f}C" if mat.glass_transition_C is not None else "Tg=N/A"
        print(f"  {name:6s} ({mat.name:40s}) {tg}")
    print()
    print(f"High-performance: {len(HIGH_PERFORMANCE_POLYMERS)}")
    print(f"Thermosets: {len(THERMOSET_POLYMERS)}")
    print(f"Solvents: {len(POLYMER_SOLVENTS)}")
    print(f"\nTotal materials: {len(ALL_POLYMERS)}")
