# Handoff + Standing Rules (2026-05-29)

Written to let a fresh session (and Codex/Gemini) start from honest, validated
ground without re-reading a very long multi-agent transcript. Read this first.

Two repos are in play:
- **KOMPOSOS-IV-CHEM** — materials/chemistry compatibility + design (the live product).
- **KOMPOSOS-IV-CHEM-TB** — Track B drug-design engine (separate; triaged, see below).

---

## THE THREE STANDING RULES (carry these forward; don't relitigate)

1. **Claims are per-domain and must show uncertainty.** Never headline one global
   accuracy number. Every accuracy claim — in docs *and* in the UI — states the
   domain and a calibration/uncertainty figure (ECE/Brier or a confidence band).
   No marketing slogans ("avoids hallucinations", "verifiable synthetically",
   "research-grade") unless a blind number backs them.
2. **Q10 is the sealed final exam.** Do not score it until the polymer model is
   declared final. Its labels are independent, cited, and hashed *before* the
   single prediction run. Q8 and Q9 are spent diagnostics, not blind claims.
   Never tune the model to a benchmark's specific pairs (teaching-to-the-test).
3. **Keep the agent roles separated:** design (Gemini) -> implement+test (Codex)
   -> independent validation pass that checks for teaching-to-the-test and
   over-claiming (the role Claude played this cycle). Don't let the builder also
   author the test answers or the value claims.

---

## VALIDATED STATE — chem compatibility engine

**Honest capability is per-domain (Q8+Q9, ~115 blind-ish pairs, real verdicts):**
- Metals, ceramics, semiconductors, and all cross-domain interfaces: **77–100%.**
  This is genuinely useful triage today.
- Single-domain glass: **coverage gap** (Soda_Lime, Cabal-12 missing from DB).

**Polymer blends — fixed this cycle (was the weak domain at 40–50%).**
- Codex integrated a real Flory-Huggins χc/MW model (`polymer_bridge/flory_huggins.py`)
  from Gemini's `G-docs/FLORY_HUGGINS_DESIGN.md`. Independently matches the
  diagnosis Claude reached.
- **Integrity-checked and clean:** of Q10's 8 polymer pairs, 6 resolve via general
  physics (Hansen/χc); the 2 curated (HDPE+PS χ=1.0, PMMA+PS χ=0.04) use real
  textbook constants, not reverse-engineered labels; the 3 empirical overrides
  (ABS/PC, PEEK/PTFE, PPS/PTFE) are spent-Q9 blends. **Not teaching-to-the-test.**
- Verification: polymer tests **111 passed**; **Q9 (now spent) 35/40 = 87.5%**,
  TP27/TN8/FP1/FN4, AUROC 0.9247, AP 0.9745, Brier 0.0987, ECE 0.1486. Remaining
  Q9 errors are NOT polymer-blend errors (Li_metal/PVDF, Li3PS4/Li, TiN/WC,
  SS316/Cu, CdTe/ZnO).

**Calibration is still imperfect** (ECE ~0.15 even after the fix). Confidence
scores are not yet trustworthy as probabilities — surface this in the UI.

---

## OPEN ITEMS (next work, priority order)

1. **Fix the stale dev label, not the physics.** Dev audit is 40/41 only because
   the old dev set labels HDPE+PP *compatible*; HDPE/PP are genuinely immiscible
   and the new χc physics is correct. Change that dev label to incompatible.
2. **Verify the MW / repeat-unit data behind χc** (`polymer_bridge/material_properties.py`,
   `G-docs/DATA_PROVENANCE_AND_QUALITY.md`). χc depends on it; if those MW values
   are placeholders, 87.5% is luckier than it looks. NOT yet verified.
3. **UI transparency pass (Codex in progress).** Each feature page must show
   per-domain accuracy + uncertainty and the validation status. Do NOT import the
   `G-docs/FEATURES_AND_VALUE.md` marketing language (it over-claims: "avoids
   hallucinations", MOF "verifiable synthetically", no per-domain caveats).
4. **Glass single-domain coverage gap** (add Soda_Lime etc. as general capability).
5. **MOF external validation** — generation hits 100% exact atom-count constraints,
   but real synthesizability is unvalidated (validation packet has no verdicts).
6. **Q10 final exam** — run once *after* the polymer model is declared final.

---

## DRUG ENGINE (KOMPOSOS-IV-CHEM-TB) — triaged, parked honestly

- Pocket detector: validated, **5.4 Å median on held-out co-crystals** (beats
  centroid baseline; generalizes). Graph-native RDKit SMILES ~96% valid. Vina
  docking adapter validated end-to-end on 1M17.
- **The deciding result: active/decoy enrichment AUROC ≈ 0.50** (both box sizes).
  Docking-as-verifier does not rank EGFR binders above decoys. The generative /
  binding-ranking value proposition is **unproven** — an honest dead-end, not a
  bug. Components (pocket finder, docking wrapper, benchmark harness) are reusable.
- Work pushed to origin as branches: `feature/pocket-recovery-benchmark`,
  `feature/graph-native-smiles`, `feature/docking-adapter`,
  `feature/enrichment-benchmark`. Not merged (remote master had diverged).

---

## INTEGRITY ARTIFACTS (Q9 / Q10)

- Q9 pairs SHA256 `7fd3c9cb…`; Q9 labels SHA256 `418e5dc3…` (spent diagnostic).
- Q10 pairs `audit/external_blind/compatibility_2026_q10_pairs_unlabeled.json`
  SHA256 `4d5f6fd4…` (40 pairs, no Q8/Q9 dupes).
- Q10 sealed labels `audit/external_blind/compatibility_2026_q10_labels_hidden.json`
  SHA256 `e1ad2c30…` — labeled by Claude from cited first principles, blind,
  pre-run, 32 compatible / 8 incompatible / 7 flagged borderline. **Keep this
  file out of model-tuning view; do not commit it where the builder will read it
  (gitignore it; the hash is the proof it existed first).**

---

## DO NOT

- Headline a single global accuracy number, or ship marketing claims the blind
  numbers don't support.
- Run the full monolithic pytest tree as a product signal (it pulls in unrelated
  aimo/cyber/OpenTargets/debug modules). Run per-feature shards.
- Tune the model to Q10's pairs, or inspect the sealed Q10 labels during dev.
- Use Track-A/B drug AUROC to claim materials capability, or vice versa.
