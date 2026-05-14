# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Metal Material Properties
============================

Validated property tables for metals and alloys, analogous to
polymer_bridge/material_properties.py.

Each material entry uses real published values with source citations.

Property Sources:
-----------------
- ASM International, "ASM Handbook Vol. 2: Properties and Selection", 1990
- MatWeb Material Property Data (matweb.com)
- MIL-HDBK-5J, "Metallic Materials for Aerospace", 2003
- Davis (ed.), "ASM Specialty Handbook: Stainless Steels", 1994
- Boyer et al., "Materials Properties Handbook: Titanium Alloys", 1994
- Smithells, "Metals Reference Book" 8th ed., 2004
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class MetalClass(Enum):
    """Classification of metal materials."""
    PURE_METAL = "pure_metal"
    FERROUS_ALLOY = "ferrous_alloy"
    ALUMINUM_ALLOY = "aluminum_alloy"
    COPPER_ALLOY = "copper_alloy"
    TITANIUM_ALLOY = "titanium_alloy"
    NICKEL_ALLOY = "nickel_alloy"
    REFRACTORY = "refractory"
    PRECIOUS_METAL = "precious_metal"
    BATTERY_METAL = "battery_metal"


class CrystalSystem(Enum):
    """Crystal structure at room temperature."""
    FCC = "fcc"
    BCC = "bcc"
    HCP = "hcp"
    BCT = "bct"
    MIXED = "mixed"


class MetalFailureMode(Enum):
    """Known failure modes for metals and alloys."""
    GENERAL_CORROSION = "general_corrosion"
    GALVANIC_CORROSION = "galvanic_corrosion"
    PITTING = "pitting"
    CREVICE_CORROSION = "crevice_corrosion"
    STRESS_CORROSION_CRACKING = "stress_corrosion_cracking"
    HYDROGEN_EMBRITTLEMENT = "hydrogen_embrittlement"
    INTERGRANULAR_CORROSION = "intergranular_corrosion"
    FATIGUE = "fatigue"
    CREEP = "creep"
    HIGH_TEMP_OXIDATION = "high_temp_oxidation"
    DEZINCIFICATION = "dezincification"
    SENSITIZATION = "sensitization"
    EROSION_CORROSION = "erosion_corrosion"


@dataclass
class MetalMaterial:
    """
    A metal or alloy with validated physical properties.

    Analogous to PolymerMaterial in polymer_bridge/material_properties.py.
    Every numerical value has a source citation.
    """
    name: str
    formula: str
    metal_class: MetalClass
    crystal_system: CrystalSystem

    # Thermal
    melting_point_C: Optional[float] = None
    thermal_conductivity_W_mK: Optional[float] = None
    cte_per_K: Optional[float] = None   # Coefficient of thermal expansion (x10^-6 /K)

    # Mechanical
    elastic_modulus_GPa: Optional[float] = None
    yield_strength_MPa: Optional[float] = None
    ultimate_tensile_MPa: Optional[float] = None
    elongation_pct: Optional[float] = None
    hardness_HV: Optional[float] = None
    fatigue_limit_MPa: Optional[float] = None

    # Physical
    density_g_cm3: Optional[float] = None

    # Electrical
    electrical_resistivity_ohm_m: Optional[float] = None

    # Corrosion / Galvanic
    galvanic_potential_V: Optional[float] = None   # vs SCE in flowing seawater
    corrosion_rate_mm_yr: Optional[float] = None   # in standard atmosphere

    # Failure modes
    failure_modes: List[MetalFailureMode] = field(default_factory=list)

    # Source citations
    sources: Dict[str, str] = field(default_factory=dict)

    # Additional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    # Surface coating (if any) — affects electrochemical stability limits
    coating: Optional[str] = None  # e.g., "carbon", "Al2O3", "TiN"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'formula': self.formula,
            'metal_class': self.metal_class.value,
            'crystal_system': self.crystal_system.value,
        }
        if self.melting_point_C is not None:
            result['melting_point_C'] = self.melting_point_C
        if self.elastic_modulus_GPa is not None:
            result['elastic_modulus_GPa'] = self.elastic_modulus_GPa
        if self.yield_strength_MPa is not None:
            result['yield_strength_MPa'] = self.yield_strength_MPa
        if self.galvanic_potential_V is not None:
            result['galvanic_potential_V'] = self.galvanic_potential_V
        if self.cte_per_K is not None:
            result['cte_per_K'] = self.cte_per_K
        if self.density_g_cm3 is not None:
            result['density_g_cm3'] = self.density_g_cm3
        if self.failure_modes:
            result['failure_modes'] = [fm.value for fm in self.failure_modes]
        return result


# =============================================================================
# PURE METALS
# =============================================================================

PURE_METALS: Dict[str, MetalMaterial] = {}

PURE_METALS['Fe'] = MetalMaterial(
    name='Iron',
    formula='Fe',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=1538.0,
    thermal_conductivity_W_mK=80.0,
    cte_per_K=11.8,
    elastic_modulus_GPa=210.0,
    yield_strength_MPa=100.0,
    ultimate_tensile_MPa=350.0,
    elongation_pct=40.0,
    hardness_HV=80,
    density_g_cm3=7.87,
    electrical_resistivity_ohm_m=9.71e-8,
    galvanic_potential_V=-0.60,
    corrosion_rate_mm_yr=0.10,
    failure_modes=[
        MetalFailureMode.GENERAL_CORROSION,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
        'galvanic': 'ASTM G82, galvanic series in seawater',
    },
)

PURE_METALS['Al'] = MetalMaterial(
    name='Aluminum',
    formula='Al',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=660.0,
    thermal_conductivity_W_mK=237.0,
    cte_per_K=23.1,
    elastic_modulus_GPa=70.0,
    yield_strength_MPa=35.0,
    ultimate_tensile_MPa=90.0,
    elongation_pct=60.0,
    hardness_HV=15,
    density_g_cm3=2.70,
    electrical_resistivity_ohm_m=2.65e-8,
    galvanic_potential_V=-0.76,
    corrosion_rate_mm_yr=0.005,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.PITTING,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True, 'battery_role': 'cathode current collector foil'},
)

PURE_METALS['Cu'] = MetalMaterial(
    name='Copper',
    formula='Cu',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1085.0,
    thermal_conductivity_W_mK=401.0,
    cte_per_K=17.0,
    elastic_modulus_GPa=130.0,
    yield_strength_MPa=70.0,
    ultimate_tensile_MPa=220.0,
    elongation_pct=50.0,
    hardness_HV=40,
    density_g_cm3=8.96,
    electrical_resistivity_ohm_m=1.68e-8,
    galvanic_potential_V=-0.20,
    corrosion_rate_mm_yr=0.003,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': False, 'battery_role': 'anode current collector foil'},
)

PURE_METALS['Ti'] = MetalMaterial(
    name='Titanium',
    formula='Ti',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.HCP,
    melting_point_C=1668.0,
    thermal_conductivity_W_mK=22.0,
    cte_per_K=8.6,
    elastic_modulus_GPa=116.0,
    yield_strength_MPa=170.0,
    ultimate_tensile_MPa=240.0,
    elongation_pct=24.0,
    hardness_HV=120,
    density_g_cm3=4.51,
    electrical_resistivity_ohm_m=4.20e-7,
    galvanic_potential_V=-0.02,
    corrosion_rate_mm_yr=0.001,
    failure_modes=[
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
        MetalFailureMode.CREEP,
    ],
    sources={
        'mechanical': 'Boyer et al., Ti Alloys Handbook, 1994',
        'thermal': 'Smithells Metals Reference Book, 2004',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True},
)

PURE_METALS['Ni'] = MetalMaterial(
    name='Nickel',
    formula='Ni',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1455.0,
    thermal_conductivity_W_mK=91.0,
    cte_per_K=13.4,
    elastic_modulus_GPa=200.0,
    yield_strength_MPa=150.0,
    ultimate_tensile_MPa=450.0,
    elongation_pct=47.0,
    hardness_HV=80,
    density_g_cm3=8.91,
    electrical_resistivity_ohm_m=6.84e-8,
    galvanic_potential_V=-0.10,
    corrosion_rate_mm_yr=0.002,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'Special Metals Nickel 200 datasheet',
        'thermal': 'Smithells Metals Reference Book, 2004',
        'galvanic': 'ASTM G82',
    },
    metadata={'battery_role': 'battery tab material'},
)

PURE_METALS['Zn'] = MetalMaterial(
    name='Zinc',
    formula='Zn',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.HCP,
    melting_point_C=420.0,
    thermal_conductivity_W_mK=116.0,
    cte_per_K=30.2,
    elastic_modulus_GPa=108.0,
    yield_strength_MPa=30.0,
    ultimate_tensile_MPa=50.0,
    elongation_pct=30.0,
    hardness_HV=30,
    density_g_cm3=7.14,
    electrical_resistivity_ohm_m=5.90e-8,
    galvanic_potential_V=-1.05,
    corrosion_rate_mm_yr=0.01,
    failure_modes=[
        MetalFailureMode.GENERAL_CORROSION,
        MetalFailureMode.CREEP,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'galvanic': 'ASTM G82',
    },
    metadata={'note': 'Used as sacrificial anode for galvanic protection of steel'},
)

PURE_METALS['Mg'] = MetalMaterial(
    name='Magnesium',
    formula='Mg',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.HCP,
    melting_point_C=650.0,
    thermal_conductivity_W_mK=156.0,
    cte_per_K=26.0,
    elastic_modulus_GPa=45.0,
    yield_strength_MPa=69.0,
    ultimate_tensile_MPa=130.0,
    elongation_pct=8.0,
    hardness_HV=44,
    density_g_cm3=1.74,
    electrical_resistivity_ohm_m=4.40e-8,
    galvanic_potential_V=-1.60,
    corrosion_rate_mm_yr=0.05,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.GENERAL_CORROSION,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'galvanic': 'ASTM G82',
    },
    metadata={'note': 'Most anodic common structural metal; lightest structural metal'},
)

PURE_METALS['W'] = MetalMaterial(
    name='Tungsten',
    formula='W',
    metal_class=MetalClass.REFRACTORY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=3422.0,
    thermal_conductivity_W_mK=173.0,
    cte_per_K=4.5,
    elastic_modulus_GPa=411.0,
    yield_strength_MPa=750.0,
    ultimate_tensile_MPa=980.0,
    elongation_pct=2.0,
    hardness_HV=350,
    density_g_cm3=19.25,
    electrical_resistivity_ohm_m=5.28e-8,
    galvanic_potential_V=-0.12,
    failure_modes=[
        MetalFailureMode.HIGH_TEMP_OXIDATION,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
    },
    metadata={'note': 'Highest melting point of all metals'},
)

PURE_METALS['Mo'] = MetalMaterial(
    name='Molybdenum',
    formula='Mo',
    metal_class=MetalClass.REFRACTORY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=2623.0,
    thermal_conductivity_W_mK=138.0,
    cte_per_K=4.8,
    elastic_modulus_GPa=329.0,
    yield_strength_MPa=550.0,
    ultimate_tensile_MPa=690.0,
    elongation_pct=12.0,
    hardness_HV=200,
    density_g_cm3=10.28,
    electrical_resistivity_ohm_m=5.34e-8,
    galvanic_potential_V=-0.15,
    failure_modes=[
        MetalFailureMode.HIGH_TEMP_OXIDATION,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
    },
)

PURE_METALS['Sn'] = MetalMaterial(
    name='Tin',
    formula='Sn',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.BCT,
    melting_point_C=232.0,
    thermal_conductivity_W_mK=67.0,
    cte_per_K=22.0,
    elastic_modulus_GPa=50.0,
    yield_strength_MPa=11.0,
    ultimate_tensile_MPa=22.0,
    elongation_pct=60.0,
    hardness_HV=5,
    density_g_cm3=7.29,
    electrical_resistivity_ohm_m=1.15e-7,
    galvanic_potential_V=-0.35,
    failure_modes=[
        MetalFailureMode.CREEP,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'galvanic': 'ASTM G82',
    },
    metadata={'note': 'Solder base metal; tin pest below 13C'},
)

PURE_METALS['Pb'] = MetalMaterial(
    name='Lead',
    formula='Pb',
    metal_class=MetalClass.PURE_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=327.0,
    thermal_conductivity_W_mK=35.0,
    cte_per_K=29.0,
    elastic_modulus_GPa=16.0,
    yield_strength_MPa=8.0,
    ultimate_tensile_MPa=18.0,
    elongation_pct=50.0,
    hardness_HV=4,
    density_g_cm3=11.35,
    electrical_resistivity_ohm_m=2.08e-7,
    galvanic_potential_V=-0.40,
    failure_modes=[
        MetalFailureMode.CREEP,
        MetalFailureMode.GENERAL_CORROSION,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'galvanic': 'ASTM G82',
    },
)

PURE_METALS['Ag'] = MetalMaterial(
    name='Silver',
    formula='Ag',
    metal_class=MetalClass.PRECIOUS_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=962.0,
    thermal_conductivity_W_mK=429.0,
    cte_per_K=18.9,
    elastic_modulus_GPa=83.0,
    yield_strength_MPa=55.0,
    ultimate_tensile_MPa=170.0,
    elongation_pct=48.0,
    hardness_HV=25,
    density_g_cm3=10.49,
    electrical_resistivity_ohm_m=1.59e-8,
    galvanic_potential_V=0.05,
    failure_modes=[],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
    },
    metadata={'note': 'Highest electrical and thermal conductivity of all metals'},
)

PURE_METALS['Au'] = MetalMaterial(
    name='Gold',
    formula='Au',
    metal_class=MetalClass.PRECIOUS_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1064.0,
    thermal_conductivity_W_mK=318.0,
    cte_per_K=14.2,
    elastic_modulus_GPa=79.0,
    yield_strength_MPa=25.0,
    ultimate_tensile_MPa=130.0,
    elongation_pct=45.0,
    hardness_HV=25,
    density_g_cm3=19.32,
    electrical_resistivity_ohm_m=2.44e-8,
    galvanic_potential_V=0.15,
    failure_modes=[],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'thermal': 'Smithells Metals Reference Book, 2004',
    },
    metadata={'note': 'Noble metal; virtually no corrosion'},
)

PURE_METALS['Pt'] = MetalMaterial(
    name='Platinum',
    formula='Pt',
    metal_class=MetalClass.PRECIOUS_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1768.0,
    thermal_conductivity_W_mK=72.0,
    cte_per_K=8.8,
    elastic_modulus_GPa=168.0,
    yield_strength_MPa=50.0,
    ultimate_tensile_MPa=140.0,
    elongation_pct=40.0,
    hardness_HV=40,
    density_g_cm3=21.45,
    electrical_resistivity_ohm_m=1.06e-7,
    galvanic_potential_V=0.20,
    failure_modes=[],
    sources={
        'mechanical': 'ASM Handbook Vol. 2, 1990',
        'galvanic': 'ASTM G82',
    },
    metadata={'note': 'Most noble common metal in galvanic series'},
)


# =============================================================================
# FERROUS ALLOYS
# =============================================================================

FERROUS_ALLOYS: Dict[str, MetalMaterial] = {}

FERROUS_ALLOYS['SS_304'] = MetalMaterial(
    name='304 Stainless Steel',
    formula='Fe-18Cr-8Ni',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1425.0,
    thermal_conductivity_W_mK=16.2,
    cte_per_K=17.3,
    elastic_modulus_GPa=193.0,
    yield_strength_MPa=215.0,
    ultimate_tensile_MPa=505.0,
    elongation_pct=70.0,
    hardness_HV=170,
    fatigue_limit_MPa=240.0,
    density_g_cm3=8.00,
    electrical_resistivity_ohm_m=7.20e-7,
    galvanic_potential_V=-0.08,
    corrosion_rate_mm_yr=0.001,
    failure_modes=[
        MetalFailureMode.PITTING,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.SENSITIZATION,
        MetalFailureMode.INTERGRANULAR_CORROSION,
    ],
    sources={
        'mechanical': 'ASM Handbook; Davis, SS Specialty Handbook, 1994',
        'thermal': 'Davis, SS Specialty Handbook, 1994',
        'galvanic': 'ASTM G82 (passive condition)',
    },
    metadata={'passivating': True},
)

FERROUS_ALLOYS['SS_316'] = MetalMaterial(
    name='316 Stainless Steel',
    formula='Fe-16Cr-10Ni-2Mo',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1390.0,
    thermal_conductivity_W_mK=16.3,
    cte_per_K=16.0,
    elastic_modulus_GPa=193.0,
    yield_strength_MPa=205.0,
    ultimate_tensile_MPa=515.0,
    elongation_pct=60.0,
    hardness_HV=160,
    fatigue_limit_MPa=260.0,
    density_g_cm3=8.00,
    electrical_resistivity_ohm_m=7.40e-7,
    galvanic_potential_V=-0.05,
    corrosion_rate_mm_yr=0.0005,
    failure_modes=[
        MetalFailureMode.PITTING,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'Davis, SS Specialty Handbook, 1994',
        'thermal': 'Davis, SS Specialty Handbook, 1994',
        'galvanic': 'ASTM G82 (passive, Mo improves pitting resistance)',
    },
    metadata={'passivating': True},
)

FERROUS_ALLOYS['Steel_1018'] = MetalMaterial(
    name='1018 Mild Steel',
    formula='Fe-0.18C-0.8Mn',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=1500.0,
    thermal_conductivity_W_mK=51.9,
    cte_per_K=11.7,
    elastic_modulus_GPa=205.0,
    yield_strength_MPa=370.0,
    ultimate_tensile_MPa=440.0,
    elongation_pct=15.0,
    hardness_HV=126,
    fatigue_limit_MPa=220.0,
    density_g_cm3=7.87,
    electrical_resistivity_ohm_m=1.59e-7,
    galvanic_potential_V=-0.60,
    corrosion_rate_mm_yr=0.10,
    failure_modes=[
        MetalFailureMode.GENERAL_CORROSION,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'MatWeb; ASM Handbook Vol. 1',
        'galvanic': 'ASTM G82',
    },
)

FERROUS_ALLOYS['Steel_4140'] = MetalMaterial(
    name='4140 Alloy Steel',
    formula='Fe-0.4C-1Cr-0.2Mo',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=1500.0,
    thermal_conductivity_W_mK=42.7,
    cte_per_K=12.3,
    elastic_modulus_GPa=210.0,
    yield_strength_MPa=655.0,
    ultimate_tensile_MPa=1020.0,
    elongation_pct=18.0,
    hardness_HV=310,
    fatigue_limit_MPa=510.0,
    density_g_cm3=7.85,
    electrical_resistivity_ohm_m=2.22e-7,
    galvanic_potential_V=-0.58,
    corrosion_rate_mm_yr=0.08,
    failure_modes=[
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
        MetalFailureMode.FATIGUE,
        MetalFailureMode.GENERAL_CORROSION,
    ],
    sources={
        'mechanical': 'MatWeb; MIL-HDBK-5J (Q&T condition)',
        'galvanic': 'ASTM G82',
    },
)

FERROUS_ALLOYS['Tool_A2'] = MetalMaterial(
    name='A2 Tool Steel',
    formula='Fe-1C-5Cr-1Mo',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=1420.0,
    thermal_conductivity_W_mK=24.0,
    cte_per_K=10.7,
    elastic_modulus_GPa=210.0,
    yield_strength_MPa=1500.0,
    ultimate_tensile_MPa=1700.0,
    elongation_pct=5.0,
    hardness_HV=600,
    density_g_cm3=7.86,
    electrical_resistivity_ohm_m=6.50e-7,
    galvanic_potential_V=-0.55,
    failure_modes=[
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 1 (hardened condition)',
    },
)

FERROUS_ALLOYS['Maraging_300'] = MetalMaterial(
    name='Maraging 300',
    formula='Fe-18Ni-9Co-5Mo-0.7Ti',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.BCC,
    melting_point_C=1420.0,
    thermal_conductivity_W_mK=25.0,
    cte_per_K=10.1,
    elastic_modulus_GPa=190.0,
    yield_strength_MPa=2000.0,
    ultimate_tensile_MPa=2050.0,
    elongation_pct=8.0,
    hardness_HV=550,
    density_g_cm3=8.10,
    electrical_resistivity_ohm_m=6.00e-7,
    galvanic_potential_V=-0.55,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 1 (aged condition)',
    },
)

FERROUS_ALLOYS['Cast_Iron'] = MetalMaterial(
    name='Gray Cast Iron',
    formula='Fe-3.4C-1.8Si',
    metal_class=MetalClass.FERROUS_ALLOY,
    crystal_system=CrystalSystem.MIXED,
    melting_point_C=1200.0,
    thermal_conductivity_W_mK=46.0,
    cte_per_K=10.5,
    elastic_modulus_GPa=100.0,
    yield_strength_MPa=None,
    ultimate_tensile_MPa=200.0,
    elongation_pct=0.5,
    hardness_HV=200,
    density_g_cm3=7.15,
    electrical_resistivity_ohm_m=5.90e-7,
    galvanic_potential_V=-0.55,
    corrosion_rate_mm_yr=0.08,
    failure_modes=[
        MetalFailureMode.GENERAL_CORROSION,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 1',
    },
    metadata={'note': 'Class 30 gray cast iron; virtually no ductility'},
)


# =============================================================================
# ALUMINUM ALLOYS
# =============================================================================

ALUMINUM_ALLOYS: Dict[str, MetalMaterial] = {}

ALUMINUM_ALLOYS['Al_6061'] = MetalMaterial(
    name='6061-T6 Aluminum',
    formula='Al-1Mg-0.6Si-0.3Cu',
    metal_class=MetalClass.ALUMINUM_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=582.0,
    thermal_conductivity_W_mK=167.0,
    cte_per_K=23.6,
    elastic_modulus_GPa=68.9,
    yield_strength_MPa=276.0,
    ultimate_tensile_MPa=310.0,
    elongation_pct=12.0,
    hardness_HV=107,
    fatigue_limit_MPa=96.0,
    density_g_cm3=2.70,
    electrical_resistivity_ohm_m=3.99e-8,
    galvanic_potential_V=-0.74,
    corrosion_rate_mm_yr=0.005,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.PITTING,
    ],
    sources={
        'mechanical': 'MIL-HDBK-5J; MatWeb',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True},
)

ALUMINUM_ALLOYS['Al_7075'] = MetalMaterial(
    name='7075-T6 Aluminum',
    formula='Al-5.6Zn-2.5Mg-1.6Cu',
    metal_class=MetalClass.ALUMINUM_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=477.0,
    thermal_conductivity_W_mK=130.0,
    cte_per_K=23.4,
    elastic_modulus_GPa=71.7,
    yield_strength_MPa=503.0,
    ultimate_tensile_MPa=572.0,
    elongation_pct=11.0,
    hardness_HV=175,
    fatigue_limit_MPa=159.0,
    density_g_cm3=2.81,
    electrical_resistivity_ohm_m=5.22e-8,
    galvanic_potential_V=-0.73,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'MIL-HDBK-5J; MatWeb',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True, 'note': 'Aerospace standard; highest strength Al alloy'},
)

ALUMINUM_ALLOYS['Al_2024'] = MetalMaterial(
    name='2024-T3 Aluminum',
    formula='Al-4.4Cu-1.5Mg-0.6Mn',
    metal_class=MetalClass.ALUMINUM_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=502.0,
    thermal_conductivity_W_mK=121.0,
    cte_per_K=23.2,
    elastic_modulus_GPa=73.1,
    yield_strength_MPa=345.0,
    ultimate_tensile_MPa=483.0,
    elongation_pct=18.0,
    hardness_HV=137,
    fatigue_limit_MPa=138.0,
    density_g_cm3=2.78,
    electrical_resistivity_ohm_m=5.82e-8,
    galvanic_potential_V=-0.70,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.INTERGRANULAR_CORROSION,
    ],
    sources={
        'mechanical': 'MIL-HDBK-5J; MatWeb',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True},
)

ALUMINUM_ALLOYS['Al_5052'] = MetalMaterial(
    name='5052-H32 Aluminum',
    formula='Al-2.5Mg-0.25Cr',
    metal_class=MetalClass.ALUMINUM_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=607.0,
    thermal_conductivity_W_mK=138.0,
    cte_per_K=23.8,
    elastic_modulus_GPa=70.3,
    yield_strength_MPa=193.0,
    ultimate_tensile_MPa=228.0,
    elongation_pct=12.0,
    hardness_HV=67,
    fatigue_limit_MPa=117.0,
    density_g_cm3=2.68,
    electrical_resistivity_ohm_m=4.99e-8,
    galvanic_potential_V=-0.76,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.PITTING,
    ],
    sources={
        'mechanical': 'MatWeb; ASM Handbook Vol. 2',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True, 'note': 'Best corrosion resistance of common Al alloys'},
)


# =============================================================================
# COPPER ALLOYS
# =============================================================================

COPPER_ALLOYS: Dict[str, MetalMaterial] = {}

COPPER_ALLOYS['Brass_C260'] = MetalMaterial(
    name='Cartridge Brass C260',
    formula='Cu-30Zn',
    metal_class=MetalClass.COPPER_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=915.0,
    thermal_conductivity_W_mK=120.0,
    cte_per_K=20.0,
    elastic_modulus_GPa=110.0,
    yield_strength_MPa=338.0,
    ultimate_tensile_MPa=448.0,
    elongation_pct=23.0,
    hardness_HV=130,
    density_g_cm3=8.53,
    electrical_resistivity_ohm_m=6.20e-8,
    galvanic_potential_V=-0.28,
    failure_modes=[
        MetalFailureMode.DEZINCIFICATION,
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2 (half-hard)',
        'galvanic': 'ASTM G82',
    },
)

COPPER_ALLOYS['Bronze_C510'] = MetalMaterial(
    name='Phosphor Bronze C510',
    formula='Cu-5Sn-0.2P',
    metal_class=MetalClass.COPPER_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1050.0,
    thermal_conductivity_W_mK=84.0,
    cte_per_K=18.0,
    elastic_modulus_GPa=110.0,
    yield_strength_MPa=520.0,
    ultimate_tensile_MPa=560.0,
    elongation_pct=3.0,
    hardness_HV=190,
    density_g_cm3=8.80,
    electrical_resistivity_ohm_m=9.69e-8,
    galvanic_potential_V=-0.24,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'ASM Handbook Vol. 2 (H08 temper)',
        'galvanic': 'ASTM G82',
    },
)

COPPER_ALLOYS['BeCu_C172'] = MetalMaterial(
    name='Beryllium Copper C172',
    formula='Cu-2Be',
    metal_class=MetalClass.COPPER_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=870.0,
    thermal_conductivity_W_mK=115.0,
    cte_per_K=17.0,
    elastic_modulus_GPa=131.0,
    yield_strength_MPa=1035.0,
    ultimate_tensile_MPa=1140.0,
    elongation_pct=4.0,
    hardness_HV=360,
    density_g_cm3=8.25,
    electrical_resistivity_ohm_m=6.78e-8,
    galvanic_potential_V=-0.22,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'Materion C17200 datasheet (age-hardened)',
        'galvanic': 'ASTM G82',
    },
    metadata={'note': 'Non-sparking; used in explosive environments and springs'},
)


# =============================================================================
# TITANIUM ALLOYS
# =============================================================================

TITANIUM_ALLOYS: Dict[str, MetalMaterial] = {}

TITANIUM_ALLOYS['Ti6Al4V'] = MetalMaterial(
    name='Ti-6Al-4V',
    formula='Ti-6Al-4V',
    metal_class=MetalClass.TITANIUM_ALLOY,
    crystal_system=CrystalSystem.HCP,
    melting_point_C=1604.0,
    thermal_conductivity_W_mK=6.7,
    cte_per_K=8.6,
    elastic_modulus_GPa=113.8,
    yield_strength_MPa=880.0,
    ultimate_tensile_MPa=950.0,
    elongation_pct=14.0,
    hardness_HV=334,
    fatigue_limit_MPa=510.0,
    density_g_cm3=4.43,
    electrical_resistivity_ohm_m=1.71e-6,
    galvanic_potential_V=0.00,
    corrosion_rate_mm_yr=0.0001,
    failure_modes=[
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
        MetalFailureMode.FATIGUE,
    ],
    sources={
        'mechanical': 'Boyer et al., Ti Alloys Handbook, 1994',
        'galvanic': 'ASTM G82 (passive)',
    },
    metadata={
        'passivating': True,
        'note': 'Most widely used titanium alloy (alpha-beta); aerospace standard',
    },
)

TITANIUM_ALLOYS['CP_Ti_Gr2'] = MetalMaterial(
    name='CP Titanium Grade 2',
    formula='Ti-0.3Fe-0.25O',
    metal_class=MetalClass.TITANIUM_ALLOY,
    crystal_system=CrystalSystem.HCP,
    melting_point_C=1665.0,
    thermal_conductivity_W_mK=16.4,
    cte_per_K=8.6,
    elastic_modulus_GPa=105.0,
    yield_strength_MPa=275.0,
    ultimate_tensile_MPa=345.0,
    elongation_pct=20.0,
    hardness_HV=200,
    density_g_cm3=4.51,
    electrical_resistivity_ohm_m=5.60e-7,
    galvanic_potential_V=-0.02,
    corrosion_rate_mm_yr=0.0005,
    failure_modes=[
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
    ],
    sources={
        'mechanical': 'Boyer et al., Ti Alloys Handbook, 1994',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True},
)


# =============================================================================
# NICKEL ALLOYS
# =============================================================================

NICKEL_ALLOYS: Dict[str, MetalMaterial] = {}

NICKEL_ALLOYS['Inconel_625'] = MetalMaterial(
    name='Inconel 625',
    formula='Ni-22Cr-9Mo-3.5Nb',
    metal_class=MetalClass.NICKEL_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1290.0,
    thermal_conductivity_W_mK=9.8,
    cte_per_K=12.8,
    elastic_modulus_GPa=205.0,
    yield_strength_MPa=490.0,
    ultimate_tensile_MPa=930.0,
    elongation_pct=42.0,
    hardness_HV=200,
    density_g_cm3=8.44,
    electrical_resistivity_ohm_m=1.29e-6,
    galvanic_potential_V=-0.05,
    corrosion_rate_mm_yr=0.0001,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'Special Metals Inconel 625 datasheet',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True, 'note': 'Excellent corrosion and high-temp resistance'},
)

NICKEL_ALLOYS['Inconel_718'] = MetalMaterial(
    name='Inconel 718',
    formula='Ni-19Cr-18Fe-5Nb-3Mo',
    metal_class=MetalClass.NICKEL_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1260.0,
    thermal_conductivity_W_mK=11.4,
    cte_per_K=13.0,
    elastic_modulus_GPa=200.0,
    yield_strength_MPa=1036.0,
    ultimate_tensile_MPa=1240.0,
    elongation_pct=12.0,
    hardness_HV=385,
    density_g_cm3=8.19,
    electrical_resistivity_ohm_m=1.25e-6,
    galvanic_potential_V=-0.05,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.CREEP,
    ],
    sources={
        'mechanical': 'Special Metals Inconel 718 datasheet (aged)',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True},
)

NICKEL_ALLOYS['Hastelloy_C276'] = MetalMaterial(
    name='Hastelloy C-276',
    formula='Ni-16Cr-16Mo-5Fe-4W',
    metal_class=MetalClass.NICKEL_ALLOY,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1325.0,
    thermal_conductivity_W_mK=10.2,
    cte_per_K=11.2,
    elastic_modulus_GPa=205.0,
    yield_strength_MPa=365.0,
    ultimate_tensile_MPa=790.0,
    elongation_pct=60.0,
    hardness_HV=190,
    density_g_cm3=8.89,
    electrical_resistivity_ohm_m=1.30e-6,
    galvanic_potential_V=0.00,
    corrosion_rate_mm_yr=0.0001,
    failure_modes=[],
    sources={
        'mechanical': 'Haynes Hastelloy C-276 datasheet',
        'galvanic': 'ASTM G82',
    },
    metadata={'passivating': True, 'note': 'Best overall corrosion resistance of Ni alloys'},
)


# =============================================================================
# BATTERY-RELEVANT METALS (specific tempers for battery applications)
# =============================================================================

BATTERY_METALS: Dict[str, MetalMaterial] = {}

BATTERY_METALS['Al_foil'] = MetalMaterial(
    name='Aluminum Foil 1145-O',
    formula='Al (99.45%)',
    metal_class=MetalClass.BATTERY_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=657.0,
    thermal_conductivity_W_mK=234.0,
    cte_per_K=23.6,
    elastic_modulus_GPa=69.0,
    yield_strength_MPa=34.0,
    ultimate_tensile_MPa=97.0,
    elongation_pct=25.0,
    hardness_HV=26,
    density_g_cm3=2.70,
    electrical_resistivity_ohm_m=2.73e-8,
    galvanic_potential_V=-0.76,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
        MetalFailureMode.PITTING,
    ],
    sources={
        'mechanical': 'Novelis 1145-O foil datasheet',
        'galvanic': 'ASTM G82',
    },
    metadata={'battery_role': 'cathode current collector (Li-ion)'},
)

BATTERY_METALS['Cu_foil'] = MetalMaterial(
    name='Copper Foil C110',
    formula='Cu (99.9%)',
    metal_class=MetalClass.BATTERY_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1085.0,
    thermal_conductivity_W_mK=398.0,
    cte_per_K=17.0,
    elastic_modulus_GPa=130.0,
    yield_strength_MPa=69.0,
    ultimate_tensile_MPa=220.0,
    elongation_pct=45.0,
    hardness_HV=40,
    density_g_cm3=8.94,
    electrical_resistivity_ohm_m=1.72e-8,
    galvanic_potential_V=-0.20,
    failure_modes=[
        MetalFailureMode.GALVANIC_CORROSION,
    ],
    sources={
        'mechanical': 'MatWeb C11000 annealed',
        'galvanic': 'ASTM G82',
    },
    metadata={'battery_role': 'anode current collector (Li-ion)'},
)

BATTERY_METALS['Ni_tab'] = MetalMaterial(
    name='Nickel 200 Tab',
    formula='Ni (99.6%)',
    metal_class=MetalClass.BATTERY_METAL,
    crystal_system=CrystalSystem.FCC,
    melting_point_C=1446.0,
    thermal_conductivity_W_mK=70.0,
    cte_per_K=13.4,
    elastic_modulus_GPa=204.0,
    yield_strength_MPa=148.0,
    ultimate_tensile_MPa=462.0,
    elongation_pct=47.0,
    hardness_HV=80,
    density_g_cm3=8.89,
    electrical_resistivity_ohm_m=9.50e-8,
    galvanic_potential_V=-0.10,
    failure_modes=[
        MetalFailureMode.STRESS_CORROSION_CRACKING,
    ],
    sources={
        'mechanical': 'Special Metals Nickel 200 datasheet',
        'galvanic': 'ASTM G82',
    },
    metadata={'battery_role': 'cell tab for welding to bus bars'},
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_METALS: Dict[str, MetalMaterial] = {}
ALL_METALS.update(PURE_METALS)
ALL_METALS.update(FERROUS_ALLOYS)
ALL_METALS.update(ALUMINUM_ALLOYS)
ALL_METALS.update(COPPER_ALLOYS)
ALL_METALS.update(TITANIUM_ALLOYS)
ALL_METALS.update(NICKEL_ALLOYS)
ALL_METALS.update(BATTERY_METALS)


def get_metal(name: str) -> Optional[MetalMaterial]:
    """Look up a metal by name or abbreviation."""
    return ALL_METALS.get(name)


def get_metals_by_class(metal_class: MetalClass) -> Dict[str, MetalMaterial]:
    """Get all metals of a given class."""
    return {k: v for k, v in ALL_METALS.items() if v.metal_class == metal_class}


def list_pure_metals() -> List[str]:
    return list(PURE_METALS.keys())


def list_ferrous_alloys() -> List[str]:
    return list(FERROUS_ALLOYS.keys())


def list_aluminum_alloys() -> List[str]:
    return list(ALUMINUM_ALLOYS.keys())


def list_nickel_alloys() -> List[str]:
    return list(NICKEL_ALLOYS.keys())


# =============================================================================
# KNOWN GOOD/BAD PAIRINGS (for test validation)
# =============================================================================

KNOWN_GOOD_JOINTS = [
    {
        'name': '304SS + 316SS',
        'metal_a': 'SS_304',
        'metal_b': 'SS_316',
        'notes': 'Same austenitic family; nearly identical galvanic potential',
    },
    {
        'name': 'Ti-6Al-4V + CP Ti',
        'metal_a': 'Ti6Al4V',
        'metal_b': 'CP_Ti_Gr2',
        'notes': 'Same base metal; fully compatible',
    },
    {
        'name': 'Cu + Ni',
        'metal_a': 'Cu',
        'metal_b': 'Ni',
        'notes': 'Complete solid solution; both FCC; similar atomic radius',
    },
    {
        'name': 'Cu + Bronze C510',
        'metal_a': 'Cu',
        'metal_b': 'Bronze_C510',
        'notes': 'Same base metal family; Cu-based alloys compatible',
    },
    {
        'name': '6061 + 5052 Aluminum',
        'metal_a': 'Al_6061',
        'metal_b': 'Al_5052',
        'notes': 'Both Al alloys; similar galvanic potential, same crystal structure',
    },
]

KNOWN_BAD_JOINTS = [
    {
        'name': 'Cu + Al (galvanic couple)',
        'metal_a': 'Cu',
        'metal_b': 'Al',
        'issue': 'Large galvanic potential difference (~0.56V); brittle intermetallics form',
    },
    {
        'name': 'Mg + Cu (extreme galvanic)',
        'metal_a': 'Mg',
        'metal_b': 'Cu',
        'issue': 'Extreme galvanic potential difference (~1.4V); Mg rapidly corrodes',
    },
    {
        'name': 'Steel + Al (galvanic + intermetallics)',
        'metal_a': 'Steel_1018',
        'metal_b': 'Al',
        'issue': 'Galvanic couple in wet environments; Fe-Al intermetallics form at interface',
    },
    {
        'name': 'Mg + Steel (galvanic)',
        'metal_a': 'Mg',
        'metal_b': 'Steel_1018',
        'issue': 'Large potential difference (~1.0V); Mg is sacrificial anode',
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("Metal Material Properties - Summary")
    print("=" * 70)
    print()

    categories = [
        ("Pure Metals", PURE_METALS),
        ("Ferrous Alloys", FERROUS_ALLOYS),
        ("Aluminum Alloys", ALUMINUM_ALLOYS),
        ("Copper Alloys", COPPER_ALLOYS),
        ("Titanium Alloys", TITANIUM_ALLOYS),
        ("Nickel Alloys", NICKEL_ALLOYS),
        ("Battery Metals", BATTERY_METALS),
    ]

    for cat_name, cat_dict in categories:
        print(f"{cat_name}: {len(cat_dict)}")
        for name, mat in cat_dict.items():
            galv = f"E={mat.galvanic_potential_V:+.2f}V" if mat.galvanic_potential_V is not None else ""
            tm = f"Tm={mat.melting_point_C:.0f}C" if mat.melting_point_C is not None else ""
            print(f"  {name:16s} ({mat.name:30s}) {tm:12s} {galv}")
        print()

    print(f"Total materials: {len(ALL_METALS)}")
