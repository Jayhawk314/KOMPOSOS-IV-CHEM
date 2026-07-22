# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer Interface Validator
===============================

Validates polymer interface/blend viability between two materials,
analogous to battery_bridge/interface_validator.py.

Pattern:
  Battery bridge:  "Can material A interface with material B?"
  Polymer bridge:  "Can polymer A blend with polymer B?"

The validator combines all five interaction scorers into a weighted
composite PolymerInterfaceScore with configurable weights and thresholds.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from polymer_bridge.material_properties import PolymerMaterial, get_polymer
from polymer_bridge.interaction_scoring import (
    score_solubility_compatibility,
    score_thermal_compatibility,
    score_mechanical_compatibility,
    score_chemical_resistance,
    score_aging_penalty,
    ScorerResult,
)
from polymer_bridge.flory_huggins import assess_flory_huggins


@dataclass
class PolymerConditions:
    """Operating/environmental conditions that affect polymer viability."""
    temperature_C: float = 25.0
    humidity_pct: float = 50.0
    uv_exposure: bool = False
    chemical_environment: str = "air"  # "air", "water", "acid", "base", "electrolyte"


@dataclass
class PolymerInterfaceScore:
    """
    Composite interface viability score with component breakdown.

    Mirrors InterfaceScore from battery_bridge.
    """
    total: float                        # Weighted composite (0-1)
    solubility_compatibility: float     # Component score
    thermal_compatibility: float        # Component score
    mechanical_compatibility: float     # Component score
    chemical_resistance: float          # Component score
    aging_penalty: float                # Component score
    viable: bool                        # Above threshold?
    details: Dict = field(default_factory=dict)
    # Explicit abstention. When True, this interface is OUTSIDE the validated
    # model and `total`/`viable` carry no evidential weight — callers must
    # surface "not assessed" rather than treating `total` as a verdict. This
    # exists so an uncovered interface cannot masquerade as a confident score
    # (the failure this bridge previously had: polymer-vs-solvent pairs were
    # run through the blend model and emitted a constant 0.45).
    not_assessed: bool = False
    not_assessed_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'solubility_compatibility': round(self.solubility_compatibility, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'mechanical_compatibility': round(self.mechanical_compatibility, 4),
            'chemical_resistance': round(self.chemical_resistance, 4),
            'aging_penalty': round(self.aging_penalty, 4),
            'viable': self.viable,
            'not_assessed': self.not_assessed,
            'not_assessed_reason': self.not_assessed_reason,
        }


@dataclass
class PolymerWeights:
    """Configurable weights for the five scoring components."""
    solubility: float = 0.35  # Increased from 0.30 to penalize immiscibility more
    thermal: float = 0.20
    mechanical: float = 0.20
    chemical_resistance: float = 0.10  # Reduced from 0.15
    aging: float = 0.15

    def validate(self):
        """Check weights sum to ~1.0."""
        total = (self.solubility + self.thermal + self.mechanical +
                 self.chemical_resistance + self.aging)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'PolymerWeights':
        """Default weights emphasizing solubility compatibility."""
        return cls()

    @classmethod
    def blend_focus(cls) -> 'PolymerWeights':
        """Weights for blend miscibility assessment."""
        return cls(
            solubility=0.40,
            thermal=0.20,
            mechanical=0.15,
            chemical_resistance=0.10,
            aging=0.15,
        )

    @classmethod
    def structural_focus(cls) -> 'PolymerWeights':
        """Weights for structural/mechanical applications."""
        return cls(
            solubility=0.15,
            thermal=0.15,
            mechanical=0.35,
            chemical_resistance=0.15,
            aging=0.20,
        )

    @classmethod
    def durability_focus(cls) -> 'PolymerWeights':
        """Weights emphasizing long-term durability and aging."""
        return cls(
            solubility=0.15,
            thermal=0.15,
            mechanical=0.15,
            chemical_resistance=0.20,
            aging=0.35,
        )

    @classmethod
    def coexistence_focus(cls) -> 'PolymerWeights':
        """Weights for interfaces where the two polymers COEXIST rather than
        form a single miscible phase (binder dispersions, binder vs separator,
        coatings, liners). Miscibility is not the governing criterion here — what
        matters is whether they chemically attack each other and survive aging —
        so solubility is heavily de-emphasized and chemical resistance/aging lead.
        """
        return cls(
            solubility=0.10,
            thermal=0.25,
            mechanical=0.15,
            chemical_resistance=0.30,
            aging=0.20,
        )


# Interface roles where two polymers COEXIST (dispersion / adjacent layers /
# coating-on-substrate) rather than being asked to form one miscible phase.
# For these, the Flory-Huggins immiscibility veto is the WRONG criterion
# (e.g. CMC+SBR is the industry-standard aqueous binder, used together as a
# dispersion; CMC vs PP separator merely coexist). The veto is gated off for
# these roles. Any other role — including None/unknown and explicit blend/alloy
# roles — keeps the strict veto, preserving blend-miscibility behaviour.
COEXISTENCE_INTERFACE_ROLES = frozenset({
    "binder", "binder_dispersion", "dispersion",
    "separator", "membrane",
    "coating", "non_stick_coating", "insulation", "wire_insulation",
    "seal", "gasket", "seal_gasket",
    "liner", "chemical_resistant_liner",
    "current_collector", "encapsulant", "coexisting",
})


def _is_coexistence_role(role: Optional[str]) -> bool:
    """True if `role` is a coexistence/dispersion interface (veto should be gated off)."""
    if not role:
        return False
    return role.strip().lower().replace("-", "_").replace(" ", "_") in COEXISTENCE_INTERFACE_ROLES


# --- Polymer-vs-solvent interfaces: two opposite intents -------------------
#
# A polymer/solvent pair carries TWO opposite questions, and the same measurement
# answers them in opposite directions:
#
#   dissolution intent (DEFAULT here) — "can this solvent dissolve/process this
#       polymer?" Used for binder slurries and solution casting (PVDF+NMP,
#       CMC+water). A solubility MATCH is success. Hansen parameters are exactly
#       the right tool, and this bridge's original behaviour targeted this.
#
#   resistance intent — "will this polymer survive contact with this solvent?"
#       A solubility match is FAILURE. This intent was previously unrepresentable:
#       every polymer/solvent pair was answered as a dissolution/blend question,
#       so chemical-resistance questions received systematically wrong verdicts
#       (PTFE+toluene, POM+acetone read as failures because the solvent cannot
#       dissolve them — which is precisely why they are resistant).
#
# The defect was therefore a MISSING INTENT, not an inverted formula. Resistance
# must be requested explicitly via SOLVENT_RESISTANCE_INTERFACE_ROLES.
#
# Grounding for the resistance side (measured 2026-07-20 over 30 polymer/solvent
# cases with established outcomes): Hansen distance Ra ALONE does not separate
# resistance from attack — the best single Ra threshold scores only 22/30.
# Counterexamples are physically explicable and not fixable by moving it:
#   * PTFE + toluene (Ra 3.88) RESISTS  — highly crystalline fluoropolymer
#   * PPS  + toluene (Ra 3.28) RESISTS  — semi-crystalline high-performance
#   * CMC  + water   (Ra 22.3) DISSOLVES — ionic/H-bonding dominates
#   * PA6  + water   (Ra 34.2) ABSORBS   — amide H-bonding dominates
# Resistance depends on crystallinity, Tg/Tm vs service temperature, and specific
# interactions, none of which a cohesive-energy distance captures.
#
# So this module does NOT invent an Ra-based resistance score. It answers a
# resistance question only where curated per-polymer data supports one (water
# uptake, verified 7/7) and ABSTAINS otherwise. A validated organic-solvent
# resistance model is tracked future work, not something to approximate here.
# Two OPPOSITE intents share the polymer/solvent interface, and the same
# measurement means opposite things in each:
#   * resistance intent  — the polymer must survive contact. Dissolving = FAIL.
#   * dissolution intent — the solvent is being used to process the polymer
#     (slurry casting, binder solution). Dissolving = the POINT; insolubility
#     means the process does not work.
# CMC + water is the standard example: as chemical resistance it fails, as
# aqueous binder processing it is the industry-standard system (the Water entry's
# own metadata records "Solvent for CMC+SBR water-based binder systems").
SOLVENT_RESISTANCE_INTERFACE_ROLES = frozenset({
    "solvent_exposure", "chemical_resistance", "chemical_exposure",
    "solvent_contact", "immersion", "chemical_resistant_liner",
})
SOLVENT_DISSOLUTION_INTERFACE_ROLES = frozenset({
    "processing_solvent", "slurry", "binder_processing", "casting",
    "coating_solution", "solution", "dissolution",
})


def _normalize_role(role: Optional[str]) -> str:
    if not role:
        return ""
    return role.strip().lower().replace("-", "_").replace(" ", "_")


def _is_dissolution_intent(role: Optional[str]) -> bool:
    """True if the solvent is being used to PROCESS the polymer (dissolving is desired).

    This is the DEFAULT for a polymer/solvent pair in this bridge: an unqualified
    "polymer + solvent" question here has always meant "can this solvent dissolve
    or process this polymer" (PVDF+NMP, CMC+water binder slurries). Resistance
    must be requested explicitly, because the same measurement means the opposite
    thing under each intent.
    """
    return not _is_resistance_intent(role)


def _is_resistance_intent(role: Optional[str]) -> bool:
    """True if the polymer must SURVIVE contact with the solvent."""
    return _normalize_role(role) in SOLVENT_RESISTANCE_INTERFACE_ROLES


def _vetoed_score(total: float, cap: float) -> float:
    """Map a vetoed composite to at most ``cap``, PRESERVING ORDER within the tier.

    A hard clamp (``min(total, cap)``) collapses every vetoed pair at or above
    the cap onto one value, destroying ranking among rejected pairs. Scaling by
    the cap keeps the ordering while still guaranteeing the result stays below
    ``cap`` (and thus below the viability threshold). ``cap`` is passed
    per-branch because it encodes veto CONFIDENCE: the confirmed-immiscible veto
    uses a lower cap (0.35) than the uncertain, missing-chain-length veto (0.45),
    and that distinction must survive.
    """
    return cap * max(0.0, min(1.0, total))

# Water-uptake bands, from curated `water_absorption_pct` (% at saturation).
# Verified 7/7 against established outcomes (PTFE/PEEK/HDPE/PP/PVC resist;
# PA6 hygroscopic; CMC dissolves).
_WATER_SOLUBLE_PCT = 100.0   # CMC, PEO: dissolves outright
_WATER_HYGROSCOPIC_PCT = 5.0  # PA6 9.5, PA66 8.0: dimensional/property loss
_WATER_MODERATE_PCT = 1.0     # PAN 2.0, PI 1.8: usable but degraded


def _solvent_name(material: PolymerMaterial) -> Optional[str]:
    """Return the solvent key if `material` is a solvent, else None."""
    from polymer_bridge.material_properties import POLYMER_SOLVENTS
    abbrev = (material.abbreviation or "").strip()
    for key in POLYMER_SOLVENTS:
        if key.lower() == abbrev.lower():
            return key
    return None


def _split_polymer_solvent(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
) -> Optional[Tuple[PolymerMaterial, PolymerMaterial, str]]:
    """If exactly one of the pair is a solvent, return (polymer, solvent, name).

    Returns None for polymer/polymer pairs (normal blend path) and for
    solvent/solvent pairs (not a materials interface this bridge models).
    """
    sa = _solvent_name(material_a)
    sb = _solvent_name(material_b)
    if sa and not sb:
        return material_b, material_a, sa
    if sb and not sa:
        return material_a, material_b, sb
    return None


class PolymerInterfaceValidator:
    """
    Validates polymer interface/blend viability.

    Mirrors BatteryInterfaceValidator pattern exactly.

    Usage:
        validator = PolymerInterfaceValidator()
        result = validator.validate('PVDF', 'PMMA')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[PolymerWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or PolymerWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        polymer_a: str,
        polymer_b: str,
        conditions: Optional[PolymerConditions] = None,
        interface_role: Optional[str] = None,
    ) -> PolymerInterfaceScore:
        """
        Validate an interface between two polymers by name.

        Args:
            polymer_a: Name/abbreviation of first polymer
            polymer_b: Name/abbreviation of second polymer
            conditions: Optional operating conditions
            interface_role: Optional role of the interface. For coexistence/
                dispersion roles (binder, separator, coating, ...) the
                Flory-Huggins immiscibility veto is gated off and solubility is
                de-emphasized; for blend/alloy/unknown roles the strict veto
                applies (default).

        Returns:
            PolymerInterfaceScore with component breakdown

        Raises:
            ValueError: If polymer name not found
        """
        mat_a = get_polymer(polymer_a)
        mat_b = get_polymer(polymer_b)
        if mat_a is None:
            raise ValueError(f"Unknown polymer: '{polymer_a}'")
        if mat_b is None:
            raise ValueError(f"Unknown polymer: '{polymer_b}'")

        return self.validate_materials(mat_a, mat_b, conditions, interface_role)

    def validate_materials(
        self,
        material_a: PolymerMaterial,
        material_b: PolymerMaterial,
        conditions: Optional[PolymerConditions] = None,
        interface_role: Optional[str] = None,
    ) -> PolymerInterfaceScore:
        """
        Validate an interface between two PolymerMaterial objects.

        Args:
            material_a: First polymer
            material_b: Second polymer
            conditions: Optional operating conditions

        Returns:
            PolymerInterfaceScore with full breakdown
        """
        conditions = conditions or PolymerConditions()

        # Polymer-vs-solvent interfaces are handled by a dedicated path. The
        # blend model is INVERTED for them (see SOLVENT_EXPOSURE_INTERFACE_ROLES
        # notes above), so they must never reach the Flory-Huggins veto below.
        solvent_split = _split_polymer_solvent(material_a, material_b)
        if solvent_split is not None:
            polymer, solvent, solvent_key = solvent_split
            # Only take the dedicated path where it is better-grounded than the
            # Hansen default: water (curated per-polymer uptake data) always, and
            # any solvent when RESISTANCE is explicitly requested. Otherwise fall
            # through to the established Hansen/blend path, which is the right
            # tool for the default dissolution/processing question ("can this
            # solvent dissolve this polymer") and whose behaviour is unchanged.
            if solvent_key.lower() == 'water' or _is_resistance_intent(interface_role):
                return self._validate_solvent_exposure(
                    polymer, solvent, solvent_key, conditions, interface_role
                )

        # Run all five scorers
        s_sol = score_solubility_compatibility(material_a, material_b)
        s_therm = score_thermal_compatibility(material_a, material_b)
        s_mech = score_mechanical_compatibility(material_a, material_b)
        s_chem = score_chemical_resistance(material_a, material_b)
        s_aging = score_aging_penalty(material_a, material_b)

        # Apply condition modifiers
        scores = {
            'solubility': s_sol.score,
            'thermal': s_therm.score,
            'mechanical': s_mech.score,
            'chemical_resistance': s_chem.score,
            'aging': s_aging.score,
        }
        scores = self._apply_condition_modifiers(
            scores, material_a, material_b, conditions
        )

        # Role-aware gate: for coexistence/dispersion interfaces, miscibility is
        # not the governing criterion, so down-weight solubility and (below) skip
        # the immiscibility veto. Unknown/blend roles keep the default weights.
        coexistence = _is_coexistence_role(interface_role)
        weights = PolymerWeights.coexistence_focus() if coexistence else self.weights

        # Weighted composite
        total = (
            weights.solubility * scores['solubility'] +
            weights.thermal * scores['thermal'] +
            weights.mechanical * scores['mechanical'] +
            weights.chemical_resistance * scores['chemical_resistance'] +
            weights.aging * scores['aging']
        )

        # Collect details
        all_details = {
            'solubility_details': s_sol.details,
            'thermal_details': s_therm.details,
            'mechanical_details': s_mech.details,
            'chemical_details': s_chem.details,
            'aging_details': s_aging.details,
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'humidity_pct': conditions.humidity_pct,
                'uv_exposure': conditions.uv_exposure,
                'chemical_environment': conditions.chemical_environment,
            },
            'polymer_a': material_a.abbreviation,
            'polymer_b': material_b.abbreviation,
        }

        # Veto check: High Flory-Huggins χ indicates immiscibility (phase separation)
        # Critical χ ≈ 0.04 for many polymer pairs (Krause 1972, Nishi & Wang 1975)
        # Current implementation uses chain-length critical chi, not a fixed cutoff.
        is_viable = total >= self.viability_threshold
        fh = assess_flory_huggins(material_a, material_b)
        all_details['flory_huggins'] = fh.to_dict()

        if coexistence:
            # Coexistence/dispersion interface: immiscibility is expected and fine
            # (e.g. CMC+SBR aqueous binder, CMC binder vs PP separator). Skip the
            # Flory-Huggins phase-separation veto entirely — it is the wrong
            # criterion here. Chemical-resistance/aging (now weighted up) still
            # drive viability through `total`.
            all_details['role_gate'] = (
                f"coexistence interface (role={interface_role}): Flory-Huggins "
                "immiscibility veto skipped; solubility down-weighted "
                "(coexistence_focus weights)"
            )
        elif fh.miscible is False:
            is_viable = False
            total = _vetoed_score(total, 0.35)  # confirmed immiscible: firm veto
            all_details['veto'] = (
                f"Immiscible blend (chi={fh.chi:.4g} > chi_c={fh.critical_chi:.4g}): "
                "Flory-Huggins phase separation expected"
            )
        elif fh.miscible is None and fh.chi is not None and fh.chi > 0.15:
            is_viable = False
            total = _vetoed_score(total, 0.45)  # missing chain length: uncertain veto
            all_details['veto'] = (
                f"Immiscible blend (chi={fh.chi:.3f}; missing chain length): "
                "phase separation expected"
            )
        elif fh.chi is None and scores['solubility'] < 0.30:
            # No tabulated chi: fall back to the Hansen solubility score. A very
            # low solubility score = strongly mismatched cohesive energy density
            # -> immiscibility. Same 0.30 threshold blend_analyzer already uses.
            # NOTE: this only catches clearly mismatched pairs; it cannot detect
            # crystallinity/entropy-driven immiscibility of solubility-matched
            # polyolefins (e.g. HDPE/PP), which needs curated chi data.
            is_viable = False
            total = _vetoed_score(total, 0.45)  # solubility-only fallback: uncertain veto
            all_details['veto'] = (
                f"Immiscible (no tabulated chi; solubility={scores['solubility']:.2f} < 0.30)"
            )

        return PolymerInterfaceScore(
            total=total,
            solubility_compatibility=scores['solubility'],
            thermal_compatibility=scores['thermal'],
            mechanical_compatibility=scores['mechanical'],
            chemical_resistance=scores['chemical_resistance'],
            aging_penalty=scores['aging'],
            viable=is_viable,
            details=all_details,
        )

    def _validate_solvent_exposure(
        self,
        polymer: PolymerMaterial,
        solvent: PolymerMaterial,
        solvent_key: str,
        conditions: PolymerConditions,
        interface_role: Optional[str],
    ) -> PolymerInterfaceScore:
        """Score a polymer exposed to a solvent (chemical-resistance interface).

        Emits a verdict ONLY where curated data supports one. For water, the
        per-polymer `water_absorption_pct` is curated and reliable. For organic
        solvents this bridge has no validated resistance model, so it abstains
        rather than emitting a number that would look like a verdict.
        """
        details: Dict = {
            'interface_kind': 'polymer_solvent_exposure',
            'polymer': polymer.abbreviation,
            'solvent': solvent_key,
            'interface_role': interface_role,
            'blend_veto_applicable': False,
            'blend_veto_note': (
                'Flory-Huggins immiscibility veto deliberately NOT applied: for '
                'solvent exposure a solubility mismatch indicates RESISTANCE, not '
                'incompatibility. The blend model is inverted for this interface.'
            ),
            'conditions': {
                'temperature_C': conditions.temperature_C,
                'chemical_environment': conditions.chemical_environment,
            },
        }

        # Report Hansen distance as context only — it is NOT used as the verdict.
        if polymer.hansen is not None and solvent.hansen is not None:
            ra = polymer.hansen.distance(solvent.hansen)
            details['hansen_distance_Ra'] = round(ra, 2)
            details['hansen_note'] = (
                'context only; Ra alone does not separate resistance from attack '
                '(measured 22/30 at the best single threshold)'
            )

        if solvent_key.lower() != 'water':
            return PolymerInterfaceScore(
                total=0.0,
                solubility_compatibility=0.0,
                thermal_compatibility=0.0,
                mechanical_compatibility=0.0,
                chemical_resistance=0.0,
                aging_penalty=0.0,
                viable=False,
                details=details,
                not_assessed=True,
                not_assessed_reason=(
                    f"No validated resistance model for {polymer.abbreviation} vs "
                    f"{solvent_key}. Organic-solvent resistance depends on "
                    "crystallinity, Tg/Tm vs service temperature, and specific "
                    "interactions; no curated per-polymer/per-solvent data exists "
                    "in this bridge. Abstaining rather than guessing."
                ),
            )

        # --- Water exposure: curated water_absorption_pct ---
        wa = polymer.water_absorption_pct
        if wa is None:
            return PolymerInterfaceScore(
                total=0.0,
                solubility_compatibility=0.0,
                thermal_compatibility=0.0,
                mechanical_compatibility=0.0,
                chemical_resistance=0.0,
                aging_penalty=0.0,
                viable=False,
                details=details,
                not_assessed=True,
                not_assessed_reason=(
                    f"No curated water_absorption_pct for {polymer.abbreviation}; "
                    "cannot assess water exposure."
                ),
            )

        details['water_absorption_pct'] = wa
        details['evidence'] = 'curated water_absorption_pct'

        if _is_dissolution_intent(interface_role):
            # The solvent is being used to process the polymer: solubility is the
            # requirement, not the failure mode.
            details['intent'] = 'dissolution (solvent used to process the polymer)'
            if wa >= _WATER_SOLUBLE_PCT:
                score, viable = 0.90, True
                details['water_verdict'] = (
                    'water-soluble: suitable for aqueous processing (this is the goal)'
                )
            elif wa > _WATER_HYGROSCOPIC_PCT:
                score, viable = 0.55, True
                details['water_verdict'] = (
                    'takes up water but does not dissolve: partial aqueous processability'
                )
            else:
                score, viable = 0.15, False
                details['water_verdict'] = (
                    'not water-soluble: cannot be processed from aqueous solution'
                )
            # Report the measured Hansen solubility component as-is; `total`
            # carries the curated-data verdict. The component field must reflect
            # the component measurement, not echo the composite.
            return PolymerInterfaceScore(
                total=score,
                solubility_compatibility=score_solubility_compatibility(polymer, solvent).score,
                thermal_compatibility=0.0,
                mechanical_compatibility=0.0,
                chemical_resistance=0.0,
                aging_penalty=0.0,
                viable=viable,
                details=details,
            )

        details['intent'] = 'resistance (polymer must survive contact)'
        if wa >= _WATER_SOLUBLE_PCT:
            score, viable = 0.05, False
            details['water_verdict'] = 'water-soluble: dissolves on water contact'
        elif wa > _WATER_HYGROSCOPIC_PCT:
            score, viable = 0.25, False
            details['water_verdict'] = (
                'strongly hygroscopic: significant dimensional/mechanical change'
            )
        elif wa > _WATER_MODERATE_PCT:
            score, viable = 0.55, True
            details['water_verdict'] = 'moderate uptake: usable, properties shift'
        else:
            score, viable = 0.90, True
            details['water_verdict'] = 'negligible uptake: resistant to water'

        # Hydrolysis-susceptible polymers degrade in hot water regardless of uptake.
        from polymer_bridge.material_properties import PolymerFailureMode
        if (
            PolymerFailureMode.HYDROLYSIS in polymer.failure_modes
            and conditions.temperature_C >= 60.0
        ):
            score = min(score, 0.40)
            viable = False
            details['hydrolysis_note'] = (
                f'hydrolysis-susceptible at {conditions.temperature_C:.0f} C'
            )

        return PolymerInterfaceScore(
            total=score,
            solubility_compatibility=0.0,
            thermal_compatibility=0.0,
            mechanical_compatibility=0.0,
            chemical_resistance=score,
            aging_penalty=0.0,
            viable=viable,
            details=details,
        )

    def _apply_condition_modifiers(
        self,
        scores: Dict[str, float],
        material_a: PolymerMaterial,
        material_b: PolymerMaterial,
        conditions: PolymerConditions,
    ) -> Dict[str, float]:
        """Apply operating condition modifiers to raw scores."""
        modified = dict(scores)

        # High temperature effects
        if conditions.temperature_C > 80:
            # Elevated temperature accelerates aging
            temp_factor = max(0.5, 1.0 - (conditions.temperature_C - 80) / 300)
            modified['aging'] *= temp_factor
            # May soften thermoplastics (worse mechanical performance)
            modified['mechanical'] *= max(0.7, 1.0 - (conditions.temperature_C - 80) / 500)

        # Low temperature effects
        if conditions.temperature_C < -20:
            # Embrittlement below Tg
            modified['mechanical'] *= max(0.5, 1.0 + conditions.temperature_C / 100)

        # UV exposure
        if conditions.uv_exposure:
            from polymer_bridge.material_properties import PolymerFailureMode
            uv_sensitive = sum(
                1 for m in [material_a, material_b]
                if PolymerFailureMode.UV_DEGRADATION in m.failure_modes
            )
            if uv_sensitive > 0:
                modified['aging'] *= max(0.4, 1.0 - uv_sensitive * 0.25)

        # Wet/aqueous environment
        if conditions.chemical_environment == "water":
            modified['chemical_resistance'] *= 0.8
            # Extra penalty for hygroscopic materials
            for mat in [material_a, material_b]:
                if mat.water_absorption_pct and mat.water_absorption_pct > 5.0:
                    modified['chemical_resistance'] *= 0.7

        # High humidity
        if conditions.humidity_pct > 80:
            for mat in [material_a, material_b]:
                if mat.water_absorption_pct and mat.water_absorption_pct > 2.0:
                    modified['aging'] *= 0.85

        return modified

    def validate_all_interfaces(
        self,
        polymers: List[str],
        conditions: Optional[PolymerConditions] = None,
    ) -> Dict[Tuple[str, str], PolymerInterfaceScore]:
        """
        Validate all pairwise interfaces in a set of polymers.

        Args:
            polymers: List of polymer names
            conditions: Operating conditions

        Returns:
            Dict mapping (poly_a, poly_b) to PolymerInterfaceScore
        """
        results = {}
        for i in range(len(polymers)):
            for j in range(i + 1, len(polymers)):
                key = (polymers[i], polymers[j])
                try:
                    results[key] = self.validate(polymers[i], polymers[j], conditions)
                except ValueError:
                    pass
        return results


def validate_interface(
    polymer_a: str,
    polymer_b: str,
    conditions: Optional[PolymerConditions] = None,
    interface_role: Optional[str] = None,
) -> PolymerInterfaceScore:
    """Convenience function for quick interface validation.

    `interface_role` is forwarded to the validator's role-aware gate; the shared
    compatibility service (`_call_validator`) auto-supplies it from the request
    context, so coexistence/dispersion interfaces skip the immiscibility veto.
    """
    validator = PolymerInterfaceValidator()
    return validator.validate(polymer_a, polymer_b, conditions, interface_role)


if __name__ == "__main__":
    print("=" * 70)
    print("Polymer Interface Validator - Demo")
    print("=" * 70)
    print()

    validator = PolymerInterfaceValidator()

    # Good pairing
    print("--- PVDF + PMMA (miscible blend) ---")
    result = validator.validate('PVDF', 'PMMA')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Solubility:   {result.solubility_compatibility:.3f}")
    print(f"  Thermal:      {result.thermal_compatibility:.3f}")
    print(f"  Mechanical:   {result.mechanical_compatibility:.3f}")
    print(f"  Chem resist:  {result.chemical_resistance:.3f}")
    print(f"  Aging:        {result.aging_penalty:.3f}")
    print()

    # Bad pairing
    print("--- HDPE + PA6 (immiscible) ---")
    result = validator.validate('HDPE', 'PA6')
    print(f"  Total: {result.total:.3f}  Viable: {result.viable}")
    print(f"  Solubility:   {result.solubility_compatibility:.3f}")
    print(f"  Thermal:      {result.thermal_compatibility:.3f}")
    print(f"  Mechanical:   {result.mechanical_compatibility:.3f}")
    print(f"  Chem resist:  {result.chemical_resistance:.3f}")
    print(f"  Aging:        {result.aging_penalty:.3f}")
