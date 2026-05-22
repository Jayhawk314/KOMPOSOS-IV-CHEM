# MASTER REPLICATOR ARCHITECTURE
## KOMPOSOS-III as the Reasoning Cortex of a Self-Driving Lab
### Updated 2026-04-02 — reflects actual running code

---

## What This Document Covers

This is the definitive architecture document for the **replicator** side of KOMPOSOS-III. It documents every module, every bridge, every functor, and every connection as they exist in running code with passing tests.

For the drug repurposing architecture, see `docs/MASTER_ARCHITECTURE.md`.

---

## System Overview

KOMPOSOS-III is the **reasoning layer** of a self-driving laboratory. It answers five questions:

1. **WILL this work?** — Material compatibility screening across 7 domains
2. **HOW do you make it?** — Synthesis route planning with precursors and conditions
3. **WHAT properties does it have?** — Forward prediction from any chemical formula (Kan extension + Dempster-Shafer fusion)
4. **WHAT should we design?** — Inverse composition design: given target properties, find candidate materials
5. **WHAT should we predict?** — Oracle inference engine with 9+ mathematical strategies

```
                    ┌─────────────────────────────────────┐
                    │         USER / SPECIFICATION         │
                    │   "Make me an LFP cathode cell"      │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │       CROSS-BRIDGE ANALYZER          │
                    │   MultiDomainAnalyzer.analyze()      │
                    │   Spans 4+ domains per query         │
                    └───┬───────┬───────┬───────┬─────────┘
                        │       │       │       │
              ┌─────────▼┐ ┌───▼───┐ ┌─▼─────┐ ┌▼────────┐
              │ battery   │ │polymer│ │ metal │ │ ceramic │
              │ _bridge/  │ │bridge/│ │bridge/│ │ bridge/ │
              │ 22 mats   │ │33 mat │ │36 mat │ │ 28 mat  │
              │ 58 tests  │ │98 test│ │101 tst│ │102 test │
              └───────────┘ └───────┘ └───────┘ └─────────┘
              ┌───────────┐ ┌───────┐
              │semicond.  │ │ glass │
              │ _bridge/  │ │bridge/│
              │ 27 mats   │ │23 mat │
              │ 113 tests │ │179 tst│
              └───────────┘ └───────┘
                        │
              ┌─────────▼──────────────────────┐
              │     SYNTHESIS PLANNER           │
              │   24 routes, 53 precursors      │
              │   SynthesisPlanner.plan()       │
              │   94 tests                      │
              └────────────────────────────────┘
                        │
              ┌─────────▼──────────────────────┐
              │     CATEGORICAL LAYER           │
              │   StoredObject, StoredMorphism   │
              │   StoredPath, Category           │
              │   Ricci curvature, Sheaf check   │
              └────────────────────────────────┘
```

---

## Current Status (2026-03-24)

| Phase | Module | Status | Tests | Key Metric |
|-------|--------|--------|-------|------------|
| Pre-existing | oracle/ | COMPLETE | -- | AUROC 0.7577 |
| Pre-existing | battery_bridge/ | COMPLETE | 58/58 | 22 materials |
| Phase 1 | polymer_bridge/ | COMPLETE | 98/98 | 33 polymers |
| Phase 1 | metal_bridge/ | COMPLETE | 101/101 | 36 metals |
| Phase 1 | ceramic_bridge/ | COMPLETE | 102/102 | 28 ceramics |
| Phase 1 (bonus) | semiconductor_bridge/ | COMPLETE | 113/113 | 27 semiconductors |
| Phase 1 (bonus) | glass_bridge/ | COMPLETE | 179/179 | 23 glasses |
| Phase 1 | cross_bridge/ | COMPLETE | 103/103 | 3 functors + multi-domain |
| Phase 2 | synthesis_planner/ | COMPLETE | 94/94 | 24 routes, 53 precursors |
| Phase 3 | molecular_bridge/ | COMPLETE | 90/90 | 37 molecules, PubChem CIDs |
| Phase 5 | pfas_bridge/ | COMPLETE | 81/81 | 35 PFAS, 7 categories |
| Phase 7 | composition_engine/ | COMPLETE | 196/196 | Forward + inverse prediction |
| Phase 8 | cross_bridge fixes | COMPLETE | +10 | Coated substrates, deposition |
| Phase 9 | inverse design | COMPLETE | +37 | Crystal Dreamer: 4 strategies |
| Phase 10 | Materials Project | COMPLETE | +56 | 103K+ materials, structure derivation |
| Phase 11 | Kulik/PFAS Sprint | COMPLETE | +152 | MOF bridge, PFAS reports, constraint search |
| Phase 12 | Estimator De-weighting| COMPLETE | +5 | InP relative error 270% -> 0.0% |
| Phase 13 | Embedded Physics | COMPLETE | +12 | 120D group-aware composition vectors |
| Phase 14 | Active Verification | COMPLETE | +15 | GROMACS MD integration with explicit input-bundle requirements |
| Phase B | api/ (v1.2.0) | COMPLETE | 52/52 | 19 endpoints, auth, Docker |
| -- | ZFC + enhanced math | COMPLETE | 110/110 | Enriched categories, D-S, streaming Kan |

**Totals: 8 bridges, 103K+ materials (199 curated + 103,644 MP), 1,633 tests passing (includes 22 MOF designer tests), 24 synthesis routes, 19 API endpoints**

**Audit Results (2026-05-19):** 215 unique literature pairs, **100% accuracy** on tuned pairs, **92.0% accuracy** on held-out generalization. Structure prediction accuracy: **96%**.

---

## Module Architecture

### Layer 1: Material Bridges (7 domains)

Every bridge follows the **exact same pattern**:

```
<domain>_bridge/
  material_properties.py    # Dataclass + curated property table + KNOWN_GOOD/BAD
  interaction_scoring.py    # 5 scorers, each returning [0,1]
  interface_validator.py    # Weighted composite: 0.75*bottleneck + 0.25*avg
  <flow_analyzer>.py        # Multi-component assembly analysis
  integration.py            # material_to_stored_object, build_category
  __init__.py               # Public API, version 1.0.0
  tests/                    # 40-180 tests per bridge
```

| Bridge | Dataclass | Scorers | Analyzer | Materials |
|--------|-----------|---------|----------|-----------|
| battery_bridge/ | BatteryMaterial | 5 (ion, echem, interface, mech, degrad) | BatteryFlowAnalyzer | 22 |
| polymer_bridge/ | PolymerMaterial | 5 (solubility, thermal, mech, chem_resist, aging) | PolymerBlendAnalyzer | 33 |
| metal_bridge/ | MetalMaterial | 5 (galvanic, phase, joinability, mech, corrosion) | MetalJointAnalyzer | 36 |
| ceramic_bridge/ | CeramicMaterial | 5 (sintering, CTE, chem_compat, mech, degradation) | CeramicAssemblyAnalyzer | 28 |
| semiconductor_bridge/ | SemiconductorMaterial | 5 (lattice, band, thermal, defect, process) | HeterostructureAnalyzer | 27 |
| glass_bridge/ | GlassMaterial | 5 (thermal, optical, chem, mech, viscosity) | GlassAssemblyAnalyzer | 23 |
| mof_bridge/ | MOFMaterial | 5 (pore, chem, thermal, mech, app) | MOFInterfaceValidator | 30 |

### Layer 2: Cross-Bridge Functors

```
cross_bridge/
  battery_polymer.py   # F: Battery -> Polymer (voltage, thermal, mech, chem)
  battery_metal.py     # F: Battery -> Metal (echem, galvanic, CTE, conductivity, corrosion)
                       #   Supports metal_coating param for coated substrates (carbon, Al2O3, TiN)
  ceramic_metal.py     # F: Ceramic -> Metal (CTE, thermal processing, mech, chem)
                       #   Supports DepositionMethod enum (PVD, CVD, ALD, PLASMA_SPRAY, BULK_SINTERING)
  molecular_material.py # F: Molecular -> Battery (molecule-material cross-scale functor)
  multi_domain.py      # MultiDomainAnalyzer: spans 3-4 bridges in single query
                       #   Supports scoring_mode: "bottleneck" | "weighted" | auto-detect
  __init__.py
  tests/               # 103 tests
```

**Cross-bridge scoring formula:**
- Each functor scores 4-5 dimensions, each [0,1]
- Composite = weighted sum of dimensions
- Veto rules: if any critical dimension < threshold, cap composite
- **Battery-metal coating awareness**: `metal_coating` param boosts anodic limit (carbon +1.5V, Al2O3 +1.0V, TiN +1.2V)
- **Ceramic-metal deposition method**: `DepositionMethod` enum controls CTE compliance factor (PVD/CVD=0.5, ALD=0.4) and thermal processing evaluation
- MultiDomainAnalyzer scoring modes:
  - `bottleneck` (default for <=2 interfaces): `overall = 0.75 * min + 0.25 * avg`
  - `weighted` (default for >2 interfaces): weighted average with 0.5x weight on bottleneck interface
  - Auto-detect selects mode based on interface count

**Pre-defined multi-domain queries:**
| Query | Components | Domains | Result (bottleneck) | Result (weighted) |
|-------|-----------|---------|--------|--------|
| LFP Standard Cell | LFP + PVDF + Al_foil + LiPF6 | battery, polymer, metal | 0.853 VIABLE | same |
| Graphite Anode | Graphite + CMC + Cu_foil | battery, polymer, metal | 0.837 VIABLE | same |
| YSZ Thermal Barrier | ZrO2_YSZ + Inconel_718 | ceramic, metal | 0.832 VIABLE | same |
| Solid-State Battery | NMC811 + LLZO + PEO + Cu_foil | battery, ceramic, polymer, metal | 0.295 NOT VIABLE | ~0.55 VIABLE |
| Problematic PEO+NMC | PEO + NMC811 + Al_foil + LiTFSI | battery, polymer, metal | 0.263 NOT VIABLE | NOT VIABLE |

### Layer 3: Composition Engine (Forward + Inverse Prediction)

```
composition_engine/
  parser.py              # Formula parser, 41 elements, shorthand map (NMC811 -> LiNi0.8Mn0.1Co0.1O2)
  properties.py          # Rule-based estimates: Faraday capacity, Vegard, EN correlation
  known_compositions.py  # KnownCompositionDB from all 7 bridges + Materials Project (~103K materials)
  mp_loader.py           # MPEntry/MPCache: gzipped JSON cache of Materials Project data
  spatial_index.py       # KD-tree O(log N) nearest-neighbor queries in composition space
  structure_deriver.py   # Lattice params via Kan extension over nearest MP structures
  predictor.py           # CompositionPredictor: Kan extension + D-S fusion + derived structure
  formation_energy.py    # DFT surrogate: 154K+ Ef from MP, Kapustinskii + Miedema, hull distance, ZFC constraints
  structure_predictor.py # Crystal structure type: 4 sources (rules + Kan + Goldschmidt + MP), 21 types
  designer.py            # Inverse design: 4 search strategies, O(N log N) KD-tree dedup
  __init__.py
  tests/                 # 252 tests (30 parser + 22 properties + 31 predictor + 39 Ef + 42 structure + 32 designer + 15 MP loader + 41 structure deriver)
```

**Forward prediction:** Enter any chemical formula, get voltage, capacity, thermal stability, ionic conductivity, formation energy, synthesizability score, crystal structure type, and derived crystal structure (lattice parameters + space group + provenance). 
- **Physics-Embedded Search**: 120D composition vectors incorporate Periodic Table Group/Period to ensure chemically relevant neighbor selection.
- **Estimator De-weighting**: DS-fusion ramps down rule-based weights linearly as distance to ground truth decreases, protecting DFT accuracy.
- **True LOO Validation**: Native `exclude_formula` support in `_kan_predict` for unbiased accuracy reporting.

**Inverse design (Crystal Dreamer):** Given target properties + element constraints, find candidate compositions via 4 search strategies:

| Strategy | How | Budget |
|----------|-----|--------|
| Anchor perturbation | +/-5%, 10%, 20% stoichiometry shifts on 103K+ known materials | 40% |
| Interpolation sweeps | Walk between same-domain material pairs at 0.1 steps | 25% |
| Element substitution | Swap elements within 7 chemical groups (Ni<->Fe<->Mn, O<->S, etc.) | 20% |
| Stoichiometry variation | NMC triangle grid, olivine M-site sweep, spinel variations | 15% |

**Performance:** ~5ms per predict() call, 500 candidates in ~2.5s.

### Layer 4: Synthesis Planner

```
synthesis_planner/
  route_graph.py       # SynthesisConditions, SynthesisStep, SynthesisRoute + 24 curated routes
  precursor_db.py      # 53 precursors with cost, purity, hazard, supplier
  route_planner.py     # SynthesisPlanner, MaterialSpec, ScoredRoute
  integration.py       # step_to_stored_morphism, route_to_stored_path
  __init__.py
  tests/               # 94 tests
```

**Route targets:**
- Battery cathodes: LFP (3 routes), NMC811, NMC622, NMC111, LCO, LMO, NCA
- Battery anodes: Graphite electrode (2 routes: NMP-based, water-based)
- Solid electrolytes: LLZO, LGPS, Li3PS4, NASICON
- Ceramics: Al2O3 (2 routes: Bayer, PVD), TiN (PVD), SiC (Acheson)
- Polymers: PVDF film, PEO electrolyte membrane
- Coatings: YSZ thermal barrier
- Electrode fabrication: LFP cathode, NMC811 cathode

### Layer 5: Categorical Infrastructure

```
categorical/
  category.py          # Object, Morphism, Category (the foundation)
  kan_extensions.py    # Left/Right Kan extensions, Functor, CommaCategory

data/
  store.py             # StoredObject, StoredMorphism, StoredPath, EquivalenceClass

geometry/
  ricci.py             # Ollivier-Ricci curvature (bottleneck detection)
  flow.py              # Discrete Ricci flow (geometrization)
  spectral.py          # Spectral graph analysis (community detection)

topology/
  persistence.py       # Persistent homology (feedback loops, cascades)
  hypergraph.py        # Multi-way interactions

hott/
  identity.py          # Identity types, paths
  path_induction.py    # J eliminator
  homotopy.py          # Path homotopy checker
  geometric_homotopy.py

cubical/
  paths.py             # Interval, PathType, Square, Cube
  kan_ops.py           # hcomp, hfill, comp, inv (gap-filling)

game/
  open_games.py        # Categorical game theory
  nash.py              # Nash equilibrium (prediction optimization)

oracle/
  strategies.py        # 9 inference strategies
  coherence.py         # Sheaf coherence checker
  optimizer.py         # Game-theoretic selection
  conjecture.py        # Conjecture generator
  prediction.py        # Prediction engine
```

---

## Data Flow: End-to-End Example

**User asks:** "Make me an LFP cathode with standard binder"

```
1. Material Selection (cross_bridge/multi_domain.py)
   Query: [LFP (battery), PVDF (polymer), Al_foil (metal), LiPF6 (battery)]

   Battery-Polymer functor: PVDF + LFP -> 0.87 (voltage OK, chem OK)
   Battery-Metal functor: Al_foil + LFP + LiPF6 -> 0.85 (no corrosion)

   Overall: 0.853 VIABLE
   Bottleneck: battery-metal interface (Al foil anodic limit)

2. Synthesis Planning (synthesis_planner/route_planner.py)
   Target: "LFP" -> 3 routes found

   Route 1: LFP_sol_gel (score=0.852)
     Steps: dissolve -> gel -> calcine
     Precursors: LiNO3, Fe(NO3)3, H3PO4, citric_acid
     Time: 23h, Max temp: 600C, Risk: low

   Route 2: LFP_solid_state (score=0.844)
     Steps: mix -> calcine -> grind -> sinter
     Precursors: Li2CO3, Fe2O3, NH4H2PO4
     Time: 18h, Max temp: 700C, Risk: low

   Route 3: LFP_hydrothermal (score=0.830)
     Steps: dissolve -> hydrothermal -> wash -> dry
     Precursors: LiOH, FeSO4, H3PO4, DI_water
     Time: 25.5h, Max temp: 180C, Risk: low (but needs autoclave)

3. Electrode Fabrication (synthesis_planner/route_graph.py)
   Target: "LFP_cathode_electrode"
   Route: LFP_cathode_coating
     dissolve PVDF in NMP -> mix LFP+CB+PVDF -> coat on Al foil -> dry -> calender
     Time: 8.6h

4. Categorical Integration (synthesis_planner/integration.py)
   Each step -> StoredMorphism
   Full route -> StoredPath
   Category built with objects=materials, morphisms=steps
   Ricci curvature identifies bottleneck steps
```

---

## Data Flow: Inverse Design Example

**User asks:** "Find me a high-voltage cathode material without cobalt"

```
1. Specification (composition_engine/designer.py)
   DesignSpec:
     targets: [PropertyTarget("voltage", min_value=4.0)]
     element_constraints: ElementConstraint(excluded_elements=["Co"])
     max_candidates: 500

2. Candidate Generation (4 strategies, ~1000 raw candidates)
   Strategy A: Perturbation — shift stoichiometries of 103K+ known materials
   Strategy B: Interpolation — walk between same-domain pairs
   Strategy C: Substitution — swap Co->Fe, Co->Mn, Co->Ni in known cathodes
   Strategy D: Stoichiometry — NMC triangle grid, olivine M-site sweep

3. Pre-filtering (fast, no predict() call)
   - Remove candidates containing Co (element constraint)
   - Deduplicate by composition_distance < 0.01
   → ~500 unique candidates pass

4. Forward Prediction (composition_engine/predictor.py, ~5ms each)
   For each candidate formula:
     - Kan extension over 103K+ known materials in composition space
     - Rule-based estimates (Faraday, Vegard, EN correlation)
     - Dempster-Shafer fusion of both sources
     → PredictedMaterial: voltage, capacity, thermal, conductivity, Ef, structure

5. Scoring (per-target + overall)
   Per-target: 0.8+0.2*confidence if met, exp(-2*distance)*confidence if missed
   Overall: weighted_sum * (0.5+0.5*synth) * stability * (0.5+0.5*conf)
   → Ranked candidates, top: LiMn2O4 (score 0.911, voltage 4.1V, spinel)

6. Result: 500 candidates ranked by overall score
   Each with: formula, predicted properties, target scores,
   synthesizability, formation energy, crystal structure, strategy provenance
```

### Layer 6: Uncertainty Quantification & Evidence Framework (NEW)

KOMPOSOS-III explicitly distinguishes between **Categorical Truth** (known materials) and **Heuristic Hypotheses** (novel discoveries) through a multi-tiered evidence framework:

| Tier | Physical Basis | Validation Path |
| :--- | :--- | :--- |
| **Categorical Ground Truth** | dist < 0.05 | Exact match in `KNOWN_EF` / Bridge Registry. |
| **Dense Interpolation** | dist < 0.2 | High-density local cluster in composition space. |
| **Moderate Extrapolation** | dist < 0.5 | Logical analogs within same element groups. |
| **Sparse Discovery** | dist >= 0.5 | Novel chemistry. Requires MD or lab verification. |
| **Heuristic Prediction** | Rule-based | No nearby neighbors. Based on physical rules of thumb. |

**Key mechanisms:**
- **Estimator De-weighting**: DS-fusion ramps down rule-based weights linearly as distance to ground truth decreases, protecting DFT accuracy.
- **Physics-Embedded Search**: 120D composition vectors incorporate Periodic Table Group/Period to ensure chemically relevant neighbor selection.
- **True LOO Validation**: Native `exclude_formula` support in `_kan_predict` for unbiased accuracy reporting.
- **Active Verification**: GROMACS MD runner can be triggered for borderline (0.45-0.55) or low-confidence queries when prepared `.gro`/`.top` inputs are available; otherwise it returns an explicit no-verdict readiness state.

### Layer 7: Active Verification (Molecular Dynamics)

For high-stakes or low-confidence queries, KOMPOSOS-III can trigger MD verification when prepared GROMACS inputs are available:

```
oracle/
  md_integration.py    # MDIntegrator, MDVerificationResult
  gromacs_runner.py    # GROMACSRunner: input-bundle resolution + subprocess
```

**Key Capabilities:**
- **Automated Triggering**: borderline compatibility scores (0.45-0.55) or low confidence (<0.5) can trigger simulation when a prepared GROMACS input bundle is available.
- **Interfacial Fidelity**: Validates reactive interdiffusion (e.g. sulfide vs oxide) and mechanical delamination.
- **Metadata Feedback**: Returns potential energy shifts, diffusion coefficients, no-verdict input readiness, and measured-MD flags to the API.

---

## Directory Structure

```
KOMPOSOS-III-LAMBDA-max-3D-chem/
│
├── oracle/                    # 9-strategy inference engine
│   ├── strategies.py          # Kan, Semantic, Temporal, Type, Yoneda,
│   │                          #   Composition, Fibration, StructuralHole, Geometric
│   ├── conjecture.py          # Conjecture generation
│   ├── prediction.py          # Prediction engine
│   ├── coherence.py           # Sheaf coherence
│   ├── optimizer.py           # Nash equilibrium selection
│   └── learner.py             # Bayesian confidence adjustment
│
├── data/                      # Storage + embeddings
│   ├── store.py               # SQLite: StoredObject, StoredMorphism, StoredPath
│   ├── embeddings.py          # sentence-transformers (768d)
│   └── pubchem_loader.py      # PubChem PUG REST loader (fetch by name/CID/SMILES)
│
├── categorical/               # Category theory primitives
│   ├── category.py            # Object, Morphism, Category
│   ├── kan_extensions.py      # Left/Right Kan, Functor, CommaCategory
│   ├── enriched_category.py   # V-enriched categories
│   ├── dempster_shafer.py     # D-S evidence fusion
│   └── streaming_kan.py       # Streaming Kan extensions
│
├── geometry/                  # Ricci curvature, spectral, structure
│   ├── ricci.py               # Ollivier-Ricci curvature
│   ├── flow.py                # Discrete Ricci flow
│   └── spectral.py            # Spectral graph analysis
│
├── topology/                  # Topological data analysis
│   ├── persistence.py         # Persistent homology
│   └── hypergraph.py          # Multi-way interactions
│
├── hott/                      # Homotopy type theory
│   ├── identity.py            # Identity types, paths
│   ├── path_induction.py      # J eliminator
│   └── homotopy.py            # Path homotopy
│
├── cubical/                   # Cubical type theory
│   ├── paths.py               # Interval, PathType, Square, Cube
│   └── kan_ops.py             # hcomp, hfill, comp, inv
│
├── game/                      # Game theory
│   ├── open_games.py          # Categorical open games
│   └── nash.py                # Nash equilibrium
│
├── battery_bridge/            # Battery domain (22 materials)
├── polymer_bridge/            # Polymer domain (33 materials)
├── metal_bridge/              # Metal domain (36 materials)
├── ceramic_bridge/            # Ceramic domain (28 materials)
├── semiconductor_bridge/      # Semiconductor domain (27 materials)
├── glass_bridge/              # Glass domain (23 materials)
│
├── mof_bridge/                # MOF domain (30 MOFs) + linker designer — Phase 11
│   ├── material_properties.py # 30 MOFs with DOIs, CSD codes, topologies, applications
│   ├── interaction_scoring.py # 5 scorers (pore, chem, thermal, mech, app)
│   ├── interface_validator.py # MOFInterfaceValidator (MOF-vs-conditions, not pair compat)
│   ├── analyzer.py            # MOF screening, application matching
│   ├── mp_mof_loader.py       # Materials Project MOF download + linker extraction
│   ├── linker_generator.py    # Novel 22-atom linker generation (3 strategies)
│   ├── atomic_descriptors.py  # Per-atom properties (hybridization, electronegativity, etc.)
│   ├── komposos_verdicts.py   # 5 verdicts (synthesizability, toxicity, stability, activity, conductivity)
│   ├── linker_screening.py    # Full screening pipeline with ZFC+CAT dual-engine
│   └── integration.py         # Categorical store integration
│
├── molecular_bridge/          # Molecular domain (37 molecules)
│   ├── molecule_properties.py # PubChem CIDs, CAS, SMILES
│   ├── interaction_scoring.py # 5 molecular scorers
│   ├── interface_validator.py # MolecularInterfaceValidator
│   ├── constraint_search.py   # Ligand constraint search — Phase 11 (heavy atom counting, element parsing)
│   └── integration.py         # Categorical store integration
│
├── cross_bridge/              # Cross-domain functors
│   ├── battery_polymer.py     # Battery <-> Polymer compatibility
│   ├── battery_metal.py       # Battery <-> Metal compatibility (coating-aware)
│   ├── ceramic_metal.py       # Ceramic <-> Metal compatibility (deposition-aware)
│   ├── molecular_material.py  # Molecular <-> Material cross-scale functor
│   └── multi_domain.py        # Multi-domain analyzer (3-4 bridges, weighted/bottleneck)
│
├── synthesis_planner/         # Synthesis route planning
│   ├── route_graph.py         # 24 curated routes
│   ├── precursor_db.py        # 53 precursors
│   ├── route_planner.py       # SynthesisPlanner
│   └── integration.py         # Categorical hooks
│
├── composition_engine/        # Forward + inverse composition prediction
│   ├── parser.py              # Formula parser, 41 elements
│   ├── properties.py          # Rule-based estimates
│   ├── known_compositions.py  # KnownCompositionDB (103K+ materials with MP)
│   ├── mp_loader.py           # MPEntry/MPCache (gzipped JSON, download-time mp-api)
│   ├── spatial_index.py       # KD-tree O(log N) nearest-neighbor queries
│   ├── structure_deriver.py   # Lattice params via Kan extension over MP structures
│   ├── predictor.py           # Kan extension + D-S fusion + derived structure
│   ├── formation_energy.py    # DFT surrogate (154K+ Ef from MP + Kapustinskii/Miedema)
│   ├── structure_predictor.py # Crystal structure (4 sources, 21 types)
│   └── designer.py            # Inverse design (Crystal Dreamer, O(N log N) dedup)
│
├── pfas_bridge/               # PFAS compliance (35 substances)
│   ├── pfas_registry.py       # CAS numbers, 7 categories, 11 brand names, resolve_base_pfas()
│   ├── replacement_scorer.py  # Use-case-specific replacements
│   └── compliance_checker.py  # Single/batch checks, urgency levels, detection tiers (exact/heuristic/unknown)
│
├── reports/                   # Report generators — Phase 11 + 11.6
│   ├── pfas_report.py         # 7-section auditable compliance reports (provenance, verdict logic, timeline, action plans)
│   └── pfas_pdf.py            # Branded PDF generation (cover page, domain scores, narrative, provenance, action plan, audit cert)
│
├── api/                       # FastAPI web API (v1.2.0)
│   ├── main.py                # App, auth, rate limiting, middleware
│   ├── auth.py                # API key authentication
│   ├── rate_limit.py          # Token bucket rate limiter
│   └── routes/                # 17 authenticated + 2 public endpoints
│       ├── mof_designer.py    # POST /design-mof-linker (MOF linker inverse design)
│
├── streamlit_app/             # Web UI (8 pages)
│   ├── app.py                 # Main entry point
│   └── pages/                 # Compat (+ Molecule Search), PFAS (+ Compliance Report), Predictor, Cell Designer, Crystal Dreamer, MP Explorer, MOF Explorer, MOF Designer
│
├── zfc/                       # ZFC set-theoretic dual engine
├── temporal/                  # Temporal dynamics
└── docs/                      # Documentation
```

---

## Integration Architecture

Every bridge's `integration.py` follows the same pattern:

```python
# Try imports with graceful fallback
try:
    from data.store import StoredObject, StoredMorphism
    STORE_AVAILABLE = True
except ImportError:
    STORE_AVAILABLE = False

# Material -> StoredObject
def material_to_stored_object(material) -> StoredObject:
    return StoredObject(
        name=material.name,
        type_name=material.material_class.value,
        metadata={...properties...},
        provenance='<bridge>.material_properties',
    )

# Interface -> StoredMorphism
def interface_to_stored_morphism(mat_a, mat_b, score) -> StoredMorphism:
    return StoredMorphism(
        name='<domain>_interface',
        source_name=mat_a.name,
        target_name=mat_b.name,
        confidence=score.total,
        provenance='<bridge>.interface_validator',
    )

# Build domain Category
def build_category(materials=None) -> Category:
    # Objects = materials, Morphisms = viable interfaces
```

---

## Confidence Composition (Universal Formula)

Used everywhere: bridges, cross-bridge, synthesis planner:

**Single-bridge / few-interface mode (bottleneck):**
```
composite = 0.75 * bottleneck + 0.25 * average
```

Where:
- `bottleneck` = minimum score across all dimensions
- `average` = mean of all dimension scores

This means one catastrophically bad dimension dominates the result (as it should in materials science — one incompatibility kills the whole system).

**Multi-interface mode (weighted, for >2 interfaces):**
```
weights = [0.5 if score == min else 1.0 for each interface]
composite = weighted_average(scores, weights)
```

This prevents a single mediocre interface from killing an otherwise viable multi-component design. The bottleneck still counts (0.5x weight), but doesn't completely dominate. Auto-selected when a multi-domain query has >2 cross-domain interfaces.

**Coating & deposition awareness (Phase 8):**
- Battery-metal functor: `metal_coating` param boosts anodic voltage limit before veto evaluation
- Ceramic-metal functor: `DepositionMethod` enum applies CTE compliance factor (thin films deform elastically with substrate, reducing effective CTE mismatch)
