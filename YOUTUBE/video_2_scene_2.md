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

# Scanning the Bill of Materials
## From Raw BOM to Risk Verdicts

### Voiceover Script

"We use three Detection Tiers: 
1. EXACT for CAS number matches.
2. HEURISTIC for brand-name resolution.
3. UNKNOWN for clean materials.

In seconds, the scanner flags the existential threat: the PVDF binder used in our cathode formulation."

---

### Visual Asset: The Detection Pipeline

<p align="center">
<svg width="500" height="300" viewBox="0 0 500 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="200" y="20" width="100" height="40" rx="5" fill="#161b22" stroke="#c9d1d9" stroke-width="2"/>
  <text x="215" y="45" fill="#c9d1d9" font-size="12">BOM CSV</text>
  
  <path d="M 250 60 V 90" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>
  
  <rect x="175" y="90" width="150" height="60" rx="10" fill="#58a6ff" stroke="#fff" stroke-width="2"/>
  <text x="205" y="125" fill="#fff" font-size="16" font-weight="bold">PFAS BRIDGE</text>

  <path d="M 175 120 H 100 V 170" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>
  <path d="M 325 120 H 400 V 170" stroke="#c9d1d9" stroke-width="2" marker-end="url(#arr)"/>

  <rect x="30" y="170" width="120" height="40" rx="5" fill="#161b22" stroke="#238636" stroke-width="2"/>
  <text x="45" y="195" fill="#238636" font-size="12" font-weight="bold">Tier 1: EXACT</text>

  <rect x="350" y="170" width="120" height="40" rx="5" fill="#161b22" stroke="#f0883e" stroke-width="2"/>
  <text x="360" y="195" fill="#f0883e" font-size="12" font-weight="bold">Tier 2: BRAND</text>

  <defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c9d1d9"/></marker></defs>
</svg>
</p>
