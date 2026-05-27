---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
  h2 { color: #58a6ff; }
  .data-stat {
    font-family: 'Courier New', monospace;
    font-size: 28px;
    color: #238636;
    font-weight: bold;
  }
  .data-label {
    font-size: 14px;
    color: #8b949e;
    margin-bottom: 15px;
  }
---

# The Data Inventory
## A Massive Foundation of Evidence

### Voiceover Script

"To reason effectively, the engine requires a massive library of established truth. Yes, we are still leveraging the full power of the **103,671 Materials Project structures**, giving us DFT-computed formation energies and crystal parameters for the entire known materials universe.

But that’s just the beginning. 

We also maintain **175 curated bridge materials** with peer-reviewed properties, **37 molecular objects** with full SMILES and CAS data, and **30 experimental MOF topologies**. 

We’ve even mapped **35 regulated PFAS substances** and **274 known organic linkers**. 

This isn't just a database; it is a 104,000-node knowledge graph where every node is a potential witness to your next discovery."

---

### Visual Asset: The Data Dashboard (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- MP Cache Block -->
  <rect x="50" y="50" width="240" height="100" rx="10" fill="#161b22" stroke="#238636" stroke-width="2" />
  <text x="70" y="90" fill="#238636" font-size="36" font-weight="bold" font-family="monospace">103,671</text>
  <text x="70" y="125" fill="#8b949e" font-size="14">Materials Project (DFT)</text>

  <!-- Curated Materials Block -->
  <rect x="310" y="50" width="240" height="100" rx="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <text x="330" y="90" fill="#58a6ff" font-size="36" font-weight="bold" font-family="monospace">175</text>
  <text x="330" y="125" fill="#8b949e" font-size="14">Curated Bridge Materials</text>

  <!-- Small Blocks -->
  <rect x="50" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#f0883e" stroke-width="2" />
  <text x="70" y="210" fill="#f0883e" font-size="28" font-weight="bold" font-family="monospace">37</text>
  <text x="70" y="235" fill="#8b949e" font-size="12">Molecules</text>

  <rect x="225" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#bc8cff" stroke-width="2" />
  <text x="245" y="210" fill="#bc8cff" font-size="28" font-weight="bold" font-family="monospace">30</text>
  <text x="245" y="235" fill="#8b949e" font-size="12">MOF Topologies</text>

  <rect x="400" y="170" width="150" height="80" rx="10" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <text x="420" y="210" fill="#f85149" font-size="28" font-weight="bold" font-family="monospace">35</text>
  <text x="420" y="235" fill="#8b949e" font-size="12">PFAS Substances</text>
</svg>
</p>

---

### Data Scale (LaTeX)

$$ |\text{Graph}(\mathcal{C})| = \text{MP}_{103K} + \text{Curated}_{175} + \text{Mol}_{37} + \text{MOF}_{30} + \dots $$
$$ \mathcal{K} \approx 1.04 \times 10^5 \text{ Unique Entities} $$
