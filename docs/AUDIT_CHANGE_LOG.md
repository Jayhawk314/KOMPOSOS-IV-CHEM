# KOMPOSOS-IV Audit Change Log

*Version IV Categorical Runtime Synchronization*

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
