# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for the level-of-theory engine and the typed DFT terminal oracle."""

from dataclasses import dataclass

import pytest

from core.errors import OracleUnavailable, ProvenancePromotionError, TheoryCompositionError
from core.level_of_theory import (
    Conversion,
    LevelOfTheory,
    Provenance,
    TypedQuantity,
    PBE_MP,
    SURROGATE_KAN,
    B3LYP_def2TZVP_D3,
    WB97XD_def2TZVP,
    from_formation_energy_result,
)
from oracle import dft_integration as dft


# ----------------------------------------------------------------------------
# Level-of-theory discipline
# ----------------------------------------------------------------------------

def _q(val, level, prov=Provenance.COMPUTATIONAL, unc=0.0):
    return TypedQuantity(val, "eV/atom", level, prov, unc)


def test_same_level_combines():
    a = _q(-1.6, PBE_MP)
    b = _q(-0.1, PBE_MP)
    assert (a + b).value == pytest.approx(-1.7)
    assert (a - b).value == pytest.approx(-1.5)


def test_cross_level_combination_is_refused():
    surrogate = _q(-1.61, SURROGATE_KAN, Provenance.SURROGATE)
    dft_val = _q(-1.58, PBE_MP)
    with pytest.raises(TheoryCompositionError):
        _ = surrogate - dft_val
    with pytest.raises(TheoryCompositionError):
        _ = surrogate + dft_val


def test_different_dft_functionals_are_not_interchangeable():
    a = _q(-1.0, B3LYP_def2TZVP_D3)
    b = _q(-1.0, WB97XD_def2TZVP)
    assert not a.level.is_compatible_with(b.level)
    with pytest.raises(TheoryCompositionError):
        _ = a + b


def test_unit_mismatch_is_refused():
    a = TypedQuantity(1.0, "eV", PBE_MP, Provenance.COMPUTATIONAL)
    b = TypedQuantity(1.0, "eV/atom", PBE_MP, Provenance.COMPUTATIONAL)
    with pytest.raises(TheoryCompositionError):
        _ = a + b


def test_explicit_lift_crosses_levels_and_amplifies_uncertainty():
    surrogate = _q(-1.61, SURROGATE_KAN, Provenance.SURROGATE, unc=0.30)
    conv = Conversion(SURROGATE_KAN, PBE_MP,
                      rationale="surrogate trained on MP PBE; transfer as-is",
                      added_uncertainty=0.05)
    lifted = surrogate.lifted_to(PBE_MP, conv)
    assert lifted.level == PBE_MP
    assert lifted.uncertainty == pytest.approx(0.35)
    # now it combines with a PBE value
    assert (lifted - _q(-1.58, PBE_MP)).value == pytest.approx(-0.03, abs=1e-9)


def test_wrong_conversion_endpoints_rejected():
    surrogate = _q(-1.61, SURROGATE_KAN, Provenance.SURROGATE)
    bad = Conversion(B3LYP_def2TZVP_D3, PBE_MP, rationale="unrelated")
    with pytest.raises(TheoryCompositionError):
        surrogate.lifted_to(PBE_MP, bad)


def test_predicted_is_never_asserted_as_measured():
    comp = _q(-1.6, PBE_MP, Provenance.COMPUTATIONAL)
    with pytest.raises(ProvenancePromotionError):
        comp.asserted_as_measured()
    surrogate = _q(-1.6, SURROGATE_KAN, Provenance.SURROGATE)
    with pytest.raises(ProvenancePromotionError):
        surrogate.asserted_as_measured()


def test_levels_are_hashable_and_labelled():
    s = {PBE_MP, B3LYP_def2TZVP_D3, WB97XD_def2TZVP}
    assert len(s) == 3
    assert "def2-TZVP" in B3LYP_def2TZVP_D3.label
    assert "D3BJ" in B3LYP_def2TZVP_D3.label


# ----------------------------------------------------------------------------
# Adapter from the existing surrogate
# ----------------------------------------------------------------------------

@dataclass
class _FakeFER:
    formula: str
    ef_per_atom: float
    error_estimate_eV: float
    uncertainty_tier: str
    calibration_status: str = "isotonic"
    chemistry_class: str = "oxide"


def test_formation_energy_result_is_tagged_as_surrogate():
    fer = _FakeFER("LiNi0.8Mn0.1Co0.1O2", -1.61, 0.30, "Sparse Discovery")
    tq = from_formation_energy_result(fer)
    assert tq.level == SURROGATE_KAN
    assert tq.provenance == Provenance.SURROGATE
    assert tq.value == pytest.approx(-1.61)
    assert tq.uncertainty == pytest.approx(0.30)
    # and therefore cannot be silently mixed with a DFT number
    with pytest.raises(TheoryCompositionError):
        _ = tq - _q(-1.58, PBE_MP, Provenance.COMPUTATIONAL)


# ----------------------------------------------------------------------------
# DFT oracle: honest availability + geometry + active learning
# ----------------------------------------------------------------------------

def test_backend_discovery_consistent():
    backends = dft.available_backends()
    assert isinstance(backends, list)
    # dft_available implies both a backend and rdkit
    if dft.dft_available():
        assert backends


def test_geometry_from_smiles_benzene():
    rdkit_present = __import__("importlib").util.find_spec("rdkit") is not None
    if not rdkit_present:
        pytest.skip("rdkit not installed")
    geom = dft.geometry_from_smiles("c1ccccc1")
    assert geom.n_atoms == 12          # 6 C + 6 H
    assert geom.symbols.count("C") == 6
    assert geom.symbols.count("H") == 6
    assert geom.charge == 0
    assert geom.multiplicity == 1
    assert len(geom.coords_angstrom) == 12


def test_invalid_smiles_raises_valueerror():
    rdkit_present = __import__("importlib").util.find_spec("rdkit") is not None
    if not rdkit_present:
        pytest.skip("rdkit not installed")
    with pytest.raises(ValueError):
        dft.geometry_from_smiles("this-is-not-smiles$$")


def test_dft_run_without_backend_raises_oracle_unavailable():
    if dft.available_backends():
        pytest.skip("a DFT backend is installed; unavailable-path not exercised")
    oracle = dft.DFTOracle()
    with pytest.raises(OracleUnavailable) as ei:
        oracle.run_smiles("c1ccccc1")
    assert ei.value.oracle == "dft"
    # verify_candidates must also fail fast, not silently return fakes
    with pytest.raises(OracleUnavailable):
        dft.verify_candidates(["c1ccccc1", "CCO"])


@pytest.mark.skipif(not dft.dft_available(),
                    reason="no DFT backend installed (pyscf/psi4)")
def test_dft_runs_benzene_when_backend_present():
    from core.level_of_theory import PBE0_def2SVP
    oracle = dft.DFTOracle(level=PBE0_def2SVP)
    res = oracle.run_smiles("c1ccccc1")
    assert res.measured_dft
    assert res.total_energy.unit == "eV"
    assert res.total_energy.level == PBE0_def2SVP
    assert res.total_energy.value < 0          # bound molecule
    if res.homo_lumo_gap is not None:
        assert res.homo_lumo_gap.value > 0


def test_select_for_dft_prioritises_low_trust_high_error():
    rows = [
        _FakeFER("KnownLCO", -1.86, 0.02, "Categorical Ground Truth"),
        _FakeFER("CloseNMC", -1.68, 0.08, "Dense Interpolation"),
        _FakeFER("NovelA", -0.90, 0.45, "Sparse Discovery"),
        _FakeFER("NovelB", -1.10, 0.25, "Moderate Extrapolation"),
    ]
    picks = dft.select_for_dft(rows, max_picks=10, error_floor_eV=0.10)
    names = [p.formula for p in picks]
    # the confident known material is not worth a DFT spend
    assert "KnownLCO" not in names
    # the novel sparse-discovery candidate is top priority
    assert names[0] == "NovelA"
    # priority is sorted descending
    prio = [p.priority for p in picks]
    assert prio == sorted(prio, reverse=True)
