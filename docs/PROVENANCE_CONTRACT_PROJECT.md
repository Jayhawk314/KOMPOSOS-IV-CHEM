# Provenance Contract: a communication layer between user, model, and tools

Status: side-project design and CHEM/Noesis integration contract

## The failure this is meant to prevent

An LLM assessed application pages it had not opened. The primary failure was not
tone, intelligence, or confidence calibration. It was **epistemic authorization**:
the model emitted an assessment whose required evidence event did not exist.

Natural language hides this because claims and connective prose have the same
surface form. A fluent unsupported judgment can look stronger than a clumsy
measured result. The layer should therefore make claims typed objects before they
become sentences.

## Claim object

```json
{
  "claim_id": "sha256:...",
  "subject": "streamlit_app/pages/11_Synthesis_Planner.py",
  "predicate": "implements",
  "object": "formal element-balance checks",
  "scope": "encoded curated routes",
  "modality": "observed",
  "evidence_role": "derived_check",
  "evidence_refs": ["receipt:read-file", "receipt:run-stoich-audit"],
  "confidence": 1.0,
  "calibration_cohort": null,
  "freshness": "2026-07-17T...Z",
  "vetoes": [],
  "producer": "model-or-tool-id"
}
```

Evidence roles should be finite and visible: `measured`, `source_record`,
`derived_check`, `screening_model`, `simulation`, `development_benchmark`,
`external_holdout`, `model_memory`, and `not_assessed`.

## Rules enforced before rendering prose

1. An artifact assessment requires a matching read/trace receipt for that artifact.
2. A performance claim requires a benchmark receipt, dataset role, dataset hash,
   executable command, and result artifact.
3. `verified` requires evidence hashes that can be rechecked now.
4. A conclusion's evidence role and confidence cannot exceed the weakest required
   premise without an explicit transformation justified by a calibration record.
5. A hard physical veto or epistemic veto survives composition.
6. Missing required support produces `ORPHAN`/`NOT_ASSESSED`, not a low-looking
   numeric score that can be averaged away.
7. Contradictory evidence produces `CLASH`; changed but still in-tolerance artifacts
   produce `TENSION`; supported agreement produces `AGREE`.
8. The renderer chooses language from the verified type. It may say "the file name
   suggests" for model-memory inference, but may not say "the feature is".

The same typing applies to the user side: `question`, `constraint`, `preference`,
`hypothesis`, `observation`, and `assumption`. This does not police the user; it
prevents an unstated preference or hypothesis from becoming a shared fact.

## Drift is not one number

Noesis can help, but prediction drift must be split into distinct contracts:

- **software/artifact drift:** code, model, or calibration hash changed;
- **benchmark drift:** frozen inputs now produce materially different metrics;
- **calibration drift:** predicted intervals/probabilities lose empirical coverage;
- **coverage drift:** more requested cases become unknown, skipped, or proxy-only;
- **data drift:** input distribution changes relative to the calibration cohort;
- **outcome drift:** later measurements disagree with earlier predictions.

Noesis's generic AERO persistence/refusal machinery can represent the state
transitions and receipts. A jet-specific numeric drift baseline should not be
reused as if it were chemistry calibration.

## Implemented CHEM seam

This repair pass adds:

- `api/monitoring_export.py`: stable JSON exports for composition predictions,
  pairwise compatibility workflows, and prediction drift;
- `audit/baselines/prediction_baseline_2026-07-17.json`: frozen current strict-LOO
  development baseline and artifact hashes;
- `audit/prediction_drift.py`: `AGREE`/`TENSION`/`CLASH`/`ORPHAN` evaluation with a
  content-addressed receipt;
- regression tests for deterministic receipts and visible metric drift.

The current baseline evaluates to `AGREE`. That means the executable behavior
matches a frozen development benchmark. It does **not** mean the predictor is
experimentally validated.

## Noesis bridge

`noesi-base` already has the right receiver shape: it invokes CHEM in an isolated
child process, keeps CHEM's native interface verdict separate from its Gray
reasoning-coherence state, and writes canonical hashed receipts to a ledger. It
also correctly notes that CHEM's historical ZFC summary is derived from the same
scorer output and is not an independent measurement.

The next integration should consume the stable CHEM exports rather than import
private Python objects. Noesis should:

1. verify the receipt hash and schema;
2. store the native CHEM payload unchanged;
3. attach reasoning-coherence and temporal state as a separate record;
4. compare receipt sequences for drift;
5. refuse to upgrade `screening_model_estimate` into measurement or external
   validation;
6. surface missing coverage and proxy distance as veto-bearing evidence, not notes.

## MVP beyond CHEM

The smallest useful standalone project is:

1. JSONL claim and action-receipt stores;
2. a verifier that builds a support graph and emits the four reasoning states;
3. adapters for file reads, test runs, web citations, and domain tool responses;
4. a renderer that turns verified types into allowed language and badges;
5. a calibration log mapping confidence expressions to observed frequencies;
6. an audit view showing exactly which premise authorized each sentence.

The key product is not a better confidence adjective. It is a contract in which
an unsupported assessment is mechanically unable to masquerade as an observed
one.
