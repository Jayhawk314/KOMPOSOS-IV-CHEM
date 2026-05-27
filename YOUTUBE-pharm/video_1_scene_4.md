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
  .stream-box {
    background: #161b22;
    border: 1px solid #238636;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 0 10px rgba(35, 134, 54, 0.2);
  }
---

# The Streaming Kan Extension
## Real-Time Repurposing at Scale

### Voiceover Script

"Finding a repurposing candidate is like searching for a needle in a haystack of billions of data points. But in a categorical runtime, we don’t search—we interpolate.

Version IV introduces the **Streaming Kan Extension**. 

As a patient’s genetic stream enters the engine, the runtime category dynamically extends its knowledge. It maps the patient's unique mutation profile onto the global map of drug-disease interactions, discovering 'Best Approximations' of treatment success in milliseconds. 

This is the ultimate scalability: a system that grows its intelligence with every new patient, every new paper, and every new clinical trial. We aren't just predicting the future of oncology; we are streaming it into existence."

---

### Visual Asset: Streaming Interpolation (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- The Knowledge Category (Base) -->
  <circle cx="300" cy="150" r="100" stroke="#30363d" stroke-width="2" fill="#161b22" />
  <text x="250" y="270" fill="#8b949e" font-size="12">KNOWLEDGE BASE (C)</text>

  <!-- Incoming Stream -->
  <g id="stream">
    <rect x="20" y="140" width="100" height="20" rx="3" fill="#238636" fill-opacity="0.3" stroke="#238636" />
    <text x="30" y="155" fill="#238636" font-size="10" font-weight="bold">GENETIC STREAM</text>
    <path d="M 120 150 H 220" stroke="#238636" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#arrow-green)" />
  </g>

  <!-- Kan Extension Mapping -->
  <path d="M 230 150 Q 300 80 370 150" stroke="#58a6ff" stroke-width="3" stroke-dasharray="4 2" />
  <text x="260" y="100" fill="#58a6ff" font-size="14" font-weight="bold">Lan_F(P)</text>
  
  <!-- Discovered Candidate -->
  <circle cx="380" cy="160" r="8" fill="#f0883e" />
  <text x="395" y="165" fill="#f0883e" font-size="12" font-weight="bold">DISCOVERED DRUG</text>

  <!-- Animation Elements (Simulated) -->
  <circle cx="250" cy="150" r="4" fill="#238636"><animate attributeName="cx" from="50" to="250" dur="2s" repeatCount="indefinite" /></circle>
  <circle cx="270" cy="130" r="4" fill="#238636"><animate attributeName="cx" from="50" to="270" dur="2.5s" repeatCount="indefinite" /></circle>

  <defs>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#238636" /></marker>
  </defs>
</svg>
</p>

---

### Technical Deep Dive (LaTeX)

<div class="stream-box">

$$ \text{Streaming\_Lan}_F(t) = \text{colim} \left( \mathcal{C} \downarrow \text{Stream}(t) \xrightarrow{F} \mathcal{D} \right) $$
$$ \mathcal{U}(t) \cong \int^{c \in \mathcal{C}} \text{Hom}(\text{Stream}(t), c) \cdot F(c) $$
*(Continuous categorical interpolation over a living stream of genetic and clinical data)*

</div>
