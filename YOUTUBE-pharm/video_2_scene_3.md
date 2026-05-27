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
  h2 { color: #f0883e; border-bottom: 2px solid #f0883e; }
  .math-container {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
  }
---

# Optimal Transport for Drug Targeting
## Minimizing Biological Work

### Voiceover Script

"Finding a target is only half the battle. We also have to find the most efficient path to reach it. **KOMPOSOS-IV-PHARM** solves this using the mathematics of **Optimal Transport**. 

We treat the patient's diseased state and the drug's therapeutic profile as two probability distributions in a high-dimensional biological space. 

The engine then calculates the **Wasserstein distance**—measuring the mathematical 'work' required to move the biological system from disease to health. By minimizing this transport cost, we don't just find a drug that works; we find the one that reaches the target with the lowest energy cost and the fewest side effects. 

It’s precision targeting, driven by the geometry of optimal delivery."

---

### Visual Asset: The Transport Map (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Distribution 1: Disease (Mu) -->
  <path d="M 50 250 Q 150 50 250 250" stroke="#f85149" stroke-width="3" fill="rgba(248, 81, 73, 0.1)" />
  <text x="120" y="270" fill="#f85149" font-size="14" font-weight="bold">Disease (μ)</text>

  <!-- Distribution 2: Health (Nu) -->
  <path d="M 350 250 Q 450 100 550 250" stroke="#238636" stroke-width="3" fill="rgba(35, 134, 54, 0.1)" />
  <text x="430" y="270" fill="#238636" font-size="14" font-weight="bold">Health (ν)</text>

  <!-- Transport Map (Arrows) -->
  <path d="M 120 180 Q 250 100 380 180" stroke="#58a6ff" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow-blue)" />
  <path d="M 150 130 Q 300 50 450 130" stroke="#58a6ff" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow-blue)" />
  <path d="M 180 180 Q 310 100 440 180" stroke="#58a6ff" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow-blue)" />
  
  <text x="260" y="140" fill="#58a6ff" font-size="12" font-weight="bold">TRANSPORT MAP (T)</text>

  <defs>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" />
    </marker>
  </defs>
</svg>
</p>

---

### Mathematical Core (LaTeX)

<div class="math-container">

$$ W_p(\mu, \nu) = \left( \inf_{\gamma \in \Gamma(\mu, \nu)} \int_{\mathcal{X} \times \mathcal{X}} d(x, y)^p \, d\gamma(x, y) \right)^{1/p} $$
*(Wasserstein Distance: The minimum 'cost' of transforming the diseased distribution $\mu$ into the healthy distribution $\nu$)*

</div>
