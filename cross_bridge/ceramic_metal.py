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


class InterfaceRole(Enum):
    """The role/application of the ceramic-metal interface."""
    COATING = "coating"
    STRUCTURAL_COMPOSITE = "structural_composite"
    CONTAINER_CRUCIBLE = "container_crucible"


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
    ('SiC', 'Al_6061'),      # SiC/Al MMC - commercially established structural composite
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
    role: InterfaceRole = InterfaceRole.COATING,
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

        # Structural composites (MMCs): metal matrix accommodates CTE mismatch
        # via plastic deformation; powder metallurgy processing avoids worst
        # thermal stress. Floor at 0.35 — even large CTE diff is manageable in MMCs.
        if role == InterfaceRole.STRUCTURAL_COMPOSITE:
            score = max(score, 0.35)
            details['mmc_relaxation'] = True
    else:
        score = 0.5  # Unknown CTE
        details['note'] = 'Missing CTE data'

    return score, details


def _score_thermal_processing(
    ceramic: CeramicMaterial,
    metal: MetalMaterial,
    deposition_method: Optional[DepositionMethod] = None,
    role: InterfaceRole = InterfaceRole.COATING,
) -> Tuple[float, Dict]:
    """
    Score whether the ceramic can be processed onto the metal substrate.

    Real ceramic-metal coatings use multiple deposition methods:
    - Bulk sintering: requires sintering_temp < metal melting
    - PVD/CVD: substrate stays below 500C (most ceramics depositable)
    - Plasma spray: substrate stays below 300C

    Structural composites and crucibles often use different processing
    routes (e.g. powder metallurgy, infiltration) that are less constrained
     by the coating-on-substrate melting model.
    """
    details = {}
    details['role'] = role.value

    # Structural composites and crucibles are less sensitive to substrate melting
    # during coating, as the metal is often the matrix or being melted into it.
    if role in (InterfaceRole.STRUCTURAL_COMPOSITE, InterfaceRole.CONTAINER_CRUCIBLE):
        details['note'] = f'Thermal processing constraints relaxed for {role.value}'
        return 0.85, details

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


def score_ceramic_metal_compatibility(
    ceramic_name: str,
    metal_name: str,
    deposition_method: Optional[DepositionMethod] = None,
    role: InterfaceRole = InterfaceRole.COATING,
) -> CeramicMetalResult:
    """
    Score compatibility between a ceramic and a metal for a given role.

    Args:
        ceramic_name: Name in ceramic_bridge
        metal_name: Name in metal_bridge
        deposition_method: Optional processing method
        role: The application role (COATING, STRUCTURAL_COMPOSITE, CONTAINER_CRUCIBLE)

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
    cte_score, cte_details = _score_cte_compatibility(ceramic, metal, deposition_method, role)
    tp_score, tp_details = _score_thermal_processing(ceramic, metal, deposition_method, role)
    mech_score, mech_details = _score_mechanical_compatibility(ceramic, metal)
    chem_score, chem_details = _score_chemical_interaction(ceramic, metal)

    # Composite weights depend on role
    if role == InterfaceRole.COATING:
        composite = (
            0.35 * cte_score +
            0.25 * tp_score +
            0.20 * mech_score +
            0.20 * chem_score
        )
    elif role == InterfaceRole.STRUCTURAL_COMPOSITE:
        # Focus more on mechanical match and chemical stability
        composite = (
            0.30 * cte_score +
            0.10 * tp_score +
            0.30 * mech_score +
            0.30 * chem_score
        )
    else:  # CONTAINER_CRUCIBLE
        # Focus on chemical inertness
        composite = (
            0.15 * cte_score +
            0.10 * tp_score +
            0.15 * mech_score +
            0.60 * chem_score
        )

    # Vetoes
    # Thin film coatings delaminate easily (strict veto)
    # Structural composites/crucibles can handle more strain (relaxed veto)
    cte_veto_threshold = 0.15 if role == InterfaceRole.COATING else 0.05
    if cte_score < cte_veto_threshold:
        composite = min(composite, 0.25)
        warnings.append(f"CTE veto: {ceramic_name} vs {metal_name} mismatch (too extreme for {role.value})")

    if tp_score < 0.1:
        composite = min(composite, 0.20)
        warnings.append(f"Thermal veto: Processing temp exceeds metal melting point")

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
            'role': role.value,
            'cte': cte_details,
            'thermal_processing': tp_details,
            'mechanical': mech_details,
            'chemical': chem_details,
        },
    )


def score_coating_compatibility(
    ceramic_name: str,
    metal_name: str,
    deposition_method: Optional[DepositionMethod] = None,
) -> CeramicMetalResult:
    """Legacy wrapper for backward compatibility."""
    return score_ceramic_metal_compatibility(
        ceramic_name, metal_name, deposition_method, role=InterfaceRole.COATING
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Ceramic-Metal Cross-Bridge Demo")
    print("=" * 60)
    print()

    test_cases = [
        ('Al2O3', 'SS_304', InterfaceRole.COATING, 'Alumina coating on stainless'),
        ('TiN', 'Ti6Al4V', InterfaceRole.COATING, 'TiN coating (excellent)'),
        ('SiC', 'Al_6061', InterfaceRole.COATING, 'SiC coating on Al (Fails thermal)'),
        ('SiC', 'Al_6061', InterfaceRole.STRUCTURAL_COMPOSITE, 'SiC/Al MMC (Should pass)'),
    ]

    for ceramic, metal, role, desc in test_cases:
        r = score_ceramic_metal_compatibility(ceramic, metal, role=role)
        status = "PASS" if r.compatible else "FAIL"
        print(f"  [{status}] {ceramic}+{metal} ({role.value}): {r.score:.3f}  ({desc})")
        if r.warnings:
            for w in r.warnings:
                print(f"         WARNING: {w}")
    print()
