# KOMPOSOS-IV Current State

Date: 2026-05-30 (updated: Formation Energy Accuracy + Stability Framework)

## Project Identity

KOMPOSOS-IV is a **categorical runtime** for multi-domain discovery. It is deployed across two main tracks:

- **Track A (Bio/Pharm)**: Drug repurposing over a curated drug-target-disease graph.
- **Track C (Chem/Materials)**: Advanced material compatibility and inverse design (Batteries, Polymers, etc.).

## 2026-05-30 Accuracy & Stability Frontier

Formation-energy surrogate accuracy improved **36%** (MAE 0.473 → 0.304 eV/atom). Integrated nonlinear sparse-discovery model (RandomForest on leak-free MP split). Fixed name-vs-formula parsing trust bug and duplicate composition leakage. Crystal Dreamer property recovery unchanged (78%, different property path). All regression tests green.

### Key Accomplishments (2026-05-27 through 2026-05-30)
- **Formation Energy Accuracy**: MAE **0.304 eV/atom** (−36%), RMSE **0.454** (−40%), median **0.215** (−37%). Sparse-discovery model upgraded from linear ridge to RandomForest; validation: 0.133 eV/atom on 2498 held-out MP materials.
- **Trust Bug Fixed**: Name-vs-formula parsing (predict("Cordierite") was read as "Co") and duplicate LOO leakage both resolved.
- **Interval Recalibration**: Confidence intervals now honest at 50/80/95% coverage; conformal factors tighter due to better point predictions.
- **Simplicial Weight Calibration**: Optimized ensemble weights via grid search (`yoneda=0.75`, `transport=0.25`).
- **Q8 Blind Benchmark Frozen**: 40 new literature-backed pairs (2024-2026) are registered as the current blind benchmark for the next validation claim.
- **Rezk Equivalence**: Enabled mathematical material substitution via isomorphic presheaf detection.
- **Cross-Domain Functors**: Formalized inter-bridge reasoning in the core categorical architecture.
- **UI Simplicial Visualization**: Added interactive Presheaf Overlap comparison to the Compatibility Checker.
- **Shared Reasoning Service**: Unified `oracle/compatibility_service.py` for API/UI compatibility reasoning; the public API preserves its same-domain route contract.
- **Backward Compatibility**: Restored seamless operation for legacy KOMPOSOS-III strategies.
- **Polymer Thermodynamics**: Fixed HDPE+PP label to reflect immiscibility (Flory-Huggins, Robeson citation).

## Current Audit State (Verified 2026-05-30)

### Materials Compatibility (Track C)
- **Development Set (Q5)**: `41/41`, `100.0%` accuracy (polymer label HDPE+PP corrected 2026-05-29).
- **Q8 External Blind**: `30/40` scored, `70.0%` accuracy (frozen 2026-05-27; spent diagnostic).
- **Q9 Blind Diagnostic**: `35/40 = 87.5%` after STT integration (spent diagnostic).
- **Protocol Status**: **PASS** (Accuracy, Physical grounding, Computational, Integration).
- **Q10 Sealed Holdout**: 40 unlabeled pairs; labels hidden. Do not score until polymer model complete.

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
1. **Run Q8 Blind Validation**: Report results against `audit/external_blind/compatibility_2026_q8.json` before further scorer tuning.
2. **Expand Workbench Pipelines**: Add CRYSTAL and MOF pipeline modes beyond the current composition-first path.
3. **Data Leakage Monitoring**: Continuously run `check_data_leakage.py` during dataset expansion to ensure evaluation integrity.

---

*KOMPOSOS-IV | James Ray Hawkins | 2026*
