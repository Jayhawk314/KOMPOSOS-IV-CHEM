# Crystal Dreamer: Data, Representation, and Bayesian Embedding Plan

**Date:** 2026-08-09  
**Status:** Design proposal. The two ideas below have not yet been implemented or validated.

## Purpose

This note documents two related ideas:

1. Improve Crystal Dreamer using battery-relevant data and better material representations, escalating to structure-aware models when geometry is available.
2. Compensate cautiously for sparse voltage and capacity labels using a shared pretrained embedding with separate Bayesian property heads.

The recommended order is data first, Bayesian modelling second. Bayesian uncertainty can expose missing evidence, borrow limited strength from related data, and guide the next calculation. It cannot manufacture voltage or capacity knowledge that is absent from the training data.

## Current observed baseline

The local database has about 103,850 material records, but its target-label coverage is highly uneven:

| Property | All records | Battery records |
|---|---:|---:|
| Density | 103,816 | 12,374 |
| Formation energy | 103,555 | 12,352 |
| Band gap | 59,721 | 10,076 |
| Voltage | 12 | 12 |
| Theoretical capacity | 12 | 12 |
| Ionic conductivity | 7 | not established |
| Volume expansion | 11 | not established |

The central limitation is therefore not database size. It is the scarcity and narrow chemical coverage of consistently defined voltage and capacity labels.

The current retrieval path uses a sparse element-count vector and Euclidean KD-tree distance. This is fast, but raw stoichiometric distance is not a learned measure of chemical similarity. A different database engine or vector database would improve retrieval mechanics, not scientific accuracy by itself.

The current named Crystal Dreamer audit is development/spent evidence, not blind evidence:

- 9 targets assessed; Si skipped because required voltage/capacity labels were absent.
- Property-window recovery: 7/9 (77.78%).
- Exact composition in the top 25: 2/9 (22.22%).
- Near composition in the top 25: 6/9 (66.67%).
- Physical-gate coverage: 2527/2700 (93.5926%).
- 102 decisions were vetoed and 71 were unassessable.
- Report: `audit/crystal_recovery_report.json`.
- Report SHA-256: `3992d0e0abdc09f3359e27dd58a657cc5f51260ed69d1b652c4798c6d4d2963b`.

This shows useful recovery on inspected development targets. It does not establish novel-material quality, structure correctness, experimental performance, or superiority to external systems.

## Idea 1: Better data and representations

### Battery-specific dataset

Build a versioned electrode dataset instead of relying on a general Materials Project summary cache. Each observation should preserve:

- formula, material ID, structure ID, charged phase, and discharged phase;
- working ion, material role, and chemistry family;
- average voltage and voltage profile when available;
- theoretical gravimetric and volumetric capacity;
- experimental capacity kept separate from theoretical capacity;
- calculation method, correction scheme, experimental protocol, and source;
- dataset role: training, development, spent diagnostic, sealed holdout, or external review;
- source and extraction hashes.

Computed and experimental labels must not be silently averaged. Their difference is evidence about fidelity and noise.

The first recommended source is the electrode data underlying the Materials Project Battery Explorer, followed by other sources only when property definitions and provenance can be preserved.

### Representation ablation

Compare all representations using the same frozen data, chemistry-family splits, candidate budget, and physical gates:

| Variant | Representation | Role |
|---|---|---|
| A | Current raw element-count vector | Executable baseline |
| B | Normalized stoichiometry plus group/period features | Cheap correction |
| C | Magpie-style compositional descriptors | Classical formula baseline |
| D | Pretrained formula embedding such as CrabNet or Roost | Learned chemical relationships |
| E | Crystal graph/equivariant model such as CGCNN or CHGNet | Geometry-aware tier |

“Using a tensor” is not itself a scientific improvement. All modern models use tensors internally. What matters is the encoded information, training objective, labelled evidence, applicability range, and frozen benchmark.

### Geometry escalation

Use formula models before a structure exists and structure models only after a defensible structure is retrieved or generated:

```text
formula proposal
  -> composition embedding and broad property estimates
  -> physical and epistemic vetoes
  -> structure retrieval or generation
  -> CHGNet/MLIP relaxation and scoring
  -> DFT or expert-review shortlist
  -> reproducible receipt
```

The repository has an MLIP/CHGNet tier, but it is not currently an audited part of Crystal Dreamer’s return path. Connecting it is a proposed integration requiring a separate benchmark.

## Idea 2: Shared Bayesian embedding

### Model

Use a pretrained shared representation with small, separate Bayesian heads:

```text
z = encoder(composition, optional structure, auxiliary properties)

voltage              ~ p(V | z, chemistry family, fidelity)
theoretical capacity ~ p(C_theory | z, stoichiometric prior)
experimental capacity~ p(C_exp | z, protocol, fidelity)
formation energy     ~ p(Ef | z)
applicability        ~ p(in support | z, labelled neighbourhood)
```

A joint voltage/capacity head may use:

```text
[V, C] | z ~ Normal(mu(z), Sigma_model(z) + Sigma_data(z))
```

Output covariance must be learned and tested; sharing an embedding does not prove that the two targets are correlated.

With only 12 voltage and capacity labels, do not train a large embedding from scratch. Pretrain on abundant auxiliary data or adopt an established representation, freeze most of it, and begin with a small Bayesian linear head or Gaussian process.

### What it can and cannot do

It may:

- borrow representation learning from formation energy, density, band gap, and structures;
- incorporate physical priors;
- share limited strength among related chemistry families;
- widen intervals and abstain where target evidence is sparse;
- select informative DFT calculations or experiments.

It may not:

- turn 12 labels into broad validation;
- record posterior means as observations or pseudo-labels;
- treat formation energy as a substitute for voltage or capacity;
- hide prior-dominated estimates behind a single confidence number;
- extrapolate across chemistry families without an applicability warning.

### Physics-informed priors

Capacity priors can use molar mass, stoichiometry, plausible electron transfer, working-ion content, and material role.

Voltage priors can use redox-active elements, oxidation-state changes, working ion, chemistry family, and charged/discharged phase-energy differences where available.

The UI and receipt must distinguish a physics-derived prior, learned correction, calculated value, and experimental observation.

### Ranking and abstention

Rank by probability of meeting the requested window, not only by posterior mean:

```text
P(voltage in target AND capacity in target)
  * P(required physical gates pass)
  * applicability
```

Each returned candidate should expose:

- posterior mean and 50%, 80%, and 95% intervals;
- nearest labelled chemistry and embedding distance;
- chemistry-family coverage and out-of-distribution status;
- a prior-dominated flag;
- physical vetoes, missing gates, and unassessable gates;
- data, model, calibration, and source hashes;
- expected information gain from a DFT calculation or experiment.

If support is inadequate, the result should be `NOT_ASSESSED` or an explicitly prior-dominated screening estimate.

## Frozen experiment

Compare:

1. Current raw-vector deterministic baseline.
2. Normalized/enriched deterministic baseline.
3. Classical composition descriptors.
4. Pretrained embedding with deterministic heads.
5. The same embedding with independent Bayesian heads.
6. Correlated multi-output Bayesian heads.
7. Hierarchical multi-fidelity heads with physics priors.
8. Structure-aware scoring where structures exist.

Use leave-one-chemistry-family-out, source/time holdouts where possible, and a sealed external set. Random splits alone are insufficient. The existing 7/9 recovery result remains spent development evidence.

Measure:

- MAE and RMSE by property and chemistry family;
- probabilistic scoring and empirical 50/80/95% interval coverage;
- calibration error;
- error versus labelled-neighbour distance;
- abstention risk and retained coverage;
- target-window, exact, and near-composition recovery at fixed K;
- candidate diversity;
- gate coverage, vetoes, and unassessable decisions;
- runtime and cost per surviving candidate.

Adopt a model only if it improves frozen out-of-family performance or probabilistic calibration, abstains sensibly as support decreases, preserves every physical and epistemic veto, and produces a reproducible receipt.

## Recommended implementation order

1. Freeze the current executable baseline and hashes.
2. Define and ingest a battery-electrode dataset with explicit property and fidelity contracts.
3. Freeze chemistry-family development and sealed splits before tuning.
4. Benchmark normalized counts, classical descriptors, and one pretrained formula embedding.
5. Fit a small Bayesian head over the winning fixed representation.
6. Add applicability, prior-dominance, and abstention to backend and UI.
7. Benchmark structure-aware escalation separately.
8. Use expected information gain to select new DFT calculations or experiments.
9. Recompute calibration and drift receipts after each labelled-data release.

Suggested new modules, not yet implemented:

```text
composition_engine/battery_dataset.py
composition_engine/embeddings.py
composition_engine/bayesian_properties.py
composition_engine/applicability.py
composition_engine/structure_escalation.py
audit/run_crystal_embedding_ablation.py
audit/run_crystal_bayesian_calibration.py
```

## Research-value boundary

Researchers may value the combined workflow because it connects generation, physical vetoes, missing-coverage reporting, uncertainty, dataset roles, escalation, and reproducible receipts. The individual ingredients—composition transformers, graph networks, Bayesian surrogates, active learning, and provenance—already exist elsewhere.

The defensible research question is:

> Does preserving physical and epistemic vetoes through a multi-fidelity inverse-design cascade reduce unsupported high-confidence recommendations while retaining useful candidate recall?

That should be tested by comparative ablation. Until then, the safe claim is that the experiment is specified, not that the approach is unique or validated.

## Key references

- [CrabNet](https://www.nature.com/articles/s41524-021-00545-1)
- [Roost](https://www.nature.com/articles/s41467-020-19964-7)
- [Crystal Graph Convolutional Neural Networks](https://arxiv.org/abs/1710.10324)
- [CHGNet](https://www.nature.com/articles/s42256-023-00716-3)
- [Materials Project documentation](https://docs.materialsproject.org/)
- [MatterGen](https://doi.org/10.1038/s41586-025-08628-5)
- [AiiDA provenance concepts](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/concepts.html)
- [NOMAD workflow provenance](https://nomad-lab.eu/prod/v1/develop/docs/explanation/workflows.html)

## Safe and unsafe claims

Safe:

- The two proposed experiments are now specified.
- The current database has broad auxiliary-property coverage but only 12 voltage and 12 capacity labels.
- The Bayesian design is intended to expose uncertainty and abstain where support is missing.
- The current 7/9 result is development/spent evidence.

Unsafe:

- The Bayesian embedding fixes the missing labels.
- Crystal Dreamer accurately predicts real battery performance.
- A tensor or vector database improves the chemistry by itself.
- The shared embedding has been validated.
- Generated formulas are experimentally viable.
- The approach is scientifically unique.
