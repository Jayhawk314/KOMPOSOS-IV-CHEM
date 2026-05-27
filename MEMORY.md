# KOMPOSOS-IV-CHEM Memory

Read this first when entering this repo. Code and live data are the source of
truth; many older docs are aspirational or stale.

## What This Repo Is

KOMPOSOS-IV-CHEM is a **categorical runtime** applied to chemistry and materials discovery. It transitions from static database bridges to a live execution category ($\infty$-cosmos).

Primary goal: advanced compatibility reasoning, structural design, and multi-domain interface analysis (Batteries, Polymers, Metals, Ceramics, etc.).

## Current System State (2026-05-27)

Unified the reasoning pipeline and integrated Simplicial Type Theory (STT) concepts to remove heuristics.

### Unified Reasoning Architecture
- **Shared Service**: `oracle/compatibility_service.py` is the single source of truth for both FastAPI and Streamlit UI.
- **Ensemble Integration**: The `CompatibilityEnsembleResult` now fuses classical rules, typed morphisms, MD integration, and STT strategies.
- **Categorical Foundation**: The system correctly handles both III-style stores and IV-style categorical objects via robust base classes and `Morphism` aliases.

### Advanced Math Features
- **Simplicial Yoneda**: Uses Jaccard distance between presheaf fingerprints to find structural analogs.
- **Fibration Transport**: Lifts compatibility results across base category morphisms.
- **Typed Capabilities**: Bridges explicitly declare math-level requirements (2-cells, fibrations, etc.) using `TypedPluginMixin`.

## Scientific Audit Status

- **Development Set (Q5)**: `41/41`, `100.0%` accuracy. (Verified 2026-05-27)
- **External Blind (Q7)**: `35/35`, `91.4%` accuracy. (Verified 2026-05-27)
- **AUROC (Bio)**: Confirmed at `0.9008` (simple average) for Drug->Disease prediction.

## Standing Rules

1. **Code & Data Priority**: Frozen audit results and live database queries outrank docs.
2. **Execution as Category**: Queries are proof searches in a simplicially enriched category.
3. **Physical Grounding**: Use normalized Gaussian typicality for bond plausibility checks.
4. **Transparency**: Always surface strategy votes and ZFC witnesses to the user.
5. **No Hallucination**: Enforce strict chemical/physical constraints (e.g., exact atom counts in MOF designer).

## Key Files

- `oracle/compatibility_service.py`: unified reasoning entry point.
- `oracle/simplicial_strategies.py`: STT-enhanced strategies (Yoneda, Transport).
- `core/types.py`: fused categorical types (Object, Morphism with aliases).
- `audit/run_audit.py`: main scientific audit harness.
- `api/routes/compatibility.py`: unified API endpoint.
- `streamlit_app/pages/1_Compatibility_Checker.py`: rewired UI using shared service.
- `SESSION_SUMMARY.md`: detailed history of the 2026-05-27 integration session.
