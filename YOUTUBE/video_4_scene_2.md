---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
  h1 { color: #f85149; } /* Red for Clinical/High Stakes */
  .functor { color: #58a6ff; font-weight: bold; }
  .box {
    background: #161b22;
    border: 2px solid #30363d;
    border-radius: 12px;
    padding: 15px;
  }
---

# The Precision Oncology Leap
## Mapping Chemistry to Clinical Reality

### Voiceover Script

"The ultimate proof of a mathematical framework is its scalability. If Category Theory can model a solid-state battery, can it model a human patient?

Welcome to **KOMPOSOS-IV-PHARM**. 

By applying a **Functorial Mapping**, we've transitioned from materials chemistry to precision medicine. Instead of Material-Interactions, we reason through **Drug-Disease-Patient Morphisms**. 

The engine uses **Streaming Kan Extensions** to find cancer drug repurposing candidates in real-time, matching the unique genetic 'geometry' of a patient's tumor to the existing world of approved treatments. It’s the same logic, but with a different set of stakes: saving lives through compositional oncology."

---

### Visual Asset: The Functorial Leap (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Domain: CHEM -->
  <rect x="50" y="50" width="200" height="200" rx="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <text x="120" y="40" fill="#58a6ff" font-size="16" font-weight="bold">CHEM</text>
  <circle cx="100" cy="100" r="10" fill="#58a6ff" />
  <circle cx="200" cy="200" r="10" fill="#58a6ff" />
  <path d="M 110 110 L 190 190" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow-blue)" />

  <!-- The Functor F -->
  <path d="M 270 150 H 330" stroke="#f0f6fc" stroke-width="4" marker-end="url(#arrow-white)" />
  <text x="290" y="130" fill="#f0f6fc" font-size="24" font-weight="bold">F</text>

  <!-- Domain: PHARM -->
  <rect x="350" y="50" width="200" height="200" rx="10" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <text x="420" y="40" fill="#f85149" font-size="16" font-weight="bold">PHARM</text>
  <circle cx="400" cy="100" r="10" fill="#f85149" />
  <circle cx="500" cy="200" r="10" fill="#f85149" />
  <path d="M 410 110 L 490 190" stroke="#f85149" stroke-width="2" marker-end="url(#arrow-red)" />

  <!-- Labels -->
  <text x="60" y="130" fill="#8b949e" font-size="10">Material</text>
  <text x="180" y="230" fill="#8b949e" font-size="10">Property</text>
  
  <text x="360" y="130" fill="#8b949e" font-size="10">Drug</text>
  <text x="480" y="230" fill="#8b949e" font-size="10">Outcome</text>

  <defs>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" /></marker>
    <marker id="arrow-white" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f0f6fc" /></marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f85149" /></marker>
  </defs>
</svg>
</p>

---

### Cross-Domain Reasoning (LaTeX)

<div class="box">

$$ F : \mathcal{C}_{\text{Materials}} \to \mathcal{D}_{\text{Oncology}} $$
$$ \text{Drug} \xrightarrow{\text{Interaction}} \text{Target} \xrightarrow{\text{Morphism}} \text{Patient\_State} $$
*(Mapping physical compatibility into clinical survivability)*

</div>
