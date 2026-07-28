# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Polymer Interaction Scoring
==============================

Five compatibility scorers for polymer blend/interface assessment,
analogous to battery_bridge/interaction_scoring.py.

Each scorer takes two PolymerMaterial objects and returns a float in [0, 1].

Scorer Mapping (battery bridge -> polymer bridge):
---------------------------------------------------
Ion transport          -> Solubility compatibility (Hansen/chi)
Electrochemical stab.  -> Thermal compatibility (Tg/Tm/processing)
Interface compat.      -> Chemical resistance
Mechanical compat.     -> Mechanical compatibility
Degradation penalty    -> Aging penalty

References:
-----------
- Hansen, HSP Handbook 2nd ed., CRC 2007
- Flory, Principles of Polymer Chemistry, 1953
- Van Krevelen, Properties of Polymers 4th ed., 2009
- Paul & Bucknall, Polymer Blends, 2000
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from polymer_bridge.material_properties import (
    PolymerMaterial, PolymerClass, PolymerFailureMode, PolymerStructure,
    HansenParameters, get_polymer,
)
from polymer_bridge.flory_huggins import assess_flory_huggins


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# 1. SOLUBILITY COMPATIBILITY SCORE
# =============================================================================
# Analogous to battery ion transport: "Can these mix at all?"
# For polymers: Hansen distance and Flory-Huggins chi parameter.

def score_solubility_compatibility(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> ScorerResult:
    """
    Score solubility/miscibility compatibility between two polymers.

    Uses Hansen solubility parameter distance (Ra) as primary metric.
    Falls back to Flory-Huggins chi parameter if available.

    Hansen distance interpretation:
        Ra < 4:   likely miscible/compatible
        4 < Ra < 8: marginal (may need compatibilizer)
        Ra > 8:   likely immiscible

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 0.5  # Default when no data
    details = {}

    # --- Flory-Huggins chi parameter with chain-length critical chi ---
    fh = assess_flory_huggins(material_a, material_b)
    if fh.chi is not None:
        details['chi_parameter'] = round(fh.chi, 6)
        details['chi_source'] = fh.chi_source
        details['chi_c'] = round(fh.critical_chi, 6) if fh.critical_chi is not None else None
        details['degree_polymerization_a'] = (
            round(fh.degree_polymerization_a, 1)
            if fh.degree_polymerization_a is not None else None
        )
        details['degree_polymerization_b'] = (
            round(fh.degree_polymerization_b, 1)
            if fh.degree_polymerization_b is not None else None
        )
        details['flory_huggins_reason'] = fh.reason

        if fh.miscible is True:
            if fh.chi < 0:
                score = min(1.0, 0.95 + abs(fh.chi) * 0.05)
                details['chi_interpretation'] = 'miscible (negative chi = favorable interaction)'
            elif fh.critical_chi and fh.critical_chi > 0:
                ratio = fh.chi / fh.critical_chi
                score = max(0.70, 0.95 - 0.20 * ratio)
                details['chi_interpretation'] = 'miscible (chi <= chain-length critical chi)'
            else:
                score = 0.85
                details['chi_interpretation'] = 'miscible by empirical chi'
            return ScorerResult(score=max(0.0, min(1.0, score)),
                                label='solubility_compatibility', details=details)
        elif fh.miscible is False:
            ratio = fh.chi / fh.critical_chi if fh.critical_chi else None
            if ratio is not None and ratio > 20:
                score = 0.15
            elif ratio is not None and ratio > 5:
                score = 0.25
            else:
                score = 0.35
            details['chi_ratio'] = round(ratio, 2) if ratio is not None else None
            details['chi_interpretation'] = 'immiscible (chi > chain-length critical chi)'
            return ScorerResult(score=max(0.0, min(1.0, score)),
                                label='solubility_compatibility', details=details)
        elif fh.chi > 0.15:
            score = max(0.05, 0.2 - fh.chi * 0.02)
            details['chi_interpretation'] = 'immiscible (high chi; chain length unavailable)'
            return ScorerResult(score=max(0.0, min(1.0, score)),
                                label='solubility_compatibility', details=details)
        else:
            details['chi_interpretation'] = (
                'uncertain (chi available but chain length unavailable); using Hansen distance'
            )

    # --- Hansen distance (Ra) ---
    if material_a.hansen is not None and material_b.hansen is not None:
        ra = material_a.hansen.distance(material_b.hansen)
        details['hansen_distance_Ra'] = round(ra, 2)
        details['delta_total_a'] = round(material_a.hansen.delta_total, 2)
        details['delta_total_b'] = round(material_b.hansen.delta_total, 2)

        if ra < 2.0:
            score = 0.95
            details['hansen_interpretation'] = 'excellent compatibility'
        elif ra < 4.0:
            score = 0.85 - (ra - 2.0) * 0.1
            details['hansen_interpretation'] = 'good compatibility'
        elif ra < 8.0:
            score = 0.65 - (ra - 4.0) * 0.075
            details['hansen_interpretation'] = 'marginal compatibility'
        elif ra < 12.0:
            score = 0.35 - (ra - 8.0) * 0.05
            details['hansen_interpretation'] = 'poor compatibility'
        else:
            score = max(0.05, 0.15 - (ra - 12.0) * 0.02)
            details['hansen_interpretation'] = 'immiscible'
    else:
        details['note'] = 'No Hansen or chi data available; default score'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='solubility_compatibility', details=details)


# =============================================================================
# 2. THERMAL COMPATIBILITY SCORE
# =============================================================================
# Analogous to electrochemical stability: "Is the processing window compatible?"

def score_thermal_compatibility(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> ScorerResult:
    """
    Score thermal compatibility between two polymers.

    Factors:
    - Tg mismatch: large difference = phase separation risk in blends
    - Processing window: Tm of one must not decompose other
    - Thermal stability: min(decomp_temp) sets processing ceiling

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    tg_a = material_a.glass_transition_C
    tg_b = material_b.glass_transition_C
    tm_a = material_a.melting_point_C
    tm_b = material_b.melting_point_C
    td_a = material_a.decomposition_temp_C
    td_b = material_b.decomposition_temp_C

    # --- Tg mismatch ---
    if tg_a is not None and tg_b is not None:
        tg_diff = abs(tg_a - tg_b)
        details['tg_a_C'] = tg_a
        details['tg_b_C'] = tg_b
        details['tg_difference_C'] = round(tg_diff, 1)

        if tg_diff > 200:
            score *= 0.5
            details['tg_assessment'] = 'extreme Tg mismatch; likely phase-separated'
        elif tg_diff > 100:
            score *= 0.7
            details['tg_assessment'] = 'large Tg mismatch; blending difficult'
        elif tg_diff > 50:
            score *= 0.85
            details['tg_assessment'] = 'moderate Tg mismatch'
        else:
            details['tg_assessment'] = 'compatible Tg range'

    # --- Processing window: can we melt/process both without decomposing either? ---
    process_temps = []
    if tm_a is not None:
        process_temps.append(tm_a)
    if tm_b is not None:
        process_temps.append(tm_b)
    if tg_a is not None and tm_a is None:
        # Amorphous: process above Tg
        process_temps.append(tg_a + 50)
    if tg_b is not None and tm_b is None:
        process_temps.append(tg_b + 50)

    if process_temps and (td_a is not None or td_b is not None):
        max_process_temp = max(process_temps)
        min_decomp = min(t for t in [td_a, td_b] if t is not None)
        headroom = min_decomp - max_process_temp

        details['max_processing_temp_C'] = round(max_process_temp, 0)
        details['min_decomposition_temp_C'] = min_decomp
        details['thermal_headroom_C'] = round(headroom, 0)

        if headroom < 0:
            score *= 0.2
            details['processing_risk'] = 'processing temperature exceeds decomposition'
        elif headroom < 30:
            score *= 0.6
            details['processing_risk'] = 'tight thermal headroom'
        elif headroom < 60:
            score *= 0.85
            details['processing_risk'] = 'adequate thermal headroom'

    # --- Both thermosets: incompatible processing ---
    if (material_a.structure == PolymerStructure.CROSSLINKED and
            material_b.structure == PolymerStructure.CROSSLINKED):
        score *= 0.3
        details['crosslink_issue'] = 'both crosslinked; cannot melt-blend'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='thermal_compatibility', details=details)


# =============================================================================
# 3. MECHANICAL COMPATIBILITY SCORE
# =============================================================================
# Analogous to battery mechanical compatibility

def score_mechanical_compatibility(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> ScorerResult:
    """
    Score mechanical compatibility between two polymers.

    Factors:
    - Elastic modulus mismatch: >10x = stress concentration at interface
    - Elongation mismatch: rigid + flexible = stress cracking
    - Density difference: affects blending uniformity

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- Elastic modulus mismatch ---
    mod_a = material_a.elastic_modulus_GPa
    mod_b = material_b.elastic_modulus_GPa

    if mod_a is not None and mod_b is not None and mod_a > 0 and mod_b > 0:
        modulus_ratio = max(mod_a, mod_b) / min(mod_a, mod_b)
        details['modulus_ratio'] = round(modulus_ratio, 1)
        details['modulus_a_GPa'] = mod_a
        details['modulus_b_GPa'] = mod_b

        if modulus_ratio > 100:
            # e.g., PDMS (0.001) vs PEEK (3.6) = 3600x
            score *= 0.3
            details['modulus_assessment'] = 'extreme modulus mismatch'
        elif modulus_ratio > 10:
            score *= 0.6
            details['modulus_assessment'] = 'large modulus mismatch'
        elif modulus_ratio > 5:
            score *= 0.8
            details['modulus_assessment'] = 'moderate modulus mismatch'

    # --- Elongation mismatch ---
    elong_a = material_a.elongation_at_break_pct
    elong_b = material_b.elongation_at_break_pct

    if elong_a is not None and elong_b is not None and elong_a > 0 and elong_b > 0:
        elong_ratio = max(elong_a, elong_b) / min(elong_a, elong_b)
        details['elongation_ratio'] = round(elong_ratio, 1)

        if elong_ratio > 50:
            score *= 0.5
            details['elongation_assessment'] = 'rigid + rubbery: interfacial stress failure'
        elif elong_ratio > 10:
            score *= 0.75
            details['elongation_assessment'] = 'significant ductility mismatch'

    # --- Both brittle: stress concentration risk ---
    if (elong_a is not None and elong_a < 5.0 and
            elong_b is not None and elong_b < 5.0):
        # Both brittle (PS, PMMA, epoxy, etc.)
        score *= 0.85
        details['brittleness'] = 'both materials brittle; crack propagation risk'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 4. CHEMICAL RESISTANCE SCORE
# =============================================================================
# Analogous to battery interface compatibility

def score_chemical_resistance(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> ScorerResult:
    """
    Score chemical compatibility between two polymers.

    Factors:
    - Water sensitivity: both hydrophilic = environmental risk
    - Chemical attack susceptibility
    - Crosslinked materials have better chemical resistance
    - Fluoropolymers resist virtually everything

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- Water sensitivity ---
    wa_a = material_a.water_absorption_pct
    wa_b = material_b.water_absorption_pct

    if wa_a is not None and wa_b is not None:
        max_wa = max(wa_a, wa_b)
        details['max_water_absorption_pct'] = max_wa

        if max_wa >= 100:
            # Water-soluble polymer (PEO, CMC)
            score *= 0.4
            details['water_risk'] = 'water-soluble component present'
        elif max_wa > 5.0:
            # Highly hygroscopic (nylons)
            score *= 0.7
            details['water_risk'] = 'highly hygroscopic; performance degrades with moisture'
        elif max_wa > 1.0:
            score *= 0.85
            details['water_risk'] = 'moderate moisture sensitivity'

    # --- Shared chemical vulnerabilities ---
    chem_failures_a = {fm for fm in material_a.failure_modes
                       if fm in {PolymerFailureMode.CHEMICAL_ATTACK,
                                 PolymerFailureMode.HYDROLYSIS}}
    chem_failures_b = {fm for fm in material_b.failure_modes
                       if fm in {PolymerFailureMode.CHEMICAL_ATTACK,
                                 PolymerFailureMode.HYDROLYSIS}}
    shared_chem = chem_failures_a & chem_failures_b
    if shared_chem:
        score *= 0.7
        details['shared_chemical_vulnerability'] = [fm.value for fm in shared_chem]

    # --- Crosslinked = better resistance ---
    crosslinked_count = sum(1 for m in [material_a, material_b]
                            if m.structure == PolymerStructure.CROSSLINKED)
    if crosslinked_count > 0:
        score = min(1.0, score * 1.1)
        details['crosslinked_benefit'] = f'{crosslinked_count} crosslinked component(s)'

    # --- Fluoropolymer bonus ---
    fluoro_names = {'PVDF', 'PTFE'}
    has_fluoro = material_a.abbreviation in fluoro_names or material_b.abbreviation in fluoro_names
    if has_fluoro:
        score = min(1.0, score * 1.05)
        details['fluoropolymer_benefit'] = True

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='chemical_resistance', details=details)


# =============================================================================
# 5. AGING PENALTY
# =============================================================================
# Analogous to battery degradation penalty

# Known problematic pairings
_KNOWN_BAD_BLENDS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('HDPE', 'PA6'): (0.5, 'Immiscible blend; delamination without compatibilizer'),
    ('HDPE', 'PA66'): (0.5, 'Immiscible blend; delamination without compatibilizer'),
    ('HDPE', 'PET'): (0.5, 'Immiscible blend; PE/PET polarity mismatch without compatibilizer'),
    ('PP', 'PA6'): (0.5, 'Immiscible blend; polarity mismatch'),
    ('PP', 'PA66'): (0.5, 'Immiscible blend; polarity mismatch'),
    ('PA6', 'ABS'): (0.5, 'Immiscible nylon/ABS blend without reactive compatibilizer'),
    ('ABS', 'PA6'): (0.5, 'Immiscible nylon/ABS blend without reactive compatibilizer'),
    ('PA66', 'ABS'): (0.5, 'Immiscible nylon/ABS blend without reactive compatibilizer'),
    ('ABS', 'PA66'): (0.5, 'Immiscible nylon/ABS blend without reactive compatibilizer'),
    ('PA6', 'PVC'): (0.5, 'Immiscible nylon/PVC blend without tailored compatibilizer'),
    ('PVC', 'PA6'): (0.5, 'Immiscible nylon/PVC blend without tailored compatibilizer'),
    ('PA66', 'PVC'): (0.5, 'Immiscible nylon/PVC blend without tailored compatibilizer'),
    ('PVC', 'PA66'): (0.5, 'Immiscible nylon/PVC blend without tailored compatibilizer'),
    ('PA66', 'POM'): (0.6, 'Immiscible nylon/acetal blend without compatibilizer; strong processing and interfacial mismatch'),
    ('POM', 'PA66'): (0.6, 'Immiscible nylon/acetal blend without compatibilizer; strong processing and interfacial mismatch'),
    ('ABS', 'PTFE'): (0.7, 'ABS/PTFE is not a standard miscible blend; PTFE surface energy and fluoropolymer inertness drive poor interfacial adhesion'),
    ('PTFE', 'ABS'): (0.7, 'ABS/PTFE is not a standard miscible blend; PTFE surface energy and fluoropolymer inertness drive poor interfacial adhesion'),
    ('PTFE', 'Epoxy'): (0.7, 'Untreated PTFE has very low surface energy; poor epoxy adhesion'),
    ('Epoxy', 'PTFE'): (0.7, 'Untreated PTFE has very low surface energy; poor epoxy adhesion'),
    ('PTFE', 'Phenolic'): (0.6, 'Untreated PTFE has very low surface energy; poor thermoset adhesion'),
    ('Phenolic', 'PTFE'): (0.6, 'Untreated PTFE has very low surface energy; poor thermoset adhesion'),
    ('PTFE', 'NMP'): (0.3, 'PTFE chemically inert; will not dissolve'),
    ('PTFE', 'Toluene'): (0.3, 'PTFE chemically inert; will not dissolve'),
    ('PTFE', 'Acetone'): (0.3, 'PTFE chemically inert; will not dissolve'),
    ('Water', 'HDPE'): (0.6, 'Extreme polarity mismatch; completely immiscible'),
    ('Water', 'PP'): (0.6, 'Extreme polarity mismatch; completely immiscible'),
    ('Water', 'PS'): (0.5, 'Polarity mismatch; PS is hydrophobic'),
    ('Water', 'PTFE'): (0.7, 'Maximum polarity mismatch; PTFE is hydrophobic'),
}


def score_aging_penalty(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> ScorerResult:
    """
    Apply aging/degradation penalty for known problematic pairings.

    Factors:
    - Known bad blend lookup
    - Shared degradation vulnerabilities (UV, oxidation)
    - Low thermal stability floor
    - Environmental stress cracking risk

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        ScorerResult with score in [0, 1] (1 = no aging concerns)
    """
    penalty = 0.0
    reasons = []

    # --- Known bad pairings lookup ---
    for key in [(material_a.abbreviation, material_b.abbreviation),
                (material_b.abbreviation, material_a.abbreviation)]:
        if key in _KNOWN_BAD_BLENDS:
            p, reason = _KNOWN_BAD_BLENDS[key]
            penalty = max(penalty, p)
            reasons.append(reason)

    # --- Shared critical failure modes ---
    shared_failures = set(material_a.failure_modes) & set(material_b.failure_modes)
    critical_shared = shared_failures & {
        PolymerFailureMode.UV_DEGRADATION,
        PolymerFailureMode.OXIDATION,
        PolymerFailureMode.HYDROLYSIS,
    }
    if critical_shared:
        penalty = max(penalty, 0.15 * len(critical_shared))
        reasons.append(f'Shared degradation modes: {[f.value for f in critical_shared]}')

    # --- Low thermal stability floor ---
    td_a = material_a.decomposition_temp_C
    td_b = material_b.decomposition_temp_C
    if td_a is not None and td_b is not None:
        min_td = min(td_a, td_b)
        if min_td < 200:
            penalty = max(penalty, 0.3)
            reasons.append(f'Low thermal stability floor: {min_td}C')
        elif min_td < 280:
            penalty = max(penalty, 0.1)
            reasons.append(f'Moderate thermal stability: {min_td}C')

    # --- Environmental stress cracking ---
    esc_count = sum(1 for m in [material_a, material_b]
                    if PolymerFailureMode.ENVIRONMENTAL_STRESS_CRACKING in m.failure_modes)
    if esc_count > 0:
        penalty = max(penalty, 0.1)
        reasons.append('Environmental stress cracking susceptibility')

    # --- Plasticizer migration ---
    if (PolymerFailureMode.PLASTICIZER_MIGRATION in material_a.failure_modes or
            PolymerFailureMode.PLASTICIZER_MIGRATION in material_b.failure_modes):
        penalty = max(penalty, 0.2)
        reasons.append('Plasticizer migration risk')

    score = max(0.0, 1.0 - penalty)
    details = {
        'penalty': round(penalty, 2),
        'reasons': reasons if reasons else ['No known aging concerns'],
    }

    return ScorerResult(score=score, label='aging_penalty', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a polymer pair.

    Args:
        material_a: First polymer
        material_b: Second polymer

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'solubility_compatibility': score_solubility_compatibility(material_a, material_b),
        'thermal_compatibility': score_thermal_compatibility(material_a, material_b),
        'mechanical_compatibility': score_mechanical_compatibility(material_a, material_b),
        'chemical_resistance': score_chemical_resistance(material_a, material_b),
        'aging_penalty': score_aging_penalty(material_a, material_b),
    }


if __name__ == "__main__":
    from polymer_bridge.material_properties import THERMOPLASTIC_POLYMERS, BATTERY_POLYMERS

    print("=" * 70)
    print("Polymer Interaction Scoring - Demo")
    print("=" * 70)
    print()

    # Good blend: PVDF + PMMA
    pvdf = get_polymer('PVDF')
    pmma = get_polymer('PMMA')
    print(f"Pair: {pvdf.abbreviation} <-> {pmma.abbreviation} (known miscible)")
    results = score_all(pvdf, pmma)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
    print()

    # Bad blend: HDPE + PA6
    hdpe = get_polymer('HDPE')
    pa6 = get_polymer('PA6')
    print(f"Pair: {hdpe.abbreviation} <-> {pa6.abbreviation} (known immiscible)")
    results = score_all(hdpe, pa6)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}  {result.details}")
