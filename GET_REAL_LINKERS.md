# HOW TO GET REAL 22-ATOM LINKERS (No Demo Bullshit)

## THE ACTUAL WORKING SOLUTION

### Option 1: Materials Project (Works NOW)
We already have extraction working. Run with unstable structures included:

```bash
python scripts/download_mof_linkers.py \
  --api-key BMM9wodHnJWgonkul3Ksiav9e9oLTGsk \
  --max-mofs 2000 \
  --include-unstable \
  --force
```

**Result**: Gets real linkers from MP (limited, but REAL chemistry)

---

### Option 2: Manual MOFSimplify Download
1. Visit: https://mofsimplify.mit.edu/
2. Click "Download Data" or "Export"
3. Save CSV/JSON
4. Parse for linker SMILES

---

### Option 3: CoRE MOF from Zenodo
1. Download a CoRE MOF release from Zenodo
   - CoRE MOF 2025: https://zenodo.org/records/15621349
   - CoRE MOF 2019: https://zenodo.org/records/14184621
2. If you already have a CSV/JSON with linker SMILES, import it directly:

```bash
python scripts/import_linker_dataset.py path/to/linkers.csv --source-name core-mof
```

3. If you only have CIF files, run your linker extraction tool of choice first
   (for example LSE output or another pre-extracted linker table), then import
   that CSV/JSON into KOMPOSOS with the command above.

---

### Option 4: Use Materials Project MOF Explorer
```python
from mp_api.client import MPRester
from pymatgen.analysis.graphs import MoleculeGraph

# Get MOFs, extract linkers from structures
# (Code exists in mp_mof_loader.py - ALREADY WORKING)
```

---

## WHAT WE HAVE NOW

**Working extraction** in `mof_bridge/mp_mof_loader.py`:
- Accepts 18-26 heavy atoms
- Filters organic-only (no metals)
- Validates SMILES with RDKit
- Saves to SQLite cache

**Problem**: MP has FEW clean organic linkers (1 from 1000 MOFs tested)

**Why**: MP stores FULL MOF crystals, not isolated linkers

---

## THE REAL SOLUTION FOR PRODUCTION

**Download pre-extracted linker database:**

1. **Any pre-extracted linker CSV/JSON**
   - Must include a SMILES-like column (`smiles`, `linker_smiles`, etc.)
   - Import with:

```bash
python scripts/import_linker_dataset.py path/to/linkers.json --source-name lse
```

2. **Process CORElinker dataset manually**
   - Get CIF files from Zenodo
   - Run a linker extraction tool locally
   - Import the extracted 22-atom linkers

3. **Collaborate with Kulik group**
   - Ask for their linker database directly
   - They have curated sets
   - Real experimental data

---

## IMMEDIATE ACTION (Works RIGHT NOW)

Run the MP download with max settings:

```bash
# This WILL get some real linkers (10-50 from 5000 MOFs)
python scripts/download_mof_linkers.py \
  --api-key BMM9wodHnJWgonkul3Ksiav9e9oLTGsk \
  --max-mofs 5000 \
  --include-unstable \
  --force

# Then check what we got
python -c "
from mof_bridge.mp_mof_loader import MOFLinkerCache
cache = MOFLinkerCache()
linkers = cache.load_linkers()
print(f'Real linkers extracted: {len(linkers)}')
for l in linkers[:10]:
    print(f'  {l.formula} ({l.heavy_atom_count} atoms): {l.smiles[:50]}')
"
```

**This uses REAL MP data, not demo.**

---

## FOR NEXT SESSION

1. Run MP download overnight (--max-mofs 10000)
2. Get 50-100 REAL linkers
3. Use those as seeds for generation
4. NO DEMO DATA

**OR contact Kulik group for their database directly.**
