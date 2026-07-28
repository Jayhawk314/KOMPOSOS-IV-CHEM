# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Levels of theory as first-class types on chemical quantities.

The central discipline this module enforces: a number produced by a B3LYP/6-31G*
calculation, a number measured in a calorimeter, and a number interpolated by the
KOMPOSOS surrogate are *different kinds of claim*. They must not be silently
averaged, subtracted, or composed. Current pipelines mix them freely -- that is a
root cause of irreproducibility in computational chemistry/materials work.

A :class:`TypedQuantity` carries its value together with the
:class:`LevelOfTheory` that produced it and a provenance tag. Arithmetic between
two TypedQuantities at *different* levels raises
:class:`~core.errors.TheoryCompositionError`. Crossing levels is only possible via
an explicit, documented :class:`Conversion` (the analogue of a cartesian lift in
the level-of-theory fibration), which records the uncertainty it adds.

This is the prerequisite for adding genuine DFT into the runtime safely: DFT
itself is level-dependent (functional choice flips spin-state and tautomer
ground states), so an *untyped* DFT number is a precise-looking liability. Tag it,
and it composes only with things it is actually comparable to.

Example::

    surrogate = TypedQuantity(-1.61, "eV/atom", SURROGATE_KAN, Provenance.COMPUTATIONAL)
    dft       = TypedQuantity(-1.58, "eV/atom", PBE_MP, Provenance.COMPUTATIONAL)
    surrogate - dft                      # -> TheoryCompositionError
    surrogate.lifted_to(PBE_MP, conv) - dft   # ok, uncertainty amplified
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, Optional

from .errors import ProvenancePromotionError, TheoryCompositionError


class Provenance(str, enum.Enum):
    """How a quantity was obtained. Computational is never promoted to measured."""

    EXPERIMENTAL = "experimental"      # measured in the physical world
    COMPUTATIONAL = "computational"    # produced by a simulation (DFT/MD/...)
    SURROGATE = "surrogate"            # ML/categorical surrogate of a simulation
    LITERATURE = "literature"          # asserted in a paper (claim, not re-measured)
    CURATED = "curated"                # human-curated reference value


class Family(str, enum.Enum):
    """Coarse family of a level of theory -- used for compatibility grouping."""

    DFT = "dft"
    WAVEFUNCTION = "wavefunction"      # HF, MP2, CCSD(T), ...
    SEMIEMPIRICAL = "semiempirical"    # xtb, PM6, ...
    FORCE_FIELD = "force_field"        # classical MD
    SURROGATE = "surrogate"            # KOMPOSOS Kan/Miedema surrogate, ML
    EXPERIMENT = "experiment"
    LITERATURE = "literature"


@dataclass(frozen=True)
class LevelOfTheory:
    """An immutable, hashable specification of how a number was produced.

    For DFT/wavefunction levels the structural fields (method, basis, ...) carry
    the real content. For experimental/literature/surrogate "levels" the
    distinguished classmethods below should be used; their structural fields are
    left empty and identity is by ``label``/``family``.

    Two levels are *the same* iff all defining fields match. Two levels are
    *compatible* (composable without conversion) iff :meth:`is_compatible_with`
    returns True -- by default that means identical, which is the strict and
    correct default.
    """

    family: Family
    method: str = ""                 # e.g. "B3LYP", "wB97X-D", "CCSD(T)"
    basis: str = ""                  # e.g. "6-31G*", "def2-TZVP"
    dispersion: str = ""             # e.g. "D3BJ", "" if none/in-functional
    solvation: str = ""              # e.g. "CPCM(water)", "" for gas phase
    spin_treatment: str = ""         # e.g. "RKS", "UKS", "broken-symmetry"
    relativistic: str = ""           # e.g. "", "ZORA", "DKH2"
    label: str = ""                  # human label; auto-filled for structural levels

    def __post_init__(self) -> None:
        if not self.label:
            object.__setattr__(self, "label", self._auto_label())

    def _auto_label(self) -> str:
        if self.family in (Family.EXPERIMENT, Family.LITERATURE, Family.SURROGATE):
            return self.family.value
        parts = [self.method]
        if self.basis:
            parts.append(self.basis)
        tail = "+".join(p for p in (self.dispersion, self.solvation,
                                    self.spin_treatment, self.relativistic) if p)
        core = "/".join(p for p in parts if p) or self.family.value
        return f"{core}" + (f" [{tail}]" if tail else "")

    # -- distinguished, non-structural levels -------------------------------
    @classmethod
    def experimental(cls, technique: str = "") -> "LevelOfTheory":
        return cls(Family.EXPERIMENT, label=f"experimental:{technique}" if technique
                   else "experimental")

    @classmethod
    def literature(cls, source: str = "") -> "LevelOfTheory":
        return cls(Family.LITERATURE, label=f"literature:{source}" if source
                   else "literature")

    @classmethod
    def surrogate(cls, name: str) -> "LevelOfTheory":
        return cls(Family.SURROGATE, method=name, label=f"surrogate:{name}")

    # -- comparison ----------------------------------------------------------
    def is_compatible_with(self, other: "LevelOfTheory") -> bool:
        """Can quantities at these two levels be combined WITHOUT a conversion?

        Strict default: only identical levels are compatible. This is the whole
        point -- B3LYP/6-31G* is not interchangeable with wB97X-D/def2-TZVP, and
        a surrogate estimate is not interchangeable with DFT.
        """
        return self == other

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.label


# ---------------------------------------------------------------------------
# A small registry of standard levels relevant to the proof problems.
# ---------------------------------------------------------------------------

#: KOMPOSOS formation-energy surrogate (Kan extension over MP DFT + Miedema/Kapustinskii).
SURROGATE_KAN = LevelOfTheory.surrogate("kan+miedema")

#: Materials Project reference DFT (GGA / GGA+U, PBE). What the surrogate is trained on.
PBE_MP = LevelOfTheory(Family.DFT, method="GGA-PBE", basis="PW(MP)",
                       label="DFT:GGA-PBE (Materials Project)")

#: Common molecular DFT levels (for linker / molecular proofs via Psi4 or PySCF).
B3LYP_631G = LevelOfTheory(Family.DFT, method="B3LYP", basis="6-31G*")
B3LYP_def2TZVP_D3 = LevelOfTheory(Family.DFT, method="B3LYP", basis="def2-TZVP",
                                  dispersion="D3BJ")
WB97XD_def2TZVP = LevelOfTheory(Family.DFT, method="wB97X-D", basis="def2-TZVP")
PBE0_def2SVP = LevelOfTheory(Family.DFT, method="PBE0", basis="def2-SVP")

EXPERIMENT = LevelOfTheory.experimental()

STANDARD_LEVELS: Dict[str, LevelOfTheory] = {
    lvl.label: lvl for lvl in (
        SURROGATE_KAN, PBE_MP, B3LYP_631G, B3LYP_def2TZVP_D3,
        WB97XD_def2TZVP, PBE0_def2SVP, EXPERIMENT,
    )
}


@dataclass(frozen=True)
class Conversion:
    """A documented procedure to move a value from one level to another.

    This is the explicit "cartesian lift" -- the ONLY sanctioned way to cross
    levels. It records the multiplicative/additive uncertainty it introduces so
    that downstream error bars stay honest.

    ``transform`` maps the source value to the target level's value. If omitted,
    the value is assumed transferable as-is (identity) but the uncertainty is
    still amplified.
    """

    source: LevelOfTheory
    target: LevelOfTheory
    rationale: str
    added_uncertainty: float = 0.0           # absolute, in the quantity's unit
    transform: Optional[Callable[[float], float]] = None

    def apply(self, value: float) -> float:
        return self.transform(value) if self.transform is not None else value


@dataclass
class TypedQuantity:
    """A scalar that knows the level of theory and provenance that produced it.

    Arithmetic is gated: two TypedQuantities combine only if their levels are
    compatible (identical by default), otherwise :class:`TheoryCompositionError`
    is raised. This is enforced for ``+``, ``-`` and :meth:`combine`.
    """

    value: float
    unit: str
    level: LevelOfTheory
    provenance: Provenance
    uncertainty: float = 0.0                  # absolute 1-sigma-ish, in ``unit``
    meta: Dict[str, str] = field(default_factory=dict)

    # -- gate helpers --------------------------------------------------------
    def _check(self, other: "TypedQuantity", op: str) -> None:
        if not isinstance(other, TypedQuantity):
            raise TypeError(f"cannot {op} TypedQuantity with {type(other).__name__}")
        if self.unit != other.unit:
            raise TheoryCompositionError(f"{self.level} <{self.unit}>",
                                         f"{other.level} <{other.unit}>", op)
        if not self.level.is_compatible_with(other.level):
            raise TheoryCompositionError(self.level, other.level, op)

    def __add__(self, other: "TypedQuantity") -> "TypedQuantity":
        self._check(other, "add")
        return TypedQuantity(self.value + other.value, self.unit, self.level,
                             self._merged_provenance(other),
                             self.uncertainty + other.uncertainty)

    def __sub__(self, other: "TypedQuantity") -> "TypedQuantity":
        self._check(other, "subtract")
        return TypedQuantity(self.value - other.value, self.unit, self.level,
                             self._merged_provenance(other),
                             self.uncertainty + other.uncertainty)

    def _merged_provenance(self, other: "TypedQuantity") -> Provenance:
        # Mixing measured + computed yields the weaker (computational) claim.
        if self.provenance == other.provenance:
            return self.provenance
        return Provenance.COMPUTATIONAL

    # -- explicit, sanctioned level crossing --------------------------------
    def lifted_to(self, target: LevelOfTheory, conv: Conversion) -> "TypedQuantity":
        """Return this quantity expressed at ``target`` via an explicit conversion.

        Raises if the conversion's endpoints don't match this quantity and the
        requested target -- you cannot apply an unrelated conversion.
        """
        if conv.source != self.level or conv.target != target:
            raise TheoryCompositionError(
                f"{self.level} -> {target}",
                f"conversion {conv.source} -> {conv.target}",
                "lift",
            )
        new_val = conv.apply(self.value)
        new_unc = self.uncertainty + conv.added_uncertainty
        m = dict(self.meta)
        m["lifted_from"] = self.level.label
        m["lift_rationale"] = conv.rationale
        return TypedQuantity(new_val, self.unit, target, self.provenance, new_unc, m)

    def asserted_as_measured(self) -> "TypedQuantity":
        """Promote to experimental provenance -- forbidden for computed values."""
        if self.provenance in (Provenance.COMPUTATIONAL, Provenance.SURROGATE):
            raise ProvenancePromotionError(self.provenance.value,
                                           Provenance.EXPERIMENTAL.value)
        return replace(self, provenance=Provenance.EXPERIMENTAL)

    def to_dict(self) -> Dict[str, object]:
        return {
            "value": self.value,
            "unit": self.unit,
            "uncertainty": self.uncertainty,
            "level_of_theory": self.level.label,
            "level_family": self.level.family.value,
            "provenance": self.provenance.value,
            "meta": self.meta,
        }

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        pm = f" +/- {self.uncertainty:g}" if self.uncertainty else ""
        return f"{self.value:g}{pm} {self.unit} @ {self.level} ({self.provenance.value})"


def from_formation_energy_result(result: object) -> TypedQuantity:
    """Adapter: wrap a ``FormationEnergyResult`` as a typed surrogate quantity.

    Lets the existing predictor feed the typed pipeline without modifying it.
    Tags the value as ``surrogate:kan+miedema`` so it can never be silently
    combined with a DFT or experimental formation energy.
    """
    ef = float(getattr(result, "ef_per_atom"))
    err = float(getattr(result, "error_estimate_eV", 0.0) or 0.0)
    meta = {
        "uncertainty_tier": str(getattr(getattr(result, "uncertainty_tier", ""),
                                        "value", getattr(result, "uncertainty_tier", ""))),
        "calibration_status": str(getattr(result, "calibration_status", "")),
        "chemistry_class": str(getattr(result, "chemistry_class", "")),
    }
    return TypedQuantity(ef, "eV/atom", SURROGATE_KAN, Provenance.SURROGATE,
                         uncertainty=err, meta=meta)
