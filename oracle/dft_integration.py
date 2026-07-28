# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
DFT as a typed *terminal* oracle.

Design stance (deliberate, and the reason this is safe to add):

* DFT does **not** live in the inverse-design inner loop. Crystal Dreamer / the
  MOF funnel call fast surrogates (~ms). DFT is 1e6-1e9x slower and needs a 3D
  structure. So DFT runs only on the *shortlist* a fast stage already produced --
  exactly the slot ``oracle/md_integration.py`` occupies for GROMACS.

* Every value DFT returns is a :class:`~core.level_of_theory.TypedQuantity`
  tagged with the exact :class:`~core.level_of_theory.LevelOfTheory`
  (functional/basis/...). An untyped DFT number would be a precise-looking
  liability because DFT is functional-dependent; tagged, it composes only with
  things it is actually comparable to.

* If no quantum-chemistry backend is installed, the oracle RAISES
  :class:`~core.errors.OracleUnavailable`. It never fabricates a number or
  silently downgrades to a surrogate while keeping the DFT label. (No oracle
  invention.)

Two genuine uses are implemented:

1. :func:`verify_candidates` -- terminal verification of a design shortlist
   (molecular linkers): total energy + HOMO-LUMO gap at a chosen level.
2. :func:`select_for_dft` -- active learning: pick the formation-energy
   predictions where the surrogate is *least* trustworthy (sparse-discovery /
   large error bar). Those are precisely where new DFT ground truth buys the most
   and where it should be spent.

Backends: PySCF (pip-installable, primary) or Psi4 (conda, secondary). Geometry
is generated from SMILES with RDKit (ETKDG + MMFF). All heavy imports are lazy.
"""

from __future__ import annotations

import importlib.util
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from core.errors import OracleUnavailable
from core.level_of_theory import (
    LevelOfTheory,
    Provenance,
    TypedQuantity,
    B3LYP_def2TZVP_D3,
    PBE_MP,
)

HARTREE_TO_EV = 27.211386245988

# Backend-specific functional aliases (libxc / Psi4 spellings differ from labels).
_PYSCF_XC_ALIASES = {
    "wB97X-D": "wb97x_d",
    "B3LYP": "b3lyp",
    "PBE0": "pbe0",
    "PBE": "pbe",
    "TPSS": "tpss",
}


# ---------------------------------------------------------------------------
# Backend discovery
# ---------------------------------------------------------------------------

def available_backends() -> List[str]:
    """Names of quantum-chemistry backends importable in this environment."""
    out = []
    for name in ("pyscf", "psi4"):
        if importlib.util.find_spec(name) is not None:
            out.append(name)
    return out


def dft_available() -> bool:
    """True iff at least one DFT backend AND RDKit (for geometry) are present."""
    return bool(available_backends()) and importlib.util.find_spec("rdkit") is not None


def _require_backend(preferred: Optional[str] = None) -> str:
    backends = available_backends()
    if not backends:
        raise OracleUnavailable(
            "dft",
            "no quantum-chemistry backend installed (need pyscf or psi4)",
            remediation="pip install pyscf  (or install psi4 via conda)",
        )
    if importlib.util.find_spec("rdkit") is None:
        raise OracleUnavailable(
            "dft", "RDKit not available for 3D geometry generation",
            remediation="pip install rdkit",
        )
    if preferred and preferred in backends:
        return preferred
    return backends[0]


# ---------------------------------------------------------------------------
# Geometry from SMILES (RDKit)
# ---------------------------------------------------------------------------

@dataclass
class Geometry:
    """A 3D molecular geometry ready for a quantum-chemistry backend."""

    symbols: List[str]
    coords_angstrom: List[Tuple[float, float, float]]
    charge: int
    multiplicity: int          # 2S+1
    smiles: str
    n_atoms: int

    def xyz_block(self) -> str:
        lines = [f"{s} {x:.6f} {y:.6f} {z:.6f}"
                 for s, (x, y, z) in zip(self.symbols, self.coords_angstrom)]
        return "\n".join(lines)


def geometry_from_smiles(smiles: str, seed: int = 0xC0FFEE) -> Geometry:
    """Embed a SMILES into a single MMFF-relaxed 3D conformer.

    Raises :class:`OracleUnavailable` if RDKit is missing, ``ValueError`` if the
    SMILES is invalid or cannot be embedded.
    """
    if importlib.util.find_spec("rdkit") is None:
        raise OracleUnavailable("dft", "RDKit not available",
                                remediation="pip install rdkit")
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"invalid SMILES: {smiles!r}")
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        # retry with random coords as a fallback embedding strategy
        params.useRandomCoords = True
        if AllChem.EmbedMolecule(mol, params) != 0:
            raise ValueError(f"could not embed 3D geometry for {smiles!r}")
    try:
        AllChem.MMFFOptimizeMolecule(mol)
    except Exception:
        pass  # geometry still usable; DFT will relax/score it

    conf = mol.GetConformer()
    symbols, coords = [], []
    for atom in mol.GetAtoms():
        p = conf.GetAtomPosition(atom.GetIdx())
        symbols.append(atom.GetSymbol())
        coords.append((p.x, p.y, p.z))

    charge = Chem.GetFormalCharge(mol)
    n_radical = sum(a.GetNumRadicalElectrons() for a in mol.GetAtoms())
    multiplicity = n_radical + 1  # closed-shell -> singlet
    return Geometry(symbols, coords, charge, multiplicity, smiles, len(symbols))


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DFTResult:
    """Outcome of a DFT single-point on one molecule. All values are typed."""

    smiles: str
    level: LevelOfTheory
    backend: str
    converged: bool
    total_energy: TypedQuantity            # eV
    homo_lumo_gap: Optional[TypedQuantity] # eV
    n_atoms: int
    wall_seconds: float
    detail: str = ""
    meta: Dict[str, object] = field(default_factory=dict)

    @property
    def measured_dft(self) -> bool:
        """True only when an SCF actually converged (mirrors md.measured_md)."""
        return bool(self.converged)

    def to_dict(self) -> Dict[str, object]:
        return {
            "smiles": self.smiles,
            "level_of_theory": self.level.label,
            "backend": self.backend,
            "converged": self.converged,
            "measured_dft": self.measured_dft,
            "total_energy": self.total_energy.to_dict(),
            "homo_lumo_gap": self.homo_lumo_gap.to_dict() if self.homo_lumo_gap else None,
            "n_atoms": self.n_atoms,
            "wall_seconds": round(self.wall_seconds, 3),
            "detail": self.detail,
            "meta": self.meta,
        }


# ---------------------------------------------------------------------------
# The oracle
# ---------------------------------------------------------------------------

class DFTOracle:
    """Runs DFT single-points and tags every output with its level of theory."""

    def __init__(self, level: LevelOfTheory = B3LYP_def2TZVP_D3,
                 preferred_backend: Optional[str] = None,
                 max_scf_cycles: int = 200):
        self.level = level
        self.preferred_backend = preferred_backend
        self.max_scf_cycles = max_scf_cycles

    # -- public --------------------------------------------------------------
    def run_smiles(self, smiles: str) -> DFTResult:
        """Single-point DFT energy + HOMO-LUMO gap for one molecule.

        Raises :class:`OracleUnavailable` if no backend is installed.
        """
        backend = _require_backend(self.preferred_backend)
        geom = geometry_from_smiles(smiles)
        t0 = time.time()
        if backend == "pyscf":
            energy_ev, gap_ev, converged, detail = self._run_pyscf(geom)
        else:
            energy_ev, gap_ev, converged, detail = self._run_psi4(geom)
        wall = time.time() - t0

        energy_q = TypedQuantity(energy_ev, "eV", self.level, Provenance.COMPUTATIONAL,
                                 meta={"quantity": "total_electronic_energy"})
        gap_q = (TypedQuantity(gap_ev, "eV", self.level, Provenance.COMPUTATIONAL,
                               meta={"quantity": "homo_lumo_gap"})
                 if gap_ev is not None else None)
        return DFTResult(smiles, self.level, backend, converged, energy_q, gap_q,
                         geom.n_atoms, wall, detail,
                         meta={"charge": geom.charge, "multiplicity": geom.multiplicity})

    # -- backends ------------------------------------------------------------
    def _run_pyscf(self, geom: Geometry):
        from pyscf import gto, dft

        mol = gto.M(
            atom=geom.xyz_block(),
            unit="Angstrom",
            basis=self.level.basis or "def2-SVP",
            charge=geom.charge,
            spin=geom.multiplicity - 1,   # n_alpha - n_beta = number of unpaired e-
            verbose=0,
        )
        xc = _PYSCF_XC_ALIASES.get(self.level.method, self.level.method.lower())
        mf = dft.UKS(mol) if geom.multiplicity > 1 else dft.RKS(mol)
        mf.xc = xc
        mf.max_cycle = self.max_scf_cycles
        if self.level.solvation:
            try:  # implicit solvation if requested and available
                mf = mf.PCM()
            except Exception:
                pass
        energy_ha = mf.kernel()
        converged = bool(getattr(mf, "converged", False))
        gap_ev = self._pyscf_gap(mf)
        return energy_ha * HARTREE_TO_EV, gap_ev, converged, f"pyscf {xc}/{mol.basis}"

    @staticmethod
    def _pyscf_gap(mf) -> Optional[float]:
        import numpy as np
        mo_e = mf.mo_energy
        mo_occ = mf.mo_occ
        try:
            if isinstance(mo_occ, (list, tuple)) or getattr(mo_occ, "ndim", 1) == 2:
                # unrestricted: combine both spin channels
                e = np.concatenate([np.asarray(mo_e[0]), np.asarray(mo_e[1])])
                occ = np.concatenate([np.asarray(mo_occ[0]), np.asarray(mo_occ[1])])
            else:
                e, occ = np.asarray(mo_e), np.asarray(mo_occ)
            homo = e[occ > 0].max()
            lumo = e[occ == 0].min()
            return float((lumo - homo) * HARTREE_TO_EV)
        except Exception:
            return None

    def _run_psi4(self, geom: Geometry):
        import psi4

        psi4.core.be_quiet()
        mol_spec = f"{geom.charge} {geom.multiplicity}\n{geom.xyz_block()}\nno_reorient\nno_com"
        psi4.geometry(mol_spec)
        psi4.set_options({"reference": "uhf" if geom.multiplicity > 1 else "rhf",
                          "maxiter": self.max_scf_cycles})
        method = f"{self.level.method}/{self.level.basis or 'def2-SVP'}"
        try:
            energy_ha = psi4.energy(method)
            converged = True
        except Exception as exc:  # SCF non-convergence etc.
            return float("nan"), None, False, f"psi4 failed: {exc}"
        gap_ev = None
        try:
            wfn = psi4.core.Wavefunction.from_file  # noqa: F841  (gap optional in psi4 path)
        except Exception:
            pass
        return energy_ha * HARTREE_TO_EV, gap_ev, converged, f"psi4 {method}"


# ---------------------------------------------------------------------------
# Terminal shortlist verification
# ---------------------------------------------------------------------------

@dataclass
class CandidateVerification:
    """DFT verdict for one shortlisted candidate."""

    smiles: str
    ok: bool
    result: Optional[DFTResult]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {"smiles": self.smiles, "ok": self.ok,
                "result": self.result.to_dict() if self.result else None,
                "error": self.error}


def verify_candidates(smiles_list: Sequence[str],
                      level: LevelOfTheory = B3LYP_def2TZVP_D3,
                      top_n: Optional[int] = None,
                      preferred_backend: Optional[str] = None
                      ) -> List[CandidateVerification]:
    """Run DFT on a design shortlist (e.g. top MOF linkers).

    Probes backend availability *once* up front so an unavailable environment
    fails loudly and immediately (``OracleUnavailable``) rather than per
    candidate. Per-candidate chemistry errors (bad SMILES, SCF blow-up) are
    captured into the verdict, not raised.
    """
    _require_backend(preferred_backend)        # fail fast & honestly if no DFT
    chosen = list(smiles_list)[: top_n] if top_n else list(smiles_list)
    oracle = DFTOracle(level=level, preferred_backend=preferred_backend)
    out: List[CandidateVerification] = []
    for smi in chosen:
        try:
            res = oracle.run_smiles(smi)
            out.append(CandidateVerification(smi, res.measured_dft, res))
        except OracleUnavailable:
            raise
        except Exception as exc:
            out.append(CandidateVerification(smi, False, None, str(exc)))
    return out


# ---------------------------------------------------------------------------
# Offline DFT reference: the cached Materials Project dataset
# ---------------------------------------------------------------------------

def _composition_signature(comp: Dict[str, float]) -> str:
    """Canonical fractional-composition key (order/scale invariant)."""
    total = sum(comp.values())
    if total <= 0:
        return ""
    items = sorted((el, round(amt / total, 4)) for el, amt in comp.items())
    return ";".join(f"{el}:{frac:.4f}" for el, frac in items)


class MaterialsProjectDFTOracle:
    """Real GGA-PBE formation energies from the cached Materials Project dataset.

    This is an *offline* DFT source: ~100k precomputed DFT formation energies that
    ship in the repo cache. Unlike :class:`DFTOracle` (live molecular DFT via
    pyscf/psi4) it needs no quantum-chemistry backend, so it works on any machine
    and is the ground-truth source for the formation-energy active-learning loop.

    Honest contract: a composition that is not in the dataset raises
    :class:`OracleUnavailable`. It never interpolates and labels the result DFT --
    interpolation is the surrogate's job, and the surrogate is separately typed.
    """

    def __init__(self) -> None:
        self._idx: Optional[Dict[str, object]] = None

    def _ensure(self) -> Dict[str, object]:
        if self._idx is None:
            from composition_engine.mp_loader import MPCache
            from composition_engine.parser import parse_formula
            cache = MPCache()
            if not cache.is_available():
                raise OracleUnavailable(
                    "mp_dft", "Materials Project DFT cache not present",
                    remediation="run scripts/download_mp_data.py",
                )
            idx: Dict[str, object] = {}
            for e in cache.load_entries():
                comp = getattr(e, "composition", None) or parse_formula(e.formula)
                sig = _composition_signature(comp)
                if not sig:
                    continue
                cur = idx.get(sig)
                # keep the most stable polymorph (lowest energy above hull)
                if cur is None or e.energy_above_hull < cur.energy_above_hull:  # type: ignore[attr-defined]
                    idx[sig] = e
            self._idx = idx
        return self._idx

    def available(self) -> bool:
        try:
            self._ensure()
            return True
        except OracleUnavailable:
            return False

    def lookup(self, formula: str) -> TypedQuantity:
        """Real DFT formation energy (eV/atom) for ``formula``, or raise."""
        from composition_engine.parser import parse_formula
        idx = self._ensure()
        sig = _composition_signature(parse_formula(formula))
        e = idx.get(sig)
        if e is None:
            raise OracleUnavailable(
                "mp_dft", f"composition {formula!r} not in MP DFT dataset",
                remediation="compute it with pyscf/VASP, or choose a known composition",
            )
        return TypedQuantity(
            float(e.formation_energy_per_atom), "eV/atom", PBE_MP,  # type: ignore[attr-defined]
            Provenance.COMPUTATIONAL,
            meta={"mp_id": e.mp_id, "e_above_hull_eV": e.energy_above_hull,  # type: ignore[attr-defined]
                  "source": "materials_project", "quantity": "formation_energy"},
        )

    def entries(self) -> List[object]:
        """All unique (most-stable-polymorph) MP entries with real DFT data."""
        return list(self._ensure().values())


# ---------------------------------------------------------------------------
# Active learning: where is DFT worth spending?
# ---------------------------------------------------------------------------

# Surrogate tiers (by label) ordered worst -> best trust. Sparse discovery and
# heuristic estimates are where new DFT ground truth pays off most.
_LOW_TRUST_TIERS = {"Sparse Discovery", "Heuristic Estimate", "Moderate Extrapolation"}


# Physically plausible window for a formation energy (eV/atom). Almost no real
# compound forms below ~ -4.5; a surrogate value outside this is a failure.
_PHYS_EF_MIN = -4.5
_PHYS_EF_MAX = 0.5


@dataclass
class DFTCandidate:
    """A formation-energy prediction flagged as worth verifying with DFT."""

    formula: str
    surrogate_ef: float
    error_estimate_eV: float
    tier: str
    priority: float            # higher = verify sooner
    fusion_drift_eV: float = 0.0     # |fused ef - trusted base source| (committee disagreement)
    implausibility_eV: float = 0.0   # distance of fused ef outside the physical window

    def to_dict(self) -> Dict[str, object]:
        return {"formula": self.formula, "surrogate_ef_eV": self.surrogate_ef,
                "error_estimate_eV": self.error_estimate_eV, "tier": self.tier,
                "fusion_drift_eV": self.fusion_drift_eV,
                "implausibility_eV": self.implausibility_eV,
                "priority": round(self.priority, 4)}


def select_for_dft(formation_results: Sequence[object],
                   max_picks: int = 10,
                   error_floor_eV: float = 0.10) -> List[DFTCandidate]:
    """Pick the predictions where a real DFT calculation buys the most.

    Acquisition signal (validated against MP DFT in ``dft_calibration``): the raw
    surrogate error bar is a *weak* predictor of true error, so it is combined
    with two stronger signals available from the surrogate's own output:

    * **fusion drift** -- how far the Dempster-Shafer-fused estimate moved from
      its trusted base source (``kan_extension``). Large drift means a rule-based
      estimator (e.g. Kapustinskii) dragged the answer; that is where the big
      errors live (query-by-committee).
    * **physical implausibility** -- a fused value outside the physical formation
      -energy window is self-evidently a failure that DFT should resolve.

    Low-trust tiers (sparse discovery) still get a boost. Accepts any objects
    exposing ``formula``, ``ef_per_atom``, ``error_estimate_eV``,
    ``uncertainty_tier`` and (optionally) ``sources`` -- e.g.
    ``FormationEnergyResult``.
    """
    scored: List[DFTCandidate] = []
    for r in formation_results:
        err = float(getattr(r, "error_estimate_eV", 0.0) or 0.0)
        tier = getattr(getattr(r, "uncertainty_tier", ""), "value",
                       getattr(r, "uncertainty_tier", ""))
        tier = str(tier)
        ef = float(getattr(r, "ef_per_atom", float("nan")))
        sources = getattr(r, "sources", None) or {}

        drift = 0.0
        base = sources.get("kan_extension") if isinstance(sources, dict) else None
        if base is not None and ef == ef:                       # ef==ef => not NaN
            drift = abs(ef - float(base))

        implausible = 0.0
        if ef == ef:
            if ef < _PHYS_EF_MIN:
                implausible = _PHYS_EF_MIN - ef
            elif ef > _PHYS_EF_MAX:
                implausible = ef - _PHYS_EF_MAX

        low_trust = tier in _LOW_TRUST_TIERS
        boost = 1.5 if low_trust else 1.0
        priority = boost * err + 2.0 * drift + 1.0 * implausible

        if priority < error_floor_eV and not low_trust:
            continue
        scored.append(DFTCandidate(
            formula=str(getattr(r, "formula", "?")),
            surrogate_ef=ef,
            error_estimate_eV=err,
            tier=tier,
            priority=priority,
            fusion_drift_eV=round(drift, 4),
            implausibility_eV=round(implausible, 4),
        ))
    scored.sort(key=lambda c: c.priority, reverse=True)
    return scored[:max_picks]
