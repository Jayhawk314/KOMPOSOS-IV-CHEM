# KOMPOSOS-IV-CHEM Definitive Web UI Guide

Version: 2.0
Evidence sync date: 2026-07-17
Interface: Streamlit
Scope: all eleven numbered application pages

## Purpose of this guide

This is the authoritative operating guide for the current audited web
interface. It describes the controls that exist now, the backend each page
calls, how to interpret its output, and which conclusions the evidence does not
authorize.

Definitive means definitive about current software behavior. It does not mean
that every scientific output has been externally or experimentally validated.
When this guide conflicts with an older product, marketing, or feature document,
this guide and CURRENT_STATE.md govern.

## Starting and stopping the application

From the repository root, run:

    python -m streamlit run streamlit_app/app.py

The default local address is:

    http://localhost:8501

Keep the launching terminal open. Press Ctrl+C in that terminal to stop the
server. If port 8501 is occupied, use:

    python -m streamlit run streamlit_app/app.py --server.port 8502

The application loads the numbered Python files under streamlit_app/pages as
separate navigation pages. Streamlit reloads a page when its source changes.

## System-wide interpretation rules

### Screening is not qualification

Outputs prioritize questions, candidates, and tests. They do not replace
laboratory qualification, DFT, engineering safety review, process validation,
or legal advice.

### Physical vetoes survive

When a native bridge identifies a hard physical incompatibility, that veto is
not averaged away by favorable secondary scores.

### Missing evidence survives

If a required physical contact has no native scorer, the UI reports it as
unscored. Missing coverage cannot be converted into a neutral score or hidden
inside an average. A full-stack verdict is withheld when required coverage is
incomplete.

### Calibration is scoped

The pairwise compatibility probability is tied to a 98-row
development/spent-diagnostic cohort. Its recorded out-of-sample ECE is about
0.072 and its Brier score is about 0.049. This does not establish per-domain
calibration and does not calibrate cell-wide or other multi-interface
aggregates.

### Evidence roles matter

The interface distinguishes source records, measured or literature-backed
values, derived checks, screening-model estimates, development benchmarks,
spent diagnostics, and unassessed cases. A development result must not be
reported as a fresh blind result.

### Current blind status

No compatibility dataset is currently blind. Q9 is spent: its initial frozen
score was 32 of 40, and its post-remediation regression score was 35 of 40.
Q10 remains sealed and unscored.

## Navigation summary

| Page | Primary job | Strongest supported output |
| --- | --- | --- |
| 1 - Compatibility Checker | Screen one pair within one material domain | Traceable native pairwise decision |
| 2 - PFAS Scanner | Inventory PFAS signals and triage replacements | Detection evidence and explicit interface coverage |
| 3 - Composition Predictor | Estimate properties from formula | Screening estimate with uncertainty and provenance |
| 4 - Cell Designer | Analyze and rank battery stacks | Covered-interface bottleneck and missing-contact map |
| 5 - Crystal Dreamer | Generate formulas against targets | Physically gated candidate lead set |
| 6 - MP Explorer | Inspect local Materials Project records | Source-versus-derived provenance |
| 7 - MOF Explorer | Screen the curated MOF registry | Rule-based application shortlist |
| 8 - MOF Designer | Generate exact-constraint linkers | Grounded structural funnel ranking |
| 9 - Discovery Workbench | Chain several screening stages | Candidate scorecard with hard vetoes |
| 10 - Advanced Triage | Review charge, proxies, coverage, uncertainty | Mixed-fidelity evidence console |
| 11 - Synthesis Planner | Rank encoded literature routes | Formal element-balance witness where applicable |

## Global interface elements

### Validation banner

Each major feature page renders a validation-status block. Read it before the
result table. It identifies the evidence cohort, current caveats, and whether a
number is a development, spent-diagnostic, or other scoped result.

### Access control

Some analyses call the shared access-control helper before execution. If the UI
asks for authentication or reports that the available use allowance is spent,
that is an application-access state, not a scientific rejection.

### Downloads

Downloads preserve results for inspection. A report or audit-certificate label
does not upgrade a screening output into regulatory, experimental, or external
validation.

## Page 1: Material Compatibility Checker

### Purpose

This page provides a traceable second opinion about whether two registered
materials in the same domain are compatible under the native bridge rules.

### Supported domains

- battery;
- polymer;
- metal;
- ceramic;
- semiconductor;
- glass.

Both selected materials come from the same domain registry. The page does not
perform an arbitrary cross-domain pair query.

### Controls

1. Domain selects the native material bridge.
2. Material A and Material B select two registered entries.
3. Trigger Active Verification optionally requests a GROMACS workflow.
4. Check Compatibility runs the pairwise workflow.

The two materials must be different.

### Active Verification requirements

The molecular-dynamics option needs real GROMACS structure and topology inputs.
Depending on the selected mode, the expander requests an input directory or
specific GRO, TOP, MDP, and optional index paths, plus runtime conditions.
Missing inputs return a no-verdict readiness state. They do not create a
simulated compatibility result.

### Primary result

The Pairwise Decision and Derived Constraint Diagnostic shows two related views:

- Pairwise bridge decision: native component scores, physical vetoes, ensemble
  metadata, and scoped calibration.
- Derived constraint summary: logical rules constructed from those same native
  component scores.

These are not independent experiments. Agreement between them means internal
workflow consistency, not two independent confirmations.

### Verdict language

- AGREE: the native score passes and the derived rules contain no veto.
- HOLLOW: the native score passes but a derived hard constraint vetoes it.
- ORPHAN: the derived summary has no hard veto while the native score remains
  below threshold.
- REJECT: both views reject the pair.

These state names describe internal reasoning structure. They are not laboratory
outcomes.

### Additional outputs

- score breakdown by native component;
- calibration metadata when applicable;
- ensemble votes and evidence-quality labels;
- shared-partner, transport, or equivalence evidence when the workflow finds it;
- raw JSON score data;
- human-readable Markdown report;
- machine-readable JSON audit trail.

### Molecule Constraint Search

The bottom section searches the registered molecular library by exact
non-hydrogen atom count, optional class, and excluded elements. It returns known
library entries only. It does not generate novel molecules.

### Correct use

Use the page to identify a likely incompatibility, inspect the reason, find a
possible substitute relationship, or decide what interface needs testing next.
Do not call its probability a universal chemistry probability or transfer it to
a multi-interface system score.

## Page 2: PFAS Screening and Replacement Triage

### Purpose

This page performs first-pass PFAS inventory and ranks possible replacements
within an application context while preserving interface coverage.

### Single Check controls

- material domain and registered material, or a custom material name;
- application context;
- adjoining materials, one per line;
- Check PFAS Status.

Detection may come from an exact registry match, resolved brand or synonym,
heuristic pattern, or available structural rule. The page identifies the
detection path so an exact match is not confused with a heuristic flag.

### Replacement interpretation

Each PFAS-free replacement is screened against the requested adjoining
materials when a native scorer exists. Results expose:

- number of requested contacts;
- number of scored contacts;
- coverage fraction;
- scored interface values;
- missing contacts;
- full bottleneck only when coverage is complete.

With incomplete coverage, the ranking uses a coverage-aware partial score and
does not display a full-stack probability. Zero coverage is not converted into
0.5 or another neutral-looking value.

### Batch Scan

Batch mode accepts one material per line and screens a bill of materials. It
separates detected, apparently clean, heuristic, and unknown entries. Unknown
means manual review is required, not PFAS-free.

### Screening Report

The report generator accepts the demo battery bill of materials or a custom
list using name, function, and optional quantity. It produces detections,
replacement triage, qualitative regulatory context, follow-up actions, raw
data, and a downloadable PDF.

The report is not a legal compliance determination or a filing-ready
certificate. Verify current primary regulatory sources for the substance,
product, use, jurisdiction, and date before making a compliance statement.

### Registry

The registry area exposes the curated PFAS list and, when locally available,
the EPA structural dataset with search and family or molecular-weight filters.

### Correct use

Use this page to build an inventory, locate uncertain names, prioritize supplier
questions, and identify replacement interfaces that require testing. Do not
claim that a ranked candidate is a qualified drop-in substitute.

## Page 3: Composition Predictor

### Purpose

This page estimates material properties from a formula or supported shorthand
and shows the evidence neighborhood behind the estimate.

### Inputs and outputs

The formula control supports known formulas, common shorthands, and custom
formulas. Output can include:

- formula-derived property estimates;
- uncertainty intervals and confidence;
- uncertainty tier;
- nearest known materials and distances;
- predicted structure type;
- optional structure derived from the local Materials Project cache;
- stability and synthesizability fields;
- downloadable result data;
- raw prediction data.

### Formation-energy evidence

The current strict-formula leave-one-out development benchmark contains 179
entries:

- MAE 0.416 eV per atom;
- RMSE 0.552 eV per atom;
- median absolute error 0.340 eV per atom;
- deployed interval coverage approximately 50, 79, and 95 percent.

The historical 0.304 MAE headline is superseded for this executable path.
Formation-energy intervals have a recorded conformal calibration artifact.
Other property intervals remain heuristic unless separately documented.

### Uncertainty tiers

- Categorical Ground Truth;
- Dense Interpolation;
- Moderate Extrapolation;
- Sparse Discovery.

The tier communicates neighborhood support. It does not by itself establish
accuracy for an individual formula.

### Strict LOO Development Diagnostic

This control removes the selected formula and same-formula anchors before
prediction and compares the result with the known reference value. It is useful
for self-exclusion diagnosis. Because the data and errors were already inspected
during development, it is not a fresh blind or external-generalization test.

### Composition interpolation

The final section interpolates between two selected compositions. Treat the
result as a mathematical screening interpolation, not proof of a stable solid
solution or synthesizable phase.

## Page 4: Solid-State Cell Designer and Battery Optimizer

### Purpose

This page maps a battery stack into required physical contacts, scores the
contacts for which native cross-domain functors exist, and keeps missing
contacts visible.

### Manual Designer components

The manual configuration contains six distinct components:

1. cathode;
2. anode;
3. solid or liquid electrolyte;
4. polymer binder;
5. cathode current collector;
6. anode current collector.

The preset control fills these fields with a known example. Every field remains
editable. Cathode and anode are separate roles, as are the two current
collectors.

### Advanced controls

- scoring mode;
- viability threshold;
- optional Active Verification for the covered bottleneck;
- GROMACS inputs when Active Verification is enabled.

The scoring modes combine only scored native interfaces. They do not manufacture
scores for missing contacts.

### Interface analysis

The page builds the physical adjacency map and displays:

- expected required interfaces;
- interfaces with available native scorers;
- interface scores and explanations;
- scored-interface coverage fraction;
- unscored physical interfaces;
- lowest-scored covered interface;
- workflow warnings.

If one or more required contacts are unscored, the page withholds a full-cell
viable verdict. The covered bottleneck remains useful, but it is not evidence
that the unscored contacts work.

### Battery Optimizer

The optimizer supports solid or liquid electrolyte pools, optional PFAS-free
filtering, fixed electrolyte or cathode collector, and optional discovery from
the local Materials Project cache.

Role pools are physically separated:

- aluminum foil is not a cathode;
- copper foil is not an anode;
- cathodes and anodes come from their appropriate battery roles.

Optional discovery searches the local cache for cathode refinements. Discovery
results are labeled and remain screening candidates.

### Energy-density interpretation

The reported objective is cathode-active voltage times cathode capacity. It is
not pack-level Wh/kg and does not include all inactive mass, packaging, cycle
life, thermal behavior, dendrites, manufacturing yield, or cost.

### Correct use

Use this page to identify the weakest covered contact, expose absent interface
models, compare constrained stacks, and decide which missing contact needs
experimental or literature evidence.

## Page 5: Crystal Dreamer

### Purpose

Crystal Dreamer searches formula space for candidates matching weighted
property targets.

### Target controls

Each target has:

- property name;
- optional lower bound;
- optional upper bound;
- weight.

Targets with neither lower nor upper bound are skipped.

### Constraint controls

- required elements;
- excluded elements;
- material domain;
- maximum candidates;
- minimum synthesizability score;
- optional thermodynamic-stability requirement.

### Generation and ranking

The engine uses perturbation, interpolation, substitution, and stoichiometry
variation, then calls the forward predictor and configured gates. Every returned
candidate is checked against the gates; there is no unchecked tail after an
initial batch.

The page reports candidate count, scores, predicted properties, top pick,
structure information when available, derived structure provenance, and
strategy distribution.

### Evidence boundary

Candidate scores inherit the limits of the formula-based forward predictor.
A 2026-08-09 strict leave-one-anchor-out development run completed against the
103,850-entry local database: 7/9 top-ranked candidates landed in the target
property windows, 2/9 targets were recovered exactly within the top 25, and 6/9
were compositionally near within the top 25. Si was skipped because the forward
predictor supplied no voltage/capacity target. Charge balance was assessed for
2,527 of 2,700 candidate decisions (93.59%); 102 definite failures were vetoed
and 71 unassessable candidates were retained without physical clearance. This is
self-consistency against the same forward predictor and is development/spent
evidence, not predictive accuracy, experimental recovery, or a blind result.
Receipt: `audit/crystal_recovery_report.json`.

Every retained lead row is now labeled `ASSESSED_PASS` or `NOT_ASSESSED`.
Definite failures are labeled `VETOED`, excluded from the lead list, and shown
in a separate rejection view. The CSV audit download includes both retained and
rejected rows with their disposition; the JSON download preserves the full
nested result and aggregate coverage.

### Correct use

Use Crystal Dreamer to create a small, physically filtered lead set. Do not
describe its top result as a discovered material, stable phase, or validated
synthesis target without the corresponding external evidence.

## Page 6: Materials Project Explorer

### Purpose

This page is the provenance and neighborhood inspection surface for the local
Materials Project cache.

### Available modes

- smart material search;
- structure derivation from a formula;
- nearest Materials Project search;
- dataset statistics;
- instructions for enabling the local cache.

When present, the current local cache contains approximately 103,644 entries.
The page is not a live Materials Project API browser.

### Structure derivation

Structure derivation reports fields such as predicted or source structure,
lattice parameters, volume per atom, confidence, and provenance. Read the
provenance field closely:

- source Materials Project values are records from the cache;
- interpolated, nearest-neighbor, or KOMPOSOS-derived values are estimates.

A source identifier does not imply that every displayed neighboring field came
directly from that source.

### Missing-data behavior

If the cache or search engine is unavailable, the page falls back to reduced
local capability and displays enablement instructions. Missing data is an
availability state, not a negative material result.

## Page 7: MOF Explorer

### Purpose

This page screens the 30-entry curated MOF registry against operating
conditions.

### Application Screening controls

- target application;
- dry, humid, aqueous, acidic, or basic environment;
- operating temperature;
- operating pressure;
- optional target-molecule diameter;
- required water stability;
- required acid stability.

The molecule-diameter value of zero disables pore-size filtering.

### Outputs

- suitable and unsuitable counts;
- best rule-based score;
- ranked MOF table;
- per-MOF detail;
- database overview;
- result download.

Physical conditions such as pore access or required stability can act as vetoes.

### Evidence boundary

The application scorer is a compact rule-based screen over the curated registry.
It is not the linker-generation funnel and does not inherit that funnel's AUROC
or recall. A suitable result means suitable under the encoded registry fields
and rules, not experimentally validated for the requested process.

## Page 8: MOF Linker Designer

### Purpose

This page deterministically enforces user constraints during linker generation
and then ranks candidates through a grounded structural funnel.

### Primary controls

- exact heavy-atom count from 5 through 60;
- number of candidates to generate;
- application context;
- required donor elements;
- excluded elements.

Hydrogens are not included in the heavy-atom count.

### Legacy controls

The optional five legacy categorical descriptors are unvalidated for novel
linkers. Requiring all five to agree is off by default. Allowing legacy HOLLOW
states is explicitly exploratory. These descriptors are not the primary
evidence for the candidate ranking.

### Directed generation controls

- functional-group substitution weight;
- backbone-modification weight;
- template-generation weight;
- optional seed SMILES;
- required functional groups.

A pinned seed restricts generation to derivatives of that molecule and disables
the template path. When the seed heavy-atom count differs from the target,
backbone modification needs nonzero weight to resize it.

Required functional groups are hard constraints. Adding several constraints can
reduce the candidate yield substantially.

### Grounded funnel

The primary funnel checks:

1. chemical sanity;
2. at least two recognized coordinating sites;
3. synthetic-accessibility score;
4. donor geometry;
5. novelty relative to known-linker coordinates.

The result view reports where a rejected candidate stopped and distinguishes
informational drug-filter alerts from MOF-linker vetoes. It now preserves four
assessment states: ASSESSED_PASS, PARTIAL_PASS, VETOED, and NOT_ASSESSED.
PARTIAL_PASS means the implemented funnel retained the candidate but 3D donor
geometry could not be assessed; missing geometry is not presented as a full
pass.

For researcher review, the page exports the same ranked candidates in two
forms: a conventional CSV and an evidence-governed CSV containing funnel
status, scope, soft flags, novelty, missing evidence, and explicit experimental
NOT_ASSESSED status. The JSON audit export preserves candidate objects and the
exact funnel decisions. The paired CSVs support a controlled presentation
study; they do not create independent chemistry evidence.

### Reproduced benchmark

The 2026-07-17 audit reproduced:

- seed set: 253;
- held-out real linkers: 423;
- gold-tier linkers: 120;
- held-out pass-all recall: 0.9433;
- AUROC against raw-generator decoys: 0.8843;
- exact-22 subset size: 20;
- exact-22 recall: 0.95;
- exact-22 AUROC: 0.9013.

In the audited generation run, 233 candidates were generated, 60 passed all
funnel gates, and 14 were both novel by the encoded coordinate and pass-all.

### Evidence boundary

The benchmark tests whether the structural funnel retains known synthesized
linker-like molecules while separating raw generator decoys. It does not show
that a newly generated candidate was synthesized, coordinates a chosen metal,
forms a desired topology, is nontoxic, is conductive, or performs in an
application.

## Page 9: Discovery Workbench

### Purpose

This page chains several existing screening engines into one composition-first
pipeline. Its value is orchestration and evidence visibility, not an additional
independent predictor.

### Configuration stages

1. Target Properties: add properties and optional minimum or maximum values.
2. Element Constraints: require or exclude elements and set a maximum element
   count.
3. Compatibility Context: select a registered reference material and interface
   role.
4. Pipeline Limits: set the maximum candidate count.

### Pipeline stages

The service performs:

- inverse formula design;
- PFAS screening;
- oxidation-state and charge-balance feasibility where assessable;
- proxy selection for a registered material when needed;
- compatibility screening in the requested context;
- available synthesis-route lookup;
- integrated confidence and pipeline-depth calculation.

### Hard veto behavior

A definite charge-balance failure is a hard veto. The previous placeholder that
marked every candidate as witnessed has been removed. An unassessable formula
does not receive a positive charge-balance verdict.

PFAS detection and other configured safety vetoes remain visible in the
candidate record.

### Proxy behavior

Native compatibility bridges generally require registered material names. A
novel formula may therefore be represented by its nearest registered proxy.
The workbench records:

- proxy name;
- actual proxy distance;
- native interface context;
- scores produced;
- missing or limited applicability.

The proxy score describes the analog under the native bridge. It is not direct
measurement of the generated formula.

### Outputs

- integrated candidate scorecard;
- formula and design score;
- overall confidence and pipeline depth;
- hard and safety vetoes;
- compatibility score and metadata;
- synthesizability and precursor fields;
- candidate deep dive and audit trail.

### Correct use

Use this page to narrow a search and identify which candidate deserves a
direct pairwise check, higher-fidelity calculation, literature search, or
experiment. Do not treat overall confidence as a calibrated probability of
real-world success.

## Page 10: Advanced Triage Workbench

### Purpose

Advanced Triage exposes the mixed fidelity of candidate assessment more
explicitly than Page 9.

### Triage controls

- weighted target properties and bounds;
- charge-balance gate toggle;
- multi-domain interface-check toggle;
- reference electrolyte;
- reference collector;
- required elements;
- triage batch size.

### Charge-balance gate

The gate uses pymatgen oxidation-state feasibility. Its result can be:

- pass;
- fail and hard veto;
- unassessable with no verdict.

This is not an independent ZFC proof. A pass establishes only that an oxidation
state assignment is feasible under the check.

### Multi-domain context

Each surviving candidate is placed in a reference interface system. When native
bridges require a registered material, the candidate uses a visible proxy.
The output reports:

- proxy identity and distance;
- expected interfaces;
- scored interfaces;
- missing interfaces;
- coverage fraction;
- covered bottleneck.

Incomplete required coverage prevents full-system wording. Pairwise calibration
is not applied to the multi-interface aggregate.

### Uncertainty display

The candidate deep dive shows central estimates, lower and upper bounds,
confidence, charge metadata, proxy information, and interface evidence.
Formation-energy intervals are separately calibrated. Bounds for other
properties remain heuristic unless a feature-specific status says otherwise.

### Correct use

Use this page as an evidence console for deciding why a candidate advanced,
which premise is weakest, and which higher-fidelity action is next. It is not a
wet-lab verification layer.

## Page 11: Synthesis Planner

### Purpose

The planner ranks encoded literature routes for 24 curated targets and checks
formal element conservation where the route representation supports it.

### Control

Select a target material and press Plan synthesis.

### Route outputs

For every available route the page can display:

- composite score;
- feasibility score;
- cost score;
- time score;
- safety score;
- precursor cost and availability;
- total time;
- bottleneck step and encoded success probability;
- process steps, conditions, equipment, and hazards;
- citation;
- stoichiometry status;
- formal balanced-reaction witness.

### Stoichiometry states

- BALANCED: an element-conserving coefficient assignment exists.
- BALANCED UNUSED INPUTS: a witness exists without consuming every listed input.
- UNBALANCED: no witness exists for the encoded route and the route is vetoed.
- SKIPPED: the target is a composite or mixture not represented by a single
  formal formula.
- UNAVAILABLE: Z3 was not available, so no balance verdict was produced.

### Reproduced audit

The current library contains 24 targets. In the 2026-07-17 audit:

- 17 routes received formal element-balance witnesses;
- seven composite or mixture targets were explicitly skipped;
- zero checked routes were unbalanced.

### Evidence boundary

The Z3 witness proves element conservation for the encoded equation and allowed
auxiliary species only. It does not establish:

- the cited paper's exact reaction equation;
- charge or electron balance unless explicitly encoded;
- redox plausibility;
- reaction mechanism;
- kinetics;
- yield;
- phase purity;
- scale-up success.

Use the planner as a structured route library and formal transcription check,
then consult the cited source and domain experts.

## Downloads and report semantics

### Markdown and JSON compatibility reports

These preserve the native component scores, verdict, evidence chain, and report
identifier. JSON is intended for machine replay and audit storage. Markdown is
intended for human review.

### PFAS PDF

The PDF records screening inputs, detections, qualitative context, and
replacement triage. It is not a regulatory certificate.

### Candidate CSV or JSON bundles

MOF and workbench downloads preserve generation controls and candidate evidence.
They do not convert a generated structure into a synthesized material.

## Current evidence ledger

| Capability | Current recorded evidence | Interpretation |
| --- | --- | --- |
| Pairwise compatibility | 41 of 41 development regression | Code-path regression, not blind accuracy |
| Compatibility Q9 | 32 of 40 initial; 35 of 40 after remediation | Spent diagnostic |
| Pairwise calibration | 98 development/spent rows; ECE 0.072; Brier 0.049 | Cohort-scoped reliability evidence |
| Formation energy | Strict LOO n=179; MAE 0.416; RMSE 0.552 | Screening-grade development result |
| Formation intervals | Deployed coverage 50, 79, 95 percent | Recalibrated interval behavior |
| MOF linker funnel | AUROC 0.8843; held-out recall 0.9433 | Structural funnel evidence |
| Exact-22 funnel subset | n=20; AUROC 0.9013; recall 0.95 | Small exact-count subset |
| Synthesis balance | 17 witnessed; seven skipped; zero checked failures | Element conservation only |
| Cell optimizer | Role pools, discovery, and coverage regression tested | Partial-interface orchestration |

No row in this table is a blanket product-validation claim.

## Reproducibility commands

Run commands from the repository root.

### Prediction and artifact drift

    python -m audit.prediction_drift --baseline audit/baselines/prediction_baseline_2026-07-17.json

The expected current state is AGREE with receipt:

    fc00c0ae46f7d4f879ab2fc590a0645ada0c5667e2e579ea5787e1b1ad184357

AGREE means the current executable metrics and named artifact hashes match the
frozen development baseline. It is not experimental validation.

### Formation accuracy

    python audit/run_predictor_accuracy.py

### Battery optimizer

    python audit/run_battery_optimizer_audit.py

### PFAS replacement screen

    python audit/run_pfas_replacement_audit.py

### Registered chemistry audit

    python audit/chem_audit.py

### Focused repaired-boundary tests

    python -m pytest -q --import-mode=importlib audit/tests/test_prediction_drift.py api/tests/test_monitoring_export.py battery_bridge/tests/test_optimizer.py cross_bridge/tests/test_multi_domain.py discovery/tests/test_workbench_service.py pfas_bridge/tests/test_cell_replacement_coverage.py pfas_bridge/tests/test_compatible_replacements.py mof_bridge/tests/test_mof_designer.py tests/test_oracle_strategies.py

The 2026-07-17 run passed 107 tests with one dependency deprecation warning.

## Common failure states

### Page loads but analysis does not run

Check the access-control state and launching terminal. Authentication or use
allowance is separate from scientific validity.

### Port already in use

Launch on port 8502 or stop the existing Streamlit process.

### Materials Project features unavailable

Confirm the local cache exists. Pages 3 and 6 should degrade visibly rather than
invent source data.

### Active Verification returns no verdict

Provide valid GROMACS inputs and verify the local executable. Missing inputs are
not evidence for compatibility or incompatibility.

### A cell has a good score but no full verdict

Inspect Unscored Physical Interfaces. The score summarizes covered contacts
only. Obtain a native scorer, source evidence, simulation, or measurement for
each missing required contact.

### PFAS replacement has low coverage

Add the actual adjoining materials and check whether native pair scorers exist.
A PFAS-free label alone does not establish application compatibility.

### A generated candidate disappears

Inspect target bounds, excluded elements, hard gates, required functional
groups, charge-balance status, and candidate limit. Rejection by a hard gate is
expected behavior.

### A synthesis route is skipped

Composite and mixture targets may lack a single formal product formula. SKIPPED
means the element-balance encoding is inapplicable, not that the literature
route failed.

## Recommended operating workflow

1. State the decision and required physical interfaces.
2. Run the narrowest relevant page.
3. Read validation status before interpreting a number.
4. Inspect vetoes, missing coverage, proxy distance, and uncertainty.
5. Download the evidence artifact.
6. Reproduce the named benchmark or drift receipt when making a public claim.
7. Escalate the weakest premise to literature review, DFT, simulation, or
   experiment.
8. Record the outcome so future calibration can use real consequences rather
   than development labels alone.

## Source-of-truth documents

- CURRENT_STATE.md: concise current scientific state.
- docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md: feature-by-feature evidence audit.
- docs/PROVENANCE_CONTRACT_PROJECT.md: claim receipts and Noesis drift contract.
- audit/dataset_registry.json: compatibility dataset roles and blind status.
- streamlit_app/validation_status.py: evidence text rendered inside the UI.

## Final interpretation

The interface is most useful when a missing answer remains missing. Its central
contract is that physical vetoes and evidence gaps remain visible through a
composed workflow. Use its positive results to prioritize work, its negative
results to inspect physical failure modes, and its unassessed results to locate
the next evidence that must be obtained.
