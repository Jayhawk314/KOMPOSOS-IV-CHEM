# Codex Review of G-docs - 2026-05-29

This folder is useful, but it needed reconciliation with the focused
research-grade audit state in `docs/`.

## What G-docs Is

- A documentation and prototype workspace created by Gemini.
- Useful for architecture explanation, polymer chi_c design, CRYSTAL pipeline
  sketches, and lightweight smoke diagnostics.
- Not the canonical source for research-grade metrics. Canonical metric framing
  lives in `docs/Q9_PER_DOMAIN_RESULTS_2026-05-29.md`,
  `docs/RESEARCH_GRADE_REMEDIATION_PLAN_2026-05-29.md`,
  `docs/TUNING_LOG.md`, and `docs/AUDIT_CHANGE_LOG.md`.

## Fixes Applied

- Repaired Windows console crashes in all G-docs test scripts by forcing UTF-8
  stdout.
- Fixed `deep_audit.py` to instantiate `CogEngine` with a `CogSession`.
- Fixed `prototype_polymer_chi.py` so the PS/PPO miscible control is actually
  predicted compatible through an empirical chi override.
- Corrected G-docs metric language so Q8 AUROC `0.9038` is described as a
  post-remediation diagnostic artifact, not a fresh blind claim.
- Integrated the polymer prototype into production as
  `polymer_bridge/flory_huggins.py` with MW/N-based `chi_c`, HSP chi fallback,
  PPO, and empirical compatibility overrides for common engineering pairs.
- Fixed `compute_auroc_chem.py` so it prints the dataset version from the audit
  report instead of hard-coding Q8.

## Scripts Re-run

- `python G-docs/tests/system_audit.py` passed structural presence checks.
- `python G-docs/tests/ui_feature_audit.py` reported 4/4 UI/core checks.
- `python G-docs/tests/deep_audit.py` reported 5/5 architectural checks.
- `python G-docs/tests/prototype_polymer_chi.py` rejected ABS/PVDF and PA66/PEO
  while keeping PS/PPO compatible via empirical chi.
- `python G-docs/tests/prototype_crystal_pipeline.py` demonstrated the toy
  Goldschmidt tolerance veto.
- `python G-docs/tests/compute_auroc_chem.py` reported AUROC `0.9038` from
  `audit/audit_report_2026-05-29.json`.

After production chi_c integration, the same AUROC script reports Q9
`external_blind.compatibility.2026_q9.labeled.v1` AUROC `0.9247` from the
current audit artifact.

## Metric Caution

The old stored Q8 artifact reported 38/40 evaluated, 2 skipped, accuracy
`86.8%`, AUROC `0.9038`, Brier `0.119`, ECE `0.117`. The current generic audit
artifact has since been regenerated from Q9 after chi_c integration. Both Q8 and
Q9 are spent diagnostics and must not be used as headline fresh-blind results.

Q10 is the future exam. Codex has not inspected
`audit/external_blind/compatibility_2026_q10_labels_hidden.json`.
