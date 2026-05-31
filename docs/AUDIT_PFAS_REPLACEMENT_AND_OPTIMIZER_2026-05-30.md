# Feature Verification — PFAS Replacement & Battery Optimizer (2026-05-30)

Scientific / quality verification of two features Gemini built this cycle, in the
same honest spirit as the PFAS detection, MOF, and Crystal Dreamer audits: name
the metric, say whether each claim is a **checkable fact** or a **modeled
estimate**, and report the limitations rather than a single headline number.

Reproduce:
```
python audit/run_pfas_replacement_audit.py
python audit/run_battery_optimizer_audit.py
python audit/run_pfas_audit.py            # detection (re-confirmed after SMILES guard)
```

---

## 1. PFAS Replacement Engine — `audit/run_pfas_replacement_audit.py`

The engine is a **curated expert database** of (PFAS, use_case) → ranked
PFAS-free candidates, plus a **compatibility filter** that re-ranks candidates
against an adjoining material. It is not a classifier, so there is no AUROC.

| Check | Result | Kind |
|---|---|---|
| **PFAS-free guarantee** (no suggested replacement is itself PFAS) | **18/18 = 100%** | checkable FACT |
| Quality ranking monotone (sorted best-first) | YES | structural |
| Compatibility filter discriminates by adjoining material | YES (4/4 distinct) | physics |
| Coverage — regulated PFAS with replacement data | **4** | scope limit |
| Coverage — (PFAS, use_case) pairs | 7 | scope limit |
| Candidates the compat engine can actually score | **2 of 4** (rest default) | scope limit |

**Strongest result — the compatibility filter reproduces real materials science.**
For PVDF binder replacements:
- next to a **graphite anode**, `CMC+SBR` tops at **0.919** — it is the real-world
  standard aqueous binder for graphite;
- next to **NMC811** (high-voltage cathode), `CMC+SBR` correctly collapses to
  **0.35** and `PAN` takes over — matching the known fact that CMC+SBR is
  unsuitable for high-voltage cathodes (it is even in the candidate's own
  `limitations`). The filter is doing physics, not returning a static list.

**Honest limitations:**
- Replacement **coverage is thin**: only 4 regulated PFAS have curated
  alternatives. Good for the battery-relevant ones (PVDF, PTFE) but not broad.
- The compatibility filter only scores candidates that exist in the bridge
  registries (**2 of 4** for the PVDF case); the rest fall back to a neutral
  default. Adding the missing polymers (PAA, Alginate) to the polymer bridge
  would close this.
- Candidate performance/cost/availability numbers are **expert estimates**, not
  measured. The PFAS-free check is the only hard fact.

---

## 2. Battery Optimizer — `audit/run_battery_optimizer_audit.py`

**What it optimizes:** theoretical energy density (cathode V × gravimetric
capacity) under cross-domain **compatibility** constraints. It does **not** model
cycle life, safety, thermal runaway, or cost — those are not computable from the
available data, so they are deliberately excluded rather than invented.

| Check | Result | Kind |
|---|---|---|
| **No false veto** of real commercial cells (recall) | **7/7 = 100%** | checkable |
| Energy-density objective computed exactly | **99,999/99,999** | checkable FACT |
| Chemistry ordering physically sane (S8 top; LFP < NMC) | YES | physics |
| **Constrained Hits@K** — real design in viable output | **7/7 = 100%** | checkable |
| Invariants (threshold, ranks 1..N, monotone) | YES | structural |

Commercial panel: CATL/BYD LFP, NMC811, NCA (Tesla 2170), LCO, NMC622, LMO/LTO,
NMC811/Si. Max theoretical Wh/kg (cathode-active basis): S8 3518 ≫ LCO 1069 ≈ NMC
family ~1045 > LMO 607 > LFP 578 — the expected ordering.

**Honest findings & limitations:**
- **FIXED (2026-05-30): bimetallic two-collector model with physical adjacency.**
  Previously the cell had one collector slot and scored every pair, so an Al
  collector was scored against the anode (`Al_foil ↔ graphite` = 0.18) — a
  *phantom* interface that doesn't physically exist (Al never touches the anode;
  cells use Al on the cathode, **Cu** on the anode). Added opt-in role-based
  adjacency (`BATTERY_CELL_ADJACENCY` in `cross_bridge/multi_domain.py`) and split
  the optimizer into cathode-side + anode-side collectors. Only physically-
  adjacent interfaces are now scored. Effect: the phantom bottleneck is gone, the
  bottleneck is now the real `Al_foil ↔ EC` (0.68), and commercial-cell viability
  rose from ~0.79 to ~0.82–0.86. The optimizer's factorized sweep was verified
  bit-identical (maxdiff 2e-16) to `analyze()` with adjacency, and is backward-
  compatible (callers that don't pass adjacency, e.g. the Q8/Q9 audits, are
  unchanged). Anode collector defaults to Cu (overridable).
- Reported energy density is **theoretical** (cathode-active only); real
  cell-level Wh/kg is ~40–55% after anode + packaging mass. UI already labels it
  theoretical — keep that.
- The optimizer returns top-N by energy density, so low-energy chemistries (LFP,
  LMO) are correctly dropped from an unconstrained sweep — expected, not a bug.

**On adding cycle-life / safety targets (discussed 2026-05-30):** do **not** add
them as invented numeric targets (no ground truth → false precision, breaks the
honesty rule). The defensible path is grounded **risk flags / constraints** from
citable facts (high-SOC O₂ release for NCA/NMC, dendrite risk for Li-metal, ~300%
volume expansion for Si) shown alongside energy density — never blended into one
magic score. TODO markers are placed in the audit where these would slot in.

---

## 3. PFAS Detection — re-confirmed after the SMILES guard

Gemini's `smiles_is_pfas` guard (skip RDKit parse for short non-SMILES names)
does **not** regress detection: specificity **25/25 = 100%** on the hard-negative
panel, EPA concordance **99.53%** (10725/10776), positive controls 4/4. Unchanged
from the prior audit.

---

## Bottom line

PFAS replacement and the battery optimizer both pass their honest verifications.
The replacement engine's PFAS-free guarantee (100%) and the optimizer's no-false-
veto + objective correctness (100%) are **checkable facts**. The one structural
model gap found (single collector → phantom Al↔anode interface) has been **fixed**
with an adjacency-aware bimetallic model. Remaining limitations are scope
(replacement coverage, compat-registry coverage) — none are correctness bugs.
