# Session Summary — PFAS go-to-market + role-aware gate + test-tracking (2026-05-31, Opus)

Branch `remediation/compatibility-coverage-2026-05-29`. Pushed to GitHub
(`Jayhawk314/KOMPOSOS-IV-CHEM`) as commits **9b1a889** (feature) + **072fbc4** (tests).
Still on the feature branch; **no PR opened to `master` yet.**

## What changed (runtime wiring + reports)
1. **Role-aware polymer gate** (`polymer_bridge/interface_validator.py`):
   `validate(...)`/`validate_materials(...)`/`validate_interface(...)` gain
   `interface_role`. For **coexistence/dispersion** roles (`COEXISTENCE_INTERFACE_ROLES`:
   binder, separator, coating, seal, liner, ...) the Flory-Huggins **immiscibility
   veto is skipped** and solubility is down-weighted (`PolymerWeights.coexistence_focus`).
   Blend/unknown roles keep the strict veto. Fixes false negatives on **co-used**
   pairs (CMC+SBR 0.45→0.595 viable, CMC/PP 0.45→0.708) while **HDPE/PP, HDPE/PA6
   stay vetoed and PVDF/PMMA stays miscible** (role unset). Threaded from the
   replacement use-case via `_USECASE_TO_INTERFACE_ROLE` in `pfas_bridge/replacement_scorer.py`,
   auto-passed by `compatibility_service._call_validator` (it forwards `interface_role`).
   **Dev benchmark unchanged: 41/41, Brier 0.095, FP=0 FN=0.** 246 polymer+pfas+report tests pass.
2. **Cell-aware client report** (`reports/pfas_report.py` + `reports/pfas_pdf.py`):
   replacements now scored against the whole **clean cell** via
   `find_replacements_for_cell`; **weakest-interface bottleneck governs the verdict**;
   ordering = evaluated-first (best bottleneck first), no-data last. New **REVIEW**
   verdict so an unscored candidate can't masquerade as VALIDATED on its standalone
   score. Honest "no drop-in clears your cell" recommendation when all candidates
   fail/REVIEW. ENGINE_VERSION 1.2.0→1.3.0.
3. **Date-free regulatory section** (report + `streamlit_app/pages/2_PFAS_Scanner.py`):
   removed all hardcoded effective dates (they go stale / lock us in and the old
   docs even had a **wrong "EU ban Aug 2026"**). Now qualitative `timeframe` +
   `status`, with an explicit "verify current dates against primary sources" note.
4. **`go_to_market/pfas/`** (new): `bom_triage.py` design-partner CLI driving the
   live `pfas_bridge`; `COMPLIANCE_CLOCK_2026.md` (corrected, sourced deadlines —
   near-term teeth are US state laws, EU would not apply before 2029);
   `GO_TO_MARKET.md` (positioning + honesty backlog); `out/` gitignored.
5. **`.gitignore` test fix** (072fbc4): removed the blanket `test_*.py` rule that
   silently kept the **entire test suite untracked**; added 11 verified chem/compat
   tests (PFAS report+pdf, material ZFC, calibration, Dempster-Shafer, enriched
   category, CAT engine, ZFC integration, streaming Kan, MD integration, access
   control). Cyber/mythos + aimo tests deliberately left out (out of scope).

## Verified-real this session
- **MOF linker benchmark** `python -m mof_bridge.benchmark.run` reproduces:
  **94.3% recall** on 423 held-out reals, **AUROC 0.884**, 22-atom slice **95% / 0.90**,
  leak-controlled (SAscore threshold from seed only). Strongest/most honest artifact.

## Bug found + verified (in GO_TO_MARKET.md backlog)
- CMC–SBR / CMC–PP at "7%" were **false negatives** from the immiscibility veto +
  an isotonic **calibration floor** that compresses raw [0.35–0.55]→~7-8%. Gate
  fixes the veto; the calibration low-end resolution remains (backlog #2).

## Next step is James's: outreach (not code)
Pantziarka (PHARM) → one PFAS design partner → Riehl (math; Rzk vs Lean) → Kulik (MOF).
One artifact per person; lead with limitations; never link the wider repo network.

---

# Session Summary — Directed MOF + Calibration + PFAS cell-fit (2026-05-30, Opus)

Three features shipped on `remediation/compatibility-coverage-2026-05-29` (after
Gemini's Advanced Triage Workbench work):

1. **Directed MOF generation** (08256d0) — `LinkerGenerator.generate_candidates`
   gains `strategy_weights`, `seed_smiles`, `required_groups`; threaded through
   `LinkerScreeningSpec` + MOF Designer UI. Random discovery → directed optimization.
   108 MOF tests pass.
2. **Compatibility calibration → isotonic** (cbcffbd) — score is now a calibrated
   probability. Isotonic chosen by out-of-sample ECE (raw 0.167 / platt 0.158 /
   **iso 0.095** on 277 pairs); deployed with honest k-fold **OOS ECE 0.072**.
   Builder fits + stores monotonic breakpoints; runtime interpolates dependency-free.
   **Dev unchanged 41/41 / 100% / Brier 0.095**; Q8 diag 89.5%. UI drops stale
   "ECE ~0.15 / not a probability". See `docs/AUDIT_CHANGE_LOG.md`.
3. **PFAS → cell-compatible alternatives** (904874e) — `find_replacements_for_cell`
   scores each PFAS-free replacement against every adjoining material and surfaces
   the calibrated bottleneck = "PFAS-free AND fits your cell". Fixed a latent
   `CompatibilityWorkflowResult.to_dict` bug that broke the old compatibility column.

Audit posture below is unchanged from 2026-05-29.

---

# Session Summary — Research-Grade Remediation (2026-05-29)

Goal: honest research-grade compatibility on data the system has not seen. Q8 is
the only honest signal and it failed protocol at 70%. This session repaired
coverage and one calibration bug, with a hard rule: **general capability, not
Q8 patches**; the real claim comes from a freshly-frozen Q9.

## Audit-posture change
- **Q8 demoted `current_blind` → `spent_diagnostic`** in `audit/dataset_registry.json`
  (its skip/fail cases were inspected; also 14/40 pairs overlap existing
  benchmarks — never a clean holdout). `current_blind_version` set to `null`.
  **Q8 improvements must NEVER be reported as a blind claim. Freeze Q9 first.**

## What changed (all general capability)
1. **Cross-bridge orientation + abstain** (`cross_bridge/battery_polymer.py`,
   `battery_metal.py`): bridges were order-sensitive and returned a *confident*
   `score=0.0` on the wrong argument order — an honesty bug that manufactured
   false negatives. Now they resolve orientation by DB membership and raise
   `UnknownMaterialError` (→ runner SKIP) on genuinely-unknown materials.
2. **Name resolution + materials**: `get_metal` alias+form-factor layer
   (SS316→SS_316, Ti_foil→Ti, element names); `get_glass` aliases
   (Soda_Lime→SodaLime_Float, Borosilicate→Boro_33); `get_polymer` aliases
   (Silicone→PDMS); added **NCA** cathode (battery DB) and **Kovar** sealing
   alloy (metal DB).
3. **Three new physics-based cross-bridges** (+wired into `audit/run_audit.py`):
   - `cross_bridge/glass_metal.py` — CTE matching + active-metal reactivity.
   - `cross_bridge/metal_semiconductor.py` — metallization suitability + thermal stress.
   - `cross_bridge/polymer_glass.py` — Hansen-polarity + siloxane/thermoset coupling adhesion.
   These behave correctly on non-Q8 inputs too (e.g. SS316+boro fails on CTE,
   Al+GaAs fails metallization, PTFE+glass fails adhesion).
4. **One calibration logic fix**: water-processed binders (CMC/SBR) + Li metal
   now carry a moisture-reaction penalty (Bresser 2018) instead of the generic
   anode-binder bonus. Fixed the `Li_metal+CMC` FP that the orientation fix exposed.

## Q8 DIAGNOSTIC progression (NOT a blind claim)
| stage | acc | eval/skip | TP/TN/FP/FN | MCC | Brier | ECE |
|---|---|---|---|---|---|---|
| baseline | 70.0% | 30/10 | 13/8/2/7 | 0.424 | 0.259 | 0.256 |
| +orientation/abstain | 79.3% | 29/11 | 16/7/3/3 | 0.542 | 0.162 | 0.097 |
| +materials | 81.2% | 32/8 | 18/8/3/3 | 0.584 | 0.156 | 0.115 |
| +cross-bridges | 84.2% | 38/2 | 23/9/3/3 | 0.635 | 0.137 | 0.103 |
| +CMC fix | 86.8% | 38/2 | 23/10/2/3 | 0.703 | 0.119 | 0.117 |

- **Dev set unchanged at 41/41, Brier 0.095** throughout (regression gate).
- 2 intentional remaining skips: `Soda_Lime`/`Cabal-12` + `Li_metal` (niche
  glass-vs-lithium corrosion; not fabricated to match Q8).

## Tooling
- `audit/chem_audit.py` — chem-system-only regression harness (explicit in-scope
  allowlist; never runs the monolithic pytest tree). Pre-existing baseline reds
  (NOT from this work): `mof test_screening_pipeline_small`, 2× `FibrationLiftStrategy`.
- New tests: `cross_bridge/tests/test_interface_cross_domain.py`; updated
  unknown-material tests in `test_battery_polymer.py` / `test_battery_metal.py`.

## Remaining (deferred to user decision before Q9)
- 5 genuine calibration errors: FP `ABS+PVDF`, `PA66+PEO`; FN `Spinel+MgO`,
  `PTFE+PVDF`, `B4C+Al2O3`. These need polymer-miscibility / ceramic-compatibility
  scorer changes with real overfit risk and partly-debatable Q8 labels
  (`PTFE+PVDF` "compatible" is lamination, not blend miscibility).
- **Then: freeze Q9 (uninspected recent-literature pairs) and report Q9 ONLY**
  (coverage, accuracy, AUROC, AP, Brier, ECE, FP/FN). After that: PFAS blind BOM,
  MP category-precision, MOF external verdicts.
