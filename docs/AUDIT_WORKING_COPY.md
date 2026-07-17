# CHEM Audit Working Copy — Accuracy & Communication

> **2026-07-17 repair pass completed.** The executable findings and corrected
> feature assessment are consolidated in
> `docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md`. The earlier filename-based
> characterizations of pages 4-7 and 9-11 are retracted; every page was traced to
> its backend and assessed by function. This working copy remains as audit history.

*Opened 2026-07-17. Same method as the komposos-grid audit: find every claim, check it against
the repo's own data and audit posture, quarantine what can't be sourced, and decide outreach fit.
Statuses: `OPEN` · `IN PROGRESS` · `FIXED` · `PARKED (deliberate)` · `VERIFY EXTERNALLY`*

## Scope note (important)

This repo is ~219 MB, dozens of top-level dirs, and mixes chemistry/materials (MOF, PFAS, polymer,
metal, ceramic, glass, semiconductor, battery bridges) with **biology/pharma/oncology** content
(spatial_biology, opentargets cancer, AML triage, drug repurposing, protein loaders). Per the
owner's standing instruction, this audit pass covers **only the chemistry/materials + MOF surface**.
The bio/pharma bridges are explicitly **out of scope** here and untouched.

A full file-by-file audit of the whole repo is a multi-session effort. This document starts with the
highest-value, most decision-relevant findings (the Kulik outreach question and the claims that would
appear in any outreach) and leaves a scoped backlog.

---

## Headline: what's strong here

Unlike a typical "dirty" repo, CHEM already has real audit discipline baked in:

- **`audit/dataset_registry.json`** is genuinely rigorous — it tracks each benchmark's role
  (development / spent_diagnostic / current_blind), records SHA256 + pair counts, and **explicitly
  forbids reporting tuned numbers as blind claims**. `current_blind` is honestly `None` right now.
- **CLAUDE.md** carries honest posture: "Never report any Q8 number as a blind claim", physical-veto
  logic (pore access, Flory-Huggins) that survives composition instead of being averaged away, and
  calibration with out-of-sample ECE.
- The **22-atom linker generator works and is real** (verified 2026-07-17): constraint-based
  substitution/modification of known linkers via RDKit, produces valid MOF-linker motifs
  (biphenyl/stilbene dicarboxylates), **not an LLM**. Exact-heavy-atom filtering is a real capability.

The problem is not the core science. It's that the **outreach layer ignores the repo's own honesty
rules**, and the repo is drenched in commercialization framing that conflicts with the owner's stated
goal of offering value for free.

---

## K. The Kulik outreach question (highest priority)

### K1 — The "solved your challenge" framing is the wrong move — `RECOMMEND REFRAME`
Kulik's 22-atom-ligand line (transcript `latentspaces1txt.txt` lines 3, 57–63) is a **probe of LLM
chemical reasoning**, used as an anecdote for *why you still must learn chemistry*. She even calls it
"maybe a trivial thing… something an expert chemist could do in a second." She is **not** asking for a
tool that hits an atom count; she's illustrating that LLMs lack chemical grounding.

`KULIK_EMAIL_DRAFT.md` subject line — *"Your 22-atom ligand challenge - solved"* — therefore answers a
question she didn't ask. A constraint solver that filters by heavy-atom count does the *trivial* part
(counting), not the *hard* part (is the ligand chemically sensible, synthesizable, will it actually
bind two N to the metal). Sending "solved" risks reading as missing her point.

**The owner's own instinct in this session is more correct than the draft:** she'd care about *chemical
grounding* ("getting her models to guess, not any model"), not a SMARTS counter. What she values, from
the transcripts: knowing when models are right/wrong, reactivity prediction, transition-metal chemistry,
experimental-fidelity data, and **uncertainty quantification** (the one thing `KULIK_RELIABILITY_UPGRADE.md`
gets right).

### K2 — The email inflates and mismatches its validation numbers — `MUST FIX before any send`
`KULIK_EMAIL_DRAFT.md` claims *"validated against 143 literature pairs (94.4% accuracy, F1=0.963)"*.
- That number is the **material-compatibility** benchmark aggregate — **unrelated** to ligand
  generation. Bolting it onto the 22-atom claim implies a validation that doesn't exist for that task.
- 143 pairs = the sum of development + spent-diagnostic pairs, which the repo's **own registry rule
  forbids reporting as a blind claim**. The honest first-run blind numbers are smaller sets: Q6 100%
  (35), Q7 91.4% (35), Q4 85.7% (42), Q3 83.3% (36), Q8 70% (40). `current_blind = None`.
- The ligand generator's actual grounding is the **MOF funnel** (AUROC 0.884, recall@22 0.95) — cite
  *that* for the ligand claim, not the compatibility number, and label it a screening funnel.

### K3 — Chemistry overclaims in the email body — `MUST FIX`
"Linker #13: C16H14N6 (22 atoms, 6 N donors, **perfect for coordination**)" — a 22-heavy-atom ligand
with 6 N is unusual and strained; "perfect for coordination" is exactly the kind of claim a MOF chemist
will bounce. "5 verdicts all AGREE (synthesizability, toxicity, stability, activity, conductivity)" —
toxicity/activity/conductivity verdicts on a novel ligand are generic engine outputs, not chemically
meaningful validation. Drop them.

### K4 — Stale/leaky details — `FIX`
Email GitHub URL points to a **different repo** (`KOMPOSOS-III-LAMBDA-max-3D-chem`), not this one.
"Success Metrics" section plans email-open tracking and "co-authorship possibility" — see V1.

### K5 — Privacy: real person's outreach drafts committed — `DECIDE`
`KULIK_EMAIL_DRAFT.md`, `KULIK_OUTREACH_NEXT_STEPS.md`, `KULIK_OUTREACH_REVISED.md`,
`KULIK_RESEARCH_INTEGRATION.md` name a real person and a drafting/tracking strategy. Same policy as the
grid Julia draft: keep locally, untrack + gitignore, and (if already pushed) purge from history.

### Recommendation on contacting her
**Yes, contacting her can be worthwhile — but not with the current email.** Reframe from
"I solved your challenge" to a genuine, free, no-ask offering, e.g.:
> "Your 22-atom line stuck with me — not as a challenge to beat, but because it's a clean example of
> where free-form LLMs fail. I built a small *constrained* generator that guarantees the atom count and
> N-donor pattern deterministically (category-theory + RDKit, no LLM), then screens candidates through a
> grounded MOF-linker funnel. It's open and free; here are 20 exactly-22 / 2-N-donor candidates. I'd
> value a chemist's gut check on whether any are actually sensible — and I'm not trying to sell or
> co-author anything."

That framing (a) respects that the count is the easy part, (b) offers the *screening* as the real
contribution, (c) matches the owner's "value for free" stance, and (d) invites her expertise instead of
claiming to have replaced it. Verify every number, cite the MOF funnel (not the compatibility number),
and cut the toxicity/activity verdicts.

---

## V. Values / framing mismatch (repo-wide)

### V1 — Commercialization framing contradicts the owner's stated goal — `DECIDE`
Owner (2026-07-17): *"I only want to offer value to others for free, I'm not trying to be the next big
person."* The repo contains `COMMERCIALIZATION_PLAN.md`, `INVESTOR_EVIDENCE_PLAYBOOK.md`,
`LAUNCH_PLAYBOOK.md` (49 KB), `go_to_market/`, `CHEAP_DRUG_REPURPOSING_CANDIDATES.md`, and outreach
"success metrics" aiming at co-authorship. None of this is wrong to have explored, but it pulls against
the free-value mission and, in outreach, creates the "what's the ask?" wariness that makes experts
cautious. Decide what the public repo should say the project *is*.

---

## A. Accuracy findings (chem/materials surface) — backlog

### A1 — Verify headline benchmark numbers reproduce — `FIXED / ONE QUARANTINED`

- MOF funnel reproduced: AUROC 0.8843, held-out-real pass-all recall 0.9433,
  exact-22 recall 0.95 (n=20) and AUROC 0.9013.
- Compatibility development regression reproduced at 41/41. Q9 is spent and is
  now registered as such (35/40 after remediation); Q10 remains sealed.
- Current strict-formula formation LOO does **not** reproduce 0.304: n=179, MAE
  0.416, RMSE 0.552, median 0.340. Primary docs now use the current result.
- Formation intervals were miscalibrated at 31/61/88 against nominal 50/80/95.
  The official recalibration command regenerated the artifact; deployed coverage
  is now 50/79/95 and five-fold calibration is 49/80/94.
- Crystal Dreamer's historical 7/9 claim was not re-reproduced within this pass's
  interactive window. It is quarantined instead of repeated.
- The audited local MP cache contains 103,644 entries. The 3-linker fallback is a
  demo fallback, not the corpus used by the reproduced MOF benchmark.

### A2 — Demo-cache honesty — `OPEN`
Same pattern as the grid MOF test relaxation (`len(linkers) >= 3`): several components fall back to a
tiny demo cache. Any figure computed on the demo cache must say so.

### A3 — UI provenance labels — `PARTIALLY FIXED`
Port the grid's measured/derived/simulated badge discipline to the CHEM Streamlit app
(`streamlit_app/`). Scattered pages (MOF, PFAS, material compatibility) each need a one-line "what this
is / what it isn't" and a provenance tier.

All eleven pages now expose a central feature-status note; Explorer notes that
were defined but not rendered are visible. Cell/advanced/synthesis/composition
copy was corrected. A future visual badge system can improve scanability, but the
load-bearing claims are no longer hidden.

---

## C. Communication / UI — backlog

### C1 — Scattered multi-purpose UI — `OPEN`
UI has accreted pages for different purposes (MOF designer, PFAS scanner, material compatibility, …).
Same fix as grid: organize by user question, put the math one click down, one honest label per page.

### C2 — Doc sprawl — `OPEN`
Dozens of top-level strategy/marketing/playbook .md files. Decide which are public-facing vs local
working notes; a first-time visitor can't tell what the project is.

---

## Guardrails (same as grid)

- Never let a compatibility/aggregate number stand in as validation for an unrelated task (ligand gen).
- Never report tuned/dev/spent-diagnostic numbers as blind — the repo's own registry already says so.
- Screening ≠ measurement ≠ validation. Cite the *right* benchmark for the *specific* claim.
- Any claim naming a real person must be verifiable and must not overclaim on their behalf.
- Free-value framing beats commercialization framing for this owner's goals and for expert outreach.
