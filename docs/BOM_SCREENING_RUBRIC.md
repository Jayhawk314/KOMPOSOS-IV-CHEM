# PFAS Compliance BOM Screening Rubric

**For: James (KOMPOSOS Compliance Services)**
**Version: 1.0 | 2026-04-02**

A step-by-step professional rubric for delivering PFAS compliance screenings to clients.

---

## Industry Standards: Where KOMPOSOS Fits

### The Compliance Ecosystem (What Exists)

There are 3 layers to PFAS compliance. You need to know where your service sits.

| Layer | What It Is | Standards | Who Does It |
|-------|-----------|-----------|-------------|
| **1. Material Declaration** | Documenting what's IN a product | IPC-1752A, IEC 62474, SCIP | Suppliers & manufacturers |
| **2. Substance Screening** | Identifying PFAS in a BOM | ECHA REACH Candidate List, IEC 62474 DSL | Compliance software (you) |
| **3. Analytical Testing** | Lab-testing for PFAS presence | EPA 533, EPA 537.1, TOP Assay, TOF | Certified laboratories |

**KOMPOSOS operates at Layer 2** -- computational substance screening with replacement analysis. It does NOT replace Layer 1 (supplier declarations) or Layer 3 (lab testing). It sits between them: faster than lab testing, smarter than simple list-matching.

### Key Standards You Should Know

#### IPC-1752A (Material Declaration Management)
- **What**: Industry standard for exchanging material composition data between supply chain participants
- **4 disclosure levels**: Class A (simple compliance statement) -> Class D (Full Material Disclosure to 100 ppm)
- **Why it matters to you**: When a client sends you their BOM, they're giving you Class B-C level data. Your report helps them move toward Class D disclosure for PFAS specifically.
- **Updated**: February 2026 (Appendices B-F revised)
- **Your positioning**: "Our screening accepts your existing BOM data (IPC-1752A Class B/C level) and produces PFAS-specific analysis that supports your Class D Full Material Disclosure requirements."

#### IEC 62474 (Material Declaration for Electronics)
- **What**: International standard for material declarations in electronics, maintained by IEC
- **Declarable Substance List (DSL)**: Includes a PFAS group entry derived from US state legislation (629 reference substances)
- **Why it matters**: If your client is in electronics, they already use IEC 62474 for RoHS/REACH. PFAS is now on their DSL.
- **Your positioning**: "Our PFAS registry covers the 35 most commercially relevant PFAS substances, including all IEC 62474 declarable fluoropolymers, with application-specific replacement scoring that the standard doesn't provide."

#### ECHA SCIP Database (EU)
- **What**: EU database where companies must report articles containing REACH Candidate List substances (SVHC) above 0.1% w/w
- **253 substances** on the Candidate List as of February 2026
- **Why it matters**: Several PFAS are SVHCs. If your client sells into the EU, they must report to SCIP.
- **Your positioning**: "Our screening identifies which materials in your BOM trigger SCIP reporting obligations and provides the substance data needed for your SCIP notification."

#### EU REACH PFAS Restriction (In Progress)
- **What**: Proposed EU-wide restriction on ~10,000 PFAS substances -- the broadest chemical ban in EU history
- **Status**: ECHA Risk Assessment Committee (RAC) adopted opinion March 2026. Public consultation on draft opinion spring 2026. Final restriction expected late 2026 or early 2027.
- **Sector-specific derogations**: Some uses (medical devices, semiconductors) may get temporary exemptions
- **Your positioning**: "We track the evolving EU REACH PFAS restriction timeline and flag which of your materials fall under proposed derogations vs. immediate phase-out requirements."

#### US EPA PFAS Rules
- **TSCA**: EPA using Toxic Substances Control Act authority to regulate PFAS manufacturing and use
- **Drinking water**: EPA Methods 533 and 537.1 for detecting 29 PFAS in water (this is LAB testing, not BOM screening)
- **Your positioning**: "For US-market products, we screen against current EPA TSCA actions and flag substances likely to face future restrictions based on the regulatory trajectory."

#### Stockholm Convention (Global)
- **What**: International treaty eliminating persistent organic pollutants (POPs)
- **PFOS**: Listed since 2009. PFOA: Listed since 2019.
- **Why it matters**: Applies globally to 186 signatory countries
- **Your positioning**: "Our screening covers Stockholm Convention listed PFAS, which applies to any product sold internationally."

### What KOMPOSOS Does That Standards Don't

| Standard Method | What It Tells You | What It Doesn't Tell You |
|----------------|-------------------|--------------------------|
| IPC-1752A / IEC 62474 | "This product contains PVDF" | Nothing about what to use instead |
| ECHA REACH Candidate List | "PVDF is under review" | Nothing about urgency or timeline |
| EPA 533/537.1 lab test | "This sample contains 4.2 ppb PFOS" | Nothing about replacement materials |
| BOMcheck / Assent screening | "PVDF is flagged for PFAS" | Nothing about application-specific alternatives |

**KOMPOSOS adds:**
- Application-context replacement scoring (battery binder vs. gasket vs. membrane)
- Cross-domain compatibility analysis (does the replacement work with your cathode?)
- Urgency quantification with days-to-deadline
- Prioritized action plan with risk-if-delayed
- Full provenance chain (every score traceable to published data)

**No existing compliance platform does application-specific replacement scoring.** Certivo, Assent, GreenSoft, and Source Intelligence all flag PFAS but cannot answer "what replaces PVDF specifically in my battery binder application, and will it work with NMC811?" That's your differentiator.

### Compliance Workflow: Where You Fit in the Client's Process

```
CLIENT'S FULL COMPLIANCE WORKFLOW:

1. Supplier Data Collection (IPC-1752A declarations)
   Client collects BOMs from their supply chain
                    |
                    v
2. >>> KOMPOSOS SCREENING (YOU ARE HERE) <<<
   - Identify PFAS substances in BOM
   - Score application-specific replacements
   - Generate auditable compliance report
   - Provide regulatory timeline + action plan
                    |
                    v
3. Replacement Qualification
   Client pilot-tests top-scored replacements
   (You can support this -- $5K-15K engagement)
                    |
                    v
4. Analytical Verification (if required)
   Lab testing via EPA 533/537.1 or TOF/TOP assay
   (Not your service -- refer to certified labs)
                    |
                    v
5. Regulatory Submission
   Client updates SCIP database, IEC 62474 declarations
   (Not your service -- client's regulatory team)
                    |
                    v
6. Ongoing Monitoring
   Re-screen quarterly as regulations evolve
   (Your recurring revenue -- $1K-2.5K/quarter)
```

### How to Talk About Standards With Clients

**If they ask "Do you follow IPC-1752A?"**
> "We accept BOM data at any IPC-1752A disclosure level and produce PFAS-specific analysis that supports your Full Material Disclosure (Class D) requirements. Our report format is designed to complement your existing material declaration workflow, not replace it."

**If they ask "Is this REACH compliant?"**
> "Our screening covers all PFAS substances on the REACH Candidate List (SVHC) and the proposed EU-wide PFAS restriction. The report identifies which materials trigger SCIP reporting obligations and provides the substance data needed for your notifications."

**If they ask "Do we still need lab testing?"**
> "Computational screening identifies PFAS based on known material composition. For definitive presence/absence confirmation, analytical testing (EPA 533/537.1 or Total Organic Fluorine) may be required depending on your regulatory obligation. Our screening tells you WHERE to focus expensive lab testing, saving you from testing every material."

**If they ask "What about sector derogations?"**
> "The proposed EU PFAS restriction includes time-limited derogations for specific sectors including semiconductors, medical devices, and certain industrial applications. Our report flags which of your materials may qualify for derogations vs. which face immediate phase-out, so you can prioritize your transition efforts."

---

## Phase 1: Client Intake (30 min)

### 1.1 What to Ask the Client

| Question | Why You Need It | Example Answer |
|----------|----------------|----------------|
| "Can you send your bill of materials as a spreadsheet?" | You need material names | Excel/CSV with 10-500 rows |
| "What is each material's function in your product?" | Scoring changes by application | "PVDF is our cathode binder" |
| "Do you have approximate quantities (kg per unit)?" | Helps prioritize the action plan | "2.5 kg PVDF per battery pack" |
| "Do you have CAS numbers for any materials?" | Increases detection accuracy | "CAS 24937-79-9 for PVDF" |
| "What product/industry is this for?" | Determines which regulations apply | "Li-ion battery cells for EU market" |
| "What is your compliance deadline?" | Frames the urgency | "We need to qualify by Q4 2026" |
| "Company name for the report header?" | Branding the deliverable | "Acme Battery Corp" |

### 1.2 What You'll Receive (Typical)

Clients usually send one of these:
- **Best case**: Excel with columns for Material, Function, Quantity, CAS
- **Common case**: PDF or Word list of material names (no quantities, no functions)
- **Worst case**: "Here's our 200-page spec sheet, materials are somewhere in there"

**Your job**: Turn whatever they send into this format:

```
Material Name | Function | Quantity (kg)
PVDF | cathode binder | 2.5
PTFE | gasket seal | 0.5
NMC811 | cathode active material | 45.0
Cu foil | current collector | 12.0
```

---

## Phase 2: BOM Preparation (30-60 min)

### 2.1 Format Each Material Entry

Each line needs at minimum a **name**. Function and quantity are optional but improve the report quality significantly.

| Field | Required? | Format | Notes |
|-------|-----------|--------|-------|
| **Name** | YES | Plain text | Exactly as the client calls it |
| **Function** | Recommended | Plain text | What it does in their product |
| **Quantity (kg)** | Optional | Number | Per unit or per batch |
| **CAS Number** | Optional | XXX-XX-X format | If client provides it |

### 2.2 Name Normalization Checklist

The system recognizes the current internal material-pair benchmark (6 domains) + 35 PFAS + brand names. Before running:

- [ ] Trim whitespace and fix obvious typos
- [ ] Commercial brands are auto-detected (Kynar -> PVDF, Teflon -> PTFE, Viton -> FKM)
- [ ] If the client uses internal codes ("Binder A"), ask what the actual material is
- [ ] Abbreviations work: PVDF, PTFE, NMC811, LFP, PEEK, EPDM
- [ ] Full names also work: "polyvinylidene fluoride" may need to be entered as "PVDF"
- [ ] Mixtures: enter each component separately (e.g., "EC/DMC 1:1" -> two entries: "EC" and "DMC")

### 2.3 Function Mapping Guide

The system auto-maps function text to scoring categories. Use these keywords for best results:

| Write This | System Maps To | Scoring Focus |
|-----------|---------------|---------------|
| "cathode binder" or "anode binder" | Battery Binder | Adhesion, electrolyte stability, thermal |
| "gasket" or "seal" or "O-ring" | Seal/Gasket | Chemical resistance, compression set |
| "separator" or "membrane" | Membrane | Ion permeability, thermal shutdown |
| "wire insulation" or "cable jacket" | Wire Insulation | Dielectric, flame retardancy |
| "coating" or "non-stick" | Non-Stick Coating | Release properties, wear resistance |
| "tank liner" or "chemical container" | Chemical-Resistant Liner | Acid/base resistance |
| "cathode" or "anode" or "electrolyte" | General (not PFAS-relevant) | Standard scoring |
| Anything else / blank | General | Generic performance matching |

### 2.4 Quality Checks Before Running

- [ ] Every material has a name (no blank rows)
- [ ] No duplicate entries (combine quantities instead)
- [ ] Functions are filled in for PFAS-suspect materials (PVDF, PTFE, FEP, Nafion, ETFE)
- [ ] Quantities use consistent units (all kg, or all grams -- convert to kg)
- [ ] Client name is confirmed for report branding
- [ ] You know which jurisdictions matter (EU? US? Both?)

---

## Phase 3: Running the Screening (5-15 min)

### 3.1 Option A: Streamlit Web UI (Recommended for Clients)

1. Go to https://komposos-chem.onrender.com (or your deployed URL)
2. Navigate to **PFAS Scanner** > **Compliance Report** tab
3. Enter client name
4. Select "Custom materials list"
5. Paste BOM in pipe-delimited format:
   ```
   PVDF | cathode binder | 2.5
   PTFE | gasket seal | 0.5
   NMC811 | cathode | 45.0
   ```
6. Click **Generate Compliance Report**
7. Click **Download PDF Report**

### 3.2 Option B: API (For Programmatic Use)

```bash
curl -X POST https://your-api-url/api/v1/pfas-report \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "materials": [
      {"name": "PVDF", "function": "cathode binder", "quantity_kg": 2.5},
      {"name": "PTFE", "function": "gasket seal", "quantity_kg": 0.5}
    ],
    "client_name": "Acme Battery Corp"
  }'
```

### 3.3 Option C: Python Script (For Large BOMs)

```python
from reports.pfas_report import PFASComplianceReport, MaterialInput
from reports.pfas_pdf import generate_pfas_pdf

# Build BOM from client spreadsheet
bom = [
    MaterialInput(name="PVDF", function="cathode binder", quantity_kg=2.5),
    MaterialInput(name="PTFE", function="gasket seal", quantity_kg=0.5),
    MaterialInput(name="NMC811", function="cathode", quantity_kg=45.0),
    # ... add all materials
]

gen = PFASComplianceReport()
report = gen.screen_portfolio(bom, client_name="Acme Battery Corp")
pdf = generate_pfas_pdf(report)

with open(f"{report.report_id}.pdf", "wb") as f:
    f.write(pdf)

print(f"Report {report.report_id}: {report.summary}")
```

---

## Phase 4: Interpreting Results (15-30 min)

### 4.1 Risk Level Guide

| Risk Level | Meaning | Client Impact |
|------------|---------|---------------|
| **CLEAN** | Zero PFAS detected | No action needed. Compliance verified. |
| **LOW** | PFAS found but only "under review" status | Monitor regulatory developments. No immediate action. |
| **MODERATE** | PFAS found with "restricted" or "proposed ban" status | Begin replacement qualification within 6-12 months. |
| **HIGH** | PFAS found with ban effective within 12 months | Urgent replacement needed. Timeline is tight. |
| **CRITICAL** | PFAS found that is already BANNED | Immediate action. Product may already be non-compliant. |

### 4.2 Detection Tier Guide

| Tier | What It Means | Your Action |
|------|--------------|-------------|
| **Exact** | Material is in the PFAS registry by name or CAS | High confidence. Report as-is. |
| **Heuristic** | Detected via brand name (Kynar, Teflon, etc.) | Confirm with client: "Is your Kynar product PVDF-based?" |
| **Unknown** | Material not recognized by the system | Flag for manual review. Research the material yourself or ask client for SDS (Safety Data Sheet). |

### 4.3 Replacement Verdict Guide

| Verdict | Score Range | What to Tell the Client |
|---------|-----------|------------------------|
| **VALIDATED** | 0.70 - 1.00 | "This replacement is supported by published data and cross-domain compatibility analysis. Recommended for pilot testing." |
| **CAUTION** | 0.40 - 0.69 | "This replacement shows promise but has limitations in one or more scoring dimensions. Requires additional qualification testing." |
| **VETOED** | 0.00 - 0.39 | "This replacement does not meet minimum compatibility thresholds for your application. Not recommended." |

### 4.4 What to Review Before Sending

- [ ] Every "Unknown" material is investigated (check SDS, ask client)
- [ ] Heuristic detections are confirmed with client
- [ ] Top replacement for each PFAS detection makes sense for the application
- [ ] Action plan deadlines align with client's stated compliance deadline
- [ ] Regulatory timeline shows correct jurisdictions for client's market
- [ ] Client name is correct on the report
- [ ] Report ID is noted for your records

---

## Phase 5: Delivering the Report (15 min)

### 5.1 What You Deliver

| Deliverable | Format | Contents |
|------------|--------|----------|
| **Primary**: Compliance Report | PDF | 7-section auditable report with detections, replacements, action plan |
| **Optional**: Raw Data | JSON | Machine-readable full results (for technical clients) |
| **Optional**: Summary Email | Text | 3-paragraph executive summary with key findings |

### 5.2 Summary Email Template

```
Subject: PFAS Compliance Screening Results - [Client Name] [Product]

Hi [Name],

I've completed the PFAS compliance screening of your [N]-material bill
of materials for [product]. Here are the key findings:

SUMMARY: [N_detected] of [N_total] materials contain PFAS substances.
Overall risk level: [RISK_LEVEL].

KEY FINDINGS:
- [Material 1] ([function]): PFAS detected ([urgency]).
  Top replacement: [replacement] (score: [score], verdict: VALIDATED).
- [Material 2] ([function]): PFAS detected ([urgency]).
  Top replacement: [replacement] (score: [score], verdict: VALIDATED).

TIMELINE: The EU PFAS restriction takes effect [date] ([N] days).
The US EPA rule takes effect [date] ([N] days).

The full compliance report is attached (PDF). It includes scored
replacement alternatives, regulatory timeline, and a prioritized
action plan.

Happy to walk through the findings on a call if useful.

Best,
James
KOMPOSOS Compliance Services
```

### 5.3 Pricing Guide

| Service | Scope | Price Range |
|---------|-------|-------------|
| **Single BOM Screening** | 1 product, up to 50 materials | $2,500 - $3,500 |
| **Multi-Product Portfolio** | 3-10 products, up to 200 materials total | $5,000 - $10,000 |
| **Ongoing Monitoring** | Quarterly re-screening + regulatory updates | $1,000 - $2,500/quarter |
| **Replacement Qualification Support** | Help pilot-test top replacements | $5,000 - $15,000 (project) |

### 5.4 What to Say If They Ask Hard Questions

| Question | Your Answer |
|----------|------------|
| "Is this a legal opinion?" | "No. This is a technical screening and compatibility assessment. For legal compliance advice, consult your regulatory counsel. This report gives them the technical evidence they need." |
| "How accurate are the replacement scores?" | "Replacement scores are based on published material property data, cross-domain compatibility analysis, and 1,575 validated test cases. However, scores indicate compatibility potential -- any replacement should be pilot-tested in your specific application before production use." |
| "Can you guarantee compliance?" | "No tool can guarantee compliance because regulations change and material specifications vary. What this report does is identify PFAS exposure, quantify urgency, and provide evidence-based replacement candidates ranked by your specific application context." |
| "Why should I trust a computational tool?" | "Every score in this report has a provenance chain -- you can trace each number back to published property data, CAS numbers, and peer-reviewed sources. The system runs 1,575 automated validation tests on every build. It's not a black box." |
| "What if a material shows as Unknown?" | "Unknown means the material isn't in our curated database. I'll research it using the Safety Data Sheet (SDS) and add it to the analysis. This typically adds 30-60 minutes to the engagement." |

---

## Phase 6: Post-Delivery (Ongoing)

### 6.1 Follow-Up Actions

- [ ] Send invoice (Net 30 terms)
- [ ] File report copy in your records (report ID: PFAS-YYYY-MMDD-NNNN)
- [ ] Note any "Unknown" materials that need database expansion
- [ ] Schedule follow-up in 90 days for regulatory updates
- [ ] Ask for referral: "Do you know anyone else who might need this?"

### 6.2 Database Expansion Log

When a client has materials not in the system, track them here for future addition:

| Material | Client | Function | SDS Available? | Added to System? |
|----------|--------|----------|---------------|-----------------|
| _____    | _____  | _____    | Y/N           | Y/N             |

**Adding a new material takes 30-60 minutes** if published property data exists (melting point, density, relevant domain properties, citations).

---

## Quick Reference: System Capacity

| Category | Current Count | What It Covers |
|----------|--------------|----------------|
| **Base Materials** | 205 | Battery, polymer, metal, ceramic, semiconductor, glass (curated, cited) |
| **Molecules** | 37 | Solvents, salts, monomers, coatings, gases (PubChem-linked) |
| **PFAS Registry** | 35 | All major PFAS categories with CAS numbers and regulations |
| **MOFs** | 30 | Metal-organic frameworks with DOIs |
| **Brand Names Auto-Detected** | 11 | Teflon, Kynar, Viton, Solef, Hylar, Fluorel, Tecnoflon, Dyneon, Kalrez, Neoflon, Halar |
| **Replacement Candidates** | 30+ | Scored per use case (battery binder, seal, membrane, wire, coating, liner) |
| **Composition Predictions** | Unlimited | Any chemical formula via Kan extension prediction engine |
| **Formation Energies (DFT)** | 175 | Validated against published DFT calculations |
| **Crystal Structure Types** | 30 | 100% accuracy on known materials |

**With MP cache active**: 103,000+ materials available for crystal structure lookups

---

## Appendix: The 15-Material Demo BOM

This is the built-in demo you can use to show clients what a report looks like:

| # | Material | Function | Qty (kg) |
|---|----------|----------|----------|
| 1 | PVDF | cathode binder | 2.5 |
| 2 | PTFE | separator coating | 0.5 |
| 3 | NMC811 | cathode active material | 45.0 |
| 4 | Graphite | anode active material | 30.0 |
| 5 | EC | electrolyte solvent | 8.0 |
| 6 | DMC | electrolyte solvent | 8.0 |
| 7 | LiPF6 | electrolyte salt | 4.0 |
| 8 | Cu foil | anode current collector | 12.0 |
| 9 | Al foil | cathode current collector | 8.0 |
| 10 | PP | separator | 3.0 |
| 11 | PE | separator | 2.0 |
| 12 | Carbon Black | conductive additive | 1.5 |
| 13 | NMP | processing solvent | 5.0 |
| 14 | CMC | anode binder | 1.0 |
| 15 | SBR | anode binder | 0.8 |

**Expected results**: 2-3 PFAS detections (PVDF, PTFE), 12-13 clean materials, risk level HIGH.

---

*This rubric is your playbook. Print it. Follow it step by step. Each screening gets easier.*
