# KOMPOSOS-IV-CHEM: System Architecture

## Overview
KOMPOSOS-IV-CHEM is a **Categorical Runtime** applied to chemistry and materials discovery. It treats materials, molecules, and their interactions not as entries in a static database, but as objects and morphisms within an active execution category ($ \infty $-cosmos). 

The system's primary goal is advanced compatibility reasoning, structural design, and multi-domain interface analysis (spanning Batteries, Polymers, Metals, Ceramics, MOFs, etc.).

## Unified Reasoning Architecture

At the heart of the system is the `compatibility_service.py`, which serves as the single source of truth for both the FastAPI backend and the Streamlit UI.

### 1. Categorical Foundation
The core runtime replaces heuristic rules with rigorous mathematical structures:
- **Simplicial Type Theory (STT)**: Uses Homotopy Type Theory concepts to analyze material relationships without relying on opaque neural networks.
- **Simplicial Yoneda**: Uses Jaccard distance between presheaf fingerprints to find structural analogs and substitute materials.
- **Fibration Transport**: Lifts compatibility results across base category morphisms.
- **Rezk Equivalence**: Groups isomorphic materials for exact functional substitution discovery.

### 2. Dual-Engine Verification
Every claim is vetted by two independent logic engines:
- **Category Engine**: Checks structural composability (Does a path exist from A to B?).
- **ZFC Engine (Set Theory)**: Checks physical and logical constraints (Do the atom counts align? Are empirical bond limits respected using normalized Gaussian typicality?).

## Active UI Features & Domain Bridges

The system surfaces its categorical reasoning through several active chemistry-focused UI modules:

1. **Compatibility Checker**: The flagship feature. Predicts if two materials will react or remain stable. Fuses classical rules, typed morphisms, MD integration, and STT strategies.
2. **PFAS Scanner**: Auditable compliance screening and replacement discovery using Rezk Equivalence to find non-PFAS analogs.
3. **MOF Designer**: Solves exact-constraint molecular generation (e.g., the Kulik 22-atom challenge). Guarantees exact atom counts and donor-atom placement through ZFC-verified combinatorial generation.
4. **Crystal Dreamer (Discovery Workbench)**: An inverse design prototype that chains property search, element constraints, and synthesis planning.
5. **Cell Designer**: Optimizes multi-layer battery stacks and identifies bottleneck interfaces.

## Bridge Architecture
Domain knowledge is loaded into the categorical runtime via specialized bridges:
- `battery_bridge`, `polymer_bridge`, `metal_bridge`, `ceramic_bridge`, `semiconductor_bridge`, `glass_bridge`, `mof_bridge`, `pfas_bridge`.
- Each bridge explicitly declares its mathematical capabilities (2-cells, fibrations) via the `TypedPluginMixin`.

---
*G-docs Architecture | 2026-05-29*