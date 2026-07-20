# Scorer Remediation Following Q11 — 2026-07-20

Fixes for the three root causes found by the Q11 blind run
(`docs/Q11_BLIND_RESULT_2026-07-20.md`), developed and validated on
**independent and development pairs**, followed by the single authorized Q11
regression re-run and Q11's demotion.

## Headline: the honest reading of the regression

| | Q11 first (blind) | Q11 after fixes (regression) |
| --- | ---: | ---: |
| Correct answers (of 40) | **23** | **23** |
| Wrong answers | 13 | **10** |
| Abstentions / skips | 4 | **7** |
| Accuracy on evaluated | 63.9% (36 eval) | 69.7% (33 eval) |
| MCC | 0.278 | **0.401** |
| Brier | 0.279 | **0.220** |
| ECE | 0.177 | **0.151** |

**The number of correct answers did not change.** Four genuine fixes were gained
and four previously-"correct" answers became honest abstentions:

Gained: `S8+Cu_foil` FP→TN (collector veto), `PEEK+Water` FN→TP (curated uptake
data), `CMC+Water` and `Bi2Te3+Ni` SKIP→TP (role threading, cross-domain routing).

Lost to abstention: `PS+Acetone`, `PC+Acetone`, `PDMS+Toluene`, `PMMA+Toluene`.
These were right **only because a constant 0.45 fell below threshold and the
labels happened to be "incompatible"** — the base-rate artifact Q11 exposed.
Converting them to abstentions is an epistemic gain even though the score is flat.

What genuinely improved is the quality of the answers that *are* given: errors
fell 13→10 and MCC rose 0.278→0.401. **Accuracy-on-evaluated rising 63.9%→69.7%
is partly a shrinking denominator and must never be quoted on its own.**

## Fix 1 — polymer/solvent: a missing intent, not an inverted formula

**Original diagnosis was wrong and is corrected here.** The polymer/solvent path
was deliberately answering the **dissolution** question ("can this solvent
dissolve/process this polymer"), which is what binder-slurry work needs
(PVDF+NMP, CMC+water). For that question Hansen matching is the correct tool and
the existing behaviour was right — as this bridge's own tests assert.

The defect: **resistance intent was unrepresentable.** Both questions share one
interface and the same measurement answers them in *opposite* directions, so
chemical-resistance questions were answered with the dissolution model. PTFE and
POM read as failures against toluene/acetone precisely because those solvents
*cannot* dissolve them — which is the definition of resistance.

Implemented in `polymer_bridge/interface_validator.py`:

- `SOLVENT_RESISTANCE_INTERFACE_ROLES` / `SOLVENT_DISSOLUTION_INTERFACE_ROLES`.
  **Dissolution stays the default**, so all existing behaviour and tests are
  preserved; resistance must be requested explicitly.
- Water (either intent) is answered from curated per-polymer
  `water_absorption_pct` — **verified 7/7** against established outcomes
  (PTFE/PEEK/HDPE/PP/PVC resist; PA6 hygroscopic; CMC dissolves).
- Organic solvents under resistance intent **abstain**
  (`PolymerInterfaceScore.not_assessed`), because no validated model exists.

### Why abstention rather than an Ra-based resistance score

Measured over 30 polymer/solvent cases with established outcomes, Hansen
distance alone separates resistance from attack at only **22/30** for the best
possible single threshold. The counterexamples are physically explicable and not
fixable by moving it:

| pair | Ra | outcome | why Ra fails |
| --- | ---: | --- | --- |
| PTFE + toluene | 3.88 | resists | highly crystalline fluoropolymer |
| PPS + toluene | 3.28 | resists | semi-crystalline high-performance |
| CMC + water | 22.3 | dissolves | ionic/H-bonding dominates |
| PA6 + water | 34.2 | absorbs | amide H-bonding dominates |

Resistance depends on crystallinity, Tg/Tm versus service temperature, and
specific interactions that a cohesive-energy distance cannot capture. Inventing
an Ra-based resistance score would have replaced one wrong answer with a
differently-wrong one while looking confident. A validated organic-solvent
resistance model is **tracked future work**, not something to approximate.

`NotAssessedError` was added to the audit path so an abstention is recorded as a
skip and can never be reported as a confident "incompatible" — the same disease
already fixed in the PFAS path ("zero coverage is no longer converted to 0.5").

## Fix 2 — battery current-collector chemistry vetoes

The five component scorers reason about the **electrochemical window**. Two
dominant collector failure modes are not electrochemical oxidation and were
therefore invisible, so a collector scored identically whether it was the correct
or the catastrophic choice.

Added to `battery_bridge/interface_validator.py` as physical vetoes that
annihilate the composite (same principle as the MOF pore and Flory-Huggins
vetoes):

1. **Li-Al alloying** — aluminium lithiates below ~0.3 V vs Li/Li+, so it fails
   against any electrode whose `voltage_window.lower` is below that. Grounded in
   the existing per-material voltage data, which is why it correctly spares
   **LTO** (1.0–2.5 V): commercial LTO cells legitimately use aluminium on both
   electrodes.
2. **Sulfide corrosion of copper** — sulfur-bearing chemistries convert Cu to
   Cu₂S. Implemented as a general rule on parsed formula elements (with a proper
   symbol parser so `Si` is never read as sulfur), so it generalizes: it fires
   for `Li3PS4+Cu_foil` as well as `S8+Cu_foil`.

Validated **12/13** on independent established cases. The one miss
(`Si+Cu_foil`) is caught by the *pre-existing* mechanical veto for silicon's
~300% volume expansion — defensible physics, and left untouched rather than
weakened to make a test pass.

## Fix 3 — cross-domain routing

Four Q11 pairs were skipped with "Unknown material" although the partner
material lives in another bridge **and a dedicated cross-domain scorer already
exists** (`glass_metal.py`, `metal_semiconductor.py`).

`audit/run_audit.py` now tries the declared domain **first** and only re-resolves
on a genuine name-resolution failure (`_is_unresolved_material_error`, kept
deliberately narrow so real scoring errors still propagate).

The ordering matters and cost one iteration to learn: a first attempt
re-resolved pre-emptively from the material registry, which maps each material
to a *single* domain even though many live in several bridges. That rerouted
`AlN+TiN` (ceramic **and** semiconductor) and `Al_foil+Si` (battery **and**
semiconductor) and broke two development pairs. Try-declared-first preserves
every pair that already worked.

Also fixed in `oracle/compatibility_service.py`: `resolve_workflow_domain` had no
glass+metal or polymer+glass case and fell through to an **order-dependent**
composite string; both are now explicit and the fallback is sorted.

The polymer branch also never passed `interface_role`, so the role-aware gate
documented on 2026-05-31 was unreachable from the audit path. Now threaded.

## Remaining known gaps (unfixed, deliberately)

- `Bi2Te3+Cu` and `Bi2Te3+Ni` still score **identically (0.600)**: the
  metal-semiconductor scorer does not model interdiffusion, so it cannot tell a
  diffusion barrier from a diffuser. Routing was fixed; the *model* gap remains.
- `Al_foil+LiTFSI` still scores identically to `Al_foil+LiPF6` (0.837): salt
  identity does not affect collector passivation scoring.
- `S8+LiPF6` still FP: polysulfide/carbonate nucleophilic attack is not modeled.
- Prediction remains **non-monotonic in score** (`Ni+Fe` 0.721→incompatible vs
  `Al+Fe` 0.674→compatible): a veto changes the verdict without changing the
  surfaced number.
- Ceramic co-sintering reactivity (`Hydroxyapatite+ZrO2_YSZ`) and glass/metal CTE
  sealing (`Kovar+FusedSilica`) produce wrong verdicts.

These were left alone rather than patched toward Q11's labels.

## Verification

- Development benchmark: **41/41, Brier 0.095, 0 skips — unchanged.**
- `polymer_bridge` + `battery_bridge` + `audit/tests`: **174 passed.**
- Full bridge/integration suite: 1256 passed, 5 failed — all 5 **pre-existing**,
  verified by stashing only the four changed files and re-running (bio/
  repurposing DB-hash drift, unrelated to compatibility).

## Dataset roles after this work

- **Q11 → `spent_diagnostic`.** Its 63.9% first run remains the only genuine
  blind compatibility number it will ever produce. The 69.7% regression is
  **not** a blind claim.
- **Q12 → `current_blind`, UNSCORED.** 36 pairs, **12 contrast groups**, zero
  overlap with all 525 prior benchmark pairs. Contrast groups are the direct
  lesson from Q11: a constant fallback cannot pass two pairs sharing a material
  whose correct answers are opposite.
- **Q10** remains sealed and has still never been consumed.
