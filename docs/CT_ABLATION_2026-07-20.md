# Category-Theory Ablation — 2026-07-20

**Result: the categorical layer contributes no measurable predictive accuracy in
the chemistry compatibility path.** Across 374 development + spent-diagnostic
pairs, removing it changes accuracy by 0.0000 and MCC by 0.0000.

This settles an open vulnerability. It does **not** show the architecture is
worthless — it shows the *accuracy* claim was never supported, so it must not be
made. Sell the receipts, not the functors.

Reproduce: `python audit/run_ct_ablation.py --json audit/ct_ablation_report.json`

## Scope and discipline

- Corpus: development (41) + spent diagnostics Q2–Q9 and Q11 (333) = **374 pairs**,
  365 evaluated, 9 skipped.
- **Q12 (current blind) was excluded**, and the script reads the registry to
  block whatever is currently `current_blind` rather than relying on a hardcoded
  filename. Running the ablation on the blind set would spend it.
- Development-grade finding, not a blind result.

## Two CT surfaces, different causal status

The compatibility path contains two distinct categorical surfaces, so they were
ablated separately rather than lumped together.

### B. Yoneda transfer guard / strategy ensemble — reporting only

`build_compatibility_ensemble` (which carries the `yoneda_transfer_guard` and
`typed_morphism` votes) is referenced **only** inside
`_compatibility_decision_metadata`, never inside `_evaluate_pair_in_domain`.
Verified structurally by source inspection, not assumed:

```
ensemble called inside scoring path : False
ensemble called inside metadata only: True
```

It cannot affect score or verdict **by construction**. There is no numeric
ablation to run: this surface is evidence reporting, and the formal Yoneda
presheaf evidence surfaced in vote metadata is exactly that — evidence, not a
predictor.

The same holds in `oracle/compatibility_service.run_compatibility_workflow`: the
ensemble result is stored into `scores["ensemble"]`, while the returned `viable`
comes from the bridge scorer (possibly adjusted by typed morphisms, below).

### A. Typed morphisms — in the causal path, but inert in practice

`_apply_typed_context_score` → `apply_typed_morphism_adjustment` *can* overwrite
both score and verdict (`veto` / `negative_prior` / `positive_prior`), and is
applied on eight domain routes: ceramic, semiconductor, glass, ceramic-metal,
battery-metal, metal-semiconductor, glass-metal, polymer-glass.

Ablated by replacing it with the identity function:

| config | evaluated | skipped | accuracy | MCC |
| --- | ---: | ---: | ---: | ---: |
| baseline (typed morphisms ON) | 365 | 9 | **0.9151** | **0.8298** |
| typed morphisms OFF | 365 | 9 | **0.9151** | **0.8298** |

- Δ accuracy: **+0.0000**
- Δ MCC: **+0.0000**
- pairs whose (score, verdict) changed at all: **1 of 374**
- pairs whose **verdict** flipped: **0**

The single perturbed pair:

| pair | domain | baseline | ablated |
| --- | --- | --- | --- |
| GaN + SiC_4H | semiconductor | 0.760, compatible | 0.750, compatible |

A 0.01 nudge that changed no decision.

## What this does and does not license

**Do not claim:** that category theory improves predictive accuracy, that the
categorical runtime is validated by the benchmark numbers, or that CT explains
the compatibility results. The benchmarks are produced by the domain bridge
scorers. On this corpus the categorical layer is decorative with respect to
accuracy.

**Still defensible:** typed composition, provenance and receipts, transfer
guards, dataset-role discipline, and the veto algebra (physical vetoes that
annihilate rather than dilute — those live in the *bridges*, not the CT layer).
These are architecture and governance claims, and this experiment does not test
them.

**Not tested here:** whether the Yoneda transfer guard prevents bad *transfer*
between domains (it gates transfer, which pairwise scoring never exercises);
whether CT helps in discovery, multi-domain aggregation, or the drug-repurposing
path (`validation/ablation_study.py` covers that separate bio benchmark, which is
currently in a drifted state — its manifest tests fail on a DB hash mismatch
unrelated to this work).

## Caveat on the corpus

The 0.9151 baseline is a development + spent-diagnostic figure and is **not** a
generalization estimate — Q11's blind run scored 63.9% on the same scorers. The
ablation's validity does not depend on that level, since both arms run on the
identical corpus; but the level itself must not be quoted as performance.
