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
  .tier-label { font-weight: bold; font-size: 14px; }
  .tier-desc { font-size: 12px; color: #8b949e; }
---

# The COG Co-processor
## 5 Tiers of Cognitive Audit

### Voiceover Script

"Inside KOMPOSOS-IV lives the **COG Engine**—the cognitive co-processor that audits the runtime. It doesn't just run one check; it verifies every claim through <span class="highlight">five increasing tiers of rigor</span>.

Tier 0 is a simple graph lookup.
Tier 1 and 2 check path composition and **Sheaf Coherence**—ensuring local interactions match the global knowledge graph.
Tier 3 brings in the **ZFC Dual-Engine** for set-theoretic witnesses.
And Tier 4? This is the high-stakes layer. It uses **Ricci Flow** to detect knowledge bottlenecks and **Persistent Homology** to find voids in our chemical understanding. 

It’s defense-in-depth for materials science."

---

### Visual Asset: The Cognitive Stack (Inline SVG)

<p align="center">
<svg width="500" height="300" viewBox="0 0 500 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Tier 4: Topology -->
  <path d="M 100 60 L 400 60 L 380 20 L 120 20 Z" fill="#bc8cff" fill-opacity="0.3" stroke="#bc8cff" stroke-width="2" />
  <text x="210" y="45" fill="#bc8cff" font-size="12" font-weight="bold">TIER 4: TOPOLOGY</text>

  <!-- Tier 3: ZFC Logic -->
  <path d="M 80 110 L 420 110 L 400 70 L 100 70 Z" fill="#58a6ff" fill-opacity="0.3" stroke="#58a6ff" stroke-width="2" />
  <text x="210" y="95" fill="#58a6ff" font-size="12" font-weight="bold">TIER 3: ZFC LOGIC</text>

  <!-- Tier 2: Sheaf/Kan -->
  <path d="M 60 160 L 440 160 L 420 120 L 80 120 Z" fill="#1f6feb" fill-opacity="0.3" stroke="#1f6feb" stroke-width="2" />
  <text x="210" y="145" fill="#1f6feb" font-size="12" font-weight="bold">TIER 2: COHERENCE</text>

  <!-- Tier 1: Composition -->
  <path d="M 40 210 L 460 210 L 440 170 L 60 170 Z" fill="#238636" fill-opacity="0.3" stroke="#238636" stroke-width="2" />
  <text x="200" y="195" fill="#238636" font-size="12" font-weight="bold">TIER 1: COMPOSITION</text>

  <!-- Tier 0: Graph -->
  <path d="M 20 260 L 480 260 L 460 220 L 40 220 Z" fill="#30363d" fill-opacity="0.3" stroke="#30363d" stroke-width="2" />
  <text x="210" y="245" fill="#c9d1d9" font-size="12" font-weight="bold">TIER 0: LOOKUP</text>
  
  <!-- The Coherence Signal -->
  <path d="M 250 260 V 60" stroke="#f0883e" stroke-width="2" stroke-dasharray="4 4" />
  <circle cx="250" cy="40" r="5" fill="#f0883e">
    <animate attributeName="opacity" values="0;1;0" dur="1s" repeatCount="indefinite" />
  </circle>
</svg>
</p>

---

### Technical Coherence (LaTeX)

$$ \mathcal{F}(U) \cong \text{Eq}\left( \prod_i \mathcal{F}(U_i) \rightrightarrows \prod_{i,j} \mathcal{F}(U_i \cap U_j) \right) $$
*(The Sheaf Condition: Local interactions must glue together into a unique global interaction without contradiction)*
