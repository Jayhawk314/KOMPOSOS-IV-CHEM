"""Composition Predictor ACCURACY + CALIBRATION benchmark (leave-one-out).

This measures the thing recovery does NOT: are the predicted property values
actually correct, and are the uncertainty intervals honest?

Target: formation energy (eV/atom) -- a real physical quantity the predictor
genuinely predicts (Kan extension over neighbors), with 179 reference values in
KNOWN_EF. True leave-one-out: each material is excluded from its own prediction.

Reports:
  - MAE / RMSE / median abs error (accuracy)
  - interval coverage at 50/80/95% (calibration: a well-calibrated 80% interval
    should contain the truth ~80% of the time)
  - per-uncertainty-tier breakdown
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from composition_engine.formation_energy import FormationEnergyPredictor, KNOWN_EF


def main():
    p = FormationEnergyPredictor(use_mp_cache=False)
    errs = []
    cov = {"50": 0, "80": 0, "95": 0}
    by_tier = {}
    n = skipped = 0

    for entry in KNOWN_EF:
        name = entry.name
        truth = entry.ef_per_atom
        try:
            # Predict from the FORMULA, not the display name: a name like
            # "Cordierite" would be mis-parsed as a formula (leading "Co" -> Co).
            # Exclude by formula so near-duplicate anchors (e.g. GeO2/GeO2_glass)
            # cannot leak the answer -- true leave-one-out.
            r = p.predict(entry.formula, exclude_formula=entry.formula)
        except Exception:
            skipped += 1
            continue
        if r.ef_per_atom is None:
            skipped += 1
            continue
        err = abs(r.ef_per_atom - truth)
        errs.append(err)
        n += 1

        iv = r.calibrated_intervals_eV or {}
        for lvl in ("50", "80", "95"):
            hw = iv.get(lvl)
            if hw is not None and err <= hw:
                cov[lvl] += 1

        tier = getattr(r.uncertainty_tier, "value", str(r.uncertainty_tier))
        t = by_tier.setdefault(tier, {"n": 0, "abs_sum": 0.0})
        t["n"] += 1
        t["abs_sum"] += err

    errs.sort()
    mae = sum(errs) / len(errs) if errs else 0.0
    rmse = (sum(e * e for e in errs) / len(errs)) ** 0.5 if errs else 0.0
    median = errs[len(errs) // 2] if errs else 0.0

    print("=" * 60)
    print("COMPOSITION PREDICTOR ACCURACY + CALIBRATION (LOO)")
    print("=" * 60)
    print(f"Formation energy, {n} materials ({skipped} skipped)")
    print(f"\nAccuracy (eV/atom):  MAE {mae:.3f} | RMSE {rmse:.3f} | median {median:.3f}")
    print("\nCalibration (interval coverage vs. stated level):")
    for lvl in ("50", "80", "95"):
        rate = cov[lvl] / n if n else 0.0
        flag = "ok" if abs(rate * 100 - int(lvl)) <= 10 else "MISCALIBRATED"
        print(f"  {lvl}% interval -> covers truth {rate:.0%}  [{flag}]")
    print("\nPer uncertainty tier:")
    for tier, d in sorted(by_tier.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {tier:26s} n={d['n']:3d}  MAE {d['abs_sum']/d['n']:.3f}")
    print("\nNote: LOO removes each material's own neighbors, so errors reflect")
    print("true generalization to unseen chemistry, not memorized lookups.")


if __name__ == "__main__":
    main()
