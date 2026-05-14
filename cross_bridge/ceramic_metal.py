# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Ceramic-Metal Cross-Bridge Functor
====================================

Scores compatibility between ceramic coatings/substrates and metal
substrates/structures. This is the functor F: Ceramic -> Metal that maps
sintering/CTE constraints into metal selection criteria.

Key cross-domain questions answered:
- Will the CTE mismatch cause delamination or cracking?
- Can the ceramic be processed without melting the metal substrate?
- Are the mechanical properties sufficiently matched?
- What is the chemical interaction risk at the interface?
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class DepositionMethod(Enum):
    """Ceramic deposition/processing method onto metal substrate."""
    BULK_SINTERING = "bulk_sintering"
    PVD = "pvd"
    CVD = "cvd"
    ALD = "ald"
    PLASMA_SPRAY = "plasma_spray"


VAPOR_PHASE_METHODS = {DepositionMethod.PVD, DepositionMethod.CVD, DepositionMethod.ALD}

# Thin-film compliance factor: effective CTE mismatch is reduced because
# thin coatings deform elastically with the substrate rather than cracking.
CTE_COMPLIANCE_FACTOR = {
    DepositionMethod.PVD: 0.5,
    DepositionMethod.CVD: 0.5,
    DepositionMethod.ALD: 0.4,           # Thinnest films = most compliant
    DepositionMethod.PLASMA_SPRAY: 0.6,  # Thicker coatings, less compliant
}

# Process temperature by deposition method (substrate temperature, not source)
DEPOSITION_TEMP_C = {
    DepositionMethod.PVD: 500.0,
    DepositionMethod.CVD: 800.0,
    DepositionMethod.ALD: 300.0,
    DepositionMethod.PLASMA_SPRAY: 200.0,
}


from ceramic_bridge.material_properties import (
    CeramicMaterial,
    get_ceramic,
    ALL_CERAMICS,
)
from metal_bridge.material_properties import (
    MetalMaterial,
    get_metal,
    ALL_METALS,
)


# ============================================================================
# Known cross-domain pairs
# ============================================================================

KNOWN_GOOD_PAIRS: List[Tuple[str, str]] = [
    # (ceramic, metal)
    ('Al2O3', 'SS_304'),     # Alumina on stainless steel (CTE 8.1 vs 17.3)
    ('Al2O3', 'SS_316'),     # Same, slightly different steel
    ('Al2O3', 'Ni'),         # Alumina on Ni (CTE 8.1 vs 13.4)
    ('TiN', 'Steel_4140'),   # TiN hard coating on tool steel
    ('TiN', 'Ti6Al4V'),      # TiN on Ti alloy (CTE 9.4 vs 8.6, excellent)
    ('ZrO2_YSZ', 'Inconel_718'),  # Thermal barrier coating
    ('SiC', 'Steel_4140'),   # SiC coating on steel
]

KNOWN_BAD_PAIRS: List[Tuple[str, str]] = [
    # (ceramic, metal)
    ('SiO2', 'Al'),          # CTE 0.55 vs 23.1 - extreme mismatch
    ('SiO2', 'Al_6061'),     # Same issue
    ('Al2O3', 'Al'),         # CTE 8.1 vs 23.1 - large mismatch
    ('Al2O3', 'Mg'),         # CTE 8.1 vs 26.0 + reactivity
    ('LGPS', 'Cu'),          # LGPS decomposes on contact with metals
]


@dataclass
class CeramicMetalResult:
    """Result of cross-domain ceramic-metal compatibility scoring."""
    compatible: bool
    score: float                      # 0-1 composite
    cte_compatibility: float          # CTE mismatch score
    thermal_processing: float         # Can process without melting metal?
    mechanical_compatibility: float   # Modulus/hardness match
    chemical_interaction: float       # Interface reactivity risk
    ceramic_name: str
    metal_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _score_cte_compatibility(
    ceramic: CeramicMaterial,
    metal: MetalMaterial,
    deposition_method: Optional[DepositionMethod] = None,
) -> Tuple[float, Dict]:
    """
    Score CTE mismatch between ceramic and metal.
    This is the #1 failure mode for ceramic-metal joints.

    For vapor-phase deposition (PVD/CVD/ALD), thin films are more
    compliant and tolerate larger CTE mismatches without cracking.
    """
    details = {}

    c_cte = ceramic.cte_per_K
    m_cte = metal.cte_per_K

    details['ceramic_cte'] = c_cte
    details['metal_cte'] = m_cte

    if c_cte is not None and m_cte is not None:
        diff = abs(c_cte - m_cte)
        details['cte_difference_raw'] = diff

        # Apply thin-film compliance factor for vapor-phase deposition
        if deposition_method and deposition_method in CTE_COMPLIANCE_FACTOR:
            factor = CTE_COMPLIANCE_FACTOR[deposition_method]
            diff *= factor
            details['compliance_factor'] = factor
            details['deposition_method'] = deposition_method.value

        details['cte_difference'] = diff

        # Ratio matters too
        bigger = max(c_cte, m_cte, 0.1)
        smaller = max(min(c_cte, m_cte), 0.01)
        ratio = bigger / smaller
        details['cte_ratio'] = ratio

        # Score based on absolute difference (x10^-6 /K)
        if diff < 2.0:
            score = 1.0      # Excellent match
        elif diff < 4.0:
            score = 0.85     # Good match
        elif diff < 6.0:
            score = 0.7      # Acceptable with graded interlayer
        elif diff < 10.0:
            score = 0.45     # Problematic
        elif diff < 15.0:
            score = 0.25     # High risk of delamination
        else:
            score = 0.1      # Will crack/delaminate

        # Additional ratio penalty for extreme mismatches
        # Reduced for thin films (ratio is less meaningful for compliant coatings)
        if ratio > 5.0:
            penalty = 0.7
            if deposition_method and deposition_method in VAPOR_PHASE_METHODS:
                penalty = 0.85  # Thin films tolerate ratio mismatches better
            score *= penalty
            details['ratio_penalty'] = True
    else:
        score = 0.5  # Unknown CTE
        details['note'] = 'Missing CTE data'

    return score, details


def _score_thermal_processing(
    ceramic: CeramicMaterial,
    metal: MetalMaterial,
    deposition_method: Optional[DepositionMethod] = None,
) -> Tuple[float, Dict]:
    """
    Score whether the ceramic can be processed onto the metal substrate.

    Real ceramic-metal coatings use multiple deposition methods:
    - Bulk sintering: requires sintering_temp < metal melting
    - PVD/CVD: substrate stays below 500C (most ceramics depositable)
    - Plasma spray: substrate stays below 300C
    - Sol-gel: substrate stays below 600C

    When deposition_method is specified, only that route is evaluated.
    When None, both bulk sintering and PVD routes are evaluated and the
    best one is used (current behavior).
    """
    details = {}

    c_sinter = ceramic.sintering_temp_C
    m_melt = metal.melting_point_C

    details['ceramic_sintering_C'] = c_sinter
    details['metal_melting_C'] = m_melt

    if c_sinter is not None and m_melt is not None:
        if deposition_method and deposition_method != DepositionMethod.BULK_SINTERING:
            # Evaluate only the specified deposition route
            dep_temp = DEPOSITION_TEMP_C[deposition_method]
            margin = m_melt - dep_temp
            details['deposition_method'] = deposition_method.value
            details['deposition_temp_C'] = dep_temp
            details['margin_C'] = margin

            if margin > 200:
                score = 0.85  # Excellent margin for thin-film processing
            elif margin > 0:
                score = 0.5
            else:
                score = 0.1   # Metal melts too low even for this method

        elif deposition_method == DepositionMethod.BULK_SINTERING:
            # Evaluate only bulk sintering route
            sinter_margin = m_melt - c_sinter
            details['sintering_margin_C'] = sinter_margin
            details['deposition_method'] = 'bulk_sintering'

            if sinter_margin > 500:
                score = 1.0
            elif sinter_margin > 300:
                score = 0.85
            elif sinter_margin > 100:
                score = 0.65
            elif sinter_margin > 0:
                score = 0.4
            else:
                score = 0.0
                details['bulk_sintering_impossible'] = True

        else:
            # No method specified: evaluate both routes, use the best
            PVD_TEMP = 500.0

            # Route 1: Bulk sintering
            sinter_margin = m_melt - c_sinter
            details['sintering_margin_C'] = sinter_margin

            if sinter_margin > 500:
                sinter_score = 1.0
            elif sinter_margin > 300:
                sinter_score = 0.85
            elif sinter_margin > 100:
                sinter_score = 0.65
            elif sinter_margin > 0:
                sinter_score = 0.4
            else:
                sinter_score = 0.0
                details['bulk_sintering_impossible'] = True

            # Route 2: PVD/CVD thin film
            pvd_margin = m_melt - PVD_TEMP
            if pvd_margin > 200:
                pvd_score = 0.8
            elif pvd_margin > 0:
                pvd_score = 0.5
            else:
                pvd_score = 0.1

            details['pvd_score'] = pvd_score
            details['sintering_score'] = sinter_score

            score = max(sinter_score, pvd_score)
    else:
        score = 0.5

    return score, details


def _score_mechanical_compatibility(
    ceramic: CeramicMaterial,
    metal: MetalMaterial,
) -> Tuple[float, Dict]:
    """
    Score mechanical compatibility between ceramic and metal.

    Concerns:
    - Large modulus mismatch creates stress concentration at interface
    - Hardness mismatch affects wear behavior
    - Ceramic brittleness vs metal ductility
    """
    details = {}

    c_mod = ceramic.elastic_modulus_GPa
    m_mod = metal.elastic_modulus_GPa

    if c_mod is not None and m_mod is not None:
        ratio = max(c_mod, m_mod) / max(min(c_mod, m_mod), 0.1)
        details['modulus_ratio'] = ratio
        details['ceramic_modulus_GPa'] = c_mod
        details['metal_modulus_GPa'] = m_mod

        if ratio < 1.5:
            mod_score = 1.0
        elif ratio < 2.0:
            mod_score = 0.85
        elif ratio < 3.0:
            mod_score = 0.7
        elif ratio < 5.0:
            mod_score = 0.5
        else:
            mod_score = 0.3  # Large mismatch
    else:
        mod_score = 0.6

    # Hardness ratio (ceramic usually much harder)
    c_hard = ceramic.hardness_HV
    m_hard = metal.hardness_HV

    if c_hard is not None and m_hard is not None:
        h_ratio = c_hard / max(m_hard, 1)
        details['hardness_ratio'] = h_ratio
        # Ceramic harder than metal is normal and expected
        # Very large ratio just means ceramic is doing its job as coating
        if h_ratio < 2.0:
            hard_score = 0.9
        elif h_ratio < 5.0:
            hard_score = 0.8
        elif h_ratio < 10.0:
            hard_score = 0.7
        else:
            hard_score = 0.5  # Extreme mismatch, adhesion concerns
    else:
        hard_score = 0.7

    score = 0.6 * mod_score + 0.4 * hard_score
    return score, details


def _score_chemical_interaction(
    ceramic: CeramicMaterial,
    metal: MetalMaterial,
) -> Tuple[float, Dict]:
    """
    Score chemical interaction risk at the ceramic-metal interface.

    Concerns:
    - Reactive metals (Ti, Al) can reduce oxide ceramics
    - Some ceramics decompose on metal contact at processing temp
    - Diffusion bonding vs reaction barrier needs
    """
    details = {}
    score = 0.7  # Default baseline

    # Known pair lookup
    pair = (ceramic.name, metal.name)
    if pair in KNOWN_GOOD_PAIRS:
        score = 0.95
        details['known_pair'] = 'good'
    elif pair in KNOWN_BAD_PAIRS:
        score = 0.15
        details['known_pair'] = 'bad'
    else:
        details['known_pair'] = 'unknown'

        # Check chemical stability of ceramic
        stability = ceramic.chemical_stability
        details['ceramic_stability'] = stability

        if stability == 'inert':
            score = 0.85
        elif stability == 'stable':
            score = 0.75
        elif stability == 'reactive':
            score = 0.45
        elif stability == 'hygroscopic':
            score = 0.5

        # Reactive metals penalty with oxide ceramics
        metal_meta = metal.metadata or {}
        if metal_meta.get('reactive', False) and ceramic.ceramic_class.name == 'OXIDE':
            score *= 0.7
            details['reactive_metal_penalty'] = True

    return max(0.0, min(1.0, score)), details


def score_coating_compatibility(
    ceramic_name: str,
    metal_name: str,
    deposition_method: Optional[DepositionMethod] = None,
) -> CeramicMetalResult:
    """
    Score compatibility between a ceramic coating/layer and a metal substrate.

    Args:
        ceramic_name: Name in ceramic_bridge (e.g., 'Al2O3', 'TiN')
        metal_name: Name in metal_bridge (e.g., 'SS_304', 'Ti6Al4V')
        deposition_method: Optional processing method. When set, CTE compliance
            factor is applied for thin-film methods (PVD/CVD/ALD) and only the
            specified processing route is evaluated for thermal scoring.

    Returns:
        CeramicMetalResult with component scores and composite
    """
    warnings = []

    ceramic = get_ceramic(ceramic_name)
    if ceramic is None:
        return CeramicMetalResult(
            compatible=False, score=0.0,
            cte_compatibility=0.0, thermal_processing=0.0,
            mechanical_compatibility=0.0, chemical_interaction=0.0,
            ceramic_name=ceramic_name, metal_name=metal_name,
            warnings=[f"Unknown ceramic: {ceramic_name}"],
        )

    metal = get_metal(metal_name)
    if metal is None:
        return CeramicMetalResult(
            compatible=False, score=0.0,
            cte_compatibility=0.0, thermal_processing=0.0,
            mechanical_compatibility=0.0, chemical_interaction=0.0,
            ceramic_name=ceramic_name, metal_name=metal_name,
            warnings=[f"Unknown metal: {metal_name}"],
        )

    # Score each dimension
    cte_score, cte_details = _score_cte_compatibility(ceramic, metal, deposition_method)
    tp_score, tp_details = _score_thermal_processing(ceramic, metal, deposition_method)
    mech_score, mech_details = _score_mechanical_compatibility(ceramic, metal)
    chem_score, chem_details = _score_chemical_interaction(ceramic, metal)

    # Composite: CTE is dominant failure mode
    composite = (
        0.35 * cte_score +
        0.25 * tp_score +
        0.20 * mech_score +
        0.20 * chem_score
    )

    # CTE veto: extreme mismatch
    if cte_score < 0.15:
        composite = min(composite, 0.25)
        warnings.append(
            f"CTE veto: {ceramic_name} ({ceramic.cte_per_K}) vs "
            f"{metal_name} ({metal.cte_per_K}) x10^-6/K"
        )

    # Thermal impossibility veto
    if tp_score < 0.1:
        composite = min(composite, 0.20)
        warnings.append(
            f"Thermal veto: {ceramic_name} sintering ({ceramic.sintering_temp_C}C) "
            f"exceeds {metal_name} melting ({metal.melting_point_C}C)"
        )

    compatible = composite >= 0.50

    return CeramicMetalResult(
        compatible=compatible,
        score=round(composite, 4),
        cte_compatibility=round(cte_score, 4),
        thermal_processing=round(tp_score, 4),
        mechanical_compatibility=round(mech_score, 4),
        chemical_interaction=round(chem_score, 4),
        ceramic_name=ceramic_name,
        metal_name=metal_name,
        warnings=warnings,
        details={
            'cte': cte_details,
            'thermal_processing': tp_details,
            'mechanical': mech_details,
            'chemical': chem_details,
        },
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Ceramic-Metal Cross-Bridge Demo")
    print("=" * 60)
    print()

    test_cases = [
        ('Al2O3', 'SS_304', 'Alumina on stainless steel'),
        ('TiN', 'Ti6Al4V', 'TiN coating on Ti alloy (excellent)'),
        ('TiN', 'Steel_4140', 'TiN on tool steel'),
        ('ZrO2_YSZ', 'Inconel_718', 'Thermal barrier coating'),
        ('SiO2', 'Al', 'SiO2 on Al (CTE mismatch)'),
        ('Al2O3', 'Mg', 'Alumina on Mg (bad)'),
        ('SiC', 'Steel_4140', 'SiC on tool steel'),
    ]

    for ceramic, metal, desc in test_cases:
        r = score_coating_compatibility(ceramic, metal)
        status = "PASS" if r.compatible else "FAIL"
        print(f"  [{status}] {ceramic}+{metal}: {r.score:.3f}  ({desc})")
        if r.warnings:
            for w in r.warnings:
                print(f"         WARNING: {w}")
    print()
