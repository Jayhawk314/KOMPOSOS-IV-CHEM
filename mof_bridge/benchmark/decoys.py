# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""P2 — Build the three decoy classes (negatives for AUROC).

Positives are real synthesized linkers; we have no labelled negatives, so we
construct three classes, reported separately:

  1. generator-raw   : the LinkerScreener's output BEFORE any gating. The fair
                       test of whether the funnel can filter its own guesses.
  2. perturbed-real  : real eval linkers with their coordinating groups ablated
                       (carboxylate -> methyl, pyridyl N -> CH). Hard negatives:
                       linker-shaped but coordinatively dead.
  3. random-valid    : random valid C/N/O molecules at matched atom count. Sanity
                       floor; a funnel that can't beat these is broken.

All decoys are canonicalized and any that collide with a real corpus linker are
dropped (a "decoy" that is actually real would poison the AUROC).

Run:
    python -m mof_bridge.benchmark.decoys
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from rdkit import Chem
from rdkit import RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

_ROOT = Path(__file__).resolve().parent.parent.parent
_CORPUS = _ROOT / "data" / "benchmark" / "mof_linkers" / "linker_corpus.json"
_SPLIT = _ROOT / "data" / "benchmark" / "mof_linkers" / "seed_eval_split.json"
_OUT = _ROOT / "data" / "benchmark" / "mof_linkers" / "decoys.json"

_SEED = 20260529
_CARBOXYL = Chem.MolFromSmarts("[CX3](=O)[OX1H0-,OX2H1]")
_METHYL = Chem.MolFromSmiles("C")


def _canon(smiles: str) -> Optional[tuple[str, int]]:
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    return Chem.MolToSmiles(m), m.GetNumHeavyAtoms()


def _real_smiles() -> set[str]:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    return {lk["canonical_smiles"] for lk in corpus["linkers"]}


def _eval_records() -> List[dict]:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    split = json.loads(_SPLIT.read_text(encoding="utf-8"))
    eval_set = set(split["eval"]["smiles"])
    return [lk for lk in corpus["linkers"] if lk["canonical_smiles"] in eval_set]


# ── Class 1: generator-raw ──────────────────────────────────────────────────
def _generator_raw(atom_counts: Dict[int, int]) -> List[dict]:
    from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec

    screener = LinkerScreener()
    out = []
    for atoms, n in atom_counts.items():
        screener.generator.min_atoms = atoms
        screener.generator.max_atoms = atoms
        spec = LinkerScreeningSpec(
            application_context="custom",
            num_candidates=max(n, 10),
            require_all_agree=False,
            allow_hollow=True,
        )
        try:
            res = screener.screen(spec)
        except Exception:
            continue
        for c in res.candidates:
            out.append(c.linker_smiles)
    return [{"smiles": s} for s in out]


# ── Class 2: perturbed-real (coordinating-group ablation) ───────────────────
def _ablate(smiles: str) -> Optional[str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    # carboxylate / carboxylic acid -> methyl
    if mol.HasSubstructMatch(_CARBOXYL):
        mol = Chem.ReplaceSubstructs(mol, _CARBOXYL, _METHYL, replaceAll=True)[0]
    # aromatic pyridyl N -> aromatic C (kill the donor lone pair)
    rw = Chem.RWMol(mol)
    changed = False
    for atom in rw.GetAtoms():
        if atom.GetSymbol() == "N" and atom.GetIsAromatic() and atom.GetTotalNumHs() == 0 \
           and atom.GetDegree() == 2:
            atom.SetAtomicNum(6)
            changed = True
    try:
        out = rw.GetMol()
        Chem.SanitizeMol(out)
    except Exception:
        return None
    if not changed and not mol.HasSubstructMatch(_CARBOXYL):
        return None  # nothing to ablate; not a useful hard negative
    return Chem.MolToSmiles(out)


def _perturbed_real(eval_records: List[dict]) -> List[dict]:
    out = []
    for lk in eval_records:
        abl = _ablate(lk["canonical_smiles"])
        if abl:
            out.append({"smiles": abl})
    return out


# ── Class 3: random-valid C/N/O molecules at matched atom count ─────────────
def _random_molecule(n_atoms: int, rng: random.Random, tries: int = 40) -> Optional[str]:
    elements = ["C", "C", "C", "N", "O"]  # carbon-rich, organic-ish
    for _ in range(tries):
        rw = Chem.RWMol()
        idxs = [rw.AddAtom(Chem.Atom(rng.choice(elements))) for _ in range(n_atoms)]
        # spanning tree for connectivity
        for i in range(1, n_atoms):
            j = rng.randrange(i)
            rw.AddBond(idxs[i], idxs[j], Chem.BondType.SINGLE)
        # a few extra random bonds (rings / unsaturation)
        for _ in range(rng.randint(1, max(1, n_atoms // 4))):
            a, b = rng.sample(idxs, 2)
            if rw.GetBondBetweenAtoms(a, b) is None:
                rw.AddBond(a, b, rng.choice([Chem.BondType.SINGLE, Chem.BondType.DOUBLE]))
        mol = rw.GetMol()
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            continue
        if mol.GetNumHeavyAtoms() == n_atoms:
            return Chem.MolToSmiles(mol)
    return None


def _random_valid(atom_counts: Dict[int, int], rng: random.Random) -> List[dict]:
    out = []
    for atoms, n in atom_counts.items():
        made = 0
        attempts = 0
        while made < n and attempts < n * 20:
            attempts += 1
            s = _random_molecule(atoms, rng)
            if s:
                out.append({"smiles": s})
                made += 1
    return out


def _finalize(raw: List[dict], real: set[str], seen: set[str]) -> List[dict]:
    """Canonicalize, drop reals and dups, attach heavy_atom_count."""
    out = []
    for rec in raw:
        c = _canon(rec["smiles"])
        if c is None:
            continue
        csmiles, heavy = c
        if csmiles in real or csmiles in seen:
            continue
        seen.add(csmiles)
        out.append({"canonical_smiles": csmiles, "heavy_atom_count": heavy})
    return out


def build_decoys() -> Dict:
    rng = random.Random(_SEED)
    real = _real_smiles()
    eval_records = _eval_records()

    # Match decoy atom-count histogram to the eval positives.
    hist: Dict[int, int] = {}
    for lk in eval_records:
        hist[lk["heavy_atom_count"]] = hist.get(lk["heavy_atom_count"], 0) + 1

    seen: set[str] = set()
    gen = _finalize(_generator_raw(hist), real, seen)
    perturbed = _finalize(_perturbed_real(eval_records), real, seen)
    rand = _finalize(_random_valid(hist, rng), real, seen)

    payload = {
        "schema": "mof_linker_decoys.v0",
        "matched_atom_histogram": {str(k): v for k, v in sorted(hist.items())},
        "classes": {
            "generator_raw": gen,
            "perturbed_real": perturbed,
            "random_valid": rand,
        },
        "counts": {
            "generator_raw": len(gen),
            "perturbed_real": len(perturbed),
            "random_valid": len(rand),
        },
    }
    _OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    p = build_decoys()
    print("Decoy counts:", p["counts"])
    print(f"Written: {_OUT}")
