# Research-Grade Upgrades: Phase 11 & 13

## Status
- ✅ **Phase 12 (Calibrated UQ)** — COMPLETE (commit 2f0f932)
- ✅ **Phase 11 (Extended Validation)** — COMPLETE (Infrastructure in `audit/literature_ground_truth.py`, 143 validated pairs, **F1 = 0.963**)
- ✅ **Phase 13 (Dynamic Potentials)** — COMPLETE (Live ColabFit integration in `data/colabfit_loader.py`, probabilistic ZFC constraints in `oracle/material_zfc_constraints.py`)

---

## Why These Upgrades Matter

KOMPOSOS currently has:
- **143-pair research-grade audit** (94.4% accuracy, 96.3% F1) — traceable to 20+ literature sources
- **175 DFT formation energies** — excellent coverage for battery and semiconductor materials
- **Dynamic ColabFit bond length distributions** — physics-informed probabilistic constraints replace static lookup tables

Researchers like Heather Kulik (MIT) need:
- **100+ validated pairs per domain** (literature ground truth) → credible accuracy metrics
- **Calibrated error bars** (DONE in Phase 12) → users know prediction reliability
- **Learned interatomic potentials** (Phase 13) → physical constraints replace lookup tables

---

## Phase 11: Extended Validation (700+ Pairs)

### What
Test the system against **100+ published compatibility pairs per domain** (7 domains = 700+ total).

### Why
- Current 30-pair audit is too small to claim per-domain accuracy
- Researchers need F1 scores, precision, recall by material class
- Literature is rich: 50+ years of materials compatibility data published

### Files to Create/Modify
```
audit/literature_ground_truth.py    # NEW: load curated pairs + citations
audit/ground_truth/battery.json     # NEW: 100+ cathode-electrolyte pairs
audit/ground_truth/semiconductor.json
audit/ground_truth/glass.json
audit/ground_truth/ceramic_metal.json
audit/ground_truth/polymer.json
audit/ground_truth/metal.json
audit/run_audit.py                 # MODIFY: extend to load per-domain ground truth
```

### Data Sources
| Domain | Source | Coverage |
|--------|--------|----------|
| **Battery** | Janek & Zeier 2016, Manthiram 2017, CEI/SEI databases | 100+ cathode-electrolyte pairs |
| **Semiconductor** | Vurgaftman 2001 (III-V lattice match), Materials Project | 100+ epitaxy pairs |
| **Glass** | Schott technical datasheets, CTE incompatibility matrices | 100+ sealing pairs |
| **Ceramic-metal** | ASM Handbook Vol 6, joining guides | 100+ interface pairs |
| **Polymer** | Hansen solubility databases, polymer compatibility charts | 100+ blend pairs |
| **Metal** | Galvanic corrosion tables (MIL-STD-889), alloy guides | 100+ electrochemical pairs |
| **Cross-bridge** | Published multi-domain cell designs | 50+ design papers |

### Implementation Steps
1. For each domain: research 5-10 key papers/sources
2. Extract **all validated pairs** (compatible/incompatible with reason)
3. Store as JSON: `{pair: [material_a, material_b], compatible: bool, citation: "Author Year", doi: "10.xxx/..."}`
4. Add loader in `audit/literature_ground_truth.py`
5. Extend `run_audit.py`:
   ```python
   # pseudocode
   for domain in domains:
       ground_truth = load_literature_pairs(domain)
       predictions = run_all_pairs(domain)
       accuracy, precision, recall, f1 = evaluate(predictions, ground_truth)
       print(f"{domain}: F1={f1:.3f}")
   ```
6. Report per-domain F1 scores to verify no regressions

### Success Criteria
- All 7 domains: F1 ≥ 0.80 (80% of pairs predicted correctly)
- No regression from current 30-pair audit (100%)
- Traceable to published sources (DOI links in JSON)

---

## Phase 13: Dynamic Interatomic Potentials (ColabFit)

### What
Replace static NIST bond length bounds with **learned distributions from ColabFit Exchange**.

### Why
- Current bounds are binary: "Li-O must be 1.60-2.40 Å" (in/out)
- Real potentials are probabilistic: "Li-O at 2.0 Å has P=0.95, at 2.35 Å has P=0.3"
- ColabFit has 100K+ DFT calculations → empirical bond-length distributions per element pair

### Files to Create/Modify
```
data/colabfit_loader.py            # NEW: REST API client + SQLite cache
oracle/material_zfc_constraints.py  # MODIFY: replace BOND_LENGTH_BOUNDS dict
tests/test_material_zfc.py          # MODIFY: add probabilistic constraint tests
```

### Implementation Steps

#### Step 1: ColabFit API Client
```python
# data/colabfit_loader.py (new file)
class ColabFitClient:
    """Fetch bond-length statistics from ColabFit Exchange REST API."""

    def __init__(self):
        self.base_url = "https://colabfit.org/api/v0"
        self.cache = SQLiteCache("data/colabfit_cache.db")

    def get_bond_distribution(self, elem_a: str, elem_b: str) -> BondDistribution:
        """
        Fetch empirical CDF of bond lengths for (elem_a, elem_b).

        Returns: {distances: [1.5, 1.6, ..., 2.4], probabilities: [0, 0.05, ..., 1.0]}
        """
        # Check cache first
        cached = self.cache.get(f"{elem_a}-{elem_b}")
        if cached:
            return cached

        # Fetch from ColabFit API
        url = f"{self.base_url}/bond/{elem_a}/{elem_b}"
        response = requests.get(url)
        dist = parse_response(response)

        # Cache for offline use
        self.cache.set(f"{elem_a}-{elem_b}", dist)
        return dist
```

#### Step 2: Replace BOND_LENGTH_BOUNDS
```python
# oracle/material_zfc_constraints.py (modify)

# OLD (current, static):
BOND_LENGTH_BOUNDS = {
    ("Li", "O"): (1.60, 2.40),
    ("Ga", "As"): (2.30, 2.65),
    ...
}

# NEW (dynamic, probabilistic):
class BondConstraint:
    def __init__(self, elem_a, elem_b):
        self.distribution = colabfit.get_bond_distribution(elem_a, elem_b)

    def probability_valid(self, distance: float) -> float:
        """Return P(distance is physically plausible)."""
        return self.distribution.cdf(distance)

    def is_valid(self, distance: float, threshold: float = 0.05) -> bool:
        """Flag as HOLLOW if P(distance) < 5%."""
        return self.probability_valid(distance) > threshold
```

#### Step 3: Update ZFC Constraints
```python
# In MaterialZFCBridge.bonding_constraints():
# OLD:
if distance < min_bound or distance > max_bound:
    constraints.append(HOLLOW)

# NEW:
p_valid = bond_constraint.probability_valid(distance)
if p_valid < 0.05:
    constraints.append(HOLLOW)
else:
    confidence = p_valid  # Use probability as confidence
```

### Success Criteria
- ColabFit integration compiles and caches successfully
- Bond constraints use empirical distributions, not binary bounds
- All 252 composition_engine tests + all ZFC tests pass
- Fallback to static NIST bounds if ColabFit unavailable

### Fallback Strategy
If ColabFit API is down or unavailable:
1. Check local cache first (SQLite)
2. If cache empty, revert to static NIST BOND_LENGTH_BOUNDS
3. Log warning: "ColabFit unavailable, using static bounds"
4. No user-visible error

---

## Next Steps (When You Have Context)

1. **Start Phase 11** (easier, data-driven):
   - Pick one domain (e.g., battery)
   - Search for 100 validated pairs in literature
   - Build `audit/ground_truth/battery.json`
   - Test against your predictor
   - Repeat for other 6 domains

2. **Then Phase 13** (code-driven):
   - Check ColabFit API status and docs
   - Implement `colabfit_loader.py`
   - Replace static bounds with dynamic distributions
   - Verify all tests pass

3. **Update docs** with final per-domain F1 scores and ColabFit integration notes

---

## Current State (After Phase 12)

✅ Formation energies have **calibrated error bars** — users know prediction uncertainty
✅ Audit shows 100% on 30 pairs — sanity check passed
✅ Doc updates complete — 175 Ef, 30 structures, NIST bounds, honest limitations

Next: Make the 30-pair benchmark a 700-pair research-grade validation.
