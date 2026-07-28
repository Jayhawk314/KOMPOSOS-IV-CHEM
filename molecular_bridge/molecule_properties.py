# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular-Level Property Database
====================================

Validated property tables for individual molecules relevant to battery
chemistry, polymer synthesis, coatings, and materials processing.

This is the molecular-level counterpart to battery_bridge/material_properties.py.
Where the battery bridge operates at the material level (NMC811, LFP, etc.),
this module operates at the molecule level (EC, DMC, LiPF6, etc.) with
per-molecule physical/chemical properties, PubChem CIDs, CAS numbers,
and SMILES strings.

Property Sources:
-----------------
- PubChem (https://pubchem.ncbi.nlm.nih.gov/) -- CIDs, MW, SMILES, bp/mp
- CRC Handbook of Chemistry and Physics, 97th ed. -- thermodynamic data
- NIST Chemistry WebBook (https://webbook.nist.gov/) -- vapor pressure, IE
- Xu, Chem. Rev. 2004, 104, 4303 -- electrolyte solvent properties
- Aurbach et al., Electrochim. Acta 2002, 47, 1423 -- SEI chemistry
- Haynes, CRC Handbook 2016 -- physical constants
- DrugBank / ChemicalBook -- logP, pKa, solubility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class MoleculeClass(Enum):
    """Classification of molecules by role in chemistry/materials."""
    ELECTROLYTE_SOLVENT = "electrolyte_solvent"
    SALT_ANION = "salt_anion"
    POLYMER_MONOMER = "polymer_monomer"
    REAGENT = "reagent"
    COATING = "coating"
    GAS = "gas"
    ADDITIVE = "additive"
    OTHER = "other"


@dataclass
class Molecule:
    """
    A molecule with validated physical and chemical properties.

    Every molecule has a PubChem CID (0 if unknown), CAS number,
    SMILES string, and published property data with source citations.
    """
    # Identity
    name: str
    formula: str
    pubchem_cid: int                    # PubChem Compound ID (0 if unknown)
    cas_number: str                     # CAS Registry Number
    smiles: str                         # Canonical SMILES

    # Basic properties
    molecular_weight: float             # g/mol
    functional_groups: List[str] = field(default_factory=list)

    # Thermodynamic / physical properties
    boiling_point_C: Optional[float] = None
    melting_point_C: Optional[float] = None
    vapor_pressure_mmHg_25C: Optional[float] = None
    density_g_cm3: Optional[float] = None
    logP: Optional[float] = None        # Octanol-water partition coefficient
    solubility_mg_L: Optional[float] = None  # Water solubility at 25C

    # Electronic properties
    ionization_energy_eV: Optional[float] = None
    electron_affinity_eV: Optional[float] = None
    dipole_moment_debye: Optional[float] = None
    polarizability_A3: Optional[float] = None

    # Hydrogen bonding
    hbond_donors: int = 0
    hbond_acceptors: int = 0

    # Redox properties
    is_reducing: bool = False
    is_oxidizing: bool = False
    redox_potential_V: Optional[float] = None  # Standard reduction potential

    # Acid-base and safety
    pKa: Optional[float] = None
    flash_point_C: Optional[float] = None

    # Classification
    molecule_class: MoleculeClass = MoleculeClass.OTHER
    hazard_class: str = "unclassified"

    # Source citations
    sources: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            'name': self.name,
            'formula': self.formula,
            'pubchem_cid': self.pubchem_cid,
            'cas_number': self.cas_number,
            'smiles': self.smiles,
            'molecular_weight': self.molecular_weight,
            'molecule_class': self.molecule_class.value,
            'hazard_class': self.hazard_class,
            'functional_groups': self.functional_groups,
            'hbond_donors': self.hbond_donors,
            'hbond_acceptors': self.hbond_acceptors,
            'is_reducing': self.is_reducing,
            'is_oxidizing': self.is_oxidizing,
        }
        # Optional floats
        for attr in ('boiling_point_C', 'melting_point_C', 'vapor_pressure_mmHg_25C',
                      'density_g_cm3', 'logP', 'solubility_mg_L',
                      'ionization_energy_eV', 'electron_affinity_eV',
                      'dipole_moment_debye', 'polarizability_A3',
                      'redox_potential_V', 'pKa', 'flash_point_C'):
            val = getattr(self, attr)
            if val is not None:
                result[attr] = val
        return result


# =============================================================================
# ELECTROLYTE SOLVENTS (7 molecules)
# =============================================================================

ELECTROLYTE_SOLVENTS: Dict[str, Molecule] = {}

# Ethylene Carbonate (EC)
ELECTROLYTE_SOLVENTS['EC'] = Molecule(
    name='EC',
    formula='C3H4O3',
    pubchem_cid=7303,
    cas_number='96-49-1',
    smiles='O=C1OCCO1',
    molecular_weight=88.06,
    functional_groups=['carbonate', 'cyclic_ester'],
    boiling_point_C=248.0,       # PubChem / CRC
    melting_point_C=36.4,        # Solid at room temperature
    vapor_pressure_mmHg_25C=0.01,  # Very low -- Xu 2004
    density_g_cm3=1.321,         # CRC Handbook
    logP=-0.41,                  # PubChem
    solubility_mg_L=None,        # Miscible with polar organics
    ionization_energy_eV=10.5,   # NIST est.
    electron_affinity_eV=None,
    dipole_moment_debye=4.87,    # Xu, Chem. Rev. 2004
    polarizability_A3=6.05,      # Computational est.
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=143.0,         # PubChem
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 7303; CRC Handbook 97th ed.',
        'density': 'CRC Handbook 97th ed.',
        'dipole': 'Xu, Chem. Rev. 2004, 104, 4303',
        'logP': 'PubChem CID 7303',
        'flash_point': 'PubChem CID 7303',
    },
)

# Dimethyl Carbonate (DMC)
ELECTROLYTE_SOLVENTS['DMC'] = Molecule(
    name='DMC',
    formula='C3H6O3',
    pubchem_cid=12021,
    cas_number='616-38-6',
    smiles='COC(=O)OC',
    molecular_weight=90.08,
    functional_groups=['carbonate', 'linear_ester'],
    boiling_point_C=90.0,
    melting_point_C=4.6,
    vapor_pressure_mmHg_25C=18.3,  # NIST
    density_g_cm3=1.069,
    logP=0.23,                     # PubChem
    solubility_mg_L=139000.0,      # ~139 g/L in water
    ionization_energy_eV=10.2,
    electron_affinity_eV=None,
    dipole_moment_debye=0.91,      # Xu 2004
    polarizability_A3=6.74,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=18.0,            # PubChem
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 12021; CRC Handbook',
        'density': 'CRC Handbook',
        'dipole': 'Xu, Chem. Rev. 2004',
        'vapor_pressure': 'NIST WebBook',
    },
)

# Diethyl Carbonate (DEC)
ELECTROLYTE_SOLVENTS['DEC'] = Molecule(
    name='DEC',
    formula='C5H10O3',
    pubchem_cid=7766,
    cas_number='105-58-8',
    smiles='CCOC(=O)OCC',
    molecular_weight=118.13,
    functional_groups=['carbonate', 'linear_ester'],
    boiling_point_C=126.0,
    melting_point_C=-43.0,
    vapor_pressure_mmHg_25C=10.5,
    density_g_cm3=0.975,
    logP=1.21,                     # PubChem
    solubility_mg_L=15700.0,
    ionization_energy_eV=10.0,
    electron_affinity_eV=None,
    dipole_moment_debye=0.96,
    polarizability_A3=9.50,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=25.0,
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 7766; CRC Handbook',
        'density': 'CRC Handbook',
        'dipole': 'Xu, Chem. Rev. 2004',
    },
)

# Ethyl Methyl Carbonate (EMC)
ELECTROLYTE_SOLVENTS['EMC'] = Molecule(
    name='EMC',
    formula='C4H8O3',
    pubchem_cid=522046,
    cas_number='623-53-0',
    smiles='CCOC(=O)OC',
    molecular_weight=104.10,
    functional_groups=['carbonate', 'linear_ester'],
    boiling_point_C=107.0,
    melting_point_C=-53.0,
    vapor_pressure_mmHg_25C=14.0,
    density_g_cm3=1.006,
    logP=0.72,
    solubility_mg_L=None,
    ionization_energy_eV=10.1,
    electron_affinity_eV=None,
    dipole_moment_debye=0.89,
    polarizability_A3=8.10,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=23.0,
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 522046; Xu, Chem. Rev. 2004',
        'density': 'Xu, Chem. Rev. 2004',
        'dipole': 'Xu, Chem. Rev. 2004',
    },
)

# Propylene Carbonate (PC)
ELECTROLYTE_SOLVENTS['PC'] = Molecule(
    name='PC',
    formula='C4H6O3',
    pubchem_cid=7924,
    cas_number='108-32-7',
    smiles='CC1COC(=O)O1',
    molecular_weight=102.09,
    functional_groups=['carbonate', 'cyclic_ester'],
    boiling_point_C=242.0,
    melting_point_C=-48.8,
    vapor_pressure_mmHg_25C=0.03,
    density_g_cm3=1.205,
    logP=-0.41,                    # PubChem
    solubility_mg_L=240000.0,      # ~240 g/L
    ionization_energy_eV=10.5,
    electron_affinity_eV=None,
    dipole_moment_debye=4.94,      # Xu 2004
    polarizability_A3=8.56,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=132.0,
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 7924; CRC Handbook',
        'density': 'CRC Handbook',
        'dipole': 'Xu, Chem. Rev. 2004',
    },
)

# Fluoroethylene Carbonate (FEC) -- additive for Si anodes
ELECTROLYTE_SOLVENTS['FEC'] = Molecule(
    name='FEC',
    formula='C3H3FO3',
    pubchem_cid=69722,
    cas_number='114435-02-8',
    smiles='O=C1OC(F)CO1',
    molecular_weight=106.05,
    functional_groups=['carbonate', 'cyclic_ester', 'fluoride'],
    boiling_point_C=249.0,         # Est. from analogues
    melting_point_C=18.0,
    vapor_pressure_mmHg_25C=0.02,
    density_g_cm3=1.454,
    logP=-0.47,
    solubility_mg_L=None,
    ionization_energy_eV=11.0,     # Higher due to F
    electron_affinity_eV=None,
    dipole_moment_debye=5.10,      # Est.
    polarizability_A3=6.00,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=120.0,
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'density': 'ChemicalBook CAS 114435-02-8',
        'mp': 'Sigma-Aldrich product data',
        'role': 'SEI-forming additive for Si anodes; Xu et al., Energy Environ. Sci. 2014',
    },
)

# Vinylene Carbonate (VC) -- SEI-forming additive
ELECTROLYTE_SOLVENTS['VC'] = Molecule(
    name='VC',
    formula='C3H2O3',
    pubchem_cid=67532,
    cas_number='872-36-6',
    smiles='O=C1OC=CO1',
    molecular_weight=86.05,
    functional_groups=['carbonate', 'cyclic_ester', 'vinyl'],
    boiling_point_C=162.0,
    melting_point_C=22.0,
    vapor_pressure_mmHg_25C=0.3,
    density_g_cm3=1.355,
    logP=-0.63,
    solubility_mg_L=None,
    ionization_energy_eV=10.3,
    electron_affinity_eV=None,
    dipole_moment_debye=4.55,
    polarizability_A3=5.50,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=73.0,
    molecule_class=MoleculeClass.ELECTROLYTE_SOLVENT,
    hazard_class='flammable liquid',
    sources={
        'bp_mp': 'PubChem CID 67532',
        'density': 'Sigma-Aldrich product data',
        'role': 'SEI film-forming additive; Aurbach et al., Electrochim. Acta 2002',
    },
)


# =============================================================================
# SALT ANIONS (4 molecules -- represented as their lithium salts)
# =============================================================================

SALT_ANIONS: Dict[str, Molecule] = {}

# LiPF6
SALT_ANIONS['LiPF6'] = Molecule(
    name='LiPF6',
    formula='LiPF6',
    pubchem_cid=23685558,
    cas_number='21324-40-3',
    smiles='[Li+].F[P-](F)(F)(F)(F)F',
    molecular_weight=151.91,
    functional_groups=['hexafluorophosphate', 'ionic_salt'],
    boiling_point_C=None,          # Decomposes before boiling
    melting_point_C=200.0,         # Decomposes ~200 C
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.50,
    logP=None,
    solubility_mg_L=None,          # Soluble in organic carbonates
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=6,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.SALT_ANION,
    hazard_class='corrosive; moisture-sensitive',
    sources={
        'mw': 'PubChem CID 23685558',
        'mp': 'Yang et al., J. Power Sources 2006',
        'conductivity': '~10 mS/cm at 1M in EC:DMC -- Xu, Chem. Rev. 2004',
    },
)

# LiTFSI (LiN(SO2CF3)2)
SALT_ANIONS['LiTFSI'] = Molecule(
    name='LiTFSI',
    formula='LiC2F6NO4S2',
    pubchem_cid=68648,
    cas_number='90076-65-6',
    smiles='[Li+].O=S(=O)([N-]S(=O)(=O)C(F)(F)F)C(F)(F)F',
    molecular_weight=287.09,
    functional_groups=['bis_trifluoromethanesulfonimide', 'ionic_salt'],
    boiling_point_C=None,          # Decomposes
    melting_point_C=236.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=None,
    logP=None,
    solubility_mg_L=None,
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=-2.0,                     # Very strong acid (TFSI anion)
    flash_point_C=None,
    molecule_class=MoleculeClass.SALT_ANION,
    hazard_class='corrosive; moisture-sensitive',
    sources={
        'mw': 'PubChem CID 68648',
        'pKa': 'Foropoulos & DesMarteau, Inorg. Chem. 1984',
        'conductivity': '~7 mS/cm at 1M -- Xu, Chem. Rev. 2004',
    },
)

# LiBF4
SALT_ANIONS['LiBF4'] = Molecule(
    name='LiBF4',
    formula='LiBF4',
    pubchem_cid=66577,
    cas_number='14283-07-9',
    smiles='[Li+].F[B-](F)(F)F',
    molecular_weight=93.75,
    functional_groups=['tetrafluoroborate', 'ionic_salt'],
    boiling_point_C=None,
    melting_point_C=293.0,         # Decomposes
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=None,
    logP=None,
    solubility_mg_L=None,
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.SALT_ANION,
    hazard_class='corrosive; moisture-sensitive',
    sources={
        'mw': 'PubChem CID 66577',
        'conductivity': '~3.4 mS/cm at 1M in EC:DMC -- Xu, Chem. Rev. 2004',
    },
)

# LiClO4
SALT_ANIONS['LiClO4'] = Molecule(
    name='LiClO4',
    formula='LiClO4',
    pubchem_cid=23665647,
    cas_number='7791-03-9',
    smiles='[Li+].[O-]Cl(=O)(=O)=O',
    molecular_weight=106.39,
    functional_groups=['perchlorate', 'ionic_salt'],
    boiling_point_C=None,          # Decomposes ~400 C
    melting_point_C=236.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=2.42,
    logP=None,
    solubility_mg_L=None,
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=True,             # Perchlorate is a strong oxidizer
    redox_potential_V=1.23,        # ClO4-/Cl- ~1.23 V vs SHE
    pKa=-10.0,                    # Very strong acid
    flash_point_C=None,
    molecule_class=MoleculeClass.SALT_ANION,
    hazard_class='oxidizer; explosive risk',
    sources={
        'mw': 'PubChem CID 23665647',
        'density': 'CRC Handbook',
        'conductivity': '~5.6 mS/cm at 1M in EC:DMC -- Xu, Chem. Rev. 2004',
        'redox': 'CRC Handbook',
    },
)


# =============================================================================
# POLYMER MONOMERS (5 molecules)
# =============================================================================

POLYMER_MONOMERS: Dict[str, Molecule] = {}

# Ethylene Oxide
POLYMER_MONOMERS['ethylene_oxide'] = Molecule(
    name='ethylene_oxide',
    formula='C2H4O',
    pubchem_cid=6354,
    cas_number='75-21-8',
    smiles='C1CO1',
    molecular_weight=44.05,
    functional_groups=['epoxide'],
    boiling_point_C=10.7,
    melting_point_C=-111.3,
    vapor_pressure_mmHg_25C=1314.0,  # Very volatile
    density_g_cm3=0.882,             # Liquid at bp
    logP=-0.30,
    solubility_mg_L=None,            # Miscible with water
    ionization_energy_eV=10.56,      # NIST
    electron_affinity_eV=-1.76,      # Negative = does not bind electron easily
    dipole_moment_debye=1.89,
    polarizability_A3=4.43,
    hbond_donors=0,
    hbond_acceptors=1,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=-20.0,
    molecule_class=MoleculeClass.POLYMER_MONOMER,
    hazard_class='extremely flammable; toxic; carcinogen',
    sources={
        'bp_mp': 'PubChem CID 6354; NIST WebBook',
        'IE': 'NIST WebBook',
        'dipole': 'NIST WebBook',
        'polymer': 'Monomer for PEO (solid polymer electrolyte)',
    },
)

# Vinylidene Fluoride (VDF) -- monomer for PVDF
POLYMER_MONOMERS['vinylidene_fluoride'] = Molecule(
    name='vinylidene_fluoride',
    formula='C2H2F2',
    pubchem_cid=6366,
    cas_number='75-38-7',
    smiles='C=C(F)F',
    molecular_weight=64.03,
    functional_groups=['vinyl', 'gem_difluoride'],
    boiling_point_C=-83.0,
    melting_point_C=-144.0,
    vapor_pressure_mmHg_25C=25700.0,  # Gas at room temp
    density_g_cm3=None,               # Gas
    logP=0.75,
    solubility_mg_L=None,
    ionization_energy_eV=10.29,       # NIST
    electron_affinity_eV=None,
    dipole_moment_debye=1.37,
    polarizability_A3=4.00,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=-83.0,             # Gas -- autoignition relevant
    molecule_class=MoleculeClass.POLYMER_MONOMER,
    hazard_class='extremely flammable gas',
    sources={
        'bp_mp': 'PubChem CID 6366; NIST WebBook',
        'IE': 'NIST WebBook',
        'polymer': 'Monomer for PVDF binder (battery cathodes)',
    },
)

# Acrylonitrile
POLYMER_MONOMERS['acrylonitrile'] = Molecule(
    name='acrylonitrile',
    formula='C3H3N',
    pubchem_cid=7855,
    cas_number='107-13-1',
    smiles='C=CC#N',
    molecular_weight=53.06,
    functional_groups=['vinyl', 'nitrile'],
    boiling_point_C=77.3,
    melting_point_C=-83.6,
    vapor_pressure_mmHg_25C=109.0,
    density_g_cm3=0.806,
    logP=0.25,                     # PubChem
    solubility_mg_L=73500.0,       # ~7.35%
    ionization_energy_eV=10.91,    # NIST
    electron_affinity_eV=0.01,
    dipole_moment_debye=3.87,
    polarizability_A3=5.79,
    hbond_donors=0,
    hbond_acceptors=1,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=25.0,                     # Very weak acid (alpha-H)
    flash_point_C=0.0,
    molecule_class=MoleculeClass.POLYMER_MONOMER,
    hazard_class='flammable; toxic; carcinogen',
    sources={
        'bp_mp': 'PubChem CID 7855; CRC Handbook',
        'IE': 'NIST WebBook',
        'dipole': 'CRC Handbook',
        'polymer': 'Monomer for PAN (carbon fiber precursor, separator coatings)',
    },
)

# Styrene
POLYMER_MONOMERS['styrene'] = Molecule(
    name='styrene',
    formula='C8H8',
    pubchem_cid=7501,
    cas_number='100-42-5',
    smiles='C=Cc1ccccc1',
    molecular_weight=104.15,
    functional_groups=['vinyl', 'aromatic'],
    boiling_point_C=145.0,
    melting_point_C=-30.6,
    vapor_pressure_mmHg_25C=6.4,
    density_g_cm3=0.906,
    logP=2.95,                     # PubChem
    solubility_mg_L=310.0,
    ionization_energy_eV=8.43,     # NIST
    electron_affinity_eV=0.00,
    dipole_moment_debye=0.13,
    polarizability_A3=14.48,
    hbond_donors=0,
    hbond_acceptors=0,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=44.0,                     # Vinylic C-H extremely weak
    flash_point_C=31.0,
    molecule_class=MoleculeClass.POLYMER_MONOMER,
    hazard_class='flammable liquid; possible carcinogen',
    sources={
        'bp_mp': 'PubChem CID 7501; CRC Handbook',
        'IE': 'NIST WebBook',
        'dipole': 'CRC Handbook',
    },
)

# Methyl Methacrylate (MMA)
POLYMER_MONOMERS['methyl_methacrylate'] = Molecule(
    name='methyl_methacrylate',
    formula='C5H8O2',
    pubchem_cid=6658,
    cas_number='80-62-6',
    smiles='CC(=C)C(=O)OC',
    molecular_weight=100.12,
    functional_groups=['vinyl', 'ester', 'methacrylate'],
    boiling_point_C=100.0,
    melting_point_C=-48.0,
    vapor_pressure_mmHg_25C=38.5,
    density_g_cm3=0.936,
    logP=1.38,
    solubility_mg_L=15900.0,
    ionization_energy_eV=9.70,     # NIST
    electron_affinity_eV=None,
    dipole_moment_debye=1.67,
    polarizability_A3=10.10,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=10.0,
    molecule_class=MoleculeClass.POLYMER_MONOMER,
    hazard_class='flammable liquid; irritant',
    sources={
        'bp_mp': 'PubChem CID 6658; CRC Handbook',
        'IE': 'NIST WebBook',
        'polymer': 'Monomer for PMMA (optical coatings, gel electrolytes)',
    },
)


# =============================================================================
# COMMON REAGENTS (10 molecules)
# =============================================================================

REAGENTS: Dict[str, Molecule] = {}

# Lithium Hydroxide
REAGENTS['LiOH'] = Molecule(
    name='LiOH',
    formula='LiOH',
    pubchem_cid=3939,
    cas_number='1310-65-2',
    smiles='[Li]O',
    molecular_weight=23.95,
    functional_groups=['hydroxide'],
    boiling_point_C=924.0,
    melting_point_C=462.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.46,
    logP=None,
    solubility_mg_L=128000.0,      # 12.8 g/100 mL
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=4.75,
    polarizability_A3=None,
    hbond_donors=1,
    hbond_acceptors=1,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=13.8,                     # Strong base
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='corrosive',
    sources={
        'bp_mp': 'CRC Handbook',
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
    },
)

# Phosphoric Acid
REAGENTS['H3PO4'] = Molecule(
    name='H3PO4',
    formula='H3PO4',
    pubchem_cid=1004,
    cas_number='7664-38-2',
    smiles='OP(O)(O)=O',
    molecular_weight=98.00,
    functional_groups=['phosphoric_acid', 'hydroxy'],
    boiling_point_C=158.0,         # Decomposes
    melting_point_C=42.4,
    vapor_pressure_mmHg_25C=0.03,
    density_g_cm3=1.885,           # 85% aqueous
    logP=-0.77,
    solubility_mg_L=None,          # Miscible with water
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=3,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=2.15,                     # First dissociation
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='corrosive',
    sources={
        'mp_bp': 'CRC Handbook',
        'density': 'CRC Handbook -- 85% solution',
        'pKa': 'CRC Handbook (pKa1=2.15, pKa2=7.20, pKa3=12.35)',
    },
)

# Iron(II) Sulfate
REAGENTS['FeSO4'] = Molecule(
    name='FeSO4',
    formula='FeSO4',
    pubchem_cid=24393,
    cas_number='7720-78-7',
    smiles='[Fe+2].[O-]S([O-])(=O)=O',
    molecular_weight=151.91,
    functional_groups=['sulfate', 'iron_salt'],
    boiling_point_C=None,          # Decomposes at ~400 C
    melting_point_C=680.0,         # Anhydrous, decomposes before melting
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=3.65,            # Anhydrous
    logP=None,
    solubility_mg_L=295000.0,      # 29.5 g/100 mL at 25 C
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=True,              # Fe2+ is a reducing agent
    is_oxidizing=False,
    redox_potential_V=-0.44,       # Fe2+/Fe standard reduction potential
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='irritant',
    sources={
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'redox': 'CRC Handbook: Fe2+/Fe = -0.44 V vs SHE',
        'role': 'Fe source for LFP synthesis',
    },
)

# Lithium Carbonate
REAGENTS['Li2CO3'] = Molecule(
    name='Li2CO3',
    formula='Li2CO3',
    pubchem_cid=11125,
    cas_number='554-13-2',
    smiles='[Li+].[Li+].[O-]C([O-])=O',
    molecular_weight=73.89,
    functional_groups=['carbonate'],
    boiling_point_C=1310.0,        # Decomposes
    melting_point_C=723.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=2.11,
    logP=None,
    solubility_mg_L=13300.0,       # 1.33 g/100 mL at 20 C
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=10.33,                    # Carbonate pKa2
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='irritant',
    sources={
        'bp_mp': 'CRC Handbook',
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'role': 'Li source for cathode synthesis (NMC, LMO, LCO)',
    },
)

# Manganese Dioxide
REAGENTS['MnO2'] = Molecule(
    name='MnO2',
    formula='MnO2',
    pubchem_cid=14801,
    cas_number='1313-13-9',
    smiles='O=[Mn]=O',
    molecular_weight=86.94,
    functional_groups=['oxide'],
    boiling_point_C=None,          # Decomposes at ~535 C
    melting_point_C=535.0,         # Decomposes
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=5.03,
    logP=None,
    solubility_mg_L=None,          # Insoluble
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=True,             # Strong oxidizer
    redox_potential_V=1.23,        # MnO2/Mn2+ in acid
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='oxidizer; harmful',
    sources={
        'density': 'CRC Handbook',
        'redox': 'CRC Handbook: MnO2/Mn2+ = +1.23 V vs SHE (acidic)',
        'role': 'Mn source for LMO/NMC cathode synthesis',
    },
)

# Nickel(II) Sulfate
REAGENTS['NiSO4'] = Molecule(
    name='NiSO4',
    formula='NiSO4',
    pubchem_cid=24404,
    cas_number='7786-81-4',
    smiles='[Ni+2].[O-]S([O-])(=O)=O',
    molecular_weight=154.76,
    functional_groups=['sulfate', 'nickel_salt'],
    boiling_point_C=None,
    melting_point_C=840.0,         # Anhydrous decomposes
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=3.68,
    logP=None,
    solubility_mg_L=293000.0,      # 29.3 g/100 mL at 20 C (hexahydrate)
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=-0.26,       # Ni2+/Ni
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='carcinogen; sensitizer; toxic to aquatic life',
    sources={
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook (hexahydrate)',
        'redox': 'CRC Handbook: Ni2+/Ni = -0.26 V vs SHE',
        'role': 'Ni source for NMC cathode co-precipitation',
    },
)

# Cobalt(II) Sulfate
REAGENTS['CoSO4'] = Molecule(
    name='CoSO4',
    formula='CoSO4',
    pubchem_cid=24965,
    cas_number='10124-43-3',
    smiles='[Co+2].[O-]S([O-])(=O)=O',
    molecular_weight=155.00,
    functional_groups=['sulfate', 'cobalt_salt'],
    boiling_point_C=None,
    melting_point_C=735.0,         # Anhydrous
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=3.71,
    logP=None,
    solubility_mg_L=362000.0,      # 36.2 g/100 mL at 20 C
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=-0.28,       # Co2+/Co
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='carcinogen; sensitizer; toxic to aquatic life',
    sources={
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'redox': 'CRC Handbook: Co2+/Co = -0.28 V vs SHE',
        'role': 'Co source for NMC/LCO cathode co-precipitation',
    },
)

# Aluminum Oxide Precursor (Al(NO3)3)
REAGENTS['Al_NO3_3'] = Molecule(
    name='Al_NO3_3',
    formula='Al(NO3)3',
    pubchem_cid=26053,
    cas_number='7784-27-2',
    smiles='[Al+3].[O-][N+]([O-])=O.[O-][N+]([O-])=O.[O-][N+]([O-])=O',
    molecular_weight=213.00,       # Nonahydrate: 375.13
    functional_groups=['nitrate', 'aluminum_salt'],
    boiling_point_C=None,          # Decomposes ~150 C
    melting_point_C=73.0,          # Nonahydrate
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.72,            # Nonahydrate
    logP=None,
    solubility_mg_L=None,          # Very soluble
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=9,
    is_reducing=False,
    is_oxidizing=True,             # Nitrate is an oxidizer
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='oxidizer; irritant',
    sources={
        'density': 'CRC Handbook',
        'role': 'Al2O3 coating precursor for sol-gel cathode coating',
    },
)

# Titanium Dioxide Precursor (TiO2, anatase)
REAGENTS['TiO2'] = Molecule(
    name='TiO2',
    formula='TiO2',
    pubchem_cid=26042,
    cas_number='13463-67-7',
    smiles='O=[Ti]=O',
    molecular_weight=79.87,
    functional_groups=['oxide'],
    boiling_point_C=2972.0,
    melting_point_C=1843.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=3.90,            # Anatase
    logP=None,
    solubility_mg_L=None,          # Insoluble
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='low hazard; possible inhalation risk',
    sources={
        'bp_mp': 'CRC Handbook (anatase phase)',
        'density': 'CRC Handbook',
        'role': 'TiO2 coating for anode materials; LTO precursor',
    },
)

# Urea
REAGENTS['urea'] = Molecule(
    name='urea',
    formula='CH4N2O',
    pubchem_cid=1176,
    cas_number='57-13-6',
    smiles='NC(N)=O',
    molecular_weight=60.06,
    functional_groups=['amide', 'amine'],
    boiling_point_C=None,          # Decomposes at ~133 C
    melting_point_C=133.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.32,
    logP=-2.11,
    solubility_mg_L=1080000.0,     # 108 g/100 mL -- extremely soluble
    ionization_energy_eV=9.56,     # NIST
    electron_affinity_eV=None,
    dipole_moment_debye=3.83,
    polarizability_A3=5.50,
    hbond_donors=2,
    hbond_acceptors=1,
    is_reducing=True,              # Mild reducing agent in synthesis
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=0.18,                     # Very weak base (conjugate acid pKa)
    flash_point_C=None,
    molecule_class=MoleculeClass.REAGENT,
    hazard_class='low hazard',
    sources={
        'mp': 'CRC Handbook',
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'role': 'N source / fuel in combustion synthesis of oxides',
    },
)


# =============================================================================
# COATING / ADDITIVE MOLECULES (5 molecules)
# =============================================================================

COATINGS: Dict[str, Molecule] = {}

# Aluminum Isopropoxide
COATINGS['Al_isopropoxide'] = Molecule(
    name='Al_isopropoxide',
    formula='C9H21AlO3',
    pubchem_cid=8005,
    cas_number='555-31-7',
    smiles='CC(C)O[Al](OC(C)C)OC(C)C',
    molecular_weight=204.24,
    functional_groups=['alkoxide', 'aluminum_alkoxide'],
    boiling_point_C=135.0,         # At 8 mmHg
    melting_point_C=118.0,
    vapor_pressure_mmHg_25C=0.1,   # Low volatility
    density_g_cm3=1.035,
    logP=None,
    solubility_mg_L=None,          # Reacts with water
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=3,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=49.0,
    molecule_class=MoleculeClass.COATING,
    hazard_class='flammable; moisture-sensitive',
    sources={
        'bp_mp': 'PubChem CID 8005',
        'density': 'Sigma-Aldrich product data',
        'role': 'Sol-gel Al2O3 coating precursor for NMC cathodes',
    },
)

# Titanium(IV) Isopropoxide
COATINGS['Ti_isopropoxide'] = Molecule(
    name='Ti_isopropoxide',
    formula='C12H28O4Ti',
    pubchem_cid=7076,
    cas_number='546-68-9',
    smiles='CC(C)O[Ti](OC(C)C)(OC(C)C)OC(C)C',
    molecular_weight=284.22,
    functional_groups=['alkoxide', 'titanium_alkoxide'],
    boiling_point_C=232.0,
    melting_point_C=17.0,
    vapor_pressure_mmHg_25C=2.0,
    density_g_cm3=0.960,
    logP=None,
    solubility_mg_L=None,          # Reacts with water
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=35.0,
    molecule_class=MoleculeClass.COATING,
    hazard_class='flammable; moisture-sensitive; irritant',
    sources={
        'bp_mp': 'PubChem CID 7076; CRC Handbook',
        'density': 'CRC Handbook',
        'role': 'Sol-gel TiO2 coating precursor for anode/cathode coatings',
    },
)

# Zirconium(IV) Propoxide
COATINGS['Zr_propoxide'] = Molecule(
    name='Zr_propoxide',
    formula='C12H28O4Zr',
    pubchem_cid=18944,
    cas_number='23519-77-9',
    smiles='CCCO[Zr](OCCC)(OCCC)OCCC',
    molecular_weight=327.57,
    functional_groups=['alkoxide', 'zirconium_alkoxide'],
    boiling_point_C=None,          # Decomposes
    melting_point_C=None,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.058,
    logP=None,
    solubility_mg_L=None,          # Reacts with water
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=0,
    hbond_acceptors=4,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=21.0,
    molecule_class=MoleculeClass.COATING,
    hazard_class='flammable; moisture-sensitive',
    sources={
        'density': 'Sigma-Aldrich product data',
        'role': 'ZrO2 coating precursor for solid-state electrolyte interfaces',
    },
)

# Citric Acid
COATINGS['citric_acid'] = Molecule(
    name='citric_acid',
    formula='C6H8O7',
    pubchem_cid=311,
    cas_number='77-92-9',
    smiles='OC(=O)CC(O)(CC(O)=O)C(O)=O',
    molecular_weight=192.12,
    functional_groups=['carboxylic_acid', 'hydroxyl', 'tricarboxylic'],
    boiling_point_C=None,          # Decomposes ~175 C
    melting_point_C=153.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.665,
    logP=-1.72,
    solubility_mg_L=730000.0,      # 73 g/100 mL
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=4,
    hbond_acceptors=7,
    is_reducing=True,              # Mild reducing agent / chelator
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=3.13,                     # pKa1
    flash_point_C=None,
    molecule_class=MoleculeClass.COATING,
    hazard_class='irritant',
    sources={
        'mp': 'CRC Handbook',
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'pKa': 'CRC Handbook (pKa1=3.13, pKa2=4.76, pKa3=6.40)',
        'role': 'Chelating agent / carbon source in Pechini sol-gel synthesis',
    },
)

# Oxalic Acid
COATINGS['oxalic_acid'] = Molecule(
    name='oxalic_acid',
    formula='C2H2O4',
    pubchem_cid=971,
    cas_number='144-62-7',
    smiles='OC(=O)C(O)=O',
    molecular_weight=90.03,
    functional_groups=['carboxylic_acid', 'dicarboxylic'],
    boiling_point_C=None,          # Sublimes ~100 C
    melting_point_C=101.5,         # Dihydrate: 101.5 C
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=1.90,            # Anhydrous
    logP=-0.81,
    solubility_mg_L=143000.0,      # 14.3 g/100 mL at 25 C
    ionization_energy_eV=None,
    electron_affinity_eV=None,
    dipole_moment_debye=None,
    polarizability_A3=None,
    hbond_donors=2,
    hbond_acceptors=4,
    is_reducing=True,              # Reducing agent (C in +3 state)
    is_oxidizing=False,
    redox_potential_V=-0.49,       # CO2/H2C2O4 = -0.49 V vs SHE
    pKa=1.25,                     # pKa1 (strong dicarboxylic)
    flash_point_C=None,
    molecule_class=MoleculeClass.COATING,
    hazard_class='harmful; irritant',
    sources={
        'mp': 'CRC Handbook',
        'density': 'CRC Handbook',
        'solubility': 'CRC Handbook',
        'pKa': 'CRC Handbook (pKa1=1.25, pKa2=4.27)',
        'redox': 'CRC Handbook',
        'role': 'Co-precipitation agent / reducing agent in cathode synthesis',
    },
)


# =============================================================================
# GAS MOLECULES (6 molecules)
# =============================================================================

GAS_MOLECULES: Dict[str, Molecule] = {}

# Oxygen
GAS_MOLECULES['O2'] = Molecule(
    name='O2',
    formula='O2',
    pubchem_cid=977,
    cas_number='7782-44-7',
    smiles='O=O',
    molecular_weight=31.998,
    functional_groups=['diatomic_gas'],
    boiling_point_C=-183.0,
    melting_point_C=-218.8,
    vapor_pressure_mmHg_25C=None,  # Gas at STP
    density_g_cm3=0.001429,        # Gas at STP
    logP=0.65,
    solubility_mg_L=40.0,          # ~40 mg/L in water at 25 C
    ionization_energy_eV=12.07,    # NIST
    electron_affinity_eV=0.45,     # NIST
    dipole_moment_debye=0.0,       # Non-polar
    polarizability_A3=1.58,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=True,
    redox_potential_V=1.23,        # O2/H2O standard reduction potential
    pKa=None,
    flash_point_C=None,            # Oxidizer, not flammable itself
    molecule_class=MoleculeClass.GAS,
    hazard_class='oxidizer; supports combustion',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'EA': 'NIST WebBook',
        'redox': 'CRC Handbook: O2 + 4H+ + 4e- -> 2H2O = +1.23 V',
        'solubility': 'CRC Handbook',
    },
)

# Nitrogen
GAS_MOLECULES['N2'] = Molecule(
    name='N2',
    formula='N2',
    pubchem_cid=947,
    cas_number='7727-37-9',
    smiles='N#N',
    molecular_weight=28.014,
    functional_groups=['diatomic_gas'],
    boiling_point_C=-195.8,
    melting_point_C=-210.0,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=0.001251,
    logP=0.67,
    solubility_mg_L=19.0,          # ~19 mg/L in water at 25 C
    ionization_energy_eV=15.58,    # NIST -- highest of common diatomics
    electron_affinity_eV=-1.90,    # Does not bind electrons
    dipole_moment_debye=0.0,
    polarizability_A3=1.74,
    hbond_donors=0,
    hbond_acceptors=0,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.GAS,
    hazard_class='asphyxiant (simple)',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'solubility': 'CRC Handbook',
    },
)

# Argon
GAS_MOLECULES['Ar'] = Molecule(
    name='Ar',
    formula='Ar',
    pubchem_cid=23968,
    cas_number='7440-37-1',
    smiles='[Ar]',
    molecular_weight=39.948,
    functional_groups=['noble_gas'],
    boiling_point_C=-185.8,
    melting_point_C=-189.4,
    vapor_pressure_mmHg_25C=None,
    density_g_cm3=0.001784,
    logP=None,
    solubility_mg_L=52.0,          # ~52 mg/L at 25 C
    ionization_energy_eV=15.76,    # NIST
    electron_affinity_eV=-1.00,    # Does not form stable anion
    dipole_moment_debye=0.0,
    polarizability_A3=1.64,
    hbond_donors=0,
    hbond_acceptors=0,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=None,
    flash_point_C=None,
    molecule_class=MoleculeClass.GAS,
    hazard_class='asphyxiant (simple)',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'solubility': 'CRC Handbook',
        'role': 'Inert atmosphere for moisture-sensitive synthesis (glovebox)',
    },
)

# Carbon Dioxide
GAS_MOLECULES['CO2'] = Molecule(
    name='CO2',
    formula='CO2',
    pubchem_cid=280,
    cas_number='124-38-9',
    smiles='O=C=O',
    molecular_weight=44.009,
    functional_groups=['linear_triatomic'],
    boiling_point_C=-78.5,         # Sublimes at 1 atm
    melting_point_C=-56.6,         # At 5.18 atm
    vapor_pressure_mmHg_25C=None,  # Gas at STP (~49,000 mmHg at 25 C)
    density_g_cm3=0.001977,        # Gas at STP
    logP=0.83,
    solubility_mg_L=1450.0,        # ~1.45 g/L at 25 C
    ionization_energy_eV=13.78,    # NIST
    electron_affinity_eV=-0.60,
    dipole_moment_debye=0.0,       # Linear, symmetric
    polarizability_A3=2.91,
    hbond_donors=0,
    hbond_acceptors=2,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=-0.11,       # CO2/CO = -0.11 V vs SHE
    pKa=6.35,                     # CO2 + H2O -> H2CO3, pKa1
    flash_point_C=None,
    molecule_class=MoleculeClass.GAS,
    hazard_class='asphyxiant; compressed gas',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'solubility': 'CRC Handbook',
        'pKa': 'CRC Handbook (apparent pKa for CO2(aq))',
    },
)

# Water
GAS_MOLECULES['H2O'] = Molecule(
    name='H2O',
    formula='H2O',
    pubchem_cid=962,
    cas_number='7732-18-5',
    smiles='O',
    molecular_weight=18.015,
    functional_groups=['hydroxyl'],
    boiling_point_C=100.0,
    melting_point_C=0.0,
    vapor_pressure_mmHg_25C=23.8,  # CRC Handbook
    density_g_cm3=0.997,
    logP=-1.38,
    solubility_mg_L=None,          # Is the solvent
    ionization_energy_eV=12.62,    # NIST
    electron_affinity_eV=-1.00,    # Does not form stable anion
    dipole_moment_debye=1.85,      # Textbook value
    polarizability_A3=1.45,
    hbond_donors=2,
    hbond_acceptors=1,
    is_reducing=False,
    is_oxidizing=False,
    redox_potential_V=None,
    pKa=15.74,                    # Autoprotolysis Kw
    flash_point_C=None,
    molecule_class=MoleculeClass.GAS,
    hazard_class='non-hazardous',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'dipole': 'Textbook standard (Atkins Physical Chemistry)',
        'vapor_pressure': 'CRC Handbook',
        'role': 'Contaminant in battery electrolytes (reacts with LiPF6 -> HF)',
    },
)

# Hydrogen
GAS_MOLECULES['H2'] = Molecule(
    name='H2',
    formula='H2',
    pubchem_cid=783,
    cas_number='1333-74-0',
    smiles='[HH]',
    molecular_weight=2.016,
    functional_groups=['diatomic_gas'],
    boiling_point_C=-252.9,
    melting_point_C=-259.2,
    vapor_pressure_mmHg_25C=None,  # Gas at STP
    density_g_cm3=0.0000899,       # Gas at STP
    logP=None,
    solubility_mg_L=1.6,           # ~1.6 mg/L at 25 C
    ionization_energy_eV=15.43,    # NIST
    electron_affinity_eV=0.75,     # H- (hydride)
    dipole_moment_debye=0.0,
    polarizability_A3=0.79,
    hbond_donors=0,
    hbond_acceptors=0,
    is_reducing=True,
    is_oxidizing=False,
    redox_potential_V=0.0,         # Standard hydrogen electrode by definition
    pKa=None,
    flash_point_C=None,            # Autoignition ~500 C
    molecule_class=MoleculeClass.GAS,
    hazard_class='extremely flammable gas',
    sources={
        'bp_mp': 'CRC Handbook',
        'IE': 'NIST WebBook',
        'EA': 'NIST WebBook',
        'redox': 'Standard hydrogen electrode: 0.00 V by definition',
        'solubility': 'CRC Handbook',
        'role': 'Reducing atmosphere in calcination / sintering',
    },
)


# =============================================================================
# CONVENIENCE LOOKUPS
# =============================================================================

ALL_MOLECULES: Dict[str, Molecule] = {}
ALL_MOLECULES.update(ELECTROLYTE_SOLVENTS)
ALL_MOLECULES.update(SALT_ANIONS)
ALL_MOLECULES.update(POLYMER_MONOMERS)
ALL_MOLECULES.update(REAGENTS)
ALL_MOLECULES.update(COATINGS)
ALL_MOLECULES.update(GAS_MOLECULES)


def get_molecule(name: str) -> Optional[Molecule]:
    """Look up a molecule by name.

    Args:
        name: Molecule name (key in ALL_MOLECULES).

    Returns:
        Molecule instance or None if not found.
    """
    return ALL_MOLECULES.get(name)


def get_molecules_by_class(cls: MoleculeClass) -> Dict[str, Molecule]:
    """Get all molecules belonging to a given class.

    Args:
        cls: MoleculeClass enum value.

    Returns:
        Dict mapping name -> Molecule for all molecules of that class.
    """
    return {k: v for k, v in ALL_MOLECULES.items()
            if v.molecule_class == cls}


def list_molecule_names() -> List[str]:
    """Return a sorted list of all molecule names."""
    return sorted(ALL_MOLECULES.keys())


# =============================================================================
# MAIN (summary display)
# =============================================================================

if __name__ == "__main__":
    print("=" * 72)
    print("Molecular-Level Property Database -- Summary")
    print("=" * 72)
    print()

    categories = [
        ("Electrolyte Solvents", ELECTROLYTE_SOLVENTS),
        ("Salt Anions", SALT_ANIONS),
        ("Polymer Monomers", POLYMER_MONOMERS),
        ("Reagents", REAGENTS),
        ("Coatings / Additives", COATINGS),
        ("Gas Molecules", GAS_MOLECULES),
    ]

    for label, cat_dict in categories:
        print(f"{label}: {len(cat_dict)}")
        for name, mol in cat_dict.items():
            mw_str = f"MW={mol.molecular_weight:.2f}"
            cid_str = f"CID={mol.pubchem_cid}" if mol.pubchem_cid else "CID=?"
            cas_str = f"CAS {mol.cas_number}"
            print(f"  {name:25s} {mol.formula:18s} {mw_str:12s} {cid_str:16s} {cas_str}")
        print()

    print(f"Total molecules: {len(ALL_MOLECULES)}")
    print()

    # Quick sanity checks
    assert len(ELECTROLYTE_SOLVENTS) == 7, f"Expected 7 solvents, got {len(ELECTROLYTE_SOLVENTS)}"
    assert len(SALT_ANIONS) == 4, f"Expected 4 salts, got {len(SALT_ANIONS)}"
    assert len(POLYMER_MONOMERS) == 5, f"Expected 5 monomers, got {len(POLYMER_MONOMERS)}"
    assert len(REAGENTS) == 10, f"Expected 10 reagents, got {len(REAGENTS)}"
    assert len(COATINGS) == 5, f"Expected 5 coatings, got {len(COATINGS)}"
    assert len(GAS_MOLECULES) == 6, f"Expected 6 gases, got {len(GAS_MOLECULES)}"
    assert len(ALL_MOLECULES) == 37, f"Expected 37 total, got {len(ALL_MOLECULES)}"
    print("All sanity checks passed.")
