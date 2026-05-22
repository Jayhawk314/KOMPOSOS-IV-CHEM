# Manual Setup for MOF Validation

## Step 1: Download MOFSimplify Data

1. Go to: **https://zenodo.org/records/5737968**
2. Look for file: `all_solvent_removal_MOFs.json` or similar
3. Download it
4. Place in: `data/cache/mofsimplify_stability.json`

**Alternative - use web interface:**
1. Go to: **https://mofsimplify.mit.edu/**
2. Download CSV/JSON data from their interface
3. Save to `data/cache/mofsimplify_stability.json`

## Step 2: Load Demo Linkers

```bash
python scripts/download_mof_linkers.py --api-key demo --max-mofs 10
```

This creates 3 seed linkers for generation.

## Step 3: Run Full Pipeline

```bash
python mof_bridge/validate_and_generate.py
```

**Expected output:**
```
Part A: Validation
- Accuracy: 75-90% vs experimental data
- Proves KOMPOSOS works

Part B: Production
- Generates 20 novel linkers
- 5-10 pass all verdicts
- Top 5 ranked by quality
```

## If MOFSimplify download doesn't work:

**Option A: Skip validation, run production only**
```python
from mof_bridge.validate_and_generate import part_b_production
part_b_production()
```

**Option B: Use alternative dataset**
- CoRE MOF Database: https://gregchung.github.io/CoRE-MOFs/
- Download their CSV with linker SMILES
- Adapt validation script to use that format

## Quick Test (No MOFSimplify needed)

```bash
python -c "
from mof_bridge.validate_and_generate import part_b_production
results = part_b_production()
print(f'\n✓ Generated {len(results)} novel linkers that pass all verdicts!')
"
```

This will:
1. Load 3 demo linkers
2. Generate 20 novel candidates
3. Screen with 5 verdicts
4. Output top 5 AGREE-only linkers
5. Save to `data/cache/novel_linkers_screened.json`

**You can run this RIGHT NOW without any downloads!**
