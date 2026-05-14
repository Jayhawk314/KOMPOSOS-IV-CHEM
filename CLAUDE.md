# CLAUDE.md - KOMPOSOS-IV-PHARM

## Project Identity

KOMPOSOS-IV-PHARM applies a categorical AI runtime to pharmaceutical discovery.

Primary long-term purpose: Track B drug design, including molecular generation,
binding/efficacy/safety prediction, ADMET, and patient context.

Current working capability: Track A drug repurposing over a curated
drug-target-disease graph.

Current audit rule: code and live data outrank stale docs. Always name the graph
view and validation protocol with any AUROC.

Author: James Ray Hawkins
License: Apache 2.0 / Commercial dual license
Python: 3.10+

## Read First

1. `CURRENT_STATE.md`
2. `MEMORY.md`
3. `INDEPENDENT_EXTERNAL_AUDIT_2026-05-06.md`
4. This file
5. `TECHNICAL_OVERVIEW.md` (architecture, strategies, validation, limitations)
6. `DATA_EXPANSION_GUIDE.md` (data source recommendations for expansion)

## Track A: Drug Repurposing

Status: working research prototype, not clinical or translational validation.

Data source: `data/drugs/tier1.db`
Reproducible build: `data/drugs/build_tier1.py` from `tier1_manifest.json`

Full typed DB facts (2026-05-12, post-provenance completion):
- 1143 objects, 1260 morphisms
- 78 drugs, 20 diseases, 366 proteins, 679 ExternalCompound nodes
- 44 Drug->Disease approved indication labels (all FDA-approved, all with PMIDs)
- All 44 positives have mechanistic paths (Drug->Protein->Disease)
- Zero missing endpoint rows (679 ChEMBL endpoints now explicit objects)
- Zero unreferenced objects
- 1260/1260 morphisms have provenance (100.0%): PMIDs + ChEMBL IDs
- Zero uncited morphisms remain
- 16/16 original positive-pair mechanistic chains fully cited
- ChEMBL drug names normalized (salt forms stripped, matched to base drugs)
- 17 new Drug->Protein edges added for base drugs via ChEMBL normalization
- DB SHA256: `0BA4A7E01BBA3E1E52A03CD7765A3E6523618F439AB8A90ED4BD6B4BD95BC8E6`

Current canonical harness:

```powershell
python validation\repurposing_benchmark.py --view legacy --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol remove_direct_labels
python validation\repurposing_benchmark.py --view full_typed --protocol loocv
```

Add `--ci` for bootstrap 95% confidence intervals, `--baselines` for baseline
comparisons (random, degree, common-neighbor, shortest-path, path-count).

Current metrics (2026-05-11, post-audit corrections, 44 positives, path bonus tuned):
- `legacy/as_loaded`: AUROC 0.917, AUPRC 0.536
- `full_typed/as_loaded`: AUROC 0.890, AUPRC 0.154
- `full_typed/remove_direct_labels`: AUROC 0.974, AUPRC 0.500
- `full_typed/loocv`: AUROC 0.974, AUPRC 0.515, Hits@5 1.00, MRR 0.078

Path bonus tuned via LOOCV grid search: min(0.25, 0.10 * composition_count).
Uniform strategy weights confirmed optimal by calibrate_loocv.py.

as_loaded protocols show Hits@K regression (now 0.00) because composition skips
existing edges — positives get zero path bonus while negatives can. This is an
artifact of the protocol, not real performance loss. The scientifically valid
protocols (loocv, remove_direct_labels) maintained or improved performance.

LOOCV baselines (AUROC, corrected 2026-05-11):
- strongest: shortest_path 0.931
- system AUROC: 0.974
- margin: +0.043 over strongest baseline

The old baseline table (shortest_path 0.559) was a label-order artifact corrected
via audit. The honest claim is modest improvement over strong graph-topology baselines
plus strategy votes, mechanistic paths, and evidence tracing for triage.

Additional validation (reported but not fully audit-reproduced with executable scripts):
- External (Hetionet): AUROC 0.744 on 7 held-out Hetionet-confirmed pairs
- Temporal holdout (pre/post 2013): AUROC 0.959 on 22 post-2013 FDA approvals
- Disease-level holdout: Mean AUROC 0.877 across 7 diseases (range 0.615-0.996)

Interpretation:
- The legacy AUROC is a historical hurdle only.
- Do not say "no leakage" without naming the protocol and label-removal policy.
- Unlabeled pairs are open-world unknowns, not confirmed negatives.

Benchmark manifest: `validation/repurposing_benchmark_manifest.json`.

Candidate triage CLI:

```powershell
# Disease-first: rank all drugs for a disease
python validation\triage.py Melanoma

# Drug-first: rank all diseases for a drug
python validation\triage.py --drug Sorafenib

# Specific pair: detailed report
python validation\triage.py Melanoma --drug Vemurafenib

# Output formats: --json, --markdown
# Options: --top N (default 10), --all, --db path.db
```

Every report includes: self-check (44/44 approved indications recoverable),
strategy vote breakdown, evidence chains with PMIDs, provenance coverage per
candidate, and APPROVED/NOT_APPROVED labels. NOT_APPROVED means not in our
44 FDA oncology indications (may already be in trials/literature). Detail
auto-expands for top-5 NOT_APPROVED candidates in terminal mode; specific
pair mode always shows full detail.

Provenance tools:
- `validation/triage.py` -- candidate triage reports with evidence chains
- `validation/trace_prediction.py` -- trace any prediction to evidence chains with PMIDs
- `validation/generate_citation_worksheet.py` -- generate citation TODO list
- 1260/1260 morphisms have provenance (100.0%): PMIDs + ChEMBL IDs
- Zero uncited morphisms remain

Data expansion:
- ChEMBL SQLite expansion deployed (2026-05-10): +269 proteins, +872 morphisms, +17 base drug targets
- See `CHEMBL_NORMALIZATION_2026-05-10.md` for details on drug name normalization
- See `DATA_EXPANSION_GUIDE.md` for further expansion recommendations (OpenTargets, STRING)
- Provenance complete (100%, 2026-05-12)

## Track B: Drug Design

Status: long-term goal, not scientifically validated in this repo.

Existing files such as `boltz2_bridge.py` and `abpp_bridge.py` contain
scaffolding, examples, and fallback behavior. Do not use Track A AUROC to claim
Track B readiness.

Track B will need:
- Molecular fragments and scaffold libraries.
- Binding-site geometries and structure prediction.
- SMILES/structure data.
- ADMET and safety data.
- Synthesis routes.
- Ternary complex support.
- Patient/tissue context.
- Design-specific validation metrics.

## Architecture Summary

Core layers:
- Orion/plugin layer: bridge plugins and events.
- KOMPOSOS-IV Category runtime: objects, morphisms, persistence, enrichment, hooks.
- Infinity-cosmos/higher structure: 2-cells, fibrations, Yoneda, Kan extensions.
- COG: claim verification.
- OPTIMUS: categorical refinement/self-correction.

Key code areas:
- `core/`: fused Category runtime and categorical infrastructure.
- `oracle/`: prediction/scoring strategies.
- `domains/bio/`: bio graph loader.
- `data/store.py`: SQLite store API.
- `data/drugs/build_tier1.py`: reproducible DB build from manifest.
- `validation/`: repurposing validation harnesses and candidate triage CLI.
- `validation/triage.py`: candidate triage CLI (disease-first, drug-first, pair detail).
- `tests/`: regression and strategy tests.

## Loader Rule

`KomposOSStore.list_objects()` defaults to `limit=100`. Do not use it without an
explicit limit or pagination when loading production/scientific graphs.

`domains/bio/loader.py::BioDomainLoader` now loads all object rows. The old
first-100-object behavior is preserved only by
`validation.repurposing_benchmark.load_legacy_view()`.

## Scientific Rules

1. Code and database queries outrank docs.
2. Every AUROC must specify view, protocol, pair count, positive count, and label policy.
3. Direct Drug->Disease labels must be removed or held out for stronger claims.
4. Treat unlabeled Drug->Disease pairs as unknown, not confirmed false.
5. Report AUPRC, enrichment@K, Hits@K/MRR, calibration, and confidence intervals before external claims.
6. Require provenance for nodes and edges before treating the graph as publication-grade.
7. Do not represent fallback/mock scientific modules as production capability.

## Current Best Path

1. ~~Freeze evaluation.~~ DONE.
2. ~~Repair data integrity and provenance.~~ DONE (zero orphans, DB build script).
3. ~~Expand positive set and mechanistic coverage.~~ DONE (44 positives).
4. ~~Add external, temporal, disease-level validation.~~ DONE.
5. ~~Tune score combiners.~~ DONE (path bonus tuned via LOOCV grid search, AUROC 0.945→0.968).
6. ~~Build candidate triage CLI with evidence paths, provenance, uncertainty.~~ DONE (`validation/triage.py`).
7. ~~Complete provenance for remaining 302 uncited morphisms.~~ DONE (100%, 2026-05-12).
8. ~~Ablation studies.~~ DONE (composition is dominant strategy).
9. ~~ClinicalTrials.gov cross-check.~~ DONE (63% IN_TRIALS, 30% PRECLINICAL, 7% NOVEL).
8. Expand data sources (ChEMBL SQLite - see `data/drugs/importers/CHEMBL_SETUP.md`).

## Verification

Focused regression:

```powershell
pytest tests\test_repurposing_benchmark.py -q
```

Full suite:

```powershell
pytest tests -q
```
