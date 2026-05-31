# G-docs: KOMPOSOS-IV-CHEM Documentation Index

This folder contains a comprehensive set of documents describing the KOMPOSOS-IV-CHEM system, its architecture, mathematical foundations, data provenance, and competitive value.

## Documentation Map

1.  **[ARCHITECTURE.md](./ARCHITECTURE.md)**: The 3-layer categorical runtime system (Syntax, Semantics, Refinement) and core components like COG and ZFC engines.
2.  **[MATHEMATICAL_FOUNDATIONS.md](./MATHEMATICAL_FOUNDATIONS.md)**: Deep dive into the $ \infty $-cosmos, Yoneda distance, Kan extensions, and Ricci curvature.
3.  **[DATA_PROVENANCE_AND_QUALITY.md](./DATA_PROVENANCE_AND_QUALITY.md)**: How data is tiered, the audit benchmarks (Q7-Q10), and the logical trace model.
4.  **[FEATURES_AND_VALUE.md](./FEATURES_AND_VALUE.md)**: Analysis of the 8+ UI features, competitive advantages (Zero-shot reasoning, Exact constraints), and current limitations.
5.  **[LIMITATIONS_AND_FUTURE.md](./LIMITATIONS_AND_FUTURE.md)**: The "Polymer Fix" roadmap and the long-term vision for autonomous lab integration.
6.  **[FLORY_HUGGINS_DESIGN.md](./FLORY_HUGGINS_DESIGN.md)**: Mathematical specification for solving the polymer miscibility false positive limitation.
7.  **[POLYMER_FIX_INTEGRATION_PLAN.md](./POLYMER_FIX_INTEGRATION_PLAN.md)**: Step-by-step roadmap and impact analysis for implementing the polymer fix into the active system.
8.  **[CRYSTAL_PIPELINE_DESIGN.md](./CRYSTAL_PIPELINE_DESIGN.md)**: Technical design for upgrading the Discovery Workbench to perform full 3D structural inverse design using geometric vetoes.
9.  **[PFAS_SCANNER_UPGRADE_DESIGN.md](./PFAS_SCANNER_UPGRADE_DESIGN.md)**: Roadmap for transitioning the PFAS scanner from a static name registry to a generalized, structural OECD SMARTS detector.
10. **[DRUG_VS_MATERIAL_DESIGN.md](./DRUG_VS_MATERIAL_DESIGN.md)**: Comparative analysis showing why the materials track requires hard-physics ZFC vetoes compared to the graph-based pharmaceutical modules.
11. **[VALIDATION_STRATEGY_MASTER.md](./VALIDATION_STRATEGY_MASTER.md)**: A comprehensive guide on the required Gold Standard datasets and metric shapes (AUROC vs. Recovery Recall) for auditing every current and future UI pipeline.
12. **[DIRECTED_GENERATION_DESIGN.md](./DIRECTED_GENERATION_DESIGN.md)**: Directed MOF generation (strategy weights, seed pinning, required groups) — **IMPLEMENTED 2026-05-30**.
13. **[EXPLORATION_REPORT_2026-05-30.md](./EXPLORATION_REPORT_2026-05-30.md)** + **[SESSION_SUMMARY_2026-05-30_Workbench.md](./SESSION_SUMMARY_2026-05-30_Workbench.md)**: Advanced Triage Workbench (mixed-fidelity: triage → ZFC gates → multi-domain).
14. **[SESSION_CHANGES.md](./SESSION_CHANGES.md)**: 2026-05-29 session change log (PFAS structural upgrade, polymer χc).

> **Latest (2026-05-30):** compatibility confidence is now calibrated (isotonic, OOS ECE
> 0.072); directed MOF generation and PFAS cell-compatible alternatives shipped. No dataset
> is currently held blind (Q8 demoted to spent_diagnostic). See root `SESSION_SUMMARY.md`.

## Personal Test Space

- **[tests/](./tests/)**: A folder for custom diagnostic and verification scripts.
    - **[ui_feature_audit.py](./tests/ui_feature_audit.py)**: A script that verifies the presence and mapping of all chemical UI components.
    - **[compute_auroc_chem.py](./tests/compute_auroc_chem.py)**: Calculates the AUROC metric from the JSON audit reports.
    - **[prototype_polymer_chi.py](./tests/prototype_polymer_chi.py)**: Mathematical prototype proving the efficacy of the Flory-Huggins ZFC veto.
    - **[prototype_crystal_pipeline.py](./tests/prototype_crystal_pipeline.py)**: Prototype demonstrating 3D structural motif prediction via the Goldschmidt tolerance factor.
    - **[prototype_pfas_detector.py](./tests/prototype_pfas_detector.py)**: OECD structural PFAS detector tested against 10K+ EPA SMILES records.

---
*Created by Gemini CLI | 2026-05-29*
