# Q9 Blind Result + Per-Domain Compatibility Breakdown (2026-05-29)

First trustworthy blind validation of the materials-compatibility engine, plus a
per-domain breakdown that shows *which domains are research-grade and which are
not*. Recorded so this diagnosis is not lost.

## Method (why this one is honest)

- **Q9 pair list** was frozen unlabeled first: `compatibility_2026_q9_pairs_unlabeled.json`
  (40 pairs, no labels, no Q8 duplicates). SHA256
  `7fd3c9cb8818b1e0218e556912a133a77808dab5c20a37381a7b3724bb7bf99c`.
- **Labels were assigned from materials-science first principles BEFORE running
  the model** (not copied from model output), then locked:
  `compatibility_2026_q9.json`, labels SHA256
  `418e5dc3a49c3c40277799495f123c571c15079ac25ecf823538455da6c0fb9c`
  (31 compatible / 9 incompatible). Four pairs were flagged borderline at label
  time (Li3PS4/Li, PTFE/PEEK, SS316/Cu, CdTe/ZnO).
- Run once via `audit/run_audit.py --module external`.

This avoids the dev=100%/blind=70% trap: the engine was never tuned to these
pairs, and the labels were not derived from its predictions.

## Q9 result (single blind run)

- **32/40 = 80% accuracy** (full coverage, 0 unscorable — the Q8 coverage gaps
  for SS316 / cross-domain / glass-metal are closed).
- Confusion: TP 27, TN 5, FP 4, FN 4.
- Correctly caught the hard incompatibilities: SS304+Al and Ti6Al4V+Al7075
  (galvanic), Si3N4+YSZ and CP-Ti+borosilicate (CTE mismatch), LGPS+Li (reduction).
- 4 false positives were the concern: **Li_metal+PVDF (0.86)** and the polymer
  blends **HDPE+PP (0.87), PE+PVC, PMMA+PC** — all scored "compatible" when they
  are not.

## Per-domain accuracy (Q8 + Q9 combined, 80 pairs, real audit verdicts)

| Domain | Accuracy (scored) |
|---|---|
| metal-semiconductor (cross) | 100% |
| glass-metal (cross) | 100% |
| polymer-glass (cross) | 100% |
| battery-metal (cross) | 100% |
| battery-polymer (cross) | 93% |
| metal | 88% |
| battery | 83% |
| semiconductor | 83% |
| ceramic | 77% |
| **polymer (single-domain)** | **40% -> 50% after fix** |
| glass (single-domain) | unscored (2 skipped — coverage gap) |
| **OVERALL (scored)** | **83% -> 85% after fix** |

## Polymer weakness — root cause (NOT a small bug)

The polymer bridge already has a Hansen/Flory-Huggins (chi) miscibility model and
a chi-based immiscibility veto, but it fails on real blends because:

1. The veto's fixed `chi >= 0.04` threshold is **wrong physics for high-MW
   polymers**: Flory-Huggins critical chi `chi_c = 0.5*(N_A^-0.5 + N_B^-0.5)^2`
   approaches ~0.001-0.01 for real chains, so HDPE/PP at chi=0.01 *should* be
   flagged immiscible but slips through.
2. The polymer DB has **no degree-of-polymerization / molecular-weight field**,
   so the correct `chi_c` cannot be computed.
3. Several chi values are **missing** (e.g. PMMA/PC), and Hansen solubility
   parameters alone cannot detect crystallinity/entropy-driven immiscibility
   (HDPE/PP have near-identical Hansen parameters yet are immiscible).

### Fix applied (general, regression-clean)
`polymer_bridge/interface_validator.py`: when no tabulated chi exists, fall back
to a solubility-score veto (`solubility < 0.30 -> not viable`), using the same
0.30 threshold `blend_analyzer` already uses. Effect: polymer 40%->50%, overall
83%->85%. **No regressions** (dev audit still 41/41 100%; polymer unit tests
98/98; all other domains unchanged). This catches clearly mismatched pairs
(PE+PVC) but **not** solubility-matched immiscible pairs (HDPE/PP) — by design,
to avoid over-vetoing.

### Real fix (not yet done; do NOT hack to pass Q9)
Add MW / N to the polymer DB -> compute `chi_c` from N -> compare actual chi to
`chi_c` -> fill missing literature chi values (general table, not Q9-specific).
Hard-coding Q9's pairs as immiscible would be teaching-to-the-test and is
explicitly avoided.

### chi_c integration update (Codex, 2026-05-29)

The G-docs polymer prototype is now integrated into production as general
polymer logic:

- Added `polymer_bridge/flory_huggins.py` with symmetric empirical chi lookup,
  Hansen-estimated chi fallback, degree-of-polymerization, and Flory-Huggins
  `chi_c`.
- Added representative repeat-unit MW / typical MW fields to key polymers.
- Added PPO and empirical compatibility overrides for known engineering
  interfaces/blends: PS/PPO, PC/ABS, PTFE/PEEK, PPS/PTFE.
- Updated stale HDPE/PP expectations. With high-MW chains, chi=0.01 still
  exceeds `chi_c`, so HDPE/PP is now rejected as a molecularly immiscible blend.

Focused verification:

- `python -m pytest polymer_bridge\tests -q` -> 111 passed.
- Development audit -> 40/41 because the old HDPE/PP dev label remains expected
  true; this is a label conflict with the new polymer physics.
- Q9 spent diagnostic after chi_c integration -> 35/40 = 87.5%, TP=27, TN=8,
  FP=1, FN=4, AUROC=0.9247, AP=0.9745, Brier=0.0987, ECE=0.1486.

Remaining Q9 errors are no longer polymer-polymer blend errors: Li_metal/PVDF
FP, Li3PS4/Li_metal FN, TiN/WC FN, SS316/Cu FN, CdTe/ZnO FN.

## Honest product framing

- **Closer to research-grade (state per-domain):** inorganic and interface
  compatibility — metals, ceramics, semiconductors, and all cross-domain
  interfaces (77-100%).
- **Improved but still not final-exam validated:** polymer-polymer blend
  compatibility now has a production chi_c/MW model and empirical override
  path. The spent Q9 diagnostic improved to 87.5% overall, but Q10 remains the
  only clean future exam.
- **Do not headline one global score** without the domain breakdown.
- **Coverage gap:** single-domain glass materials (Soda_Lime, Cabal-12) still
  missing from the DB.

## Q10

`compatibility_2026_q10_pairs_unlabeled.json` exists as the future pair file:

- Pairs file: `audit/external_blind/compatibility_2026_q10_pairs_unlabeled.json`
- SHA256: `4d5f6fd414eae277493e6b8f2ceebedfcdb8add6989c910d45959d0ded0c1003`
- Pair count: 40
- Label fields: none (`expected_compatible` is intentionally absent)
- Exact duplicate identities against Q8/Q9: 0

A hidden label file is present but must remain sealed from model-tuning work:

- Labels file: `audit/external_blind/compatibility_2026_q10_labels_hidden.json`
- Labels SHA256: `e1ad2c309443426352a167352ec46cf35f1bd5af6c1fc1b61bacf7826d05501e`
- Codex did not inspect this JSON while updating the docs.

Q10 must stay unscored until the team explicitly decides the polymer model is
ready for a final check. Labels must remain independent, cited, and hashed
before predictions are inspected. Q8 and Q9 are now spent diagnostics, not
future blind claims.
