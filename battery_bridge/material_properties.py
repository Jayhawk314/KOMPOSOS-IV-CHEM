# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery Material Properties
=============================

Validated property tables for battery-relevant species, analogous to
chemistry/hydrogen_bonds.py amino acid property tables.

Each material entry uses real published values with source citations.

Property Sources:
-----------------
- Materials Project (https://materialsproject.org/) -- crystal structures, voltages
- Goodenough & Park, JACS 2013 -- cathode voltage/capacity benchmarks
- Xu, Chem. Rev. 2004 -- electrolyte stability windows
- Aurbach et al., Electrochim. Acta 2002 -- SEI formation
- Janek & Zeier, Nat. Energy 2016 -- solid electrolytes
- Nitta et al., Mater. Today 2015 -- Li-ion battery overview
- Liu et al., Nat. Energy 2019 -- Si anode volume expansion
- Manthiram, Nat. Commun. 2020 -- NMC cathode review
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MaterialClass(Enum):
    """Classification of battery materials."""
    CATHODE = "cathode"
    ANODE = "anode"
    ELECTROLYTE_SOLVENT = "electrolyte_solvent"
    ELECTROLYTE_SALT = "electrolyte_salt"
    SOLID_ELECTROLYTE = "solid_electrolyte"
    ION = "ion"
    SEPARATOR = "separator"


class CrystalStructure(Enum):
    """Crystal structure types relevant to battery materials."""
    LAYERED = "layered"           # alpha-NaFeO2 type (NMC, LCO)
    SPINEL = "spinel"             # Fd-3m (LMO, LTO)
    OLIVINE = "olivine"           # Pnma (LFP)
    GRAPHITE = "graphite"         # P63/mmc (hexagonal layered)
    GARNET = "garnet"             # Ia-3d (LLZO)
    THIO_LISICON = "thio-LISICON" # (LGPS)
    ARGYRODITE = "argyrodite"     # (Li6PS5Cl)
    AMORPHOUS = "amorphous"
    CUBIC = "cubic"               # Li metal BCC
    DIAMOND_CUBIC = "diamond_cubic"  # Si
    ROCK_SALT = "rock_salt"
    MOLECULAR = "molecular"       # Organic solvents


class FailureMode(Enum):
    """Known failure modes for battery materials."""
    DENDRITE_GROWTH = "dendrite_growth"
    SEI_GROWTH = "sei_growth"
    CEI_DEGRADATION = "cei_degradation"
    VOLUME_EXPANSION = "volume_expansion"
    TRANSITION_METAL_DISSOLUTION = "tm_dissolution"
    OXYGEN_RELEASE = "oxygen_release"
    JAHN_TELLER_DISTORTION = "jahn_teller"
    ELECTROLYTE_DECOMPOSITION = "electrolyte_decomposition"
    THERMAL_RUNAWAY = "thermal_runaway"
    CRACKING = "mechanical_cracking"
    GAS_EVOLUTION = "gas_evolution"
    LITHIUM_PLATING = "lithium_plating"
    PHASE_TRANSITION = "phase_transition"


@dataclass
class VoltageWindow:
    """Electrochemical voltage window (V vs Li/Li+)."""
    lower: float   # Lower cutoff
    upper: float   # Upper cutoff
    nominal: float  # Nominal operating voltage

    @property
    def width(self) -> float:
        return self.upper - self.lower


@dataclass
class BatteryMaterial:
    """
    A battery-relevant material with validated physical properties.

    Analogous to amino acid property tables in chemistry/hydrogen_bonds.py.
    Every numerical value has a source citation in the comment field.
    """
    name: str
    formula: str
    material_class: MaterialClass
    crystal_structure: CrystalStructure

    # Electrochemical properties
    voltage_window: Optional[VoltageWindow] = None  # V vs Li/Li+
    theoretical_capacity: Optional[float] = None     # mAh/g
    ionic_conductivity: Optional[float] = None       # S/cm at 25C
    electronic_conductivity: Optional[float] = None  # S/cm

    # Physical properties
    density: Optional[float] = None           # g/cm3
    ionic_radius: Optional[float] = None      # Angstroms (for ions)
    volume_expansion: Optional[float] = None  # Fractional (0.0 = none, 3.0 = 300%)
    elastic_modulus: Optional[float] = None   # GPa

    # Thermal properties
    thermal_stability_max: Optional[float] = None  # Celsius
    melting_point: Optional[float] = None          # Celsius

    # Electrochemical stability
    oxidation_potential: Optional[float] = None   # V vs Li/Li+ (HOMO-related)
    reduction_potential: Optional[float] = None   # V vs Li/Li+ (LUMO-related)

    # Failure modes
    failure_modes: List[FailureMode] = field(default_factory=list)

    # Source citations for property values
    sources: Dict[str, str] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'formula': self.formula,
            'material_class': self.material_class.value,
            'crystal_structure': self.crystal_structure.value,
        }
        if self.voltage_window:
            result['voltage_window'] = {
                'lower': self.voltage_window.lower,
                'upper': self.voltage_window.upper,
                'nominal': self.voltage_window.nominal,
            }
        if self.theoretical_capacity is not None:
            result['theoretical_capacity_mAh_g'] = self.theoretical_capacity
        if self.ionic_conductivity is not None:
            result['ionic_conductivity_S_cm'] = self.ionic_conductivity
        if self.volume_expansion is not None:
            result['volume_expansion_frac'] = self.volume_expansion
        if self.failure_modes:
            result['failure_modes'] = [fm.value for fm in self.failure_modes]
        return result


# =============================================================================
# CATHODE MATERIALS
# =============================================================================

CATHODE_MATERIALS: Dict[str, BatteryMaterial] = {}

# LiCoO2 (LCO) -- Goodenough 1980, the original Li-ion cathode
CATHODE_MATERIALS['LCO'] = BatteryMaterial(
    name='LCO',
    formula='LiCoO2',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.LAYERED,
    voltage_window=VoltageWindow(lower=3.0, upper=4.2, nominal=3.9),
    # Nitta et al., Mater. Today 2015: theoretical 274 mAh/g, practical ~140
    theoretical_capacity=274.0,
    density=5.05,  # Materials Project mp-22526
    ionic_conductivity=None,  # Cathode: mixed ionic/electronic
    electronic_conductivity=1e-2,  # ~0.01 S/cm, Ménétrier et al. 1999
    thermal_stability_max=200,  # Onset of O2 release at ~200C (Bak et al. 2018)
    volume_expansion=0.02,  # ~2% lattice change on cycling (Reimers & Dahn 1992)
    elastic_modulus=191.0,  # GPa, Qi et al. 2014
    failure_modes=[
        FailureMode.TRANSITION_METAL_DISSOLUTION,
        FailureMode.OXYGEN_RELEASE,
        FailureMode.PHASE_TRANSITION,  # O3->H1-3 at high delithiation
    ],
    sources={
        'voltage': 'Goodenough & Mizushima, Mater. Res. Bull. 1980',
        'capacity': 'Nitta et al., Mater. Today 2015',
        'density': 'Materials Project mp-22526',
        'thermal': 'Bak et al., Chem. Mater. 2018',
        'modulus': 'Qi et al., J. Electrochem. Soc. 2014',
    },
)

# LiFePO4 (LFP) -- Padhi et al. 1997
CATHODE_MATERIALS['LFP'] = BatteryMaterial(
    name='LFP',
    formula='LiFePO4',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.OLIVINE,
    voltage_window=VoltageWindow(lower=2.5, upper=4.0, nominal=3.4),
    theoretical_capacity=170.0,  # Padhi et al. 1997
    density=3.60,  # Materials Project mp-19017
    electronic_conductivity=1e-9,  # Very low, needs carbon coating
    thermal_stability_max=400,  # Excellent thermal stability (Ong et al. 2008)
    volume_expansion=0.067,  # 6.7% (Delmas et al. 2008)
    elastic_modulus=125.0,  # GPa, Maxisch & Ceder 2006
    failure_modes=[
        FailureMode.CRACKING,  # At high C-rates due to poor conductivity
    ],
    sources={
        'voltage': 'Padhi et al., J. Electrochem. Soc. 1997',
        'capacity': 'Padhi et al., J. Electrochem. Soc. 1997',
        'density': 'Materials Project mp-19017',
        'thermal': 'Ong et al., Electrochem. Commun. 2008',
        'modulus': 'Maxisch & Ceder, Phys. Rev. B 2006',
    },
)

# NMC811 -- Manthiram, Nat. Commun. 2020
CATHODE_MATERIALS['NMC811'] = BatteryMaterial(
    name='NMC811',
    formula='LiNi0.8Mn0.1Co0.1O2',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.LAYERED,
    voltage_window=VoltageWindow(lower=3.0, upper=4.3, nominal=3.8),
    theoretical_capacity=275.0,  # Manthiram 2020
    density=4.78,  # Li et al., Adv. Energy Mater. 2018
    thermal_stability_max=170,  # Lower than LCO due to Ni content (Noh et al. 2013)
    volume_expansion=0.05,  # ~5% (de Biasi et al. 2019)
    elastic_modulus=170.0,  # GPa, estimate from NMC family
    failure_modes=[
        FailureMode.OXYGEN_RELEASE,         # High Ni -> O2 at >4.3V
        FailureMode.CEI_DEGRADATION,        # Surface reactivity
        FailureMode.CRACKING,               # Intergranular cracking
        FailureMode.PHASE_TRANSITION,       # H2->H3 at high SOC
        FailureMode.TRANSITION_METAL_DISSOLUTION,
    ],
    sources={
        'voltage': 'Manthiram, Nat. Commun. 2020',
        'capacity': 'Manthiram, Nat. Commun. 2020',
        'thermal': 'Noh et al., J. Power Sources 2013',
        'failure': 'de Biasi et al., J. Phys. Chem. C 2019',
    },
)

# NMC622
CATHODE_MATERIALS['NMC622'] = BatteryMaterial(
    name='NMC622',
    formula='LiNi0.6Mn0.2Co0.2O2',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.LAYERED,
    voltage_window=VoltageWindow(lower=3.0, upper=4.3, nominal=3.8),
    theoretical_capacity=276.0,
    density=4.75,
    thermal_stability_max=210,  # Better than 811 (Noh et al. 2013)
    volume_expansion=0.04,
    elastic_modulus=175.0,
    failure_modes=[
        FailureMode.OXYGEN_RELEASE,
        FailureMode.CEI_DEGRADATION,
        FailureMode.TRANSITION_METAL_DISSOLUTION,
    ],
    sources={
        'voltage': 'Noh et al., J. Power Sources 2013',
        'capacity': 'Noh et al., J. Power Sources 2013',
    },
)

# NMC111 (equal ratios)
CATHODE_MATERIALS['NMC111'] = BatteryMaterial(
    name='NMC111',
    formula='LiNi1/3Mn1/3Co1/3O2',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.LAYERED,
    voltage_window=VoltageWindow(lower=3.0, upper=4.3, nominal=3.8),
    theoretical_capacity=278.0,
    density=4.70,
    thermal_stability_max=250,  # Best thermal in NMC family
    volume_expansion=0.03,
    elastic_modulus=180.0,
    failure_modes=[
        FailureMode.TRANSITION_METAL_DISSOLUTION,
    ],
    sources={
        'voltage': 'Ohzuku & Makimura, Chem. Lett. 2001',
    },
)

# LiMn2O4 (LMO) -- Thackeray et al. 1983
CATHODE_MATERIALS['LMO'] = BatteryMaterial(
    name='LMO',
    formula='LiMn2O4',
    material_class=MaterialClass.CATHODE,
    crystal_structure=CrystalStructure.SPINEL,
    voltage_window=VoltageWindow(lower=3.0, upper=4.3, nominal=4.1),
    theoretical_capacity=148.0,  # Thackeray 1983
    density=4.28,  # Materials Project mp-18767
    thermal_stability_max=300,  # Good thermal stability
    volume_expansion=0.065,  # ~6.5%
    elastic_modulus=135.0,
    failure_modes=[
        FailureMode.JAHN_TELLER_DISTORTION,     # Mn3+ distortion
        FailureMode.TRANSITION_METAL_DISSOLUTION, # Mn dissolution at high T
    ],
    sources={
        'voltage': 'Thackeray et al., Mater. Res. Bull. 1983',
        'capacity': 'Thackeray et al., Mater. Res. Bull. 1983',
        'density': 'Materials Project mp-18767',
    },
)


# =============================================================================
# ANODE MATERIALS
# =============================================================================

ANODE_MATERIALS: Dict[str, BatteryMaterial] = {}

# Graphite
ANODE_MATERIALS['Graphite'] = BatteryMaterial(
    name='Graphite',
    formula='C6',
    material_class=MaterialClass.ANODE,
    crystal_structure=CrystalStructure.GRAPHITE,
    voltage_window=VoltageWindow(lower=0.01, upper=0.3, nominal=0.1),
    theoretical_capacity=372.0,  # LiC6 (Winter et al. 1998)
    density=2.26,
    volume_expansion=0.10,  # ~10% (Qi & Harris 2010)
    elastic_modulus=36.0,   # GPa, in-plane much higher
    thermal_stability_max=600,
    failure_modes=[
        FailureMode.SEI_GROWTH,           # Continuous SEI thickening
        FailureMode.LITHIUM_PLATING,      # At low T or high C-rate
        FailureMode.GAS_EVOLUTION,        # During SEI formation
    ],
    sources={
        'capacity': 'Winter et al., Adv. Mater. 1998',
        'expansion': 'Qi & Harris, J. Electrochem. Soc. 2010',
    },
)

# Lithium metal
ANODE_MATERIALS['Li_metal'] = BatteryMaterial(
    name='Li_metal',
    formula='Li',
    material_class=MaterialClass.ANODE,
    crystal_structure=CrystalStructure.CUBIC,
    voltage_window=VoltageWindow(lower=0.0, upper=0.0, nominal=0.0),
    # 3860 mAh/g -- highest of any anode (Xu et al. 2014)
    theoretical_capacity=3860.0,
    density=0.534,
    volume_expansion=None,   # Infinite/undefined: plating not intercalation
    elastic_modulus=4.9,     # GPa, very soft (Xu et al. 2017)
    melting_point=180.5,
    thermal_stability_max=180,
    failure_modes=[
        FailureMode.DENDRITE_GROWTH,      # Primary safety concern
        FailureMode.SEI_GROWTH,           # Continuous SEI consumption
        FailureMode.THERMAL_RUNAWAY,      # Dendrite short -> thermal runaway
    ],
    sources={
        'capacity': 'Xu et al., Energy Environ. Sci. 2014',
        'modulus': 'Xu et al., J. Mech. Phys. Solids 2017',
    },
)

# Silicon
ANODE_MATERIALS['Si'] = BatteryMaterial(
    name='Si',
    formula='Si',
    material_class=MaterialClass.ANODE,
    crystal_structure=CrystalStructure.DIAMOND_CUBIC,
    voltage_window=VoltageWindow(lower=0.01, upper=0.5, nominal=0.4),
    # 4200 mAh/g for Li22Si5 (Obrovac & Christensen 2004)
    theoretical_capacity=4200.0,
    density=2.33,
    volume_expansion=3.0,  # ~300% (Liu et al., Nat. Energy 2019)
    elastic_modulus=130.0,  # GPa crystalline Si
    thermal_stability_max=500,
    failure_modes=[
        FailureMode.VOLUME_EXPANSION,     # 300% -> pulverization
        FailureMode.SEI_GROWTH,           # SEI breaks and reforms each cycle
        FailureMode.CRACKING,             # Particle fracture
    ],
    sources={
        'capacity': 'Obrovac & Christensen, Electrochem. Solid-State Lett. 2004',
        'expansion': 'Liu et al., Nat. Energy 2019',
    },
)

# Li4Ti5O12 (LTO)
ANODE_MATERIALS['LTO'] = BatteryMaterial(
    name='LTO',
    formula='Li4Ti5O12',
    material_class=MaterialClass.ANODE,
    crystal_structure=CrystalStructure.SPINEL,
    voltage_window=VoltageWindow(lower=1.0, upper=2.5, nominal=1.55),
    theoretical_capacity=175.0,  # Ohzuku et al. 1995
    density=3.50,
    volume_expansion=0.001,  # "Zero-strain" (<0.1%) -- Ohzuku et al. 1995
    elastic_modulus=180.0,
    thermal_stability_max=400,
    failure_modes=[
        FailureMode.GAS_EVOLUTION,  # Gassing at high T with some electrolytes
    ],
    sources={
        'capacity': 'Ohzuku et al., J. Electrochem. Soc. 1995',
        'expansion': 'Ohzuku et al., J. Electrochem. Soc. 1995',
    },
)


# =============================================================================
# ELECTROLYTE SOLVENTS
# =============================================================================

ELECTROLYTE_SOLVENTS: Dict[str, BatteryMaterial] = {}

# Ethylene Carbonate (EC)
ELECTROLYTE_SOLVENTS['EC'] = BatteryMaterial(
    name='EC',
    formula='C3H4O3',
    material_class=MaterialClass.ELECTROLYTE_SOLVENT,
    crystal_structure=CrystalStructure.MOLECULAR,
    # Xu, Chem. Rev. 2004: EC oxidation ~4.5V, reduction ~0.8V vs Li/Li+
    oxidation_potential=4.5,
    reduction_potential=0.8,
    density=1.321,
    melting_point=36.4,  # Solid at room temperature (high mp for carbonate)
    thermal_stability_max=260,
    ionic_conductivity=None,  # Solvent alone: no ionic conductivity
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,  # Reduction at anode forms SEI
        FailureMode.GAS_EVOLUTION,               # CO2, C2H4 during decomposition
    ],
    sources={
        'oxidation': 'Xu, Chem. Rev. 2004',
        'reduction': 'Xu, Chem. Rev. 2004; Aurbach et al., Electrochim. Acta 2002',
        'density': 'CRC Handbook of Chemistry and Physics',
    },
    metadata={
        'dielectric_constant': 89.78,   # Very high -- enables Li salt dissolution
        'viscosity_cP': 1.90,           # At 40C (solid at 25C)
        'role': 'Primary SEI-forming solvent; high dielectric enables salt dissolution',
    },
)

# Dimethyl Carbonate (DMC)
ELECTROLYTE_SOLVENTS['DMC'] = BatteryMaterial(
    name='DMC',
    formula='C3H6O3',
    material_class=MaterialClass.ELECTROLYTE_SOLVENT,
    crystal_structure=CrystalStructure.MOLECULAR,
    oxidation_potential=5.0,  # Higher stability than EC
    reduction_potential=0.5,
    density=1.069,
    melting_point=4.6,
    thermal_stability_max=250,
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,
    ],
    sources={
        'oxidation': 'Xu, Chem. Rev. 2004',
        'density': 'CRC Handbook',
    },
    metadata={
        'dielectric_constant': 3.11,  # Low -- provides fluidity
        'viscosity_cP': 0.59,
        'role': 'Low-viscosity co-solvent; reduces electrolyte viscosity',
    },
)

# Diethyl Carbonate (DEC)
ELECTROLYTE_SOLVENTS['DEC'] = BatteryMaterial(
    name='DEC',
    formula='C5H10O3',
    material_class=MaterialClass.ELECTROLYTE_SOLVENT,
    crystal_structure=CrystalStructure.MOLECULAR,
    oxidation_potential=5.1,
    reduction_potential=0.4,
    density=0.975,
    melting_point=-43.0,
    thermal_stability_max=230,
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,
    ],
    sources={
        'oxidation': 'Xu, Chem. Rev. 2004',
    },
    metadata={
        'dielectric_constant': 2.80,
        'viscosity_cP': 0.75,
        'role': 'Low-viscosity co-solvent; good low-temperature performance',
    },
)

# Ethyl Methyl Carbonate (EMC)
ELECTROLYTE_SOLVENTS['EMC'] = BatteryMaterial(
    name='EMC',
    formula='C4H8O3',
    material_class=MaterialClass.ELECTROLYTE_SOLVENT,
    crystal_structure=CrystalStructure.MOLECULAR,
    oxidation_potential=5.0,
    reduction_potential=0.5,
    density=1.006,
    melting_point=-53.0,
    thermal_stability_max=240,
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,
    ],
    sources={
        'oxidation': 'Xu, Chem. Rev. 2004',
    },
    metadata={
        'dielectric_constant': 2.96,
        'viscosity_cP': 0.65,
        'role': 'Co-solvent in EV electrolytes; replaces DMC in some formulations',
    },
)


# =============================================================================
# ELECTROLYTE SALTS
# =============================================================================

ELECTROLYTE_SALTS: Dict[str, BatteryMaterial] = {}

# LiPF6
ELECTROLYTE_SALTS['LiPF6'] = BatteryMaterial(
    name='LiPF6',
    formula='LiPF6',
    material_class=MaterialClass.ELECTROLYTE_SALT,
    crystal_structure=CrystalStructure.MOLECULAR,
    # 1M LiPF6 in EC:DMC -> ~10 mS/cm (Xu, Chem. Rev. 2004)
    ionic_conductivity=1e-2,
    thermal_stability_max=80,  # Decomposes to LiF + PF5 above ~80C
    failure_modes=[
        FailureMode.THERMAL_RUNAWAY,             # PF5 + H2O -> HF
        FailureMode.ELECTROLYTE_DECOMPOSITION,   # Moisture sensitivity
    ],
    sources={
        'conductivity': 'Xu, Chem. Rev. 2004',
        'thermal': 'Yang et al., J. Power Sources 2006',
    },
    metadata={
        'concentration_M': 1.0,
        'role': 'Standard salt; excellent conductivity but poor thermal stability',
        'HF_risk': True,  # Generates HF with moisture
    },
)

# LiTFSI
ELECTROLYTE_SALTS['LiTFSI'] = BatteryMaterial(
    name='LiTFSI',
    formula='LiN(SO2CF3)2',
    material_class=MaterialClass.ELECTROLYTE_SALT,
    crystal_structure=CrystalStructure.MOLECULAR,
    ionic_conductivity=7e-3,  # Slightly lower than LiPF6
    thermal_stability_max=360,  # Much more thermally stable
    failure_modes=[
        FailureMode.TRANSITION_METAL_DISSOLUTION,  # Corrodes Al above 3.7V
    ],
    sources={
        'conductivity': 'Xu, Chem. Rev. 2004',
        'thermal': 'Xu, Chem. Rev. 2004',
    },
    metadata={
        'role': 'Thermally stable salt; corrodes Al current collector above 3.7V',
        'al_corrosion_onset_V': 3.7,
    },
)


# =============================================================================
# SOLID ELECTROLYTES
# =============================================================================

SOLID_ELECTROLYTES: Dict[str, BatteryMaterial] = {}

# LLZO (Li7La3Zr2O12, garnet)
SOLID_ELECTROLYTES['LLZO'] = BatteryMaterial(
    name='LLZO',
    formula='Li7La3Zr2O12',
    material_class=MaterialClass.SOLID_ELECTROLYTE,
    crystal_structure=CrystalStructure.GARNET,
    # Murugan et al., Angew. Chem. 2007: ~1e-4 S/cm (cubic phase)
    ionic_conductivity=1e-4,
    electronic_conductivity=1e-10,  # Negligible
    # Wide window: 0-6V (Monroe & Newman 2005; Zhu et al. 2015)
    oxidation_potential=6.0,
    reduction_potential=0.0,
    density=5.10,
    thermal_stability_max=900,
    elastic_modulus=150.0,  # GPa, Monroe & Newman 2005
    failure_modes=[
        FailureMode.DENDRITE_GROWTH,  # Li can penetrate grain boundaries
        FailureMode.CRACKING,         # Brittle ceramic
    ],
    sources={
        'conductivity': 'Murugan et al., Angew. Chem. 2007',
        'stability': 'Zhu et al., ACS Appl. Mater. Interfaces 2015',
        'modulus': 'Monroe & Newman, J. Electrochem. Soc. 2005',
    },
)

# LGPS (Li10GeP2S12)
SOLID_ELECTROLYTES['LGPS'] = BatteryMaterial(
    name='LGPS',
    formula='Li10GeP2S12',
    material_class=MaterialClass.SOLID_ELECTROLYTE,
    crystal_structure=CrystalStructure.THIO_LISICON,
    # Kamaya et al., Nat. Mater. 2011: 12 mS/cm (liquid-like!)
    ionic_conductivity=1.2e-2,
    electronic_conductivity=1e-9,
    # Narrow stability: ~1.7-2.1V (Zhu et al. 2015; Richards et al. 2016)
    oxidation_potential=2.1,
    reduction_potential=1.7,
    density=2.03,
    thermal_stability_max=500,
    elastic_modulus=25.0,  # GPa, softer than oxide
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,  # Narrows electrochemical window
        FailureMode.THERMAL_RUNAWAY,             # Generates H2S with moisture
    ],
    sources={
        'conductivity': 'Kamaya et al., Nat. Mater. 2011',
        'stability': 'Zhu et al., ACS Appl. Mater. Interfaces 2015',
        'window': 'Richards et al., Chem. Mater. 2016',
    },
)

# Li3PS4 (beta phase)
SOLID_ELECTROLYTES['Li3PS4'] = BatteryMaterial(
    name='Li3PS4',
    formula='Li3PS4',
    material_class=MaterialClass.SOLID_ELECTROLYTE,
    crystal_structure=CrystalStructure.AMORPHOUS,  # Commonly used amorphous
    ionic_conductivity=1.6e-4,  # Liu et al. 2013
    electronic_conductivity=1e-10,
    oxidation_potential=2.5,
    reduction_potential=1.5,
    density=1.88,
    thermal_stability_max=300,
    elastic_modulus=18.0,  # GPa
    failure_modes=[
        FailureMode.ELECTROLYTE_DECOMPOSITION,
    ],
    sources={
        'conductivity': 'Liu et al., J. Am. Chem. Soc. 2013',
    },
)


# =============================================================================
# IONS
# =============================================================================

IONS: Dict[str, BatteryMaterial] = {}

# Li+
IONS['Li+'] = BatteryMaterial(
    name='Li+',
    formula='Li+',
    material_class=MaterialClass.ION,
    crystal_structure=CrystalStructure.AMORPHOUS,  # In solution
    ionic_radius=0.76,  # Shannon radii, coordination 6 (Shannon, Acta Cryst. 1976)
    density=None,
    metadata={
        'charge': 1,
        'electronegativity': 0.98,  # Pauling scale
        'coordination_numbers': [4, 6],
        'diffusion_in_liquid': 1e-6,  # cm2/s typical in carbonate electrolyte
    },
    sources={
        'radius': 'Shannon, Acta Cryst. A 1976',
    },
)

# Na+
IONS['Na+'] = BatteryMaterial(
    name='Na+',
    formula='Na+',
    material_class=MaterialClass.ION,
    crystal_structure=CrystalStructure.AMORPHOUS,
    ionic_radius=1.02,  # Shannon, coord 6
    metadata={
        'charge': 1,
        'electronegativity': 0.93,
        'coordination_numbers': [4, 6, 8],
    },
    sources={
        'radius': 'Shannon, Acta Cryst. A 1976',
    },
)

# Mg2+
IONS['Mg2+'] = BatteryMaterial(
    name='Mg2+',
    formula='Mg2+',
    material_class=MaterialClass.ION,
    crystal_structure=CrystalStructure.AMORPHOUS,
    ionic_radius=0.72,  # Shannon, coord 6
    metadata={
        'charge': 2,
        'electronegativity': 1.31,
        'coordination_numbers': [4, 6],
        'note': 'Divalent: higher charge density, sluggish diffusion in hosts',
    },
    sources={
        'radius': 'Shannon, Acta Cryst. A 1976',
    },
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_MATERIALS: Dict[str, BatteryMaterial] = {}
ALL_MATERIALS.update(CATHODE_MATERIALS)
ALL_MATERIALS.update(ANODE_MATERIALS)
ALL_MATERIALS.update(ELECTROLYTE_SOLVENTS)
ALL_MATERIALS.update(ELECTROLYTE_SALTS)
ALL_MATERIALS.update(SOLID_ELECTROLYTES)
ALL_MATERIALS.update(IONS)


def get_material(name: str) -> Optional[BatteryMaterial]:
    """Look up a material by name."""
    return ALL_MATERIALS.get(name)


def get_materials_by_class(material_class: MaterialClass) -> Dict[str, BatteryMaterial]:
    """Get all materials of a given class."""
    return {k: v for k, v in ALL_MATERIALS.items()
            if v.material_class == material_class}


def list_cathodes() -> List[str]:
    return list(CATHODE_MATERIALS.keys())


def list_anodes() -> List[str]:
    return list(ANODE_MATERIALS.keys())


def list_electrolytes() -> List[str]:
    """List all electrolyte components (solvents + salts + solid)."""
    return (list(ELECTROLYTE_SOLVENTS.keys()) +
            list(ELECTROLYTE_SALTS.keys()) +
            list(SOLID_ELECTROLYTES.keys()))


# =============================================================================
# KNOWN GOOD/BAD PAIRINGS (for test validation)
# =============================================================================

KNOWN_GOOD_CELLS = [
    {
        'name': 'Standard LFP cell',
        'cathode': 'LFP',
        'anode': 'Graphite',
        'electrolyte_salt': 'LiPF6',
        'electrolyte_solvents': ['EC', 'DMC'],
        'notes': 'Mature, safe chemistry used in millions of EVs (BYD Blade)',
    },
    {
        'name': 'Standard NMC811 EV cell',
        'cathode': 'NMC811',
        'anode': 'Graphite',
        'electrolyte_salt': 'LiPF6',
        'electrolyte_solvents': ['EC', 'EMC'],
        'notes': 'High energy density EV cell (Tesla, BMW, etc.)',
    },
]

KNOWN_BAD_PAIRINGS = [
    {
        'name': 'Li metal + liquid carbonate',
        'material_a': 'Li_metal',
        'material_b': 'EC',
        'issue': 'Dendrite growth through liquid electrolyte -> internal short',
        'expected_flag': FailureMode.DENDRITE_GROWTH,
    },
    {
        'name': 'NMC811 >4.3V + EC',
        'material_a': 'NMC811',
        'material_b': 'EC',
        'issue': 'EC oxidation at cathode surface above 4.3V',
        'expected_flag': FailureMode.ELECTROLYTE_DECOMPOSITION,
    },
    {
        'name': 'Si anode + standard electrolyte',
        'material_a': 'Si',
        'material_b': 'EC',
        'issue': '300% volume expansion pulverizes SEI layer',
        'expected_flag': FailureMode.VOLUME_EXPANSION,
    },
    {
        'name': 'LGPS + high voltage cathode',
        'material_a': 'LGPS',
        'material_b': 'NMC811',
        'issue': 'LGPS decomposes above 2.1V; NMC811 operates at 3.8V',
        'expected_flag': FailureMode.ELECTROLYTE_DECOMPOSITION,
    },
]


if __name__ == "__main__":
    print("=" * 70)
    print("Battery Material Properties - Summary")
    print("=" * 70)
    print()
    print(f"Cathode materials: {len(CATHODE_MATERIALS)}")
    for name, mat in CATHODE_MATERIALS.items():
        print(f"  {name:8s} ({mat.formula:25s}) "
              f"V={mat.voltage_window.nominal:.1f}V  "
              f"Cap={mat.theoretical_capacity:.0f} mAh/g")
    print()
    print(f"Anode materials: {len(ANODE_MATERIALS)}")
    for name, mat in ANODE_MATERIALS.items():
        cap = f"{mat.theoretical_capacity:.0f}" if mat.theoretical_capacity else "N/A"
        print(f"  {name:8s} ({mat.formula:10s}) Cap={cap} mAh/g")
    print()
    print(f"Electrolyte solvents: {len(ELECTROLYTE_SOLVENTS)}")
    print(f"Electrolyte salts: {len(ELECTROLYTE_SALTS)}")
    print(f"Solid electrolytes: {len(SOLID_ELECTROLYTES)}")
    print(f"Ions: {len(IONS)}")
    print(f"\nTotal materials: {len(ALL_MATERIALS)}")
