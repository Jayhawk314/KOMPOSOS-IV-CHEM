# KOMPOSOS-III Battery Bridge Architecture — Verified by Source
# Last verified: 2026-02-21

## What This Is

A physical-chemical bridge for battery materials engineering, built on the same architecture as the protein contact bridge in `chemistry/`. Instead of scoring amino acid residue contacts, it scores electrochemical material interfaces.

The same categorical infrastructure (StoredObject, StoredMorphism, Ricci curvature, persistent homology, sheaf coherence) applies to both domains.

## Architecture Mapping

| Protein Bridge (`chemistry/`) | Battery Bridge (`battery_bridge/`) |
|---|---|
| Amino acid properties (Kyte-Doolittle, charges) | Material properties (voltage, capacity, conductivity) |
| H-bond scoring (`hydrogen_bonds.py`) | Ion transport scoring (`interaction_scoring.py`) |
| Salt bridge scoring (`electrostatics.py`) | Electrochemical stability scoring |
| Hydrophobic scoring (`hydrophobic.py`) | Interface compatibility scoring (SEI/CEI) |
| Van der Waals scoring (`van_der_waals.py`) | Mechanical compatibility scoring |
| Electrostatic repulsion penalty | Degradation penalty |
| `can_form_hbond(aa1, aa2)` | `validate(material_a, material_b)` |
| HBondMorphism -> StoredMorphism | InterfaceMorphism -> StoredMorphism |
| Protein structure validation | Cell configuration analysis |
| EnergyBreakdown (weighted sum) | InterfaceScore (weighted sum) |
| EnergyWeights | InterfaceWeights |

## Module Structure

```
battery_bridge/
  __init__.py                  # Public API (exports all key types)
  material_properties.py       # 22 materials with real published values
  interaction_scoring.py       # 5 scorers (each returns ScorerResult with 0-1 score)
  interface_validator.py       # BatteryInterfaceValidator (weighted composite)
  battery_flow.py              # Full cell analysis + degradation cascades
  data_ingestion.py            # API stubs for Materials Project, AFLOW, Battery Archive
  integration.py               # Hooks into KOMPOSOS categorical core
  tests/
    test_properties.py         # Material table validation (21 tests)
    test_scoring.py            # Scorer range and correctness (17 tests)
    test_known_cells.py        # Ground-truth cell validation (20 tests)
```

## Data Flow

```
CellConfiguration (cathode, anode, salt, solvents)
  -> BatteryFlowAnalyzer.analyze_cell()
     -> Enumerate all material interfaces
     -> For each interface pair:
        -> score_ion_transport()
        -> score_electrochemical_stability()
        -> score_interface_compatibility()
        -> score_mechanical_compatibility()
        -> score_degradation_penalty()
        -> BatteryInterfaceValidator combines with weights -> InterfaceScore
     -> Find bottleneck (lowest scoring interface)
     -> Predict degradation cascades (from failure modes)
     -> Overall viability = 75% bottleneck + 25% average
  -> CellAnalysis (viability, interfaces, bottleneck, cascades, voltage)
```

## Layer 1: Material Properties (`material_properties.py`)

22 materials with real published values and source citations:

| Category | Materials | Count |
|---|---|---|
| Cathodes | LCO, LFP, NMC811, NMC622, NMC111, LMO | 6 |
| Anodes | Graphite, Li_metal, Si, LTO | 4 |
| Electrolyte Solvents | EC, DMC, DEC, EMC | 4 |
| Electrolyte Salts | LiPF6, LiTFSI | 2 |
| Solid Electrolytes | LLZO, LGPS, Li3PS4 | 3 |
| Ions | Li+, Na+, Mg2+ | 3 |

Key types:
- `BatteryMaterial` dataclass: name, formula, MaterialClass, CrystalStructure, VoltageWindow, theoretical_capacity, ionic_conductivity, volume_expansion, elastic_modulus, thermal_stability_max, failure_modes, sources
- `MaterialClass` enum: CATHODE, ANODE, ELECTROLYTE_SOLVENT, ELECTROLYTE_SALT, SOLID_ELECTROLYTE, ION
- `FailureMode` enum: 13 failure modes (dendrite, SEI growth, volume expansion, O2 release, etc.)

## Layer 2: Interaction Scoring (`interaction_scoring.py`)

Five scorers, each returns `ScorerResult(score: float, label: str, details: Dict)`:

| Scorer | Protein Analogue | What It Checks |
|---|---|---|
| `score_ion_transport()` | H-bond scoring | Conductivity ratio, crystal structure compatibility, channel sizes |
| `score_electrochemical_stability()` | Salt bridge scoring | Electrode voltage vs. electrolyte stability window |
| `score_interface_compatibility()` | Hydrophobic scoring | SEI/CEI formation quality, known good/bad pairs |
| `score_mechanical_compatibility()` | Van der Waals scoring | Volume expansion mismatch, elastic modulus ratio |
| `score_degradation_penalty()` | Electrostatic repulsion | Lookup table of known failure pairings |

Auto-detection: `score_electrochemical_stability()` auto-detects electrode vs. electrolyte roles from MaterialClass so argument order doesn't matter.

## Layer 3: Interface Validation (`interface_validator.py`)

`BatteryInterfaceValidator` combines all 5 scorers into a weighted `InterfaceScore`:

```python
# Default weights (sum to 1.0)
InterfaceWeights(
    ion_transport=0.25,
    electrochemical_stability=0.30,   # Heaviest — voltage mismatch kills cells
    interface_compatibility=0.20,
    mechanical_compatibility=0.10,
    degradation_penalty=0.15,
)
```

Weight presets: `.default()`, `.mechanical_focus()` (solid-state), `.safety_focus()` (degradation-heavy)

Operating condition modifiers (`InterfaceConditions`):
- Temperature >60C: accelerates degradation, improves transport
- Temperature <0C: hurts ion transport
- C-rate >3C: stresses mechanical compatibility
- Cycle number >500: ages interface and degrades SEI

Viability threshold: 0.50 (interface-level)

## Layer 4: Flow Analysis (`battery_flow.py`)

`BatteryFlowAnalyzer` analyzes complete cell configurations:

1. **Interface enumeration**: cathode-solvent, anode-solvent, cathode-salt, anode-salt (liquid cells) or cathode-SE, anode-SE (solid-state)
2. **Bottleneck detection**: lowest-scoring interface
3. **Overall viability**: `0.75 * bottleneck + 0.25 * average` (cell is as strong as its weakest link)
4. **Degradation cascades**: 5 cascade paths predicted from material failure modes
5. **Cell voltage**: cathode nominal - anode nominal

Cell viability threshold: 0.45

Pre-defined cells: `STANDARD_LFP_CELL`, `STANDARD_NMC811_CELL`, `SOLID_STATE_CELL`, `PROBLEMATIC_SI_CELL`, `PROBLEMATIC_LGPS_CELL`

## Layer 5: KOMPOSOS Integration (`integration.py`)

Maps battery concepts into the categorical framework:

- **Objects** = Materials -> `StoredObject` via `material_to_stored_object()`
- **Morphisms** = Interfaces -> `StoredMorphism` via `InterfaceMorphism.to_stored_morphism()`
- **Category** = Material graph -> `build_battery_category()` (objects + viable interface morphisms)
- **Ricci curvature** = `compute_battery_curvature()` on interface graph (negative = bottleneck)
- **Persistent homology** = `analyze_cycling_topology()` on (capacity, voltage) point clouds
- **Sheaf coherence** = `check_thermodynamic_coherence()` across shared interfaces

Entry point: `run_battery_categorical_analysis(config)` runs the full pipeline.

## Layer 6: Data Ingestion (`data_ingestion.py`)

Stub implementations with defined interfaces:

- `MaterialsProjectClient`: crystal structures, voltages, capacities
- `AFLOWClient`: thermomechanical properties
- `BatteryArchiveClient`: real cycling data (Sandia)
- `BatteryDataIngestion`: unified interface

All methods currently raise `NotImplementedError`. To enable: `pip install mp-api`.

## Design Decisions

1. **Heuristic scoring, not DFT/MD**: Real DFT calculations take hours per interface. Heuristic scoring enables rapid screening of thousands of material combinations. The scoring encodes the same physical intuitions a battery engineer uses.

2. **75/25 bottleneck/average weighting**: A cell fails at its weakest interface (like a chain). The bottleneck dominates, but multiple weak interfaces compound.

3. **Auto-detect electrode/electrolyte roles**: `score_electrochemical_stability()` checks MaterialClass to determine which material is the electrode and which is the electrolyte. This prevents argument-order bugs.

4. **Condition modifiers, not condition tables**: Temperature/C-rate effects are applied as multipliers to base scores rather than maintaining separate property tables for each condition.

5. **Mirrors protein bridge exactly**: Same patterns (dataclass properties, scorer functions returning 0-1, weighted composite, morphism bridge to categorical store) so developers familiar with one bridge can immediately understand the other.

## Verified Status (58/58 tests pass)

```
test_properties.py  — 21 tests: material existence, property ranges, class membership
test_scoring.py     — 17 tests: scorer ranges [0,1], known good/bad pairings
test_known_cells.py — 20 tests: cell viability, voltages, conditions, integration
```

Good cells score high: LFP >0.45, NMC811 >0.40
Bad cells flag correctly: Si (volume expansion), LGPS+NMC811 (voltage mismatch), Li metal+carbonate (dendrites)
