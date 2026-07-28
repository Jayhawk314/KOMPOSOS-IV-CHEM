# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Nonlinear sparse-discovery mean model for formation energy.

The forward model uses inverse-distance Kan extension (IDW) over known DFT
anchors. That is near-exact when a close neighbour exists, but ~96% of queries
fall in "sparse discovery" space (nearest anchor >= 0.5 away), where IDW
over-smooths and the error is large.

The Phase-16 calibration already swaps in a learned mean model for that sparse
regime, but it is LINEAR ridge. Formation energy is not linear in these
descriptors, so a RandomForest on the SAME leak-free Phase-16 calibration split
roughly halves the held-out error:

    Phase-16 MP validation (2498 held-out):  ridge 0.202 -> RF 0.133 eV/atom
    Transfer to the curated 179 audit set:    ridge 0.434 -> RF 0.300 eV/atom

RF was chosen over KernelRidge: KRR is marginally better in-distribution (0.108)
but worse and less stable on transfer; RF is strong on both and cannot
extrapolate outside the physical Ef range.

This module only affects the sparse-discovery POINT estimate. It is leak-free
(trained only on the Phase-16 calibration split, which excludes every KNOWN_EF
formula and mp-id), loads lazily, and falls back to the linear Phase-16 model if
the artifact is missing or the sklearn version is incompatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .parser import parse_formula
from .phase16_calibration import (
    composition_feature_vector,
    load_manifest,
    DEFAULT_MANIFEST_PATH,
)

CALIBRATION_DIR = Path(__file__).resolve().parent.parent / "data" / "calibration"
DEFAULT_RF_PATH = CALIBRATION_DIR / "phase16_sparse_rf.joblib"
DEFAULT_RF_REPORT = CALIBRATION_DIR / "phase16_sparse_rf_report.json"


@dataclass
class SparseMeanModel:
    """Wraps a fitted RandomForest over Phase-16 composition descriptors."""
    model: Any
    sklearn_version: str
    n_train: int
    val_mae: float
    val_rmse: float

    def predict(self, comp: Dict[str, float]) -> Optional[float]:
        try:
            x = composition_feature_vector(comp).reshape(1, -1)
            return float(self.model.predict(x)[0])
        except Exception:
            return None


def train_and_save(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    out_path: Path = DEFAULT_RF_PATH,
    report_path: Path = DEFAULT_RF_REPORT,
    n_estimators: int = 150,
    max_depth: int = 14,
    random_state: int = 0,
) -> Dict[str, Any]:
    """Fit the sparse-discovery RF on the Phase-16 calibration split, evaluate on
    the held-out validation split, and persist the model + a metrics report."""
    import sklearn
    import joblib
    from sklearn.ensemble import RandomForestRegressor

    entries = load_manifest(manifest_path)
    cal = [e for e in entries if e.split == "calibration"]
    val = [e for e in entries if e.split == "validation"]
    if len(cal) < 100:
        raise RuntimeError(f"too few calibration entries ({len(cal)})")

    Xtr = np.vstack([composition_feature_vector(parse_formula(e.formula)) for e in cal])
    ytr = np.array([e.target_ef for e in cal])
    Xva = np.vstack([composition_feature_vector(parse_formula(e.formula)) for e in val])
    yva = np.array([e.target_ef for e in val])

    rf = RandomForestRegressor(
        n_estimators=n_estimators, max_depth=max_depth,
        random_state=random_state, n_jobs=-1,
    )
    rf.fit(Xtr, ytr)

    pv = rf.predict(Xva)
    val_mae = float(np.mean(np.abs(pv - yva)))
    val_rmse = float(np.sqrt(np.mean((pv - yva) ** 2)))

    bundle = SparseMeanModel(
        model=rf, sklearn_version=sklearn.__version__,
        n_train=len(cal), val_mae=round(val_mae, 6), val_rmse=round(val_rmse, 6),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out_path, compress=3)
    load_sparse_mean_model.cache_clear()

    report = {
        "model": "RandomForestRegressor on Phase-16 composition descriptors",
        "sklearn_version": sklearn.__version__,
        "n_estimators": n_estimators,
        "random_state": random_state,
        "n_train_calibration": len(cal),
        "n_validation": len(val),
        "validation_mae_eV": round(val_mae, 6),
        "validation_rmse_eV": round(val_rmse, 6),
        "leak_free": (
            "trained only on the Phase-16 calibration split; the manifest excludes "
            "every KNOWN_EF formula and mp-id, and the validation split is held out."
        ),
        "artifact": str(out_path),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


@lru_cache(maxsize=2)
def load_sparse_mean_model(path: Optional[Path] = None) -> Optional[SparseMeanModel]:
    """Load the sparse-discovery RF, or None if absent/incompatible.

    Returns None silently on any failure so the predictor falls back to the
    linear Phase-16 mean model — never breaks prediction.
    """
    p = Path(path) if path is not None else DEFAULT_RF_PATH
    if not p.exists():
        return None
    try:
        import joblib
        bundle = joblib.load(p)
        if not isinstance(bundle, SparseMeanModel):
            return None
        return bundle
    except Exception:
        return None


if __name__ == "__main__":
    rep = train_and_save()
    print(json.dumps(rep, indent=2))
