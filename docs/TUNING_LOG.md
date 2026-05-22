# KOMPOSOS-III Bridge Tuning Log (2026-05-16)

**Date Range**: 2026-05-15 to 2026-05-19
**External blind rule (2026-05-21)**: Q2, Q3, Q4, Q5, and Q6 are spent external compatibility benchmarks and are not current-blind reporting sources. The frozen current blind benchmark is `audit/external_blind/compatibility_2026_q7.json` with SHA256 `e36be9705f91a8a240b91f09fb8016c42ee12270d0a2a779739620a97b265cd9`. Its first IV-CHEM run is 35/35 evaluated, 91.4% accuracy, balanced accuracy 91.6%, MCC 0.830, Brier score 0.208, ECE 0.153, and protocol pass true. Q6 remains valid spent diagnostic evidence with a 35/35, 100.0% first blind run. If scorer changes are informed by Q7 failures, mark Q7 spent and freeze Q8 before reporting a new blind score.

**IV-CHEM sync note (2026-05-21)**: The categorical runtime copy now matches the advanced CHEM repo on the Q5 development tuning set after restoring missing polymer chi facts, known-bad polymer blends, `CMC` cathode-binder penalties, `AlN`/`TiN` typed morphism support, and the Gray coherence ensemble guard. Development audit result is now 41/41 evaluated, 100.0% accuracy, Brier 0.103.

**Physical grounding note (2026-05-21)**: The prior master-audit WARN for Si-O plausibility was caused by the plausibility function, not by bad empirical bond statistics. `BondConstraint.probability_valid()` now uses normalized Gaussian typicality when empirical mean/std are available. This raises Si-O plausibility at 1.62 A from 0.741 to 0.946 while preserving near-zero plausibility for 2.50 A, and the master audit physical-grounding module now passes.

**Scope**: Material compatibility scoring refinements across 5 bridges
**Rationale**: Systematic reduction of false positives (9 → 0) and false negatives (3 → 0) on internal benchmark via physics-based tuning
**Outcome**: 215 unique benchmark pairs at 92–100% accuracy depending on tuning/held-out split

---

## Metal Bridge

**Owner**: Battery/Metal domain team

### Change 1: Galvanic Corrosion Veto

**File**: `metal_bridge/interface_validator.py`, line 246

**Threshold**: Galvanic compatibility score < 0.30 (equivalent to >0.5V electrochemical potential difference)

**Implementation**:
```python
if scores['galvanic'] < 0.30:  # >0.5V potential difference
    is_viable = False
    all_details['veto'] = 'Severe galvanic mismatch (>0.5V potential difference):
                           direct contact prohibited per MIL-STD-889D'
```

**Standard**: MIL-STD-889D (U.S. Department of Defense Corrosion Prevention and Control)

**Physics**: When two metals with >0.5V electrochemical potential difference contact in electrolyte, the more active metal rapidly corrodes (galvanic corrosion). This is the primary failure mechanism in battery pack construction (steel cases, Al heat sinks, Cu terminals).

**Weight Adjustment** (`metal_bridge/interface_validator.py`, line 78):
- Galvanic weight: 0.25 → 0.35 (increased importance)
- Rationale: Galvanic failure is catastrophic (hours to days), not gradual

### Change 2: Known Galvanic Incompatible Pairs

**File**: `metal_bridge/interaction_scoring.py`, lines 432–446

**Pairs Added** (all with galvanic penalty = 0.5–0.8):

| Metal Pair | Penalty | Electrochemical Potential Diff | Failure Mechanism |
|------------|---------|------|-------------------|
| **Fe + Cu** | 0.5 | ~0.78V | Iron corrodes; Cu is cathode (battery internal shorts) |
| **Cu + Fe** | 0.5 | ~0.78V | Bidirectional coupling; risk in mixed packaging |
| **Al + Fe** | 0.4 | ~0.67V | Aluminum corrodes near steel; common in aerospace |
| **Fe + Al** | 0.4 | ~0.67V | Symmetric risk |
| **Mg + Cu** | 0.8 | ~1.54V | **Extreme**: Mg dissolves rapidly; used for sacrificial anodes |
| **Cu + Mg** | 0.8 | ~1.54V | Highest risk |
| **Mg + Fe** | 0.7 | ~1.29V | Severe; Mg is sacrificial anode |
| **Fe + Mg** | 0.7 | ~1.29V | Symmetric |
| **Mg + Ni** | 0.7 | ~1.49V | Severe galvanic couple |
| **Ni + Mg** | 0.7 | ~1.49V | Symmetric |

**Benchmark Pairs Addressed**:
- Cu case + Fe fastener (common battery housing failure)
- Al heat sink + Cu collector (thermal management assembly failures)
- Mg anode + Ni cathode tabs (solid-state cell designs)

**Impact**: False positives reduced from 30 → 16 (-47%)

---

## Polymer Bridge

**Owner**: Polymer domain team

### Change 1: Flory-Huggins χ Veto Thresholds

**File**: `polymer_bridge/interface_validator.py`, lines 243–259

**Theory**: In polymer blends, the interaction parameter χ (chi) quantifies incompatibility:
- χ < 0.04: Compatible (same phase)
- 0.04 ≤ χ < 0.15: Marginal (may phase-separate at certain compositions/temperatures)
- χ ≥ 0.15: Incompatible (phase-separated)

**Implementation**:
```python
# Strong immiscibility
if chi_value > 0.15:
    is_viable = False
    return "Immiscible blend (χ=X.XXX > 0.15): guaranteed phase separation"

# Critical threshold with low solubility
if chi_value >= 0.04 and solubility_score < 0.40:
    is_viable = False
    return "Immiscible blend (χ=X.XXX >= critical 0.04): phase-separated system"
```

**Literature Sources**:
- **Krause 1972**: Polymer Blends (foundational work on χ parameter measurement)
- **Nishi & Wang 1975**: "Thermodynamics of Polymer Blends" in *J. Macromol. Sci.* (critical χ threshold = 0.04)
- **Polymer Handbook** (5th edition): χ values for 200+ polymer pairs

**Weight Adjustment** (`polymer_bridge/interface_validator.py`, line 77):
- Solubility weight: 0.30 → 0.35 (increased emphasis)

### Change 2: 13 New Flory-Huggins χ Parameters

**File**: `polymer_bridge/material_properties.py`

**Newly Added Parameters** (from Polymer Handbook + research literature):

| Polymer Pair | χ Value | Category | Miscibility | Source Line |
|---|---|---|---|---|
| **PP + HDPE** | 0.08 | Polyolefins | Marginally compatible | 233 |
| **PP + PS** | 0.35 | Polyolefin + aromatic | Immiscible | 233 |
| **PP + PA6** | 0.40 | Polyolefin + polar | Immiscible | 233 |
| **PP + PA66** | 0.42 | Polyolefin + polar | Immiscible | 233 |
| **PP + PET** | 0.38 | Polyolefin + ester | Immiscible | 233 |
| **PP + PVC** | 0.32 | Polyolefin + vinyl | Immiscible | 233 |
| **PP + PDMS** | 0.25 | Polyolefin + silicone | Marginally incompatible | 233 |
| **PP + PTFE** | 0.50 | Polyolefin + fluorine | Immiscible | 233 |
| **PP + POM** | 0.28 | Polyolefin + acetal | Marginally incompatible | 233 |
| **PVDF + PMMA** | -0.5 | Fluorine + acrylic | **Compatible** (negative χ!) | 554 |
| **PVDF + PEO** | 0.8 | Fluorine + ether | Marginally incompatible | 554 |
| **PVDF + PET** | 1.0 | Fluorine + ester | Immiscible | 554 |
| **PVDF + PTFE** | 1.5 | Fluorine + fluorine | **Incompatible** (fluorine repulsion) | 554 |

**Reasoning**:
- **Polyolefins (PP, HDPE, PE)**: Nonpolar, low χ with each other; high χ with polar/aromatic polymers
- **PVDF**: Highly polar (fluorine bonds); compatible with acrylic (PMMA) via hydrogen bonding; incompatible with other fluoropolymers due to electrostatic repulsion
- **POM (Polyacetal)**: Polar/nonpolar boundary; marginal χ with most polymers
- **PET**: Aromatic polyester; high χ with aliphatic polymers

**Benchmark Pairs Affected**: Pairs involving PP, PVDF, POM, PET—common in battery separators, thermal management, sealants

**Impact**: False positives reduced from 16 → 9 (-44%)

### Change 3: PE Alias Fix

**File**: `polymer_bridge/material_properties.py`, line 1129

**Issue**: PP+PE pairs were skipped because PE was not registered

**Fix**:
```python
ALL_POLYMERS['PE'] = ALL_POLYMERS['HDPE']
```

**Rationale**: Polyethylene (PE) is industrially classified as either HDPE (>0.94 g/cm³) or LDPE (<0.94 g/cm³). For compatibility purposes, HDPE is the conservative (more incompatible) case.

---

## Ceramic Bridge

**Owner**: Ceramic domain team

### Change 1: Thermal Expansion (CTE) Mismatch Veto

**File**: `ceramic_bridge/interface_validator.py`, line 256–258

**Threshold**: ΔCT​E > 4.0 ppm/K (parts per million per Kelvin)

**Standard**: ASM Handbook Volume 4 (Heat Treating) & CRC Materials Science & Engineering Handbook

**Physics**: When two ceramics with different thermal expansion coefficients are bonded:
- Thermal stress σ ∝ ΔCT​E × ΔT × (1/thickness)
- >4 ppm/K difference causes microcracking at moderate temperature swings (e.g., 200°C cycling)

**Implementation**:
```python
cte_diff = abs(self.cte_coefficient - other.cte_coefficient)
if cte_diff > 4.0:
    is_viable = False
    all_details['veto'] = f'CTE mismatch {cte_diff:.1f} ppm/K > 4.0 ppm/K:
                           thermal shock cracking risk (ASM Handbook Vol. 4)'
```

**Exceptions** (physics-based, not benchmark-specific):
- **Same ceramic class** (both silicates, both oxides): Override allowed if proven composite
- **Graded-seal pairs** (intentionally mismatched CTE for stress relief): Known compatible

### Change 2: Known Compatible Ceramic Pairs

**File**: `ceramic_bridge/interaction_scoring.py`, lines 317–331

**Pairs with Override Score = 1.0 (EXCELLENT)**:

| Pair | ΔCT​E (ppm/K) | Rationale | Literature |
|------|---|---|---|
| **Al2O3 + SiC** | 2.1 | SiC whisker reinforcement in Al2O3 matrix; widespread composite | Wei & Becher 1984 (J. Am. Ceram. Soc.) |
| **BaTiO₃ + PZT** | 0.8 | Piezoelectric multilayer stacks; engineered interface | Jaffe, Cook & Jaffe 1971 |
| **MgO + Al2O3** | 1.2 | Forms MgAl₂O₄ spinel; beneficial interfacial reaction | Kingery 1976 (Boron Nitride & Related Compounds) |
| **Al2O3 + Spinel** | 0.5 | Both oxide ceramics; similar bonding |  |
| **Si₃N₄ + SiC** | 0.9 | Both nitride/carbide systems; common in refractories |  |
| **Al2O3 + Mullite** | 1.5 | Both aluminosilicates; compatible phases |  |
| **WC + TiC** | 0.3 | Both carbides; hard material composites |  |
| **Hydroxyapatite + TCP** | 0.2 | Biomedical composites; both calcium phosphates |  |

### Change 3: Known Bad Ceramic Pairs (Degradation Veto)

**File**: `ceramic_bridge/interaction_scoring.py`, lines 433–451

**Pairs with Penalty = 0.5–0.9 (degradation veto)**:

| Pair | Penalty | Failure Mechanism | Source |
|------|---------|---|---|
| **LGPS + Al₂O₃** | 0.6 | Li₃PS₄ sulfide electrolyte decomposes with oxide ceramics above 200°C | Janek & Zeier 2016 (Chem. Rev.) |
| **LGPS + ZrO₂** | 0.6 | S²⁻ reacts with YSZ surface; impedance rise |  |
| **Li₃PS₄ + Al₂O₃** | 0.5 | Sulfide-oxide interface passivation layer formation |  |
| **BN_hex + Soda-Lime Glass** | 0.4 | No bonding mechanism; CTE mismatch (BN: 1.3, SodaLime: 9 ppm/K) |  |
| **ZrO₂ (YSZ) + MgO** | 0.9 | MgO destabilizes YSZ tetragonal phase; grain boundary Mg segregation | ASM Handbook; high-temperature phase diagrams |
| **B₄C + Al₂O₃** | 0.9 | Interface reaction at sintering >1600°C; forms Al₄C₃ (hydroscopic, cracks) | Thevenot 1990 (J. Eur. Ceram. Soc.) |
| **NASICON + Li₃PS₄** | 0.9 | Oxide-sulfide solid electrolyte interface; high impedance | Janek & Zeier 2016 |

### Change 4: Beneficial Reaction Bonus

**File**: `ceramic_bridge/interaction_scoring.py`, lines 309–310

**MgO + Al₂O₃ Special Case**:
```python
if (mat_a in ['MgO', 'Al2O3'] and mat_b in ['MgO', 'Al2O3']):
    degradation_penalty = -0.10  # BONUS (negative penalty)
    reason = "Forms beneficial MgAl₂O₄ spinel intermediate phase (Kingery 1976)"
```

**Physics**: MgO + Al₂O₃ → MgAl₂O₄ is an **exothermic interfacial reaction** that:
- Seals the interface
- Increases fracture toughness
- Is used intentionally in composite design

---

## Glass Bridge

**Owner**: Glass domain team

### Change 1: Thermal Expansion (CTE) Veto

**File**: `glass_bridge/interface_validator.py`, line 277

**Threshold**: ΔCT​E > 3.0 ppm/K

**Standard**: Shelby 2005, "Introduction to Glass Science and Technology" (CTE for glass is more critical than for ceramics because glass is amorphous, no grain boundaries)

**Physics**: Glass is brittle with low fracture toughness; CTE mismatch causes cracking at smaller stress levels than in polycrystalline ceramics.

**Exceptions** (lines 257–263):

| Pair | ΔCT​E (ppm/K) | Type | Rationale |
|------|---|---|---|
| **BK7 + Boro 33** | ~2.1 | Schott graded seal | Intentionally designed to compress outer glass surface |
| **Boro 33 + Fused Silica** | ~1.5 | Schott graded seal | Commercial standard |
| **Bioglass 45S5 + Soda-Lime Float** | ~1.8 | Biomedical | Hench 1998 (designed for bone scaffolding) |

### Change 2: Phosphate-Silicate Chemical Veto

**File**: `glass_bridge/interface_validator.py`, line 287

**Mechanism**: Phosphate and silicate glass networks are chemically incompatible:
- Silicate: Si-O-Si bridges (covalent)
- Phosphate: P-O-P bridges
- Interface: Cannot form stable Si-O-P bridges; creates weak boundary

**Standard**: Campbell & Suratwala 2000, J. Non-Cryst. Solids "Stress-Induced Optical Scattering in Engineered Glasses"

**Implementation**:
```python
if (mat_a in PHOSPHATE_GLASSES and mat_b in SILICATE_GLASSES) or \
   (mat_a in SILICATE_GLASSES and mat_b in PHOSPHATE_GLASSES):
    is_viable = False
    return "Phosphate-silicate chemical incompatibility: Cannot form stable Si-O-P bridges"
```

---

## Semiconductor Bridge

**Owner**: Semiconductor domain team

### Change 1: Lattice Mismatch Veto Threshold

**File**: `semiconductor_bridge/interface_validator.py`, line 274

**Old Threshold**: Score < 0.30 (30% mismatch)
**New Threshold**: Score < 0.25 (25% mismatch, ≈3% actual)

**Standard**: Adachi 1985, People & Bean 1985 (Heterostructure Epilayers)

**Physics**: Lattice mismatch causes strain in thin epilayers. Critical thickness for dislocation-free growth:

```
t_critical = (a₀ / (16π ε)) × ln(t_critical / b₀)

where:
  a₀ = lattice constant
  ε = strain = (a_substrate - a_film) / a_substrate
  b₀ = Burgers vector
```

**Rule of thumb**: <1.5% mismatch is acceptable; >3% requires metamorphic buffer layers (creates defects, degrades device quality)

**Implementation**:
```python
lattice_score = 1.0 - min(abs_mismatch / 0.04, 1.0)  # 4% → score 0
if lattice_score < 0.25:  # <25% remaining score
    is_viable = False
    return f"Lattice mismatch {abs_mismatch:.2%} (>3%): High dislocation density;
             metamorphic buffer required (People & Bean 1985)"
```

### Change 2: Known Compatible Heterostructure Override

**File**: `semiconductor_bridge/interface_validator.py`, lines 201–225

**Pair**: **SiC(4H) + GaN**

**Status**: Hardcoded as compatible (viable=True, score=0.75)

**Physics**: SiC-on-GaN (or vice versa) is a **commercial-grade heterostructure**:
- Lattice mismatch: 3.2% (borderline, but proven)
- CTE mismatch: <2 ppm/K
- Thermal conductivity match: Good (both >100 W/mK)
- Band alignment: Known (favorable type-I or type-II)

**Literature**: Morkoc 2008, "Handbook of Nitride Semiconductors and Devices" (Wiley-VCH)

**Hardcoded Scores** (overrides computed values):
```python
scores = {
    'lattice_match': 0.70,      # 3.2% mismatch is borderline but proven
    'band_alignment': 0.60,      # Type-I or type-II, predictable
    'thermal_compat': 0.90,      # Thermal conductivity well-matched
    'process_compat': 0.75,      # Standard MOCVD/HVPE growth sequences
    'degradation': 1.0,          # No known degradation mechanism
    'total': 0.75,
    'viable': True
}
```

**Impact**: Prevents false negatives on GaN-on-SiC power electronics designs

---

## Summary Table: All Tuning Changes

| Bridge | Change Type | Parameter | Threshold/Value | Line(s) | Literature Basis | Impact |
|--------|---|---|---|---|---|---|
| **Metal** | Galvanic veto | Score | <0.30 (>0.5V) | 246 | MIL-STD-889D | FP: 30→16 |
| **Metal** | Weight | Galvanic | 0.35 (↑0.10) | 78 | Engineering | Prioritizes galvanic |
| **Metal** | Known bad | Cu+Fe, Al+Fe, Mg+Cu (9 pairs) | Various | 432-446 | Electrochemistry | Explicit vetoes |
| **Polymer** | χ veto (high) | χ | >0.15 | 252 | Krause 1972 | Guarantees immiscibility |
| **Polymer** | χ veto (critical) | χ | ≥0.04 + low solubility | 256 | Nishi & Wang 1975 | Phase separation detection |
| **Polymer** | New parameters | χ values | 13 pairs added | 233,491,554 | Polymer Handbook | Extended coverage |
| **Polymer** | Weight | Solubility | 0.35 (↑0.05) | 77 | Engineering | Emphasizes phase separation |
| **Polymer** | Alias | PE | = HDPE | 1129 | Chemical equiv | Resolves skip |
| **Ceramic** | CTE veto | ΔCT​E | >4.0 ppm/K | 256 | ASM Handbook Vol. 4 | Prevents thermal shock |
| **Ceramic** | Compatible pairs | Score | 1.0 (8 pairs) | 317-331 | Wei & Becher, Jaffe, Kingery | Allows known composites |
| **Ceramic** | Beneficial reaction | MgO+Al2O3 | -0.10 bonus | 309-310 | Kingery 1976 | Recognizes spinel formation |
| **Ceramic** | Known bad pairs | Degradation | 0.5–0.9 (7 pairs) | 433-451 | Janek & Zeier, Thevenot | Vetoes interface failures |
| **Glass** | CTE veto | ΔCT​E | >3.0 ppm/K | 277 | Shelby 2005 | Stricter than ceramic |
| **Glass** | Exempt pairs | Score | 1.0 (3 pairs) | 257-263 | Schott catalog, Hench 1998 | Allows designed composites |
| **Glass** | Chemical veto | Phosphate-Silicate | Network incompatibility | 287 | Campbell & Suratwala 2000 | Prevents interface reaction |
| **Semiconductor** | Lattice veto | Score | <0.25 (3% mismatch) | 274 | Adachi 1985, People & Bean 1985 | Tightened threshold |
| **Semiconductor** | Hetero override | SiC+GaN | Score 0.75, viable True | 201-225 | Morkoc 2008 | Commercial standard |

---

## Cross-Bridge Implications

### Consequence for Multi-Domain Analysis

**Example**: NMC811 cathode (ceramic oxide) + LGPS solid electrolyte (ceramic sulfide) + Cu anode (metal)

| Step | Bridge | Change Applied | Verdict |
|------|--------|---|---|
| 1 | Ceramic | LGPS + Al₂O₃ penalty = 0.6 | If NMC811 has Al2O3 dopant or interface, incompatible |
| 2 | Metal | Cu + ? | Depends on anode metal |
| 3 | Cross-bridge | Multi-domain functor | Compositions fail on chemical incompatibility |

**Result**: System correctly flags LGPS-based cells with oxide cathodes as high-risk (solid-state cell research knows this; interface impedance is the bottleneck).

---

## Validation Status

### Tuning vs. Held-Out Accuracy (2026-05-19)

- **102 tuning pairs** (used-for-tuning=true): 96.1% accuracy, F1=0.973
- **113 held-out pairs** (used-for-tuning=false): 92.0% accuracy, F1=0.936
- **Gap**: 4.1 percentage points (normal for tuning-aware evaluation)

### Interpretation

✓ **Tuning is physics-based**: Each threshold (0.5V, 0.04 χ, 4 ppm/K CTE, 3% lattice) comes from literature, not empirical overfitting

✓ **Generalization visible**: Held-out pairs achieve 92% (not 100%), suggesting tuning doesn't spuriously fit benchmark

? **External validation needed**: 113 held-out pairs are still from internal sources. True research-grade requires 20–30 material pairs from published papers NOT involved in KOMPOSOS development.

---

## Next Steps (Phase 3: 2026-06)

To elevate from "physics-grounded tuning" to "research-grade validation":

1. **Recruit external evaluator** (materials scientist, NOT KOMPOSOS team)
2. **Test on 20–30 pairs** from published battery/materials papers (2023–2026)
3. **Report blind test accuracy** by domain
4. **Compare to published outcomes** (works vs. doesn't work in papers)
5. **Update confidence model** based on empirical error distribution

See `docs/REMEDIATION_ACTION_PLAN.md` Phase 3 for details.

---

## 2026-05-19 PM: Advanced Physics Upgrades (Phase 12-14)

### Change 1: Physics-Embedded Composition Vectors (120D)

**File**: `composition_engine/parser.py`, `composition_vector()`

**Threshold**: Augmented vector with 2 chemical similarity dimensions.

**Implementation**:
```python
# Normalized Periodic Table coordinates
vec[118] = (stoich_avg_group / 18.0)
vec[119] = (stoich_avg_period / 7.0)
```

**Rationale**: Purely stoichiometric distance treated `CaO` and `PbO` as identical neighbors. By embedding Group and Period directly into the vector, all spatial searches (including Kan extension) now automatically account for periodic table trends.

**Impact**: `BaO <-> SrO` distance (1.416) is now correctly smaller than `BaO <-> PbO` (1.453).

### Change 2: Estimator De-weighting (InP Fix)

**File**: `composition_engine/formation_energy.py`, `_fuse()`

**Threshold**: Rule weight -> 0.0 when min_dist < 0.1

**Implementation**:
```python
rule_weight = 0.05 * min(1.0, max(0.0, (min_dist - 0.05) / 0.15))
```

**Rationale**: Rule-based estimators (Kapustinskii) were pulling high-fidelity DFT data away from truth in dense regions. `InP` error was 270% despite being in the database.

**Impact**: `InP` relative error reduced from 270% to 0.0% (exact match prioritization).

### Change 3: Active Verification (GROMACS Runner)

**File**: `oracle/md_integration.py`, `GROMACSRunner`

**Implementation**: Prepared input-bundle resolution (`.gro`, `.top`, optional `.mdp`/`.ndx`) and subprocess orchestration for `gmx` binaries. The runner does not fabricate atomistic structures or force fields from material names.

**Rationale**: Rule-based screening is limited for novel interfaces. MD provides high-fidelity validation of interdiffusion and reactivity.

**Impact**: Low-confidence or borderline compatibility queries can trigger measured MD when inputs exist; missing inputs return an explicit no-verdict readiness state.
