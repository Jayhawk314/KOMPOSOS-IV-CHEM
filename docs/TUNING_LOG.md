# KOMPOSOS-IV Bridge Tuning Log

*Updated 2026-05-28 - Version IV Categorical Runtime*

---

## 2026-05-29: Research-Grade Compatibility Tuning Status

### Evaluation correction
The development and extended audit sets remain useful regression checks, but
they are not valid headline accuracy claims. The research-grade posture is now
based on blind or blind-like sets only.

### Current compatibility metrics
- Development set: 41/41, 100.0%; regression only.
- Extended curated set: 214/215, 99.5%; regression only.
- Q8 frozen blind: 30/40 evaluated, 70.0% on scored pairs, 10 unscorable;
  TP=13, TN=8, FP=2, FN=7, AUROC=0.700, AP=0.882, Brier=0.259, ECE=0.256.
- Q9 initial blind diagnostic: 32/40, 80.0%, full coverage; TP=27, TN=5,
  FP=4, FN=4.
- Q9 spent diagnostic after chi_c integration: 35/40, 87.5%, full coverage;
  TP=27, TN=8, FP=1, FN=4, AUROC=0.9247, AP=0.9745, Brier=0.0987, ECE=0.1486.
- Q8 and Q9 are now spent diagnostics. Do not tune against them and then report
  their improved scores as fresh blind performance.

### Polymer tuning result
A general polymer solubility veto was added in
`polymer_bridge/interface_validator.py`. It improved the combined Q8+Q9 polymer
slice from 40% to 50% and overall blind-like accuracy from 83% to 85%, with no
movement in other domains. This is a real but marginal improvement.

### Remaining modeling gap
The polymer failure mode is not solved by hard-coded pair rules. The next real
modeling step is to add molecular weight or degree-of-polymerization data and
compute Flory-Huggins critical chi per pair. Until that lands, polymer blend
compatibility should be described as experimental.

### chi_c production integration
Codex integrated the G-docs polymer prototype into production:
`polymer_bridge/flory_huggins.py`, chain-length fields on key polymers, PPO, and
empirical compatibility overrides for PS/PPO, PC/ABS, PTFE/PEEK, and PPS/PTFE.
Focused polymer tests pass: 111/111. Spent-Q9 diagnostic improved to 35/40
(87.5%), AUROC 0.9247, AP 0.9745, Brier 0.0987, ECE 0.1486. Development audit
is now 40/41 because the old HDPE/PP dev label conflicts with the chain-length
chi_c model.

### Sealed future exam
`audit/external_blind/compatibility_2026_q10_pairs_unlabeled.json` contains 40
unlabeled pairs for a later final check. SHA256:
`4d5f6fd414eae277493e6b8f2ceebedfcdb8add6989c910d45959d0ded0c1003`.
A hidden labels file is also present:
`audit/external_blind/compatibility_2026_q10_labels_hidden.json`, SHA256
`e1ad2c309443426352a167352ec46cf35f1bd5af6c1fc1b61bacf7826d05501e`.
Codex did not inspect the label JSON. Do not score Q10 until the team explicitly
decides the polymer model is ready for a final check.

---

## 2026-05-28: STT Category Cache + Formal Evidence Wiring

### Problem
`_try_get_domain_category(domain)` was called independently inside each of the
three STT score functions — building the domain category O(n²) pairwise
validation calls 3× per compatibility query, then discarding it.

### Fix
`build_domain_category(domain)` — public, module-level cached in
`_DOMAIN_CATEGORY_CACHE`. Built once per domain per process lifetime.
Passed explicitly from `build_compatibility_ensemble` to all three STT
strategies.

### Evidence enrichment
`score_simplicial_yoneda` now computes and returns the formal Yoneda presheaf
evidence (sieve distance, presheaf overlap, shared sources with confidences,
proof steps) in vote metadata. `score_fibration_transport` includes per-path
details. `score_rezk_equivalence` includes the full isomorphism witness.

### Impact on scores
**None.** Score formulas are identical. Benchmark: 41/41, 100.0%, Brier 0.095.

### New report module
`reports/compatibility_report.py` — domain-aware narration registry translates
categorical concepts to chemistry-field language for each supported domain.

---

## 2026-05-22: IV-CHEM Synchronization

### Restored Q5 Development Tuning
The categorical runtime copy now matches the advanced CHEM repo on the Q5 development set.

**Restored Fact Sets:**
- **Polymer χ facts**: `PA66/POM`, `ABS/PTFE`, `PEO/PAN`, and `PAN/PEO`.
- **Blend Penalties**: Known-bad combinations for `PA66/POM` and `ABS/PTFE`.
- **Battery-Polymer Context**: Penalty for `CMC`/`SBR` used as cathode binders (correctly identifies them as anode-optimized).
- **Ceramic Morphisms**: Typed morphisms for `AlN` + `TiN` (wide-bandgap power electronics).
- **Gray Coherence**: Enforced coherence guard in the compatibility ensemble.

**Result**: 
- `python audit/run_audit.py --module development`
- `41/41` evaluated, `100.0%` accuracy, Brier 0.103.

---

## Physical Grounding (Gaussian Tuning)

**Metric Refinement**:
- **Problem**: Si-O bond at 1.62 Å flagged as plausibility error (0.741).
- **Solution**: Replaced CDF-centrality with **Normalized Gaussian Typicality**.
- **Math**: $ P(x) = \exp\left(-\frac{(x - \mu)^2}{2\sigma^2}\right) $
- **Impact**: Si-O plausibility at 1.62 Å is now **0.946**. Master audit Physical-Grounding: **PASS**.

---

## COG Tier 3 (ZFC) Veto Thresholds

- **Veto Threshold**: 0.20.
- **Rationale**: Any individual scorer below 0.20 triggers a hard ZFC constraint veto (HOLLOW state).
- **Coverage**: 29 HOLLOW pairs identified in the battery domain alone (Aggregate score > 0.45 but contains a critical failure axis).

---

*KOMPOSOS-IV-CHEM | james Hawkins | 2026*
