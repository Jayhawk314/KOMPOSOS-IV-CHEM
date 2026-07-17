# Feature Status & Roadmap — honest assessment (2026-05-30)

> **Superseded evidence snapshot.** The 2026-07-17 executable audit corrected the
> formation-energy metrics, compatibility calibration scope, cell-interface
> coverage, workbench charge-balance terminology, and synthesis-planner scope.
> See `CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md`. The text below is retained as a
> historical roadmap, not current product copy.

Goal: value to researchers. We already have **triage value**; **accuracy** is what
would lift it from "useful for ideas" to "useful for decisions." This report says,
per feature: what it is, how good it actually is, what's *checkable fact* vs
*modeled estimate*, what to do next, and how the UI should reflect it.

The single most useful distinction in this whole system:

> **A claim is only as strong as the ground truth it's checked against, and
> whether the thing being judged is a CHECKABLE FACT or a MODELED PREDICTION.**

That one idea explains why MOF's claims are stronger than Crystal Dreamer's.

---

## Why MOF Designer has stronger claims than Crystal Dreamer

They feel like the same problem (generate candidates, rank them) but they are
**not the same difficulty**, for one reason:

- **MOF quality is judged by checkable facts.** "Does it have ≥2 coordinating
  atoms? Is the valence sane? How close is it to a *real synthesized* linker
  from MOFSimplify/CoRE-MOF?" These are facts you can compute or look up. So MOF
  can be validated against a real corpus (passes ~94% of real linkers, ranks real
  above junk at AUROC 0.88).
- **Crystal Dreamer quality is judged by predicted properties.** "What's the
  voltage / formation energy?" — that requires an *accurate forward model*, and
  ours is rough (formation-energy MAE ~0.47 eV/atom). You can't validate a
  candidate as "good" any better than your property predictor is accurate.

So MOF rests on structure + a real existence corpus; Crystal Dreamer rests on a
property model whose accuracy is the bottleneck. **Making Crystal Dreamer "as good
as MOF" means either grounding its candidates in checkable physics, or making the
forward predictor genuinely accurate (a hard, open problem) — not a quick fix.**

---

## Per-feature scorecard

### PFAS Scanner — STRONGEST / most trustworthy
- **What:** detects PFAS by the OECD 2021 structural definition (CF2/CF3 rule),
  including novel PFAS via name→PubChem→structure.
- **How good:** specificity 100% on a 25-molecule hard-negative panel; 99.5%
  concordance with EPA's structural list; catches novel PFAS by name.
- **Grounded?** Yes — a regulatory definition + a structural fact. Near
  regulator-grade *for detection*.
- **Do next:** **usable alternatives** — run each suggested replacement through the
  compatibility engine against the user's adjoining materials, so the output is
  "PFAS-clean AND compatible with your cell," not just "not PFAS." (The
  PFAS×compatibility combination.)
- **UI:** surface the new detection tiers (exact / brand / structural /
  structural_resolved) and, once built, show replacement compatibility scores.

### Compatibility Checker — physics-grounded triage (the workhorse)
- **What:** 5 physics component scorers (ion transport, electrochemical stability,
  interface chemistry, mechanical/CTE, degradation) + hard electrochemical vetoes,
  across battery/polymer/metal/ceramic/semiconductor/glass + cross-domain.
- **How good:** 77–100% per domain on Q8+Q9 (spent diagnostics, ~115 pairs).
  Genuinely useful triage.
- **Grounded?** The *scorers* are real physics (beyond heuristics). The *limits*:
  the combination weights are hand-set, **confidence is not calibrated (ECE ~0.15)**,
  and there is **no current blind benchmark** (Q8/Q9 are spent).
- **Do next:** (1) **calibrate confidence** — apply the same conformal recalibration
  we just used for formation energy so a 0.8 means ~0.8; (2) freeze a fresh blind
  benchmark and report it; (3) consider learning the combination weights honestly.
- **UI:** already states "confidence is a ranking signal, not a probability" — keep
  that until calibrated, then update.

### MOF Designer — genuinely good at what it claims
- **What:** generates novel linker candidates with exact atom counts; scores them
  through a validated grounded funnel (sanity, ≥2 donors, SAscore, geometry) +
  novelty vs known linkers.
- **How good:** ~94% recall on real held-out linkers, AUROC 0.88 vs raw generator,
  95% recall on the 22-atom claim.
- **Grounded?** Yes, structurally + against a real corpus. **Gap:** real lab
  synthesizability is unproven (no wet-lab).
- **Do next:** the verdicts are good; the honest missing piece is experimental
  validation, which we can't do in software. Keep the "not a synthesis guarantee"
  caveat.
- **UI:** already updated with the validated funnel numbers.

### Composition Predictor — directional, now honest
- **What:** predicts properties (formation energy, voltage, capacity, …) from a
  formula via Kan extension over known materials.
- **How good:** formation-energy MAE ~0.47 eV/atom (rough; DFT-grade is ~0.05).
  Intervals were badly overconfident (50% covered 17%); **now conformally
  recalibrated to honest out-of-sample coverage 51/81/95%.**
- **Grounded?** The uncertainty is now honest; the point values are coarse on novel
  chemistry. Accurate only where dense known neighbors exist.
- **Do next (accuracy):** target-aware neighbors; a better/learned model validated
  by LOO; investigate the `Categorical Ground Truth` tier anomaly (MAE 1.6 on n=2
  — likely a bug). This is the real accuracy frontier.
- **UI:** intervals are now honest (wider) — add a one-line "uncertainty is
  conformally calibrated (out-of-sample 51/81/95%); point values are estimates."

### Crystal Dreamer — an idea generator (frame it as such)
- **What:** inverse design — target properties → candidate compositions, scored by
  the Composition Predictor.
- **How good:** ~78% property recovery on known cathode types (finds *something*
  matching the target); near-composition recovery 67% (only inside dense families
  like NMC); does NOT rediscover exact/isolated compositions. Inherits the
  Predictor's rough point accuracy.
- **Grounded?** It's a search; its trustworthiness = the forward model's accuracy
  (rough) + the new charge-balance hygiene gate.
- **Do next (accuracy):** target-aware anchors (fixes isolated-chemistry misses),
  then forward-model accuracy. Until then, **frame honestly as a lead generator,
  not a quantitative predictor.**
- **UI:** update the banner to: "Inverse-design idea generator — ~78% property
  recovery on known cathodes, honest uncertainty; explore leads, then verify.
  Not a quantitative predictor."

### Cell Designer — inherits compatibility
- Composes compatibility interfaces + finds the bottleneck. As good as the
  compatibility engine per interface. New work needed: validate bottleneck
  identification + the "Optimize" mode (search stacks by predicted energy density
  under compatibility/PFAS constraints — honest objective only).

### MP Explorer / MOF Explorer — reference data, fine
- MP Explorer: real DFT data + Kan-extension *estimates* (kept distinct). MOF
  Explorer: 30 DOI-backed MOFs, retrieval/screening. Both honest as-is.

### Discovery Workbench — composition-first prototype
- Chains inverse design → PFAS → compatibility → synthesis planning. Inherits every
  component's honesty. Frame as triage, not lab-validated design.

---

## Cross-cutting: how the UI should integrate all this

`streamlit_app/validation_status.py` is the single source of truth for per-domain
claims — keep it that way; never hardcode a number in a page.

Recent changes to reflect in the UI:
1. **Composition Predictor** — note the conformally-calibrated honest intervals.
2. **Crystal Dreamer** — replace generic "unvalidated screening" with the specific
   "idea generator, 78% property recovery, honest uncertainty, not quantitative."
3. **PFAS** — show the structural detection tiers; later, replacement compatibility.
4. **Compatibility** — keep the "not a probability" caveat until calibrated.
5. Keep one **plain-English "how good / trust it for" line per feature** so a
   researcher never has to read AUROC/MAE to know what they can rely on.

---

## Recommended priority (most researcher value first)

1. **Compatibility confidence calibration** — the workhorse; the conformal trick we
   just proved on formation energy transfers directly. Makes its confidence
   trustworthy. High value, low risk.
2. **PFAS → usable alternatives** (PFAS×compatibility) — turns detection into
   actionable, compatible replacements. Direct researcher value.
3. **Crystal Dreamer / Predictor point accuracy** — the real accuracy frontier
   (target-aware anchors first; then a better validated model). Harder.
4. **UI banner pass** for the recent calibration/recovery changes.
5. **Battery Optimize mode** — now stands on a calibrated forward model.

Bottom line: today the system is a **research triage + idea-generation toolkit**
with honest uncertainty — strongest at PFAS detection, MOF generation, and
compatibility triage. The path to "decision-grade" runs through **calibration**
(cheap, high-trust) and **forward-model accuracy** (hard, the real frontier).
