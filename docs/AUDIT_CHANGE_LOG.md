# KOMPOSOS-IV Audit Change Log

*Version IV Categorical Runtime Synchronization*

---

## 2026-08-09: MOF paired review exports and partial geometry status

- Added same-order conventional and evidence-governed researcher-review CSVs.
- Evidence exports preserve funnel status, scope, missing evidence, soft flags,
  novelty, and experimental NOT_ASSESSED status.
- Geometry embedding failure is now PARTIAL_PASS, not displayed as clearing
  every grounded gate. The frozen funnel implementation and benchmark scoring
  are unchanged.
- Added a private, Git-excluded five-candidate A/B review packet and send guide.
  No recipient was selected and no message was sent.

## 2026-08-09: Crystal Dreamer search-strategy ablation

- Compared direct labelled filtering, an explicitly non-deployable composition
  oracle, one deterministic random draw, four individual strategies, and the
  four-strategy union under matched development targets and budgets.
- The union tied several simpler variants at 7/9 property-window recovery.
- The 58-formula stoichiometry grid matched 7/9, exceeded union exact@25
  recovery (4/9 versus 2/9), tied near@25 (6/9), and had 100% gate coverage.
- Direct MP voltage/capacity filtering was NOT_ASSESSED: zero local MP rows have
  both required labels.
- The union's incremental value is not established. Receipt:
  audit/crystal_search_ablation_report.json.

## 2026-08-09: Crystal Dreamer per-candidate physical status

- Every retained candidate now carries ASSESSED_PASS or NOT_ASSESSED.
- Definite charge-balance failures carry VETOED, remain outside the lead list,
  and are preserved in a separate rejection collection and UI audit view.
- JSON and flat CSV audit exports preserve candidate status and disposition.
- The recovery receipt schema is upgraded to v2 and records top-K candidate
  statuses plus all physical-gate rejections for each assessed target.

## 2026-08-09: Crystal Dreamer charge-gate runtime and recovery receipt

- Replaced pymatgen's combinatorial site-level oxidation-state enumeration with
  an existence-only dynamic program over the same default oxidation-state sets.
  The prototype agreed with pymatgen on 240/240 tractable candidate formulas.
- Added assessed, vetoed, and unassessable charge-balance counts to the design
  result and rendered those counts on the Crystal Dreamer page.
- The named strict leave-one-anchor-out development audit now completes in about
  27 seconds rather than exceeding 30 minutes.
- Reproduced development result: 7/9 self-consistent property-window recovery,
  2/9 exact@25, 6/9 near@25. Si was skipped for missing voltage/capacity.
- Gate coverage across the nine assessed targets: 2,527/2,700 assessed (93.59%),
  102 definite failures vetoed, 71 unassessable and retained without clearance.
- Receipt: `audit/crystal_recovery_report.json`. This is development/spent
  inverse-search evidence, not predictor accuracy, blind evidence, or experiment.

## 2026-07-21: BOM ingestion — free-form input in, honest resolution out

New `ingest/` package (`ingest/bom_ingest.py`, 23 tests in
`tests/test_bom_ingest.py`). Closes the "dropdown vocabulary" product gap: users
can now paste a real bill of materials instead of typing canonical names.

- **Parses tolerantly:** CSV/TSV/semicolon/pipe, header row optional (header
  synonyms + unit-suffix stripping, e.g. `Qty (kg)`), plain one-name-per-line,
  comments/blank lines skipped, unparsable rows reported in warnings — never
  silently lost. European decimal commas handled (`1,5` vs `1,500`).
- **Resolves in a cascade:** exact vocabulary key -> unambiguous case-insensitive
  match -> bridge alias tables -> curated free-text/brand alias table
  (`Kynar 2801`->PVDF, `Teflon tape`->PTFE, `copper foil`->Cu_foil,
  `alumina`->Al2O3, ...), with a brand-with-grade prefix fallback. The PFAS
  registry is consulted independently, so a name can be vocabulary-matched AND
  PFAS-flagged (PVDF), or PFAS-only (screenable but not interface-scoreable).
- **Honesty contract:** unrecognized names are a first-class outcome with
  difflib close-match **suggestions that are never auto-applied** — pinned by a
  test that `LiFSI` suggests LiTFSI but is NOT coerced to it (different salts).
  The alias table is tested to map only onto names the vocabulary actually
  contains, so ingestion can never invent a material.
- **Wired into the PFAS report path:** `IngestResult.to_material_inputs()` feeds
  `screen_portfolio` directly, passing canonical names (raw name preserved in
  the function text) and keeping unknowns in the report, where they are neither
  cleared nor flagged. The PFAS Scanner page's custom-BOM input now uses this
  (resolution preview with recognized/unrecognized counts and suggestions)
  instead of the rigid `name | function | qty` parser; the old pipe format still
  parses.
- Scope note: this is input plumbing. It adds no new scoring capability and
  changes no benchmark; dev/compat/PFAS behaviour on canonical names is
  untouched.

---

## 2026-07-21: narrowed the copper-sulfide veto (it was firing on LiTFSI)

Follow-up review of the collector veto added 2026-07-20 found it over-broad. It
fired whenever a Cu collector met any partner with sulfur in its formula, which
is wrong in two directions:

- **False positive: Cu + LiTFSI was vetoed.** LiTFSI's sulfur is fully-oxidized
  sulfonyl (SO2CF3); it does not sulfidize copper. LiTFSI is a standard salt, so
  vetoing it was a flat error.
- **Likely false negative: Cu + Li3PS4 / LGPS was vetoed.** Sulfide *solid
  electrolytes* sit against the anode, where copper is the standard,
  generally-stable collector. A blanket veto there suppresses a normal
  construction.

Fix (`battery_bridge/interface_validator.py`): the veto now requires the
sulfur-bearing partner to be a **cathode active material**
(`material_class == CATHODE`), which is the undisputed corrosion case (elemental
sulfur / polysulfide at cathode potential converting Cu to Cu2S). Verified:

| pair | before | after | correct? |
| --- | --- | --- | --- |
| Cu_foil + S8 | vetoed | vetoed | yes (S cathode) |
| Cu_foil + Li3PS4 | vetoed | viable | yes (solid electrolyte) |
| Cu_foil + LGPS | vetoed | viable | yes (solid electrolyte) |
| Cu_foil + LiTFSI | vetoed | viable | yes (sulfonyl salt) |
| Al_foil + S8 | viable | viable | yes (Al is correct for S) |

This also corrects a mistaken expectation in my own 2026-07-20 scratch probe,
which asserted Cu+Li3PS4 should be incompatible. Dev unchanged (41/41). No
calibration change: none of the affected pairs are in the calibration corpus, so
the isotonic artifact is byte-identical (0.055/0.054). The Al-Li alloying veto is
untouched. Q10/Q12 untouched.

---

## 2026-07-20 (correction): veto scores use an order-preserving squash, not a clamp

The fix recorded below shipped with `min(total, 0.35)`. Reviewing it turned up a
self-inflicted regression: the clamp collapsed **105 of 365 pairs (28.8%) onto
exactly 0.35**, leaving only **14 distinct scores across 168 rejected pairs**.
That is the same constant, non-discriminating score pattern this project treats
as a defect everywhere else, and it flattens the ranking that PFAS replacement
triage and discovery rely on. Twelve pairs labelled *compatible* were also buried
in that mass point, making those false negatives harder to spot than when they
carried distinctive scores.

Replaced with a monotone squash, `_vetoed_score(total) = VETO_SCORE_CAP * total`,
in `metal`, `glass`, `semiconductor` and `battery`. It guarantees the same
sub-threshold ceiling while preserving order, so a vetoed pair that was strong on
its other axes still ranks above one that was weak.

| | clamp | squash |
| --- | ---: | ---: |
| distinct scores among rejected pairs | 14 | **64** |
| overall distinct scores (of 365) | 132 | **182** |
| pairs tied at exactly 0.35 | 105 | **49** |
| score/verdict inversions | 0 | **0** |
| corpus accuracy | 0.9151 | **0.9151** |
| development benchmark | 41/41 | **41/41** |

**Correction to an overclaim in the entry below.** That entry reported the
clamp's isotonic **OOS ECE 0.045** as a clean win. It was partly an artifact: 93
identically-scored incompatible pairs are trivially easy for isotonic to fit.
Honest figures with the squash are **OOS ECE 0.055, Brier 0.054**, against a
historical baseline of 0.072/0.049 — ECE improved, Brier marginally worse. The
squash is still preferred: the ~0.010 ECE difference was illusory, the retained
ranking information is real. Calibration artifact rebuilt again accordingly.

Note the comparison to 0.072/0.049 is not cleanly attributable, since the earlier
2026-07-20 remediation (solvent intent, collector vetoes, routing) also moved raw
scores. Treat 0.055/0.054 as the current measured state, not as an isolated
effect of this change.

**Follow-up (2026-07-21): ceramic and polymer converted too, as a TIERED squash.**
These two kept `min(total, cap)` with cap in {0.35, 0.38, 0.45}, where the cap
encodes veto CONFIDENCE (polymer: 0.35 confirmed-immiscible vs 0.45
missing-chain-length/solubility-only; ceramic: 0.35 degradation vs 0.38 CTE). A
flat `0.35*total` would erase that, so both now use `_vetoed_score(total, cap) =
cap * total`, preserving the per-branch tier AND restoring intra-tier order.

Effect across the whole veto-consistency arc:

| metric | clamp | 4-bridge squash | + ceramic/polymer tiered |
| --- | ---: | ---: | ---: |
| distinct scores among 168 rejected | 14 | 64 | **104** |
| overall distinct (of 365) | 132 | 182 | **222** |
| pairs tied at 0.35 | 105 | 49 | **12** (all incompatible) |
| score/verdict inversions | 0 | 0 | **0** |
| corpus accuracy | 0.9151 | 0.9151 | **0.9151** |
| development Brier | 0.086 | 0.080 | **0.052** |

**Honest trade-off on calibration — not a clean win.** Rebuilt isotonic OOS:
ECE **0.055 -> 0.070**, Brier **0.054 -> 0.068** — modestly WORSE. But the *raw*
OOS ECE moved the other way, **0.159 -> 0.140** (better), so the underlying
scores are more honestly calibrated; it is specifically the isotonic fit that
degraded, consistent with per-fold overfitting on the now-wider, sparser score
distribution rather than a real loss. On ~55 test pairs/fold a 0.015 ECE move is
also near the noise floor. Kept because discrimination (the load-bearing property
for triage) and raw calibration both improved, verdicts are unchanged, and the
earlier clamp's better isotonic number was itself partly a mass-point artifact.
Do not quote the isotonic OOS movement as a headline in either direction.

The 12 residual ties at 0.35 are pairs whose pre-veto composite was ~1.0; all 12
are incompatible-labelled, so no compatible pair is buried. Verdict-safe by
construction: `cap*total <= cap <= min(total, cap)`, so the squash is always <=
the old clamp and never crosses the threshold upward.

---

## 2026-07-20: Vetoes now annihilate the SCORE, not just the verdict

Closes the non-monotonicity noted in the Q11 writeup: prediction was not
monotonic in the surfaced score, so a number could contradict the decision
displayed beside it.

**Root cause (systemic).** `metal` (2 vetoes), `glass` (2), `semiconductor` (1)
and 4 of 5 `battery` vetoes set `is_viable = False` **without lowering `total`**.
`ceramic` and `polymer` already annihilated correctly, so the codebase was
internally inconsistent about its own documented rule that *a physical block
survives composition (min/annihilator), not weighted sum*. The concrete symptom:
Ni+Fe scored **0.721 -> incompatible** while Al+Fe scored **0.674 -> compatible**.

**Fix.** Every bridge now caps a vetoed composite at `VETO_SCORE_CAP = 0.35`,
below the 0.50 viability threshold and matching the band ceramic/polymer already
used. The rule now applies to the reported score, not only the verdict.

**Zero verdicts changed** — this is a reporting-consistency fix, not a threshold
change:

| | before | after |
| --- | ---: | ---: |
| corpus accuracy (365 dev + spent pairs) | 0.9151 | **0.9151** |
| development benchmark | 41/41 | **41/41** |
| score/verdict inversions | 13 | **0** |
| min score among *compatible* | — | 0.502 |
| max score among *incompatible* | — | 0.473 |
| development Brier | 0.095 | **0.086** |
| isotonic 5-fold **OOS ECE** | 0.072 | **0.045** |

The calibration gain is causal rather than incidental: a high raw score attached
to an incompatible verdict is precisely what a calibrator cannot fit, so removing
those points improved it. The isotonic artifact was **rebuilt** because the raw
score distribution changed (`python audit/build_compatibility_calibration.py`;
measured with `run_compat_calibration.py` and `fit_compat_calibration.py`).
Q10 and Q12 were not touched.

Pinned by `tests/test_veto_score_consistency.py` (7 tests), including a
corpus-wide assertion that the highest incompatible score stays below the lowest
compatible score, so the inversion cannot silently return. Full suite: 1265
passed, same 5 pre-existing bio/repurposing failures.

---

## 2026-07-20: MLIP (CHGNet) oracle — 3x lower formation-energy error where a structure exists

Full writeup: `docs/MLIP_ORACLE_2026-07-20.md`. Module `oracle/mlip_integration.py`,
benchmark `python audit/run_mlip_benchmark.py --relax`, 9 tests in
`tests/test_mlip_integration.py`. Optional dependency: `pip install chgnet`
(weights ship in-package, works offline).

On **294 held-out materials** (MP PBE formation energies as ground truth,
elemental references fitted on a disjoint 445-material train split):

| model | n | MAE | RMSE | median |
| --- | ---: | ---: | ---: | ---: |
| CHGNet MLIP (relaxed) | 294 | **0.134** | 0.238 | 0.076 |
| KOMPOSOS surrogate (formula only) | 294 | 0.404 | 0.530 | 0.349 |

MLIP closer on 228/294 (77.6%). Train residual 0.117.

- **Never compare 0.134 to the 0.416 headline** — different material sets (0.416
  is the 179-material strict formula-LOO benchmark; this is cubic
  fully-determined prototypes). The like-for-like figure is the surrogate's
  **0.404 re-scored on these same 294 materials**.
- **Typed as SURROGATE, not DFT.** CHGNet is a surrogate *of* MP PBE; crossing to
  `PBE_MP` needs the explicit `MLIP_TO_PBE_MP` conversion, which adds the model's
  own error rather than pretending the lift is free. Absent the backend it raises
  `OracleUnavailable` and never falls back to the composition surrogate under an
  MLIP label. It also refuses to extrapolate over elements with no fitted
  reference.
- **Structure required** (capability boundary): the MP cache has lattice
  parameters but no coordinates, so only **759 of 103,644** entries have a fully
  determined prototype. Prototypes with free internal parameters (rutile,
  wurtzite, spinel, corundum) are excluded rather than guessed.
- **Two harness bugs were found and fixed before trusting any number**, both
  caught by the train residual: (1) fitting 63 elemental potentials from 60
  training rows left the normal equations rank-deficient and produced MAE 7.04
  eV/atom — fixed with an element-coverage requirement; (2) scoring unrelaxed
  idealized prototypes, plus alphabetical perovskite A/B site assignment (which
  put Hf on the A-site of KHfO3), left a **train residual of 0.670** — fixed by
  MLIP relaxation and radius-ordered site assignment, dropping it to 0.117.
- Additive and optional: **all existing benchmarks unchanged** (dev compatibility
  still 41/41). Not yet wired into Crystal Dreamer, discovery, or compatibility —
  deliberately separate, and no claim is made that it improves any downstream
  verdict.

---

## 2026-07-20: Category-theory ablation — no measurable accuracy contribution

Full writeup: `docs/CT_ABLATION_2026-07-20.md`. New tool:
`python audit/run_ct_ablation.py --json audit/ct_ablation_report.json`.

Over **374 development + spent-diagnostic pairs** (365 evaluated), removing the
categorical layer changes **accuracy by 0.0000 and MCC by 0.0000** (both arms
0.9151 / 0.8298). Q12 was excluded — the script reads the registry to block
whatever is currently `current_blind`, so it cannot silently spend a holdout.

Two CT surfaces were ablated separately because their causal status differs:

- **Yoneda transfer guard / strategy ensemble: REPORTING ONLY.**
  `build_compatibility_ensemble` is referenced only inside
  `_compatibility_decision_metadata`, never inside the scoring path (verified by
  source inspection, not assumed). It cannot affect score or verdict by
  construction, so there is no numeric ablation to run for it. The formal Yoneda
  presheaf evidence in vote metadata is evidence, not a predictor.
- **Typed morphisms: in the causal path, inert in practice.**
  `apply_typed_morphism_adjustment` can overwrite score and verdict on 8 domain
  routes, but perturbed **1 pair of 374** (GaN+SiC_4H, 0.750→0.760) and flipped
  **zero** verdicts.

**Consequence for claims:** do not say category theory improves predictive
accuracy, that the benchmarks validate the categorical runtime, or that CT
explains the compatibility results — the numbers come from the domain bridge
scorers, and the physical vetoes live in the bridges, not the CT layer. Typed
composition, provenance/receipts, transfer guards, dataset-role discipline and
the veto algebra remain defensible as *architecture*, and are untested here.
Not covered: cross-domain transfer gating, discovery, multi-domain aggregation,
and the separate bio repurposing benchmark (`validation/ablation_study.py`,
currently drifted — its manifest tests fail on a DB hash mismatch unrelated to
this work).

Note the 0.9151 baseline is a dev+spent figure and is **not** a generalization
estimate (Q11 blind was 63.9% on the same scorers); the ablation's validity does
not depend on that level since both arms use the identical corpus.

---

## 2026-07-20 (later): Scorer remediation, Q11 spent, Q12 frozen

Full writeup: `docs/SCORER_REMEDIATION_2026-07-20.md`.

**Honest regression reading — correct answers did NOT increase (23/40 both
before and after).** Four genuine fixes gained (S8+Cu_foil FP→TN, PEEK+Water
FN→TP, CMC+Water and Bi2Te3+Ni SKIP→TP); four previously-correct answers became
honest abstentions (PS/PC+Acetone, PDMS/PMMA+Toluene were right only because a
constant 0.45 matched an incompatible label by base rate). Errors 13→10, MCC
0.278→0.401, Brier 0.279→0.220, ECE 0.177→0.151, evaluated 36→33.
**The 63.9%→69.7% accuracy rise is partly a shrinking denominator; never quote
it alone.**

- **Correction to the 2026-07-20 diagnosis below:** the polymer/solvent path was
  NOT inverted. This bridge's own tests show it deliberately answered the
  *dissolution* question (PVDF+NMP, CMC+water binder slurries), for which Hansen
  matching is correct. The defect was a **missing resistance intent** — both
  questions shared one interface and only dissolution was implemented.
  Dissolution stays the default; resistance is explicit, answered from curated
  `water_absorption_pct` (verified 7/7) and **abstaining** for organic solvents.
  Grounding: Hansen Ra alone separates resistance from attack at only 22/30
  (PTFE+toluene Ra 3.88 resists — crystallinity; CMC+water Ra 22.3 dissolves —
  H-bonding), so no Ra-based resistance score was invented.
  New `PolymerInterfaceScore.not_assessed` + `NotAssessedError` ensure an
  abstention is recorded as a skip, never as a confident "incompatible."
- **Battery collector vetoes** (`battery_bridge/interface_validator.py`):
  Li-Al alloying below ~0.3 V (grounded in per-material `voltage_window`, so it
  correctly spares LTO, which commercially uses Al on both electrodes) and
  sulfide corrosion of Cu (general formula-element rule, so it fires for
  Li3PS4+Cu_foil as well as S8+Cu_foil). Validated 12/13 on independent cases;
  the one miss is the pre-existing Si volume-expansion mechanical veto, left
  untouched rather than weakened to pass a test.
- **Cross-domain routing** (`audit/run_audit.py`): declared domain is tried
  FIRST, re-resolving only on genuine name-resolution failure. An earlier
  pre-emptive re-resolution broke AlN+TiN and Al_foil+Si, because the registry
  maps each material to one domain though many live in several bridges. Also
  fixed `resolve_workflow_domain`: no glass+metal or polymer+glass case, and an
  order-dependent composite fallback. Polymer branch now threads
  `interface_role` (the 2026-05-31 role gate was unreachable from this path).
- **Dev unchanged: 41/41, Brier 0.095, 0 skips.** 174 bridge/audit tests pass.
  Full suite 1256 pass / 5 fail, all 5 pre-existing (verified by stashing only
  the changed files) — bio/repurposing DB-hash drift, unrelated.
- **Q11 → `spent_diagnostic`** (its 63.9% first run remains its only blind
  number). **Q12 → `current_blind`, UNSCORED**: 36 pairs, **12 contrast groups**
  (two pairs sharing a material with opposite correct answers — a constant
  fallback cannot pass one), zero overlap with all 525 prior pairs.
  **Q10 remains sealed and has never been consumed.**
- Deliberately unfixed (not patched toward Q11 labels): metal-semiconductor
  interdiffusion, salt identity in collector passivation, polysulfide/carbonate
  attack, non-monotonic score-vs-verdict, ceramic co-sintering reactivity,
  glass/metal CTE sealing.

---

## 2026-07-20: Q11 frozen and scored — first current-blind compatibility result (63.9%)

**Q11 was frozen as `current_blind` and scored in an authorized event.** Full
writeup: `docs/Q11_BLIND_RESULT_2026-07-20.md`.

- **Result: 63.9% accuracy** on 36 evaluated / 4 skipped, MCC 0.278, Brier 0.279,
  ECE 0.177, TP11/TN12/FP7/FN6. Protocol FAIL (skips) and metric FAIL (<85%).
- **Development 41/41 and Q9 87.5% do not predict blind performance.** The honest
  pairwise-compatibility headline is now the Q11 blind number, not 100%.
- **The isotonic calibration claim does not transfer:** reported 5-fold OOS ECE
  0.072 vs **blind ECE 0.177**. Scope that claim to the dev + spent-diagnostic
  distribution.
- Seal discipline: pair list + hidden labels were committed (`ce739de`) **before**
  any prediction ran. New tool `audit/merge_sealed_labels.py` re-verifies both
  SHA256 seals and refuses to merge a broken seal. Q10 remains sealed and unspent.
- Freeze checks: zero name-pair overlap against all 485 existing benchmark pairs;
  every material name resolves in a bridge vocabulary (avoids the Q8 skip storm).

**Three root causes, each confirmed on INDEPENDENT probe pairs so the diagnosis
does not consume the holdout:**

1. **Solvent-exposure inverts the miscibility veto.** `chemical_resistance` /
   `solvent_exposure` are missing from `COEXISTENCE_INTERFACE_ROLES`
   (`polymer_bridge/interface_validator.py`), so the blend immiscibility veto
   (`total = min(total, 0.45)`) fires on chemical-resistance interfaces — where a
   solubility *mismatch* is precisely why the polymer resists the solvent. Probe:
   10 of 12 chemically distinct polymer+solvent pairs return the **identical
   0.45** (PEEK+acetone == PVC+acetone). No discrimination; correct only by base
   rate. This is the rule CLAUDE.md already states — the role list just lacks it.
2. **Current-collector identity is ignored.** `Graphite/LTO + Al_foil/Cu_foil` all
   return exactly 0.9375, so S8+Cu_foil (Cu2S corrosion) scores identically to
   S8+Al_foil, and Al_foil+LiPF6 (passivates) identically to Al_foil+LiTFSI (pits).
3. **Cross-domain routing skips.** CMC+Water, Kovar+FusedSilica, Bi2Te3+Cu,
   Bi2Te3+Ni die on "Unknown material" although the partner exists in another
   bridge's vocabulary. Abstention is the safe behavior and failure-memory logged
   it honestly, but these are real engineering interfaces.

Also observed: **prediction is not monotonic in score** — Ni+Fe 0.721 predicted
incompatible while Al+Fe 0.674 predicted compatible (a veto changes the verdict
without changing the surfaced score).

**Why dev 41/41 did not predict this — visible in the dev run itself:** 11 of the
41 development pairs return the identical score **0.350** and *every one is
labeled incompatible* (further constant clusters at 0.380/0.250/0.180, likewise
all incompatible). About a quarter of the dev set therefore cannot distinguish
"correctly identified incompatibility" from "no applicable model, returned a low
constant that matched the label." Q11's **contrast pairs** (chemically opposite
pairs sharing a material: S8+Cu_foil vs S8+Al_foil, Al_foil+LiTFSI vs
Al_foil+LiPF6, POM+acetone vs PC+acetone) are what exposed it — each contrast
pair scored **identically**. Contrast pairs are the highest-information test
design available here and should be standard in Q12 and in the dev set, because a
constant-fallback scorer cannot pass them by base rate.

**Audit-tooling defect fixed:** the external runner reported "Overlap with
existing benchmark identities: 40" for Q11 — entirely **self-overlap**, because
`_load_existing_benchmark_identities` excluded only the merged file under test and
not its same-period siblings (the unlabeled pair list). Every split-format holdout
(Q9/Q10/Q11) was over-reported. Fixed by excluding the whole same-period file
family; Q11 now reports 0, Q9 still correctly reports its genuine 16 and unchanged
87.5%.

**Discipline:** Q11 is still `current_blind`. Seeing these results does not spend
it; **remediating against them does**. Fix the three causes on independent/dev
pairs, then re-run Q11 **once** as regression and demote it to `spent_diagnostic`
in the same commit, and freeze Q12 before any further blind claim.

---

## 2026-07-19: Known limitation — funnel `azole_N` SMARTS overcounts (deliberately unfixed)

**Finding:** `mof_bridge/benchmark/funnel.py` `_COORD_SMARTS["azole_N"]` is
`[n;r5]`, which also matches **N-substituted** five-ring aromatic nitrogens
that cannot donate to a metal (their lone pair is either alkylated away or in
the ring π-system). `azine_N` correctly requires `[n;X2;r6]`. Effect: the
reported `recognized_coordination_sites` is inflated for N-alkylated azole
candidates (e.g., a bis(N-alkyltriazole) with 6 ring N reports 6 sites; only
4 are pyridinic-type donors).

**Impact bound (measured 2026-07-19 against the frozen benchmark pools with a
strict `[n;X2;r5]` variant):** seed reals 253 → 44 counts inflated, **0 G2
pass/fail flips**; eval reals 423 → 69 inflated, **0 flips**; decoys:
generator_raw 6 inflated / 0 flips, random_valid 0 affected,
**perturbed_real 40/163 would newly die at G2**. The frozen recall 0.9433 /
AUROC 0.8843 headline is therefore **unaffected on the real-linker side**, and
a stricter pattern could only flatter AUROC by killing decoys.

**Why it was NOT fixed:** (1) changing a gate after observing which eval
decoys it kills is tuning on eval, which this benchmark forbids
("Nothing here tunes on eval", `mof_bridge/benchmark/run.py`); (2) a naive
`X2` restriction stops crediting deprotonatable azole N–H (imidazolate/
pyrazolate, i.e., ZIF-type chemistry), so the correct pattern needs a
chemistry decision, a fresh frozen benchmark run, and a new report artifact.
Until then: **treat per-candidate site counts for N-substituted azoles as
upper bounds**; the G2 pass/fail verdicts for real linkers stand.

---

## 2026-06-10: Stoichiometric SMT Validation (Z3) for Synthesis Routes

**New audit + runtime guard:** `synthesis_planner/stoich_solver.py` encodes
route-level element balance (leaf precursors -> target, chemistry-gated
byproduct escapes) as a Z3 feasibility problem.

- **Audit result:** 17/17 stoichiometric routes BALANCED, 0 UNBALANCED,
  7 SKIPPED (composite/mixture targets — balance undefined). This is an
  **internal-consistency / development check, NOT a blind claim** (no held-out
  dataset; not registered in `dataset_registry.json`).
- Run: `python audit\run_stoich_audit.py [--json audit\stoich_balance_report.json]`.
  Frozen artifact: `audit/stoich_balance_report.json`.
- **Runtime wiring:** `SynthesisPlanner.score_route()` attaches
  `stoichiometry` / `balanced_reaction` / `stoichiometry_notes`; UNBALANCED is
  a **hard veto** (composite annihilated to 0 — min/annihilator, not weighted
  sum, same principle as the MOF pore and Flory-Huggins vetoes). SKIPPED
  carries no penalty. Without z3-solver installed the planner degrades to
  `UNAVAILABLE` (no crash, no behavior change).
- **No regression:** synthesis_planner tests 111 pass (94 existing + 17 new);
  no curated route's ranking changed (none are UNBALANCED). Compatibility/MOF/
  Crystal Dreamer/PFAS code paths untouched — their frozen numbers stand.
- Scope honesty: SAT = element-balance feasibility only (witness equation is
  minimal-byproduct, not a mechanism); balance cannot check redox, kinetics,
  or phase purity. Heuristic warning flags net O2 release under inert high-T
  atmospheres (no curated route currently triggers it).
- UI: new `streamlit_app/pages/11_Synthesis_Planner.py` surfaces ranked routes
  with balanced equations and veto badges; `validation_status.py` gained the
  `synthesis_planner` feature note.

---

## 2026-05-30: Compatibility Confidence Calibration (isotonic)

**Improvement:** compatibility scores are now mapped to a **calibrated probability**
via a global isotonic calibrator (fit on dev + spent diagnostics, leak-controlled
dedup; current-blind excluded). Honest k-fold **out-of-sample ECE 0.072** (Brier
0.049), down from raw ECE ~0.194. The 277-pair dev+Q2–Q9 measurement shows
calibrated ECE 0.058 (in-sample) vs raw 0.154.

- Method chosen by `audit/fit_compat_calibration.py` (raw 0.167 / Platt 0.158 /
  **isotonic 0.095** OOS ECE on 277 pairs); isotonic generalized best.
- Stored as monotonic (x, y) breakpoints in
  `audit/calibration/compatibility_calibration_2026_q4_dev.json` so the runtime
  interpolates **without sklearn**. `CompatibilityCalibrationStore.calibrate()`
  prefers isotonic; binned/domain remain the fallback.
- **No verdict regression:** development **41/41, 100%, Brier 0.095** (unchanged);
  Q8 diagnostic 89.5%, MCC 0.797, Brier 0.107 (not degraded). 22/22 calibration
  unit tests pass.
- UI now states the calibrated probability honestly (a 70% ≈ 7-in-10); the stale
  "ECE ~0.15 / not a probability" wording is removed. `validation_status.py`
  `CONFIDENCE_CAVEAT` updated (single source of truth).
- Rebuild: `python audit/build_compatibility_calibration.py`; measure:
  `python audit/run_compat_calibration.py`.

---

## 2026-05-30: Formation Energy Accuracy + Trust Bug Fixes

**Major improvement:** Composition predictor formation-energy accuracy **MAE 0.473 → 0.304 eV/atom (−36%)**; RMSE 0.753 → 0.454 (−40%).

### Composition predictor (formation energy surrogate)

| Dataset | Metric | Before | After | Status |
|---|---|---|---|---|
| 179 curated (LOO) | MAE (eV/atom) | 0.473 | **0.304** | ✓ In audit |
| 179 curated (LOO) | RMSE | 0.753 | **0.454** | ✓ In audit |
| 179 curated (LOO) | Median error | 0.344 | **0.215** | ✓ In audit |
| 179 curated (LOO) | 50% coverage | 50% | **50%** | ✓ Honest |
| 179 curated (LOO) | 80% coverage | 79% | **80%** | ✓ Honest |
| 179 curated (LOO) | 95% coverage | 94% | **95%** | ✓ Honest |

**Root causes fixed:**
1. **Sparse-discovery model was linear.** ~96% of queries are "sparse discovery" (nearest
   DFT anchor ≥0.5 away in composition space). Phase-16 already swaps in a learned mean
   model there, but it was **linear ridge** (MAE 0.202 on 2498 held-out MP materials).
   Replaced with **RandomForest** (n=150, depth=14, fit on leak-free Phase-16 calibration split):
   **held-out MAE 0.133** (−34%), **transfer MAE to 179-set: 0.300** (−31% vs ridge 0.434).
   7 MB compressed; loads lazily with graceful fallback.

2. **Name-vs-formula parsing bug (trust bug).** The audit predicted from display *name*,
   so `parse_formula("Cordierite")` silently read leading "Co" as **cobalt** → matched
   elemental Co at distance 0 → predicted Ef ≈ 0 (true −3.18) **and labeled it
   "Categorical Ground Truth," the highest-confidence tier.** Added name→formula guard.

3. **Duplicate composition leakage in LOO.** Excluding only by name let near-duplicates
   (GeO₂ / GeO₂_glass) leak the answer. Tightened to strict LOO: exclude by both
   name AND near-identical composition.

**Scope:** Improves **stability/synthesizability screening** (formation energy) only.
Does *not* affect voltage/capacity (Crystal Dreamer property recovery **unchanged at 78%**).

**Testing:** 261 composition unit tests pass; Crystal Dreamer recovery unchanged;
production path (MP cache) works without error. Artifacts: `composition_engine/sparse_mean_model.py`,
`data/calibration/phase16_sparse_rf.joblib`, `data/calibration/phase16_sparse_rf_report.json`.

**Interval recalibration:** Refit `formation_energy_conformal.json` to the improved model.
Conformal factors *tighter* (3.06→1.73 @ 50%, etc.) because point predictions are more accurate,
and coverage remains honest at 50/80/95%.

**Development benchmark:** Unchanged at 41/41 (100.0%); HDPE+PP label corrected 2026-05-29.
Q8/Q9 unchanged; Q10 still sealed.

---

## 2026-05-29: Focused Research-Grade Audit State

**Audit posture changed:** full-tree pytest is not the product metric for this
dirty multi-project repo. Do not use unrelated AIMO, cyber/Mythos,
OpenTargets/drug, root debug, or old generic categorical/math failures to judge
the chem/materials system. Run focused shards for the chem product only.

### Compatibility audit state

| Dataset | Evaluated | Result | Use |
| :--- | :--- | :--- | :--- |
| Development | 41/41 | 100.0%, Brier 0.095 | Regression only |
| Extended curated | 215/215 | 214/215 = 99.5%, AUROC 0.971, Brier 0.111, ECE 0.174 | Regression only |
| Q8 frozen blind | 30/40 scored | 70.0%, AUROC 0.700, AP 0.882, Brier 0.259, ECE 0.256 | Spent diagnostic |
| Q9 initial blind diagnostic | 40/40 scored | 32/40 = 80.0%, TP=27, TN=5, FP=4, FN=4 | Spent diagnostic |
| Q9 after chi_c integration | 40/40 scored | 35/40 = 87.5%, AUROC 0.9247, Brier 0.0987, ECE 0.1486 | Spent diagnostic |

Q8 exposed coverage and calibration failures. Q9 confirmed useful per-domain
performance outside polymers: metals, ceramics, semiconductors, and cross-domain
interfaces are materially stronger than polymer blends. Polymer compatibility is
the weak domain and should be marked experimental until the Flory-Huggins
critical-chi model is implemented.

### Q10 holdout control

Created the unlabeled pair file:
`audit/external_blind/compatibility_2026_q10_pairs_unlabeled.json`.

- Pair count: 40.
- Labels in file: 0.
- Exact duplicate identities against Q8/Q9: 0.
- Pair SHA256:
  `4d5f6fd414eae277493e6b8f2ceebedfcdb8add6989c910d45959d0ded0c1003`.
- Hidden label file present:
  `audit/external_blind/compatibility_2026_q10_labels_hidden.json`.
- Hidden label SHA256:
  `e1ad2c309443426352a167352ec46cf35f1bd5af6c1fc1b61bacf7826d05501e`.

Codex did not inspect the hidden label JSON. Do not run or score Q10 now. Q10
should be used once, after the team explicitly decides the polymer model is
ready for a final check.

### Focused regression status

Recent focused shards passed after the composition, MP search, workbench, cell
veto, and structure-predictor fixes:
- Composition parser/MP/structure: 113 passed.
- Formation/calibration: 48 passed.
- Predictor/properties/designer: 85 passed.
- Battery/cell design: 58 passed.
- Discovery/API contracts: 6 passed.
- Domain bridge shard: 651 passed.
- Molecular/cross/synthesis shard: 316 passed.
- PFAS shard: 134 passed.
- MOF shard: 108 passed.

### Polymer chi_c integration status

Integrated the G-docs Flory-Huggins prototype into production polymer logic:

- New `polymer_bridge/flory_huggins.py`.
- Representative MW / repeat-unit data for key polymers.
- PPO material added.
- Empirical compatibility overrides for known engineering pairs:
  PS/PPO, PC/ABS, PTFE/PEEK, PPS/PTFE.

Focused verification:

- `python -m pytest polymer_bridge\tests -q` -> 111 passed.
- Development audit -> 40/41, with the only miss being the stale HDPE/PP label.
- Q9 spent diagnostic -> 40 evaluated, 0 skipped, TP=27, TN=8, FP=1, FN=4,
  accuracy 87.5%, balanced 88.0%, precision 96.4%, recall 87.1%, MCC 0.692,
  AUROC 0.9247, AP 0.9745, Brier 0.0987, ECE 0.1486.

---

## 2026-05-28: STT Wiring Repair, Formal Evidence Chain, Audit Reports

**Audit result: 41/41, 100.0%, Brier 0.095 — unchanged from 2026-05-27.**

### What changed

**STT runtime fix** — `oracle/simplicial_strategies.py`:
- Domain category was being built 3× per compatibility query and discarded.
  Now built once, cached in `_DOMAIN_CATEGORY_CACHE`, passed to all three
  STT strategies via `oracle/compatibility_ensemble.py`.
- Vote scores and ensemble weights **unchanged** — no benchmark impact.

**Formal Yoneda evidence** — new in every `simplicial_yoneda` vote metadata:
- `yoneda_proof`: representable presheaves Hom(−,A) and Hom(−,B), sieve
  distance `d = |Δ|/|∪|`, presheaf overlap, isomorphism verdict, proof steps,
  shared-source table with per-direction confidence values.
- `fibration_transport`: per-path strength, shared property features, reasoning.
- `rezk_equivalence`: isomorphism witness with shared relation count, transport
  morphisms, logic chain.

**New module** — `reports/compatibility_report.py`:
- Domain-aware narration registry for battery, polymer, metal, ceramic,
  semiconductor, glass, MOF.
- `build_compatibility_report()` → `CompatibilityAuditReport` dataclass.
- `render_markdown()` → two-track report (chemistry narrative + math backing).
- `report_to_dict()` → JSON audit trail.

**UI** — `streamlit_app/pages/1_Compatibility_Checker.py`:
- Download Report (Markdown) and Download Audit Trail (JSON) buttons.
- Chemistry-domain labels on all STT evidence expanders.
- Formal proof steps and shared-source table visible in UI.

**Bug fix** — `domains/bio/loader.py`: added `List` to typing imports
(pre-existing `NameError` prevented Compatibility Checker from loading).

### Audit posture unchanged
- Development: 41/41, 100.0% (re-verified 2026-05-28).
- Q8: frozen, unreported. Do not run.

---

## 2026-05-27: Integration, Q8 Freeze, and Workbench Repair

**Outcome**: Data-driven calibration of STT weights and freezing of the Q8 blind benchmark.

### Performance Tuning
- **STT Calibration**: Performed grid search across 41 dev pairs. Optimized weights: `simplicial_yoneda=0.75`, `fibration_transport=0.25`.
- **Q8 Freeze**: Frozen `audit/external_blind/compatibility_2026_q8.json` with 40 new pairs (2024-2026 literature).

### Structural Completion
- **Rezk Equivalence**: Full implementation of `RezkEquivalenceStrategy` for exact material substitution.
- **Cross-Domain Functors**: Formalized functor architecture for reasoning between material domains.
- **Workbench Repair**: Fixed API/UI import contracts and workbench schema mismatches found during verification.

### 2026-05-27 Final Metrics
- **Development Accuracy**: `100.0%` (Pass).
- **System Consistency**: Focused API compatibility tests pass; Q8 remains unreported.

---

## 2026-05-27: Integration & Simplicial Enhancement

---

## 2026-05-22: IV-CHEM Synchronization

### Physical Grounding Fix
- **Issue**: Si-O bond plausibility was incorrectly flagged as WARN in master audit.
- **Root Cause**:CDF-centrality was a poor metric for empirical Gaussian distributions.
- **Fix**: Switched to **normalized Gaussian typicality** for empirical `mean/std` pairs.
- **Result**: Si-O plausibility at 1.62 Å increased from 0.74 to 0.95. Master audit **PASS**.

---

## Metrics Breakdown (2026-05-22)

| Dataset | Evaluated | Accuracy | Status |
| :--- | :--- | :--- | :--- |
| **Development** | 41 | 100.0% | Pass |
| **Q6 (Blind)** | 35 | 100.0% | Pass (Spent) |
| **Q7 (Blind)** | 35 | 91.4% | Pass (Spent) |
| **Q8 (Blind)** | 40 | Not run | Current frozen holdout |

---

*KOMPOSOS-IV-CHEM | james Hawkins | 2026*
