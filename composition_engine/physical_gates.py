"""Physical plausibility gates for generated compositions (Prong B).

The analogue of the MOF funnel's hard gates, in composition space. The guiding
rule (learned from the MOF PAINS mistake): a gate must never reject a real
material. So we reject only DEFINITIVE failures and treat anything we cannot
assess as a pass.

Currently implements charge-balance feasibility via pymatgen oxidation-state
guessing. Fractional compositions (e.g. NMC811) are scaled to integers first,
since pymatgen's charge analysis requires integer stoichiometry.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd
from typing import Dict, Optional

try:
    from pymatgen.core import Composition
    _PMG = True
except Exception:  # pragma: no cover
    _PMG = False

_CACHE: Dict[str, Optional[bool]] = {}


def _to_integer_comp(amounts: Dict[str, float], max_mult: int = 24, maxden: int = 12) -> Optional[Dict[str, int]]:
    """Scale fractional amounts to the smallest integer cell (bounded)."""
    dens = [Fraction(v).limit_denominator(maxden).denominator for v in amounts.values()]
    m = 1
    for x in dens:
        m = m * x // gcd(m, x)
    if m > max_mult:
        m = max_mult
    scaled = {el: round(v * m) for el, v in amounts.items()}
    if any(v <= 0 for v in scaled.values()):
        return None
    return scaled


def charge_balanceable(formula: str) -> Optional[bool]:
    """Can the composition be charge-balanced with common oxidation states?

    Returns True / False when determinable, or None when it cannot be assessed
    (pymatgen missing, unparseable, or scaling failed). None must be treated as
    a pass by callers.
    """
    if not _PMG:
        return None
    if formula in _CACHE:
        return _CACHE[formula]
    result: Optional[bool] = None
    try:
        amounts = Composition(formula).get_el_amt_dict()
        scaled = _to_integer_comp(amounts)
        if scaled is not None:
            c = Composition(" ".join(f"{e}{n}" for e, n in scaled.items()))
            result = bool(c.oxi_state_guesses())
    except Exception:
        result = None
    _CACHE[formula] = result
    return result


def passes_physical_gates(formula: str) -> bool:
    """Reject only DEFINITIVE physical failures; unassessable -> pass."""
    return charge_balanceable(formula) is not False
