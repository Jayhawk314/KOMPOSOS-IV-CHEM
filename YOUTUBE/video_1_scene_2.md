---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #f0f6fc;
  }
  h2 { color: #58a6ff; border-bottom: 2px solid #58a6ff; }
  .box {
    border: 2px solid #30363d;
    border-radius: 10px;
    padding: 15px;
    margin: 10px;
    background: #161b22;
  }
---

# The Architecture of Evidence
## The $\infty$-Cosmos Hierarchy

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
<div>

### The Reasoning Stack
- **2-Cells**: Path Equivalence
- **1-Cells**: Interaction Morphisms
- **0-Cells**: Material Objects

<br>

$$ \alpha : f \Rightarrow g $$
$$ f, g : A \to B $$

</div>
<div class="box">

<!-- INFINITY COSMOS SVG -->
<svg width="300" height="200" viewBox="0 0 300 200">
  <!-- Objects -->
  <circle cx="50" cy="100" r="10" fill="#58a6ff" />
  <text x="40" y="130" fill="#58a6ff" font-size="12">Mat A</text>
  <circle cx="250" cy="100" r="10" fill="#58a6ff" />
  <text x="240" y="130" fill="#58a6ff" font-size="12">Mat B</text>
  
  <!-- Path 1 -->
  <path d="M 60 90 Q 150 20 240 90" stroke="#f0883e" stroke-width="3" fill="none" />
  <text x="130" y="45" fill="#f0883e" font-size="12">Path f</text>
  
  <!-- Path 2 -->
  <path d="M 60 110 Q 150 180 240 110" stroke="#bc8cff" stroke-width="3" fill="none" />
  <text x="130" y="170" fill="#bc8cff" font-size="12">Path g</text>
  
  <!-- 2-Cell Natural Transformation -->
  <path d="M 150 70 L 150 130" stroke="#f0f6fc" stroke-width="2" stroke-dasharray="4" marker-end="url(#arrow)" />
  <text x="160" y="105" fill="#f0f6fc" font-size="16">α</text>
  
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f0f6fc" />
    </marker>
  </defs>
</svg>

</div>
</div>
