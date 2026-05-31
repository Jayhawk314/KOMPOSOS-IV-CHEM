# Session Changes Log (2026-05-29)

> **Later sessions (2026-05-30):** see `SESSION_SUMMARY_2026-05-30_Workbench.md` (Advanced
> Triage Workbench) and the root `SESSION_SUMMARY.md` (directed MOF generation, isotonic
> compatibility calibration, PFAS cell-fit). Note: the "Q8 blind set" referenced below was
> **demoted to spent_diagnostic on 2026-05-29** — no dataset is currently held blind.

This document tracks all files created, modified, or evaluated during this session.

## 1. Directory Creation
- Created `G-docs/` to isolate documentation and prototype work.
- Created `G-docs/tests/` for prototype scripts and custom audits.

## 2. Documentation Authored (`G-docs/`)
- `ARCHITECTURE.md`: Documented the 3-layer categorical runtime, unified `compatibility_service.py`, and STT strategies.
- `MATHEMATICAL_FOUNDATIONS.md`: Deep dive into $\infty$-cosmos, Yoneda distance, Kan extensions, and Ricci curvature.
- `DATA_PROVENANCE_AND_QUALITY.md`: Defined the strict empirical audit posture (Q8 blind set) and recorded the AUROC metrics.
- `FEATURES_AND_VALUE.md`: Outlined the core UI features and the competitive value of exact constraint satisfaction.
- `LIMITATIONS_AND_FUTURE.md`: Outlined the roadmap for the Flory-Huggins polymer fix and CRYSTAL pipeline.
- `FLORY_HUGGINS_DESIGN.md`: Mathematical specification for the polymer miscibility fix.
- `POLYMER_FIX_INTEGRATION_PLAN.md`: Roadmap for integrating the polymer fix into the active system.
- `CRYSTAL_PIPELINE_DESIGN.md`: Technical design for full 3D structural inverse design using geometric vetoes.
- `PFAS_SCANNER_UPGRADE_DESIGN.md`: Roadmap for transitioning the PFAS scanner to a structural OECD SMARTS detector.
- `DRUG_VS_MATERIAL_DESIGN.md`: Comparative analysis mapping cross-branch synergies between Track A (Drugs) and Track C (Materials).
- `VALIDATION_STRATEGY_MASTER.md`: Defined the "Gold Standard" datasets and metric shapes (AUROC vs. Hits@K) for all current and future pipelines.
- `MEMORY.md`: The central index mapping all created documents.

## 3. Test Scripts & Prototypes (`G-docs/tests/`)
- `deep_audit.py` (Deleted/Replaced): Initial attempt at deep system verification.
- `ui_feature_audit.py`: Successfully verified the presence and wiring of the 4 core chemical UI features.
- `compute_auroc_chem.py`: Extracted and computed the 0.9038 AUROC for the core compatibility system from the Q8 JSON report.
- `prototype_polymer_chi.py`: Proved the Flory-Huggins $\chi_c$ thermodynamic veto correctly identifies immiscible polymer false positives.
- `prototype_crystal_pipeline.py`: Proved the Goldschmidt Tolerance geometric veto stops impossible perovskite structures.
- `prototype_pfas_detector.py`: Evaluated the structural OECD SMARTS rule against 10,776 EPA records (99.53% recall).
- `inject_pfas_bridge.py`: Python script used to inject the structural logic into the active system.

## 4. Live Core System Modifications
- **Modified**: `pfas_bridge/pfas_registry.py`
  - Replaced the static, name-based `is_pfas()` function with the strict RDKit SMARTS structural detector (OECD 2021 rule).
- **Executed**: `audit/run_pfas_audit.py`
  - Audit (corrected, honest edition): **specificity 100% on a 25-molecule hard-negative panel**, **99.5% concordance** with EPA PFASSTRUCT v4 (10,776 SMILES), 4/4 positive controls. Reported as concordance, not independent validation; **no AUROC** (a binary substructure rule has no ROC curve). The earlier "0.9976 AUROC" was balanced accuracy on 8 negatives and was mislabeled.

## 5. Discovery & Crystal Pipeline Research
- **Crystal Dreamer (`5_Crystal_Dreamer.py`)**: Analyzed as a "composition-first" inverse design tool that uses Kan extensions over the Materials Project cache.
- **Discovery Workbench (`9_Discovery_Workbench.py`)**: Analyzed as an orchestration pipeline that chains inverse design, PFAS screening, and compatibility.
- **Composition Predictor Validation**: Ran `composition_engine.predictor` demo, revealing Leave-One-Out (LOO) validation metrics for NMC cathodes (e.g., Voltage error ~1.7%, Theoretical Capacity error ~0.4%).
- **Differentiated Architecture**: 
  - *Crystal Dreamer*: Finds formulas.
  - *Discovery Workbench*: Triages formulas.
  - *Crystal Pipeline*: Maps formulas to 3D structures (The designed upgrade).