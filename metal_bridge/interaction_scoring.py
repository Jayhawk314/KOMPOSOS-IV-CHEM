# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Metal Interaction Scoring
============================

Five compatibility scorers for metal interface/joint assessment,
analogous to polymer_bridge/interaction_scoring.py.

Each scorer takes two MetalMaterial objects and returns a float in [0, 1].

Scorer Mapping (polymer bridge -> metal bridge):
---------------------------------------------------
Solubility compat.   -> Galvanic compatibility (electrode potential)
Thermal compat.      -> Thermal compatibility (CTE mismatch, Tm gap)
Mechanical compat.   -> Mechanical compatibility (modulus/strength)
Chemical resistance  -> Metallurgical compatibility (crystal, solubility)
Aging penalty        -> Corrosion penalty (known pairs, environment)

References:
-----------
- Jones, "Principles and Prevention of Corrosion" 2nd ed., 1996
- ASM Handbook Vol. 13A, "Corrosion: Fundamentals", 2003
- Hume-Rothery, "The Structure of Metals and Alloys", 1936
- ASTM G82, "Standard Guide for Development of Galvanic Series"
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from metal_bridge.material_properties import (
    MetalMaterial, MetalClass, MetalFailureMode, CrystalSystem,
    get_metal,
)


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# 1. GALVANIC COMPATIBILITY SCORE
# =============================================================================
# Analogous to polymer solubility: "Will these corrode each other?"
# Based on galvanic series position difference.

def score_galvanic_compatibility(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> ScorerResult:
    """
    Score galvanic compatibility between two metals.

    Based on electrode potential difference in the galvanic series.
    Larger potential difference = more galvanic corrosion risk.

    Potential difference interpretation:
        dV < 0.05V:  negligible galvanic risk
        0.05-0.15V:  low risk
        0.15-0.30V:  moderate risk (caution in wet environments)
        0.30-0.50V:  high risk (insulation required)
        > 0.50V:     severe (avoid direct contact)

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {}

    va = material_a.galvanic_potential_V
    vb = material_b.galvanic_potential_V

    if va is None or vb is None:
        details['note'] = 'Galvanic potential not available for one/both metals'
        return ScorerResult(score=0.5, label='galvanic_compatibility', details=details)

    dv = abs(va - vb)
    details['potential_a_V'] = va
    details['potential_b_V'] = vb
    details['potential_difference_V'] = round(dv, 3)

    # Identify anode (more negative potential = corrodes)
    if va < vb:
        details['anode'] = material_a.formula
        details['cathode'] = material_b.formula
    else:
        details['anode'] = material_b.formula
        details['cathode'] = material_a.formula

    if dv < 0.05:
        score = 0.95
        details['galvanic_risk'] = 'negligible'
    elif dv < 0.15:
        score = 0.85 - (dv - 0.05) * 1.0
        details['galvanic_risk'] = 'low'
    elif dv < 0.30:
        score = 0.75 - (dv - 0.15) * 1.5
        details['galvanic_risk'] = 'moderate (insulate in wet environments)'
    elif dv < 0.50:
        score = 0.525 - (dv - 0.30) * 1.25
        details['galvanic_risk'] = 'high (electrical insulation required)'
    elif dv < 1.0:
        score = 0.275 - (dv - 0.50) * 0.35
        details['galvanic_risk'] = 'severe (avoid direct contact)'
    else:
        score = max(0.05, 0.10 - (dv - 1.0) * 0.05)
        details['galvanic_risk'] = 'extreme (e.g., Mg near Cu/steel)'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='galvanic_compatibility', details=details)


# =============================================================================
# 2. THERMAL COMPATIBILITY SCORE
# =============================================================================
# CTE mismatch causes thermal fatigue at joints.

def score_thermal_compatibility(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> ScorerResult:
    """
    Score thermal compatibility between two metals.

    Factors:
    - CTE mismatch: different expansion = interfacial stress during thermal cycling
    - Melting point gap: affects joining method selection (welding, brazing)
    - Thermal conductivity mismatch: affects heat treatment uniformity

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- CTE mismatch ---
    cte_a = material_a.cte_per_K
    cte_b = material_b.cte_per_K

    if cte_a is not None and cte_b is not None and cte_a > 0 and cte_b > 0:
        cte_ratio = max(cte_a, cte_b) / min(cte_a, cte_b)
        cte_diff = abs(cte_a - cte_b)
        details['cte_a'] = cte_a
        details['cte_b'] = cte_b
        details['cte_ratio'] = round(cte_ratio, 2)
        details['cte_difference'] = round(cte_diff, 1)

        if cte_ratio > 4.0:
            score *= 0.3
            details['cte_assessment'] = 'extreme CTE mismatch; thermal fatigue inevitable'
        elif cte_ratio > 3.0:
            score *= 0.5
            details['cte_assessment'] = 'severe CTE mismatch; thermal cycling risk'
        elif cte_ratio > 2.0:
            score *= 0.7
            details['cte_assessment'] = 'moderate CTE mismatch'
        elif cte_ratio > 1.3:
            score *= 0.85
            details['cte_assessment'] = 'mild CTE mismatch'
        else:
            details['cte_assessment'] = 'compatible CTE'

    # --- Melting point gap ---
    tm_a = material_a.melting_point_C
    tm_b = material_b.melting_point_C

    if tm_a is not None and tm_b is not None:
        tm_ratio = max(tm_a, tm_b) / max(min(tm_a, tm_b), 1.0)
        tm_diff = abs(tm_a - tm_b)
        details['melting_point_a_C'] = tm_a
        details['melting_point_b_C'] = tm_b
        details['melting_point_gap_C'] = round(tm_diff, 0)

        if tm_ratio > 3.0:
            score *= 0.5
            details['melting_risk'] = 'extreme Tm gap; one melts while other is cold'
        elif tm_ratio > 2.0:
            score *= 0.7
            details['melting_risk'] = 'large Tm gap; welding difficult'
        elif tm_diff > 500:
            score *= 0.8
            details['melting_risk'] = 'significant Tm gap'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='thermal_compatibility', details=details)


# =============================================================================
# 3. MECHANICAL COMPATIBILITY SCORE
# =============================================================================

def score_mechanical_compatibility(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> ScorerResult:
    """
    Score mechanical compatibility between two metals.

    Factors:
    - Elastic modulus mismatch: stress concentration at interface
    - Strength mismatch: load transfer imbalance
    - Ductility mismatch: brittle + ductile = crack propagation risk

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- Elastic modulus mismatch ---
    mod_a = material_a.elastic_modulus_GPa
    mod_b = material_b.elastic_modulus_GPa

    if mod_a is not None and mod_b is not None and mod_a > 0 and mod_b > 0:
        mod_ratio = max(mod_a, mod_b) / min(mod_a, mod_b)
        details['modulus_a_GPa'] = mod_a
        details['modulus_b_GPa'] = mod_b
        details['modulus_ratio'] = round(mod_ratio, 2)

        if mod_ratio > 10:
            score *= 0.4
            details['modulus_assessment'] = 'extreme modulus mismatch'
        elif mod_ratio > 5:
            score *= 0.6
            details['modulus_assessment'] = 'large modulus mismatch'
        elif mod_ratio > 3:
            score *= 0.8
            details['modulus_assessment'] = 'moderate modulus mismatch'
        elif mod_ratio > 2:
            score *= 0.9
            details['modulus_assessment'] = 'mild modulus mismatch'

    # --- Strength mismatch (yield strength) ---
    ys_a = material_a.yield_strength_MPa
    ys_b = material_b.yield_strength_MPa

    if ys_a is not None and ys_b is not None and ys_a > 0 and ys_b > 0:
        ys_ratio = max(ys_a, ys_b) / min(ys_a, ys_b)
        details['yield_strength_ratio'] = round(ys_ratio, 2)

        if ys_ratio > 20:
            score *= 0.6
            details['strength_assessment'] = 'extreme strength mismatch'
        elif ys_ratio > 10:
            score *= 0.75
            details['strength_assessment'] = 'large strength mismatch'
        elif ys_ratio > 5:
            score *= 0.85
            details['strength_assessment'] = 'moderate strength mismatch'

    # --- Ductility mismatch ---
    elong_a = material_a.elongation_pct
    elong_b = material_b.elongation_pct

    if elong_a is not None and elong_b is not None:
        # One very brittle + one ductile
        min_elong = min(elong_a, elong_b)
        max_elong = max(elong_a, elong_b)

        if min_elong < 2.0 and max_elong > 30.0:
            score *= 0.7
            details['ductility_assessment'] = 'brittle + ductile: crack initiation risk'
        elif min_elong < 5.0 and max_elong > 20.0:
            score *= 0.85
            details['ductility_assessment'] = 'significant ductility mismatch'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 4. METALLURGICAL COMPATIBILITY SCORE
# =============================================================================
# Can these metals form sound joints? Crystal structure, solid solubility,
# intermetallic formation.

# Hume-Rothery atomic radii (pm, metallic) for solid solubility estimation
_ATOMIC_RADII_PM = {
    'Fe': 126, 'Al': 143, 'Cu': 128, 'Ti': 147, 'Ni': 124,
    'Zn': 134, 'Mg': 160, 'W': 139, 'Mo': 139, 'Sn': 151,
    'Pb': 175, 'Ag': 144, 'Au': 144, 'Pt': 139, 'Cr': 128,
}

# Known intermetallic-forming pairs (brittle compounds at interface)
_INTERMETALLIC_PAIRS = {
    ('Fe', 'Al'), ('Al', 'Fe'),
    ('Ti', 'Al'), ('Al', 'Ti'),
    ('Cu', 'Al'), ('Al', 'Cu'),
    ('Ni', 'Al'), ('Al', 'Ni'),
    ('Ti', 'Fe'), ('Fe', 'Ti'),
}

# Known complete/extensive solid solution pairs
_SOLID_SOLUTION_PAIRS = {
    ('Cu', 'Ni'), ('Ni', 'Cu'),
    ('Au', 'Ag'), ('Ag', 'Au'),
    ('Au', 'Cu'), ('Cu', 'Au'),
    ('Fe', 'Ni'), ('Ni', 'Fe'),
    ('Fe', 'Cr'), ('Cr', 'Fe'),
    ('Mo', 'W'), ('W', 'Mo'),
}


def _get_base_element(material: MetalMaterial) -> str:
    """Extract base element from formula for metallurgical lookup."""
    formula = material.formula
    # Pure metals: Fe, Al, Cu, etc.
    if formula in _ATOMIC_RADII_PM:
        return formula
    # Alloys: extract first element
    for elem in ['Fe', 'Al', 'Cu', 'Ti', 'Ni', 'Zn', 'Mg', 'W', 'Mo',
                  'Sn', 'Pb', 'Ag', 'Au', 'Pt']:
        if formula.startswith(elem):
            return elem
    # Stainless steels are Fe-based
    if 'Fe-' in formula or 'Fe ' in formula:
        return 'Fe'
    # Inconel, Hastelloy are Ni-based
    if 'Ni-' in formula or 'Ni ' in formula:
        return 'Ni'
    return formula.split('-')[0] if '-' in formula else formula[:2]


def score_metallurgical_compatibility(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> ScorerResult:
    """
    Score metallurgical compatibility between two metals.

    Factors:
    - Crystal structure match (FCC+FCC better than FCC+BCC)
    - Atomic size factor (Hume-Rothery: <15% difference for solid solution)
    - Known intermetallic formation
    - Known solid solution pairs
    - Same metal class bonus

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 0.7  # Default: moderate compatibility
    details = {}

    # --- Same metal class = strong bonus ---
    if material_a.metal_class == material_b.metal_class:
        score = 0.9
        details['class_match'] = True
    else:
        details['class_match'] = False

    # --- Crystal structure match ---
    cs_a = material_a.crystal_system
    cs_b = material_b.crystal_system
    details['crystal_a'] = cs_a.value
    details['crystal_b'] = cs_b.value

    if cs_a == cs_b and cs_a != CrystalSystem.MIXED:
        score = min(1.0, score + 0.1)
        details['crystal_match'] = 'same crystal structure (favorable for bonding)'
    elif {cs_a, cs_b} == {CrystalSystem.FCC, CrystalSystem.BCC}:
        score *= 0.85
        details['crystal_match'] = 'FCC/BCC mismatch (some compatibility)'
    elif CrystalSystem.HCP in {cs_a, cs_b}:
        score *= 0.8
        details['crystal_match'] = 'HCP involved (limited slip systems)'

    # --- Hume-Rothery atomic size factor ---
    elem_a = _get_base_element(material_a)
    elem_b = _get_base_element(material_b)
    details['base_element_a'] = elem_a
    details['base_element_b'] = elem_b

    r_a = _ATOMIC_RADII_PM.get(elem_a)
    r_b = _ATOMIC_RADII_PM.get(elem_b)

    if r_a is not None and r_b is not None:
        size_factor = abs(r_a - r_b) / min(r_a, r_b)
        details['atomic_size_factor'] = round(size_factor, 3)

        if size_factor < 0.08:
            details['hume_rothery'] = 'excellent size match (< 8%)'
        elif size_factor < 0.15:
            details['hume_rothery'] = 'acceptable size match (< 15%)'
        else:
            score *= 0.7
            details['hume_rothery'] = f'size mismatch ({size_factor:.1%} > 15%); limited solid solubility'

    # --- Known intermetallic pairs (PENALTY) ---
    pair = (elem_a, elem_b)
    if pair in _INTERMETALLIC_PAIRS:
        score *= 0.5
        details['intermetallic_risk'] = f'{elem_a}-{elem_b} intermetallics form at interface (brittle)'

    # --- Known solid solution pairs (BONUS) ---
    if pair in _SOLID_SOLUTION_PAIRS:
        score = min(1.0, score + 0.2)
        details['solid_solution'] = f'{elem_a}-{elem_b} form solid solution (excellent)'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='metallurgical_compatibility', details=details)


# =============================================================================
# 5. CORROSION PENALTY
# =============================================================================

# Known problematic pairings in service
_KNOWN_BAD_METAL_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('Cu', 'Al'): (0.6, 'Severe galvanic corrosion in wet environments; Al corrodes rapidly'),
    ('Al', 'Cu'): (0.6, 'Severe galvanic corrosion in wet environments; Al corrodes rapidly'),
    ('Mg', 'Cu'): (0.8, 'Extreme galvanic couple; Mg dissolves rapidly near Cu'),
    ('Cu', 'Mg'): (0.8, 'Extreme galvanic couple; Mg dissolves rapidly near Cu'),
    ('Mg', 'Fe'): (0.7, 'Strong galvanic couple; Mg is sacrificial anode'),
    ('Fe', 'Mg'): (0.7, 'Strong galvanic couple; Mg is sacrificial anode'),
    ('Al', 'Fe'): (0.4, 'Moderate galvanic couple; Al corrodes near steel in wet environments'),
    ('Fe', 'Al'): (0.4, 'Moderate galvanic couple; Al corrodes near steel in wet environments'),
    ('Mg', 'Ni'): (0.7, 'Severe galvanic couple'),
    ('Ni', 'Mg'): (0.7, 'Severe galvanic couple'),
    # Fe + Cu: galvanic couple per MIL-STD-889D (0.35V difference)
    ('Fe', 'Cu'): (0.5, 'Galvanic corrosion; iron/steel corrodes near copper in wet environments'),
    ('Cu', 'Fe'): (0.5, 'Galvanic corrosion; iron/steel corrodes near copper in wet environments'),
}


def score_corrosion_penalty(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> ScorerResult:
    """
    Apply corrosion penalty for known problematic metal pairings.

    Factors:
    - Known bad pairing lookup
    - Shared corrosion vulnerabilities
    - Passivating vs non-passivating mismatch
    - High corrosion rate materials

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        ScorerResult with score in [0, 1] (1 = no corrosion concerns)
    """
    penalty = 0.0
    reasons = []

    # --- Known bad pairings lookup ---
    elem_a = _get_base_element(material_a)
    elem_b = _get_base_element(material_b)

    for key in [(elem_a, elem_b), (elem_b, elem_a)]:
        if key in _KNOWN_BAD_METAL_PAIRS:
            p, reason = _KNOWN_BAD_METAL_PAIRS[key]
            penalty = max(penalty, p)
            reasons.append(reason)
            break  # Don't double-count

    # --- Shared critical failure modes ---
    shared_failures = set(material_a.failure_modes) & set(material_b.failure_modes)
    critical_shared = shared_failures & {
        MetalFailureMode.STRESS_CORROSION_CRACKING,
        MetalFailureMode.HYDROGEN_EMBRITTLEMENT,
        MetalFailureMode.PITTING,
    }
    if critical_shared:
        penalty = max(penalty, 0.1 * len(critical_shared))
        reasons.append(f'Shared vulnerabilities: {[f.value for f in critical_shared]}')

    # --- High corrosion rate ---
    for mat in [material_a, material_b]:
        if mat.corrosion_rate_mm_yr is not None and mat.corrosion_rate_mm_yr > 0.05:
            penalty = max(penalty, 0.2)
            reasons.append(f'{mat.formula} has high corrosion rate ({mat.corrosion_rate_mm_yr} mm/yr)')

    # --- Sensitization risk (stainless steels) ---
    for mat in [material_a, material_b]:
        if MetalFailureMode.SENSITIZATION in mat.failure_modes:
            penalty = max(penalty, 0.1)
            reasons.append(f'{mat.formula}: sensitization risk (weld decay)')

    # --- Dezincification risk (brass) ---
    for mat in [material_a, material_b]:
        if MetalFailureMode.DEZINCIFICATION in mat.failure_modes:
            penalty = max(penalty, 0.15)
            reasons.append(f'{mat.formula}: dezincification risk')

    score = max(0.0, 1.0 - penalty)
    details = {
        'penalty': round(penalty, 2),
        'reasons': reasons if reasons else ['No known corrosion concerns'],
    }

    return ScorerResult(score=score, label='corrosion_penalty', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(
    material_a: MetalMaterial,
    material_b: MetalMaterial,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a metal pair.

    Args:
        material_a: First metal
        material_b: Second metal

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'galvanic_compatibility': score_galvanic_compatibility(material_a, material_b),
        'thermal_compatibility': score_thermal_compatibility(material_a, material_b),
        'mechanical_compatibility': score_mechanical_compatibility(material_a, material_b),
        'metallurgical_compatibility': score_metallurgical_compatibility(material_a, material_b),
        'corrosion_penalty': score_corrosion_penalty(material_a, material_b),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("Metal Interaction Scoring - Demo")
    print("=" * 70)
    print()

    # Good pair: 304SS + 316SS
    a = get_metal('SS_304')
    b = get_metal('SS_316')
    print(f"Pair: {a.formula} <-> {b.formula} (same family)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
    print()

    # Bad pair: Cu + Al
    a = get_metal('Cu')
    b = get_metal('Al')
    print(f"Pair: {a.formula} <-> {b.formula} (galvanic couple)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}  {result.details}")
