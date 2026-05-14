# Battery Engineering Bridge for KOMPOSOS-III

## What This Is

A physical-chemical bridge for battery materials engineering, built on the same architecture as KOMPOSOS-III's protein contact bridge. Instead of scoring amino acid residue contacts, it scores electrochemical material interfaces.

## Architecture Mapping

| Protein Bridge | Battery Bridge |
|---|---|
| Amino acid properties (Kyte-Doolittle, charges) | Material properties (voltage, capacity, conductivity) |
| H-bond scoring | Ion transport scoring |
| Salt bridge scoring | Electrochemical stability scoring |
| Hydrophobic interaction scoring | Interface compatibility scoring (SEI/CEI) |
| Van der Waals scoring | Mechanical compatibility scoring |
| Electrostatic repulsion penalty | Degradation penalty |
| `can_form_hbond(aa1, aa2)` | `validate(material_a, material_b)` |
| Protein structure validation | Cell configuration analysis |
| HBondMorphism -> StoredMorphism | InterfaceMorphism -> StoredMorphism |

## Quick Start

```python
from battery_bridge import BatteryInterfaceValidator, BatteryFlowAnalyzer
from battery_bridge import STANDARD_LFP_CELL, STANDARD_NMC811_CELL

# 1. Validate a single interface
validator = BatteryInterfaceValidator()
result = validator.validate('LFP', 'EC')
print(f"Viable: {result.viable}, Score: {result.total:.2f}")
# -> Viable: True, Score: 0.82

# 2. Analyze a complete cell
analyzer = BatteryFlowAnalyzer()
analysis = analyzer.analyze_cell(STANDARD_LFP_CELL)
print(f"Cell viability: {analysis.overall_viability:.2f}")
print(f"Bottleneck: {analysis.bottleneck.material_a}<->{analysis.bottleneck.material_b}")

# 3. Run full KOMPOSOS categorical analysis
from battery_bridge import run_battery_categorical_analysis
result = run_battery_categorical_analysis(STANDARD_NMC811_CELL)
print(f"Coherent: {result['coherence']['coherent']}")
```

## Module Structure

```
battery_bridge/
  __init__.py                  # Public API
  material_properties.py       # 20+ materials with real published values
  interaction_scoring.py       # 5 scorers (each returns 0-1)
  interface_validator.py       # BatteryInterfaceValidator (composite)
  battery_flow.py              # Full cell analysis + degradation cascades
  data_ingestion.py            # API stubs for Materials Project, AFLOW, Battery Archive
  integration.py               # Hooks into KOMPOSOS categorical core
  tests/
    test_properties.py         # Material table validation
    test_scoring.py            # Scorer range and correctness
    test_known_cells.py        # Ground-truth cell validation
```

## The Five Scorers

### 1. Ion Transport Score
Can Li+ migrate through this interface? Based on ionic conductivity ratio between adjacent materials, crystal structure compatibility, and channel size vs. ion radius.

### 2. Electrochemical Stability Score
Is the electrolyte stable at this electrode's operating voltage? Compares electrode voltage window against electrolyte oxidation/reduction potentials. Accounts for SEI formation at anodes (expected) vs. solid electrolyte decomposition (problematic).

### 3. Interface Compatibility Score
Will a stable passivation layer (SEI/CEI) form? Encodes known good pairings (EC on graphite = excellent SEI) and known bad ones (Li metal in liquid carbonate = unstable SEI + dendrites).

### 4. Mechanical Compatibility Score
Will cycling cause delamination or cracking? Based on volume expansion during lithiation/delithiation, elastic modulus mismatch, and known cracking-prone materials.

### 5. Degradation Penalty
Known bad pairings get penalized directly. Encodes literature knowledge: Li metal + carbonates (dendrites), Si + standard electrolyte (expansion kills SEI), LGPS + high-voltage cathode (decomposition).

## Material Database

20+ materials with real published values and source citations:

**Cathodes**: LCO, LFP, NMC811, NMC622, NMC111, LMO
**Anodes**: Graphite, Li metal, Si, LTO
**Electrolyte Solvents**: EC, DMC, DEC, EMC
**Electrolyte Salts**: LiPF6, LiTFSI
**Solid Electrolytes**: LLZO, LGPS, Li3PS4
**Ions**: Li+, Na+, Mg2+

All values sourced from Materials Project, Shannon radii tables, and peer-reviewed literature (see `sources` dict on each material entry).

## Validated Test Cases

The test suite (`tests/test_known_cells.py`) verifies:

**GOOD cells (must score high):**
- LFP + Graphite + LiPF6/EC:DMC (standard safe cell)
- NMC811 + Graphite + LiPF6/EC:EMC (standard EV cell)

**KNOWN PROBLEMS (must flag issues):**
- Li metal + liquid carbonate -> dendrite risk flagged
- NMC811 >4.3V + EC -> oxidative decomposition flagged
- Si anode + EC -> 300% expansion tanks mechanical score
- LGPS + NMC811 -> electrochemical instability (3.8V >> 2.1V limit)

## KOMPOSOS Integration

The battery bridge connects to the existing categorical infrastructure:

- **Objects** = Materials (cathodes, anodes, electrolytes, ions)
- **Morphisms** = Electrochemical interfaces (scored by viability)
- **Ricci curvature** = Identifies bottleneck interfaces in the cell graph
- **Persistent homology** = Detects cycles/hysteresis in cycling data
- **Sheaf coherence** = Cross-validates thermodynamic consistency across all interfaces

## Running Tests

```bash
cd KOMPOSOS-III-LAMBDA-max-3D-chem
python -m pytest battery_bridge/tests/ -v
# or individually:
python -m unittest battery_bridge.tests.test_properties
python -m unittest battery_bridge.tests.test_scoring
python -m unittest battery_bridge.tests.test_known_cells
```

## Data Ingestion (Stubs)

`data_ingestion.py` defines interfaces for:
- **Materials Project** (`mp-api`): Crystal structures, voltages, capacities
- **AFLOW**: Thermomechanical properties
- **Battery Archive** (Sandia): Real cycling data

These are stub implementations with TODO markers. To enable:
```bash
pip install mp-api  # Materials Project
# Get API key at https://materialsproject.org/api
```

## Limitations

- Property values are curated from literature; real cells have manufacturing variability
- Scoring is heuristic-based, not physics-simulated (no DFT, no MD)
- SEI/CEI modeling is simplified (real SEI chemistry is extremely complex)
- No temperature-dependent property tables (only modifier functions)
- Solid-state interface contact area not modeled (needs FEM)
- No aging/calendar-life models beyond simple cycle-count modifiers
