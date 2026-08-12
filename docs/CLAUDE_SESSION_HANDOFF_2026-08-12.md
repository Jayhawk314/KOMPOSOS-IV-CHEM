# Claude Session Handoff

Date: 2026-08-12

Repository: `https://github.com/Jayhawk314/KOMPOSOS-IV-CHEM.git`

Authoritative checkout:

    C:\Users\JAMES\github-clean\KOMPOSOS-IV-CHEM

Branch: `master`

Current HEAD and `origin/master`: `b81085e`

Working tree at handoff: clean.

## Read this first

Do not work from `C:\Users\JAMES\github\KOMPOSOS-IV-CHEM` unless the user
explicitly changes the authoritative checkout. The completed and pushed work is
in `github-clean`.

Do not assess a feature from its filename, page title, documentation, or prior
agent summary alone. For any scientific or product claim:

1. open the rendered page or executable output;
2. trace the backend it actually calls;
3. inspect the evidence artifact and dataset role;
4. run the relevant test or named benchmark;
5. separate observed behavior, development evidence, spent diagnostics,
   screening estimates, historical claims, and `NOT_ASSESSED` claims.

Never combine overlapping test counts. Never convert internal agreement into
experimental validation.

## Current product decision

The candidate product is not an all-in-one materials-discovery platform and not
a generic provenance product. The active hypothesis is:

> A fast, local, mixed-fidelity materials-triage workbench that narrows an option
> set, preserves physical vetoes and missing coverage, and tells a researcher
> what calculation, experiment, or review is needed next.

Evidence governance is the safety architecture under that job. It is not yet a
demonstrated reason that an external researcher will adopt or pay for the tool.

The next gate is external researcher behavior. Do not add Bayesian, vector,
tensor, MLIP, or new-database work merely to improve the internal Crystal
Dreamer story. External demand must select the domain and workflow first.

## Work completed and pushed this session

### `1eb1d04` — measurable fast triage

Implemented and pushed:

- replaced inappropriate PubChem/name/SMILES PFAS work for generated inorganic
  formulas with a formula-scoped tri-state screen;
- preserved exact-registry PFAS vetoes;
- `ASSESSED_PASS` when a valid formula lacks carbon or fluorine;
- `NOT_ASSESSED` when carbon and fluorine co-occur and connectivity/identity is
  still required;
- exposed the tri-state status in Discovery and Advanced Triage tables/exports;
- added `audit/run_triage_readiness.py` and a versioned receipt;
- synchronized UI validation wording and the fast-triage roadmap.

Development diagnostic:

- 30 candidates requested;
- 29 unique formulas returned;
- 18 received route-library matches;
- post-repair elapsed time: 10.859643 seconds;
- pre-repair diagnostic: 69.630 seconds;
- receipt:
  `0cb2c460212a2a6255c565b9b364d47341c4f4573339b75e4043ff5d2b5ad271`.

This is latency and functional evidence only. It is not accuracy, an external
workflow comparison, or a service-level guarantee.

### `99c69b0` — retrieval/search baseline decision

The existing executable Crystal Dreamer ablation was opened, traced through the
real `CompositionDesigner`, extended, tested, and rerun.

Added:

- deployable known-material property retrieval without access to the hidden
  target formula;
- exact target windows in each report row;
- name-stable per-variant seed offsets;
- cache scope keyed by predictor identity, domain, and formula;
- scan/computation counts;
- focused artifact/seed/cache tests.

Current spent development results:

| Variant | Top-1 hits | Any top-25 hit | Exact@25 | Near@25 | Gate coverage |
|---|---:|---:|---:|---:|---:|
| Direct labelled filter | 5/9 | 5/9 | 0/9 | 4/9 | 91.9% |
| Known-property retrieval | 7/9 | 8/9 | 0/9 | 7/9 | 97.4% |
| Hidden-composition oracle | 8/9 | 8/9 | 0/9 | 8/9 | 97.6% |
| Random union, one fixed seed | 7/9 | 7/9 | 1/9 | 4/9 | 81.3% |
| Stoichiometry grid | 7/9 | 7/9 | 4/9 | 6/9 | 100.0% |
| Four-strategy union | 7/9 | 7/9 | 2/9 | 6/9 | 93.6% |

Artifact:

    audit/crystal_search_ablation_report.json

SHA-256:

    c167b3f369987b1f9cf8dbbf36934e51a4765daf5a2e955fab6bdde36c66e1a1

Interpretation:

- four-way generation has no demonstrated incremental search value on these
  spent targets;
- known retrieval is the conservative comparison arm;
- the stoichiometry grid is a transparent battery-family template arm;
- four-way generation may remain only as an explicitly experimental diversity
  arm;
- all target windows and candidate values use the same forward predictor;
- the target formula was removed from retrieval candidates, not from every
  predictor reference artifact;
- none of this is voltage/capacity accuracy, blind evidence, synthesis evidence,
  or experimental validation.

### `b81085e` — external researcher test protocol

Created and pushed:

    docs/EXTERNAL_RESEARCHER_TEST_PROTOCOL_2026-08-12.md

It contains the detailed external-testing plan:

- MOF technical falsification;
- controlled MOF evidence-presentation A/B;
- researcher-supplied battery/interface cases with sealed outcomes;
- PFAS workflow test after regeneration;
- provenance-contract adversarial review;
- recruitment, randomization, data schema, coding rubric, and go/simplify/stop
  rules.

The active roadmap and session decision record link to it.

## Verification completed

Phase 1:

- 295 connected triage tests passed with one unrelated `mp_api` Pydantic
  deprecation warning; this suite overlaps prior test groups;
- application, Discovery Workbench, and Advanced Triage loaded in Streamlit
  AppTest with zero exceptions;
- the then-running Streamlit health endpoint returned HTTP 200.

Phase 2:

- 40 focused audit/designer tests passed;
- Crystal Dreamer loaded in Streamlit AppTest with zero exceptions;
- one expected bare-mode `ScriptRunContext` warning remained;
- expanded ablation completed in approximately 333 seconds;
- Python compilation and `git diff --check` passed.

MOF packet support:

- `python -m mof_bridge.benchmark.run` completed in 17.3 seconds on the current
  checkout;
- reproduced 253 seed, 423 held-out real, 0.9433 pass-all recall, 0.8843 AUROC
  versus raw-generator decoys, exact-22 n=20, recall 0.95, AUROC 0.9013;
- benchmark report SHA-256:
  `a091d9001a72854d409ca245938605ad4e949968cd762733da77cc3a648c5cfa`;
- rerun left the public working tree clean.

Useful commands:

    python -m pytest audit\tests\test_crystal_search_ablation.py composition_engine\tests\test_designer.py -q --import-mode=importlib
    python -u audit\run_crystal_search_ablation.py
    python -m mof_bridge.benchmark.run

The Crystal ablation rewrites a timestamped/runtime-bearing JSON report and will
dirty the working tree even when scientific results are unchanged. Do not rerun
it casually and then commit the artifact without reviewing the full diff.

## Private outreach state

The private directory remains Git-excluded and must not be committed or pushed:

    .private_outreach/

No message was sent and no recipient was selected during this session.

### MOF packet integrity verified

Files:

    .private_outreach/01_mof_chemist/RESEARCHER_REVIEW_A_CONVENTIONAL_2026-08-09.csv
    .private_outreach/01_mof_chemist/RESEARCHER_REVIEW_B_EVIDENCE_2026-08-09.csv
    .private_outreach/01_mof_chemist/RESEARCHER_REVIEW_AB_RECEIPT_2026-08-09.json

Observed:

- A rows: 5;
- B rows: 5;
- same candidate IDs and order: true;
- same formulas and order: true;
- same SMILES and order: true;
- same rank scores and order: true;
- A SHA-256:
  `bf69afb7f0521e73e45d6ae2a4bfbbe024e34284edb4b2e6c05f217bac293c6c`;
- B SHA-256:
  `c96fb3eb0bde4844f933146f8192709134e85dd7c5a1ec3d39e29fbb355d820f`.

### MOF packet defects discovered

Do not run a controlled A/B with the current attachments unchanged:

- the suggested image is a 15-candidate grid with funnel scores, while A and B
  contain only five candidates;
- the 15-grid visually exposes ten extra candidates and can contaminate review;
- the A and B Markdown files do not show exactly the same common fields;
- the CSVs preserve the common fields, but they are not ideal matched reviewer
  layouts;
- the model pre-review contains suggested concerns and would anchor the chemist.

Required repair:

1. create a neutral five-candidate plate with FRESH22-008, -004, -006, -001,
   and -002 in that order;
2. show ID, formula, and structure only on the neutral plate;
3. create matched read-only A/B packet files with identical common fields and
   layout;
4. B adds only the evidence fields being tested;
5. generate a new receipt without overwriting the August 9 receipt;
6. run two usability pilots before main randomization;
7. do not attach the model pre-review until after the primary response is locked.

For simple expert falsification rather than controlled A/B, show the corrected
five-row evidence condition and ask:

> Which candidate would you reject first, and what chemical failure mode is the
> software missing?

### Materials-engineer packet is stale

Do not send its current evidence file unchanged. Replace compatibility status
with:

- Q11 first blind: 23/36 evaluated correct, four no-verdicts, 63.9%, MCC 0.278,
  Brier 0.279, ECE 0.177;
- Q11 is spent after remediation;
- Q12 is current blind and unscored;
- Q10 remains sealed and unconsumed;
- development remains 41/41;
- pairwise calibration is not cell-wide calibration.

Do not score Q12 for outreach.

### PFAS packet is stale and not send-ready

Do not send the July 21 PFAS PDF/Markdown unchanged:

- the files contain visible encoding defects;
- the report says the US EPA TSCA start date is still being finalized;
- the current EPA page records an April 2026 rule update and changed timing;
- all dated regulatory statements require a fresh primary-source check;
- the broad EU restriction remains a proposal/process, not an enacted blanket
  ban;
- the enacted PFHxA restriction has specific scope.

Regenerate the report from current code and verify:

- https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas
- https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202402462
- https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping

Never say `PFAS compliant` or imply the software makes a legal determination.

## Compatibility dataset state

- Development regression: 41/41.
- Q11 first blind: 23/36 among evaluated pairs, four no-verdicts, 63.9%.
- Q11 labels had zero external source-identifier coverage and were authored by
  the same AI assistant that worked on code; independence is limited.
- Q11 is spent after remediation.
- Q12 is current blind and unscored.
- Q10 remains sealed and unconsumed.
- Do not apply pairwise calibration to multi-interface aggregates.
- `AGREE` means executable/internal workflow agreement, not lab confirmation.

## Other modules remain distinct

The Crystal Dreamer result does not invalidate the other functions, and their
evidence must not be pooled into a platform-validation claim:

- MOF Designer/funnel: strongest current structural-screen evidence;
- Compatibility Checker: pair screening with limited dataset independence;
- Cell Designer: explicit physical adjacency and missing-interface coverage;
- PFAS Scanner: first-pass inventory and coverage-aware replacement triage;
- MP Explorer: local provenance/neighborhood inspection, not a live MP session;
- MOF Explorer: 30 curated MOFs with rule-based application scores; does not
  inherit linker-funnel AUROC/recall;
- Synthesis Planner: 24 targets and 17 element-balance witnesses; balance is not
  reaction feasibility;
- Discovery/Advanced Triage: mixed-fidelity orchestration with visible vetoes,
  proxies, and missing coverage.

Do not present all eleven pages in an initial external message.

## Exact next recommended execution

1. Build the neutral five-candidate MOF plate from the existing individual PNGs.
2. Build matched A/B read-only reviewer packets.
3. Create and verify a new packet receipt.
4. Run two usability pilots; do not include them in the main A/B cohort.
5. Freeze assignment and coding rubric.
6. Begin with five MOF falsification requests; nothing is sent automatically.
7. Update the materials-engineer packet to Q11/Q12 state.
8. Create the two-envelope battery-case intake form:
   inputs/conditions in A, sealed outcome in B.
9. Regenerate and re-audit the PFAS demo before any PFAS outreach.
10. Freeze unrelated feature expansion for the 30-to-45-day external test.

Continue development only if external behavior is concrete:

- at least three independent researcher-supplied cases completed;
- evidence changes or prevents at least two next-step decisions;
- at least two groups offer a second case, pilot, or integration;
- repeated missing gates/scorers identify one domain to deepen.

Simplify if retrieval/templates match generation or reviewers value coverage maps
more than predictions. Stop active product development if people discuss the
idea but will not supply artifacts, evidence changes no decisions, or no group
will pilot or integrate it.

## Files to read in order

1. `CURRENT_STATE.md`
2. `docs/SESSION_EXECUTION_AND_VALUE_DECISION_2026-08-12.md`
3. `docs/FAST_EVIDENCE_GOVERNED_TRIAGE_ROADMAP_2026-08-12.md`
4. `docs/EXTERNAL_RESEARCHER_TEST_PROTOCOL_2026-08-12.md`
5. `docs/CRYSTAL_DREAMER_SEARCH_ABLATION_2026-08-09.md`
6. `docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md`

These documents route work, but they are not substitutes for opening pages,
tracing backends, and running the relevant executable evidence before making a
new claim.
