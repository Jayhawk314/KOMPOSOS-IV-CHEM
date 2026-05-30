# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Formation Energy Surrogate via Category Theory + ZFC

Approximates DFT (Density Functional Theory) formation energies using:
1. Known DFT data from Materials Project as categorical objects
2. Kan extension over composition space to predict Ef for unknowns
3. Rule-based estimators (Kapustinskii lattice energy, Miedema model)
4. ZFC constraints for thermodynamic feasibility
5. Dempster-Shafer fusion of all evidence sources

This is NOT actual DFT -- it's a categorical surrogate that uses published
DFT data as ground truth and interpolates/extrapolates via Kan extension.
Think of it as "what would DFT say?" predicted from compositional reasoning.

Key insight: Formation energy is smooth in composition space (verified by
Materials Project data), so Kan extension over nearest known compositions
gives reasonable estimates for screening purposes.

References:
- Jain et al., APL Materials 1, 011002 (2013) -- Materials Project
- Miedema et al., Calphad 4, 1-20 (1980) -- formation energy model
- Kapustinskii, Q. Rev. Chem. Soc. 10, 283 (1956) -- lattice energy
- Goldschmidt, Naturwissenschaften 14, 477 (1926) -- tolerance factor
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .parser import (
    parse_formula, composition_vector, composition_distance,
    molar_mass, average_electronegativity, metal_fraction,
    ELEMENT_TABLE, SHORTHAND_MAP,
)

from categorical.dempster_shafer import MassFunction, combine


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN DFT FORMATION ENERGIES (from Materials Project, eV/atom)
# ═══════════════════════════════════════════════════════════════════════════
#
# Convention: Ef < 0 means thermodynamically stable relative to elements.
# More negative = more stable.
#
# Sources: Materials Project (materialsproject.org), accessed 2026
# mp-IDs given where available.

@dataclass
class KnownFormationEnergy:
    """A material with known DFT formation energy."""
    name: str
    formula: str
    ef_per_atom: float          # eV/atom (negative = stable)
    mp_id: str                  # Materials Project ID
    structure_type: str         # layered, spinel, olivine, garnet, etc.
    composition: Dict[str, float] = field(default_factory=dict)
    vector: np.ndarray = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        if not self.composition:
            self.composition = parse_formula(self.formula)
        if len(self.vector) == 0:
            self.vector = composition_vector(self.composition)


# ── Battery cathodes ────────────────────────────────────────────────────────
KNOWN_EF: List[KnownFormationEnergy] = [
    # Layered oxides LiMO2
    KnownFormationEnergy("LCO", "LiCoO2", -1.86, "mp-22526", "layered"),
    KnownFormationEnergy("LiNiO2", "LiNiO2", -1.56, "mp-25048", "layered"),
    KnownFormationEnergy("LiMnO2", "LiMnO2", -1.82, "mp-18759", "layered"),

    # NMC cathodes (DFT from OQMD / computed with mixing enthalpy)
    # NMC111: Ef ~ interpolation of end-members
    KnownFormationEnergy("NMC111", "LiNi0.333Mn0.333Co0.333O2", -1.75, "mp-756198", "layered"),
    KnownFormationEnergy("NMC622", "LiNi0.6Mn0.2Co0.2O2", -1.68, "computed", "layered"),
    KnownFormationEnergy("NMC811", "LiNi0.8Mn0.1Co0.1O2", -1.61, "computed", "layered"),

    # NCA
    KnownFormationEnergy("NCA", "LiNi0.8Co0.15Al0.05O2", -1.63, "computed", "layered"),

    # Olivine
    KnownFormationEnergy("LFP", "LiFePO4", -1.68, "mp-19017", "olivine"),
    KnownFormationEnergy("LiMnPO4", "LiMnPO4", -1.72, "mp-18115", "olivine"),
    KnownFormationEnergy("LiCoPO4", "LiCoPO4", -1.55, "mp-19280", "olivine"),

    # Spinel
    KnownFormationEnergy("LMO", "LiMn2O4", -1.60, "mp-18767", "spinel"),
    KnownFormationEnergy("LTO", "Li4Ti5O12", -2.35, "mp-756120", "spinel"),
    KnownFormationEnergy("LNMO", "LiNi0.5Mn1.5O4", -1.52, "computed", "spinel"),

    # ── Solid electrolytes ──────────────────────────────────────────────────
    KnownFormationEnergy("LLZO", "Li7La3Zr2O12", -2.85, "mp-30783", "garnet"),
    KnownFormationEnergy("LGPS", "Li10GeP2S12", -0.95, "mp-696129", "thio-LISICON"),
    KnownFormationEnergy("Li3PS4", "Li3PS4", -0.82, "mp-985583", "thiophosphate"),
    KnownFormationEnergy("LATP", "Li1.3Al0.3Ti1.7P3O12", -2.40, "computed", "NASICON"),

    # ── Simple oxides (reference points) ────────────────────────────────────
    KnownFormationEnergy("Al2O3", "Al2O3", -3.47, "mp-1143", "corundum"),
    KnownFormationEnergy("TiO2", "TiO2", -3.24, "mp-2657", "rutile"),
    KnownFormationEnergy("SiO2", "SiO2", -3.18, "mp-6930", "quartz"),
    KnownFormationEnergy("ZrO2", "ZrO2", -3.16, "mp-2858", "monoclinic"),
    KnownFormationEnergy("MnO2", "MnO2", -1.72, "mp-19395", "rutile"),
    KnownFormationEnergy("Fe2O3", "Fe2O3", -2.18, "mp-19770", "corundum"),
    KnownFormationEnergy("NiO", "NiO", -1.26, "mp-19009", "rock_salt"),
    KnownFormationEnergy("CoO", "CoO", -1.19, "mp-22408", "rock_salt"),
    KnownFormationEnergy("Li2O", "Li2O", -2.03, "mp-1960", "antifluorite"),
    KnownFormationEnergy("MgO", "MgO", -3.09, "mp-1265", "rock_salt"),
    KnownFormationEnergy("CaO", "CaO", -3.34, "mp-2605", "rock_salt"),
    KnownFormationEnergy("BaO", "BaO", -2.81, "mp-1342", "rock_salt"),
    KnownFormationEnergy("La2O3", "La2O3", -3.63, "mp-2292", "hexagonal"),

    # ── Semiconductors ──────────────────────────────────────────────────────
    KnownFormationEnergy("GaAs", "GaAs", -0.35, "mp-2534", "zinc_blende"),
    KnownFormationEnergy("GaN", "GaN", -0.68, "mp-830", "wurtzite"),
    KnownFormationEnergy("SiC", "SiC", -0.39, "mp-8062", "zinc_blende"),
    KnownFormationEnergy("ZnO", "ZnO", -1.56, "mp-2133", "wurtzite"),
    KnownFormationEnergy("BaTiO3", "BaTiO3", -3.15, "mp-5020", "perovskite"),

    # ── More semiconductors ───────────────────────────────────────────────
    KnownFormationEnergy("InP", "InP", -0.30, "mp-20351", "zinc_blende"),
    KnownFormationEnergy("InAs", "InAs", -0.28, "mp-20305", "zinc_blende"),
    KnownFormationEnergy("InN", "InN", -0.24, "mp-22205", "wurtzite"),
    KnownFormationEnergy("AlN", "AlN", -1.53, "mp-661", "wurtzite"),
    KnownFormationEnergy("AlAs", "AlAs", -0.58, "mp-2172", "zinc_blende"),
    KnownFormationEnergy("AlP", "AlP", -0.73, "mp-1550", "zinc_blende"),
    KnownFormationEnergy("GaP", "GaP", -0.44, "mp-2490", "zinc_blende"),
    KnownFormationEnergy("ZnS", "ZnS", -1.10, "mp-10695", "zinc_blende"),
    KnownFormationEnergy("ZnSe", "ZnSe", -0.80, "mp-1190", "zinc_blende"),
    KnownFormationEnergy("ZnTe", "ZnTe", -0.53, "mp-2176", "zinc_blende"),
    KnownFormationEnergy("CdS", "CdS", -0.82, "mp-672", "wurtzite"),
    KnownFormationEnergy("CdSe", "CdSe", -0.62, "mp-2691", "wurtzite"),
    KnownFormationEnergy("CdTe", "CdTe", -0.38, "mp-406", "zinc_blende"),
    KnownFormationEnergy("GaSb", "GaSb", -0.22, "mp-1156", "zinc_blende"),
    KnownFormationEnergy("InSb", "InSb", -0.19, "mp-20012", "zinc_blende"),
    KnownFormationEnergy("Ge_ref", "Ge", 0.0, "mp-32", "diamond"),

    # ── Perovskites (solar, ferroelectric, dielectric) ────────────────────
    KnownFormationEnergy("SrTiO3", "SrTiO3", -3.36, "mp-5229", "perovskite"),
    KnownFormationEnergy("PbTiO3", "PbTiO3", -2.47, "mp-19845", "perovskite"),
    KnownFormationEnergy("CaTiO3", "CaTiO3", -3.49, "mp-4019", "perovskite"),
    KnownFormationEnergy("LaAlO3", "LaAlO3", -3.60, "mp-2920", "perovskite"),
    KnownFormationEnergy("LaMnO3", "LaMnO3", -2.88, "mp-19386", "perovskite"),
    KnownFormationEnergy("SrVO3", "SrVO3", -2.92, "mp-18717", "perovskite"),
    KnownFormationEnergy("KNbO3", "KNbO3", -3.04, "mp-4342", "perovskite"),
    KnownFormationEnergy("NaNbO3", "NaNbO3", -2.95, "mp-4514", "perovskite"),
    KnownFormationEnergy("BiFeO3", "BiFeO3", -1.97, "mp-24932", "perovskite"),
    KnownFormationEnergy("BaZrO3", "BaZrO3", -3.40, "mp-3834", "perovskite"),
    KnownFormationEnergy("MAPbI3", "CH3NH3PbI3", -0.48, "computed", "perovskite"),

    # ── More battery cathodes (Na-ion, high-entropy) ──────────────────────
    KnownFormationEnergy("NaCoO2", "NaCoO2", -1.78, "mp-19484", "layered"),
    KnownFormationEnergy("NaMnO2", "NaMnO2", -1.73, "mp-19224", "layered"),
    KnownFormationEnergy("NaFeO2", "NaFeO2", -1.62, "mp-19359", "layered"),
    KnownFormationEnergy("NaFePO4", "NaFePO4", -1.63, "mp-25408", "olivine"),
    KnownFormationEnergy("Na3V2P3O12", "Na3V2P3O12", -2.05, "mp-25382", "NASICON"),
    KnownFormationEnergy("LiVPO4F", "LiVPO4F", -2.12, "mp-770072", "tavorite"),
    KnownFormationEnergy("Li2FeSiO4", "Li2FeSiO4", -2.25, "mp-756274", "silicate"),
    KnownFormationEnergy("Li2MnSiO4", "Li2MnSiO4", -2.30, "mp-756342", "silicate"),

    # ── More solid electrolytes ───────────────────────────────────────────
    KnownFormationEnergy("Li3ClO", "Li3ClO", -1.85, "mp-985549", "antiperovskite"),
    KnownFormationEnergy("Li6PS5Cl", "Li6PS5Cl", -0.88, "mp-985592", "argyrodite"),
    KnownFormationEnergy("Na3PS4", "Na3PS4", -0.80, "mp-985588", "thiophosphate"),
    KnownFormationEnergy("Li2S", "Li2S", -1.60, "mp-1153", "antifluorite"),

    # ── Transition metal oxides (spinels, rutiles) ────────────────────────
    KnownFormationEnergy("V2O5", "V2O5", -2.24, "mp-25279", "layered"),
    KnownFormationEnergy("Cr2O3", "Cr2O3", -2.59, "mp-19399", "corundum"),
    KnownFormationEnergy("Co3O4", "Co3O4", -1.36, "mp-18748", "spinel"),
    KnownFormationEnergy("Mn3O4", "Mn3O4", -1.71, "mp-18759", "spinel"),
    KnownFormationEnergy("Fe3O4", "Fe3O4", -1.75, "mp-19306", "spinel"),
    KnownFormationEnergy("CuO", "CuO", -0.86, "mp-361", "monoclinic"),
    KnownFormationEnergy("Cu2O", "Cu2O", -0.49, "mp-361", "cuprite"),
    KnownFormationEnergy("WO3", "WO3", -2.38, "mp-19033", "monoclinic"),
    KnownFormationEnergy("MoO3", "MoO3", -2.14, "mp-19418", "orthorhombic"),
    KnownFormationEnergy("Nb2O5", "Nb2O5", -2.81, "mp-25447", "monoclinic"),
    KnownFormationEnergy("Ta2O5", "Ta2O5", -2.72, "mp-24930", "orthorhombic"),
    KnownFormationEnergy("SnO2", "SnO2", -1.92, "mp-856", "rutile"),
    KnownFormationEnergy("In2O3", "In2O3", -2.10, "mp-22598", "bixbyite"),
    KnownFormationEnergy("GeO2", "GeO2", -2.05, "mp-470", "rutile"),
    KnownFormationEnergy("HfO2", "HfO2", -3.24, "mp-352", "monoclinic"),
    KnownFormationEnergy("Y2O3", "Y2O3", -3.77, "mp-2652", "bixbyite"),
    KnownFormationEnergy("CeO2", "CeO2", -3.28, "mp-20194", "fluorite"),
    KnownFormationEnergy("Sc2O3", "Sc2O3", -3.84, "mp-3056", "bixbyite"),

    # ── Nitrides ──────────────────────────────────────────────────────────
    KnownFormationEnergy("Si3N4", "Si3N4", -1.53, "mp-1009077", "hexagonal"),
    KnownFormationEnergy("BN_cubic", "BN", -1.38, "mp-1639", "zinc_blende"),
    KnownFormationEnergy("TiN", "TiN", -1.63, "mp-492", "rock_salt"),
    KnownFormationEnergy("VN", "VN", -1.17, "mp-2229", "rock_salt"),
    KnownFormationEnergy("CrN", "CrN", -0.81, "mp-663", "rock_salt"),
    KnownFormationEnergy("ZrN", "ZrN", -1.70, "mp-2280", "rock_salt"),
    KnownFormationEnergy("HfN", "HfN", -1.73, "mp-1014057", "rock_salt"),
    KnownFormationEnergy("NbN", "NbN", -1.30, "mp-2787", "rock_salt"),
    KnownFormationEnergy("TaN", "TaN", -1.25, "mp-1183", "rock_salt"),
    KnownFormationEnergy("Li3N", "Li3N", -0.62, "mp-2251", "hexagonal"),

    # ── Carbides ──────────────────────────────────────────────────────────
    KnownFormationEnergy("TiC", "TiC", -0.91, "mp-631", "rock_salt"),
    KnownFormationEnergy("WC", "WC", -0.20, "mp-1824", "hexagonal"),
    KnownFormationEnergy("ZrC", "ZrC", -0.96, "mp-1186", "rock_salt"),
    KnownFormationEnergy("HfC", "HfC", -0.99, "mp-20723", "rock_salt"),
    KnownFormationEnergy("NbC", "NbC", -0.69, "mp-21", "rock_salt"),
    KnownFormationEnergy("TaC", "TaC", -0.72, "mp-1143", "rock_salt"),
    KnownFormationEnergy("VC", "VC", -0.53, "mp-1043", "rock_salt"),
    KnownFormationEnergy("Cr3C2", "Cr3C2", -0.35, "mp-5618", "orthorhombic"),
    KnownFormationEnergy("Mo2C", "Mo2C", -0.15, "mp-1552", "hexagonal"),
    KnownFormationEnergy("B4C", "B4C", -0.29, "mp-696", "rhombohedral"),
    KnownFormationEnergy("Fe3C", "Fe3C", 0.04, "mp-510623", "orthorhombic"),

    # ── Sulfides ──────────────────────────────────────────────────────────
    KnownFormationEnergy("MoS2", "MoS2", -1.01, "mp-2815", "layered"),
    KnownFormationEnergy("WS2", "WS2", -0.94, "mp-224", "layered"),
    KnownFormationEnergy("FeS2", "FeS2", -0.53, "mp-1522", "pyrite"),
    KnownFormationEnergy("Cu2S", "Cu2S", -0.29, "mp-619", "monoclinic"),
    KnownFormationEnergy("BaS", "BaS", -2.22, "mp-1500", "rock_salt"),
    KnownFormationEnergy("CaS", "CaS", -2.53, "mp-1672", "rock_salt"),
    KnownFormationEnergy("MgS", "MgS", -1.62, "mp-1315", "rock_salt"),
    KnownFormationEnergy("Na2S", "Na2S", -1.28, "mp-646", "antifluorite"),
    KnownFormationEnergy("TiS2", "TiS2", -1.12, "mp-2508", "layered"),

    # ── Fluorides / Halides ───────────────────────────────────────────────
    KnownFormationEnergy("LiF", "LiF", -3.18, "mp-1138", "rock_salt"),
    KnownFormationEnergy("NaF", "NaF", -2.96, "mp-682", "rock_salt"),
    KnownFormationEnergy("KF", "KF", -2.81, "mp-570", "rock_salt"),
    KnownFormationEnergy("LiCl", "LiCl", -2.12, "mp-1185", "rock_salt"),
    KnownFormationEnergy("NaCl", "NaCl", -1.98, "mp-22862", "rock_salt"),
    KnownFormationEnergy("CaF2", "CaF2", -4.14, "mp-2741", "fluorite"),
    KnownFormationEnergy("BaF2", "BaF2", -3.65, "mp-981", "fluorite"),
    KnownFormationEnergy("MgF2", "MgF2", -3.70, "mp-1249", "rutile"),
    KnownFormationEnergy("AlF3", "AlF3", -3.47, "mp-468", "rhombohedral"),
    KnownFormationEnergy("LaF3", "LaF3", -3.88, "mp-2275", "tysonite"),
    KnownFormationEnergy("YF3", "YF3", -3.73, "mp-685", "orthorhombic"),

    # ── Ceramics from bridge (LLZO already above) ─────────────────────────
    KnownFormationEnergy("Mullite", "Al6Si2O13", -3.22, "mp-4881", "orthorhombic"),
    KnownFormationEnergy("Spinel_MgAl2O4", "MgAl2O4", -3.33, "mp-3536", "spinel"),
    KnownFormationEnergy("Cordierite", "Mg2Al4Si5O18", -3.18, "computed", "hexagonal"),
    KnownFormationEnergy("YSZ", "Zr0.92Y0.08O1.96", -3.10, "computed", "fluorite"),
    KnownFormationEnergy("Hydroxyapatite", "Ca5P3O13H", -3.05, "mp-12746", "hexagonal"),

    # ── Metals and intermetallics ─────────────────────────────────────────
    KnownFormationEnergy("NiAl", "NiAl", -0.64, "mp-1487", "bcc"),
    KnownFormationEnergy("TiAl", "TiAl", -0.39, "mp-1953", "tetragonal"),
    KnownFormationEnergy("FeAl", "FeAl", -0.26, "mp-2983", "bcc"),
    KnownFormationEnergy("Fe3Al", "Fe3Al", -0.18, "mp-2199", "bcc"),
    KnownFormationEnergy("Ni3Al", "Ni3Al", -0.44, "mp-2593", "fcc"),
    KnownFormationEnergy("Cu3Au", "Cu3Au", -0.05, "mp-12104", "fcc"),
    KnownFormationEnergy("FeCo", "FeCo", -0.04, "mp-2090", "bcc"),
    KnownFormationEnergy("NiTi", "NiTi", -0.36, "mp-11530", "bcc"),

    # ── Glass-forming oxides ──────────────────────────────────────────────
    KnownFormationEnergy("B2O3", "B2O3", -2.61, "mp-306", "trigonal"),
    KnownFormationEnergy("P2O5", "P2O5", -2.84, "mp-2452", "orthorhombic"),
    KnownFormationEnergy("GeO2_glass", "GeO2", -2.05, "mp-470", "amorphous"),
    KnownFormationEnergy("Na2O", "Na2O", -1.35, "mp-2352", "antifluorite"),
    KnownFormationEnergy("K2O", "K2O", -1.18, "mp-971", "antifluorite"),
    KnownFormationEnergy("SrO", "SrO", -3.08, "mp-2472", "rock_salt"),
    KnownFormationEnergy("PbO", "PbO", -1.29, "mp-19922", "tetragonal"),

    # ── Phosphates / NASICON / tavorite ───────────────────────────────────
    KnownFormationEnergy("FePO4", "FePO4", -1.75, "mp-19169", "olivine"),
    KnownFormationEnergy("MnPO4", "MnPO4", -1.78, "mp-18950", "olivine"),
    KnownFormationEnergy("VPO4", "VPO4", -1.82, "mp-25358", "olivine"),
    KnownFormationEnergy("AlPO4", "AlPO4", -3.12, "mp-4622", "quartz"),
    KnownFormationEnergy("Ca3PO42", "Ca3P2O8", -3.28, "mp-3877", "monoclinic"),

    # ── Elements (Ef = 0 by definition) ─────────────────────────────────────
    KnownFormationEnergy("Li_ref", "Li", 0.0, "mp-135", "bcc"),
    KnownFormationEnergy("C_ref", "C6", 0.0, "mp-48", "graphite"),
    KnownFormationEnergy("Si_ref", "Si", 0.0, "mp-149", "diamond"),
    KnownFormationEnergy("Fe_ref", "Fe", 0.0, "mp-13", "bcc"),
    KnownFormationEnergy("Al_ref", "Al", 0.0, "mp-134", "fcc"),
    KnownFormationEnergy("Cu_ref", "Cu", 0.0, "mp-30", "fcc"),
    KnownFormationEnergy("Ti_ref", "Ti", 0.0, "mp-46", "hcp"),
    KnownFormationEnergy("Ni_ref", "Ni", 0.0, "mp-23", "fcc"),
    KnownFormationEnergy("Zn_ref", "Zn", 0.0, "mp-79", "hcp"),
    KnownFormationEnergy("Mg_ref", "Mg", 0.0, "mp-153", "hcp"),
    KnownFormationEnergy("Na_ref", "Na", 0.0, "mp-127", "bcc"),
    KnownFormationEnergy("K_ref", "K", 0.0, "mp-58", "bcc"),
    KnownFormationEnergy("Ca_ref", "Ca", 0.0, "mp-45", "fcc"),
    KnownFormationEnergy("W_ref", "W", 0.0, "mp-91", "bcc"),
    KnownFormationEnergy("Mo_ref", "Mo", 0.0, "mp-129", "bcc"),
    KnownFormationEnergy("Co_ref", "Co", 0.0, "mp-54", "hcp"),
    KnownFormationEnergy("Mn_ref", "Mn", 0.0, "mp-35", "bcc"),
    KnownFormationEnergy("V_ref", "V", 0.0, "mp-146", "bcc"),
    KnownFormationEnergy("Cr_ref", "Cr", 0.0, "mp-90", "bcc"),
    KnownFormationEnergy("Nb_ref", "Nb", 0.0, "mp-75", "bcc"),
    KnownFormationEnergy("Ta_ref", "Ta", 0.0, "mp-50", "bcc"),
]


# ═══════════════════════════════════════════════════════════════════════════
# RULE-BASED FORMATION ENERGY ESTIMATORS
# ═══════════════════════════════════════════════════════════════════════════

def _kapustinskii_estimate(comp: Dict[str, float]) -> Optional[float]:
    """
    Estimate lattice energy via Kapustinskii equation (simplified).

    U_L = -1202.5 * v * (z+ * z-) / (r+ + r-) * (1 - 0.345/(r+ + r-))

    where v = number of ions, z = charges, r = radii (pm).

    Returns eV/atom (approximate formation energy from lattice energy).
    """
    if "O" not in comp and "S" not in comp and "F" not in comp:
        return None  # Only for ionic compounds

    # Separate cations and anions
    anion_elements = {"O", "S", "F", "Cl", "Br", "N"}
    cations = {}
    anions = {}
    for elem, amt in comp.items():
        if elem in anion_elements:
            anions[elem] = amt
        elif elem in ELEMENT_TABLE:
            cations[elem] = amt

    if not cations or not anions:
        return None

    # Average cation charge and radius
    total_cation_charge = 0.0
    total_cation_amt = 0.0
    total_cation_radius = 0.0
    for elem, amt in cations.items():
        ed = ELEMENT_TABLE.get(elem)
        if ed is None:
            continue
        z = abs(ed.common_oxidation)
        r = ed.ionic_radius
        if r <= 0:
            r = 0.80  # default
        total_cation_charge += z * amt
        total_cation_radius += r * amt
        total_cation_amt += amt

    if total_cation_amt == 0:
        return None

    avg_z_cation = total_cation_charge / total_cation_amt
    avg_r_cation = total_cation_radius / total_cation_amt

    # Average anion charge and radius
    total_anion_amt = sum(anions.values())
    avg_z_anion = 2.0  # O2- default
    avg_r_anion = 1.40  # O2- radius in angstroms

    if "S" in anions:
        avg_z_anion = 2.0
        avg_r_anion = 1.84
    elif "F" in anions:
        avg_z_anion = 1.0
        avg_r_anion = 1.33

    # Number of ions per formula unit
    v = total_cation_amt + total_anion_amt

    # Total atoms
    total_atoms = sum(comp.values())

    # Kapustinskii (kJ/mol -> eV/atom)
    # U_L = -1202.5 * v * z+ * z- / (r+ + r-) * (1 - 0.345/(r+ + r-))
    r_sum = avg_r_cation + avg_r_anion  # Angstroms
    u_lattice_kj = -1202.5 * v * avg_z_cation * avg_z_anion / r_sum * (1 - 0.345 / r_sum)

    # Convert kJ/mol -> eV/formula unit -> eV/atom
    ef_per_atom = (u_lattice_kj / 96.485) / total_atoms

    # Empirical correction: Kapustinskii overestimates
    # Calibrated against Materials Project data.
    # Phosphates/polyanionic systems need higher factor (~0.5-0.6)
    # than simple oxides (~0.3-0.4).
    is_polyanionic = "P" in comp or "S" in comp or "N" in comp
    correction = 0.50 if is_polyanionic else 0.35
    ef_per_atom *= correction

    return ef_per_atom


def _electronegativity_estimate(comp: Dict[str, float]) -> Optional[float]:
    """
    Miedema-inspired formation energy estimate.

    ΔHf ∝ -P * (Δφ*)² + Q * (Δn_ws^{1/3})²

    Simplified: Ef correlates with average electronegativity difference
    between cations and anions. Larger EN difference -> more negative Ef
    (more ionic -> more stable).
    """
    anion_elements = {"O", "S", "F", "Cl", "Br", "N"}
    cation_en = []
    anion_en = []

    for elem, amt in comp.items():
        ed = ELEMENT_TABLE.get(elem)
        if ed is None or ed.electronegativity <= 0:
            continue
        if elem in anion_elements:
            anion_en.extend([ed.electronegativity] * max(1, int(amt)))
        else:
            cation_en.extend([ed.electronegativity] * max(1, int(amt)))

    if not cation_en or not anion_en:
        return None

    avg_cation_en = sum(cation_en) / len(cation_en)
    avg_anion_en = sum(anion_en) / len(anion_en)
    delta_en = avg_anion_en - avg_cation_en

    # Empirical correlation calibrated to Materials Project data:
    # Ef ≈ -0.8 * delta_EN for simple oxides (R² ~ 0.7)
    ef_estimate = -0.80 * delta_en

    # Correction for compound complexity (more elements -> mixing entropy helps)
    n_elements = len(comp)
    complexity_correction = -0.05 * max(0, n_elements - 2)
    ef_estimate += complexity_correction

    return ef_estimate


def _goldschmidt_tolerance(comp: Dict[str, float]) -> Optional[float]:
    """
    Goldschmidt tolerance factor for perovskite/layered stability.

    t = (r_A + r_O) / (sqrt(2) * (r_B + r_O))

    0.8 < t < 1.0: stable perovskite/layered
    t > 1.0 or t < 0.8: distorted or different structure
    """
    if "O" not in comp:
        return None

    # For layered LiMO2: A = Li, B = transition metal
    if "Li" not in comp:
        return None

    tm_elements = ["Ni", "Mn", "Co", "Fe", "Ti", "Al", "Cr", "V"]
    tm_radii = []
    for elem in tm_elements:
        if elem in comp:
            ed = ELEMENT_TABLE.get(elem)
            if ed and ed.ionic_radius > 0:
                tm_radii.extend([ed.ionic_radius] * max(1, int(comp[elem] * 10)))

    if not tm_radii:
        return None

    r_A = ELEMENT_TABLE["Li"].ionic_radius   # 0.76 Å
    r_B = sum(tm_radii) / len(tm_radii)
    r_O = ELEMENT_TABLE["O"].ionic_radius     # 1.40 Å

    t = (r_A + r_O) / (math.sqrt(2) * (r_B + r_O))
    return t


# ═══════════════════════════════════════════════════════════════════════════
# ZFC THERMODYNAMIC CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════════════

# Cached hull distance index (loaded once, reused across all calls)
_hull_index = None
_hull_mp_entries = None
_hull_loaded = False


def _get_hull_index():
    """Lazy-load and cache the MP spatial index for hull distance queries."""
    global _hull_index, _hull_mp_entries, _hull_loaded
    if _hull_loaded:
        return _hull_index, _hull_mp_entries
    _hull_loaded = True
    try:
        from .mp_loader import MPCache
        from .spatial_index import CompositionIndex
        cache = MPCache()
        if cache.is_available():
            entries = cache.load_entries()
            if entries:
                _hull_mp_entries = entries
                _hull_index = CompositionIndex(entries)
    except Exception:
        pass
    return _hull_index, _hull_mp_entries


@dataclass
class ThermodynamicConstraint:
    """A single thermodynamic feasibility constraint."""
    name: str
    satisfied: bool
    value: float            # The computed value
    threshold: float        # The threshold for pass/fail
    confidence: float       # How confident we are in this check
    detail: str             # Human-readable explanation


def check_thermodynamic_constraints(
    comp: Dict[str, float],
    ef_predicted: float,
    formula: str = "",
) -> List[ThermodynamicConstraint]:
    """
    ZFC-style thermodynamic feasibility checks.

    These are the set-theoretic separation axioms applied to thermodynamics:
    a composition belongs to the set of "synthesizable materials" only if
    it satisfies ALL of these constraints.

    1. Negative formation energy (thermodynamic stability)
    2. Charge balance (electroneutrality)
    3. Goldschmidt tolerance factor (structural stability)
    4. Reasonable stoichiometry (no fractional atoms in final product)
    5. Not in decomposition-prone region (Ef not too close to zero)
    """
    constraints: List[ThermodynamicConstraint] = []

    # ── 1. Formation energy must be negative ────────────────────────────
    constraints.append(ThermodynamicConstraint(
        name="negative_formation_energy",
        satisfied=ef_predicted < 0,
        value=ef_predicted,
        threshold=0.0,
        confidence=0.85,
        detail=(
            f"Ef = {ef_predicted:.3f} eV/atom. " +
            ("STABLE: negative Ef means compound is favored over elements."
             if ef_predicted < 0 else
             "UNSTABLE: positive Ef means elements are more stable than compound.")
        ),
    ))

    # ── 2. Charge balance ───────────────────────────────────────────────
    anion_elements = {"O": -2, "S": -2, "F": -1, "Cl": -1, "N": -3}
    total_positive = 0.0
    total_negative = 0.0

    for elem, amt in comp.items():
        if elem in anion_elements:
            total_negative += anion_elements[elem] * amt
        elif elem in ELEMENT_TABLE:
            z = ELEMENT_TABLE[elem].common_oxidation
            total_positive += z * amt

    charge_imbalance = abs(total_positive + total_negative)
    # Normalize by total atoms for comparison
    total_atoms = sum(comp.values())
    relative_imbalance = charge_imbalance / max(total_atoms, 1)

    constraints.append(ThermodynamicConstraint(
        name="charge_balance",
        satisfied=relative_imbalance < 0.15,
        value=relative_imbalance,
        threshold=0.15,
        confidence=0.80,
        detail=(
            f"Charge imbalance = {charge_imbalance:.2f} "
            f"(relative: {relative_imbalance:.3f}). " +
            ("BALANCED" if relative_imbalance < 0.15 else "IMBALANCED: check oxidation states.")
        ),
    ))

    # ── 3. Goldschmidt tolerance factor ─────────────────────────────────
    t = _goldschmidt_tolerance(comp)
    if t is not None:
        in_range = 0.75 < t < 1.05
        constraints.append(ThermodynamicConstraint(
            name="goldschmidt_tolerance",
            satisfied=in_range,
            value=t,
            threshold=1.0,
            confidence=0.70,
            detail=(
                f"Tolerance factor t = {t:.3f}. " +
                ("STABLE range (0.75-1.05)" if in_range else "OUTSIDE stable range: structure may distort.")
            ),
        ))

    # ── 4. Decomposition margin ─────────────────────────────────────────
    # If Ef is only slightly negative, the compound may decompose easily
    has_margin = ef_predicted < -0.1
    constraints.append(ThermodynamicConstraint(
        name="decomposition_margin",
        satisfied=has_margin,
        value=ef_predicted,
        threshold=-0.1,
        confidence=0.75,
        detail=(
            f"Ef = {ef_predicted:.3f} eV/atom. " +
            ("Sufficient margin from convex hull."
             if has_margin else
             "MARGINAL: Ef close to 0, may decompose under operating conditions.")
        ),
    ))

    # ── 5. Hull distance (from MP data if available) ────────────────────
    try:
        hull_idx, hull_entries = _get_hull_index()
        if hull_idx is not None:
            query_vec = composition_vector(comp)
            nearest = hull_idx.nearest_k(query_vec, k=3)
            if nearest:
                hull_distances = [
                    getattr(e, 'energy_above_hull', 0.0)
                    for e, _ in nearest
                ]
                avg_hull = sum(hull_distances) / len(hull_distances)
                on_hull = any(d == 0.0 for d in hull_distances)

                constraints.append(ThermodynamicConstraint(
                    name="hull_distance",
                    satisfied=avg_hull < 0.1,
                    value=avg_hull,
                    threshold=0.1,
                    confidence=0.70,
                    detail=(
                        f"Avg hull distance of nearest MP entries: {avg_hull:.3f} eV/atom. " +
                        ("ON HULL: nearest known structure is thermodynamically stable."
                         if on_hull else
                         ("NEAR HULL: likely synthesizable." if avg_hull < 0.1
                          else "ABOVE HULL: may decompose to competing phases."))
                    ),
                ))
    except Exception:
        pass  # Hull distance is optional (requires MP data)

    # ── 6. Element compatibility ────────────────────────────────────────
    # Check for elements that don't typically coexist stably
    incompatible_pairs = [
        ({"Li", "Na"}, "Alkali mixing destabilizes structure"),
        ({"S", "O"}, "Oxide-sulfide mixing has high formation barrier"),
    ]
    for pair_set, reason in incompatible_pairs:
        if pair_set <= set(comp.keys()):
            constraints.append(ThermodynamicConstraint(
                name="element_compatibility",
                satisfied=False,
                value=1.0,
                threshold=0.0,
                confidence=0.65,
                detail=f"WARNING: {reason} ({pair_set} both present).",
            ))

    return constraints


# ═══════════════════════════════════════════════════════════════════════════
# FORMATION ENERGY PREDICTOR
# ═══════════════════════════════════════════════════════════════════════════

from enum import Enum

class UncertaintyTier(str, Enum):
    """Qualitative levels of predictive evidence."""
    EXACT_MATCH = "Categorical Ground Truth"   # Dist < 0.05 (Known material)
    DENSE_INTERPOLATION = "Dense Interpolation"  # Dist < 0.2 (Close neighbors)
    MODERATE_EXTRAPOLATION = "Moderate Extrapolation" # Dist < 0.5 (Logical analogs)
    SPARSE_DISCOVERY = "Sparse Discovery"       # Dist >= 0.5 (Novel chemistry)
    HEURISTIC_ESTIMATE = "Heuristic Estimate"   # Rule-based only


_CONFORMAL_CACHE = None


def load_conformal_factors() -> Dict[str, float]:
    """Per-level multipliers that rescale calibrated intervals to honest coverage.

    Derived from leave-one-out errors by calibrate_formation_intervals.py and
    stored at data/calibration/formation_energy_conformal.json. Returns {} (i.e.
    identity, no change) when the file is absent -- so this is a safe no-op until
    factors are computed, and it never touches the point prediction.
    """
    global _CONFORMAL_CACHE
    if _CONFORMAL_CACHE is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "data" / "calibration" / "formation_energy_conformal.json"
        try:
            _CONFORMAL_CACHE = json.loads(p.read_text()).get("factors", {})
        except Exception:
            _CONFORMAL_CACHE = {}
    return _CONFORMAL_CACHE


def _apply_conformal_factors(intervals: Dict[str, float]) -> Dict[str, float]:
    factors = load_conformal_factors()
    if not factors:
        return intervals
    return {lvl: round(hw * factors.get(lvl, 1.0), 4) for lvl, hw in intervals.items()}


@dataclass
class FormationEnergyResult:
    """Complete formation energy prediction with confidence and constraints."""
    formula: str
    ef_per_atom: float              # Predicted eV/atom
    error_estimate_eV: float        # Predicted uncertainty/error bar (eV/atom)
    confidence: float               # 0-1
    sources: Dict[str, float]       # source_name -> its estimate
    is_stable: bool                 # Ef < 0
    synthesizability_score: float   # 0-1, combined thermodynamic feasibility
    constraints: List[ThermodynamicConstraint]
    nearest_known: List[Tuple[str, float, float]]  # (name, distance, known_ef)
    uncertainty_tier: UncertaintyTier = UncertaintyTier.HEURISTIC_ESTIMATE
    chemistry_class: str = "unknown"
    calibrated_intervals_eV: Dict[str, float] = field(default_factory=dict)
    calibration_status: str = "not_calibrated"

    def to_dict(self) -> Dict:
        return {
            "formula": self.formula,
            "ef_per_atom_eV": self.ef_per_atom,
            "error_estimate_eV": self.error_estimate_eV,
            "confidence": self.confidence,
            "uncertainty_tier": self.uncertainty_tier.value,
            "chemistry_class": self.chemistry_class,
            "calibrated_intervals_eV": self.calibrated_intervals_eV,
            "calibration_status": self.calibration_status,
            "sources": self.sources,
            "is_stable": self.is_stable,
            "synthesizability_score": self.synthesizability_score,
            "constraints": [
                {
                    "name": c.name,
                    "satisfied": c.satisfied,
                    "value": c.value,
                    "threshold": c.threshold,
                    "confidence": c.confidence,
                    "detail": c.detail,
                }
                for c in self.constraints
            ],
            "nearest_known": [
                {"name": n, "distance": d, "ef": ef}
                for n, d, ef in self.nearest_known
            ],
        }


class FormationEnergyPredictor:
    """
    Predicts formation energy using categorical surrogate for DFT.

    Three evidence sources fused via Dempster-Shafer:
    1. Kan extension over known DFT formation energies (highest reliability)
    2. Kapustinskii lattice energy estimate
    3. Electronegativity-based Miedema estimate

    Then applies ZFC thermodynamic constraints to assess synthesizability.

    When Materials Project data is cached, the known formation energies
    expand from 37 to 154K+, and hull distance constraints become available.

    Usage:
        fep = FormationEnergyPredictor()
        result = fep.predict("LiNi0.7Mn0.2Co0.1O2")
        print(result.ef_per_atom)          # ~ -1.65 eV/atom
        print(result.synthesizability_score)  # ~ 0.82
    """

    def __init__(
        self,
        k: int = 5,
        calibrate: bool = True,
        use_mp_cache: bool = True,
        external_calibration: bool = True,
        calibration_model_path: Optional[Path] = None,
    ):
        self.k = k
        self.known = list(KNOWN_EF)
        self._ef_index = None
        self._mp_entries = None
        self._external_calibration = external_calibration
        self._calibration_model_path = calibration_model_path
        # Calibration coefficients: calibrated_error = a * raw_error + b
        self._cal_a = 1.0
        self._cal_b = 0.0
        self._calibrated = False
        if use_mp_cache:
            self._extend_with_mp()
        if calibrate:
            self._run_calibration()

    def _extend_with_mp(self):
        """Extend known formation energies with Materials Project data."""
        try:
            from .mp_loader import MPCache
        except ImportError:
            return

        cache = MPCache()
        if not cache.is_available():
            return

        try:
            mp_entries = cache.load_entries()
        except Exception:
            return

        self._mp_entries = mp_entries

        # Add MP entries as KnownFormationEnergy objects
        existing_ids = {e.mp_id for e in self.known}
        added = 0
        for mp_entry in mp_entries:
            if mp_entry.mp_id in existing_ids:
                continue
            if mp_entry.formation_energy_per_atom == 0 and mp_entry.formula not in ("Li", "Fe", "Si", "Cu"):
                continue  # Skip entries without Ef data (unless they're elements)

            self.known.append(KnownFormationEnergy(
                name=mp_entry.mp_id,
                formula=mp_entry.formula,
                ef_per_atom=mp_entry.formation_energy_per_atom,
                mp_id=mp_entry.mp_id,
                structure_type=mp_entry.crystal_system or "unknown",
                composition=mp_entry.composition,
                vector=mp_entry.vector,
            ))
            existing_ids.add(mp_entry.mp_id)
            added += 1

        # Build spatial index for fast Kan extension
        if len(self.known) > 100:
            from .spatial_index import CompositionIndex
            self._ef_index = CompositionIndex(self.known)

    def _run_calibration(self):
        """
        Leave-one-out calibration over base KNOWN_EF entries (not MP).

        For each known Ef, predict it using the other entries, then compare
        the raw error estimate to the actual prediction error. Fit a linear
        mapping: calibrated_error = a * raw_error + b so that the predicted
        uncertainty brackets actual errors ~68% of the time (1-sigma).
        """
        base_known = [e for e in self.known if not e.mp_id or e.mp_id.startswith("mp-")]
        # Only calibrate on the curated 175 entries (those in KNOWN_EF list)
        base_known = list(KNOWN_EF)
        if len(base_known) < 10:
            return

        raw_errors = []
        actual_errors = []

        for i, held_out in enumerate(base_known):
            # Build temporary predictor state without this entry
            comp = parse_formula(held_out.formula)
            query_vec = composition_vector(comp)
            epsilon = 0.01

            # Find k nearest neighbours EXCLUDING the held-out entry
            distances = []
            for j, entry in enumerate(base_known):
                if j == i:
                    continue
                dist = float(np.linalg.norm(query_vec - entry.vector))
                distances.append((entry, dist))
            distances.sort(key=lambda x: x[1])
            neighbours = distances[:self.k]

            if not neighbours:
                continue

            # IDW prediction (same logic as _kan_predict)
            weights = [1.0 / (d + epsilon) for _, d in neighbours]
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            ef_pred = sum(e.ef_per_atom * w for (e, _), w in zip(neighbours, weights))

            # Raw error estimate (same heuristic as _kan_predict)
            min_dist = neighbours[0][1]
            neighbor_vals = [e.ef_per_atom for e, _ in neighbours]
            local_std = float(np.std(neighbor_vals)) if len(neighbor_vals) > 1 else 0.1
            raw_err = 0.05 + (min_dist * 0.1) + (local_std * 0.5)

            actual_err = abs(ef_pred - held_out.ef_per_atom)

            raw_errors.append(raw_err)
            actual_errors.append(actual_err)

        if len(raw_errors) < 10:
            return

        # Fit linear calibration: actual_error ≈ a * raw_error + b
        raw_arr = np.array(raw_errors)
        act_arr = np.array(actual_errors)
        # Least-squares fit
        A = np.vstack([raw_arr, np.ones(len(raw_arr))]).T
        result = np.linalg.lstsq(A, act_arr, rcond=None)
        self._cal_a = float(result[0][0])
        self._cal_b = float(result[0][1])
        self._calibrated = True

    def _calibrate_error(self, raw_error: float) -> float:
        """Apply calibration to raw error estimate."""
        if not self._calibrated:
            return raw_error
        calibrated = self._cal_a * raw_error + self._cal_b
        return max(0.01, calibrated)  # Floor at 0.01 eV/atom

    def predict(
        self,
        formula: str,
        structure_type: Optional[str] = None,
        exclude_formula: Optional[str] = None,
    ) -> FormationEnergyResult:
        """
        Predict formation energy for a chemical formula.

        Args:
            formula: The chemical formula
            structure_type: Optional structure type (layered, spinel, etc.)
                to bias the Kan extension towards similar structures.
            exclude_formula: Optional material name, formula, or MP ID to exclude
                from the Kan neighborhood for leave-one-out validation.
        """
        resolved = SHORTHAND_MAP.get(formula, formula)
        comp = parse_formula(resolved)

        # Step 1: Kan extension over known formation energies
        # Now returns (ef, confidence, error_estimate, nearest)
        kan_ef, kan_conf, kan_error, nearest = self._kan_predict(
            comp, structure_type, exclude_formula=exclude_formula
        )

        # Step 2: Rule-based estimates
        kap_ef = _kapustinskii_estimate(comp)
        en_ef = _electronegativity_estimate(comp)

        # 3. Dempster-Shafer fusion
        # kan_error is min_dist based
        min_dist = nearest[0][1] if nearest else 1.0
        ef_predicted, confidence = self._fuse(kan_ef, kan_conf, kap_ef, en_ef, min_dist=min_dist)


        # Ensemble spread: disagreement between estimators as additional UQ signal
        estimator_vals = [v for v in [kan_ef, kap_ef, en_ef] if v is not None]
        ensemble_spread = (max(estimator_vals) - min(estimator_vals)) if len(estimator_vals) > 1 else 0.0

        # Total uncertainty: combine Kan error with ensemble spread, then calibrate
        # Rule estimators are useful far from DFT anchors, but they should not
        # inflate uncertainty when the Kan source is an exact or near-exact DFT
        # match. Use the same distance-ramp philosophy as _fuse().
        rule_spread_weight = min(1.0, max(0.0, (min_dist - 0.05) / 0.50))
        raw_error = kan_error * (1.1 - confidence) + 0.2 * ensemble_spread * rule_spread_weight
        total_error = self._calibrate_error(raw_error)

        # Build sources dict before external calibration can add its mean model.
        sources: Dict[str, float] = {}
        if kan_ef is not None:
            sources["kan_extension"] = kan_ef
        if kap_ef is not None:
            sources["kapustinskii"] = kap_ef
        if en_ef is not None:
            sources["electronegativity"] = en_ef

        chemistry_class = "unknown"
        calibrated_intervals: Dict[str, float] = {}
        calibration_status = "not_calibrated"
        if self._external_calibration:
            try:
                from .phase16_calibration import classify_chemistry, load_calibration_model
                chemistry_class = classify_chemistry(comp)
                model = load_calibration_model(self._calibration_model_path)
                if model is None:
                    calibration_status = "phase16_model_missing"
                else:
                    calibrated_mean = model.predict_mean(comp)
                    # The external mean model is strongest for sparse discovery
                    # space. Dense local interpolation should preserve the
                    # anchored Kan value, especially for tuned battery families.
                    if calibrated_mean is not None and min_dist >= 0.5:
                        ef_predicted = calibrated_mean
                        sources["phase16_mean_model"] = calibrated_mean
                    calibrated_intervals = model.intervals(total_error, chemistry_class)
                    # Post-hoc conformal rescale to honest coverage (identity if
                    # no factors file present). Point prediction is untouched.
                    calibrated_intervals = _apply_conformal_factors(calibrated_intervals)
                    calibration_status = model.status_for(chemistry_class)
            except Exception:
                calibration_status = "phase16_model_error"

        # Step 4: ZFC thermodynamic constraints
        constraints = check_thermodynamic_constraints(comp, ef_predicted, formula)

        # Step 5: Synthesizability score
        synth_score = self._compute_synthesizability(ef_predicted, confidence, constraints)

        # Determine uncertainty tier
        tier = UncertaintyTier.HEURISTIC_ESTIMATE
        if nearest:
            min_dist = nearest[0][1]
            if min_dist < 0.05:
                tier = UncertaintyTier.EXACT_MATCH
            elif min_dist < 0.2:
                tier = UncertaintyTier.DENSE_INTERPOLATION
            elif min_dist < 0.5:
                tier = UncertaintyTier.MODERATE_EXTRAPOLATION
            else:
                tier = UncertaintyTier.SPARSE_DISCOVERY

        return FormationEnergyResult(
            formula=formula,
            ef_per_atom=ef_predicted,
            error_estimate_eV=round(total_error, 4),
            confidence=confidence,
            uncertainty_tier=tier,
            chemistry_class=chemistry_class,
            calibrated_intervals_eV=calibrated_intervals,
            calibration_status=calibration_status,
            sources=sources,
            is_stable=ef_predicted < 0,
            synthesizability_score=synth_score,
            constraints=constraints,
            nearest_known=nearest,
        )

    def _kan_predict(self, query_comp: Dict[str, float],
                     structure_type: Optional[str] = None,
                     exclude_formula: Optional[str] = None
                     ) -> Tuple[Optional[float], float, float, List[Tuple[str, float, float]]]:
        """
        Kan extension: inverse-distance-weighted colimit over known Ef values.

        Returns:
            (ef_predicted, confidence, error_estimate, nearest_list)
        """
        query_vec = composition_vector(query_comp)
        epsilon = 0.01

        # Use spatial index if available (fast path for large datasets)
        if self._ef_index is not None and not exclude_formula:
            neighbours = self._ef_index.nearest_k(query_vec, k=self.k)
        else:
            # Linear scan fallback (or True LOO path)
            distances = []
            for entry in self.known:
                if exclude_formula and exclude_formula in {entry.name, entry.formula, entry.mp_id}:
                    continue
                dist = float(np.linalg.norm(query_vec - entry.vector))
                distances.append((entry, dist))
            distances.sort(key=lambda x: x[1])
            neighbours = distances[:self.k]

        nearest = [
            (e.name, d, e.ef_per_atom) for e, d in neighbours
        ]

        if not neighbours:
            return None, 0.0, 0.5, nearest

        # 1. IDW weights with structure bias
        weights = []
        for entry, dist in neighbours:
            w = 1.0 / (dist + epsilon)
            if structure_type and entry.structure_type == structure_type:
                w *= 2.0
            weights.append(w)

        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        # 2. Weighted colimit (Prediction)
        ef_predicted = sum(e.ef_per_atom * w for (e, _), w in zip(neighbours, weights))

        # 3. Local Density & Variance (Uncertainty Quantification)
        # Epistemic: Distance to nearest neighbor
        min_dist = neighbours[0][1]

        # Aleatoric: Standard deviation among neighbors
        neighbor_vals = [e.ef_per_atom for e, _ in neighbours]
        local_std = float(np.std(neighbor_vals)) if len(neighbor_vals) > 1 else 0.1

        # Total Error Estimate (eV/atom)
        # Base floor 0.05 eV + penalty for distance + neighbor variance
        error_estimate = 0.05 + (min_dist * 0.1) + (local_std * 0.5)

        # 4. Confidence Score (0-1)
        # Based on Kulik-style density reasoning:
        # Low uncertainty (small dist, small variance) -> High confidence
        dist_factor = max(0.0, 1.0 - min_dist / 2.0)
        variance_factor = max(0.0, 1.0 - local_std / 1.0)
        confidence = 0.5 * dist_factor + 0.5 * variance_factor

        # Penalty for polymorph confusion (dist=0 but high variance)
        # If we are at the exact composition but Ef is inconsistent among neighbors
        if min_dist < 0.1 and local_std > 0.1:
            confidence *= (1.0 - local_std)

        confidence = min(0.95, max(0.05, confidence))

        return ef_predicted, confidence, error_estimate, nearest

    def _fuse(self, kan_ef: Optional[float], kan_conf: float,
              kap_ef: Optional[float], en_ef: Optional[float],
              min_dist: float = 1.0
              ) -> Tuple[float, float]:
        """Dempster-Shafer fusion of multiple formation energy estimates."""
        estimates = []
        # When Kan extension is available (we have nearby DFT data),
        # it is the primary source. Rule-based estimates serve as:
        # (a) sanity checks (sign agreement)
        # (b) fallbacks when Kan has no nearby data
        if kan_ef is not None and kan_conf > 0.3:
            # Kan dominates -- rule-based as minor correction
            estimates = [(kan_ef, kan_conf, "kan")]
            rule_vals = []
            if kap_ef is not None:
                rule_vals.append(kap_ef)
            if en_ef is not None:
                rule_vals.append(en_ef)

            if rule_vals:
                # Use rule-based only as sign-agreement check
                rule_avg = sum(rule_vals) / len(rule_vals)
                sign_agrees = (kan_ef < 0) == (rule_avg < 0)

                # D-S fusion: Kan with high weight, rules as confirmatory
                frame = frozenset(["accurate", "inaccurate"])
                accurate = frozenset(["accurate"])
                m_kan = MassFunction(masses={accurate: kan_conf, frame: 1.0 - kan_conf})

                rule_conf = 0.3 if sign_agrees else 0.1
                m_rule = MassFunction(masses={accurate: rule_conf, frame: 1.0 - rule_conf})

                try:
                    combined, _ = combine(m_kan, m_rule)
                    fused_conf = combined.belief(accurate)
                except ValueError:
                    fused_conf = kan_conf

                # Value: Kan dominates (90%+), small rule nudge
                # DE-WEIGHTING: If min_dist is very small (<0.1), rules get 0 weight
                # Linear ramp from 0 to 0.05 between dist 0 and 0.2
                rule_weight = 0.05 * min(1.0, max(0.0, (min_dist - 0.05) / 0.15))

                fused_val = kan_ef * (1.0 - rule_weight) + rule_avg * rule_weight
                return fused_val, min(0.95, max(0.1, fused_conf))
            else:
                return kan_ef, kan_conf * 0.9

        # Fallback: no good Kan data, rely on rules
        estimates = []
        if kan_ef is not None:
            estimates.append((kan_ef, kan_conf, "kan"))
        if kap_ef is not None:
            estimates.append((kap_ef, 0.40, "kap"))
        if en_ef is not None:
            estimates.append((en_ef, 0.35, "en"))

        if not estimates:
            return 0.0, 0.05

        if len(estimates) == 1:
            return estimates[0][0], estimates[0][1] * 0.9

        # Simple confidence-weighted average for fallback
        total_conf = sum(c for _, c, _ in estimates)
        if total_conf > 0:
            fused_val = sum(v * c for v, c, _ in estimates) / total_conf
        else:
            fused_val = sum(v for v, _, _ in estimates) / len(estimates)
        avg_conf = total_conf / len(estimates)
        return fused_val, min(0.85, max(0.1, avg_conf))

    def _compute_synthesizability(self, ef: float, confidence: float,
                                  constraints: List[ThermodynamicConstraint]
                                  ) -> float:
        """
        Compute overall synthesizability score (0-1).

        Combines:
        - Formation energy favorability
        - Constraint satisfaction ratio
        - Prediction confidence
        """
        # Energy favorability: more negative = more synthesizable
        if ef >= 0:
            energy_score = 0.1  # Positive Ef: very unlikely
        elif ef > -0.1:
            energy_score = 0.3  # Marginal
        elif ef > -1.0:
            energy_score = 0.5 + 0.3 * (-ef - 0.1) / 0.9  # Linear ramp
        else:
            energy_score = min(0.95, 0.8 + 0.15 * (-ef - 1.0) / 2.0)  # Saturates

        # Constraint satisfaction
        if constraints:
            n_satisfied = sum(1 for c in constraints if c.satisfied)
            constraint_score = n_satisfied / len(constraints)
        else:
            constraint_score = 0.5

        # Weighted combination
        synth = 0.45 * energy_score + 0.35 * constraint_score + 0.20 * confidence
        return min(0.95, max(0.05, synth))


if __name__ == "__main__":
    fep = FormationEnergyPredictor()

    print("=" * 75)
    print("Formation Energy Predictor -- Categorical DFT Surrogate")
    print("=" * 75)

    formulas = [
        "NMC811", "NMC622", "NMC111", "NMC721", "NMC532",
        "LCO", "LFP", "LMO", "LLZO", "NCA",
        "LiNi0.9Mn0.05Co0.05O2",
        "LiNi0.7Mn0.15Co0.15O2",
    ]

    for f in formulas:
        result = fep.predict(f)
        status = "STABLE" if result.is_stable else "UNSTABLE"
        print(f"\n{f}: Ef = {result.ef_per_atom:.3f} +/- {result.error_estimate_eV:.3f} eV/atom  [{status}]"
              f"  synth={result.synthesizability_score:.2f}  conf={result.confidence:.2f}")
        print(f"  Sources: {result.sources}")
        n_ok = sum(1 for c in result.constraints if c.satisfied)
        n_total = len(result.constraints)
        print(f"  ZFC constraints: {n_ok}/{n_total} satisfied")
        for c in result.constraints:
            flag = "OK" if c.satisfied else "FAIL"
            print(f"    [{flag}] {c.name}: {c.detail[:80]}")
