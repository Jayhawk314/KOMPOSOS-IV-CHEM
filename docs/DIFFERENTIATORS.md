# KOMPOSOS-III: What Makes It Different

## The One-Sentence Pitch

KOMPOSOS is the only tool that predicts new material compositions, checks if they work together in a complete device, explains why, and tells you how to make them — without a GPU, training data, or black-box AI.

---

## The Problem

Materials engineers designing a solid-state battery need to answer:

1. What cathode material should I use?
2. What electrolyte is compatible with it?
3. What binder won't degrade at operating voltage?
4. What current collector won't corrode?
5. Do all four work together as a system?
6. Is any component a PFAS substance I'll need to replace by August 2026?
7. Can I actually synthesize the target material?

Today, each of these questions is answered by a different tool, a different spreadsheet, or a different expert. No existing product answers all seven. KOMPOSOS does.

---

## Six Capabilities No Competitor Combines

### 1. Novel Composition Prediction

Enter any chemical formula — even one that doesn't exist yet — and get predicted voltage, capacity, thermal stability, ionic conductivity, crystal structure type, formation energy, and a synthesizability score.

The system uses Kan extension (a category theory construction) over a knowledge graph of 103K+ known materials (205 curated bridge materials + 103,644 from Materials Project), fused with Dempster-Shafer evidence theory. It interpolates between compositions, screens bulk candidate lists, and rediscovers known materials in leave-one-out validation (voltage errors 1.6-7.2%). Composition vectors are **physics-embedded** (120 dimensions including stoichiometry, group, and period), ensuring that searches are chemically aware (e.g. Ba similarity to Sr is prioritized over Pb). Crystal structures are derived with full provenance — lattice parameters, space groups, and volume per atom all trace back to specific Materials Project entries.

This is not curve fitting. It is compositional reasoning: the same mathematical framework used in algebraic topology and theoretical computer science, applied to chemistry. The stricter 2026-05-19 audit reports a **215-evaluated-record internal benchmark (100% accuracy, 92% held-out generalization)** with tuned galvanic, Hansen chi parameter enhancement, CTE, and lattice scoring.

### 2. Multi-Domain Device Screening with Active Verification

No other tool evaluates a complete multi-material device in one query. KOMPOSOS spans 8 material domains (batteries, polymers, metals, ceramics, semiconductors, glass, MOFs, molecules) through cross-bridge functors.

KOMPOSOS includes **Active Verification**: high-stakes or low-confidence queries can trigger a production-ready **GROMACS MD runner** when a prepared `.gro`/`.top` input bundle is available. If the bundle or analyzable trajectory signals are missing, KOMPOSOS returns an explicit no-verdict readiness report instead of claiming simulated stability.

Competitors evaluate one material at a time or use static ML models. KOMPOSOS evaluates the system and verifies it with simulation.

### 3. Interpretable Reasoning

Every score traces through named mathematical operations. When a Cu collector scores 0.25 against NMC811, you see: "electrochemical stability = 0.15 because Cu anodic limit (3.0V) is below NMC811 operating voltage (4.2V), triggering the voltage veto."

This is not a feature — it is the architecture. KOMPOSOS is built on category theory (objects, morphisms, composition) and ZFC set theory (axioms, proofs, logical verification). The math provides the explanation automatically.

Why this matters:
- The EU AI Act (2026) requires explainability for high-risk AI systems
- Aerospace, medical device, and nuclear materials decisions require audit trails
- Engineers need to know WHY a combination fails, not just that it fails
- The $21B explainable AI market is a tailwind only KOMPOSOS can access

### 4. PFAS Compliance with Application-Specific Replacement Scoring

35 PFAS substances mapped against EU REACH, US EPA, and Stockholm Convention regulations. But the real value is replacement scoring: KOMPOSOS doesn't just flag "PVDF is PFAS." It scores alternatives for your specific application.

PVDF as a battery binder: CMC+SBR scores 0.83, PAA scores 0.76, PAN scores 0.62.
PVDF as a membrane: SPEEK scores 0.63, PBI scores 0.55.

Different applications need different replacements. No competitor does application-specific scoring.

**PFAS Compliance Reports (Phase 11):** Generate auditable 7-section reports for bill-of-materials screening with full provenance. Every verdict traces from material → detection → regulation → alternative → action plan. Enables regulatory filing preparation and supplier audits.

**Brand name detection (Phase 11.6):** 11 brand names (Teflon, Kynar, Viton, Scotchgard, Gore-Tex, etc.) auto-resolve to base PFAS substances. Detection tiers (exact/heuristic/unknown) provide audit transparency.

**Branded PDF reports (Phase 11.6):** Download professional compliance PDFs with client name on cover page, domain-specific scores (Adhesion, Electrolyte, Thermal, Cathode from cross-bridge analysis), narrative recommendations, provenance tables, P0/P1/P2 action plans, and audit certificates. The PDF IS the deliverable for paid compliance engagements.

Deadlines are real: EU food-contact PFAS ban hits August 12, 2026 with no grandfathering. The battery industry's PVDF, LiTFSI, and fluorinated separators are all PFAS. Every battery manufacturer needs screening now.

### 5. Synthesis Route Planning

24 synthesis routes for target materials, ranked by feasibility, cost, time, and safety. 53 precursors with real pricing and hazard data. Equipment requirements mapped per route.

This connects material selection to manufacturability. "LFP via solid-state synthesis: Li2CO3 + Fe2O3 + NH4H2PO4, 700C for 12 hours in argon, $47/batch."

No materials screening tool includes synthesis planning. No synthesis tool includes compatibility screening. KOMPOSOS does both.

### 6. MOF Linker Inverse Design with Dual-Engine Verdicts

Generate novel 22-atom organic linkers for Metal-Organic Frameworks with 5 KOMPOSOS verdicts: synthesizability, toxicity, stability, activity, conductivity. Each verdict uses ZFC (logical constraints) + CAT (compositional reasoning) dual-engine verification.

**The Kulik Challenge**: Prof. Heather Kulik (MIT) asked LLMs for ligands with exactly 22 heavy atoms. LLMs hallucinate — they can't count. KOMPOSOS uses exact constraint search with element parsing, returning real candidates or honest "not found."

**Verdict classifications**:
- **AGREE**: CAT score passes and ZFC constraint checks find no veto
- **HOLLOW**: CAT yes, ZFC veto -- structurally plausible but violates current constraints
- **ORPHAN**: ZFC no veto, CAT no -- not ruled out by constraints but compositionally weak
- **REJECT**: Both engines reject

**Morphism integrity**: 0-1 score measuring internal consistency of atomic descriptors (hybridization → bond type matching). High (>0.9) = likely realizable.

No competitor offers application-specific linker generation with dual-engine verification and full reasoning traces. Built for academic partnership with MIT Kulik group.

### 7. Zero Infrastructure Cost

KOMPOSOS runs on a laptop. No GPU. No training data. No cloud compute. No vendor lock-in.

This is possible because the engine reasons from published material properties (199 curated materials with DOI citations + 103,644 from Materials Project), not from learned weights. The bridges and ZFC engine are pure Python — no PyTorch, no TensorFlow.

Competitors require GPU clusters (CuspAI, Orbital), proprietary training data (Citrine), or expensive simulation licenses (Schrodinger). KOMPOSOS costs nothing to run.

---

## Competitive Landscape

$2.1 billion has been invested in materials AI. Every dollar went to black-box machine learning.

| Company | Raised | What They Do | What They Don't Do |
|---------|--------|-------------|-------------------|
| Orbital Materials ($1.2B) | $221M | ML potentials for climate materials | Multi-domain device design, PFAS, synthesis |
| CuspAI ($520M val) | $154M | Generative AI for crystal structures | Compatibility screening, explainability, synthesis |
| Citrine ($140M val) | $81M | ML on customer-uploaded data | Works without your data, multi-domain, PFAS |
| Mitra Chem | $196M | Battery materials manufacturing | Software product, multi-domain reasoning |
| Schrodinger | $256M rev | Molecular simulation | Only $17M from materials, no multi-domain |
| GNoME (Google) | Internal | 2.2M predicted crystals | Which ones work together in a device? |

KOMPOSOS occupies a gap none of them fill: interpretable, multi-domain, composition-to-device reasoning.

The real competition is not these companies. It is the spreadsheet on a battery engineer's desktop and the retiring expert whose knowledge walks out the door.

---

## The Investment Case

**Immediate revenue**: PFAS compliance consulting. EU deadline August 2026. Target: $125K-1M in first year from 5-10 manufacturer engagements.

**Growth revenue**: Battery cell design SaaS. $500/month pro tier, $5K-20K/month enterprise. Solid-state battery market growing 32-40% CAGR to $15-48B by 2033.

**Strategic value**: Pre-simulation screening layer. Sits between AI generators (GNoME, MatterGen) and expensive compute (DFT, molecular dynamics). Potential OEM/partnership with Google, Microsoft, Materials Project.

**Defensibility**: Category theory is hard to replicate. Five patentable methods. ZFC dual-engine architecture is unique in the field. The test count should be taken from `pytest --collect-only` in the current checkout. Materials Project integration is available through the composition engine cache; public material listing endpoints expose the curated bridge registries. MOF linker designer enables academic partnerships via exact constraint search + dual-engine verdicts. Bridge tuning methodology (galvanic veto, Hansen chi, CTE mismatch, lattice matching) is proprietary.

**What exists today**: Working product with 19 API endpoints, web UI (8 pages including MOF Designer), Docker deployment, Python SDK, CI/CD pipeline, and comprehensive test coverage. 103K+ materials. Not a prototype — a product.

---

## Technical Proof Points

- 103K+ materials: 205 curated bridge materials (175 + 30 MOFs) + 103,644 from Materials Project with DFT formation energies and crystal structures
- 37 molecules with PubChem CIDs, CAS numbers, SMILES + ligand constraint search (heavy atom counting, element parsing)
- 30 MOFs with DOI citations, experimental data, CSD codes spanning 8 topologies
- MOF linker designer: 22-atom constraint, 5 verdicts, ZFC+CAT dual-engine, morphism integrity scoring
- Automated test count changes with the checkout; run `python -m pytest --collect-only -q` for the current count.
- 64 real materials science questions answered correctly (dogfood test, 100% pass, includes Kulik 22-atom challenge with exact heavy atom counting)
- Leave-one-out validation: voltage prediction errors 1.6-7.2%
- Crystal structure prediction: 23/23 known materials correct
- Solid-state battery designs: 3 of 4 configurations viable after Phase 8 fixes
- 158 novel compositions screened in bulk, rediscovering known materials
- PFAS compliance reports: 7-section auditable format with full provenance, branded PDF downloads
- Brand name detection: 11 brands auto-resolve (Teflon→PTFE, Kynar→PVDF, Viton→FKM, etc.)
- Detection tiers: exact/heuristic/unknown with audit trail transparency

---

*KOMPOSOS-III-chem | Built by James Ray Hawkins | 2026*
