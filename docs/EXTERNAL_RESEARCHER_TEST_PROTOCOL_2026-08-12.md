# External Researcher Test Protocol

Date: 2026-08-12

Status: recommended external-validation protocol. Nothing in this document
authorizes sending messages, publishing private responses, opening sealed
compatibility labels, or presenting screening output as experimental validation.

## Executive recommendation

Run two tests, in this order:

1. **MOF expert falsification and evidence-presentation test.** This is the most
   ready external test because the same five candidates already exist in
   conventional and evidence-governed conditions, the structures are rendered,
   and the supporting funnel benchmark reproduces.
2. **Researcher-supplied battery/interface cases with sealed outcomes.** This is
   the more direct test of the proposed product value: whether explicit vetoes,
   missing contacts, and next-test guidance change a real decision.

Do not begin with a generic tour of all eleven pages. Do not build a Bayesian
model, ingest another database, or tune the current candidate ranking during the
test window. The purpose is to learn whether an external researcher changes a
decision or supplies a real case, not to make the internal numbers look better.

The PFAS workflow may have a strong recurring user need, but its current private
demo report must be regenerated before use. The July 21 report contains stale
regulatory language and encoding defects. The provenance packet is suitable for
adversarial protocol review, but it is not the first test of chemistry-product
value.

## Evidence state used to choose this order

### Observed packet behavior

- The MOF A and B CSV files each contain five rows.
- Candidate IDs, formulas, SMILES, rank scores, and order match exactly across
  conditions.
- Condition B adds evidence role, implemented-gate status, experimental
  `NOT_ASSESSED`, missing evidence, geometry status, novelty, and donor-count
  review fields.
- The recorded A and B SHA-256 hashes match the private A/B receipt.
- The existing full structure grid renders 15 candidates and displays funnel
  scores. It is not a neutral five-candidate attachment for the controlled A/B.
- The A and B Markdown tables do not preserve exactly the same common columns;
  the CSVs do. Use newly generated matched presentation files for a controlled
  study rather than sending the Markdown tables as-is.

### Reproduced development evidence

The current executable MOF funnel benchmark was rerun on 2026-08-12:

- frozen seed records: 253;
- held-out real linkers: 423;
- held-out pass-all recall: 0.9433;
- AUROC versus raw-generator decoys: 0.8843;
- exact-22 held-out linkers: 20;
- exact-22 recall: 0.95;
- exact-22 AUROC versus raw-generator decoys: 0.9013;
- generated decoys/candidates in the benchmark: 233;
- passed all implemented gates: 60;
- novel-coordinate and passed: 14.

Command:

    python -m mof_bridge.benchmark.run

Frozen report SHA-256:

    a091d9001a72854d409ca245938605ad4e949968cd762733da77cc3a648c5cfa

This supports structural funnel behavior against a recorded real-linker corpus
and constructed decoys. It does not support synthesis, correct metal
coordination, topology, phase formation, stability, toxicity, conductivity, or
application performance for any generated molecule.

### Spent and not-yet-assessed evidence

- The five MOF rows were chosen during model pre-review and are spent
  development material.
- No row has a manual chemist review.
- Every row's experimental status is `NOT_ASSESSED`.
- The study can test expert falsification and presentation usefulness. It cannot
  retrospectively turn these five candidates into a blind chemistry benchmark.
- The Crystal Dreamer battery target set is also spent and same-predictor. New
  battery value evidence must come from researcher-supplied cases.

## Keep four questions separate

Do not treat one reply as answering all of these:

1. **Technical credibility:** does a chemist find an obvious missing failure
   mode in the MOF funnel?
2. **Presentation value:** does evidence-governed output produce a better review
   than a conventional rank table?
3. **Workflow value:** does the tool change which calculation, interface, or
   experiment a researcher performs next?
4. **Adoption value:** will a group supply its own artifact and run or integrate
   a pilot?

The first MOF outreach can answer question 1. A randomized presentation study
addresses question 2. Researcher-supplied battery or MOF cases address question
3. Only a concrete second case, pilot, or integration answers question 4.

## Test 1A: MOF expert falsification

### Purpose

Find missing chemical failure modes before spending effort on DFT, synthesis
planning, or model expansion.

This is the recommended first contact because it asks for criticism rather than
endorsement and can be answered in one sentence.

### Recipient profile

Prioritize researchers who have personally worked on at least one of:

- MOF or coordination-polymer synthesis;
- linker design and functionalization;
- reticular chemistry and topology;
- metal-node/linker compatibility;
- solvothermal phase formation;
- experimental failure analysis for porous materials.

Postdoctoral researchers, staff scientists, facility scientists, and senior
graduate researchers may give more direct technical feedback than prominent
principal investigators. Expertise matters more than prestige.

Exclude from the first analysis cohort anyone who:

- already saw both packet conditions;
- helped choose the five candidates;
- has only general materials or machine-learning expertise without relevant
  linker/coordination experience;
- cannot tell whether their response may be retained in de-identified form.

### What to send

Send the evidence-governed five-candidate condition for this falsification-only
test, not the 15-row packet:

1. a corrected, matched five-candidate evidence table derived from
   `RESEARCHER_REVIEW_B_EVIDENCE_2026-08-09.csv`;
2. a new neutral image plate containing only FRESH22-008, -004, -006, -001,
   and -002 in that order;
3. the short email in
   `.private_outreach/01_mof_chemist/SEND_THIS_RESEARCHER_REVIEW_2026-08-09.md`.

The neutral plate should show only candidate ID, structure, and formula. It
should not show funnel score, rank interpretation, status, or model concerns.
Use the same neutral plate in every condition.

Do **not** attach initially:

- the current 15-candidate grid;
- `MODEL_PRE_REVIEW_2026-07-19.md`;
- the generation receipt;
- the full 15-row table;
- the legacy `kulik_22atom_linkers_100.csv`;
- both A and B conditions.

The model pre-review would anchor the reviewer toward concerns already proposed
by the model. Offer it only after the primary response has been recorded.

### Exact first question

> Which candidate would you reject first, and what chemical failure mode is the
> software missing?

Optional second question after they answer:

> Which candidate, if any, is worth one higher-fidelity calculation, and what
> calculation should come first?

Do not ask whether the system is innovative, impressive, or publishable. Those
questions invite politeness rather than falsification.

### Contact cadence

1. Send one individualized message with one artifact and one question.
2. If there is no reply, send one brief reminder after 7 to 10 days.
3. Close the contact after 14 to 18 days without another reminder.
4. Never add a non-responder to the result denominator after changing the email,
   attachment, or question without recording the new version.

### What to record

Assign a private reviewer ID. Preserve:

- expertise category and approximate years of relevant work;
- packet version and file hashes;
- date sent, reminder date, and response date;
- exact verbatim response;
- first rejected candidate;
- stated chemical failure mode;
- requested missing calculation or experiment;
- candidate selected for next work, including `none`;
- confidence from 1 to 5, if supplied;
- whether the person will review a researcher-supplied follow-up case;
- permission level: private only, de-identified aggregate, or quotable.

Do not put names, email addresses, private company data, or verbatim responses in
Git. Store them only under the Git-excluded private outreach directory.

### Failure-mode coding taxonomy

Code after preserving the original words. Allow multiple codes and an open
`OTHER` field:

- donor availability, protonation, or donor overcount;
- steric access to a donor;
- metal/node incompatibility;
- linker geometry or topology mismatch;
- excessive conformational flexibility;
- solubility or precursor availability;
- synthesis-route implausibility;
- intramolecular reaction, anhydride formation, or decomposition;
- competing phase or coordination polymer;
- charge, counterion, or oxidation-state issue;
- framework or operating-condition stability;
- duplicate/known compound or insufficient novelty;
- application-specific performance requirement;
- no obvious rejection.

Do not tune the funnel after the first comment. Collect a wave, freeze the raw
responses, then decide whether a repeated failure mode justifies a new gate.

### Technical go/stop rule

Continue MOF funnel work only if at least one of these occurs:

- two independent chemists identify the same missing, computable failure mode;
- a chemist supplies a real linker set, failed synthesis, or metal/node question
  for a prospective test;
- a chemist identifies a candidate worth a named next calculation and explains
  why the simpler implemented gates could not decide it.

Stop candidate-quality marketing and redesign the funnel if several independent
chemists reject most or all five for the same obvious generator artifact.

## Test 1B: controlled evidence-presentation study

### Purpose

Test whether evidence fields help a researcher identify unsupported
recommendations and missing follow-up work. This tests the project's proposed
differentiator more directly than another predictor benchmark.

### Do not mix this with Test 1A

Test 1A deliberately shows the richer evidence condition to maximize useful
falsification. Test 1B requires random assignment. A response cannot belong to
both primary analyses unless that was declared before contact.

### Prelaunch packet repair

Create two matched, read-only one-page files:

- **Condition A:** ID, neutral structure, formula, SMILES, rank, and score.
- **Condition B:** every Condition A field plus evidence role, implemented-gate
  status, experimental `NOT_ASSESSED`, plausible donor count and review status,
  geometry status, novelty scope, and missing-evidence list.

The five candidates and their order must remain identical. Fonts, structure
size, page count, introductory language, and question wording should match.
Condition B may be longer only because the tested evidence is present.

Recompute SHA-256 hashes and write a new private packet receipt. Do not overwrite
the August 9 receipt; create a new version.

### Pilot and sample

Run two usability pilots first. Their only purpose is to find layout ambiguity,
not to estimate an effect. Exclude pilot participants from the main analysis.

For the main pilot:

- minimum useful target: 8 completed reviews, balanced 4/4;
- preferred target: 12 to 20 completed reviews, balanced by condition;
- interpret results descriptively; the cohort is too small for a broad market or
  causal claim even if a p-value happens to be small.

If fewer than eight researchers can be recruited, use a randomized-order delayed
crossover as qualitative evidence: collect the first response, lock it, reveal
the alternate condition, then ask what changed. Carryover prevents treating that
as a clean between-group effect.

### Randomization

Before sending the first main-study packet:

1. assign pseudonymous reviewer IDs;
2. stratify only by synthesis-heavy versus computational-heavy MOF experience;
3. use balanced block randomization within each stratum;
4. freeze the assignment table and its hash;
5. never change condition based on the person, expected friendliness, or prior
   response behavior.

Keep the assignment table private. The person coding response quality should not
see condition labels until primary coding is frozen, if a second helper is
available.

### Questions shown to both conditions

1. Which candidate would you reject first, and why?
2. What missing chemical check matters most before DFT or synthesis work?
3. Which candidate, if any, merits the next calculation?
4. What exact calculation or experiment should be next?
5. How confident are you in that decision, from 1 to 5?
6. How difficult was this packet to review, from 1 to 5?

Record elapsed review time when practical, but do not install invasive tracking.
Self-reported start/end time is sufficient for this pilot.

### Primary outcomes

Freeze the rubric before unblinding:

1. **Actionable failure-mode quality**
   - 0: no failure mode;
   - 1: generic concern with no candidate-specific mechanism;
   - 2: candidate-specific mechanism or missing check;
   - 3: candidate-specific disqualifying mechanism plus a named verification.
2. **Next-step specificity**
   - 0: no next step or generic "do DFT/test it";
   - 1: named calculation/measurement without a decision criterion;
   - 2: named calculation/measurement and what result would change the choice.
3. **Unsupported advancement**
   - yes: recommends synthesis/application advancement while treating an
     unassessed requirement as cleared;
   - no: preserves the missing requirement or chooses no advancement.

Secondary outcomes:

- review time;
- confidence;
- burden rating;
- number of distinct missing checks found;
- whether the alternate condition changes the choice after the primary response;
- willingness to submit an own case.

Report raw numerators and denominators. For a small pilot, emphasize effect
direction and response examples with permission, not significance testing.

### Presentation-value decision

Evidence presentation is promising only if Condition B improves actionable
failure modes or next-step specificity and does not create enough burden to make
reviewers abandon the packet. Confidence alone is not success; increased
confidence with no better reasoning may be harmful.

The product hypothesis fails this test if evidence fields mostly repeat what the
chemist already knows, do not change any next step, or make the packet too slow
to use.

## Test 2: researcher-supplied battery/interface cases

### Purpose

Test the actual fast-triage job: does explicit scored coverage, missing contact
coverage, proxy distance, and veto status change which interface a researcher
investigates next?

The existing Crystal Dreamer target-window results cannot answer this. Use new
cases chosen by external researchers.

### Repair the private packet first

Do not send the current materials-engineer evidence file unchanged. It predates
the current compatibility registry state. Replace its compatibility section with:

- Q11 first blind: 23/36 correct among evaluated pairs, four no-verdicts,
  63.9% accuracy, MCC 0.278, Brier 0.279, ECE 0.177;
- Q11 is now spent after remediation;
- Q12 is current blind and unscored;
- Q10 remains sealed and unconsumed;
- development regression remains 41/41;
- pairwise calibration does not transfer to a cell-wide aggregate.

Do not score Q12 merely to make the outreach packet more persuasive.

### Two-envelope intake

Ask the researcher to separate the case into two files or messages.

**Envelope A: inputs available before the outcome**

- material names or abstract labels;
- component roles;
- physical adjacency/contact map;
- temperature, atmosphere, solvent/electrolyte, pressure, and relevant cycling or
  dwell conditions;
- coatings, surface treatments, and approximate state of charge when relevant;
- which information may be retained;
- the decision they would normally make next.

**Envelope B: outcome or known failure**

- known compatible/incompatible outcome;
- failed interface or observed degradation;
- evidence source: experiment, field return, literature, simulation, or expert
  judgment;
- confidence and ambiguity;
- whether the outcome may be revealed after the prediction receipt is frozen.

Do not open Envelope B until the input normalization, command, code revision,
dataset role, and output receipt are frozen. If the researcher cannot separate
the outcome, label the case `EXTERNAL_SPENT`, not blind.

### Baseline decision before showing KOMPOSOS

Ask the researcher:

1. Which interface would you investigate first?
2. Which interface do you already consider safe enough to defer?
3. What evidence is missing?
4. How confident are you, from 1 to 5?
5. How long would this triage normally take?

This is the practical comparison. The system does not need to outperform DFT;
it needs to improve the decision made before expensive work.

### Run and freeze

For every case, preserve:

- raw input hash and normalized-input hash;
- code revision;
- command or UI action receipt;
- native pair scores and vetoes;
- expected, scored, and unscored contacts;
- coverage fraction and completeness;
- missing interfaces;
- proxy identity and distance, when used;
- `ASSESSED_PASS`, `VETOED`, or `NOT_ASSESSED` for each required check;
- recommended next calculation or experiment;
- runtime and manual preparation time.

Do not apply pairwise probability calibration to a multi-interface aggregate.
Do not convert zero coverage to 0.5. Missing required contacts must block a
full-stack conclusion.

### Reveal and review

After freezing the receipt, open Envelope B and classify the result:

- **Supported catch:** the known failure was covered and vetoed/flagged.
- **Scientific miss:** the known failure was covered but the system passed it.
- **Governance catch:** the failed interface was explicitly `NOT_ASSESSED` or
  outside applicability, so the system correctly withheld clearance.
- **False reassurance:** the failed interface was missing or out of scope but the
  rendered output implied clearance.
- **Correct covered pass:** a known success was covered and passed.
- **Unresolvable:** the external outcome is ambiguous or lacks enough detail.

The distinction between scientific miss and governance catch is central. A
`NOT_ASSESSED` result is not a correct chemistry prediction, but it may prevent a
bad decision.

### Post-output questions

1. Would this output change the first interface you investigate?
2. Did it identify a missing contact you had not written down?
3. Did any score create false confidence?
4. Which field should be removed?
5. Which missing scorer would be most valuable?
6. Would you submit a second case or run this locally?

### Minimum external case set

Obtain at least three cases from independent groups. Prefer:

- at least two known interface failures;
- at least one case with an intentionally unsupported interface;
- at least one case outside the familiar NMC/graphite liquid-cell template;
- at least one case where material names must be abstracted.

Do not count three cases from one person as three independent validations.

## Test 3: PFAS workflow-value test, after regeneration

### Why it is not ready today

The current private PDF/Markdown report is dated 2026-07-21. It says the US EPA
TSCA reporting start date is still being finalized. The current EPA page records
an April 2026 final rule and a changed timing mechanism. The private files also
contain visible character-encoding defects. Sending that report would test the
reviewer's tolerance for stale copy rather than the workflow's value.

Before any PFAS outreach:

1. regenerate the synthetic BOM report from the current code;
2. fix encoding in every attachment;
3. recheck every regulatory statement against current primary sources;
4. keep the universal EU restriction labeled as a proposal/process, not an
   enacted blanket ban;
5. keep the enacted PFHxA restriction separate and scoped;
6. state that the output is screening, not legal advice or qualification;
7. have a practitioner supply a redacted BOM only after agreeing on data handling.

Primary sources to check immediately before sending:

- https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas
- https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202402462
- https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping

The best PFAS question is not "is the software correct?" Ask:

> Does this report help you decide which supplier questions and qualification
> tests to perform first, and which required field is missing?

Measure whether the person supplies a real/redacted BOM, identifies required
supplier fields, or agrees to repeat the workflow. Do not measure success by
whether they agree that PFAS regulation is important.

## Test 4: provenance-contract adversarial review

Run this separately from chemistry-product evaluation. Send the unopened-file
failure, action-receipt rules, and one stable JSON export. Ask for the smallest
case in which all receipts exist but the conclusion remains unauthorized.

Success is an adversarial failure that forces a contract revision or a group
willing to test the contract on its own tool-using workflow. Praise for the
category-theory architecture is not an outcome.

## Recruitment and study operations

### Contact sequence

Recommended waves:

1. 5 to 8 MOF falsification contacts;
2. 8 to 20 MOF A/B invitations after the packet repair and two pilots;
3. 5 to 10 materials engineers asking for one own case;
4. PFAS practitioners only after report regeneration;
5. provenance researchers as a separate protocol study.

Personalize the first two lines around the person's actual work. Do not claim to
have solved their challenge. Do not introduce unrelated pages.

### Response classifications

Every contact should end in one recorded state:

- `NO_RESPONSE`;
- `DECLINED`;
- `POLITE_NONTECHNICAL`;
- `TECHNICAL_CRITIQUE`;
- `OWN_CASE_OFFERED`;
- `PILOT_OFFERED`;
- `DATA_USE_UNCLEAR`.

Do not describe a polite reply as external validation.

### Private study directory

Create a Git-excluded folder such as:

    .private_outreach/external_test_2026-08/

Recommended contents:

- `PROTOCOL_FROZEN.md`;
- `PACKET_MANIFEST.json`;
- `ASSIGNMENT_PRIVATE.csv`;
- `CONTACT_LOG_PRIVATE.csv`;
- `RESPONSES_VERBATIM_PRIVATE.jsonl`;
- `CODING_BLINDED.csv`;
- `CASE_INPUT_MANIFESTS/`;
- `CASE_RECEIPTS/`;
- `DEIDENTIFIED_RESULTS.md`.

Hash the frozen protocol and packet manifest before the first main-study send.
Never commit identifying or proprietary data. Publish only de-identified
aggregates with permission.

## Final 30-to-45-day decision

The product outlook is favorable enough to continue only if the external window
produces concrete behavior, not compliments.

### Continue and deepen one workflow when

- at least three independent researcher-supplied cases are completed;
- evidence changes or prevents at least two concrete next-step decisions;
- at least two groups offer a second case, pilot, or integration;
- the same missing scorer/gate appears repeatedly enough to define focused work;
- the evidence layer improves review without unacceptable burden.

### Simplify when

- known retrieval or transparent templates are as useful as generation;
- one domain receives cases and the others receive only general interest;
- reviewers value missing-coverage maps but not predicted rankings.

In that event, remove ornamental orchestration and productize the demanded
triage packet/API only.

### Stop active product development when

- researchers will discuss the idea but will not provide an artifact;
- evidence fields change no decisions or next experiments;
- candidate generation creates obvious artifacts that simple retrieval avoids;
- no group will repeat, pilot, or integrate the workflow;
- maintaining all eleven pages prevents a reliable domain-specific tool.

## Immediate checklist

1. Create a neutral five-candidate MOF image plate.
2. Generate matched A and B read-only packet files and a new receipt.
3. Run two usability pilots.
4. Freeze the main assignment and coding rubric.
5. Send the first five MOF falsification requests.
6. Synchronize the materials-engineer packet to Q11/Q12 before contacting anyone.
7. Prepare the two-envelope external-case intake form.
8. Regenerate the PFAS report before PFAS outreach.
9. Record every response, non-response, own case, and pilot offer.
10. Make the go/simplify/stop decision on the frozen deadline.
