# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Glass-Metal Cross-Bridge Functor
================================

Scores compatibility for glass-to-metal seals (hermetic packages, feedthroughs,
lamp/vacuum envelopes). Functor F: Glass -> Metal mapping sealing constraints.

Two physical failure modes dominate, and BOTH must pass:

1. CTE mismatch (mechanical). A *matched* seal needs the glass and metal to
   contract together on cooling from the sealing temperature; a large
   coefficient-of-thermal-expansion difference cracks the glass or breaks the
   hermetic bond. Kovar (ASTM F15, ~5.1 ppm/K) is engineered to match
   borosilicate for exactly this reason.

2. Chemical reactivity at the interface. A good seal also needs a stable,
   adherent oxide bond. Active/getter metals (Ti, Zr, Al, Mg, Ta, Nb, Be)
   thermodynamically REDUCE silicate glass at sealing temperature, forming
   brittle, non-hermetic interfacial phases. This is why titanium does not make
   a reliable direct seal to soda-lime glass even though their CTEs are close —
   the failure is chemical, not CTE.
"""

import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Dict, List, Optional, Tuple

_root = str(_Path(__file__).resolve().parent.parent)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from glass_bridge.material_properties import GlassMaterial, get_glass
from metal_bridge.material_properties import MetalMaterial, get_metal


class UnknownMaterialError(ValueError):
    """Raised when a material cannot be resolved as a glass or a metal."""


# Active / getter metals that thermodynamically reduce silicate glass at sealing
# temperatures, forming brittle non-hermetic interfaces. Source: Kohl,
# "Handbook of Materials and Techniques for Vacuum Devices" (glass-to-metal
# sealing); Donald, "Glass-to-Metal Seals" (Soc. Glass Tech., 2009).
_GLASS_REACTIVE_METAL_SYMBOLS = {"Ti", "Zr", "Al", "Mg", "Ta", "Nb", "Be", "Hf"}


@dataclass
class GlassMetalResult:
    compatible: bool
    score: float
    cte_compatibility: float
    chemical_compatibility: float
    glass_name: str
    metal_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _orient_glass_metal(arg1: str, arg2: str) -> Tuple[str, str]:
    """Return ``(glass_name, metal_name)`` in the orientation where both resolve."""
    if get_glass(arg1) is not None and get_metal(arg2) is not None:
        return arg1, arg2
    if get_glass(arg2) is not None and get_metal(arg1) is not None:
        return arg2, arg1
    unknown = [m for m in (arg1, arg2) if get_glass(m) is None and get_metal(m) is None]
    if unknown:
        raise UnknownMaterialError(f"Unknown glass-metal material(s): {', '.join(unknown)}")
    raise UnknownMaterialError(
        f"Cannot resolve a (glass, metal) orientation for {arg1!r} + {arg2!r}"
    )


def _score_cte(glass: GlassMaterial, metal: MetalMaterial) -> Tuple[float, Dict]:
    details: Dict = {"glass_cte": glass.cte_per_K, "metal_cte": metal.cte_per_K}
    if glass.cte_per_K is None or metal.cte_per_K is None:
        details["note"] = "missing CTE data"
        return 0.5, details
    diff = abs(glass.cte_per_K - metal.cte_per_K)
    details["cte_difference"] = round(diff, 3)
    if diff < 0.5:
        score = 1.0
    elif diff < 1.0:
        score = 0.9
    elif diff < 2.0:
        score = 0.75
    elif diff < 3.0:
        score = 0.5
    elif diff < 5.0:
        score = 0.3
    else:
        score = 0.1
    return score, details


def _score_chemistry(metal: MetalMaterial, metal_name: str) -> Tuple[float, Dict]:
    details: Dict = {}
    meta = metal.metadata or {}
    symbol = (metal.formula or "").strip()
    if meta.get("sealing_alloy") or meta.get("controlled_expansion"):
        details["sealing_alloy"] = True
        return 0.95, details
    if symbol in _GLASS_REACTIVE_METAL_SYMBOLS:
        details["glass_reactive_metal"] = symbol
        return 0.2, details
    # Standard sealing/housekeeper metals (stainless, Ni, Cu, Fe, noble metals)
    # form stable adherent oxide bonds to silicate glass.
    details["note"] = "standard non-reactive sealing metal"
    return 0.8, details


def score_glass_metal_compatibility(
    material_a: str,
    material_b: str,
    role: Optional[str] = None,
) -> GlassMetalResult:
    """Score a glass-to-metal seal. Arguments may be given in either order."""
    warnings: List[str] = []
    glass_name, metal_name = _orient_glass_metal(material_a, material_b)
    glass = get_glass(glass_name)
    metal = get_metal(metal_name)

    cte_score, cte_details = _score_cte(glass, metal)
    chem_score, chem_details = _score_chemistry(metal, metal_name)

    # CTE is the primary matched-seal constraint; chemistry gates hermeticity.
    composite = 0.6 * cte_score + 0.4 * chem_score

    if chem_score < 0.3:
        composite = min(composite, 0.35)
        warnings.append(
            f"Reactivity veto: {metal_name} reduces silicate glass at sealing "
            f"temperature, forming a brittle non-hermetic interface"
        )
    if cte_score < 0.2:
        composite = min(composite, 0.3)
        warnings.append(f"CTE veto: {glass_name} vs {metal_name} expansion mismatch too large")

    compatible = composite >= 0.50
    return GlassMetalResult(
        compatible=compatible,
        score=round(composite, 4),
        cte_compatibility=round(cte_score, 4),
        chemical_compatibility=round(chem_score, 4),
        glass_name=glass_name,
        metal_name=metal_name,
        warnings=warnings,
        details={"role": role, "cte": cte_details, "chemical": chem_details},
    )


if __name__ == "__main__":
    for a, b, desc in [
        ("Kovar", "Borosilicate", "matched hermetic seal (good)"),
        ("Titanium", "Soda_Lime", "CTE-close but Ti reduces glass (bad seal)"),
        ("SS_316", "Borosilicate", "stainless to boro (CTE mismatch)"),
    ]:
        r = score_glass_metal_compatibility(a, b)
        print(f"[{'PASS' if r.compatible else 'FAIL'}] {a}+{b}: {r.score:.3f} ({desc})")
        for w in r.warnings:
            print(f"     WARNING: {w}")
