# KOMPOSOS-III Chemistry Quickstart

## Install

```bash
pip install numpy scipy networkx fastapi uvicorn aiosqlite aiohttp httpx pytest
```

## Start the API

```bash
uvicorn api.main:app --reload
```

Then visit http://localhost:8000/docs for interactive Swagger UI.

## Try a compatibility check

```bash
curl -X POST http://localhost:8000/api/v1/compatibility \
  -H "Content-Type: application/json" \
  -d '{"material_a": "NMC811", "material_b": "EC"}'
```

Or use Python:

```python
import httpx

r = httpx.post("http://localhost:8000/api/v1/compatibility",
               json={"material_a": "NMC811", "material_b": "EC"})
print(r.json())
# {"material_a": "NMC811", "material_b": "EC", "domain": "battery",
#  "scores": {"thermal": 0.85, "electrochemical": 0.90, ...}, "viable": true}
```

## Check PFAS compliance

```bash
curl -X POST http://localhost:8000/api/v1/pfas-check \
  -H "Content-Type: application/json" \
  -d '{"material_name": "PVDF"}'
```

```python
r = httpx.post("http://localhost:8000/api/v1/pfas-check",
               json={"material_name": "PVDF"})
print(r.json())
# {"material_name": "PVDF", "is_pfas": true, "pfas_category": "fluoropolymer",
#  "restricted_eu": true, "alternatives": ["CMC+SBR", "PAA", "PAN", ...]}
```

## Get PFAS-free alternatives

```bash
curl -X POST http://localhost:8000/api/v1/pfas-alternatives \
  -H "Content-Type: application/json" \
  -d '{"material_name": "PVDF", "use_case": "battery_binder"}'
```

## Multi-domain query

```bash
curl -X POST http://localhost:8000/api/v1/multi-domain \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Full Cell",
    "components": [
      {"name": "NMC811", "role": "cathode"},
      {"name": "PEO", "role": "binder"},
      {"name": "Cu", "role": "collector"}
    ],
    "electrolyte": "EC"
  }'
```

## Synthesis planning

```bash
curl -X POST http://localhost:8000/api/v1/synthesis \
  -H "Content-Type: application/json" \
  -d '{"target": "LFP"}'
```

## Use without the API

```python
# Material compatibility
from battery_bridge.interface_validator import validate_interface
result = validate_interface("NMC811", "EC")
print(f"Viable: {result.viable}, Score: {result.total:.2f}")

# PFAS compliance
from pfas_bridge.compliance_checker import PFASComplianceChecker
from pfas_bridge.replacement_scorer import UseCase

checker = PFASComplianceChecker()
result = checker.check("PVDF", use_case=UseCase.BATTERY_BINDER)
print(f"PFAS: {result.is_pfas}, Urgency: {result.urgency}")
for r in result.replacements[:3]:
    print(f"  {r.name}: score={r.overall_score:.3f}")

# Batch BOM screening
batch = checker.check_batch(["PVDF", "PTFE", "HDPE", "CMC"])
print(f"PFAS found: {batch.pfas_count}, Max urgency: {batch.max_urgency}")

# Synthesis planning
from synthesis_planner.route_planner import SynthesisPlanner
planner = SynthesisPlanner()
routes = planner.plan("LFP")
print(f"Best route: {routes[0]['name']}, Cost: ${routes[0]['cost']:.0f}")

# Multi-domain analysis
from cross_bridge.multi_domain import MultiDomainAnalyzer
analyzer = MultiDomainAnalyzer()
result = analyzer.analyze(
    name="Full Cell",
    components=[("NMC811", "cathode"), ("PEO", "binder"), ("Cu", "collector")],
)
print(f"Overall: {result['overall_score']:.2f}, Viable: {result['viable']}")
```

## Run demos (no API needed)

```bash
# Multi-domain replicator demo
python -m cross_bridge.multi_domain

# Synthesis planner demo
python -m synthesis_planner.route_planner

# ZFC dual-engine demo
python -m zfc.bridge

# PFAS compliance demo
python -m pfas_bridge.compliance_checker
```

## Inverse design (Crystal Dreamer)

```bash
curl -X POST http://localhost:8000/api/v1/design-composition \
  -H "Content-Type: application/json" \
  -H "X-API-Key: komposos-demo-key" \
  -d '{"targets": [{"name": "voltage", "min_value": 4.0}], "element_constraints": {"excluded_elements": ["Co"]}, "max_candidates": 100}'
```

```python
from composition_engine.designer import CompositionDesigner, DesignSpec, PropertyTarget, ElementConstraint

designer = CompositionDesigner()
spec = DesignSpec(
    targets=[PropertyTarget("voltage", min_value=4.0)],
    element_constraints=ElementConstraint(excluded_elements=["Co"]),
    max_candidates=100,
)
result = designer.design(spec)
for c in result.candidates[:5]:
    print(f"{c.formula}: score={c.overall_score:.3f}, voltage={c.predicted_properties.get('voltage', 0):.2f}V")
```

## Start the web UI

```bash
streamlit run streamlit_app/app.py
# 6 pages: Compatibility Checker, PFAS Scanner, Composition Predictor,
# Cell Designer, Crystal Dreamer, MP Explorer
```

## Download Materials Project data (optional, one-time)

```bash
# Requires mp-api: pip install mp-api
# Get an API key from https://materialsproject.org
python scripts/download_mp_data.py --api-key YOUR_KEY
# Downloads 103K+ materials with DFT formation energies, crystal structures,
# lattice parameters. Cached as gzipped JSON (~30MB).
# Without this, the system works with 169 curated bridge materials.
```

## Run tests

```bash
# All 1,423 tests
python -m pytest battery_bridge/tests/ polymer_bridge/tests/ metal_bridge/tests/ \
  ceramic_bridge/tests/ semiconductor_bridge/tests/ glass_bridge/tests/ \
  cross_bridge/tests/ synthesis_planner/tests/ molecular_bridge/tests/ \
  pfas_bridge/tests/ composition_engine/tests/ api/tests/ tests/test_material_zfc.py \
  tests/test_enriched_category.py tests/test_dempster_shafer.py \
  tests/test_streaming_kan.py -q

# Just PFAS tests (81 tests)
python -m pytest pfas_bridge/tests/ -v

# Just API tests (42 tests)
python -m pytest api/tests/test_api.py -v
```

## Available domains

| Domain | Count | Example materials |
|--------|-------|-------------------|
| battery | 22 | NMC811, LFP, LLZO, EC, LiPF6 |
| polymer | 33 | PVDF, PEO, HDPE, PEEK, Epoxy |
| metal | 36 | Cu, Al, Ti-6Al-4V, SS316L |
| ceramic | 28 | Al2O3, ZrO2, SiC, BN |
| semiconductor | 27 | Si, GaAs, GaN, SiC-4H |
| glass | 23 | Borosilicate, Soda-lime, Fused silica |
| molecular | 37 | EC, DMC, LiPF6, TEOS, Acetone |
| pfas | 35 | PFOA, PFOS, PVDF, PTFE, GenX, Nafion |
