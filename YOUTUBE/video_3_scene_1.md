---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
  h1 { color: #bc8cff; } /* Purple for Math/Abstract */
  .math-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
  }
---

# Video 3: The Core Mathematics
## Scene 1: Materials as Objects (0:00 - 2:00)

### Voiceover Script

"To understand how KOMPOSOS-IV reasons, we have to stop thinking about data as a flat table and start seeing it as a geometric structure. In this engine, **Chemistry is a Category**.

Every material—whether it's an NMC cathode, an EC solvent, or a copper collector—is represented as an **Object**. 

Every interaction between them—compatibility, wetting, or electrochemical stability—is a **Morphism**. 

This shift is profound. It means we aren't just storing facts; we are building a logic where interactions can be **composed**. If the system knows how Material A interacts with B, and B with C, it can mathematically deduce the relationship between A and C without a single guess."

---

### Visual Asset: Compositional Reasoning (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Objects -->
  <circle cx="100" cy="200" r="15" fill="#58a6ff" />
  <text x="85" y="240" fill="#58a6ff" font-size="14" font-weight="bold">Obj A</text>
  
  <circle cx="300" cy="100" r="15" fill="#58a6ff" />
  <text x="285" y="140" fill="#58a6ff" font-size="14" font-weight="bold">Obj B</text>
  
  <circle cx="500" cy="200" r="15" fill="#58a6ff" />
  <text x="485" y="240" fill="#58a6ff" font-size="14" font-weight="bold">Obj C</text>

  <!-- Morphism f -->
  <path d="M 115 190 L 285 110" stroke="#bc8cff" stroke-width="3" marker-end="url(#arrow-purple)" />
  <text x="180" y="140" fill="#bc8cff" font-size="16" font-style="italic">f</text>

  <!-- Morphism g -->
  <path d="M 315 110 L 485 190" stroke="#bc8cff" stroke-width="3" marker-end="url(#arrow-purple)" />
  <text x="400" y="140" fill="#bc8cff" font-size="16" font-style="italic">g</text>

  <!-- Composition g ∘ f -->
  <path d="M 115 205 L 485 205" stroke="#f0883e" stroke-width="3" stroke-dasharray="8 4" marker-end="url(#arrow-orange)" />
  <text x="280" y="230" fill="#f0883e" font-size="18" font-weight="bold">g ∘ f</text>

  <defs>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#bc8cff" />
    </marker>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f0883e" />
    </marker>
  </defs>
</svg>
</p>

---

### Categorical Foundation (LaTeX)

<div class="math-box">

$$ \text{Comp}(\mathcal{C}) : \text{Hom}(A, B) \times \text{Hom}(B, C) \to \text{Hom}(A, C) $$
$$ \forall f: A \to B, \, g: B \to C \implies \exists (g \circ f): A \to C $$

</div>
