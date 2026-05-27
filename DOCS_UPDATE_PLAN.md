# Documentation Update Plan for KOMPOSOS-IV-CHEM

The goal is to update the existing documentation (mostly ported from KOMPOSOS-III) to accurately reflect the KOMPOSOS-IV categorical runtime architecture.

## 1. Key Architectural Changes to Reflect
- **Categorical Runtime**: Shift from static bridges to a dynamic execution category (`InfinityCosmos`).
- **COG Engine**: Tiered verification (Tiers 0-4) including Ricci flow, homology, and energy-based coherence.
- **OPTIMUS**: Optimal transport and game-theoretic Nash equilibrium for material trade-offs.
- **ZFC Dual Engine**: Refined set-theoretic foundation with AGREE/ORPHAN/HOLLOW/REJECT verdicts.
- **Core Engine Integration**: Unified COG + OPTIMUS + Cosmos loop.

## 2. Target Files for Update

### A. `KOMPOSOS_COMPLETE_SYSTEM_GUIDE.md` (Primary)
- **Rewrite Section 1 (System Overview)**: Introduce the IV-CHEM categorical runtime concept.
- **Rewrite Section 2 (Core Architecture)**: Move from "Bridge Pattern" to "Categorical Runtime + COG Tiers".
- **Update Section 4 (Capabilities)**: Add details on COG Tiers, OPTIMUS optimization, and Infinity Cosmos higher-order reasoning.
- **Update Section 5 (Mathematical Foundations)**: Include $\infty$-cosmos, Ricci flow, homology, and game theory details.

### B. `docs/FEATURES.md`
- **Upgrade from III to IV**: Emphasize the categorical runtime and tiered verification.
- **Add COG & OPTIMUS**: Explicitly list these as top-level features.

### C. `docs/DIFFERENTIATORS.md`
- **Highlight "Execution as Category"**: Differentiate from static ML or simple rule engines.
- **Highlight Tiered Audit**: Explain the benefit of the 5-tier COG verification.

### D. `docs/AUDIT_PROTOCOL.md` & `docs/AUDIT_CHANGE_LOG.md`
- **Sync with current IV-CHEM status**: Use the metrics from the 2026-05-21 addendum (Q5, Q6, Q7).
- **Reflect Physical Grounding fix**: Mention Gaussian typicality for Si-O bonds.

### E. `docs/LIMITATIONS.md`
- **Update failure modes**: Mention complexity of higher-order reasoning and COG Tier 4 computational costs.

### F. `docs/TUNING_LOG.md`
- **Sync with IV-CHEM sync note**: Reflect the restored Q5 tuning.

### G. `docs/WEB_UI_USER_GUIDE.md`
- **Reflect IV-specific UI features**: If any (e.g., COG tier selection, OPTIMUS trade-off charts).

### H. `CURRENT_STATE.md`
- **Rewrite completely**: Remove PHARM-specific drug repurposing focus, replace with IV-CHEM categorical runtime status.

## 3. Execution Steps
1.  **Draft `KOMPOSOS_COMPLETE_SYSTEM_GUIDE.md`**: Focus on the new architecture.
2.  **Draft `FEATURES.md` and `DIFFERENTIATORS.md`**: Align with the new guide.
3.  **Update Audit Docs**: Ensure they match the actual repo state.
4.  **Rewrite `CURRENT_STATE.md`**.
5.  **Review and refine all docs**.
