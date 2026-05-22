# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Glass Interaction Scoring
============================

Five compatibility scorers for glass interface/assembly assessment,
analogous to ceramic_bridge/interaction_scoring.py.

Each scorer takes two GlassMaterial objects and returns a float in [0, 1].

Scorer Mapping (ceramic bridge -> glass bridge):
---------------------------------------------------
Sintering compat.   -> Viscosity compatibility (working/sealing temp overlap)
CTE match            -> Thermal expansion match (CTE mismatch -> stress)
Mechanical compat.   -> Mechanical compatibility (modulus, toughness match)
Chemical compat.     -> Chemical compatibility (durability match, composition)
Degradation penalty  -> Degradation penalty (known failures, environment)

References:
-----------
- Shelby, "Introduction to Glass Science and Technology", 2nd ed., 2005
- Varshneya, "Fundamentals of Inorganic Glasses", 2nd ed., 2006
- Schott Technical Information TI-43, "Glass-to-Glass and Glass-to-Metal Sealing"
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from glass_bridge.material_properties import (
    GlassMaterial, GlassClass, GlassFailureMode, CompositionType,
    get_glass,
)


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# 1. THERMAL EXPANSION MATCH SCORE
# =============================================================================
# CTE mismatch is the primary cause of seal failure and cracking.
# For glass-to-glass seals, the critical threshold is typically +/- 5% CTE match.

def score_thermal_expansion_match(
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> ScorerResult:
    """
    Score thermal expansion compatibility between two glasses.

    CTE mismatch generates interfacial stress upon cooling from sealing
    temperature. Standard glass-to-glass seals require < 10% CTE difference.

    CTE mismatch interpretation:
        < 5%:   excellent (matched seal)
        5-10%:  good (compression seal acceptable)
        10-20%: moderate (graded seal needed)
        20-50%: poor (intermediate glass required)
        > 50%:  incompatible

    Also considers absolute CTE difference (x10^-6/K):
        < 0.5:  negligible
        0.5-1.5: manageable
        1.5-3.0: significant
        3.0-6.0: large
        > 6.0:  extreme

    Args:
        material_a: First glass
        material_b: Second glass

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {}

    cte_a = material_a.cte_per_K
    cte_b = material_b.cte_per_K

    if cte_a is None or cte_b is None:
        details['note'] = 'CTE not available'
        return ScorerResult(score=0.5, label='thermal_expansion_match', details=details)

    cte_diff = abs(cte_a - cte_b)
    cte_avg = (cte_a + cte_b) / 2.0
    cte_pct_diff = (cte_diff / max(cte_avg, 0.01)) * 100.0

    details['cte_a'] = cte_a
    details['cte_b'] = cte_b
    details['cte_difference'] = round(cte_diff, 2)
    details['cte_pct_difference'] = round(cte_pct_diff, 1)

    # Score based on absolute difference
    if cte_diff < 0.5:
        score = 0.98
        details['assessment'] = 'negligible CTE mismatch (matched seal)'
    elif cte_diff < 1.5:
        score = 0.85
        details['assessment'] = 'good CTE match'
    elif cte_diff < 3.0:
        score = 0.70
        details['assessment'] = 'moderate CTE mismatch (compression seal may work)'
    elif cte_diff < 6.0:
        score = 0.45
        details['assessment'] = 'large CTE mismatch (graded seal needed)'
    elif cte_diff < 10.0:
        score = 0.25
        details['assessment'] = 'severe CTE mismatch (intermediate glass required)'
    else:
        score = max(0.05, 0.15 - (cte_diff - 10) * 0.01)
        details['assessment'] = 'extreme CTE mismatch (incompatible)'

    # Percentage-based check: enforce documented thresholds (lines 65-70)
    # Only applied when absolute diff is significant (>= 2.0 x10^-6/K),
    # since ultra-low CTE pairs (Zerodur + FusedSilica) have high % but tiny absolute diff
    if cte_diff >= 2.0:
        if cte_pct_diff > 50:
            score = min(score, 0.15)
            details['pct_penalty'] = f'{cte_pct_diff:.0f}% CTE difference exceeds 50% incompatibility threshold'
        elif cte_pct_diff > 30:
            score = min(score, 0.30)
            details['pct_penalty'] = f'{cte_pct_diff:.0f}% CTE difference exceeds 30% threshold'

    # Additional penalty for extreme ratios (only meaningful when CTEs > 1.0)
    if cte_avg > 1.0:
        cte_ratio = max(cte_a, cte_b) / max(min(cte_a, cte_b), 0.01)
        if cte_ratio > 20:
            score *= 0.4
            details['ratio_note'] = f'extreme CTE ratio {cte_ratio:.0f}x'
        elif cte_ratio > 10:
            score *= 0.6
            details['ratio_note'] = f'large CTE ratio {cte_ratio:.0f}x'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='thermal_expansion_match', details=details)


# =============================================================================
# 2. VISCOSITY COMPATIBILITY SCORE
# =============================================================================
# Can these glasses be sealed/fused together? Working temperature overlap.

def score_viscosity_compatibility(
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> ScorerResult:
    """
    Score viscosity (working temperature) compatibility between two glasses.

    For glass-to-glass sealing, both materials must be workable at a
    common temperature. If one glass is already rigid while the other
    is still fluid, sealing is impossible.

    Uses softening point as primary indicator (viscosity = 10^7.6 poise).

    Args:
        material_a: First glass
        material_b: Second glass

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {}

    # Use softening point as primary, fall back to Tg
    sp_a = material_a.softening_point_C or material_a.Tg_C
    sp_b = material_b.softening_point_C or material_b.Tg_C

    if sp_a is None or sp_b is None:
        details['note'] = 'Softening point not available'
        return ScorerResult(score=0.5, label='viscosity_compatibility', details=details)

    details['softening_a_C'] = sp_a
    details['softening_b_C'] = sp_b

    sp_diff = abs(sp_a - sp_b)
    details['softening_diff_C'] = round(sp_diff, 0)

    # Check if one glass's softening point is far below the other's Tg
    # (meaning one is fully rigid while the other is barely softening)
    tg_a = material_a.Tg_C
    tg_b = material_b.Tg_C

    severe_conflict = False
    if tg_a and tg_b:
        if sp_a < tg_b - 100:
            severe_conflict = True
            details['conflict'] = (f'{material_a.formula} softens at {sp_a}C, '
                                   f'but {material_b.formula} Tg={tg_b}C (still rigid)')
        if sp_b < tg_a - 100:
            severe_conflict = True
            details['conflict'] = (f'{material_b.formula} softens at {sp_b}C, '
                                   f'but {material_a.formula} Tg={tg_a}C (still rigid)')

    if severe_conflict:
        score = 0.15
        details['assessment'] = 'severe viscosity conflict (no common working range)'
    elif sp_diff < 50:
        score = 0.95
        details['assessment'] = 'excellent viscosity overlap'
    elif sp_diff < 150:
        score = 0.80
        details['assessment'] = 'good viscosity overlap'
    elif sp_diff < 300:
        score = 0.60
        details['assessment'] = 'moderate viscosity gap'
    elif sp_diff < 500:
        score = 0.40
        details['assessment'] = 'large viscosity gap'
    elif sp_diff < 800:
        score = 0.25
        details['assessment'] = 'very large viscosity gap'
    else:
        score = 0.10
        details['assessment'] = 'extreme viscosity mismatch'

    # Composition type compatibility
    ct_a = material_a.composition_type
    ct_b = material_b.composition_type
    if ct_a != ct_b:
        # Different glass networks are harder to seal
        incompatible_combos = {
            frozenset({CompositionType.CHALCOGENIDE, CompositionType.SILICATE}),
            frozenset({CompositionType.FLUORIDE, CompositionType.SILICATE}),
            frozenset({CompositionType.CHALCOGENIDE, CompositionType.FLUORIDE}),
        }
        if frozenset({ct_a, ct_b}) in incompatible_combos:
            score *= 0.4
            details['composition_note'] = f'{ct_a.value} + {ct_b.value}: incompatible glass networks'
        else:
            score *= 0.8
            details['composition_note'] = f'{ct_a.value} + {ct_b.value}: different networks'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='viscosity_compatibility', details=details)


# =============================================================================
# 3. MECHANICAL COMPATIBILITY SCORE
# =============================================================================

def score_mechanical_compatibility(
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> ScorerResult:
    """
    Score mechanical compatibility between two glasses.

    Factors:
    - Elastic modulus mismatch: stress concentration at interface
    - Fracture toughness mismatch: crack initiation at interface
    - Hardness mismatch: abrasion at contact surfaces

    Args:
        material_a: First glass
        material_b: Second glass

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

        if mod_ratio > 5:
            score *= 0.4
            details['modulus_assessment'] = 'extreme modulus mismatch'
        elif mod_ratio > 3:
            score *= 0.6
            details['modulus_assessment'] = 'large modulus mismatch'
        elif mod_ratio > 2:
            score *= 0.8
            details['modulus_assessment'] = 'moderate modulus mismatch'
        elif mod_ratio > 1.5:
            score *= 0.9
            details['modulus_assessment'] = 'mild modulus mismatch'

    # --- Fracture toughness mismatch ---
    kic_a = material_a.fracture_toughness_MPa_m05
    kic_b = material_b.fracture_toughness_MPa_m05

    if kic_a is not None and kic_b is not None and kic_a > 0 and kic_b > 0:
        kic_ratio = max(kic_a, kic_b) / min(kic_a, kic_b)
        details['toughness_ratio'] = round(kic_ratio, 2)

        if kic_ratio > 3:
            score *= 0.6
            details['toughness_assessment'] = 'large toughness mismatch'
        elif kic_ratio > 2:
            score *= 0.8
            details['toughness_assessment'] = 'moderate toughness mismatch'

    # --- Hardness mismatch ---
    h_a = material_a.hardness_HK
    h_b = material_b.hardness_HK

    if h_a is not None and h_b is not None and h_a > 0 and h_b > 0:
        h_ratio = max(h_a, h_b) / min(h_a, h_b)
        details['hardness_ratio'] = round(h_ratio, 2)

        if h_ratio > 4:
            score *= 0.6
            details['hardness_assessment'] = 'large hardness mismatch (abrasion risk)'
        elif h_ratio > 2.5:
            score *= 0.8
            details['hardness_assessment'] = 'moderate hardness mismatch'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 4. CHEMICAL COMPATIBILITY SCORE
# =============================================================================

# Known compatible pairs (standard glass combinations in industry)
_COMPATIBLE_PAIRS: Set[Tuple[str, str]] = {
    ('BK7', 'F2'), ('F2', 'BK7'),
    ('BK7', 'LAK9'), ('LAK9', 'BK7'),
    ('FusedSilica', 'BK7'), ('BK7', 'FusedSilica'),
    ('FusedSilica', 'QuartzGlass'), ('QuartzGlass', 'FusedSilica'),
    ('Boro_33', 'Boro_51'), ('Boro_51', 'Boro_33'),
    ('Boro_33', 'Boro_Neutral'), ('Boro_Neutral', 'Boro_33'),
    ('SodaLime_Float', 'SodaLime_Container'), ('SodaLime_Container', 'SodaLime_Float'),
    ('SodaLime_Float', 'SodaLime_Tempered'), ('SodaLime_Tempered', 'SodaLime_Float'),
    ('LAS_Zerodur', 'FusedSilica'), ('FusedSilica', 'LAS_Zerodur'),
    ('Bioglass_45S5', 'S53P4'), ('S53P4', 'Bioglass_45S5'),
    ('As2S3', 'Ge28Sb12Se60'), ('Ge28Sb12Se60', 'As2S3'),
}

# Known problematic pairs
_INCOMPATIBLE_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('As2S3', 'Boro_33'): (0.5, 'Chalcogenide + oxide glass: incompatible chemistry and CTE'),
    ('Boro_33', 'As2S3'): (0.5, 'Chalcogenide + oxide glass: incompatible chemistry'),
    ('ZBLAN', 'SodaLime_Float'): (0.4, 'Fluoride + silicate: no miscibility; incompatible working temps'),
    ('SodaLime_Float', 'ZBLAN'): (0.4, 'Fluoride + silicate incompatible'),
    ('Bioglass_45S5', 'FusedSilica'): (0.3, 'Bioglass designed to dissolve; extreme CTE mismatch'),
    ('FusedSilica', 'Bioglass_45S5'): (0.3, 'Extreme CTE and durability mismatch'),
    ('As2S3', 'FusedSilica'): (0.5, 'Chalcogenide + fused silica: incompatible networks'),
    ('FusedSilica', 'As2S3'): (0.5, 'Incompatible glass networks'),
    ('SodaLime_Float', 'Boro_33'): (0.7, 'Soda-lime + borosilicate: 93% CTE mismatch (9.0 vs 3.3); seal will crack'),
    ('Boro_33', 'SodaLime_Float'): (0.7, 'Borosilicate + soda-lime: 93% CTE mismatch; incompatible for sealing'),
}


def score_chemical_compatibility(
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> ScorerResult:
    """
    Score chemical compatibility between two glasses.

    Factors:
    - Same glass class bonus
    - Same composition type bonus
    - Known compatible/incompatible pairs
    - Chemical durability match

    Args:
        material_a: First glass
        material_b: Second glass

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 0.7  # default: moderate compatibility
    details = {}

    key_a = _get_glass_key(material_a)
    key_b = _get_glass_key(material_b)
    details['key_a'] = key_a
    details['key_b'] = key_b

    # --- Same glass class = bonus ---
    if material_a.glass_class == material_b.glass_class:
        score = 0.90
        details['class_match'] = True
    else:
        details['class_match'] = False

    # --- Same composition type = bonus ---
    if material_a.composition_type == material_b.composition_type:
        score = min(1.0, score + 0.05)
        details['composition_match'] = True
    else:
        details['composition_match'] = False

    # --- Known compatible pairs (BONUS) ---
    pair = (key_a, key_b)
    if pair in _COMPATIBLE_PAIRS:
        score = min(1.0, score + 0.10)
        details['compatible_pair'] = f'{key_a} + {key_b} standard compatible combination'

    # --- Known incompatible pairs (PENALTY) ---
    if pair in _INCOMPATIBLE_PAIRS:
        penalty, reason = _INCOMPATIBLE_PAIRS[pair]
        score *= (1.0 - penalty)
        details['incompatible_pair'] = reason

    # --- Chemical durability match ---
    hc_a = material_a.hydrolytic_class
    hc_b = material_b.hydrolytic_class
    if hc_a is not None and hc_b is not None:
        durability_diff = abs(hc_a - hc_b)
        details['hydrolytic_class_a'] = hc_a
        details['hydrolytic_class_b'] = hc_b
        if durability_diff >= 3:
            score *= 0.6
            details['durability_note'] = f'extreme durability mismatch (classes {hc_a} vs {hc_b})'
        elif durability_diff >= 2:
            score *= 0.8
            details['durability_note'] = f'moderate durability mismatch (classes {hc_a} vs {hc_b})'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='chemical_compatibility', details=details)


def _get_glass_key(material: GlassMaterial) -> str:
    """Extract simplified key for pair lookups."""
    for name, mat in _all_glasses_cache().items():
        if mat is material:
            return name
    return material.formula


def _all_glasses_cache():
    """Lazy import to avoid circular dependency."""
    from glass_bridge.material_properties import ALL_GLASSES
    return ALL_GLASSES


# =============================================================================
# 5. DEGRADATION PENALTY
# =============================================================================

_KNOWN_BAD_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('As2S3', 'Boro_33'): (0.5, 'Chalcogenide corrodes oxide glass at sealing temps'),
    ('Boro_33', 'As2S3'): (0.5, 'Chalcogenide corrodes oxide glass'),
    ('ZBLAN', 'SodaLime_Float'): (0.5, 'Fluoride + silicate: chemical attack; crystallization'),
    ('SodaLime_Float', 'ZBLAN'): (0.5, 'Fluoride + silicate incompatible'),
    ('LaserPhosphate', 'SodaLime_Float'): (0.3, 'Phosphate glass poor durability + soda-lime alkali leaching'),
    ('SodaLime_Float', 'LaserPhosphate'): (0.3, 'Both have durability concerns'),
    ('SodaLime_Float', 'Boro_33'): (0.4, 'CTE mismatch 93% (9.0 vs 3.3 x10^-6/K); seal cracks on cooling'),
    ('Boro_33', 'SodaLime_Float'): (0.4, 'CTE mismatch 93%; borosilicate-soda lime seal incompatible'),
}


def score_degradation_penalty(
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> ScorerResult:
    """
    Apply degradation penalty for known problematic glass pairings.

    Factors:
    - Known bad pairing lookup
    - Shared failure mode vulnerabilities
    - Weathering/hydrolytic susceptibility
    - Crystallization risk

    Args:
        material_a: First glass
        material_b: Second glass

    Returns:
        ScorerResult with score in [0, 1] (1 = no degradation concerns)
    """
    penalty = 0.0
    reasons = []

    key_a = _get_glass_key(material_a)
    key_b = _get_glass_key(material_b)

    # --- Known bad pairings lookup ---
    for key in [(key_a, key_b), (key_b, key_a)]:
        if key in _KNOWN_BAD_PAIRS:
            p, reason = _KNOWN_BAD_PAIRS[key]
            penalty = max(penalty, p)
            reasons.append(reason)
            break

    # --- Shared critical failure modes ---
    shared_failures = set(material_a.failure_modes) & set(material_b.failure_modes)
    critical_shared = shared_failures & {
        GlassFailureMode.DEVITRIFICATION,
        GlassFailureMode.CRYSTALLIZATION,
        GlassFailureMode.HYDROLYTIC_ATTACK,
    }
    if critical_shared:
        penalty = max(penalty, 0.1 * len(critical_shared))
        reasons.append(f'Shared vulnerabilities: {[f.value for f in critical_shared]}')

    # --- Weathering susceptibility ---
    for mat in [material_a, material_b]:
        if GlassFailureMode.WEATHERING in mat.failure_modes:
            penalty = max(penalty, 0.15)
            reasons.append(f'{mat.formula}: weathering susceptible')

    # --- Poor hydrolytic resistance ---
    for mat in [material_a, material_b]:
        if mat.hydrolytic_class is not None and mat.hydrolytic_class >= 4:
            penalty = max(penalty, 0.2)
            reasons.append(f'{mat.formula}: poor hydrolytic resistance (class {mat.hydrolytic_class})')

    # --- Both alkali-leaching prone ---
    leaching_count = sum(
        1 for mat in [material_a, material_b]
        if GlassFailureMode.ALKALI_LEACHING in mat.failure_modes
    )
    if leaching_count == 2:
        penalty = max(penalty, 0.15)
        reasons.append('Both glasses prone to alkali leaching')

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
    material_a: GlassMaterial,
    material_b: GlassMaterial,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a glass pair.

    Args:
        material_a: First glass
        material_b: Second glass

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'thermal_expansion_match': score_thermal_expansion_match(material_a, material_b),
        'viscosity_compatibility': score_viscosity_compatibility(material_a, material_b),
        'mechanical_compatibility': score_mechanical_compatibility(material_a, material_b),
        'chemical_compatibility': score_chemical_compatibility(material_a, material_b),
        'degradation_penalty': score_degradation_penalty(material_a, material_b),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("Glass Interaction Scoring - Demo")
    print("=" * 70)
    print()

    # Good pair: BK7 + F2 (achromatic doublet)
    a = get_glass('BK7')
    b = get_glass('F2')
    print(f"Pair: {a.name} <-> {b.name} (achromatic doublet)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
    print()

    # Bad pair: Fused Silica + Soda-Lime
    a = get_glass('FusedSilica')
    b = get_glass('SodaLime_Float')
    print(f"Pair: {a.name} <-> {b.name} (CTE mismatch)")
    results = score_all(a, b)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
