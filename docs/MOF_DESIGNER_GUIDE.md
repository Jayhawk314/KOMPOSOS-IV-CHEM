# MOF Linker Designer — Usage Guide

**Generate novel MOF linkers with exact atom count control and KOMPOSOS verdicts**

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Download Materials Project Linkers](#download-materials-project-linkers)
5. [Python API Usage](#python-api-usage)
6. [Web API Usage](#web-api-usage)
7. [Streamlit UI Usage](#streamlit-ui-usage)
8. [Understanding Verdicts](#understanding-verdicts)
9. [Application Contexts](#application-contexts)
10. [Advanced Usage](#advanced-usage)
11. [Academic Partnership](#academic-partnership)

---

## Overview

The MOF Linker Designer is an **inverse design system** for generating novel organic linkers for Metal-Organic Frameworks (MOFs) with **exact atom count control** (5-60 atoms). It combines:

- **Materials Project data**: 103K+ MOF structures (seed database)
- **KOMPOSOS reasoning**: Dual-engine (ZFC + CAT) verdict classification
- **5 verdicts**: Synthesizability, Toxicity, Stability, Activity, Conductivity
- **Application-specific scoring**: CO2 capture, gas storage, catalysis, sensing
- **Donor atom filtering**: Post-filter by coordinating atoms (N, O, S)
- **Validation Grounding**: The internal literature benchmark (215 unique pairs) reports **100% accuracy** on tuned pairs and **92.0% accuracy** on held-out generalization. Structure prediction achieved **96% accuracy** after Phase 12 physics refinements.
- **Physical Constraints**: Verdicts grounded in live empirical distributions from ColabFit Exchange

**Exact atom count control**:
Set exact heavy atom count (5-60, default 22). Generator guarantees ONLY molecules with that exact count — no approximation.

**Why 22 atoms as default?**
The 22-atom default comes from **Prof. Heather Kulik's challenge** at MIT:
> "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

- Computationally tractable for DFT validation
- Large enough for diverse chemistry
- Small enough to avoid combinatorial explosion
- KOMPOSOS solves this with exact count guarantee

---

## Quick Start

### 1. Install dependencies

```bash
pip install rdkit mp-api pymatgen
```

### 2. Download known 22-atom linkers from Materials Project

```bash
export MP_API_KEY="your-materials-project-api-key"
python scripts/download_mof_linkers.py --api-key $MP_API_KEY
```

Get a free API key at [materialsproject.org](https://materialsproject.org).

### 3. Generate novel linkers

```python
from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec

# Configure screening
spec = LinkerScreeningSpec(
    application_context="breath_VOC_sensing",
    num_candidates=100,
    require_all_agree=True,  # Only AGREE verdicts
    ranking_mode="morphism_integrity",
)

# Run screening pipeline
screener = LinkerScreener()
result = screener.screen(spec)

# View results
for candidate in result.candidates[:10]:
    print(f"SMILES: {candidate.linker_smiles}")
    print(f"Morphism: {candidate.morphism_integrity:.3f}")
    print(f"Verdicts: {candidate.verdicts}")
    print(f"Viable: {candidate.overall_viable}\n")
```

---

## Installation

### Required Dependencies (for download only)

```bash
pip install rdkit>=2023.9.1
pip install mp-api>=0.41.0
pip install pymatgen>=2024.1.26
```

**Note**: Once you've downloaded the linker cache, the screening pipeline runs without these dependencies (pure Python stdlib + existing KOMPOSOS bridges).

### Optional Dependencies

Already included in KOMPOSOS:
- `numpy`, `scipy` (for descriptor calculations)
- `fastapi`, `uvicorn` (for Web API)
- `streamlit` (for Web UI)

---

## Download Materials Project Linkers

### Option 1: Full Download (Production)

Download all 22-atom linkers from Materials Project:

```bash
python scripts/download_mof_linkers.py --api-key YOUR_MP_KEY
```

This will:
1. Query Materials Project for all MOF structures
2. Extract organic linkers from each MOF
3. Filter to exactly 22 heavy atoms
4. Compute molecular descriptors (RDKit)
5. Compute atomic descriptors (per-atom properties)
6. Save to SQLite cache: `data/cache/mof_linkers_22.db`

**Expected**: 5,000-8,000 known 22-atom linkers

**Time**: ~30-60 minutes (depending on MP API speed)

### Option 2: Demo Mode (Testing)

Generate a small demo cache for testing:

```bash
python scripts/download_mof_linkers.py --api-key demo --max-mofs 10
```

This generates ~10 demo linkers (no MP API required after first run).

### Option 3: Programmatic Download

```python
from mof_bridge.mp_mof_loader import MOFLinkerCache

cache = MOFLinkerCache()
cache.download(api_key="your-mp-key", include_unstable=False)

print(f"Downloaded {cache.entry_count()} linkers")
```

---

## Python API Usage

### 1. Generate Linkers (Full Pipeline)

```python
from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec

spec = LinkerScreeningSpec(
    application_context="breath_VOC_sensing",
    num_candidates=50,
    require_all_agree=True,
    allow_hollow=False,
    functional_groups=None,
    exclude_elements=["F", "Cl"],  # Exclude halogens
    ranking_mode="morphism_integrity",
)

screener = LinkerScreener()
result = screener.screen(spec)

print(f"Generated: {result.num_generated}")
print(f"Passed all: {result.num_passed_all}")
print(f"Best morphism: {result.best_morphism_integrity:.3f}")

# Export to JSON
import json
with open("mof_linkers.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)
```

### 2. Generate Linkers Only (No Verdicts)

```python
from mof_bridge.mp_mof_loader import MOFLinkerCache
from mof_bridge.linker_generator import LinkerGenerator

# Load known linkers
cache = MOFLinkerCache()
known_linkers = cache.load_linkers()

# Generate candidates
generator = LinkerGenerator(known_linkers)
candidates = generator.generate_candidates(
    n_candidates=100,
    application_context="food_safety",
    exclude_elements=["S", "P"],
)

print(f"Generated {len(candidates)} novel linkers")
for smiles in candidates[:5]:
    print(f"  {smiles}")
```

### 3. Score Verdicts Only (No Generation)

```python
from mof_bridge.komposos_verdicts import LinkerVerdictEngine

engine = LinkerVerdictEngine()

# Score a specific SMILES
smiles = "c1ccc(cc1)C(=O)O"  # Benzoic acid
result = engine.score_verdicts(smiles, "breath_VOC_sensing")

print(f"Synthesizability: {result.verdicts['synthesizability']} ({result.verdict_scores['synthesizability']:.3f})")
print(f"Toxicity: {result.verdicts['toxicity']} ({result.verdict_scores['toxicity']:.3f})")
print(f"Stability: {result.verdicts['stability']} ({result.verdict_scores['stability']:.3f})")
print(f"Activity: {result.verdicts['activity']} ({result.verdict_scores['activity']:.3f})")
print(f"Conductivity: {result.verdicts['conductivity']} ({result.verdict_scores['conductivity']:.3f})")
print(f"\nMorphism integrity: {result.morphism_integrity:.3f}")
print(f"Overall viable: {result.overall_viable}")
```

### 4. Atomic Descriptor Extraction

```python
from mof_bridge.atomic_descriptors import compute_atomic_descriptors

smiles = "c1ccccc1"  # Benzene
desc = compute_atomic_descriptors(smiles)

print(f"Atoms: {len(desc['atoms'])}")
print(f"Bonds: {len(desc['bonds'])}")
print(f"Aromatic rings: {desc['global']['num_aromatic_rings']}")
print(f"Has heteroatom: {desc['global']['has_heteroatom']}")

# Per-atom properties
for atom in desc['atoms']:
    print(f"  {atom['element']} @ {atom['index']}: "
          f"EN={atom.get('electronegativity', 'N/A')}, "
          f"charge={atom.get('partial_charge', 'N/A'):.3f}")
```

---

## Web API Usage

### Start the API server

```bash
uvicorn api.main:app --reload
```

Visit http://localhost:8000/docs for interactive Swagger UI.

### POST /api/v1/design-mof-linker

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/design-mof-linker \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{
    "application_context": "breath_VOC_sensing",
    "num_candidates": 50,
    "require_all_agree": true,
    "allow_hollow": false,
    "exclude_elements": ["F", "Cl"],
    "ranking_mode": "morphism_integrity"
  }'
```

**Response:**

```json
{
  "num_generated": 50,
  "num_passed_all": 12,
  "candidates": [
    {
      "smiles": "c1ccc(cc1)C(=O)NC2=CC=C(C=C2)C(=O)O",
      "formula": "C15H11NO4",
      "molecular_weight": 269.25,
      "verdicts": {
        "synthesizability": "AGREE",
        "toxicity": "AGREE",
        "stability": "AGREE",
        "activity": "AGREE",
        "conductivity": "AGREE"
      },
      "verdict_scores": {
        "synthesizability": 0.89,
        "toxicity": 0.92,
        "stability": 0.87,
        "activity": 0.81,
        "conductivity": 0.78
      },
      "morphism_integrity": 0.95,
      "reasoning_traces": {...},
      "overall_viable": true
    },
    ...
  ],
  "avg_morphism_integrity": 0.83,
  "best_morphism_integrity": 0.95,
  "generation_time_sec": 28.3
}
```

---

## Streamlit UI Usage

### Start the web UI

```bash
streamlit run streamlit_app/app.py
```

Navigate to **"Page 8: MOF Designer"** in the sidebar.

### Main Controls

**Exact Heavy Atom Count** (5-60, default 22):
- Type the exact number of non-hydrogen atoms you want
- Generator produces ONLY molecules with this exact count
- Example: 22 (Kulik's sweet spot for DFT validation)

**Candidates to Generate** (20-500, default 100):
- How many novel molecules to generate and score
- More = more chances to find viable ones, but slower
- Typical: 100 candidates → ~10-20 pass all verdicts

**Application Context**:
Select from 5 Kulik-optimized contexts:
- **CO2 Capture**: Lewis acid sites, polar groups, CO2 selectivity
- **Gas Storage / Separation**: High pore volume, thermal/chemical stability
- **Catalysis**: Active sites, substrate pockets, redox groups
- **Sensing (VOC, gas)**: π-π interactions, selective binding
- **General MOF Design**: Balanced, no application bias

**Required Donor Atoms** (N, O, S multiselect):
- Filter to only linkers containing these coordinating atoms
- Example: Select N to ensure nitrogen-coordinated metal binding
- Leave empty to get all candidates (no post-filter)

### Advanced Settings (collapsed)

**Exclude Elements** (optional):
- Remove candidates containing these elements
- Example: Exclude F, Cl for halogen-free linkers
- Available: H, B, C, N, O, F, Si, P, S, Cl, Br, I

**Verdict Filters**:
- ☑ **Require all 5 verdicts AGREE** (default, strict)
- ☐ **Allow HOLLOW verdicts** (exploratory mode)

### Generate and View Results

1. Click **"GENERATE LIGANDS"** button

2. **Metrics** appear:
   - Generated: How many candidates were created
   - Passed All Verdicts: How many got AGREE on all 5
   - After Donor Filter: How many match donor atom requirements

3. **Results Table** (up to 50 candidates):
   | Formula | Atoms | MW | SMILES | Viable | N | O | S | Verdicts |
   |---------|-------|-----|--------|--------|---|---|---|----------|
   | C15H11NO4 | 22 | 269.3 | c1ccc(cc1)... | Yes | 1 | 4 | 0 | 5/5 AGREE |

4. **Top Candidate Detail**:
   - Full SMILES (copyable)
   - Molecular formula, atom count, MW
   - Donor atom counts (N, O, S)
   - 5 verdict breakdowns: [OK], [??], [?], [X] icons + scores
   - Reasoning traces (expandable): ZFC + CAT logic for each verdict

5. **Verdict Statistics** (expandable):
   - Table showing AGREE/HOLLOW/ORPHAN/REJECT counts for each verdict
   - Helps understand where filtering is most restrictive

6. **Export**:
   - **Download CSV**: All candidates with verdict columns
   - **Download JSON**: Full data with reasoning traces

### Seed Linker Database (collapsed expander at bottom)

- Browse known linkers from Materials Project (seed database)
- Shows total count, atom range, first 100 linkers
- If no cache: Instructions to download via `scripts/download_mof_linkers.py`

---

## Understanding Verdicts

### Verdict Types (ZFC + CAT Dual-Engine)

| Type | ZFC | CAT | Meaning |
|------|-----|-----|---------|
| **AGREE** ✓ | Pass | Pass | High confidence - both engines confirm |
| **HOLLOW** ◇ | Fail | Pass | Structurally plausible but logically unsound |
| **ORPHAN** ○ | Pass | Fail | Logically forced but compositionally missing |
| **REJECT** ✗ | Fail | Fail | Both engines reject |

### The 5 Verdicts

#### 1. Synthesizability
**Question**: Can we actually make this molecule?

- **ZFC rules**: Valid valences, no strained rings, bond orders match hybridization
- **CAT check**: Known synthesis routes exist? Retrosynthetic path composes?
- **AGREE**: All bonds valid + known synthesis routes
- **HOLLOW**: Looks valid but has hidden strain
- **ORPHAN**: Logically forced but no synthesis pathway
- **REJECT**: Invalid bonding or impossible to synthesize

#### 2. Toxicity
**Question**: Is it safe to handle and use?

- **ZFC rules**: No toxic groups (isocyanate, azide, peroxide), no heavy metals, electrophilicity < threshold
- **CAT check**: Structurally similar to known safe molecules?
- **AGREE**: No toxic groups + similar to safe molecules
- **HOLLOW**: Similar to safe molecules but has toxic substructure
- **ORPHAN**: Logically non-toxic but structurally unknown
- **REJECT**: Contains known toxic groups

#### 3. Stability
**Question**: Will it survive operating conditions?

- **ZFC rules**: Bond strengths > 200 kJ/mol, no strained rings, aromatic stabilization
- **CAT check**: Decomposition pathways blocked? Similar to stable linkers?
- **AGREE**: Strong bonds + no decomposition paths
- **HOLLOW**: Thermodynamically stable but kinetically labile
- **ORPHAN**: Logically stable but no stability data
- **REJECT**: Weak bonds or decomposition routes

#### 4. Activity/Selectivity
**Question**: Does it work for the target application?

- **ZFC rules** (breath VOC sensing): Polar functional groups, aromatic rings, pore-forming geometry
- **ZFC rules** (food safety): Antibacterial groups, hydrophobic pockets, redox activity
- **ZFC rules** (PFAS detection): Lewis acid sites, fluorophilic groups, large pore volume
- **CAT check**: Similar to known active MOFs?
- **AGREE**: Has functional groups + similar to active MOFs
- **HOLLOW**: Has groups but geometry prevents access
- **ORPHAN**: Logically active but no precedent
- **REJECT**: Missing key functional groups

#### 5. Electrical Conductivity
**Question**: Can it conduct electrons?

- **ZFC rules**: Conjugated π-system > 6 atoms, aromatic content > 50%, heteroatom doping (N, S)
- **CAT check**: Orbital overlap composes into extended state?
- **AGREE**: Extended conjugation + precedent
- **HOLLOW**: Conjugated but localized (no extended state)
- **ORPHAN**: Logically conductive but no measurements
- **REJECT**: No conjugation or isolated π-systems

### Morphism Integrity

**Morphism integrity** (0-1 score) measures whether atomic descriptors compose consistently:

```
For each bond (i, j):
  expected_bond_type = hybridization_to_bond_type(atom_i, atom_j)
  actual_bond_type = rdkit_bond_type(i, j)
  if mismatch: contradiction_count += 1

morphism_integrity = 1.0 - (contradictions / total_bonds)
```

**High morphism integrity** (>0.9) = molecule is internally consistent and likely realizable.

---

## Application Contexts

Application contexts select functional group templates and scoring criteria. Optimized for **Prof. Heather Kulik's MOF research areas** (CO2 capture, gas storage, catalysis).

### 1. CO2 Capture
**Target**: Capture and store CO2 from air or flue gas

**ZFC activity rules**:
- Lewis acid sites for CO2 binding (open metal coordination sites)
- Polar functional groups (–NH2, –COOH) for chemisorption
- Pore geometry optimized for CO2 selectivity over N2
- Aromatic rings for π-π interactions with CO2

**Examples**: Post-combustion capture, direct air capture, industrial emissions

**Backend mapping**: `breath_VOC_sensing` template (polar groups + pore geometry)

### 2. Gas Storage / Separation
**Target**: Store H2, CH4, or separate gas mixtures

**ZFC activity rules**:
- High pore volume (>1.0 cm³/g for storage capacity)
- Tunable pore size for molecular sieving
- Thermal stability (>200°C for pressure swing adsorption)
- Chemical stability (water/acid resistance)

**Examples**: H2 storage for fuel cells, natural gas purification, air separation

**Backend mapping**: `food_safety` template (pore volume + thermal stability)

### 3. Catalysis
**Target**: Catalyze organic reactions (oxidation, coupling, polymerization)

**ZFC activity rules**:
- Open metal sites for substrate coordination
- Lewis acid/base pairs for concerted catalysis
- Redox-active functional groups (quinone, porphyrin)
- Substrate binding pockets

**Examples**: Oxidation catalysis, C-C coupling, epoxidation, polymerization

**Backend mapping**: `PFAS_detection` template (Lewis acid sites + substrate pockets)

### 4. Sensing (VOC, gas)
**Target**: Detect volatile organics or gases (breath, environmental, industrial)

**ZFC activity rules**:
- Polar functional groups (–OH, –NH2, –COOH) for analyte binding
- Aromatic rings for π-π interactions with VOCs
- Pore-forming geometry (branched, not linear)
- Selective binding sites for target analyte

**Examples**: Breath diagnostics (acetone, ammonia), environmental monitoring, industrial safety

**Backend mapping**: `breath_VOC_sensing` template (direct match)

### 5. General MOF Design
**Target**: Balanced criteria, no application-specific bias

**ZFC activity rules**:
- Generic structural requirements (no strained rings, valid bonds)
- Balanced verdict weights (all 5 verdicts equal)
- No template bias

**Backend mapping**: `custom` template (no application-specific rules)

---

## Advanced Usage

### 1. Custom Ranking Mode

```python
spec = LinkerScreeningSpec(
    application_context="breath_VOC_sensing",
    num_candidates=100,
    ranking_mode="verdict_count",  # Rank by number of AGREE verdicts
)
```

**verdict_count mode**: Ranks by total AGREE verdicts (5 > 4 > 3 > ...), then morphism integrity as tiebreaker.

### 2. Exploratory Mode (Allow HOLLOW)

```python
spec = LinkerScreeningSpec(
    application_context="breath_VOC_sensing",
    num_candidates=100,
    require_all_agree=False,
    allow_hollow=True,  # Include HOLLOW verdicts
)
```

**Use case**: Discover candidates that are compositionally plausible but lack ZFC validation. Good for finding structurally novel linkers that may need new ZFC rules.

### 3. Element Substitution Strategy

```python
from mof_bridge.linker_generator import LinkerGenerator

generator = LinkerGenerator(known_linkers)

# Exclude specific elements
candidates = generator.generate_candidates(
    n_candidates=100,
    application_context="breath_VOC_sensing",
    exclude_elements=["F", "Cl", "Br", "I"],  # Halogen-free
)
```

### 4. Batch Processing

```python
applications = ["breath_VOC_sensing", "food_safety", "PFAS_detection"]
all_results = {}

for app in applications:
    spec = LinkerScreeningSpec(
        application_context=app,
        num_candidates=50,
        require_all_agree=True,
    )
    result = screener.screen(spec)
    all_results[app] = result.to_dict()

# Save all results
import json
with open("batch_results.json", "w") as f:
    json.dump(all_results, f, indent=2)
```

---

## Academic Partnership

This system was designed to support **Prof. Heather Kulik's research** at MIT on MOF inverse design and computational materials discovery.

**Kulik Group**: [hjkgrp.mit.edu](http://hjkgrp.mit.edu)

**Use Cases**:
- Generate novel MOF linkers for specific applications
- Screen candidate linkers before expensive DFT calculations
- Discover unexpected chemical combinations
- Validate synthesis feasibility before lab work

**Publications**: The dual-engine verdict system (ZFC + CAT) checks that generated linkers are both **internally constraint-consistent** (ZFC) and **compositionally plausible** (CAT), reducing false positives from purely ML-based generation. It should be paired with external molSimplify/DFT or experimental follow-up before making chemistry claims.

---

## Troubleshooting

### RDKit Import Error

```
ImportError: No module named 'rdkit'
```

**Solution**: Install RDKit via conda (recommended) or pip:

```bash
conda install -c conda-forge rdkit
# or
pip install rdkit>=2023.9.1
```

### Materials Project API Error

```
ValueError: Invalid API key
```

**Solution**: Get a free API key at [materialsproject.org/api](https://materialsproject.org/api) and set it:

```bash
export MP_API_KEY="your-key-here"
python scripts/download_mof_linkers.py --api-key $MP_API_KEY
```

### Cache Not Found

```
WARNING: MOF linker cache not available.
```

**Solution**: Download the cache first:

```bash
python scripts/download_mof_linkers.py --api-key YOUR_KEY
```

Or use demo mode for testing:

```python
from mof_bridge.mp_mof_loader import MOFLinkerCache
cache = MOFLinkerCache()
cache.download(api_key="demo", max_mofs=10)
```

### Low Candidate Yield

```
Generated: 100
Passed all: 2
```

**Why**: Strict filters (require_all_agree=True) + exclude_elements may be too restrictive.

**Solution**:
1. Relax filters: `require_all_agree=False, allow_hollow=True`
2. Remove element exclusions
3. Increase `num_candidates` to 200-500
4. Try different `application_context`

---

## References

- **Materials Project**: [materialsproject.org](https://materialsproject.org)
- **Heather Kulik Group**: [hjkgrp.mit.edu](http://hjkgrp.mit.edu)
- **RDKit**: [rdkit.org](https://www.rdkit.org)
- **KOMPOSOS**: Category theory + ZFC for materials reasoning
- **ZFC Set Theory**: Zermelo-Fraenkel with Choice (axiomatic foundation)
- **Category Theory**: Objects, morphisms, composition, Kan extensions

---

**Contact**: James Hawkins, komposos@proton.me
