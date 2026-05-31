# KOMPOSOS-IV-CHEM: CRYSTAL Pipeline Integration Design

## 1. Problem Context
Currently, the "Crystal Dreamer" (Discovery Workbench) operates as a **composition-first** engine. When a user requests a new material with specific properties (e.g., high ionic conductivity, solid electrolyte), the categorical runtime searches the $\infty$-cosmos to suggest a chemical formula (e.g., `Li7La3Zr2O12` or `LLZO`). 

However, predicting a composition is only half the battle. A material's physical properties are dictated by its 3D spatial arrangement (the crystal lattice). For example, Carbon can be Graphite (soft, conductive) or Diamond (hard, insulating) depending purely on structure. The current system lacks the pipeline to map a predicted composition to its most stable 3D structural motif.

## 2. The Solution: The CRYSTAL Pipeline
The CRYSTAL Pipeline will transition the system from *Composition Prediction* to *Full Structural Inverse Design*. It introduces geometric logic into the categorical reasoning engine.

### 2.1 Categorical Structural Motifs
Instead of just reasoning about elements, the $\infty$-cosmos must reason about **Structural Motifs** (e.g., Perovskite, Spinel, Garnet, Layered). 
- A motif becomes a categorical object.
- The system predicts a composition and then searches for compatible motif objects.

### 2.2 ZFC Geometric Constraints
Just as we designed the Flory-Huggins math to veto bad polymers, we need geometric math to veto impossible structures. The ZFC Engine will be expanded to include crystallographic rules.

**Example: The Goldschmidt Tolerance Factor ($t$) for Perovskites ($ABX_3$)**
To form a stable perovskite structure, the ionic radii of the atoms ($r_A$, $r_B$, $r_X$) must physically fit together:
$$ t = \frac{r_A + r_X}{\sqrt{2} (r_B + r_X)} $$

**The Rule:**
- If $0.75 < t < 1.0$: A perovskite structure is geometrically possible. (Ideal cubic is $\sim 0.9 - 1.0$).
- If $t$ is outside this range: The atoms physically cannot pack into that lattice.

### 2.3 Integration with Materials Project (MP) Cache
Once a composition and motif pass the ZFC geometric veto, the system queries the local Materials Project cache (103K+ DFT structures) to find the closest relaxed crystal structure match, providing the user with exact lattice parameters and formation energies.

## 3. Integration Roadmap
1.  **Update ZFC Proof Engine**: Add a `CrystallographicConstraint` module containing rules like the Goldschmidt tolerance factor and Pauling's Rules.
2.  **Expand Discovery Workbench**: Add a step after composition generation to iterate over known structural motifs and apply the geometric vetoes.
3.  **Local Structure Mapping**: Query the `composition_engine`'s MP cache to pull `.cif` string representations of the winning structure to display in the UI.

This upgrade transforms the system into a true end-to-end inverse design platform.

---
*G-docs Design Document | 2026-05-29*
