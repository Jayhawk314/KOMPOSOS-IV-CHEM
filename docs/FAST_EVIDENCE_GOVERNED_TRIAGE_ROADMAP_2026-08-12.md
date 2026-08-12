# Fast Evidence-Governed Materials Triage Roadmap

Date: 2026-08-12

Status: active go/no-go roadmap. This document does not declare commercial,
predictive, experimental, or regulatory validation.

## Product decision

Do not position KOMPOSOS as an all-in-one materials-discovery platform or as a
generic provenance product. Both framings create tunnel vision and place the
system against substantially stronger professional platforms.

The candidate product is:

> A fast, local, mixed-fidelity materials-triage workbench that narrows a large
> option set, preserves physical vetoes and missing coverage, and tells a
> researcher what must be calculated, measured, or reviewed next.

Evidence governance is the safety architecture underneath that job. It is not
necessarily the reason a researcher opens the tool.

## What fast triage means

Fast triage is not discovery proof. It is an early decision stage before DFT,
molecular dynamics, synthesis, supplier qualification, or laboratory testing.
A useful triage run should:

1. accept a target and constraints in minutes rather than requiring a custom
   notebook or full simulation campaign;
2. produce a reproducible shortlist;
3. eliminate candidates that violate computable hard constraints;
4. distinguish assessed passes, vetoes, and unassessed checks;
5. show proxy distance, interface coverage, and uncertainty role;
6. identify the next missing calculation or experiment;
7. avoid presenting its ranking as experimental or full-engineering truth.

The main value hypothesis is reduced researcher attention and avoided wasted
follow-up work, not superior first-principles accuracy.

## Intended users and market

Primary users:

- experimental researchers planning which candidates to inspect or synthesize;
- computational materials researchers preparing a higher-fidelity campaign;
- materials-informatics teams combining heterogeneous evidence;
- small research groups without a custom screening infrastructure;
- R&D teams evaluating externally supplied candidate lists or substitutions.

Likely buyer or sponsor:

- R&D methods or digitalization lead;
- laboratory or research-program manager;
- materials-informatics lead;
- technical-quality or model-validation owner.

This is not initially a PFAS compliance, production battery safety, enterprise
LIMS/ELN, HPC orchestration, or autonomous-laboratory product.

## Current evidence

Observed behavior:

- the Advanced Triage page calls the real composition designer, charge-balance
  gate, known-material proxy resolver, multi-domain interface analyzer, and
  synthesis planner;
- charge-balance failures are hard vetoes;
- unassessable charge balance receives no verdict;
- partial interface coverage is shown separately from a full-stack verdict;
- proxy identity and composition distance are displayed;
- formation-energy intervals are separated from heuristic property bounds.

Development evidence:

- the pre-repair 2026-08-12 cold local run requesting 30 Li-bearing, 3.0-to-4.5 V candidates
  returned 29 unique formulas in about 70 seconds;
- after removing the inappropriate network/SMILES PFAS path, two post-repair runs
  returned the same 29 unique formulas in 10.498 and 10.860 seconds, about
  6.4 to 6.6 times faster than the 69.630-second pre-repair run;
- in both runs all 29 passed the charge-balance gate and 18 received a
  route-library match;
- this is functional and latency evidence only, not predictive accuracy;
- the run exposed an inappropriate name/SMILES/PubChem PFAS path for generated
  inorganic formulas. Phase 1 replaced it with a formula-scoped tri-state gate.

Previously reproduced evidence, with its original scope:

- Crystal Dreamer recovered 7/9 predictor-generated property windows, but only
  2/9 exact compositions at top 25; this is spent self-consistency evidence;
- the MOF funnel achieved 0.943 held-out real-linker recall and 0.884 AUROC
  against constructed raw-generator decoys; this is structural funnel evidence,
  not wet-lab success;
- formation-energy strict formula leave-one-out MAE is about 0.416 eV/atom;
- pair compatibility has development and spent evidence but no currently scored
  blind dataset; Q12 remains sealed;
- PFAS replacement screening returned 18/18 structurally PFAS-free suggestions
  in the curated audit, but its replacement library covers only four PFAS and
  seven PFAS/use-case combinations.

Not yet established:

- that evidence-governed triage changes a research decision or saves time versus
  a direct database filter or simple notebook on externally supplied cases;
- that the ranking predicts experimental outcomes;
- that researchers save meaningful time or change decisions;
- that users will supply data, adopt the workflow, or pay for it;
- that all eleven UI functions belong in one product.

## Phase 1: make fast triage measurable

Status: implemented and benchmarked locally on 2026-08-12.

Deliverables:

- remove network/SMILES resolution from generated inorganic formula screening;
- represent PFAS formula screening as assessed pass, veto, or not assessed;
- preserve exact-registry PFAS vetoes;
- add a reproducible local triage-readiness benchmark and receipt;
- show tri-state PFAS status in both discovery pages;
- retain hard charge-balance veto behavior.

Acceptance criteria:

- no PubChem lookup occurs for generated formulas;
- formula-only C/F candidates are not called PFAS-free;
- a representative 30-candidate local triage run completes in a measured,
  reviewable time;
- the report clearly says that latency and functional coverage are not
  predictive or experimental evidence.

Verification:

- versioned report: `audit/triage_readiness_report.json`;
- versioned run elapsed time: 10.859643 seconds;
- receipt: `0cb2c460212a2a6255c565b9b364d47341c4f4573339b75e4043ff5d2b5ad271`;
- receipt recomputation matched;
- 295 connected tests passed;
- four changed Python modules compiled from source;
- both modified Streamlit pages loaded in AppTest with zero exceptions;
- the running Streamlit health endpoint returned HTTP 200 and ok;
- one unrelated dependency warning remained from `mp_api` using deprecated
  Pydantic class-based configuration.

## Phase 2: benchmark triage value

Status: internal search-mechanics comparison completed on 2026-08-12. External
workflow value remains unassessed and moves to Phase 3.

Compared under the same spent target windows, top-25 rule, forward predictor,
and physical-gate path:

- direct filtering of the remaining labelled battery records;
- deployable known-material property retrieval;
- an explicitly non-deployable hidden-composition oracle;
- random candidates from the same generator;
- individual Crystal Dreamer strategies;
- the four-strategy union.

Direct Materials Project voltage/capacity filtering was `NOT_ASSESSED`: the
local MP summary cache contains zero entries carrying both labels. The direct
labelled-record baseline had only 11 eligible records after target removal.

Observed development/spent results:

| Variant | Top-1 window hits | Any top-25 hit | Exact@25 | Near@25 | Gate coverage |
|---|---:|---:|---:|---:|---:|
| Direct labelled filter | 5/9 | 5/9 | 0/9 | 4/9 | 91.9% |
| Known-property retrieval | 7/9 | 8/9 | 0/9 | 7/9 | 97.4% |
| Hidden-composition oracle | 8/9 | 8/9 | 0/9 | 8/9 | 97.6% |
| Random union, one fixed seed | 7/9 | 7/9 | 1/9 | 4/9 | 81.3% |
| Stoichiometry grid | 7/9 | 7/9 | 4/9 | 6/9 | 100.0% |
| Four-strategy union | 7/9 | 7/9 | 2/9 | 6/9 | 93.6% |

Receipt: `audit/crystal_search_ablation_report.json`; SHA-256
`c167b3f369987b1f9cf8dbbf36934e51a4765daf5a2e955fab6bdde36c66e1a1`.
The report freezes exact target windows and name-stable variant seeds.

Decision rules:

- The four-strategy union has no demonstrated incremental search value on these
  spent targets. Do not market the orchestration as an advantage.
- Keep known-material retrieval as the conservative comparison arm and the
  stoichiometry grid as a transparent family-template arm for external cases.
- Keep four-way generation only as an explicitly experimental diversity arm
  until an external target shows an outcome the simpler methods miss.
- Do not implement Bayesian, vector, tensor, MLIP, or new-database expansion to
  repair this result. Those are separate data/model hypotheses.
- Local self-consistency cannot establish user value; Phase 3 is now the active
  gate.

Measure:

- wall-clock and researcher interaction time;
- unique and family-diverse candidates;
- hard vetoes caught;
- unassessed requirements exposed;
- proxy distances and interface coverage;
- higher-fidelity calculations avoided or prioritized;
- performance on externally supplied known failures.

The target windows and candidate values came from the same forward predictor.
Known retrieval is deployable as a search policy, but its 8/9 result is still
same-model self-consistency: the target formula was removed from the candidate
pool, not from all predictor reference artifacts. None of these numbers
establish experimental or prospective accuracy.

## Phase 3: external researcher test

Time box: 30 to 45 days. Freeze unrelated feature expansion.

1. Obtain at least three real candidate lists, substitution questions, or stack
   failures from independent researchers.
2. Present a conventional shortlist and an evidence-governed triage shortlist.
3. Ask 6 to 10 domain researchers to review paired outputs without coaching.
4. Measure unsupported leads caught, missing work identified, decision changes,
   review time, and perceived burden.
5. Obtain at least two real pilot or integration commitments.

The private MOF shortlist and a battery-interface case are starting artifacts,
not external validation.

Kill criteria:

- triage does not outperform a simple filter or notebook in useful decisions;
- the extra evidence does not change a review or next experiment;
- researchers will discuss the idea but will not supply an artifact;
- no group will pilot or integrate it;
- maintaining breadth prevents a reliable workflow in any one domain.

If these conditions hold after the time box, stop active product development.

## Phase 4: productize only the demanded workflow

Begin only after external use establishes which workflow has value.

- expose a small triage API and reproducible decision packet;
- add explicit GO, VETO, and NOT_ASSESSED requirement policies;
- export provenance through an established format such as RO-Crate;
- integrate with AiiDA or NOMAD rather than replacing them;
- harden authentication, tenancy, persistence, and deployment only for a real
  pilot requirement;
- deepen one scientific domain, not all eleven pages simultaneously.

Bayesian battery work belongs here only if external demand selects battery
triage and a versioned dataset with adequate voltage/reaction and capacity
labels exists. Twelve joint labels cannot support a competitive broad model.

## Immediate sequence

1. Preserve the completed Phase 2 audit, tests, receipt, and decision.
2. Select one externally understandable battery/interface packet and the existing
   MOF evidence packet; do not introduce all eleven pages.
3. Recruit independent researchers and obtain at least three cases they supplied,
   not cases chosen by this project.
4. Compare conservative retrieval/template output with four-way generation, and
   compare conventional CSV presentation with evidence-governed presentation.
5. Measure decisions changed, unsupported leads caught, missing work identified,
   review time, and willingness to pilot.
6. Make the 30-to-45-day go/no-go decision before expanding models or pages.
