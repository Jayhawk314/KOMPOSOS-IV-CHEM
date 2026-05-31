# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""External calibration for formation-energy uncertainty.

Phase 16 is deliberately separate from the predictor implementation so that
validation data cannot leak into the model by accident. The calibration runner
uses cached Materials Project entries as frozen external truth, evaluates a
predictor that is trained only on the curated KOMPOSOS baseline, fits interval
scales on one split, and reports metrics on the held-out split.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .parser import ELEMENT_ORDER, ELEMENT_TABLE, parse_formula


CALIBRATION_DIR = Path(__file__).resolve().parent.parent / "data" / "calibration"
DEFAULT_MANIFEST_PATH = CALIBRATION_DIR / "phase16_external_validation.json"
DEFAULT_MODEL_PATH = CALIBRATION_DIR / "phase16_calibration_model.json"
DEFAULT_REPORT_PATH = CALIBRATION_DIR / "phase16_calibration_report.json"

CHEMISTRY_CLASSES = (
    "oxide",
    "sulfide",
    "halide",
    "carbide",
    "nitride",
    "intermetallic",
    "mof",
    "other",
)

INTERVAL_LEVELS = (50, 80, 95)

ELEMENT_STAT_FEATURES = (
    "atomic_number",
    "atomic_mass",
    "electronegativity",
    "ionic_radius",
    "common_oxidation",
    "group",
    "period",
)


def _stable_int(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _all_elements_supported(comp: Dict[str, float]) -> bool:
    return bool(comp) and all(elem in ELEMENT_TABLE for elem in comp)


def _metal_elements(comp: Dict[str, float]) -> set[str]:
    non_metals = {"H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Se", "Br", "I"}
    return {elem for elem in comp if elem in ELEMENT_TABLE and elem not in non_metals}


def classify_chemistry(comp: Dict[str, float]) -> str:
    """Assign a composition to a calibration stratum.

    This is intentionally compositional and deterministic. The classes are used
    for uncertainty calibration, not for scientific taxonomy claims.
    """
    elements = set(comp)
    metals = _metal_elements(comp)
    halogens = {"F", "Cl", "Br", "I"} & elements

    if "C" in elements and "H" in elements and metals and ({"O", "N"} & elements):
        total_atoms = sum(comp.values())
        if total_atoms >= 10:
            return "mof"

    if "O" in elements:
        return "oxide"
    if "S" in elements:
        return "sulfide"
    if halogens:
        return "halide"
    if "C" in elements and metals and "H" not in elements:
        return "carbide"
    if "N" in elements and metals:
        return "nitride"
    if len(metals) >= 2 and not (elements & {"O", "S", "F", "Cl", "Br", "I", "N", "C"}):
        return "intermetallic"
    return "other"


def mean_model_feature_names() -> List[str]:
    """Feature names for the Phase 16 calibrated mean model."""
    names = [f"frac_{elem}" for elem in ELEMENT_ORDER]
    for attr in ELEMENT_STAT_FEATURES:
        names.extend([f"{attr}_mean", f"{attr}_std", f"{attr}_min", f"{attr}_max"])
    names.extend([f"class_{cls}" for cls in CHEMISTRY_CLASSES])
    names.extend(["atom_count", "n_elements", "max_fraction", "min_fraction"])
    return names


def composition_feature_vector(comp: Dict[str, float]) -> np.ndarray:
    """Build a deterministic descriptor vector for calibrated Ef regression."""
    total = float(sum(comp.values()))
    if total <= 0:
        total = 1.0

    features: List[float] = [float(comp.get(elem, 0.0)) / total for elem in ELEMENT_ORDER]

    supported = [(elem, float(amount)) for elem, amount in comp.items() if elem in ELEMENT_TABLE]
    weight_total = sum(amount for _, amount in supported)
    for attr in ELEMENT_STAT_FEATURES:
        if weight_total <= 0:
            features.extend([0.0, 0.0, 0.0, 0.0])
            continue
        values = np.array([float(getattr(ELEMENT_TABLE[elem], attr)) for elem, _ in supported], dtype=float)
        weights = np.array([amount / weight_total for _, amount in supported], dtype=float)
        mean = float(np.sum(values * weights))
        variance = float(np.sum(((values - mean) ** 2) * weights))
        features.extend([mean, math.sqrt(max(0.0, variance)), float(np.min(values)), float(np.max(values))])

    chemistry_class = classify_chemistry(comp)
    features.extend([1.0 if cls == chemistry_class else 0.0 for cls in CHEMISTRY_CLASSES])
    fractions = [float(amount) / total for amount in comp.values()] or [0.0]
    features.extend([total, float(len(comp)), max(fractions), min(fractions)])
    return np.array(features, dtype=float)


@dataclass
class ExternalValidationEntry:
    mp_id: str
    formula: str
    target_ef: float
    chemistry_class: str
    split: str
    source: str = "Materials Project cache"
    energy_above_hull: float = 0.0
    is_stable: bool = False
    crystal_system: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mp_id": self.mp_id,
            "formula": self.formula,
            "target_ef": self.target_ef,
            "chemistry_class": self.chemistry_class,
            "split": self.split,
            "source": self.source,
            "energy_above_hull": self.energy_above_hull,
            "is_stable": self.is_stable,
            "crystal_system": self.crystal_system,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExternalValidationEntry":
        return cls(
            mp_id=str(d["mp_id"]),
            formula=str(d["formula"]),
            target_ef=float(d["target_ef"]),
            chemistry_class=str(d["chemistry_class"]),
            split=str(d["split"]),
            source=str(d.get("source", "Materials Project cache")),
            energy_above_hull=float(d.get("energy_above_hull", 0.0)),
            is_stable=bool(d.get("is_stable", False)),
            crystal_system=str(d.get("crystal_system", "")),
        )


@dataclass
class CalibrationObservation:
    entry: ExternalValidationEntry
    predicted_ef: float
    raw_error_eV: float
    confidence: float
    uncertainty_tier: str

    @property
    def abs_error(self) -> float:
        return abs(self.predicted_ef - self.entry.target_ef)

    @property
    def squared_error(self) -> float:
        return self.abs_error * self.abs_error

    def to_dict(self) -> Dict[str, Any]:
        d = self.entry.to_dict()
        d.update({
            "predicted_ef": self.predicted_ef,
            "raw_error_eV": self.raw_error_eV,
            "confidence": self.confidence,
            "uncertainty_tier": self.uncertainty_tier,
            "abs_error": self.abs_error,
        })
        return d


@dataclass
class CalibrationScale:
    count: int
    scale_by_level: Dict[str, float]
    median_abs_error: float
    mae: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "scale_by_level": self.scale_by_level,
            "median_abs_error": self.median_abs_error,
            "mae": self.mae,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CalibrationScale":
        return cls(
            count=int(d.get("count", 0)),
            scale_by_level={str(k): float(v) for k, v in d.get("scale_by_level", {}).items()},
            median_abs_error=float(d.get("median_abs_error", 0.0)),
            mae=float(d.get("mae", 0.0)),
        )


@dataclass
class MeanEnergyModel:
    """Leak-free calibrated mean model for formation energy."""
    count: int
    regularization: float
    feature_names: List[str]
    feature_mean: List[float]
    feature_scale: List[float]
    coefficients: List[float]
    training_mae: float
    training_rmse: float

    def predict(self, comp: Dict[str, float]) -> Optional[float]:
        x = composition_feature_vector(comp)
        if len(x) != len(self.feature_names):
            return None
        mean = np.array(self.feature_mean, dtype=float)
        scale = np.array(self.feature_scale, dtype=float)
        coef = np.array(self.coefficients, dtype=float)
        if len(coef) != len(x) + 1:
            return None
        z = (x - mean) / scale
        return float(coef[0] + np.dot(z, coef[1:]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "regularization": self.regularization,
            "feature_names": self.feature_names,
            "feature_mean": self.feature_mean,
            "feature_scale": self.feature_scale,
            "coefficients": self.coefficients,
            "training_mae": self.training_mae,
            "training_rmse": self.training_rmse,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MeanEnergyModel":
        return cls(
            count=int(d.get("count", 0)),
            regularization=float(d.get("regularization", 1.0)),
            feature_names=[str(v) for v in d.get("feature_names", [])],
            feature_mean=[float(v) for v in d.get("feature_mean", [])],
            feature_scale=[float(v) for v in d.get("feature_scale", [])],
            coefficients=[float(v) for v in d.get("coefficients", [])],
            training_mae=float(d.get("training_mae", 0.0)),
            training_rmse=float(d.get("training_rmse", 0.0)),
        )


@dataclass
class Phase16CalibrationModel:
    version: str
    created_at: str
    target: str
    manifest_sha256: str
    global_scale: CalibrationScale
    class_scales: Dict[str, CalibrationScale] = field(default_factory=dict)
    min_class_count: int = 30
    interval_floor_eV: float = 0.02
    mean_model: Optional[MeanEnergyModel] = None

    def scale_for(self, chemistry_class: str, level: int) -> float:
        key = str(level)
        class_scale = self.class_scales.get(chemistry_class)
        if class_scale is not None and class_scale.count >= self.min_class_count:
            return class_scale.scale_by_level.get(key, self.global_scale.scale_by_level[key])
        return self.global_scale.scale_by_level[key]

    def intervals(self, raw_error_eV: float, chemistry_class: str) -> Dict[str, float]:
        base = max(float(raw_error_eV), self.interval_floor_eV)
        intervals = {}
        last = self.interval_floor_eV
        for level in INTERVAL_LEVELS:
            width = max(self.interval_floor_eV, base * self.scale_for(chemistry_class, level))
            width = max(width, last)
            intervals[str(level)] = round(width, 4)
            last = width
        return intervals

    def predict_mean(self, comp: Dict[str, float]) -> Optional[float]:
        if self.mean_model is None:
            return None
        return self.mean_model.predict(comp)

    def status_for(self, chemistry_class: str) -> str:
        class_scale = self.class_scales.get(chemistry_class)
        if class_scale is not None and class_scale.count >= self.min_class_count:
            return f"phase16_external_{chemistry_class}"
        return "phase16_external_global"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "target": self.target,
            "manifest_sha256": self.manifest_sha256,
            "min_class_count": self.min_class_count,
            "interval_floor_eV": self.interval_floor_eV,
            "global": self.global_scale.to_dict(),
            "classes": {k: v.to_dict() for k, v in sorted(self.class_scales.items())},
            "mean_model": self.mean_model.to_dict() if self.mean_model is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Phase16CalibrationModel":
        return cls(
            version=str(d.get("version", "phase16.v1")),
            created_at=str(d.get("created_at", "")),
            target=str(d.get("target", "formation_energy_per_atom")),
            manifest_sha256=str(d.get("manifest_sha256", "")),
            min_class_count=int(d.get("min_class_count", 30)),
            interval_floor_eV=float(d.get("interval_floor_eV", 0.02)),
            global_scale=CalibrationScale.from_dict(d["global"]),
            class_scales={
                str(k): CalibrationScale.from_dict(v)
                for k, v in d.get("classes", {}).items()
            },
            mean_model=(
                MeanEnergyModel.from_dict(d["mean_model"])
                if d.get("mean_model") is not None
                else None
            ),
        )


def manifest_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(entries: List[ExternalValidationEntry], path: Path = DEFAULT_MANIFEST_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "phase16.external.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "Materials Project cache",
        "target": "formation_energy_per_atom",
        "split_rule": "deterministic per-class alternating split after SHA-256 sort",
        "entries": [e.to_dict() for e in entries],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> List[ExternalValidationEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [ExternalValidationEntry.from_dict(d) for d in payload.get("entries", [])]


def build_external_manifest(
    max_entries: int = 5000,
    path: Path = DEFAULT_MANIFEST_PATH,
) -> List[ExternalValidationEntry]:
    """Build a deterministic frozen external validation set from MP cache."""
    from .formation_energy import KNOWN_EF
    from .mp_loader import MPCache

    known_mp_ids = {e.mp_id for e in KNOWN_EF if e.mp_id and e.mp_id != "computed"}
    known_formulas = {e.formula for e in KNOWN_EF}

    cache = MPCache()
    entries = cache.load_entries()

    by_class: Dict[str, List[Any]] = {cls: [] for cls in CHEMISTRY_CLASSES}
    seen_mp_ids: set[str] = set()

    for mp_entry in entries:
        if mp_entry.mp_id in seen_mp_ids:
            continue
        seen_mp_ids.add(mp_entry.mp_id)

        if mp_entry.mp_id in known_mp_ids or mp_entry.formula in known_formulas:
            continue
        if len(mp_entry.composition) <= 1:
            continue
        if not _all_elements_supported(mp_entry.composition):
            continue
        if not math.isfinite(mp_entry.formation_energy_per_atom):
            continue
        if abs(mp_entry.formation_energy_per_atom) < 1e-12:
            continue

        chemistry_class = classify_chemistry(mp_entry.composition)
        by_class.setdefault(chemistry_class, []).append(mp_entry)

    for cls in by_class:
        by_class[cls].sort(key=lambda e: _stable_hash(f"{e.mp_id}:{e.formula}"))

    selected_ids: set[str] = set()
    selected = []
    first_pass_target = max(1, max_entries // len(CHEMISTRY_CLASSES))
    for cls in CHEMISTRY_CLASSES:
        for entry in by_class.get(cls, [])[:first_pass_target]:
            selected.append(entry)
            selected_ids.add(entry.mp_id)

    remaining = [
        entry
        for cls in CHEMISTRY_CLASSES
        for entry in by_class.get(cls, [])[first_pass_target:]
        if entry.mp_id not in selected_ids
    ]
    remaining.sort(key=lambda e: _stable_hash(f"fill:{e.mp_id}:{e.formula}"))
    for entry in remaining:
        if len(selected) >= max_entries:
            break
        selected.append(entry)
        selected_ids.add(entry.mp_id)

    selected_by_class: Dict[str, List[Any]] = {cls: [] for cls in CHEMISTRY_CLASSES}
    for entry in selected:
        selected_by_class[classify_chemistry(entry.composition)].append(entry)

    frozen: List[ExternalValidationEntry] = []
    for cls in CHEMISTRY_CLASSES:
        class_entries = selected_by_class.get(cls, [])
        class_entries.sort(key=lambda e: _stable_hash(f"split:{e.mp_id}:{e.formula}"))
        for idx, entry in enumerate(class_entries):
            frozen.append(ExternalValidationEntry(
                mp_id=entry.mp_id,
                formula=entry.formula,
                target_ef=float(entry.formation_energy_per_atom),
                chemistry_class=cls,
                split="calibration" if idx % 2 == 0 else "validation",
                energy_above_hull=float(entry.energy_above_hull),
                is_stable=bool(entry.is_stable),
                crystal_system=str(entry.crystal_system),
            ))

    frozen.sort(key=lambda e: (e.chemistry_class, e.split, e.mp_id))
    write_manifest(frozen, path)
    return frozen


def _fit_scale(observations: List[CalibrationObservation]) -> CalibrationScale:
    if not observations:
        return CalibrationScale(
            count=0,
            scale_by_level={str(level): 1.0 for level in INTERVAL_LEVELS},
            median_abs_error=0.0,
            mae=0.0,
        )

    ratios = np.array([
        obs.abs_error / max(obs.raw_error_eV, 1e-9)
        for obs in observations
    ], dtype=float)
    abs_errors = np.array([obs.abs_error for obs in observations], dtype=float)

    scale_by_level: Dict[str, float] = {}
    previous = 0.05
    for level in INTERVAL_LEVELS:
        value = float(np.quantile(ratios, level / 100.0, method="higher"))
        value = max(previous, value)
        scale_by_level[str(level)] = round(value, 6)
        previous = value

    return CalibrationScale(
        count=len(observations),
        scale_by_level=scale_by_level,
        median_abs_error=round(float(np.median(abs_errors)), 6),
        mae=round(float(np.mean(abs_errors)), 6),
    )


def _summarize_error(observations: List[CalibrationObservation]) -> Dict[str, Any]:
    if not observations:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "median_abs_error": None,
            "p90_abs_error": None,
        }
    abs_errors = np.array([obs.abs_error for obs in observations], dtype=float)
    sq_errors = np.array([obs.squared_error for obs in observations], dtype=float)
    return {
        "n": len(observations),
        "mae": round(float(np.mean(abs_errors)), 6),
        "rmse": round(float(np.sqrt(np.mean(sq_errors))), 6),
        "median_abs_error": round(float(np.median(abs_errors)), 6),
        "p90_abs_error": round(float(np.quantile(abs_errors, 0.90)), 6),
    }


def fit_mean_energy_model(
    observations: List[CalibrationObservation],
    regularization: float = 1.0,
) -> Optional[MeanEnergyModel]:
    """Fit a ridge regression Ef mean model on the calibration split only."""
    calibration_obs = [obs for obs in observations if obs.entry.split == "calibration"]
    if len(calibration_obs) < 20:
        return None

    feature_names = mean_model_feature_names()
    x = np.vstack([
        composition_feature_vector(parse_formula(obs.entry.formula))
        for obs in calibration_obs
    ])
    y = np.array([obs.entry.target_ef for obs in calibration_obs], dtype=float)

    feature_mean = np.mean(x, axis=0)
    feature_scale = np.std(x, axis=0)
    feature_scale[feature_scale < 1e-8] = 1.0
    x_scaled = (x - feature_mean) / feature_scale
    design = np.column_stack([np.ones(len(x_scaled)), x_scaled])

    penalty = np.eye(design.shape[1], dtype=float)
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(
        design.T @ design + regularization * penalty,
        design.T @ y,
    )

    train_pred = design @ beta
    train_abs = np.abs(train_pred - y)
    train_sq = (train_pred - y) ** 2
    return MeanEnergyModel(
        count=len(calibration_obs),
        regularization=float(regularization),
        feature_names=feature_names,
        feature_mean=[round(float(v), 10) for v in feature_mean],
        feature_scale=[round(float(v), 10) for v in feature_scale],
        coefficients=[round(float(v), 10) for v in beta],
        training_mae=round(float(np.mean(train_abs)), 6),
        training_rmse=round(float(np.sqrt(np.mean(train_sq))), 6),
    )


def apply_mean_energy_model(
    observations: List[CalibrationObservation],
    mean_model: Optional[MeanEnergyModel],
) -> List[CalibrationObservation]:
    """Replace baseline Ef means with calibrated model means when available."""
    if mean_model is None:
        return observations
    corrected: List[CalibrationObservation] = []
    for obs in observations:
        pred = mean_model.predict(parse_formula(obs.entry.formula))
        corrected.append(CalibrationObservation(
            entry=obs.entry,
            predicted_ef=float(pred) if pred is not None else obs.predicted_ef,
            raw_error_eV=obs.raw_error_eV,
            confidence=obs.confidence,
            uncertainty_tier=obs.uncertainty_tier,
        ))
    return corrected


def _summarize(
    observations: List[CalibrationObservation],
    model: Phase16CalibrationModel,
) -> Dict[str, Any]:
    if not observations:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "coverage": {str(level): None for level in INTERVAL_LEVELS},
        }

    abs_errors = np.array([obs.abs_error for obs in observations], dtype=float)
    sq_errors = np.array([obs.squared_error for obs in observations], dtype=float)
    coverage = {}
    for level in INTERVAL_LEVELS:
        hits = 0
        for obs in observations:
            intervals = model.intervals(obs.raw_error_eV, obs.entry.chemistry_class)
            if obs.abs_error <= intervals[str(level)]:
                hits += 1
        coverage[str(level)] = round(hits / len(observations), 4)

    return {
        "n": len(observations),
        "mae": round(float(np.mean(abs_errors)), 6),
        "rmse": round(float(np.sqrt(np.mean(sq_errors))), 6),
        "median_abs_error": round(float(np.median(abs_errors)), 6),
        "p90_abs_error": round(float(np.quantile(abs_errors, 0.90)), 6),
        "coverage": coverage,
    }


def evaluate_manifest(entries: List[ExternalValidationEntry]) -> List[CalibrationObservation]:
    """Evaluate the leak-free predictor on a frozen external manifest."""
    from .formation_energy import FormationEnergyPredictor

    predictor = FormationEnergyPredictor(
        k=5,
        calibrate=True,
        use_mp_cache=False,
        external_calibration=False,
    )
    observations: List[CalibrationObservation] = []
    for entry in entries:
        result = predictor.predict(entry.formula)
        observations.append(CalibrationObservation(
            entry=entry,
            predicted_ef=float(result.ef_per_atom),
            raw_error_eV=float(result.error_estimate_eV),
            confidence=float(result.confidence),
            uncertainty_tier=str(result.uncertainty_tier.value),
        ))
    return observations


def fit_phase16_model(
    observations: List[CalibrationObservation],
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    mean_model: Optional[MeanEnergyModel] = None,
) -> Phase16CalibrationModel:
    calibration_obs = [obs for obs in observations if obs.entry.split == "calibration"]
    global_scale = _fit_scale(calibration_obs)
    class_scales = {}
    for cls in CHEMISTRY_CLASSES:
        class_obs = [obs for obs in calibration_obs if obs.entry.chemistry_class == cls]
        class_scales[cls] = _fit_scale(class_obs)

    return Phase16CalibrationModel(
        version="phase16.v1",
        created_at=datetime.now(timezone.utc).isoformat(),
        target="formation_energy_per_atom",
        manifest_sha256=manifest_sha256(manifest_path),
        global_scale=global_scale,
        class_scales=class_scales,
        mean_model=mean_model,
    )


def write_model(model: Phase16CalibrationModel, path: Path = DEFAULT_MODEL_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")
    load_calibration_model.cache_clear()
    return path


@lru_cache(maxsize=4)
def load_calibration_model(path: Optional[Path] = None) -> Optional[Phase16CalibrationModel]:
    model_path = Path(path) if path is not None else DEFAULT_MODEL_PATH
    if not model_path.exists():
        return None
    payload = json.loads(model_path.read_text(encoding="utf-8"))
    return Phase16CalibrationModel.from_dict(payload)


def run_phase16_calibration(
    max_entries: int = 5000,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    force_manifest: bool = False,
) -> Dict[str, Any]:
    """Build/evaluate/finalize Phase 16 external calibration."""
    if force_manifest or not manifest_path.exists():
        entries = build_external_manifest(max_entries=max_entries, path=manifest_path)
    else:
        entries = load_manifest(manifest_path)

    baseline_observations = evaluate_manifest(entries)
    mean_model = fit_mean_energy_model(baseline_observations)
    observations = apply_mean_energy_model(baseline_observations, mean_model)
    model = fit_phase16_model(observations, manifest_path=manifest_path, mean_model=mean_model)
    write_model(model, model_path)

    validation_obs = [obs for obs in observations if obs.entry.split == "validation"]
    calibration_obs = [obs for obs in observations if obs.entry.split == "calibration"]
    baseline_validation_obs = [obs for obs in baseline_observations if obs.entry.split == "validation"]
    baseline_calibration_obs = [obs for obs in baseline_observations if obs.entry.split == "calibration"]
    by_class = {}
    for cls in CHEMISTRY_CLASSES:
        cls_validation = [obs for obs in validation_obs if obs.entry.chemistry_class == cls]
        cls_calibration = [obs for obs in calibration_obs if obs.entry.chemistry_class == cls]
        cls_baseline_validation = [
            obs for obs in baseline_validation_obs if obs.entry.chemistry_class == cls
        ]
        cls_baseline_calibration = [
            obs for obs in baseline_calibration_obs if obs.entry.chemistry_class == cls
        ]
        by_class[cls] = {
            "baseline_calibration": _summarize_error(cls_baseline_calibration),
            "baseline_validation": _summarize_error(cls_baseline_validation),
            "calibration": _summarize(cls_calibration, model),
            "validation": _summarize(cls_validation, model),
            "scale_source": model.status_for(cls),
        }

    report = {
        "version": "phase16.report.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256(manifest_path),
        "model_path": str(model_path),
        "target": "formation_energy_per_atom",
        "predictor_training": (
            "KOMPOSOS KNOWN_EF baseline plus Phase16 ridge mean model trained "
            "only on the frozen calibration split; validation split is held out"
        ),
        "prediction_path_note": (
            "Runtime predictor applies the Phase16 mean model only in sparse "
            "discovery space so exact and dense local anchors remain dominant."
        ),
        "entries": {
            "total": len(entries),
            "calibration": len(calibration_obs),
            "validation": len(validation_obs),
        },
        "baseline": {
            "calibration": _summarize_error(baseline_calibration_obs),
            "validation": _summarize_error(baseline_validation_obs),
        },
        "global": {
            "calibration": _summarize(calibration_obs, model),
            "validation": _summarize(validation_obs, model),
        },
        "by_class": by_class,
        "model": model.to_dict(),
        "validation_observations": [obs.to_dict() for obs in validation_obs],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def format_report(report: Dict[str, Any]) -> str:
    """Human-readable Phase 16 summary for CLI output."""
    lines = []
    entries = report["entries"]
    global_validation = report["global"]["validation"]
    baseline_validation = report.get("baseline", {}).get("validation", {})
    lines.append("Phase 16 External Calibration")
    lines.append(f"Entries: {entries['total']} total ({entries['calibration']} calibration, {entries['validation']} validation)")
    if baseline_validation.get("mae") is not None:
        lines.append(
            "Baseline validation: "
            f"MAE={baseline_validation['mae']:.3f} eV/atom, "
            f"RMSE={baseline_validation['rmse']:.3f} eV/atom"
        )
    lines.append(
        "Calibrated validation: "
        f"MAE={global_validation['mae']:.3f} eV/atom, "
        f"RMSE={global_validation['rmse']:.3f} eV/atom, "
        f"coverage50={global_validation['coverage']['50']:.1%}, "
        f"coverage80={global_validation['coverage']['80']:.1%}, "
        f"coverage95={global_validation['coverage']['95']:.1%}"
    )
    lines.append("")
    lines.append("By class (held-out validation):")
    for cls in CHEMISTRY_CLASSES:
        summary = report["by_class"][cls]["validation"]
        if summary["n"] == 0:
            lines.append(f"  {cls:14s} n=0")
            continue
        cov = summary["coverage"]
        lines.append(
            f"  {cls:14s} n={summary['n']:4d} "
            f"MAE={summary['mae']:.3f} RMSE={summary['rmse']:.3f} "
            f"C50={cov['50']:.1%} C80={cov['80']:.1%} C95={cov['95']:.1%}"
        )
    return "\n".join(lines)
