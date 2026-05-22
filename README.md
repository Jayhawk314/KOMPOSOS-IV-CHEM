# KOMPOSOS-III LAMBDA-max-3D-chem

**A compositional reasoning engine for chemistry and materials.**

You give it two materials. It tells you whether they'll work together and **why** — with scores across multiple physical dimensions (thermal, mechanical, electrochemical, chemical), backed by published property data.

```
NMC811 + LLZO  →  compatible (score 0.72)
  Thermal match:  0.85  (both stable to 700°C)
  Voltage match:  0.90  (overlapping electrochemical windows)
  Chemical:       0.55  (Li exchange at interface — monitor)
```

The system was never told this specific pair has been tested. It derived compatibility by composing physical property constraints from curated data tables.

---

## What It Does

1. **Material compatibility** — Check if two materials from the same domain (battery, polymer, metal, ceramic, semiconductor, glass) are compatible. Five scorers evaluate thermal, mechanical, chemical, structural, and transport properties. Every score traces back to published data with citations.

2. **Multi-domain analysis** — Span multiple domains in one query. "NMC811 cathode + PEO binder + Cu collector" crosses battery, polymer, and metal bridges in a single call.

3. **Molecular-level reasoning** — 37 molecules (solvents, salts, monomers) with PubChem CIDs. Five molecular scorers (electronic, thermodynamic, steric, solubility, reactivity) plus a cross-bridge functor connecting molecules to materials.

4. **Composition prediction** — Enter any chemical formula, get predicted voltage, capacity, thermal stability, ionic conductivity, formation energy (with error estimate in eV/atom), synthesizability, crystal structure type (30 types), and derived crystal structure with lattice parameters + provenance. 175 DFT formation energies with Materials Project IDs. Kan extension + Dempster-Shafer fusion over 103K+ materials. Leave-one-out validated (voltage errors 1.6-7.2%).

5. **Inverse design ("Crystal Dreamer")** — Describe the material you *want* — target properties, element constraints, synthesizability floor — and the engine searches composition space for candidates that match. Four search strategies (perturbation, interpolation, element substitution, stoichiometry variation) generate candidates; the forward predictor scores each one. 500 candidates in ~2.5 seconds.

6. **PFAS compliance** — Screen materials against 35 curated PFAS substances with real CAS numbers and EU/US/Stockholm Convention regulations. Get urgency-based alerts and use-case-specific PFAS-free replacement suggestions.

7. **Synthesis planning** — 24 synthesis routes, 53 precursors with cost/hazard data. Input a target material, get ranked routes with equipment needs and time estimates.

8. **ZFC verification** — Independent set-theoretic verification of compatibility predictions using ZFC axioms. Catches "hollow" predictions (structurally plausible but logically unsound). Includes NIST-derived bonding constraints (bond lengths, coordination numbers, charge balance).

**Internal multi-domain benchmark** (rechecked 2026-05-19): the stricter audit runner now reports 259 evaluated records, 1 skipped record, **94.6% accuracy**, and F1=0.960. The older 95.4% result depended on weaker audit assumptions. Independent review found missing DOI fields, duplicate/non-independent pairs, and weak computational/provenance checks. Treat current validation as screening-grade until the benchmark is de-duplicated, DOI-backed, and held out from tuning. See `docs/AUDIT_FINDINGS_2026-05-19.md`.

**Not a neural network.** KOMPOSOS doesn't train on data — it reasons compositionally over knowledge graphs. It's an interpretable reasoning layer that sits above (and could feed into) simulation tools like DFT, molecular dynamics, or generative AI.

---

## Quickstart

```bash
# Install dependencies
pip install numpy scipy networkx fastapi uvicorn aiosqlite aiohttp httpx pytest

# Start the API server
uvicorn api.main:app --reload
# Visit http://localhost:8000/docs for interactive Swagger UI

# Run the full test suite
python -m pytest -q

# Run the curated bridge/API subset used for fast regression checks
python -m pytest battery_bridge/tests/ polymer_bridge/tests/ metal_bridge/tests/ \
  ceramic_bridge/tests/ semiconductor_bridge/tests/ glass_bridge/tests/ \
  cross_bridge/tests/ synthesis_planner/tests/ molecular_bridge/tests/ \
  pfas_bridge/tests/ composition_engine/tests/ api/tests/ tests/test_material_zfc.py \
  tests/test_enriched_category.py tests/test_dempster_shafer.py \
  tests/test_streaming_kan.py -q
```

See [QUICKSTART.md](QUICKSTART.md) for more examples.

---

## Web API

FastAPI server with 17 endpoints (15 authenticated + 2 public). Run with `uvicorn api.main:app --reload`.

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/api/v1/materials` | GET | Curated bridge materials grouped by domain |
| `/api/v1/materials/{domain}` | GET | Materials with full property details |
| `/api/v1/compatibility` | POST | Two-material same-domain compatibility |
| `/api/v1/molecules` | GET | All 37 molecules grouped by class |
| `/api/v1/molecular-compatibility` | POST | Two-molecule compatibility check |
| `/api/v1/multi-domain` | POST | Cross-domain analysis (2+ components) |
| `/api/v1/pfas-check` | POST | Single material PFAS compliance check |
| `/api/v1/pfas-substances` | GET | All ~35 PFAS substances by category |
| `/api/v1/pfas-alternatives` | POST | PFAS-free replacement suggestions |
| `/api/v1/predict-composition` | POST | Predict properties from chemical formula |
| `/api/v1/interpolate` | POST | Interpolate between two compositions |
| `/api/v1/design-composition` | POST | Inverse design: find compositions matching target properties |
| `/api/v1/synthesis` | POST | Synthesis route planning |
| `/api/v1/synthesis/targets` | GET | List synthesizable targets |
| `/api/v1/zfc-verify` | POST | ZFC constraint verification |

---

## Coverage

| Domain | Materials | Tests | Key Properties |
|--------|----------|-------|----------------|
| battery_bridge | 28 | 58 | Voltage windows, ionic conductivity, crystal structure |
| polymer_bridge | 33 | 98 | Hansen solubility, Tg/Tm, Flory-Huggins chi |
| metal_bridge | 36 | 101 | Galvanic series, CTE, fatigue limit |
| ceramic_bridge | 28 | 102 | Sintering temp, fracture toughness, hardness |
| semiconductor_bridge | 27 | 113 | Band gap, mobility, lattice constant |
| glass_bridge | 23 | 179 | CTE, softening point, hydrolytic resistance |
| molecular_bridge | 37 molecules | 90 | Electronic, thermodynamic, steric, solubility |
| pfas_bridge | 35 substances | 81 | Regulatory compliance, replacement scoring |
| cross_bridge | all | 103 | Multi-domain functors |
| synthesis_planner | 24 routes | 94 | Cost, time, equipment, safety |
| composition_engine | 41 elements, 175 Ef | 252 | Forward prediction, inverse design, formation energy (with error bars), 30 structure types, MP integration |
| mof_bridge | 30 MOFs | 83 | MOF linker inverse design, 5 verdicts, exact atom count control |
| **Total** | **175 curated bridge materials + optional 103K+ MP composition cache + 37 molecules + 35 PFAS** | **Run `pytest --collect-only` for current count** | |

---

## How It Works

Materials are **objects**, reactions/interactions are **morphisms**, compatibility is **composition**. If A→B works and B→C works, the engine reasons about A→C.

Nine mathematical inference strategies vote on every prediction:
Kan Extension, Semantic Similarity, Temporal, Type Heuristic, Yoneda Pattern, Composition, Fibration Lift, Structural Hole, Geometric.

A ZFC dual-engine provides independent logical verification, classifying predictions as AGREE (both engines say yes), ORPHAN (logically forced but structurally missing), HOLLOW (structurally plausible but logically unsound), or REJECT.

Every bridge follows the same architecture:
`material_properties.py` → `interaction_scoring.py` (5 scorers, 0–1) → `interface_validator.py` → `integration.py`

---

## PFAS Compliance

EU PFHxA ban takes effect October 2026. The PFAS module screens materials against regulations and suggests replacements.

```python
from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge.replacement_scorer import UseCase

checker = PFASComplianceChecker()
result = checker.check("PVDF", use_case=UseCase.BATTERY_BINDER)
# result.is_pfas = True
# result.urgency = "moderate"  (proposed ban)
# result.replacements = [CMC+SBR (0.83), PAA (0.76), PAN (0.62), ...]
```

**Urgency levels**: `critical` (BANNED), `high` (ban <12 months), `moderate` (RESTRICTED/PROPOSED), `low` (UNDER_REVIEW), `none`

---

## Competitive Landscape

| Company | Approach | KOMPOSOS difference |
|---------|----------|-------------------|
| CuspAI ($154M) | Generative AI + simulation | Black-box vs interpretable reasoning |
| Orbital Materials | ML potentials (100K atoms) | Simulation speed vs compositional logic |
| Deep Principle | GenAI + quantum chemistry | ReactGen synthesis vs category-theoretic routes |
| DeepMind GNoME | Graph neural networks | Data-driven vs logic-driven |

**KOMPOSOS value**: A reasoning layer that answers "WHAT combinations should we try?" before expensive compute. The composition engine can use a local 103K+ Materials Project cache, while the public materials endpoint exposes the curated bridge registries. The multi-domain cross-bridge spans 6 material domains in one query.

---

## License

Dual-licensed: Apache License 2.0 / KOMPOSOS-III Commercial License.

Free for academic and non-commercial use. See [LICENSE](LICENSE).

Commercial licensing: jhawk314@gmail.com

## Author

James Ray Hawkins — jhawk314@gmail.com

## Citation

```bibtex
@software{komposos3_chem_2026,
  title = {KOMPOSOS-III: Compositional Reasoning for Chemistry and Materials},
  author = {Hawkins, James Ray},
  year = {2026},
  url = {https://github.com/Jayhawk314/KOMPOSOS-III-LAMBDA-max-3D-chem}
}
```
