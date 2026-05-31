# KOMPOSOS-IV-CHEM: Master Validation Strategy

## Overview
KOMPOSOS-IV-CHEM contains multiple distinct discovery pipelines. Because the outputs range from binary compatibility decisions to complex 3D generative structures, the system **cannot** use a monolithic pytest suite to measure scientific accuracy. 

Each feature requires a specific "Gold Standard" ground truth dataset and a mathematically appropriate metric shape (e.g., AUROC for classification vs. Recovery Recall for generative design).

---

## Part 1: Current Validated Features

### 1. Compatibility Checker
*   **The Task**: Binary classification (Compatible vs. Incompatible) between two materials across continuous interfaces (Battery, Polymer, Ceramic, etc.).
*   **Gold Standard Data**: Tuned **development set** (41 pairs) + **spent diagnostics** Q2–Q8.
    **No dataset is currently held blind** (`current_blind_version: null`): Q8 was demoted to
    spent_diagnostic on 2026-05-29 after its skip/fail cases were inspected (14/40 identity
    overlap). **Freeze Q9 (uninspected recent-literature pairs) before the next blind claim.**
*   **Metric Shape**: Accuracy/MCC + **Brier Score** and **ECE** (calibration).
*   **Current Baseline**: Development **41/41 (100%), Brier 0.095**. Confidence is now a
    **calibrated probability** via global isotonic calibration: honest k-fold **out-of-sample
    ECE 0.072** (Brier 0.049), chosen over raw/Platt by held-out ECE
    (`audit/fit_compat_calibration.py`). Q8 spent-diagnostic latest run 89.5%, MCC 0.797.
    *(The earlier "AUROC 0.9038 on Q8 blind" predates the demotion — Q8 is no longer a blind claim.)*

### 2. MOF Designer
*   **The Task**: Generative exact-constraint design (e.g., exactly 22 atoms, exactly 2 Nitrogen donors).
*   **Gold Standard Data**: **Kulik's Corpus** (MOFSimplify + CoRE-MOF). ~875 curated, real-world synthesized linkers.
*   **Metric Shape**: **Recovery Recall** and **AUROC (Functor vs. Random)**.
*   **Current Baseline**: 94% Recall on real synthesized linkers, AUROC 0.88 against raw/unfiltered generator output, 100% exact constraint adherence.

### 3. PFAS Scanner
*   **The Task**: Binary classification (PFAS vs. Non-PFAS) of massive industrial BOMs, **plus** ranking PFAS-free replacements by compatibility with the user's cell.
*   **Gold Standard Data**: **EPA CompTox PFASSTRUCT Dataset** (~10,700+ SMILES) and a curated negative set of non-PFAS fluorinated molecules.
*   **Metric Shape**: **Specificity** (on a hard-negative panel of fluorinated-but-not-PFAS molecules) + **concordance/recall** vs the EPA list. NOT AUROC — a binary OECD substructure rule has no ROC curve.
*   **Current Baseline**: Specificity **100% on a 25-molecule hard-negative panel**; **99.5% concordance** with EPA PFASSTRUCT v4 (consistency with EPA's structural definition, not independent validation); 4/4 positive controls. (Prior "0.9976 AUROC" was balanced accuracy on 8 negatives; corrected.)
*   **Replacements (2026-05-30)**: each PFAS-free candidate is scored for **calibrated compatibility** against every adjoining material (`find_replacements_for_cell`); the weakest-interface bottleneck inherits the compatibility calibration above.

---

## Part 2: Strategy for Future Pipelines

### 4. Cell Designer $\to$ Battery Optimizer
*   **The Goal**: Upgrade from simply checking one stack to sweeping millions of combinations to maximize energy density under compatibility constraints.
*   **The Trap**: Predicting cycle life or thermal runaway is noisy and highly unvalidated at the cell level.
*   **Gold Standard Data**: A curated set of **Commercial Cell Stacks** (e.g., Tesla 4680, CATL LFP, known failed prototypes).
*   **Metric Shape**: **Recovery Recall (Hits@K)**. 
    *   *Test*: If constrained to the elements of a Tesla 4680, does the optimizer rank the actual commercial NMC811/Si-Graphite design in its Top 5 suggestions (Hits@5)?
    *   *Objective*: Maximize Theoretical Energy Density ($V \times C$). We only validate what we can rigorously compute.

### 5. Discovery Workbench / Crystal Dreamer / CRYSTAL Pipeline
*   **Differentiation**:
    *   **Crystal Dreamer**: Inverse composition search (Formula Finder).
    *   **Discovery Workbench**: Orchestration pipeline (Formula Triage: Inverse Design $\to$ PFAS $\to$ Compatibility).
    *   **CRYSTAL Pipeline**: Structural mapping (Formula $\to$ 3D Motif).
*   **Gold Standard Data**: A temporal holdout of the **Materials Project (MP)** database. 
*   **Metric Shape**: **Property Prediction Calibration** and **Recovery Recall (Hits@K)**.
    *   *Empirical Test (2026-05-29)*: Ran a Recovery Recall test on Crystal Dreamer holding out `NMC811`.
    *   *Result*: The engine successfully explored the space, finding 76 candidates with a minimum compositional distance of **0.2562** to the target. This confirms the generator is successfully navigating "near" the target space but identifies the need for finer-grained stoichiometry grids for exact recovery.
    *   *Test 1 (Property)*: Does the compositional typicality engine accurately bound the target property within its 95% Confidence Interval?
    *   *Test 2 (Generative)*: What percentage of proposed formulas synthesize into stable structures in external DFT databases?

### 6. The CRYSTAL Pipeline (3D Structure Mapping)
*   **The Goal**: Moving from a 1D compositional formula (e.g., `CaTiO3`) to a 3D relaxed crystal lattice motif (e.g., Perovskite).
*   **Gold Standard Data**: The local **103K+ Materials Project (MP) Cache**. 
*   **Metric Shape**: **Topological Motif Accuracy**.
    *   *Test*: The system is given 1,000 known stoichiometric formulas (without coordinates). The ZFC engine applies the geometric vetoes (Goldschmidt Tolerance, Pauling's Rules).
    *   *Success*: The system accurately assigns the correct structural motif (e.g., Spinel vs. Olivine) before running expensive DFT relaxation, measured as a categorical accuracy percentage.

## Summary: The Audit Philosophy
The core rule of KOMPOSOS-IV-CHEM validation is **Honesty of Claims**. 
- If a metric relies on continuous physics (Compatibility, PFAS), we use **AUROC / True Recall** against curated literature/EPA lists.
- If a metric is generative (MOFs, Crystal Dreamer, Battery Optimizer), we use **Recovery Recall (Hits@K)** against known successful real-world artifacts (Commercial batteries, MP structures, Kulik's MOFs).
- We never claim to optimize "real-world cycle life" if we only have the math to optimize "theoretical energy density."

---
*G-docs Validation Strategy | 2026-05-29*
