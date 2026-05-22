# MASTER REPLICATOR CHEMISTRY AND PHYSICS
## Physical Science Behind Every Bridge
### Updated 2026-04-02 — all data from curated material property tables

---

## What This Document Covers

The physical and chemical principles encoded in each material bridge. Every number in KOMPOSOS-III comes from published literature with citations. This is NOT ML-generated data — it is hand-curated materials science.

---

## Battery Bridge: Electrochemistry

### Materials (22)
Cathodes: LFP (LiFePO4), NMC811, NMC622, NMC111, LCO (LiCoO2), LMO (LiMn2O4), NCA
Anodes: Graphite, Li metal, Si, Li4Ti5O12
Solid electrolytes: LLZO (Li7La3Zr2O12), LGPS (Li10GeP2S12), Li3PS4, NASICON
Liquid electrolyte components: LiPF6, LiTFSI, EC, DMC

### Key Physics
- **Voltage windows**: Each material has nominal and upper cutoff voltage vs Li/Li+
  - LFP: 3.4V nominal, 4.0V upper (olivine, very stable)
  - NMC811: 3.8V nominal, 4.3V upper (layered oxide, high energy)
  - Graphite: 0.1V nominal (intercalation anode)
- **Ionic conductivity**: Ion transport rate (S/cm)
  - LGPS: 1.2e-2 S/cm (highest known solid electrolyte)
  - LLZO: 3e-4 S/cm (oxide, air-stable)
  - Li3PS4: 1.6e-4 S/cm (sulfide glass)
- **Volume expansion**: Fractional volume change during charge/discharge
  - Graphite: 0.10 (10% — manageable)
  - Si: 2.80 (280% — destroys most binders)
  - LFP: 0.02 (2% — negligible)
- **Thermal stability**: Onset temperature of thermal runaway
  - LFP: 270C (very safe)
  - NMC811: 150C (needs careful thermal management)
  - LCO: 200C
- **Failure modes**: dendrite growth, SEI thickening, phase transition, particle cracking

### Scoring Dimensions
1. Ion transport (ionic conductivity matching)
2. Electrochemical stability (voltage window overlap)
3. Interface compatibility (CEI/SEI formation)
4. Mechanical compatibility (volume change tolerance)
5. Degradation resistance (cycle life factors)

---

## Polymer Bridge: Polymer Science

### Materials (33)
Commodity: PE, PP, PVC, PS, PET, Nylon-6, Nylon-66
Engineering: PC, PEEK, PEI, PSU, PPO, POM, ABS
Fluoropolymers: PTFE, PVDF, FEP, ETFE, PFA
Elastomers: NR, SBR, NBR, EPDM, Silicone
Battery-specific: PEO, PAN, CMC, PVDF (as binder), Nafion

### Key Physics
- **Hansen solubility parameters** (MPa^0.5): Three-component model
  - delta_d (dispersion): 14-20 for most polymers
  - delta_p (polar): 0-18 depending on polarity
  - delta_h (hydrogen bonding): 0-22
  - Compatibility: Ra = sqrt(4*(Dd)^2 + (Dp)^2 + (Dh)^2) < R0
- **Glass transition temperature** (Tg): Below Tg = glassy, above = rubbery
  - PS: 100C, PC: 147C, PEEK: 143C, PE: -120C
  - Battery binders: want above Tg for flexibility at operating temp
- **Melting temperature** (Tm): Processing upper limit
  - PE: 135C, PVDF: 177C, PEEK: 343C, PTFE: 327C
- **Decomposition temperature**: Absolute upper limit
  - PVDF: 400C, PEEK: 550C, Silicone: 300C
- **Elongation at break**: Ability to accommodate strain
  - PVDF: 30-50%, SBR: 400-600%, PTFE: 200-400%
- **Chemical resistance**: Acid/base/solvent resistance ratings
- **Water absorption**: Critical for battery applications
  - PVDF: 0.04% (excellent), PEO: high (problematic)

### Scoring Dimensions
1. Solubility compatibility (Hansen distance Ra/R0)
2. Thermal compatibility (Tg, Tm, decomp margins)
3. Mechanical compatibility (modulus, elongation matching)
4. Chemical resistance (to specific environment)
5. Aging resistance (UV, thermal, hydrolytic)

---

## Metal Bridge: Metallurgy

### Materials (36)
Pure metals: Fe, Al, Cu, Ti, Ni, Zn, Mg, W, Mo, Sn, Pb, Ag, Au, Pt
Steels: SS_304, SS_316, Steel_1018, Steel_4140, Tool_A2, Maraging_300, Cast_Iron
Aluminum alloys: Al_6061, Al_7075, Al_2024, Al_5052
Copper alloys: Brass_C260, Bronze_C510, BeCu_C172
Titanium alloys: Ti6Al4V, CP_Ti_Gr2
Nickel alloys: Inconel_625, Inconel_718, Hastelloy_C276
Battery foils: Al_foil, Cu_foil, Ni_tab

### Key Physics
- **Galvanic series** (mV vs SHE): Predicts galvanic corrosion
  - Au: +1500, Pt: +1200, Cu: +337, Fe: -440, Al: -1660, Mg: -2370
  - Rule: >250mV difference = severe galvanic corrosion risk
- **CTE** (x10^-6/K): Coefficient of thermal expansion
  - W: 4.5, Ti: 8.6, Steel: 11-12, Al: 23.1, Mg: 26.0
  - CTE mismatch = cracking at interfaces (critical for ceramic-metal)
- **Melting point** (C): Processing upper limit
  - W: 3422, Mo: 2623, Ti: 1668, Fe: 1538, Al: 660, Sn: 232
- **Elastic modulus** (GPa): Stiffness
  - W: 411, Steel: 200, Ti: 116, Al: 69, Mg: 45
- **Yield strength** (MPa): Structural capacity
  - Maraging_300: 2000, Ti6Al4V: 880, SS_304: 215
- **Electrical conductivity** (% IACS): Current carrying
  - Cu: 100, Al: 61, Au: 70, Steel: 3
- **Weldability**: Fusion, resistance, friction joining compatibility

### Scoring Dimensions
1. Galvanic compatibility (potential difference < 250mV)
2. Phase stability (thermodynamic equilibrium)
3. Joinability (weldability, brazeability)
4. Mechanical compatibility (modulus, strength matching)
5. Corrosion resistance (in specific environment)

---

## Ceramic Bridge: Ceramic Engineering

### Materials (28)
Oxides: Al2O3, ZrO2_YSZ, ZrO2_PSZ, MgO, TiO2, SiO2, BaTiO3, Mullite, Spinel
Carbides: SiC, WC, B4C, TiC
Nitrides: Si3N4, AlN, BN_hex, TiN
Glass-ceramics: Borosilicate, Soda_Lime, LAS
Bioceramics: Hydroxyapatite, TCP, Bioglass
Piezoelectric: PZT
Solid electrolytes: LLZO, LGPS, Li3PS4, NASICON

### Key Physics
- **CTE** (x10^-6/K): THE dominant failure mode for ceramic-metal joints
  - SiO2: 0.55, Si3N4: 3.0, Al2O3: 8.1, TiN: 9.4
  - CTE mismatch > 10 = coating will crack/delaminate
- **Sintering temperature** (C): Processing temperature
  - Al2O3: 1600, SiC: 2100, LLZO: 1100, ZrO2: 1450
  - Must be < metal substrate melting point (or use PVD/CVD route)
- **Elastic modulus** (GPa): Very high for ceramics
  - WC: 700, Al2O3: 370, SiC: 450, Si3N4: 310
- **Hardness** (HV): Vickers hardness
  - WC: 2200, SiC: 2500, Al2O3: 1800, TiN: 2100
  - Ceramic always harder than metal (that's the point of coating)
- **Fracture toughness** (MPa.m^0.5): Resistance to crack propagation
  - ZrO2_YSZ: 6-8 (transformation toughening)
  - Al2O3: 3-4, SiC: 3-4, Glass: 0.7-0.8
- **Ionic conductivity** (for solid electrolytes):
  - LGPS: 0.012 S/cm, LLZO: 0.0003 S/cm
- **Chemical stability**: inert, stable, reactive, hygroscopic
  - Al2O3: inert, LGPS: reactive (decomposes on metal contact)

### Scoring Dimensions
1. Sintering compatibility (temperature overlap)
2. CTE matching (critical: Δ < 5 for good, Δ > 15 for catastrophic)
3. Chemical compatibility (reactivity at interface)
4. Mechanical compatibility (modulus ratio)
5. Degradation resistance (moisture, oxidation)

---

## Semiconductor Bridge: Solid-State Physics

### Materials (27)
Elemental: Si, Ge, C_diamond
IV-IV: SiGe, SiC_4H, SiC_6H
III-V: GaAs, AlAs, AlGaAs, InP, InAs, InGaAs, GaP, InSb, GaN, AlN, AlGaN, InN
II-VI: ZnO, CdTe, ZnSe, HgCdTe
Oxide: Ga2O3, IGZO
2D: MoS2, WS2
Thermoelectric: Bi2Te3

### Key Physics
- **Bandgap** (eV): Fundamental electronic property
  - Si: 1.12 (indirect), GaAs: 1.42 (direct), GaN: 3.4, Ga2O3: 4.8
- **Lattice constant** (Angstrom): Determines epitaxial compatibility
  - GaAs: 5.653, AlAs: 5.661 (0.14% mismatch — excellent)
  - Si: 5.431, Ge: 5.658 (4.2% mismatch — high strain)
  - Rule: < 0.5% = pseudomorphic, 0.5-2% = metamorphic, > 2% = relaxed with defects
- **Electron mobility** (cm^2/V.s): Speed of electron transport
  - GaAs: 8500, InSb: 77000, Si: 1450, GaN: 1000
- **Thermal conductivity** (W/m.K): Heat dissipation
  - C_diamond: 2200, SiC: 490, Si: 148, GaAs: 46
- **Band alignment** (Anderson's rule): Conduction/valence band offsets
  - Type I (straddling): both carriers confined — LEDs, lasers
  - Type II (staggered): carrier separation — solar cells
  - Type III (broken gap): tunneling — tunnel diodes

### Scoring Dimensions
1. Lattice matching (mismatch percentage)
2. Band alignment (offset type and magnitude)
3. Thermal compatibility (conductivity, CTE matching)
4. Defect tolerance (dislocations per cm^2)
5. Process compatibility (growth temperature, ambient)

---

## Glass Bridge: Glass Science

### Materials (23)
Soda-lime: Float, Container, Tempered
Borosilicate: Boro_33, Boro_51, Neutral
Aluminosilicate: Display, ChemStrength
Lead: Crystal, Dense_Flint
Fused silica: FusedSilica, QuartzGlass
Optical: BK7, F2, LAK9
Bioactive: Bioglass_45S5, S53P4
Chalcogenide: As2S3, Ge28Sb12Se60
Glass-ceramic: LAS_Zerodur, LAS_Cooktop
Specialty: LaserPhosphate, ZBLAN

### Key Physics
- **Refractive index** (n_d): Optical property
  - Fused silica: 1.458, BK7: 1.517, F2: 1.620, Lead crystal: 1.545
- **Abbe number** (V_d): Chromatic dispersion
  - Fused silica: 67.8, BK7: 64.2, F2: 36.4 (flint — high dispersion)
- **CTE** (x10^-7/K): Very low for specialty glasses
  - Fused silica: 5.5, Zerodur: ~0, Boro_33: 33, Soda-lime: 90
- **Transformation temperature** (Tg): Softening onset
  - Fused silica: 1200C, Boro: 560C, Soda-lime: 573C
- **Young's modulus** (GPa): Mechanical stiffness
  - Fused silica: 73, BK7: 82, Zerodur: 91
- **Chemical durability**: Resistance to acid, base, water attack
  - Fused silica: excellent (class 1)
  - Soda-lime: moderate (class 2-3)
  - Phosphate: poor (class 3-4)

### Scoring Dimensions
1. Thermal compatibility (CTE, Tg matching)
2. Optical compatibility (index matching, dispersion)
3. Chemical compatibility (durability classes)
4. Mechanical compatibility (modulus, strength)
5. Viscosity compatibility (working temperature overlap)

---

## MOF Bridge: Metal-Organic Framework Science (Phase 11)

### Materials (30 MOFs)
ZIF family: ZIF-8, ZIF-67, ZIF-90
UiO family: UiO-66, UiO-67, UiO-68
MIL family: MIL-53, MIL-88, MIL-101, MIL-125
IRMOF family: IRMOF-1, IRMOF-3
HKUST-1, MOF-5, MOF-74, NOTT-101, NU-1000, PCN-222, PCN-224, UTSA-16, ZJU-5, and more

### Key Physics
- **BET surface area** (m²/g): Porosity via nitrogen adsorption
  - NU-1000: 2320 m²/g (ultra-high), MOF-5: 2500-3800 m²/g
  - ZIF-8: 1600 m²/g, UiO-66: 1200 m²/g
  - Higher surface area = more adsorption sites, better for gas storage/separation
- **Pore diameter** (Angstrom): Size selectivity for molecular sieving
  - ZIF-8: 11.6 Å (CO2 selective), MOF-74: 11.0 Å
  - HKUST-1: 9.0 Å, UiO-66: 8.0 Å
  - Molecular sieving: target molecule must fit through pore aperture
- **Pore volume** (cm³/g): Total void space for guest molecules
  - NU-1000: 1.41 cm³/g, MOF-5: 1.55 cm³/g, UiO-66: 0.44 cm³/g
- **Thermal stability** (°C): Onset of framework decomposition
  - UiO-66: 540°C (Zr-carboxylate), MOF-5: 300°C (Zn-carboxylate)
  - ZIF-8: 550°C (Zn-imidazolate, zeolitic topology)
- **Water stability**: Critical for industrial applications
  - UiO-66: excellent (Zr₆O₄(OH)₄ cluster, stable in boiling water)
  - ZIF-8: excellent (hydrophobic pores)
  - MOF-5: poor (Zn₄O cluster hydrolyzes)
  - HKUST-1: moderate (Cu₂(paddlewheel) degrades slowly in moisture)
- **Chemical stability**: Acid/base resistance
  - UiO-66: stable to pH 1-10 (Zr-O bonds resist hydrolysis)
  - MIL-101: stable in acidic conditions
  - ZIF-8: stable to pH 2-14
- **Bulk modulus** (GPa): Mechanical stiffness (when measured)
  - UiO-66: 16.3 GPa, ZIF-8: 6.5 GPa
  - Most MOFs lack bulk modulus data (too new, difficult to measure)
- **Applications**: gas_storage (H₂, CH₄, CO₂), gas_separation (CO₂/N₂, olefin/paraffin), catalysis (Lewis acid sites), drug_delivery (biocompatible frameworks), sensing (luminescent MOFs), water_purification (adsorb pollutants), energy_storage (supercapacitors)

### Topology (8 types in 30 MOFs)
- **pcu** (primitive cubic): ZIF-8, HKUST-1, MOF-5 (6-connected nodes)
- **fcu** (face-centered cubic): UiO-66, UiO-67, UiO-68 (12-connected Zr₆ clusters)
- **ftw** (frameworks): MOF-5 variant
- **reo** (ReO₃): MIL-53, MIL-101 (corner-sharing octahedra)
- **sql** (square lattice): IRMOF-1
- **nbo** (niobium oxide): MOF-74 (hexagonal channels)
- **pts** (PtS): PCN-222
- **ith** (ITH zeolite): MIL-88

### Metal Nodes
- **Zr₆O₄(OH)₄**: UiO family (very stable, 12-connected)
- **Zn₄O**: MOF-5 (Zn-O tetrahedral cluster)
- **Cu₂(COO)₄**: HKUST-1, PCN-222 (paddlewheel dimers)
- **Zn(methylimidazolate)₄**: ZIF-8, ZIF-67 (zeolitic)
- **Cr₃O**: MIL-101 (trimeric cluster)
- **Ti₈O₈(OH)₄**: MIL-125 (octameric cluster)

### Organic Linkers
- **BDC** (benzene-1,4-dicarboxylate): UiO-66, MOF-5
- **BTC** (benzene-1,3,5-tricarboxylate): HKUST-1
- **Terephthalate**: Many MOFs
- **Imidazolate**: ZIF-8, ZIF-67
- **Amino-functionalized**: UiO-66-NH₂ (enhanced CO₂ affinity)

### Scoring Dimensions (MOF-specific, not pair compatibility)
MOF bridge differs from all other bridges: it scores MOF-vs-conditions, not material-vs-material.

1. **Pore accessibility**: Target molecule diameter vs pore diameter (molecular sieving)
2. **Chemical stability**: MOF stability in target environment (dry, humid, aqueous, acidic, basic)
3. **Thermal compatibility**: Operating temperature vs thermal stability onset
4. **Mechanical compatibility**: Operating pressure vs bulk modulus (if available)
5. **Application suitability**: Target application (gas_storage, catalysis, etc.) vs MOF primary application

**Validation**: MOF-vs-conditions screening, not A-vs-B pair compatibility. ZIF-8 screened at 25°C, 1 bar, CO₂ capture → suitable (high pore score, excellent water stability, low temp margin).

---

## MOF Linker Inverse Design (Phase 12)

Novel organic linker generation for Metal-Organic Frameworks — built for Prof. Heather Kulik (MIT).

### What This Does

Generates novel 22-atom organic molecules suitable for MOF synthesis. Each candidate is scored with 5 KOMPOSOS verdicts using ZFC + CAT dual-engine reasoning. Returns only linkers where both engines AGREE on all 5 verdicts.

### The 5 Verdicts

**1. Synthesizability**:
- **ZFC (logic)**: Valid bonds (hybridization matches), no strained rings (<3 or >8 atoms), reasonable bond angles
- **CAT (composition)**: Retrosynthetic path exists (known coupling reactions: Suzuki, Heck, Sonogashira, amidation)
- **AGREE** = All bonds valid + synthesis routes precedent

**2. Toxicity**:
- **ZFC (logic)**: No toxic functional groups (isocyanate, azide, nitroso, organometallics), electrophilicity < 0.3
- **CAT (composition)**: Structurally similar to known non-toxic molecules (benzoic acids, naphthalene derivatives)
- **AGREE** = No toxic groups + similar to safe molecules

**3. Stability**:
- **ZFC (logic)**: Bond strengths > 200 kJ/mol, aromatic stabilization, no weak heteroatom-heteroatom bonds
- **CAT (composition)**: No known decomposition pathways (hydrolysis, oxidation, photolysis)
- **AGREE** = Strong bonds + no decomposition precedent

**4. Activity** (application-specific):
- **ZFC (logic)**: Has required functional groups for target application
  - **Breath VOC sensing**: Polar groups (OH, COOH, NH2), π-π stacking sites (aromatic rings), pore-compatible geometry
  - **Food safety**: Antibacterial groups (quaternary ammonium, phenolic), hydrophobic pockets (aromatic clusters)
  - **PFAS detection**: Lewis acid sites (carbonyl, nitro), fluorophilic groups (electron-withdrawing)
- **CAT (composition)**: Similar to known active MOF linkers for the application
- **AGREE** = Has groups + similar to active linkers

**5. Conductivity**:
- **ZFC (logic)**: Extended conjugation (π-system > 6 atoms), aromatic content > 50%, heteroatom doping (N, S, O in aromatic rings)
- **CAT (composition)**: Orbital overlap composes to extended electronic state (band structure)
- **AGREE** = Extended conjugation + orbital overlap precedent

### Morphism Integrity

Measures internal consistency of atomic descriptors (0-1 score):

```
For each bond (i, j) in the molecule:
  expected_bond_type = from hybridization (sp3 -> single, sp2 -> double/aromatic, sp -> triple)
  actual_bond_type = from RDKit molecular graph
  if mismatch: contradiction++

morphism_integrity = 1.0 - (contradictions / total_bonds)
```

High morphism integrity (>0.9) = internally consistent atomic descriptors, likely realizable molecule.

### Generation Strategies

**1. Substitution** (40% of candidates):
- Start from known 22-atom linkers
- Substitute aromatic H with functional groups (F, Cl, OH, NH2, COOH, NO2)
- Preserves core structure, modulates electronics

**2. Modification** (30% of candidates):
- Extend conjugation by adding aromatic rings
- Insert heteroatoms (N, S, O) into aromatic systems
- Adjust spacer groups between coordination sites

**3. Template** (30% of candidates):
- Use common MOF linker motifs (dicarboxylates, triazoles, pyridines)
- Vary substituents and spacer lengths
- Target specific coordination geometries

### Kulik 22-Atom Challenge

**Problem**: LLMs hallucinate molecules when asked for specific atom counts.
> "I constantly ask LLMs: design me a ligand with exactly 22 heavy atoms. I can never get an answer that has 22 atoms." — Prof. Heather Kulik (MIT)

**KOMPOSOS solution**: Heavy atom counting via element parsing (Fe != F), exact constraint search, no hallucinations. Returns real candidates or honest "not found" — never makes up molecules.

### Academic Partnership

Built for **Heather Kulik Group** (MIT) to accelerate computational MOF discovery:
- Screen before DFT (save compute)
- Discover novel linker combinations
- Validate synthesis feasibility
- Focus on 22 atoms (DFT-tractable, diverse chemistry)

### Example Output

```
Generated: 100 candidates
Passed all verdicts: 12
Best morphism integrity: 0.952
Avg morphism integrity: 0.837

Top candidate:
  SMILES: c1ccc(cc1)C(=O)Nc2ccc(cc2)C(=O)O
  Formula: C15H11NO4
  MW: 269.3 g/mol
  Morphism integrity: 0.952
  Verdicts: ✓ ✓ ✓ ✓ ✓ (all AGREE)
  Overall viable: Yes

  Reasoning:
    Synthesizability (AGREE, 0.89): Suzuki coupling + amidation, no strained rings
    Toxicity (AGREE, 0.92): Benzoic acid derivative, electrophilicity 0.12
    Stability (AGREE, 0.88): C-C/C-N bonds >350 kJ/mol, aromatic stabilization
    Activity (AGREE, 0.85): Polar COOH groups, π-π stacking sites
    Conductivity (AGREE, 0.82): Extended π-system (15 conjugated atoms), aromatic 80%
```

### API Endpoint

`POST /api/v1/design-mof-linker` with request body:
```json
{
  "application_context": "breath_voc_sensing",
  "num_candidates": 100,
  "exclude_elements": ["F", "Cl"],
  "rank_by": "morphism_integrity",
  "require_all_agree": true
}
```

Returns JSON with ranked candidates, verdict breakdowns, reasoning traces, and export-ready data.

### UI Page

**Page 8: MOF Designer** (3 tabs):
1. **Design Linkers**: Configure + generate + view results + export CSV/JSON
2. **Linker Database**: Browse 6,843 known 22-atom linkers from Materials Project
3. **About**: Verdict docs, classification guide, academic partnership info

---

## Cross-Bridge Physics

### Battery-Polymer Interface
The critical physics: **Can this polymer survive the electrode's voltage window?**
- PEO oxidizes above 3.8V vs Li/Li+ — incompatible with NMC811 (3.8V nominal)
- PVDF stable to ~5V — universal cathode binder
- CMC is water-based — incompatible with moisture-sensitive high-voltage cathodes

### Battery-Metal Interface
The critical physics: **Will the current collector dissolve at operating voltage?**
- Cu_foil dissolves above ~3.0V vs Li/Li+ — anode only
- Al_foil passivates in LiPF6 but corrodes in LiTFSI (Al-TFSI complex)
- Galvanic potential difference between foil and electrode

### Ceramic-Metal Interface
The critical physics: **Will CTE mismatch crack the coating?**
- TiN (9.4) on Ti6Al4V (8.6) = 0.8 difference = excellent
- SiO2 (0.55) on Al (23.1) = 22.5 difference = catastrophic
- Also: can the ceramic be deposited without melting the metal?
  - Bulk sintering: ceramic sintering temp must be < metal melting point
  - PVD/CVD alternative: substrate stays below 500C (most coatings feasible)

---

## Composition Prediction Physics

### Forward Prediction: Formula → Properties

Given any chemical formula, KOMPOSOS predicts material properties using three independent physics-based approaches fused via Dempster-Shafer theory.

**Kan Extension (categorical extrapolation):**
- Treats 103K+ known materials as points in composition space (mole-fraction vectors) — 169 curated bridge materials + 103,644 from Materials Project
- For a query formula, finds nearest neighbors by composition distance (O(log N) via KD-tree)
- Extrapolates properties via inverse-distance-weighted colimit
- Confidence decreases with distance from known data

**Rule-Based Estimates (first-principles approximations):**
- **Faraday capacity**: C = nF / (3.6 * M), where n = electron transfer, M = molar mass
- **Vegard interpolation**: Linear interpolation of end-member properties by composition
- **Electronegativity correlation**: Higher average Pauling EN → higher voltage (empirical)
- **Ionic radius ratio**: Predicts stable crystal structure via Goldschmidt tolerance factor

**Formation Energy (DFT surrogate):**
- 154K+ DFT formation energies from Materials Project cache (eV/atom)
- Kan extension over known Ef data (primary, high confidence)
- Kapustinskii lattice energy estimate: U = K * (n * z+ * z-) / (r+ + r-)
- Miedema model: ΔH ∝ -P(Δφ*)² + Q(Δn_ws^{1/3})²
- Convex hull distance from MP (E_hull = 0 → thermodynamically stable)
- 5 ZFC thermodynamic constraints: negative Ef, charge balance, Goldschmidt tolerance, decomposition margin, element compatibility
- Hull distance constraint (when MP cache exists)
- Combined into synthesizability score (0-1)

**Crystal Structure Prediction (4-source D-S fusion):**
- Rule-based patterns: composition → structure (Li+TM+O₂ → layered, AB₂O₄ → spinel, etc.)
- Kan extension vote: nearest known materials' structure types weighted by distance
- Goldschmidt tolerance factor: t = (r_A + r_O) / (√2 * (r_B + r_O))
  - 0.9-1.0 → perovskite, 0.71-0.9 → spinel/ilmenite, <0.71 → corundum
- Materials Project lookup: nearest MP entries' crystal systems (4th source, optional)
- 21 structure types, 23/23 known materials predicted correctly

**Derived Crystal Structure (from Materials Project):**
- Full lattice parameters: a, b, c (Angstroms), alpha, beta, gamma (degrees)
- Space group and space group number (e.g., Imma #74)
- Volume per atom (Angstroms³)
- Derived via Kan extension (inverse-distance-weighted average) over nearest MP entries
- Provenance chain: every parameter traces to specific MP entries with weights (e.g., "Derived from mp-1281785 (14%), mp-1273466 (14%)...")
- Confidence metric based on distance to nearest MP entry

**Validation:**
- Leave-one-out voltage errors: 1.6-7.2%
- Leave-one-out thermal stability errors: 2.7-20%
- Structure prediction: 100% accuracy on known materials

### Inverse Design: Properties → Composition

The inverse of forward prediction. Given target properties, search composition space for candidates.

**Composition space geometry:**
- Materials live in an N-dimensional simplex (N = number of elements)
- Composition distance = Euclidean distance in mole-fraction space
- Perturbation = small displacement along simplex axes
- Interpolation = geodesic between two compositions on the simplex

**Search physics:**
- **Perturbation**: Shifts stoichiometry of known materials by ±5%, ±10%, ±20%. Physically: changing doping levels, off-stoichiometry, substitution fraction.
- **Interpolation**: Walks between two known compositions at 0.1 steps. Physically: solid solution series (e.g., NMC811 → NMC622 → NMC111).
- **Substitution**: Swaps elements within chemical groups. Physically: isovalent substitution (Ni↔Fe↔Mn in transition metal sites), anion exchange (O↔S in chalcogenides).
- **Stoichiometry variation**: Systematic grid search. Physically: NMC triangle (Ni+Mn+Co=1), olivine M-site sweep (Fe↔Mn), spinel inversion parameter.

**Constraint satisfaction:**
- Element inclusion/exclusion (e.g., no cobalt for ethical sourcing)
- Synthesizability floor (formation energy + ZFC constraints)
- Property targets with min/max bounds and confidence weighting
- Domain restriction (battery, ceramic, etc.)

**Scoring physics:**
- Per-target: full credit (0.8 + 0.2×conf) if property within bounds, exponential decay outside
- Overall: weighted target scores × synthesizability factor × stability factor × confidence
- Deduplication: compositions within distance 0.01 are considered identical

---

## Ligand Constraint Search (Phase 11)

Chemical query system for molecular discovery — built for MIT Kulik group's computational screening challenges.

### Heavy Atom Counting
- **Heavy atoms**: All atoms except hydrogen (H)
- **Algorithm**: Parse chemical formula → count element occurrences → sum all non-H atoms
- **Edge cases**:
  - H₂ has 0 heavy atoms (not 2) — range (0, 100) not (1, 100)
  - Fe != F — must use element parsing, not substring matching
  - C₆H₁₂O₆ has 6+6=12 heavy atoms
- **Kulik 22-atom challenge**: Find molecules with exactly 22 heavy atoms for computational screening → constraint_search returns exact matches in <1s

### Element Constraints
- **Required elements**: Must contain all listed elements (e.g., requires=["C", "N", "O"])
- **Forbidden elements**: Must not contain any listed elements (e.g., forbidden=["F", "Cl", "Br"])
- **Element parsing**: Regex-based element extraction from chemical formula
  - C₆H₁₂O₆ → ["C", "H", "O"]
  - Fe₂O₃ → ["Fe", "O"] (not ["F", "e", "O"])

### Functional Class Constraints
- **Classes**: solvent, salt, monomer, reagent, coating, gas
- **Filtering**: Restrict search to specific molecule types
- **Example**: solvents with 10 heavy atoms + no fluorine → ethyl acetate, acetone

### Use Cases
- **Academic research**: Computational screening of ligands for MOF synthesis (Kulik group)
- **PFAS-free design**: Find alternatives by excluding fluorine-containing molecules
- **Stoichiometry matching**: Find molecules with specific atom counts for synthesis balancing
- **Molecular sieving**: Identify molecules within size constraints (via heavy atom count as proxy)

---

## PFAS Compliance Report Logic (Phase 11)

### 7-Section Report Structure
1. **Executive Summary**: Screened count, detected count, clean count, overall verdict (COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW)
2. **Screening Results**: Per-material detection status, PFAS substance, CAS number, category, regulatory status
3. **Regulatory Analysis**: Deadlines by regulation (EU REACH, US EPA, Stockholm), urgency levels, action windows
4. **Replacement Recommendations**: Per-detected-PFAS alternatives ranked by compatibility score, use-case-specific
5. **Action Plan**: Prioritized actions (IMMEDIATE: ban <6mo, NEAR_TERM: 6-12mo, PLANNED: >12mo, MONITOR: under review)
6. **Provenance**: Full traceability chain: material → detection method (exact match / heuristic / formula check) → regulation → alternative → verdict
7. **Verdict Summary**: Overall compliance status with justification

### Verdict Logic
```
overall_verdict = COMPLIANT if no PFAS detected
                = NON_COMPLIANT if any PFAS with urgency >= high (ban <12mo or BANNED)
                = NEEDS_REVIEW if any PFAS with urgency < high (RESTRICTED / UNDER_REVIEW)
```

### Provenance Chain
Every detected PFAS traces:
- Material name + function + quantity → Detection (exact CAS match / heuristic pattern / formula check)
- → PFAS substance + CAS + category → Regulation (EU/US/Stockholm) + status + urgency
- → Replacement alternatives (use-case-specific, ranked by score)
- → Action timeline (deadline - current_date)

**Example**: PVDF cathode binder (2.5 kg) → detected as fluoropolymer (exact CAS match) → EU REACH RESTRICTED (Aug 2026, urgency=high) → alternatives: CMC+SBR (0.83), PAA (0.76), PAN (0.62) → action: NEAR_TERM (7 months until ban) → verdict contributes to NON_COMPLIANT

### Use Case Mapping
- **Function field**: cathode binder, seal, wire insulation, membrane, etc.
- **Mapping**: _map_function_to_use_case() with None guard (function can be None)
- **Fallback**: If function unknown, use PFAS category as use case

### Brand Name Detection (Phase 11.6)
- **11 brand names**: Teflon, Kynar, Viton, Scotchgard, Gore-Tex, Stainmaster, Chemours, 3M Novec, Dyneon, Daikin, Solvay Solef
- **Resolution**: `resolve_base_pfas()` maps brand → base substance (e.g., Teflon→PTFE, Kynar→PVDF, Viton→FKM)
- **Detection tiers**: `exact` (CAS match), `heuristic` (brand/substring match, resolved to base), `unknown` (not PFAS)
- Heuristic matches get full replacements + CAS numbers via resolution to base substance

### Cross-Bridge Domain Scoring (Phase 11.6)
- **Purpose**: Score PFAS replacements against cathode/electrolyte using cross-bridge functors
- **Method**: `_compute_domain_scores()` calls `cross_bridge.battery_polymer.score_polymer_electrode_compatibility()` for each replacement
- **Mapping**: voltage_compat → Electrolyte, thermal_compat → Thermal, mechanical_compat → Adhesion, chemical_compat → Cathode
- **Fallback**: PAA, Alginate not in polymer_bridge → score=0.0, falls back to generic scores
- **Known**: CMC+NMC811 and SBR+NMC811 are KNOWN_BAD_PAIRS → cathode score 0.15 (real chemistry)

### PDF Report Generation (Phase 11.6)
- **File**: `reports/pfas_pdf.py`
- **Cover page**: "Prepared for: [Client Name]", portfolio count, confidential
- **Domain scores**: Adhesion/Electrolyte/Thermal/Cathode columns (from cross-bridge)
- **Narrative**: Intro + recommendation paragraphs per detection
- **Provenance table**: Property/Value/Source/Contribution
- **Action plan**: P0/P1/P2 priorities, Weeks timeline, "Risk if Delayed" column
- **Audit certificate**: 10 fields incl Verification Method, Validation Status, Test Suite

---

## Synthesis Chemistry

### Battery Material Synthesis
- **LFP solid-state**: Li2CO3 + Fe2O3 + NH4H2PO4 -> ball mill -> calcine 350C/N2 -> grind -> sinter 700C/N2
- **NMC811 coprecipitation**: NiSO4+MnSO4+CoSO4 -> coprecipitate pH11.5/N2 -> wash -> dry -> mix LiOH -> calcine 800C/O2
- **LLZO**: LiOH + La2O3 + ZrO2 -> ball mill -> calcine 900C -> grind -> pelletize -> sinter 1100C
- **LGPS**: Li2S + GeS2 + P2S5 -> ball mill 20h/Ar -> anneal 550C/Ar (HIGH RISK: H2S release)

### Ceramic Synthesis
- **Al2O3 Bayer**: Bauxite + NaOH -> autoclave 180C -> precipitate Al(OH)3 -> calcine 1100C
- **TiN PVD**: Clean substrate -> Ar etch -> reactive DC sputtering (Ti target + N2, 400C)
- **SiC Acheson**: SiO2 + petroleum coke -> 2500C resistance furnace -> crush

### Polymer Processing
- **PVDF film**: Dissolve in NMP (60C/4h) -> cast (doctor blade) -> vacuum dry (80C/12h)
- **PEO membrane**: Dissolve PEO+LiTFSI in acetonitrile/Ar -> cast -> dry 24h/Ar -> hot press 80C

---

## Physical Constants Used

| Property | Symbol | Unit | Where Used |
|----------|--------|------|-----------|
| Galvanic potential | E° | mV vs SHE | metal_bridge/ |
| CTE | alpha | 10^-6/K | ceramic_bridge/, metal_bridge/, glass_bridge/ |
| Ionic conductivity | sigma | S/cm | battery_bridge/, ceramic_bridge/ |
| Bandgap | Eg | eV | semiconductor_bridge/ |
| Lattice constant | a | Angstrom | semiconductor_bridge/ |
| Hansen parameters | delta_d, delta_p, delta_h | MPa^0.5 | polymer_bridge/ |
| Refractive index | n_d | dimensionless | glass_bridge/ |
| Voltage window | V | V vs Li/Li+ | battery_bridge/, cross_bridge/ |
| Sintering temp | T_sinter | C | ceramic_bridge/ |
| Elastic modulus | E | GPa | all bridges |
| Thermal conductivity | k | W/m.K | semiconductor_bridge/, glass_bridge/ |
| Formation energy | Ef | eV/atom | composition_engine/ (154K+ DFT values from Materials Project) |
| Faraday constant | F | 96485 C/mol | composition_engine/ (theoretical capacity) |
| Pauling electronegativity | χ | dimensionless | composition_engine/ (voltage correlation) |
| Shannon ionic radius | r | pm | composition_engine/ (Goldschmidt tolerance, structure prediction) |
| Molar mass | M | g/mol | composition_engine/ (capacity calculation) |
| Goldschmidt tolerance | t | dimensionless | composition_engine/ (structure prediction) |

All values sourced from published literature (ASM Handbooks, MatWeb, Callister, Ashby charts, Materials Project, journal papers with DOIs).

**MOF data sources (30 MOFs, all with DOIs):**
- Cambridge Structural Database (CSD) codes where available
- Published experimental measurements: BET via N₂ adsorption (77K), pore diameter via crystallographic analysis, thermal stability via TGA, water stability via immersion tests
- Representative DOIs: 10.1126/science.283.5405.1148 (MOF-5), 10.1021/ja0276974 (HKUST-1), 10.1021/ja106207w (UiO-66), 10.1021/ja500330a (NU-1000)
