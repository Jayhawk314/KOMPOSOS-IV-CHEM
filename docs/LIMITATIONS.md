# KOMPOSOS-III Limitations & Confidence Bounds

## Formation Energy Prediction

### Accuracy
- **On materials compositionally similar to KNOWN_EF**: ±0.15–0.2 eV/atom (typical).
- **On novel element combinations**: ±0.3–0.5 eV/atom (typical).
- **Resolved (Phase 12)**: Estimator De-weighting now prevents rule-based noise from pulling accurate DFT data away from reality in dense regions. High-stakes regions are further validated via Active Verification (MD).

### Transparency & Evidence Framework (NEW)
Predictions are now classified into **Uncertainty Tiers** to clearly communicate the degree of heuristic estimation involved:

| Tier | Basis | Physical Meaning |
| :--- | :--- | :--- |
| **Categorical Ground Truth** | dist < 0.05 | Material exists in `KNOWN_EF`. Prediction is an exact match. |
| **Dense Interpolation** | dist < 0.2 | Close neighbors exist. High confidence in chemical similarity. |
| **Moderate Extrapolation** | dist < 0.5 | Logical analogs found. Reliable for screening/hypotheses. |
| **Sparse Discovery** | dist >= 0.5 | Novel chemistry. Treat as qualitative estimate. |
| **Heuristic Estimate** | Rule-based | No nearby neighbors. Based on physical "rules of thumb." |

Formation-energy intervals are now empirically calibrated against the Phase 16 frozen external MP-style split. Compatibility scores also report calibration diagnostics, but they are not guaranteed probabilities; use the external blind Brier score and score-bin reliability table before treating a score like 0.80 as "80% likely correct."

Compatibility calibration is now generated from `audit/dataset_registry.json`
with `python audit/build_compatibility_calibration.py`. The current artifact,
`audit/calibration/compatibility_calibration_2026_q4_dev.json`, uses only
development plus calibration-eligible spent diagnostic data and explicitly
excludes Q4. This improves probability reporting, but it is still a
development calibration artifact, not independent proof of physical truth.

The pre-Q5 ensemble, typed capability checks, failure-memory gate, and strict
Yoneda/Kan transfer guard are decision-support layers. They improve consistency
and reduce known failure modes, but they do not turn development/spent diagnostic
performance into an external blind claim. Q5 remains the next final frozen test
after these add-ons stop changing.

### Known Failure Cases
- **Complex mixed-valence oxides**: Prediction assumes simplified valence states.
- **Novel element groups**: Very sparse regions (e.g. some lanthanides) still have higher uncertainty.

## Structure Type Prediction

### Accuracy
- **On curated materials** (test suite): 96%–100% correct.
- **On full KNOWN_EF database**: ~87% correct.

### Failure Cases
- **Mixed-metal oxides**: Complex cation disorder can confuse rule-based heuristics.
- **Uncommon coordination**: Coordination environments significantly different from standard octahedral/tetrahedral geometries.

## Thermal Stability Prediction

### Status
- **Indirect Inference**: System estimates formation energy and infers stability; it does NOT directly measure decomposition temperature.
- **Max Error**: ~22% on identified benchmark sets.

## Active Verification / GROMACS MD

### Status
- **Real-run path**: API and UI can run GROMACS from a prepared `.gro` structure and `.top` topology, with optional `.mdp` and `.ndx` files.
- **Input discovery**: Users can pass explicit paths, an input directory, or store bundles under `data/gromacs_inputs/<material_a>__<material_b>/`.
- **No fabricated physics**: KOMPOSOS does not auto-generate force fields or atomistic interface structures from material names alone. If inputs, GROMACS, or analyzable trajectory signals are missing, the MD result is `no_verdict` with `measured_md=false`.

## Audit & Validation Status

### Internal Benchmark (215 unique pairs)
- **Tuning split** (102 pairs): 96.1% accuracy.
- **Held-out split** (113 pairs): 92.0% accuracy.
- **Status**: Screening-grade. Requires external validation for research-grade claims.

### External Blind Compatibility Benchmarks
- **Q2 dataset**: `audit/external_blind/compatibility_2026_q2.json`; SHA256 manifest in `audit/external_blind/compatibility_2026_q2.sha256`.
- **Q2 status**: Spent diagnostic set. Its misses informed context-aware and family-specific fixes, so its 100.0% diagnostic rerun must not be presented as a fresh blind score.
- **Q3 dataset**: `audit/external_blind/compatibility_2026_q3.json`; SHA256 `6c4cdaf570f2a69ef3aea62e1d0bcdf516f1838ab2957ea9f9de8e48652ff032`.
- **Q3 first run before Q3-derived tuning**: 36 evaluated, 0 skipped; accuracy 83.3%, balanced accuracy 82.5%, MCC 0.662, Brier score 0.122, ECE 0.207.
- **Q3-derived development file**: `audit/dev_compatibility/q3_failure_family_dev_2026_q3.json`.
- **Q3 spent rerun after tuning**: 36 evaluated, 0 skipped; accuracy 100.0%, balanced accuracy 100.0%, MCC 1.000, Brier score 0.089, ECE 0.216, but protocol pass is false because Q3 now overlaps tuning data.
- **Q4 spent diagnostic dataset**: `audit/external_blind/compatibility_2026_q4.json`; SHA256 `11dd612877667acfa1c7ddeb3626a7f2859d065b5c1c3440fccc4f60f2acf714`.
- **Q4 first run**: 42 evaluated, 0 skipped; accuracy 85.7%, balanced accuracy 85.6%, MCC 0.712, Brier score 0.150, ECE 0.140, protocol pass true.
- **Q4 diagnostic rerun after typed morphism development**: 42 evaluated, 0 skipped; accuracy 100.0%, balanced accuracy 100.0%, MCC 1.000, Brier score 0.100, ECE 0.188. Protocol pass is false because Q4-derived development rows now overlap Q4. This is not a fresh blind claim.
- **Remaining Q4 miss clusters**: none after Q4-derived development, but this only demonstrates that the identified Q4 failure families were addressed.
- **Calibration map**: `audit/dataset_registry.json` marks Q2/Q3/Q4 as spent diagnostics, keeps the raw Q4 file excluded from calibration, and marks all dev files as calibration-eligible development data.

## Path to Research-Grade Status
1. **External Blind Test**: Keep extending frozen, dated blind compatibility sets and never tune against a reported blind file.
2. **External DFT Validation**: 25-50 entries from OQMD/ICSD.
3. **Peer Review**: Submission of methodology paper.
