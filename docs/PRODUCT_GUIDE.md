# KOMPOSOS Product Guide

A plain-language guide for understanding, presenting, and customizing KOMPOSOS for clients.

---

## 1. What KOMPOSOS Actually Does

KOMPOSOS answers one question: **"Will these materials work together?"**

A battery company picks a cathode, an electrolyte, a binder, a separator, and a current collector. Before they spend 6 months and $50K on lab testing, KOMPOSOS tells them in seconds:

- Will PEO binder survive the voltage of an NMC811 cathode? (No -- it oxidizes above 3.8V)
- Is PVDF binder PFAS-regulated? (Yes -- EU ban proposed for 2027)
- What can replace PVDF *for my cell*? Each PFAS-free option is scored for calibrated
  compatibility against your whole stack. (e.g. CMC+SBR is great for a graphite anode but
  fails against an NMC811 cathode -- so for a full NMC cell the tool promotes PAN instead.)
- **Synthesis planning**: Tells you HOW to make it ($47/batch solid-state synthesis).
- **Interpretable Reasoning**: Every score traces back to a citation. Users can distinguish between Literature-Backed data, Cross-Bridge Analysis, and Heuristic Predictions via explicit **Uncertainty Tiers**.
- **Active Verification (NEW)**: GROMACS molecular dynamics for high-stakes or low-confidence queries when a prepared `.gro`/`.top` input bundle is supplied. Missing inputs produce a no-verdict readiness report, not a fake simulation verdict.

It does this using published property data, not black-box AI. Every score traces back to a citation or a measured property. That's the selling point: **interpretable, auditable, multi-domain, simulation-verified**.

---

## 2. The 205 Materials -- What They Are

KOMPOSOS has 175 curated bridge materials across 7 domains (battery 28, polymer 33, metal 36, ceramic 28, semiconductor 27, glass 23), plus 37 molecules, 35 PFAS substances, and (optionally) 103K+ from Materials Project. These are the names you type into the UI. Each material has real published property data (thermal stability, voltage windows, CTE, etc.) that the scoring engine uses.

All composition-level reasoning now uses **physics-embedded 120D vectors**, ensuring that chemical similarity (Periodic Table Group/Period) is weighted alongside stoichiometry.



### Battery Domain (112+ materials)

These are cathodes, anodes, electrolyte solvents, electrolyte salts, and solid electrolytes. This vertical has been significantly expanded for liquid and solid-state chemistry screening.

| What you type | What it is | Role |
|---|---|---|
| NMC811 | LiNi0.8Mn0.1Co0.1O2 | Cathode active material (high energy) |
...
| Li3PS4 | Lithium thiophosphate | Solid electrolyte (sulfide) |
| LATP | Li1.3Al0.3Ti1.7(PO4)3 | Solid electrolyte (NASICON-type) |
| S8 | Sulfur | Cathode (highest theoretical capacity) |
| Cu_foil | Copper foil | Current collector (Anode) |
| Al_foil | Aluminum foil | Current collector (Cathode) |
| PEO | Polyethylene oxide | Polymer electrolyte (solid-state) |
| PVDF | Polyvinylidene fluoride | Binder (high-voltage stable) |

### Polymer Domain (33 materials)

Binders, separators, structural plastics, rubbers, and solvents.

| What you type | What it is | Common use |
|---|---|---|
| PVDF | Polyvinylidene fluoride | Cathode binder (**PFAS**) |
| PTFE | Polytetrafluoroethylene (Teflon) | Gaskets, seals (**PFAS**) |
| PEO | Polyethylene oxide | Solid polymer electrolyte |
| CMC | Carboxymethyl cellulose | Anode binder (water-based) |
| SBR | Styrene-butadiene rubber | Co-binder with CMC |
| PAN | Polyacrylonitrile | Separator, gel electrolyte |
| PP | Polypropylene | Separator base |
| PE (via HDPE) | Polyethylene | Separator layer |
| PEEK | Polyether ether ketone | High-temp engineering plastic |
| PA6 | Nylon 6 | Structural, housings |
| PA66 | Nylon 66 | Structural, connectors |
| PC | Polycarbonate | Transparent housings |
| PET | Polyethylene terephthalate | Film, packaging |
| PMMA | Poly(methyl methacrylate) | Optical, display covers |
| PS | Polystyrene | Packaging, insulation |
| PVC | Polyvinyl chloride | Pipes, insulation |
| ABS | Acrylonitrile butadiene styrene | Housings, 3D printing |
| Epoxy | Epoxy resin | Adhesive, composite matrix |
| PI | Polyimide (Kapton) | Flexible circuits, high-temp film |
| EPDM | Ethylene propylene diene monomer | Seals, gaskets (PFAS-free) |
| NBR | Nitrile rubber | Oil-resistant seals |
| PDMS | Polydimethylsiloxane (silicone) | Seals, medical devices |
| NR | Natural rubber | General-purpose rubber |
| HDPE | High-density polyethylene | Containers, liners |
| PPS | Polyphenylene sulfide | High-temp automotive |
| PPSU | Polyphenylsulfone | Medical devices |
| POM | Polyoxymethylene (Delrin) | Gears, bearings |
| UPE | Ultra-high molecular weight PE | Wear-resistant parts |
| LCP | Liquid crystal polymer | Connectors, 5G components |
| Phenolic | Phenolic resin | Circuit boards, brake pads |
| NMP | N-methyl-2-pyrrolidone | Processing solvent for PVDF |
| Toluene | Toluene | Solvent |
| Water | H2O | Processing solvent |
| Acetone | Acetone | Cleaning solvent |

### Metal Domain (36 materials)

Pure metals, alloys, and foils.

| What you type | What it is | Common use |
|---|---|---|
| Cu | Copper | Anode current collector |
| Cu_foil | Copper foil | Battery anode collector |
| Al | Aluminum | Cathode current collector |
| Al_foil | Aluminum foil | Battery cathode collector |
| Ni | Nickel | Plating, tabs |
| Ni_tab | Nickel tab | Battery connection tab |
| Fe | Iron | Structural |
| Ti | Titanium | Aerospace, medical |
| Ti6Al4V | Ti-6Al-4V alloy | Aerospace standard |
| SS_304 | 304 Stainless Steel | General-purpose stainless |
| SS_316 | 316 Stainless Steel | Corrosion-resistant |
| Al_6061 | 6061 Aluminum alloy | Structural, heat sinks |
| Al_7075 | 7075 Aluminum alloy | Aerospace |
| Al_2024 | 2024 Aluminum alloy | Aircraft skin |
| Al_5052 | 5052 Aluminum alloy | Marine, fuel tanks |
| Steel_1018 | 1018 Carbon steel | General machining |
| Steel_4140 | 4140 Alloy steel | Shafts, gears |
| Inconel_625 | Inconel 625 | High-temp, corrosion-resistant |
| Inconel_718 | Inconel 718 | Jet engines, turbines |
| Hastelloy_C276 | Hastelloy C-276 | Chemical processing |
| Maraging_300 | Maraging 300 steel | Tooling, aerospace |
| BeCu_C172 | Beryllium copper C172 | Springs, connectors |
| Brass_C260 | Brass C260 | Fittings, valves |
| Bronze_C510 | Phosphor bronze C510 | Springs, bearings |
| Cast_Iron | Cast iron | Engine blocks, cookware |
| CP_Ti_Gr2 | Commercially pure Ti Grade 2 | Medical implants |
| Tool_A2 | A2 Tool steel | Dies, punches |
| Ag | Silver | Contacts, brazing |
| Au | Gold | Bonding wires, contacts |
| Pt | Platinum | Catalysts, sensors |
| Mo | Molybdenum | High-temp furnaces |
| W | Tungsten | Filaments, radiation shielding |
| Sn | Tin | Solder, plating |
| Zn | Zinc | Galvanizing, anodes |
| Pb | Lead | Batteries (lead-acid), shielding |
| Mg | Magnesium | Lightweight structural |

### Ceramic Domain (28 materials)

Structural ceramics, electronic ceramics, bioceramics, and solid electrolytes.

| What you type | What it is | Common use |
|---|---|---|
| Al2O3 | Alumina | Substrates, wear parts |
| ZrO2_YSZ | Yttria-stabilized zirconia | Fuel cells, dental |
| ZrO2_PSZ | Partially stabilized zirconia | Structural ceramic |
| SiC | Silicon carbide | Armor, abrasives |
| Si3N4 | Silicon nitride | Bearings, turbines |
| BN_hex | Hexagonal boron nitride | Thermal management |
| AlN | Aluminum nitride | LED substrates, heat sinks |
| SiO2 | Silica (quartz) | Optical, crucibles |
| TiO2 | Titania | Photocatalysis, coatings |
| MgO | Magnesia | Refractory, insulation |
| WC | Tungsten carbide | Cutting tools |
| B4C | Boron carbide | Armor, abrasives |
| TiC | Titanium carbide | Coatings, tools |
| TiN | Titanium nitride | Hard coatings, gold color |
| BaTiO3 | Barium titanate | Capacitors, sensors |
| PZT | Lead zirconate titanate | Piezo sensors, actuators |
| Mullite | 3Al2O3-2SiO2 | Kiln furniture, refractories |
| Spinel | MgAl2O4 | Transparent armor, optics |
| Hydroxyapatite | Ca10(PO4)6(OH)2 | Bone implants |
| TCP | Tricalcium phosphate | Bone scaffolds |
| Bioglass | 45S5 Bioglass | Bone repair |
| NASICON | Na3Zr2Si2PO12 | Na-ion solid electrolyte |
| LLZO | Li7La3Zr2O12 | Li-ion solid electrolyte |
| LGPS | Li10GeP2S12 | Li-ion solid electrolyte |
| Li3PS4 | Lithium thiophosphate | Li-ion solid electrolyte |
| LAS | Lithium aluminosilicate | Low-expansion cooktops |
| Soda_Lime | Soda-lime glass | Windows, bottles |
| Borosilicate | Borosilicate glass | Lab glassware |

### Semiconductor Domain (27 materials)

| What you type | What it is | Common use |
|---|---|---|
| Si | Silicon | Chips, solar cells |
| Ge | Germanium | IR optics, SiGe HBTs |
| GaAs | Gallium arsenide | RF, solar, LEDs |
| GaN | Gallium nitride | Power electronics, LEDs |
| InP | Indium phosphide | Fiber optics, lasers |
| SiC_4H | 4H Silicon carbide | Power MOSFETs, EVs |
| SiC_6H | 6H Silicon carbide | LEDs (blue/green) |
| GaP | Gallium phosphide | LEDs (green) |
| InAs | Indium arsenide | IR detectors |
| InSb | Indium antimonide | IR sensors, Hall sensors |
| AlAs | Aluminum arsenide | Heterostructure barriers |
| AlGaAs | Aluminum gallium arsenide | Lasers, solar cells |
| InGaAs | Indium gallium arsenide | Photodetectors, fiber |
| AlGaN | Aluminum gallium nitride | UV LEDs, HEMTs |
| SiGe | Silicon germanium | BiCMOS, HBTs |
| CdTe | Cadmium telluride | Solar cells, X-ray |
| ZnO | Zinc oxide | Varistors, transparent conductors |
| ZnSe | Zinc selenide | IR windows, lasers |
| AlN | Aluminum nitride | UV-C LEDs |
| InN | Indium nitride | Terahertz devices |
| Ga2O3 | Gallium oxide | Ultra-wide bandgap power |
| MoS2 | Molybdenum disulfide | 2D transistors |
| WS2 | Tungsten disulfide | 2D electronics |
| IGZO | Indium gallium zinc oxide | Display TFTs |
| C_diamond | Diamond | Heat spreaders, quantum |
| HgCdTe | Mercury cadmium telluride | IR focal plane arrays |
| Bi2Te3 | Bismuth telluride | Thermoelectrics |

### Glass Domain (23 materials)

| What you type | What it is | Common use |
|---|---|---|
| SodaLime_Float | Soda-lime float glass | Windows |
| SodaLime_Container | Soda-lime container glass | Bottles |
| SodaLime_Tempered | Tempered soda-lime | Automotive, safety |
| Boro_33 | Borosilicate 3.3 (Pyrex-type) | Lab glassware |
| Boro_51 | Borosilicate 5.1 | Ampoules, tubing |
| Boro_Neutral | Neutral borosilicate | Pharma vials |
| BK7 | Schott BK7 | Optical lenses |
| F2 | Schott F2 (flint glass) | Prisms |
| LAK9 | Schott LAK9 (lanthanum crown) | Camera lenses |
| FusedSilica | Fused silica | UV optics, fiber |
| QuartzGlass | Quartz glass | Semiconductor processing |
| AlSi_Display | Aluminosilicate display glass | Phone/tablet screens |
| AlSi_ChemStrength | Chem-strengthened aluminosilicate | Gorilla Glass type |
| LAS_Zerodur | Zerodur (LAS glass-ceramic) | Telescope mirrors |
| LAS_Cooktop | LAS cooktop glass-ceramic | Stove tops |
| Lead_Crystal | Lead crystal | Decorative glassware |
| Lead_Dense_Flint | Dense flint (leaded) | Radiation shielding |
| Bioglass_45S5 | 45S5 Bioglass | Medical implants |
| S53P4 | S53P4 bioactive glass | Bone infection treatment |
| LaserPhosphate | Laser phosphate glass | Nd-doped laser glass |
| ZBLAN | ZrF4-BaF2-LaF3-AlF3-NaF | IR fiber optics |
| As2S3 | Arsenic trisulfide | IR lenses |
| Ge28Sb12Se60 | Chalcogenide glass | IR thermal imaging |

### MOF Domain (30 Metal-Organic Frameworks)

These are porous crystalline materials used for gas storage, catalysis, separation, and drug delivery. MOFs are scored against **operating conditions** (temperature, pressure, target molecule), not against other materials.

| Family | MOFs | Key properties |
|---|---|---|
| ZIF | ZIF-8, ZIF-67, ZIF-90 | Zeolitic topology, excellent water stability |
| UiO | UiO-66, UiO-67, UiO-68 | Zr-based, extreme stability |
| MIL | MIL-53, MIL-88, MIL-101, MIL-125 | Cr/Ti-based, high porosity |
| IRMOF | IRMOF-1, IRMOF-3 | Classic Zn-carboxylate frameworks |
| Others | HKUST-1, MOF-5, MOF-74, NU-1000, PCN-222, PCN-224, etc. | Various applications |

All 30 MOFs have DOI citations and experimental data (BET surface area, pore diameter, thermal stability, water stability).

**MOF Linker Inverse Design**: Generate novel organic linkers for MOFs with exact atom count control (5-60 atoms, default 22). Candidates are scored by a **validated grounded funnel** (chemical sanity, ≥2 coordinating donors, SAscore, donor geometry, + novelty vs. known linkers): ~94% recall on held-out real synthesized linkers, AUROC ~0.88. Donor atom filtering (N, O, S). **Directed generation** lets a researcher steer the search — strategy-weight sliders, seed-molecule pinning (only derivatives of one SMILES), and required functional groups. Built for **Prof. Heather Kulik** (MIT) to solve her #1 LLM challenge: "I just ask it, please design me a ligand that has 22 atoms. I can never get an answer that has 22 atoms." KOMPOSOS guarantees exact count.

### Also: 37 Molecules (molecular-level analysis)

These are individual chemical compounds used for molecular-level scoring (different from material-level). You use these with the Molecule Compatibility checker.

Solvents: EC, DMC, EMC, DEC, PC, FEC, VC, NMP, Water, Acetone, Toluene
Salts: LiPF6, LiTFSI, LiBF4, LiClO4
Precursors: Li2CO3, LiOH, NiSO4, CoSO4, FeSO4, MnO2, TiO2, H3PO4
Gases: H2, O2, N2, CO2, Ar
Monomers: vinylidene_fluoride, acrylonitrile, styrene, methyl_methacrylate, ethylene_oxide
Metal alkoxides: Ti_isopropoxide, Al_isopropoxide, Zr_propoxide, Al_NO3_3
Other: citric_acid, oxalic_acid, urea

---

## 3. The Sign-In System -- What It Does

### Three tiers

| Tier | How you get it | What it gives you |
|---|---|---|
| **Demo** (default) | Just open the app, no login needed | 3 analyses per session |
| **Voucher** | Enter a client-specific code | Custom limit (e.g., 20 analyses) |
| **Admin** | Enter admin password | Unlimited |

### What "analyses" are counted

Each time you click a button that runs a computation (Check Compatibility, Generate Report, Predict Composition, etc.), that counts as one use. Browsing pages, looking at material lists, and reading results do NOT count.

### How it works right now

The sign-in box appears in the **sidebar** of every page. If you don't enter anything, you're in demo mode with 3 free analyses. After 3, you see a message saying "Demo limit reached" with contact info.

### Setting up codes for clients

All configuration is via environment variables -- no database, no user accounts:

```bash
# Set admin password (default is "komposos-admin")
export KOMPOSOS_ADMIN_PASSWORD="your-secure-password"

# Create voucher codes for clients (format: CODE:limit,CODE:limit)
export KOMPOSOS_VOUCHER_CODES="ATEIOS2026:50,CERTIVO2026:20,SAMSUNG2026:100"

# Change demo limit (default 3)
export KOMPOSOS_DEMO_LIMIT=5
```

When you give a client their code (e.g., "ATEIOS2026"), they type it in the sidebar and get 50 analyses. When they run out, they contact you for more.

### Do you need it for the demo?

**For a live demo to a client**: You probably don't need the login at all. Just show them the tool. The 3 free analyses is enough for a demo session (check compatibility, run PFAS scan, predict a composition).

**For a deployed pilot**: Yes, use voucher codes. Give each client their own code so you can track usage and limit access.

**For a public demo site**: The 3-scan limit is perfect. It lets people try it without giving away unlimited access.

---

## 4. Is 175 Materials Enough?

### The honest answer

**For a demo: Yes, absolutely.** 175 materials covers the most important battery, polymer, metal, ceramic, semiconductor, and glass materials. Any battery company will see NMC811, LFP, PVDF, EC, DMC, LiPF6, Cu foil, Al foil -- their actual bill of materials.

**For a production tool: You'll need to add client-specific materials.** A ceramic company won't find their proprietary alumina blend. A semiconductor fab won't find their specific resist formulations. That's expected -- you'd add those as part of onboarding.

### What the 175 covers well

- **Li-ion batteries**: Full cell stack (cathodes, anodes, electrolytes, binders, collectors, separators). This is the strongest vertical.
- **Structural metals**: Standard alloys (6061, 7075, 304SS, 316SS, Ti6Al4V, Inconel). Good for aerospace/automotive.
- **Engineering polymers**: All the major plastics plus battery-specific binders.
- **Ceramics**: Structural, electronic, bio, and solid electrolytes.
- **PFAS compliance**: The PFAS scanner works on ANY material name, not just the 199. It checks against 35 known PFAS substances plus heuristic detection with 11 brand names (Teflon, Kynar, Viton, Scotchgard, Gore-Tex, etc.). Brand names auto-resolve to base substances (e.g., "Teflon" resolves to PTFE).
- **MOFs**: 30 Metal-Organic Frameworks for gas storage, catalysis, separation. Scored against operating conditions, not material pairs.

### What it doesn't cover

- Proprietary formulations (a client's custom electrolyte blend)
- Niche materials (rare earth compounds, specialty glasses)
- Organic chemistry beyond the 37 molecules (drugs, fragrances, agricultural chemicals)

### Does the mix look legitimate?

**Yes for batteries and metals.** These are real industrial materials with real names that engineers recognize.

**The glass names are technical** (BK7, LAK9, ZBLAN) -- a glass company would know these, but a general audience might not. That's fine, because a general audience wouldn't be evaluating glass compatibility.

---

## 5. How PFAS Detection Actually Works

### What happens when you scan a material

1. **Exact match** (detection tier: `exact`): The name is compared against 35 known PFAS substances (PVDF, PTFE, FEP, Nafion, PFOA, PFOS, etc.). Each has a CAS number, regulatory status, and urgency level.

2. **Heuristic match** (detection tier: `heuristic`): If the name isn't an exact match, it's checked against 36+ substrings including 11 brand names:
   - "Teflon" -> resolves to PTFE (gets PTFE's replacements + CAS number)
   - "Kynar" -> resolves to PVDF
   - "Viton" -> resolves to FKM (fluoroelastomer)
   - "Scotchgard", "Gore-Tex", "Stainmaster", "Chemours", etc.
   - Anything containing "fluoro" or "pfas" -> flagged
   - Brand names auto-resolve to base PFAS substance, so heuristic matches get the same quality results as exact matches

3. **Structural / novel match** (detection tier: `structural` or `structural_resolved`):
   If the name isn't a known substance or brand, the scanner resolves it to a structure
   (direct SMILES, or name→PubChem→SMILES) and applies the **OECD structural rule**
   (CF2/CF3 definition). This is what lets it catch a **novel PFAS never seen by name**.

4. **Unknown** (detection tier: `unknown`): If nothing matches and no structure can be
   resolved, the material is flagged for manual review (treated as not-detected).

Each result includes a `detection_tier` field (exact/heuristic/structural/structural_resolved/
unknown) and a `resolved_base`/`resolved_smiles` field showing what was identified.
Specificity is 100% on a 25-molecule hard-negative panel; 99.5% concordance with the EPA list.

### What information you need from the client

To run a PFAS scan, you need:
- **Material name** (required) -- e.g., "PVDF", "Kynar 761", "Teflon FEP"
- **Function** (optional but helpful) -- e.g., "cathode binder", "gasket seal"
- **Quantity in kg** (optional) -- for reporting purposes

You do NOT need:
- CAS numbers (the system looks them up)
- Chemical formulas
- Supplier data sheets

### The gap: what the scanner CAN'T detect

The scanner works on **names**. If a client gives you "Polymer X" or "Coating 7B" or a trade name the system doesn't know, it will say "PFAS-FREE" even if the material contains PFAS.

**To make it reliable for a real engagement:**
- Ask the client for the **chemical name or CAS number** of each material, not just trade names
- If they give you proprietary names, ask what the base polymer/chemistry is
- For coatings and adhesives, ask specifically: "does this contain any fluorinated compounds?"

The scanner is a first-pass screening tool, not a lab analysis. It catches the obvious PFAS (PVDF, PTFE, FEP, Nafion) that show up in battery/industrial BOMs. For regulatory filing, the client still needs analytical testing (LC-MS/MS) to confirm.

**Validation grounding** (audited 2026-07-17): compatibility development regression
is 41/41. No dataset is currently blind; Q9 is also spent (35/40 after remediation)
and Q10 remains sealed. The deployed 98-row development/spent isotonic artifact
reports OOS ECE 0.072, but that does not prove domain-specific calibration or
calibrate whole-stack aggregates. Current strict-formula formation-energy LOO is
MAE 0.416 eV/atom (n=179), with deployed interval coverage 50/79/95%. GROMACS is
an optional verification path only when an applicable simulation is configured;
its existence is not blanket high-stakes validation.

---

## 6. How to Add New Materials

### The simple version

Each domain has a file called `material_properties.py`. To add a material, you add an entry to the dictionary in that file with the material's properties.

### Example: Adding a new battery cathode

Open `battery_bridge/material_properties.py` and add:

```python
"NCA": BatteryMaterial(
    name="NCA",
    material_class=MaterialClass.CATHODE,
    voltage_window=VoltageWindow(lower=2.5, upper=4.3, nominal=3.7),
    capacity_mAh_g=200,
    thermal_stability_max=150,    # degrees C
    volume_expansion=0.04,
    crystal_structure="layered",
),
```

### Example: Adding a new polymer

Open `polymer_bridge/material_properties.py` and add:

```python
"TPU": PolymerMaterial(
    name="TPU",
    abbreviation="TPU",
    glass_transition_C=-40,
    melting_point_C=220,
    decomposition_temp_C=350,
    elastic_modulus_GPa=0.02,
    elongation_at_break_pct=600,
    water_absorption_pct=0.5,
),
```

### What properties you need

Each domain has different required properties. The minimum is just a name -- the system will work with partial data (scoring will be less precise but won't crash). Here's what matters most per domain:

| Domain | Critical properties |
|---|---|
| Battery | voltage_window (upper, lower, nominal), capacity, thermal_stability_max |
| Polymer | glass_transition_C, melting_point_C, decomposition_temp_C |
| Metal | density, melting_point, CTE, yield_strength, galvanic_potential |
| Ceramic | sintering_temp, CTE, fracture_toughness |
| Semiconductor | band_gap_eV, mobility, lattice_constant |
| Glass | CTE, softening_point, Tg |

### For a client engagement

The process would be:

1. **Client sends their BOM** (bill of materials) with material names
2. **You map their names** to existing materials in KOMPOSOS (e.g., "Kynar 761" -> PVDF)
3. **For materials we don't have**, you add them to the appropriate bridge file with whatever property data the client provides or you can find in literature/datasheets
4. **Run the analysis** and deliver the report

This is a services component -- you're adding value by curating the data for each client's specific use case.

---

## 7. How to Present This to a Client

### The pitch in 30 seconds

"We provide first-pass PFAS inventory and materials-compatibility screening with
an audit trail. Applicable PFHxA scope and dates depend on product and use; we
verify the current official rule before any compliance statement."

### What to show in a demo

1. **PFAS Scanner**: Enter materials or use the demo BOM. Show structural/name
   detection and the evidence tier. Replacement results are triage; show pairwise
   coverage and withhold a full-stack value when any contact is unscored.

2. **Compatibility Checker**: Show the native pairwise decision, derived constraint
   diagnostic, scorer breakdown, and calibration cohort. Do not present the two
   views as independent evidence.

3. **Composition Predictor** (1 minute): Enter a chemical formula. Show predicted voltage, capacity, structure type, and derived crystal structure with MP provenance. This is the "wow" moment -- it predicts properties from composition alone.

4. **Crystal Dreamer**: Set target properties and show a small lead set with
   uncertainty and physical gates. Runtime depends on candidate count and checks;
   do not promise 500 candidates in 2.5 seconds.

### What NOT to say

- Don't say "175 materials" -- say "curated materials database covering 6 industrial domains"
- Call a demo a demo; call it a pilot only when a user has agreed to a scoped pilot.
- Don't promise it replaces lab testing -- say "it prioritizes what to test first"
- Don't claim ML/AI -- say "interpretable compositional reasoning with published data"

### Value angle

The defensible value is a fast, auditable first-pass PFAS inventory plus
replacement triage. It is not a legal compliance determination. Regulatory
scope and dates vary by substance, product, use, and jurisdiction: the broad EU
restriction remains under evaluation, while narrower restrictions such as
PFHxA already have use-specific transition dates. Verify the current official
rule for every client-facing statement.

---

## 8. Making It Real for a Specific Client

### Step 1: Get their BOM
Ask for: material names, functions, quantities, and (if possible) CAS numbers or chemical names for anything proprietary.

### Step 2: Map to KOMPOSOS
Match their materials to the current internal benchmark pairs. Make a list of what's missing and do not treat matches as externally validated without source review.

### Step 3: Add missing materials
For each missing material, find published property data (datasheets, literature, MatWeb, Materials Project) and add it to the appropriate bridge file.

### Step 4: Run and deliver
Generate the PFAS compliance report (enter their company name in the "Client / Company Name" field for branded reports), compatibility matrices, and any composition predictions they need. Download the PDF -- it includes domain-specific scores (Adhesion, Electrolyte, Thermal, Cathode), provenance chains, action plans with priority levels, and an audit certificate.

### Step 5: Iterate
Client says "what about Material X with Material Y?" -- you run the query and give them the answer. Each interaction reinforces the value.

---

## Summary

| Question | Answer |
|---|---|
| How many materials? | 199 across 7 domains + 37 molecules + 35 PFAS + 30 MOFs |
| Is that enough for a demo? | Yes |
| Is that enough for production? | No -- you add client materials |
| What does sign-in do? | Limits free analyses (3 demo, custom for clients) |
| Do you need sign-in for a demo? | No, 3 free scans is enough |
| How does PFAS detection work? | Name match (35 substances) + brand heuristics + **OECD structural rule via PubChem** for novel PFAS; tiers exact/heuristic/structural/structural_resolved/unknown |
| What about replacements? | Ranked by a coverage-aware interface screen. A full-stack bottleneck is shown only when every required contact has a native score; otherwise the missing contacts remain explicit. |
| What does the client need to provide? | Material names (ideally chemical names, not just trade names) |
| How do you add materials? | Add entries to `material_properties.py` in the relevant bridge |
| What's the value angle? | Auditable first-pass PFAS inventory and replacement triage; never a blanket legal-compliance promise. |
| What's the deliverable? | Branded screening report with evidence tiers, coverage, provenance, and follow-up actions. |
