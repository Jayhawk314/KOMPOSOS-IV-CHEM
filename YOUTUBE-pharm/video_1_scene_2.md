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
  h2 { color: #f85149; border-bottom: 2px solid #f85149; }
  .data-tag {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 14px;
    margin: 5px;
    display: inline-block;
  }
---

# The Digital Patient Twin
## Modeling Patients as Categorical Objects

### Voiceover Script

"In traditional medicine, treatments are designed for the 'average' patient. But in **KOMPOSOS-IV-PHARM**, there is no average. 

We model every patient as a unique **Object** in our clinical category. 

By integrating genomic sequences, proteomic markers, and real-world clinical history, we build a **Digital Patient Twin**. This isn't just a medical record; it’s a mathematical representation of a patient's biological state. 

We map their specific tumor mutations as 'holes' in their health-sheaf—topological gaps that we must fill with the right drug-morphism. We aren't treating a disease; we are resolving a patient's unique biological logic."

---

### Visual Asset: The Patient Object (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Central Patient Node -->
  <circle cx="300" cy="150" r="60" fill="#161b22" stroke="#f85149" stroke-width="3" />
  <text x="270" y="155" fill="#f85149" font-size="16" font-weight="bold">PATIENT P</text>

  <!-- Data Strands (DNA-like) -->
  <path d="M 100 150 Q 200 100 300 150 T 500 150" stroke="#58a6ff" stroke-width="2" stroke-dasharray="4 4" />
  <path d="M 100 150 Q 200 200 300 150 T 500 150" stroke="#bc8cff" stroke-width="2" stroke-dasharray="4 4" />

  <!-- Specific Markers -->
  <g>
    <circle cx="200" cy="80" r="5" fill="#f85149" />
    <text x="140" y="75" fill="#8b949e" font-size="10">KRAS Mutation</text>
    <line x1="200" y1="80" x2="250" y2="120" stroke="#30363d" stroke-width="1" />
  </g>
  
  <g>
    <circle cx="400" cy="80" r="5" fill="#f85149" />
    <text x="410" y="75" fill="#8b949e" font-size="10">TP53 Status</text>
    <line x1="400" y1="80" x2="350" y2="120" stroke="#30363d" stroke-width="1" />
  </g>

  <g>
    <circle cx="300" cy="250" r="5" fill="#238636" />
    <text x="280" y="270" fill="#8b949e" font-size="10">Clinical History</text>
    <line x1="300" y1="250" x2="300" y2="210" stroke="#30363d" stroke-width="1" />
  </g>
</svg>
</p>

---

### Patient Identity Logic (LaTeX)

$$ \mathcal{P}_i = \{ \text{Gen}_i, \text{Prot}_i, \text{Clin}_i \} \in \text{Ob}(\text{Pharm}) $$
$$ \text{State}(P) = \int_{g \in \text{Genes}} \omega(g) \cdot \delta(g) \, dg $$
*(Integrating genetic weights $\omega$ over the patient's biological domain to define their categorical state)*
