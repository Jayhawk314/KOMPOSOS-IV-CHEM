---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
  h2 { color: #238636; }
---

# The GPU-Free Revolution
## Local Intelligence, Global Rigidity

### Voiceover Script

"While the rest of the industry is burning millions on GPU clusters for black-box guesses, KOMPOSOS-IV runs on a standard laptop. 

Why? Because logic is lighter than parameters. 

By embedding chemistry into a **120-dimensional physics space**, we use **Kan Extensions** to interpolate properties in milliseconds. We don’t need to train a model to 'know' that Barium is like Strontium; the geometry of our category already proves it. 

It’s zero-GPU, zero-latency, and 100% interpretable."

---

### Visual Asset: The 120D Composition Space

<p align="center">
<svg width="500" height="200" viewBox="0 0 500 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="70" width="120" height="60" rx="5" fill="#161b22" stroke="#c9d1d9" stroke-width="2"/>
  <text x="25" y="105" fill="#c9d1d9" font-size="12">Chemical Formula</text>
  
  <path d="M 130 100 H 170" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>
  
  <rect x="175" y="70" width="130" height="60" rx="5" fill="#238636" stroke="#fff" stroke-width="2"/>
  <text x="185" y="105" fill="#fff" font-size="12" font-weight="bold">120D Physics Vector</text>

  <path d="M 305 100 H 345" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <rect x="350" y="70" width="130" height="60" rx="5" fill="#58a6ff" stroke="#fff" stroke-width="2"/>
  <text x="360" y="105" fill="#fff" font-size="12" font-weight="bold">Categorical Runtime</text>

  <defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c9d1d9"/></marker></defs>
</svg>
</p>

---

### Mathematical Efficiency (LaTeX)

$$ Lan_F(c) = \int_{c_i \in \mathcal{C}} w(c, c_i) \cdot F(c_i) \, d\mathcal{C} $$
