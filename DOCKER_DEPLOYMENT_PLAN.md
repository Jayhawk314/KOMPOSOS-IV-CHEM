# Docker Deployment Plan for Heather Kulik Demo

## Context

Heather Kulik (MIT Chemical Engineering) has a challenge: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms." She develops molSimplify/MOFSimplify for MOF screening and wants tools that integrate with her workflow.

**Goal**: Package KOMPOSOS MOF Designer as a Docker image on DockerHub so Heather can run it with one command at MIT, plus provide pre-generated CSV of 100 viable 22-atom linkers for immediate validation.

**Why Docker (Option 4):**
- One command deployment (`docker run -p 8501:8501 jayhawk314/komposos-chemistry`)
- No Python version conflicts
- All heavy dependencies (rdkit, mp-api, pymatgen) pre-installed
- Runs locally (no internet dependency for demos)
- Integrates into her active learning pipeline
- Works on MIT cluster/HPC environments

**Current State:**
- Dockerfile.streamlit exists (optimized for Render, port 10000)
- docker-compose.yml orchestrates API + UI services
- No Docker Hub registry configuration or push workflow
- requirements.txt has rdkit-pypi, mp-api, pymatgen (recent commit 6029a0c)
- Access control disabled (no-ops since commit 83c5cef)

---

## Implementation Plan

### 1. Create Production Dockerfile for DockerHub

**File**: `Dockerfile.kulik` (CREATED)

**Changes from existing Dockerfile.streamlit:**
- Base image: `python:3.11-slim` (keep)
- Port: 8501 (standard Streamlit, not Render's 10000)
- Remove Render-specific env vars (STREAMLIT_SERVER_ENABLE_CORS=false, etc.)
- Keep rdkit/mp-api/pymatgen in requirements.txt
- Add MOF cache initialization step (run demo download to seed database)
- Health check: `/_stcore/health` on 8501
- CMD: `streamlit run streamlit_app/app.py --server.port=8501 --server.address=0.0.0.0`

**Why new file**: Keeps Render deployment (Dockerfile.streamlit) separate from DockerHub production image.

---

### 2. Build and Push to DockerHub

**Prerequisites:**
- DockerHub account (username: `jayhawk314` or create new)
- Docker Desktop installed locally

**Commands:**
```bash
# Build image with version tag
docker build -f Dockerfile.kulik -t jayhawk314/komposos-chemistry:v1.0.0 -t jayhawk314/komposos-chemistry:latest .

# Test locally
docker run -p 8501:8501 jayhawk314/komposos-chemistry:latest
# Visit localhost:8501, test MOF Designer with 22 atoms

# Login to DockerHub
docker login

# Push to registry
docker push jayhawk314/komposos-chemistry:v1.0.0
docker push jayhawk314/komposos-chemistry:latest
```

**Image size**: Expect ~2-3GB (base image + rdkit ~500MB + pymatgen ~300MB + dependencies)

---

### 3. Generate 100 Viable 22-Atom Linkers CSV

**Script**: `scripts/generate_kulik_linkers.py` (TO BE CREATED)

**Logic:**
```python
from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors, Descriptors

spec = LinkerScreeningSpec(
    application_context="breath_VOC_sensing",  # Maps to CO2 capture per docs
    num_candidates=500,                        # Generate more to get 100 AGREE
    require_all_agree=True,                    # Only all-AGREE verdicts
    ranking_mode="morphism_integrity",
)

screener = LinkerScreener()
screener.generator.min_atoms = 22
screener.generator.max_atoms = 22

result = screener.screen(spec)

# Take top 100 viable
viable = [c for c in result.candidates if c.overall_viable][:100]

# Build CSV
rows = []
for i, c in enumerate(viable, 1):
    mol = Chem.MolFromSmiles(c.linker_smiles)
    rows.append({
        "rank": i,
        "SMILES": c.linker_smiles,
        "formula": rdMolDescriptors.CalcMolFormula(mol) if mol else "?",
        "heavy_atoms": mol.GetNumHeavyAtoms() if mol else 0,
        "MW": round(Descriptors.MolWt(mol), 2) if mol else 0,
        "N_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "N") if mol else 0,
        "O_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "O") if mol else 0,
        "S_count": sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "S") if mol else 0,
        "morphism_integrity": round(c.morphism_integrity, 4),
        "zfc_constraints_passed": c.zfc_constraints_passed,
        "synthesizability": c.verdicts["synthesizability"],
        "synthesizability_score": round(c.verdict_scores["synthesizability"], 4),
        "toxicity": c.verdicts["toxicity"],
        "toxicity_score": round(c.verdict_scores["toxicity"], 4),
        "stability": c.verdicts["stability"],
        "stability_score": round(c.verdict_scores["stability"], 4),
        "activity": c.verdicts["activity"],
        "activity_score": round(c.verdict_scores["activity"], 4),
        "conductivity": c.verdicts["conductivity"],
        "conductivity_score": round(c.verdict_scores["conductivity"], 4),
        "viable": c.overall_viable,
    })

df = pd.DataFrame(rows)
df.to_csv("kulik_22atom_linkers_100.csv", index=False)
print(f"Generated {len(df)} viable 22-atom linkers")
```

**Output**: `kulik_22atom_linkers_100.csv` (21 columns, 100 rows + header)

---

### 4. Create README for Heather

**File**: `README_KULIK.md` (TO BE CREATED)

**Content:**
```markdown
# KOMPOSOS MOF Linker Designer — Quick Start for Heather Kulik

## What This Solves

Your #1 LLM challenge: "Please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

KOMPOSOS generates ligands with **exact** atom count control (5-60 atoms), filters by coordinating atoms (N, O, S), and scores with 5 compositional verdicts.

## One-Command Docker Deployment

```bash
docker run -p 8501:8501 jayhawk314/komposos-chemistry:latest
```

Visit http://localhost:8501 → Page 8: MOF Designer

## Quick Test

1. Set "Exact Heavy Atom Count" = 22
2. Select "Required Donor Atoms" = Nitrogen (N)
3. Click "GENERATE LIGANDS"
4. Results: Ranked list of 22-atom N-coordinating ligands with verdicts

## Pre-Generated Linkers

Attached: `kulik_22atom_linkers_100.csv`
- 100 validated 22-atom ligands
- All 5 verdicts = AGREE (high confidence)
- Donor atom counts (N, O, S) included
- Ready for molSimplify/DFT validation

## Integration with Your Workflow

**API Access:**
```python
import requests
response = requests.post("http://localhost:8501/api/v1/design-mof-linker", json={
    "application_context": "breath_VOC_sensing",
    "num_candidates": 100,
    "exact_atoms": 22
})
```

## Contact

Questions? james@komposos.com
GitHub: https://github.com/Jayhawk314/KOMPOSOS-CHEM
```

---

## Notes

- **Image size**: ~2-3GB (rdkit is 500MB, pymatgen ~300MB) - **TOO BIG FOR FIRST CONTACT**
- **Build time**: ~10-15 minutes (rdkit compilation)
- **Demo cache**: MOF Designer auto-generates 10 demo linkers if no full MP cache exists (sufficient for proof-of-concept)
- **Access control**: Disabled since commit 83c5cef (no login required)
- **Material count**: Dynamic from DB (shows 103,663 on your computer, ~169 without MP cache)

---

## REVISED STRATEGY (Lower Friction First Contact)

**Problem**: 2-3GB Docker download is too much to ask in first email.

**Better approach:**
1. **First contact**: Send CSV of 100 linkers + link to live web demo (Render/HF Spaces)
2. **Second contact** (if interested): Docker image for local integration
3. **Third contact** (if using): API integration for molSimplify pipeline

See `KULIK_OUTREACH_REVISED.md` for new strategy.
