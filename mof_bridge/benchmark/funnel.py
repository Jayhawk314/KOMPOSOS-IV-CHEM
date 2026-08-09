# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""P3 — The grounded funnel. Each gate is a checkable signal, not a self-score.

G1  chemical sanity   : RDKit sanitize (hard); PAINS/Brenk flag        (soft)
G2  coordination      : >=2 recognized coordinating groups             (hard)
G3  synthesizability  : SAscore (Ertl) <= threshold (from seed only)   (threshold)
G4  geometry          : 3D-embed, donors spatially separated (ditopic) (survivors)
G5  precedent         : max Tanimoto to seed corpus -> novelty axis     (coordinate)

`evaluate` returns a graded funnel score in [0, 1] for ranking (AUROC) plus the
per-gate detail used for the recall funnel chart and novelty frontier.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional

from rdkit import Chem
from rdkit import RDLogger
from rdkit.Chem import AllChem, DataStructs
from rdkit.Chem import FilterCatalog
from rdkit.Chem import RDConfig

RDLogger.DisableLog("rdApp.*")

sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer  # noqa: E402

# Coordinating motifs a MOF linker uses to bind metal nodes. Broadened to cover
# protonated/deprotonated carboxylate, azine + azole N-donors, and phenolate,
# since real linkers present these in many forms.
_COORD_SMARTS = {
    "carboxyl":    "[CX3](=O)[O;H1,H0-]",      # -COOH and -COO(-)
    "azine_N":     "[n;X2;r6]",                # pyridyl / bipyridyl / triazine
    "azole_N":     "[n;r5]",                   # imidazolate, pyrazolate, triazolate
    "tetrazole":   "c1nnnn1",
    "phosphonate": "P(=O)([O;H1,H0-])[O;H1,H0-]",
    "sulfonate":   "S(=O)(=O)[O;H1,H0-]",
    "catecholate": "c1cc(O)c(O)cc1",
    "hydroxamate": "[CX3](=O)[NX3][OX2H1,OX1-]",
    "phenolate":   "[OX2H1,OX1-]c",            # phenol / phenolate O-donor
    "nitrile_N":   "[NX1]#[CX2]",
    "amine_N":     "[NX3;H0,H1,H2;!$(N[CX3]=[OX1]);!$(Na)]",  # aliphatic amine / azamacrocycle
    "amide_anion": "[N-]",                                      # deprotonated N donor
}
_COORD_PATTERNS = {k: Chem.MolFromSmarts(v) for k, v in _COORD_SMARTS.items()}

_FILTER_CATALOG = None


def _filter_catalog() -> FilterCatalog.FilterCatalog:
    global _FILTER_CATALOG
    if _FILTER_CATALOG is None:
        params = FilterCatalog.FilterCatalogParams()
        params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
        params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
        _FILTER_CATALOG = FilterCatalog.FilterCatalog(params)
    return _FILTER_CATALOG


def morgan_fp(smiles: str):
    m = Chem.MolFromSmiles(smiles)
    return AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) if m else None


def _count_coordination(mol) -> int:
    """Number of distinct coordinating sites (matched motif atom groups)."""
    sites = set()
    for patt in _COORD_PATTERNS.values():
        if patt is None:
            continue
        for match in mol.GetSubstructMatches(patt):
            sites.add(min(match))  # one site per matched group
    return len(sites)


def _coord_atom_indices(mol) -> List[int]:
    idxs = set()
    for patt in _COORD_PATTERNS.values():
        if patt is None:
            continue
        for match in mol.GetSubstructMatches(patt):
            idxs.update(match)
    return sorted(idxs)


def _geometry_ok(mol) -> Optional[bool]:
    """Embed one conformer; check coordinating atoms are spatially separated.

    Returns True/False, or None if embedding could not be assessed (we do not
    penalize a real linker for a flaky embed).
    """
    coord_idx = _coord_atom_indices(mol)
    if len(coord_idx) < 2:
        return False
    mh = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mh, randomSeed=42, maxAttempts=50) != 0:
        return None
    try:
        AllChem.MMFFOptimizeMolecule(mh, maxIters=100)
    except Exception:
        pass
    conf = mh.GetConformer()
    max_d = 0.0
    for i in range(len(coord_idx)):
        for j in range(i + 1, len(coord_idx)):
            d = conf.GetAtomPosition(coord_idx[i]).Distance(conf.GetAtomPosition(coord_idx[j]))
            max_d = max(max_d, d)
    return max_d >= 2.5  # donors meaningfully separated -> ditopic-capable


def evaluate(smiles: str, seed_fps: List, sa_threshold: float) -> Dict:
    """Run the funnel on one molecule. Higher score = more linker-like."""
    result = {
        "smiles": smiles, "died_at": None, "gate_level": 0,
        "passed_all": False, "n_coord": 0, "sascore": None,
        "geometry_ok": None, "max_tanimoto": None, "score": 0.0,
        "pains_brenk_flag": False,
    }
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        result["died_at"] = "G1_parse"
        return result

    # G1 — chemical sanity = valid molecule. PAINS/Brenk is recorded as a SOFT
    # flag, not a reject: real MOF linkers (azo, quinone, catechol, polyphenyl)
    # legitimately trip drug-discovery filters.
    result["pains_brenk_flag"] = bool(_filter_catalog().HasMatch(mol))
    result["gate_level"] = 1

    # G2 — coordination topology
    n_coord = _count_coordination(mol)
    result["n_coord"] = n_coord
    if n_coord < 2:
        result["died_at"] = "G2_coordination"
        result["score"] = 0.2
        return result
    result["gate_level"] = 2

    # G3 — synthesizability (SAscore; lower = easier)
    sa = sascorer.calculateScore(mol)
    result["sascore"] = round(sa, 3)
    if sa > sa_threshold:
        result["died_at"] = "G3_sascore"
        result["score"] = 0.4
        return result
    result["gate_level"] = 3

    # G4 — geometry (survivors only; None = unassessed, not a failure)
    geom = _geometry_ok(mol)
    result["geometry_ok"] = geom
    if geom is False:
        result["died_at"] = "G4_geometry"
        result["score"] = 0.55
        return result
    result["gate_level"] = 4
    result["passed_all"] = True

    # G5 — precedent / novelty coordinate
    fp = morgan_fp(smiles)
    if fp is not None and seed_fps:
        result["max_tanimoto"] = round(max(DataStructs.TanimotoSimilarity(fp, s) for s in seed_fps), 3)

    sa_quality = max(0.0, min(1.0, (8.0 - sa) / 7.0))
    result["score"] = round(0.7 + 0.3 * sa_quality, 4)
    return result
