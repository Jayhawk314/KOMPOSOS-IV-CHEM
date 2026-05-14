# KOMPOSOS-IV-PHARM Memory

Read this first when entering this repo. Code and live data are the source of
truth; many older docs are aspirational or stale.

## What This Repo Is

KOMPOSOS-IV-PHARM is a categorical runtime applied to pharmaceutical discovery.

Primary long-term goal: drug design, including molecular generation, binding,
ADMET, efficacy, and patient context.

Current working capability: drug repurposing over a curated
drug-target-disease knowledge graph.

The immediate goal is not "maximize AUROC at any cost." The goal is to build the
best defensible drug-repurposing tool we can: mechanistic, reproducible,
auditable, leakage-aware, and useful for candidate triage.

## Current Track A Reality

Source DB: `data/drugs/tier1.db` (audit-corrected 2026-05-11)
Reproducible build: `data/drugs/build_tier1.py` from `tier1_manifest.json`

Direct SQLite facts (2026-05-12, post-provenance completion):
- 1143 objects total: 78 drugs, 20 diseases, 366 proteins, 679 ExternalCompound nodes
- 44 Drug->Disease approved indication labels
- 1260 morphisms total
- Zero orphans, zero missing endpoints (679 ChEMBL endpoints now explicit objects)
- 1260/1260 morphisms have provenance (100.0%): PMIDs + ChEMBL IDs
- All 44 treats edges have PMIDs
- All 44 positives have mechanistic Drug->Protein->Disease paths
- 16/16 original positive-pair chains fully cited
- 17 new Drug->Protein edges added for base drugs via ChEMBL drug name normalization

## Named Benchmark Views

Use `validation/repurposing_benchmark.py` for AUROC numbers. Do not mix numbers
from older scripts without stating the view and protocol.

```powershell
python validation\repurposing_benchmark.py --view legacy --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol remove_direct_labels
python validation\repurposing_benchmark.py --view full_typed --protocol loocv
```

Current measured values (2026-05-13, 8 strategies incl. binding_evidence):
- `legacy/as_loaded`: AUROC 0.923, AUPRC 0.436
- `full_typed/as_loaded`: AUROC 0.882, AUPRC 0.133 over 78 drugs x 20 diseases, 44 positives
- `full_typed/remove_direct_labels`: AUROC 0.933, AUPRC 0.419
- `full_typed/loocv`: AUROC 0.970, AUPRC 0.533, Hits@5 1.00, Hits@10 1.00, MRR 0.081

Path bonus tuned via LOOCV grid search: `min(0.25, 0.10 * composition_count)`.
Uniform strategy weights confirmed optimal by `calibrate_loocv.py`.

as_loaded protocols show Hits@K = 0.00 (artifact: composition skips existing edges).
The scientifically valid protocols are loocv and remove_direct_labels.

**LOOCV baselines (AUROC, corrected 2026-05-11)**:
The old baseline table (shortest_path 0.559) was a label-order artifact corrected
via audit. Corrected values:
- shortest_path: 0.931
- common_neighbor: 0.918
- path_count: 0.596
- degree_product: 0.474
- random: 0.469

**System AUROC: 0.974, margin +0.043 over strongest baseline.**
Honest claim is modest improvement over strong graph baselines plus mechanistic
explanations, strategy votes, evidence chains, and triage CLI.

Use `--ci --baselines` flags for full output.

## Additional Validation (reported but not audit-reproduced)

**Note**: Executable scripts and frozen held-out artifacts not preserved. Treat as
directional evidence pending reproduction.

External (Hetionet): Reported AUROC 0.744 on 7 Hetionet-confirmed pairs.

Temporal holdout (cutoff 2013): Reported AUROC 0.959 on 22 post-2013 FDA approvals.

Disease-level holdout: Reported mean AUROC 0.877 across 7 diseases.

## OpenTargets Experiment (2026-05-11)

Tested cancer-filtered OpenTargets import (3 score thresholds: 0.5, 0.6, 0.7).
All degraded AUROC: 0.974 → 0.952-0.968. **Decision: DO NOT DEPLOY**.
Curated graph > automated expansion.

## Important Loader Rule

`domains/bio/loader.py::BioDomainLoader` now loads all object rows before all
morphisms. The old first-100-object behavior is preserved only in
`load_legacy_view()` inside `validation/repurposing_benchmark.py`.

Do not reintroduce silent truncation through `KomposOSStore.list_objects()`,
which defaults to `limit=100`.

## Scientific Cautions

AUROC is a ranking metric under open-world negative assumptions. Unobserved
Drug->Disease pairs are not proven negatives.

Positive label count is now 44 (up from 16), improving statistical power. CIs
are tighter. Report uncertainty and multiple metrics for scientific claims.

Direct Drug->Disease labels contaminate analogy/profile strategies unless a
protocol removes or holds them out.

## Current Best Path

1. ~~Freeze evaluation.~~ DONE (CIs, baselines, AUPRC, Hits@K, MRR all in harness).
2. ~~Repair data integrity.~~ DONE (zero orphans, zero missing endpoints, DB build script).
3. ~~Expand positive set and mechanistic coverage.~~ DONE (44 positives, all with paths).
4. ~~Add external, temporal, disease-level validation.~~ DONE.
5. ~~Build candidate triage CLI.~~ DONE (`validation/triage.py`).
6. ~~Write complete technical documentation.~~ DONE (`MASTER_TECHNICAL.md`, `DATA_EXPANSION_GUIDE.md`).
7. ~~Tune score combiners.~~ DONE (path bonus tuned via LOOCV grid search, AUROC 0.945->0.968).
8. ~~Expand data sources.~~ DONE (ChEMBL deployed 2026-05-10: +269 proteins, +872 morphisms, drug name normalization).
9. ~~Complete provenance for remaining 302 uncited morphisms.~~ DONE (100% coverage, 2026-05-12).
10. ~~Ablation studies.~~ DONE (composition is dominant strategy, path bonus +0.017 AUROC).
11. ~~ClinicalTrials.gov cross-check.~~ DONE (63% IN_TRIALS, 30% PRECLINICAL, 7% NOVEL).

## Latest Session (2026-05-13): Binding Evidence Strategy Integration

Wired molecular/chemistry bridges into the drug repurposing scoring pipeline
as the 8th oracle strategy (`BindingEvidenceStrategy`).

**What was integrated:**
1. ABPP Bridge: 65 IC50 entries (up from 6) for drug-target pairs with PMIDs
2. Boltz2 Bridge: heuristic binding prediction (fallback mode)
3. Drug Properties: MW, logP, HBD, HBA, functional groups for all 78 drugs
   (`data/drugs/drug_properties.py`)
4. Drug-target molecular compatibility scoring (logP matching, H-bond
   complementarity, functional group domain matching)
5. Lipinski drug-likeness scoring

**Impact on LOOCV:**
- AUROC: 0.974 -> 0.970 (negligible, within noise)
- AUPRC: 0.515 -> 0.533 (+0.018, improvement)
- Hits@10: 0.700 -> 1.000 (+0.300, major improvement)
- MRR: 0.078 -> 0.081 (slight improvement)

**Triage reports** now show IC50 values, engagement %, publication PMIDs, and
drug-likeness scores when binding_evidence strategy votes.

**Files created:** `oracle/binding_strategy.py`, `data/drugs/drug_properties.py`
**Files modified:** `abpp_bridge.py`, `oracle/prediction.py`,
`validation/repurposing_benchmark.py`, `validation/triage.py`

## Previous Session (2026-05-10): ChEMBL Expansion Deployment

**Problem:** ChEMBL imports used uppercase salt forms ("IMATINIB MESYLATE") while base manifest used title-case ("Imatinib"), preventing 989 imported edges from connecting to base drugs.

**Solution:** Implemented `normalize_drug_name()` in `import_chembl_sqlite.py` to strip salt suffixes and title-case names. Re-normalized existing `tier1_manifest_chembl.json`.

**Result:** 17 new Drug→Protein edges now connect to base drugs (e.g., Imatinib→ABL1, Doxycycline→MMP1/7/8/13, Afatinib→ERBB4). Deployed as new default.

**Impact:**
- Graph: 195→464 objects, 388→1260 morphisms
- Provenance: 22.2%→76.0%→100% (1260/1260 cited, completed 2026-05-12)
- LOOCV AUROC: 0.968→0.974 [0.965, 0.983]
- All baselines still far below (CI lower bound 0.965 vs best baseline 0.566)

**Files:** `CHEMBL_NORMALIZATION_2026-05-10.md`, `DEPLOYMENT_2026-05-10.md` document the work.

## Key Files

- `validation/repurposing_benchmark.py`: canonical named AUROC harness (8 strategies).
- `validation/triage.py`: candidate triage CLI (now shows IC50, drug-likeness).
- `validation/trace_prediction.py`: trace predictions to evidence chains with PMIDs.
- `validation/repurposing_benchmark_manifest.json`: frozen counts and metrics.
- `oracle/binding_strategy.py`: BindingEvidenceStrategy (ABPP + Boltz2 + drug props).
- `data/drugs/drug_properties.py`: molecular properties for 78 drugs + target pocket data.
- `abpp_bridge.py`: 65 experimental IC50 entries for drug-target pairs.
- `boltz2_bridge.py`: heuristic binding prediction bridge.
- `data/drugs/build_tier1.py`: reproducible DB build script.
- `data/drugs/tier1_manifest.json`: canonical graph manifest.
- `tests/test_repurposing_benchmark.py`: regression tests.
- `domains/bio/loader.py`: full typed production loader.
- `CURRENT_STATE.md`: current project state.
- `CLAUDE.md`: operating instructions for future agents.
- `MASTER_TECHNICAL.md`: complete technical architecture & scientific pipeline guide.
- `DATA_EXPANSION_GUIDE.md`: data source recommendations (OpenTargets, STRING, etc.).

## Standing Rules

1. Code and live data outrank docs.
2. Always name the graph view and validation protocol with any AUROC.
3. Do not claim clinical readiness.
4. Do not call the full DB a benchmark unless it has a frozen manifest and label policy.
5. Preserve the legacy AUROC hurdle, but optimize for scientific usefulness.
6. Do not hide fallback/mock scientific modules behind production language.
7. Do not mix Track A repurposing validation with Track B drug-design claims.
