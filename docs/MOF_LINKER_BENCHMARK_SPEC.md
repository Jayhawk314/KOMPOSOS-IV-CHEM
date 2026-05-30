# MOF Linker Generator — Validation Benchmark Spec (v0)

Status: design approved 2026-05-29. Substrate verified present on disk
(MOFSimplify 274 real linkers loaded; CoRE-MOF 2019 zips in `data/external/core_mof/`).

## 1. The question it answers

*"Does the funnel produce 22-atom linkers that are indistinguishable from real
synthesized linkers by every checkable signal — and does it pass real linkers it
has never seen?"*

This is the measurable form of the Kulik challenge. It validates the
**scorer/funnel**, which is what lets us attach honest confidence to generated
candidates.

**What it does NOT prove:** that a specific novel linker is wet-lab
synthesizable. A high score means "indistinguishable from real linkers on every
computable axis," not "guaranteed makeable." This sentence must appear in the
report.

## 2. Datasets (all local)

- **Positives:** MOFSimplify real linkers (274 loaded; 18-26 heavy atoms; **49 at
  exactly 22**) + CoRE-MOF 2019 (`data/external/core_mof/*.zip`, needs import pass).
- **Label axes:**
  - *Synthesizability* = "appears in a synthesized MOF" (binary, both sources).
  - *Stability* = MOFSimplify thermal/solvent labels (`data/cache/mofsimplify_stability.json`) — richer, optional second axis.
- **Provenance:** keep CSD refcode + source per linker.

## 3. Splits (the integrity core)

- Split **by MOF refcode, not by linker** (a linker shared by two MOFs must not
  straddle the split).
- **Seed half** -> feeds the generator and any threshold tuning.
- **Eval half** -> never seen by generator or tuning. Recall is measured here.
- **Freeze the eval split to a SHA-256 before the first run** (same discipline as Q10).

## 4. Negatives / decoys (positives-only data needs these for AUROC)

Three decoy classes, reported separately:

1. **Generator-raw** — the generator's output *before* gating. The most honest
   test: can the funnel separate reals from its own guesses? If yes, the funnel
   earns its place.
2. **Property-matched random** — random valid molecules at matched heavy-atom
   count (so the classifier cannot cheat on size).
3. **Perturbed-real (hard)** — real linkers with a coordinating group
   broken/scrambled. Tests subtle non-linker-ness.

## 5. The funnel under test (each gate grounded, not self-graded)

- **G1 — Chemical sanity (hard reject):** RDKit sanitize, valence, PAINS/Brenk,
  strained rings, protonation correction.
- **G2 — Coordination topology (hard):** >=2 recognized coordinating groups
  (carboxylate / azolate / pyridyl / phosphonate ...).
- **G3 — Synthesizability proxy:** SAscore (Ertl), threshold tuned on **seed
  only**; optional SCScore/RAscore.
- **G4 — Geometry (survivors only):** 3D-embed, check donor-donor distance/angle
  for ditopic/tritopic suitability.
- **G5 — Precedent (coordinate, not a gate):** max Tanimoto to the **seed**
  corpus -> novelty axis.

## 6. Metrics

- **Per-gate recall on held-out reals** (funnel chart). A gate that rejects more
  than ~5% of real synthesized linkers is miscalibrated, not the linkers. Headline
  honesty check.
- **AUROC / AP:** reals vs. each decoy class, overall **and restricted to 22 atoms**.
- **Enrichment factor @ top-k.**
- **Calibration (ECE)** if the funnel emits a probability.
- **Novelty-validity frontier:** for generated 22-atom candidates, plot
  max-Tanimoto-to-real vs. gates-passed -> quantifies "**novel AND linker-like**".

## 7. Integrity rules

- Eval split hashed before running; no threshold ever tuned on eval.
- Dedup CoRE-MOF against MOFSimplify (overlap check) before splitting.
- Report decoy classes separately (generator-raw is the meaningful one; random is
  a sanity floor).

## 8. Honest threats to validity (state in the report)

- Positives-only -> AUROC depends on decoy realism; generator-raw decoys are the
  fair test, random ones inflate the number.
- SAscore/SCScore are themselves heuristics/ML proxies — cite them, do not claim
  wet-lab ground truth.
- Geometry from a single conformer is approximate.

## 9. Deliverables

- `mof_bridge/benchmark/` harness; frozen `eval_split.json` + `.sha256`;
  `linker_corpus.json` (unified, deduped, provenance).
- A report: per-gate recall, AUROC table (by decoy class, +/-22-atom), novelty
  frontier, and the plain-English "what this does/does not prove" paragraph.

## 10. Phasing

- **P0** Import CoRE-MOF from the on-disk zips; dedup with MOFSimplify; build
  unified corpus.
- **P1** Freeze refcode-level seed/eval split + hash.
- **P2** Build the three decoy sets.
- **P3** Implement the 5 grounded gates.
- **P4** Run recall + AUROC + 22-atom claim + novelty frontier -> report.
- **P5** *Only then* wire the funnel into the MOF Designer UI, replacing the
  self-graded verdicts with grounded ones + the novelty coordinate.
