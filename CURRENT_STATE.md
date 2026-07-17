# KOMPOSOS-IV-CHEM current state

Updated: 2026-07-17

## Identity

The chemistry/materials track is an evidence-governed screening workbench. Its
strongest general capability is not a universal chemical predictor; it is the
ability to compose narrow screens while preserving provenance, physical vetoes,
dataset roles, uncertainty scope, and missing coverage.

## Current reproducible headline numbers

- Compatibility development regression: 41/41.
- No compatibility dataset is currently blind. Q9 is spent (35/40 after
  remediation); Q10 is sealed and unscored.
- Pairwise compatibility calibration artifact: 98 development/spent rows,
  isotonic OOS ECE 0.072 and Brier 0.049. This is not per-domain evidence and is
  not valid for arbitrary aggregate scores.
- Formation-energy strict-formula LOO: n=179, MAE 0.416, RMSE 0.552, median
  absolute error 0.340 eV/atom.
- Formation-energy interval coverage after recalibration: deployed 50/79/95%;
  five-fold out-of-sample calibration 49/80/94%.
- MOF funnel: held-out-real pass-all recall 0.9433; AUROC 0.8843 versus raw
  generator decoys; exact-22 n=20 recall 0.95 and AUROC 0.9013.
- Synthesis planner: 24 curated targets, 17 formal element-balance witnesses,
  seven composite/mixture targets explicitly skipped.
- Local Materials Project cache: 103,644 entries in the audited checkout.

The historical 0.304 eV/atom formation-energy headline is superseded for the
current strict-LOO executable path. Historical reports may retain it as a record
of a previous protocol; current product copy may not use it without naming that
protocol.

## Repairs completed in the 2026-07-17 audit

- Removed current collectors from battery active-material search pools.
- Repaired the 103K discovery path's cache/index/predictor API mismatches and made
  enabled discovery visible in returned results.
- Added anode and separate cathode/anode collectors to manual cell design.
- Added physical adjacency, expected-interface coverage, and an epistemic veto:
  incomplete coverage cannot produce a full-stack viable verdict.
- Relabeled pymatgen oxidation-state feasibility as charge balance, not
  independent ZFC verification.
- Replaced the Discovery Workbench's unconditional charge-balance placeholder
  with a real hard gate.
- Preserved charge-balance metadata through downstream compatibility calls.
- Removed pairwise probability calibration from multi-interface aggregates.
- Replaced zero-valued proxy assertions with actual composition distance where
  resolvable.
- Ensured every returned Crystal Dreamer candidate passes physical gates.
- Recalibrated formation-energy intervals and froze a drift baseline with artifact
  hashes.
- Added stable monitoring exports and content-addressed drift receipts for a
  Noesis bridge.
- Corrected stale topology imports and Category/store adapter use in oracle
  strategies; corrected the chemistry test harness's import collision.
- Updated UI validation notes and the primary public documentation.

## Important boundaries

- Category theory organizes the runtime. No repository ablation demonstrates an
  accuracy gain caused by category theory.
- A calibrated pairwise compatibility probability is not calibration evidence for
  a whole-cell or multi-interface aggregate.
- A generated formula scored through a known proxy inherits proxy distance and
  applicability limits.
- Formal stoichiometric balance is not reaction feasibility.
- MOF funnel performance is screening evidence, not synthesis validation.
- PFAS-free replacement ordering is triage until validated for the user's process.

## Verification

- Focused repair set: 44 passed.
- Bridge/orchestration set: 903 passed.
- Oracle stale-interface regressions: 4 passed.
- Composition parser/properties/spatial: 66 passed.
- Structure predictor: 42 passed in 77.45 seconds.
- Formation/calibration/predictor: 80 passed in 187.15 seconds.

See `docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md` for the per-feature assessment
and `docs/PROVENANCE_CONTRACT_PROJECT.md` for the LLM/user evidence-layer design.
