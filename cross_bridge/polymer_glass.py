# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer-Glass Cross-Bridge Functor
==================================

Scores adhesive/sealant compatibility of a polymer bonded to a glass substrate
(encapsulants, laminates, sealants, coatings). Functor F: Polymer -> Glass.

Glass presents a high-energy, hydroxylated (silanol, Si-OH) surface. Adhesion is
governed by the polymer's ability to wet and chemically/physically couple to it
(Kinloch, "Adhesion and Adhesives", 1987; Pocius, "Adhesion and Adhesives
Technology", 2012):

- Polar / hydrogen-bonding polymers wet and bond well (captured here by the
  Hansen polar + hydrogen-bonding components delta_p, delta_h).
- Thermosets such as epoxy and polyurethane form covalent/strong polar bonds and
  are routinely silane-coupled to glass -> excellent adhesion.
- Silicones (siloxane backbone) condense with surface silanols (Si-O-Si), so
  RTV silicone sealants bond glass durably despite low Hansen polarity.
- Non-polar polyolefins and fluoropolymers (PE, PP, PTFE) have low surface
  energy and poor glass adhesion without surface treatment.
"""

import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Dict, List, Optional, Tuple

_root = str(_Path(__file__).resolve().parent.parent)
if _root not in _sys.path:
    _sys.path.insert(0, _root)

from polymer_bridge.material_properties import (
    PolymerMaterial,
    PolymerClass,
    get_polymer,
)
from glass_bridge.material_properties import GlassMaterial, get_glass


class UnknownMaterialError(ValueError):
    """Raised when a material cannot be resolved as a polymer or a glass."""


# Polymers whose backbone chemically couples to glass silanols (siloxanes).
_SILOXANE_ABBREVS = {"PDMS"}
# Low-surface-energy polymers that adhere poorly to glass without treatment.
_LOW_ENERGY_ABBREVS = {"PTFE", "HDPE", "LDPE", "PP", "PE"}


@dataclass
class PolymerGlassResult:
    compatible: bool
    score: float
    adhesion: float
    polymer_name: str
    glass_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def _orient_polymer_glass(arg1: str, arg2: str) -> Tuple[str, str]:
    """Return ``(polymer_name, glass_name)`` in the resolvable orientation."""
    if get_polymer(arg1) is not None and get_glass(arg2) is not None:
        return arg1, arg2
    if get_polymer(arg2) is not None and get_glass(arg1) is not None:
        return arg2, arg1
    unknown = [m for m in (arg1, arg2) if get_polymer(m) is None and get_glass(m) is None]
    if unknown:
        raise UnknownMaterialError(f"Unknown polymer-glass material(s): {', '.join(unknown)}")
    raise UnknownMaterialError(
        f"Cannot resolve a (polymer, glass) orientation for {arg1!r} + {arg2!r}"
    )


def _score_adhesion(polymer: PolymerMaterial) -> Tuple[float, Dict]:
    details: Dict = {}
    abbrev = (polymer.abbreviation or polymer.name or "").strip()
    details["polymer"] = abbrev

    # Siloxane backbone couples to surface silanols regardless of Hansen polarity.
    if abbrev in _SILOXANE_ABBREVS:
        details["mechanism"] = "siloxane-silanol condensation"
        return 0.85, details

    # Low-surface-energy polyolefins / fluoropolymers: poor untreated adhesion.
    if abbrev in _LOW_ENERGY_ABBREVS:
        details["mechanism"] = "low surface energy, poor untreated adhesion"
        return 0.3, details

    # Polar / hydrogen-bonding contribution from Hansen parameters.
    if polymer.hansen is not None:
        polar = (polymer.hansen.delta_p or 0.0) + (polymer.hansen.delta_h or 0.0)
        details["hansen_polar_plus_hbond"] = round(polar, 2)
        if polar >= 15.0:
            base = 0.9
        elif polar >= 10.0:
            base = 0.8
        elif polar >= 6.0:
            base = 0.62
        elif polar >= 3.0:
            base = 0.45
        else:
            base = 0.32
    else:
        base = 0.55
        details["note"] = "no Hansen data; neutral prior"

    # Thermosets (epoxy, polyurethane, phenolic) form strong covalent/polar bonds
    # and are routinely silane-coupled to glass.
    if polymer.polymer_class == PolymerClass.THERMOSET:
        base = min(1.0, base + 0.1)
        details["thermoset_coupling_bonus"] = True

    return base, details


def score_polymer_glass_compatibility(
    material_a: str,
    material_b: str,
    role: Optional[str] = None,
) -> PolymerGlassResult:
    """Score a polymer-to-glass bond. Arguments may be given in either order."""
    warnings: List[str] = []
    polymer_name, glass_name = _orient_polymer_glass(material_a, material_b)
    polymer = get_polymer(polymer_name)

    adhesion, details = _score_adhesion(polymer)
    composite = adhesion
    if adhesion < 0.35:
        warnings.append(
            f"Adhesion warning: {polymer_name} has low surface energy and bonds "
            f"poorly to glass without surface treatment / coupling agent"
        )

    compatible = composite >= 0.50
    return PolymerGlassResult(
        compatible=compatible,
        score=round(composite, 4),
        adhesion=round(adhesion, 4),
        polymer_name=polymer_name,
        glass_name=glass_name,
        warnings=warnings,
        details={"role": role, "adhesion": details},
    )


if __name__ == "__main__":
    for a, b, desc in [
        ("Epoxy", "Borosilicate", "epoxy on glass (excellent)"),
        ("Silicone", "Soda_Lime", "silicone sealant on glass (good)"),
        ("PTFE", "Soda_Lime", "fluoropolymer on glass (poor)"),
    ]:
        r = score_polymer_glass_compatibility(a, b)
        print(f"[{'PASS' if r.compatible else 'FAIL'}] {a}+{b}: {r.score:.3f} ({desc})")
        for w in r.warnings:
            print(f"     WARNING: {w}")
