# KOMPOSOS-IV Limitations & Confidence Bounds

*Updated 2026-05-22 - Version IV Categorical Runtime*

While KOMPOSOS-IV introduces significant improvements in rigor and optimization, it operates within defined mathematical and physical boundaries.

---

## 1. Computational Complexity (COG Engine)

- **Tier 4 Latency**: High-order topological audits (Ricci Flow, Persistent Homology) can take 10-30 seconds per query on standard hardware. This tier is disabled by default for real-time API use.
- **Factorization Explosion**: OPTIMUS search for intermediate objects can be computationally expensive in highly dense regions of the materials graph (e.g., complex mixed-metal oxides).
- **Memory Scaling**: Initial load of the 103K+ Materials Project cache into the runtime category requires 4GB+ of RAM.

---

## 2. Categorical Reasoning Boundaries

- **Higher-Order Equivalence**: While 2-cells can compare synthesis paths, the system may struggle to detect equivalence if paths involve radically different chemical mechanisms not yet mapped into the runtime.
- **Functorial Gaps**: Cross-domain functors (e.g., mapping molecular reactivity to battery voltage) are based on currently curated evidence. If a new domain is added, a "cold start" period exists where functors are less reliable.
- **Kan Extension Edge Cases**: In extremely sparse regions of the 120D embedding space (e.g., rare earth elements or novel transuranics), interpolation confidence remains low.

---

## 3. Physical Grounding (ZFC Engine)

- **Heuristic Fallbacks**: When empirical bond statistics are missing for specific element pairs, the ZFC engine falls back to static covalent/ionic radii. This can lead to "HOLLOW" verdicts that are overly conservative.
- **Thermodynamic Simplification**: Formation energy predictions assume simplified valence states. Complex mixed-valence systems (e.g., some transition metal spinels) may exhibit higher error bars.
- **MD Constraints**: Active verification via GROMACS requires prepared input structures (`.gro`, `.top`). The system does not "hallucinate" force fields; if inputs are missing, the MD verdict is skipped.

---

## 4. Uncertainty Tiers (Version IV)

Predictions are explicitly classified into tiers to communicate reliability:

| Tier | Basis | Physical Meaning |
| :--- | :--- | :--- |
| **Ground Truth** | Exact Match | Material/Interaction exists in curated database. |
| **Dense Interpolation** | Close Neighbors | High confidence; well-mapped chemical space. |
| **Moderate Extrapolation** | Logical Analogs | Reliable for screening and hypotheses. |
| **Sparse Discovery** | dist >= 0.5 | Novel chemistry. Treat as qualitative estimate. |
| **Heuristic Estimate** | Rule-based | No nearby neighbors; based on physical rules-of-thumb. |

---

## 5. Audit & Validation Status (IV-CHEM)

- **Internal Benchmark**: 215 unique literature pairs.
- **Generalization**: 92.0% accuracy on held-out pairs.
- **Status**: Screening-grade. Not yet approved for clinical or regulated aerospace decisions without human-in-the-loop validation.

---

*KOMPOSOS-IV-CHEM | james Hawkins | 2026*
