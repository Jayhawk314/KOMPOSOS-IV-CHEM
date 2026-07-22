# CLAUDE.md - KOMPOSOS-IV-CHEM

## Project Identity

KOMPOSOS-IV-CHEM applies a categorical AI runtime to chemistry and materials discovery.

Primary long-term purpose: chemistry-first inverse design across molecular,
materials, and interface domains, including batteries, polymers, metals,
ceramics, semiconductors, glass, MOFs, and broader green-chemistry material
design.

Current working capability: advanced chemistry/material compatibility reasoning
with categorical runtime orchestration, domain bridges, dual-engine CAT+ZFC
constraint checks, cross-bridge analysis, audit harnesses, and MOF/linker
generation support.

Current audit rule: code and frozen audit artifacts outrank stale docs. Always
name the benchmark file, validation protocol, and whether a dataset is
`development`, `spent_diagnostic`, or `current_blind`.

Author: James Ray Hawkins
License: Apache 2.0 / Commercial dual license
Python: 3.10+

## Read First

1. `audit/dataset_registry.json`
2. `docs/AUDIT_PROTOCOL.md`
3. `docs/TUNING_LOG.md`
4. `docs/AUDIT_CHANGE_LOG.md`
5. `KOMPOSOS_COMPLETE_SYSTEM_GUIDE.md`
6. This file

## Current Audit Posture (Updated 2026-07-20)

### Copper-sulfide veto narrowed to sulfur CATHODES only (2026-07-21)
- The collector veto added 2026-07-20 fired on any Cu-collector pair whose
  partner had sulfur in its formula. That was over-broad: it vetoed **Cu+LiTFSI**
  (a false positive — sulfonyl sulfur does not sulfidize Cu) and **Cu+Li3PS4/LGPS**
  (a likely false negative — Cu is the standard anode-side collector against
  sulfide solid electrolytes).
- Now requires the sulfur-bearing partner to be a **cathode active material**
  (`material_class == CATHODE`), i.e. the undisputed elemental-S/polysulfide
  case. Cu+S8 still vetoed; Cu+{Li3PS4, LGPS, LiTFSI} now viable. Dev 41/41,
  calibration byte-identical (no affected pair is in the corpus).

### Veto scores use an ORDER-PRESERVING squash, not a clamp (2026-07-20, corrected)
- The first version of the fix below used `min(total, 0.35)`. That eliminated the
  inversions but **collapsed 105 of 365 pairs (28.8%) onto exactly 0.35**,
  leaving only **14 distinct scores across 168 rejected pairs** — manufacturing
  precisely the constant, non-discriminating score this codebase treats as a
  defect elsewhere, and flattening the ranking that PFAS/discovery triage uses.
- Replaced with `_vetoed_score(total) = 0.35 * total`: strictly monotone, so a
  vetoed pair strong on its other axes still outranks a weak one, while still
  guaranteed below the threshold. Distinct scores among rejected pairs
  **14 -> 64**; overall distinct 132 -> 182. Inversions still 0, accuracy still
  0.9151, dev still 41/41.
- **Correction to an overclaim:** the clamp's headline "OOS ECE 0.045" was
  **partly an artifact** — 93 identically-scored incompatible pairs are trivially
  easy for an isotonic calibrator to fit. Honest current figures with the squash
  are **OOS ECE 0.055, Brier 0.054** (historical baseline was 0.072/0.049, so ECE
  improved and Brier is marginally worse). Prefer the squash anyway: the ~0.010
  ECE difference was illusory, the ranking information is real.
- Follow-up not done: `ceramic` and `polymer` still hard-clamp (0.35/0.38/0.45),
  which is why 49 pairs still tie at 0.35. Converting them would change
  long-standing, documented, benchmarked veto values, so it needs its own change.

### Vetoes now annihilate the SCORE, not just the verdict (2026-07-20)
- Fixed a systemic inconsistency: `metal`, `glass`, `semiconductor` and 4 of 5
  `battery` vetoes set `viable = False` **without lowering `total`**, so the
  surfaced number contradicted the verdict next to it (Ni+Fe 0.721 -> incompatible
  while Al+Fe 0.674 -> compatible). `ceramic` and `polymer` were already correct.
- All bridges now cap a vetoed score via `VETO_SCORE_CAP = 0.35` (below the 0.50
  threshold), applying the project's own rule that **a physical block survives
  composition (min/annihilator), including in the reported score**.
- **Zero verdicts changed.** Corpus accuracy is identical (0.9151 on 365 dev +
  spent pairs) and dev stays 41/41; only the reported numbers moved.
  Score/verdict inversions went **13 -> 0**; min compatible score 0.502 vs max
  incompatible 0.473, cleanly separated by the threshold.
- Knock-on benefit: dev Brier 0.095 -> **0.086**, and the isotonic calibrator
  (rebuilt, since raw scores shifted) improved to **5-fold OOS ECE 0.045**
  from 0.072. A high raw score attached to an incompatible verdict was itself a
  calibration failure.
- Pinned by `tests/test_veto_score_consistency.py`, including a corpus-wide
  no-inversion test so this cannot silently regress.

### MLIP (CHGNet) oracle added as a typed tier (2026-07-20)
- `oracle/mlip_integration.py`. On 294 held-out materials **MAE 0.134 eV/atom vs
  0.404** for the composition surrogate (3.0x lower; MLIP closer on 77.6%).
  See `docs/MLIP_ORACLE_2026-07-20.md`;
  `python audit\run_mlip_benchmark.py --relax`.
- **Do NOT compare 0.134 to the 0.416 headline.** Different material sets: 0.416
  is the 179-material strict formula-LOO benchmark; this is cubic
  fully-determined prototypes only. The like-for-like number is the surrogate's
  **0.404 re-scored on the same 294 materials**.
- **An MLIP is a SURROGATE of DFT, never DFT.** Typed `Family.SURROGATE`;
  crossing to `PBE_MP` requires the explicit `MLIP_TO_PBE_MP` conversion, which
  adds uncertainty. Without the backend it raises `OracleUnavailable` and never
  falls back to the composition surrogate under an MLIP label.
- **Requires a 3D structure** — a capability boundary, not a bug. The MP cache
  has lattice parameters but no coordinates, so only 759 of 103,644 entries have
  a fully determined prototype. Prototypes with free internal parameters
  (rutile/wurtzite/spinel/corundum) are excluded, not guessed.
- **Relaxation is mandatory for a meaningful number**: unrelaxed idealized
  prototypes gave a train residual of 0.670 eV/atom; relaxing dropped it to
  0.117. Always run `--relax`.
- Optional dependency (`pip install chgnet`, offline-capable). Not yet wired into
  Crystal Dreamer, discovery, or compatibility — deliberately a separate change,
  and no claim is made that it improves any downstream verdict.

### Category theory does NOT contribute predictive accuracy (2026-07-20)
- Ablation over **374 development + spent-diagnostic pairs**: removing the
  categorical layer changes accuracy by **0.0000** and MCC by **0.0000**.
  See `docs/CT_ABLATION_2026-07-20.md`; rerun with
  `python audit\run_ct_ablation.py --json audit\ct_ablation_report.json`.
- **Yoneda transfer guard / strategy ensemble is REPORTING ONLY.**
  `build_compatibility_ensemble` is called only from
  `_compatibility_decision_metadata`, never in the scoring path — verified by
  source inspection. It cannot affect a verdict by construction.
- **Typed morphisms** *can* overwrite score/verdict on 8 domain routes, but on
  this corpus they perturbed **1 pair of 374** (GaN+SiC_4H, 0.750→0.760) and
  flipped **zero** verdicts.
- **Never claim** that category theory improves accuracy, that the benchmarks
  validate the categorical runtime, or that CT explains the compatibility
  results. The numbers come from the domain bridge scorers. Physical vetoes live
  in the **bridges**, not the CT layer.
- Still defensible (untested by this experiment, so state them as architecture,
  not results): typed composition, provenance/receipts, transfer guards, dataset
  -role discipline, veto algebra. The ablation does not cover cross-domain
  transfer, discovery, or the separate bio repurposing path.
- Q12 was excluded; the script reads the registry to block whatever is currently
  `current_blind` rather than a hardcoded name.

### Scorer remediation + Q11 spent + Q12 frozen (2026-07-20, later same day)
- Q11's three root causes were fixed on independent/dev pairs, then Q11 was
  re-run **once** as regression and **demoted to `spent_diagnostic`**.
  See `docs/SCORER_REMEDIATION_2026-07-20.md`.
- **Correct answers did not increase: 23/40 before and after.** Four genuine
  fixes were gained; four previously-correct answers became honest abstentions
  (they had been right only because a constant 0.45 matched an incompatible
  label by base rate). Errors fell 13→10, MCC 0.278→0.401, Brier 0.279→0.220.
  **Never quote the 63.9%→69.7% accuracy rise alone** — the denominator shrank
  from 36 to 33 because the bridge now declines organic-solvent resistance.
- Correction to the earlier diagnosis: the polymer/solvent path was **not**
  "inverted." It correctly implemented the *dissolution* question (PVDF+NMP,
  CMC+water). The defect was that **resistance intent was unrepresentable**.
  Dissolution remains the default; resistance is now explicit, answered from
  curated water-uptake data (7/7) and **abstaining** for organic solvents,
  because Hansen distance alone separates resistance at only 22/30.
- **`Q12` is the current blind benchmark and is UNSCORED.** 36 pairs, **12
  contrast groups** (two pairs sharing a material with opposite answers) —
  the direct lesson from Q11, since a constant fallback cannot pass a contrast
  group. Zero overlap with all 525 prior pairs. **Q10 still sealed, never used.**
- Still broken on purpose (not patched toward Q11 labels): metal-semiconductor
  interdiffusion (Bi2Te3+Cu == Bi2Te3+Ni), salt identity in collector
  passivation (Al_foil+LiTFSI == Al_foil+LiPF6), polysulfide/carbonate attack,
  non-monotonic score-vs-verdict, ceramic co-sintering reactivity, glass/metal
  CTE sealing.

### Q11 blind result supersedes the compatibility headline (2026-07-20)
- **There is now current blind compatibility evidence, and it is 63.9%**
  (36 evaluated, 4 skipped, MCC 0.278, Brier 0.279, ECE 0.177, protocol FAIL).
  See `docs/Q11_BLIND_RESULT_2026-07-20.md`. **Do not lead with development
  41/41 or the ~87–90% spent diagnostics as if they indicate generalization** —
  Q11 shows they do not.
- **Calibration scope narrowed:** isotonic OOS ECE 0.072 was measured on
  dev + spent-diagnostic pairs; **blind ECE is 0.177**. Describe the calibrator
  as calibrated *on that distribution*, not generally.
- Known error mechanisms (each confirmed on independent probe pairs, not on Q11):
  solvent-exposure/chemical-resistance roles are missing from
  `COEXISTENCE_INTERFACE_ROLES` so the blend immiscibility veto fires inverted
  (10 of 12 probe polymer+solvent pairs return an identical 0.45); battery
  current-collector identity is ignored (Al_foil vs Cu_foil changes nothing);
  cross-domain pairs skip on "Unknown material" when the partner lives in
  another bridge.
- **Q11 is still `current_blind`.** Seeing the results did not spend it;
  remediating against them will. Fix on independent/dev pairs, then re-run Q11
  once as regression, demote it to `spent_diagnostic` in that same commit, and
  freeze Q12. **Q10 remains sealed and unspent.**
- New tool: `python audit\merge_sealed_labels.py --period <p> [--check-only]`
  verifies both SHA256 seals before merging hidden labels for scoring.

## Prior Audit Posture (Updated 2026-07-17)

### July 2026 executable-audit corrections
- Current `python audit/run_predictor_accuracy.py` result is **MAE 0.416
  eV/atom**, RMSE 0.552, median 0.340 on 179 strict formula-deduplicated LOO
  cases. The older 0.304 headline below is a historical May result and must not
  be presented as current performance.
- Formation-energy conformal factors were regenerated on 2026-07-17 after
  prediction/artifact drift. Current deployed interval coverage is 50/79/95%;
  5-fold OOS calibration coverage is 49/80/94%.
- Q9 is a **spent diagnostic** (initial 32/40; later 35/40 after inspected-error
  remediation) and is now recorded in `audit/dataset_registry.json`. Q10 remains
  sealed and unscored. There is still no current blind compatibility dataset.
- Battery optimizer active-material pools now use `CATHODE_MATERIALS` and
  `ANODE_MATERIALS`; the former class-based filter incorrectly admitted Al foil
  as a cathode and Cu foil as an anode. The 103K discovery path's index/API
  integration was also repaired.
- Workbench "ZFC" wording was corrected: composition feasibility uses a
  pymatgen charge-balance/oxidation-state gate. It is deterministic but is not
  an independent ZFC proof. Multi-domain aggregate scores are no longer passed
  through the pairwise compatibility calibrator, and missing interface coverage
  is surfaced explicitly.

### Physical Vetoes in Verdicts (2026-06-02)
- **MOF pore access is now a hard veto** (`mof_bridge/interaction_scoring.py`,
  `interface_validator.py`): a guest that physically cannot enter the pore
  (aperture ratio < 0.8) sets `ScorerResult.veto`, which **annihilates** the
  composite (`suitable=False`, `total=0`) instead of being diluted to 10% of a
  25%-weighted term. Previously a pore-blocked MOF could still be ruled suitable
  on thermal/chemical/mechanical merit. Mirrors the polymer Flory-Huggins veto:
  **a true physical block survives composition (min/annihilator), not weighted sum.**
- **Crystal Dreamer mandatory targets** (`composition_engine/designer.py`):
  `PropertyTarget` gains `mandatory: bool`. A missed mandatory target zeroes
  `overall_score` so a hard requirement can no longer be averaged away by other
  satisfied targets. **Off by default** — existing specs/behavior unchanged.
- **Current audit posture:** MOF funnel benchmark reproduced at **AUROC 0.8843,
  recall@22 0.95** (`python -m mof_bridge.benchmark.run`). The historical Crystal
  Dreamer **7/9** recovery run did not complete within the 2026-07-17 interactive
  audit window, so do not promote it as a current reproduced headline.

### Formation Energy Predictor (historical 2026-05-30 result; superseded above)
- **Historical result:** MAE 0.304 eV/atom, RMSE 0.454, median 0.215. Do not
  present this as the current executable-audit result; current is 0.416/0.552/0.340.
- **Model:** Sparse-discovery tier (~96% of queries) now uses **RandomForest** (was linear ridge);
  trained on leak-free Phase-16 MP calibration split (2502 materials), held-out validation
  error: 0.133 eV/atom (vs 0.202 for ridge).
- **Bug fixes:** (1) Name-vs-formula parsing (predict("Cordierite") was read as "Co" → cobalt);
  (2) Duplicate composition leakage (now strict LOO: exclude by name AND composition).
- **Calibration:** Current regenerated intervals cover 50/79/95% in the deployed
  LOO pool and 49/80/94% in 5-fold OOS calibration.
- **Scope:** Improves stability/synthesizability screening (formation energy), *not*
  voltage/capacity. Crystal Dreamer recovery remains quarantined pending a fresh
  recorded run.
- **Audit:** `python audit/run_predictor_accuracy.py`, `composition_engine/experiments/forward_model_bench.py`.

### Compatibility & Development Benchmarks
- `audit/dataset_registry.json` is the source of truth for external blind roles.
- **No dataset is currently blind** (`current_blind_version: null`). Q2–Q8 are all
  `spent_diagnostic`. Q8 was demoted from current_blind to spent_diagnostic on
  2026-05-29 (its skip/fail cases were inspected; 14/40 pairs overlap existing
  identities — never a clean holdout). **Never report any Q8 number as a blind claim.**
  Q9 is also spent diagnostic. Q10 is sealed and unscored; do not claim a
  current blind result.
- Development benchmark: `41/41`, `100.0%`, `0` skips, Brier 0.095. (Re-verified
  2026-05-30 after relabeling HDPE+PP polymer pair to immiscible/incompatible — the
  Flory-Huggins veto correctly flags it; prior `true` label was thermodynamically wrong.)
- Q8 spent-diagnostic latest run: 89.5% (TP22/TN12/FP0/FN4), MCC 0.797, Brier 0.107 —
  coverage/error-family regression tracking only, NOT a blind claim.
- Q10 is the sealed final exam (labels hashed/hidden); do not score until ready.

### Compatibility Confidence Calibration (2026-05-30)
- Pairwise compatibility scores are mapped to a **calibrated probability** via a global
  **isotonic** calibrator. Rebuilt 2026-07-20 after the veto-score changes moved
  the raw distribution: 5-fold **OOS ECE 0.055, Brier 0.054** (vs raw 0.159).
  The historical baseline was 0.072/0.049 — so ECE improved and Brier is
  marginally worse. An intermediate clamp design showed 0.045 but that was
  partly an artifact of a 93-pair identical-score mass point; do not quote it.
  A 0.70 means ~70% of such pairs are compatible.
- Built by `audit/build_compatibility_calibration.py` (dev + spent diagnostics only,
  leak-controlled; current-blind excluded), stored as monotonic (x,y) breakpoints in
  `audit/calibration/compatibility_calibration_2026_q4_dev.json`. Runtime
  (`oracle/compatibility_calibration.py`) interpolates them dependency-free and prefers
  isotonic; binned/domain calibrators remain the fallback. This is not a fresh
  blind or domain-specific result, and it must not be applied to multi-interface
  aggregate scores. Dev verdicts unchanged.
- Rebuild: `python audit/build_compatibility_calibration.py`; measure:
  `python audit/run_compat_calibration.py`.

### Role-Aware Polymer Gate & Cell-Aware PFAS Report (2026-05-31)
- **Role-aware polymer interface gate** (`polymer_bridge/interface_validator.py`):
  `validate*` accept `interface_role`. For coexistence/dispersion roles
  (`COEXISTENCE_INTERFACE_ROLES`: binder, separator, coating, seal, liner, ...) the
  Flory-Huggins **immiscibility veto is skipped** and solubility is down-weighted
  (`coexistence_focus` weights); blend/unknown roles keep the strict veto. This fixes
  use-inappropriate false negatives (CMC+SBR, CMC/PP — co-used as dispersions) **without**
  changing blend behavior (HDPE/PP still vetoed) or the dev benchmark (**41/41, Brier 0.095**).
  Role is threaded from the replacement use-case (`_USECASE_TO_INTERFACE_ROLE` in
  `pfas_bridge/replacement_scorer.py`) and auto-passed by `compatibility_service._call_validator`.
  Rule of thumb: **immiscibility only means incompatibility for single-phase/blend
  interfaces** — not dispersions, coatings, or coexisting parts.
- **Client report is now cell-aware** (`reports/pfas_report.py` + `pfas_pdf.py`, v1.3.0):
  replacements scored against the whole clean cell via `find_replacements_for_cell`;
  weakest-interface **bottleneck governs the verdict**; new **REVIEW** verdict (cell fit
  unscorable → manual review; never promoted to VALIDATED on standalone score). The
  regulatory section is **date-free** (qualitative timeframe + status) on purpose — do
  not re-introduce hardcoded deadlines. Corrected deadline reference (for your notes, not
  baked into deliverables): `go_to_market/pfas/COMPLIANCE_CLOCK_2026.md`.
- **PFAS replacement *ranking* is triage, not validated** — no held-out baseline yet, and
  the isotonic calibrator has poor resolution in the raw 0.35–0.55 band. See
  `go_to_market/pfas/GO_TO_MARKET.md` §5 backlog.

### Tests Are Now Tracked (2026-05-31)
- The blanket `test_*.py` `.gitignore` rule (which silently kept the **whole suite**
  out of version control) was removed; chem/compat test suites are committed. The
  materials **bridge dirs are still gitignored** — new files there need `git add -f`
  (see the bridges-footgun note). Cyber/mythos + aimo tests are intentionally untracked.

### MOF Directed Generation (2026-05-30)
- `mof_bridge/linker_generator.py` `generate_candidates` accepts `strategy_weights`
  (substitution/modification/template mix), `seed_smiles` (pin to derivatives of one
  molecule; disables the template strategy), and `required_groups` (hard SMARTS filter
  + biases template selection). Threaded through `LinkerScreeningSpec` and the MOF
  Designer UI ("Directed Generation Controls"). Turns random discovery into directed
  optimization. Grounded funnel (~94% recall on real linkers, AUROC 0.88) unchanged.

### PFAS → Cell-Compatible Alternatives (2026-05-30)
- `pfas_bridge/replacement_scorer.py` `find_replacements_for_cell()` scores each
  PFAS-free replacement against every adjoining material and surfaces the **calibrated
  bottleneck** (weakest interface): output is "PFAS-free AND compatible with your cell."
  Surfaced in PFAS Scanner Tab 1. (e.g. CMC+SBR is high-quality but its NMC811 interface
  fails, so PAN is correctly promoted for a full NMC cell.)

### Core Architecture
- STT reasoning (Yoneda, Fibration, Rezk) is integrated, calibrated, and wired:
  domain category is built once per process (cached), passed to all three strategies,
  and formal Yoneda presheaf evidence is surfaced in vote metadata and audit reports.
- Audit reports: `reports/compatibility_report.py` generates domain-aware Markdown +
  JSON reports from any compatibility workflow result.
- System integrity: `InferenceStrategy` supports both III-style Store and IV-style Category via `Morphism` aliases.
- Bio domain loader: `domains/bio/loader.py` List import fixed (pre-existing NameError).

## Runtime Rule

- Categorical runtime is primary.
- Domain bridges are evidence providers.
- ZFC is active and required as a dual-engine constraint layer.
- Gray coherence, typed morphisms, Yoneda transfer, failure-memory gates, and
  calibration are bounded guards around bridge decisions.

## Canonical Audit Commands

```powershell
python audit\run_audit.py --module development
python audit\run_audit.py --module external
python audit\run_audit.py --module external --external-path audit\external_blind\compatibility_2026_q8.json
python audit\run_master_audit.py
```

## Physical Grounding Rule

- Do not "fix" physical grounding by weakening thresholds unless the empirical
  bond source itself is wrong.
- The acceptable fix is to correct the plausibility mapping from the empirical
  distribution.
- Current implementation uses normalized Gaussian typicality for empirical bond
  stats and fallback CDF-centrality only for bounds-only cases.

## Session Summary File

Keep a local session summary in `SESSION_SUMMARY.md` when a long audit/porting
session changes benchmark state, runtime wiring, or audit claims.
