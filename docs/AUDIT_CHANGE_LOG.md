# KOMPOSOS-IV Audit Change Log

*Version IV Categorical Runtime Synchronization*

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
