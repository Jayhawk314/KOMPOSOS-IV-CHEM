# Session Execution and Value Decision

Date: 2026-08-12

Authoritative checkout: `C:\Users\JAMES\github-clean\KOMPOSOS-IV-CHEM`

## Outcome

This session moved the project from a broad feature roadmap to a gated product
hypothesis:

> Fast, local materials triage may be useful when it reduces a candidate set,
> preserves physical vetoes and missing evidence, and identifies the next
> calculation or experiment. Evidence governance supports that job; it is not by
> itself proof of market value.

The current four-strategy Crystal Dreamer search is not a demonstrated product
advantage. On the current spent battery targets, simpler known-material retrieval
and transparent family templates match or exceed it. The next value test is
external researcher use, not another internal model.

## Work preserved and pushed

Commit `1eb1d04` (`feat: make evidence-governed triage measurable`) was pushed
to `origin/master`.

It contains:

- tri-state, formula-scoped PFAS screening for generated inorganic formulas;
- removal of inappropriate PubChem/name/SMILES resolution from that path;
- PFAS `ASSESSED_PASS`, `VETOED`, and `NOT_ASSESSED` display/export behavior;
- a versioned fast-triage diagnostic and receipt;
- focused tests, UI copy, current-state synchronization, and the active roadmap.

## Observed behavior

- The Discovery Workbench calls the real inverse designer, charge-balance gate,
  proxy/compatibility path, and synthesis planner.
- Generated inorganic formulas no longer trigger network/name/SMILES PFAS work.
- Formula-only carbon/fluorine co-occurrence abstains because connectivity is
  required; absence of either element can rule a PFAS structure out.
- Crystal Dreamer candidates pass through prediction, ranking, post-filters, and
  a charge-balance gate before return. Definite failures are removed and
  retained in the rejection audit; unassessable candidates remain labeled.

## Development evidence

Fast-triage diagnostic:

- 30 candidates requested;
- 29 unique formulas returned;
- 18 route-library matches;
- post-repair elapsed time: 10.859643 seconds;
- pre-repair diagnostic: 69.630 seconds;
- receipt: `0cb2c460212a2a6255c565b9b364d47341c4f4573339b75e4043ff5d2b5ad271`.

This is one local latency/functional diagnostic. It is not an accuracy result,
external workflow comparison, or service-level guarantee.

Crystal search-mechanics audit:

| Variant | Top-1 window hits | Any top-25 hit | Exact@25 | Near@25 | Gate coverage |
|---|---:|---:|---:|---:|---:|
| Direct labelled filter | 5/9 | 5/9 | 0/9 | 4/9 | 91.9% |
| Known-property retrieval | 7/9 | 8/9 | 0/9 | 7/9 | 97.4% |
| Hidden-composition oracle | 8/9 | 8/9 | 0/9 | 8/9 | 97.6% |
| Random union, one fixed seed | 7/9 | 7/9 | 1/9 | 4/9 | 81.3% |
| Stoichiometry grid | 7/9 | 7/9 | 4/9 | 6/9 | 100.0% |
| Four-strategy union | 7/9 | 7/9 | 2/9 | 6/9 | 93.6% |

The audit now includes a deployable known-property retrieval policy, exact target
windows, name-stable variant seeds, cache-scope tests, scan/computation counts,
and a current JSON artifact. Final receipt SHA-256:
`c167b3f369987b1f9cf8dbbf36934e51a4765daf5a2e955fab6bdde36c66e1a1`.

The 8/9 retrieval result is still same-forward-predictor self-consistency. The
target formula is removed from the candidate pool, but not from every predictor
reference artifact. It is not strict predictive generalization.

## Spent diagnostics and historical claims

- The nine assessed battery targets were already inspected and are spent.
- One random seed is a deterministic control, not a random-baseline distribution.
- The historical 7/9 Crystal Dreamer result remains current as development
  self-consistency, not experimental recovery.
- Direct Materials Project voltage/capacity filtering remains `NOT_ASSESSED`:
  the local MP summary cache has zero rows carrying both labels.
- The hidden-composition nearest-neighbor row is an oracle diagnostic and cannot
  be deployed for an unknown target.

## Verification

- Phase 1 connected regression: 295 passed, with one unrelated `mp_api`
  Pydantic deprecation warning. This overlaps earlier suites.
- Changed discovery pages and application loaded in Streamlit AppTest with zero
  exceptions; the health endpoint returned HTTP 200.
- Phase 2 search audit/designer focused suite: 40 passed.
- Crystal Dreamer loaded in Streamlit AppTest with zero exceptions; one expected
  bare-mode `ScriptRunContext` warning was emitted.
- Expanded ablation completed on the current code in approximately 333 seconds.
- Python compilation and `git diff --check` passed for the modified audit path.

## Product decision

Apply the roadmap's simplify rule:

- do not claim that four-way generation outperforms simple search;
- use known-material retrieval as the conservative search comparison;
- use the small stoichiometry grid as a transparent battery-family template;
- retain four-way generation only as an experimental diversity arm;
- do not add Bayesian/vector/tensor/MLIP machinery to rescue this internal
  comparison;
- do not remove other modules solely because Crystal Dreamer lacks search lift.

The MOF funnel currently has stronger structural-screen evidence than Crystal
Dreamer's property search. Compatibility, cell-interface coverage, PFAS triage,
MP provenance inspection, and synthesis element-balance witnesses remain
distinct functions. Their scientific scopes do not combine into proof that an
eleven-page product has market value.

## Recommended next execution

Phase 3 is now the active gate for 30 to 45 days:

1. Use one battery/interface packet and the existing MOF paired-review packet;
   do not introduce all eleven pages.
2. Obtain at least three cases supplied by independent researchers.
3. For battery search, compare known retrieval, stoichiometry templates, and the
   experimental four-way generator under the same review budget.
4. Separately compare a conventional ranked CSV with the same candidates plus
   physical status, missing evidence, provenance, and next-test requirements.
5. Measure unsupported leads caught, missing work identified, decision changes,
   review time, and willingness to pilot.
6. Stop active product development if researchers will not supply cases, the
   evidence layer changes no decisions, or no group will pilot/integrate it.

Only after external demand selects a workflow should the project add a new data
source or Bayesian representation. If battery voltage is selected, define
charged/discharged phase pairs, working ion, method/fidelity, provenance, and
family/source/time splits before modeling. If MOF review is selected, obtain
chemist assessment and later outcome labels before changing the funnel.
