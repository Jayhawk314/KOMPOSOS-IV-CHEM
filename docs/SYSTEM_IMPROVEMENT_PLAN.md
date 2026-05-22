# KOMPOSOS-III System Improvement Plan (Post-Audit 2026-05)

This document outlines the roadmap for addressing the limitations identified during the May 2026 Scientific & Computational Audit.

## 1. Scientific Accuracy Fixes (Module 1)

The audit revealed a 76.7% accuracy rate, below the 80% target. The following physics-based fixes are required:

### 1.1. Explicit SEI Stability Modeling
**Issue**: False Positives for `Li_metal + EC` and `Si + EC`. The current battery bridge scorer ignores the interface's dynamic stability (Solid Electrolyte Interphase).
**Proposed Fix**:
- Update `battery_bridge/interaction_scoring.py` to include a `score_sei_stability` function.
- Penalize interfaces involving `Li_metal` or `Si` and `EC`-based electrolytes unless a stabilization additive (e.g., `FEC`) is present.
- **ZFC Veto**: Add `SEI_UNSTABLE` logic to `oracle/material_zfc_constraints.py`.

### 1.2. Semiconductor Lattice Mismatch Veto
**Issue**: False Positive for `GaAs + InP`. The system misses the threshold where lattice mismatch (~3.8%) makes epitaxial growth impossible.
**Proposed Fix**:
- In `semiconductor_bridge/interaction_scoring.py`, implement a hard-rejection threshold for lattice mismatch > 3%.
- Currently, it only provides a continuous score; it must trigger `viable=False` at extreme mismatches.

### 1.3. Glass CTE Mismatch Sensitivity
**Issue**: False Positive for `Soda-Lime + Borosilicate`. The system's tolerance for CTE mismatch in glasses is too high.
**Proposed Fix**:
- Tighten the `score_thermal_compatibility` in `glass_bridge/interaction_scoring.py` specifically for brittle silicate interfaces.
- Reduce the thermal score by 40% when ΔCTE > 5 ppm/K for fused glass interfaces.

---

## 2. Functor & Bridge Architectural Improvements

### 2.1. Structural Composite Functor
**Issue**: False Negatives for `SiC + Al_6061` and `BN_hex + Cu`. The `ceramic-metal` bridge assumes a *coating* application (which requires low-temp processing) and fails when evaluated as a *structural composite* or *crucible*.
**Proposed Fix**:
- Refactor `cross_bridge/ceramic_metal.py` to support multiple `InterfaceRole` types:
    - `COATING` (existing logic: strict processing limits)
    - `STRUCTURAL_COMPOSITE` (ignore processing temp, focus on CTE/Modulus)
    - `CONTAINER_CRUCIBLE` (focus on chemical inertness)
- Update `MultiDomainAnalyzer` to pass the `role` from the query to the functor.

### 2.2. Multi-Domain Routing Refinement
**Issue**: `cross_bridge/multi_domain.py` sometimes defaults to the wrong functor if a material exists in multiple bridges.
**Proposed Fix**:
- Implement a priority-based registry in `_build_domain_registry()`.
- Explicitly handle ambiguous materials (like `C`, `Si`, `Al`) by checking the `role` (e.g., if `role='collector'`, use `metal_bridge`; if `role='anode'`, use `battery_bridge`).

---

## 3. Computational Integrity & Surrogate Models (Module 2)

### 3.1. Refine Formation Energy Surrogate
**Issue**: High error (40-55%) for Phosphates (`LiFePO4`) and Spinels (`LiMn2O4`).
**Proposed Fix**:
- Update `composition_engine/formation_energy.py` to include a `structure_bias` term in the Kan extension weights.
- Give 2x weight to known DFT points with the SAME crystal structure (e.g., use olivines to predict other olivines).
- Calibrate the `Kapustinskii` empirical correction factor (currently 0.35) specifically for polyanionic systems.

### 3.2. ZFC-CAT Dual Engine Synchronization
**Issue**: ZFC classification was occasionally empty or inconsistent.
**Proposed Fix**:
- Standardize the `DualResult` classification logic into a core utility in `zfc/bridge.py` instead of duplicating it in audit scripts.
- Ensure `interface_viable` atom in ZFC is only asserted if ALL sub-scorers pass the veto threshold.

---

## 4. Implementation Roadmap

| Phase | Task | Priority | Estimated Effort |
| :--- | :--- | :--- | :--- |
| **Phase 1** | SEI Stability & Lattice Mismatch Vetoes | Critical | 2 days |
| **Phase 2** | Structural Composite Functor (Ceramic-Metal) | High | 3 days |
| **Phase 3** | Formation Energy Calibration (Phosphates) | Medium | 2 days |
| **Phase 4** | Standardize ZFC Classification | Medium | 1 day |

## 5. Verification
Following implementation, the `audit/run_audit.py` script must be run to confirm:
1. Accuracy >= 80% (with seed=42)
2. F1 Score >= 75%
3. Formation Energy reproducibility error < 25% for all test cases.
