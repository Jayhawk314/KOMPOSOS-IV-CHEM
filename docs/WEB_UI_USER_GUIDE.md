# KOMPOSOS-IV Web UI — User Guide

**Interactive Categorical Reasoning Interface**

Version: 1.8.0
Date: 2026-07-17
Platform: Streamlit — `streamlit run streamlit_app/app.py`

---

## Pages at a Glance

| Page | What it does |
|---|---|
| **1 — Compatibility Checker** | Two-material compatibility with full evidence chain and audit report download |
| **2 — PFAS Scanner** | First-pass PFAS inventory, replacement triage, and PDF report generation |
| **3 — Composition Predictor** | Property prediction from a chemical formula |
| **4 — Cell Designer** | Multi-domain battery cell design and bottleneck analysis |
| **5 — Crystal Dreamer** | Inverse design: target properties → candidate compositions |
| **6 — MP Explorer** | Browse optional Materials Project data and crystal structures |
| **7 — MOF Explorer** | Screen 30 MOFs against operating conditions |
| **8 — MOF Designer** | Generate novel MOF linkers with atom count and donor-atom control |
| **9 — Discovery Workbench** | Composition-first pipeline: inverse design → PFAS → compatibility → synthesis |
| **10 — Advanced Triage Workbench** | Mixed-fidelity: fast triage → charge-balance gate → coverage-aware interface context, with surfaced uncertainty |

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

#### Pairwise decision and constraint diagnostic

Two views of the same native bridge workflow are shown side by side. They are
not independent experiments:

| Engine | What it checks |
|---|---|
| **Pairwise bridge decision** | Native bridge score, physical vetoes, calibration, and ensemble metadata |
| **Derived constraint summary** | Logical rules generated from the same bridge component scores |

The result also shows a cohort-calibrated pairwise probability from a 98-row
development/spent isotonic artifact (OOS ECE 0.072). That is useful reliability
evidence for the recorded cohort; it is not a fresh blind result, is not established
per domain, and does not calibrate multi-interface aggregates.

The combined verdict is one of four states:

| Verdict | Meaning |
|---|---|
| **AGREE** | Score passes and its derived constraint summary has no veto; internal agreement only. |
| **HOLLOW** | Score passes but a derived hard constraint vetoes it. |
| **ORPHAN** | Derived summary has no hard veto but the native score is below threshold. |
| **REJECT** | Both native score and derived summary reject the pair. |

#### Audit Report (download buttons)

Two buttons appear immediately after the verdict:

- **Download Report (Markdown)** — human-readable document with:
  - Executive summary in plain chemistry language for the specific domain
  - Every evidence vote with chemistry interpretation first, math formula second
  - Shared interface partners table (materials that can interface with both A and B)
  - Isomorphism witness chain (if a Rezk-equivalent substitution was found)
  - Fibration transport paths (inherited compatibility via similar materials)
  - Derived logical-constraint summary
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

- **Single Check** — one material against the registry, brand heuristics, AND the OECD
  structural rule (name→PubChem→SMILES) so novel PFAS are caught even when unseen by name.
  Add your cell's **adjoining materials** (one per line) and each PFAS-free replacement is
  ranked by **calibrated compatibility** with the whole stack, surfacing the weakest
  interface ("PFAS-free AND compatible with your cell").
- **Batch Scan** — screen a full bill of materials with detection tiers.
- **Compliance Report** — generates a 7-section auditable PDF for regulatory filings,
  with replacement candidates scored for specific use cases.
- **PFAS Registry** — browse the curated registry + the EPA structural dataset (10,776).

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
- Scores interfaces with available native functors and lists required contacts
  that remain unscored.
- Highlights the bottleneck interface (lowest compatibility score).
- Refuses a full-cell verdict when physical-interface coverage is incomplete.

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
- **Grounded funnel (validated)** scores each candidate: chemical sanity, ≥2 coordinating
  donors, SAscore, donor geometry, + novelty vs. known linkers (~94% recall on real
  synthesized linkers, AUROC ~0.88). The legacy 5 descriptor verdicts
  (Synthesizability/Toxicity/Stability/Activity/Conductivity) are shown as *unvalidated* extras.
- **Directed Generation Controls** (expander): steer the search instead of relying on chance —
  **strategy-weight sliders** (substitution / backbone modification / template),
  **seed-molecule pinning** (paste a SMILES to generate only its derivatives), and
  **required functional groups** (every candidate must carry them). A reproducibility bundle
  records the exact controls used.
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

## Page 10: Advanced Triage Workbench

A **mixed-fidelity** pipeline: fast inverse-design triage, then high-precision
verification of each candidate.

1. **Fast triage** generates candidate compositions.
2. A **pymatgen oxidation-state/charge-balance check** hard-vetoes definite failures;
   unassessable formulas receive no charge-balance verdict.
3. **Multi-domain context** evaluates each survivor in a reference interface system
   (e.g. against an electrolyte and collector) and reports missing scorer coverage; novel
   formulas are mapped to a known topological proxy when a registered name is required.
4. **Uncertainty is surfaced explicitly** (e.g. `4.3 V [4.1–4.5] (conf 0.85)`), so high
   uncertainty is a visible trigger for deeper structural derivation.

> Triage casts a wide net; the later phase applies a charge-balance gate and
> coverage-aware proxy interface checks. Missing coverage and distant proxies block
> strong wording. Frame results as triage, not lab-validated design.

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
(verified 2026-05-30). Confidence is **calibrated** (isotonic, out-of-sample ECE ~0.07).
**No dataset is currently held blind** (`current_blind_version: null`); Q2–Q8 are spent
diagnostics through Q9; Q9 was inspected and used for remediation. Q10 is sealed
and remains the only candidate for a future untouched evaluation.

Audit commands:
```powershell
python audit\run_audit.py --module development
python audit\build_compatibility_calibration.py   # rebuild calibration
python audit\run_compat_calibration.py             # measure ECE/Brier
python audit\run_master_audit.py
```

---

*KOMPOSOS-IV-CHEM | James Ray Hawkins | 2026-05-30*
