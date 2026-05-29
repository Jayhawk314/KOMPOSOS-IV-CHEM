# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Metal-Semiconductor Cross-Bridge Functor
========================================

Scores compatibility of a metal contact/metallization on a semiconductor
(ohmic contacts, gate/interconnect metallization). Functor F: Metal ->
Semiconductor.

Two considerations:

1. Metallization suitability. Decades of device practice establish which metals
   form usable, manufacturable contacts to which semiconductors (Sze & Ng,
   "Physics of Semiconductor Devices", 3rd ed.; Plummer, "Silicon VLSI
   Technology"). Al and Cu to Si are the canonical interconnect/contact metals;
   refractory metals (W, Ti, Ni, Co, Mo, Ta) form silicides; Au/Ge/Ni and
   Ti/Pt/Au are standard on GaAs. Reactive light metals on compound
   semiconductors (e.g. Al on GaAs) are problematic.

2. Thermal-mechanical stress. A very large CTE mismatch between a thick metal
   film and the semiconductor causes stress/cracking on thermal cycling; thin
   contact films are largely compliant, so this is a secondary penalty.
"""

import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Dict, List, Optional, Tuple

_root = str(_Path(__file__).resolve().parent.parent)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from metal_bridge.material_properties import MetalMaterial, get_metal
from semiconductor_bridge.material_properties import (
    SemiconductorMaterial,
    get_semiconductor,
)


class UnknownMaterialError(ValueError):
    """Raised when a material cannot be resolved as a metal or a semiconductor."""


# Standard contact/metallization metals by semiconductor (element symbol form).
# Source: Sze & Ng 2007; Plummer et al. 2000.
_STANDARD_CONTACT_METALS = {
    "Si": {"Al", "Cu", "W", "Ti", "Ni", "Co", "Mo", "Ta", "Pt", "Pd", "Au", "Ag"},
    "Ge": {"Al", "Au", "Ni", "Ti", "W"},
    "GaAs": {"Au", "Ti", "Pt", "Pd", "Ni", "W"},
    "GaN": {"Ti", "Al", "Ni", "Au", "Pt"},
    "SiC": {"Ni", "Ti", "Al", "W", "Mo"},
}

# Metal/compound-semiconductor pairs that are known to be problematic without an
# engineered barrier (reactive interdiffusion / poor morphology).
_PROBLEMATIC_PAIRS = {
    ("Al", "GaAs"),   # Al-Ga interdiffusion; Au or Ti/Pt/Au preferred
}


@dataclass
class MetalSemiconductorResult:
    compatible: bool
    score: float
    metallization_suitability: float
    thermal_stress: float
    metal_name: str
    semiconductor_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _orient_metal_semiconductor(arg1: str, arg2: str) -> Tuple[str, str]:
    """Return ``(metal_name, semiconductor_name)`` in the resolvable orientation."""
    if get_metal(arg1) is not None and get_semiconductor(arg2) is not None:
        return arg1, arg2
    if get_metal(arg2) is not None and get_semiconductor(arg1) is not None:
        return arg2, arg1
    unknown = [
        m for m in (arg1, arg2)
        if get_metal(m) is None and get_semiconductor(m) is None
    ]
    if unknown:
        raise UnknownMaterialError(
            f"Unknown metal-semiconductor material(s): {', '.join(unknown)}"
        )
    raise UnknownMaterialError(
        f"Cannot resolve a (metal, semiconductor) orientation for {arg1!r} + {arg2!r}"
    )


def _metal_symbol(metal: MetalMaterial) -> str:
    return (metal.formula or metal.name or "").strip()


def _score_metallization(
    metal: MetalMaterial, semi: SemiconductorMaterial
) -> Tuple[float, Dict]:
    details: Dict = {}
    symbol = _metal_symbol(metal)
    semi_key = (semi.formula or semi.name or "").strip()
    details["metal_symbol"] = symbol
    details["semiconductor"] = semi_key

    if (symbol, semi_key) in _PROBLEMATIC_PAIRS:
        details["known_problematic"] = True
        return 0.25, details

    standard = _STANDARD_CONTACT_METALS.get(semi_key, set())
    if symbol in standard:
        details["standard_contact_metal"] = True
        return 0.9, details

    # Unknown-but-conductive metal on a semiconductor: plausible contact but not
    # an established recipe -> moderate, sub-decision confidence.
    details["standard_contact_metal"] = False
    return 0.5, details


def _score_thermal_stress(
    metal: MetalMaterial, semi: SemiconductorMaterial
) -> Tuple[float, Dict]:
    details: Dict = {"metal_cte": metal.cte_per_K, "semiconductor_cte": semi.cte_per_K}
    if metal.cte_per_K is None or semi.cte_per_K is None:
        return 0.8, details  # thin films are largely compliant; mild default
    diff = abs(metal.cte_per_K - semi.cte_per_K)
    details["cte_difference"] = round(diff, 3)
    # Thin contact/metallization films tolerate substantial mismatch; only very
    # large differences meaningfully threaten thick-film/thermal-cycling cases.
    if diff < 10.0:
        return 1.0, details
    if diff < 20.0:
        return 0.85, details
    return 0.7, details


def score_metal_semiconductor_compatibility(
    material_a: str,
    material_b: str,
    role: Optional[str] = None,
) -> MetalSemiconductorResult:
    """Score a metal contact on a semiconductor. Arguments may be in either order."""
    warnings: List[str] = []
    metal_name, semi_name = _orient_metal_semiconductor(material_a, material_b)
    metal = get_metal(metal_name)
    semi = get_semiconductor(semi_name)

    m_score, m_details = _score_metallization(metal, semi)
    t_score, t_details = _score_thermal_stress(metal, semi)

    composite = 0.8 * m_score + 0.2 * t_score
    if m_score < 0.3:
        composite = min(composite, 0.4)
        warnings.append(
            f"Metallization veto: {metal_name} is not a suitable direct contact "
            f"for {semi_name} without an engineered diffusion barrier"
        )

    compatible = composite >= 0.50
    return MetalSemiconductorResult(
        compatible=compatible,
        score=round(composite, 4),
        metallization_suitability=round(m_score, 4),
        thermal_stress=round(t_score, 4),
        metal_name=metal_name,
        semiconductor_name=semi_name,
        warnings=warnings,
        details={"role": role, "metallization": m_details, "thermal": t_details},
    )


if __name__ == "__main__":
    for a, b, desc in [
        ("Si", "Cu", "standard Si interconnect (good)"),
        ("Si", "Al", "classic Si contact (good)"),
        ("Al", "GaAs", "reactive on GaAs (problematic)"),
    ]:
        r = score_metal_semiconductor_compatibility(a, b)
        print(f"[{'PASS' if r.compatible else 'FAIL'}] {a}+{b}: {r.score:.3f} ({desc})")
        for w in r.warnings:
            print(f"     WARNING: {w}")
