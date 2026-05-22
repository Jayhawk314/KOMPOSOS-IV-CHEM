# KOMPOSOS-III Independent Audit Findings

Date: 2026-05-19

Scope: `docs/AUDIT_PROTOCOL.md`, headline validation claims in `README.md`,
`CLAUDE.md`, `KOMPOSOS_COMPLETE_SYSTEM_GUIDE.md`, the audit runner, the UI
test surface, and spot checks of the composition engine and regulatory claims.

## Executive Finding

I cannot confirm the current repository as research-grade scientifically
validated from the evidence in the repo. The system is a substantial screening
prototype with useful domain heuristics, a large local Materials Project cache,
and a reproducible internal benchmark score. The current audit package does
not yet establish independent research-grade validity.

Recommended public classification until the audit is rebuilt:

- Screening-grade / research-prototype engine.
- Useful for first-pass compatibility triage and hypothesis generation.
- Not yet validated enough for standalone research-grade or compliance-grade
  claims.

## Commands Run

```powershell
python audit\run_audit.py --module all --seed 42
python -m pytest battery_bridge/tests/ polymer_bridge/tests/ metal_bridge/tests/ ceramic_bridge/tests/ semiconductor_bridge/tests/ glass_bridge/tests/ cross_bridge/tests/ synthesis_planner/tests/ molecular_bridge/tests/ pfas_bridge/tests/ composition_engine/tests/ api/tests/ tests/test_material_zfc.py tests/test_enriched_category.py tests/test_dempster_shafer.py tests/test_streaming_kan.py -q
python -m pytest --collect-only -q
python -m pytest -q
```

## What Reproduced Before Fixes

The original audit runner reproduced the headline internal benchmark:

- 259 evaluated pairs.
- TP=172, TN=75, FP=9, FN=3.
- Accuracy=95.37%.
- Precision=95.03%.
- Recall=98.29%.
- F1=96.63%.

The generated report is `audit/audit_report_2026-05-18.json`. The report date
reflects the workstation clock used by the script.

## Post-Fix Audit Status

After removing the benchmark-specific ceramic-metal role override and enforcing
protocol diagnostics, `python audit\run_audit.py --module all --seed 42`
returns overall `FAIL`, as intended.

Scientific module:

- 260 records loaded.
- 219 unique pair identities.
- 27 duplicate pair groups.
- 256 records missing DOI fields.
- 259 evaluated records.
- 1 skipped record (`PP + PE`, unknown polymer `PE`).
- TP=170, TN=75, FP=9, FN=5.
- Accuracy=94.6%.
- Precision=95.0%.
- Recall=97.1%.
- F1=0.960.
- `metric_pass=True` for the loose 80%/75% thresholds.
- `protocol_pass=False` for research-grade validation.

Computational module:

- 9/11 checks passed.
- Category associativity now checks composition metadata and passes.
- Structure prediction reports 21/23 on the 23-material protocol sample.
- Formation energy reports 22/37 within 20%.

Provenance module:

- 30/30 field-presence checks pass.
- This still does not verify values against source papers or official
  registries.

The README-listed pytest command effectively completed with:

- 1485 passed.
- 1 skipped.

The shell wrapper timed out after completion, so this was not a clean process
exit, but the pytest output itself showed the listed subset passing.

## Blocking Findings

### 1. The benchmark is not independent enough for research-grade claims

The protocol claims 259 literature-backed pairs with DOI citations. The loaded
data contained 260 records before one skip, and 256 of those records lacked a
`doi` field. Citations are present, but they are often broad literature strings
rather than exact, source-level provenance.

There are duplicate and non-independent benchmark records. Examples include
repeated battery pairs and repeated semiconductor pairs. This makes the 95.4%
score an internal benchmark result, not evidence of held-out external validity.

### 2. The audit runner has correctness issues

The scientific audit reports `pairs_total` from the last domain's local `pairs`
variable instead of all loaded pairs.

Formation-energy validation prints "within 20%" but accepts relative error
below 60%.

The category associativity check only verifies that both sides exist; it does
not compare the resulting morphism endpoints or data.

The ceramic-metal evaluator contains benchmark-specific role selection for
specific blind-test pairs.

The provenance audit checks field presence and broad numeric ranges. It does
not verify sampled values against the cited papers or official registries.

### 3. The full test suite is not clean

A full `python -m pytest -q` run produced:

- 1704 passed.
- 1 skipped.
- 12 failed.
- 1 error.

The failures were concentrated in UI access-control tests. Access control is
currently disabled intentionally in `streamlit_app/access_control.py`, while
the tests still expect private loader helpers from the prior gated
implementation. The error came from a root-level `_ui_backend_test.py` script
being collected as a pytest test module.

### 4. Composition-engine claims are mixed

The local Materials Project cache is real. The composition engine can load
about 103K cached entries. However, `/api/v1/materials` currently returns the
curated bridge registries, not 103K Materials Project entries. Documentation
that says `/api/v1/materials` exposes 103K+ materials is inaccurate.

Broader spot checks did not support precise research-grade quantitative claims:

- Voltage leave-one-out looked good, but only covered 6 voltage-bearing
  examples.
- Thermal leave-one-out had a max error around 22%, slightly beyond the
  documented 20% upper bound.
- Formation energy across the broader known set had large outliers.
- Structure prediction across the broader known set was about 87% accurate,
  not equivalent to the curated 23/23 claim.

### 5. Regulatory/PFAS docs need timestamped source control

PFAS regulatory dates are category-specific and have changed over time. Local
docs mix or overgeneralize dates. Official sources checked:

- EU PFHxA restriction: Commission Regulation (EU) 2024/2462.
  - 10 April 2026 for specified firefighting foam uses.
  - 10 October 2026 for specified consumer categories.
  - 10 October 2027 and 10 October 2029 for other categories.
- EPA PFAS drinking-water rules were actively changing as of 2026-05-18, with
  proposed rules around PFOA/PFOS compliance extensions and reconsideration of
  some other PFAS determinations.

Regulatory claims should be timestamped, linked to official sources, and
treated as compliance screening, not legal advice.

## Fixes To Make In This Pass

These are code/documentation fixes that can be done safely now:

- Correct audit pair accounting.
- Report duplicate benchmark pairs and missing DOI counts.
- Make skipped scientific pairs fail the audit instead of disappearing behind
  the headline metric.
- Remove benchmark-specific ceramic-metal role assumptions from the audit
  evaluator.
- Make the category associativity check compare the actual composed endpoints
  and composition metadata.
- Make the formation-energy threshold match the printed 20% criterion.
- Mark `_ui_backend_test.py` as non-pytest collection.
- Reconcile the disabled access-control implementation with tests by restoring
  pure parsing helpers while keeping runtime access disabled.
- Update headline docs to call the current result an internal benchmark rather
  than confirmed research-grade validation.

## Work Still Required For Real Research-Grade Validation

These require scientific data curation, not just code edits:

- Freeze a de-duplicated external validation manifest.
- Add DOI or official URL for every ground-truth pair.
- Store exact source claims, extracted property values, and inclusion criteria.
- Mark whether each pair was used for tuning.
- Hold out a benchmark that is never used for threshold tuning.
- Re-run metrics on unique held-out pairs.
- Replace provenance spot checks with source-value verification.
- Add uncertainty/error calibration for formation energy, structure prediction,
  and compatibility scores.
