---
marp: true
theme: gaia
invert: true
style: |
  section {
    background-color: #0d1117;
    color: #c9d1d9;
  }
  h1 { color: #f85149; } /* Red for urgency */
  .countdown {
    font-family: 'Courier New', monospace;
    font-size: 40px;
    color: #f85149;
    text-shadow: 0 0 10px #f85149;
  }
---

# Video 2: High-Stakes Risk
## Scene 1: The Regulatory Ticking Clock (0:00 - 1:30)

### Voiceover Script

"By August 2026, the industrial world changes forever. 

Per- and polyfluoroalkyl substances—**PFAS**—are being banned across the EU and the US. These 'Forever Chemicals' are in everything: your gaskets, your seals, and critically, the PVDF binders holding your battery cathodes together. 

For manufacturers, this isn't just a compliance hurdle; it's an existential risk. If you can't replace these chemicals without losing performance, your entire product line dies. 

Today, we're going to use the **KOMPOSOS-IV** categorical runtime to find the escape path."

---

### Visual Asset: The 2026 Ticking Clock (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Timeline Base -->
  <line x1="50" y1="200" x2="550" y2="200" stroke="#30363d" stroke-width="4" />
  
  <!-- Milestones -->
  <circle cx="100" cy="200" r="8" fill="#58a6ff" />
  <text x="70" y="230" fill="#58a6ff" font-size="12">Today (2026)</text>
  
  <circle cx="300" cy="200" r="8" fill="#f0883e" />
  <text x="260" y="230" fill="#f0883e" font-size="12">EU PFHxA Ban (Aug)</text>
  
  <circle cx="500" cy="200" r="10" fill="#f85149" />
  <text x="460" y="230" fill="#f85149" font-size="12" font-weight="bold">TOTAL PROHIBITION</text>

  <!-- The Ticking Arc -->
  <path d="M 300 150 A 50 50 0 1 1 300 50 A 50 50 0 1 1 300 150" stroke="#f85149" stroke-width="2" stroke-dasharray="10 5" />
  <line x1="300" y1="100" x2="330" y2="70" stroke="#f85149" stroke-width="3" marker-end="url(#arrow)" />
  
  <text x="360" y="105" fill="#f85149" font-size="28" font-weight="bold" class="countdown">AUGUST 2026</text>

  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f85149" />
    </marker>
  </defs>
</svg>
</p>

---

### Mathematical Core: Risk Quantale (LaTeX)

$$ \mathcal{R}(t) = \bigoplus_{c \in \text{BOM}} \text{PFAS\_Detect}(c) \otimes \text{Urgency}(c, t) $$
*(Mapping each component in the Bill of Materials to a temporal risk category)*
