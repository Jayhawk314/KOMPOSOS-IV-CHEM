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
  h1 { color: #f85149; } /* Clinical Red */
  .highlight { color: #58a6ff; font-weight: bold; }
---

# Video 1: The Pivot
## Scene 1: From Materials to Medicine (0:00 - 0:45)

### Voiceover Script

"We’ve proven that **KOMPOSOS-IV** can reason about the world’s most complex materials—batteries, semiconductors, and polymers. But the geometry of logic doesn’t stop at the lab bench. 

What if the same categorical runtime that designs a solid-state battery could design a personalized treatment for a stage-IV cancer patient?

Today, we are pivoting. We are applying the same <span class="highlight">functorial mapping</span> to move from chemistry to precision oncology. 

This is **KOMPOSOS-IV-PHARM**: where patients are objects, diseases are morphisms, and drugs are the proofs that lead to recovery."

---

### Visual Asset: The Ontological Pivot (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Pivot Background -->
  <circle cx="300" cy="150" r="120" stroke="#30363d" stroke-width="1" stroke-dasharray="5 5" />
  
  <!-- Left Side: Materials (Ghosted/Transitioning) -->
  <g opacity="0.4">
    <rect x="50" y="100" width="120" height="100" rx="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
    <text x="60" y="155" fill="#58a6ff" font-size="14" font-weight="bold">MATERIALS</text>
  </g>

  <!-- Right Side: Clinical (Active/Bright) -->
  <g>
    <rect x="430" y="100" width="120" height="100" rx="10" fill="#161b22" stroke="#f85149" stroke-width="4" />
    <text x="455" y="155" fill="#f85149" font-size="14" font-weight="bold">CLINICAL</text>
  </g>

  <!-- The Pivot Arrow -->
  <path d="M 200 150 Q 300 50 400 150" stroke="#f0f6fc" stroke-width="4" stroke-dasharray="10 5" marker-end="url(#arrow-pivot)" />
  <text x="270" y="80" fill="#f0f6fc" font-size="18" font-weight="bold">FUNCTOR F</text>

  <!-- Central Symbol -->
  <path d="M 280 150 L 320 150 M 300 130 L 300 170" stroke="#f85149" stroke-width="8" stroke-linecap="round" />

  <defs>
    <marker id="arrow-pivot" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f0f6fc" />
    </marker>
  </defs>
</svg>
</p>

---

### Mathematical Transition (LaTeX)

$$ \Phi : \text{Chem}_{\text{Structure}} \xrightarrow{\sim} \text{Pharm}_{\text{Efficacy}} $$
$$ \text{Material}(\text{Composition}) \mapsto \text{Drug}(\text{Patient\_Profile}) $$
*(The structural identity of a material maps to the therapeutic efficacy of a drug treatment)*
