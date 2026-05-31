# KOMPOSOS-IV-CHEM: Polymer Integration Plan & Impact Analysis

## 1. Overview
This document outlines the strategy for integrating the Flory-Huggins $\chi_c$ (Critical Chi) mathematical model into the core KOMPOSOS-IV-CHEM categorical runtime. This upgrade addresses the system's primary limitation identified in the Q8 External Blind Audit: the misclassification of immiscible polymer blends as compatible.

## 2. Will it help overall? (Impact Analysis)

**Yes, it should improve the system's polymer reliability and may improve
post-remediation diagnostic AUROC.** The clean future claim must come from Q10
or another sealed set after the model is implemented.

### The "Why" and "How"
The current categorical engine is highly effective at finding structural analogs (via Simplicial Yoneda and Fibration Transport). However, polymers are a physical exception to general proximity rules. Because of their massive size (high Degree of Polymerization, $N$), the entropy gained by mixing them is near zero. Therefore, even polymers that look "similar" categorically will violently phase-separate in reality unless their enthalpic interaction is exceptionally favorable.

**Expected Impact on Metrics (Based on Q8 Audit):**
*   **Reduced False Positives**: The Q8 audit revealed that the categorical engine incorrectly predicted compatibility for pairs like `ABS + PVDF` and `PA66 + PEO`. The prototype proved that the $\chi_c$ math correctly identifies these as phase-separating.
*   **Increased Specificity**: By aggressively vetoing these false positives, the system's specificity (ability to correctly identify incompatible materials) will rise.
*   **AUROC / calibration impact**: Moving from a heuristic to a strict
    thermodynamic boundary should clean up high-confidence polymer false
    positives. The stored post-repair Q8 diagnostic artifact reports AUROC
    `0.9038`; after production chi_c integration, spent Q9 reports AUROC
    `0.9247`. The honest final measurement must still be on sealed Q10.

## 3. Step-by-Step Integration Roadmap

To implement this without breaking the existing architecture, the fix must be integrated as a **ZFC Dual-Engine Constraint**, rather than altering the base categorical logic.

### Step 1: Update the Polymer Bridge Schema
**Target File**: `bridges/polymer_bridge/material_properties.py` (or equivalent database schema)
*   **Action**: Expand the polymer property schema to mandate two new fields:
    *   `monomer_mw` (Monomer Molecular Weight)
    *   `polymer_mw` (Typical/Target Polymer Molecular Weight)
*   *Requirement*: The system cannot calculate $N$ (Degree of Polymerization) without these values.

### Step 2: Create the ZFC Constraint
**Target File**: `zfc/material_zfc_constraints.py` (or new `polymer_constraints.py`)
*   **Action**: Implement a new class `PolymerMiscibilityConstraint`.
*   **Logic**:
    1.  Extract Hansen Solubility Parameters (HSP) and MWs for both polymers.
    2.  Calculate Interaction $\chi$ (using standard $V_r / RT$ scaling).
    3.  Calculate Critical $\chi_c$ using $N_1$ and $N_2$.
    4.  Evaluate: If $\chi > \chi_c$, trigger a constraint violation.

### Step 3: Implement the "Empirical Whitelist" Safeguard
*   **The Trap Discovered in Prototyping**: Basic HSP math fails for specific favorable interactions (e.g., pi-pi stacking in `PS + PPO`).
*   **Action**: The `PolymerMiscibilityConstraint` must first check an empirical interaction table. If a specific negative interaction parameter (e.g., $\chi = -0.05$) is known from literature, it must override the basic HSP calculation to prevent False Negatives.

### Step 4: Wire into the Compatibility Service
**Target File**: `oracle/compatibility_service.py` (or the ZFC verifier module)
*   **Action**: When evaluating a pair where both materials belong to the `polymer` domain, invoke the `PolymerMiscibilityConstraint` as part of the ZFC verification phase.
*   **Outcome**: If the constraint is violated, the final ensemble result must be overridden to `viable = False`, and the system must surface a `ZFC_REJECT` reason: "Thermodynamic phase separation predicted: $\chi > \chi_c$".

## 4. Final Validation Protocol
1.  **Do NOT use Q10**: The Q10 dataset remains sealed.
2.  **Regression Testing**: Run the `development` module audit. The fix must not break the current 41/41 (100%) score.
3.  **Q8/Q9 diagnostic re-evaluation only**: Re-run spent sets to verify the
    expected FP causes move in the right direction. Do not report improved Q8/Q9
    as fresh blind performance.
4.  **Q10 final check**: Score Q10 once only after the model is complete and the
    hidden labels remain sealed from the tuning work.

---
*G-docs Integration Plan | 2026-05-29*
