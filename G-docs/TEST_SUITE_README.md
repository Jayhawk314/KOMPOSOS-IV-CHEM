# KOMPOSOS-IV-CHEM System Audit Test Suite

This folder contains diagnostic scripts used to verify the architectural integrity and functional coverage of the KOMPOSOS-IV-CHEM system.

These scripts are smoke diagnostics, not research-grade accuracy benchmarks.
They should not replace the focused compatibility, PFAS, formation-energy, MOF,
MP Explorer, or Workbench evaluations recorded in `docs/`.

## Diagnostic Tools

### `system_audit.py`
This script performs a 5-point audit of the current workspace:
1.  **Categorical Integrity**: Verifies the `InfinityCosmos` and `OPTIMUS` kernels are loadable.
2.  **Bridge Coverage**: Checks for the presence of the 8+ domain bridges.
3.  **ZFC Logic**: Validates the ZFC dual-engine's presence and basic rule-set.
4.  **Feature Discovery**: Maps the UI pages to their corresponding backend services.
5.  **Data Provenance**: Verifies access to the local composition database and Materials Project cache status.

### Current observed status (2026-05-29)

- `system_audit.py`: runs on Windows after stdout encoding repair; structural
  presence checks pass.
- `ui_feature_audit.py`: 4/4 UI/core components verified.
- `deep_audit.py`: 5/5 architectural checks verified after passing a
  `CogSession` into `CogEngine`.
- `prototype_polymer_chi.py`: correctly rejects ABS/PVDF and PA66/PEO and
  keeps PS/PPO compatible through an empirical chi override.
- `prototype_crystal_pipeline.py`: demonstrates a toy Goldschmidt tolerance
  veto for BaTiO3/CaTiO3/MgTiO3.
- `compute_auroc_chem.py`: reads the dataset version from
  `audit/audit_report_2026-05-29.json`. After chi_c integration, it reports Q9
  AUROC `0.9247`. This is a spent-diagnostic result, not a fresh blind claim.

## How to run
```bash
python G-docs/tests/system_audit.py
```

---
*G-docs Tests | 2026-05-29*
