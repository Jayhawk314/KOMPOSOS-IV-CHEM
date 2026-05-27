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
  h1 { color: #58a6ff; }
  .highlight { color: #f0883e; font-weight: bold; }
---

# Video 1: The Hook
## Scene 1: The Contrast (0:00 - 0:45)

### Voiceover Script

"Most people see me as the guy delivering their packages, navigating the friction of the physical world. But while I'm on the road, another engine is running.

A pure Python, zero-GPU compositional reasoning engine that just cleared <span class="highlight">1,633 automated tests</span>.

This isn't a black-box model guessing at patterns. This is **KOMPOSOS-IV**: a categorical runtime where discovery is a proof, and chemistry is a category. 

Welcome to the era of interpretable materials intelligence."

---

### Visual Asset: "The Dual Engine" (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Physical Path (Friction) -->
  <path d="M50 250C150 250 150 200 250 200" stroke="#444" stroke-width="2" stroke-dasharray="5 5" />
  <circle cx="50" cy="250" r="5" fill="#444" />
  <text x="40" y="275" fill="#666" font-size="12">Physical Delivery (Noise)</text>

  <!-- Categorical Path (Engine) -->
  <path d="M350 200C450 200 450 100 550 100" stroke="#58a6ff" stroke-width="3" />
  <circle cx="350" cy="200" r="8" fill="#58a6ff" />
  <circle cx="550" cy="100" r="8" fill="#58a6ff" />
  
  <!-- Commutative Square Elements -->
  <line x1="350" y1="200" x2="550" y2="200" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)" />
  <line x1="550" y1="200" x2="550" y2="100" stroke="#58a6ff" stroke-width="2" marker-end="url(#arrow)" />
  
  <text x="330" y="225" fill="#58a6ff" font-size="14" font-weight="bold">Material A</text>
  <text x="540" y="80" fill="#58a6ff" font-size="14" font-weight="bold">Property Φ</text>
  <text x="430" y="140" fill="#f0883e" font-size="16" font-weight="bold">1,633 TESTS PASS</text>
  
  <!-- Definitions -->
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" />
    </marker>
  </defs>
</svg>
</p>

---

### Mathematical Core (LaTeX)

$$ \mathcal{C}_{runtime} : \text{Execution as a Functor } F: \text{Chem} \to \text{Logic} $$
$$ \forall m \in \text{Morphisms}, \text{Proof}(m) \implies \text{Valid}(m) $$
