# KOMPOSOS-IV Web UI — User Guide

**Interactive Categorical Reasoning Interface**

Version: 1.7.0
Date: 2026-05-28
Platform: Streamlit — `streamlit run streamlit_app/app.py`

---

## Pages at a Glance

| Page | What it does |
|---|---|
| **1 — Compatibility Checker** | Two-material compatibility with full evidence chain and audit report download |
| **2 — PFAS Scanner** | PFAS compliance screening and PDF report generation |
| **3 — Composition Predictor** | Property prediction from a chemical formula |
| **4 — Cell Designer** | Multi-domain battery cell design and bottleneck analysis |
| **5 — Crystal Dreamer** | Inverse design: target properties → candidate compositions |
| **6 — MP Explorer** | Browse optional Materials Project data and crystal structures |
| **7 — MOF Explorer** | Screen 30 MOFs against operating conditions |
| **8 — MOF Designer** | Generate novel MOF linkers with atom count and donor-atom control |
| **9 — Discovery Workbench** | Composition-first pipeline: inverse design → PFAS → compatibility → synthesis |

---

## Page 1: Material Compatibility Checker

### How to use

1. **Select Domain** — Battery, Polymer, Metal, Ceramic, Semiconductor, Glass, Bio.
2. **Select Material A and Material B** — must be from the same domain.
3. Optionally enable **Active Verification (MD)** to trigger a GROMACS simulation
   (requires a real `.gro`/`.top` input bundle; returns a no-verdict readiness state
   if inputs are missing).
4. Click **Check Compatibility**.

### What you get

#### Dual-Engine Verdict

Two independent reasoning engines are shown side by side:

| Engine | What it checks |
|---|---|
| **Categorical Oracle** | Weighted ensemble of structural, calibration, and transport strategies |
| **ZFC Logic Oracle** | Hard constraint verification — logical rules derived from known chemistry |

The combined verdict is one of four states:

| Verdict | Meaning |
|---|---|
| **AGREE** | Both engines pass. High confidence. |
| **HOLLOW** | Categorical scores it viable; ZFC rejects it. Structurally plausible but a hard constraint (e.g. electrochemical stability window) says no. |
| **ORPHAN** | ZFC finds no hard veto; categorical scorer falls below threshold. Weak structural evidence. |
| **REJECT** | Both engines reject the pair. |

#### Audit Report (download buttons)

Two buttons appear immediately after the verdict:

- **Download Report (Markdown)** — human-readable document with:
  - Executive summary in plain chemistry language for the specific domain
  - Every evidence vote with chemistry interpretation first, math formula second
  - Shared interface partners table (materials that can interface with both A and B)
  - Isomorphism witness chain (if a Rezk-equivalent substitution was found)
  - Fibration transport paths (inherited compatibility via similar materials)
  - ZFC constraint summary
  - Methodology table translating every categorical term to chemistry language
  - Report ID for traceability

- **Download Audit Trail (JSON)** — full machine-readable audit trail
  for programmatic verification and lab records.

Both files are named `compat_{A}_{B}_{domain}.{ext}`.

#### Score Breakdown

Bar chart and table of the component scorer values from the domain bridge.

#### Ensemble Votes & Categorical Evidence Chain

An expandable section showing every vote in the ensemble:

**Evidence quality summary** — four metrics at a glance:
- Total votes, formal proof votes, structural-only votes, no-category votes.

**Vote summary table** — columns: Strategy, Score, Confidence, Verdict,
Evidence quality (`✓ Formal proof` / `~ Structural` / `✗ No category`), Reasoning.

**Per-strategy evidence expanders** — three STT strategies show full detail:

*Structural Role Analysis (Simplicial Yoneda):*
- Chemistry narrative: what the Yoneda distance means for this domain
  (e.g. "Electrochemical Profile Dissimilarity: 0.31 — 69% shared interface chemistry")
- Formal proof steps: numbered trace of the presheaf computation
- Shared partners table: materials that can interface with both A and B,
  with confidence values in each direction
- Yoneda distance, presheaf overlap, max transfer threshold

*Inherited Compatibility (Fibration Transport):*
- Chemistry narrative explaining the transport paths
- Per-path table: via-material, transport strength, shared property features
- Drill-down: exact shared property tags per path

*Equivalent Material Check (Rezk Equivalence):*
- Chemistry narrative in domain language
  (e.g. "LCO and NMC811 are electrochemically interchangeable — same SEI chemistry")
- Isomorphism witness: shared relation count, logic chain, transport morphism table

#### Raw Score Data

Full JSON of all scores for debugging and programmatic use.

---

## Page 2: PFAS Scanner

Screens materials against 2026 PFAS regulations.

- **Single Check** — one material against the PFAS registry.
- **Batch Scan** — screen a full bill of materials.
- **Compliance Report** — generates a 7-section auditable PDF for regulatory filings,
  with replacement candidates scored for specific use cases.
- **PFAS Registry** — browse the full known-PFAS database.

---

## Page 3: Composition Predictor

Predict properties from a chemical formula using a 120-dimensional physics embedding.

- Uncertainty tiers: Ground Truth, Dense Interpolation, Sparse Extrapolation.
- Optional Materials Project crystal structure lookup when MP cache is installed.
- Dempster-Shafer evidence fusion breakdown per property.

---

## Page 4: Cell Designer

Design a multi-domain battery cell and identify the weakest interface.

- Specify anode, cathode, electrolyte, separator, and current collectors.
- Runs compatibility checks across all internal interfaces.
- Highlights the bottleneck interface (lowest compatibility score).
- Shows the full scoring breakdown per interface.

---

## Page 5: Crystal Dreamer

Inverse design: describe target property bounds, get candidate compositions.

- Define min/max targets for conductivity, stability, formation energy, etc.
- Optional element constraints (required elements, excluded elements, max element count).
- Physics-aware neighbour search in composition space.
- Candidates ranked by predicted property match.

---

## Page 6: MP Explorer

Browse optional Materials Project data when the local 103K+ DFT cache is installed.

- Search by formula, element set, or composition range.
- View lattice parameters, formation energies, convex hull distances.
- Derives crystal structures from the local cache — not a live API call.

---

## Page 7: MOF Explorer

Screen 30 curated Metal-Organic Frameworks against operating conditions.

- Set temperature, pressure, and target guest molecule.
- 5-scorer breakdown per MOF (pore size, BET area, stability, selectivity, cost).
- Side-by-side MOF comparison.

---

## Page 8: MOF Designer

Generate novel MOF linkers with exact atom count and donor-atom control.

- Set target heavy atom count (5–60).
- Filter by donor atom type (N, O, S, mixed).
- 5 KOMPOSOS verdicts per candidate: Synthesizability, Toxicity, Stability,
  Activity, Conductivity.
- SMILES output ready for retrosynthesis tools.

---

## Page 9: Discovery Workbench

Composition-first pipeline for inverse design.

Current stages:
1. Target property bounds with optional min/max controls.
2. Element constraints with searchable element selectors.
3. Compatibility context with searchable material and interface-role selectors.
4. Synthesis planning through the current route planner.

> **Note:** The workbench is a screening and triage prototype. CRYSTAL-specific
> and MOF-specific pipeline modes are planned. Use it to narrow the candidate
> space before running targeted bridge checks on individual pairs.

---

## Molecule Constraint Search (bottom of Compatibility Checker)

Exact-match search across the 37-molecule molecular library.

- Set target heavy atom count (non-hydrogen atoms only).
- Optional molecule class filter and element exclusions.
- Returns only real molecules — no hallucinations, no fabrications.

---

## Audit and Reproducibility

All compatibility scores are **deterministic** given the material database version.
Scores do not change between runs on the same input. The domain category is built
from the same pairwise validation rules used in the benchmark audit.

Current benchmark: **41/41 development pairs, 100.0% accuracy, Brier 0.095**
(verified 2026-05-28). Q8 blind benchmark frozen for next independent validation.

Audit commands:
```powershell
python audit\run_audit.py --module development
python audit\run_master_audit.py
```

---

*KOMPOSOS-IV-CHEM | James Ray Hawkins | 2026-05-28*
