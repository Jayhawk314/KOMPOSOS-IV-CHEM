# KOMPOSOS-IV-CHEM: Features and Competitive Value

## UI-Driven Chemical Discovery

The KOMPOSOS-IV-CHEM Streamlit UI exposes the underlying categorical runtime as a suite of powerful, chemistry-first discovery tools.

### 1. Compatibility Checker
*   **The Problem**: Determining if two novel materials will react undesirably before synthesizing them in the lab.
*   **The KOMPOSOS Solution**: Fuses multiple reasoning strategies—Simplicial Type Theory (Yoneda, Transport), classical rules, and empirical data—into a single `CompatibilityEnsembleResult`.
*   **Value**: A **calibrated probability** of compatibility (isotonic calibration, honest out-of-sample ECE 0.072 — a 0.70 means ~70%, not a black-box number), backed by a ZFC logical witness, avoiding neural-network hallucinations. Development benchmark 41/41.

### 2. MOF Designer & Explorer
*   **The Problem**: Large Language Models (LLMs) fail at exact constraint satisfaction, such as generating a Metal-Organic Framework (MOF) linker with exactly 22 atoms and 2 Nitrogen donors.
*   **The KOMPOSOS Solution**: Constraint-based combinatorial generation that guarantees exact atom counts and donor filtering, scored by a **validated grounded funnel** (chemical sanity, ≥2 donors, SAscore, donor geometry, + novelty). **Directed generation** lets researchers steer the search — strategy-weight sliders, seed-molecule pinning (only derivatives of one SMILES), and required functional groups.
*   **Value**: Solves the "Kulik Challenge" with 100% exact constraint pass rates; ~94% recall on held-out real synthesized linkers, AUROC ~0.88.

### 3. PFAS Scanner
*   **The Problem**: Screening complex industrial bills of materials (BOMs) against evolving global PFAS regulations (e.g., 2026 EU/US rules), and finding replacements that actually fit the product.
*   **The KOMPOSOS Solution**: Detects PFAS by the **OECD structural rule** (CF2/CF3) including novel substances via name→PubChem, then scores curated PFAS-free replacements for **calibrated compatibility against every adjoining material in the cell**, surfacing the weakest interface.
*   **Value**: Auditable compliance reports whose replacements are "PFAS-free AND compatible with your cell," not just "not PFAS." 100% specificity on a 25-molecule hard-negative panel; 99.5% EPA-list concordance.

### 4. Crystal Dreamer (Discovery Workbench)
*   **The Problem**: Finding materials that fit a specific multi-property profile across vast chemical spaces.
*   **The KOMPOSOS Solution**: A composition-first inverse design pipeline. Users define target property bounds and element constraints. The categorical engine navigates the knowledge graph to suggest compositions and maps out synthesizability paths.
*   **Value**: A unified triage pipeline that bridges the gap between desired physical properties and actual chemical synthesis.

### 5. Advanced Triage Workbench (mixed-fidelity)
*   **The Problem**: Fast inverse-design triage generates many candidates, some physically impossible.
*   **The KOMPOSOS Solution**: Fast triage → **ZFC charge-balance gates** → **multi-domain full-cell context** (each candidate scored against a reference electrolyte/collector), with uncertainty surfaced explicitly so high uncertainty triggers deeper derivation.
*   **Value**: Filters hallucinations out of the fast triage without losing its breadth.

## Competitive Edge: Execution as Category

The fundamental advantage of KOMPOSOS-IV-CHEM is that **Execution is a Category**. 
Instead of relying on static relational databases or probabilistic LLMs, a query triggers a proof search within a simplicially enriched category. If a direct interaction is unknown, the system uses Kan Extensions and Fibration Transport to interpolate properties safely, bounded by strict set-theoretic (ZFC) physical guards.

---
*G-docs Features & Value | 2026-05-29*