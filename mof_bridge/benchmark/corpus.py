"""P0 — Build the unified, deduped real-linker corpus.

Positives come from two local sources of *synthesized* MOF linkers:
  - MOFSimplify (Kulik group): clean linker SMILES already in the linker cache.
  - CoRE-MOF 2019: fragments extracted from the precomputed `mofid-v1` strings
    (data/external/core_mof/extracted_linkers_from_metadata.json).

Each linker is canonicalized with RDKit, deduped by canonical SMILES, and tagged
with provenance and a MOF-level key (refcode for MOFSimplify, structure id for
CoRE-MOF) so the split in P1 can be done by MOF, not by linker.

Run:
    python -m mof_bridge.benchmark.corpus
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")  # silence parse warnings; we count failures ourselves

_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE_EXTRACTED = _ROOT / "data" / "external" / "core_mof" / "extracted_linkers_from_metadata.json"
_OUT_DIR = _ROOT / "data" / "benchmark" / "mof_linkers"
_OUT_PATH = _OUT_DIR / "linker_corpus.json"


@dataclass
class LinkerRecord:
    canonical_smiles: str
    heavy_atom_count: int
    tier: str = "extended"                                 # "gold" (MOFSimplify) | "extended" (CoRE)
    sources: List[str] = field(default_factory=list)      # e.g. ["mofsimplify", "core_mof"]
    source_ids: List[str] = field(default_factory=list)    # raw provenance ids
    mof_keys: List[str] = field(default_factory=list)      # MOF-level grouping keys


def _mofsimplify_key(source_id: str) -> str:
    """`mofsimplify:POHCOG_clean` -> `mofsimplify:POHCOG`."""
    tail = source_id.split(":", 1)[-1]
    return "mofsimplify:" + tail.split("_")[0]


def _core_key(mof_id: str) -> str:
    """`ja0c07257_si_005_ASR_pacman#frag1` -> `core:ja0c07257_si_005_ASR_pacman`."""
    return "core:" + mof_id.split("#frag", 1)[0]


def _canonical(smiles: str) -> Optional[tuple[str, int]]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol), mol.GetNumHeavyAtoms()


def _load_mofsimplify() -> List[tuple[str, str, str]]:
    """Return (smiles, source_id, mof_key) for MOFSimplify linkers."""
    from mof_bridge.mp_mof_loader import MOFLinkerCache

    cache = MOFLinkerCache()
    if not cache.is_available():
        return []
    out = []
    for lk in cache.load_linkers():
        sid = lk.mp_source_id or "mofsimplify:unknown"
        out.append((lk.smiles, sid, _mofsimplify_key(sid)))
    return out


def _load_core() -> List[tuple[str, str, str]]:
    """Return (smiles, source_id, mof_key) for CoRE-MOF extracted fragments."""
    if not _CORE_EXTRACTED.exists():
        return []
    data = json.loads(_CORE_EXTRACTED.read_text(encoding="utf-8"))
    out = []
    for rec in data:
        smi = rec.get("linker_smiles")
        mid = rec.get("mof_id", "core:unknown")
        if smi:
            out.append((smi, mid, _core_key(mid)))
    return out


def build_corpus(min_atoms: int = 6, max_atoms: int = 80) -> Dict:
    """Merge, canonicalize, dedup, and write the unified linker corpus."""
    raw = [("mofsimplify", *t) for t in _load_mofsimplify()]
    raw += [("core_mof", *t) for t in _load_core()]

    records: Dict[str, LinkerRecord] = {}
    invalid = out_of_range = radical_dropped = 0
    per_source_in = {"mofsimplify": 0, "core_mof": 0}
    dropped_log: List[dict] = []

    for source, smiles, source_id, mof_key in raw:
        per_source_in[source] += 1
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            invalid += 1
            if len(dropped_log) < 100:
                dropped_log.append({"smiles": smiles, "reason": "unparseable", "source": source})
            continue
        # Drop fragmentation artifacts: open-valence radical atoms (e.g. [C], [N])
        # produced by the heuristic CoRE mofid extraction. Not real molecules.
        if sum(a.GetNumRadicalElectrons() for a in mol.GetAtoms()) > 0:
            radical_dropped += 1
            if len(dropped_log) < 100:
                dropped_log.append({"smiles": smiles, "reason": "open_valence_radical", "source": source})
            continue
        csmiles, heavy = Chem.MolToSmiles(mol), mol.GetNumHeavyAtoms()
        if not (min_atoms <= heavy <= max_atoms):
            out_of_range += 1
            continue
        rec = records.get(csmiles)
        if rec is None:
            rec = LinkerRecord(canonical_smiles=csmiles, heavy_atom_count=heavy)
            records[csmiles] = rec
        if source not in rec.sources:
            rec.sources.append(source)
        if source_id not in rec.source_ids:
            rec.source_ids.append(source_id)
        if mof_key not in rec.mof_keys:
            rec.mof_keys.append(mof_key)
        # Gold = curated MOFSimplify; a linker confirmed by MOFSimplify is gold.
        if "mofsimplify" in rec.sources:
            rec.tier = "gold"

    corpus = sorted(records.values(), key=lambda r: (r.heavy_atom_count, r.canonical_smiles))
    by_count: Dict[int, int] = {}
    for r in corpus:
        by_count[r.heavy_atom_count] = by_count.get(r.heavy_atom_count, 0) + 1

    n_gold = sum(1 for r in corpus if r.tier == "gold")
    payload = {
        "schema": "mof_linker_corpus.v1_clean",
        "n_unique_linkers": len(corpus),
        "n_gold_tier": n_gold,
        "n_extended_tier": len(corpus) - n_gold,
        "n_raw_in": {k: v for k, v in per_source_in.items()},
        "n_invalid_smiles": invalid,
        "n_open_valence_radical_dropped": radical_dropped,
        "n_out_of_atom_range": out_of_range,
        "atom_range_filter": [min_atoms, max_atoms],
        "count_at_22": by_count.get(22, 0),
        "linkers": [asdict(r) for r in corpus],
    }

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    _OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (_OUT_DIR / "dropped_fragments.json").write_text(
        json.dumps({
            "n_invalid": invalid,
            "n_open_valence_radical": radical_dropped,
            "examples": dropped_log,
        }, indent=2),
        encoding="utf-8",
    )
    return payload


def _summary(payload: Dict) -> None:
    n = payload["n_unique_linkers"]
    print(f"Unique real linkers: {n} (gold {payload['n_gold_tier']} / extended {payload['n_extended_tier']})")
    print(f"  raw in       : {payload['n_raw_in']}")
    print(f"  invalid SMILES: {payload['n_invalid_smiles']}")
    print(f"  radical/open-valence dropped: {payload['n_open_valence_radical_dropped']}")
    print(f"  out of range : {payload['n_out_of_atom_range']}")
    print(f"  at 22 atoms  : {payload['count_at_22']}")
    both = sum(1 for r in payload["linkers"] if len(r["sources"]) > 1)
    print(f"  in BOTH sources (overlap): {both}")
    print(f"Written: {_OUT_PATH}")


if __name__ == "__main__":
    _summary(build_corpus())
