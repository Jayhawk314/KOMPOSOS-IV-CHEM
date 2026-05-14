# Data Importers for tier1.db Expansion

This directory contains scripts to import biomedical data from external sources into `tier1_manifest.json`.

Each importer:
1. Queries an external API or downloads bulk data
2. Filters by confidence/quality thresholds
3. Maps to tier1_manifest.json format
4. Adds provenance/evidence IDs
5. Outputs new manifest file

## Available Importers

### 1. ChEMBL SQLite (PRIORITY 1 - PRODUCTION-GRADE)

**File**: `import_chembl_sqlite.py`

**What it does**:
- Imports drug-target associations from local ChEMBL SQLite database
- PRODUCTION APPROACH: No API delays, no rate limits, complete data access
- Full provenance: PMIDs for EVERY edge
- Addresses Roadmap Step 8: Complete provenance for 302 uncited morphisms

**Why this is best**:
- ✅ **Quality**: Measured IC50/Ki/Kd values + curated mechanisms
- ✅ **Provenance**: PMIDs from literature for every association
- ✅ **Reliability**: Local database, no network dependencies
- ✅ **Speed**: Instant SQL queries (vs hours of API calls)
- ✅ **Complete**: Access to all ChEMBL data, not just API endpoints
- ✅ **Reproducible**: Versioned database files (chembl_33.db)

**Setup** (one-time):

```bash
# Download ChEMBL SQLite database (~4GB)
wget https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_33_sqlite.tar.gz
tar -xzf chembl_33_sqlite.tar.gz

# Database will be at: chembl_33/chembl_33_sqlite/chembl_33.db
```

See **CHEMBL_SETUP.md** for complete setup guide.

**Usage**:

```bash
# Test with small sample (100 associations)
python data/drugs/importers/import_chembl_sqlite.py \
    --chembl-db chembl_33/chembl_33_sqlite/chembl_33.db \
    --manifest data/drugs/tier1_manifest.json \
    --output tier1_manifest_chembl_test.json \
    --limit 100

# Production import (1000-5000 associations)
python data/drugs/importers/import_chembl_sqlite.py \
    --chembl-db chembl_33/chembl_33_sqlite/chembl_33.db \
    --manifest data/drugs/tier1_manifest.json \
    --output tier1_manifest_chembl.json \
    --limit 1000
```

**Parameters**:
- `--chembl-db`: Path to ChEMBL SQLite database (REQUIRED)
- `--manifest`: Path to existing manifest (default: data/drugs/tier1_manifest.json)
- `--output`: Path to save updated manifest (default: tier1_manifest_chembl.json)
- `--min-pchembl`: Minimum pChEMBL value (6.0=1µM, 7.0=100nM, 8.0=10nM). Default: 6.0
- `--limit`: Maximum associations to import (default: 10000)
- `--all-phases`: Include clinical trials (default: approved only)

**Output**:
- Drug-target associations with PMIDs
- Mechanisms of action (INHIBITOR, ANTAGONIST, AGONIST, etc.)
- Clinical phase information (FDA approval status)
- Provenance improvement: **22% → 50-65%** ✅

**Expected impact**:
- +250 morphisms (limit=1000) or +1000 morphisms (limit=5000)
- +100-200 new protein objects
- **Addresses Roadmap Step 8**: Provenance coverage dramatically improved

**Next steps after import**:

```bash
# 1. Rebuild database
python data/drugs/build_tier1.py --manifest tier1_manifest_chembl.json

# 2. Validate AUROC stays ≥0.94
python validation/repurposing_benchmark.py --view full_typed --protocol loocv --ci

# 3. If AUROC ≥0.94, replace original manifest
cp tier1_manifest_chembl.json tier1_manifest.json
python data/drugs/build_tier1.py
```

---

### 2. OpenTargets (PRIORITY 2 - API ALTERNATIVE)

**File**: `import_opentargets.py`

**What it does**:
- Imports 30,000+ drug-target associations
- All associations have evidence IDs (OpenTargets data source identifiers)
- Automatically infers morphism type from mechanism of action (inhibits, activates, antagonizes, modulates)
- Maps OpenTargets confidence scores to morphism confidence [0-1]

**Usage**:

```bash
# Basic (default settings)
python data/drugs/importers/import_opentargets.py \
    --manifest data/drugs/tier1_manifest.json \
    --output data/drugs/tier1_manifest_opentargets.json

# Custom thresholds
python data/drugs/importers/import_opentargets.py \
    --manifest data/drugs/tier1_manifest.json \
    --output data/drugs/tier1_manifest_opentargets.json \
    --min-score 0.8 \
    --limit 30000
```

**Parameters**:
- `--manifest`: Path to existing tier1_manifest.json (default: data/drugs/tier1_manifest.json)
- `--output`: Path to save updated manifest (default: tier1_manifest_opentargets.json)
- `--min-score`: Minimum association score 0-1 (default: 0.7)
  - 0.5-0.7: Moderate confidence (ChEMBL, text mining evidence)
  - 0.7-0.9: High confidence (clinical trials, GWAS)
  - 0.9+: Very high confidence (approved drugs with strong evidence)
- `--limit`: Maximum associations to import (default: 50000)

**Output**:
- New manifest with +30k morphisms, +5k protein objects
- All morphisms tagged with provenance `opentargets:{drug_id}:{target}`
- Example morphism:
  ```json
  {
    "source": "Sorafenib",
    "target": "VEGFR2",
    "name": "inhibits",
    "confidence": 0.85,
    "provenance": "opentargets:CHEMBL274810:VEGFR2",
    "metadata": {
      "source": "OpenTargets",
      "moa": "tyrosine kinase inhibitor",
      "phase": "PHASE_4",
      "drug_id": "CHEMBL274810"
    }
  }
  ```

**Next steps after import**:

```bash
# 1. Review the output manifest
head -100 data/drugs/tier1_manifest_opentargets.json

# 2. Rebuild tier1.db with new data
python data/drugs/build_tier1.py \
    --manifest data/drugs/tier1_manifest_opentargets.json \
    --output data/drugs/tier1_opentargets.db

# 3. Run benchmarks to verify AUROC stays ≥0.94
python validation/repurposing_benchmark.py \
    --view full_typed --protocol loocv --ci --baselines \
    --db data/drugs/tier1_opentargets.db

# 4. If AUROC ≥0.94, replace original manifest
cp data/drugs/tier1_manifest_opentargets.json data/drugs/tier1_manifest.json
python data/drugs/build_tier1.py
```

**API Details**:
- **Endpoint**: https://api.platform.opentargets.org/api/v4/graphql (free, no authentication)
- **Rate limit**: No official limit, but request responsibly (~1000 requests per minute safe)
- **Response format**: GraphQL JSON
- **Evidence types**: ChEMBL, ClinicalTrials.gov, Reactome, GWAS, PheWAS, and 15+ others

**Troubleshooting**:
- "No associations retrieved": Check internet connection and API endpoint status
- "Score < min_score": Lower min_score threshold (try 0.5 for broader coverage)
- "AUROC drops below 0.94": Morphism confidence mapping may need adjustment (contact maintainer)

---

### 2. STRING (PRIORITY 1)

**File**: `import_string.py`

**What it does**:
- Imports high-confidence protein-protein interactions
- Downloads STRING bulk file (~200MB compressed, 24M human PPIs)
- Filters for proteins already in tier1.db (from OpenTargets or manual curation)
- Creates bidirectional morphisms (A→B and B→A for each PPI)
- All interactions have combined scores (experimental + database + text mining + co-expression)

**Usage**:

```bash
# Basic (requires OpenTargets import first)
python data/drugs/importers/import_string.py \
    --manifest data/drugs/tier1_manifest.json \
    --output data/drugs/tier1_manifest_string.json

# Custom thresholds
python data/drugs/importers/import_string.py \
    --manifest data/drugs/tier1_manifest.json \
    --output data/drugs/tier1_manifest_string.json \
    --min-score 800 \
    --limit 1000
```

**Parameters**:
- `--manifest`: Path to existing manifest (should already have OpenTargets data)
- `--output`: Path to save updated manifest
- `--min-score`: Minimum combined score 0-1000 (default: 700)
  - 400-699: Medium confidence (co-expression, text mining)
  - 700-899: High confidence (experiments, databases)
  - 900-1000: Very high confidence (multiple experimental sources)
- `--limit`: Maximum PPIs to import (default: 5000)
- `--species`: NCBI taxonomy ID (default: 9606 = human)

**Output**:
- New manifest with +500-2000 morphisms (depends on how many proteins from OpenTargets)
- All morphisms tagged with provenance `string:{protein1}:{protein2}`
- Example morphism:
  ```json
  {
    "source": "BRAF",
    "target": "MEK1",
    "name": "interacts_with",
    "confidence": 0.85,
    "provenance": "string:BRAF:MEK1",
    "metadata": {
      "source": "STRING",
      "score": 850,
      "direction": "forward"
    }
  }
  ```

**IMPORTANT**: Run STRING AFTER OpenTargets
- STRING needs existing proteins to filter against
- If you run STRING first, it will find no matches
- Recommended order: OpenTargets → STRING → ClinicalTrials → DisGeNET

**API Details**:
- **Bulk download**: https://stringdb-downloads.org/download/protein.links.v12.0/
- **Mapping API**: https://string-db.org/api (for ENSP → gene symbol)
- **Rate limit**: No official limit, but downloads are ~200MB (may take 5-10 minutes)
- **Evidence types**: Experimental, database, text mining, co-expression, genomic context, homology

---

## Planned Importers (Priority 2)

### 3. ClinicalTrials.gov (Clinical Trial Outcomes)
- **Status**: Not yet implemented
- **Expected contribution**: +1000 Drug→Disease morphisms, temporal validation dataset
- **See**: DATA_EXPANSION_GUIDE.md

### 4. DisGeNET (Gene-Disease Associations)
- **Status**: Not yet implemented
- **Expected contribution**: +2000 Protein→Disease morphisms, improved provenance
- **See**: DATA_EXPANSION_GUIDE.md

---

## Data Quality Checklist

Before adding any importer, verify:

- [ ] **License**: Can we use it? (Academic? Commercial?)
- [ ] **Provenance**: Does it have IDs/PMIDs for tracking?
- [ ] **Confidence scores**: Reliability metrics provided?
- [ ] **Versioning**: Reproducible builds possible?
- [ ] **Update frequency**: How often is it updated?
- [ ] **Species filter**: Can we filter for human only?
- [ ] **Ontology mapping**: Standard ontologies (UMLS, Gene Ontology)?
- [ ] **Test import**: Run on sample data before full scale

---

## Development Guide

To create a new importer:

1. **Copy template**:
   ```bash
   cp import_opentargets.py import_[source].py
   ```

2. **Implement query method**:
   ```python
   def get_associations(self) -> List[Dict[str, Any]]:
       # Query API or download bulk file
       # Filter by confidence/quality
       # Return list of raw associations
   ```

3. **Implement mapping method**:
   ```python
   def map_to_morphism(self, assoc: Dict[str, Any]) -> Dict[str, Any]:
       # Convert to {"source": ..., "target": ..., "name": ..., ...}
       # Infer morphism type from evidence
       # Add provenance ID
   ```

4. **Update run() method**:
   ```python
   def run(self, manifest_path: str, output_path: str):
       associations = self.get_associations()
       manifest = self.load_manifest(manifest_path)
       self.add_objects(manifest, associations)
       self.add_morphisms(manifest, associations)
       self.save_manifest(manifest, output_path)
   ```

5. **Test**:
   ```bash
   python import_[source].py --manifest data/drugs/tier1_manifest.json --limit 100
   python data/drugs/build_tier1.py --manifest tier1_manifest_test.json
   ```

6. **Document**:
   - Update this README
   - Add to DATA_EXPANSION_GUIDE.md priority list
   - Document any API quirks

---

## Contact

For questions or issues with importers, see:
- `DATA_EXPANSION_GUIDE.md` - Integration workflow
- `MASTER_TECHNICAL.md` - Full architecture
- `CLAUDE.md` - Operating instructions
