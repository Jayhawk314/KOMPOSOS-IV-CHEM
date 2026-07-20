# Q11 — First Current-Blind Compatibility Result (2026-07-20)

**This is the project's first genuine current-blind compatibility number.**
It is substantially worse than the development and spent-diagnostic figures,
and that gap is the finding.

## Provenance

| Item | Value |
| --- | --- |
| Pairs file | `audit/external_blind/compatibility_2026_q11_pairs_unlabeled.json` |
| Pairs SHA256 | `f16cbbfabe245ee28e3f06133225895d9efd018291bc981306e7ec02c95b9971` |
| Sealed labels | `audit/external_blind/compatibility_2026_q11_labels_hidden.json` |
| Labels SHA256 | `e49f2fbb755969914d5e3dea15e2d76bcc59eb2211b5c84e8be11a71bfc4bcfe` |
| Merged scored file | `compatibility_2026_q11.json`, SHA256 `d3cb14de24244f3a95c2b4d6cca9bdcb84ce99753f53bcba9c793b6bbe9ed925` |
| Result artifact | `audit/q11_blind_result_2026-07-20.json`, SHA256 `093fe0a71012c65883b2c8d4ea291f08539dd09c995687ea06b116dc952a9e41` |
| Console log | `audit/q11_blind_run_2026-07-20.txt` |

Seal order (verifiable in git): the pair list and sealed labels were committed
in `ce739de` **before** any prediction was run. `audit/merge_sealed_labels.py`
re-verifies both hashes and refuses to merge a broken seal.

Reproduce:
```powershell
python audit\merge_sealed_labels.py --period 2026_q11 --check-only
python audit\run_audit.py --module external --external-path audit\external_blind\compatibility_2026_q11.json
```

## Result

| Metric | Q11 blind | Development | Q9 spent diagnostic |
| --- | ---: | ---: | ---: |
| Accuracy | **63.9%** | 100% (41/41) | 87.5% |
| Balanced accuracy | 63.9% | — | — |
| MCC | **0.278** | — | 0.692 |
| Brier | **0.279** | 0.095 | — |
| ECE | **0.177** | — | — |
| Evaluated / skipped | 36 / 4 | 41 / 0 | 40 / 0 |
| Confusion | TP 11, TN 12, FP 7, FN 6 | — | — |
| Protocol pass | **False** (4 skips) | — | True |
| Metric pass | **False** (<85%) | — | True |

Overlap with all prior benchmarks: **0** identities (485 existing name-pairs
checked at freeze time and re-verified by the audit runner).

### What this changes

- The development **41/41** and the ~87–90% spent-diagnostic figures do **not**
  predict blind performance. The honest headline for pairwise compatibility is
  now **63.9% blind on 36 evaluated pairs**, not 100%.
- The isotonic calibrator's reported **5-fold OOS ECE 0.072** does not transfer:
  blind **ECE is 0.177**. The calibration claim should be scoped to
  "dev + spent-diagnostic distribution," not presented as general.

## Root causes (diagnosed on INDEPENDENT pairs, not on Q11)

The Q11 errors are not 13 unrelated chemistry misses. They concentrate in three
mechanisms, each confirmed with non-Q11 probe pairs so the diagnosis does not
consume the holdout.

### 1. Solvent-exposure role inverts the miscibility veto (accounts for all polymer FNs)

`polymer_bridge/interface_validator.py` caps `total` at 0.45 when solubility
matching is poor (`total = min(total, 0.45)`, the "immiscible / no tabulated chi"
veto). `COEXISTENCE_INTERFACE_ROLES` gates that veto off for binder, separator,
coating, seal, liner, etc. — but **`chemical_resistance` / `solvent_exposure`
are not in that set** (even though `chemical_resistant_liner` is).

For a polymer-in-contact-with-solvent interface the relationship is **inverted**
relative to a blend: a solubility *mismatch* is exactly why the polymer resists
the solvent. The scorer treats mismatch as failure.

Independent probe (no Q11 pairs):

```
HDPE+Acetone 0.4500   PP+Acetone  0.4500   PI+Acetone  0.4500
PVC+Acetone  0.4500   ABS+Acetone 0.4500   PEEK+Acetone 0.4500
PI+Toluene   0.4500   NBR+Water   0.4500   PA6+Water   0.4500   PVC+Water 0.4500
HDPE+Toluene 0.9675   PPS+Toluene 0.9027
```

Ten of twelve chemically distinct pairs return the **identical** 0.45. PEEK and
PVC in acetone score the same. The path does not discriminate; where it appears
"correct" on solvent pairs it is correct only by base rate, because 0.45 is below
threshold so everything is called incompatible. The two pairs that escape the
veto (HDPE/PPS + toluene) escape it because their solubility parameters *match* —
scoring them compatible, which is backwards for hydrocarbon swelling.

This is the same disease CLAUDE.md already documents a rule for: *"immiscibility
only means incompatibility for single-phase/blend interfaces."* The rule exists;
the solvent-exposure role just was never added to it.

### 2. Current-collector identity is ignored (battery FPs)

```
Graphite+Al_foil 0.9375   Graphite+Cu_foil 0.9375
LTO+Al_foil      0.9375   LTO+Cu_foil      0.9375
```

The collector metal does not affect the score at all. In Q11 this made
`S8+Cu_foil` (sulfur corrodes Cu to Cu2S) score identically to `S8+Al_foil`
(the correct commercial choice). Likewise the salt-vs-collector chemistry that
distinguishes `Al_foil+LiPF6` (passivates, compatible) from `Al_foil+LiTFSI`
(pits above ~3.7 V) is not represented — both returned 0.837.

### 3. Cross-domain routing produces skips (4 pairs, protocol fail)

`CMC+Water`, `Kovar+FusedSilica`, `Bi2Te3+Cu`, `Bi2Te3+Ni` all failed with
"Unknown material" errors where the material **exists in another bridge's
vocabulary** (CMC is in the polymer bridge; Kovar is in the metal bridge; Cu/Ni
are in the metal bridge). The pair is routed to a single domain and then dies on
the partner material.

Abstaining here is the *safe* behavior and the failure-memory correctly logged
`no_verdict:scorer_unavailable_or_error: 4` rather than inventing a verdict.
But these are exactly the cross-domain interfaces (metal↔glass seal,
semiconductor↔metal contact) that a materials engineer cares about.

### 4. Prediction is not monotonic in score

`Ni+Fe` scored **0.721 → predicted incompatible**, while `Al+Fe` scored
**0.674 → predicted compatible**. A veto path is changing the verdict without
changing the reported score, so the surfaced number does not explain the verdict.

## Why development 41/41 did not predict this (visible in the dev set itself)

This does not require Q11 to see — it is in the development run output:

- **11 of 41 development pairs return the exact same score `0.350`**
  (PA6+ABS, PA66+ABS, PVC+PA6, HDPE+PET, HDPE+PP, BN_hex+SiO2, BN_hex+Borosilicate,
  CMC+LMO, CMC+LFP, ABS+PTFE, PA66+POM) — and **every one of them is labeled
  incompatible**. Further clusters sit at 0.380, 0.250, and 0.180, also all
  labeled incompatible.
- So roughly a quarter of the development set cannot distinguish *"the scorer
  correctly identified incompatibility"* from *"the scorer had no applicable
  model and returned a low constant, which happened to match the label."*

The development set is dominated by pairs whose correct answer is "incompatible,"
which is exactly the answer a low constant fallback produces. Q11 deliberately
included **contrast pairs** — chemically opposite pairs sharing a material
(S8+Cu_foil vs S8+Al_foil; Al_foil+LiTFSI vs Al_foil+LiPF6; POM+acetone vs
PC+acetone) — and those are what broke the illusion: the members of each contrast
pair received **identical scores**.

Design implication for Q12 and for the dev set: **contrast pairs are the highest
information-per-pair test available**, because a constant-fallback scorer cannot
pass them by base rate.

## Audit-tooling defect found and fixed

The external audit reported **"Overlap with existing benchmark identities: 40"**
for Q11 — i.e. 100% overlap, which would have invalidated the holdout. It was
entirely **self-overlap**: `_load_existing_benchmark_identities` excluded only the
merged file under test, not its same-period siblings (the unlabeled pair list a
sealed holdout is merged from). Fixed in `audit/run_audit.py` by excluding the
whole same-period file family. Q11 now correctly reports 0; Q9 correctly still
reports its genuine 16-identity overlap and its unchanged 87.5%.

Any split-format holdout (Q9, Q10, Q11) was affected by this over-report.

## Discipline status — READ BEFORE FIXING ANYTHING

Q11 is **`current_blind`** in `audit/dataset_registry.json`. Under the registry's
own rule, *"if a current_blind dataset is used for tuning or calibration, change
its role to spent_diagnostic and freeze a new blind dataset."*

Seeing these results does not spend Q11. **Remediating against them does.**

The three root causes above were each confirmed on independent probe pairs, so a
fix can be developed and validated without touching Q11. But the moment Q11 is
re-run to demonstrate improvement, that re-run is regression evidence, not a
blind claim, and Q11 must be demoted to `spent_diagnostic` with Q12 frozen.

Recommended sequence:
1. Fix the solvent-exposure role gap, collector-identity blindness, and
   cross-domain routing — validating on independent/dev pairs only.
2. Re-run Q11 **once** as post-fix regression; demote it to `spent_diagnostic`
   in the same commit that records the re-run.
3. Freeze Q12 before making any further blind claim.

**Q10 remains sealed and unscored.** It was not consumed by this work.

## Limitations of Q11 itself (disclosed, not discovered later)

- Labels are **expert judgment from materials-science first principles**, not
  curated external experimental ground truth. One pair (11012, LGPS/LTO) is
  flagged borderline in the sealed file.
- Labels were authored by the **same AI assistant that has worked on this
  codebase**. Sealing and hashing before prediction constrains hindsight, but
  this is weaker independence than an external labeler. Externally supplied
  pairs (the materials-engineer outreach ask) remain the strongest available
  upgrade.
- Pairs reuse **known materials in unused combinations**. Introducing genuinely
  novel materials would have produced Q8-style skip storms, so Q11 tests
  generalization to new *pairings*, not to out-of-vocabulary materials.
- No labels were changed after seeing results, and none should be. The scored
  file is reproducible from the sealed inputs.
