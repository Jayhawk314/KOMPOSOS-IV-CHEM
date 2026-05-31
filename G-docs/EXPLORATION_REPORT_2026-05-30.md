# KOMPOSOS-IV: Discovery Workbench Exploration & Integration Strategy

## 1. Executive Summary
The Discovery Workbench (Crystal Dreamer) represents the transition of KOMPOSOS from a **Reasoning Engine** to a **Design Platform**. This exploration identifies that while the current pipeline is functional, its value can be multiplied by integrating it more deeply with the repository's advanced categorical and math-kernel modules.

## 2. Current State Analysis
*   **Pipeline**: Linear orchestrator (Inverse Design → PFAS → Compatibility → Synthesis).
*   **Accuracy**: ~94.6% per bridge, but with "black-box" risks in the inverse design generation phase (~85% LOO).
*   **Constraint Handling**: Simple charge-balance gates and stoichiometry search.

## 3. Strategic Integration Brainstorming

### 3.1 Advanced Categorical Generation (The AIMO Bridge)
The `discovery/math_discovery_engine.py` and `hole_navigation.py` modules contain topological search logic currently used for Lean theorems. 
- **Integration**: Apply "Hole Navigation" to property space. Treat a missing high-voltage/high-safety material as a "topological hole" in the chemical knowledge graph.
- **Functorial Suggestion**: Use shared-neighbor analysis (from `complete_conjecture_pipeline.py`) to suggest material analogs that satisfy the user's constraints by "transporting" properties across common structural motifs.

### 3.2 Full-Stack Compatibility (The Multi-Domain Bridge)
The `cross_bridge/multi_domain.py` module is a powerful tool for analyzing layered stacks.
- **Integration**: The Workbench should not just check "discovered material vs. Lithium". It should run the `MultiDomainAnalyzer` to evaluate the candidate in a **Full Cell Context** (Candidate + Collector + Binder + Electrolyte).
- **Bottleneck Identification**: This allows the workbench to flag if a discovered high-capacity cathode is actually unusable because it corrodes the standard Aluminum collector.

### 3.3 ZFC-Hardened Physical Gates
The `composition_engine/physical_gates.py` currently only checks charge balance.
- **Integration**: Formalize the `CRYSTAL Pipeline` designs (Goldschmidt Tolerance Factor, Pauling's Rules) as ZFC-verified constraints.
- **Veto Logic**: Reject formulas that are mathematically "correct" but geometrically impossible before they even reach the compatibility or synthesis stages.

### 3.4 Feedback-Aware Synthesis
The `synthesis_planner` is currently a passive estimator at the end of the pipeline.
- **Integration**: Turn the planner into an **active constraint**. If the `SynthesisPlanner` identifies that a formula requires a \$5,000/g precursor or an unavailable reactor, the `CompositionDesigner` should automatically pivot to a chemically similar but cheaper alternative.

## 4. Proposed "Unified Workbench" Architecture
The evolution of the workbench should follow a **Closed-Loop Categorical Functor**:

1.  **Target Definition**: User sets property/regulatory goals.
2.  **Topological Generation**: Math kernel identifies "holes" in the graph and proposes candidates via shared-neighbor transport.
3.  **Logical Veto (ZFC)**: Physical gates (Charge, Geometry, Bond Typicality) filter out unphysical hallucinations.
4.  **Contextual Validation**: `MultiDomainAnalyzer` evaluates the candidate in its intended device environment.
5.  **Synthesis Verification**: Planner confirms a feasible path exists to reach the candidate.

## 5. Accuracy & Reliability Considerations
| Module | Current Limit | Mitigation via Integration |
| :--- | :--- | :--- |
| **Inverse Design** | HALLUCINATION RISK | ZFC Geometric Vetoes (Pauling/Goldschmidt). |
| **Compatibility** | ISOLATED INTERFACES | `MultiDomainAnalyzer` full-stack bottleneck check. |
| **Synthesis** | HEURISTIC COST | Live market-data bridge (planned) + Precursor-biased search. |

---
*Exploration Report | G-docs/ | 2026-05-30*
