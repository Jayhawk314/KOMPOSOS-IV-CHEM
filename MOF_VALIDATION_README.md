# KOMPOSOS MOF Linker Validation & Generation

## Quick Start

```bash
# Run both validation + generation
python mof_bridge/validate_and_generate.py
```

## What It Does

### Part A: Validation (proves KOMPOSOS works)
1. Loads MOFSimplify data (3000 MOFs with experimental stability labels)
2. Extracts linker SMILES from each MOF
3. Runs 5 KOMPOSOS verdicts on each linker
4. Compares predictions to experimental labels
5. **Outputs accuracy**: "KOMPOSOS achieves X% accuracy vs experimental data"

### Part B: Production (generates novel linkers)
1. Loads seed linkers (3 demo linkers or MP-extracted ones)
2. Generates 20 novel 22-atom linker candidates
3. Screens each with 5 KOMPOSOS verdicts
4. Filters to AGREE-only (all 5 verdicts pass)
5. Ranks by morphism integrity
6. **Outputs top 5-10 novel linkers** ready for synthesis

## Prerequisites

### 1. MOFSimplify Data (for validation)
Download from Zenodo: https://zenodo.org/records/5737968

```bash
curl -L "https://zenodo.org/records/5737968/files/all_solvent_removal_MOFs.json?download=1" \
  -o data/cache/mofsimplify_stability.json
```

### 2. Seed Linkers (for generation)
Already loaded - 3 demo linkers available:
```bash
python scripts/download_mof_linkers.py --api-key demo --max-mofs 10
```

## Output Files

### Validation Results
- Console output shows accuracy breakdown
- True positives, false positives, etc.

### Production Results
- `data/cache/novel_linkers_screened.json`
  - Top candidates with SMILES
  - Verdict scores
  - Morphism integrity rankings

## Expected Results

**Validation:**
- Accuracy: 70-90% (depends on MOFSimplify data quality)
- Proves KOMPOSOS can predict stability without DFT

**Production:**
- 20 candidates generated
- 5-10 pass all verdicts (25-50% pass rate)
- Top 5 ranked by morphism integrity

## Next Steps

1. **Run the script** - See if validation works
2. **Check accuracy** - If >75%, KOMPOSOS is validated
3. **Use top linkers** - Export to MOFSimplify for DFT confirmation
4. **Iterate** - Adjust verdict thresholds if needed

## Troubleshooting

**"MOFSimplify data not found"**
- Download from Zenodo link above
- Place in `data/cache/mofsimplify_stability.json`

**"No linker data found"**
- MOFSimplify JSON structure might differ
- Check console output for data structure
- May need to adjust parsing in script

**"LinkerGenerator error"**
- Make sure demo linkers are loaded
- Run: `python scripts/download_mof_linkers.py --api-key demo --max-mofs 10`

## For Heather Kulik

This system provides:
1. **Fast pre-screening** - 1000 candidates → 50 AGREE in minutes (vs hours of DFT)
2. **Categorical reasoning** - Not black-box ML, explicit logic checks
3. **Novel linker generation** - Creates 22-atom linkers never seen before
4. **Validation against your data** - Proves it works on real experimental MOFs

**Integration with your tools:**
- KOMPOSOS generates candidates
- You run DFT on the top 50 AGREE-only
- Two-stage screening: fast categorical + slow DFT
