---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Inter', sans-serif;
  }
  h2 { color: #58a6ff; }
  .provenance-box {
    background: #161b22;
    border: 2px solid #238636;
    border-radius: 12px;
    padding: 15px;
    font-size: 14px;
  }
  .highlight { color: #f0883e; font-weight: bold; }
---

# The Rigorous Evidence Base
## 100% Provenance, Zero Assumptions

### Voiceover Script

"In precision medicine, an unverified connection is a liability. That’s why **KOMPOSOS-IV-PHARM** is built on an evidence base of <span class="highlight">1,260 therapeutic morphisms</span> with **100% complete provenance**. 

Every edge in our clinical category—whether it's a drug inhibiting a kinase or a protein driving a disease—is backed by a PMID or a ChEMBL identifier. 

We model biological plausibility through **Edge Confidences**, typically ranging from 0.5 to 0.8. These aren't just weights; they represent the strength of the underlying literature evidence. 

We further harden this with **ESM2 intelligence**, capturing the evolutionary grammar of proteins in 1280 dimensions, and **Boltz2 structural filters** that verify the physical geometry of every drug-target complex. 

Finally, we ground our patient models in public **Spatial Transcriptomics data**, using NanoString CosMx SMI datasets to ensure our reasoning accounts for the real-world spatial orientation of tumor cells."

---

### Visual Asset: Evidence Provenance (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Edge Confidence Scale -->
  <rect x="50" y="50" width="500" height="20" rx="5" fill="#161b22" stroke="#30363d" />
  <rect x="300" y="52" width="150" height="16" rx="3" fill="#238636" fill-opacity="0.6" />
  <text x="50" y="40" fill="#8b949e" font-size="10">Edge Confidence (0.5 - 0.8)</text>
  <text x="320" y="65" fill="#fff" font-size="10" font-weight="bold">Plausibility Zone</text>

  <!-- Provenance Bubbles -->
  <circle cx="100" cy="150" r="40" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <text x="75" y="155" fill="#58a6ff" font-size="12" font-weight="bold">PMID</text>
  
  <circle cx="220" cy="150" r="40" fill="#161b22" stroke="#bc8cff" stroke-width="2" />
  <text x="185" y="155" fill="#bc8cff" font-size="12" font-weight="bold">ChEMBL</text>

  <circle cx="340" cy="150" r="40" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <text x="310" y="155" fill="#f85149" font-size="12" font-weight="bold">CosMx</text>

  <!-- Total Count -->
  <rect x="420" y="120" width="130" height="60" rx="10" fill="#161b22" stroke="#238636" stroke-width="3" />
  <text x="435" y="150" fill="#238636" font-size="20" font-weight="bold">1,260 Edges</text>
  <text x="435" y="170" fill="#8b949e" font-size="10">100% CITED</text>

  <!-- Inter-scale connections -->
  <path d="M 140 150 H 180 M 260 150 H 300" stroke="#30363d" stroke-width="2" stroke-dasharray="4 2" />
</svg>
</p>

---

### Technical Rigor (LaTeX)

<div class="provenance-box">

$$ \forall e \in \text{Edges}(\mathcal{D}), \, \exists s \in \{\text{PMID, ChEMBL, CosMx}\} \mid \text{Source}(e) = s $$
$$ \mathcal{C}(e) = w_{\text{lit}} \cdot \mathcal{B}_{\text{boltz2}} \cdot \mathcal{E}_{\text{esm2}} \in [0.5, 0.8] $$
*(Aggregating literature evidence, structural geometry, and sequence intelligence into a rigid confidence metric)*

</div>
