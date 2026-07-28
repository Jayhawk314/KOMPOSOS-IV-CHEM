# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for the MLIP (CHGNet) typed oracle.

The behavioural contracts that matter here are the epistemic ones: an MLIP is a
SURROGATE of DFT and must never be typed or reported as DFT, it must refuse
rather than fabricate when unavailable, and it must refuse to extrapolate over
elements it has no fitted reference for.
"""

from __future__ import annotations

import pytest

from core.errors import OracleUnavailable
from core.level_of_theory import Family, PBE_MP, Provenance, TypedQuantity
from oracle import mlip_integration as M


def test_mlip_level_is_surrogate_not_dft():
    """An MLIP is a surrogate OF DFT. Typing it as DFT would misreport it."""
    assert M.CHGNET_MPTRJ.family is Family.SURROGATE
    assert M.CHGNET_MPTRJ.family is not Family.DFT
    assert "CHGNet" in M.CHGNET_MPTRJ.label


def test_mlip_level_not_compatible_with_dft_without_conversion():
    """Surrogate and DFT quantities must not combine silently."""
    assert not M.CHGNET_MPTRJ.is_compatible_with(PBE_MP)


def test_conversion_to_pbe_adds_uncertainty_and_does_not_shrink_it():
    conv = M.MLIP_TO_PBE_MP
    assert conv.source == M.CHGNET_MPTRJ
    assert conv.target == PBE_MP
    assert conv.added_uncertainty > 0

    q = TypedQuantity(-1.5, "eV/atom", M.CHGNET_MPTRJ, Provenance.SURROGATE,
                      uncertainty=0.01)
    lifted = q.lifted_to(PBE_MP, conv)
    assert lifted.level == PBE_MP
    assert lifted.uncertainty > q.uncertainty


def test_surrogate_cannot_be_promoted_to_measured():
    from core.errors import ProvenancePromotionError
    q = TypedQuantity(-1.5, "eV/atom", M.CHGNET_MPTRJ, Provenance.SURROGATE)
    with pytest.raises(ProvenancePromotionError):
        q.asserted_as_measured()


def test_raises_when_backend_missing_rather_than_fabricating(monkeypatch):
    """No backend must mean OracleUnavailable, never a silent fallback number."""
    monkeypatch.setattr(M, "_MODEL", None)
    monkeypatch.setattr(M, "backend_available", lambda: False)
    with pytest.raises(OracleUnavailable):
        M._load_model()


def test_formation_energy_refuses_unknown_element():
    """Missing an elemental reference must raise, not extrapolate."""
    pytest.importorskip("pymatgen")
    from pymatgen.core import Lattice, Structure

    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(4.2), ["Mg", "O"],
                                  [[0, 0, 0], [0.5, 0.5, 0.5]])
    with pytest.raises(ValueError, match="refusing to extrapolate"):
        M.predict_formation_energy(s, {"Mg": -1.0})  # no potential for O


def test_elemental_potential_fit_requires_data():
    with pytest.raises(ValueError):
        M.fit_elemental_potentials([])


def test_solver_recovers_known_solution():
    """The dependency-free linear solver must actually solve."""
    a = [[2.0, 1.0], [1.0, 3.0]]
    b = [5.0, 10.0]
    x = M._solve(a, b)
    assert x[0] == pytest.approx(1.0, abs=1e-9)
    assert x[1] == pytest.approx(3.0, abs=1e-9)


@pytest.mark.skipif(not M.backend_available(), reason="chgnet not installed")
def test_end_to_end_total_energy_is_typed_surrogate():
    from pymatgen.core import Lattice, Structure
    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(4.21), ["Mg", "O"],
                                  [[0, 0, 0], [0.5, 0.5, 0.5]])
    res = M.predict_total_energy(s)
    q = res.total_energy_per_atom
    assert q.provenance is Provenance.SURROGATE
    assert q.level is M.CHGNET_MPTRJ
    assert q.unit == "eV/atom"
    assert -20.0 < q.value < 5.0          # physically plausible band
    assert res.n_sites == len(s)
