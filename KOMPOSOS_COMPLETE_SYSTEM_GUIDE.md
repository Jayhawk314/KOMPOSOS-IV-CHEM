# KOMPOSOS-IV Chemistry - Complete System Guide
## Categorical Runtime & Compositional Reasoning Engine

**Version:** 1.7.0
**Date:** May 30, 2026
**Author:** James Hawkins

## 2026-05-30 IV-CHEM Update

KOMPOSOS-IV-CHEM is a **categorical runtime** for chemistry and materials science. Unlike traditional materials informatics tools or Version III's static bridge pattern, Version IV treats **execution itself as a category**. 

This repo combines:
- the advanced CHEM compatibility and audit stack from `KOMPOSOS-III-LAMBDA-max-3D-chem`
- the **Categorical Runtime** architecture (Infinity Cosmos) from `KOMPOSOS-IV`
- the **COG Engine** (Cognitive Co-processor) for tiered verification
- the **OPTIMUS** decision engine for game-theoretic trade-off optimization
- **Simplicial Type Theory (STT)**: Rigorous structural similarity (Yoneda distance) and transport laws replace heuristic weights.

Current audit state (source of truth: `audit/dataset_registry.json`):
- Development tuning: `41/41`, `100.0%`, Brier 0.095.
- Formation-energy surrogate: MAE **0.304 eV/atom** (−36%; RandomForest sparse-discovery model).
- Compatibility confidence: **calibrated** (isotonic, out-of-sample ECE 0.072; a 0.70 ≈ 70%).
- **No dataset is currently blind** (`current_blind_version: null`). Q2–Q8 are spent
  diagnostics; **Q8 was demoted to spent_diagnostic on 2026-05-29** (latest run 89.5%,
  not a blind claim). Freeze Q9 before the next blind validation claim. Q10 is sealed.
- Master audit status: development + computational **PASS**.

Latest features (2026-05-30): **directed MOF generation** (strategy weights, seed pinning,
required groups), **isotonic compatibility calibration**, and **PFAS → cell-compatible
alternatives** (replacements ranked by calibrated compatibility with the whole stack).

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture (Categorical Runtime)](#core-architecture)
3. [The COG Engine (Tiered Verification)](#the-cog-engine)
4. [OPTIMUS (Optimal Transport & Game Theory)](#optimus)
5. [MOF Linker Designer - Deep Dive](#mof-linker-designer-deep-dive)
6. [Mathematical Foundations ($\infty$-Cosmos)](#mathematical-foundations)
7. [Bridges & Domain Data](#bridges--domain-data)
8. [ZFC Dual-Engine Verification](#zfc-dual-engine)
9. [Validation and Benchmarks](#validation-and-benchmarks)
10. [Use Cases and Applications](#use-cases-and-applications)
11. [Technical Implementation](#technical-implementation)

---

## 1. System Overview

### What KOMPOSOS IV Is

KOMPOSOS-IV is a **compositional reasoning engine** where the knowledge graph is not just a database, but a **runtime category** ($ \infty $-cosmos). It uses higher-order category theory and ZFC set theory to reason about material compatibility, synthesis paths, and molecular properties.

**Core Philosophy:**
- **Materials are Objects** in a category
- **Interactions are Morphisms** carrying confidence/quantale weights
- **Discovery is Composition** (A→B and B→C implies A→C)
- **Verification is Path Induction** (Homotopy Type Theory)

**Key Differentiator:** The system doesn't just predict; it **reasons through 5 tiers of verification**. Every result is backed by a categorical trace and a ZFC logical witness.

---

### What KOMPOSOS Is NOT

❌ **Not a black-box neural network** - No hidden layers, every decision is traceable
❌ **Not a static database** - Dynamically discovers intermediate objects and optimal paths
❌ **Not an LLM** - Enforces exact chemical and physical constraints (e.g., atom counting)
❌ **Not a pure simulator** - Integrates empirical data, DFT, and MD into a single logical framework

---

### The Big Picture: Execution as Category

In KOMPOSOS-IV, a query like *"Is NMC811 compatible with EC?"* triggers a **morphism lookup** in the runtime category. If the direct morphism is unknown, the engine:
1. Finds all paths A→...→B
2. Applies **Kan extensions** to interpolate properties
3. Uses **OPTIMUS** to find the most "stable" path in the quantale
4. Passes the result through the **COG Engine's 5-tier verification**

---

## 2. Core Architecture (Categorical Runtime)

### The Infinity Cosmos Layer

The foundation of KOMPOSOS-IV is the **Infinity Cosmos** (`core/cosmos.py`). Based on the Riehl-Verity framework, it provides a simplicially enriched category where:
- **0-cells**: Materials and Molecules
- **1-cells**: Interactions, Reactions, Compatibility scores
- **2-cells**: Homotopies/Natural Transformations between paths (e.g., comparing two different synthesis routes)

This allows the system to handle **higher-order reasoning**, such as detecting when two synthesis paths are "equivalent" or when one is a "deformation" of another into a more efficient state.

### The Bridge ABC

Domains (Battery, Polymer, etc.) are loaded into the runtime via the **Bridge ABC** (`core/bridge.py`). This simplifies the architecture by treating all domain data as categorical input:

```python
from core.bridge import Bridge

class BatteryBridge(Bridge):
    def get_objects(self):
        # Returns list of Materials as categorical Objects
        ...
    def get_morphisms(self):
        # Returns interactions as categorical Morphisms
        ...
    def score_pair(self, source, target):
        # Returns domain-specific compatibility scores
        ...

bridge = BatteryBridge("battery")
bridge.load()  # Data is now "live" in the InfinityCosmos
```

### Quantale Enrichment

Morphisms in KOMPOSOS-IV are enriched over a **Quantale** (`optimus_core.py`). This determines how scores compose:
- **Multiplicative**: $ w(f \circ g) = w(f) \cdot w(g) $ (Probabilistic confidence)
- **Additive**: $ w(f \circ g) = w(f) + w(g) $ (Cost/Energy)
- **Min**: $ w(f \circ g) = \min(w(f), w(g)) $ (Bottleneck analysis)

---

## 3. The COG Engine (Tiered Verification)

The **COG Engine** (`cog/engine.py`) is the cognitive co-processor that validates every claim made by the runtime. It operates in **5 tiers** of increasing depth:

| Tier | Name | Latency | Logic |
| :--- | :--- | :--- | :--- |
| **0** | Graph Lookup | ~1ms | Direct edge/morphism existence check |
| **1** | Path Composition | ~10ms | Finding chains of interactions (A→B→C) |
| **2** | Sheaf & Kan | ~100ms | Sheaf coherence and Kan extension interpolation |
| **3** | ZFC Dual Engine | ~1s | Set-theoretic constraint verification (AGREE/REJECT/HOLLOW) |
| **4** | Topology & Flow | ~10s | Ricci curvature, persistent homology, h₂K 2-cell induction |

### Energy-Based Coherence

COG uses an **Energy Computer** (`cog/energy.py`) to measure the "surprise" of a claim:
- **Low Energy**: Coherent with existing knowledge; supports established patterns.
- **High Energy**: Contradicts known data or logical constraints.
- **Collapse Detection**: Detects when two individually safe morphisms compose into a "NULL_COLLAPSE" (e.g., A+B is toxic).

---

## 4. OPTIMUS (Optimal Transport & Game Theory)

**OPTIMUS** (`optimus_core.py`) is the decision engine used to find optimal materials or paths.

### Factorization Search
Instead of adjusting parameters like a neural network, OPTIMUS discovers **intermediate objects**. It searches for factorizations $ A \to B \to C $ of a morphism $ A \to C $ that improve the overall confidence/weight in the quantale.

### Game-Theoretic Equilibrium
OPTIMUS uses **multi-player Nash equilibrium** to balance competing material properties:
- **Player 1**: Maximizes Conductivity
- **Player 2**: Maximizes Stability
- **Player 3**: Minimizes Cost
OPTIMUS finds the "Nash point" where no single property can be improved without unacceptably degrading another.

---

## 5. MOF Linker Designer - Deep Dive

### What Problem Does This Solve?

**Heather Kulik's challenge (MIT ChemE):**
> "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

**Why LLMs fail:**
- They count tokens, not atoms.
- They lack logical grounding to guarantee chemical stability.
- They cannot enforce exact constraints (22 atoms, 2 N donors, etc.).

**KOMPOSOS solves this with:**
- **Exact atom count control** (5-60 atoms, user-specified)
- **Categorical constraint search** (Must have N, O, or S donors)
- **Novelty filtering** (Check against known linker databases)
- **5-verdict screening** using the **COG Engine** and **ZFC logic**.

---

### How MOF Linker Generation Works in Version IV

In Version IV, linker generation is treated as a **Search for Factorizations** in the Infinity Cosmos.

**Step 1: Seed Linker Database**
The system loads 274 known linkers from Materials Project MOF structures as "Anchor Objects".

**Step 2: Combinatorial Generation (Morphism Deformation)**
Three strategies generate novel linkers, each a deformation of an existing molecule:
1. **Functional Group Substitution**: swap groups (–OH, –NH₂, –F, …) on a backbone.
2. **Backbone Modification**: add/remove atoms to resize/reshape a linker.
3. **Template**: build from application-specific scaffolds (new backbones).

**Directed generation (2026-05-30):** the researcher can steer the search instead of
relying on chance — **strategy-weight sliders** (e.g. substitution-only), **seed-molecule
pinning** (generate only derivatives of one SMILES), and **required functional groups**
(every candidate must carry chosen groups, enforced by SMARTS). Turns "slot machine"
random discovery into "microscope" directed optimization.

**Step 3: Grounded funnel (validated) + descriptor verdicts**
Candidate quality is scored by a **validated grounded funnel** — chemical sanity, ≥2
coordinating donor sites, SAscore (synthesizability), donor geometry, plus novelty vs.
known linkers. **~94% recall on held-out real synthesized linkers, AUROC ~0.88** vs. raw
generator output. The legacy 5-verdict descriptors (synthesizability/toxicity/stability/
activity/conductivity) are retained as *unvalidated* dynamic descriptors, not the headline
claim. A high score is NOT a synthesis guarantee (no wet-lab validation).

---

## 6. Mathematical Foundations ($\infty$-Cosmos)

### Higher Category Theory
Based on the Riehl-Verity framework, the system treats the materials universe as an $ \infty $-cosmos. This allows for:
- **Pointwise Kan Extensions**: Formal way to compute "best approximations" of properties.
- **Cartesian Fibrations**: Mapping properties over the base category of compositions.
- **Yoneda Embedding**: materials defined by their "relationships" to all others.

### Ricci Flow & Knowledge Graph Curvature
Using **Ollivier-Ricci curvature**, KOMPOSOS identifies:
- **Bottlenecks (Negative Curvature)**: Interfaces likely to fail.
- **Redundancy (Positive Curvature)**: Reliable, well-mapped chemical spaces.

### Persistent Homology
The system uses homology to detect "voids" and "loops" in knowledge:
- **H2 Voids**: Finding "Topological Gaps" where novel materials likely exist.

---

## 7. Bridges & Domain Data

| Bridge | What It Does | Key Properties |
|--------|--------------|----------------|
| **battery_bridge/** | Cathodes, anodes, electrolytes | Voltage, Capacity, ionic conductivity |
| **polymer_bridge/** | Binders, separators, coatings | Hansen χ, Tg, Elongation |
| **metal_bridge/** | Current collectors, casings | Galvanic potential, CTE, Corrosion |
| **ceramic_bridge/** | Solid electrolytes, coatings | Ionic conductivity, CTE, Sintering temp |
| **semiconductor/** | Substrates, active layers | Band gap, Mobility, Lattice constant |
| **glass_bridge/** | Substrates, encapsulation | CTE, Softening point, Chemical resistance |
| **mof_bridge/** | Metal-organic frameworks | Pore size, Surface area, Thermal stability |
| **molecular_bridge/** | Small molecules, gases | BP, Dipole, Solubility |

---

## 8. ZFC Dual-Engine Verification

While the Categorical Runtime provides structural reasoning, the **ZFC Engine** provides a logical audit.

### Dual-Engine Verdicts
- **AGREE**: Both engines say YES. High confidence.
- **HOLLOW**: Category says YES, but ZFC finds a logical contradiction (e.g., bond length violation).
- **ORPHAN**: ZFC sees no contradiction, but Category finds no composing morphism.
- **REJECT**: Both engines say NO.

### Physical Grounding: Gaussian Typicality
Version IV uses **normalized Gaussian typicality** for bond plausibility, ensuring bond lengths are verified against crystallographic statistics.

---

## 9. Validation and Benchmarks

### Compatibility
- **Development set**: `41/41`, `100.0%`, Brier 0.095.
- **Confidence calibration**: isotonic, honest out-of-sample **ECE 0.072** (Brier 0.049),
  down from raw ~0.194 — the score is now a real probability (a 0.70 ≈ 70%).
- **Blind status**: **no dataset is currently blind** (`current_blind_version: null`).
  Q2–Q8 are spent diagnostics; Q8 demoted 2026-05-29 (latest run 89.5%, MCC 0.797,
  Brier 0.107 — coverage tracking only, NOT a blind claim). Freeze Q9 next. Q10 sealed.

### Formation Energy Surrogate
- **179 curated (LOO)**: MAE **0.304 eV/atom**, RMSE 0.454; held-out MP MAE 0.133.
- Intervals conformally calibrated to honest 50/80/95% coverage.

### MOF Linker Validation
- **Exact Atom Count**: 100% — the generator never fabricates the count.
- **Grounded funnel**: ~94% recall on held-out real synthesized linkers, AUROC ~0.88.
- **Novelty**: scored as 1 − similarity to nearest known linker.

### PFAS Detection
- 100% specificity on a 25-molecule hard-negative panel; 99.5% concordance with the EPA
  structural list; catches novel PFAS by name (PubChem) + OECD structural rule.

---

## 10. Use Cases and Applications

### Industrial Cell Design
- Design solid-state battery stacks with 4-6 materials.
- Identify bottleneck interfaces via min-quantale composition.
- Optimize binder selection using OPTIMUS trade-offs.

### PFAS Compliance
- Screen bill-of-materials against 2026 EU/US regulations (OECD structural rule + EPA list).
- Generate auditable compliance reports with replacement scoring.
- **Cell-aware replacements**: list the adjoining materials and each PFAS-free candidate is
  scored for **calibrated compatibility** against the whole stack, surfacing the weakest
  interface — "PFAS-free AND compatible with your cell," not just "not PFAS."

---

## 11. Technical Implementation

### Requirements
- Python 3.11+
- 8GB RAM (16GB recommended for COG Tier 4)
- 10GB disk space (with MP cache)

### Installation
```bash
git clone https://github.com/JAMES/KOMPOSOS-IV-CHEM
cd KOMPOSOS-IV-CHEM
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

### API Usage
Visit `http://localhost:8000/docs` for Swagger UI. 19 endpoints including `/api/v1/compatibility` and `/api/v1/design-mof-linker`.

---

*KOMPOSOS-IV-CHEM | James Ray Hawkins | 2026*
