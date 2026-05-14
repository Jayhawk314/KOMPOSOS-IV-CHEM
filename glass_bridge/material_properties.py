# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Glass Material Properties
============================

Validated property tables for glass materials, analogous to
ceramic_bridge/material_properties.py and semiconductor_bridge/material_properties.py.

Each material entry uses real published values with source citations.

Property Sources:
-----------------
- Shelby, "Introduction to Glass Science and Technology", 2nd ed., 2005
- Varshneya, "Fundamentals of Inorganic Glasses", 2nd ed., 2006
- Schott AG, "Optical Glass Data Sheets" (www.schott.com)
- Corning Inc., product data sheets
- Hench, "Bioceramics", J. Am. Ceram. Soc. 81, 1705 (1998)
- Sanghera & Aggarwal, "Active and Passive Chalcogenide Glass Optical Fibers", 2006
- Bansal & Doremus, "Handbook of Glass Properties", 1986
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class GlassClass(Enum):
    """Classification of glass materials."""
    SODA_LIME = "soda_lime"
    BOROSILICATE = "borosilicate"
    ALUMINOSILICATE = "aluminosilicate"
    LEAD_GLASS = "lead_glass"
    FUSED_SILICA = "fused_silica"
    OPTICAL = "optical"
    BIOACTIVE = "bioactive"
    CHALCOGENIDE = "chalcogenide"
    GLASS_CERAMIC = "glass_ceramic"
    PHOSPHATE = "phosphate"
    FLUORIDE = "fluoride"


class CompositionType(Enum):
    """Glass composition network type."""
    SILICATE = "silicate"
    BORATE = "borate"
    PHOSPHATE = "phosphate"
    CHALCOGENIDE = "chalcogenide"
    FLUORIDE = "fluoride"
    GERMANATE = "germanate"


class GlassFailureMode(Enum):
    """Known failure modes for glasses."""
    THERMAL_SHOCK = "thermal_shock"
    DEVITRIFICATION = "devitrification"
    STRESS_CORROSION = "stress_corrosion"
    WEATHERING = "weathering"
    SOLARIZATION = "solarization"
    PHASE_SEPARATION = "phase_separation"
    ALKALI_LEACHING = "alkali_leaching"
    HYDROLYTIC_ATTACK = "hydrolytic_attack"
    CRYSTALLIZATION = "crystallization"
    BUBBLING = "bubbling"
    SURFACE_BLOOM = "surface_bloom"
    STATIC_FATIGUE = "static_fatigue"


@dataclass
class GlassMaterial:
    """
    A glass material with validated physical properties.

    Analogous to CeramicMaterial / SemiconductorMaterial in other bridges.
    Every numerical value has a source citation.
    """
    name: str
    formula: str
    glass_class: GlassClass
    composition_type: CompositionType

    # Thermal transition temperatures (C)
    Tg_C: Optional[float] = None                   # Glass transition temperature
    softening_point_C: Optional[float] = None       # Littleton softening point
    annealing_point_C: Optional[float] = None       # Strain relief temperature
    working_point_C: Optional[float] = None         # Viscosity = 10^4 poise

    # Thermal
    cte_per_K: Optional[float] = None               # x10^-6 /K (20-300C)
    thermal_conductivity_W_mK: Optional[float] = None

    # Mechanical
    density_g_cm3: Optional[float] = None
    elastic_modulus_GPa: Optional[float] = None
    fracture_toughness_MPa_m05: Optional[float] = None
    hardness_HK: Optional[float] = None             # Knoop hardness
    poisson_ratio: Optional[float] = None

    # Optical
    refractive_index: Optional[float] = None        # nd (at 587.6 nm)
    abbe_number: Optional[float] = None             # Vd (dispersion)
    transmission_range_um: Optional[Tuple[float, float]] = None  # UV-IR window

    # Chemical durability (ISO 695 / DIN 12116 classes, lower = better)
    hydrolytic_class: Optional[int] = None          # 1-5 (HGB 1 = best)
    acid_class: Optional[int] = None                # 1-4
    alkali_class: Optional[int] = None              # 1-3
    weathering_class: Optional[int] = None          # 1-4

    # Failure modes
    failure_modes: List[GlassFailureMode] = field(default_factory=list)

    # Source citations
    sources: Dict[str, str] = field(default_factory=dict)

    # Additional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'formula': self.formula,
            'glass_class': self.glass_class.value,
            'composition_type': self.composition_type.value,
        }
        if self.Tg_C is not None:
            result['Tg_C'] = self.Tg_C
        if self.cte_per_K is not None:
            result['cte_per_K'] = self.cte_per_K
        if self.density_g_cm3 is not None:
            result['density_g_cm3'] = self.density_g_cm3
        if self.refractive_index is not None:
            result['refractive_index'] = self.refractive_index
        if self.abbe_number is not None:
            result['abbe_number'] = self.abbe_number
        if self.elastic_modulus_GPa is not None:
            result['elastic_modulus_GPa'] = self.elastic_modulus_GPa
        if self.failure_modes:
            result['failure_modes'] = [fm.value for fm in self.failure_modes]
        return result


# =============================================================================
# SODA-LIME GLASSES
# =============================================================================

SODA_LIME_GLASSES: Dict[str, GlassMaterial] = {}

SODA_LIME_GLASSES['SodaLime_Float'] = GlassMaterial(
    name='Soda-Lime Float Glass',
    formula='Na2O-CaO-SiO2',
    glass_class=GlassClass.SODA_LIME,
    composition_type=CompositionType.SILICATE,
    Tg_C=564.0,
    softening_point_C=726.0,
    annealing_point_C=546.0,
    working_point_C=1040.0,
    cte_per_K=9.0,
    thermal_conductivity_W_mK=1.0,
    density_g_cm3=2.50,
    elastic_modulus_GPa=72.0,
    fracture_toughness_MPa_m05=0.75,
    hardness_HK=530,
    poisson_ratio=0.22,
    refractive_index=1.518,
    abbe_number=59.0,
    transmission_range_um=(0.32, 4.5),
    hydrolytic_class=3,
    acid_class=2,
    alkali_class=2,
    weathering_class=2,
    failure_modes=[
        GlassFailureMode.THERMAL_SHOCK,
        GlassFailureMode.ALKALI_LEACHING,
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'thermal': 'Bansal & Doremus, Handbook of Glass Properties, 1986',
        'mechanical': 'Varshneya, Fundamentals of Inorganic Glasses, 2006',
        'optical': 'Schott AG product data',
    },
    metadata={'note': 'Most common glass; windows, containers, float process'},
)

SODA_LIME_GLASSES['SodaLime_Container'] = GlassMaterial(
    name='Soda-Lime Container Glass',
    formula='Na2O-CaO-SiO2 (container)',
    glass_class=GlassClass.SODA_LIME,
    composition_type=CompositionType.SILICATE,
    Tg_C=550.0,
    softening_point_C=710.0,
    annealing_point_C=530.0,
    working_point_C=1010.0,
    cte_per_K=9.3,
    thermal_conductivity_W_mK=1.0,
    density_g_cm3=2.52,
    elastic_modulus_GPa=70.0,
    fracture_toughness_MPa_m05=0.72,
    hardness_HK=520,
    poisson_ratio=0.22,
    refractive_index=1.520,
    abbe_number=58.0,
    transmission_range_um=(0.32, 4.5),
    hydrolytic_class=3,
    acid_class=2,
    alkali_class=2,
    weathering_class=2,
    failure_modes=[
        GlassFailureMode.THERMAL_SHOCK,
        GlassFailureMode.ALKALI_LEACHING,
    ],
    sources={
        'general': 'Shelby, Introduction to Glass Science, 2005',
    },
    metadata={'note': 'Bottles and jars; slightly higher alkali than float'},
)

SODA_LIME_GLASSES['SodaLime_Tempered'] = GlassMaterial(
    name='Soda-Lime Tempered (Safety) Glass',
    formula='Na2O-CaO-SiO2 (tempered)',
    glass_class=GlassClass.SODA_LIME,
    composition_type=CompositionType.SILICATE,
    Tg_C=564.0,
    softening_point_C=726.0,
    annealing_point_C=546.0,
    working_point_C=1040.0,
    cte_per_K=9.0,
    thermal_conductivity_W_mK=1.0,
    density_g_cm3=2.50,
    elastic_modulus_GPa=72.0,
    fracture_toughness_MPa_m05=0.75,
    hardness_HK=530,
    poisson_ratio=0.22,
    refractive_index=1.518,
    abbe_number=59.0,
    hydrolytic_class=3,
    acid_class=2,
    alkali_class=2,
    weathering_class=2,
    failure_modes=[
        GlassFailureMode.ALKALI_LEACHING,
    ],
    sources={
        'general': 'Varshneya, 2006',
    },
    metadata={'note': 'Thermally tempered; 4x bend strength; auto glass, shower doors'},
)


# =============================================================================
# BOROSILICATE GLASSES
# =============================================================================

BOROSILICATE_GLASSES: Dict[str, GlassMaterial] = {}

BOROSILICATE_GLASSES['Boro_33'] = GlassMaterial(
    name='Borosilicate 3.3 (Pyrex/Duran type)',
    formula='B2O3-SiO2-Na2O-Al2O3',
    glass_class=GlassClass.BOROSILICATE,
    composition_type=CompositionType.SILICATE,
    Tg_C=525.0,
    softening_point_C=820.0,
    annealing_point_C=560.0,
    working_point_C=1260.0,
    cte_per_K=3.3,
    thermal_conductivity_W_mK=1.14,
    density_g_cm3=2.23,
    elastic_modulus_GPa=63.0,
    fracture_toughness_MPa_m05=0.76,
    hardness_HK=480,
    poisson_ratio=0.20,
    refractive_index=1.474,
    abbe_number=65.0,
    transmission_range_um=(0.30, 4.5),
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    weathering_class=1,
    failure_modes=[
        GlassFailureMode.PHASE_SEPARATION,
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Schott AG, DURAN data sheet',
        'thermal': 'Shelby, 2005',
    },
    metadata={'note': 'Lab glass, cookware, chemical apparatus; low CTE'},
)

BOROSILICATE_GLASSES['Boro_51'] = GlassMaterial(
    name='Borosilicate 5.1 (Vycor-process type)',
    formula='B2O3-SiO2-Na2O (high-B)',
    glass_class=GlassClass.BOROSILICATE,
    composition_type=CompositionType.SILICATE,
    Tg_C=480.0,
    softening_point_C=710.0,
    annealing_point_C=510.0,
    cte_per_K=5.1,
    thermal_conductivity_W_mK=1.05,
    density_g_cm3=2.36,
    elastic_modulus_GPa=56.0,
    fracture_toughness_MPa_m05=0.68,
    hardness_HK=440,
    poisson_ratio=0.21,
    refractive_index=1.490,
    abbe_number=62.0,
    hydrolytic_class=2,
    acid_class=1,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.PHASE_SEPARATION,
    ],
    sources={
        'general': 'Shelby, 2005; Bansal & Doremus, 1986',
    },
    metadata={'note': 'Higher B2O3 content; used for sealing applications'},
)

BOROSILICATE_GLASSES['Boro_Neutral'] = GlassMaterial(
    name='Neutral Pharmaceutical Borosilicate',
    formula='B2O3-SiO2-Na2O-Al2O3 (Type I)',
    glass_class=GlassClass.BOROSILICATE,
    composition_type=CompositionType.SILICATE,
    Tg_C=565.0,
    softening_point_C=830.0,
    annealing_point_C=570.0,
    cte_per_K=4.9,
    thermal_conductivity_W_mK=1.10,
    density_g_cm3=2.34,
    elastic_modulus_GPa=68.0,
    fracture_toughness_MPa_m05=0.74,
    hardness_HK=490,
    poisson_ratio=0.20,
    refractive_index=1.487,
    abbe_number=64.0,
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Schott AG, Fiolax data sheet; USP Type I',
    },
    metadata={'note': 'Pharma vials, ampoules; USP Type I hydrolytic resistance'},
)


# =============================================================================
# ALUMINOSILICATE GLASSES
# =============================================================================

ALUMINOSILICATE_GLASSES: Dict[str, GlassMaterial] = {}

ALUMINOSILICATE_GLASSES['AlSi_Display'] = GlassMaterial(
    name='Aluminosilicate Display Glass (Eagle XG type)',
    formula='Al2O3-B2O3-SiO2 (alkali-free)',
    glass_class=GlassClass.ALUMINOSILICATE,
    composition_type=CompositionType.SILICATE,
    Tg_C=669.0,
    softening_point_C=971.0,
    annealing_point_C=722.0,
    cte_per_K=3.2,
    thermal_conductivity_W_mK=1.09,
    density_g_cm3=2.38,
    elastic_modulus_GPa=73.6,
    fracture_toughness_MPa_m05=0.70,
    hardness_HK=545,
    poisson_ratio=0.23,
    refractive_index=1.510,
    abbe_number=59.0,
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    weathering_class=1,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Corning Eagle XG data sheet',
    },
    metadata={'note': 'LCD/OLED substrates; alkali-free to prevent ion migration'},
)

ALUMINOSILICATE_GLASSES['AlSi_ChemStrength'] = GlassMaterial(
    name='Chemically Strengthened Aluminosilicate (Gorilla type)',
    formula='Na2O-Al2O3-SiO2',
    glass_class=GlassClass.ALUMINOSILICATE,
    composition_type=CompositionType.SILICATE,
    Tg_C=615.0,
    softening_point_C=900.0,
    annealing_point_C=630.0,
    cte_per_K=7.8,
    thermal_conductivity_W_mK=1.0,
    density_g_cm3=2.44,
    elastic_modulus_GPa=71.5,
    fracture_toughness_MPa_m05=0.68,
    hardness_HK=590,
    poisson_ratio=0.22,
    refractive_index=1.509,
    abbe_number=58.0,
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Corning Gorilla Glass data sheet',
        'ion_exchange': 'Varshneya, J. Non-Cryst. Solids 356, 2289, 2010',
    },
    metadata={'note': 'Phone/tablet screens; K-for-Na ion exchange in molten KNO3'},
)


# =============================================================================
# LEAD GLASSES
# =============================================================================

LEAD_GLASSES: Dict[str, GlassMaterial] = {}

LEAD_GLASSES['Lead_Crystal'] = GlassMaterial(
    name='Lead Crystal Glass (24% PbO)',
    formula='PbO-SiO2-K2O',
    glass_class=GlassClass.LEAD_GLASS,
    composition_type=CompositionType.SILICATE,
    Tg_C=440.0,
    softening_point_C=630.0,
    annealing_point_C=450.0,
    working_point_C=985.0,
    cte_per_K=9.1,
    thermal_conductivity_W_mK=0.87,
    density_g_cm3=3.10,
    elastic_modulus_GPa=60.0,
    fracture_toughness_MPa_m05=0.55,
    hardness_HK=400,
    poisson_ratio=0.23,
    refractive_index=1.560,
    abbe_number=41.0,
    hydrolytic_class=2,
    acid_class=3,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.THERMAL_SHOCK,
        GlassFailureMode.WEATHERING,
        GlassFailureMode.ALKALI_LEACHING,
    ],
    sources={
        'general': 'Shelby, 2005; Bansal & Doremus, 1986',
    },
    metadata={'note': 'Stemware, chandeliers; high brilliance; Pb leaching concern'},
)

LEAD_GLASSES['Lead_Dense_Flint'] = GlassMaterial(
    name='Dense Flint Glass (SF11 type)',
    formula='PbO-SiO2 (high PbO)',
    glass_class=GlassClass.LEAD_GLASS,
    composition_type=CompositionType.SILICATE,
    Tg_C=424.0,
    softening_point_C=587.0,
    annealing_point_C=437.0,
    cte_per_K=8.8,
    thermal_conductivity_W_mK=0.74,
    density_g_cm3=4.74,
    elastic_modulus_GPa=55.0,
    fracture_toughness_MPa_m05=0.50,
    hardness_HK=350,
    poisson_ratio=0.25,
    refractive_index=1.785,
    abbe_number=25.8,
    hydrolytic_class=2,
    acid_class=4,
    failure_modes=[
        GlassFailureMode.THERMAL_SHOCK,
        GlassFailureMode.WEATHERING,
        GlassFailureMode.SURFACE_BLOOM,
    ],
    sources={
        'general': 'Schott SF11 data sheet',
    },
    metadata={'note': 'High-dispersion optical element; high refractive index'},
)


# =============================================================================
# FUSED SILICA / QUARTZ
# =============================================================================

FUSED_SILICA_GLASSES: Dict[str, GlassMaterial] = {}

FUSED_SILICA_GLASSES['FusedSilica'] = GlassMaterial(
    name='Fused Silica (Suprasil type)',
    formula='SiO2',
    glass_class=GlassClass.FUSED_SILICA,
    composition_type=CompositionType.SILICATE,
    Tg_C=1200.0,
    softening_point_C=1665.0,
    annealing_point_C=1215.0,
    working_point_C=1800.0,
    cte_per_K=0.55,
    thermal_conductivity_W_mK=1.38,
    density_g_cm3=2.20,
    elastic_modulus_GPa=73.0,
    fracture_toughness_MPa_m05=0.79,
    hardness_HK=600,
    poisson_ratio=0.17,
    refractive_index=1.458,
    abbe_number=67.8,
    transmission_range_um=(0.17, 3.5),
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=3,
    weathering_class=1,
    failure_modes=[
        GlassFailureMode.SOLARIZATION,
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Heraeus Suprasil data sheet',
        'thermal': 'Shelby, 2005',
        'optical': 'Malitson, JOSA 55, 1205, 1965',
    },
    metadata={'note': 'Purest glass; UV optics, fiber preforms, semiconductor lithography'},
)

FUSED_SILICA_GLASSES['QuartzGlass'] = GlassMaterial(
    name='Quartz Glass (IR grade)',
    formula='SiO2 (IR)',
    glass_class=GlassClass.FUSED_SILICA,
    composition_type=CompositionType.SILICATE,
    Tg_C=1200.0,
    softening_point_C=1665.0,
    annealing_point_C=1215.0,
    cte_per_K=0.55,
    thermal_conductivity_W_mK=1.38,
    density_g_cm3=2.20,
    elastic_modulus_GPa=73.0,
    fracture_toughness_MPa_m05=0.79,
    hardness_HK=600,
    poisson_ratio=0.17,
    refractive_index=1.458,
    abbe_number=67.8,
    transmission_range_um=(0.26, 3.5),
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=3,
    weathering_class=1,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Heraeus Infrasil data sheet',
    },
    metadata={'note': 'Lower OH content for IR transmission; furnace tubes'},
)


# =============================================================================
# OPTICAL GLASSES
# =============================================================================

OPTICAL_GLASSES: Dict[str, GlassMaterial] = {}

OPTICAL_GLASSES['BK7'] = GlassMaterial(
    name='BK7 (Borosilicate Crown)',
    formula='B2O3-SiO2-Na2O (BK7)',
    glass_class=GlassClass.OPTICAL,
    composition_type=CompositionType.SILICATE,
    Tg_C=557.0,
    softening_point_C=719.0,
    annealing_point_C=559.0,
    cte_per_K=7.1,
    thermal_conductivity_W_mK=1.11,
    density_g_cm3=2.51,
    elastic_modulus_GPa=82.0,
    fracture_toughness_MPa_m05=0.85,
    hardness_HK=610,
    poisson_ratio=0.21,
    refractive_index=1.5168,
    abbe_number=64.17,
    transmission_range_um=(0.31, 2.5),
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    weathering_class=1,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Schott N-BK7 data sheet',
    },
    metadata={'note': 'Most common optical glass; lenses, prisms, windows'},
)

OPTICAL_GLASSES['F2'] = GlassMaterial(
    name='F2 (Flint Glass)',
    formula='PbO-SiO2-K2O (F2)',
    glass_class=GlassClass.OPTICAL,
    composition_type=CompositionType.SILICATE,
    Tg_C=438.0,
    softening_point_C=592.0,
    annealing_point_C=440.0,
    cte_per_K=8.2,
    thermal_conductivity_W_mK=0.78,
    density_g_cm3=3.60,
    elastic_modulus_GPa=57.0,
    fracture_toughness_MPa_m05=0.55,
    hardness_HK=420,
    poisson_ratio=0.22,
    refractive_index=1.6200,
    abbe_number=36.37,
    transmission_range_um=(0.35, 2.5),
    hydrolytic_class=2,
    acid_class=3,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.WEATHERING,
        GlassFailureMode.SURFACE_BLOOM,
    ],
    sources={
        'general': 'Schott N-F2 data sheet',
    },
    metadata={'note': 'Standard flint glass; high dispersion for achromats'},
)

OPTICAL_GLASSES['LAK9'] = GlassMaterial(
    name='LAK9 (Lanthanum Crown)',
    formula='La2O3-B2O3-SiO2',
    glass_class=GlassClass.OPTICAL,
    composition_type=CompositionType.SILICATE,
    Tg_C=583.0,
    softening_point_C=734.0,
    annealing_point_C=589.0,
    cte_per_K=6.3,
    thermal_conductivity_W_mK=0.83,
    density_g_cm3=3.51,
    elastic_modulus_GPa=110.0,
    fracture_toughness_MPa_m05=0.70,
    hardness_HK=560,
    poisson_ratio=0.29,
    refractive_index=1.6910,
    abbe_number=54.71,
    hydrolytic_class=1,
    acid_class=2,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.STATIC_FATIGUE,
    ],
    sources={
        'general': 'Schott N-LAK9 data sheet',
    },
    metadata={'note': 'High-index, low-dispersion; camera lenses, microscope objectives'},
)


# =============================================================================
# BIOACTIVE GLASSES
# =============================================================================

BIOACTIVE_GLASSES: Dict[str, GlassMaterial] = {}

BIOACTIVE_GLASSES['Bioglass_45S5'] = GlassMaterial(
    name='45S5 Bioglass (Hench)',
    formula='45SiO2-24.5Na2O-24.5CaO-6P2O5',
    glass_class=GlassClass.BIOACTIVE,
    composition_type=CompositionType.SILICATE,
    Tg_C=538.0,
    softening_point_C=600.0,
    annealing_point_C=500.0,
    cte_per_K=15.1,
    thermal_conductivity_W_mK=1.35,
    density_g_cm3=2.72,
    elastic_modulus_GPa=35.0,
    fracture_toughness_MPa_m05=0.40,
    hardness_HK=460,
    poisson_ratio=0.24,
    refractive_index=1.540,
    hydrolytic_class=5,
    failure_modes=[
        GlassFailureMode.CRYSTALLIZATION,
        GlassFailureMode.HYDROLYTIC_ATTACK,
        GlassFailureMode.DEVITRIFICATION,
    ],
    sources={
        'general': 'Hench, J. Am. Ceram. Soc. 81, 1705, 1998',
        'thermal': 'Shelby, 2005',
    },
    metadata={'note': 'First bioactive glass; bonds to bone; FDA-approved for dental/ortho'},
)

BIOACTIVE_GLASSES['S53P4'] = GlassMaterial(
    name='S53P4 BonAlive',
    formula='53SiO2-23Na2O-20CaO-4P2O5',
    glass_class=GlassClass.BIOACTIVE,
    composition_type=CompositionType.SILICATE,
    Tg_C=548.0,
    softening_point_C=610.0,
    annealing_point_C=510.0,
    cte_per_K=14.0,
    thermal_conductivity_W_mK=1.30,
    density_g_cm3=2.66,
    elastic_modulus_GPa=38.0,
    fracture_toughness_MPa_m05=0.42,
    hardness_HK=470,
    refractive_index=1.535,
    hydrolytic_class=5,
    failure_modes=[
        GlassFailureMode.CRYSTALLIZATION,
        GlassFailureMode.HYDROLYTIC_ATTACK,
    ],
    sources={
        'general': 'Andersson et al., J. Mater. Sci. Mater. Med. 1, 219, 1990',
    },
    metadata={'note': 'Antibacterial bioactive glass; bone graft substitute'},
)


# =============================================================================
# CHALCOGENIDE GLASSES
# =============================================================================

CHALCOGENIDE_GLASSES: Dict[str, GlassMaterial] = {}

CHALCOGENIDE_GLASSES['As2S3'] = GlassMaterial(
    name='Arsenic Trisulfide',
    formula='As2S3',
    glass_class=GlassClass.CHALCOGENIDE,
    composition_type=CompositionType.CHALCOGENIDE,
    Tg_C=210.0,
    softening_point_C=310.0,
    cte_per_K=24.6,
    thermal_conductivity_W_mK=0.17,
    density_g_cm3=3.20,
    elastic_modulus_GPa=15.8,
    fracture_toughness_MPa_m05=0.25,
    hardness_HK=130,
    poisson_ratio=0.30,
    refractive_index=2.40,
    abbe_number=150.0,
    transmission_range_um=(0.6, 11.0),
    hydrolytic_class=1,
    failure_modes=[
        GlassFailureMode.CRYSTALLIZATION,
        GlassFailureMode.SOLARIZATION,
    ],
    sources={
        'general': 'Sanghera & Aggarwal, 2006',
        'optical': 'Hilton, J. Non-Cryst. Solids 2, 28, 1970',
    },
    metadata={'note': 'Mid-IR optics and fibers; photosensitive; toxic'},
)

CHALCOGENIDE_GLASSES['Ge28Sb12Se60'] = GlassMaterial(
    name='Germanium-Antimony-Selenide (IG6 type)',
    formula='Ge28Sb12Se60',
    glass_class=GlassClass.CHALCOGENIDE,
    composition_type=CompositionType.CHALCOGENIDE,
    Tg_C=285.0,
    softening_point_C=390.0,
    cte_per_K=14.0,
    thermal_conductivity_W_mK=0.20,
    density_g_cm3=4.63,
    elastic_modulus_GPa=22.0,
    fracture_toughness_MPa_m05=0.30,
    hardness_HK=170,
    poisson_ratio=0.27,
    refractive_index=2.60,
    abbe_number=100.0,
    transmission_range_um=(0.8, 14.0),
    failure_modes=[
        GlassFailureMode.CRYSTALLIZATION,
    ],
    sources={
        'general': 'Amorphous Materials Inc, AMTIR-6 data sheet',
        'optical': 'Sanghera & Aggarwal, 2006',
    },
    metadata={'note': 'Thermal imaging optics; broader IR transmission than sulfide'},
)


# =============================================================================
# GLASS-CERAMICS
# =============================================================================

GLASS_CERAMIC_MATERIALS: Dict[str, GlassMaterial] = {}

GLASS_CERAMIC_MATERIALS['LAS_Zerodur'] = GlassMaterial(
    name='LAS Glass-Ceramic (Zerodur type)',
    formula='Li2O-Al2O3-SiO2 (glass-ceramic)',
    glass_class=GlassClass.GLASS_CERAMIC,
    composition_type=CompositionType.SILICATE,
    Tg_C=660.0,
    softening_point_C=None,
    annealing_point_C=700.0,
    cte_per_K=0.05,
    thermal_conductivity_W_mK=1.46,
    density_g_cm3=2.53,
    elastic_modulus_GPa=90.3,
    fracture_toughness_MPa_m05=0.90,
    hardness_HK=620,
    poisson_ratio=0.24,
    refractive_index=1.542,
    hydrolytic_class=1,
    acid_class=1,
    alkali_class=2,
    failure_modes=[
        GlassFailureMode.DEVITRIFICATION,
    ],
    sources={
        'general': 'Schott Zerodur data sheet',
        'thermal': 'Petzoldt, Phys. Chem. Glasses 8, 1, 1967',
    },
    metadata={'note': 'Near-zero CTE; telescope mirrors, precision optics, ring laser gyros'},
)

GLASS_CERAMIC_MATERIALS['LAS_Cooktop'] = GlassMaterial(
    name='LAS Glass-Ceramic (Cooktop type)',
    formula='Li2O-Al2O3-SiO2 (cooktop)',
    glass_class=GlassClass.GLASS_CERAMIC,
    composition_type=CompositionType.SILICATE,
    Tg_C=680.0,
    annealing_point_C=720.0,
    cte_per_K=0.15,
    thermal_conductivity_W_mK=1.60,
    density_g_cm3=2.56,
    elastic_modulus_GPa=92.0,
    fracture_toughness_MPa_m05=1.50,
    hardness_HK=640,
    poisson_ratio=0.24,
    refractive_index=None,
    hydrolytic_class=1,
    acid_class=1,
    failure_modes=[
        GlassFailureMode.DEVITRIFICATION,
    ],
    sources={
        'general': 'Schott Ceran data sheet',
    },
    metadata={'note': 'Cooktop panels; transmits IR, resists thermal shock'},
)


# =============================================================================
# PHOSPHATE GLASSES
# =============================================================================

PHOSPHATE_GLASSES: Dict[str, GlassMaterial] = {}

PHOSPHATE_GLASSES['LaserPhosphate'] = GlassMaterial(
    name='Nd-doped Laser Phosphate Glass (LG-770 type)',
    formula='P2O5-Al2O3-K2O (Nd:glass)',
    glass_class=GlassClass.PHOSPHATE,
    composition_type=CompositionType.PHOSPHATE,
    Tg_C=485.0,
    softening_point_C=620.0,
    cte_per_K=12.2,
    thermal_conductivity_W_mK=0.56,
    density_g_cm3=2.83,
    elastic_modulus_GPa=50.0,
    fracture_toughness_MPa_m05=0.46,
    hardness_HK=340,
    poisson_ratio=0.26,
    refractive_index=1.526,
    abbe_number=68.0,
    transmission_range_um=(0.30, 4.0),
    hydrolytic_class=4,
    failure_modes=[
        GlassFailureMode.HYDROLYTIC_ATTACK,
        GlassFailureMode.WEATHERING,
    ],
    sources={
        'general': 'Schott LG-770 data sheet; Campbell & Suratwala, J. Non-Cryst. Solids 263, 318, 2000',
    },
    metadata={'note': 'Nd:glass lasers (NIF); low cross-relaxation; poor chemical durability'},
)


# =============================================================================
# FLUORIDE GLASSES
# =============================================================================

FLUORIDE_GLASSES: Dict[str, GlassMaterial] = {}

FLUORIDE_GLASSES['ZBLAN'] = GlassMaterial(
    name='ZBLAN Fluoride Glass',
    formula='ZrF4-BaF2-LaF3-AlF3-NaF',
    glass_class=GlassClass.FLUORIDE,
    composition_type=CompositionType.FLUORIDE,
    Tg_C=260.0,
    softening_point_C=380.0,
    cte_per_K=17.2,
    thermal_conductivity_W_mK=0.77,
    density_g_cm3=4.33,
    elastic_modulus_GPa=53.0,
    fracture_toughness_MPa_m05=0.30,
    hardness_HK=250,
    poisson_ratio=0.31,
    refractive_index=1.499,
    abbe_number=80.0,
    transmission_range_um=(0.22, 7.0),
    hydrolytic_class=3,
    failure_modes=[
        GlassFailureMode.CRYSTALLIZATION,
        GlassFailureMode.HYDROLYTIC_ATTACK,
    ],
    sources={
        'general': 'Poulain et al., Mat. Res. Bull. 10, 243, 1975',
        'optical': 'France et al., J. Non-Cryst. Solids 51, 307, 1982',
    },
    metadata={'note': 'Mid-IR fibers; low phonon energy; microgravity interest'},
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_GLASSES: Dict[str, GlassMaterial] = {}
ALL_GLASSES.update(SODA_LIME_GLASSES)
ALL_GLASSES.update(BOROSILICATE_GLASSES)
ALL_GLASSES.update(ALUMINOSILICATE_GLASSES)
ALL_GLASSES.update(LEAD_GLASSES)
ALL_GLASSES.update(FUSED_SILICA_GLASSES)
ALL_GLASSES.update(OPTICAL_GLASSES)
ALL_GLASSES.update(BIOACTIVE_GLASSES)
ALL_GLASSES.update(CHALCOGENIDE_GLASSES)
ALL_GLASSES.update(GLASS_CERAMIC_MATERIALS)
ALL_GLASSES.update(PHOSPHATE_GLASSES)
ALL_GLASSES.update(FLUORIDE_GLASSES)


def get_glass(name: str) -> Optional[GlassMaterial]:
    """Look up a glass by name or abbreviation."""
    return ALL_GLASSES.get(name)


def get_glasses_by_class(
    gc: GlassClass,
) -> Dict[str, GlassMaterial]:
    """Get all glasses of a given class."""
    return {k: v for k, v in ALL_GLASSES.items()
            if v.glass_class == gc}


def list_soda_lime() -> List[str]:
    return list(SODA_LIME_GLASSES.keys())


def list_borosilicate() -> List[str]:
    return list(BOROSILICATE_GLASSES.keys())


def list_optical() -> List[str]:
    return list(OPTICAL_GLASSES.keys())


def list_bioactive() -> List[str]:
    return list(BIOACTIVE_GLASSES.keys())


def list_chalcogenide() -> List[str]:
    return list(CHALCOGENIDE_GLASSES.keys())


# =============================================================================
# KNOWN GOOD/BAD ASSEMBLIES (for test validation)
# =============================================================================

KNOWN_GOOD_ASSEMBLIES = [
    {
        'name': 'BK7 + F2 achromat',
        'glass_a': 'BK7',
        'glass_b': 'F2',
        'notes': 'Standard achromatic doublet; crown + flint corrects chromatic aberration',
    },
    {
        'name': 'Fused Silica + BK7 optical assembly',
        'glass_a': 'FusedSilica',
        'glass_b': 'BK7',
        'notes': 'Common optical system combination; both excellent optical quality',
    },
    {
        'name': 'Boro 3.3 + Boro 5.1 graded seal',
        'glass_a': 'Boro_33',
        'glass_b': 'Boro_51',
        'notes': 'Intermediate CTE for graded glass-to-metal seals',
    },
    {
        'name': 'Soda-lime + soda-lime (same type)',
        'glass_a': 'SodaLime_Float',
        'glass_b': 'SodaLime_Container',
        'notes': 'Same glass family; trivially compatible',
    },
    {
        'name': 'LAS Zerodur + Fused Silica (precision)',
        'glass_a': 'LAS_Zerodur',
        'glass_b': 'FusedSilica',
        'notes': 'Both ultra-low CTE; precision optical assemblies',
    },
]

KNOWN_BAD_ASSEMBLIES = [
    {
        'name': 'Fused Silica + Soda-Lime',
        'glass_a': 'FusedSilica',
        'glass_b': 'SodaLime_Float',
        'issue': 'CTE mismatch: 0.55 vs 9.0 x10^-6/K; extreme thermal stress at seal',
    },
    {
        'name': 'Chalcogenide + Borosilicate',
        'glass_a': 'As2S3',
        'glass_b': 'Boro_33',
        'issue': 'Extreme CTE mismatch (24.6 vs 3.3); incompatible working temps; chemical incompatibility',
    },
    {
        'name': 'Bioglass + Fused Silica',
        'glass_a': 'Bioglass_45S5',
        'glass_b': 'FusedSilica',
        'issue': 'CTE mismatch (15.1 vs 0.55); bioglass intentionally dissolves',
    },
    {
        'name': 'ZBLAN + Soda-Lime',
        'glass_a': 'ZBLAN',
        'glass_b': 'SodaLime_Float',
        'issue': 'Fluoride + silicate incompatible chemistry; extreme working temp gap',
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("Glass Material Properties - Summary")
    print("=" * 70)
    print()

    categories = [
        ("Soda-Lime", SODA_LIME_GLASSES),
        ("Borosilicate", BOROSILICATE_GLASSES),
        ("Aluminosilicate", ALUMINOSILICATE_GLASSES),
        ("Lead", LEAD_GLASSES),
        ("Fused Silica", FUSED_SILICA_GLASSES),
        ("Optical", OPTICAL_GLASSES),
        ("Bioactive", BIOACTIVE_GLASSES),
        ("Chalcogenide", CHALCOGENIDE_GLASSES),
        ("Glass-Ceramic", GLASS_CERAMIC_MATERIALS),
        ("Phosphate", PHOSPHATE_GLASSES),
        ("Fluoride", FLUORIDE_GLASSES),
    ]

    for cat_name, cat_dict in categories:
        print(f"{cat_name}: {len(cat_dict)}")
        for name, mat in cat_dict.items():
            nd = f"nd={mat.refractive_index}" if mat.refractive_index is not None else ""
            cte = f"CTE={mat.cte_per_K}" if mat.cte_per_K is not None else ""
            print(f"  {name:24s} ({mat.name:48s}) {nd:12s} {cte}")
        print()

    print(f"Total glasses: {len(ALL_GLASSES)}")
