# KOMPOSOS-III Scientific & Computational Audit Protocol

**Version**: 1.2
**System**: KOMPOSOS-III Chemistry Engine
**Purpose**: Independent third-party validation of scientific accuracy, computational integrity, and data provenance

**Current status (2026-05-21)**: The audit runner includes selectable frozen
external compatibility modules. Q2, Q3, Q4, and Q5 are spent diagnostic sets
because their misses informed context-aware, typed-morphism, or family-specific
scorer fixes. Q5 first ran at 35/35 evaluated, zero skips, 85.7% accuracy,
balanced accuracy 85.8%, MCC 0.712, Brier score 0.159, and ECE 0.231 before
Q5-derived tuning. The frozen Q6 set (`audit/external_blind/compatibility_2026_q6.json`) is
the current blind benchmark. Its first run evaluates 35/35 pairs with zero
skips, zero overlap, 100.0% accuracy, balanced accuracy 100.0%, specificity
100.0%, NPV 100.0%, MCC 1.000, Brier score 0.094, ECE 0.271, and protocol pass
true.

---

## Overview

This audit protocol enables an independent reviewer to validate KOMPOSOS-III across four modules. Each module can be performed independently. The auditor needs only Python 3.10+ and this repository.

**Estimated effort**: 4-8 hours total (can be split across sessions)

---

## Module 1: Scientific Accuracy (Extended Validation)

**Goal**: Verify that KOMPOSOS predictions match published experimental results on a large-scale dataset of literature ground truth.

### Setup
```bash
# Start the API server
uvicorn api.main:app --reload
# Or run the extended audit script directly
python audit/run_audit.py --module scientific
```

### Protocol
1. A benchmark is loaded from `audit/blind_test_pairs.json` and `audit/ground_truth/*.json`.
2. Each pair must have a published ground truth (compatible/incompatible), exact citation, and at least one source identifier: DOI, ISBN, standard ID, official URL, or manual source note.
3. The benchmark must be de-duplicated, and held-out pairs must not be used for tuning.
4. The auditor verifies these materials are correctly registered in the bridge registries.
5. KOMPOSOS evaluates each pair via the compatibility API or audit runner.
6. Predictions are compared against ground truth.

### Metrics (Historical Internal Benchmark)
| Metric | Definition | Pass Threshold | Historical internal result |
|--------|-----------|----------------|----------------------------|
| Accuracy | (TP + TN) / Total | >= 80% | 94.6% on 259 evaluated records |
| Precision | TP / (TP + FP) | >= 75% | 95.0% |
| Recall | TP / (TP + FN) | >= 75% | 97.1% |
| F1 Score | 2 * (P * R) / (P + R) | >= 75% | 0.960 |
| Protocol readiness | No skips, DOI/URL provenance, no duplicate pair identities, no conflicting labels | Required for research-grade claim | Not met as of 2026-05-19 |

### Calibration Metrics
The audit runner also reports:
- **Brier score**: mean squared error between score and binary outcome.
- **Balanced accuracy**: average of recall and specificity.
- **Specificity**: TN / (TN + FP).
- **Negative predictive value**: TN / (TN + FN).
- **Matthews correlation coefficient**: class-balance-aware binary correlation.
- **Score-bin reliability**: 0.0-0.1 through 0.9-1.0 bins comparing mean predicted score with observed positive rate.
- **Coverage / abstention**: evaluated verdicts divided by total records, with `needs_context` and `no_verdict` counted separately.

### Dataset Registry and Calibration Artifact
Compatibility data is separated by role in `audit/dataset_registry.json`:
- `development`: may be used for scorer changes and calibration.
- `spent_diagnostic`: formerly blind data that has informed development; may be used for calibration, but not as a fresh blind claim.
- `current_blind`: reporting-only data; must not be used for scorer tuning or calibration.

Build the current calibration artifact with:
```bash
python audit/build_compatibility_calibration.py
```

The generated artifact is
`audit/calibration/compatibility_calibration_2026_q4_dev.json`. It uses Q2/Q3
spent diagnostics plus development files, deduplicates exact pair identities,
and excludes the raw Q4 external file. Q4 is now spent diagnostic evidence after
post-run miss-family analysis; the Q4-derived development file is explicitly
non-blind and calibration-eligible. Runtime API responses include
`scores.calibration` with the raw score, calibrated probability, source bin,
support count, and artifact version when the artifact is present.

### Typed Compatibility Morphisms
Compatibility scoring now records typed role/interface morphisms such as
`Al_foil --cathode_collector_for[LiPF6]--> NMC622` and
`Al_foil --not_anode_collector_for[LiPF6]--> Si`. It also captures interface
relations such as oxide/sulfide solid-electrolyte vetoes, PZT/alumina package
compatibility, GaN/SiC wide-bandgap epitaxy, and BK7/fused-silica optical
assembly. These morphisms separate collector, tab, coating, electrolyte,
substrate, epitaxy, and assembly evidence from the unordered material pair. They
can act as source-backed priors or vetoes, and audit/API metadata reports the
morphism relation behind each adjusted score.

### Strategy Ensemble and Transfer Guard
Each evaluated compatibility decision now carries an `ensemble` metadata block
with votes from:
- base bridge rule scorer
- typed morphism scorer
- score-bin calibration
- strict Yoneda/Kan transfer guard over sourced development/spent cases
- MetaKan failure-memory gate
- ZFC-style constraint vote
- measured MD/real-tool evidence when real inputs exist

The transfer guard is conservative: it refuses transfer unless structurally
similar source-backed cases clear the threshold and do not conflict. The failure
gate lowers confidence or flips only when a query matches a recorded historical
failure family. These components were frozen before the current Q5 blind run.

- **True Positive**: KOMPOSOS says compatible, experiment confirms compatible
- **True Negative**: KOMPOSOS says incompatible, experiment confirms incompatible
- Decision states: `compatible`, `incompatible`, `needs_context`, `no_verdict`
- Compatible = score >= 0.5, Incompatible = score < 0.5, unless the caller enables context abstention and required role/electrolyte/voltage context is missing.

### Enriched Quantale Diagnostics
Battery-metal and battery-polymer bridge results also include enriched summaries:
- **Bottleneck score**: min quantale over component scores; identifies the weakest axis.
- **Failure risk OR**: probabilistic OR over component failure risks.
- **Confidence product**: multiplicative confidence over component scores.

These are diagnostic composition rules. They help expose hidden vetoes and compounded risk, but they do not replace external validation or prove physical truth.

### MetaKan Failure Memory
The audit runner records every FP, FN, `needs_context`, `no_verdict`, and skip as a compatibility episode in `failure_memory`. Each episode stores:
- material pair, domain, role/context, score, expected label, predicted label
- MetaKan delta type: `HOLLOW` for false positives, `ORPHAN` for false negatives, `UNKNOWN` for abstentions/no-verdicts
- resolution: `REFUTED` for wrong forced predictions, `REFRAMED` for missing-context abstentions
- coarse failure pattern, such as `false_negative:glass_family_rule_gap`

This memory is for error analysis and future scorer development. It must not be used to relabel a frozen blind benchmark while still claiming it is blind.

### What the Auditor Checks
- [ ] Confirm material properties match cited papers in `*_bridge/material_properties.py`
- [ ] Run all loaded pairs through the API or audit runner, with zero skips
- [ ] Record each prediction score and verdict
- [ ] Compute accuracy/precision/recall/F1 plus Brier, balanced accuracy, specificity, NPV, MCC, and score-bin reliability
- [ ] Verify tuning calibrations (galvanic veto, Hansen χ, CTE, lattice) are correctly applied
- [ ] Verify that ZFC classifications (AGREE/HOLLOW) are internally consistent constraint checks; do not treat ZFC agreement as proof of physical truth

---

## Module 2: Computational Integrity

**Goal**: Verify the mathematical framework is correctly implemented.

### 2A: Category Theory Axioms
```bash
python audit/run_audit.py --module computational
```

The script verifies:
- **Associativity**: For morphisms f, g, h: (f . g) . h == f . (g . h)
- **Identity**: For any morphism f: id . f == f == f . id
- **Functor preservation**: F(f . g) == F(f) . F(g) for cross-bridge functors
- **Composition closure**: If A->B and B->C exist, A->C can be computed

### 2B: ZFC Dual Engine
- AGREE: Both CAT and ZFC return positive -> verify both engines were actually consulted
- REJECT: Both negative -> verify constraints that caused rejection
- HOLLOW: CAT yes, ZFC no -> verify a specific ZFC constraint was violated
- ORPHAN: ZFC yes, CAT no -> verify no morphism path exists

### 2C: Dempster-Shafer Fusion
- Verify belief + plausibility bounds: 0 <= Bel(A) <= Pl(A) <= 1
- Verify combination rule: m1 + m2 produces valid mass function
- Verify conflict handling: high-conflict sources reduce combined confidence

### 2D: Reproducibility
- Re-run leave-one-out validation on voltage predictions (expected error: 1.6-7.2%)
- Re-run leave-one-out on thermal stability (expected error: 2.7-22%)
- Re-run crystal structure prediction on 23 known materials and record the exact count
- Re-run formation energy predictions against 37 source-backed DFT values using the stated 20% threshold
- Note: leave-one-out predictor includes known targets in neighbor set (not true held-out)

### Pass Criteria
- [ ] All category theory axioms hold on sampled morphisms
- [ ] ZFC classifications are logically consistent
- [ ] D-S fusion satisfies mathematical constraints
- [ ] **Physics-Embedded Vectors**: Verify that `composition_distance(CaO, PbO) > composition_distance(CaO, MgO)`
- [ ] **Estimator De-weighting**: Verify that `InP` prediction error < 5% (exact match prioritization)
- [ ] **Active Verification**: Run a high-stakes query with a prepared GROMACS `.gro`/`.top` bundle and verify measured-MD or `no_verdict` handling
- [ ] Leave-one-out errors within stated ranges
- [ ] Crystal structure: >= 21/23 correct (91%) or 96% after Phase 12 fixes

---

## Module 3: Data Provenance Spot-Check

**Goal**: Verify that material property data traces back to real published sources.

### Protocol
1. Randomly select 20 materials from the 175 in the database
2. For each material, verify 3 key properties against the cited source
3. Check that CAS numbers and PubChem CIDs are valid
4. Spot-check 5 PFAS regulatory dates against official sources

### Sources to Verify Against
- Material properties: Original journal papers cited in `material_properties.py`
- CAS numbers: https://commonchemistry.cas.org/
- PubChem CIDs: https://pubchem.ncbi.nlm.nih.gov/
- EU PFAS regulations: https://echa.europa.eu/
- US EPA regulations: https://www.epa.gov/pfas

### Pass Criteria
- [ ] >= 19/20 materials have correct property values (within 5% tolerance)
- [ ] >= 19/20 CAS/PubChem identifiers are valid
- [ ] >= 4/5 PFAS regulatory dates match official sources

---

## Module 4: External Blind Compatibility Validation

**Goal**: Report honest compatibility performance on a frozen, non-tuning dataset.

### Setup
```bash
python audit/run_audit.py --module external
python audit/run_audit.py --module external --external-path audit/external_blind/compatibility_2026_q3.json
```

### Frozen Datasets
- Archived diagnostic dataset: `audit/external_blind/compatibility_2026_q2.json`
- Spent diagnostic dataset: `audit/external_blind/compatibility_2026_q3.json`
- Q3 manifest: `audit/external_blind/compatibility_2026_q3.sha256`
- Q3 SHA256: `6c4cdaf570f2a69ef3aea62e1d0bcdf516f1838ab2957ea9f9de8e48652ff032`
- Current non-blind tuning file: `audit/dev_compatibility/q3_failure_family_dev_2026_q3.json`
- Spent diagnostic dataset: `audit/external_blind/compatibility_2026_q4.json`
- Q4 manifest: `audit/external_blind/compatibility_2026_q4.sha256`
- Q4 SHA256: `11dd612877667acfa1c7ddeb3626a7f2859d065b5c1c3440fccc4f60f2acf714`
- Spent diagnostic dataset: `audit/external_blind/compatibility_2026_q5.json`
- Q5 manifest: `audit/external_blind/compatibility_2026_q5.sha256`
- Q5 SHA256: `0c25a2953c10041690f284521a909b78645fbb10e01a3c33eb4fc44b14a4d913`
- Default/current blind dataset: `audit/external_blind/compatibility_2026_q6.json`
- Q6 manifest: `audit/external_blind/compatibility_2026_q6.sha256`
- Q6 SHA256: `f47972bb4d603b8fe1d00e6d36fabc2ec81d5d9639e3879b87a96026c630cc8c`

### Protocol
1. Load 30-50 pairs from `audit/external_blind/`.
2. Verify the SHA256 manifest matches the JSON file.
3. Verify each pair has `used_for_tuning: false`.
4. Verify zero duplicate or conflicting identities inside the external set.
5. Verify zero exact pair-identity overlap with `audit/blind_test_pairs.json`, `audit/ground_truth/*.json`, prior frozen external files, and `audit/dev_compatibility/*.json`.
6. Run every pair through the normal bridge path, with no fallback label substitution.
7. Report all classification and calibration metrics.

### Q3 First Blind Result
Before Q3-derived tuning, `python audit/run_audit.py --module external --external-path audit/external_blind/compatibility_2026_q3.json` reported:
- 36 evaluated, 0 skipped
- TP=18, TN=12, FP=4, FN=2
- Accuracy 83.3%, balanced accuracy 82.5%
- Specificity 75.0%, NPV 85.7%, MCC 0.662
- Brier score 0.122, expected calibration error 0.207
- Failure-memory episodes: 6
- Miss clusters: polymer miscibility false positives (3), ceramic false positive (1), metal false negative (1), semiconductor family-rule false negative (1)
- Protocol pass: true

### Q3 Spent Diagnostic Rerun
After tuning from `q3_failure_family_dev_2026_q3.json`, Q3 reruns at:
- 36 evaluated, 0 skipped
- TP=20, TN=16, FP=0, FN=0
- Accuracy 100.0%, balanced accuracy 100.0%, MCC 1.000
- Brier score 0.089, expected calibration error 0.216
- Protocol pass: false because Q3 now overlaps a development/tuning file

### Q4 Spent Diagnostic Result
`python audit/run_audit.py --module external --external-path audit/external_blind/compatibility_2026_q4.json` reports:
- 42 evaluated, 0 skipped
- TP=20, TN=16, FP=3, FN=3
- Accuracy 85.7%, balanced accuracy 85.6%
- Specificity 84.2%, NPV 84.2%, MCC 0.712
- Brier score 0.150, expected calibration error 0.140
- Failure-memory episodes: 6
- Miss clusters: battery-metal context false positives (2), ceramic false positive (1), ceramic false negative (1), semiconductor family-rule false negative (1), glass-family false negative (1)
- Protocol pass: true

### Q5 Spent Diagnostic Result
`python audit/run_audit.py --module external --external-path audit/external_blind/compatibility_2026_q5.json` reports:
- 35 evaluated, 0 skipped
- TP=13, TN=17, FP=3, FN=2
- Accuracy 85.7%, balanced accuracy 85.8%
- Specificity 85.0%, NPV 89.5%, MCC 0.712
- Brier score 0.159, expected calibration error 0.231
- Failure-memory episodes: 5
- Miss clusters: battery-polymer context false positive (1), polymer miscibility false positives (2), ceramic false negative (1), polymer false negative (1)
- Protocol pass: true

### Q6 Current Blind Result
`python audit/run_audit.py --module external` currently reports:
- 35 evaluated, 0 skipped
- TP=22, TN=13, FP=0, FN=0
- Accuracy 100.0%, balanced accuracy 100.0%
- Specificity 100.0%, NPV 100.0%, MCC 1.000
- Brier score 0.094, expected calibration error 0.271
- Failure-memory episodes: 0
- Protocol pass: true

`python audit/run_audit.py --module development` runs the contextual
development sets at `audit/dev_compatibility/*.json`. Those files are
explicitly non-blind and may be used for tuning.

---

## Running the Full Audit

```bash
# Run all 4 modules
python audit/run_audit.py --module all

# Run individual modules
python audit/run_audit.py --module scientific
python audit/run_audit.py --module computational
python audit/run_audit.py --module provenance
python audit/run_audit.py --module external

# Output: audit/audit_report_YYYY-MM-DD.json
```

## Output Format

The audit script generates a JSON report with:
```json
{
  "audit_id": "AUDIT-2026-MMDD-XXXX",
  "date": "2026-XX-XX",
  "engine_version": "1.2.0",
  "modules": {
    "scientific_accuracy": {"accuracy": 0.XX, "f1": 0.XX, "pass": true/false},
    "computational_integrity": {"axioms_verified": X, "pass": true/false},
    "data_provenance": {"checked": 20, "correct": XX, "pass": true/false},
    "external_blind_compatibility": {"accuracy": 0.XX, "calibration_metrics": {}, "pass": true/false}
  },
  "overall_pass": true/false
}
```

## Who Should Perform This Audit
- Materials science researcher (grad student or postdoc)
- Computational chemistry researcher
- National lab scientist with materials informatics experience
- University research group (potential collaboration opportunity)
