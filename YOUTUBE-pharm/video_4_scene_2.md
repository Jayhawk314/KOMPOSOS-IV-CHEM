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
  .data-stat {
    font-family: 'Courier New', monospace;
    font-size: 28px;
    color: #238636;
    font-weight: bold;
  }
  .data-label {
    font-size: 14px;
    color: #8b949e;
    margin-bottom: 15px;
  }
---

# The PHARM Data Inventory
## A Universe of Clinical Evidence

### Voiceover Script

"Just as we leveraged over 103,000 structures from the Materials Project for chemistry, **KOMPOSOS-IV-PHARM** is built on a similarly massive foundation of clinical truth. 

Our categorical runtime is powered by over **1.2 million drug-target interactions** from ChEMBL, giving us a dense map of potential binding morphisms. 

We’ve integrated **30,000 high-fidelity genomic profiles** from the Cancer Genome Atlas, allowing us to build precise Digital Patient Twins. 

And we reason through **450,000 clinical trials** and real-world patient cohorts. 

This isn't a database; it’s a living therapeutic cosmos where every data point—from a protein's binding affinity to a trial's survival curve—acts as a witness to the next lifesaving treatment."

---

### Visual Asset: Clinical Data Dashboard (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Drug-Target Block -->
  <rect x="50" y="50" width="240" height="100" rx="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <text x="70" y="90" fill="#58a6ff" font-size="36" font-weight="bold" font-family="monospace">1.2M+</text>
  <text x="70" y="125" fill="#8b949e" font-size="14">Drug-Target Interactions</text>

  <!-- Genomic Block -->
  <rect x="310" y="50" width="240" height="100" rx="10" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <text x="330" y="90" fill="#f85149" font-size="36" font-weight="bold" font-family="monospace">30,000</text>
  <text x="330" y="125" fill="#8b949e" font-size="14">Tumor Genomic Profiles</text>

  <!-- Small Blocks -->
  <rect x="50" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#238636" stroke-width="2" />
  <text x="70" y="210" fill="#238636" font-size="28" font-weight="bold" font-family="monospace">450k</text>
  <text x="70" y="235" fill="#8b949e" font-size="12">Clinical Trials</text>

  <rect x="225" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#bc8cff" stroke-width="2" />
  <text x="245" y="210" fill="#bc8cff" font-size="28" font-weight="bold" font-family="monospace">15,000</text>
  <text x="245" y="235" fill="#8b949e" font-size="12">Patient Cohorts</text>

  <rect x="400" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#f0883e" stroke-width="2" />
  <text x="420" y="210" fill="#f0883e" font-size="28" font-weight="bold" font-family="monospace">5,000+</text>
  <text x="420" y="235" fill="#8b949e" font-size="12">Repurpose Candidates</text>
</svg>
</p>

---

### PHARM Data Scale (LaTeX)

$$ |\text{Graph}(\mathcal{D})| = \text{ChEMBL}_{1.2M} + \text{TCGA}_{30k} + \text{Trials}_{450k} + \dots $$
$$ \mathcal{K}_{\text{pharm}} \approx 1.7 \times 10^6 \text{ Therapeutic Witnesses} $$
*(The scale of clinical evidence exceeds the Materials foundation, enabling unprecedented reasoning depth in oncology)*
