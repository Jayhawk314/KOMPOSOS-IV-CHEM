# KOMPOSOS-III "Kulik-Grade" Reliability Upgrade Vision

This document details the roadmap to reach 92%+ accuracy and "publication-ready" reliability for KOMPOSOS-III, following the research principles of Prof. Heather Kulik (MIT).

## 1. Implemented: Density-Based Uncertainty (UQ)
The system now avoids returning "overconfident" results when training data is sparse.
- **Epistemic Uncertainty**: Penalizes confidence based on distance to the nearest training data point in composition space.
- **Aleatoric Uncertainty**: Estimates error bars based on the local variance (standard deviation) of the k-nearest neighbors.
- **Output**: Every formation energy now includes a physically meaningful +/- error bar (eV/atom).

## 2. Roadmap: Electronic Environment Descriptors
To bridge the "fidelity gap," we must move beyond stoichiometry.
- **Task**: Add `coordination_geometry` (e.g., Octahedral, Tetrahedral) to `KnownFormationEnergy`.
- **Impact**: Better accuracy for transition metals where high spin/low spin states and Jahn-Teller distortions dictate stability.

## 3. Roadmap: Multi-Fidelity Delta Learning
- **Task**: Implement categorical functors that predict the *correction* between fast models (Kapustinskii) and high-fidelity DFT.
- **Math**: $\Delta = Ef_{DFT} - Ef_{Empirical}$. The Kan extension should operate on $\Delta$ space for smoother interpolation.

## 4. Roadmap: Transition Metal Hard Vetoes
- **Task**: Implement rejections for high-voltage instability in Ni-rich systems (surface phase transitions).
- **Benchmark**: Validate against the `molsimplify` dataset for coordination complexes.

## 5. Summary of Reliability Targets
| Metric | Current (Post-Audit) | Kulik-Grade Target |
| :--- | :--- | :--- |
| Blind Test Accuracy | 83.3% | **92%+** |
| UQ Calibration | Heuristic | **Density-Based (Implemented)** |
| Physics Layer | Bulk Properties | **Electronic/Spin Descriptors** |
| Engine Logic | Heuristic Scoring | **Evidence-Based (D-S intervals)** |
