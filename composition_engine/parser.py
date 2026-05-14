# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Chemical Formula Parser + Composition Distance

Parses chemical formulas into element-stoichiometry dicts and computes
distances in composition space for Kan extension neighbour queries.

Examples:
    parse_formula("LiNi0.8Mn0.1Co0.1O2")  -> {"Li": 1.0, "Ni": 0.8, ...}
    parse_formula("LiFePO4")               -> {"Li": 1.0, "Fe": 1.0, ...}
    composition_distance(comp_a, comp_b)   -> float (Euclidean)
"""

import re
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── Shorthand map: common battery names -> actual formulas ──────────────────

SHORTHAND_MAP: Dict[str, str] = {
    # Cathodes
    "NMC811": "LiNi0.8Mn0.1Co0.1O2",
    "NMC622": "LiNi0.6Mn0.2Co0.2O2",
    "NMC111": "LiNi0.333Mn0.333Co0.333O2",
    "NMC333": "LiNi0.333Mn0.333Co0.333O2",
    "NMC532": "LiNi0.5Mn0.3Co0.2O2",
    "NMC721": "LiNi0.7Mn0.2Co0.1O2",
    "NMC442": "LiNi0.4Mn0.4Co0.2O2",
    "NMC955": "LiNi0.9Mn0.05Co0.05O2",
    "LCO": "LiCoO2",
    "LFP": "LiFePO4",
    "LMO": "LiMn2O4",
    "LTO": "Li4Ti5O12",
    "LNMO": "LiNi0.5Mn1.5O4",
    "NCA": "LiNi0.8Co0.15Al0.05O2",
    # Solid electrolytes
    "LLZO": "Li7La3Zr2O12",
    "LGPS": "Li10GeP2S12",
    "LATP": "Li1.3Al0.3Ti1.7P3O12",
    "LLTO": "Li0.5La0.5TiO3",
    # Anodes
    "Graphite": "C6",
    "Li_metal": "Li",
    # Ceramics
    "YSZ": "Zr0.92Y0.08O1.96",
    "BZY": "BaZr0.8Y0.2O3",
}


# ── Element data table ──────────────────────────────────────────────────────

@dataclass
class ElementData:
    symbol: str
    atomic_number: int
    atomic_mass: float          # g/mol
    electronegativity: float    # Pauling scale (0 if unknown)
    ionic_radius: float         # Angstroms, most common oxidation state CN=6
    common_oxidation: int       # Most common oxidation state in oxides

ELEMENT_TABLE: Dict[str, ElementData] = {}

_RAW_ELEMENTS = [
    # symbol, Z, mass, EN, ionic_radius, common_ox
    ("H",   1,   1.008, 2.20, 0.00,  1),
    ("Li",  3,   6.941, 0.98, 0.76,  1),
    ("Be",  4,   9.012, 1.57, 0.45,  2),
    ("B",   5,  10.811, 2.04, 0.27,  3),
    ("C",   6,  12.011, 2.55, 0.16,  4),
    ("N",   7,  14.007, 3.04, 0.13, -3),
    ("O",   8,  15.999, 3.44, 1.40, -2),
    ("F",   9,  18.998, 3.98, 1.33, -1),
    ("Na", 11,  22.990, 0.93, 1.02,  1),
    ("Mg", 12,  24.305, 1.31, 0.72,  2),
    ("Al", 13,  26.982, 1.61, 0.54,  3),
    ("Si", 14,  28.086, 1.90, 0.40,  4),
    ("P",  15,  30.974, 2.19, 0.38,  5),
    ("S",  16,  32.065, 2.58, 1.84, -2),
    ("Cl", 17,  35.453, 3.16, 1.81, -1),
    ("K",  19,  39.098, 0.82, 1.38,  1),
    ("Ca", 20,  40.078, 1.00, 1.00,  2),
    ("Ti", 22,  47.867, 1.54, 0.61,  4),
    ("V",  23,  50.942, 1.63, 0.54,  5),
    ("Cr", 24,  51.996, 1.66, 0.62,  3),
    ("Mn", 25,  54.938, 1.55, 0.53,  4),
    ("Fe", 26,  55.845, 1.83, 0.55,  3),
    ("Co", 27,  58.933, 1.88, 0.55,  3),
    ("Ni", 28,  58.693, 1.91, 0.56,  3),
    ("Cu", 29,  63.546, 1.90, 0.73,  2),
    ("Zn", 30,  65.380, 1.65, 0.74,  2),
    ("Ga", 31,  69.723, 1.81, 0.62,  3),
    ("Ge", 32,  72.640, 2.01, 0.53,  4),
    ("As", 33,  74.922, 2.18, 0.46,  5),
    ("Se", 34,  78.960, 2.55, 1.98, -2),
    ("Br", 35,  79.904, 2.96, 1.96, -1),
    ("Sr", 38,  87.620, 0.95, 1.18,  2),
    ("Y",  39,  88.906, 1.22, 0.90,  3),
    ("Zr", 40,  91.224, 1.33, 0.72,  4),
    ("Nb", 41,  92.906, 1.60, 0.64,  5),
    ("Mo", 42,  95.940, 2.16, 0.59,  6),
    ("Sn", 50, 118.710, 1.96, 0.69,  4),
    ("Ba", 56, 137.327, 0.89, 1.35,  2),
    ("La", 57, 138.905, 1.10, 1.03,  3),
    ("Ce", 58, 140.116, 1.12, 0.87,  4),
    ("W",  74, 183.840, 2.36, 0.60,  6),
]

for _sym, _z, _m, _en, _ir, _ox in _RAW_ELEMENTS:
    ELEMENT_TABLE[_sym] = ElementData(_sym, _z, _m, _en, _ir, _ox)


# ── Canonical element ordering for composition vectors ──────────────────────

ELEMENT_ORDER: List[str] = sorted(ELEMENT_TABLE.keys(),
                                   key=lambda s: ELEMENT_TABLE[s].atomic_number)


# ── Formula parser ──────────────────────────────────────────────────────────

def parse_formula(formula: str) -> Dict[str, float]:
    """
    Parse a chemical formula into {element: stoichiometry}.

    Handles:
        LiNi0.8Mn0.1Co0.1O2  -> {Li:1, Ni:0.8, Mn:0.1, Co:0.1, O:2}
        LiFePO4               -> {Li:1, Fe:1, P:1, O:4}
        Li7La3Zr2O12          -> {Li:7, La:3, Zr:2, O:12}
        Li1/3Mn1/3Co1/3       -> {Li:0.333, Mn:0.333, Co:0.333}

    Also resolves shorthands: NMC811, LFP, LCO, etc.
    """
    # Check shorthand
    if formula in SHORTHAND_MAP:
        formula = SHORTHAND_MAP[formula]

    composition: Dict[str, float] = {}

    # Regex: element symbol (1 upper + 0-1 lower) followed by optional number
    # Number can be integer, decimal, or fraction (1/3)
    pattern = r'([A-Z][a-z]?)(\d+\.?\d*(?:/\d+\.?\d*)?)?'

    for match in re.finditer(pattern, formula):
        element = match.group(1)
        amount_str = match.group(2)

        if amount_str is None or amount_str == '':
            amount = 1.0
        elif '/' in amount_str:
            num, den = amount_str.split('/')
            amount = float(num) / float(den)
        else:
            amount = float(amount_str)

        composition[element] = composition.get(element, 0.0) + amount

    return composition


def composition_vector(comp: Dict[str, float]) -> np.ndarray:
    """
    Convert composition dict to fixed-length numpy vector.

    Elements ordered by atomic number (ELEMENT_ORDER).
    Unknown elements get index at end.
    """
    vec = np.zeros(len(ELEMENT_ORDER))
    for elem, amount in comp.items():
        if elem in ELEMENT_ORDER:
            idx = ELEMENT_ORDER.index(elem)
            vec[idx] = amount
    return vec


def composition_distance(comp_a: Dict[str, float],
                         comp_b: Dict[str, float]) -> float:
    """
    Euclidean distance in stoichiometry space.

    This is the primary metric for finding nearest known compositions
    for Kan extension prediction.
    """
    vec_a = composition_vector(comp_a)
    vec_b = composition_vector(comp_b)
    return float(np.linalg.norm(vec_a - vec_b))


def molar_mass(comp: Dict[str, float]) -> float:
    """Compute molar mass from composition."""
    total = 0.0
    for elem, amount in comp.items():
        if elem in ELEMENT_TABLE:
            total += amount * ELEMENT_TABLE[elem].atomic_mass
    return total


def average_electronegativity(comp: Dict[str, float]) -> float:
    """Stoichiometry-weighted average Pauling electronegativity."""
    total_en = 0.0
    total_amount = 0.0
    for elem, amount in comp.items():
        if elem in ELEMENT_TABLE and ELEMENT_TABLE[elem].electronegativity > 0:
            total_en += amount * ELEMENT_TABLE[elem].electronegativity
            total_amount += amount
    if total_amount == 0:
        return 0.0
    return total_en / total_amount


def metal_fraction(comp: Dict[str, float],
                   metals: Optional[List[str]] = None) -> Dict[str, float]:
    """
    Extract transition-metal fractions from a composition.

    For NMC: returns {"Ni": 0.8, "Mn": 0.1, "Co": 0.1} from NMC811.
    """
    if metals is None:
        metals = ["Ni", "Mn", "Co", "Fe", "Al", "Ti", "V", "Cr", "Cu", "Zn"]
    fracs = {}
    total = 0.0
    for m in metals:
        if m in comp:
            fracs[m] = comp[m]
            total += comp[m]
    if total > 0:
        fracs = {k: v / total for k, v in fracs.items()}
    return fracs


if __name__ == "__main__":
    examples = [
        "LiNi0.8Mn0.1Co0.1O2",
        "LiFePO4",
        "LiCoO2",
        "NMC622",
        "NMC532",
        "Li7La3Zr2O12",
        "LiNi0.7Mn0.15Co0.15O2",
    ]
    for f in examples:
        comp = parse_formula(f)
        mm = molar_mass(comp)
        en = average_electronegativity(comp)
        print(f"{f:30s} -> M={mm:.1f} g/mol, EN_avg={en:.2f}, comp={comp}")
