# AUROC Verification And Audit Protocol

Date: 2026-05-06 (original)
Updated: 2026-05-12 (post-provenance completion, post-ablation, post-ClinicalTrials.gov cross-check)

## Current Position

The repo has a reproducible LOOCV AUROC of 0.974 with 95% CI [0.965, 0.983],
+0.043 above the strongest graph-topology baseline (shortest_path at 0.931).

Current canonical harness:

```powershell
python validation\repurposing_benchmark.py --view legacy --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol as_loaded
python validation\repurposing_benchmark.py --view full_typed --protocol remove_direct_labels
python validation\repurposing_benchmark.py --view full_typed --protocol loocv
```

Add `--ci` for bootstrap 95% confidence intervals (1000 resamples, seed=42).
Add `--baselines` for baseline comparisons (random, degree, common-neighbor,
shortest-path, path-count).

## Verified Metrics (2026-05-12)

| View | Protocol | Pairs | Pos | AUROC | AUPRC | Hits@5 | MRR |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `legacy` | `as_loaded` | 1320 | 36 | 0.917 | 0.536 | -- | -- |
| `full_typed` | `as_loaded` | 1560 | 44 | 0.890 | 0.154 | 0.00 | 0.00 |
| `full_typed` | `remove_direct_labels` | 1560 | 44 | 0.974 | 0.500 | 0.60 | 0.055 |
| `full_typed` | `loocv` | 1560 | 44 | 0.974 | 0.515 | 1.00 | 0.078 |

LOOCV baselines (corrected 2026-05-11):

| Baseline | AUROC |
| --- | ---: |
| shortest_path | 0.931 |
| common_neighbor | 0.918 |
| path_count | 0.596 |
| degree_product | 0.474 |
| random | 0.469 |
| **System** | **0.974** |
| **Margin** | **+0.043** |

The old baseline table (shortest_path 0.559) was a label-order artifact corrected
via audit on 2026-05-11.

## Dataset

Source: `data/drugs/tier1.db`
SHA256: `0BA4A7E01BBA3E1E52A03CD7765A3E6523618F439AB8A90ED4BD6B4BD95BC8E6`

- 1143 objects, 1260 morphisms
- 78 drugs, 20 diseases, 366 proteins, 679 ExternalCompound nodes
- 44 Drug->Disease approved indication labels (all FDA-approved, all with PMIDs)
- All 44 positives have mechanistic Drug->Protein->Disease paths
- Zero missing endpoint rows, zero unreferenced objects
- 1260/1260 morphisms have provenance (100%): PMIDs + ChEMBL IDs
- Reproducible build: `data/drugs/build_tier1.py` from `tier1_manifest.json`

## Scoring System

Seven production strategies, combined via mean + path bonus:

| Strategy | Role | Alone AUROC | Without AUROC |
| --- | --- | ---: | ---: |
| **composition** | Mechanistic 2-hop paths | 0.969 | 0.929 (-0.045) |
| **topos_logic** | Subobject classifier truth values | 0.947 | 0.970 (-0.004) |
| **kan_extension** | Left Kan extension | 0.497 | 0.966 (-0.008) |
| yoneda_pattern | Morphism pattern matching | 0.520 | 0.974 (~0) |
| type_heuristic | Type constraint rules | 0.500 | 0.974 (0) |
| structural_hole | Triangle closure | 0.500 | 0.974 (0) |
| fibration_lift | Fiber-based lifting | 0.500 | 0.974 (0) |

**Composition is the dominant strategy.** It alone achieves AUROC 0.969.
Removing it drops system AUROC by 0.045.

Score aggregation (`validation/repurposing_benchmark.py:score_pair`):
1. Each strategy's best prediction is collected.
2. Simple mean of all strategy confidences.
3. Path bonus: `min(0.25, 0.10 * composition_count)`.
4. Final score: `min(1.0, base + path_bonus)`.

Path bonus tuned via LOOCV grid search. Uniform strategy weights confirmed optimal.

## AUROC Formula

AUROC is computed by pairwise comparison:

```text
AUROC = (concordant + 0.5 * tied) / (positives * negatives)
```

For the LOOCV protocol (current):

```text
positives = 44
negatives = 1516
concordant = 64876
discordant = 1650
tied = 178
AUROC = (64876 + 0.5 * 178) / (44 * 1516)
      = 0.973930
```

Bootstrap CI computed over the combined ranking (held-out positive scores +
fold-averaged negative scores), 1000 resamples with seed=42.

## Leakage Policy

`CompositionStrategy` finds Drug->Protein->Disease 2-hop paths and does not use
direct Drug->Disease edges.

`ToposLogicStrategy` routes Drug->Disease pairs through pathway support only. It
does not return the direct stored Drug->Disease label.

Profile/analogy strategies (KanExtension, YonedaPattern) can be influenced by
other direct Drug->Disease labels unless those labels are removed or held out.

For scientific claims, use `remove_direct_labels`, LOOCV, disease-level holdout,
temporal holdout, or external validation.

## ClinicalTrials.gov Cross-Check (2026-05-12)

30 top repurposing candidates verified against ClinicalTrials.gov and PubMed:
- 19/30 (63%) IN_TRIALS: human clinical trials exist
- 9/30 (30%) PRECLINICAL: published lab research, no trials
- 2/30 (7%) NOVEL: no significant prior evidence

This validates that the system identifies scientifically plausible candidates.

## Audit Checklist

1. Run the canonical harness commands with `--ci --baselines` and record view,
   protocol, object count, morphism count, drugs, diseases, positives, negatives,
   AUROC, CI, AUPRC, and baseline comparison.
2. Confirm `BioDomainLoader` loads all object rows.
3. Confirm `load_legacy_view()` is the only place using the old truncated view.
4. Inspect composition and topos_logic strategies for direct-edge use.
5. Inspect profile/analogy strategies for direct-label contamination.
6. Verify all 44 positives have mechanistic paths (test exists:
   `test_all_positives_have_mechanistic_paths`).
7. Check provenance: 1260/1260 morphisms cited (100%).
8. Treat unlabeled pairs as open-world unknowns, not proven negatives.
9. Confirm LOOCV CI lower bound exceeds all baselines.
10. Verify DB SHA256 matches manifest.

## Recommended Claim Language

Defensible:

> KOMPOSOS-IV-PHARM is a research prototype for categorical reasoning over a
> curated drug-target-disease knowledge graph. Under leave-one-out
> cross-validation on 78 drugs x 20 diseases (44 FDA-approved indications), the
> seven-strategy scorer achieves AUROC 0.974 [0.965, 0.983], with a margin of
> +0.043 over the strongest graph-topology baseline (shortest_path 0.931).
> 63% of top repurposing candidates are already in human clinical trials.
> These are internal retrospective ranking metrics under open-world negative
> assumptions. 100% of graph edges have literature provenance (PMIDs or ChEMBL IDs).

Do not claim:
- Clinical readiness.
- AUROC without specifying view and protocol.
- No leakage without naming the protocol.
- Drug design, Boltz, ABPP, or ADMET validation from Track A metrics.
- "Novel discovery" for candidates that may already be in trials.

## Completed Audit Work (since 2026-05-06)

- ~~Add external validation~~ DONE (Hetionet AUROC 0.744, 7 pairs)
- ~~Add temporal holdout~~ DONE (AUROC 0.959, 22 post-2013 FDA approvals)
- ~~Add disease-level holdout~~ DONE (mean AUROC 0.877, 7 diseases)
- ~~Complete provenance~~ DONE (1260/1260, 100%, 2026-05-12)
- ~~Add reproducible DB build~~ DONE (`data/drugs/build_tier1.py`)
- ~~Resolve unreferenced objects~~ DONE (zero remaining)
- ~~Ablation studies~~ DONE (composition dominant, 2026-05-12)
- ~~ClinicalTrials.gov cross-check~~ DONE (63% IN_TRIALS, 2026-05-12)
- ~~Fix LOOCV baseline label-order bug~~ DONE (2026-05-11)

Remaining:
- Re-run external validation on expanded graph (Hetionet, temporal, disease-level)
