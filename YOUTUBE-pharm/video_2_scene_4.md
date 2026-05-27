---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
---

# The Multi-Scale Clinical Foundation
## Grounding Therapeutic Logic in Data

### Voiceover Script

"We reason through raw mutation data, interaction data from databases like ChEMBL, and real-world outcomes from thousands of clinical trials. We aren't just predicting drug success; we are mapping the Relations between scales."

---

### Visual Asset: Clinical Provenance Chain

<p align="center">
<svg width="500" height="200" viewBox="0 0 500 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="70" width="80" height="60" rx="5" fill="#161b22" stroke="#30363d" stroke-width="2"/>
  <text x="30" y="105" fill="#8b949e" font-size="12" font-weight="bold">Genomics</text>
  
  <path d="M 100 100 H 140" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <rect x="140" y="70" width="80" height="60" rx="5" fill="#161b22" stroke="#30363d" stroke-width="2"/>
  <text x="150" y="105" fill="#8b949e" font-size="12" font-weight="bold">ChEMBL</text>

  <path d="M 220 100 H 260" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <rect x="260" y="70" width="80" height="60" rx="5" fill="#161b22" stroke="#30363d" stroke-width="2"/>
  <text x="270" y="105" fill="#8b949e" font-size="12" font-weight="bold">Trials</text>

  <path d="M 340 100 H 380" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <circle cx="430" cy="100" r="45" fill="#f85149" stroke="#fff" stroke-width="3"/>
  <text x="405" y="105" fill="#fff" font-size="12" font-weight="bold">LOGIC</text>

  <defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c9d1d9"/></marker></defs>
</svg>
</p>
