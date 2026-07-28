# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Ceramic Material Properties
============================

Validated property tables for ceramics, analogous to
metal_bridge/material_properties.py.

Each material entry uses real published values with source citations.

Property Sources:
-----------------
- Kingery, Bowen & Uhlmann, "Introduction to Ceramics" 2nd ed., 1976
- Munro, "Material Properties of a Sintered alpha-SiC", NIST, 1997
- ASM International, "Engineered Materials Handbook Vol. 4: Ceramics and Glasses", 1991
- Richerson, "Modern Ceramic Engineering", 3rd ed., 2005
- Carter & Norton, "Ceramic Materials: Science and Engineering", 2007
- CoorsTek, Saint-Gobain, Kyocera technical datasheets
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class CeramicClass(Enum):
    """Classification of ceramic materials."""
    OXIDE = "oxide"
    CARBIDE = "carbide"
    NITRIDE = "nitride"
    BORIDE = "boride"
    GLASS = "glass"
    BIOCERAMIC = "bioceramic"
    PIEZOELECTRIC = "piezoelectric"
    SOLID_ELECTROLYTE = "solid_electrolyte"


class CrystalSystem(Enum):
    """Crystal structure at room temperature."""
    CUBIC = "cubic"
    HEXAGONAL = "hexagonal"
    TETRAGONAL = "tetragonal"
    RHOMBOHEDRAL = "rhombohedral"
    ORTHORHOMBIC = "orthorhombic"
    MONOCLINIC = "monoclinic"
    AMORPHOUS = "amorphous"
    MIXED = "mixed"


class CeramicFailureMode(Enum):
    """Known failure modes for ceramics."""
    BRITTLE_FRACTURE = "brittle_fracture"
    THERMAL_SHOCK = "thermal_shock"
    CREEP = "creep"
    OXIDATION = "oxidation"
    HYDROLYSIS = "hydrolysis"
    PHASE_TRANSFORMATION = "phase_transformation"
    GRAIN_BOUNDARY_ATTACK = "grain_boundary_attack"
    SUBCRITICAL_CRACK_GROWTH = "subcritical_crack_growth"
    CORROSION = "corrosion"
    DECOMPOSITION = "decomposition"
    DELAMINATION = "delamination"
    WEAR = "wear"


@dataclass
class CeramicMaterial:
    """
    A ceramic material with validated physical properties.

    Analogous to MetalMaterial in metal_bridge/material_properties.py.
    Every numerical value has a source citation.
    """
    name: str
    formula: str
    ceramic_class: CeramicClass
    crystal_system: CrystalSystem

    # Thermal
    melting_point_C: Optional[float] = None       # Or decomposition temp
    sintering_temp_C: Optional[float] = None      # Typical sintering temperature
    max_use_temp_C: Optional[float] = None        # Max continuous service temp
    thermal_conductivity_W_mK: Optional[float] = None
    cte_per_K: Optional[float] = None             # x10^-6 /K

    # Mechanical
    elastic_modulus_GPa: Optional[float] = None
    hardness_HV: Optional[float] = None           # Vickers hardness (or equivalent)
    fracture_toughness_MPa_m05: Optional[float] = None  # K_IC in MPa*sqrt(m)
    flexural_strength_MPa: Optional[float] = None
    compressive_strength_MPa: Optional[float] = None

    # Physical
    density_g_cm3: Optional[float] = None

    # Electrical
    dielectric_constant: Optional[float] = None
    band_gap_eV: Optional[float] = None
    electrical_resistivity_ohm_m: Optional[float] = None

    # Chemical
    chemical_stability: Optional[str] = None   # "inert", "stable", "reactive", "hygroscopic"

    # Failure modes
    failure_modes: List[CeramicFailureMode] = field(default_factory=list)

    # Source citations
    sources: Dict[str, str] = field(default_factory=dict)

    # Additional metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'formula': self.formula,
            'ceramic_class': self.ceramic_class.value,
            'crystal_system': self.crystal_system.value,
        }
        if self.melting_point_C is not None:
            result['melting_point_C'] = self.melting_point_C
        if self.sintering_temp_C is not None:
            result['sintering_temp_C'] = self.sintering_temp_C
        if self.max_use_temp_C is not None:
            result['max_use_temp_C'] = self.max_use_temp_C
        if self.elastic_modulus_GPa is not None:
            result['elastic_modulus_GPa'] = self.elastic_modulus_GPa
        if self.fracture_toughness_MPa_m05 is not None:
            result['fracture_toughness_MPa_m05'] = self.fracture_toughness_MPa_m05
        if self.cte_per_K is not None:
            result['cte_per_K'] = self.cte_per_K
        if self.density_g_cm3 is not None:
            result['density_g_cm3'] = self.density_g_cm3
        if self.failure_modes:
            result['failure_modes'] = [fm.value for fm in self.failure_modes]
        return result


# =============================================================================
# OXIDE CERAMICS
# =============================================================================

OXIDE_CERAMICS: Dict[str, CeramicMaterial] = {}

OXIDE_CERAMICS['Al2O3'] = CeramicMaterial(
    name='Alumina (99.5%)',
    formula='Al2O3',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.RHOMBOHEDRAL,
    melting_point_C=2072.0,
    sintering_temp_C=1600.0,
    max_use_temp_C=1750.0,
    thermal_conductivity_W_mK=35.0,
    cte_per_K=8.1,
    elastic_modulus_GPa=380.0,
    hardness_HV=1500,
    fracture_toughness_MPa_m05=3.5,
    flexural_strength_MPa=380.0,
    compressive_strength_MPa=2600.0,
    density_g_cm3=3.96,
    dielectric_constant=9.8,
    band_gap_eV=8.8,
    electrical_resistivity_ohm_m=1e14,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.THERMAL_SHOCK,
    ],
    sources={
        'mechanical': 'CoorsTek AD-995 datasheet; ASM Eng. Mat. Handbook Vol. 4',
        'thermal': 'Kingery et al., Introduction to Ceramics, 1976',
        'electrical': 'Richerson, Modern Ceramic Engineering, 2005',
    },
    metadata={'note': 'Most widely used structural oxide ceramic'},
)

OXIDE_CERAMICS['ZrO2_YSZ'] = CeramicMaterial(
    name='Yttria-Stabilized Zirconia (3Y-TZP)',
    formula='ZrO2-3mol%Y2O3',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.TETRAGONAL,
    melting_point_C=2715.0,
    sintering_temp_C=1450.0,
    max_use_temp_C=1200.0,
    thermal_conductivity_W_mK=2.5,
    cte_per_K=10.5,
    elastic_modulus_GPa=210.0,
    hardness_HV=1300,
    fracture_toughness_MPa_m05=8.0,
    flexural_strength_MPa=1000.0,
    compressive_strength_MPa=2000.0,
    density_g_cm3=6.05,
    dielectric_constant=27.0,
    band_gap_eV=5.0,
    electrical_resistivity_ohm_m=1e7,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.PHASE_TRANSFORMATION,
        CeramicFailureMode.HYDROLYSIS,
    ],
    sources={
        'mechanical': 'Tosoh 3Y-TZP datasheet; Carter & Norton, 2007',
        'thermal': 'Richerson, Modern Ceramic Engineering, 2005',
        'fracture': 'Hannink et al., J. Am. Ceram. Soc. 83(3), 2000',
    },
    metadata={'note': 'Transformation toughening; dental and SOFC applications'},
)

OXIDE_CERAMICS['ZrO2_PSZ'] = CeramicMaterial(
    name='Partially Stabilized Zirconia (Mg-PSZ)',
    formula='ZrO2-MgO',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.MIXED,
    melting_point_C=2715.0,
    sintering_temp_C=1700.0,
    max_use_temp_C=1000.0,
    thermal_conductivity_W_mK=2.0,
    cte_per_K=10.0,
    elastic_modulus_GPa=200.0,
    hardness_HV=1150,
    fracture_toughness_MPa_m05=9.0,
    flexural_strength_MPa=600.0,
    compressive_strength_MPa=1800.0,
    density_g_cm3=5.74,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.PHASE_TRANSFORMATION,
    ],
    sources={
        'mechanical': 'ASM Eng. Mat. Handbook Vol. 4',
        'fracture': 'Hannink et al., J. Am. Ceram. Soc. 83(3), 2000',
    },
)

OXIDE_CERAMICS['MgO'] = CeramicMaterial(
    name='Magnesia',
    formula='MgO',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.CUBIC,
    melting_point_C=2852.0,
    sintering_temp_C=1700.0,
    max_use_temp_C=2200.0,
    thermal_conductivity_W_mK=42.0,
    cte_per_K=13.5,
    elastic_modulus_GPa=310.0,
    hardness_HV=700,
    fracture_toughness_MPa_m05=2.5,
    flexural_strength_MPa=100.0,
    density_g_cm3=3.58,
    chemical_stability='hygroscopic',
    failure_modes=[
        CeramicFailureMode.HYDROLYSIS,
        CeramicFailureMode.THERMAL_SHOCK,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Carter & Norton, Ceramic Materials, 2007',
        'thermal': 'Kingery et al., Introduction to Ceramics, 1976',
    },
    metadata={'note': 'Refractory oxide; susceptible to moisture'},
)

OXIDE_CERAMICS['TiO2'] = CeramicMaterial(
    name='Titania (Rutile)',
    formula='TiO2',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.TETRAGONAL,
    melting_point_C=1843.0,
    sintering_temp_C=1400.0,
    max_use_temp_C=1000.0,
    thermal_conductivity_W_mK=8.5,
    cte_per_K=9.0,
    elastic_modulus_GPa=230.0,
    hardness_HV=1000,
    fracture_toughness_MPa_m05=2.5,
    flexural_strength_MPa=140.0,
    density_g_cm3=4.23,
    dielectric_constant=86.0,
    band_gap_eV=3.0,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Carter & Norton, Ceramic Materials, 2007',
        'electrical': 'Kingery et al., Introduction to Ceramics, 1976',
    },
    metadata={'note': 'Photocatalyst; very high dielectric constant'},
)

OXIDE_CERAMICS['SiO2'] = CeramicMaterial(
    name='Fused Silica',
    formula='SiO2',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.AMORPHOUS,
    melting_point_C=1713.0,
    sintering_temp_C=None,
    max_use_temp_C=1100.0,
    thermal_conductivity_W_mK=1.4,
    cte_per_K=0.55,
    elastic_modulus_GPa=73.0,
    hardness_HV=600,
    fracture_toughness_MPa_m05=0.75,
    flexural_strength_MPa=50.0,
    density_g_cm3=2.20,
    dielectric_constant=3.8,
    band_gap_eV=9.0,
    electrical_resistivity_ohm_m=1e16,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.SUBCRITICAL_CRACK_GROWTH,
    ],
    sources={
        'mechanical': 'Corning 7980 fused silica datasheet',
        'thermal': 'Kingery et al., Introduction to Ceramics, 1976',
    },
    metadata={'note': 'Lowest CTE of any common ceramic; excellent thermal shock resistance'},
)

OXIDE_CERAMICS['BaTiO3'] = CeramicMaterial(
    name='Barium Titanate',
    formula='BaTiO3',
    ceramic_class=CeramicClass.PIEZOELECTRIC,
    crystal_system=CrystalSystem.TETRAGONAL,
    melting_point_C=1625.0,
    sintering_temp_C=1350.0,
    max_use_temp_C=120.0,
    thermal_conductivity_W_mK=6.0,
    cte_per_K=9.0,
    elastic_modulus_GPa=110.0,
    hardness_HV=450,
    fracture_toughness_MPa_m05=1.2,
    flexural_strength_MPa=80.0,
    density_g_cm3=6.02,
    dielectric_constant=1700.0,
    band_gap_eV=3.2,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.PHASE_TRANSFORMATION,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Carter & Norton, Ceramic Materials, 2007',
        'electrical': 'Jaffe et al., Piezoelectric Ceramics, 1971',
    },
    metadata={'note': 'Lead-free piezoelectric; Curie temp ~120C'},
)

OXIDE_CERAMICS['Mullite'] = CeramicMaterial(
    name='Mullite',
    formula='3Al2O3-2SiO2',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.ORTHORHOMBIC,
    melting_point_C=1840.0,
    sintering_temp_C=1600.0,
    max_use_temp_C=1650.0,
    thermal_conductivity_W_mK=6.0,
    cte_per_K=5.3,
    elastic_modulus_GPa=220.0,
    hardness_HV=1000,
    fracture_toughness_MPa_m05=2.5,
    flexural_strength_MPa=200.0,
    density_g_cm3=3.17,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.CREEP,
    ],
    sources={
        'mechanical': 'Richerson, Modern Ceramic Engineering, 2005',
        'thermal': 'Kingery et al., Introduction to Ceramics, 1976',
    },
    metadata={'note': 'Excellent thermal shock resistance; kiln furniture'},
)

OXIDE_CERAMICS['Spinel'] = CeramicMaterial(
    name='Magnesium Aluminate Spinel',
    formula='MgAl2O4',
    ceramic_class=CeramicClass.OXIDE,
    crystal_system=CrystalSystem.CUBIC,
    melting_point_C=2135.0,
    sintering_temp_C=1650.0,
    max_use_temp_C=1800.0,
    thermal_conductivity_W_mK=15.0,
    cte_per_K=7.6,
    elastic_modulus_GPa=260.0,
    hardness_HV=1400,
    fracture_toughness_MPa_m05=2.0,
    flexural_strength_MPa=200.0,
    density_g_cm3=3.58,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Carter & Norton, Ceramic Materials, 2007',
        'thermal': 'Kingery et al., 1976',
    },
    metadata={'note': 'Transparent in IR; armor and optical applications'},
)


# =============================================================================
# CARBIDE CERAMICS
# =============================================================================

CARBIDE_CERAMICS: Dict[str, CeramicMaterial] = {}

CARBIDE_CERAMICS['SiC'] = CeramicMaterial(
    name='Silicon Carbide (sintered alpha)',
    formula='SiC',
    ceramic_class=CeramicClass.CARBIDE,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=2730.0,
    sintering_temp_C=2100.0,
    max_use_temp_C=1650.0,
    thermal_conductivity_W_mK=120.0,
    cte_per_K=4.0,
    elastic_modulus_GPa=410.0,
    hardness_HV=2500,
    fracture_toughness_MPa_m05=3.5,
    flexural_strength_MPa=450.0,
    compressive_strength_MPa=3900.0,
    density_g_cm3=3.21,
    band_gap_eV=3.0,
    electrical_resistivity_ohm_m=1e5,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Munro, NIST J. Phys. Chem. Ref. Data 26(5), 1997',
        'thermal': 'Munro, NIST, 1997; Saint-Gobain SiC datasheet',
    },
    metadata={'note': 'Excellent thermal conductivity for a ceramic; semiconductor'},
)

CARBIDE_CERAMICS['WC'] = CeramicMaterial(
    name='Tungsten Carbide',
    formula='WC',
    ceramic_class=CeramicClass.CARBIDE,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=2870.0,
    sintering_temp_C=1500.0,
    max_use_temp_C=800.0,
    thermal_conductivity_W_mK=84.0,
    cte_per_K=5.2,
    elastic_modulus_GPa=700.0,
    hardness_HV=2200,
    fracture_toughness_MPa_m05=5.0,
    flexural_strength_MPa=550.0,
    density_g_cm3=15.63,
    electrical_resistivity_ohm_m=2e-7,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'ASM Eng. Mat. Handbook Vol. 4; Sandvik WC datasheet',
        'thermal': 'Richerson, Modern Ceramic Engineering, 2005',
    },
    metadata={'note': 'Hardest common engineering ceramic; usually used with Co binder'},
)

CARBIDE_CERAMICS['B4C'] = CeramicMaterial(
    name='Boron Carbide',
    formula='B4C',
    ceramic_class=CeramicClass.CARBIDE,
    crystal_system=CrystalSystem.RHOMBOHEDRAL,
    melting_point_C=2450.0,
    sintering_temp_C=2200.0,
    max_use_temp_C=800.0,
    thermal_conductivity_W_mK=30.0,
    cte_per_K=5.0,
    elastic_modulus_GPa=460.0,
    hardness_HV=3000,
    fracture_toughness_MPa_m05=2.5,
    flexural_strength_MPa=350.0,
    density_g_cm3=2.52,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.OXIDATION,
    ],
    sources={
        'mechanical': 'Carter & Norton, Ceramic Materials, 2007',
        'thermal': 'Richerson, Modern Ceramic Engineering, 2005',
    },
    metadata={'note': 'Third hardest material; neutron absorber; armor ceramic'},
)

CARBIDE_CERAMICS['TiC'] = CeramicMaterial(
    name='Titanium Carbide',
    formula='TiC',
    ceramic_class=CeramicClass.CARBIDE,
    crystal_system=CrystalSystem.CUBIC,
    melting_point_C=3067.0,
    sintering_temp_C=2000.0,
    max_use_temp_C=1200.0,
    thermal_conductivity_W_mK=21.0,
    cte_per_K=7.4,
    elastic_modulus_GPa=450.0,
    hardness_HV=2800,
    fracture_toughness_MPa_m05=3.0,
    flexural_strength_MPa=300.0,
    density_g_cm3=4.93,
    electrical_resistivity_ohm_m=6.8e-7,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'ASM Eng. Mat. Handbook Vol. 4',
        'thermal': 'Richerson, 2005',
    },
    metadata={'note': 'Cutting tool and wear-resistant coating material'},
)


# =============================================================================
# NITRIDE CERAMICS
# =============================================================================

NITRIDE_CERAMICS: Dict[str, CeramicMaterial] = {}

NITRIDE_CERAMICS['Si3N4'] = CeramicMaterial(
    name='Silicon Nitride',
    formula='Si3N4',
    ceramic_class=CeramicClass.NITRIDE,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=1900.0,
    sintering_temp_C=1750.0,
    max_use_temp_C=1300.0,
    thermal_conductivity_W_mK=30.0,
    cte_per_K=3.2,
    elastic_modulus_GPa=310.0,
    hardness_HV=1600,
    fracture_toughness_MPa_m05=6.5,
    flexural_strength_MPa=800.0,
    compressive_strength_MPa=3500.0,
    density_g_cm3=3.22,
    band_gap_eV=5.3,
    electrical_resistivity_ohm_m=1e13,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
        CeramicFailureMode.SUBCRITICAL_CRACK_GROWTH,
    ],
    sources={
        'mechanical': 'Saint-Gobain Si3N4 datasheet; ASM Eng. Mat. Handbook Vol. 4',
        'thermal': 'Richerson, 2005',
        'fracture': 'Becher et al., J. Am. Ceram. Soc. 81(10), 1998',
    },
    metadata={'note': 'Best thermal shock resistance of structural ceramics; bearing material'},
)

NITRIDE_CERAMICS['AlN'] = CeramicMaterial(
    name='Aluminum Nitride',
    formula='AlN',
    ceramic_class=CeramicClass.NITRIDE,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=2200.0,
    sintering_temp_C=1800.0,
    max_use_temp_C=1000.0,
    thermal_conductivity_W_mK=180.0,
    cte_per_K=4.5,
    elastic_modulus_GPa=330.0,
    hardness_HV=1200,
    fracture_toughness_MPa_m05=3.0,
    flexural_strength_MPa=350.0,
    density_g_cm3=3.26,
    dielectric_constant=8.8,
    band_gap_eV=6.2,
    electrical_resistivity_ohm_m=1e13,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.HYDROLYSIS,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Kyocera AlN datasheet; Carter & Norton, 2007',
        'thermal': 'Slack et al., J. Phys. Chem. Solids 48(7), 1987',
    },
    metadata={'note': 'Highest thermal conductivity oxide-free ceramic; substrate material'},
)

NITRIDE_CERAMICS['BN_hex'] = CeramicMaterial(
    name='Hexagonal Boron Nitride',
    formula='h-BN',
    ceramic_class=CeramicClass.NITRIDE,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=2973.0,
    sintering_temp_C=2000.0,
    max_use_temp_C=900.0,
    thermal_conductivity_W_mK=33.0,
    cte_per_K=1.0,
    elastic_modulus_GPa=30.0,
    hardness_HV=20,
    fracture_toughness_MPa_m05=None,
    flexural_strength_MPa=40.0,
    density_g_cm3=2.10,
    dielectric_constant=4.0,
    band_gap_eV=5.9,
    electrical_resistivity_ohm_m=1e13,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
    ],
    sources={
        'mechanical': 'Saint-Gobain h-BN datasheet',
        'thermal': 'Carter & Norton, 2007',
    },
    metadata={'note': 'Machinable; lubricating; inert to most chemicals up to 900C in N2'},
)

NITRIDE_CERAMICS['TiN'] = CeramicMaterial(
    name='Titanium Nitride',
    formula='TiN',
    ceramic_class=CeramicClass.NITRIDE,
    crystal_system=CrystalSystem.CUBIC,
    melting_point_C=2930.0,
    sintering_temp_C=1800.0,
    max_use_temp_C=600.0,
    thermal_conductivity_W_mK=19.0,
    cte_per_K=9.4,
    elastic_modulus_GPa=251.0,
    hardness_HV=2000,
    fracture_toughness_MPa_m05=4.0,
    flexural_strength_MPa=350.0,
    density_g_cm3=5.22,
    electrical_resistivity_ohm_m=2.5e-7,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.OXIDATION,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'ASM Eng. Mat. Handbook Vol. 4',
        'thermal': 'Richerson, 2005',
    },
    metadata={'note': 'Gold-colored hard coating; PVD/CVD coating material'},
)


# =============================================================================
# GLASS CERAMICS
# =============================================================================

GLASS_CERAMICS: Dict[str, CeramicMaterial] = {}

GLASS_CERAMICS['Borosilicate'] = CeramicMaterial(
    name='Borosilicate Glass (Pyrex)',
    formula='SiO2-B2O3-Na2O',
    ceramic_class=CeramicClass.GLASS,
    crystal_system=CrystalSystem.AMORPHOUS,
    melting_point_C=820.0,
    sintering_temp_C=None,
    max_use_temp_C=500.0,
    thermal_conductivity_W_mK=1.14,
    cte_per_K=3.3,
    elastic_modulus_GPa=63.0,
    hardness_HV=480,
    fracture_toughness_MPa_m05=0.7,
    flexural_strength_MPa=69.0,
    density_g_cm3=2.23,
    dielectric_constant=4.6,
    electrical_resistivity_ohm_m=1e12,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.THERMAL_SHOCK,
    ],
    sources={
        'mechanical': 'Corning Pyrex 7740 datasheet',
        'thermal': 'Schott Technical Glass Guide',
    },
    metadata={'note': 'Lab glassware and cookware; good thermal shock resistance for glass'},
)

GLASS_CERAMICS['Soda_Lime'] = CeramicMaterial(
    name='Soda-Lime Glass',
    formula='SiO2-Na2O-CaO',
    ceramic_class=CeramicClass.GLASS,
    crystal_system=CrystalSystem.AMORPHOUS,
    melting_point_C=730.0,
    sintering_temp_C=None,
    max_use_temp_C=250.0,
    thermal_conductivity_W_mK=1.0,
    cte_per_K=9.0,
    elastic_modulus_GPa=72.0,
    hardness_HV=530,
    fracture_toughness_MPa_m05=0.75,
    flexural_strength_MPa=70.0,
    density_g_cm3=2.50,
    dielectric_constant=7.0,
    electrical_resistivity_ohm_m=1e10,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.THERMAL_SHOCK,
        CeramicFailureMode.CORROSION,
    ],
    sources={
        'mechanical': 'Schott Technical Glass Guide',
        'thermal': 'Kingery et al., 1976',
    },
    metadata={'note': 'Most common glass; windows, bottles'},
)

GLASS_CERAMICS['LAS'] = CeramicMaterial(
    name='Lithium Aluminosilicate Glass-Ceramic',
    formula='Li2O-Al2O3-SiO2',
    ceramic_class=CeramicClass.GLASS,
    crystal_system=CrystalSystem.MIXED,
    melting_point_C=1400.0,
    sintering_temp_C=None,
    max_use_temp_C=700.0,
    thermal_conductivity_W_mK=1.7,
    cte_per_K=0.5,
    elastic_modulus_GPa=92.0,
    hardness_HV=600,
    fracture_toughness_MPa_m05=1.5,
    flexural_strength_MPa=120.0,
    density_g_cm3=2.50,
    chemical_stability='inert',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Schott Zerodur datasheet; Corning glass-ceramic literature',
        'thermal': 'Carter & Norton, 2007',
    },
    metadata={'note': 'Near-zero CTE; telescope mirrors, cooktops (Ceran/Zerodur)'},
)


# =============================================================================
# BIOCERAMICS
# =============================================================================

BIOCERAMICS: Dict[str, CeramicMaterial] = {}

BIOCERAMICS['Hydroxyapatite'] = CeramicMaterial(
    name='Hydroxyapatite',
    formula='Ca5(PO4)3(OH)',
    ceramic_class=CeramicClass.BIOCERAMIC,
    crystal_system=CrystalSystem.HEXAGONAL,
    melting_point_C=1614.0,
    sintering_temp_C=1250.0,
    max_use_temp_C=None,
    thermal_conductivity_W_mK=1.25,
    cte_per_K=11.0,
    elastic_modulus_GPa=80.0,
    hardness_HV=500,
    fracture_toughness_MPa_m05=1.0,
    flexural_strength_MPa=60.0,
    density_g_cm3=3.16,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.DECOMPOSITION,
    ],
    sources={
        'mechanical': 'Hench, J. Am. Ceram. Soc. 81(7), 1998',
        'thermal': 'Carter & Norton, 2007',
    },
    metadata={'note': 'Main mineral in bone; bioactive and resorbable implant material'},
)

BIOCERAMICS['TCP'] = CeramicMaterial(
    name='Tricalcium Phosphate (beta)',
    formula='Ca3(PO4)2',
    ceramic_class=CeramicClass.BIOCERAMIC,
    crystal_system=CrystalSystem.RHOMBOHEDRAL,
    melting_point_C=1391.0,
    sintering_temp_C=1100.0,
    max_use_temp_C=None,
    thermal_conductivity_W_mK=1.1,
    cte_per_K=12.0,
    elastic_modulus_GPa=90.0,
    hardness_HV=400,
    fracture_toughness_MPa_m05=0.8,
    flexural_strength_MPa=50.0,
    density_g_cm3=3.07,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.DECOMPOSITION,
    ],
    sources={
        'mechanical': 'Hench, J. Am. Ceram. Soc. 81(7), 1998',
    },
    metadata={'note': 'Resorbable bone substitute; faster resorption than HA'},
)

BIOCERAMICS['Bioglass'] = CeramicMaterial(
    name='45S5 Bioglass',
    formula='SiO2-Na2O-CaO-P2O5',
    ceramic_class=CeramicClass.BIOCERAMIC,
    crystal_system=CrystalSystem.AMORPHOUS,
    melting_point_C=1050.0,
    sintering_temp_C=None,
    max_use_temp_C=None,
    thermal_conductivity_W_mK=1.0,
    cte_per_K=15.0,
    elastic_modulus_GPa=35.0,
    hardness_HV=450,
    fracture_toughness_MPa_m05=0.6,
    flexural_strength_MPa=42.0,
    density_g_cm3=2.70,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.CORROSION,
    ],
    sources={
        'mechanical': 'Hench, J. Am. Ceram. Soc. 81(7), 1998; Hench, Biomaterials 19, 1998',
    },
    metadata={'note': 'First bioactive glass; bonds to bone via HA layer formation'},
)


# =============================================================================
# PIEZOELECTRIC CERAMICS
# =============================================================================

PIEZOELECTRIC_CERAMICS: Dict[str, CeramicMaterial] = {}

PIEZOELECTRIC_CERAMICS['PZT'] = CeramicMaterial(
    name='Lead Zirconate Titanate (PZT-5A)',
    formula='Pb(Zr0.52Ti0.48)O3',
    ceramic_class=CeramicClass.PIEZOELECTRIC,
    crystal_system=CrystalSystem.TETRAGONAL,
    melting_point_C=1350.0,
    sintering_temp_C=1250.0,
    max_use_temp_C=365.0,
    thermal_conductivity_W_mK=1.5,
    cte_per_K=4.0,
    elastic_modulus_GPa=63.0,
    hardness_HV=350,
    fracture_toughness_MPa_m05=1.0,
    flexural_strength_MPa=75.0,
    density_g_cm3=7.75,
    dielectric_constant=1700.0,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.PHASE_TRANSFORMATION,
        CeramicFailureMode.DECOMPOSITION,
    ],
    sources={
        'mechanical': 'Jaffe et al., Piezoelectric Ceramics, 1971; CTS PZT datasheet',
        'electrical': 'Jaffe et al., 1971',
    },
    metadata={'note': 'Standard piezoelectric actuator/sensor; contains lead'},
)


# =============================================================================
# SOLID ELECTROLYTE CERAMICS
# =============================================================================

SOLID_ELECTROLYTE_CERAMICS: Dict[str, CeramicMaterial] = {}

SOLID_ELECTROLYTE_CERAMICS['LLZO'] = CeramicMaterial(
    name='Lithium Lanthanum Zirconium Oxide (cubic)',
    formula='Li7La3Zr2O12',
    ceramic_class=CeramicClass.SOLID_ELECTROLYTE,
    crystal_system=CrystalSystem.CUBIC,
    melting_point_C=None,
    sintering_temp_C=1100.0,
    max_use_temp_C=300.0,
    thermal_conductivity_W_mK=2.0,
    cte_per_K=12.0,
    elastic_modulus_GPa=150.0,
    hardness_HV=600,
    fracture_toughness_MPa_m05=1.5,
    flexural_strength_MPa=120.0,
    density_g_cm3=5.10,
    dielectric_constant=50.0,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.HYDROLYSIS,
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.GRAIN_BOUNDARY_ATTACK,
    ],
    sources={
        'mechanical': 'Yu et al., Chem. Mater. 28(1), 2016',
        'thermal': 'Wang & Bhatt, Electrochem. Soc. Interface 29(3), 2020',
    },
    metadata={'note': 'Oxide solid electrolyte for solid-state Li batteries; 0.3 mS/cm conductivity'},
)

SOLID_ELECTROLYTE_CERAMICS['LGPS'] = CeramicMaterial(
    name='Lithium Germanium Phosphorus Sulfide',
    formula='Li10GeP2S12',
    ceramic_class=CeramicClass.SOLID_ELECTROLYTE,
    crystal_system=CrystalSystem.TETRAGONAL,
    melting_point_C=None,
    sintering_temp_C=550.0,
    max_use_temp_C=200.0,
    thermal_conductivity_W_mK=0.5,
    cte_per_K=15.0,
    elastic_modulus_GPa=20.0,
    hardness_HV=150,
    fracture_toughness_MPa_m05=0.3,
    flexural_strength_MPa=30.0,
    density_g_cm3=2.00,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.DECOMPOSITION,
        CeramicFailureMode.HYDROLYSIS,
        CeramicFailureMode.BRITTLE_FRACTURE,
    ],
    sources={
        'mechanical': 'Kamaya et al., Nature Materials 10, 2011',
        'thermal': 'Kamaya et al., 2011; Kato et al., Nature Energy 1, 2016',
    },
    metadata={'note': 'Highest Li-ion conductivity (12 mS/cm); extremely air-sensitive'},
)

SOLID_ELECTROLYTE_CERAMICS['Li3PS4'] = CeramicMaterial(
    name='Lithium Thiophosphate (beta)',
    formula='Li3PS4',
    ceramic_class=CeramicClass.SOLID_ELECTROLYTE,
    crystal_system=CrystalSystem.ORTHORHOMBIC,
    melting_point_C=None,
    sintering_temp_C=300.0,
    max_use_temp_C=200.0,
    thermal_conductivity_W_mK=0.5,
    cte_per_K=14.0,
    elastic_modulus_GPa=18.0,
    hardness_HV=100,
    fracture_toughness_MPa_m05=0.2,
    flexural_strength_MPa=25.0,
    density_g_cm3=1.88,
    chemical_stability='reactive',
    failure_modes=[
        CeramicFailureMode.DECOMPOSITION,
        CeramicFailureMode.HYDROLYSIS,
    ],
    sources={
        'mechanical': 'Liu et al., J. Am. Chem. Soc. 135, 2013',
    },
    metadata={'note': 'Sulfide solid electrolyte; 0.16 mS/cm; moisture-sensitive'},
)

SOLID_ELECTROLYTE_CERAMICS['NASICON'] = CeramicMaterial(
    name='NASICON (Na-type)',
    formula='Na3Zr2Si2PO12',
    ceramic_class=CeramicClass.SOLID_ELECTROLYTE,
    crystal_system=CrystalSystem.RHOMBOHEDRAL,
    melting_point_C=None,
    sintering_temp_C=1200.0,
    max_use_temp_C=300.0,
    thermal_conductivity_W_mK=1.5,
    cte_per_K=10.0,
    elastic_modulus_GPa=100.0,
    hardness_HV=500,
    fracture_toughness_MPa_m05=1.2,
    flexural_strength_MPa=80.0,
    density_g_cm3=3.27,
    chemical_stability='stable',
    failure_modes=[
        CeramicFailureMode.BRITTLE_FRACTURE,
        CeramicFailureMode.GRAIN_BOUNDARY_ATTACK,
    ],
    sources={
        'mechanical': 'Goodenough et al., Mater. Res. Bull. 11(2), 1976',
    },
    metadata={'note': 'Na-ion solid electrolyte; 1 mS/cm; air-stable'},
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_CERAMICS: Dict[str, CeramicMaterial] = {}
ALL_CERAMICS.update(OXIDE_CERAMICS)
ALL_CERAMICS.update(CARBIDE_CERAMICS)
ALL_CERAMICS.update(NITRIDE_CERAMICS)
ALL_CERAMICS.update(GLASS_CERAMICS)
ALL_CERAMICS.update(BIOCERAMICS)
ALL_CERAMICS.update(PIEZOELECTRIC_CERAMICS)
ALL_CERAMICS.update(SOLID_ELECTROLYTE_CERAMICS)


def get_ceramic(name: str) -> Optional[CeramicMaterial]:
    """Look up a ceramic by name or abbreviation."""
    return ALL_CERAMICS.get(name)


def get_ceramics_by_class(ceramic_class: CeramicClass) -> Dict[str, CeramicMaterial]:
    """Get all ceramics of a given class."""
    return {k: v for k, v in ALL_CERAMICS.items() if v.ceramic_class == ceramic_class}


def list_oxides() -> List[str]:
    return list(OXIDE_CERAMICS.keys())


def list_carbides() -> List[str]:
    return list(CARBIDE_CERAMICS.keys())


def list_nitrides() -> List[str]:
    return list(NITRIDE_CERAMICS.keys())


def list_glasses() -> List[str]:
    return list(GLASS_CERAMICS.keys())


def list_bioceramics() -> List[str]:
    return list(BIOCERAMICS.keys())


def list_solid_electrolytes() -> List[str]:
    return list(SOLID_ELECTROLYTE_CERAMICS.keys())


# =============================================================================
# KNOWN GOOD/BAD PAIRINGS (for test validation)
# =============================================================================

KNOWN_GOOD_COMPOSITES = [
    {
        'name': 'Alumina + Zirconia (ZTA)',
        'ceramic_a': 'Al2O3',
        'ceramic_b': 'ZrO2_YSZ',
        'notes': 'Zirconia-toughened alumina; CTE match, similar sintering, transformation toughening',
    },
    {
        'name': 'Si3N4 + SiC',
        'ceramic_a': 'Si3N4',
        'ceramic_b': 'SiC',
        'notes': 'Both non-oxides; similar CTE (~3-4); co-sintered composites exist',
    },
    {
        'name': 'Alumina + Mullite',
        'ceramic_a': 'Al2O3',
        'ceramic_b': 'Mullite',
        'notes': 'Mullite is an alumino-silicate; compatible sintering; refractory linings',
    },
    {
        'name': 'Alumina + Spinel',
        'ceramic_a': 'Al2O3',
        'ceramic_b': 'Spinel',
        'notes': 'Both Al-containing oxides; CTE close; refractory composites',
    },
    {
        'name': 'Al2O3 substrate + TiN coating',
        'ceramic_a': 'Al2O3',
        'ceramic_b': 'TiN',
        'notes': 'Standard cutting tool composite; good adhesion',
    },
]

KNOWN_BAD_COMPOSITES = [
    {
        'name': 'SiO2 + MgO',
        'ceramic_a': 'SiO2',
        'ceramic_b': 'MgO',
        'issue': 'Extreme CTE mismatch (0.55 vs 13.5); MgO is hygroscopic; react to form forsterite',
    },
    {
        'name': 'LGPS + Al2O3',
        'ceramic_a': 'LGPS',
        'ceramic_b': 'Al2O3',
        'issue': 'Extreme modulus/hardness mismatch; LGPS decomposes on contact with oxides at high temp',
    },
    {
        'name': 'Bioglass + SiC',
        'ceramic_a': 'Bioglass',
        'ceramic_b': 'SiC',
        'issue': 'Incompatible sintering temps (Bioglass ~1050C decomposes, SiC needs >2100C); extreme mechanical mismatch',
    },
    {
        'name': 'BN + Soda-Lime Glass',
        'ceramic_a': 'BN_hex',
        'ceramic_b': 'Soda_Lime',
        'issue': 'Extreme modulus mismatch (30 vs 72 GPa) and CTE mismatch (1.0 vs 9.0); no bonding mechanism',
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("Ceramic Material Properties - Summary")
    print("=" * 70)
    print()

    categories = [
        ("Oxide Ceramics", OXIDE_CERAMICS),
        ("Carbide Ceramics", CARBIDE_CERAMICS),
        ("Nitride Ceramics", NITRIDE_CERAMICS),
        ("Glass Ceramics", GLASS_CERAMICS),
        ("Bioceramics", BIOCERAMICS),
        ("Piezoelectric Ceramics", PIEZOELECTRIC_CERAMICS),
        ("Solid Electrolyte Ceramics", SOLID_ELECTROLYTE_CERAMICS),
    ]

    for cat_name, cat_dict in categories:
        print(f"{cat_name}: {len(cat_dict)}")
        for name, mat in cat_dict.items():
            cte = f"CTE={mat.cte_per_K}" if mat.cte_per_K is not None else ""
            kic = f"KIC={mat.fracture_toughness_MPa_m05}" if mat.fracture_toughness_MPa_m05 is not None else ""
            print(f"  {name:20s} ({mat.name:40s}) {cte:10s} {kic}")
        print()

    print(f"Total materials: {len(ALL_CERAMICS)}")
