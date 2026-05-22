# KOMPOSOS Web UI: Input Reference Guide

*Complete reference for all valid inputs in text fields*

---

## Quick Reference

| Input Type | Where Used | Examples | Format |
|-----------|------------|----------|--------|
| Chemical Formulas | Composition Predictor, Crystal Dreamer | LiCoO2, NMC811, Li4Ti5O12 | Element symbols + subscripts |
| Material Names | Compatibility Checker, Cell Designer | NMC811, PVDF, Al_foil | Exact names from database |
| Element Symbols | Crystal Dreamer (constraints) | Li, Co, Ni, Mn, Fe, O | Standard periodic table |
| Shorthand Names | Composition Predictor | NMC811, LFP, LGPS | Pre-defined abbreviations |

---

## 1. Chemical Formula Input

**Where:** Composition Predictor (page 3), Crystal Dreamer (page 5), Interpolation

### Valid Element Symbols (41 total)

KOMPOSOS recognizes these elements from the periodic table:

**Alkali & Alkaline Earth:**
- Li, Na, K, Mg, Ca, Ba

**Transition Metals:**
- Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Zr, Nb, Mo, W

**Post-Transition & Metalloids:**
- Al, Ga, Ge, Sn, Pb, Bi, Si

**Lanthanides:**
- La, Ce

**Chalcogens & Halogens:**
- O, S, Se, F, Cl, Br, I

**Pnictogens:**
- N, P, As

**Others:**
- C, H, B

### Formula Syntax

**Basic format:** `Element[subscript]Element[subscript]...`

**Rules:**
- Element symbols are case-sensitive: `Li` ✓, `li` ✗, `LI` ✗
- Subscripts are optional (default = 1): `LiCoO2` = `Li1Co1O2`
- No spaces: `LiCoO2` ✓, `Li Co O2` ✗
- No parentheses (yet): `Li(NiMnCo)O2` ✗ — use expanded form `LiNi0.33Mn0.33Co0.33O2`

**Valid examples:**
```
LiCoO2          # Lithium cobalt oxide (LCO cathode)
LiFePO4         # Lithium iron phosphate (LFP cathode)
Li4Ti5O12       # Lithium titanate (LTO anode)
Li7La3Zr2O12    # LLZO solid electrolyte
NMC811          # Shorthand (auto-expands to LiNi0.8Mn0.1Co0.1O2)
```

**Fractional subscripts:**
```
LiNi0.8Mn0.1Co0.1O2   # NMC811 (long form)
LiNi0.33Mn0.33Co0.33O2  # NMC111
Li1.2Mn0.6Ni0.2O2     # Li-rich NMC
```

### Shorthand Abbreviations

KOMPOSOS recognizes these shorthand names and auto-expands them:

| Shorthand | Expands To | Material Type |
|-----------|-----------|---------------|
| **NMC811** | LiNi0.8Mn0.1Co0.1O2 | Cathode |
| **NMC622** | LiNi0.6Mn0.2Co0.2O2 | Cathode |
| **NMC111** | LiNi0.33Mn0.33Co0.33O2 | Cathode |
| **LFP** | LiFePO4 | Cathode |
| **LCO** | LiCoO2 | Cathode |
| **LMO** | LiMn2O4 | Cathode |
| **NCA** | LiNi0.8Co0.15Al0.05O2 | Cathode |
| **LTO** | Li4Ti5O12 | Anode |
| **LLZO** | Li7La3Zr2O12 | Solid electrolyte |
| **LGPS** | Li10GeP2S12 | Solid electrolyte |
| **LNMO** | LiNi0.5Mn1.5O4 | High-voltage cathode |
| **NASICON** | Na3Zr2Si2PO12 | Sodium electrolyte |

**Usage:** Just type the shorthand in any formula field. The system auto-detects and expands it.

---

## 2. Material Name Input

**Where:** Compatibility Checker (page 1), Cell Designer (page 4), Multi-Domain queries

### Battery Materials (22)

**Cathodes:**
```
LFP, NMC811, NMC622, NMC111, LCO, LMO, NCA
```

**Anodes:**
```
Graphite, Li_metal, Si, LTO
```

**Solid Electrolytes:**
```
LLZO, LGPS, Li3PS4, NASICON
```

**Liquid Components:**
```
LiPF6, LiTFSI, EC, DMC, PC
```

### Polymer Materials (33)

**Commodity:**
```
PE, PP, PVC, PS, PET, Nylon-6, Nylon-66
```

**Engineering:**
```
PC, PEEK, PEI, PSU, PPO, POM, ABS
```

**Fluoropolymers:**
```
PTFE, PVDF, FEP, ETFE, PFA
```

**Elastomers:**
```
NR, SBR, NBR, EPDM, Silicone
```

**Battery-Specific:**
```
PEO, PAN, CMC, PVDF, Nafion
```

### Metal Materials (36)

**Pure Metals:**
```
Fe, Al, Cu, Ti, Ni, Zn, Mg, W, Mo, Sn, Pb, Ag, Au, Pt
```

**Steels:**
```
SS_304, SS_316, Steel_1018, Steel_4140, Tool_A2, Maraging_300, Cast_Iron
```

**Aluminum Alloys:**
```
Al_6061, Al_7075, Al_2024, Al_5052
```

**Copper Alloys:**
```
Brass_C260, Bronze_C510, BeCu_C172
```

**Titanium Alloys:**
```
Ti6Al4V, CP_Ti_Gr2
```

**Nickel Alloys:**
```
Inconel_625, Inconel_718, Hastelloy_C276
```

**Battery Foils:**
```
Al_foil, Cu_foil, Ni_tab
```

### Ceramic Materials (28)

**Oxides:**
```
Al2O3, ZrO2_YSZ, ZrO2_PSZ, MgO, TiO2, SiO2, BaTiO3, Mullite, Spinel
```

**Carbides:**
```
SiC, WC, B4C, TiC
```

**Nitrides:**
```
Si3N4, AlN, BN_hex, TiN
```

**Glass-Ceramics:**
```
Borosilicate, Soda_Lime, LAS
```

**Bioceramics:**
```
Hydroxyapatite, TCP, Bioglass
```

**Others:**
```
PZT, LLZO, LGPS, Li3PS4, NASICON
```

### Semiconductor Materials (27)

**Elemental:**
```
Si, Ge, C_diamond
```

**IV-IV:**
```
SiGe, SiC_4H, SiC_6H
```

**III-V:**
```
GaAs, AlAs, AlGaAs, InP, InAs, InGaAs, GaP, InSb, GaN, AlN, AlGaN, InN
```

**II-VI:**
```
ZnO, CdTe, ZnSe, HgCdTe
```

**Others:**
```
Ga2O3, IGZO, MoS2, WS2, Bi2Te3
```

### Glass Materials (23)

**Soda-Lime:**
```
Float, Container, Tempered
```

**Borosilicate:**
```
Boro_33, Boro_51, Neutral
```

**Aluminosilicate:**
```
Display, ChemStrength
```

**Lead:**
```
Crystal, Dense_Flint
```

**Fused Silica:**
```
FusedSilica, QuartzGlass
```

**Optical:**
```
BK7, F2, LAK9
```

**Bioactive:**
```
Bioglass_45S5, S53P4
```

**Chalcogenide:**
```
As2S3, Ge28Sb12Se60
```

**Glass-Ceramic:**
```
LAS_Zerodur, LAS_Cooktop
```

**Specialty:**
```
LaserPhosphate, ZBLAN
```

### MOF Materials (30)

**ZIF Family:**
```
ZIF-8, ZIF-67, ZIF-90
```

**UiO Family:**
```
UiO-66, UiO-67, UiO-68
```

**MIL Family:**
```
MIL-53, MIL-88, MIL-101, MIL-125
```

**IRMOF Family:**
```
IRMOF-1, IRMOF-3
```

**Others:**
```
HKUST-1, MOF-5, MOF-74, NOTT-101, NU-1000, PCN-222, PCN-224
UTSA-16, ZJU-5, Mg-MOF-74, Co-MOF-74, CPO-27-Ni
DUT-8, MIL-100, MIL-110, CAU-10, SIFSIX-3-Ni
```

---

## 3. Molecule Name Input

**Where:** Compatibility Checker (Molecule Search), Molecular Compatibility API

### 37 Molecules by Class

**Solvents (12):**
```
EC, DMC, DEC, EMC, PC, GBL, NMP, THF, Acetone, Ethanol, Water, Toluene
```

**Salts (6):**
```
LiPF6, LiTFSI, LiBF4, LiClO4, NaPF6, KFSI
```

**Monomers (7):**
```
Styrene, MMA, Ethylene, Propylene, VDF, Acrylonitrile, Caprolactam
```

**Reagents (6):**
```
H2SO4, NaOH, HCl, NH3, H2O2, Acetonitrile
```

**Coatings (3):**
```
PDMS, Parylene_C, SiO2_sol
```

**Gases (3):**
```
H2, O2, CO2
```

---

## 4. Element Constraint Input

**Where:** Crystal Dreamer (page 5) - "Allowed/Excluded Elements"

### Format

**Comma-separated element symbols:**
```
Li, Co, Ni, Mn, O       # Only use these elements
F, Cl, Br, I            # Exclude all halogens
```

**Rules:**
- Use standard periodic table symbols (case-sensitive)
- Separate with commas: `Li, Co, O` ✓
- Spaces optional: `Li,Co,O` also works
- No brackets or quotes: `[Li, Co]` ✗, `"Li"` ✗

**Common constraints:**

```
# Cobalt-free cathodes
Excluded: Co

# PFAS-free (no fluorine)
Excluded: F

# Transition metal only
Allowed: Ti, V, Cr, Mn, Fe, Co, Ni, Cu

# Earth-abundant elements
Allowed: Fe, Mn, O, N, C, S, P

# No heavy metals
Excluded: Pb, Cd, Hg, Tl
```

---

## 5. Numerical Input

**Where:** Crystal Dreamer (property targets), MOF Explorer (operating conditions)

### Property Targets (Crystal Dreamer)

| Property | Unit | Typical Range | Example |
|----------|------|---------------|---------|
| Voltage | V | 1.5 - 5.0 | 3.8 |
| Capacity | mAh/g | 100 - 300 | 170 |
| Thermal stability | °C | 200 - 800 | 300 |
| Ionic conductivity | S/cm | 1e-6 - 1e-2 | 0.001 |

**Format:** Plain numbers, no units in field
```
Min voltage: 3.5      # Target >= 3.5 V
Max voltage: 4.5      # Target <= 4.5 V
```

### Operating Conditions (MOF Explorer)

| Parameter | Unit | Range | Default |
|-----------|------|-------|---------|
| Operating temp | °C | -50 to 800 | 25 |
| Operating pressure | bar | 0.01 to 500 | 1.0 |
| Molecule diameter | Angstrom | 0 to 50 | 0 (skip) |

---

## 6. Common Errors and Fixes

### ❌ Invalid Input → ✅ Valid Input

**Chemical Formulas:**
```
❌ li co o2          → ✅ LiCoO2
❌ LI CO O2          → ✅ LiCoO2
❌ Li-Co-O2          → ✅ LiCoO2
❌ Li(Co)O2          → ✅ LiCoO2
❌ nmc811            → ✅ NMC811
```

**Material Names:**
```
❌ nmc 811           → ✅ NMC811
❌ Lfp               → ✅ LFP
❌ stainless steel   → ✅ SS_304 (or SS_316)
❌ aluminum          → ✅ Al (element) or Al_6061 (alloy)
❌ PVDF binder       → ✅ PVDF
```

**Element Symbols:**
```
❌ lithium           → ✅ Li
❌ cobalt            → ✅ Co
❌ manganese         → ✅ Mn
❌ Iron              → ✅ Fe (case-sensitive!)
```

**Molecule Names:**
```
❌ ethylene carbonate → ✅ EC
❌ dimethyl carbonate → ✅ DMC
❌ lithium salt       → ✅ LiPF6 (or LiTFSI, LiBF4, etc.)
```

---

## 7. Pro Tips

### Copy-Paste from Literature

When copying formulas from papers, watch for:
- **Superscripts mistaken for subscripts:** Li⁺ → remove the ⁺
- **Spaces:** Li Co O₂ → LiCoO2
- **Unicode subscripts:** Li₇La₃Zr₂O₁₂ → Li7La3Zr2O12 (convert to normal numbers)

### Unknown Material?

If a material isn't recognized:
1. **Try the chemical formula** instead of the name (Composition Predictor)
2. **Check exact spelling** against the lists above
3. **Use shorthand** if available (NMC811 vs LiNi0.8Mn0.1Co0.1O2)

### Multi-Element Queries

For element constraints, order doesn't matter:
```
Li, Co, O  =  O, Li, Co  =  Co, O, Li
```

---

## Quick Test Examples

Copy these to test each page:

**Composition Predictor:**
```
LiCoO2
NMC811
Li4Ti5O12
LiNi0.8Mn0.1Co0.1O2
```

**Crystal Dreamer:**
```
Min voltage: 3.5
Excluded elements: Co
```

**Compatibility Checker:**
```
Material A: NMC811
Material B: EC
```

**Cell Designer:**
```
Cathode: LFP
Binder: PVDF
Collector: Al_foil
Electrolyte: LiPF6
```

**MOF Explorer:**
```
Target molecule diameter: 3.3
Operating temp: 25
Environment: dry
```

---

## 8. PFAS-Specific Inputs

**Where:** PFAS Scanner (page 2) — all tabs

### Brand Names (Heuristic Detection)

These brand names auto-resolve to base PFAS substances:

| Brand Name | Resolves To | Base PFAS |
|-----------|-------------|-----------|
| Teflon | PTFE | Polytetrafluoroethylene |
| Kynar | PVDF | Polyvinylidene fluoride |
| Viton | FKM | Fluoroelastomer |
| Scotchgard | PFAS (generic) | Perfluorinated treatment |
| Gore-Tex | PTFE | Expanded PTFE membrane |
| Stainmaster | PFAS (generic) | Perfluorinated treatment |
| Chemours | PFAS (generic) | Fluoropolymer manufacturer |
| 3M Novec | PFAS (generic) | Fluorinated fluid |
| Dyneon | PFAS (generic) | Fluoropolymer brand |
| Daikin | PFAS (generic) | Fluoropolymer manufacturer |
| Solvay Solef | PVDF | Polyvinylidene fluoride |

**Usage:** Enter the brand name in any material name field. The system auto-detects and resolves it.

### Client Name Input (Compliance Report Tab)

**Where:** PFAS Scanner > Compliance Report tab
**Format:** Free text (e.g., "Acme Corp", "Samsung SDI", "Ateios Systems")
**Purpose:** Brands the PDF report cover page ("Prepared for: [Client Name]") and audit certificate

### BOM Entry Format (Custom Mode)

**Format:** `name | function | quantity_kg`

```
PVDF | cathode binder | 2.5
NMC811 | cathode active | 15.0
Kynar 761 | seal gasket | 0.3
Carbon_Black | conductive additive | 1.2
```

**Notes:**
- Function and quantity are optional (omit with `name | |`)
- Brand names work in BOM entries (e.g., "Kynar 761" resolves to PVDF)

---

---

## 9. MOF Designer Inputs (Page 8)

**Where:** MOF Designer (page 8) — Single-page simplified UI

**Purpose:** Generate novel MOF linkers with exact atom count control. Built for **Prof. Heather Kulik** (MIT).

### Main Controls

#### Exact Heavy Atom Count

**Number input** (5-60, default 22):

```
22      # Kulik's sweet spot (computationally tractable for DFT)
18      # Smaller linkers (faster screening)
30      # Larger linkers (more diverse chemistry)
```

**Rules:**
- Must be integer (whole number)
- Range: 5-60 atoms
- Generator produces ONLY molecules with this exact count
- Heavy atoms = C, N, O, S, etc. (excludes hydrogen)

#### Candidates to Generate

**Slider** (20-500, default 100):

```
100     # Default (typical: ~10-20 pass all verdicts)
50      # Fast screening
500     # Exhaustive search (slower)
```

**What it does:** How many novel candidates to generate and score with 5 KOMPOSOS verdicts.

#### Application Context

**Dropdown selector** with 5 Kulik-optimized applications:

| Application | What it means | Key functional groups |
|-------------|--------------|----------------------|
| **CO2 Capture** | Capture CO2 from air or flue gas | Lewis acid sites, polar groups (NH2, COOH), π-π interactions |
| **Gas Storage / Separation** | Store H2/CH4 or separate gas mixtures | High pore volume, thermal/chemical stability |
| **Catalysis** | Catalyze organic reactions (oxidation, coupling) | Active sites, substrate pockets, redox groups |
| **Sensing (VOC, gas)** | Detect volatile organics or gases | π-π interactions, polar groups, selective binding |
| **General MOF Design** | Balanced criteria, no application bias | No template bias |

**Backend mapping:** These map to internal template names (e.g., "CO2 Capture" → `breath_VOC_sensing` template).

#### Required Donor Atoms

**Multiselect** (N, O, S):

```
Nitrogen (N)              # Ensure N-coordinated metal binding
Nitrogen (N), Oxygen (O)  # Require both N and O donor atoms
(empty)                   # No filter (all candidates returned)
```

**What it does:** Post-filters results to only linkers containing ALL selected coordinating atoms. Example: Kulik wants "binding to the metal with two nitrogen atoms" → select Nitrogen.

### Advanced Settings (collapsed expander)

#### Exclude Elements

**Multiselect** (H, B, C, N, O, F, Si, P, S, Cl, Br, I):

```
F, Cl           # Halogen-free linkers
F               # PFAS-free (no fluorine)
S, P            # Sulfur/phosphorus-free
```

**What it does:** Removes candidates containing ANY of the selected elements.

#### Verdict Filters

**Checkboxes:**

| Filter | Effect |
|--------|--------|
| ☑ **Require all 5 verdicts AGREE** | Only linkers with AGREE on all 5 verdicts (strict, default) |
| ☐ **Allow HOLLOW verdicts** | Include HOLLOW (structurally plausible but logically unsound) for exploratory mode |

**Default:** Require all AGREE (strict mode)

### Output Format

**Export buttons:**

- **Download CSV**: All filtered candidates with verdict columns
- **Download JSON**: Full data with reasoning traces, scores, provenance

**CSV columns:**
```
SMILES,formula,heavy_atoms,MW,N_count,O_count,S_count,morphism_integrity,viable,
synthesizability,toxicity,stability,activity,conductivity
```

**JSON structure:**
```json
[
  {
    "linker_smiles": "c1ccc(cc1)C(=O)...",
    "verdicts": {
      "synthesizability": "AGREE",
      "toxicity": "AGREE",
      "stability": "AGREE",
      "activity": "AGREE",
      "conductivity": "AGREE"
    },
    "verdict_scores": {
      "synthesizability": 0.89,
      "toxicity": 0.92,
      "stability": 0.88,
      "activity": 0.85,
      "conductivity": 0.82
    },
    "morphism_integrity": 0.952,
    "reasoning_traces": {...},
    "overall_viable": true
  }
]
```

### Results Display

**Metrics row:**
| Generated | Passed All Verdicts | After Donor Filter |
|-----------|--------------------|--------------------|
| 100 | 12 | 8 |

**Results table columns:**
- **Formula**: Molecular formula (e.g., C15H11NO4)
- **Atoms**: Heavy atom count (should match your input)
- **MW**: Molecular weight
- **SMILES**: Copyable SMILES string
- **Viable**: "Yes" if all 5 verdicts == AGREE
- **N, O, S**: Donor atom counts
- **Verdicts**: Summary (e.g., "5/5 AGREE")

**Verdict icons:**
- **[OK]** AGREE — Both engines confirm
- **[??]** HOLLOW — Structurally plausible but logically unsound
- **[?]** ORPHAN — Logically forced but compositionally missing
- **[X]** REJECT — Both engines reject

---

## Need Help?

- **Unsure what to type?** Use the dropdown selectors where available (most pages)
- **Getting an error?** Check spelling and capitalization
- **Material not found?** Use chemical formula in Composition Predictor instead
- **Want a new material added?** File an issue with DOI citation for the material properties
- **MOF Designer returning 0 candidates?** Relax constraints (allow HOLLOW, reduce required verdicts, remove element exclusions)

---

*Last updated: 2026-04-16 | KOMPOSOS v1.5.0*
