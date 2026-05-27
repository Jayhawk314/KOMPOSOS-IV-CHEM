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
  h1 { color: #bc8cff; }
  .shield-box {
    background: #161b22;
    border: 2px solid #f85149;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 0 15px rgba(248, 81, 73, 0.1);
  }
---

# Gray Coherence & The Patient Guard
## The Engine's Clinical Immune System

### Voiceover Script

"Beyond tiered verification, the clinical runtime is shielded by three specialized protection layers that function as a mathematical immune system.

First, **Gray Coherence** ensures that the order of treatment operations—like the sequence of surgery and chemotherapy—results in a logically consistent outcome. 
Second, the **Patient Guard** uses fully faithful Yoneda embedding to transfer evidence between similar clinical profiles without losing the unique precision of the individual. 
And finally, our **Clinical Failure-Memory Gates** act as a cognitive record, remembering every past logical miss and preventing the engine from ever repeating the same reasoning errors for future patients.

We’ve built a system that doesn't just reason—it remembers, protects, and evolves."

---

### Visual Asset: Triple-Shield Clinical Protection (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Outer Shield: Gray Coherence -->
  <path d="M 300 20 L 500 80 V 220 L 300 280 L 100 220 V 80 Z" fill="#bc8cff" fill-opacity="0.1" stroke="#bc8cff" stroke-width="4" stroke-dasharray="10 5" />
  <text x="300" y="270" text-anchor="middle" fill="#bc8cff" font-size="12" font-weight="bold">GRAY COHERENCE (SEQUENCE INVARIANCE)</text>

  <!-- Middle Shield: Patient Guard -->
  <path d="M 300 50 L 450 100 V 200 L 300 250 L 150 200 V 100 Z" fill="#f85149" fill-opacity="0.1" stroke="#f85149" stroke-width="3" />
  <text x="300" y="240" text-anchor="middle" fill="#f85149" font-size="12" font-weight="bold">PATIENT GUARD (PROFILE TRANSFER)</text>

  <!-- Inner Core: Failure Memory -->
  <path d="M 300 80 L 400 120 V 180 L 300 220 L 200 180 V 120 Z" fill="#f0883e" fill-opacity="0.1" stroke="#f0883e" stroke-width="2" />
  <text x="300" y="210" text-anchor="middle" fill="#f0883e" font-size="12" font-weight="bold">FAILURE MEMORY (RECURRENCE PREVENTION)</text>

  <!-- Clinical Data Flow -->
  <path d="M 50 150 H 200" stroke="#c9d1d9" stroke-width="2" stroke-dasharray="4 2" marker-end="url(#arrow)" />
  <text x="50" y="140" fill="#c9d1d9" font-size="10">PATIENT CLAIM</text>

  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#c9d1d9" />
    </marker>
  </defs>
</svg>
</p>

---

### Patient Integrity (LaTeX)

<div class="shield-box">

$$ y_{\text{pharm}} : \mathcal{P} \hookrightarrow [\mathcal{P}^{op}, \text{Set}] $$
$$ P \mapsto \text{Hom}(-, P) $$
*(Patient Yoneda Embedding: A patient is uniquely defined by the totality of their biological and clinical relationships)*

</div>
