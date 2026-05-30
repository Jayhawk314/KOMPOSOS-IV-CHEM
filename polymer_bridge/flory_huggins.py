# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Flory-Huggins polymer miscibility helpers.

This module turns the G-docs prototype into reusable production logic:
chain-length-aware critical chi, symmetric chi lookup, and HSP fallback.
"""

from dataclasses import dataclass
from typing import Optional

from polymer_bridge.material_properties import PolymerMaterial


R_GAS_J_MOL_K = 8.314
ROOM_TEMPERATURE_K = 298.15
DEFAULT_REFERENCE_VOLUME_CM3_MOL = 100.0


EMPIRICAL_COMPATIBLE_INTERFACES = {
    ("ABS", "PC"): "commercial PC/ABS engineering blend",
    ("PEEK", "PTFE"): "PEEK/PTFE tribological composite interface",
    ("PPS", "PTFE"): "PPS/PTFE self-lubricating composite interface",
}


@dataclass(frozen=True)
class FloryHugginsAssessment:
    """Thermodynamic miscibility assessment for a polymer pair."""

    chi: Optional[float]
    chi_source: str
    critical_chi: Optional[float]
    degree_polymerization_a: Optional[float]
    degree_polymerization_b: Optional[float]
    miscible: Optional[bool]
    reason: str

    def to_dict(self) -> dict:
        return {
            "chi": self.chi,
            "chi_source": self.chi_source,
            "critical_chi": self.critical_chi,
            "degree_polymerization_a": self.degree_polymerization_a,
            "degree_polymerization_b": self.degree_polymerization_b,
            "miscible": self.miscible,
            "reason": self.reason,
        }


def degree_of_polymerization(material: PolymerMaterial) -> Optional[float]:
    """Return N = Mw / repeat-unit Mw when representative chain data exists."""
    repeat_mw = material.repeat_unit_mw_g_mol
    typical_mw = material.typical_mw_g_mol
    if repeat_mw is None or typical_mw is None:
        return None
    if repeat_mw <= 0 or typical_mw <= 0:
        return None
    return typical_mw / repeat_mw


def critical_chi(material_a: PolymerMaterial, material_b: PolymerMaterial) -> Optional[float]:
    """
    Flory-Huggins critical chi for binary polymer miscibility.

    chi_c = 0.5 * (N_a^-0.5 + N_b^-0.5)^2
    """
    n_a = degree_of_polymerization(material_a)
    n_b = degree_of_polymerization(material_b)
    if n_a is None or n_b is None:
        return None
    return 0.5 * ((n_a ** -0.5) + (n_b ** -0.5)) ** 2


def lookup_empirical_chi(material_a: PolymerMaterial, material_b: PolymerMaterial) -> Optional[float]:
    """
    Symmetric curated chi lookup.

    If either direction contains a negative value, preserve it as the empirical
    favorable-interaction override. Otherwise use the more conservative larger
    non-negative chi when bidirectional values disagree.
    """
    values = []
    if material_b.abbreviation in material_a.chi_parameters:
        values.append(material_a.chi_parameters[material_b.abbreviation])
    if material_a.abbreviation in material_b.chi_parameters:
        values.append(material_b.chi_parameters[material_a.abbreviation])
    if not values:
        return None
    negative_values = [value for value in values if value < 0]
    if negative_values:
        return min(negative_values)
    return max(values)


def estimate_chi_from_hansen(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
    temperature_K: float = ROOM_TEMPERATURE_K,
    reference_volume_cm3_mol: float = DEFAULT_REFERENCE_VOLUME_CM3_MOL,
) -> Optional[float]:
    """
    Estimate chi from Hansen parameter differences.

    Uses the common HSP-derived approximation:
    chi = Vr / RT * (dd^2 + 0.25 dp^2 + 0.25 dh^2)
    with MPa treated as J/cm3.
    """
    if material_a.hansen is None or material_b.hansen is None:
        return None
    if temperature_K <= 0 or reference_volume_cm3_mol <= 0:
        return None

    delta_d = material_a.hansen.delta_d - material_b.hansen.delta_d
    delta_p = material_a.hansen.delta_p - material_b.hansen.delta_p
    delta_h = material_a.hansen.delta_h - material_b.hansen.delta_h
    distance_sq = delta_d ** 2 + 0.25 * delta_p ** 2 + 0.25 * delta_h ** 2
    return (reference_volume_cm3_mol / (R_GAS_J_MOL_K * temperature_K)) * distance_sq


def assess_flory_huggins(
    material_a: PolymerMaterial,
    material_b: PolymerMaterial,
    temperature_K: float = ROOM_TEMPERATURE_K,
) -> FloryHugginsAssessment:
    """
    Evaluate miscibility using empirical chi when available, then HSP fallback.

    Returns miscible=None when the available data cannot support a thermodynamic
    verdict. A negative empirical chi is always treated as favorable.
    """
    pair_key = tuple(sorted((material_a.abbreviation, material_b.abbreviation)))
    empirical_interface_reason = EMPIRICAL_COMPATIBLE_INTERFACES.get(pair_key)
    n_a = degree_of_polymerization(material_a)
    n_b = degree_of_polymerization(material_b)
    chi_c = critical_chi(material_a, material_b)
    if empirical_interface_reason is not None:
        return FloryHugginsAssessment(
            chi=0.0,
            chi_source="empirical_compatibility_override",
            critical_chi=chi_c,
            degree_polymerization_a=n_a,
            degree_polymerization_b=n_b,
            miscible=True,
            reason=empirical_interface_reason,
        )

    chi = lookup_empirical_chi(material_a, material_b)
    chi_source = "empirical"
    if chi is None:
        chi = estimate_chi_from_hansen(material_a, material_b, temperature_K)
        chi_source = "hansen_estimate" if chi is not None else "unavailable"

    if chi is None:
        return FloryHugginsAssessment(
            chi=None,
            chi_source=chi_source,
            critical_chi=chi_c,
            degree_polymerization_a=n_a,
            degree_polymerization_b=n_b,
            miscible=None,
            reason="no_chi_data",
        )

    if chi < 0:
        return FloryHugginsAssessment(
            chi=chi,
            chi_source=chi_source,
            critical_chi=chi_c,
            degree_polymerization_a=n_a,
            degree_polymerization_b=n_b,
            miscible=True,
            reason="negative_empirical_chi",
        )

    if chi_c is None:
        return FloryHugginsAssessment(
            chi=chi,
            chi_source=chi_source,
            critical_chi=None,
            degree_polymerization_a=n_a,
            degree_polymerization_b=n_b,
            miscible=None,
            reason="missing_chain_length_for_chi_c",
        )

    miscible = chi <= chi_c
    return FloryHugginsAssessment(
        chi=chi,
        chi_source=chi_source,
        critical_chi=chi_c,
        degree_polymerization_a=n_a,
        degree_polymerization_b=n_b,
        miscible=miscible,
        reason="chi_below_critical" if miscible else "chi_above_critical",
    )
