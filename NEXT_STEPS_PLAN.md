# KOMPOSOS-IV-CHEM: Next Steps Implementation Plan
**Version:** 1.1 (2026-05-30)
**Target:** Triage Accuracy Frontier & Calibration

This plan provides a roadmap for future agents to build upon the Accuracy Milestone (May 2026).

---

## Completed Phase 1: Performance Tuning (2026-05-27 through 2026-05-30)

### ✅ 1.1 Calibrate Simplicial Ensemble Weights — DONE
- **Result**: Yoneda 0.75, Transport 0.25 via grid search on dev set.
- **Status**: Deployed and wired in `oracle/compatibility_ensemble.py`.
- **Reference**: `docs/AUDIT_CHANGE_LOG.md`.

### ⚠️ 1.2 Q8 Blind Benchmark — DEMOTED to spent_diagnostic (2026-05-29)
- **Result**: `audit/external_blind/compatibility_2026_q8.json`, 40 pairs frozen 2026-05-27.
- **Status**: **Demoted from current_blind → spent_diagnostic** because its skip/fail cases
  were inspected during remediation and 14/40 pairs overlap existing identities (never a
  clean holdout). `current_blind_version` is now `null` — **no dataset is currently blind.**
- **Latest Q8 spent-diagnostic run**: 89.5% (TP22/TN12/FP0/FN4), MCC 0.797, Brier 0.107 —
  coverage/error-family tracking only, NOT a blind claim.
- **Next**: freeze Q9 (uninspected recent-literature pairs) before the next blind claim.

### ✅ 1.3 Formation Energy Surrogate Accuracy — DONE (NEW, 2026-05-30)
Highest-priority triage bottleneck tackled. The forward model accuracy gates all stability/synthesizability screening, and it was the roughest component.
- **Improvement**: MAE 0.473 → **0.304 eV/atom** (−36%); RMSE 0.753 → **0.454** (−40%).
- **Method**: Sparse-discovery tier (96% of queries) upgraded from linear ridge to RandomForest on leak-free MP split; name-vs-formula trust bug fixed; duplicate LOO leakage resolved.
- **Validation**: 261 composition tests pass; Crystal Dreamer unchanged (78%); all audits green.
- **Reference**: `docs/FORWARD_MODEL_ACCURACY_2026-05-30.md`, `composition_engine/sparse_mean_model.py`.

### ✅ 1.4 Compatibility Confidence Calibration — DONE (2026-05-30)
- **Improvement**: scores now map to a **calibrated probability** via global **isotonic**
  calibration. Honest k-fold **OOS ECE 0.072** (Brier 0.049), down from raw ECE ~0.194.
- **Method chosen by data**: `audit/fit_compat_calibration.py` (raw 0.167 / Platt 0.158 /
  isotonic 0.095 OOS on 277 pairs). Stored as monotonic breakpoints; runtime interpolates
  dependency-free and prefers isotonic, binned/domain as fallback.
- **No regression**: dev 41/41 / 100% / Brier 0.095; Q8 diag 89.5%; 22/22 calibration tests.
- **Reference**: `docs/AUDIT_CHANGE_LOG.md`, `oracle/compatibility_calibration.py`.

### ✅ 1.5 Directed MOF Generation — DONE (2026-05-30)
- Strategy-weight sliders, seed-molecule pinning, and required functional groups in
  `mof_bridge/linker_generator.py`, wired to `LinkerScreeningSpec` + MOF Designer UI.

### ✅ 1.6 PFAS → Cell-Compatible Alternatives — DONE (2026-05-30)
- `find_replacements_for_cell()` ranks PFAS-free replacements by calibrated compatibility
  with the user's whole cell, surfacing the weakest interface. PFAS Scanner Tab 1 updated.

---

## Phase 2: Blind Validation (High Priority)

The formation-energy accuracy is now at screening-grade (0.30 eV/atom). Next frontier is **calibration and blind validation of the whole triage pipeline** (compatibility + formation energy + inverse design together).

### 2.1 Freeze Q9, then Validate on Q10
Confidence is now **calibrated** (isotonic, OOS ECE 0.072), but calibration was fit on
dev+spent diagnostics — it still needs a **fresh blind** confirmation. No dataset is
currently blind. Freeze Q9 (uninspected recent-literature pairs) and report it first;
Q10 stays the sealed final exam.
*   **When Ready**: After polymer model is complete (Flory-Huggins + DKLT).
*   **Procedure**:
    1. Unseal `audit/external_blind/compatibility_2026_q10_labels_hidden.json`.
    2. Score 40 Q10 pairs via the full ensemble.
    3. Measure accuracy, coverage, ECE, and Brier score.
    4. Report per-domain performance (metals/ceramics should be strong; polymers expected weaker).
    5. Mark Q10 as the **external validation benchmark** for the next publication claim.

### 2.2 Combine Formation Energy + Compatibility for Triage Validation (NEW, Next)
Validate the **end-to-end triage pipeline**: candidates generated → PFAS screened → compatibility checked → formation energy rated.
*   **Test Vehicle**: Battery Optimizer + PFAS Replacement module (both committed).
*   **Procedure**:
    1. Run optimizer over 233K cell combos; collect top-100 candidates.
    2. Filter PFAS-free (100% recall).
    3. Score compatibility + formation energy for each.
    4. Measure: Do top-ranked candidates match real commercial cells? Are bottlenecks physically sensible?
    5. Reference**: `audit/run_battery_optimizer_audit.py`, `audit/run_pfas_replacement_audit.py`.

### ✅ 2.3 Implement Rezk-Equivalence Strategy — DONE (2026-05-27)
Materials A and B are equivalent if there exists a 2-cell (isomorphism) between presheaf embeddings.
*   **Status**: Integrated into `oracle/simplicial_strategies.py`; wired in ensemble votes.
*   **Reference**: STT calibration + Q8 + Q9 audits confirm it works.

### ✅ 2.4 Formalize Cross-Domain Functors — DONE (2026-05-27)
Mapped objects in Domain A → objects/properties in Domain B via TypedPluginMixin.
*   **Status**: Updated `oracle/compatibility_service.py` and cross-bridge analysis live.
*   **Reference**: Multi-domain analyzer + bimetallic cell model.

---

## Phase 3: UI Clarity & Transparency

### ✅ 3.1 Visualizing the "Presheaf Fingerprint" — DONE (2026-05-27)
Researchers can see *why* Yoneda similarity occurred via presheaf overlap visualization.
*   **Status**: Interactive "Presheaf Overlap" comparison live in Compatibility Checker.
*   **Reference**: `streamlit_app/pages/1_Compatibility_Checker.py`.

### 3.2 Triage Page Overhaul (NEW, Recommended)
Update UI pages to be aligned with formation-energy + compatibility pipeline confidence claims.
*   **Target**: `streamlit_app/validation_status.py` is the **single source of truth** for all accuracy/confidence claims.
*   **Status**: Already updated for compatibility, PFAS, MOF, composition predictor.
*   **Remaining**: Integrate formation-energy results (MAE 0.304, tier breakdown, conformal intervals).

### ✅ 3.3 Bio-Domain Realignment — DONE (2026-05-27)
Drug Repurposing track unified with materials track via shared reasoning service.
*   **Status**: `domains/bio/loader.py` fixed (NameError); compatibility_service handles bio routes.
*   **Reference**: Unified oracle architecture.

---

## Phase 4: Frontier Accuracy Work (Medium Priority)

### 4.1 Crystal Dreamer Target-Aware Anchors (Post Formation-Energy)
Crystal Dreamer's property recovery is 78% (good), but composition recovery is 67% because it only works inside dense families.
*   **Hypothesis**: Select Kan neighbors *close to the target property space*, not arbitrary k-nearest-composition.
*   **Target File**: `composition_engine/designer.py`.
*   **When**: After formation-energy work is validated and documented.
*   **Expected Gain**: ~5–10% composition recovery on isolated chemistries (LTO, LiMnO₂).

### 4.2 PFAS Replacement Coverage Expansion
The **cell-compatibility ranking is done** (`find_replacements_for_cell`, calibrated
bottleneck). Remaining gap is *coverage*: only 4 PFAS have curated replacements, and some
candidates (PAA, Alginate) aren't in the polymer compat registry so they can't be cell-scored.
*   **Scope**: Research + add candidates and their compat-registry entries.
*   **Expected**: Higher-quality, cell-scored replacement suggestions for lower-volume PFAS.

---

## Verification Checklist (Updated 2026-05-30)
- [x] `python audit/run_audit.py --module development` passes with 100%.
- [x] `python audit/run_predictor_accuracy.py` — formation energy MAE 0.304, calibration honest.
- [x] `python audit/run_crystal_recovery.py` — property recovery 78% unchanged.
- [x] 261 composition unit tests pass.
- [x] No regressions in API tests.
- [x] `check_data_leakage.py` reports zero leakage from STT + sparse-RF modules.
- [ ] Q10 blind validation (when polymer model ready).
- [ ] Triage end-to-end pipeline validation (optimizer + PFAS + compat + formation energy).

---
**Updated by:** Claude Opus 4.8 | **Last:** 2026-05-30
**Status:** Formation-energy frontier completed; confidence + blind validation next.
