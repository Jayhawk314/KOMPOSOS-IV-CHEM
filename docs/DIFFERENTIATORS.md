# What makes KOMPOSOS-IV-CHEM different

## One-sentence description

KOMPOSOS-IV-CHEM is a reproducible materials-screening workbench that keeps
physical vetoes, evidence roles, calibration scope, provenance, and missing
interface coverage attached to its answers.

## Defensible differentiators

### Evidence roles are part of the result

Development data, spent diagnostics, sealed holdouts, source records, derived
checks, model estimates, and simulations are not interchangeable. The dataset
registry and monitoring receipts make those roles machine-readable.

### Vetoes survive composition

A pore-access failure, immiscibility rule, charge-balance failure, PFAS detection,
or missing required physical-interface scorer cannot be rescued by averaging a
different score. This applies to epistemic gaps as well as physical failures.

### Calibration is scoped

The runtime pairwise path uses a 98-row development/spent isotonic artifact
(artifact OOS ECE 0.0549, Brier 0.0337). A broader post-squash five-fold study
reports OOS ECE 0.070 and Brier 0.068, while Q11 blind ECE was 0.177. These
measurements use different cohorts and procedures. The system explicitly does
not apply the pairwise artifact to arbitrary multi-interface aggregates.
Formation-energy intervals have their own calibration record.

### Constraints plus a grounded referee

The MOF workflow deterministically enforces exact heavy-atom count and then uses
a separately benchmarked structural funnel. On the frozen benchmark it reproduces
0.9433 pass-all recall on held-out real linkers and AUROC 0.8843 against raw
generator output. That is screening evidence, not a synthesis claim.

### Inspection surfaces are first-class

MP and MOF explorers are not just presentation pages: they let users distinguish
source data from derived estimates, inspect nearest-composition anchors, and see
the evidence coverage behind downstream predictions.

### Stable external monitoring

Content-addressed JSON exports let an external system such as Noesis record native
CHEM predictions without upgrading their evidence role. Frozen metric and artifact
baselines distinguish software drift from model accuracy.

## What is not a differentiator claim

- The repository does not prove it is the only system with these properties.
- It does not contain an ablation showing category theory increases accuracy.
- Historical ZFC summaries derived from bridge scores are not independent
  measurements.
- A current strict formation-energy LOO MAE of 0.416 eV/atom is screening-grade.
- No compatibility benchmark is currently blind.
- Whole-cell and workbench aggregates are not calibrated probabilities.

The category-theory implementation matters as reusable structure for typed
composition and constraints. The public value claim should rest on observable
behavior and reproducible audits, not mathematical vocabulary by itself.
