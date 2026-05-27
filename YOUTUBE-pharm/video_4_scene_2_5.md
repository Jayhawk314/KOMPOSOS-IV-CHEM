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
  .component-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 10px;
    margin: 5px;
    font-size: 14px;
  }
  .highlight { color: #f0883e; font-weight: bold; }
---

# The PHARM Intelligence Stack
## High-Performance Sensors for Clinical Logic

### Voiceover Script

"Our categorical runtime doesn't just process data; it processes **Intelligence**. We use a specialized stack of 'biological sensors' to feed the engine.

First, we use **ESM2**—an evolutionary scale model—to convert raw protein sequences into 1280-dimensional vectors, capturing the hidden 'grammar' of life. 
We ground our drug library with high-resolution **Public Spatial Biology Data**, ensuring our Digital Twins are anchored in high-quality biological reality and FDA-approved evidence. 
For binding evidence, we plug directly into **ChEMBL**, ingesting over 1.2 million morphisms to understand exactly how drugs engage with human targets. 
And finally, we use **Boltz2** as a structural filter, running heuristic geometry checks to ensure that a predicted binding isn't just a statistical guess, but a physically plausible interaction. 

It’s a multi-layered sensor suite that ensures our reasoning is as deep as the biology itself."

---

### Visual Asset: The Intelligence Stack (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Sensor 1: ESM2 -->
  <rect x="50" y="50" width="120" height="80" rx="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <text x="65" y="85" fill="#58a6ff" font-size="14" font-weight="bold">ESM2</text>
  <text x="65" y="110" fill="#8b949e" font-size="10">Sequence Vectors</text>

  <!-- Sensor 2: Spatial Bio (Formerly labeled Noetik) -->
  <rect x="180" y="50" width="120" height="80" rx="10" fill="#161b22" stroke="#bc8cff" stroke-width="2" />
  <text x="195" y="85" fill="#bc8cff" font-size="14" font-weight="bold">SPATIAL BIO</text>
  <text x="195" y="110" fill="#8b949e" font-size="10">Public Data Grounding</text>

  <!-- Sensor 3: ChEMBL -->
  <rect x="310" y="50" width="120" height="80" rx="10" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <text x="325" y="85" fill="#f85149" font-size="14" font-weight="bold">ChEMBL</text>
  <text x="325" y="110" fill="#8b949e" font-size="10">Binding Morphisms</text>

  <!-- Sensor 4: Boltz2 -->
  <rect x="440" y="50" width="120" height="80" rx="10" fill="#161b22" stroke="#238636" stroke-width="2" />
  <text x="455" y="85" fill="#238636" font-size="14" font-weight="bold">BOLTZ2</text>
  <text x="455" y="110" fill="#8b949e" font-size="10">Structural Filter</text>

  <!-- Unified Out -->
  <path d="M 110 130 V 200 H 490 V 130" stroke="#30363d" stroke-width="2" stroke-dasharray="5 5" />
  <circle cx="300" cy="220" r="40" fill="#161b22" stroke="#f0883e" stroke-width="4" />
  <text x="270" y="225" fill="#f0883e" font-size="12" font-weight="bold">INTEGRATOR</text>

  <path d="M 300 260 V 280" stroke="#f0883e" stroke-width="2" marker-end="url(#arrow-orange)" />
  
  <defs>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f0883e" /></marker>
  </defs>
</svg>
</p>

---

### Technical Sensor Mapping (LaTeX)

$$ \mathcal{E} : \text{Seq} \xrightarrow{\text{ESM2}} \mathbb{R}^{1280} $$
$$ \mathcal{B} : \text{Complex} \xrightarrow{\text{Boltz2}} [0, 1] \text{ (Geometric Score)} $$
*(Intelligence integration: Sequence embeddings $\mathcal{E}$ and structural scores $\mathcal{B}$ act as bounded evidence in the categorical runtime)*
