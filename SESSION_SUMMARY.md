# Session Summary - IV-CHEM Audit and Runtime Sync

**Date**: 2026-05-21
**Repo**: `KOMPOSOS-IV-CHEM`
**Status**: audit posture synchronized, Q7 imported, physical grounding corrected

---

## Main outcomes

1. Advanced CHEM audit artifacts were synchronized into `IV-CHEM`.
2. Q5-derived development tuning behavior now matches the advanced CHEM repo.
3. Q7 was copied in as the new frozen blind benchmark and promoted to current blind.
4. Physical grounding WARN was fixed at the plausibility-function layer, not by weakening the audit threshold.

---

## Audit state now

- Development benchmark:
  - `python audit\\run_audit.py --module development`
  - `41/41` evaluated
  - `0` skipped
  - `100.0%` accuracy
  - `Brier 0.103`

- Q6 external blind:
  - retained as spent diagnostic evidence
  - first IV-CHEM run was `35/35`, `100.0%`

- Q7 external blind:
  - file: `audit/external_blind/compatibility_2026_q7.json`
  - SHA256: `e36be9705f91a8a240b91f09fb8016c42ee12270d0a2a779739620a97b265cd9`
  - overlap with prior benchmark identities: `0`
  - first IV-CHEM run:
    - `35/35` evaluated
    - `0` skipped
    - `91.4%` accuracy
    - `balanced 91.6%`
    - `MCC 0.830`
    - `Brier 0.208`
    - protocol pass `true`

- Master audit:
  - Accuracy: PASS
  - Physical grounding: PASS
  - Computational: PASS
  - Integration: PASS

---

## Key code changes

- Restored missing advanced-CHEM scorer behavior:
  - polymer chi facts and known-bad blends
  - battery-polymer cathode-binder penalty for `CMC`/`SBR`
  - ceramic typed morphism for `AlN` + `TiN`
  - Gray coherence ensemble guard

- Restored category/ZFC bridge posture already wired into IV-CHEM:
  - categorical runtime remains primary
  - ZFC remains active as the dual-engine constraint layer
  - bridge scorers, typed morphisms, transfer guards, Gray coherence, and failure-memory gates remain bounded evidence layers

- Fixed physical grounding:
  - `BondConstraint.probability_valid()` now uses normalized Gaussian typicality when empirical `mean/std` exist
  - fallback CDF-centrality remains only for non-empirical distributions

- Fixed master audit summary reporting:
  - removed stale hardcoded `143 pairs / 94.4%` text
  - summary now reports live metrics returned by `run_scientific_audit()`

---

## Why the physical grounding WARN happened

The empirical Si-O stats were fine:
- mean `1.63`
- std `0.03`

The bug was the plausibility mapping. The old central-CDF symmetry score gave only `0.741` at `1.62 A`, even though that bond length is only about `0.33 sigma` from the mean. After switching to Gaussian typicality:
- Si-O plausibility at `1.62 A` = `0.946`
- Si-O plausibility at `2.50 A` = effectively `0.000`

That is the acceptable fix because it preserves the empirical source and corrects the interpretation layer.

---

## Important rule going forward

- `audit/dataset_registry.json` is the source of truth for blind-vs-development roles.
- Q7 is the current blind benchmark.
- If Q7 misses are used for scorer tuning, Q7 becomes spent and Q8 must be frozen before a new blind claim.
