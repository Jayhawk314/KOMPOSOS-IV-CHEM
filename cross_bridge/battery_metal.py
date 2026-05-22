# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery-Metal Cross-Bridge Functor
====================================

Scores compatibility between battery electrodes/electrolytes and metal
current collectors. This is the functor F: Battery -> Metal that maps
electrochemical stability constraints into metal selection criteria.

Key cross-domain questions answered:
- Will this metal corrode in this electrolyte at operating voltage?
- Is the CTE match adequate for thermal cycling?
- Does this metal have sufficient conductivity for current collection?
- What is the galvanic risk at the metal-electrode interface?
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, VoltageWindow,
    get_material as get_battery_material,
    ALL_MATERIALS as ALL_BATTERY_MATERIALS,
)
from metal_bridge.material_properties import (
    MetalMaterial,
    get_metal,
    ALL_METALS,
)
from oracle.compatibility_context import CompatibilityContext
from oracle.enrichment import summarize_compatibility_components
from oracle.typed_morphisms import apply_typed_morphism_adjustment


# ============================================================================
# Known cross-domain pairs
# ============================================================================

KNOWN_GOOD_PAIRS: List[Tuple[str, str, str]] = [
    # (metal, electrode, electrolyte_or_note)
    ('Al_foil', 'LFP', 'LiPF6'),       # Standard cathode collector + LiPF6
    ('Al_foil', 'NMC811', 'LiPF6'),     # Standard cathode collector + LiPF6
    ('Al_foil', 'LCO', 'LiPF6'),        # Standard cathode collector + LiPF6
    ('Cu_foil', 'Graphite', 'LiPF6'),   # Standard anode collector
    ('Cu_foil', 'Si', 'LiPF6'),         # Anode collector for Si
    ('Cu_foil', 'Li_metal', 'LiPF6'),   # Anode collector for Li metal
    ('Ni_tab', 'LFP', 'LiPF6'),        # Nickel tab for welding
]

KNOWN_BAD_PAIRS: List[Tuple[str, str, str]] = [
    # (metal, electrode, electrolyte_or_note)
    ('Al_foil', 'LFP', 'LiTFSI'),      # Al corrodes in LiTFSI above 3.7V
    ('Al_foil', 'NMC811', 'LiTFSI'),    # Same Al corrosion issue
    ('Cu_foil', 'NMC811', 'LiPF6'),     # Cu dissolves at cathode potentials (>3V)
    ('Cu_foil', 'LFP', 'LiPF6'),        # Cu dissolves at cathode potentials
]


# Metal electrochemical properties for battery context
# (oxidation potential in V vs Li/Li+ where metal dissolution begins)
METAL_ANODIC_LIMITS = {
    'Al_foil': 3.7,    # Al passivates in LiPF6 but corrodes in LiTFSI
    'Al': 3.7,
    'Cu_foil': 3.0,    # Cu dissolves above ~3V vs Li/Li+
    'Cu': 3.0,
    'Ni_tab': 4.5,     # Ni relatively stable
    'Ni': 4.5,
    'Ti': 4.8,         # Ti very stable
    'SS_304': 4.2,     # Stainless steel decent
    'SS_316': 4.3,     # 316 slightly better
}

# Metal cathodic limits (below this voltage, reduction/plating issues)
METAL_CATHODIC_LIMITS = {
    'Al_foil': 0.1,    # Al OK as cathode collector (high voltage side)
    'Al': 0.1,
    'Cu_foil': -0.1,   # Cu stable at low potentials (anode side)
    'Cu': -0.1,
    'Ni_tab': 0.0,
    'Ni': 0.0,
    'Ti': -0.1,
    'SS_304': 0.0,
    'SS_316': 0.0,
}

# Coating anodic stability boost (V added to bare metal limit)
# Source: literature on coated current collectors for Li-ion batteries
COATING_ANODIC_BOOST = {
    'carbon': 1.5,    # Carbon-coated Cu stable to ~4.5V (Myung et al., ACS Energy Lett., 2017)
    'Al2O3': 1.0,     # ALD Al2O3 adds ~1V margin (Jung et al., J. Electrochem. Soc., 2010)
    'TiN': 1.2,       # TiN protective coating (Park et al., J. Power Sources, 2014)
}


# Electrolyte-specific corrosion modifiers
ELECTROLYTE_CORROSION = {
    # (metal_key, electrolyte): corrosion_factor (1.0 = no extra corrosion)
    ('Al', 'LiTFSI'): 5.0,       # Al corrodes severely in LiTFSI
    ('Al_foil', 'LiTFSI'): 5.0,
    ('Cu', 'LiPF6'): 1.0,        # Cu fine in LiPF6 (if at low voltage)
    ('Cu_foil', 'LiPF6'): 1.0,
}


def _metal_lookup_candidates(metal: MetalMaterial, metal_key: Optional[str] = None) -> List[str]:
    """Names/formulas used by the battery-metal rule tables."""

    candidates = []
    if metal_key:
        candidates.extend([
            metal_key,
            metal_key.replace('_foil', '').replace('_tab', ''),
        ])
    candidates.extend([metal.name, metal.formula])

    normalized = []
    for candidate in candidates:
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


@dataclass
class BatteryMetalResult:
    """Result of cross-domain battery-metal compatibility scoring."""
    compatible: bool
    score: float                        # 0-1 composite
    electrochemical_stability: float    # Metal stable at operating voltage?
    galvanic_risk: float               # Galvanic coupling risk (1=low risk)
    cte_compatibility: float           # CTE match for thermal cycling
    conductivity_score: float          # Adequate electrical conductivity?
    corrosion_risk: float              # Electrolyte corrosion (1=low risk)
    metal_name: str
    electrode_name: str
    electrolyte_name: Optional[str]
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _score_electrochemical_stability(
    metal: MetalMaterial,
    battery_mat: BatteryMaterial,
    electrolyte: Optional[BatteryMaterial] = None,
    metal_coating: Optional[str] = None,
    metal_key: Optional[str] = None,
) -> Tuple[float, Dict]:
    """
    Score whether the metal is electrochemically stable at the electrode's
    operating voltage.

    If metal_coating is set (or metal.coating is set), the anodic limit
    is boosted to reflect the protective coating's effect.
    """
    details = {}

    # Get metal's anodic/cathodic limits
    candidates = _metal_lookup_candidates(metal, metal_key)
    anodic_limit = next(
        (METAL_ANODIC_LIMITS[name] for name in candidates if name in METAL_ANODIC_LIMITS),
        4.0,
    )
    cathodic_limit = next(
        (METAL_CATHODIC_LIMITS[name] for name in candidates if name in METAL_CATHODIC_LIMITS),
        0.0,
    )

    # Apply coating boost if present
    coating = metal_coating or metal.coating
    if coating:
        boost = COATING_ANODIC_BOOST.get(coating, 0.5)
        anodic_limit += boost
        details['coating'] = coating
        details['anodic_limit_boosted_V'] = anodic_limit

    details['metal_anodic_limit_V'] = anodic_limit
    details['metal_cathodic_limit_V'] = cathodic_limit

    if battery_mat.voltage_window is not None:
        v_upper = battery_mat.voltage_window.upper
        v_lower = battery_mat.voltage_window.lower
        details['electrode_voltage_range'] = f"{v_lower:.1f}-{v_upper:.1f}V"

        # For cathode collectors (Al): need anodic stability above v_upper
        # For anode collectors (Cu): need cathodic stability below v_lower
        mat_class = battery_mat.material_class

        if mat_class == MaterialClass.CATHODE:
            margin = anodic_limit - v_upper
            details['stability_margin_V'] = margin
            details['collector_role'] = 'cathode_collector'
            if margin > 0.5:
                score = 1.0
            elif margin > 0.2:
                score = 0.8
            elif margin > 0.0:
                score = 0.5
            else:
                score = 0.1  # Metal will dissolve
        elif mat_class == MaterialClass.ANODE:
            margin = v_lower - cathodic_limit
            details['stability_margin_V'] = margin
            details['collector_role'] = 'anode_collector'
            if margin > 0.5:
                score = 1.0
            elif margin > 0.2:
                score = 0.8
            elif margin > 0.0:
                score = 0.5
            else:
                score = 0.1
        else:
            # Electrolyte or other - check both limits
            score = 0.7
            details['collector_role'] = 'general'
    else:
        score = 0.6
        details['note'] = 'No voltage window on battery material'

    return score, details


def _score_galvanic_risk(
    metal: MetalMaterial,
    battery_mat: BatteryMaterial,
) -> Tuple[float, Dict]:
    """
    Score galvanic coupling risk between metal collector and electrode.
    Lower galvanic potential difference = lower risk = higher score.
    """
    details = {}

    metal_potential = metal.galvanic_potential_V
    details['metal_galvanic_V'] = metal_potential

    if metal_potential is not None:
        # Battery materials don't have galvanic_potential_V directly,
        # but we can estimate from their redox potentials
        if battery_mat.oxidation_potential is not None:
            # Use the effective electrochemical potential
            bat_potential = battery_mat.oxidation_potential
            diff = abs(metal_potential - (-3.04 + bat_potential))  # Convert Li scale to SCE approx
            details['estimated_galvanic_diff_V'] = diff
        else:
            # Use heuristic based on material class
            diff = 0.3  # Moderate default
            details['galvanic_diff_estimated'] = True

        if diff < 0.1:
            score = 1.0
        elif diff < 0.3:
            score = 0.85
        elif diff < 0.5:
            score = 0.7
        elif diff < 1.0:
            score = 0.5
        else:
            score = 0.25
    else:
        score = 0.6  # Unknown galvanic potential

    return score, details


def _score_cte_compatibility(
    metal: MetalMaterial,
    battery_mat: BatteryMaterial,
) -> Tuple[float, Dict]:
    """
    Score CTE compatibility for thermal cycling.
    Battery packs see -20C to +60C range during operation.
    """
    details = {}

    metal_cte = metal.cte_per_K
    details['metal_cte_per_K'] = metal_cte

    if metal_cte is not None:
        # Battery materials CTE approximations
        BATTERY_CTE_APPROX = {
            'LFP': 10.0,    # Olivine structure
            'NMC811': 12.0,  # Layered oxide
            'NMC622': 12.0,
            'NMC111': 12.0,
            'LCO': 13.0,    # Layered oxide
            'LMO': 8.0,     # Spinel
            'Graphite': 1.0, # In-plane (highly anisotropic)
            'Si': 2.6,      # Diamond cubic
            'LTO': 8.0,     # Spinel
            'Li_metal': 46.0, # Very high CTE
        }

        bat_cte = BATTERY_CTE_APPROX.get(battery_mat.name, 10.0)
        details['battery_cte_approx'] = bat_cte

        diff = abs(metal_cte - bat_cte)
        details['cte_difference'] = diff

        if diff < 3.0:
            score = 1.0
        elif diff < 6.0:
            score = 0.85
        elif diff < 10.0:
            score = 0.65
        elif diff < 20.0:
            score = 0.4
        else:
            score = 0.2
    else:
        score = 0.6

    return score, details


def _score_conductivity(
    metal: MetalMaterial,
) -> Tuple[float, Dict]:
    """
    Score metal electrical conductivity for current collection.
    Current collectors need high conductivity.
    """
    details = {}

    resistivity = metal.electrical_resistivity_ohm_m
    details['resistivity_ohm_m'] = resistivity

    if resistivity is not None:
        # Cu: 1.68e-8, Al: 2.65e-8, Ni: 6.99e-8, Steel: ~1.4e-7
        if resistivity < 3e-8:
            score = 1.0      # Cu, Al class
        elif resistivity < 1e-7:
            score = 0.85     # Ni class
        elif resistivity < 5e-7:
            score = 0.6      # Steel class
        else:
            score = 0.3      # Poor conductor
        details['conductivity_class'] = (
            'excellent' if score > 0.9 else
            'good' if score > 0.7 else
            'moderate' if score > 0.5 else 'poor'
        )
    else:
        score = 0.6

    return score, details


def _score_corrosion_risk(
    metal: MetalMaterial,
    electrolyte: Optional[BatteryMaterial] = None,
    metal_key: Optional[str] = None,
) -> Tuple[float, Dict]:
    """
    Score corrosion risk from electrolyte on metal collector.
    Returns 1.0 = low corrosion risk, 0.0 = severe corrosion.
    """
    details = {}
    score = 0.8  # Default: moderate confidence

    if electrolyte is not None:
        details['electrolyte'] = electrolyte.name

        # Check known corrosion pairs
        corrosion_factor = 1.0
        for candidate in _metal_lookup_candidates(metal, metal_key):
            corrosion_factor = max(
                corrosion_factor,
                ELECTROLYTE_CORROSION.get((candidate, electrolyte.name), 1.0),
            )

        details['corrosion_factor'] = corrosion_factor

        if corrosion_factor > 3.0:
            score = 0.1  # Severe corrosion (e.g., Al in LiTFSI)
            details['corrosion_risk'] = 'severe'
        elif corrosion_factor > 1.5:
            score = 0.4
            details['corrosion_risk'] = 'moderate'
        else:
            score = 0.9
            details['corrosion_risk'] = 'low'

    # Factor in general corrosion rate
    if metal.corrosion_rate_mm_yr is not None:
        details['base_corrosion_rate_mm_yr'] = metal.corrosion_rate_mm_yr
        if metal.corrosion_rate_mm_yr > 0.5:
            score *= 0.7
        elif metal.corrosion_rate_mm_yr > 0.1:
            score *= 0.85

    return max(0.0, min(1.0, score)), details


def score_collector_compatibility(
    metal_name: str,
    electrode_name: str,
    electrolyte_name: Optional[str] = None,
    metal_coating: Optional[str] = None,
    interface_role: Optional[str] = None,
) -> BatteryMetalResult:
    """
    Score compatibility between a metal current collector and a battery
    electrode, optionally considering a specific electrolyte.

    Args:
        metal_name: Name in metal_bridge (e.g., 'Al_foil', 'Cu_foil')
        electrode_name: Name in battery_bridge (e.g., 'LFP', 'Graphite')
        electrolyte_name: Optional name in battery_bridge (e.g., 'LiPF6')
        metal_coating: Optional coating on the metal (e.g., 'carbon', 'Al2O3', 'TiN').
            Boosts the metal's anodic stability limit per COATING_ANODIC_BOOST.
        interface_role: Optional contextual role such as 'cathode_collector',
            'anode_collector', or 'tab_connector'. Tabs are not scored as if
            they were the whole current-collector/electrode coating interface.

    Returns:
        BatteryMetalResult with component scores and composite
    """
    warnings = []

    metal = get_metal(metal_name)
    if metal is None:
        return BatteryMetalResult(
            compatible=False, score=0.0,
            electrochemical_stability=0.0, galvanic_risk=0.0,
            cte_compatibility=0.0, conductivity_score=0.0, corrosion_risk=0.0,
            metal_name=metal_name, electrode_name=electrode_name,
            electrolyte_name=electrolyte_name,
            warnings=[f"Unknown metal: {metal_name}"],
        )

    electrode = get_battery_material(electrode_name)
    if electrode is None:
        return BatteryMetalResult(
            compatible=False, score=0.0,
            electrochemical_stability=0.0, galvanic_risk=0.0,
            cte_compatibility=0.0, conductivity_score=0.0, corrosion_risk=0.0,
            metal_name=metal_name, electrode_name=electrode_name,
            electrolyte_name=electrolyte_name,
            warnings=[f"Unknown electrode: {electrode_name}"],
        )

    electrolyte = None
    if electrolyte_name:
        electrolyte = get_battery_material(electrolyte_name)
        if electrolyte is None:
            warnings.append(f"Unknown electrolyte: {electrolyte_name}")

    role = (interface_role or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not role:
        if metal_name.endswith("_tab"):
            role = "tab_connector"
        elif electrode.material_class == MaterialClass.CATHODE:
            role = "cathode_collector"
        elif electrode.material_class == MaterialClass.ANODE:
            role = "anode_collector"
        else:
            role = "current_collector"

    # Score each dimension
    ec_score, ec_details = _score_electrochemical_stability(
        metal, electrode, electrolyte, metal_coating=metal_coating, metal_key=metal_name
    )
    g_score, g_details = _score_galvanic_risk(metal, electrode)
    cte_score, cte_details = _score_cte_compatibility(metal, electrode)
    cond_score, cond_details = _score_conductivity(metal)
    corr_score, corr_details = _score_corrosion_risk(metal, electrolyte, metal_key=metal_name)

    # Check known pairs
    if electrolyte_name:
        triple = (metal_name, electrode_name, electrolyte_name)
        if triple in KNOWN_GOOD_PAIRS:
            ec_score = max(ec_score, 0.9)
            corr_score = max(corr_score, 0.9)
        elif triple in KNOWN_BAD_PAIRS:
            coating_mitigates = (
                metal_coating is not None
                and metal_name.startswith("Cu")
                and electrolyte_name == "LiPF6"
            )
            if coating_mitigates:
                ec_details["known_bad_pair_mitigated_by_coating"] = metal_coating
            else:
                corr_score = min(corr_score, 0.15)
                warnings.append(
                    f"Known bad combination: {metal_name}+{electrode_name}+{electrolyte_name}"
                )

    base_metal = metal_name.replace('_foil', '').replace('_tab', '')
    is_lipf6 = electrolyte_name == "LiPF6"
    is_cathode = electrode.material_class == MaterialClass.CATHODE
    is_tab_role = role in {"tab", "tab_connector", "collector_tab", "cell_tab"}

    if base_metal == "Al" and is_lipf6 and is_cathode:
        ec_score = max(ec_score, 0.85)
        corr_score = max(corr_score, 0.9)
        ec_details["li_pf6_al_passivation"] = True
        corr_details["li_pf6_al_passivation"] = True

    if base_metal == "Ni" and is_lipf6 and is_cathode and is_tab_role:
        ec_score = max(ec_score, 0.75)
        corr_score = max(corr_score, 0.85)
        cond_score = max(cond_score, 0.75)
        ec_details["tab_role_adjustment"] = "Ni tab connector in LiPF6 cathode hardware"
        cond_details["tab_role_adjustment"] = "tab connector duty, not full collector foil duty"

    if base_metal == "Cu" and metal_coating and is_lipf6 and is_cathode:
        margin = ec_details.get("stability_margin_V")
        if margin is not None and margin >= 0.0:
            ec_score = max(ec_score, 0.7)
            corr_score = max(corr_score, 0.8)
            ec_details["coated_cu_cathode_adjustment"] = True

    ec_details["context_role"] = role

    # Composite: electrochemical stability and corrosion are critical
    composite = (
        0.30 * ec_score +
        0.15 * g_score +
        0.10 * cte_score +
        0.15 * cond_score +
        0.30 * corr_score
    )

    # Electrochemical veto
    if ec_score < 0.2:
        composite = min(composite, 0.25)
        warnings.append(
            f"Electrochemical veto: {metal_name} unstable at "
            f"{electrode_name} operating voltage"
        )

    # Corrosion veto
    if corr_score < 0.15:
        composite = min(composite, 0.25)
        warnings.append(
            f"Corrosion veto: {metal_name} corrodes in {electrolyte_name}"
        )

    base_composite = composite
    base_compatible = base_composite >= 0.50
    morphism_context = CompatibilityContext(
        role=role,
        electrolyte=electrolyte_name,
        coating=metal_coating,
    )
    morphism_adjustment = apply_typed_morphism_adjustment(
        base_composite,
        base_compatible,
        metal_name,
        electrode_name,
        "battery-metal",
        morphism_context,
    )
    if morphism_adjustment.action in {"veto", "negative_prior", "positive_prior"}:
        composite = morphism_adjustment.score
        if morphism_adjustment.action in {"veto", "negative_prior"}:
            warnings.append(
                f"Typed morphism {morphism_adjustment.action}: "
                f"{morphism_adjustment.morphism.relation}"
            )

    compatible = composite >= 0.50
    component_scores = {
        'electrochemical_stability': ec_score,
        'galvanic_risk': g_score,
        'cte_compatibility': cte_score,
        'conductivity_score': cond_score,
        'corrosion_risk': corr_score,
    }

    return BatteryMetalResult(
        compatible=compatible,
        score=round(composite, 4),
        electrochemical_stability=round(ec_score, 4),
        galvanic_risk=round(g_score, 4),
        cte_compatibility=round(cte_score, 4),
        conductivity_score=round(cond_score, 4),
        corrosion_risk=round(corr_score, 4),
        metal_name=metal_name,
        electrode_name=electrode_name,
        electrolyte_name=electrolyte_name,
        warnings=warnings,
        details={
            'electrochemical': ec_details,
            'galvanic': g_details,
            'cte': cte_details,
            'conductivity': cond_details,
            'corrosion': corr_details,
            'enriched_quantales': summarize_compatibility_components(component_scores),
            'typed_morphism': morphism_adjustment.to_dict(),
            'context': {
                'role': role,
                'metal_coating': metal_coating,
            },
        },
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Battery-Metal Cross-Bridge Demo")
    print("=" * 60)
    print()

    test_cases = [
        ('Al_foil', 'LFP', 'LiPF6', 'Standard cathode+Al+LiPF6'),
        ('Al_foil', 'NMC811', 'LiPF6', 'High-V cathode+Al+LiPF6'),
        ('Al_foil', 'LFP', 'LiTFSI', 'Al corrosion in LiTFSI'),
        ('Cu_foil', 'Graphite', 'LiPF6', 'Standard anode+Cu'),
        ('Cu_foil', 'NMC811', 'LiPF6', 'Cu at cathode voltage (bad)'),
        ('Ni_tab', 'LFP', 'LiPF6', 'Ni tab connection'),
    ]

    for metal, electrode, elyte, desc in test_cases:
        r = score_collector_compatibility(metal, electrode, elyte)
        status = "PASS" if r.compatible else "FAIL"
        print(f"  [{status}] {metal}+{electrode}+{elyte}: {r.score:.3f}  ({desc})")
        if r.warnings:
            for w in r.warnings:
                print(f"         WARNING: {w}")
    print()
