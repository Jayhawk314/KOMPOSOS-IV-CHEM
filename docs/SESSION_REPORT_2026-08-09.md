# KOMPOSOS-IV-CHEM Session Report ? 2026-08-09

## Purpose and evidence discipline

This report records the work performed during the 2026-08-09 session, the
results that were actually reproduced, the diagnostics that were spent while
locating failures, the changes currently present in the working tree, and the
recommended plan forward.

The governing rule for this session was: do not assess a feature from a filename,
page title, or documentation alone. The relevant Streamlit page was opened as
source, its backend was traced, its evidence and artifacts were inspected, and
relevant tests or benchmarks were executed before conclusions were drawn.

Evidence labels used below:

- **Observed behavior:** directly seen on the current executable path.
- **Development/spent evidence:** data or targets already inspected or derived
  from the same system; useful for regression and diagnosis, not blind evidence.
- **Spent diagnostic:** a deliberately modified or interrupted run used only to
  locate a problem. It cannot support the product claim.
- **Screening estimate:** a model or rule output that prioritizes investigation.
- **Historical claim:** reported previously but not established by this session.
- **Not assessed:** required support was not obtained.

## Executive summary

The session produced a substantive Crystal Dreamer repair and a reproducible
receipt. The original full-cache recovery audit was not merely slow: it spent
more than 31 minutes in pymatgen's combinatorial oxidation-state enumeration and
never completed. The charge-balance gate was replaced with an existence-only
dynamic program over the same default oxidation-state sets. The replacement
matched pymatgen on all 240 tractable candidate formulas tested and allowed the
full production audit to complete in about 27 seconds.

The current strict leave-one-anchor-out development result is:

- 9 assessed targets; Si skipped because the forward predictor supplied no
  voltage/capacity target.
- Property-window recovery: 7/9 (77.78%).
- Exact composition recovery in the top 25: 2/9 (22.22%).
- Near composition recovery in the top 25: 6/9 (66.67%).
- Mean minimum fractional-composition L2 distance: 0.20089.
- Across the nine target runs, 2,527 of 2,700 charge-balance decisions were
  assessed (93.59%), 102 definite failures were vetoed, and 71 formulas were
  unassessable and retained without physical clearance.

This is **development/spent inverse-search coverage**, not predictor accuracy,
blind validation, experimental recovery, phase stability, or synthesis proof.
The targets and candidate values come from the same forward predictor.

A machine-readable receipt now exists at
`audit/crystal_recovery_report.json`. Its SHA-256 is:

`3992d0e0abdc09f3359e27dd58a657cc5f51260ed69d1b652c4798c6d4d2963b`

The complete composition-engine suite passed: **265/265**. No commit or push was
performed.

## 1. Authoritative working copy

Two local checkouts were compared against the live GitHub remote.

- `C:\Users\JAMES\github-clean\KOMPOSOS-IV-CHEM`
  - HEAD: `281ea87d05e32118e3460a0e73e2a1ba2e921536`
  - Matches live GitHub `master`.
  - Was clean before this session's changes.
- `C:\Users\JAMES\github\KOMPOSOS-IV-CHEM`
  - HEAD: `5a538cc5cdfe7d36ca520c069b76e17ab3f557cc`
  - Four commits behind the live remote.
  - Contains unrelated modified and untracked work.
  - Its cached `origin/master` is stale and therefore misleading.

All production changes from this session were placed in `github-clean`, the
GitHub-matching checkout. The older dirty checkout was not used as the source of
truth. Temporary probe files were removed.

## 2. MOF packet and benchmark checks

### Observed behavior

The private MOF outreach packet is byte-identical in both checkouts and remains
excluded from Git through `.git/info/exclude`. The candidate CSV, Markdown table,
generation receipt, model pre-review, and 2D structure images were opened or
inspected by content. The existing model pre-review is explicitly not a chemist
review.

Fresh executable checks on the authoritative checkout found:

- Candidate-table integrity: 15/15 rows.
- Unique canonical structures: 15/15.
- All 15 are neutral and have exactly 22 heavy atoms as recorded.
- MOF test suite: 108/108 passed; one unrelated `mp_api` Pydantic deprecation
  warning.
- Frozen linker benchmark reproduced:
  - Seed records: 253.
  - Held-out real linkers: 423.
  - Held-out pass-all recall: 0.9433.
  - AUROC versus raw-generator decoys: 0.8843.
  - Exact-22 held-out subset: n=20, recall 0.95, AUROC 0.9013.

### Donor-site correction

Backend tracing confirmed that the funnel SMARTS `[n;r5]` counts substituted
five-membered aromatic nitrogens that may not have an available donor lone pair.
The private packet already records the corrected plausible donor counts:

- FRESH22-002: 4 plausible donors, not 6.
- FRESH22-012: 2 plausible donors, not 4.

The shortlist remains appropriate only for expert falsification:

- Lead screening rows: FRESH22-008, FRESH22-004, FRESH22-006.
- Distinct but caveated: FRESH22-002, FRESH22-001.
- Positional variants: FRESH22-003, 005, 007, 009.
- Deprioritized model rows: FRESH22-010 through 015.

No external chemist reviewed these rows, and no message was sent.

## 3. Crystal Dreamer page and backend trace

The page `streamlit_app/pages/5_Crystal_Dreamer.py` was inspected together with:

- `composition_engine/designer.py`
- `composition_engine/physical_gates.py`
- `composition_engine/predictor.py`
- `composition_engine/known_compositions.py`
- `audit/run_crystal_recovery.py`
- `composition_engine/tests/test_designer.py`

Crystal Dreamer generates formula candidates using four strategies:

1. Anchor perturbation.
2. Same-domain interpolation.
3. Element substitution.
4. Domain-specific stoichiometry grids.

Candidates are evaluated with the same forward composition predictor used to
construct the audit target windows. Returned candidates are then checked for
charge-balance feasibility. This is a formula-level check; no 3D geometry
optimization caused the long runtime.

The local database exposed 103,850 entries during this session.

## 4. Failure localization and spent diagnostics

The following diagnostic runs were intentionally separated from valid evidence:

| Run | Purpose | Runtime/result | Evidence status |
| --- | --- | --- | --- |
| Unmodified pre-fix audit | Attempt named full audit | Terminated after 31.6 minutes and about 1,879 CPU-seconds with no completed result | Spent diagnostic; no benchmark result |
| Charge gate replaced by in-memory pass | Localize bottleneck | Completed in 22 seconds; 7/9 property recovery | Spent diagnostic; physically ungated |
| pymatgen `max_sites=-20` | Test a small hard bound | 26.4 seconds; only 130/436 unique formulas assessed, 306 unassessable | Spent diagnostic; unacceptable coverage |
| pymatgen `max_sites=-40` | Cover common fractional NMC cells | 93.6 seconds; 240/436 assessed, 196 unassessable | Spent diagnostic; incomplete coverage |
| Dynamic-programming prototype | Test existence-only feasibility | 24.8 seconds; 419/436 unique formulas assessed, 17 vetoed, 17 unassessable | Development diagnostic |
| Pymatgen parity subset | Validate the replacement decision | 240/240 agreement, zero disagreements | Development implementation evidence |
| Production fixed audit | Execute named audit unchanged | About 27 seconds; receipt-producing rerun also hashed inputs | Current development/spent result |

Several terminated child processes survived their wrappers and continued to use
CPU and memory. Those session-owned orphan processes were identified by PID and
stopped. This explained some later test slowdown; no unrelated user process was
stopped.

## 5. Implemented Crystal Dreamer changes

### Charge-balance algorithm

`composition_engine/physical_gates.py` no longer asks pymatgen to enumerate and
rank every site-level oxidation-state assignment when the system only needs a
boolean feasibility answer. It now:

- uses the same default ICSD/common oxidation-state sets as pymatgen;
- computes distinct reachable oxidation-state sums per element;
- composes those sums with dynamic programming;
- returns `True` only when total charge zero is reachable;
- returns `False` for a definite failure;
- preserves `None` for an unassessable formula.

The change accelerates the gate without converting missing evidence into a
positive result.

### Coverage accounting

`DesignResult` now records:

- `num_physical_assessed`
- `num_physical_gated`
- `num_physical_unassessed`

Definite failures remain vetoed. Unassessable formulas remain in the returned
list but are counted as missing physical clearance.

The Crystal Dreamer page renders aggregate charge-balance coverage, definite
vetoes, and unassessable counts. The validation note now states the evidence
role and explicitly denies predictive-accuracy or experimental interpretation.

### Reproducible receipt

`audit/run_crystal_recovery.py` now writes a JSON receipt containing:

- evidence role (`development_spent`);
- claim scope;
- command and Python version;
- target names and audit thresholds;
- database-entry count;
- Materials Project cache and metadata hashes;
- audit-script hash;
- per-target results and skip reasons;
- per-target and aggregate physical-gate coverage;
- summary recovery metrics.

Receipt input hashes from the completed run:

- Materials Project summary:
  `0f0b9c5ce33df323f15eb123675c2597c080cb83d5b73f00a28b32bd61017187`
- Materials Project metadata:
  `29f8df95d08825bfba4bbf9ce580880834d1a3f267d6802cdacfe95a15a80513`
- Audit script:
  `13039b95e3647225e740c78bba6763335414ace37fd319158a85b2479f8e41f8`

## 6. Verification performed

- Targeted Crystal Dreamer integration checks before repair: 3/3 passed.
- Full designer module after repair: 36/36 passed.
- Complete `composition_engine/tests` suite: 265/265 passed in 185 seconds.
- Dynamic-programming/pymatgen parity: 240/240 candidate formulas agreed.
- Modified Python modules compiled in memory: 6/6.
- `git diff --check`: passed.
- Receipt JSON schema, evidence role, target count, and SHA-256: checked.

The earlier failed `py_compile` attempt was a filesystem-permission failure while
trying to create `__pycache__` in the read-only checkout. It was not a source
compilation failure; in-memory compilation subsequently passed.

## 7. What the current Crystal Dreamer result means

### Supported interpretation

Crystal Dreamer is useful as a fast, deterministic lead generator that searches
its own forward model and retains formula-level physical vetoes and missing
coverage. It can produce a small investigation list more usefully than a raw,
unannotated ranked CSV.

### Unsupported interpretation

The 7/9 result does not show that:

- the predicted voltages or capacities are experimentally accurate;
- the candidates form stable crystalline phases;
- a particular structure, space group, or topology will form;
- a candidate can be synthesized;
- a candidate will cycle safely or durably in a battery;
- the inverse search outperforms modern generative models;
- Crystal Dreamer discovers chemistry unavailable elsewhere.

LTO and graphite missed the property-window criterion. Si was not assessed
because the forward model did not supply both target properties.

A further limitation remains: the UI now reports aggregate unassessable counts,
but individual candidate rows do not yet carry a visible per-row physical-gate
status. That should be fixed before presenting an unassessable candidate as a
lead.

## 8. Research value and competitive differentiation

### Finding

Researchers may find value in the **evidence-governed workflow**, but uniqueness
has not been demonstrated for Crystal Dreamer's inverse generation itself.

Property-conditioned materials generation already exists at a more sophisticated
structure-generating level. MatterGen directly generates inorganic structures
under property constraints:

- https://doi.org/10.1038/s41586-025-08628-5

Materials Project already provides large-scale property and composition search:

- https://docs.materialsproject.org/

Provenance also exists in mature research infrastructure:

- AiiDA data and logical provenance:
  https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/concepts.html
- NOMAD workflow/provenance schema:
  https://nomad-lab.eu/prod/v1/develop/docs/explanation/workflows.html
- atomate2 task documents and transparent input provenance:
  https://materialsproject.github.io/atomate2/user/docs_schemas_emmet.html

A-Lab demonstrates both the value of integrated discovery workflows and the
importance of learning from failed synthesis attempts:

- https://escholarship.org/uc/item/4w49b5cb

### Plausibly unusual combination

KOMPOSOS may be differentiated by combining:

- physical vetoes that cannot be averaged away;
- explicit missing-interface and unassessed-evidence coverage;
- dataset roles such as blind, sealed, spent, development, and constructed
  decoy;
- receipts tying claims to hashes, commands, parameters, and results;
- separation of source values, derived estimates, heuristics, and unsupported
  claims;
- multiple screening domains in one evidence contract.

Each component has precedents. The claim that their combination is unique
requires a systematic comparison and cannot currently be made.

### Recommended research framing

Do not pitch Crystal Dreamer as a competitor claiming better raw generation than
MatterGen. Use it as a deliberately modest demonstrator for this question:

> Can an end-to-end materials-screening system preserve physical vetoes, missing
> evidence, dataset roles, and reproducible claim receipts while composing
> heterogeneous screening methods?

That is a more credible and potentially valuable research contribution.

## 9. Recommended plan forward

### Priority 0 ? preserve and review this session's work

1. Review the current diff in `github-clean`.
2. Confirm that `audit/crystal_recovery_report.json` should be versioned.
3. Commit only the listed Crystal Dreamer code, tests, documentation, and receipt.
4. Push only after review. Do not copy unrelated work from the older checkout.
5. Make `github-clean` the default writable workspace for future sessions.

No commit or push was performed during this session.

### Priority 1 ? expose evidence per candidate

Add a per-candidate field such as `physical_gate_status` with values:

- `ASSESSED_PASS`
- `VETOED`
- `NOT_ASSESSED`

Vetoed candidates should remain absent from the returned lead list but appear in
an audit/rejection view. Unassessable candidates should be visibly labeled on
every table row and JSON export, not represented only by aggregate counts.

### Priority 2 ? benchmark the search, not merely its self-consistency

Freeze a new evaluation before examining outcomes. Compare Crystal Dreamer with
simple baselines under the same candidate budget:

- nearest known material;
- direct Materials Project property filtering;
- random sampling from the same candidate generator;
- each individual search strategy;
- the four-strategy union.

Measure target-window hit rate, chemical-family distance, physical-gate coverage,
novelty, runtime, and diversity. This would reveal whether the search orchestration
adds value beyond its candidate pool and forward predictor.

### Priority 3 ? obtain external target specifications and outcomes

Ask battery or materials researchers for targets or failure cases they supply
before the system sees the expected answer. Preserve them as sealed inputs.
Potential questions:

- Does the lead list include a known viable family?
- Does the system veto a known impossible or charge-imbalanced candidate?
- Which missing physical check would make the expert reject the top result?
- Does coverage reporting change which calculation or experiment they run next?

Do not use Q10/Q12 or any other sealed compatibility set without an authorized
scoring event.

### Priority 4 ? test the actual evidence-governance differentiator

Run a small A/B researcher study:

- Condition A: conventional ranked candidate CSV.
- Condition B: the same candidates with provenance, physical vetoes, missing
  coverage, uncertainty scope, and receipts.

Measure whether researchers identify unsupported recommendations, missing
calculations, and priority experiments faster or more accurately. This directly
tests the claimed differentiator and avoids competing on raw generative-model
quality.

### Priority 5 ? strengthen physics after ranking

For shortlisted candidates only, add typed escalation rather than silently
upgrading the formula surrogate:

1. Formula-level predictor.
2. Structure-source or structure-generation step.
3. MLIP relaxation where applicability is established.
4. DFT workflow for high-value candidates.
5. Synthesis/experimental outcome when available.

Each tier must preserve its own level of theory, inputs, failures, and receipt.
The existing MLIP tier is not yet wired into Crystal Dreamer.

### Priority 6 ? calibration and abstention

- Establish property-specific and domain-specific calibration where sufficient
  external data exist.
- Add explicit abstention for out-of-domain targets and low-coverage candidates.
- Do not apply pairwise compatibility calibration to multi-interface or inverse
  design aggregates.
- Keep heuristic intervals visibly distinct from calibrated formation-energy
  intervals.

### Priority 7 ? connect provenance infrastructure without duplicating it

Rather than claiming to replace AiiDA, NOMAD, or atomate2, export stable KOMPOSOS
receipts that can be attached to those workflows. Connect Noesis to public JSON
contracts, not private CHEM objects. The distinctive layer should be epistemic
authorization and claim composition, while mature workflow engines retain job
execution and computational provenance.

### Priority 8 ? external MOF falsification

The private five-row MOF shortlist is ready for a narrow expert question, but it
remains software output. Contact a suitable MOF chemist with one artifact, one
reproduced benchmark, one limitation, and one request for a missing chemical
failure mode. Do not send without manually choosing and checking the recipient.

## 10. Current uncommitted files from this session

In `C:\Users\JAMES\github-clean\KOMPOSOS-IV-CHEM`:

- `audit/run_crystal_recovery.py`
- `audit/crystal_recovery_report.json` (new)
- `composition_engine/designer.py`
- `composition_engine/physical_gates.py`
- `composition_engine/tests/test_designer.py`
- `streamlit_app/pages/5_Crystal_Dreamer.py`
- `streamlit_app/validation_status.py`
- `docs/AUDIT_CHANGE_LOG.md`
- `docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md`
- `docs/WEB_UI_DEFINITIVE_GUIDE_2026-07-17.md`
- `docs/SESSION_REPORT_2026-08-09.md` (this report)

## 11. Reproduction commands

From the authoritative checkout:

```powershell
python -m pytest -q -p no:cacheprovider --import-mode=importlib composition_engine/tests
python -u audit\run_crystal_recovery.py
Get-FileHash -Algorithm SHA256 audit\crystal_recovery_report.json
git diff --check
git status --short --untracked-files=all
```

Expected current headline outputs:

- Composition tests: 265 passed.
- Property recovery: 7/9.
- Exact@25: 2/9.
- Near@25: 6/9.
- Gate coverage: 2,527/2,700 = 93.59%.
- Receipt SHA-256:
  `3992d0e0abdc09f3359e27dd58a657cc5f51260ed69d1b652c4798c6d4d2963b`.

## Final assessment

Crystal Dreamer now executes reliably and produces a physically screened,
coverage-aware development lead list. That is useful. It is not an experimentally
validated discovery engine, and its 7/9 result is not evidence of forward-model
accuracy. The strongest research opportunity is the evidence-governance contract
around the screening workflow, provided its value is tested against conventional
workflows and externally supplied cases.
