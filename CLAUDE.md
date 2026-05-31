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

## Current Audit Posture (Updated 2026-05-28)

- `audit/dataset_registry.json` is the source of truth for external blind roles.
- Current blind benchmark: `audit/external_blind/compatibility_2026_q8.json` (Frozen 2026-05-27)
- Q2-Q7 are spent diagnostic evidence.
- Development benchmark: `41/41`, `100.0%`, `0` skips. (Re-verified 2026-05-30 after
  relabeling HDPE+PP polymer pair to immiscible/incompatible — the Flory-Huggins
  veto correctly flags it; prior `true` label was thermodynamically wrong.)
- Q8 blind benchmark: Active and frozen for next validation claim.
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
