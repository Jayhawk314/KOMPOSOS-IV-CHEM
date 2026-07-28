# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
MOF Interaction Scoring
========================

Five application-suitability scorers for Metal-Organic Frameworks.

Unlike other bridges (which score A-vs-B pair compatibility), the MOF bridge
scores a SINGLE MOF against a set of operating conditions/requirements.

Scorer Mapping:
    1. Pore Accessibility   — can the target molecule fit through the aperture?
    2. Chemical Stability   — will the MOF survive the operating environment?
    3. Thermal Compatibility — can it operate at the target temperature?
    4. Mechanical Compat.   — can it withstand the operating pressure?
    5. Application Suit.    — is the MOF suited for the intended application?

Each scorer returns a ScorerResult (score in [0, 1]).
"""

from dataclasses import dataclass
from typing import Dict, Optional

from mof_bridge.material_properties import (
    MOF,
    MOFApplication,
    get_mof,
)


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent suitability)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning
    veto: bool = False   # Hard physical block — annihilates the composite


# =============================================================================
# 1. PORE ACCESSIBILITY SCORE
# =============================================================================

def score_pore_accessibility(
    mof: MOF,
    target_molecule_diameter: Optional[float] = None,
    min_surface_area: Optional[float] = None,
    min_pore_volume: Optional[float] = None,
) -> ScorerResult:
    """
    Score whether a target molecule can access the MOF pores.

    Args:
        mof: MOF material
        target_molecule_diameter: Guest molecule kinetic diameter (Angstrom)
        min_surface_area: Minimum BET surface area required (m2/g)
        min_pore_volume: Minimum pore volume required (cm3/g)

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    veto = False
    details = {
        'pore_diameter_angstrom': mof.pore_diameter_angstrom,
        'bet_surface_area_m2g': mof.bet_surface_area_m2g,
        'pore_volume_cm3g': mof.pore_volume_cm3g,
    }

    # Pore aperture vs molecule diameter
    if target_molecule_diameter is not None:
        details['target_molecule_diameter'] = target_molecule_diameter
        ratio = mof.pore_diameter_angstrom / max(target_molecule_diameter, 0.1)
        details['aperture_ratio'] = round(ratio, 2)

        if ratio < 0.8:
            score *= 0.1
            veto = True
            details['aperture_assessment'] = 'blocked — molecule too large for pore'
        elif ratio < 1.0:
            score *= 0.4
            details['aperture_assessment'] = 'tight fit — diffusion-limited'
        elif ratio < 1.5:
            score *= 0.9
            details['aperture_assessment'] = 'good molecular sieving range'
        elif ratio < 3.0:
            score *= 0.8
            details['aperture_assessment'] = 'accessible but low selectivity'
        else:
            score *= 0.6
            details['aperture_assessment'] = 'pores too large — no size selectivity'

    # Surface area check
    if min_surface_area is not None:
        details['min_surface_area_required'] = min_surface_area
        if mof.bet_surface_area_m2g < min_surface_area:
            ratio = mof.bet_surface_area_m2g / min_surface_area
            score *= max(0.2, ratio)
            details['surface_area_assessment'] = 'below minimum requirement'
        else:
            details['surface_area_assessment'] = 'meets requirement'

    # Pore volume check
    if min_pore_volume is not None:
        details['min_pore_volume_required'] = min_pore_volume
        if mof.pore_volume_cm3g < min_pore_volume:
            ratio = mof.pore_volume_cm3g / min_pore_volume
            score *= max(0.2, ratio)
            details['pore_volume_assessment'] = 'below minimum requirement'
        else:
            details['pore_volume_assessment'] = 'meets requirement'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='pore_accessibility', details=details, veto=veto)


# =============================================================================
# 2. CHEMICAL STABILITY SCORE
# =============================================================================

_WATER_STABILITY_SCORES = {
    'excellent': 1.0,
    'good': 0.75,
    'moderate': 0.5,
    'poor': 0.2,
}


def score_chemical_stability(
    mof: MOF,
    requires_water_stable: bool = False,
    requires_acid_stable: bool = False,
    environment: str = "dry",
) -> ScorerResult:
    """
    Score chemical stability of a MOF for the target environment.

    Args:
        mof: MOF material
        requires_water_stable: Whether water stability is required
        requires_acid_stable: Whether acid stability is required
        environment: Operating environment ("dry", "humid", "aqueous", "acidic", "basic")

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {
        'water_stability': mof.water_stability,
        'chemical_stability': mof.chemical_stability,
        'environment': environment,
    }

    water_score = _WATER_STABILITY_SCORES.get(mof.water_stability, 0.5)
    details['water_stability_score'] = water_score

    # Environment-based scoring
    if environment == "dry":
        score = max(0.5, water_score)
    elif environment == "humid":
        score = water_score
        if water_score < 0.5:
            score *= 0.7
            details['warning'] = 'MOF may degrade in humid conditions'
    elif environment == "aqueous":
        score = water_score
        if water_score < 0.75:
            score *= 0.5
            details['warning'] = 'MOF unlikely to survive aqueous conditions'
    elif environment == "acidic":
        score = water_score * 0.8
        if 'acid' in mof.chemical_stability.lower() and 'stable' in mof.chemical_stability.lower():
            score = min(1.0, score + 0.3)
            details['acid_note'] = 'acid stability reported'
        elif 'decomposes' in mof.chemical_stability.lower():
            score *= 0.3
            details['acid_note'] = 'decomposes in acidic conditions'
    elif environment == "basic":
        score = water_score * 0.8
        if 'alkaline' in mof.chemical_stability.lower() or 'base' in mof.chemical_stability.lower():
            score = min(1.0, score + 0.2)

    # Hard requirement checks
    if requires_water_stable and water_score < 0.5:
        score *= 0.3
        details['veto'] = 'water stability required but MOF is water-unstable'

    if requires_acid_stable:
        acid_ok = ('acid' in mof.chemical_stability.lower()
                   and 'stable' in mof.chemical_stability.lower())
        if not acid_ok:
            score *= 0.4
            details['veto'] = 'acid stability required but not confirmed'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='chemical_stability', details=details)


# =============================================================================
# 3. THERMAL COMPATIBILITY SCORE
# =============================================================================

def score_thermal_compatibility(
    mof: MOF,
    operating_temp_C: float = 25.0,
    requires_regeneration: bool = False,
    regeneration_temp_C: Optional[float] = None,
) -> ScorerResult:
    """
    Score whether a MOF can withstand the operating temperature.

    Args:
        mof: MOF material
        operating_temp_C: Operating temperature in Celsius
        requires_regeneration: Whether thermal regeneration is needed
        regeneration_temp_C: Regeneration temperature if needed

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {
        'thermal_stability_C': mof.thermal_stability_C,
        'operating_temp_C': operating_temp_C,
    }

    # Thermal margin
    margin = mof.thermal_stability_C - operating_temp_C
    details['thermal_margin_C'] = round(margin, 0)

    if margin < 0:
        score = 0.05
        details['assessment'] = 'MOF decomposes below operating temperature'
    elif margin < 50:
        score = 0.3
        details['assessment'] = 'dangerously close to decomposition'
    elif margin < 100:
        score = 0.6
        details['assessment'] = 'adequate but limited thermal margin'
    elif margin < 200:
        score = 0.85
        details['assessment'] = 'good thermal margin'
    else:
        score = 0.95
        details['assessment'] = 'excellent thermal margin'

    # Regeneration requirement
    if requires_regeneration and regeneration_temp_C is not None:
        details['regeneration_temp_C'] = regeneration_temp_C
        regen_margin = mof.thermal_stability_C - regeneration_temp_C
        details['regeneration_margin_C'] = round(regen_margin, 0)

        if regen_margin < 0:
            score *= 0.1
            details['regeneration_assessment'] = 'cannot regenerate — decomposes before regen temp'
        elif regen_margin < 50:
            score *= 0.5
            details['regeneration_assessment'] = 'tight regeneration window'
        else:
            details['regeneration_assessment'] = 'regeneration feasible'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='thermal_compatibility', details=details)


# =============================================================================
# 4. MECHANICAL COMPATIBILITY SCORE
# =============================================================================

def score_mechanical_compatibility(
    mof: MOF,
    operating_pressure_bar: float = 1.0,
) -> ScorerResult:
    """
    Score whether a MOF can withstand the operating pressure.

    MOFs are notoriously fragile — bulk moduli of 5-30 GPa vs ~200 GPa for
    alumina. High-pressure applications require careful MOF selection.

    Args:
        mof: MOF material
        operating_pressure_bar: Operating pressure in bar

    Returns:
        ScorerResult with score in [0, 1]
    """
    details = {
        'bulk_modulus_GPa': mof.bulk_modulus_GPa,
        'operating_pressure_bar': operating_pressure_bar,
    }

    if mof.bulk_modulus_GPa is None:
        details['note'] = 'Bulk modulus not measured — using conservative estimate'
        score = 0.5
    else:
        # Convert pressure bar to GPa for comparison (1 bar = 0.0001 GPa)
        pressure_GPa = operating_pressure_bar * 0.0001

        # Safety factor: MOF should have modulus >> operating pressure
        if mof.bulk_modulus_GPa < 5.0:
            base_score = 0.4
            details['framework_note'] = 'soft framework — pressure sensitive'
        elif mof.bulk_modulus_GPa < 15.0:
            base_score = 0.7
            details['framework_note'] = 'moderate mechanical robustness'
        elif mof.bulk_modulus_GPa < 25.0:
            base_score = 0.85
            details['framework_note'] = 'mechanically robust'
        else:
            base_score = 0.95
            details['framework_note'] = 'exceptionally robust framework'

        # Pressure penalty
        if operating_pressure_bar > 100:
            base_score *= max(0.3, 1.0 - (operating_pressure_bar - 100) / 1000)
            details['pressure_note'] = 'high-pressure penalty applied'
        elif operating_pressure_bar > 50:
            base_score *= 0.85
            details['pressure_note'] = 'moderate-pressure penalty applied'

        score = base_score

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 5. APPLICATION SUITABILITY SCORE
# =============================================================================

# Application-specific requirements
_APP_REQUIREMENTS = {
    MOFApplication.GAS_STORAGE: {
        'min_surface_area': 1000.0,
        'min_pore_volume': 0.5,
        'description': 'High surface area and pore volume needed',
    },
    MOFApplication.CATALYSIS: {
        'min_surface_area': 500.0,
        'description': 'Accessible active sites and thermal stability needed',
    },
    MOFApplication.SEPARATION: {
        'description': 'Narrow pore size distribution for selectivity',
    },
    MOFApplication.CARBON_CAPTURE: {
        'min_surface_area': 500.0,
        'description': 'CO2-philic sites and regenerability needed',
    },
    MOFApplication.WATER_HARVESTING: {
        'min_water_stability': 'excellent',
        'description': 'Must survive repeated hydration/dehydration cycles',
    },
    MOFApplication.DRUG_DELIVERY: {
        'min_water_stability': 'good',
        'description': 'Biocompatibility and controlled release needed',
    },
    MOFApplication.SENSING: {
        'description': 'Luminescence or conductivity change upon guest adsorption',
    },
    MOFApplication.PROTON_CONDUCTION: {
        'min_water_stability': 'good',
        'description': 'Proton-conducting pathways in humid conditions',
    },
}


def score_application_suitability(
    mof: MOF,
    target_application: Optional[MOFApplication] = None,
) -> ScorerResult:
    """
    Score how well a MOF matches a target application.

    Args:
        mof: MOF material
        target_application: Target application (uses MOF's primary if None)

    Returns:
        ScorerResult with score in [0, 1]
    """
    app = target_application or mof.primary_application
    details = {
        'mof_primary_application': mof.primary_application.value,
        'target_application': app.value,
    }

    # Base score: primary application match
    if app == mof.primary_application:
        score = 0.9
        details['match'] = 'primary application match'
    else:
        score = 0.5
        details['match'] = 'secondary application (not primary)'

    # Application-specific checks
    reqs = _APP_REQUIREMENTS.get(app, {})
    details['requirements'] = reqs.get('description', 'No specific requirements')

    # Surface area check
    min_sa = reqs.get('min_surface_area')
    if min_sa and mof.bet_surface_area_m2g < min_sa:
        ratio = mof.bet_surface_area_m2g / min_sa
        score *= max(0.3, ratio)
        details['surface_area_note'] = f'below {min_sa} m2/g requirement'

    # Pore volume check
    min_pv = reqs.get('min_pore_volume')
    if min_pv and mof.pore_volume_cm3g < min_pv:
        ratio = mof.pore_volume_cm3g / min_pv
        score *= max(0.3, ratio)
        details['pore_volume_note'] = f'below {min_pv} cm3/g requirement'

    # Water stability check
    min_ws = reqs.get('min_water_stability')
    if min_ws:
        ws_order = {'excellent': 4, 'good': 3, 'moderate': 2, 'poor': 1}
        required = ws_order.get(min_ws, 0)
        actual = ws_order.get(mof.water_stability, 0)
        if actual < required:
            score *= max(0.2, actual / max(required, 1))
            details['water_stability_note'] = (
                f'requires {min_ws}, MOF has {mof.water_stability}'
            )

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='application_suitability', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(
    mof: MOF,
    target_molecule_diameter: Optional[float] = None,
    operating_temp_C: float = 25.0,
    operating_pressure_bar: float = 1.0,
    environment: str = "dry",
    target_application: Optional[MOFApplication] = None,
    requires_water_stable: bool = False,
    requires_acid_stable: bool = False,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a MOF for given conditions.

    Args:
        mof: MOF material
        target_molecule_diameter: Guest molecule diameter (Angstrom)
        operating_temp_C: Operating temperature (C)
        operating_pressure_bar: Operating pressure (bar)
        environment: "dry", "humid", "aqueous", "acidic", "basic"
        target_application: Target application
        requires_water_stable: Whether water stability is required
        requires_acid_stable: Whether acid stability is required

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'pore_accessibility': score_pore_accessibility(
            mof,
            target_molecule_diameter=target_molecule_diameter,
        ),
        'chemical_stability': score_chemical_stability(
            mof,
            requires_water_stable=requires_water_stable,
            requires_acid_stable=requires_acid_stable,
            environment=environment,
        ),
        'thermal_compatibility': score_thermal_compatibility(
            mof,
            operating_temp_C=operating_temp_C,
        ),
        'mechanical_compatibility': score_mechanical_compatibility(
            mof,
            operating_pressure_bar=operating_pressure_bar,
        ),
        'application_suitability': score_application_suitability(
            mof,
            target_application=target_application,
        ),
    }
