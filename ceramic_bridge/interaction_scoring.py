# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Ceramic Interaction Scoring
============================

Five compatibility scorers for ceramic interface/composite assessment,
analogous to metal_bridge/interaction_scoring.py.

Each scorer takes two CeramicMaterial objects and returns a float in [0, 1].

Scorer Mapping (metal bridge -> ceramic bridge):
---------------------------------------------------
Galvanic compat.     -> Sintering compatibility (temp window overlap)
Thermal compat.      -> CTE match (thermal expansion mismatch -> cracking)
Mechanical compat.   -> Mechanical compatibility (modulus/toughness)
Metallurgical compat.-> Chemical compatibility (phase reactions, crystal match)
Corrosion penalty    -> Degradation penalty (known failures, environment)

References:
-----------
- Kingery, Bowen & Uhlmann, "Introduction to Ceramics" 2nd ed., 1976
- Richerson, "Modern Ceramic Engineering", 3rd ed., 2005
- Carter & Norton, "Ceramic Materials: Science and Engineering", 2007
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from ceramic_bridge.material_properties import (
    CeramicMaterial, CeramicClass, CeramicFailureMode, CrystalSystem,
    get_ceramic,
)


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# 1. SINTERING COMPATIBILITY SCORE
# =============================================================================
# Can both ceramics be processed in the same furnace / co-sintered?
# Based on sintering temperature window overlap.

def score_sintering_compatibility(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> ScorerResult:
    """
    Score sintering compatibility between two ceramics.

    Checks whether both materials can be processed together:
    - Sintering temp overlap
    - Max use temp of one vs sintering temp of other
    - One decomposes before the other sinters

    Args:
        material_a: First ceramic
        material_b: Second ceramic

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {}

    ts_a = material_a.sintering_temp_C
    ts_b = material_b.sintering_temp_C

    # If sintering temps are unknown (e.g. glasses), use melting point
    if ts_a is None:
        ts_a = material_a.melting_point_C
        details['note_a'] = 'Using melting point as sintering proxy'
    if ts_b is None:
        ts_b = material_b.melting_point_C
        details['note_b'] = 'Using melting point as sintering proxy'

    if ts_a is None or ts_b is None:
        details['note'] = 'Sintering temperature not available'
        return ScorerResult(score=0.5, label='sintering_compatibility', details=details)

    details['sintering_temp_a_C'] = ts_a
    details['sintering_temp_b_C'] = ts_b

    temp_diff = abs(ts_a - ts_b)
    details['temp_difference_C'] = round(temp_diff, 0)

    # Check if one material melts/decomposes before the other sinters.
    # Use melting point (not max_use_temp, which is continuous service temp).
    mp_a = material_a.melting_point_C
    mp_b = material_b.melting_point_C

    decomposition_conflict = False
    if mp_a is not None and ts_b > mp_a:
        decomposition_conflict = True
        details['conflict'] = f'{material_a.formula} melts at {mp_a}C < {material_b.formula} sintering {ts_b}C'
    if mp_b is not None and ts_a > mp_b:
        decomposition_conflict = True
        details['conflict'] = f'{material_b.formula} melts at {mp_b}C < {material_a.formula} sintering {ts_a}C'

    if decomposition_conflict:
        score = 0.15
        details['assessment'] = 'one material decomposes before the other sinters'
    elif temp_diff < 100:
        score = 0.95
        details['assessment'] = 'excellent sintering window overlap'
    elif temp_diff < 250:
        score = 0.80
        details['assessment'] = 'good sintering window overlap'
    elif temp_diff < 500:
        score = 0.60
        details['assessment'] = 'moderate sintering window gap'
    elif temp_diff < 800:
        score = 0.40
        details['assessment'] = 'large sintering window gap'
    else:
        score = 0.20
        details['assessment'] = 'extreme sintering temperature mismatch'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='sintering_compatibility', details=details)


# =============================================================================
# 2. CTE MATCH SCORE
# =============================================================================
# Thermal expansion mismatch -> interfacial stress on cooling -> cracking.

def score_cte_match(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> ScorerResult:
    """
    Score thermal expansion compatibility between two ceramics.

    CTE mismatch is the primary cause of cracking in ceramic composites
    and multilayer structures during cooling from sintering temperature.

    CTE mismatch interpretation:
        delta < 1 x10^-6/K: negligible
        1-3: manageable with design
        3-5: significant (requires graded interfaces)
        5-10: severe (cracking likely)
        > 10: extreme (incompatible)

    Args:
        material_a: First ceramic
        material_b: Second ceramic

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    cte_a = material_a.cte_per_K
    cte_b = material_b.cte_per_K

    if cte_a is None or cte_b is None:
        details['note'] = 'CTE not available'
        return ScorerResult(score=0.5, label='cte_match', details=details)

    cte_diff = abs(cte_a - cte_b)
    cte_ratio = max(cte_a, cte_b) / max(min(cte_a, cte_b), 0.1)

    details['cte_a'] = cte_a
    details['cte_b'] = cte_b
    details['cte_difference'] = round(cte_diff, 1)
    details['cte_ratio'] = round(cte_ratio, 2)

    if cte_diff < 1.0:
        score = 0.95
        details['assessment'] = 'negligible CTE mismatch'
    elif cte_diff < 3.0:
        score = 0.80 - (cte_diff - 1.0) * 0.05
        details['assessment'] = 'manageable CTE mismatch'
    elif cte_diff < 5.0:
        score = 0.65 - (cte_diff - 3.0) * 0.075
        details['assessment'] = 'significant CTE mismatch (graded interface recommended)'
    elif cte_diff < 10.0:
        score = 0.45 - (cte_diff - 5.0) * 0.05
        details['assessment'] = 'severe CTE mismatch (cracking likely)'
    else:
        score = max(0.05, 0.20 - (cte_diff - 10.0) * 0.02)
        details['assessment'] = 'extreme CTE mismatch (incompatible)'

    # Additional penalty for extreme ratios
    if cte_ratio > 10.0:
        score *= 0.5
        details['ratio_note'] = f'extreme CTE ratio {cte_ratio:.1f}x'
    elif cte_ratio > 5.0:
        score *= 0.7
        details['ratio_note'] = f'large CTE ratio {cte_ratio:.1f}x'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='cte_match', details=details)


# =============================================================================
# 3. MECHANICAL COMPATIBILITY SCORE
# =============================================================================

def score_mechanical_compatibility(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> ScorerResult:
    """
    Score mechanical compatibility between two ceramics.

    Factors:
    - Elastic modulus mismatch: stress concentration at interface
    - Hardness mismatch: abrasive wear at interface
    - Fracture toughness mismatch: crack arrest vs propagation
    - Flexural strength ratio

    Args:
        material_a: First ceramic
        material_b: Second ceramic

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

        if mod_ratio > 15:
            score *= 0.3
            details['modulus_assessment'] = 'extreme modulus mismatch'
        elif mod_ratio > 8:
            score *= 0.5
            details['modulus_assessment'] = 'large modulus mismatch'
        elif mod_ratio > 4:
            score *= 0.7
            details['modulus_assessment'] = 'moderate modulus mismatch'
        elif mod_ratio > 2:
            score *= 0.85
            details['modulus_assessment'] = 'mild modulus mismatch'

    # --- Hardness mismatch ---
    h_a = material_a.hardness_HV
    h_b = material_b.hardness_HV

    if h_a is not None and h_b is not None and h_a > 0 and h_b > 0:
        h_ratio = max(h_a, h_b) / min(h_a, h_b)
        details['hardness_ratio'] = round(h_ratio, 2)

        if h_ratio > 10:
            score *= 0.6
            details['hardness_assessment'] = 'extreme hardness mismatch (abrasion risk)'
        elif h_ratio > 5:
            score *= 0.75
            details['hardness_assessment'] = 'large hardness mismatch'
        elif h_ratio > 3:
            score *= 0.9
            details['hardness_assessment'] = 'moderate hardness mismatch'

    # --- Fracture toughness mismatch ---
    kic_a = material_a.fracture_toughness_MPa_m05
    kic_b = material_b.fracture_toughness_MPa_m05

    if kic_a is not None and kic_b is not None and kic_a > 0 and kic_b > 0:
        kic_ratio = max(kic_a, kic_b) / min(kic_a, kic_b)
        details['toughness_ratio'] = round(kic_ratio, 2)

        if kic_ratio > 10:
            score *= 0.6
            details['toughness_assessment'] = 'extreme toughness mismatch'
        elif kic_ratio > 5:
            score *= 0.75
            details['toughness_assessment'] = 'large toughness mismatch'
        elif kic_ratio > 3:
            score *= 0.9
            details['toughness_assessment'] = 'moderate toughness mismatch'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 4. CHEMICAL COMPATIBILITY SCORE
# =============================================================================
# Phase reactions, crystal structure match, solid solution potential.

# Known reactive pairs (form new phases at interface during sintering)
_REACTIVE_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('Al2O3', 'SiO2'): (0.2, 'Forms mullite (3Al2O3-2SiO2) at >1500C'),
    ('SiO2', 'Al2O3'): (0.2, 'Forms mullite (3Al2O3-2SiO2) at >1500C'),
    ('MgO', 'SiO2'): (0.5, 'Forms forsterite (Mg2SiO4) at >1200C'),
    ('SiO2', 'MgO'): (0.5, 'Forms forsterite (Mg2SiO4) at >1200C'),
    ('MgO', 'Al2O3'): (-0.10, 'Forms spinel (MgAl2O4); beneficial reaction product (Kingery 1976)'),
    ('Al2O3', 'MgO'): (-0.10, 'Forms spinel (MgAl2O4); beneficial reaction product (Kingery 1976)'),
    ('SiC', 'Al2O3'): (0.3, 'SiC oxidizes at Al2O3 sintering temps; interface reaction'),
    ('Al2O3', 'SiC'): (0.3, 'SiC oxidizes at Al2O3 sintering temps; interface reaction'),
}

# Known compatible pairs (same crystal family, similar bonding, or
# established composites that tolerate CTE mismatch)
_COMPATIBLE_PAIRS: Set[Tuple[str, str]] = {
    ('Al2O3', 'ZrO2'), ('ZrO2', 'Al2O3'),
    ('Si3N4', 'SiC'), ('SiC', 'Si3N4'),
    ('Al2O3', 'Mullite'), ('Mullite', 'Al2O3'),
    ('Al2O3', 'Spinel'), ('Spinel', 'Al2O3'),
    ('Al2O3', 'TiN'), ('TiN', 'Al2O3'),
    ('WC', 'TiC'), ('TiC', 'WC'),
    ('Hydroxyapatite', 'TCP'), ('TCP', 'Hydroxyapatite'),
    # Wei & Becher, J. Am. Ceram. Soc. 1984 — SiC whisker-reinforced Al2O3
    ('Al2O3', 'SiC'), ('SiC', 'Al2O3'),
    # Jaffe et al., Piezoelectric Ceramics 1971 — multilayer piezo stacks
    ('BaTiO3', 'PZT'), ('PZT', 'BaTiO3'),
    # Kingery, Introduction to Ceramics 1976 — forms MgAl2O4 spinel
    ('MgO', 'Al2O3'), ('Al2O3', 'MgO'),
}


def _get_base_formula(material: CeramicMaterial) -> str:
    """Extract simplified key for pair lookups."""
    # Use the dict key name if it matches, otherwise use formula
    for name, mat in _all_ceramics_cache().items():
        if mat is material:
            return name
    return material.formula


def _all_ceramics_cache():
    """Lazy import to avoid circular dependency."""
    from ceramic_bridge.material_properties import ALL_CERAMICS
    return ALL_CERAMICS


def score_chemical_compatibility(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> ScorerResult:
    """
    Score chemical compatibility between two ceramics.

    Factors:
    - Known reactive pairs (phase reactions at interface)
    - Known compatible pairs (solid solution, no reaction)
    - Crystal structure match
    - Same ceramic class bonus
    - Chemical stability match

    Args:
        material_a: First ceramic
        material_b: Second ceramic

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 0.7  # Default: moderate compatibility
    details = {}

    key_a = _get_base_formula(material_a)
    key_b = _get_base_formula(material_b)
    details['key_a'] = key_a
    details['key_b'] = key_b

    # --- Same ceramic class = bonus ---
    if material_a.ceramic_class == material_b.ceramic_class:
        score = 0.85
        details['class_match'] = True
    else:
        details['class_match'] = False

    # --- Crystal structure match ---
    cs_a = material_a.crystal_system
    cs_b = material_b.crystal_system
    details['crystal_a'] = cs_a.value
    details['crystal_b'] = cs_b.value

    if cs_a == cs_b and cs_a != CrystalSystem.AMORPHOUS and cs_a != CrystalSystem.MIXED:
        score = min(1.0, score + 0.1)
        details['crystal_match'] = 'same crystal system (favorable)'
    elif CrystalSystem.AMORPHOUS in {cs_a, cs_b}:
        # Glass + crystalline is generally harder to bond
        score *= 0.85
        details['crystal_match'] = 'amorphous + crystalline (limited compatibility)'

    # --- Known reactive pairs (PENALTY) ---
    pair = (key_a, key_b)
    if pair in _REACTIVE_PAIRS:
        penalty, reason = _REACTIVE_PAIRS[pair]
        score *= (1.0 - penalty)
        details['reactive_pair'] = reason

    # --- Known compatible pairs (BONUS) ---
    if pair in _COMPATIBLE_PAIRS:
        score = min(1.0, score + 0.15)
        details['compatible_pair'] = f'{key_a} + {key_b} known compatible composite'

    # --- Chemical stability mismatch ---
    stab_a = material_a.chemical_stability
    stab_b = material_b.chemical_stability
    if stab_a and stab_b:
        stability_order = {'inert': 3, 'stable': 2, 'reactive': 1, 'hygroscopic': 0}
        diff = abs(stability_order.get(stab_a, 1) - stability_order.get(stab_b, 1))
        if diff >= 3:
            score *= 0.6
            details['stability_mismatch'] = f'{stab_a} + {stab_b}: large stability gap'
        elif diff >= 2:
            score *= 0.8
            details['stability_mismatch'] = f'{stab_a} + {stab_b}: moderate stability gap'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='chemical_compatibility', details=details)


# =============================================================================
# 5. DEGRADATION PENALTY
# =============================================================================

# Known problematic pairings
_KNOWN_BAD_CERAMIC_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('LGPS', 'Al2O3'): (0.6, 'LGPS decomposes with oxide ceramics at elevated temp'),
    ('Al2O3', 'LGPS'): (0.6, 'LGPS decomposes with oxide ceramics at elevated temp'),
    ('LGPS', 'ZrO2_YSZ'): (0.6, 'Sulfide-oxide interface reaction'),
    ('ZrO2_YSZ', 'LGPS'): (0.6, 'Sulfide-oxide interface reaction'),
    ('Li3PS4', 'Al2O3'): (0.5, 'Sulfide SE degrades with oxide ceramic'),
    ('Al2O3', 'Li3PS4'): (0.5, 'Sulfide SE degrades with oxide ceramic'),
    ('BN_hex', 'Soda_Lime'): (0.4, 'No bonding mechanism; CTE and modulus mismatch'),
    ('Soda_Lime', 'BN_hex'): (0.4, 'No bonding mechanism; CTE and modulus mismatch'),
    ('BN_hex', 'SiO2'): (0.9, 'BN-silica direct interface lacks bonding mechanism; nitride/oxide thermal and chemical mismatch'),
    ('SiO2', 'BN_hex'): (0.9, 'BN-silica direct interface lacks bonding mechanism; nitride/oxide thermal and chemical mismatch'),
    ('BN_hex', 'Borosilicate'): (0.9, 'BN-borosilicate direct interface lacks bonding mechanism without engineered interlayer'),
    ('Borosilicate', 'BN_hex'): (0.9, 'BN-borosilicate direct interface lacks bonding mechanism without engineered interlayer'),
    # ZrO2_YSZ + MgO: MgO destabilizes YSZ tetragonal phase (ASM Handbook)
    ('ZrO2_YSZ', 'MgO'): (0.9, 'MgO destabilizes YSZ tetragonal phase; grain boundary segregation'),
    ('MgO', 'ZrO2_YSZ'): (0.9, 'MgO destabilizes YSZ tetragonal phase; grain boundary segregation'),
    # B4C + Al2O3: interface reaction above 1600C (Thevenot, J. Eur. Ceram. Soc. 1990)
    ('B4C', 'Al2O3'): (0.9, 'B4C-Al2O3 interface reaction at sintering temps >1600C'),
    ('Al2O3', 'B4C'): (0.9, 'B4C-Al2O3 interface reaction at sintering temps >1600C'),
    # NASICON + Li3PS4: oxide-sulfide SE interface (Janek & Zeier, Nat. Energy 2016)
    ('NASICON', 'Li3PS4'): (0.9, 'Oxide-sulfide solid electrolyte interface; high impedance'),
    ('Li3PS4', 'NASICON'): (0.9, 'Oxide-sulfide solid electrolyte interface; high impedance'),
}


def score_degradation_penalty(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> ScorerResult:
    """
    Apply degradation penalty for known problematic ceramic pairings.

    Factors:
    - Known bad pairing lookup
    - Shared failure mode vulnerabilities
    - Hygroscopic material penalty
    - Thermal shock susceptibility of pair

    Args:
        material_a: First ceramic
        material_b: Second ceramic

    Returns:
        ScorerResult with score in [0, 1] (1 = no degradation concerns)
    """
    penalty = 0.0
    reasons = []

    key_a = _get_base_formula(material_a)
    key_b = _get_base_formula(material_b)

    # --- Known bad pairings lookup ---
    for key in [(key_a, key_b), (key_b, key_a)]:
        if key in _KNOWN_BAD_CERAMIC_PAIRS:
            p, reason = _KNOWN_BAD_CERAMIC_PAIRS[key]
            penalty = max(penalty, p)
            reasons.append(reason)
            break

    # --- Shared critical failure modes ---
    shared_failures = set(material_a.failure_modes) & set(material_b.failure_modes)
    critical_shared = shared_failures & {
        CeramicFailureMode.HYDROLYSIS,
        CeramicFailureMode.DECOMPOSITION,
        CeramicFailureMode.PHASE_TRANSFORMATION,
    }
    if critical_shared:
        penalty = max(penalty, 0.1 * len(critical_shared))
        reasons.append(f'Shared vulnerabilities: {[f.value for f in critical_shared]}')

    # --- Hygroscopic material ---
    for mat in [material_a, material_b]:
        if mat.chemical_stability == 'hygroscopic':
            penalty = max(penalty, 0.2)
            reasons.append(f'{mat.formula}: hygroscopic (moisture degrades interface)')

    # --- Both thermal shock susceptible ---
    ts_susceptible = sum(
        1 for mat in [material_a, material_b]
        if CeramicFailureMode.THERMAL_SHOCK in mat.failure_modes
    )
    if ts_susceptible == 2:
        penalty = max(penalty, 0.15)
        reasons.append('Both materials susceptible to thermal shock')

    # --- Reactive chemical stability ---
    reactive_count = sum(
        1 for mat in [material_a, material_b]
        if mat.chemical_stability == 'reactive'
    )
    if reactive_count == 2:
        penalty = max(penalty, 0.25)
        reasons.append('Both materials chemically reactive')

    score = max(0.0, 1.0 - penalty)
    details = {
        'penalty': round(penalty, 2),
        'reasons': reasons if reasons else ['No known degradation concerns'],
    }

    return ScorerResult(score=score, label='degradation_penalty', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(
    material_a: CeramicMaterial,
    material_b: CeramicMaterial,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a ceramic pair.

    Args:
        material_a: First ceramic
        material_b: Second ceramic

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'sintering_compatibility': score_sintering_compatibility(material_a, material_b),
        'cte_match': score_cte_match(material_a, material_b),
        'mechanical_compatibility': score_mechanical_compatibility(material_a, material_b),
        'chemical_compatibility': score_chemical_compatibility(material_a, material_b),
        'degradation_penalty': score_degradation_penalty(material_a, material_b),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("Ceramic Interaction Scoring - Demo")
    print("=" * 70)
    print()

    # Good pair: Al2O3 + ZrO2
    a = get_ceramic('Al2O3')
    b = get_ceramic('ZrO2_YSZ')
    print(f"Pair: {a.formula} <-> {b.formula} (known good composite)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
    print()

    # Bad pair: LGPS + Al2O3
    a = get_ceramic('LGPS')
    b = get_ceramic('Al2O3')
    print(f"Pair: {a.formula} <-> {b.formula} (incompatible)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}  {result.details}")
