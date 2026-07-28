# KOMPOSOS-IV-CHEM

KOMPOSOS-IV-CHEM is an **evidence-governed screening workbench for chemistry and
materials questions**. It combines curated property bridges, physical vetoes,
calibrated models where calibration has been measured, provenance-aware
workflows, and reproducible audit commands.

It is meant to answer:

- What evidence supports this materials-compatibility screen?
- Which physical interface is the bottleneck, and which interfaces are unscored?
- Is a proposed replacement PFAS-free and compatible with the covered parts of a
  material stack?
- Which formulas or MOF linkers are worth sending to higher-fidelity computation
  or a chemist?
- How much should this particular output be trusted?

This is **screening and triage software**. It does not replace experiment, DFT,
reaction expertise, regulatory counsel, or process qualification.

## Current evidence posture

| Capability | Current reproducible result | Boundary |
| --- | --- | --- |
| Pairwise compatibility | 41/41 development regression; deployed 98-row development/spent isotonic calibration reports OOS ECE 0.072, Brier 0.049 | No current blind dataset; not calibrated per domain or for multi-interface aggregates |
| Formation energy | Strict formula LOO, n=179: MAE 0.416, RMSE 0.552, median absolute error 0.340 eV/atom | Screening-grade point model; older 0.304 headline is superseded for this executable path |
| Formation intervals | Deployed coverage 50/79/95%; five-fold calibration 49/80/94% | Calibrated on the curated development corpus, not experimental deployment outcomes |
| MOF linker funnel | Held-out-real recall 0.9433; AUROC 0.8843 vs raw generator; exact-22 recall 0.95 | Structural screening of known/generated linkers, not synthesis proof |
| PFAS replacements | 18/18 audited suggestions PFAS-free; use-case and interface ranking checks pass | Replacement ranking is triage, not qualified substitution advice |
| Synthesis routes | 24 curated targets; 17 element-balanced witnesses; 7 composite targets skipped | Proves encoded atom conservation only, not mechanism, redox, yield, or phase purity |

Dataset roles matter. Q9 has been inspected and used for remediation, so it is a
**spent diagnostic**, not blind evidence. Q10 remains sealed and unscored. See
[`audit/dataset_registry.json`](audit/dataset_registry.json).

## Application surfaces

The Streamlit application contains eleven distinct views:

1. Pairwise Compatibility Checker
2. PFAS Scanner and replacement triage
3. Composition Predictor
4. Cell Designer and battery optimizer
5. Crystal Dreamer inverse-design leads
6. Materials Project cache explorer
7. Curated MOF explorer
8. Constrained MOF linker designer
9. Discovery Workbench
10. Advanced coverage/uncertainty triage
11. Curated Synthesis Planner

These are not equally validated. Each page renders its own scope and validation
note. Multi-component pages now report requested physical-interface coverage and
refuse a full-system verdict when a required contact has no native scorer.

The full feature/function audit is
[`docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md`](docs/CHEM_SYSTEM_VALUE_AUDIT_2026-07-17.md).

## Quick start

```powershell
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

Start the API:

```powershell
uvicorn api.main:app --reload
```

Run the chemistry-only regression/audit gate:

```powershell
python audit\chem_audit.py
```

Cache-heavy composition tests can take several minutes. Run individual shards
when diagnosing them rather than interpreting a quiet console as a result.

## Stable monitoring exports

CHEM exposes content-addressed JSON records suitable for an external ledger such
as Noesis:

```powershell
python -m api.monitoring_export prediction --formula LiFePO4 --domain battery
python -m api.monitoring_export compatibility --material-a PVDF --material-b NMC811
python -m api.monitoring_export prediction-drift
```

The drift command checks the current strict-LOO metrics and model/calibration
artifact hashes against a frozen development baseline. `AGREE` means executable
behavior matches that baseline; it is not an external-validation badge.

The communication-layer design is documented in
[`docs/PROVENANCE_CONTRACT_PROJECT.md`](docs/PROVENANCE_CONTRACT_PROJECT.md).

## Architecture

Materials are represented as objects, interactions as morphisms, and bridge
scorers as composable domain operations. The categorical runtime is useful for
typing interfaces and carrying constraints through compositions. The repository
does not currently include an ablation proving that category theory itself
improves predictive accuracy.

Several components use learned models, including the formation-energy
RandomForest. Outputs must therefore be judged by their specific benchmark and
evidence role, not by a blanket "non-black-box" claim.

## License

Apache License 2.0. See `LICENSE`.

Author: James Ray Hawkins
