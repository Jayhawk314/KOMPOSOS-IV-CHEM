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

## Current Audit Posture (Updated 2026-05-30)

### Formation Energy Predictor (2026-05-30 improvement)
- **Accuracy:** MAE **0.304 eV/atom** (was 0.473, −36%); RMSE 0.454 (−40%); median error 0.215 (−37%)
- **Model:** Sparse-discovery tier (~96% of queries) now uses **RandomForest** (was linear ridge);
  trained on leak-free Phase-16 MP calibration split (2502 materials), held-out validation
  error: 0.133 eV/atom (vs 0.202 for ridge).
- **Bug fixes:** (1) Name-vs-formula parsing (predict("Cordierite") was read as "Co" → cobalt);
  (2) Duplicate composition leakage (now strict LOO: exclude by name AND composition).
- **Calibration:** Intervals recalibrated to 50/80/95% coverage (exact); conformal factors
  tighter due to better point estimates.
- **Scope:** Improves stability/synthesizability screening (formation energy), *not*
  voltage/capacity (Crystal Dreamer unchanged at 78% property recovery).
- **Audit:** `python audit/run_predictor_accuracy.py`, `composition_engine/experiments/forward_model_bench.py`.

### Compatibility & Development Benchmarks
- `audit/dataset_registry.json` is the source of truth for external blind roles.
- **No dataset is currently blind** (`current_blind_version: null`). Q2–Q8 are all
  `spent_diagnostic`. Q8 was demoted from current_blind to spent_diagnostic on
  2026-05-29 (its skip/fail cases were inspected; 14/40 pairs overlap existing
  identities — never a clean holdout). **Never report any Q8 number as a blind claim.**
  Freeze Q9 (uninspected recent-literature pairs) before the next blind validation claim.
- Development benchmark: `41/41`, `100.0%`, `0` skips, Brier 0.095. (Re-verified
  2026-05-30 after relabeling HDPE+PP polymer pair to immiscible/incompatible — the
  Flory-Huggins veto correctly flags it; prior `true` label was thermodynamically wrong.)
- Q8 spent-diagnostic latest run: 89.5% (TP22/TN12/FP0/FN4), MCC 0.797, Brier 0.107 —
  coverage/error-family regression tracking only, NOT a blind claim.
- Q10 is the sealed final exam (labels hashed/hidden); do not score until ready.

### Compatibility Confidence Calibration (2026-05-30)
- Compatibility scores are mapped to a **calibrated probability** via a global
  **isotonic** calibrator (chosen over raw/Platt by out-of-sample ECE in
  `audit/fit_compat_calibration.py`). Honest k-fold **OOS ECE 0.072** (Brier 0.049),
  down from raw ECE ~0.194. A 0.70 now means ~70% of such pairs are compatible.
- Built by `audit/build_compatibility_calibration.py` (dev + spent diagnostics only,
  leak-controlled; current-blind excluded), stored as monotonic (x,y) breakpoints in
  `audit/calibration/compatibility_calibration_2026_q4_dev.json`. Runtime
  (`oracle/compatibility_calibration.py`) interpolates them dependency-free and prefers
  isotonic; binned/domain calibrators remain the fallback. Dev verdicts unchanged.
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
