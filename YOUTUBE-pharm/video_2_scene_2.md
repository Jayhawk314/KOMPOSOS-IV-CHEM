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
---

# Mapping the Patient Sheaf
## Gluing Local Data into Global Truth

### Voiceover Script

"The engine's job is to Glue these sections together. If the genomic data predicts a target, but the clinical history shows a contraindication, the Sheaf condition fails. By enforcing this mathematical coherence, we ensure that our repurposing candidates are globally consistent."

---

### Visual Asset: Data Integration Map

<p align="center">
<svg width="500" height="200" viewBox="0 0 500 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="20" width="100" height="40" rx="5" fill="#161b22" stroke="#58a6ff" stroke-width="2"/>
  <text x="35" y="45" fill="#58a6ff" font-size="12" font-weight="bold">Genomics</text>
  
  <rect x="140" y="20" width="100" height="40" rx="5" fill="#161b22" stroke="#bc8cff" stroke-width="2"/>
  <text x="155" y="45" fill="#bc8cff" font-size="12" font-weight="bold">Proteomics</text>

  <rect x="260" y="20" width="100" height="40" rx="5" fill="#161b22" stroke="#238636" stroke-width="2"/>
  <text x="275" y="45" fill="#238636" font-size="12" font-weight="bold">Clinical</text>

  <path d="M 70 60 V 100 H 200 V 130" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>
  <path d="M 190 60 V 130" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>
  <path d="M 310 60 V 100 H 220 V 130" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <circle cx="210" cy="150" r="40" fill="#f85149" stroke="#fff" stroke-width="3"/>
  <text x="180" y="155" fill="#fff" font-size="12" font-weight="bold">PATIENT TWIN</text>

  <defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c9d1d9"/></marker></defs>
</svg>
</p>
