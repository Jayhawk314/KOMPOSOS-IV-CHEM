# Crystal Dreamer Search Ablation - 2026-08-09

## Evidence status

This is development/spent self-consistency evidence. The nine assessed targets
were already inspected, and both target windows and candidate property values
come from the same forward predictor. The comparison measures candidate-search
behavior only. It does not measure voltage or capacity accuracy, blind
generalization, experimental performance, phase stability, or synthesis.

## Question

Does Crystal Dreamer's union of perturbation, interpolation, substitution, and
stoichiometry search add value over simpler candidate-selection baselines under
the same target windows, top-K rule, physical gates, and 300-evaluation budget?

## Data coverage discovered

- Local battery-domain entries: 12,378.
- Entries with both voltage and theoretical-capacity labels: 12.
- Materials Project entries with both labels: 0.
- Direct Materials Project voltage/capacity filtering: NOT_ASSESSED because the
  required labels are absent from the local MP summary cache.
- Si: skipped because the forward predictor does not supply both target values.

The direct labelled-record baseline therefore has only 11 eligible records per
target after strict holdout removal.

## Compared variants

- Direct filtering over the remaining labelled battery records.
- Hidden-composition nearest neighbour.
- One deterministic random sample from the four-strategy candidate union.
- Perturbation only.
- Interpolation only.
- Substitution only.
- Stoichiometry grid only.
- Four-strategy round-robin union.

The hidden-composition neighbour is an oracle diagnostic. It uses the held-out
target formula and is not available in a real inverse-design request.

## Reproduced results

| Variant | Top-1 property hits | Exact@25 | Near@25 | Mean top-25 diversity | Gate coverage |
|---|---:|---:|---:|---:|---:|
| Direct labelled filter | 5/9 | 0/9 | 4/9 | 0.8127 | 91.92% |
| Oracle composition neighbour | 8/9 | 0/9 | 8/9 | 0.2198 | 97.56% |
| Random union, one seed | 7/9 | 1/9 | 4/9 | 0.3162 | 81.30% |
| Perturbation only | 5/9 | 0/9 | 4/9 | 0.1125 | 91.15% |
| Interpolation only | 7/9 | 0/9 | 4/9 | 0.2315 | 88.78% |
| Substitution only | 7/9 | 1/9 | 5/9 | 0.1607 | 89.96% |
| Stoichiometry only | 7/9 | 4/9 | 6/9 | 0.1259 | 100.00% |
| Four-strategy union | 7/9 | 2/9 | 6/9 | 0.1522 | 93.59% |

All deployable variants missed LTO and Graphite. The oracle neighbour recovered
the property window for LTO but not Graphite.

## Finding

The current four-strategy union did not add property-window recovery on this
spent target set:

- It tied random-union, interpolation, substitution, and stoichiometry at 7/9.
- The 58-formula stoichiometry grid also reached 7/9, achieved more exact
  composition recoveries than the union (4 versus 2), tied near recovery
  (6 versus 6), and had complete charge-gate assessment.
- The union did not beat one deterministic random draw on property hits.
- Direct filtering over the sparse labelled records reached only 5/9.
- The oracle result shows that closer composition retrieval helps on eight
  targets, but it uses unavailable hidden information.

The most defensible interpretation is that the 7/9 headline mainly demonstrates
self-consistency of the forward predictor within familiar battery families.
This benchmark does not demonstrate added value from four-way search
orchestration.

The strong stoichiometry result is not evidence of broad generative ability.
The grid explicitly encodes NMC, olivine, and spinel families that overlap the
spent targets. It is a compact family-template baseline.

## Physical evidence

Per-candidate status remained preserved during the comparison. Aggregate
charge-gate coverage ranged from 81.30% for the single random draw to 100% for
the stoichiometry grid. Unassessable candidates were retained as NOT_ASSESSED;
definite failures were excluded as VETOED.

## Limitations

- The target set is small, inspected, and chemically concentrated.
- The property objective is defined by the same predictor used for ranking.
- Only one deterministic random seed was run; this is not a random-baseline
  distribution.
- Candidate-pool sizes differ, although prediction evaluation is capped at 300.
- The direct labelled filter is limited by only 12 total labelled records.
- The oracle baseline is intentionally non-deployable.
- Exact and near recovery are secondary diagnostics, not experimental outcomes.

## Decision

Do not claim that the four-strategy union outperforms simple search. Do not use
this result to justify a Bayesian model.

Before investing in new search or representation machinery:

1. Obtain an externally supplied target or known failure case.
2. Freeze the target and expected evaluation before inspecting outcomes.
3. Repeat the comparison across multiple random seeds.
4. Separate family-template recovery from genuinely out-of-family proposals.
5. Run the evidence-presentation A/B study with per-candidate status.
6. Define the battery-electrode data contract before model development.

The existing union may remain as a diversity mechanism, but its incremental
value is currently NOT_ESTABLISHED.

## Reproduction

From the repository root:

    python -u audit\run_crystal_search_ablation.py

Artifact:

- Report: audit/crystal_search_ablation_report.json
- Report SHA-256:
  5bb4541a45c336efc6560e587cb72fae5155da080a6b34f9c3a723315855392b
- Script SHA-256:
  976eb3a6e200d3338eb66cc6f7bf4ba6a94d3680c88a023723aed5d1986aaff8
- Evidence role: development_spent
- Random seed: 20260809
