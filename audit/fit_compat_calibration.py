"""Compatibility calibration — fit comparison (step 2).

Compares calibrators by k-fold OUT-OF-SAMPLE ECE/Brier on the labeled pairs
(dev+Q2-Q9; Q10 sealed): raw score vs Platt (logistic) vs isotonic. Reports the
honest held-out numbers so we deploy only what actually generalizes.

Run:
    python audit/fit_compat_calibration.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

from oracle.compatibility_context import CompatibilityContext
from audit.run_audit import _evaluate_pair, _load_external_blind_pairs

SPENT = [f"compatibility_2026_q{i}" for i in range(2, 10)]
N_FOLDS = 5


def _ece(scores, labels, n_bins=10):
    scores, labels = np.asarray(scores), np.asarray(labels)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        m = (scores >= lo) & (scores < hi if b < n_bins - 1 else scores <= hi)
        if not m.any():
            continue
        ece += m.mean() * abs(scores[m].mean() - labels[m].mean())
    return ece


def _brier(scores, labels):
    return float(np.mean((np.asarray(scores) - np.asarray(labels)) ** 2))


def collect():
    seen, S, Y = set(), [], []
    for name in SPENT:
        path = ROOT / "audit" / "external_blind" / f"{name}.json"
        if not path.exists():
            continue
        pairs, _ = _load_external_blind_pairs(path)
        for p in pairs:
            key = (p["material_a"], p["material_b"], p["domain"])
            if key in seen:
                continue
            seen.add(key)
            ctx = CompatibilityContext.from_pair(p)
            try:
                score, _ = _evaluate_pair(p["material_a"], p["material_b"], p["domain"],
                                          p.get("electrolyte"), p.get("role"), ctx)
            except Exception:
                continue
            S.append(float(score))
            Y.append(1 if p.get("expected_compatible") else 0)
    return np.array(S), np.array(Y)


def main():
    S, Y = collect()
    n = len(S)
    idx = np.arange(n)
    raw_e, platt_e, iso_e = [], [], []
    raw_b, platt_b, iso_b = [], [], []

    for k in range(N_FOLDS):
        test = idx[idx % N_FOLDS == k]
        train = idx[idx % N_FOLDS != k]
        if len(test) == 0 or len(train) == 0 or len(set(Y[train])) < 2:
            continue
        Xtr = S[train].reshape(-1, 1)
        # Platt
        lr = LogisticRegression().fit(Xtr, Y[train])
        p_platt = lr.predict_proba(S[test].reshape(-1, 1))[:, 1]
        # Isotonic
        iso = IsotonicRegression(out_of_bounds="clip").fit(S[train], Y[train])
        p_iso = iso.predict(S[test])

        raw_e.append(_ece(S[test], Y[test])); raw_b.append(_brier(S[test], Y[test]))
        platt_e.append(_ece(p_platt, Y[test])); platt_b.append(_brier(p_platt, Y[test]))
        iso_e.append(_ece(p_iso, Y[test])); iso_b.append(_brier(p_iso, Y[test]))

    def avg(x):
        return sum(x) / len(x) if x else float("nan")

    print("=" * 56)
    print("COMPATIBILITY CALIBRATION — k-fold OUT-OF-SAMPLE")
    print("=" * 56)
    print(f"{n} labeled pairs, {N_FOLDS}-fold\n")
    print(f"{'method':10s} {'OOS ECE':>9s} {'OOS Brier':>10s}")
    print(f"{'raw':10s} {avg(raw_e):9.3f} {avg(raw_b):10.3f}")
    print(f"{'platt':10s} {avg(platt_e):9.3f} {avg(platt_b):10.3f}")
    print(f"{'isotonic':10s} {avg(iso_e):9.3f} {avg(iso_b):10.3f}")
    print("\n(Existing binned calibrator measured ~0.103 ECE in-pool, for reference.)")


if __name__ == "__main__":
    main()
