# KOMPOSOS-IV Current State

Date: 2026-05-30 (updated: Directed MOF generation, compatibility calibration, PFAS cell-fit)

## Project Identity

KOMPOSOS-IV is a **categorical runtime** for multi-domain discovery. It is deployed across two main tracks:

- **Track A (Bio/Pharm)**: Drug repurposing over a curated drug-target-disease graph.
- **Track C (Chem/Materials)**: Advanced material compatibility and inverse design (Batteries, Polymers, etc.).

## 2026-05-30 Latest Frontier (3 features shipped)

- **Directed MOF generation**: the linker generator went from random discovery to
  directed optimization — strategy-weight sliders, seed-molecule pinning (generate only
  derivatives of one SMILES), and required functional groups (hard SMARTS filter).
- **Compatibility confidence calibration**: scores are now a **calibrated probability**
  via global **isotonic** calibration. Honest out-of-sample **ECE 0.072** (Brier 0.049),
  down from raw ~0.194 — a 0.70 now means ~70%. Dev verdicts unchanged (41/41).
- **PFAS → cell-compatible alternatives**: each PFAS-free replacement is scored against
  every adjoining material; the calibrated bottleneck (weakest interface) is surfaced, so
  output is "PFAS-free AND compatible with your cell," not just "not PFAS."

## 2026-05-30 Accuracy & Stability Frontier

Formation-energy surrogate accuracy improved **36%** (MAE 0.473 → 0.304 eV/atom). Integrated nonlinear sparse-discovery model (RandomForest on leak-free MP split). Fixed name-vs-formula parsing trust bug and duplicate composition leakage. Crystal Dreamer property recovery unchanged (78%, different property path). All regression tests green.

### Key Accomplishments (2026-05-27 through 2026-05-30)
- **Directed MOF Generation**: `strategy_weights`, `seed_smiles`, `required_groups` in
  `mof_bridge/linker_generator.py`, wired to `LinkerScreeningSpec` + MOF Designer UI.
- **Compatibility Calibration (isotonic)**: `audit/build_compatibility_calibration.py`
  fits a global isotonic calibrator (OOS ECE 0.072); runtime interpolates dependency-free.
- **PFAS Cell-Fit**: `find_replacements_for_cell()` ranks replacements by calibrated
  compatibility with the user's whole stack; fixed a latent `to_dict` bug that broke the
  old single-material compatibility column.
- **Formation Energy Accuracy**: MAE **0.304 eV/atom** (−36%), RMSE **0.454** (−40%), median **0.215** (−37%). Sparse-discovery model upgraded from linear ridge to RandomForest; validation: 0.133 eV/atom on 2498 held-out MP materials.
- **Trust Bug Fixed**: Name-vs-formula parsing (predict("Cordierite") was read as "Co") and duplicate LOO leakage both resolved.
- **Interval Recalibration**: Confidence intervals now honest at 50/80/95% coverage; conformal factors tighter due to better point predictions.
- **Simplicial Weight Calibration**: Optimized ensemble weights via grid search (`yoneda=0.75`, `transport=0.25`).
- **Rezk Equivalence**: Enabled mathematical material substitution via isomorphic presheaf detection.
- **Cross-Domain Functors**: Formalized inter-bridge reasoning in the core categorical architecture.
- **UI Simplicial Visualization**: Added interactive Presheaf Overlap comparison to the Compatibility Checker.
- **Shared Reasoning Service**: Unified `oracle/compatibility_service.py` for API/UI compatibility reasoning; the public API preserves its same-domain route contract.
- **Backward Compatibility**: Restored seamless operation for legacy KOMPOSOS-III strategies.
- **Polymer Thermodynamics**: Fixed HDPE+PP label to reflect immiscibility (Flory-Huggins, Robeson citation).

## Current Audit State (Verified 2026-05-30)

### Materials Compatibility (Track C)
- **Development Set**: `41/41`, `100.0%` accuracy, Brier 0.095 (polymer label HDPE+PP corrected 2026-05-29).
- **Blind status**: **No dataset is currently blind** (`current_blind_version: null`).
  Q2–Q8 are all spent diagnostics. **Q8 was demoted to spent_diagnostic on 2026-05-29**
  (skip/fail cases inspected; 14/40 identity overlap) — its numbers are coverage/error-family
  tracking only and must NOT be reported as a blind claim. Freeze Q9 before any new blind claim.
- **Q8 spent-diagnostic latest run**: 89.5% (TP22/TN12/FP0/FN4), MCC 0.797, Brier 0.107.
- **Confidence calibration**: isotonic, honest out-of-sample ECE 0.072 (down from raw ~0.194).
- **Protocol Status**: development + computational **PASS**.
- **Q10 Sealed Holdout**: 40 unlabeled pairs; labels hidden. Do not score until ready.

### Formation Energy Surrogate (Track C, new 2026-05-30)
- **Training Set (179 curated, LOO)**: MAE **0.304 eV/atom**, RMSE **0.454**, median **0.215**.
- **Held-out MP validation (2498)**: RF MAE **0.133 eV/atom** (vs ridge 0.202).
- **Transfer to curated set**: RF MAE **0.300** (vs ridge 0.434; −31%).
- **Calibration**: Honest 50/80/95% coverage; conformal factors tighter.

### Drug Repurposing (Track A)
- **AUROC (Bio)**: `0.9008` (Confirmed via `confirm_auroc.py` on full 78x20 matrix).
- **Provenance**: 100% citation coverage for the curated `tier1.db` graph.

## What Works
- Core **Infinity Cosmos** ($\infty$-cosmos) runtime is active.
- **COG Engine** provides 5 tiers of deep verification.
- **ZFC Dual-Engine** grounding is enforced.
- **MOF Linker Designer** handles exact atom counts (Kulik 22-atom challenge).
- **PFAS Scanner** provides auditable compliance reports.

## Immediate Next Steps
1. **Freeze Q9** (uninspected recent-literature pairs) and report it as the next blind claim with full calibration metrics. No dataset is currently blind.
2. **Expand Workbench Pipelines**: Add CRYSTAL and MOF pipeline modes beyond the current composition-first path.
3. **Crystal Dreamer point accuracy**: target-aware anchors for isolated chemistries (LTO, LiMnO₂).
4. **Data Leakage Monitoring**: Continuously run `check_data_leakage.py` during dataset expansion to ensure evaluation integrity.

---

*KOMPOSOS-IV | James Ray Hawkins | 2026*
