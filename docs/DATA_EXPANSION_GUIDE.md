# Data Expansion Guide for KOMPOSOS-IV-PHARM

**Date**: 2026-05-10 (updated: ChEMBL expansion deployed)
**Purpose**: Recommendations for expanding tier1.db with high-quality biomedical data sources
**Current State**: 464 objects, 1260 morphisms, 44 FDA-approved Drug→Disease labels, 76% provenance coverage

---

## Current Data Sources in tier1.db

**Existing Sources** (via "noetik_expansion" and other tags):
- **DrugBank**: FDA-approved drugs, drug-target interactions
- **ChEMBL**: Bioactivity database (drug properties, assays)
- **Manual curation**: 44 Drug→Disease treats edges (all with PMIDs)
- **Literature mining**: Protein-disease associations (partial PMID coverage)

**Provenance Status** (2026-05-10, post-ChEMBL deployment):
- ✅ 958/1260 morphisms have provenance (76.0%): 86 PMIDs, 872 ChEMBL/DOI
- ✅ All 44 Drug→Disease treats edges cited (100%)
- ⚠️ 302/1260 morphisms uncited (24.0%): protein-protein, protein-disease edges

---

## Recommended Data Sources for Expansion

### Priority 1: Immediate High-Impact Sources

#### 0. ChEMBL SQLite (chembl.gitbook.io) — ✅ DEPLOYED 2026-05-10

**Status**: ChEMBL expansion deployed as new default tier1.db.

**What was done**:
- Downloaded ChEMBL 36 (5.23 GB) via `chembl-downloader` to `C:\Users\JAMES\.data\chembl\36\chembl_36.db`
- Built importer: `data/drugs/importers/import_chembl_sqlite.py`
- Imported 989 drug-target associations (from `drug_mechanism` table)
- **Fixed drug name normalization** (2026-05-10): Added `normalize_drug_name()` to strip
  pharmaceutical salt suffixes (MESYLATE, HYDROCHLORIDE, DIMALEATE, etc.) and title-case
  names to match base manifest style
- Re-normalized existing imports: 17 Drug→Protein edges now connect to base 78 drugs
- Created and deployed expanded manifest: `data/drugs/tier1_manifest.json` (464 objects, 1260 morphisms)

**Impact**:
- Graph: 195→464 objects, 388→1260 morphisms
- Provenance: 22.2%→76.0% (958/1260 morphisms cited)
- LOOCV AUROC: 0.968→0.974 [0.965, 0.983]
- 17 new mechanistic edges for base drugs (e.g., Imatinib→ABL1/PDGFRB, Doxycycline→MMP1/7/8/13)

**Documentation**: See `CHEMBL_NORMALIZATION_2026-05-10.md` for technical details.

**API**: No API needed — local SQLite queries via `chembl-downloader` package.

---

#### 1. OpenTargets (opentargets.org)

**Why**: Best comprehensive drug-target-disease database with genetic evidence.

**What it provides**:
- 50,000+ drug-target-disease triples
- Genetic evidence scores (GWAS, rare variants)
- Clinical trial outcomes
- Known drug mechanisms
- All data has evidence provenance

**Data structure**:
- Drug → Target (proteins/genes)
- Target → Disease
- Evidence strength scores (0-1)
- Aggregates 20+ databases (including ChEMBL, ClinicalTrials.gov, PheWAS)

**Integration plan**:
```python
# Pseudocode
import opentargets_client

# 1. Query for all drug-target associations
drug_targets = client.get_drug_targets(min_score=0.7)

# 2. Add to tier1_manifest.json
for dt in drug_targets:
    objects.append({
        "name": dt.drug_name,
        "type": "Drug",
        "provenance": "opentargets_2026"
    })
    morphisms.append({
        "source": dt.drug_name,
        "target": dt.target_gene,
        "name": "inhibits" or "activates",  # from mechanism
        "confidence": dt.score,
        "provenance": f"OpenTargets:{dt.evidence_id}"
    })

# 3. Rebuild tier1.db
python data/drugs/build_tier1.py --manifest tier1_manifest.json
```

**Expected impact**:
- +30,000 morphisms (drug-target edges)
- +5,000 objects (new proteins/genes)
- Improved mechanistic path coverage (more Drug→Protein→Disease chains)
- Stronger provenance (all edges have evidence IDs)

**API**: Free, REST API, Python client available

---

#### 2. STRING (string-db.org)

**Why**: High-confidence protein-protein interaction network.

**What it provides**:
- 24 million protein-protein interactions
- Confidence scores (0-1000)
- Evidence types (experimental, database, text mining, co-expression)
- PMIDs for experimental evidence

**Data structure**:
- Protein A → Protein B (undirected, but can model as bidirectional)
- Combined score (recommended: use only combined_score > 700 = high confidence)

**Integration plan**:
```python
# Filter for high-confidence human PPIs only
ppi_data = string.get_interactions(species=9606, score_threshold=700)

for ppi in ppi_data:
    morphisms.append({
        "source": ppi.protein_a,
        "target": ppi.protein_b,
        "name": "interacts_with",
        "confidence": ppi.combined_score / 1000,  # Normalize to [0,1]
        "provenance": f"STRING:{ppi.evidence_sources}",
        "metadata": {"pmids": ppi.pubmed_ids}
    })
```

**Expected impact**:
- +500 morphisms (for proteins already in tier1.db)
- Improved composition paths (more intermediates for Drug→Protein→Protein→Disease)
- Boost YonedaPatternStrategy (more morphism profiles)

**API**: Free, downloadable bulk files, REST API

---

### Priority 2: Validation & Evidence Sources

#### 3. ClinicalTrials.gov

**Why**: Real-world clinical trial outcomes for temporal validation.

**What it provides**:
- 450,000+ clinical trials
- Drug-disease pairs with trial outcomes (success/failure)
- Trial start dates (for temporal holdout validation)
- Phase I-IV data

**Use case**:
- **Temporal validation**: Hold out trials started after 2020, score with pre-2020 graph
- **Outcome validation**: Do our high-scoring predictions correlate with trial success?
- **Contraindication detection**: Failed trials = negative labels

**Integration plan**:
```python
# Query for completed trials with results
trials = clinicaltrials.search(status="COMPLETED", has_results=True)

for trial in trials:
    if trial.outcome == "SUCCESS":
        # Add as positive Drug→Disease with trial date
        morphisms.append({
            "source": trial.drug,
            "target": trial.disease,
            "name": "treats",
            "confidence": 0.9 if trial.phase == "PHASE_4" else 0.7,
            "provenance": f"ClinicalTrials:{trial.nct_id}",
            "metadata": {"trial_date": trial.start_date, "phase": trial.phase}
        })
```

**Expected impact**:
- +1,000 Drug→Disease pairs (expand positive set from 44 to 1,000+)
- Temporal validation dataset (2010-2015 train, 2016-2020 test, 2021+ holdout)
- Better statistical power (more positives)

**API**: Free, REST API, bulk XML downloads

---

#### 4. DisGeNET (disgenet.org)

**Why**: Largest gene-disease association database.

**What it provides**:
- 1.1 million gene-disease associations
- Evidence scores (0-1)
- PMIDs (for most associations)
- Disease ontology mapping (UMLS, DO, ICD)

**Integration plan**:
```python
disgenet_data = disgenet.get_gene_disease_associations(min_score=0.4)

for gda in disgenet_data:
    morphisms.append({
        "source": gda.gene_symbol,
        "target": gda.disease_name,
        "name": "driver_of" if gda.score > 0.7 else "associated_with",
        "confidence": gda.score,
        "provenance": f"DisGeNET:{gda.source}",
        "metadata": {"pmids": gda.pmids}
    })
```

**Expected impact**:
- +2,000 Protein→Disease morphisms (complete more mechanistic paths)
- Improved provenance (PMIDs for protein-disease links)
- 302 uncited morphisms → ~100 uncited (70% reduction)

**API**: Free for academic use, REST API, downloadable TSV

---

### Priority 3: Enrichment & ADMET (Track B Future)

#### 5. Reactome (reactome.org)

**Why**: Curated biological pathways with drug-pathway-disease links.

**What it provides**:
- 2,600+ curated pathways
- Drug → Pathway associations
- Pathway → Disease associations
- Hierarchical pathway structure

**Use case**:
- Add "Pathway" as new object type
- Drug → Pathway → Disease indirect paths
- Operadic decomposition (pathway = tree of reactions)

**Expected impact**:
- +100 Pathway objects
- +1,000 morphisms (Drug→Pathway, Pathway→Disease)
- Improved ToposLogicStrategy (more evidence for partial paths)

---

#### 6. TTD - Therapeutic Target Database (db.idrblab.net/ttd/)

**Why**: Focused on drug targets with clinical trial info.

**What it provides**:
- 3,100+ targets
- 36,000+ drugs
- Clinical trial statuses
- Target-disease relationships

**Expected impact**:
- +500 Drug→Target morphisms
- Validation dataset (TTD clinical trials vs our predictions)

---

#### 7. SIDER (sideeffects.embl.de)

**Why**: Side effects for contraindication detection.

**What it provides**:
- 140,000+ drug-side effect pairs
- Frequency data
- MedDRA ontology

**Use case**:
- Add "SideEffect" as new object type
- Drug → SideEffect morphisms
- Contraindication logic: if Drug_A → SideEffect_X and Disease_B → contraindicated_by_SideEffect_X, then Drug_A NOT for Disease_B

**Expected impact**:
- +500 SideEffect objects
- +5,000 morphisms
- Negative label generation (contraindications)

---

## Integration Workflow

### Step 1: Extend tier1_manifest.json

```json
{
  "version": "2026-06-01-expanded",
  "sources": [
    "opentargets_2026",
    "string_v12",
    "clinicaltrials_2026",
    "disgenet_v8"
  ],
  "objects": [
    ... existing 195 objects ...
    ... new objects from sources ...
  ],
  "morphisms": [
    ... existing 388 morphisms ...
    ... new morphisms from sources ...
  ]
}
```

### Step 2: Write Import Scripts

Create `data/drugs/importers/`:
- `import_opentargets.py`
- `import_string.py`
- `import_clinicaltrials.py`
- `import_disgenet.py`

Each script:
1. Query API or download bulk file
2. Filter (confidence thresholds, human-only, etc.)
3. Map to tier1_manifest.json format
4. Add PMIDs/provenance
5. Append to manifest

### Step 3: Rebuild tier1.db

```bash
python data/drugs/build_tier1.py --manifest data/drugs/tier1_manifest.json --output data/drugs/tier1.db
```

### Step 4: Re-run Benchmarks

```bash
python validation/repurposing_benchmark.py --view full_typed --protocol loocv --ci --baselines
```

**Acceptance criteria**:
- AUROC ≥ 0.96 (current baseline 0.968; shouldn't drop with more data)
- AUPRC improves (current baseline 0.496; more mechanistic paths should help)
- Provenance coverage > 50% (currently 22.2%)

### Step 5: Update Audit

Re-run audit checks:
```bash
python audit_db_check.py
python audit_mechanistic_paths.py
python audit_pmids.py
```

---

## Expected Final State (After Priority 1+2)

**Before** (current):
- 195 objects
- 388 morphisms
- 86 cited (22.2%)
- 44 Drug→Disease positives

**After** (with OpenTargets + STRING + ClinicalTrials + DisGeNET):
- ~10,000 objects (5,000 proteins, 100 pathways, 4,500 new drugs, 400 diseases)
- ~50,000 morphisms
- ~30,000 cited (60% coverage)
- ~1,000 Drug→Disease positives

**Impact on benchmarks**:
- LOOCV: more positives → tighter CIs, higher statistical power
- External validation: larger overlap with Hetionet, DrugBank
- Temporal validation: 2010-2020 training set, 2021+ test set
- Provenance: 60% cited vs 22% (publication-ready)

---

## Data Quality Checklist

Before adding any source to tier1.db:

- [ ] **License check**: Can we use it? (Academic? Commercial?)
- [ ] **Provenance**: Does it have PMIDs or evidence IDs?
- [ ] **Confidence scores**: Does it provide reliability metrics?
- [ ] **Versioning**: Is it versioned? Can we reproduce builds?
- [ ] **Update frequency**: How often is it updated?
- [ ] **Species**: Human-only or filtered for human?
- [ ] **Ontology mapping**: Does it map to standard ontologies (UMLS, DO, Gene Ontology)?
- [ ] **Audit trail**: Can we trace every edge to a source?

---

## Timeline Recommendation

**Week 1-2**: OpenTargets integration
- Import drug-target data
- Add to manifest
- Rebuild + benchmark
- Expected: +30k morphisms, AUROC stable

**Week 3**: STRING integration
- Import high-confidence PPIs
- Expected: +500 morphisms, AUPRC +0.05

**Week 4**: ClinicalTrials.gov integration
- Import completed trials with results
- Temporal validation dataset
- Expected: +1000 positives, temporal AUROC 0.95+

**Week 5-6**: DisGeNET integration
- Import gene-disease associations
- Complete mechanistic paths
- Expected: Provenance 60%, 302 uncited → 100 uncited

**Month 2**: Optional (Reactome, TTD, SIDER for Track B prep)

---

## Questions for Prioritization

1. **What's the timeline?** Quick (1 month) or thorough (3 months)?
2. **What's the goal?** Publication (need provenance) or internal tool (speed)?
3. **Track B timeline?** If Track B is 6+ months out, defer SIDER/Reactome.
4. **Compute budget?** Larger graph = slower queries. Need to optimize?

**My recommendation**: Start with **OpenTargets only** (week 1). If AUROC stable and provenance improves, continue with STRING → ClinicalTrials → DisGeNET.

---

**Author**: Claude (Anthropic AI)
**Date**: 2026-05-06 (updated 2026-05-06)
**Status**: ChEMBL integration in progress; other sources pending

## ChEMBL Integration Status

**ChEMBL 36** has been downloaded (5.23 GB SQLite at `C:\Users\JAMES\.data\chembl\36\chembl_36.db`)
and an importer built (`data/drugs/importers/import_chembl_sqlite.py`).

**Results**: 989 curated drug-target associations imported into `data/drugs/tier1_manifest_chembl.json`
(464 objects, 1377 morphisms). Database built as `data/drugs/tier1_chembl.db`.

**Problem found**: ChEMBL drug names are uppercase with salt forms (e.g., "IMATINIB MESYLATE")
while our graph uses title-case base names ("Imatinib"). The 989 new edges connect to
drugs NOT in our 78-drug set, so LOOCV AUROC is unchanged (0.968).

**Next step**: Add a drug name normalization step to the importer that maps ChEMBL names
to our existing 78 drugs. This would add PMIDs and new protein targets for our current drugs,
potentially improving mechanistic path coverage and provenance.

**Next step for other sources**: Approve Priority 1 sources, write import scripts
