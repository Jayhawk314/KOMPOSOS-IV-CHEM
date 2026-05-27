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
  h1 { color: #bc8cff; } /* Purple for Abstract Math */
  .math-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
  }
---

# Video 3: Core Mathematics (PHARM)
## Scene 1: Clinical Entities as Objects (0:00 - 2:00)

### Voiceover Script

"In the materials engine, we mapped crystals and electrolytes. But in **KOMPOSOS-IV-PHARM**, the objects are far more personal. 

Here, **Patients**, **Drugs**, and **Biological Targets** are the fundamental Objects of our category. 

A 'Target' might be an overexpressed protein in a lung cancer cell. A 'Drug' is a molecule designed to interact with it. 

The interaction itself—the binding affinity or the inhibitory effect—is a **Morphism**. 

By formalizing medicine this way, we can use **Morphism Composition** to reason through the entire therapeutic chain. If a drug inhibits a target, and that target drives a disease pathway in a specific patient, the engine mathematically proves the drug's efficacy for that patient. It’s clinical logic, verified by the geometry of categories."

---

### Visual Asset: Clinical Category Structure (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Objects -->
  <g id="Drug">
    <rect x="50" y="100" width="80" height="40" rx="5" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
    <text x="70" y="125" fill="#58a6ff" font-size="12" font-weight="bold">DRUG (D)</text>
  </g>
  
  <g id="Target">
    <circle cx="300" cy="120" r="30" fill="#161b22" stroke="#bc8cff" stroke-width="2" />
    <text x="275" y="125" fill="#bc8cff" font-size="12" font-weight="bold">TARGET (T)</text>
  </g>
  
  <g id="Patient">
    <circle cx="530" cy="200" r="40" fill="#161b22" stroke="#f85149" stroke-width="2" />
    <text x="500" y="205" fill="#f85149" font-size="12" font-weight="bold">PATIENT (P)</text>
  </g>

  <!-- Morphism f: Binding -->
  <path d="M 135 120 H 265" stroke="#58a6ff" stroke-width="3" marker-end="url(#arrow-blue)" />
  <text x="170" y="110" fill="#58a6ff" font-size="14" font-style="italic">f : Binding</text>

  <!-- Morphism g: Efficacy -->
  <path d="M 335 135 L 485 185" stroke="#bc8cff" stroke-width="3" marker-end="url(#arrow-purple)" />
  <text x="360" y="155" fill="#bc8cff" font-size="14" font-style="italic">g : Efficacy</text>

  <!-- Composition g ∘ f: Predicted Outcome -->
  <path d="M 110 150 Q 300 250 490 210" stroke="#f0883e" stroke-width="3" stroke-dasharray="8 4" marker-end="url(#arrow-orange)" />
  <text x="250" y="260" fill="#f0883e" font-size="16" font-weight="bold">g ∘ f : Repurposing Proof</text>

  <defs>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" /></marker>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#bc8cff" /></marker>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f0883e" /></marker>
  </defs>
</svg>
</p>

---

### Categorical Foundation (LaTeX)

<div class="math-box">

$$ \text{Hom}_{\text{Pharm}}(D, P) \cong \sum_{T \in \text{Targets}} \text{Hom}(D, T) \otimes \text{Hom}(T, P) $$
$$ \forall d \in \text{Drug}, p \in \text{Patient}, \, \text{Therapy} = \text{Comp}(g \circ f) $$

</div>
