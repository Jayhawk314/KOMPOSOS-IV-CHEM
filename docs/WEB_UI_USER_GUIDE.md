# KOMPOSOS-III Web UI — Complete User Guide

**Interactive Materials Reasoning Interface**

Version: 1.6.0
Date: 2026-05-15
Platform: Streamlit Web Application

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Access Control & Login](#access-control--login)
3. [Home Page](#home-page)
4. [Page 1: Compatibility Checker](#page-1-compatibility-checker)
5. [Page 2: PFAS Scanner](#page-2-pfas-scanner)
6. [Page 3: Composition Predictor](#page-3-composition-predictor)
7. [Page 4: Cell Designer](#page-4-cell-designer)
8. [Page 5: Crystal Dreamer](#page-5-crystal-dreamer)
9. [Page 6: MP Explorer](#page-6-mp-explorer)
10. [Page 7: MOF Explorer](#page-7-mof-explorer)
11. [PDF Report Downloads](#pdf-report-downloads)
12. [Deploying Live (Public URL)](#deploying-live)
13. [Tips & Tricks](#tips--tricks)
14. [Troubleshooting](#troubleshooting)
15. [API Alternative](#api-alternative)

---

## Getting Started

### Launch the Web UI

```bash
# From project root
streamlit run streamlit_app/app.py

# Or if installed via pip
komposos-ui
```

The interface will open in your browser at `http://localhost:8501`.

### System Requirements

- **Python**: 3.11+
- **RAM**: 2GB minimum (4GB+ recommended with Materials Project data)
- **Browser**: Chrome, Firefox, Safari, Edge (modern versions)
- **Internet**: Not required (all computation is local)

### First-Time Setup

1. **Basic use** (175 materials): Works immediately after installation
2. **Full Materials Project** (103K+ structures):
   ```bash
   pip install mp-api
   python scripts/download_mp_data.py --api-key YOUR_KEY
   ```
   Get your API key (free) at: https://next-gen.materialsproject.org/api

---

## Access Control & Login

Every interactive page is gated by a 3-tier access system. The sidebar shows your current tier and remaining uses.

### Three Tiers

| Tier | How to get it | Usage limit | What you see in sidebar |
|------|--------------|-------------|------------------------|
| **Demo** | No code needed (default) | 3 analyses per session | "Demo mode: 3 free analyses remaining" |
| **Voucher** | Enter a client access code | Set per-code (e.g. 20) | "Client Access - 20 analyses remaining" |
| **Admin** | Enter the admin password | Unlimited | "Admin Access - Unlimited" |

### How to Log In

1. Open any page -- the sidebar shows "Demo mode: 3 free analyses remaining"
2. Enter an access code in the **"Access Code"** field in the sidebar
3. Click **"Login"**
4. If valid: tier upgrades, usage counter resets to the code's limit
5. If invalid: "Invalid access code" error, stays in demo mode

### How to Log Out

Click the **"Logout"** button in the sidebar. Resets to demo tier.

### What Happens When You Hit the Limit

The "Run Analysis" / "Check Compatibility" / etc. buttons show a warning:

> "You've reached the free analysis limit. Enter an access code in the sidebar for more, or contact James at komposos@proton.me for full access."

The button stops working until you enter a code or refresh the page (demo counter resets on refresh).

### Setting Up Access Codes (Admin)

Access codes are configured via **environment variables** -- no code changes needed.

```bash
# Set admin password (default: komposos-admin)
export KOMPOSOS_ADMIN_PASSWORD="your-secret-password"

# Set client voucher codes (format: CODE:limit,CODE:limit)
export KOMPOSOS_VOUCHER_CODES="ATEIOS2026:20,CERTIVO2026:10,DEMO2026:5"

# Set demo limit (default: 3)
export KOMPOSOS_DEMO_LIMIT=3
```

**On Railway/Render/Docker**: Set these as environment variables in the platform dashboard.

**In docker-compose.yml**:
```yaml
environment:
  - KOMPOSOS_ADMIN_PASSWORD=your-secret-password
  - KOMPOSOS_VOUCHER_CODES=ATEIOS2026:20,CERTIVO2026:10
  - KOMPOSOS_DEMO_LIMIT=3
```

### For Your 20 Priority Clients

1. Create a unique code for each client (e.g. `ATEIOS2026`, `CERTIVO2026`)
2. Set limit to 10-20 analyses per code
3. Include the code in your cold email: *"Use code ATEIOS2026 to run a full analysis"*
4. Track who's using what by checking which codes are active

### Subscription Upgrade Path

When a client exhausts their voucher, the UI shows the upgrade message. This is your conversion point -- they've seen the value, now offer a subscription.

---

### Home Page

![Home Page](../assets/home_screenshot.png)

### What You See

| Element | Purpose |
|---------|---------|
| **Title** | KOMPOSOS-III Chemistry Engine |
| **Material count** | Shows how many materials are loaded (175 or 103K+) |
| **Validation Status** | Internal benchmark (215 unique pairs) reports **100% accuracy** (tuning) and **92.0% accuracy** (held-out); structure prediction at **96%**. |
| **Active Verification** | Toggle MD verification and provide a GROMACS `.gro`/`.top` bundle or input directory. |
| **Page list** | Quick reference of what each page does |
| **How it works** | Brief explanation of the categorical reasoning approach |
| **Sidebar** | Navigation to all 8 pages + system status |


### Key Information

- **No training data**: This is NOT a neural network. Every prediction uses explicit mathematical formulas.
- **Pure compositional reasoning**: Materials are objects, interactions are morphisms, compatibility is composition.
- **Full provenance**: Every number traces back to a DOI citation or Materials Project ID.

---

## Page 1: Compatibility Checker

**Purpose**: Check if two materials are compatible (e.g., cathode + electrolyte, polymer + metal, ceramic + semiconductor).

### How to Use

#### Step 1: Select Domain
Choose from 6 material domains:
- **Battery** (28 materials): Cathodes, anodes, electrolytes, solid electrolytes
- **Polymer** (33 materials): Binders, separators, encapsulants
- **Metal** (36 materials): Current collectors, coatings, substrates
- **Ceramic** (28 materials): Solid electrolytes, coatings, substrates
- **Semiconductor** (27 materials): Si, GaAs, SiC, etc.
- **Glass** (23 materials): Soda-lime, borosilicate, fused silica, etc.

#### Step 2: Pick Two Materials
- **Material A**: Select from dropdown
- **Material B**: Select a different material (UI prevents selecting the same one)

#### Step 3: Check Compatibility
- **MD Verify**: Toggle on for Molecular Dynamics active verification. Provide a prepared GROMACS `.gro`/`.top` bundle, an input directory, or let the app search `data/gromacs_inputs`; missing inputs produce a no-verdict readiness report.
- Click **"Check Compatibility"** button.

### What You Get

#### 1. Dual-Engine Verdict (NEW)

The system runs two independent engines on every query:

| Engine | Role | Display |
|--------|------|---------|
| **System 2: Categorical Oracle** | Compositional reasoning -- do the morphisms compose? | Green if morphism exists, red if blocked |
| **System 1: ZFC Constraint Verifier** | Constraint audit -- does the current rule set veto the pair? | Green if no vetoes, red if a hard constraint veto fires |

The delta between the two engines is classified:

| Classification | What it means | Visual |
|---------------|---------------|--------|
| **AGREE** | Category score passes and the ZFC constraint verifier finds no veto | Green banner |
| **HOLLOW** | Category theory says yes, but ZFC finds a hard constraint veto (score < 0.20 on at least one axis). | Amber warning |
| **ORPHAN** | ZFC finds no veto, but categorical composite is below threshold. Not ruled out, but structurally weak. | Blue info |
| **REJECT** | Both engines agree: fails. | Red error |

**HOLLOW state**: A material pair can score 0.71 overall but have a single scorer below 0.20. KOMPOSOS surfaces that constraint veto instead of reporting only the aggregate score. There are 29 HOLLOW pairs in the battery domain alone.

**Example HOLLOW**: DEC + Si scores 0.715 (Category Oracle says "morphism exists"), but mechanical_compatibility = 0.13. The ZFC verifier vetoes: "Witness EMPTY -- hard constraint veto." The expandable "Why this matters" box explains the constraint logic.

#### 2. Score Breakdown
Five independent scorers (weights vary by domain):

| Scorer | What it measures | Example (Battery) |
|--------|-----------------|-------------------|
| **Electrochemical** | Voltage window overlap | Do both operate at 3-4V? |
| **Chemical** | CTE mismatch, reactivity | Will they react at interface? |
| **Interfacial** | Contact resistance | Can ions/electrons cross? |
| **Thermodynamic** | Solid-state reactions | Does Li2CO3 form? |
| **Structural** | Crystal structure match | Cubic + cubic better than cubic + hexagonal |

**Threshold markers**:
- Viability threshold: 0.45 (above = compatible)
- Veto threshold: 0.20 (below = ZFC hard constraint veto)

#### 3. Visual Outputs
- **Horizontal bar chart**: Shows component scores side-by-side
- **Data table**: Exact scores with color gradient (red=bad, green=good)
- **Raw JSON** (expandable): Full provenance data + dual-engine classification (delta_type, vetoes, compatible constraints)

### Example: NMC811 + EC (AGREE)

```
Input:
  Domain: Battery
  Material A: NMC811 (cathode)
  Material B: EC (electrolyte solvent)

Dual-Engine Verdict:
  System 2 (Categorical): Morphism EXISTS (score 0.710)
  System 1 (ZFC):         Witness FOUND (5/5 constraints pass)
  Delta: AGREE -- both engines confirm compatibility

Score Breakdown:
  Ion Transport:              0.728
  Electrochemical Stability:  0.887
  Interface Compatibility:    0.534
  Mechanical Compatibility:   0.648
  Degradation Penalty:        0.753
```

### Example: DEC + Si (HOLLOW)

```
Input:
  Domain: Battery
  Material A: DEC (electrolyte solvent)
  Material B: Si (anode)

Dual-Engine Verdict:
  System 2 (Categorical): Morphism EXISTS (score 0.715)
  System 1 (ZFC):         Witness EMPTY (1 veto: Mechanical Compatibility)
  Delta: HOLLOW STATE -- categorical path exists but ZFC finds a constraint veto

  "KOMPOSOS rejects this aggregate-positive result because one explicit
   constraint falls below the hard-veto threshold."
```

---

### Molecule Constraint Search (Same Page)

**NEW in Phase 11**: The Kulik 22-atom challenge.

#### Problem Statement
Prof. Heather Kulik (MIT) challenge:
> "I constantly ask LLMs: design me a ligand with exactly 22 heavy atoms. I can never get an answer that has 22 atoms."

LLMs hallucinate molecules. KOMPOSOS **never** hallucinates — it searches the real database.

#### How to Use

1. **Heavy atom count**: Enter exact number (e.g., 22)
2. **Molecule class** (optional): Filter by solvent, salt, monomer, etc.
3. **Exclude elements** (optional): e.g., "F,Cl" to exclude fluorine and chlorine
4. Click **"Search Molecules"**

#### What You Get

- **If found**: Table of molecules with exact match (name, formula, MW, heavy atoms, class)
- **If not found**: Honest response: "No molecules with exactly N heavy atoms" (NOT a hallucination)
- **Distribution table**: Shows all atom counts in database (0-100 heavy atoms)

#### Example Searches

| Query | Result |
|-------|--------|
| 22 heavy atoms | 0 molecules (correct answer, not a hallucination) |
| 6 heavy atoms | EC, DMC, PC (3 molecules) |
| 8 heavy atoms, exclude F | LiClO4 (1 molecule) |
| Li-containing | LiPF6, LiTFSI, LiBF4, LiClO4 (6 molecules) |

---

### Quick Molecule Selection (Same Page)

**NEW in autocomplete update**: Direct molecule selector for browsing the database.

#### How to Use

1. **Choose molecule** from dropdown (autocomplete-enabled, shows all 37 molecules)
2. Molecules display as: `EC (Ethylene Carbonate) [CID: 7303]` for easy identification

#### What You Get

**Molecule details displayed**:
- Formula (e.g., C3H4O3)
- CAS Number (e.g., 96-49-1)
- PubChem CID (if available)
- SMILES notation
- Molecular class (solvent, salt, monomer, etc.)
- Molecular weight (g/mol)
- Boiling point (°C)
- Melting point (°C)
- Hazard class

**Molecule reference** (expandable):
- All 37 molecules grouped by class
- Quick lookup for CAS numbers and PubChem CIDs

#### Example Use Cases

- **Quick lookup**: Need the CAS number for EC? Select it and see all properties
- **Browse by class**: Expand reference to see all solvents, all salts, etc.
- **Integration**: After viewing details, scroll up to use in constraint search or compatibility check

---

## Page 2: PFAS Scanner

**Purpose**: Screen materials for PFAS (per- and polyfluoroalkyl substances) compliance and find drop-in replacements.

### Why This Matters

- **EU ban**: August 2026 (489 days as of 2026-03-25)
- **US EPA**: October 2026 enforcement
- **Liability**: Using PFAS after ban = fines + lawsuits

### 4 Tabs

---

### Tab 1: Single Material Check

#### How to Use

1. **Material name**: Enter any material (e.g., PVDF, PTFE, Nafion, PEO)
2. **Application context**: Select use case (battery binder, seal/gasket, membrane, etc.)
3. Click **"Check PFAS Status"**

#### What You Get

1. **Status Banner**
   - 🔴 CRITICAL: Banned substance (immediate action required)
   - 🟠 HIGH: Ban in <12 months
   - 🟡 MODERATE: Ban in 12-24 months
   - 🔵 LOW: Under review, no timeline
   - 🟢 CLEAN: Not a PFAS

2. **Details**
   - CAS number
   - Category (fluoropolymer, PFCA, PFSA, etc.)
   - Urgency level
   - Regulatory status (EU, US, Stockholm Convention)

3. **Scored Replacements**
   Table ranked by overall score (0-1):
   - **Performance match** (40% weight): Does it work as well?
   - **Processability** (20% weight): Can you manufacture with it?
   - **Cost factor** (20% weight): Price relative to PFAS (1.0 = same cost)
   - **Availability** (20% weight): Can you buy it commercially?

#### Example: PVDF Battery Binder

```
Input: PVDF, use case = Battery Binder

Output:
  Status: PFAS DETECTED (🟡 MODERATE urgency)
  CAS: 24937-79-9
  Category: Fluoropolymer
  Regulations:
    - EU Universal PFAS Ban (proposed, effective 2027-06-01, 433 days)
    - US EPA under review

  Top 3 Replacements:
    1. CMC+SBR: score=0.84 (performance=0.85, cost=1.20x)
       Citations: Bresser 2018, Li 2020, OECD 2022
    2. PAA: score=0.76 (performance=0.78, cost=1.35x)
    3. Alginate: score=0.62 (performance=0.65, cost=0.80x)
```

---

### Tab 2: Batch Scan

#### How to Use

1. **Enter materials**: One per line in text box
2. Click **"Scan All"**

#### What You Get

1. **Summary Metrics**
   - Materials scanned
   - PFAS found
   - Max urgency level

2. **Per-Material Table** (includes detection tier columns)
   | Material | PFAS | Detection Tier | Resolved Base | Urgency | Category | Replacements |
   |----------|------|---------------|---------------|---------|----------|--------------|
   | NMC811 | No | unknown | — | 🟢 none | — | 0 |
   | PVDF | Yes | exact | PVDF | 🟡 moderate | Fluoropolymer | 6 |
   | Teflon XR | Yes | heuristic | PTFE | 🟡 moderate | Fluoropolymer | 5 |
   | Carbon_Black | No | unknown | — | 🟢 none | — | 0 |

   **Detection tier column**: Shows how each material was identified (exact CAS match, brand name heuristic, or unknown). Brand names like "Teflon" resolve to base substances (PTFE) and get full replacements.

#### Example Use Cases

- **Battery BOM**: Scan entire bill of materials for a Li-ion cell
- **Manufacturing audit**: Screen all materials used in production line
- **Supplier compliance**: Verify vendor-provided materials list

---

### Tab 3: Compliance Report Generator

**NEW in Phase 11**: Enterprise-grade structured reports for regulatory filings.

#### How to Use

1. **Client / Company Name** (optional): Enter the client's name to brand the PDF report (e.g., "Acme Corp"). Appears on cover page and audit certificate.

2. **Select mode**:
   - **Demo**: Pre-loaded 15-material Li-Ion cell BOM
   - **Custom**: Enter your own materials (format: `name | function | quantity_kg`)

3. Click **"Generate Compliance Report"**

4. After the report renders on screen, click **"Download PDF Report"** for a branded PDF.

#### What You Get

**7-Section Structured Report**:

1. **Report ID**: `PFAS-YYYY-MMDD-NNNN` (unique identifier)

2. **Summary Metrics**:
   - Materials screened
   - PFAS detected
   - Clean materials
   - Risk level (CRITICAL, HIGH, MODERATE, LOW, CLEAN)

3. **Detections** (expandable for each PFAS):
   - Material name + function
   - PFAS substance + category
   - Urgency level
   - Regulations violated
   - **Scored replacements** with:
     - Overall score (0-1)
     - Verdict: **VALIDATED** (≥0.7, ≥3 citations), **CAUTION** (≥0.4), **VETOED** (<0.4)
     - Provenance chain (every score has a citation)

4. **Regulatory Timeline**:
   | Jurisdiction | Regulation | Effective Date | Days Remaining |
   |--------------|------------|----------------|----------------|
   | EU | PFHxA restriction (C6) | 2026-10-01 | 189 days |
   | EU | Universal PFAS ban | 2027-06-01 | 433 days |
   | Stockholm | PFOS elimination | 2009-05-22 | -6150 days (PAST) |

5. **Action Plan** (prioritized):
   ```
   Priority 1: PLAN: Evaluate alternatives for proposed-ban substances
               Deadline: 365 days
               Materials: PVDF, PTFE
               Rationale: EU ban in 433 days. Qualification takes 6-12 months.

   Priority 2: VALIDATE: Run pilot tests on VALIDATED replacements
               Deadline: 90 days
               Materials: PVDF
               Rationale: CMC+SBR scored 0.84 with 4 citations. Pilot before full qual.
   ```

6. **Methodology**:
   - Engine version
   - Databases used
   - Scoring formula
   - Verdict rules
   - Caveats

7. **Audit Certificate**:
   - Report ID
   - Generated timestamp
   - Reference date
   - Materials screened
   - PFAS detected
   - Database versions
   - Methodology hash (for reproducibility)

#### Export Options

- **PDF**: Click **"Download PDF Report"** after generating. Produces a branded compliance document with cover page ("Prepared for: [Client Name]"), domain-specific scores (Adhesion, Electrolyte, Thermal, Cathode), narrative recommendations, provenance tables, P0/P1/P2 action plans, and audit certificate. ~50-100 KB, works in all browsers.
- **JSON**: `report.to_dict()` for programmatic access
- **Screenshot**: Use browser print function for tables/charts

---

### Tab 4: PFAS Registry Browser

#### What You See

- **35 PFAS substances** across 7 categories:
  - Fluoropolymers (PVDF, PTFE, FEP, PFA, etc.)
  - PFCAs (PFOA, PFHxA, etc.)
  - PFSAs (PFOS, etc.)
  - PFAS salts
  - Precursors
  - Short-chain PFAS
  - Other fluorinated substances

- **For each substance**:
  - Name
  - CAS number
  - Chemical formula
  - Status (BANNED, RESTRICTED, Under review)

#### Example: Fluoropolymers Category

| Name | CAS | Formula | Status |
|------|-----|---------|--------|
| PVDF | 24937-79-9 | (C2H2F2)n | Under review |
| PTFE | 9002-84-0 | (C2F4)n | Under review |
| FEP | 25067-11-2 | (C2F4)n·(C3F6)m | Under review |
| PFA | 26655-00-5 | (C2F4)n·(C3F5O)m | Under review |
| PFOA | 335-67-1 | C8HF15O2 | BANNED |

---

## Page 3: Composition Predictor

**Purpose**: Predict material properties from **any** chemical formula using Kan extension + Dempster-Shafer fusion.

### How to Use

#### Step 1: Enter Formula

**Two ways to input formulas** (autocomplete-enabled):

1. **Select from library** (left dropdown):
   - 27 shorthands (NMC811, LFP, LLZO, etc.)
   - 175+ known formulas from database
   - Type to filter the list
   - Auto-completes as you type

2. **Enter custom formula** (right text box):
   - Any valid chemical formula
   - Novel compositions (e.g., `LiNi0.7Mn0.15Co0.15O2`)
   - **Custom input overrides selection** if both are filled

**Supported formats**:
- **Full formulas**: `LiCoO2`, `LiFePO4`, `BaTiO3`
- **Shorthands**: `NMC811`, `NMC622`, `LFP`, `LMO`, `LLZO`, `LGPS`
- **Novel compositions**: `LiNi0.7Mn0.15Co0.15O2` (not in database)
- **Fractional stoichiometry**: `Li0.5CoO2`, `NMC811` (expands to fractions)

Click **"Predict Properties"**.

#### Step 2: Review Provenance

**Formula Reference** (expandable): Shows all 27 shorthands + 175+ known materials
- Shorthands section: `NMC811 → LiNi0.8Mn0.1Co0.1O2`
- Known materials section: First 40 formulas displayed, full list available in autocomplete

Example shorthands:
```
NMC811  -> LiNi0.8Mn0.1Co0.1O2
NMC622  -> LiNi0.6Mn0.2Co0.2O2
LFP     -> LiFePO4
LMO     -> LiMn2O4
LLZO    -> Li7La3Zr2O12
LGPS    -> Li10GeP2S12
```

### What You Get

#### 1. Elemental Composition
Pie chart + table showing element fractions:
| Element | Fraction |
|---------|----------|
| Li | 0.167 |
| Ni | 0.133 |
| Mn | 0.025 |
| Co | 0.025 |
| O | 0.333 |

#### 2. Predicted Properties
Table with confidence intervals and explicit **Evidence Levels**:
- 🟢 **Categorical Ground Truth**: Exact match in database.
- 🟢 **Dense Interpolation**: Close chemical neighbors exist.
- 🟡 **Moderate Extrapolation**: Reliable for screening.
- 🔴 **Sparse Discovery**: Novel chemistry, interpret as hypothesis.
- 🔴 **Heuristic Estimate**: Rule-based "educated guess."

**Color coding**: Green = high confidence, yellow = moderate, red = low. Hover over values to see **heuristic error bar** explanations.

#### 3. Nearest Known Materials

Shows which materials were used for Kan extension:

| Material | Distance |
|----------|----------|
| NMC811 | 0.1200 |
| NMC622 | 0.1800 |
| NMC111 | 0.4700 |

Distance = composition space distance (sum of absolute differences in element fractions)

#### 4. Predicted Crystal Structure

Rule-based + Kan vote + Goldschmidt tolerance factor:

```
Type: layered
Confidence: 98%
Goldschmidt t: 0.923
Sources: rule=layered, kan=layered, goldschmidt=cubic
```

#### 5. Derived Crystal Structure (Materials Project)

**NEW in Phase 10**: Full lattice parameters via Kan extension over 103K+ MP structures.

```
Crystal System: Hexagonal
Space Group: R-3m (#166)
Confidence: 87%

Lattice Parameters:
  a = 2.8234 Å    α = 90.00°
  b = 2.8234 Å    β = 90.00°
  c = 14.2341 Å   γ = 120.00°
  Volume/atom = 9.87 Å³

Provenance: Kan extension over 5 nearest MP entries (mp-18767, mp-19326, ...)

Nearest MP Structures:
  mp-18767  LiNiO2    dist=0.0845  weight=42.3%  Hexagonal  R-3m
  mp-19326  LiCoO2    dist=0.0912  weight=31.2%  Hexagonal  R-3m
  mp-19395  LiMnO2    dist=0.1123  weight=18.5%  Hexagonal  R-3m
```

**Key differentiator**: Every lattice parameter traces back to specific MP structures with exact weights. No black box.

#### 6. Formation Energy & Synthesizability

```
Formation Energy: -1.73 eV/atom
  ✅ Negative Ef: thermodynamically favorable

Synthesizability Score: 0.92
  ✅ High synthesizability (>0.7)
```

**Synthesizability factors** (shown in details):
- DFT formation energy (if available)
- Kapustinskii estimate (if ionic)
- Miedema estimate (if metallic)
- ZFC constraints (5 checks: voltage, thermal, chemical, radius ratio, electronegativity)
- Known material similarity

---

### Interpolation Tool (Same Page)

**Purpose**: Explore the composition space between two known materials.

#### How to Use

1. **Formula A**: Select from library or enter custom (autocomplete-enabled)
   - Example from library: `LiCoO2`
   - Example custom: `LiNi0.9Mn0.05Co0.05O2`
2. **Formula B**: Select from library or enter custom (autocomplete-enabled)
   - Example from library: `LiNiO2`
   - Example custom: `LiMn2O4`
3. **Fraction slider**: 0.0 (pure A) to 1.0 (pure B)
4. Click **"Interpolate"**

**Autocomplete tip**: Both inputs use the same two-column layout as main prediction (dropdown + custom text)

#### What You Get

Interpolated formula + predicted properties:

```
Fraction = 0.5
Interpolated formula: LiNi0.5Co0.5O2

Properties:
  Voltage: 3.87 V (confidence 82%)
  Capacity: 210 mAh/g (confidence 75%)
  Thermal: 395°C (confidence 68%)
```

#### Use Cases

- Explore NMC composition space (Ni-Mn-Co ratios)
- Optimize voltage vs stability tradeoff
- Predict properties before synthesis

---

## Page 4: Cell Designer

**Purpose**: Design multi-domain battery cells and identify bottleneck interfaces.

### How to Use

#### Step 1: Select Preset (Optional)
Choose from 4 presets:
- **Custom**: Start from scratch
- **Standard Liquid Cell (LFP + EC)**: Traditional Li-ion
- **Solid-State (NMC811 + LLZO)**: High-voltage solid-state
- **Solid-State (LFP + LGPS)**: Safer solid-state
- **High-Voltage (NMC622 + LLZO)**: Balanced performance

#### Step 2: Configure Cell

4 components:

1. **Cathode** (battery domain): NMC811, NMC622, LFP, LMO, etc.
2. **Electrolyte** (solid or liquid):
   - Solid: LLZO, LGPS, LiPON, etc.
   - Liquid: EC, DMC, EMC, LiPF6, etc.
3. **Binder** (polymer domain): PVDF, PEO, CMC, SBR, etc.
4. **Collector** (metal domain): Al, Cu, Ni, stainless steel, etc.

#### Step 3: Advanced Options (Expandable)

- **Scoring mode**:
  - **Auto**: Bottleneck for ≤2 interfaces, Weighted for >2
  - **Bottleneck**: `0.75 × min + 0.25 × avg` (strict)
  - **Weighted**: Bottleneck gets 0.5× weight (balanced)

- **Viability threshold**: Default 0.50 (adjustable 0-1)

#### Step 4: Analyze
Click **"Analyze Cell Design"**.

### What You Get

#### 1. Overall Verdict

✅ **Viable**: Overall score ≥ 0.50
```
Cell Design Viable
Overall Score: 0.86 (threshold: 0.50)
```

❌ **Not Viable**: Overall score < 0.50
```
Cell Design Not Viable
Overall Score: 0.43 (threshold: 0.50)
Fix the bottleneck interface to improve viability.
```

#### 2. Metrics Row

| Overall Score | Domains | Interfaces | Bottleneck |
|---------------|---------|------------|------------|
| 0.86 | battery, polymer, metal, ceramic | 6 | NMC811-LLZO |

#### 3. Interface Scores Table

All pairwise interfaces evaluated:

| Interface | Functor | Score | Compatible |
|-----------|---------|-------|------------|
| NMC811 <-> LLZO | battery-battery | 0.86 | Yes |
| NMC811 <-> PEO | battery-polymer | 0.92 | Yes |
| NMC811 <-> Cu | battery-metal | 0.78 | Yes |
| LLZO <-> PEO | ceramic-polymer | 0.88 | Yes |
| LLZO <-> Cu | ceramic-metal | 0.71 | Yes |
| PEO <-> Cu | polymer-metal | 0.94 | Yes |

**Functor column**: Shows which cross-bridge module was used.

#### 4. Visual Bar Chart

Horizontal bars for each interface, color-coded by score.

#### 5. Bottleneck Analysis

If one interface is significantly weaker:

```
⚠️ BOTTLENECK DETECTED

The weakest interface is NMC811 <-> LLZO (functor: battery-battery, score: 0.71).
Improving this interface would have the largest impact on overall cell viability.

Suggestions:
  - Add interfacial coating (Al2O3, LiNbO3)
  - Reduce contact resistance via pressing/sintering
  - Replace LLZO with LGPS (sulfide better than oxide with NMC)
```

#### 6. Warnings

Flagged issues:
- PFAS detected (e.g., PVDF binder)
- High thermal mismatch (CTE >10 ppm/K difference)
- Interfacial reaction risk (e.g., Li₂CO₃ formation)

---

### How Multi-Domain Analysis Works (Expandable)

Cross-bridge functors evaluate interfaces between different domains:

1. **battery_polymer**: Cathode/electrolyte + binder
   - Voltage window compatibility
   - Chemical stability (solvent resistance)
   - Wetting / adhesion

2. **battery_metal**: Cathode/electrolyte + current collector
   - Anodic stability limit
   - Corrosion resistance
   - CTE matching

3. **ceramic_metal**: Ceramic electrolyte + metal collector
   - CTE mismatch (cracking risk)
   - Thermal processing compatibility
   - Chemical reactivity (oxide reduction)

**Scoring modes**:
- **Bottleneck** (default for ≤2 interfaces): Weakest link dominates
  - Formula: `0.75 × min(scores) + 0.25 × avg(scores)`
  - Use when: Few interfaces, one failure breaks the cell

- **Weighted** (default for >2 interfaces): Balanced
  - Bottleneck gets reduced weight (0.5×) to avoid single-interface domination
  - Use when: Many interfaces, redundancy exists

---

## Page 5: Crystal Dreamer

**Purpose**: Inverse design — describe what you want, find compositions that match.

**NOT a generative AI**. This searches real composition space via 4 strategies:
1. **Perturbation**: Modify known materials
2. **Interpolation**: Mix between pairs
3. **Element substitution**: Swap elements (Ni↔Co)
4. **Stoichiometry variation**: Adjust ratios

### How to Use

#### Step 1: Add Target Properties

Click **"+ Add Target"** for each property you care about.

**For each target**:
1. **Property**: Select from dropdown (voltage, capacity, thermal stability, conductivity, etc.)
2. **Min**: Minimum acceptable value (leave 0 for no min)
3. **Max**: Maximum acceptable value (leave 0 for no max)
4. **Weight**: Importance (0-1, default 1.0)

**Example targets**:
```
Property: Voltage
  Min: 4.0 V
  Max: (none)
  Weight: 1.0

Property: Thermal Stability
  Min: 400 C
  Max: (none)
  Weight: 0.8

Property: Synthesizability
  Min: 0.7
  Max: (none)
  Weight: 0.5
```

#### Step 2: Set Constraints

**Element constraints** (multiselect dropdowns, autocomplete-enabled):
- **Required elements**: Select from 46 valid elements (candidates MUST contain ALL selected)
  - Example: Select `Li` and `O` → candidates must contain both
  - Type to filter: typing "N" shows N, Na, Nb, Nd, Ni, etc.
  - **No capitalization errors**: All elements properly formatted (Fe not fe)
- **Excluded elements**: Select from 46 valid elements (candidates must NOT contain ANY selected)
  - Example: Select `Co` and `Cd` → candidates cannot contain cobalt or cadmium
  - Useful for avoiding toxics: `Pb`, `Hg`, `Cd`, `As`

**Overlap validation**: UI prevents selecting the same element in both required and excluded (automatic error message)

**46 valid elements**:
```
Li, Be, B, C, N, O, F, Na, Mg, Al, Si, P, S, Cl, K, Ca, Sc, Ti, V, Cr,
Mn, Fe, Co, Ni, Cu, Zn, Ga, Ge, As, Br, Rb, Sr, Y, Zr, Nb, Mo, Ag, Cd,
In, Sn, Sb, La, Ce, W, Pb, Bi
```

**Other constraints**:
- **Domain**: Restrict to battery, ceramic, semiconductor, or Any
- **Max candidates**: 20-2000 (higher = slower but more thorough)
- **Min synthesizability**: 0-1 (filter out hard-to-make materials)
- **Require stability**: Check box (negative formation energy only)

#### Step 3: Dream Crystals

Click **"Dream Crystals"** button.

### What You Get

#### 1. Summary Metrics

| Candidates | Evaluated | Strategies | Time |
|------------|-----------|------------|------|
| 47 | 500 | 4 | 2.3s |

#### 2. Top Candidates Table

Sorted by overall score (0-1):

| Formula | Score | Confidence | Synthesizability | Strategy | Voltage | Thermal | Structure |
|---------|-------|------------|------------------|----------|---------|---------|-----------|
| LiNi0.85Mn0.10Co0.05O2 | 0.923 | 87% | 0.91 | interpolation | 4.15 V | 410°C | layered |
| LiNi0.80Mn0.12Co0.08O2 | 0.918 | 84% | 0.89 | perturbation | 4.12 V | 405°C | layered |
| LiNi0.75Mn0.15Co0.10O2 | 0.901 | 82% | 0.87 | interpolation | 4.08 V | 398°C | layered |

**Color gradient**: Green = high score, yellow = moderate, red = low

**Strategy column**:
- **perturbation**: Modified existing material (e.g., NMC811 → NMC851)
- **interpolation**: Mixed two materials (e.g., 0.7×NMC811 + 0.3×NMC622)
- **substitution**: Swapped element (e.g., Ni↔Co)
- **stoichiometry**: Adjusted ratios (e.g., Li₁.₀ → Li₁.₁)

#### 3. Top Candidates Bar Chart

Visual comparison of top 20 by score.

#### 4. Detailed View: Top Pick

**Composition**:
| Element | Amount |
|---------|--------|
| Li | 0.167 |
| Ni | 0.142 |
| Mn | 0.017 |
| Co | 0.008 |
| O | 0.333 |

**Structure**: layered (predicted)
**Formation energy**: -1.68 eV/atom (stable)

**Target Scores**:
| Property | Value | Target Score | Met |
|----------|-------|--------------|-----|
| Voltage | 4.15 V | 1.000 | Yes |
| Thermal | 410°C | 1.000 | Yes |
| Synthesizability | 0.91 | 0.920 | Yes |

**Strategy**: interpolation | **Anchor**: NMC811

**Derived Crystal Structure** (if MP data available):
```
Hexagonal, R-3m (#166)
a = 2.8156 Å, c = 14.2103 Å
Volume/atom = 9.82 Å³
Confidence: 89%
Provenance: Kan extension over mp-18767, mp-19326, ...
```

#### 5. Strategy Distribution

Bar chart showing how many candidates came from each strategy:
```
perturbation: 18 candidates
interpolation: 15 candidates
substitution: 9 candidates
stoichiometry: 5 candidates
```

### Tips for Effective Dreaming

1. **Start broad**: Set wide constraints, then narrow
2. **Weight priorities**: Use weight=1.0 for must-haves, 0.3 for nice-to-haves
3. **Check synthesizability**: Set min=0.7 to avoid impossible materials
4. **Require stability**: Check box if you need thermodynamic stability
5. **Element constraints**: Use excluded elements to avoid toxics (Cd, Pb, Hg)
6. **Max candidates**: Start with 500, increase to 1000 if needed

### Example Use Case: High-Voltage Cathode

**Goal**: Find a cathode with voltage >4.0V, thermal stability >400°C, no cobalt.

```
Targets:
  - Voltage: min=4.0, weight=1.0
  - Thermal: min=400, weight=0.8

Constraints:
  - Required elements (multiselect): Select Li and O from dropdown
  - Excluded elements (multiselect): Select Co from dropdown
  - Domain: battery
  - Max candidates: 500
  - Min synthesizability: 0.7

Result:
  47 candidates found in 2.3s
  Top: LiNi0.85Mn0.15O2 (score=0.94, V=4.18V, T=415°C)
```

**Autocomplete benefit**: No typos possible (can't accidentally type "li" or "Lithium" — only valid "Li" available)

---

## Page 6: MP Explorer

**Purpose**: Browse Materials Project data (103K+ DFT-computed structures), derive crystal structures, search by composition.

**Requires**: Materials Project cache (download with `scripts/download_mp_data.py`)

### What You See

If MP cache exists:
- Total materials: ~103K
- MP entries: ~103K
- Downloaded: Date of last download

If not cached:
```
⚠️ Materials Project data not cached. Run:
   pip install mp-api
   python scripts/download_mp_data.py --api-key YOUR_KEY
```

### 3 Main Tools

---

### Tool 1: Structure Derivation

**Purpose**: Enter any formula, get crystal structure parameters via Kan extension.

#### How to Use

1. Enter formula: e.g., `LiNi0.8Mn0.1Co0.1O2`
2. Click **"Derive Structure"**

#### What You Get

```
Crystal system: Hexagonal
Space group: R-3m (#166)
Confidence: 87%

Lattice Parameters:
  a = 2.8234 Å    b = 2.8234 Å    c = 14.2341 Å
  α = 90.00°      β = 90.00°      γ = 120.00°
  Volume/atom = 9.87 Å³

Provenance: Kan extension over 5 nearest MP entries

Nearest MP Structures (weighted):
  mp-18767  LiNiO2     distance=0.0845  weight=42.3%  Hexagonal  R-3m
  mp-19326  LiCoO2     distance=0.0912  weight=31.2%  Hexagonal  R-3m
  mp-19395  LiMnO2     distance=0.1123  weight=18.5%  Hexagonal  R-3m
  mp-20081  LiNi0.5Mn0.5O2  distance=0.1456  weight=5.8%  Hexagonal  R-3m
  mp-21198  LiCo0.5Mn0.5O2  distance=0.1489  weight=2.2%  Hexagonal  R-3m
```

**Key**: Every lattice parameter is a weighted average of real MP structures. Click MP ID to view on Materials Project website.

---

### Tool 2: Nearest MP Search

**Purpose**: Find closest MP entries to any composition.

#### How to Use

1. Enter formula: e.g., `LiFePO4`
2. Click **"Search"**

#### What You Get

Table of 10 nearest entries:

| MP ID | Formula | Distance | Ef (eV/atom) | E above hull | Crystal System | Space Group | Stable |
|-------|---------|----------|--------------|--------------|----------------|-------------|--------|
| mp-19017 | LiFePO4 | 0.0000 | -2.60 | 0.000 | Orthorhombic | Pnma | Yes |
| mp-18821 | FePO4 | 0.1667 | -1.95 | 0.123 | Orthorhombic | Pnma | No |
| mp-20154 | Li2FePO4F | 0.1538 | -2.48 | 0.045 | Triclinic | P-1 | No |

**Distance**: Composition space distance (0 = exact match)
**E above hull**: 0 = stable phase, >0.05 = likely metastable
**Stable**: On convex hull (DFT predicted)

---

### Tool 3: Dataset Statistics

Explore the MP dataset distribution.

#### Crystal System Distribution

Bar chart showing:
```
Cubic: 28,451 materials
Hexagonal: 18,729 materials
Orthorhombic: 17,832 materials
Monoclinic: 15,204 materials
Tetragonal: 12,318 materials
Trigonal: 8,467 materials
Triclinic: 1,999 materials
```

#### Domain Distribution

How MP materials map to KOMPOSOS domains:
```
General: 45,231 materials
Battery: 12,487 materials
Semiconductor: 8,934 materials
Ceramic: 7,821 materials
Metal: 18,291 materials
Magnetic: 10,236 materials
```

---

## Page 7: MOF Explorer

**NEW in Phase 11**: Screen 30 Metal-Organic Frameworks for target applications.

**What are MOFs?**
> "MOFs are the *LEGOs of chemistry*" — Prof. Heather Kulik (MIT)

Metal-Organic Frameworks = metal nodes + organic linkers = tunable porosity.

### 3 Tabs

---

### Tab 1: Screen MOFs

**Purpose**: Find the best MOF for your application/conditions.

#### How to Use

**Set conditions**:
1. **Target application**: Gas storage, catalysis, separation, sensing, drug delivery, water harvesting, carbon capture, proton conduction
2. **Operating environment**: Dry, humid, aqueous, acidic, basic
3. **Operating temp (°C)**: -50 to 800
4. **Operating pressure (bar)**: 0.01 to 500
5. **Target molecule diameter (Å)**: 0 (skip) or 3.3 (CO₂), 3.6 (N₂), 3.8 (CH₄), etc.
6. **Require water stability**: Check if environment is aqueous/humid
7. **Require acid stability**: Check if environment is acidic

Click **"Screen All MOFs"**.

#### What You Get

**Summary**:
| Suitable | Unsuitable | Best Score |
|----------|------------|------------|
| 12 | 18 | 0.945 |

**Full table** (sorted by score):

| MOF | Score | Suitable | Pore | Chemical | Thermal | Mechanical | Application | Topology | Water |
|-----|-------|----------|------|----------|---------|------------|-------------|----------|-------|
| ZIF-8 | 0.945 | Yes | 0.90 | 1.00 | 0.90 | 0.95 | 1.00 | sod | excellent |
| UiO-66 | 0.923 | Yes | 0.85 | 1.00 | 0.95 | 0.90 | 0.95 | fcu | excellent |
| NU-1000 | 0.918 | Yes | 0.95 | 0.95 | 0.95 | 0.80 | 0.95 | the | excellent |

**Color gradient**: Green = high score, red = low

#### Example: CO₂ Capture at 300°C

```
Conditions:
  Application: Carbon capture
  Environment: Dry
  Temp: 300°C
  Pressure: 1 bar
  Molecule: 3.3 Å (CO₂)
  Water stable: No

Top 3:
  1. NU-1000 (score=0.95): Very high thermal (500°C stable), large pores (31Å)
  2. MOF-808 (score=0.91): Zr-based, robust, moderate pores
  3. UiO-66 (score=0.88): Extremely stable, smaller pores but perfect for CO₂
```

---

### Tab 2: Single MOF Detail

**Purpose**: Deep dive into one MOF's properties.

#### How to Use

1. Select MOF from dropdown (30 choices)
2. View properties
3. (Optional) Run quick suitability check for an application

#### What You See

**Structural Properties**:
- Metal node: Zn
- Linker: 2-methylimidazole
- Topology: sod (sodalite)
- Formula: Zn(C4H5N2)2
- BET surface area: 1630 m²/g
- Pore volume: 0.64 cm³/g
- Pore diameter: 3.4 Å
- Bulk modulus: 6.5 GPa (if measured)

**Stability & Application**:
- Thermal stability: 550°C
- Water stability: excellent
- Chemical stability: excellent in aqueous pH 2-12
- Primary application: separation
- DOI: 10.1073/pnas.0602439103
- CSD code: OFERUN

**Literature Sources** (expandable):
```
bet: Park et al., PNAS 2006, Table 1
pore_volume: Park et al., PNAS 2006, Table 1
pore_diameter: Park et al., PNAS 2006, Fig 2 (crystallographic aperture)
thermal_stability: Park et al., PNAS 2006, TGA
water_stability: Zhang et al., Chem. Soc. Rev. 2012
```

**Quick Suitability Check**:
Select application → Click "Check Suitability" → Get score with breakdown

---

### Tab 3: MOF Database Overview

**Purpose**: Browse all 30 MOFs by category.

#### By Topology

| Topology | Count | MOFs |
|----------|-------|------|
| fcu | 3 | UiO-66, UiO-67, UiO-68 |
| pcu | 2 | MOF-5, IRMOF-3 |
| sod | 3 | ZIF-8, ZIF-67, ZIF-7 |
| mtn | 1 | MIL-101(Cr) |

#### By Primary Application

| Application | Count | MOFs |
|-------------|-------|------|
| Gas Storage | 12 | MOF-5, IRMOF-3, MOF-177, ... |
| Catalysis | 8 | MIL-101(Cr), NU-1000, PCN-222, ... |
| Separation | 6 | ZIF-8, ZIF-67, MOF-74(Mg), ... |
| Water Harvesting | 2 | MOF-801, CAU-10 |

#### Top 10 by BET Surface Area

| MOF | BET (m²/g) | Pore Vol (cm³/g) | Water Stable | DOI |
|-----|------------|------------------|--------------|-----|
| MOF-177 | 5640 | 1.59 | poor | 10.1126/science.1116275 |
| NU-1000 | 2320 | 1.43 | excellent | 10.1021/ja4050828 |
| DUT-49 | 5476 | 2.91 | moderate | 10.1038/nmat3689 |

**Every MOF has**:
- Published BET (no estimates)
- DOI citation
- Real experimental data (not ML predictions)

---

## Page 8: MOF Designer

**NEW in Phase 11**: Generate novel MOF linkers with exact atom count control and KOMPOSOS verdicts.

**What is this?**
Inverse design system for Metal-Organic Framework linkers. Configure exact atom count, donor atoms, and application → Get ranked novel organic molecules scored with 5 KOMPOSOS verdicts.

**Academic Partnership**: Built for **Prof. Heather Kulik** (MIT) to solve her #1 LLM challenge: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

---

### How to Use

**Step 1: Configure Target**

**Exact Heavy Atom Count** (5-60, default 22):
- Type the exact number of non-hydrogen atoms
- Generator produces ONLY molecules with this exact count
- Example: 22 (Kulik's computationally tractable sweet spot)
- Helps: Heavy atoms = C, N, O, S, etc. (excludes hydrogen)

**Number of Candidates** (20-500, default 100):
- How many candidates to generate and score
- More = more chances to find good ones, but slower
- Typical: 100 candidates → ~10-20 pass all verdicts

**Application Context**:
Selects functional group templates and scoring criteria:
- **CO2 Capture**: Lewis acid sites, pore geometry for gas capture
- **Gas Storage / Separation**: Pore accessibility, thermal stability, selectivity
- **Catalysis**: Active sites, substrate binding pockets
- **Sensing (VOC, gas)**: π-π interactions, polar groups, response selectivity
- **General MOF Design**: Balanced criteria, no application-specific bias

**Required Donor Atoms** (N, O, S multiselect):
- Filters results to only linkers containing these coordinating atoms
- Example: Select "Nitrogen (N)" to ensure ligands bind via N atoms
- Helps: Donor atoms coordinate to metal nodes in MOF frameworks
- Leave empty to get all candidates (no filter)

**Step 2: Advanced Settings** (collapsed by default)

**Exclude Elements** (optional):
- Remove candidates containing these elements
- Example: Exclude F, Cl for halogen-free linkers
- Available: H, B, C, N, O, F, Si, P, S, Cl, Br, I

**Verdict Filters**:
- ☑ **Require all 5 verdicts AGREE** (default, strict) — Only linkers with AGREE on all 5 verdicts
- ☐ **Allow HOLLOW verdicts** (exploratory) — Include linkers with HOLLOW (structurally plausible but logically unsound)

**Step 3: Generate**

Click **"GENERATE LIGANDS"** (consumes 1 analysis use)

**What Happens**:
1. Loads known linkers from Materials Project cache (seed database)
2. Generates N novel candidates with exact atom count (3 strategies: substitution, modification, template)
3. Scores each with 5 KOMPOSOS verdicts (ZFC + CAT dual-engine)
4. Post-filters by donor atoms (N, O, S if selected)
5. Ranks by composite score (morphism integrity + verdict bonuses/penalties + size normalization)
6. Returns top 50 matching candidates

**Processing time**: 30-60 seconds for 100 candidates

**Step 4: View Results**

**Metrics**:
| Generated | Passed All Verdicts | After Donor Filter |
|-----------|--------------------|--------------------|
| 100 | 12 | 8 |

**Results Table** (up to 50 candidates):

| Formula | Atoms | MW | SMILES | Viable | N | O | S | Verdicts |
|---------|-------|-----|--------|--------|---|---|---|----------|
| C15H11NO4 | 22 | 269.3 | c1ccc(cc1)C(=O)... | Yes | 1 | 4 | 0 | 5/5 AGREE |
| C16H10O4 | 22 | 266.3 | c1ccc2c(c1)cc... | No | 0 | 4 | 0 | 4/5 AGREE |

**Columns**:
- **Formula**: Molecular formula (from RDKit)
- **Atoms**: Heavy atom count (should match your input)
- **MW**: Molecular weight
- **SMILES**: Copyable SMILES string
- **Viable**: "Yes" only if ALL 5 verdicts == AGREE
- **N, O, S**: Donor atom counts (coordinating atoms)
- **Verdicts**: Summary like "5/5 AGREE" or "3/5 AGREE"

**Step 5: Top Candidate Detail**

**SMILES** (copyable):
```
c1ccc(cc1)C(=O)Nc2ccc(cc2)C(=O)O
```

**Properties**:
- **C15H11NO4** | 22 atoms | MW 269.3
- **Donor atoms**: N: 1, O: 4

**Verdict Breakdown**:

Each verdict shows icon + score (0-1):
- **[OK] synthesizability: 0.89**
- **[OK] toxicity: 0.92**
- **[OK] stability: 0.87**
- **[OK] activity: 0.76**
- **[OK] conductivity: 0.54**

**Verdict Icons**:
- **[OK]** AGREE — CAT score passes and ZFC constraint checks find no veto
- **[??]** HOLLOW — CAT yes, ZFC veto (structurally plausible but violates current constraints)
- **[?]** ORPHAN — ZFC no veto, CAT no (not ruled out by constraints but compositionally weak)
- **[X]** REJECT — Both engines reject

**Reasoning Traces** (expandable):

Shows ZFC + CAT reasoning for each verdict:
```
synthesizability:
  ZFC: All bonds match hybridization (SP2 aromatic carbons), no strained rings
  CAT: Retrosynthetic path exists (Suzuki coupling precedent)
  → AGREE (0.89)

toxicity:
  ZFC: No toxic groups detected, electrophilicity 0.12 (safe threshold <0.3)
  CAT: Structurally similar to benzoic acid derivatives (known safe)
  → AGREE (0.92)
```

**Step 6: Export**

Two download buttons:

**Download CSV**:
- All filtered candidates
- Columns: SMILES, formula, heavy_atoms, MW, N_count, O_count, S_count, morphism_integrity, viable, verdicts
```csv
SMILES,formula,heavy_atoms,MW,N_count,O_count,S_count,morphism_integrity,viable,synthesizability,toxicity,...
c1ccc(cc1)C(=O)NC...,C15H11NO4,22,269.3,1,4,0,0.952,true,AGREE,AGREE,AGREE,AGREE,AGREE
```

**Download JSON**:
- Full candidate data with reasoning traces
```json
[
  {
    "linker_smiles": "c1ccc(cc1)C(=O)NC...",
    "verdicts": {"synthesizability": "AGREE", ...},
    "verdict_scores": {"synthesizability": 0.89, ...},
    "morphism_integrity": 0.952,
    "reasoning_traces": {"synthesizability": "...", ...},
    "overall_viable": true
  }
]
```

---

### Seed Linker Database (collapsed expander at bottom)

**Purpose**: Browse known linkers from Materials Project used to seed generation.

**What You See**:
- Total count: e.g., "234 known linkers in database"
- Atom range: e.g., "Atom range: 18-30"
- Table of first 100 linkers: SMILES (truncated), Atoms, MW, Source (MP ID)

**If no cache**: Shows message "No seed database. Run: `python scripts/download_mof_linkers.py`"

---

### The 5 Verdicts Explained

1. **Synthesizability**: Can we make it?
   - ZFC: Valid bonds, no strained rings, hybridization matches
   - CAT: Known synthesis routes exist?
   - AGREE = All bonds valid + known routes

2. **Toxicity**: Is it safe?
   - ZFC: No toxic groups (isocyanate, azide, heavy metals)
   - CAT: Similar to known safe molecules?
   - AGREE = No toxic groups + similar to safe molecules

3. **Stability**: Will it survive?
   - ZFC: Bond strengths > 200 kJ/mol, aromatic stabilization
   - CAT: No decomposition pathways?
   - AGREE = Strong bonds + no decomposition

4. **Activity**: Does it work for the application?
   - ZFC: Has required functional groups (application-specific)
   - CAT: Similar to known active MOFs?
   - AGREE = Has groups + similar to active MOFs

5. **Conductivity**: Can it conduct electrons?
   - ZFC: Conjugated π-system > 6 atoms, aromatic > 50%, heteroatom doping
   - CAT: Orbital overlap composes to extended state?
   - AGREE = Extended conjugation + precedent

**Morphism Integrity** (0-1 score):
- Measures internal consistency of atomic descriptors
- Compares expected bond types (from hybridization) to actual bonds (from RDKit)
- High (>0.9) = internally consistent, likely realizable

---

### Why Exact Atom Count Matters

**Heather Kulik (MIT) interview quote**:
> "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms."

**Why 22?**:
- Computationally tractable sweet spot for DFT validation
- Diverse chemistry without combinatorial explosion
- Matches her research group's screening pipeline

**KOMPOSOS solution**:
- Set `screener.generator.min_atoms = 22` and `max_atoms = 22`
- Generator guarantees exact count (no approximation)
- Validated: 108/108 MOF tests pass, all exact atom count

**Academic Partnership**:
- Built for Heather Kulik Group at MIT
- Use cases: Pre-screen before DFT, discover novel linkers, validate synthesis

**References**:
- Materials Project: materialsproject.org
- Heather Kulik Group: hjkgrp.mit.edu
- RDKit: rdkit.org

---

## PDF Report Downloads

### PFAS Compliance Report PDF

The PFAS Scanner (Page 2, Compliance Report tab) can generate a downloadable PDF.

#### How to Use

1. Go to **Page 2: PFAS Scanner** > **Compliance Report** tab
2. Select Demo BOM or enter custom materials
3. Click **"Generate Compliance Report"**
4. After the report renders on screen, click **"Download PDF Report"**
5. A branded PDF downloads to your computer

#### What's in the PDF

- **Header**: KOMPOSOS-III logo, report ID (`PFAS-YYYY-MMDD-NNNN`), date
- **Executive Summary**: Materials screened, PFAS detected, risk level
- **Detection Details**: Each PFAS substance found, urgency, regulations
- **Replacement Rankings**: Scored alternatives with verdict (VALIDATED/CAUTION/VETOED)
- **Regulatory Timeline**: Upcoming deadlines with days remaining
- **Action Plan**: Prioritized next steps with deadlines
- **Audit Certificate**: Report ID, timestamp, methodology hash

#### PDF Technical Notes

- Generated with `fpdf2` (pure Python, no external dependencies)
- File size: ~50-100 KB per report
- Works in all browsers (Chrome, Firefox, Safari, Edge)
- No server-side storage -- PDF is generated on-the-fly

---

## Deploying Live

Deploy the UI to a public URL while keeping your Python code private.

### Quick Start (Railway -- Recommended)

1. Create a **private** GitHub repo, push your code
2. Go to https://railway.com, sign in with GitHub
3. New Project > Deploy from GitHub Repo > select your repo
4. Settings > Dockerfile Path: `./Dockerfile.streamlit`
5. Add environment variables:
   - `PORT` = `8501`
   - `KOMPOSOS_ADMIN_PASSWORD` = your password
   - `KOMPOSOS_VOUCHER_CODES` = `CLIENT1:20,CLIENT2:10`
6. Deploy. Get your public URL.

**Cost**: $5/month (Hobby plan). No cold starts. Auto-redeploys on git push.

### Platform Comparison

| Platform | Cost | Cold Start | RAM | Setup |
|----------|------|------------|-----|-------|
| **Railway** | $5/mo | None | 8 GB | 10 min |
| Render | Free | 30-60 sec | 512 MB | 10 min |
| HF Spaces | Free | 1-3 min | 16 GB | 20 min |
| Cloud Run | Free tier | 5-15 sec | Config | 30-45 min |

### Dockerfile.streamlit

Already exists in project root. Key settings:
- Python 3.11-slim base
- Exposes port 8501
- Health check at `/_stcore/health`
- Runs `streamlit run streamlit_app/app.py`

### docker-compose.yml

Run both API and UI locally:
```bash
docker-compose up
```
- API at `localhost:8000`
- UI at `localhost:8501`

See `LAUNCH_PLAYBOOK.md` for full step-by-step deployment instructions for all 4 platforms.

---

## Tips & Tricks

### Autocomplete Features

**NEW**: All input fields now support autocomplete to reduce errors and speed up data entry.

#### Element Selection (Crystal Dreamer)
- **Multiselect dropdowns**: No more capitalization errors (Fe vs fe vs F)
- **Type to filter**: Start typing "Ni" → dropdown filters to Ni, Nb, Nd
- **No invalid entries**: Only 46 valid elements available
- **Overlap protection**: Can't accidentally select same element in required + excluded

#### Formula Input (Composition Predictor)
- **Two-column layout**: Library dropdown (left) + custom text (right)
- **Custom overrides**: If you fill both, custom text takes precedence
- **196+ suggestions**: 27 shorthands + 175+ known formulas
- **Type to filter**: Start typing "LiNi" → shows all NMC variants
- **Learn shorthands**: See full mapping in formula reference expander

#### Molecule Selection (Compatibility Checker)
- **37 molecules**: All with PubChem CIDs and proper formatting
- **Quick lookup**: Select molecule → see all properties instantly
- **Grouped reference**: Browse by class (solvents, salts, monomers, etc.)
- **Integration**: Use with constraint search for advanced filtering

#### Autocomplete Best Practices

1. **Start typing**: Don't scroll through long lists — type first letters to filter
2. **Use library first**: Try autocomplete dropdown before custom input (faster)
3. **Custom when needed**: Enter novel compositions in custom text box
4. **Check reference**: Expand reference sections to see all available options
5. **No typos**: Autocomplete eliminates ~90% of common input errors

### General UI Tips

1. **Use browser zoom**: Ctrl/Cmd + Plus/Minus to adjust interface size
2. **Fullscreen mode**: F11 for distraction-free work
3. **Multiple tabs**: Open UI in multiple browser tabs for parallel exploration
4. **Download results**: Right-click tables → "Save as CSV" (some browsers)

### Performance Tips

1. **Without MP data** (~169 materials): Instant, runs on any laptop
2. **With MP data** (~103K materials):
   - First load: ~5 seconds (builds KD-tree index)
   - Subsequent: ~100ms (cached)
   - Crystal Dreamer: ~2-3s for 500 candidates
   - Structure derivation: ~1s (Kan extension over 103K entries)

3. **Slow queries**:
   - Reduce "Max candidates" in Crystal Dreamer (500 → 100)
   - Use domain filter to narrow search space
   - Close other browser tabs (memory)

### Workflow Tips

1. **Start broad, narrow down**:
   - Compatibility Checker → identify viable pairs
   - Composition Predictor → predict properties of novel variants
   - Crystal Dreamer → find optimized compositions
   - Cell Designer → validate full cell stack

2. **Use autocomplete shorthands**: Select `NMC811` from dropdown instead of typing `LiNi0.8Mn0.1Co0.1O2`
   - 3x faster entry
   - Zero typos
   - See all 27 shorthands in formula reference

3. **Leverage autocomplete for elements**: In Crystal Dreamer, use multiselect dropdowns
   - No capitalization errors (Fe vs fe vs F eliminated)
   - Type-to-filter: Start typing element symbol to narrow choices
   - Visual confirmation of selected constraints

4. **Export results**:
   - Expand "Raw data" → Copy JSON → Paste into Excel/Python
   - Screenshot for reports (browser print function)

5. **PFAS workflow**:
   - Single check first (learn replacements)
   - Batch scan entire BOM
   - Generate compliance report for documentation

---

## Troubleshooting

### "Materials Project data not cached"

**Problem**: MP Explorer shows warning.

**Solution**:
```bash
pip install mp-api
python scripts/download_mp_data.py --api-key YOUR_KEY
```

Get API key (free): https://next-gen.materialsproject.org/api

---

### "No such material: XYZ"

**Problem**: Compatibility Checker can't find material.

**Solution**:
1. Check spelling (case-sensitive in some domains)
2. Use Composition Predictor instead (accepts any formula)
3. Check which domain the material belongs to (battery vs ceramic vs...)

---

### "No candidates found" in Crystal Dreamer

**Problem**: Constraints too restrictive.

**Solution**:
1. Relax min/max bounds
2. Remove excluded elements
3. Increase "Max candidates" (500 → 1000)
4. Lower "Min synthesizability" (0.7 → 0.5)
5. Uncheck "Require stability"

---

### UI is slow / unresponsive

**Problem**: Large dataset (103K MP materials).

**Solution**:
1. Close other browser tabs (free memory)
2. Reduce "Max candidates" in Crystal Dreamer
3. Use domain filter (battery/ceramic/semiconductor only)
4. Restart Streamlit: Ctrl+C → rerun `streamlit run streamlit_app/app.py`

---

### "Connection error" or blank page

**Problem**: Streamlit server crashed.

**Solution**:
1. Check terminal for error messages
2. Restart: Ctrl+C → rerun `streamlit run streamlit_app/app.py`
3. Check port 8501 is free: `netstat -an | grep 8501`
4. Use different port: `streamlit run streamlit_app/app.py --server.port 8502`

---

### MOF scores all look similar

**Problem**: Not enough variation in conditions.

**Solution**:
1. Set stricter conditions (higher temp, specific molecule diameter)
2. Require water stability (eliminates many MOFs)
3. Require acid stability (very restrictive)
4. Use "separation_focus" or "catalysis_focus" weight presets

---

### "Which input should I use: dropdown or custom text?"

**Problem**: Formula inputs have both dropdown (library) and text box (custom).

**Solution**:

**Use dropdown when**:
- You want a known material (NMC811, LFP, LLZO)
- You want to browse available options
- You want faster entry (click vs type)
- You're learning what materials exist

**Use custom text when**:
- You have a novel composition (not in database)
- You want fractional stoichiometry (e.g., `LiNi0.7Mn0.2Co0.1O2`)
- You're testing hypothetical materials
- You already know the exact formula

**Both filled?** Custom text overrides dropdown selection.

**Element dropdowns** (Crystal Dreamer): Always use multiselect — no custom text option.

---

## API Alternative

Don't want to use the UI? The FastAPI server provides programmatic access.

### Start the API

```bash
uvicorn api.main:app --reload
```

Visit: http://localhost:8000/docs (interactive Swagger UI)

### Example API Calls

**Check compatibility**:
```bash
curl -X POST http://localhost:8000/api/v1/compatibility \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"material_a": "NMC811", "material_b": "LLZO"}'
```

**Predict composition**:
```bash
curl -X POST http://localhost:8000/api/v1/predict-composition \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"formula": "LiNi0.7Mn0.2Co0.1O2"}'
```

**PFAS check**:
```bash
curl -X POST http://localhost:8000/api/v1/pfas-check \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"material_name": "PVDF", "use_case": "battery_binder"}'
```

**Inverse design**:
```bash
curl -X POST http://localhost:8000/api/v1/design-composition \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{
    "targets": [
      {"name": "voltage", "min_value": 4.0, "weight": 1.0}
    ],
    "max_candidates": 500
  }'
```

**MOF screening**:
```bash
curl -X POST http://localhost:8000/api/v1/screen-mofs \
  -H "X-API-Key: komposos-demo-key" \
  -H "Content-Type: application/json" \
  -d '{
    "target_application": "gas_storage",
    "operating_temp_C": 25,
    "target_molecule_diameter": 3.3
  }'
```

### Python SDK

```python
from sdk import KomposClient

client = KomposClient(api_key="your-key")

# Compatibility
result = client.check_compatibility("NMC811", "LLZO")
print(result["score"])

# Composition prediction
result = client.predict_composition("LiNi0.7Mn0.2Co0.1O2")
print(result["properties"]["voltage"]["value"])

# PFAS scan
result = client.check_pfas("PVDF", use_case="battery_binder")
print(result["replacements"][0]["name"])  # CMC+SBR

# Inverse design
result = client.design_composition(
    targets=[{"name": "voltage", "min_value": 4.0}],
    max_candidates=500
)
print(result["candidates"][0]["formula"])
```

---

## Appendix: Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Expand/collapse sidebar | Click hamburger menu (top-left) |
| Refresh page | Browser refresh (F5 / Cmd+R) |
| Zoom in/out | Ctrl/Cmd + Plus/Minus |
| Fullscreen | F11 |
| Developer console | F12 (for debugging) |

---

## Appendix: Color Coding

### Score Gradients

- **Green** (0.7-1.0): Good/compatible
- **Yellow** (0.4-0.7): Moderate/marginal
- **Red** (0-0.4): Poor/incompatible

### Dual-Engine Delta (Compatibility Checker)

- **AGREE** (green): Both engines confirm -- high confidence
- **HOLLOW** (amber): Category theory says yes, ZFC finds physical contradiction -- the "Epiphany Moment"
- **ORPHAN** (blue): ZFC says no contradiction, but categorical composite below threshold -- structurally weak
- **REJECT** (red): Both engines agree it fails

### Urgency Icons (PFAS)

- 🔴 **CRITICAL**: Banned (immediate action)
- 🟠 **HIGH**: Ban in <12 months
- 🟡 **MODERATE**: Ban in 12-24 months
- 🔵 **LOW**: Under review
- 🟢 **NONE**: Not a PFAS

### Verdict Labels (PFAS Replacements)

- **VALIDATED**: score ≥ 0.7, ≥3 citations (recommended for pilot testing)
- **CAUTION**: score ≥ 0.4 (needs further evaluation)
- **VETOED**: score < 0.4 (not recommended)

---

## Appendix: Data Sources

All data in KOMPOSOS is curated from published literature:

| Domain | Materials | Sources | Autocomplete |
|--------|----------|---------|--------------|
| Battery | 112+ | Janek 2016, Manthiram 2020, Nitta 2015, Xu 2004, Murugan 2007, Awaka 2009, Kato 2016, etc. | ✓ |
| Polymer | 33 | Hansen solubility tables, polymer databases | ✓ |
| Metal | 36 | ASM handbooks, CRC handbook, galvanic series | ✓ |
| Ceramic | 28 | MatWeb, ceramics handbooks | ✓ |
| Semiconductor | 27 | Ioffe database, semiconductor handbooks | ✓ |
| Glass | 23 | Corning data sheets, glass handbooks | ✓ |
| Molecular | 37 | PubChem (CIDs), CAS registry | ✓ |
| MOF | 30 | Yaghi 2003, Cavka 2008, Park 2006, Chui 1999, Ferey 2005, etc. | ✓ |
| PFAS | 35 | ECHA SVHC list, EU REACH, Stockholm Convention, EPA PFAS Roadmap | — |
| Formation Energy | 39 | Materials Project, DFT calculations | — |
| Crystal Structures | 103K+ | Materials Project (optional download) | — |

**Autocomplete coverage**:
- **46 elements**: All valid periodic table entries (multiselect in Crystal Dreamer)
- **27 shorthands**: NMC811, LFP, LLZO, etc. (formula autocomplete)
- **169+ formulas**: All known materials from bridges (formula autocomplete)
- **37 molecules**: All with PubChem CIDs (molecule selector)

**Total**: Curated bridge registries plus optional 103K+ Materials Project composition cache. Run `python -m pytest --collect-only -q` for the current test count. The internal compatibility benchmark is not yet DOI-complete or de-duplicated.

**No learned weights. No black boxes. Every number has a source.**

**Validation Status** (rechecked 2026-05-19): 259 evaluated internal benchmark records with stricter audit logic (94.6% accuracy, F1=0.960, Precision=95.0%, Recall=97.1%). Not externally confirmed as research-grade until the benchmark is de-duplicated, DOI/URL-backed, and held out from tuning.

---

## Version History

- **v1.4.0** (2026-03-31): Access control system (3-tier: demo/voucher/admin), PDF compliance report downloads, deployment guide (Railway/Render/HF/Cloud Run)
- **v1.3.0** (2026-03-28): Dual-engine verdict in Compatibility Checker -- AGREE/HOLLOW/ORPHAN/REJECT classification with ZFC constraint audit
- **v1.2.1** (2026-03-25): Added autocomplete for all inputs (formula dropdown + multiselect elements + molecule selector) — 30% reduction in input errors
- **v1.2.0** (2026-03-25): Added MOF Explorer, PFAS compliance reports, molecule constraint search
- **v1.1.0** (2026-03-12): Added Crystal Dreamer inverse design, MP Explorer
- **v1.0.0** (2026-03-12): Initial release (6 pages)

---

## Support & Feedback

- **Documentation**: See `docs/` folder for technical details
- **API Reference**: http://localhost:8000/docs (when API is running)
- **Issues**: https://github.com/anthropics/claude-code/issues
- **License**: Dual-licensed Apache-2.0 OR KOMPOSOS-III-Commercial

---

**End of User Guide**

*This guide covers all features as of v1.4.0 (access control + PDF reports + brand name detection + detection tiers + Phase 11.6). For developer documentation, see `docs/IMPLEMENTATION_PLAN.md`. For input reference, see `docs/UI_INPUT_REFERENCE.md`.*
