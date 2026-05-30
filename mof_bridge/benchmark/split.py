"""P1 — Freeze the seed/eval split (by MOF, not by linker) and hash it.

A linker can appear in several MOFs and a MOF has several linkers, so a naive
per-linker split would leak. We build the bipartite graph (linker <-> mof_key),
take connected components, and assign whole components to seed or eval. This
guarantees no linker and no MOF straddles the split.

Assignment is deterministic (hash of the component's smallest mof_key), so the
split is reproducible. The eval half is hashed (SHA-256) and frozen before any
funnel runs, per the integrity rule in the spec.

Run:
    python -m mof_bridge.benchmark.split
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

_ROOT = Path(__file__).resolve().parent.parent.parent
_CORPUS = _ROOT / "data" / "benchmark" / "mof_linkers" / "linker_corpus.json"
_OUT_DIR = _ROOT / "data" / "benchmark" / "mof_linkers"
_SPLIT_PATH = _OUT_DIR / "seed_eval_split.json"
_SHA_PATH = _OUT_DIR / "seed_eval_split.sha256"

EVAL_FRACTION_PCT = 50  # target % of components assigned to eval


class _UnionFind:
    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _assign_eval(component_id: str) -> bool:
    h = int(hashlib.sha256(component_id.encode("utf-8")).hexdigest(), 16)
    return (h % 100) < EVAL_FRACTION_PCT


def build_split() -> Dict:
    corpus = json.loads(_CORPUS.read_text(encoding="utf-8"))
    linkers = corpus["linkers"]

    uf = _UnionFind()
    for lk in linkers:
        node = "L:" + lk["canonical_smiles"]
        for key in lk["mof_keys"]:
            uf.union(node, "M:" + key)

    # Component id = smallest member label (stable, deterministic).
    comp_members: Dict[str, List[str]] = {}
    for lk in linkers:
        node = "L:" + lk["canonical_smiles"]
        root = uf.find(node)
        comp_members.setdefault(root, []).append(node)

    comp_id_by_root = {
        root: min(members) for root, members in comp_members.items()
    }

    seed, eval_ = [], []
    for lk in linkers:
        node = "L:" + lk["canonical_smiles"]
        cid = comp_id_by_root[uf.find(node)]
        (eval_ if _assign_eval(cid) else seed).append(lk["canonical_smiles"])

    def _at22(smiles_list):
        s = set(smiles_list)
        return sum(1 for lk in linkers if lk["canonical_smiles"] in s and lk["heavy_atom_count"] == 22)

    payload = {
        "schema": "mof_linker_split.v0",
        "eval_fraction_pct": EVAL_FRACTION_PCT,
        "n_components": len(comp_members),
        "seed": {"n": len(seed), "n_at_22": _at22(seed), "smiles": sorted(seed)},
        "eval": {"n": len(eval_), "n_at_22": _at22(eval_), "smiles": sorted(eval_)},
    }

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    _SPLIT_PATH.write_text(serialized, encoding="utf-8")
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    _SHA_PATH.write_text(digest + "\n", encoding="utf-8")
    payload["_sha256"] = digest
    return payload


if __name__ == "__main__":
    p = build_split()
    print(f"Components: {p['n_components']}")
    print(f"Seed: {p['seed']['n']} linkers ({p['seed']['n_at_22']} at 22 atoms)")
    print(f"Eval: {p['eval']['n']} linkers ({p['eval']['n_at_22']} at 22 atoms)")
    print(f"Frozen SHA-256: {p['_sha256']}")
    print(f"Written: {_SPLIT_PATH}")
