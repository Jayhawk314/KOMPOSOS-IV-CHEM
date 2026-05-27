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
  h1 { color: #f85149; } /* Clinical Urgency Red */
  .shelf {
    fill: #161b22;
    stroke: #30363d;
    stroke-width: 2;
  }
  .drug-dot {
    fill: #58a6ff;
  }
---

# Video 2: Cancer Drug Repurposing
## Scene 1: The Repurposing Crisis (0:00 - 1:30)

### Voiceover Script

"The traditional drug discovery pipeline is broken. It takes 10 years and 2 billion dollars to bring a single new drug to market, while patients are dying today. 

But what if the cure for a rare cancer is already sitting on a pharmacy shelf, approved for a completely different condition?

This is the **Drug Repurposing Crisis**. The data is there, but the connections are missing. In **KOMPOSOS-IV-PHARM**, we don't wait for a decade of trials. We use our categorical engine to find the 'hidden morphisms' between existing drugs and novel diseases. 

Today, we're going to scan the entire pharmacopeia to find a lifeline for a patient with no other options."

---

### Visual Asset: The Repurposing Gap (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Pharmacy Shelf (Massive Data) -->
  <rect x="50" y="50" width="200" height="200" rx="5" class="shelf" />
  <text x="75" y="40" fill="#8b949e" font-size="12">PHARMACOPEIA (Data Library)</text>
  
  <!-- Drug Dots (Grid) -->
  <circle cx="80" cy="80" r="4" class="drug-dot" />
  <circle cx="110" cy="80" r="4" class="drug-dot" />
  <circle cx="140" cy="80" r="4" class="drug-dot" />
  <circle cx="170" cy="80" r="4" class="drug-dot" />
  <circle cx="80" cy="110" r="4" class="drug-dot" />
  <circle cx="110" cy="110" r="4" class="drug-dot" />
  <circle cx="140" cy="110" r="4" class="drug-dot" />
  <circle cx="170" cy="110" r="4" class="drug-dot" />
  <!-- ... more dots -->

  <!-- Unsolved Patient -->
  <circle cx="450" cy="150" r="50" fill="#161b22" stroke="#f85149" stroke-width="3" stroke-dasharray="8 4" />
  <text x="415" y="220" fill="#f85149" font-size="14" font-weight="bold">UNSOLVED PATIENT</text>

  <!-- The Gap (Disconnected paths) -->
  <path d="M 260 100 Q 350 80 400 130" stroke="#30363d" stroke-width="2" stroke-dasharray="4 4" />
  <path d="M 260 150 Q 350 150 400 150" stroke="#30363d" stroke-width="2" stroke-dasharray="4 4" />
  <path d="M 260 200 Q 350 220 400 170" stroke="#30363d" stroke-width="2" stroke-dasharray="4 4" />

  <!-- The Hidden Morphism (Activating) -->
  <path d="M 140 110 Q 300 20 420 120" stroke="#f0883e" stroke-width="4" marker-end="url(#arrow-orange)">
    <animate attributeName="stroke-dashoffset" from="1000" to="0" dur="3s" repeatCount="indefinite" />
  </path>
  <text x="260" y="60" fill="#f0883e" font-size="14" font-weight="bold">HIDDEN MORPHISM</text>

  <defs>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f0883e" /></marker>
  </defs>
</svg>
</p>

---

### Morphism Discovery (LaTeX)

$$ \mathcal{M} = \{ m \in \text{Hom}(\text{Drug}, \text{Target}) \mid \text{Score}(m \circ \text{Patient\_Profile}) > \tau \} $$
$$ \text{Repurpose}(D, P) \cong \text{Find}(f: D \to P) $$
*(Discovery is the identification of a therapeutic morphism $f$ that bridges the gap between an existing drug and a specific patient profile)*
