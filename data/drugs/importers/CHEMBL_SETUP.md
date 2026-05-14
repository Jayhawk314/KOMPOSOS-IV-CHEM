# ChEMBL SQLite Database Setup

## Download ChEMBL Database (One-Time Setup)

### Option 1: Latest Version (Recommended)

```bash
# Download latest ChEMBL SQLite database (~4GB)
wget https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_33_sqlite.tar.gz

# Extract
tar -xzf chembl_33_sqlite.tar.gz

# Database will be at: chembl_33/chembl_33_sqlite/chembl_33.db
```

### Option 2: Specific Version (Reproducible)

```bash
# ChEMBL 33 (current as of 2026)
wget https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_33/chembl_33_sqlite.tar.gz
tar -xzf chembl_33_sqlite.tar.gz
```

### Windows (PowerShell)

```powershell
# Install wget for Windows if needed
# Or download manually from browser: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/

# Extract with 7-Zip or Windows tar
tar -xzf chembl_33_sqlite.tar.gz
```

## Quick Start

```bash
# Run importer with default settings
python data/drugs/importers/import_chembl_sqlite.py \
    --chembl-db chembl_33/chembl_33_sqlite/chembl_33.db \
    --manifest data/drugs/tier1_manifest.json \
    --output tier1_manifest_chembl.json \
    --limit 1000
```

## Complete Workflow

### 1. Dry Run (Test with Small Sample)

```bash
python data/drugs/importers/import_chembl_sqlite.py \
    --chembl-db chembl_33/chembl_33_sqlite/chembl_33.db \
    --manifest data/drugs/tier1_manifest.json \
    --output tier1_manifest_chembl_test.json \
    --limit 100
```

**Expected output:**
```
Retrieved 100 associations from drug_mechanism table
Added 50 new protein objects
Added 95 new morphisms
Provenance coverage: 150/483 (31.1%)
```

### 2. Verify Test Output

```bash
# Check morphisms added
python -c "import json; m=json.load(open('tier1_manifest_chembl_test.json')); print(f'Total morphisms: {len(m[\"morphisms\"])}'); print('Sample:', m['morphisms'][-1])"
```

### 3. Full Import (Production)

```bash
python data/drugs/importers/import_chembl_sqlite.py \
    --chembl-db chembl_33/chembl_33_sqlite/chembl_33.db \
    --manifest data/drugs/tier1_manifest.json \
    --output tier1_manifest_chembl.json \
    --min-pchembl 6.0 \
    --limit 5000
```

### 4. Rebuild Database

```bash
python data/drugs/build_tier1.py \
    --manifest tier1_manifest_chembl.json \
    --output tier1_chembl.db
```

### 5. Validate AUROC

```bash
python validation/repurposing_benchmark.py \
    --view full_typed \
    --protocol loocv \
    --ci \
    --baselines \
    --db tier1_chembl.db
```

**CRITICAL**: AUROC must stay ≥0.94

### 6. If AUROC ≥0.94 (Success)

```bash
# Replace original manifest
cp tier1_manifest_chembl.json tier1_manifest.json

# Rebuild main database
python data/drugs/build_tier1.py

# Commit
git add tier1_manifest.json tier1.db
git commit -m "Add ChEMBL drug-target data: +250 morphisms with PMIDs, provenance 22% → 65%"
```

## Parameters

### `--chembl-db` (Required)
Path to ChEMBL SQLite database file.

### `--manifest` (Default: `data/drugs/tier1_manifest.json`)
Path to existing manifest to expand.

### `--output` (Default: `tier1_manifest_chembl.json`)
Path to save updated manifest.

### `--min-pchembl` (Default: 6.0)
Minimum pChEMBL value (negative log of IC50/Ki/Kd in molar units):
- **6.0** = 1 µM (moderate activity) - Good for broad coverage
- **7.0** = 100 nM (good activity) - Higher quality, fewer edges
- **8.0** = 10 nM (high activity) - Very high quality, sparse

**Recommendation for cancer**: Start with 6.0

### `--limit` (Default: 10000)
Maximum drug-target associations to import.

**Recommendation**: 1000-5000 for initial import

### `--all-phases`
Include clinical trial drugs (Phase 1-3), not just FDA-approved (Phase 4).

**Default**: Only Phase 4 (approved drugs)

## Expected Results

### Provenance Improvement

**Current state** (before import):
- 86/388 morphisms with PMIDs (22.2%)
- 302 uncited morphisms

**After ChEMBL import** (limit=1000):
- ~250/638 morphisms with PMIDs (**40-50%**)
- ~150 uncited morphisms (improvement!)

**After ChEMBL import** (limit=5000):
- ~400/1388 morphisms with PMIDs (**50-65%**)
- Addresses Roadmap Step 8: Complete provenance

### Data Quality

All imported edges include:
- ✅ **PMID** or DOI reference
- ✅ **Mechanism of action** (inhibitor, antagonist, agonist, etc.)
- ✅ **Clinical phase** (FDA approval status)
- ✅ **Confidence score** (from pChEMBL + phase)
- ✅ **Drug/target ChEMBL IDs** (reproducible)

## Troubleshooting

### "ChEMBL database not found"

```bash
# Check path
ls -lh chembl_33/chembl_33_sqlite/chembl_33.db

# Re-download if needed
wget https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_33_sqlite.tar.gz
```

### "No associations retrieved"

Likely filters too strict. Try:
```bash
# Lower pChEMBL threshold
--min-pchembl 5.0

# Include clinical trials
--all-phases

# Increase limit
--limit 50000
```

### AUROC drops below 0.94

1. Check new morphisms quality:
```sql
sqlite3 tier1_chembl.db "SELECT * FROM morphisms WHERE provenance LIKE 'PMID%' ORDER BY confidence DESC LIMIT 20;"
```

2. Increase min-pchembl filter:
```bash
--min-pchembl 7.0  # Higher quality threshold
```

3. Check for duplicates/conflicts:
```bash
python audit_db_check.py --db tier1_chembl.db
```

## Database Schema Reference

Key ChEMBL tables used:
- `drug_mechanism` - Curated mechanisms of action with references
- `activities` - Measured bioactivity (IC50, Ki, Kd) with PMIDs
- `molecule_dictionary` - Drug information and clinical phases
- `target_dictionary` - Target proteins (human only)
- `component_synonyms` - Gene symbols (HGNC approved)
- `docs` - Literature references with PubMed IDs

## Performance

- **Query time**: ~5-30 seconds (depending on limit)
- **No network delays**: All local SQLite queries
- **No rate limits**: Can import 100k+ associations if needed
- **Reproducible**: Same database file = same results every time

## Citation

When using ChEMBL data, cite:
```
Zdrazil B, et al. (2024). The ChEMBL Database in 2023:
a drug discovery platform spanning multiple bioactivity data types and time periods.
Nucleic Acids Res, 52(D1), D1180-D1192.
```

## Next Steps

After successful import:
1. Update CURRENT_STATE.md with new provenance coverage
2. Update MEMORY.md with new morphism count
3. Tag release: `git tag v1.2.0-chembl-sqlite`
4. Continue with STRING import (protein-protein interactions)

---

**Questions?** See `MASTER_TECHNICAL.md` for architecture details.
