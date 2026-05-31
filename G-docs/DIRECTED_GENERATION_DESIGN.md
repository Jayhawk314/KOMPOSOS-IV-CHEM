# Design Document: Directed MOF Generation (Reducing Randomness)

## 1. The Problem
Currently, the `LinkerGenerator` uses a highly stochastic (random) approach. It randomly selects between three strategies:
1. `substitution` (50% chance): Randomly swapping functional groups on a known linker.
2. `modification` (30% chance): Randomly adding/removing atoms from a known linker.
3. `template` (20% chance): Sticking standard building blocks together.

While this casts a wide net for discovery, it forces researchers to rely on "luck" to generate variations of a specific molecule they are interested in.

## 2. The Solution: "Directed Generation" Controls
It is **highly feasible** to expose the generator's internal parameters to the UI, allowing researchers to shift from "Random Discovery" to "Directed Optimization".

### Proposed UI Additions (The "Directed Design" Panel)

**A. Strategy Weights (Sliders)**
Instead of hardcoding `weights=[0.5, 0.3, 0.2]`, we expose these as sliders.
- *Use Case*: A researcher wants entirely new topological ideas. They set "Template-based" to 100% and "Substitution" to 0%.
- *Use Case*: A researcher has a great backbone but wants better solubility. They set "Substitution" to 100% to only generate functional group variations.

**B. "Seed" Molecule Pinning**
Currently, the generator randomly selects a "seed" linker from the database of 274 known linkers to modify.
- *Implementation*: Allow the user to input a specific SMILES string (e.g., the "Top Candidate" they found in a previous run). 
- *Result*: The generator *only* mutates that specific molecule, generating 100 structural neighbors (derivatives) rather than jumping across chemical space.

**C. Deterministic Functional Group Targeting**
Currently, the user can "exclude" elements. We can strengthen the "Require" logic.
- *Implementation*: Allow the user to specify exact functional groups to staple on (e.g., "Must add `-COOH` groups").
- *Result*: The generator algorithm explicitly filters out any `substitution` or `template` result that doesn't successfully attach the required group.

## 3. Implementation Path
This requires changes to two files:
1. `mof_bridge/linker_generator.py`: Update the `generate_candidates` signature to accept `strategy_weights`, `seed_smiles`, and `required_groups`.
2. `streamlit_app/pages/8_MOF_Designer.py`: Add a "Directed Generation Controls" expander in the sidebar to pass these values to the `LinkerScreeningSpec`.

## 4. Why this matters for the "Honest Screening" narrative
It transitions the tool from a "Slot Machine" to a "Microscope". Once a researcher finds a promising hit, they can lock it in as a seed and tell the engine: "Stop guessing wildly. Give me 50 slight variations of *this* exact molecule so I can find the one with the best stability score."

---
*G-docs Design Document | 2026-05-30*
