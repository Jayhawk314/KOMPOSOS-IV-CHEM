"""Validated funnel scorer for application use (P5).

Loads the *validated* funnel configuration — the seed-corpus fingerprints (for
the novelty coordinate) and the frozen seed-derived SAscore threshold — so the
MOF Designer scores candidates with exactly the configuration the benchmark
validated (recall ~94% on held-out reals, AUROC ~0.88 vs generator-raw).

See docs/MOF_LINKER_BENCHMARK_RESULTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from mof_bridge.benchmark.funnel import evaluate, morgan_fp

_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "benchmark" / "mof_linkers"
_REPORT = _DIR / "benchmark_report.json"
_CORPUS = _DIR / "linker_corpus.json"
_SPLIT = _DIR / "seed_eval_split.json"

_DEFAULT_SA_THRESHOLD = 4.59  # fallback only; real value read from benchmark report

_CACHE: Optional[Dict] = None


def _load_config() -> Dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    sa_threshold = _DEFAULT_SA_THRESHOLD
    if _REPORT.exists():
        sa_threshold = json.loads(_REPORT.read_text()).get(
            "sa_threshold_from_seed_p95", _DEFAULT_SA_THRESHOLD
        )

    seed_fps: List = []
    if _CORPUS.exists() and _SPLIT.exists():
        corpus = {lk["canonical_smiles"]: lk for lk in json.loads(_CORPUS.read_text())["linkers"]}
        seed_smiles = json.loads(_SPLIT.read_text())["seed"]["smiles"]
        for s in seed_smiles:
            if s in corpus:
                fp = morgan_fp(s)
                if fp is not None:
                    seed_fps.append(fp)

    _CACHE = {"sa_threshold": sa_threshold, "seed_fps": seed_fps, "available": bool(seed_fps)}
    return _CACHE


def is_available() -> bool:
    return _load_config()["available"]


def score_linker(smiles: str) -> Dict:
    """Run the validated grounded funnel on one candidate SMILES."""
    cfg = _load_config()
    return evaluate(smiles, cfg["seed_fps"], cfg["sa_threshold"])


def get_scorer() -> Callable[[str], Dict]:
    cfg = _load_config()
    return lambda smiles: evaluate(smiles, cfg["seed_fps"], cfg["sa_threshold"])
