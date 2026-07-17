# CHEM system value audit

Date: 2026-07-17

## Conclusion

KOMPOSOS-IV-CHEM is best described as an **evidence-governed materials screening
workbench**. It is not a chemistry breakthrough, a general chemical oracle, or a
single validated predictor. Its unusual value is the combination of:

- deterministic physical and epistemic vetoes;
- explicit benchmark roles (development, spent diagnostic, sealed holdout);
- calibrated outputs where calibration has actually been measured;
- provenance-carrying workflows and reproducible audit commands;
- composition of narrow domain tools without silently promoting a partial score
  into a full-system verdict.

That description holds, but it was previously more aspirational than uniformly
enforced. This audit found several places where UI language and aggregate scores
escaped those rules. The 2026-07-17 repair pass moved the rules into executable
gates: missing physical interfaces now block a full-cell verdict, charge balance
is no longer called independent ZFC proof, generated candidates retain hard
vetoes, and drift baselines produce content-addressed receipts.

There is **no ablation in this repository showing that category theory improves
predictive accuracy**. The defensible contribution of the categorical layer is
architecture: typed composition, reusable functors, explicit morphisms, and a
natural place to implement constraints and evidence flow.

## Feature-by-feature assessment

| Feature | What the code actually does | Reproduced evidence | Honest value and boundary |
| --- | --- | --- | --- |
| Compatibility Checker | Runs native bridge scorers, physical vetoes, an ensemble, and a calibrated pairwise decision workflow. | Development regression 41/41. Q9 is spent: initial 32/40, post-remediation 35/40. The deployed 98-row development/spent isotonic artifact reports OOS ECE 0.072 and Brier 0.049. | The workhorse: a traceable pairwise second opinion. No dataset is currently blind; calibration is not demonstrated per domain and does not transfer to arbitrary multi-interface aggregates. |
| PFAS Scanner | Registry/name/structure screening plus use-case replacement ranking and coverage-aware interface bottleneck checks. | Replacement audit: 18/18 returned suggestions PFAS-free; seven PFAS/use-case panels ranked monotonically and interface scores discriminated. Regression tests confirm that an unknown required contact blocks a full-stack verdict and zero coverage is not converted to a neutral 0.5. | Detection is the strongest checkable feature. Replacement ordering is useful triage, not experimentally validated substitution advice. |
| Composition Predictor | Formula parsing, nearest-material reasoning, a RandomForest formation-energy model, other property estimates, and uncertainty tiers. | Current strict-formula LOO on 179 curated entries: MAE 0.416, RMSE 0.552, median absolute error 0.340 eV/atom. Recalibrated deployed interval coverage: 50/79/95%; five-fold out-of-sample calibration: 49/80/94%. | A fast screening/sanity check. The older 0.304 MAE headline is not reproduced by the current strict LOO path. Other property intervals are heuristic unless separately documented. |
| Cell Designer and Optimizer | Models cathode, anode, electrolyte, binder, and separate current collectors with physical adjacency; sweeps curated stacks and optionally refines cathodes through the local MP cache. | Role pools now exclude `Al_foil` as cathode and `Cu_foil` as anode. The repaired discovery path loads 103,644 MP entries and returned 30 direct refinements in the audit. Missing native interface scorers are now reported. | Real orchestration and useful constrained ranking. Energy density is cathode-active `V*C`, not pack energy. The compatibility aggregate is partial whenever physical contacts lack native functors, so it is not a full-cell probability. |
| Crystal Dreamer | Searches candidate formulas by perturbation, interpolation, substitution, and stoichiometry variation, then scores with the forward predictor and physical gates. | The return-tail gate bug was fixed so every returned candidate passes the configured physical gates. The historical 7/9 recovery claim was not re-reproduced in this pass because the cache-heavy audit exceeded the interactive window. | An inverse-design lead generator whose quantitative ceiling is the forward predictor. Keep the historical recovery claim quarantined until the named audit completes and records an artifact. |
| MP Explorer | Searches the local MP cache, shows source entries and derived/predicted properties, and supports nearest-composition exploration. | Local cache contains 103,644 entries in this checkout. The page now renders its validation/scope note. | More than a generic browser: it is the provenance and neighborhood inspection surface for the prediction stack. Derived estimates must remain visibly distinct from MP source data. |
| MOF Explorer | Searches a curated MOF property registry and applies application filters. | Curated registry contains 30 MOFs; the page now renders its validation note. | A compact reference/screening surface. Its application scores do not inherit the linker-funnel benchmark and should not be presented as independently validated predictions. |
| MOF Designer | Deterministically generates linkers under atom-count/functional-group constraints and ranks them through a structural funnel. | Reproduced: 253 seed, 423 held-out real, 120 gold-tier linkers; pass-all recall 0.9433; AUROC 0.8843 against raw generator decoys. Exact-22 subset: n=20, recall 0.95, AUROC 0.9013. Generated 233; 60 passed all gates; 14 were novel and passed. | The most distinctive single workflow: exact constraints plus a referee. It validates a screening funnel against known synthesized-linker structure, not wet-lab synthesis of generated candidates. |
| Discovery Workbench | Chains inverse design, PFAS detection, charge-balance gating, proxy-based compatibility, and synthesis lookup. | Placeholder `zfc_witnessed=True` removed. Charge-balance failure is now a tested hard veto; proxy distance is computed rather than set to zero. | A real integration pipeline, not a stub. Its weakest seam is proxy substitution: downstream compatibility may describe the nearest registered analog, not the generated formula. Distance and applicability must stay visible. |
| Advanced Triage Workbench | Adds a reference interface context and detailed uncertainty/coverage display to discovery candidates. | Pairwise calibration was removed from the multi-interface aggregate; incomplete interface coverage is now explicit; charge balance is no longer labeled exact ZFC. | A useful mixed-fidelity review surface. It is not an independent predictive engine and should be valued as an evidence/coverage console. |
| Synthesis Planner | Ranks 24 curated target routes with precursor, hazard, cost, equipment, and formal element-balance checks. | Reproduced: 24 targets; 17 routes received balanced witnesses; seven composite/mixture targets were explicitly skipped; zero checked routes were unbalanced. | A substantive narrow route library. Z3 proves element conservation for the encoded equation only; it does not establish the reported paper's mechanism, redox balance, yield, phase purity, or practical success. |

## What the earlier review skipped

The filename-based review missed four meaningful forms of value:

1. **Formal, narrow tools can be valuable without broad prediction.** The synthesis
   planner's curated route data and atom-conservation witnesses are useful even
   though they do not solve synthesis.
2. **Explorers are inspection instruments.** MP Explorer is where a user can audit
   neighborhoods and source-vs-derived fields; that supports the trust contract.
3. **Orchestration exposes missing science.** Cell and advanced workbenches reveal
   which physical interfaces have no scorer. That coverage map is valuable even
   when it prevents a verdict.
4. **A generated candidate needs both physical and epistemic vetoes.** Invalid
   chemistry and unsupported evidence are different failures. Both must survive
   composition and block confident prose.

## The central design law

The earlier observation that "a generator needs a referee" is correct but
incomplete. The stronger law is:

> A composed conclusion may be no stronger than its weakest required physical
> interface **or** its weakest required evidence link.

A pore-access failure is a physical veto. An unread file, missing benchmark,
unscored interface, distant proxy, or spent dataset is an epistemic veto. Neither
may disappear inside a mean, a calibrated number from another scope, or fluent
language.

## Highest-value next work

1. Add native scorers or explicit user-supplied evidence for the central unscored
   battery contacts (battery/ceramic, battery/battery electrode-electrolyte, and
   polymer/ceramic where applicable).
2. Freeze and preserve a genuinely new compatibility holdout before inspecting
   labels. Q9 is spent; Q10 remains sealed and unscored.
3. Improve and externally validate the formation-energy point model; calibration
   makes uncertainty honest but does not lower MAE.
4. Expand linker seed diversity and seek chemist review or experimental validation
   of generated MOF candidates.
5. Keep the synthesis planner narrow while adding reaction-specific charge/redox
   constraints only where the route encoding supports them.
6. Make claim receipts and evidence roles a shared CHEM/Noesis protocol, as
   specified in `PROVENANCE_CONTRACT_PROJECT.md`.

## External value: what can be supported now

PFAS is the clearest externally forced use case, but the earlier conversation
overstated the legal picture. The broad EU PFAS action is still a restriction
proposal: ECHA reports that RAC adopted its opinion and SEAC agreed a draft
opinion in March 2026, with consultation activity continuing through June.
Separately, the enacted EU PFHxA restriction has specific product/use scopes and
dates, including 10 October 2026 for listed consumer uses; it is not a blanket
ban on every PFAS application. The US TSCA 8(a)(7) reporting schedule was also
changed again in April 2026, with the reporting start tied to a forthcoming rule
revision.

Primary sources:

- [ECHA PFAS restriction status](https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas)
- [EU Regulation 2024/2462 on PFHxA](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202402462)
- [US EPA TSCA 8(a)(7) reporting status](https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping)

The defensible product inference is narrower: organizations need auditable
inventory, structural screening, evidence capture, and replacement triage while
requirements change. CHEM can help assemble and prioritize that work. It should
not claim that its current registry determines legal compliance in every
jurisdiction, that a ranked replacement is qualified, or that a future proposal
is already law.

## Verification record

- Focused repair regression: 44 passed.
- Bridge/orchestration shards: 903 passed.
- Previously failing oracle strategies: 4 passed after stale-interface repairs.
- Composition parser/properties/spatial shards: 66 passed.
- Structure-predictor shard: 42 passed in 77.45 s.
- Formation/calibration/predictor shards: 80 passed in 187.15 s.
- Final repaired-boundary regression (monitoring, battery roles, PFAS coverage,
  discovery vetoes, multi-domain completeness, MOF designer/cache, and oracle
  adapter): 107 passed in 24.18 s.
- Frozen prediction-drift rerun: AGREE, receipt
  fc00c0ae46f7d4f879ab2fc590a0645ada0c5667e2e579ea5787e1b1ad184357;
  measured errors, interval coverage, and all three artifact hashes matched.
- MOF funnel, formation LOO/calibration, PFAS replacement, synthesis balance, and
  battery discovery commands were run directly during this audit.

These are regression and development results unless a row explicitly says
otherwise. They are not a blanket external-validation claim for the product.
