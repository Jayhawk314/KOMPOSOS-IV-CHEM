# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Machine-learned interatomic potential (MLIP) as a typed *intermediate* oracle.

Design stance, and why this is safe to add:

* This sits BETWEEN the composition-only KOMPOSOS surrogate (~ms, no structure
  needed) and real DFT (`oracle/dft_integration.py`, minutes-hours, terminal).
  A pretrained MLIP is ~100 ms and needs a 3D structure, so it occupies the
  shortlist-rescoring slot: too slow for the inner generative loop, far too cheap
  to be terminal.

* **An MLIP is NOT DFT.** CHGNet is a surrogate *of* MP PBE, trained on MPtrj
  relaxation trajectories. It is therefore typed ``Family.SURROGATE`` with
  ``Provenance.SURROGATE`` -- never ``Family.DFT``. Labelling an MLIP number
  "DFT" would be precisely the precise-looking liability `core/level_of_theory`
  exists to prevent. Crossing to ``PBE_MP`` requires the explicit
  :data:`MLIP_TO_PBE_MP` conversion, which records the uncertainty it adds.

* If no MLIP backend is installed the oracle RAISES
  :class:`~core.errors.OracleUnavailable`. It never fabricates a number and never
  silently downgrades to the composition surrogate while keeping the MLIP label.

* **A structure is required.** The composition-only predictor answers from a
  formula; this cannot. That is a capability boundary, not a bug: callers that
  have only a formula must stay on the surrogate tier. `predict_formation_energy`
  raises rather than inventing a structure.

Formation energies need elemental references. CHGNet returns a *total* energy per
atom in its own reference, so
``E_f = E_total - sum_i x_i * mu_i``. The chemical potentials ``mu_i`` are FITTED
by least squares against known formation energies
(:func:`fit_elemental_potentials`) rather than assumed, because elemental ground
states (O2, N2, S8, white P) are not all constructible crystals. The fit is a
calibration and must be trained on data disjoint from any evaluation set --
:func:`fit_elemental_potentials` takes an explicit training list so the caller
owns that split.

Install the backend with ``pip install chgnet`` (pretrained weights ship inside
the package, so it works offline).
"""

from __future__ import annotations

import importlib.util
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.errors import OracleUnavailable
from core.level_of_theory import (
    Conversion,
    Family,
    LevelOfTheory,
    Provenance,
    TypedQuantity,
    PBE_MP,
)

# --- levels -----------------------------------------------------------------

#: CHGNet pretrained on MPtrj. A SURROGATE of MP PBE, not DFT itself.
CHGNET_MPTRJ = LevelOfTheory(
    Family.SURROGATE,
    method="CHGNet",
    basis="MPtrj-pretrained",
    label="surrogate:CHGNet(MPtrj)",
)

#: The only sanctioned way to read a CHGNet number as an MP-PBE number.
#: `added_uncertainty` is the model's own reported energy MAE on MPtrj; callers
#: that measure a different value on their own corpus should build their own
#: Conversion rather than editing this one.
MLIP_TO_PBE_MP = Conversion(
    source=CHGNET_MPTRJ,
    target=PBE_MP,
    rationale=(
        "CHGNet is trained to reproduce MP GGA/GGA+U (PBE) energies on MPtrj. "
        "Reading its output as an MP-PBE value is a surrogate->reference lift and "
        "carries the model's own energy error, which is NOT reduced by the lift."
    ),
    added_uncertainty=0.03,  # eV/atom, CHGNet reported MPtrj energy MAE
)

_MODEL = None
_BACKEND: Optional[str] = None


def backend_available() -> bool:
    """True if an MLIP backend is importable. Does not load the model."""
    return importlib.util.find_spec("chgnet") is not None


def _load_model():
    """Load and memoize the pretrained model. Raises OracleUnavailable if absent."""
    global _MODEL, _BACKEND
    if _MODEL is not None:
        return _MODEL
    if not backend_available():
        raise OracleUnavailable(
            oracle="mlip:chgnet",
            reason="no MLIP backend installed",
            remediation=(
                "pip install chgnet (pretrained weights ship with the package, so "
                "it works offline). This oracle deliberately does NOT fall back to "
                "the composition surrogate: returning a surrogate number under an "
                "MLIP label would misreport the level of theory."
            ),
        )
    from chgnet.model import CHGNet  # lazy: heavy import
    _MODEL = CHGNet.load()
    _BACKEND = "chgnet"
    return _MODEL


@dataclass
class MLIPResult:
    """One MLIP evaluation, with its typed energy and timing."""

    formula: str
    n_sites: int
    total_energy_per_atom: TypedQuantity
    formation_energy_per_atom: Optional[TypedQuantity] = None
    max_force_eV_per_A: Optional[float] = None
    seconds: float = 0.0
    meta: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "formula": self.formula,
            "n_sites": self.n_sites,
            "total_energy_per_atom": self.total_energy_per_atom.to_dict(),
            "formation_energy_per_atom": (
                self.formation_energy_per_atom.to_dict()
                if self.formation_energy_per_atom is not None else None
            ),
            "max_force_eV_per_A": self.max_force_eV_per_A,
            "seconds": round(self.seconds, 4),
            "meta": self.meta,
        }


def predict_total_energy(structure) -> MLIPResult:
    """Total energy per atom for a pymatgen Structure, typed as a surrogate.

    Raises OracleUnavailable if no backend is installed.
    """
    model = _load_model()
    t0 = time.perf_counter()
    out = model.predict_structure(structure)
    dt = time.perf_counter() - t0

    e_per_atom = float(out["e"])
    forces = out.get("f")
    max_f = None
    if forces is not None:
        try:
            max_f = float(max(sum(c * c for c in row) ** 0.5 for row in forces))
        except Exception:
            max_f = None

    energy = TypedQuantity(
        e_per_atom,
        "eV/atom",
        CHGNET_MPTRJ,
        Provenance.SURROGATE,
        uncertainty=MLIP_TO_PBE_MP.added_uncertainty,
        meta={"backend": _BACKEND or "chgnet", "quantity": "total_energy"},
    )
    return MLIPResult(
        formula=structure.composition.reduced_formula,
        n_sites=len(structure),
        total_energy_per_atom=energy,
        max_force_eV_per_A=max_f,
        seconds=dt,
    )


def relax_structure(structure, fmax: float = 0.1, steps: int = 200):
    """Relax a structure with the MLIP and return (relaxed_structure, info).

    An MLIP energy is only meaningful at (or near) a local minimum of that same
    potential. Scoring an idealized, unrelaxed prototype measures the strain in
    the guessed geometry as much as the chemistry, so relaxation is part of the
    correct protocol rather than an optimisation.

    Raises OracleUnavailable if no backend is installed.
    """
    _load_model()
    from chgnet.model import StructOptimizer  # lazy
    opt = StructOptimizer()
    t0 = time.perf_counter()
    result = opt.relax(structure, fmax=fmax, steps=steps, verbose=False)
    dt = time.perf_counter() - t0
    relaxed = result["final_structure"]
    traj = result.get("trajectory")
    info = {
        "seconds": dt,
        "fmax": fmax,
        "steps_allowed": steps,
        "n_steps": len(getattr(traj, "energies", []) or []),
    }
    return relaxed, info


def _fractional_composition(structure) -> Dict[str, float]:
    comp = structure.composition.element_composition
    total = sum(comp.values())
    return {str(el): amt / total for el, amt in comp.items()}


def fit_elemental_potentials(
    training: Sequence[Tuple[object, float]],
    ridge: float = 1e-8,
) -> Dict[str, float]:
    """Least-squares fit of elemental chemical potentials mu_i.

    ``training`` is a sequence of ``(structure, known_formation_energy_per_atom)``.
    Solves ``E_total - sum_i x_i mu_i ~= E_f`` for mu.

    This is a CALIBRATION. It must be fitted on data disjoint from whatever it is
    later evaluated on; this function deliberately takes an explicit training list
    rather than choosing a split itself, so the caller owns and can document that
    separation.
    """
    if not training:
        raise ValueError("no training data for elemental potential fit")

    rows, targets, elements = [], [], []
    seen = set()
    prepared = []
    for structure, ef in training:
        res = predict_total_energy(structure)
        frac = _fractional_composition(structure)
        prepared.append((frac, res.total_energy_per_atom.value, float(ef)))
        for el in frac:
            if el not in seen:
                seen.add(el)
                elements.append(el)
    elements.sort()
    index = {el: i for i, el in enumerate(elements)}

    for frac, e_tot, ef in prepared:
        row = [0.0] * len(elements)
        for el, x in frac.items():
            row[index[el]] = x
        rows.append(row)
        targets.append(e_tot - ef)  # E_total - E_f = sum x_i mu_i

    # normal equations with tiny ridge for conditioning
    n = len(elements)
    ata = [[0.0] * n for _ in range(n)]
    atb = [0.0] * n
    for row, t in zip(rows, targets):
        for i in range(n):
            if row[i] == 0.0:
                continue
            atb[i] += row[i] * t
            for j in range(n):
                if row[j] != 0.0:
                    ata[i][j] += row[i] * row[j]
    for i in range(n):
        ata[i][i] += ridge

    mu = _solve(ata, atb)
    return {el: mu[index[el]] for el in elements}


def _solve(a: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting (no numpy dependency needed)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-14:
            continue
        m[col], m[piv] = m[piv], m[col]
        pv = m[col][col]
        for r in range(n):
            if r == col:
                continue
            f = m[r][col] / pv
            if f:
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] if abs(m[i][i]) > 1e-14 else 0.0 for i in range(n)]


def predict_formation_energy(
    structure,
    elemental_potentials: Dict[str, float],
) -> MLIPResult:
    """Formation energy per atom from a structure and fitted elemental potentials.

    Raises OracleUnavailable if no backend is installed, and ValueError if the
    structure contains an element the potentials do not cover -- it will not
    extrapolate silently over a missing element.
    """
    res = predict_total_energy(structure)
    frac = _fractional_composition(structure)
    missing = sorted(set(frac) - set(elemental_potentials))
    if missing:
        raise ValueError(
            f"no fitted elemental potential for {missing}; refusing to extrapolate"
        )
    ref = sum(x * elemental_potentials[el] for el, x in frac.items())
    ef = res.total_energy_per_atom.value - ref

    res.formation_energy_per_atom = TypedQuantity(
        ef,
        "eV/atom",
        CHGNET_MPTRJ,
        Provenance.SURROGATE,
        uncertainty=MLIP_TO_PBE_MP.added_uncertainty,
        meta={
            "quantity": "formation_energy",
            "reference": "fitted elemental chemical potentials (least squares)",
        },
    )
    return res


def save_elemental_potentials(mu: Dict[str, float], path: Path, meta: Optional[Dict] = None) -> None:
    payload = {
        "level_of_theory": CHGNET_MPTRJ.label,
        "note": "Fitted elemental chemical potentials mu_i for E_f = E_total - sum x_i mu_i",
        "meta": meta or {},
        "potentials": mu,
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_elemental_potentials(path: Path) -> Dict[str, float]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {k: float(v) for k, v in data["potentials"].items()}
