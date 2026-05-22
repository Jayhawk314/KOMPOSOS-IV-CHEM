# KOMPOSOS-MOF Inverse Design System: Complete Technical Specification

## 1. Executive Summary

Build an AI system that generates novel 22-atom MOF linkers constrained by KOMPOSOS categorical reasoning verdicts. The system handles bonding variability across material space through compositional morphism reasoning (CAT layer) and logical rule-based inference (ZFC layer).

**Core Innovation:** Categorical reasoning on atomic descriptors overcomes bonding variability by reasoning about *local* chemistry (invariant) rather than *global* bonding assumptions (variant).

---

## 2. System Architecture

```
Materials Project API (103k MOFs)
        ↓
MolSimplifier (standardize structures)
        ↓
MOthSimplifier (extract atom-centered descriptors)
        ↓
Filter: 22-atom linkers
        ↓
SQLite Database (materials_22atom.db)
        ↓
Generative Model (Graph Neural Network)
        ↓
Candidate Generation (N new linkers)
        ↓
KOMPOSOS Dual-Engine Reasoning:
  ├─ ZFC Layer (logic rules on descriptors)
  └─ CAT Layer (morphism integrity on compositions)
        ↓
5 Verdict Modules:
  1. Synthesizability
  2. Toxicity
  3. Stability
  4. Activity/Selectivity
  5. Electrical Conductivity
        ↓
Constraint Filter: Keep only AGREE across all 5
        ↓
Rank by Morphism Integrity Score
        ↓
Streamlit UI + CSV Export
```

---

## 3. Data Layer

### 3.1 Materials Project API Query

**Input:**
- MP API key (user provides)
- Query: All structures with MOF-like features

**Process:**
```python
# Pseudo-code
from mp_api.client import MPRestClient

client = MPRestClient(api_key=YOUR_KEY)

# Get all structures
all_structures = client.materials.search(
    formula="*",
    crystal_system="*",
    theoretical=False  # Experimental only
)

# Extract MOF linkers from coordination polymers
mofs = [s for s in all_structures if is_mof(s)]
# Total: ~103k structures
```

**Output:** List of 103k MOF structures (CIF-equivalent data)

### 3.2 MolSimplifier Processing

**Input:** MOF structure (3D coordinates + connectivity)

**Process:**
- Remove metal centers (or reduce to single atoms)
- Extract organic linker molecule(s)
- Standardize structure (remove duplicates, normalize geometry)
- Convert to SMILES string

**Output:** Standardized linker SMILES for each MOF

**Key Point:** MolSimplifier handles bonding variability by working with *standardized local geometry*, not assuming bonding type.

### 3.3 MOthSimplifier Descriptor Extraction

**Input:** Standardized linker SMILES

**Process:** For each atom in the linker, compute:

```
Atom-Centered Descriptors:
├─ Atomic Properties
│  ├─ Atomic number (Z)
│  ├─ Electronegativity (Pauling scale)
│  ├─ Ionization energy
│  ├─ Electron affinity
│  └─ Atomic radius
├─ Local Geometry
│  ├─ Coordination number (CN)
│  ├─ Bond angles (θ)
│  ├─ Bond distances (r)
│  ├─ Geometry type (tetrahedral, octahedral, planar, etc.)
│  └─ Deviation from ideal geometry
├─ Electronic Properties
│  ├─ Partial charge (DDEC or Bader)
│  ├─ Orbital character (% s, p, d contribution)
│  ├─ Valence electron count
│  ├─ Hybridization state
│  └─ Lone pair count
├─ Bonding Properties
│  ├─ Bond order to each neighbor
│  ├─ Bond type (single, double, triple, aromatic)
│  ├─ Bond strength estimate (BDE or empirical)
│  └─ Orbital overlap (relative)
└─ Conjugation Properties
   ├─ π-system presence (YES/NO)
   ├─ Conjugation length
   ├─ Aromatic vs aliphatic
   └─ Delocalization index
```

**Output:** Descriptor vector for each atom (typically 30-50 dimensions per atom)

**Storage in SQLite:**
```sql
CREATE TABLE linkers (
    linker_id TEXT PRIMARY KEY,
    smiles TEXT,
    atom_count INT,
    mp_source_id TEXT,
    descriptor_json JSON,  -- Full MOthSimplifier descriptors
    formal_charge INT,
    molecular_weight REAL,
    logp REAL,
    hba INT,  -- H-bond acceptors
    hbd INT,  -- H-bond donors
    rotatable_bonds INT,
    aromatic_rings INT
);
```

### 3.4 22-Atom Filter

**Constraint:** `WHERE atom_count = 22`

**Rationale:** Heather Kulik identified 22 atoms as sweet spot for:
- Computational tractability
- Chemical diversity (diverse functional groups possible)
- Synthetic accessibility (not too large, not too small)

**Result:** ~5,000-8,000 linkers with exactly 22 atoms from the 103k pool

---

## 4. Generative Model

### 4.1 Architecture: Graph Neural Network (GNN)

**Type:** Graph Convolutional Network (GCN) with autoregressive decoding

**Input:** 
- Molecular graph (22-atom linkers from training set)
- Node features: Atom type (C, N, O, etc.)
- Edge features: Bond type (single, double, aromatic)

**Model:**
```
1. Encoder: GCN to learn node embeddings
2. Latent space: 128-256 dimensional
3. Decoder: Autoregressive generation of new graphs
   - Predict next atom type
   - Predict bonds to previous atoms
   - Stop at 22 atoms
4. Validity checker: RDKit validity + valence constraints
```

**Training:**
- Dataset: 5,000-8,000 22-atom linkers from SQLite
- Loss: Graph reconstruction + validity penalty
- Epochs: Until convergence (~100-500 epochs)
- Optimizer: Adam, LR=1e-3
- GPU: Recommended (12+ GB VRAM)
- Time: 2-4 hours

**Output:** Trained checkpoint (`linker_generator_checkpoint.pt`)

**Validity Constraints (built into decoder):**
- Each atom respects valence (C=4, N=3/5, O=2, etc.)
- No disconnected fragments
- Chemically valid bond types
- RDKit sanity check on each generated SMILES

### 4.2 Generation on Demand

**Process:**
```python
# Load model
model = load_checkpoint("linker_generator_checkpoint.pt")

# Generate N candidates
for i in range(N):
    candidate_graph = model.generate()  # Returns molecular graph
    smiles = graph_to_smiles(candidate_graph)
    
    # Validity check
    mol = RDKit.MolFromSmiles(smiles)
    if mol is not None and is_valid(mol):
        candidates.append(smiles)
```

**Output:** List of valid 22-atom linker SMILES strings

---

## 5. KOMPOSOS Constraint Layer

### 5.1 Overview

**Goal:** Filter generated candidates through KOMPOSOS dual-engine reasoning.

**For each candidate linker:**
1. Standardize via MolSimplifier
2. Extract descriptors via MOthSimplifier
3. Pass through ZFC layer (logic rules)
4. Pass through CAT layer (morphism reasoning)
5. Generate 5 verdicts (AGREE/HOLLOW/ORPHAN/REJECT)

### 5.2 ZFC Layer: Logic Rules on Descriptors

**Purpose:** Rule-based inference on atomic descriptors

**Example Rule Set:**

```
Rule 1: SYNTHESIZABILITY
├─ IF: All bonds have bond_order ∈ {1, 2, 3, aromatic}
├─ AND: No unusual valence states
├─ AND: Connectivity matches known synthesis routes
└─ THEN: AGREE (likely synthetically accessible)

Rule 2: TOXICITY
├─ IF: Contains known toxic functional groups (e.g., isocyanate, diazo)
├─ THEN: REJECT (toxic)
├─ ELSE IF: Partial charges suggest electrophilicity > threshold
├─ THEN: HOLLOW (ambiguous toxicity)
└─ ELSE: AGREE (likely non-toxic)

Rule 3: STABILITY
├─ IF: All bonds have bond_strength_estimate > 2 kcal/mol
├─ AND: No strained ring systems (ring_strain > threshold)
├─ AND: Aromatic systems present OR bond_orders stable
├─ THEN: AGREE (stable under use conditions)
└─ ELSE: HOLLOW or REJECT

Rule 4: ACTIVITY/SELECTIVITY (application-dependent)
├─ IF: Application = "breath_VOC_sensing"
│  ├─ AND: Contains polar functional groups (O, N with high electronegativity)
│  ├─ AND: Aromatic rings present (π-π interactions with VOCs)
│  ├─ AND: Pore size compatible with VOC molecules
│  └─ THEN: AGREE (good for VOC sensing)
├─ IF: Application = "food_safety"
│  ├─ AND: High H-bond donor/acceptor count (detect contaminants via H-bonding)
│  └─ THEN: AGREE
└─ IF: Application = "PFAS_detection"
   ├─ AND: Contains halogen-binding sites (Lewis acidic)
   └─ THEN: AGREE

Rule 5: ELECTRICAL_CONDUCTIVITY
├─ IF: Delocalized π-system (conjugation_length > 6)
├─ AND: Aromatic content > 50%
├─ AND: Orbital overlap (relative) > threshold
├─ THEN: AGREE (good electrical conductor)
├─ ELSE IF: Partial charges suggest ionic character
├─ THEN: HOLLOW (ambiguous—depends on metal centers)
└─ ELSE: REJECT (poor conductor)
```

**Implementation:**
```python
def zfc_rule_engine(descriptors, application_context):
    """
    Input: MOthSimplifier descriptors, application context
    Output: Preliminary verdicts for each category
    """
    verdicts = {}
    
    # Synthesizability check
    if all_bonds_valid(descriptors) and no_strained_rings(descriptors):
        verdicts['synthesizability'] = 'AGREE'
    else:
        verdicts['synthesizability'] = 'REJECT'
    
    # Toxicity check
    if contains_toxic_groups(descriptors):
        verdicts['toxicity'] = 'REJECT'
    elif high_electrophilicity(descriptors):
        verdicts['toxicity'] = 'HOLLOW'
    else:
        verdicts['toxicity'] = 'AGREE'
    
    # ... repeat for stability, activity, conductivity
    
    return verdicts
```

### 5.3 CAT Layer: Morphism Integrity Reasoning

**Purpose:** Check if atomic descriptors *compose* into coherent material properties

**Key Concept:** Bonding variability is detected here.

**Process:**

For each atom pair (i, j):
1. Extract local descriptors: D_i, D_j, bond_type_{ij}
2. Define morphism: φ_{ij} = "Do D_i and D_j compose consistently through bond_type_{ij}?"
3. Check consistency:
   - Electronegativity difference → Expected bond polarity
   - Orbital overlap → Expected bond strength
   - Bond type (single/double/aromatic) → Orbital hybridization
4. If all pairs consistent → MORPHISM_INTEGRITY = HIGH
5. If some pairs contradict → MORPHISM_INTEGRITY = MEDIUM (HOLLOW verdict)
6. If many pairs contradict → MORPHISM_INTEGRITY = LOW (ORPHAN verdict)

**Example Contradiction Detection (bonding variability):**

```
Atom A: sp2 hybridized, high π-character
  ↓ (single bond)
Atom B: sp3 hybridized, no π-character
  ↓ (π-bond expected due to A's sp2)
→ CONTRADICTION: Bond type doesn't match orbital character
→ MORPHISM_INTEGRITY decreases
→ Verdict shifts toward HOLLOW or ORPHAN
```

**Implementation:**
```python
def cat_morphism_integrity(descriptors):
    """
    Compute morphism integrity score (0-1)
    Higher = more consistent atomic composition
    """
    bonds = descriptors['bonds']  # List of (atom_i, atom_j, bond_type)
    contradictions = 0
    total_bonds = len(bonds)
    
    for atom_i, atom_j, bond_type in bonds:
        d_i = descriptors['atoms'][atom_i]
        d_j = descriptors['atoms'][atom_j]
        
        expected_bond = predict_bond_type(d_i, d_j)
        if expected_bond != bond_type:
            contradictions += 1
    
    morphism_integrity = 1.0 - (contradictions / total_bonds)
    return morphism_integrity
```

### 5.4 Verdict Synthesis

**For each candidate linker:**

```python
def compute_verdicts(candidate_smiles, application_context):
    # Standardize
    linker = MolSimplifier.standardize(candidate_smiles)
    
    # Extract descriptors
    descriptors = MOthSimplifier.compute(linker)
    
    # ZFC layer
    zfc_verdicts = zfc_rule_engine(descriptors, application_context)
    
    # CAT layer
    morphism_integrity = cat_morphism_integrity(descriptors)
    
    # Combine: ZFC verdict + morphism modifier
    final_verdicts = {}
    for category in ['synthesizability', 'toxicity', 'stability', 'activity', 'conductivity']:
        zfc = zfc_verdicts[category]
        
        if morphism_integrity > 0.9:
            # High integrity: trust ZFC verdict
            final_verdicts[category] = zfc
        elif morphism_integrity > 0.7:
            # Medium integrity: downgrade to HOLLOW if contradictions exist
            if zfc == 'AGREE':
                final_verdicts[category] = 'HOLLOW'
            else:
                final_verdicts[category] = zfc
        else:
            # Low integrity: flag as ORPHAN
            final_verdicts[category] = 'ORPHAN'
    
    return {
        'verdicts': final_verdicts,
        'morphism_integrity': morphism_integrity,
        'reasoning_trace': generate_trace(zfc_verdicts, morphism_integrity)
    }
```

**Output Format:**
```json
{
  "linker_smiles": "Cc1ccccc1NC(=O)c2ccccc2C",
  "verdicts": {
    "synthesizability": "AGREE",
    "toxicity": "AGREE",
    "stability": "AGREE",
    "activity_voc_sensing": "AGREE",
    "electrical_conductivity": "HOLLOW"
  },
  "morphism_integrity": 0.94,
  "reasoning_trace": {
    "synthesizability": "All bonds valid, no strained rings",
    "toxicity": "No toxic groups detected",
    "stability": "Bond strengths > 2 kcal/mol",
    "activity": "Aromatic + polar groups → good VOC interaction",
    "conductivity": "Aromatic but partial charges suggest local ionic character → ambiguous"
  }
}
```

---

## 6. Constraint Filter & Ranking

### 6.1 Filter Criteria

**Keep candidate IF:**
- `synthesizability == AGREE`
- `toxicity == AGREE`
- `stability == AGREE`
- `activity == AGREE` (for chosen application)
- `electrical_conductivity == AGREE` (if application requires conductivity)

**Note:** Can relax to allow HOLLOW verdicts if desired (exploratory mode).

### 6.2 Ranking

**Primary sort:** Morphism integrity (descending)
**Secondary sort:** Number of properties with AGREE verdict (descending)

**Output:** Top 50 candidates ranked by morphism integrity

---

## 7. Streamlit UI

### 7.1 User Inputs

**Page 1: Configuration**
```
[Application Context: Dropdown]
  ├─ Breath VOC Sensing (stress/health)
  ├─ Food Safety (contamination)
  ├─ PFAS Detection
  └─ Custom

[Number of Candidates to Generate: Slider 10-1000, default 100]

[Include HOLLOW Verdicts: Toggle, default OFF]

[Button: Generate Candidates]
```

### 7.2 Results Display

**Page 2: Results Table**
```
Rank | SMILES | MW | Synth | Toxin | Stabil | Activity | Conduct | Morphism | Actions
-----|--------|-------|--------|--------|---------|----------|----------|----------|----------
 1   | Cc1... | 234.2 | ✓      | ✓      | ✓       | ✓        | ✓        | 0.94     | [View] [Export]
 2   | Nc2... | 245.1 | ✓      | ✓      | ✓       | ✓        | ◇        | 0.91     | [View] [Export]
 ...
```

**Legend:**
- ✓ = AGREE
- ◇ = HOLLOW
- ✗ = REJECT
- ○ = ORPHAN

### 7.3 Detail View (Click on Rank)

```
LINKER #1
SMILES: Cc1ccccc1NC(=O)c2ccccc2C
Molecular Weight: 234.2 g/mol

VERDICTS:
├─ Synthesizability: AGREE
│  └─ Reasoning: All bonds valid, matches known synthesis routes
├─ Toxicity: AGREE
│  └─ Reasoning: No known toxic groups detected
├─ Stability: AGREE
│  └─ Reasoning: Bond strengths > 2 kcal/mol, stable under conditions
├─ Activity (VOC Sensing): AGREE
│  └─ Reasoning: Aromatic + polar groups enable π-π and H-bond interactions
└─ Electrical Conductivity: HOLLOW
   └─ Reasoning: Partial charges suggest local ionic effects; conductivity ambiguous

MORPHISM INTEGRITY: 0.94 (94%)
├─ Interpretation: Atomic descriptors compose consistently
├─ Contradiction count: 1/16 bonds
└─ Note: High-quality candidate; one ambiguity in conductivity

[Export to CSV] [View Structure] [Compare with Others]
```

### 7.4 Batch Export

```
[Download as CSV]
[Download as JSON]
[Generate PDF Report]
```

**CSV Format:**
```
rank, smiles, mw, synthesizability, toxicity, stability, activity, conductivity, morphism_integrity, reasoning
1, "Cc1ccccc1...", 234.2, AGREE, AGREE, AGREE, AGREE, HOLLOW, 0.94, "..."
2, "Nc2ccccc2...", 245.1, AGREE, AGREE, AGREE, AGREE, AGREE, 0.91, "..."
```

---

## 8. Implementation Sequence

### Phase 1: Data Pipeline (1-2 hours)
**Files to create:**
- `load_mp_linkers.py` - Query MP API, extract 22-atom linkers, populate SQLite

**Deliverable:** `materials_22atom.db` (~5k-8k records)

### Phase 2: Generative Model (2-4 hours)
**Files to create:**
- `train_linker_generator.py` - Train GNN on 22-atom linkers
- `generate_candidates.py` - Use trained model to generate new linkers

**Deliverable:** `linker_generator_checkpoint.pt`

### Phase 3: KOMPOSOS Integration (1-2 hours)
**Files to create:**
- `komposos_mof_verdicts.py` - ZFC + CAT reasoning modules

**Functions:**
- `zfc_rule_engine(descriptors, application_context)`
- `cat_morphism_integrity(descriptors)`
- `compute_verdicts(candidate_smiles, application_context)`

**Deliverable:** Verdict computation pipeline

### Phase 4: Screening Pipeline (1 hour)
**Files to create:**
- `screen_candidates.py` - Generate N candidates, filter through KOMPOSOS, rank

**Deliverable:** Ranked CSV of top 50 candidates

### Phase 5: Streamlit UI (1-2 hours)
**Files to create:**
- `app.py` - Full UI with inputs, results, export

**Deliverable:** Runnable Streamlit app

### Phase 6: Testing & Refinement (1 hour)
- Validate verdicts against known MOFs
- Tune rule thresholds
- Performance optimization

---

## 9. Technical Stack

**Core Libraries:**
- `mp_api` - Materials Project API client
- `rdkit` - Molecular operations, SMILES parsing
- `molsimplifier` - Linker standardization
- `mothsimplifier` - Atom descriptor extraction
- `torch`, `torch_geometric` - GNN training & inference
- `sqlalchemy` - Database ORM
- `streamlit` - Web UI
- `pandas` - Data handling
- `numpy`, `scipy` - Numerical computing

**Hardware:**
- GPU: 12+ GB VRAM (recommended for training)
- CPU: 8+ cores
- Storage: 10+ GB for database + model checkpoints

**Development Environment:**
- Python 3.10+
- Conda or venv for environment management

---

## 10. Success Criteria

1. **Data layer:** Successfully load 5k-8k 22-atom linkers into SQLite ✓
2. **Model training:** GNN trains without divergence, achieves <5% invalid SMILES ✓
3. **KOMPOSOS verdicts:** Generate verdicts for each candidate in <1 sec ✓
4. **Screening:** Generate 100 candidates, filter to top 50, complete in <5 min ✓
5. **UI:** Streamlit app runs, user can select application + export results ✓
6. **Validation:** Compare verdicts against ~10 known MOF linkers, check for sensible predictions ✓

---

## 11. Known Limitations & Future Work

**Current Limitations:**
- GNN trained only on 22-atom linkers; may not generalize to other sizes
- ZFC rules are heuristic; DFT validation recommended for top candidates
- MOF assembly (metal + linker + topology) not yet modeled; only linker screening
- Electrical conductivity verdict is structural estimate, not quantum-mechanical

**Future Extensions:**
- Add DFT screening for top N candidates (high-accuracy electrical/stability)
- Extend to variable-size linkers (not just 22 atoms)
- Model full MOF assembly (metal node + linker + topology)
- Incorporate experimental data for rule refinement
- Multi-objective optimization (Pareto frontier of verdicts)

---

## 12. Deliverables Checklist

- [ ] `load_mp_linkers.py` - Data pipeline script
- [ ] `materials_22atom.db` - SQLite database (5k-8k linkers)
- [ ] `train_linker_generator.py` - Model training script
- [ ] `linker_generator_checkpoint.pt` - Trained GNN checkpoint
- [ ] `komposos_mof_verdicts.py` - ZFC + CAT reasoning modules
- [ ] `screen_candidates.py` - Screening & ranking pipeline
- [ ] `app.py` - Streamlit UI
- [ ] `requirements.txt` - Python dependencies
- [ ] `README.md` - Usage guide
- [ ] `sample_results.csv` - Example output (top 50 candidates)

---

**Ready to build. No more questions. Execute.**
