# KOMPOSOS-III Chemistry: Complete Feature Reference

*Updated 2026-05-20 - feature claims aligned with current audit behavior*

---

## At a Glance

KOMPOSOS-III is a **compositional reasoning engine** for chemistry and materials. It answers three questions:

1. **"Will these materials work together?"** — Compatibility checking across 6 material domains
2. **"What properties does this composition have?"** — Forward prediction from any chemical formula
3. **"What composition gives me these properties?"** — Inverse design from target specifications

No neural networks. No training data. No GPUs. Category theory + ZFC set theory over curated knowledge graphs.

---

## 1. Material Compatibility (7 Domain Bridges)

Check if two materials are compatible. Five independent scorers (thermal, mechanical, chemical, structural, transport) evaluate each pair. Scores are 0-1 with full traceability.

| Domain | Materials | Example |
|--------|----------|---------|
| Battery | 28 | NMC811 + EC electrolyte |
| Polymer | 33 | PEO + PVDF blend |
| Metal | 36 | Cu + Al galvanic pair |
| Ceramic | 28 | Al2O3 + ZrO2 composite |
| Semiconductor | 27 | Si + GaAs heterostructure |
| Glass | 23 | Borosilicate + soda-lime seal |
| MOF | 30 | ZIF-8 CO2 capture |
| **Total** | **205** (bridge materials) | |

With Materials Project integration: **103K+ materials** with DFT-computed formation energies, crystal structures, and lattice parameters.

**API:** `POST /api/v1/compatibility`
**UI:** Compatibility Checker (page 1)

---

## 2. Multi-Domain Analysis

Span 2-4 domains in a single query. "NMC811 cathode + LLZO electrolyte + PEO binder + Cu collector" crosses battery, ceramic, polymer, and metal bridges.

Three cross-bridge functors:
- **Battery-Polymer** — binder compatibility (voltage, chemical, swelling)
- **Battery-Metal** — collector compatibility (voltage window, corrosion). Supports coated substrates (carbon, Al2O3, TiN)
- **Ceramic-Metal** — coating/substrate compatibility (CTE, sintering). Supports deposition methods (PVD, CVD, ALD)

Scoring modes: bottleneck (conservative), weighted (balanced), auto-detect.

**API:** `POST /api/v1/multi-domain`
**UI:** Cell Designer (page 4)

---

## 3. Molecular-Level Reasoning

37 molecules (solvents, salts, monomers, reagents, coatings, gases) with PubChem CIDs, CAS numbers, and SMILES. Five molecular scorers: electronic, thermodynamic, steric, solubility, reactivity.

Cross-bridge functor connects molecules to materials: "EC + DMC + LiPF6 electrolyte with NMC811 cathode" scores at both molecular and material levels.

**Ligand constraint search (Kulik 22-atom challenge):** Find molecules matching exact heavy atom counts, element requirements, and functional classes. Heavy atom counting uses element parsing (Fe != F), supports H2 (0 heavy atoms). Enables academic research on MIT Kulik group's computational screening challenges.

**API:** `GET /api/v1/molecules`, `POST /api/v1/molecular-compatibility`, `POST /api/v1/search-molecules`
**UI:** Compatibility Checker (page 1) — Molecule Search section

---

## 4. Forward Composition Prediction

Enter any chemical formula — get predicted properties with confidence bounds.

**Predicted properties:**
- Voltage (V), theoretical capacity (mAh/g), thermal stability (C), ionic conductivity (S/cm)
- Formation energy (eV/atom), synthesizability score (0-1)
- Crystal structure type (21 types: layered, spinel, olivine, garnet, perovskite, ...)

**How it works:**
- Kan extension (categorical extrapolation) over 103K+ known materials in composition space
- **Physics-Embedded Search**: 120D composition vectors (stoichiometry + periodic table Group/Period) ensure chemically relevant neighbor selection.
- **Transparency & Evidence**: Explicitly classifies every prediction into 5 **Uncertainty Tiers** (Ground Truth to Heuristic) to prevent over-reliance on novel chemistry predictions.
- **Estimator De-weighting**: DS-fusion ramp-down ensures DFT ground truth dominates in well-mapped regions.

- Dempster-Shafer fusion of both sources
- 154K+ DFT formation energies from Materials Project as ground truth for stability
- Goldschmidt tolerance factor + rule patterns + Kan vote + Materials Project lookup for structure type
- **Derived crystal structures**: lattice parameters (a, b, c, alpha, beta, gamma), space groups, and volume per atom via Kan extension over nearest MP entries, with full provenance chain

**Active Verification:**
- **MD Bridge**: runs GROMACS when real `.gro` and `.top` inputs are provided through API `md_conditions`, the Streamlit input controls, or `data/gromacs_inputs/<pair>/`.
- Parses GROMACS energy/MSD XVG outputs to calculate potential-energy drift and MSD-derived diffusion.
- Converts measured MD signals into ZFC constraint scores and fuses CAT+MD evidence with Dempster-Shafer.
- Without real GROMACS inputs or analyzable trajectory signals, returns `verdict: no_verdict` and `measured_md: false` instead of presenting a simulated STABLE/UNSTABLE result.

**Validation status (updated 2026-05-21):** 215 curated literature pairs pass the internal compatibility benchmark. Q2, Q3, and Q4 are spent diagnostic sets because their misses informed scorer fixes or post-run analysis; Q3's first blind run was 83.3% accuracy, balanced accuracy 82.5%, MCC 0.662, Brier score 0.122, and ECE 0.207 before Q3-derived tuning. Q4 (`audit/external_blind/compatibility_2026_q4.json`) is frozen with SHA256 `11dd612877667acfa1c7ddeb3626a7f2859d065b5c1c3440fccc4f60f2acf714`; its first run evaluated 42/42 with zero skips, zero overlap with prior benchmark/dev identities, 85.7% accuracy, balanced accuracy 85.6%, MCC 0.712, Brier score 0.150, ECE 0.140, and protocol pass true. After typed morphism development for battery-metal, ceramic, semiconductor, and glass failure families, Q4 diagnostic rerun is 100.0% accuracy, balanced accuracy 100.0%, MCC 1.000, Brier score 0.100, and ECE 0.188, with protocol pass false because Q4-derived dev rows now overlap Q4. This is not a fresh blind claim. Formation-energy Phase 16 uses a frozen 5,000-entry external MP-style split; held-out MAE improved from 0.990 to 0.202 eV/atom, with C50=48.0%, C80=78.6%, C95=93.7%.

**Compatibility calibration:** `audit/dataset_registry.json` maps each dataset to `development`, `spent_diagnostic`, or `current_blind`. `python audit/build_compatibility_calibration.py` builds `audit/calibration/compatibility_calibration_2026_q4_dev.json` from calibration-eligible spent diagnostics plus development files, deduplicates exact pair identities, and still excludes Q4 from calibration. API compatibility responses include `scores.calibration` with raw score, calibrated probability, reliability-bin support, and artifact version.

**Pre-Q5 math add-ons:** Compatibility responses and audit decisions now include a bounded strategy ensemble: base bridge rule score, typed morphism evidence, reliability calibration, strict Yoneda/Kan transfer guard, MetaKan failure-memory gate, ZFC-style constraint vote, and measured MD/real-tool evidence when available. Domains also publish typed capability metadata so the system can state which math/evidence structures are active for a verdict.

**API:** `POST /api/v1/predict-composition`, `POST /api/v1/interpolate`
**UI:** Composition Predictor (page 3)

---

## 5. Inverse Composition Design ("Crystal Dreamer")

The inverse of prediction: given target properties, find candidate compositions.

**Input:** Target properties (e.g. voltage > 4V), element constraints (e.g. no cobalt), synthesizability floor, domain restriction.

**Search strategies:**

| Strategy | What it does |
|----------|-------------|
| Anchor perturbation | Shift stoichiometries of 103K+ known materials by +/-5%, 10%, 20% |
| Interpolation sweeps | Walk between same-domain material pairs at 0.1 steps |
| Element substitution | Swap elements within chemical groups (Ni<->Fe<->Mn, O<->S, etc.) |
| Stoichiometry variation | NMC triangle grid, olivine M-site sweep, spinel variations |

**Output:** Ranked candidates with overall score (0-1), per-target scores, predicted properties, strategy provenance, synthesizability, formation energy, structure type.

**Performance:** 500 candidates evaluated in ~2.5 seconds (forward predictor ~5ms each).

**Example:**
```python
from composition_engine.designer import CompositionDesigner, DesignSpec, PropertyTarget, ElementConstraint

designer = CompositionDesigner()
result = designer.design(DesignSpec(
    targets=[PropertyTarget("voltage", min_value=4.0)],
    element_constraints=ElementConstraint(excluded_elements=["Co"]),
))
# 500 candidates, top: LiMn2O4 (score 0.911)
```

**API:** `POST /api/v1/design-composition`
**UI:** Crystal Dreamer (page 5)

---

## 6. PFAS Compliance

Screen materials against 35 PFAS substances (real CAS numbers, 7 categories) with EU/US/Stockholm Convention regulations. Urgency-based alerts with PFAS-free replacement suggestions scored for specific use cases.

**Urgency levels:** critical (BANNED) > high (ban <12 months) > moderate (RESTRICTED) > low (UNDER_REVIEW) > none

**Key replacements:**
- PVDF battery binder -> CMC+SBR (0.83), PAA (0.76)
- PTFE seal/gasket -> EPDM (0.78), PDMS (0.74)
- Nafion membrane -> SPEEK (0.63), PBI (0.55)

**Regulatory deadlines:** EU PFHxA ban Aug 2026, US EPA Oct 2026.

**Brand name auto-detection (Phase 11.6):** 11 brand names (Teflon, Kynar, Viton, Scotchgard, Gore-Tex, Stainmaster, Chemours, 3M Novec, Dyneon, Daikin, Solvay Solef) auto-resolve to base PFAS substances via `resolve_base_pfas()`. Brand name matches return the same quality results as exact CAS matches -- full replacements, regulatory data, and CAS numbers.

**Detection tiers:** Every result includes a `detection_tier` (exact/heuristic/unknown) and `resolved_base` field for audit trail transparency. Exact = CAS number match. Heuristic = brand name or substring match, resolved to base substance. Unknown = not PFAS.

**PFAS Compliance Reports (Phase 11):** Generate auditable 7-section compliance reports for bill-of-materials screening. Includes executive summary, screening results, regulatory timeline, replacement recommendations, action plans, provenance, and verdict logic. Full traceability from material → detection → regulation → alternative → verdict.

**PDF compliance reports (Phase 11.6):** Branded PDF downloads with client name, domain-specific scores (Adhesion, Electrolyte, Thermal, Cathode via cross-bridge scoring), narrative recommendations per detection, compatibility provenance tables, P0/P1/P2 priority action plans with timelines, and audit certificates. Cross-bridge scoring sources domain scores from `battery_polymer.score_polymer_electrode_compatibility()`.

**API:** `POST /api/v1/pfas-check`, `GET /api/v1/pfas-substances`, `POST /api/v1/pfas-alternatives`, `POST /api/v1/pfas-report`
**UI:** PFAS Scanner (page 2) — single check, batch BOM scan, registry browser, Compliance Report tab with PDF download

---

## 7. Synthesis Planning

24 synthesis routes, 53 precursors with cost/hazard/availability data. Input a target material, get ranked routes with equipment needs, time estimates, and safety ratings.

Covers battery cathodes (LFP, NMC, LCO, LMO, NCA), anodes (graphite), solid electrolytes (LLZO, LGPS, NASICON), ceramics (Al2O3, TiN, SiC), polymers (PVDF, PEO), and electrode fabrication.

**API:** `POST /api/v1/synthesis`, `GET /api/v1/synthesis/targets`

---

## 8. ZFC Dual-Engine Verification

Independent set-theoretic constraint verification using ZFC-style predicates. It checks internal logical consistency and constraint satisfaction; it is not a proof of physical truth by itself. Classifies every prediction:

| Classification | Meaning |
|---------------|---------|
| **AGREE** | Category score passes and the ZFC constraint verifier finds no veto |
| **ORPHAN** | ZFC verifier finds no veto, but category score is below threshold |
| **HOLLOW** | Category score passes, but the ZFC constraint verifier finds a veto |
| **REJECT** | Both say no |

MaterialZFCBridge checks voltage, thermal, and chemical constraints independently of the scorer pipeline. The ZFC veto threshold is 0.20 -- any scorer below this triggers a hard constraint veto, not a standalone experimental proof.

**Empirical bond constraints:** ZFC bond plausibility uses local empirical bond distributions with optional ColabFit cache/API support. This is not a guaranteed live dynamic potential service in the current build.

**HOLLOW state detection**: 29 material pairs in the battery domain alone score above viability (0.45+) but contain a ZFC veto. These are pairs a pure score-only model could overstate. The Compatibility Checker UI surfaces this classification with expandable reasoning traces.

**API:** `POST /api/v1/zfc-verify`
**UI:** Compatibility Checker (page 1) -- dual-engine verdict shown for every query

---

## 9. MOF Bridge & Linker Designer (Phase 11)

Metal-Organic Frameworks — "the LEGOs of chemistry" (Prof. Heather Kulik, MIT). Two capabilities: (1) validate existing MOFs against conditions, (2) design novel linkers via inverse design.

### MOF Validation

30 MOFs with DOI citations, experimental property data, and CSD codes. Five scorers: pore accessibility, chemical stability, thermal compatibility, mechanical compatibility, application suitability.

**MOF-vs-conditions validation:** Unlike other bridges (A-vs-B pair compatibility), MOFs are scored against operating conditions (temperature, pressure, target molecule size, environment, water/acid stability requirements).

**30 MOFs spanning 8 topologies:** pcu (ZIF-8, HKUST-1), fcu (UiO-66, UiO-67), ftw (MOF-5), reo (MIL-101, MIL-53), sql (IRMOF-1), nbo (MOF-74), pts (PCN-222), ith (MIL-88).

**Applications:** gas_storage, gas_separation, catalysis, drug_delivery, sensing, water_purification, energy_storage.

**API:** Part of `/api/v1/materials` and `/api/v1/materials/mof` endpoints
**UI:** MOF Explorer (page 7) — screen all MOFs, single MOF detail, database overview

### MOF Linker Inverse Design

**Kulik 22-atom challenge:** "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms." — Prof. Heather Kulik, MIT. KOMPOSOS solves this with exact atom count control (5-60 atoms, default 22).

**5 KOMPOSOS verdicts:** synthesizability, toxicity, stability, activity, conductivity (ZFC + CAT dual-engine). Results: AGREE (score passes and constraint verifier finds no veto), HOLLOW (score passes but a constraint veto fires), ORPHAN (no constraint veto but category score is weak), REJECT (both fail).

**External validation priority:** For MOF/linker work, the next useful evidence is not a larger internally scored generation run. A small exported packet of about 50 linkers sent through an external molSimplify/DFT workflow is more valuable than another thousands-of-rows internal CSV scored only by KOMPOSOS.

**Post-filtering:** Donor atoms (N, O, S) — filter to only linkers containing required coordinating atoms for metal binding. Application contexts: CO2 capture, gas storage/separation, catalysis, sensing, general MOF design.

**Output:** Ranked list with molecular formula, atom count, molecular weight, SMILES, donor atom counts (N/O/S), verdict summary. CSV/JSON export.

**API:** `POST /api/v1/design-mof-linker`
**UI:** MOF Designer (page 8) — exact atom count, donor filters, application-specific generation

---

## Web UI (Streamlit)

8 interactive pages. Run with `streamlit run streamlit_app/app.py`.

| Page | What it does |
|------|-------------|
| Compatibility Checker | Pick domain, select two materials, see dual-engine verdict (AGREE/HOLLOW/ORPHAN/REJECT) + 5-scorer breakdown with bar charts + Molecule Search section |
| PFAS Scanner | Single check, batch BOM scan (with detection tier columns + brand name resolution), PFAS registry browser + Compliance Report tab (7-section reports, client name branding, PDF download) |
| Composition Predictor | Enter formula, get properties + structure + derived crystal structure with lattice params + provenance |
| Cell Designer | Build multi-domain cells with presets, bottleneck analysis |
| Crystal Dreamer | Set target properties + element constraints, find candidate compositions with derived structures |
| MP Explorer | Browse Materials Project data, derive crystal structures, nearest-MP search, dataset stats |
| MOF Explorer | Screen 30 MOFs against operating conditions, single MOF detail view, topology/application grouping |
| MOF Designer | Generate novel linkers with exact atom count (5-60, default 22), donor atom filters (N/O/S), application contexts (CO2 capture, gas storage, catalysis), 5 KOMPOSOS verdicts, AGREE-only filtering, CSV/JSON export |

---

## Web API (v1.2.0)

17 authenticated endpoints + 2 public (root, health). API key auth via `X-API-Key` header. Rate limited at 120 req/min per key. Docker-ready. Python SDK included.

Full endpoint list: see [CLAUDE.md](../CLAUDE.md) or visit `/docs` (Swagger UI) when running.

---

## Math Foundations

| Layer | What |
|-------|------|
| Category theory | Objects, morphisms, functors, natural transformations, Kan extensions, enriched categories |
| Dempster-Shafer | Evidence fusion from multiple sources with belief/plausibility |
| ZFC set theory | Independent logical verification (axiom of choice, well-ordering, separation) |
| Ricci curvature | Ollivier-Ricci on knowledge graphs (optimal transport) |
| Persistent homology | H0 components, H1 loops, H2 voids |
| Homotopy type theory | Path induction, identity types |
| Game theory | Nash equilibrium, open games |

56+ mathematical frameworks across 13 layers. All stdlib-compatible (no GPU required).

---

## Test Coverage

| Module | Tests |
|--------|-------|
| 7 single-domain bridges | 734 |
| Cross-bridge functors | 103 |
| Synthesis planner | 94 |
| Molecular bridge (90) + constraint search (27) | 117 |
| PFAS bridge (81) + PFAS report (32) | 113 |
| MOF bridge | 83 |
| Composition engine (forward + inverse + MP) | 252 |
| API endpoints | 52 |
| ZFC + enhanced math | 110 |
| **Total** | **1,633** |

64/64 dogfood questions pass against published literature (38 original + 26 Phase 11).

---

## What Makes This Different

Every funded competitor ($2.1B+ total) uses black-box ML. KOMPOSOS is:

- **Interpretable** — every score traces to published property data
- **Multi-domain** — 7 material domains in one query (no competitor does this)
- **Predictive** — forward AND inverse composition design
- **Compliant** — PFAS screening with branded PDF compliance reports, detection tiers, brand name resolution, and real regulatory data
- **Scaled** — 103K+ materials from Materials Project with DFT formation energies and crystal structures
- **Fast** — no GPU, no training. Compatibility check in <10ms, inverse design in <3s, MOF screening in <1s
- **Self-auditing** — dual-engine catches HOLLOW states that black-box AI would miss (29 in battery domain alone)
- **Tested** — 1,633 automated tests, 64 dogfood questions against literature
