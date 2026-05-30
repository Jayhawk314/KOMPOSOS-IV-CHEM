"""Compute conformal recalibration factors for formation-energy intervals.

The Phase-16 calibrated intervals are systematically too narrow (LOO coverage
~17/46/74% vs the stated 50/80/95%). This derives a per-level multiplier k_alpha
by split-conformal scaling of the per-prediction intervals:

    ratio_i(alpha) = |error_i| / raw_half_width_i(alpha)
    k_alpha        = quantile(ratios, alpha)

so that, after scaling each interval by k_alpha, coverage matches the stated
level. Per-prediction adaptivity (dense vs sparse) is preserved; only width is
rescaled -- the point prediction is never changed.

The DEPLOYED factors are fit on the full set (standard). To report an HONEST,
non-circular coverage estimate we also run k-fold cross-validation: factors fit
on each train split, coverage measured on the held-out split.

Idempotent: divides out any currently-applied factor before recomputing.

Run:
    python -m composition_engine.calibrate_formation_intervals
"""

import json
from pathlib import Path

from composition_engine.formation_energy import (
    FormationEnergyPredictor,
    KNOWN_EF,
    load_conformal_factors,
)

LEVELS = ("50", "80", "95")
N_FOLDS = 5
OUT = Path(__file__).resolve().parent.parent / "data" / "calibration" / "formation_energy_conformal.json"


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return 1.0
    idx = min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def _collect():
    """Predict every material LOO once; return [(err, {lvl: raw_half_width})]."""
    p = FormationEnergyPredictor(use_mp_cache=False)
    existing = load_conformal_factors()  # divide out to recover raw widths
    data = []
    for entry in KNOWN_EF:
        try:
            r = p.predict(entry.name, exclude_formula=entry.name)
        except Exception:
            continue
        if r.ef_per_atom is None:
            continue
        err = abs(r.ef_per_atom - entry.ef_per_atom)
        iv = r.calibrated_intervals_eV or {}
        raw = {}
        for lvl in LEVELS:
            hw = iv.get(lvl)
            if hw and hw > 0:
                raw[lvl] = hw / existing.get(lvl, 1.0)
        if len(raw) == len(LEVELS):
            data.append((err, raw))
    return data


def _factors_from(idxs, data):
    f = {}
    for lvl in LEVELS:
        ratios = sorted(data[i][0] / data[i][1][lvl] for i in idxs)
        f[lvl] = _quantile(ratios, int(lvl) / 100.0)
    return f


def _coverage(idxs, data, factors):
    cov = {lvl: 0 for lvl in LEVELS}
    for i in idxs:
        err, raw = data[i]
        for lvl in LEVELS:
            if err <= factors[lvl] * raw[lvl]:
                cov[lvl] += 1
    n = len(idxs) or 1
    return {lvl: cov[lvl] / n for lvl in LEVELS}


def main():
    data = _collect()
    n = len(data)

    # Deployed factors: fit on the full set.
    full = _factors_from(range(n), data)

    # k-fold out-of-sample coverage (honest, non-circular).
    fold_cov = {lvl: [] for lvl in LEVELS}
    for k in range(N_FOLDS):
        test = [i for i in range(n) if i % N_FOLDS == k]
        train = [i for i in range(n) if i % N_FOLDS != k]
        if not test or not train:
            continue
        kf = _factors_from(train, data)
        cov = _coverage(test, data, kf)
        for lvl in LEVELS:
            fold_cov[lvl].append(cov[lvl])

    oos = {lvl: sum(v) / len(v) for lvl, v in fold_cov.items() if v}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "method": "split_conformal_multiplicative",
        "target": "formation_energy_eV_per_atom",
        "n_calibration": n,
        "factors": {lvl: round(full[lvl], 4) for lvl in LEVELS},
        "kfold_oos_coverage": {lvl: round(oos.get(lvl, 0.0), 3) for lvl in LEVELS},
        "n_folds": N_FOLDS,
    }, indent=2), encoding="utf-8")

    print(f"Deployed factors (full-set): { {l: round(full[l],3) for l in LEVELS} }")
    print(f"{N_FOLDS}-fold OUT-OF-SAMPLE coverage (the honest number):")
    for lvl in LEVELS:
        rate = oos.get(lvl, 0.0)
        flag = "ok" if abs(rate * 100 - int(lvl)) <= 12 else "off"
        print(f"  {lvl}% interval -> {rate:.0%} held-out  [{flag}]")
    print(f"Written: {OUT}")


if __name__ == "__main__":
    main()
