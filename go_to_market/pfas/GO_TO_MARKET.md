# PFAS — Go-To-Market: landing the first real user

The rubric (`docs/BOM_SCREENING_RUBRIC.md`) is a good **delivery** playbook for
*paid* engagements (intake → screen → report → price). This file covers the step
*before* that: **how to land the first real user / design partner** without
over-claiming. Different job; complements the rubric, doesn't replace it.

---

## 1. What the desperate buyer actually needs

A company with intentionally-added PFAS does **not** need help *detecting* PFAS —
lists and labs already do that (Layer 1 & 3 in the rubric). Their nightmare is the
next question:

> **"What do I replace it with that won't break my product?"**

That is exactly the gap the current code fills and the older audit docs don't:
**`find_replacements_for_cell`** scores each PFAS-free candidate against the
materials that *remain* in your cell and surfaces the **weakest interface
(bottleneck)**. Detection is commoditized; **cell-aware compatible-replacement
triage is the differentiator.** Lead with it.

No existing platform (Certivo, Assent, GreenSoft, Source Intelligence) answers
"what replaces PVDF *in my NMC811 cell*, and will it hold at every interface?"

---

## 2. Position it honestly (it sells better, and protects you)

A paying company **acts** on the output, so over-claiming is more dangerous here
than with an academic. Pitch exactly what it is:

> "This narrows your replacement candidates and flags the interface most likely to
> fail, so your lab validates the right 3 instead of testing 30. It's a **triage
> accelerator and an auditable screening aid — not a compliance certification and
> not a substitute for your bench tests** (or EPA 533/537.1 lab testing)."

- Compatibility values are **calibrated probabilities** (isotonic, out-of-sample
  ECE ~0.07): a 70% means ~7 in 10 such pairs are compatible — not a black box.
- A *useful* honest result looks like the demo run: *"none of the off-the-shelf
  binders clear your NMC811 cell without a flagged interface — here's which one
  each fails."* That's value, not failure: it tells them where to engineer.

---

## 3. Who to approach (not CEOs)

- **People who feel the deadline:** product stewardship, regulatory/compliance
  managers, R&D reformulation leads — in batteries, electronics, medical devices,
  semiconductors, textiles, automotive.
- **Channel play (best shot for a solo builder):** PFAS-compliance software /
  consultancies already serving these companies do the *reporting* but **not the
  replacement-compatibility piece.** Be the missing module for someone who already
  has the customers and the trust — far easier than cold enterprise sales.

---

## 4. The concrete first move — get ONE design partner

Don't blast a list. Offer one company or consultant:

> "Send me your actual bill of materials with the PFAS components — I'll run
> replacement-compatibility triage on it for **free**, and you tell me where it's
> wrong."

Free, narrow, falsifiable, and it gets you (a) a real user, (b) a real BOM to prove
the tool on, and (c) corrections that make the tool better. One real partner beats
a hundred pitches.

**The deliverable for that offer is `bom_triage.py`** — see `README.md` here.

---

## 5. Honesty backlog (found while building this)

Real items the demo run exposed; fix before charging anyone:

1. **Suspicious pair scores — VERIFIED false negatives, then FIXED (2026-05-31).**
   Root cause: CMC–SBR / CMC–PP scored raw **0.45** (→7% calibrated) because the
   polymer validator's Flory-Huggins **immiscibility veto** fired, but CMC+SBR is
   the industry-standard aqueous binder used *as a dispersion* and CMC/PP merely
   coexist — miscibility is the wrong criterion there.
   **Fix shipped — role-aware gate** (`polymer_bridge/interface_validator.py`):
   `validate(...)` now takes `interface_role`; for coexistence/dispersion roles
   (`COEXISTENCE_INTERFACE_ROLES`) the immiscibility veto is skipped and solubility
   is down-weighted (`PolymerWeights.coexistence_focus`). Role is threaded from the
   replacement's use-case via `_USECASE_TO_INTERFACE_ROLE` in `replacement_scorer`,
   auto-passed by `compatibility_service._call_validator`. Result: CMC–SBR/CMC–PP
   as a binder are now `viable=True`; CMC+SBR's cell bottleneck moved from the bogus
   SBR/PP interfaces to **NMC811** (the legitimate high-Ni concern, a cross-domain
   interface that is correctly *not* gated). Blend veto (HDPE/PP, HDPE/PA6) and the
   dev benchmark (41/41, Brier 0.095) are unchanged; 193 polymer+pfas tests pass.
   _Still TODO:_ score a combined binder like `CMC+SBR` as a unit rather than
   splitting to `CMC` and scoring it against its own `SBR` component.

2. **Calibration low-end resolution (now the dominant distortion).** The isotonic
   calibrator maps raw [0.35–0.55] into a near-flat ~0–8% band, so genuinely
   *viable* interfaces (e.g. PAN–CMC, raw 0.516, `viable=True`) still display ~8%
   and the bottleneck **ranking-by-calibrated-%** is distorted at the low end. Fix:
   refit with more low-score support, and/or rank by raw `total` (or surface raw
   alongside calibrated) below ~0.6. Separate from the gate above.
3. **Replacement registry coverage.** Several candidates (PAA, Alginate, ceramic
   coating, cast iron) aren't in the compatibility registry, so no interface can be
   scored — they land in "manual review." Expanding coverage directly improves the
   triage.
4. **No false-positive / baseline number yet** for the *replacement ranking* (the
   detection side has 100% specificity on a 25-negative panel; the ranking side
   doesn't have its PHARM-grade benchmark). Until a design partner's real BOM gives
   ground truth, frame ranking as triage, not validated recommendation.
