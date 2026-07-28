# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular Interaction Scoring
===============================

Five molecular-level compatibility scorers, following the exact bridge pattern
of battery_bridge/interaction_scoring.py (ScorerResult dataclass + 5 scorers
+ score_all).

Each scorer takes two Molecule objects and returns a ScorerResult with a
float score in [0, 1] where 1 = excellent compatibility.

Scorer Mapping (battery bridge -> molecular bridge):
-----------------------------------------------------
Ion transport score         -> Electronic compatibility
Electrochemical stability   -> Thermodynamic stability
Interface compatibility     -> Steric compatibility
Mechanical compatibility    -> Solubility compatibility
Degradation penalty         -> Reactivity risk

References:
-----------
- Koopman's theorem: IE approx. -E(HOMO), EA approx. -E(LUMO)
- Mulliken electronegativity: chi = (IE + EA) / 2
- Pearson HSAB principle: hard-hard and soft-soft = favorable
- Lipinski's Rule of Five: drug-likeness from logP, MW, HBD, HBA
- Flory-Huggins: chi parameter from solubility parameter difference
- Hansen solubility: like dissolves like (delta_D, delta_P, delta_H)
- GHS hazard compatibility matrices: oxidizer + fuel = incompatible
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import math

from molecular_bridge.molecule_properties import Molecule


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# Helper functions
# =============================================================================

def _safe_ratio(a: float, b: float) -> float:
    """Return ratio of larger/smaller, avoiding division by zero."""
    if a <= 0 or b <= 0:
        return float('inf')
    return max(a, b) / min(a, b)


def _gaussian_similarity(a: float, b: float, sigma: float) -> float:
    """Gaussian similarity kernel: 1.0 when a==b, decays with sigma."""
    return math.exp(-((a - b) ** 2) / (2 * sigma ** 2))


def _clamp(value: float) -> float:
    """Clamp a float to [0, 1]."""
    return max(0.0, min(1.0, value))


# =============================================================================
# 1. ELECTRONIC COMPATIBILITY
# =============================================================================
# Analogous to ion_transport (battery) / H-bond (protein).
# "Can these molecules electronically interact in a compatible way?"

def score_electronic_compatibility(a: Molecule, b: Molecule) -> ScorerResult:
    """
    Score electronic compatibility between two molecules.

    Factors:
    - Ionization energy vs electron affinity matching (Mulliken scale)
    - Dipole moment alignment (both polar or both nonpolar = good mixing)
    - Chemical hardness similarity (Pearson HSAB principle)

    A good electron-transfer pair has IE(donor) close to EA(acceptor).
    For non-reactive mixing, similar chemical hardness is favorable.

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details: Dict = {}

    # --- Mulliken electronegativity and chemical hardness ---
    # chi = (IE + EA) / 2;  eta = (IE - EA) / 2
    ie_a, ea_a = a.ionization_energy_eV, a.electron_affinity_eV
    ie_b, ea_b = b.ionization_energy_eV, b.electron_affinity_eV

    if ie_a is not None and ea_a is not None and ie_b is not None and ea_b is not None:
        chi_a = (ie_a + ea_a) / 2.0
        chi_b = (ie_b + ea_b) / 2.0
        eta_a = (ie_a - ea_a) / 2.0
        eta_b = (ie_b - ea_b) / 2.0

        # Electronegativity difference drives electron transfer.
        # Large difference = strong charge transfer = may be reactive.
        chi_diff = abs(chi_a - chi_b)
        details['electronegativity_a'] = round(chi_a, 2)
        details['electronegativity_b'] = round(chi_b, 2)
        details['electronegativity_diff_eV'] = round(chi_diff, 2)

        if chi_diff > 4.0:
            score *= 0.4   # Very strong charge transfer tendency
        elif chi_diff > 2.0:
            score *= 0.7
        elif chi_diff > 1.0:
            score *= 0.9
        # chi_diff < 1.0 eV: good compatibility, no penalty

        # HSAB hardness similarity: hard-hard or soft-soft is favorable
        eta_diff = abs(eta_a - eta_b)
        details['hardness_a_eV'] = round(eta_a, 2)
        details['hardness_b_eV'] = round(eta_b, 2)
        details['hardness_diff_eV'] = round(eta_diff, 2)

        if eta_diff > 3.0:
            score *= 0.6   # Hard + soft mismatch (Pearson penalty)
        elif eta_diff > 1.5:
            score *= 0.8

    elif ie_a is not None and ie_b is not None:
        # Only IE available -- compare directly
        ie_diff = abs(ie_a - ie_b)
        details['ie_diff_eV'] = round(ie_diff, 2)
        if ie_diff > 4.0:
            score *= 0.5
        elif ie_diff > 2.0:
            score *= 0.75
    else:
        details['note'] = 'Insufficient electronic data for full analysis'

    # --- Dipole moment alignment ---
    # Both polar or both nonpolar = good miscibility
    # One polar + one nonpolar = poor mixing (oil and water)
    dp_a = a.dipole_moment_debye
    dp_b = b.dipole_moment_debye

    if dp_a is not None and dp_b is not None:
        # Polar threshold: >1.5 D is distinctly polar
        polar_a = dp_a > 1.5
        polar_b = dp_b > 1.5

        if polar_a == polar_b:
            # Both polar or both nonpolar -- compatible
            dipole_factor = 1.0
            details['dipole_match'] = 'both_polar' if polar_a else 'both_nonpolar'
        else:
            # Mismatch -- penalty scales with dipole difference
            dipole_diff = abs(dp_a - dp_b)
            dipole_factor = max(0.5, 1.0 - dipole_diff * 0.08)
            details['dipole_match'] = 'polar_nonpolar_mismatch'
            details['dipole_diff_debye'] = round(dipole_diff, 2)

        score *= dipole_factor
        details['dipole_a_debye'] = round(dp_a, 2)
        details['dipole_b_debye'] = round(dp_b, 2)

    score = _clamp(score)
    return ScorerResult(score=score, label='electronic_compatibility', details=details)


# =============================================================================
# 2. THERMODYNAMIC STABILITY
# =============================================================================
# Analogous to electrochemical_stability (battery) / salt_bridge (protein).
# "Is the mixture thermodynamically stable?"

def score_thermodynamic_stability(a: Molecule, b: Molecule) -> ScorerResult:
    """
    Score thermodynamic stability of a molecular pair.

    Factors:
    - Boiling point proximity (closer = similar volatility = better co-processing)
    - Vapor pressure ratio (large difference = one evaporates first)
    - Density similarity (large diff = phase separation tendency)

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details: Dict = {}
    factors_evaluated = 0

    # --- Boiling point proximity ---
    bp_a = a.boiling_point_C
    bp_b = b.boiling_point_C

    if bp_a is not None and bp_b is not None:
        factors_evaluated += 1
        bp_diff = abs(bp_a - bp_b)
        details['bp_a_C'] = round(bp_a, 1)
        details['bp_b_C'] = round(bp_b, 1)
        details['bp_diff_C'] = round(bp_diff, 1)

        # >200 C difference is problematic (one boils while other is liquid)
        # Use a sigmoid-like decay centered around 100 C difference
        bp_factor = 1.0 / (1.0 + math.exp((bp_diff - 100) / 40))
        bp_factor = 0.5 + 0.5 * bp_factor  # Map to [0.5, 1.0]
        score *= bp_factor
        details['bp_compatibility'] = round(bp_factor, 3)

    # --- Vapor pressure ratio ---
    vp_a = a.vapor_pressure_mmHg_25C
    vp_b = b.vapor_pressure_mmHg_25C

    if vp_a is not None and vp_b is not None and vp_a > 0 and vp_b > 0:
        factors_evaluated += 1
        # Use log ratio since vapor pressure spans many orders of magnitude
        log_ratio = abs(math.log10(vp_a) - math.log10(vp_b))
        details['vp_log_ratio'] = round(log_ratio, 2)

        if log_ratio > 4:
            score *= 0.4  # >4 orders of magnitude difference
        elif log_ratio > 2:
            score *= 0.6 + 0.2 * (4 - log_ratio) / 2
        elif log_ratio > 1:
            score *= 0.85
        # <1 order of magnitude: no penalty

    # --- Density similarity ---
    d_a = a.density_g_cm3
    d_b = b.density_g_cm3

    if d_a is not None and d_b is not None and d_a > 0 and d_b > 0:
        factors_evaluated += 1
        density_ratio = _safe_ratio(d_a, d_b)
        details['density_a_g_cm3'] = round(d_a, 3)
        details['density_b_g_cm3'] = round(d_b, 3)
        details['density_ratio'] = round(density_ratio, 2)

        # Density ratio >2 strongly promotes phase separation
        if density_ratio > 3.0:
            score *= 0.5
        elif density_ratio > 2.0:
            score *= 0.7
        elif density_ratio > 1.5:
            score *= 0.9
        # Ratio < 1.5: no penalty

    if factors_evaluated == 0:
        details['note'] = 'No thermodynamic data available'
        score = 0.5  # Uninformative prior

    score = _clamp(score)
    return ScorerResult(score=score, label='thermodynamic_stability', details=details)


# =============================================================================
# 3. STERIC COMPATIBILITY
# =============================================================================
# Analogous to interface_compatibility (battery) / hydrophobic (protein).
# "Do these molecules physically fit together?"

# Complementary functional group pairs that interact favorably
_COMPLEMENTARY_GROUPS: Dict[str, Set[str]] = {
    'hydroxyl': {'carbonyl', 'ester', 'carboxyl', 'ether'},
    'amine': {'carbonyl', 'carboxyl', 'ester', 'sulfonyl'},
    'carboxyl': {'amine', 'hydroxyl', 'ether'},
    'carbonyl': {'hydroxyl', 'amine'},
    'ether': {'hydroxyl', 'carboxyl'},
    'ester': {'hydroxyl', 'amine'},
    'aldehyde': {'hydroxyl', 'amine'},
    'thiol': {'thiol', 'halide'},
    'sulfonyl': {'amine', 'hydroxyl'},
}

# Self-reactive functional group pairs (same group on both = potential issue)
_SELF_REACTIVE_GROUPS: Set[str] = {
    'carboxyl',    # Condensation possible
    'aldehyde',    # Aldol condensation
    'isocyanate',  # Polymerization
    'epoxide',     # Ring-opening polymerization
}


def score_steric_compatibility(a: Molecule, b: Molecule) -> ScorerResult:
    """
    Score steric compatibility between two molecules.

    Factors:
    - Molecular weight ratio (similar MW = better packing/mixing)
    - Functional group complementarity (complementary = good interaction,
      same reactive groups = potential unwanted reaction)

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details: Dict = {}

    # --- Molecular weight ratio ---
    mw_a = a.molecular_weight
    mw_b = b.molecular_weight

    if mw_a > 0 and mw_b > 0:
        mw_ratio = _safe_ratio(mw_a, mw_b)
        details['mw_a'] = round(mw_a, 1)
        details['mw_b'] = round(mw_b, 1)
        details['mw_ratio'] = round(mw_ratio, 2)

        # Small molecules mix better with similar-sized partners.
        # Ratio >10 means one molecule is an order of magnitude larger.
        if mw_ratio > 10:
            score *= 0.5   # Polymer-like size mismatch
        elif mw_ratio > 5:
            score *= 0.7
        elif mw_ratio > 3:
            score *= 0.85
        # Ratio < 3: good compatibility

    # --- Functional group analysis ---
    fg_a = set(g.lower() for g in a.functional_groups)
    fg_b = set(g.lower() for g in b.functional_groups)

    if fg_a and fg_b:
        # Count complementary interactions
        complementary_count = 0
        complementary_pairs = []
        for ga in fg_a:
            complements = _COMPLEMENTARY_GROUPS.get(ga, set())
            matches = complements & fg_b
            if matches:
                complementary_count += len(matches)
                for m in matches:
                    complementary_pairs.append(f'{ga}-{m}')

        details['complementary_pairs'] = complementary_pairs
        details['complementary_count'] = complementary_count

        # Complementary groups boost compatibility
        if complementary_count >= 3:
            score *= 1.0  # Already at max, but strong confirmation
        elif complementary_count >= 1:
            score *= min(1.0, 0.9 + complementary_count * 0.05)

        # Check for self-reactive groups present in both molecules
        shared_reactive = fg_a & fg_b & _SELF_REACTIVE_GROUPS
        if shared_reactive:
            score *= 0.8
            details['self_reactive_warning'] = list(shared_reactive)

        # No complementary groups and no shared groups = inert mixing
        if complementary_count == 0 and not (fg_a & fg_b):
            details['interaction_type'] = 'no_specific_interaction'
    else:
        details['note'] = 'Functional group data incomplete'

    score = _clamp(score)
    return ScorerResult(score=score, label='steric_compatibility', details=details)


# =============================================================================
# 4. SOLUBILITY COMPATIBILITY
# =============================================================================
# Analogous to mechanical_compatibility (battery) / vdW (protein).
# "Will these molecules dissolve in each other?"

def score_solubility_compatibility(a: Molecule, b: Molecule) -> ScorerResult:
    """
    Score solubility compatibility (miscibility prediction).

    Factors:
    - logP similarity ("like dissolves like" principle)
    - H-bond donor/acceptor complementarity (donor on one + acceptor on
      the other promotes co-solvation)
    - Water solubility comparison (both hydrophilic or both hydrophobic)

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details: Dict = {}
    factors_evaluated = 0

    # --- logP similarity (like dissolves like) ---
    logp_a = a.logP
    logp_b = b.logP

    if logp_a is not None and logp_b is not None:
        factors_evaluated += 1
        logp_diff = abs(logp_a - logp_b)
        details['logP_a'] = round(logp_a, 2)
        details['logP_b'] = round(logp_b, 2)
        details['logP_diff'] = round(logp_diff, 2)

        # Gaussian similarity: sigma=2.0 gives 50% at logP diff ~2.4
        logp_factor = _gaussian_similarity(logp_a, logp_b, sigma=2.0)
        # Map from [0, 1] to [0.3, 1.0] -- even big diffs aren't total failure
        logp_factor = 0.3 + 0.7 * logp_factor
        score *= logp_factor
        details['logP_compatibility'] = round(logp_factor, 3)

        # Polarity classification
        hydrophilic_a = logp_a < 0
        hydrophilic_b = logp_b < 0
        if hydrophilic_a == hydrophilic_b:
            details['polarity_match'] = 'both_hydrophilic' if hydrophilic_a else 'both_hydrophobic'
        else:
            details['polarity_match'] = 'hydrophilic_hydrophobic_mismatch'

    # --- H-bond donor/acceptor complementarity ---
    hbd_a, hba_a = a.hbond_donors, a.hbond_acceptors
    hbd_b, hba_b = b.hbond_donors, b.hbond_acceptors

    if (hbd_a + hba_a) > 0 or (hbd_b + hba_b) > 0:
        factors_evaluated += 1
        # Complementarity: donors on A match acceptors on B and vice versa
        # Minimum of donor-acceptor pairs available
        hbond_pairs = min(hbd_a, hba_b) + min(hbd_b, hba_a)
        total_hbond_sites = hbd_a + hba_a + hbd_b + hba_b

        details['hbond_donors_a'] = hbd_a
        details['hbond_acceptors_a'] = hba_a
        details['hbond_donors_b'] = hbd_b
        details['hbond_acceptors_b'] = hba_b
        details['hbond_complementary_pairs'] = hbond_pairs

        if total_hbond_sites > 0:
            # Complementarity ratio: what fraction of H-bond sites are satisfied
            complementarity = (2.0 * hbond_pairs) / total_hbond_sites
            complementarity = min(1.0, complementarity)
            # High complementarity = strong solubility boost
            hbond_factor = 0.7 + 0.3 * complementarity
            score *= hbond_factor
            details['hbond_complementarity'] = round(complementarity, 3)

    # --- Water solubility comparison ---
    sol_a = a.solubility_mg_L
    sol_b = b.solubility_mg_L

    if sol_a is not None and sol_b is not None and sol_a > 0 and sol_b > 0:
        factors_evaluated += 1
        # Log-scale comparison (solubility spans many orders of magnitude)
        log_ratio = abs(math.log10(sol_a) - math.log10(sol_b))
        details['solubility_log_ratio'] = round(log_ratio, 2)

        if log_ratio > 4:
            score *= 0.4  # One is very soluble, other is not
        elif log_ratio > 2:
            score *= 0.6 + 0.2 * (4 - log_ratio) / 2
        elif log_ratio > 1:
            score *= 0.85

    if factors_evaluated == 0:
        details['note'] = 'No solubility data available'
        score = 0.5

    score = _clamp(score)
    return ScorerResult(score=score, label='solubility_compatibility', details=details)


# =============================================================================
# 5. REACTIVITY RISK
# =============================================================================
# Analogous to degradation_penalty (battery) / electrostatic repulsion (protein).
# "Will these molecules react dangerously or undesirably?"

# Known bad functional group pairings: (group_a, group_b) -> (penalty, reason)
_BAD_GROUP_PAIRS: Dict[Tuple[str, str], Tuple[float, str]] = {
    # Acid + base neutralization
    ('carboxyl', 'amine'): (0.5, 'Carboxylic acid + amine: salt formation / amide condensation'),
    ('carboxyl', 'hydroxyl'): (0.3, 'Acid + alcohol: Fischer esterification possible at elevated temp'),
    # Oxidizer + reductant
    ('peroxide', 'aldehyde'): (0.7, 'Peroxide + aldehyde: violent oxidation risk'),
    ('peroxide', 'ether'): (0.6, 'Peroxide + ether: explosive peroxide formation'),
    ('peroxide', 'thiol'): (0.5, 'Peroxide + thiol: rapid oxidation'),
    ('nitro', 'amine'): (0.4, 'Nitro + amine: potential energetic mixture'),
    # Ring-opening / polymerization
    ('epoxide', 'amine'): (0.5, 'Epoxide + amine: ring-opening reaction (curing agent pair)'),
    ('epoxide', 'carboxyl'): (0.4, 'Epoxide + acid: ring-opening esterification'),
    ('isocyanate', 'hydroxyl'): (0.5, 'Isocyanate + alcohol: urethane formation'),
    ('isocyanate', 'amine'): (0.6, 'Isocyanate + amine: rapid urea formation'),
    ('isocyanate', 'carboxyl'): (0.5, 'Isocyanate + acid: mixed anhydride / CO2 generation'),
    # Acid-sensitive groups
    ('acetal', 'carboxyl'): (0.4, 'Acetal hydrolysis under acidic conditions'),
    # Halide reactivity
    ('halide', 'amine'): (0.3, 'Alkyl halide + amine: nucleophilic substitution'),
    ('halide', 'hydroxyl'): (0.2, 'Alkyl halide + alcohol: Williamson ether synthesis possible'),
}


def score_reactivity_risk(a: Molecule, b: Molecule) -> ScorerResult:
    """
    Score reactivity risk for a molecular pair.

    Returns 1.0 for safe/inert pairs, lower scores for risky combinations.

    Factors:
    - Redox incompatibility (strong oxidizer + strong reducer = dangerous)
    - pKa mismatch (strong acid + strong base = violent neutralization)
    - Known bad functional group pairings (from _BAD_GROUP_PAIRS table)

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        ScorerResult with score in [0, 1] (1 = safe, 0 = dangerous)
    """
    penalty = 0.0
    reasons: List[str] = []
    details: Dict = {}

    # --- Redox incompatibility ---
    # Strong oxidizer + strong reducer = fire/explosion risk
    if (a.is_oxidizing and b.is_reducing) or (b.is_oxidizing and a.is_reducing):
        penalty = max(penalty, 0.7)
        oxidizer = a.name if a.is_oxidizing else b.name
        reducer = a.name if a.is_reducing else b.name
        reasons.append(f'Redox incompatibility: {oxidizer} (oxidizer) + {reducer} (reducer)')
        details['redox_incompatible'] = True

    # Redox potential difference gives severity
    rp_a = a.redox_potential_V
    rp_b = b.redox_potential_V
    if rp_a is not None and rp_b is not None:
        redox_diff = abs(rp_a - rp_b)
        details['redox_potential_diff_V'] = round(redox_diff, 2)
        if redox_diff > 2.0 and (a.is_oxidizing or a.is_reducing or
                                  b.is_oxidizing or b.is_reducing):
            # Large redox gap + known redox activity = severe
            penalty = max(penalty, min(0.8, redox_diff * 0.2))
            reasons.append(f'Large redox potential gap: {redox_diff:.1f} V')

    # --- pKa mismatch (acid-base reaction) ---
    pka_a = a.pKa
    pka_b = b.pKa

    if pka_a is not None and pka_b is not None:
        pka_diff = abs(pka_a - pka_b)
        details['pKa_a'] = round(pka_a, 1)
        details['pKa_b'] = round(pka_b, 1)
        details['pKa_diff'] = round(pka_diff, 1)

        # One strong acid (pKa < 0) + one base (pKa > 10) = vigorous reaction
        strong_acid = min(pka_a, pka_b) < 2
        strong_base = max(pka_a, pka_b) > 12

        if strong_acid and strong_base:
            penalty = max(penalty, 0.6)
            reasons.append(f'Strong acid (pKa={min(pka_a, pka_b):.1f}) + strong base (pKa={max(pka_a, pka_b):.1f})')
        elif pka_diff > 10:
            # Large pKa gap = proton transfer likely
            penalty = max(penalty, 0.4)
            reasons.append(f'Large pKa difference ({pka_diff:.1f}): proton transfer expected')
        elif pka_diff > 5:
            penalty = max(penalty, 0.2)
            reasons.append(f'Moderate pKa difference ({pka_diff:.1f}): partial proton transfer possible')

    # --- Known bad functional group pairings ---
    fg_a = set(g.lower() for g in a.functional_groups)
    fg_b = set(g.lower() for g in b.functional_groups)

    if fg_a and fg_b:
        triggered_pairs = []
        for (g1, g2), (p, reason) in _BAD_GROUP_PAIRS.items():
            # Check both orderings
            if (g1 in fg_a and g2 in fg_b) or (g2 in fg_a and g1 in fg_b):
                penalty = max(penalty, p)
                triggered_pairs.append(f'{g1}+{g2}')
                reasons.append(reason)

        if triggered_pairs:
            details['triggered_group_pairs'] = triggered_pairs

    # --- Flash point consideration ---
    # Both molecules with very low flash points = fire risk in combination
    fp_a = a.flash_point_C
    fp_b = b.flash_point_C
    if fp_a is not None and fp_b is not None:
        min_fp = min(fp_a, fp_b)
        details['min_flash_point_C'] = round(min_fp, 1)
        if min_fp < 0:
            penalty = max(penalty, 0.3)
            reasons.append(f'Extremely low flash point ({min_fp:.0f} C): fire hazard')
        elif min_fp < 23:
            penalty = max(penalty, 0.15)
            reasons.append(f'Low flash point ({min_fp:.0f} C): flammable mixture')

    score = _clamp(1.0 - penalty)
    details['penalty'] = round(penalty, 2)
    details['reasons'] = reasons if reasons else ['No known reactivity concerns']

    return ScorerResult(score=score, label='reactivity_risk', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(a: Molecule, b: Molecule) -> Dict[str, ScorerResult]:
    """
    Run all five molecular interaction scorers on a molecule pair.

    Args:
        a: First molecule
        b: Second molecule

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'electronic_compatibility': score_electronic_compatibility(a, b),
        'thermodynamic_stability': score_thermodynamic_stability(a, b),
        'steric_compatibility': score_steric_compatibility(a, b),
        'solubility_compatibility': score_solubility_compatibility(a, b),
        'reactivity_risk': score_reactivity_risk(a, b),
    }
