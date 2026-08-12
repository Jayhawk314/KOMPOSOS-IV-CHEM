# KOMPOSOS-IV-CHEM Session Closure - 2026-08-09

## Purpose

This document closes the August 9 work and supersedes
`docs/SESSION_REPORT_2026-08-09.md` as the current session summary. The earlier
report remains a record of the Crystal Dreamer runtime investigation, but it was
written before later implementation, ablation, MOF, UI, outreach, commit, and
push work was completed.

The governing rule remained: do not assess a feature from its filename, page
title, or documentation alone. Relevant Streamlit pages were opened as source,
their backends were traced, their evidence was inspected, and relevant tests or
benchmarks were run before conclusions were recorded.

Evidence language in this report:

- **Observed behavior:** directly inspected on the executable code path.
- **Development/spent evidence:** useful for regression or diagnosis, but not
  blind or external validation.
- **Screening estimate:** a model or rule output used to prioritize review.
- **Historical claim:** previously reported but not freshly established here.
- **Not assessed:** required evidence was not obtained.

## Authoritative checkout and Git state

The authoritative working copy is:

`C:\Users\JAMES\github-clean\KOMPOSOS-IV-CHEM`

The older checkout at `C:\Users\JAMES\github\KOMPOSOS-IV-CHEM` remains behind
and contains unrelated modified and untracked work. It was not used for the
final changes and should not be used to start the UI.

The authoritative checkout was clean after the completed work. Local `master`
and `origin/master` both pointed to:

`a189b02d74a745830dc4f7e3b42e9387f7cb0568`

Remote: `https://github.com/Jayhawk314/KOMPOSOS-IV-CHEM.git`

Completed commits:

1. `3dea991 fix: complete Crystal Dreamer gate audit`
2. `3809b64 feat: expose Crystal Dreamer physical status`
3. `4c22080 audit: benchmark Crystal Dreamer search strategies`
4. `0f35c23 docs: preserve Crystal Dreamer data model plan`
5. `a189b02 feat: add evidence-governed MOF review exports`

The private `.private_outreach/` directory remains excluded through
`.git/info/exclude`. No private packet or outreach message was committed or
pushed. No external message was sent.

## 1. Crystal Dreamer runtime repair

### Observed behavior

The original full recovery audit spent more than 31 minutes inside pymatgen's
combinatorial oxidation-state enumeration and did not complete. The bottleneck
was formula charge-balance evaluation, not geometric structure generation.

The production gate now uses an existence-only dynamic program over the same
default oxidation-state sets. It asks whether a neutral assignment exists
without enumerating and ranking every site-level assignment.

Development implementation evidence:

- Agreement with pymatgen: 240/240 tractable formulas.
- Full named audit runtime: approximately 27 seconds.
- Full composition suite at repair closure: 265/265 passed.
- Definite failures remain vetoes.
- Unassessable formulas remain explicitly unassessed.

### Recovery result and scope

The strict leave-one-anchor-out development audit reported:

- Nine assessed targets; silicon skipped because the forward predictor did not
  provide both requested properties.
- Property-window recovery: 7/9.
- Exact composition recovery in the top 25: 2/9.
- Near-composition recovery in the top 25: 6/9.
- Charge-balance decisions: 2,527 assessed, 102 definite failures vetoed, and
  71 unassessable.

This is **development/spent self-consistency evidence**. Target windows and
candidate values come from the same forward predictor. It does not establish
experimental voltage or capacity accuracy, stable phases, synthesizability,
cycle performance, safety, or superior discovery performance.

## 2. Per-candidate physical status

The unfinished correctness issue in the original report was closed.
`DesignCandidate` now carries `ASSESSED_PASS`, `VETOED`, or `NOT_ASSESSED`.
`DesignResult` preserves physical rejections separately.

Crystal Dreamer now exposes:

- per-lead physical status;
- aggregate assessed, vetoed, and unassessable counts;
- a rejection view for definite charge-balance failures;
- audit records in CSV and JSON.

Vetoed candidates remain outside the lead list. Unassessable candidates can be
retained for screening but no longer look physically cleared.

Verification:

- Focused status tests: 37/37 passed.
- Full composition suite: 266/266 passed.
- Updated receipt SHA-256:
  `78331a0e22103a1a213f8a41001f37d704edf8ca49bbdd3478e451b03b21343b`

## 3. Search-strategy ablation

The search was compared with simple baselines before adding another model.
Dataset inspection found 12,378 battery records but only 12 with both voltage
and capacity labels. Zero Materials Project rows had both labels, so direct MP
voltage/capacity filtering was `NOT_ASSESSED`.

Nine development targets were assessed:

| Method | Property windows | Exact@25 | Near@25 | Gate coverage |
| --- | ---: | ---: | ---: | ---: |
| Direct labelled lookup | 5/9 | 0/9 | 4/9 | 91.9% |
| Hidden-composition neighbour oracle | 8/9 | 0/9 | 8/9 | Non-deployable |
| Single-seed random union | 7/9 | 1/9 | 4/9 | 81.3% |
| Perturbation only | 5/9 | 0/9 | 4/9 | See receipt |
| Interpolation only | 7/9 | 0/9 | 4/9 | See receipt |
| Substitution only | 7/9 | 1/9 | 5/9 | See receipt |
| Stoichiometry grid only | 7/9 | 4/9 | 6/9 | 100% |
| Four-strategy union | 7/9 | 2/9 | 6/9 | 93.6% |

Conclusion: incremental value from the four-strategy orchestration is
**not established**. The 7/9 headline largely reflects forward-predictor
self-consistency and hard-coded NMC, olivine, and spinel templates. The small
stoichiometry grid matched the property-window and near-composition results and
exceeded the union on exact recovery.

Crystal Dreamer is therefore a transparent, template-guided formula enumerator
and evidence-governance demonstrator. It is not supported as a general
materials-discovery engine or distinctive search algorithm.

Artifacts:

- `audit/run_crystal_search_ablation.py`
- `audit/crystal_search_ablation_report.json`
- `docs/CRYSTAL_DREAMER_SEARCH_ABLATION_2026-08-09.md`

Receipt SHA-256:
`5bb4541a45c336efc6560e587cb72fae5155da080a6b34f9c3a723315855392b`

## 4. Bayesian and data proposal

`docs/CRYSTAL_DREAMER_DATA_AND_BAYESIAN_EMBEDDING_PLAN.md` is **proposal only**.
No Bayesian voltage/capacity model, joint embedding, tensor representation,
posterior calibration, or abstention model was implemented or validated.

Main conclusions:

- Drawing a Bayesian spread in an embedding cannot replace missing labels; it
  expresses assumptions rather than creating observations.
- Capacity should begin with deterministic electrochemical constraints when
  charged/discharged stoichiometry and electron transfer are defined.
- Voltage requires a charged/discharged reaction or phase pair, working ion,
  energy convention, and method provenance.
- Deterministic representation ablations should precede Bayesian heads.
- Any Bayesian head must report applicability, prior dominance, empirical
  interval coverage, and abstention.

## 5. MOF Designer review workflow

### Backend finding

The funnel sets `passed_all=True` when 3D geometry returns `None`. The old UI
language could therefore imply every grounded gate was assessed when geometry
was unavailable. The frozen scorer and benchmark were not changed. The review
layer now maps outcomes to:

- `ASSESSED_PASS`: geometry and all implemented gates assessed and passed.
- `PARTIAL_PASS`: retained, but 3D donor geometry was not assessed.
- `VETOED`: an implemented hard gate failed.
- `NOT_ASSESSED`: no funnel result exists.

MOF Designer now displays full versus partial passes, per-row status and stop
point, accurate top-candidate status, conventional and evidence-governed CSVs,
and JSON audit schema `mof_designer_review.v2`. Unvalidated generic toxicity,
conductivity, stability, and application verdicts are excluded from researcher
review CSVs.

### Reproduced development benchmark

- Frozen seed records: 253.
- Held-out real linkers: 423; gold tier: 120.
- Held-out recall: 0.9433.
- AUROC versus raw-generator decoys: 0.8843.
- Exact-22 subset: n=20, recall 0.95, AUROC 0.9013.
- Generator candidates: 233; historically passed: 60; novel-pass: 14.
- Full MOF suite: 110/110 passed.

This supports structural screening against the recorded real-linker corpus and
constructed decoys. It does not establish synthesis, correct metal
coordination, topology, phase formation, toxicity, stability, conductivity, or
application performance.

## 6. Private researcher packet and contact research

A same-order five-candidate packet was created under the ignored private folder.
All five were independently rescored as `ASSESSED_PASS`, including assessed 3D
geometry. Their experimental status remains `NOT_ASSESSED`.

Recommended initial attachments:

1. `RESEARCHER_REVIEW_B_EVIDENCE_2026-08-09.md`
2. `structures/FRESH_EXACT22_GRID_2026-07-19.png`

Never attach `kulik_22atom_linkers_100.csv`. Do not show both conventional and
evidence-governed conditions to one reviewer before collecting the response.

Private receipt SHA-256:
`995b88df7cdaa2a2ce376af9da8f54196a9b8bc98b1fd03e961bdd0ff102efe3`

Current institutional pages were checked. The strongest first-recipient fit was
Zhiling "Zach" Zheng at Washington University in St. Louis: his group combines
AI with experimental framework synthesis, and his 2026 perspective identifies
synthetic feasibility and domain-knowledge integration as open problems. The
belief that a new assistant professor may be more responsive is only a
screening estimate; no response is guaranteed.

Recommended question:

> Which candidate would you reject first, and what chemical failure mode is the
> software missing?

Backups:

1. Kyriakos Stylianou - experimental MOF design and synthesis.
2. Andrew Rosen - computational MOF data, stability, and methodology.
3. Praveen Thallapally - Washington-based experimental MOF expertise.

No chemist has reviewed the candidates and nothing has been sent.

## 7. Final UI verification

The authoritative checkout was inspected after all five commits. Crystal
Dreamer exposes physical coverage, per-candidate status, rejections, top-pick
status, and audit downloads. MOF Designer exposes full/partial counts,
per-candidate status and stop point, top status, paired CSVs, and v2 JSON.

Fresh final-check evidence:

- 39/39 relevant tests passed.
- AST syntax checks passed for both pages and supporting modules.
- `git diff --check` passed.
- Worktree was clean and local `HEAD` equalled `origin/master`.

A new browser click-through of every control on all eleven pages was not run, so
no new full browser-level UI audit is claimed. No Streamlit process was running.
Start the UI only from the authoritative checkout.

## 8. Recommended next work

### Priority 1 - obtain one real MOF falsification

Stop expanding the model temporarily. Manually review and send the two-item
packet to one carefully selected MOF researcher. Ask only for the first
rejection and missing failure mode. Record the reply verbatim before modifying
the funnel.

If a missing gate is proposed, preserve the original response, define the gate
without tuning only to the five shown rows, and test it against the frozen real
linkers and decoys. Report recall loss, discrimination change, and new
unassessable cases before production use.

### Priority 2 - test evidence presentation

With multiple reviewers, randomly assign conventional or evidence-governed
presentation. Measure whether status, missing evidence, and scope help identify
unsupported leads or the next calculation. Do not show both conditions first.

### Priority 3 - obtain externally supplied compatibility cases

Ask a materials engineer for one difficult pair or known stack failure before
the system sees the answer. Preserve it as sealed input. Keep Q12 current blind
and unscored, and keep Q10 sealed and unconsumed, until explicitly authorized
scoring events.

### Priority 4 - close interface coverage

Add native scorers for missing battery/ceramic, battery/battery, and
polymer/ceramic contacts. Missing required contacts must remain coverage gaps,
not neutral probabilities.

### Priority 5 - define the battery dataset contract

Before Bayesian modeling, version charged/discharged phases, working ion,
reaction convention, theoretical versus experimental capacity, method or
protocol, chemistry family, source, hashes, dataset role, leakage groups, and
family/source/time splits. Ingest more labelled data, compare deterministic
representations, and add a Bayesian head only if it improves calibrated
out-of-family behavior while reporting prior dominance and abstaining.

### Priority 6 - connect Noesis through public receipts

Use stable CHEM JSON exports and hashes. Do not import CHEM private objects or
reuse unrelated numeric baselines as chemistry calibration. Keep native
chemistry verdicts distinct from artifact-drift or reasoning-coherence status.

## Final assessment

This session repaired Crystal Dreamer's blocking runtime, exposed per-candidate
physical status, honestly benchmarked its search, preserved the Bayesian idea
as a proposal, corrected MOF evidence presentation, reproduced the MOF
benchmark, prepared an expert-falsification packet, and pushed all bounded
public changes.

The natural next move is not another internal feature. It is one external
chemical falsification of the MOF shortlist, followed by a controlled test of
whether evidence-governed presentation helps a researcher make a better
decision.
