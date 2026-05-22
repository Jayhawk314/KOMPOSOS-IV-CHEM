# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery-Polymer Cross-Bridge Functor
======================================

Scores compatibility between battery electrodes/electrolytes and polymer
binders/electrolytes/coatings. This is the functor F: Battery -> Polymer
that maps electrochemical constraints into polymer selection criteria.

Key cross-domain questions answered:
- Can this polymer survive the voltage window of this electrode?
- Is this polymer thermally stable at battery operating temperature?
- Can this polymer accommodate electrode volume changes during cycling?
- Is this polymer chemically resistant to the electrolyte environment?
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, VoltageWindow,
    get_material as get_battery_material,
    ALL_MATERIALS as ALL_BATTERY_MATERIALS,
)
from polymer_bridge.material_properties import (
    PolymerMaterial,
    get_polymer,
    ALL_POLYMERS,
)
from oracle.enrichment import summarize_compatibility_components


# ============================================================================
# Known cross-domain pairs (ground truth from literature)
# ============================================================================

KNOWN_GOOD_PAIRS: List[Tuple[str, str]] = [
    # (polymer, battery_material)
    ('PVDF', 'LFP'),       # Standard cathode binder
    ('PVDF', 'NMC811'),    # Standard cathode binder (within voltage window)
    ('PVDF', 'Graphite'),  # Standard anode binder
    ('CMC', 'Graphite'),   # Water-based anode binder
    ('SBR', 'Graphite'),   # Co-binder with CMC for anodes
    ('PEO', 'LFP'),        # Polymer electrolyte for LFP (3.4V, within PEO window)
    ('PTFE', 'LFP'),       # Alternative binder, chemically inert
    ('PAN', 'LFP'),        # Separator/gel electrolyte
]

KNOWN_BAD_PAIRS: List[Tuple[str, str]] = [
    # (polymer, battery_material)
    ('PEO', 'NMC811'),     # PEO oxidizes above ~3.8V; NMC811 operates at 3.8V+
    ('CMC', 'NMC811'),     # CMC water-based processing incompatible with high-voltage cathodes
    ('SBR', 'NMC811'),     # SBR same issue as CMC
    ('PEO', 'LCO'),        # PEO voltage limit too low for LCO (3.9V nominal)
]


@dataclass
class BatteryPolymerResult:
    """Result of cross-domain battery-polymer compatibility scoring."""
    compatible: bool
    score: float                          # 0-1 composite
    voltage_compatibility: float          # Can polymer survive electrode voltage?
    thermal_compatibility: float          # Polymer stable at battery temp?
    mechanical_compatibility: float       # Polymer handles volume expansion?
    chemical_compatibility: float         # Polymer resists electrolyte?
    polymer_name: str
    battery_material_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _score_voltage_compatibility(
    polymer: PolymerMaterial,
    battery_mat: BatteryMaterial,
) -> Tuple[float, Dict]:
    """
    Score whether the polymer can survive the electrode's voltage window.

    PEO is known to oxidize above ~3.8-4.0V vs Li/Li+.
    PVDF is stable to ~5V.
    PTFE is stable to ~5V+.
    Most polymers don't have explicit voltage limits, so we use heuristics
    based on their known battery applications.
    """
    details = {}

    # Polymer electrochemical stability windows (V vs Li/Li+)
    # From literature: Xu, Chem Rev 2004; Goodenough & Kim, Chem Mater 2010
    POLYMER_VOLTAGE_LIMITS = {
        'PEO': 3.8,        # Oxidizes above 3.8V
        'PVDF': 5.0,       # Stable to ~5V
        'PTFE': 5.5,       # Very stable
        'CMC': 4.5,        # Stable but water processing limits cathode choice
        'SBR': 4.5,        # Same as CMC
        'PAN': 4.8,        # Good stability
    }

    # Use abbreviation (e.g., 'PVDF') not full name ('Polyvinylidene Fluoride')
    poly_key = getattr(polymer, 'abbreviation', polymer.name)
    polymer_limit = POLYMER_VOLTAGE_LIMITS.get(poly_key, 4.0)
    details['polymer_voltage_limit_V'] = polymer_limit

    # Get electrode operating voltage
    # Use nominal voltage for compatibility (not upper cutoff which is a brief peak)
    # PEO+LFP works at 3.4V nominal even though LFP upper cutoff is 4.0V
    if battery_mat.voltage_window is not None:
        electrode_voltage = battery_mat.voltage_window.upper
        nominal = battery_mat.voltage_window.nominal
        details['electrode_upper_V'] = electrode_voltage
        details['electrode_nominal_V'] = nominal

        # Margin based on nominal operating voltage (primary check)
        margin = polymer_limit - nominal
        details['voltage_margin_V'] = margin

        if margin >= 1.0:
            score = 1.0
        elif margin >= 0.5:
            score = 0.9
        elif margin >= 0.2:
            score = 0.7
        elif margin >= 0.0:
            score = 0.5
        elif margin >= -0.2:
            score = 0.25    # Marginal - polymer near its limit
        else:
            score = 0.05    # Polymer will decompose
    else:
        # No voltage window data (e.g., electrolyte salts/solvents)
        score = 0.7  # Neutral
        details['note'] = 'No voltage window on battery material'

    return score, details


def _score_thermal_compatibility(
    polymer: PolymerMaterial,
    battery_mat: BatteryMaterial,
    operating_temp_C: float = 25.0,
) -> Tuple[float, Dict]:
    """
    Score thermal compatibility between polymer and battery material.

    Checks:
    - Polymer doesn't decompose at operating/processing temp
    - Polymer Tg is appropriate (below operating temp for flexibility)
    - Battery material thermal stability
    """
    details = {}

    # Polymer decomposition check
    poly_decomp = polymer.decomposition_temp_C
    details['polymer_decomposition_C'] = poly_decomp
    details['operating_temp_C'] = operating_temp_C

    if poly_decomp is not None:
        thermal_margin = poly_decomp - operating_temp_C
        details['thermal_margin_C'] = thermal_margin

        if thermal_margin > 200:
            decomp_score = 1.0
        elif thermal_margin > 100:
            decomp_score = 0.9
        elif thermal_margin > 50:
            decomp_score = 0.7
        elif thermal_margin > 0:
            decomp_score = 0.4
        else:
            decomp_score = 0.05
    else:
        decomp_score = 0.6  # Unknown decomp temp

    # Tg check (polymer should be above or below Tg depending on application)
    poly_tg = polymer.glass_transition_C
    if poly_tg is not None:
        details['polymer_Tg_C'] = poly_tg
        # For binders: Tg below operating temp = flexible = good
        # For structural: Tg above operating temp = rigid = good
        # Default: below Tg is better for battery applications (flexibility)
        if operating_temp_C > poly_tg:
            tg_score = 0.9  # Above Tg, rubbery = flexible binder
        else:
            tg_score = 0.6  # Below Tg, glassy = less flexible
    else:
        tg_score = 0.7

    # Battery material thermal stability
    bat_thermal = battery_mat.thermal_stability_max
    if bat_thermal is not None:
        details['battery_thermal_max_C'] = bat_thermal
        bat_margin = bat_thermal - operating_temp_C
        if bat_margin > 100:
            bat_score = 1.0
        elif bat_margin > 50:
            bat_score = 0.8
        else:
            bat_score = 0.5
    else:
        bat_score = 0.7

    score = 0.5 * decomp_score + 0.3 * tg_score + 0.2 * bat_score
    details['decomp_score'] = decomp_score
    details['tg_score'] = tg_score
    details['battery_thermal_score'] = bat_score

    return score, details


def _score_mechanical_compatibility(
    polymer: PolymerMaterial,
    battery_mat: BatteryMaterial,
) -> Tuple[float, Dict]:
    """
    Score mechanical compatibility.

    Key concern: electrode volume expansion during cycling must be
    accommodated by the polymer binder/matrix.
    """
    details = {}

    # Electrode volume expansion (fractional, 0-3.0+)
    vol_exp = battery_mat.volume_expansion
    details['electrode_volume_expansion'] = vol_exp

    # Polymer elongation (higher = more accommodating)
    poly_elong = polymer.elongation_at_break_pct
    details['polymer_elongation_pct'] = poly_elong

    # Polymer modulus
    poly_mod = polymer.elastic_modulus_GPa
    details['polymer_modulus_GPa'] = poly_mod

    if vol_exp is not None and poly_elong is not None:
        # Need elongation > volume expansion (roughly)
        # Si anode: 280% expansion needs very flexible binder
        # Graphite: 10% expansion, most binders OK
        needed_elong = vol_exp * 100  # Convert fractional to percentage
        ratio = poly_elong / max(needed_elong, 1.0)
        details['elongation_ratio'] = ratio

        if ratio > 5.0:
            mech_score = 1.0
        elif ratio > 2.0:
            mech_score = 0.9
        elif ratio > 1.0:
            mech_score = 0.7
        elif ratio > 0.5:
            mech_score = 0.4
        else:
            mech_score = 0.15  # Polymer will crack
    elif vol_exp is not None:
        # No elongation data; penalize high volume expansion
        if vol_exp < 0.05:
            mech_score = 0.9
        elif vol_exp < 0.15:
            mech_score = 0.7
        else:
            mech_score = 0.4
    else:
        mech_score = 0.7  # Unknown volume expansion

    # Modulus match: too stiff polymer + high expansion = cracking
    if poly_mod is not None and vol_exp is not None:
        if poly_mod > 3.0 and vol_exp > 0.15:
            mech_score *= 0.7  # Stiff polymer + high expansion
            details['stiffness_penalty'] = True

    return mech_score, details


def _score_chemical_compatibility(
    polymer: PolymerMaterial,
    battery_mat: BatteryMaterial,
) -> Tuple[float, Dict]:
    """
    Score chemical compatibility between polymer and battery material.

    Checks:
    - Polymer chemical resistance to electrolyte environment
    - Known good/bad pair bonuses/penalties
    - Water sensitivity issues (CMC is water-based, incompatible with
      moisture-sensitive cathodes)
    """
    details = {}
    score = 0.7  # Default baseline

    # Known pair lookup — use abbreviation for polymers
    poly_key = getattr(polymer, 'abbreviation', polymer.name)
    pair = (poly_key, battery_mat.name)

    if pair in KNOWN_GOOD_PAIRS:
        score = 0.95
        details['known_pair'] = 'good'
    elif pair in KNOWN_BAD_PAIRS:
        score = 0.15
        details['known_pair'] = 'bad'
    else:
        details['known_pair'] = 'unknown'

        # Water sensitivity check
        water_abs = polymer.water_absorption_pct
        if water_abs is not None and water_abs > 5.0:
            # High water absorption polymer with moisture-sensitive battery material
            bat_meta = battery_mat.metadata or {}
            if bat_meta.get('moisture_sensitive', False):
                score -= 0.2
                details['water_penalty'] = True

        # Check polymer chemical resistance metadata
        poly_meta = polymer.metadata or {}
        if poly_meta.get('solvent_resistant', False):
            score = min(score + 0.1, 1.0)
            details['solvent_resistant_bonus'] = True

    details['chemical_score'] = score
    return max(0.0, min(1.0, score)), details


def score_polymer_electrode_compatibility(
    polymer_name: str,
    battery_material_name: str,
    operating_temp_C: float = 25.0,
    polymer_role: Optional[str] = None,
) -> BatteryPolymerResult:
    """
    Score compatibility between a polymer and a battery material.

    Args:
        polymer_name: Name in polymer_bridge (e.g., 'PEO', 'PVDF')
        battery_material_name: Name in battery_bridge (e.g., 'LFP', 'NMC811')
        operating_temp_C: Operating temperature in Celsius
        polymer_role: Optional contextual role such as 'cathode_binder',
            'anode_binder', 'polymer_electrolyte', or 'coating'.

    Returns:
        BatteryPolymerResult with component scores and composite
    """
    warnings = []

    polymer = get_polymer(polymer_name)
    if polymer is None:
        return BatteryPolymerResult(
            compatible=False, score=0.0,
            voltage_compatibility=0.0, thermal_compatibility=0.0,
            mechanical_compatibility=0.0, chemical_compatibility=0.0,
            polymer_name=polymer_name,
            battery_material_name=battery_material_name,
            warnings=[f"Unknown polymer: {polymer_name}"],
        )

    battery_mat = get_battery_material(battery_material_name)
    if battery_mat is None:
        return BatteryPolymerResult(
            compatible=False, score=0.0,
            voltage_compatibility=0.0, thermal_compatibility=0.0,
            mechanical_compatibility=0.0, chemical_compatibility=0.0,
            polymer_name=polymer_name,
            battery_material_name=battery_material_name,
            warnings=[f"Unknown battery material: {battery_material_name}"],
        )

    # Score each dimension
    v_score, v_details = _score_voltage_compatibility(polymer, battery_mat)
    t_score, t_details = _score_thermal_compatibility(polymer, battery_mat, operating_temp_C)
    m_score, m_details = _score_mechanical_compatibility(polymer, battery_mat)
    c_score, c_details = _score_chemical_compatibility(polymer, battery_mat)

    role = (polymer_role or "").strip().lower().replace("-", "_").replace(" ", "_")
    poly_key = getattr(polymer, 'abbreviation', polymer.name)
    battery_key = battery_mat.name
    nominal_v = battery_mat.voltage_window.nominal if battery_mat.voltage_window else None
    upper_v = battery_mat.voltage_window.upper if battery_mat.voltage_window else None
    is_high_voltage_cathode = (
        battery_mat.material_class == MaterialClass.CATHODE
        and (
            battery_key.startswith("NMC")
            or battery_key in {"LCO", "LMO"}
            or (nominal_v is not None and nominal_v >= 3.7)
            or (upper_v is not None and upper_v >= 4.2)
        )
    )

    if poly_key == "PEO" and is_high_voltage_cathode:
        v_score = min(v_score, 0.15)
        c_score = min(c_score, 0.35)
        v_details["high_voltage_cathode_context"] = True
        c_details["peo_high_voltage_cathode_penalty"] = True
        warnings.append(
            f"Context penalty: {polymer_name} is not stable enough for high-voltage {battery_material_name}"
        )

    anode_binder_polymers = {"CMC", "SBR"}
    anode_materials = {"Graphite", "Si", "LTO", "Li_metal"}
    high_voltage_exempt_roles = {"protective_coating"}
    if (
        poly_key in anode_binder_polymers
        and battery_mat.material_class == MaterialClass.CATHODE
        and role == "cathode_binder"
        and role not in high_voltage_exempt_roles
    ):
        c_score = min(c_score, 0.18)
        m_score = min(m_score, 0.45)
        c_details["anode_binder_cathode_penalty"] = True
        m_details["anode_binder_cathode_penalty"] = True
        warnings.append(
            f"Context penalty: {polymer_name} is primarily an anode binder, not a {battery_material_name} cathode binder"
        )
        if is_high_voltage_cathode:
            c_score = min(c_score, 0.15)
            c_details["anode_binder_high_voltage_cathode_penalty"] = True

    if poly_key in anode_binder_polymers and battery_key in anode_materials:
        c_score = max(c_score, 0.85)
        m_score = max(m_score, 0.75)
        c_details["anode_binder_context_bonus"] = True
        m_details["anode_binder_context_bonus"] = True

    # Composite: voltage is critical for batteries
    composite = (
        0.35 * v_score +
        0.20 * t_score +
        0.20 * m_score +
        0.25 * c_score
    )

    # Voltage veto: if polymer will decompose, cap total
    if v_score < 0.2:
        composite = min(composite, 0.25)
        warnings.append(
            f"Voltage veto: {polymer_name} will decompose at "
            f"{battery_material_name} operating voltage"
        )

    # Chemical veto: known bad pair or severe incompatibility
    if c_score < 0.2:
        composite = min(composite, 0.35)
        warnings.append(
            f"Chemical veto: {polymer_name} is chemically incompatible "
            f"with {battery_material_name}"
        )

    compatible = composite >= 0.50
    component_scores = {
        'voltage_compatibility': v_score,
        'thermal_compatibility': t_score,
        'mechanical_compatibility': m_score,
        'chemical_compatibility': c_score,
    }

    return BatteryPolymerResult(
        compatible=compatible,
        score=round(composite, 4),
        voltage_compatibility=round(v_score, 4),
        thermal_compatibility=round(t_score, 4),
        mechanical_compatibility=round(m_score, 4),
        chemical_compatibility=round(c_score, 4),
        polymer_name=polymer_name,
        battery_material_name=battery_material_name,
        warnings=warnings,
        details={
            'voltage': v_details,
            'thermal': t_details,
            'mechanical': m_details,
            'chemical': c_details,
            'enriched_quantales': summarize_compatibility_components(component_scores),
            'context': {
                'role': role or None,
                'operating_temp_C': operating_temp_C,
            },
        },
    )


def list_battery_polymer_pairs() -> List[Tuple[str, str]]:
    """List all scorable (polymer, battery_material) pairs."""
    from polymer_bridge.material_properties import list_battery_polymers
    from battery_bridge.material_properties import list_cathodes, list_anodes

    polymers = list_battery_polymers()
    electrodes = list_cathodes() + list_anodes()
    return [(p, e) for p in polymers for e in electrodes]


if __name__ == "__main__":
    print("=" * 60)
    print("Battery-Polymer Cross-Bridge Demo")
    print("=" * 60)
    print()

    test_pairs = [
        ('PVDF', 'LFP', 'Standard cathode binder'),
        ('PVDF', 'NMC811', 'High-voltage cathode binder'),
        ('PEO', 'LFP', 'Polymer electrolyte (good)'),
        ('PEO', 'NMC811', 'Polymer electrolyte (voltage problem)'),
        ('CMC', 'Graphite', 'Water-based anode binder'),
        ('PTFE', 'LFP', 'Alternative binder'),
    ]

    for poly, bat, desc in test_pairs:
        r = score_polymer_electrode_compatibility(poly, bat)
        status = "PASS" if r.compatible else "FAIL"
        print(f"  [{status}] {poly} + {bat}: {r.score:.3f}  ({desc})")
        if r.warnings:
            for w in r.warnings:
                print(f"         WARNING: {w}")
    print()
