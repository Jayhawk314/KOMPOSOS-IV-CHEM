# MLIP (CHGNet) Oracle Integration — 2026-07-20

A pretrained machine-learned interatomic potential is now available as a **typed
intermediate oracle**, sitting between the composition-only KOMPOSOS surrogate
(~ms, formula in) and real DFT (`oracle/dft_integration.py`, terminal).

**Headline: on materials where a structure is available, the MLIP is 3× more
accurate than the composition surrogate on formation energy** (MAE 0.134 vs
0.404 eV/atom on 294 held-out materials) — but it requires a 3D structure the
surrogate does not, so it is an added tier, not a replacement.

- Module: `oracle/mlip_integration.py`
- Benchmark: `python audit/run_mlip_benchmark.py --relax --json audit/mlip_benchmark_report.json`
- Tests: `tests/test_mlip_integration.py` (9 tests)
- Install: `pip install chgnet` (optional; weights ship in the package, works offline)

## Typing: an MLIP is a surrogate OF DFT, never DFT

CHGNet is trained on MPtrj to reproduce Materials Project GGA/GGA+U (PBE)
energies. It is therefore typed `Family.SURROGATE` / `Provenance.SURROGATE`,
**never** `Family.DFT`. Labelling an MLIP number "DFT" is exactly the
precise-looking liability `core/level_of_theory.py` exists to prevent.

Crossing to the MP-PBE reference requires the explicit `MLIP_TO_PBE_MP`
conversion, which adds the model's own energy error (0.03 eV/atom) rather than
pretending the lift is free. `test_conversion_to_pbe_adds_uncertainty_and_does_not_shrink_it`
pins that.

If no backend is installed the oracle raises `OracleUnavailable`. It never falls
back to the composition surrogate while keeping an MLIP label.

## Capability boundary: a structure is required

The composition predictor answers from a formula. The MLIP cannot — it needs
atomic coordinates. `predict_formation_energy` raises rather than inventing a
structure. This is why the MLIP is a **tier**, not a replacement: callers holding
only a formula must stay on the surrogate tier.

This bites immediately in practice: the local MP cache (103,644 entries) stores
lattice parameters and space groups but **no atomic coordinates**, so structures
cannot be reconstructed for arbitrary entries. Of 103,644 MP entries only **759**
have a prototype fully determined by (space group, stoichiometry, lattice
constant) — rocksalt, zincblende, CsCl, fluorite, cubic perovskite. Prototypes
with a free internal parameter (rutile *u*, wurtzite *u*, spinel *u*, corundum
*z*) are **excluded rather than guessed**; inventing coordinates would fabricate
the input.

## Formation energies need fitted elemental references

CHGNet returns a *total* energy per atom in its own reference, so
`E_f = E_total − Σ xᵢ μᵢ`. The chemical potentials μᵢ are **fitted by least
squares** against known formation energies rather than assumed, because
elemental ground states (O₂, N₂, S₈, white P) are not all constructible crystals.

That fit is a calibration, so `fit_elemental_potentials` takes an **explicit
training list** — it will not choose its own split — and the benchmark fits on a
train split and evaluates on a disjoint test split.

An element is only identifiable if it appears in enough training materials;
under-covered elements are excluded rather than fitted to noise. Skipping this
check was the first bug found (below).

## Two harness bugs found before trusting any number

Both were caught by the train residual, which is the diagnostic that separates
"the model is bad" from "my harness is bad".

**1. Underdetermined fit → MAE 7.04 eV/atom.** The first run fitted 63 elemental
potentials from 60 training materials. More unknowns than equations: the normal
equations were rank-deficient and the potentials were meaningless. CHGNet's true
error is ~0.03 eV/atom, so a 7 eV/atom result was self-evidently the harness.
Fixed with an element-coverage requirement (≥3 training materials per element).

**2. Unrelaxed idealized structures → train residual 0.670 eV/atom.** After fix 1
the test MAE was 0.727 but the **train residual was 0.670** — the fit reproduced
its own training data almost as badly as held-out data. That rules out
overfitting and extrapolation and points at the inputs. Two causes: scoring ideal
prototypes at MP's lattice constant without relaxation, and assigning perovskite
A/B sites **alphabetically** (which put Hf on the A-site of KHfO₃ — a physically
wrong crystal, predicted −0.294 vs truth −2.943).

Fixes: relax with the MLIP before scoring (`relax_structure`; an MLIP energy is
only meaningful at a minimum of that same potential), and assign the perovskite
A-site to the larger cation. Train residual fell **0.670 → 0.136**.

## Result

Full run over all 759 constructible prototypes with relaxation
(`python audit/run_mlip_benchmark.py --relax`), MP PBE formation energies as
ground truth, elemental potentials fitted on the train split (445 materials, 76
covered elements) and evaluated on a **disjoint** test split:

| model | n | MAE (eV/atom) | RMSE | median |
| --- | ---: | ---: | ---: | ---: |
| **CHGNet MLIP** (relaxed, needs structure) | 294 | **0.134** | **0.238** | **0.076** |
| KOMPOSOS surrogate (formula only) | 294 | 0.404 | 0.530 | 0.349 |

- The MLIP is closer on **228 of 294 materials (77.6%)**.
- **3.0× lower MAE**, 4.6× lower median error.
- Train residual 0.117 (n=445) — close to the test MAE, so the fitted references
  generalize rather than overfitting.
- Neither model skipped any test material.

Artifacts: `audit/mlip_benchmark_report.json`,
`audit/mlip_benchmark_full_2026-07-20.txt`.

The pilot run at `--limit 200` gave MAE 0.150 vs 0.345 on n=39 — same conclusion
at a fifth of the sample, which is a mild check that the result is not a
split artifact.

### What this must NOT be compared to

**Not the 0.416 eV/atom headline.** That figure is the 179-material strict
formula-LOO benchmark (`audit/run_predictor_accuracy.py`) over a different, more
chemically diverse material set, and the composition surrogate needs no
structure there. This benchmark is cubic fully-determined prototypes only. The
honest like-for-like comparison is the table above — same materials, same ground
truth, both models — which is why the surrogate is re-scored here (0.345) rather
than quoting its number from elsewhere.

## What is and is not established

**Established:** on 294 held-out constructible cubic prototypes with relaxation,
CHGNet cuts formation-energy MAE ~3× versus the composition surrogate; the
oracle is correctly typed, refuses to fabricate when unavailable, and refuses to
extrapolate over elements without a fitted reference.

**Not established:** performance on non-cubic or low-symmetry structures, on MOFs
or molecular systems, or on the 179-material reference set (which cannot be run
without structures). No claim that the MLIP improves *any* downstream
KOMPOSOS verdict — it is not yet wired into Crystal Dreamer, the discovery
workbench, or the compatibility path. Wiring it in is deliberately a separate
change, so that this measurement stands on its own.

**Also unchanged:** every existing benchmark. The MLIP is additive and optional;
dev compatibility remains 41/41 and the formation-energy predictor is untouched.
