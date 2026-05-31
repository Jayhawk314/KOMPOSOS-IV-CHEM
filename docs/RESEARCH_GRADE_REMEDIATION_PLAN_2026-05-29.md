# Research-Grade Remediation Plan - 2026-05-29

This plan treats the current repo as the active base. Older repos are controls
for regression comparison, not rollback targets.

## Current Blind/Evaluation State

- Q8 is spent diagnostic evidence. It exposed the coverage and calibration gap:
  30/40 evaluated, 70% accuracy on scored pairs, AUROC 0.700, Brier 0.259,
  ECE 0.256.
- Q9 is the first useful post-repair blind-style result and is documented in
  `docs/Q9_PER_DOMAIN_RESULTS_2026-05-29.md`. The honest framing is per-domain:
  inorganic/interface domains are useful; polymer-polymer blend compatibility
  remains experimental.
- Q10 now exists as an unlabeled future pair file:
  `audit/external_blind/compatibility_2026_q10_pairs_unlabeled.json`.
  Pair SHA256:
  `4d5f6fd414eae277493e6b8f2ceebedfcdb8add6989c910d45959d0ded0c1003`.
  A hidden label file also exists at
  `audit/external_blind/compatibility_2026_q10_labels_hidden.json` with SHA256
  `e1ad2c309443426352a167352ec46cf35f1bd5af6c1fc1b61bacf7826d05501e`; Codex
  has not inspected it.
  Do not score it until the team explicitly decides the polymer model is ready
  for a final check.

## Scope Guard

Do not use the full monolithic pytest tree as the chem-system quality signal.
This repo contains unrelated or legacy AIMO, cyber/Mythos, OpenTargets/drug, and
root debug tests. For chem/materials work, run only the in-scope bridge,
composition, PFAS, MOF, MP Explorer, compatibility-audit, and Workbench checks.

## Tier 1: Fix Correctness Blockers

- Composition vectors must have one stable serialized shape.
  - Status: fixed by making `composition_vector()` element-only and moving
    group/period enrichment into `composition_feature_vector()`.
  - Acceptance: parser and MP vector dimension tests pass.

- Crystal structure prediction must not crash on broader formula paths.
  - Status: fixed missing `average_electronegativity` import.
  - Acceptance: structure predictor unit tests pass and broad formula sweep has
    no `NameError` coverage skips.

- MP Explorer search must find common aliases and semantic categories.
  - Status: fixed alias/formula nearest fallback and category search fallback.
  - Acceptance: `NMC811`, `LiNi0.8Mn0.1Co0.1O2`, `perovskite`, and the 10-item
    popular list return non-empty results.

- Cell Design must not let a non-viable interface pass through an average score.
  - Status: fixed cell-level viability to honor interface vetoes.
  - Acceptance: known good demo cells remain viable; Si and LGPS problem cells
    become non-viable with explicit interface warnings.

- Discovery Workbench default run must score the design objective.
  - Status: fixed default target from unsupported ionic conductivity to voltage.
  - Acceptance: default-style Workbench run has nonzero design scores.

## Tier 2: Convert Useful Tools Into Validated Claims

- PFAS Scanner:
  - Build a blind BOM benchmark with PFAS-positive and PFAS-negative materials.
  - Report sensitivity, specificity, precision, recall, false-positive causes,
    and replacement recommendation coverage.
  - Claim type: compliance screening / curated regulatory intelligence.

- Formation Energy / Composition Predictor:
  - Preserve Phase16 held-out reporting as the main research-grade result.
  - Add drift tests so vector-shape or feature changes cannot silently alter
    reported MAE/RMSE.
  - Claim type: surrogate formation-energy screening with calibrated limits.

- MOF Designer:
  - Validate generated linkers against external novelty, SA/synthetic-accessibility,
    linker-likeness, and expert/external review.
  - Report valid-generation rate, uniqueness, novelty, and external viability.
  - Claim type: candidate generator until external viability is measured.

## Tier 3: Repair Weak Predictive Surfaces

- Compatibility Checker:
  - Treat Q8 and Q9 as spent diagnostics after inspection and repair work.
  - Q9 per-domain results showed polymer-polymer blends were the weak domain.
  - Status: first production chi_c integration is now in place through
    `polymer_bridge/flory_huggins.py`, representative MW/N data, and empirical
    compatibility overrides for known engineering interfaces.
  - Current spent-Q9 diagnostic after integration: 35/40 = 87.5%, AUROC 0.9247,
    AP 0.9745, Brier 0.0987, ECE 0.1486.
  - Remaining modeling task: replace representative MW values with
    grade-specific/cited molecular-weight data and expand the empirical chi /
    compatibility table from literature instead of Q-set pairs.
  - Required target before broader research-grade claim: zero skips, AUROC above
    0.80, balanced accuracy above 0.80, and ECE below 0.15 on a sealed future
    set such as Q10.

- Cell Design:
  - Build a small literature-backed cell benchmark with known good, marginal,
    and failed interfaces.
  - Calibrate thresholds against that benchmark instead of demo cells.

- MP Explorer:
  - Improve category precision after search correctness: semiconductor pure
    elements, perovskite formula families, battery material families.
  - Treat category labels as search aids until benchmarked.

## Tier 4: Integration Claims

- Discovery Workbench:
  - Report module-level evidence for each candidate instead of a single opaque
    confidence score.
  - Only claim as much validation as the weakest module in the selected path.

- STT/Yoneda/Categorical Evidence:
  - Keep as provenance/explainability unless an ablation proves blind metric
    improvement.
  - Required claim: compare raw heuristic vs categorical-enhanced output on a
    frozen blind benchmark.
