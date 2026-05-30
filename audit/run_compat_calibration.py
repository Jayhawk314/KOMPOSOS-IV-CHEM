"""Compatibility confidence calibration — measurement (step 1).

Are the compatibility scores trustworthy as probabilities? Measures ECE / Brier /
reliability on the labeled pairs (development + Q2-Q9 spent diagnostics; Q10 stays
sealed), for the RAW bridge score and the EXISTING calibrated score.

This only MEASURES. Fitting an improved calibrator (with k-fold out-of-sample ECE)
is the next step, once we see how bad it is.

Run:
    python -m audit.run_compat_calibration   (or: python audit/run_compat_calibration.py)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_calibration import load_default_calibration
from audit.run_audit import _evaluate_pair, _load_external_blind_pairs

SPENT = [
    "compatibility_2026_q2", "compatibility_2026_q3", "compatibility_2026_q4",
    "compatibility_2026_q5", "compatibility_2026_q6", "compatibility_2026_q7",
    "compatibility_2026_q8", "compatibility_2026_q9",
]


def _ece(pairs, n_bins=10):
    """Expected Calibration Error: |mean predicted prob - empirical positive rate|."""
    bins = [[] for _ in range(n_bins)]
    for score, label in pairs:
        b = min(n_bins - 1, int(score * n_bins))
        bins[b].append((score, label))
    n = len(pairs) or 1
    ece = 0.0
    for b in bins:
        if not b:
            continue
        conf = sum(s for s, _ in b) / len(b)
        acc = sum(l for _, l in b) / len(b)
        ece += (len(b) / n) * abs(conf - acc)
    return ece


def _brier(pairs):
    return sum((s - l) ** 2 for s, l in pairs) / (len(pairs) or 1)


def main():
    store = load_default_calibration()
    seen = set()
    raw_pairs, cal_pairs = [], []
    skipped = 0

    for name in SPENT:
        path = ROOT / "audit" / "external_blind" / f"{name}.json"
        if not path.exists():
            continue
        pairs, _ = _load_external_blind_pairs(path)
        for pair in pairs:
            key = (pair["material_a"], pair["material_b"], pair["domain"])
            if key in seen:
                continue
            seen.add(key)
            label = 1 if pair.get("expected_compatible") else 0
            ctx = CompatibilityContext.from_pair(pair)
            try:
                score, _ = _evaluate_pair(
                    pair["material_a"], pair["material_b"], pair["domain"],
                    pair.get("electrolyte"), pair.get("role"), ctx,
                )
            except Exception:
                skipped += 1
                continue
            raw_pairs.append((float(score), label))
            cal = store.calibrate(float(score), pair["domain"]).get("calibrated_probability", score)
            cal_pairs.append((float(cal), label))

    n = len(raw_pairs)
    print("=" * 56)
    print("COMPATIBILITY CONFIDENCE CALIBRATION (measurement)")
    print("=" * 56)
    print(f"Labeled pairs: {n} (deduped across dev+Q2-Q9; {skipped} skipped)")
    print(f"\n{'':12s} {'ECE':>8s} {'Brier':>8s}")
    print(f"{'raw score':12s} {_ece(raw_pairs):8.3f} {_brier(raw_pairs):8.3f}")
    print(f"{'calibrated':12s} {_ece(cal_pairs):8.3f} {_brier(cal_pairs):8.3f}")
    print("\n(ECE 0 = perfectly calibrated; a 0.8 score should mean 80% compatible.)")
    print("Q10 sealed exam intentionally excluded.")


if __name__ == "__main__":
    main()
