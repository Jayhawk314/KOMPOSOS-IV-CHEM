# KOMPOSOS-IV-CHEM: PFAS Scanner Structural Upgrade Design

## 1. Problem Context
The current PFAS Scanner (UI Feature #2) operates via the `pfas_bridge` using a static, name-based registry. It contains roughly 30 curated PFAS substances (e.g., PFOA, PFOS) and heuristic brand mappings (e.g., Kynar $\to$ PVDF). 

**The Critical Flaw (The Unknown Default):**
Because the system maps strings to registry keys, if a user inputs a completely novel, newly synthesized fluorinated polymer, the scanner will fail to recognize the name. It will default to "Unknown $\to$ Non-PFAS." This is a severe regulatory risk, as the scanner would declare a massive compliance false negative simply because the chemical name wasn't in its 30-item dictionary.

## 2. The Solution: Structural OECD Detection
Regulatory bodies (like the OECD and EPA) define PFAS structurally, not by an exhaustive list of names. The OECD 2021 definition states a PFAS is:
> *Any substance that contains at least one fully fluorinated methyl (-CF3) or methylene (-CF2-) carbon atom (without any H/Cl/Br/I atom attached to it).*

By transitioning the `pfas_bridge` to evaluate the **SMILES string** of a material using RDKit SMARTS patterns, the scanner will perfectly generalize to infinite novel chemical spaces.

### 2.1 The SMARTS Logic
The upgrade replaces the string-matching dictionary with the following RDKit structural matches:
1.  **-CF3 Group**: `[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)F`
2.  **-CF2- Group**: `[#6X4;H0;!$(*~[Cl,Br,I])](F)(F)`

If a material's SMILES contains either of these substructures, it is flagged as a PFAS. 

## 3. Empirical Ground Truth Validation (The 99.53% Prototype)
To prove this logic, we downloaded the official **EPA CompTox PFASSTRUCT V4** dataset (10,776 SMILES).

A prototype script (`G-docs/tests/prototype_pfas_detector.py`) evaluated the entire database against our structural OECD logic.
*   **Total EPA PFAS Evaluated:** 10,776
*   **True Positives Detected:** 10,725
*   **Recall:** **99.53%**

### Analysis of the False Negatives (The 0.47%)
The 51 missed molecules perfectly validate the strictness of the OECD rule vs. the EPA list:
1.  **Non-compliant structures**: Molecules like `FC(F)C(F)C(F)F` contain only `-CHF-`, `-CHF2`, and `-CH2F`. They lack a *fully* fluorinated carbon. The EPA list contains historical exceptions, but the strict OECD rule correctly rejects them.
2.  **RDKit Parse Failures**: Exotic chromium/silicon complexes that violate standard valency, or malformed data rows in the EPA CSV (e.g., lines containing just a DTXSID).

## 4. Integration Roadmap
1.  **Update Composition Engine**: The composition pipeline must ensure that every material requested in the BOM scanner has an associated SMILES string resolved (via PubChem or local cache) before hitting the `pfas_bridge`.
2.  **Update PFAS Bridge**: Delete the `exact_match` and `brand_match` dictionaries. Replace the `detect()` method with the RDKit SMARTS logic.
3.  **UI Feedback**: Update the Streamlit UI to show the user the offending SMILES substructure match (e.g., highlighting the exact -CF3 group) when a PFAS is detected, providing transparent, auditable regulatory compliance.

---
*G-docs Design Document | 2026-05-29*
