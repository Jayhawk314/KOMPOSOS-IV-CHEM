# Forward-Model Accuracy Improvement — Formation Energy (2026-05-30)

The forward model (formation-energy surrogate) is the accuracy bottleneck for the
whole composition-prediction / Crystal-Dreamer triage stack: "you can't validate a
candidate as good any better than your property predictor is accurate." This work
cut its error by ~36% under honest leave-one-out, and fixed a trust bug, without
weakening any threshold or touching the dense/exact-match path that already works.

## Headline (official audit: `python audit/run_predictor_accuracy.py`)

| metric | before | after |
|---|---|---|
| MAE (eV/atom) | 0.473 | **0.304** (−36%) |
| RMSE | 0.753 | **0.454** (−40%) |
| median abs err | 0.344 | **0.215** |
| interval coverage 50/80/95 | 50/79/94 | **50/80/95** (honest, and *tighter*) |
| "Categorical Ground Truth" tier MAE | **1.600** (n=2, bogus) | **gone** |

DFT-grade reference is ~0.05 eV/atom; this is a structure-free *compositional*
surrogate, so 0.30 is "good screening," not "quantitative." Framed accordingly.

## What was actually wrong (three findings)

1. **The sparse-discovery model was linear.** IDW Kan extension is near-exact when a
   close DFT anchor exists, but ~96% of queries fall in "sparse discovery" (nearest
   anchor ≥0.5 away), where IDW over-smooths. Phase-16 already swaps in a learned
   mean model there — but it was **linear ridge**. Formation energy isn't linear in
   these descriptors.

2. **Name-vs-formula mis-parse (a trust bug).** The accuracy benchmark predicted from
   the display *name*; `parse_formula("Cordierite")` silently read the leading "Co"
   as cobalt → matched elemental Co at distance 0 → predicted Ef ≈ 0 (true −3.18)
   **and labelled it "Categorical Ground Truth," the highest-confidence tier.** That
   is the worst kind of error: confidently wrong.

3. **Duplicate leakage.** Excluding only by name let a near-duplicate anchor
   (GeO₂ / GeO₂_glass) leak the answer in LOO.

## What changed

- **`composition_engine/sparse_mean_model.py`** — a RandomForest on the same Phase-16
  physical descriptors, trained **only on the Phase-16 calibration split** (which
  excludes every KNOWN_EF formula and mp-id), evaluated on the held-out validation
  split. Held-out MAE: **ridge 0.202 → RF 0.133 eV/atom**. Transfer to the curated
  179 audit set: **ridge 0.434 → RF 0.300**. RF chosen over KernelRidge (KRR is
  better in-distribution, 0.108, but worse and less stable on transfer, and can
  extrapolate outside the physical Ef range). Artifact: 7 MB compressed joblib;
  loads lazily with graceful fallback to the linear model if absent/incompatible.
- **`formation_energy.py`** — the sparse branch (`min_dist ≥ 0.5`) now prefers the RF
  mean; dense/exact local Kan values are untouched. Added a known-name→formula guard
  so `predict("Cordierite")` resolves to its formula instead of mis-parsing.
- **Benchmark + calibration** now predict by formula and exclude by formula (true LOO,
  no duplicate leak): `audit/run_predictor_accuracy.py`,
  `composition_engine/calibrate_formation_intervals.py`.
- **Intervals recalibrated** to the improved model — coverage back to an honest
  50/80/95%, and the conformal factors *shrank* (tighter error bars), because the
  point predictions are more accurate.

## Honest caveats / scope

- This improves **formation energy** (stability/synthesizability screening). It does
  **not** change voltage/capacity prediction (a separate path) — so Crystal Dreamer's
  78% property recovery is unchanged; this strengthens the stability side of triage.
- The RF is trained on Materials Project data, so it inherits MP's distribution and
  DFT conventions. The held-out and transfer numbers are honest, but truly novel
  chemistry far from MP will still be rough (as it is for any surrogate).
- Sparse tier is still ~0.31 eV/atom — better, not DFT-grade. The remaining frontier
  is genuinely hard (structure-aware models / more anchors).

## Reproduce / retrain

```
python audit/run_predictor_accuracy.py                       # the headline numbers
python -c "from composition_engine.sparse_mean_model import train_and_save; print(train_and_save())"
python -m composition_engine.calibrate_formation_intervals   # refit honest intervals
python -m composition_engine.experiments.forward_model_bench # the model-selection study
```
