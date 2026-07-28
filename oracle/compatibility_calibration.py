# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Calibration metrics and simple score calibration for compatibility outputs."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def score_bins(results: List[Dict[str, Any]], num_bins: int = 10) -> List[Dict[str, Any]]:
    """Reliability table for predicted compatibility scores."""

    bins = []
    width = 1.0 / num_bins
    for i in range(num_bins):
        lo = i * width
        hi = (i + 1) * width
        subset = []
        for result in results:
            if result.get("score") is None:
                continue
            score = float(result["score"])
            in_bin = lo <= score <= hi if i == num_bins - 1 else lo <= score < hi
            if in_bin:
                subset.append(result)
        if not subset:
            bins.append({
                "bin": f"{lo:.1f}-{hi:.1f}",
                "lower": round(lo, 4),
                "upper": round(hi, 4),
                "n": 0,
                "mean_score": None,
                "observed_positive_rate": None,
                "accuracy": None,
                "calibration_error": None,
            })
            continue

        mean_score = sum(float(r["score"]) for r in subset) / len(subset)
        observed = sum(1 for r in subset if r["expected_compatible"]) / len(subset)
        accuracy = sum(1 for r in subset if r.get("correct")) / len(subset)
        bins.append({
            "bin": f"{lo:.1f}-{hi:.1f}",
            "lower": round(lo, 4),
            "upper": round(hi, 4),
            "n": len(subset),
            "mean_score": round(mean_score, 4),
            "observed_positive_rate": round(observed, 4),
            "accuracy": round(accuracy, 4),
            "calibration_error": round(abs(mean_score - observed), 4),
        })
    return bins


def compute_classification_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute binary and score-calibration metrics for compatibility results."""

    evaluated = [
        r for r in results
        if r.get("verdict") in {"TP", "TN", "FP", "FN"} and r.get("score") is not None
    ]
    tp = sum(1 for r in evaluated if r["verdict"] == "TP")
    tn = sum(1 for r in evaluated if r["verdict"] == "TN")
    fp = sum(1 for r in evaluated if r["verdict"] == "FP")
    fn = sum(1 for r in evaluated if r["verdict"] == "FN")
    total = tp + tn + fp + fn
    accuracy = safe_div(tp + tn, total)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    npv = safe_div(tn, tn + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    balanced_accuracy = 0.5 * (recall + specificity) if total else 0.0
    mcc_denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = safe_div(tp * tn - fp * fn, mcc_denom)
    brier = safe_div(
        sum((float(r["score"]) - (1.0 if r["expected_compatible"] else 0.0)) ** 2 for r in evaluated),
        total,
    )
    bins = score_bins(evaluated)
    ece = sum(
        (b["n"] / total) * b["calibration_error"]
        for b in bins
        if total and b["n"] and b["calibration_error"] is not None
    )
    abstentions = sum(1 for r in results if r.get("decision_status") == "needs_context")
    no_verdict = sum(1 for r in results if r.get("decision_status") == "no_verdict")

    return {
        "evaluated": total,
        "abstentions": abstentions,
        "no_verdict": no_verdict,
        "coverage": round(safe_div(total, len(results)), 4) if results else 0.0,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "specificity": round(specificity, 4),
        "negative_predictive_value": round(npv, 4),
        "f1": round(f1, 4),
        "balanced_accuracy": round(balanced_accuracy, 4),
        "matthews_correlation_coefficient": round(mcc, 4),
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "score_bins": bins,
    }


@dataclass
class BinnedCompatibilityCalibrator:
    """
    Lightweight reliability-bin calibrator.

    This is deliberately dependency-free.  It maps a raw score to the observed
    positive rate of the score bin when that bin has enough support.
    """

    num_bins: int = 10
    min_bin_count: int = 3
    bins: List[Dict[str, Any]] = field(default_factory=list)
    global_positive_rate: float = 0.5

    def fit(self, results: List[Dict[str, Any]]) -> "BinnedCompatibilityCalibrator":
        evaluated = [
            r for r in results
            if r.get("score") is not None and r.get("expected_compatible") is not None
        ]
        self.bins = score_bins(evaluated, self.num_bins)
        self.global_positive_rate = safe_div(
            sum(1 for r in evaluated if r["expected_compatible"]),
            len(evaluated),
        ) or 0.5
        return self

    def calibrate(self, score: float) -> float:
        raw = max(0.0, min(1.0, float(score)))
        for item in self.bins:
            if item["n"] >= self.min_bin_count and item["lower"] <= raw <= item["upper"]:
                observed = item.get("observed_positive_rate")
                if observed is not None:
                    return float(observed)
        return raw

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": "binned_reliability",
            "num_bins": self.num_bins,
            "min_bin_count": self.min_bin_count,
            "global_positive_rate": round(self.global_positive_rate, 4),
            "bins": self.bins,
        }


def _default_artifact_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "audit"
        / "calibration"
        / "compatibility_calibration_2026_q4_dev.json"
    )


def _isotonic_interpolate(score: float, payload: Dict[str, Any]) -> Optional[float]:
    """Map a raw score to a calibrated probability via the stored isotonic
    breakpoints (piecewise-linear, clipped at the ends). Dependency-free."""
    xs = payload.get("x")
    ys = payload.get("y")
    if not xs or not ys or len(xs) != len(ys):
        return None
    raw = max(0.0, min(1.0, float(score)))
    if raw <= xs[0]:
        return float(ys[0])
    if raw >= xs[-1]:
        return float(ys[-1])
    for i in range(1, len(xs)):
        if raw <= xs[i]:
            x0, x1 = float(xs[i - 1]), float(xs[i])
            y0, y1 = float(ys[i - 1]), float(ys[i])
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (raw - x0) / (x1 - x0)
    return float(ys[-1])


def _calibrate_from_payload(score: float, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = max(0.0, min(1.0, float(score)))
    min_bin_count = int(payload.get("min_bin_count", 3))
    for item in payload.get("bins", []):
        if item.get("n", 0) < min_bin_count:
            continue
        lower = float(item["lower"])
        upper = float(item["upper"])
        if lower <= raw <= upper and item.get("observed_positive_rate") is not None:
            return {
                "probability": float(item["observed_positive_rate"]),
                "support_n": int(item["n"]),
                "bin": item["bin"],
                "mean_score": item.get("mean_score"),
                "observed_positive_rate": item.get("observed_positive_rate"),
            }
    return None


@dataclass
class CompatibilityCalibrationStore:
    """Runtime wrapper for a generated compatibility calibration artifact."""

    artifact: Dict[str, Any]
    artifact_path: Optional[str] = None

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CompatibilityCalibrationStore":
        artifact_path = path or _default_artifact_path()
        with artifact_path.open(encoding="utf-8") as f:
            artifact = json.load(f)
        return cls(artifact=artifact, artifact_path=str(artifact_path))

    @classmethod
    def empty(cls, reason: str = "calibration artifact unavailable") -> "CompatibilityCalibrationStore":
        return cls(artifact={"version": None, "unavailable_reason": reason}, artifact_path=None)

    def calibrate(self, score: float, domain: Optional[str] = None) -> Dict[str, Any]:
        raw = max(0.0, min(1.0, float(score)))
        version = self.artifact.get("version")
        if not version:
            return {
                "raw_score": round(raw, 4),
                "calibrated_probability": round(raw, 4),
                "calibrator": "none",
                "support_n": 0,
                "artifact_version": None,
                "note": self.artifact.get("unavailable_reason", "calibration unavailable"),
            }

        # Primary: global isotonic calibrator (best out-of-sample ECE).
        isotonic = self.artifact.get("isotonic_calibrator")
        if isotonic and isotonic.get("available") and isotonic.get("x"):
            prob = _isotonic_interpolate(raw, isotonic)
            if prob is not None:
                return {
                    "raw_score": round(raw, 4),
                    "calibrated_probability": round(max(0.0, min(1.0, prob)), 4),
                    "calibrator": "isotonic_global",
                    "support_n": int(isotonic.get("n") or 0),
                    "oos_ece": isotonic.get("oos_ece"),
                    "oos_brier": isotonic.get("oos_brier"),
                    "artifact_version": version,
                }

        if domain:
            domain_payload = self.artifact.get("domain_calibrators", {}).get(domain, {}).get("calibrator")
            if domain_payload:
                calibrated = _calibrate_from_payload(raw, domain_payload)
                if calibrated:
                    return {
                        "raw_score": round(raw, 4),
                        "calibrated_probability": round(calibrated["probability"], 4),
                        "calibrator": f"domain:{domain}",
                        "support_n": calibrated["support_n"],
                        "bin": calibrated["bin"],
                        "mean_score": calibrated["mean_score"],
                        "observed_positive_rate": calibrated["observed_positive_rate"],
                        "artifact_version": version,
                    }

        global_payload = self.artifact.get("global_calibrator")
        if global_payload:
            calibrated = _calibrate_from_payload(raw, global_payload)
            if calibrated:
                return {
                    "raw_score": round(raw, 4),
                    "calibrated_probability": round(calibrated["probability"], 4),
                    "calibrator": "global",
                    "support_n": calibrated["support_n"],
                    "bin": calibrated["bin"],
                    "mean_score": calibrated["mean_score"],
                    "observed_positive_rate": calibrated["observed_positive_rate"],
                    "artifact_version": version,
                }

        return {
            "raw_score": round(raw, 4),
            "calibrated_probability": round(raw, 4),
            "calibrator": "raw_fallback",
            "support_n": 0,
            "artifact_version": version,
            "note": "no reliability bin met min support",
        }


_DEFAULT_STORE: Optional[CompatibilityCalibrationStore] = None


def load_default_calibration() -> CompatibilityCalibrationStore:
    """Load the generated compatibility calibration artifact, falling back to raw scores."""

    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        try:
            _DEFAULT_STORE = CompatibilityCalibrationStore.load()
        except FileNotFoundError:
            _DEFAULT_STORE = CompatibilityCalibrationStore.empty()
    return _DEFAULT_STORE
