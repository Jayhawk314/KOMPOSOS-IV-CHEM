# KOMPOSOS-IV-CHEM: Data Provenance & Scientific Audit

## The Empirical Audit Posture

KOMPOSOS-IV-CHEM operates under a strict scientific audit protocol. The system is designed to provide "Research Grade" validation, ensuring that predictive claims are grounded in verifiable data rather than model hallucination.

### The Audit Hierarchy
1. **Code & Live Data**: The frozen audit results and live database queries are the absolute source of truth, outranking any written documentation.
2. **Logical Witnesses**: Every compatibility or design prediction must surface the strategy votes (e.g., STT, classical, MD) and the ZFC logical witnesses to the user.

## Current Benchmark Status

The system's performance is actively measured against specialized datasets, but
the claim type depends on how much the set has been inspected.

- **Development Set (Q5)**: `41/41` (100.0% accuracy). Use only for regression.
- **Q8 first clean blind run**: 40 literature-backed pairs, 30/40 evaluated,
  `70.0%` on scored pairs, AUROC `0.700`, Brier `0.259`, ECE `0.256`.
  This exposed coverage and calibration gaps.
- **Q8 post-remediation diagnostic artifact**: one stored run reported 38/40
  evaluated, 2 skipped, accuracy `86.8%`, AUROC `0.9038`, Brier `0.119`,
  ECE `0.117`. Q8 is spent and must not be headlined as fresh blind
  performance.
- **Q9 initial blind diagnostic**: 40/40 evaluated, 32/40 = `80.0%`, TP=27,
  TN=5, FP=4, FN=4.
- **Q9 after production chi_c integration**: 40/40 evaluated, 35/40 = `87.5%`,
  TP=27, TN=8, FP=1, FN=4, AUROC `0.9247`, AP `0.9745`, Brier `0.0987`,
  ECE `0.1486`. Q9 is also spent after inspection and diagnosis.
- **Q10 sealed future exam**: pair file and hidden label file exist, but Codex
  must not inspect the labels or score the set until after the polymer
  chi_c/MW model is implemented.

The first Flory-Huggins $\chi_c$ production fix is now in place. The remaining
research-grade step is to validate on sealed Q10 after replacing representative
MW values with cited, grade-specific data where possible.

## Physical Grounding

The system rejects the practice of "fixing" failed predictions by arbitrarily weakening thresholds.
- **Rule**: If a physical grounding check fails, the empirical bond source must be evaluated.
- **Implementation**: The system uses **normalized Gaussian typicality** for bond plausibility mapping, derived from empirical crystallographic statistics, with a fallback CDF-centrality for bounds-only cases.

## Multi-Tiered Evidence Fusion

When the Compatibility Checker evaluates a pair, it fuses evidence from multiple sources:
1. **Curated Database (Tier 1)**: Hand-audited pairs backed by primary literature (PMID/DOI anchors).
2. **Materials Project Cache**: Computational grounding using 103K+ DFT-computed structures (formation energies, space groups).
3. **Simplicial Strategies**: Mathematical inference (Yoneda similarity, Fibration transport) when direct empirical data is missing.
4. **ZFC Validation**: The final gatekeeper that can "VETO" a positive prediction if it violates fundamental physical constraints.

## Regulatory Coverage (PFAS)
- **Coverage**: Generalized OECD 2021 structural definition (RDKit SMARTS).
- **Role**: Compliance screening for commercial bill-of-materials.
- **Metrics**: Specificity **100% on a 25-molecule hard-negative panel** (fluorinated-but-not-PFAS + commons); **99.5% concordance** with EPA PFASSTRUCT v4 (10,776 SMILES). The EPA figure is *concordance* with EPA's own structural definition, not independent validation, and is NOT an AUROC — a binary OECD substructure rule has no ROC curve. (Prior "0.9976 AUROC" was balanced accuracy on 8 negatives; corrected.)

---
*G-docs Data & Quality | 2026-05-29*
