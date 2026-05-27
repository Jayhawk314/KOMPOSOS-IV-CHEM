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
  .replacement { color: #238636; font-weight: bold; }
  .banned { color: #f85149; text-decoration: line-through; }
---

# Inverse Design to the Rescue
## Solving the Performance vs. Compliance Game

### Voiceover Script

"Finding a replacement isn't just about deleting a row in a spreadsheet. It’s a multi-objective optimization game. 

We need a material that is PFAS-free, but also maintains adhesion, electrochemical stability, and cost-efficiency. This is where **Crystal Dreamer** and the **OPTIMUS** engine take over. 

We define our target properties and let the system search for a **Nash Equilibrium**. 

The result? A transition from the <span class="banned">Banned PVDF</span> to a <span class="replacement">CMC+SBR Water-Based Binder</span>. It scores a 0.84 on performance and a 1.0 on compliance. We haven't just solved a regulation; we've optimized our design."

---

### Visual Asset: The Optimization Trade-off (Inline SVG)

<p align="center">
<svg width="600" height="320" viewBox="0 0 600 320" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Radar Chart Base -->
  <path d="M 300 50 L 500 150 L 400 280 L 200 280 L 100 150 Z" stroke="#30363d" stroke-width="2" fill="#161b22" />
  
  <!-- Axis Labels -->
  <text x="280" y="40" fill="#8b949e" font-size="10">Compliance (PFAS-Free)</text>
  <text x="510" y="155" fill="#8b949e" font-size="10">Adhesion</text>
  <text x="410" y="295" fill="#8b949e" font-size="10">Voltage Stability</text>
  <text x="140" y="295" fill="#8b949e" font-size="10">Process Cost</text>
  <text x="40" y="155" fill="#8b949e" font-size="10">Conductivity</text>

  <!-- PVDF Profile (Banned) -->
  <path d="M 300 150 L 480 160 L 380 260 L 250 250 L 150 160 Z" stroke="#f85149" stroke-width="2" fill="rgba(248, 81, 73, 0.2)" />
  <text x="180" y="210" fill="#f85149" font-size="12" font-weight="bold">PVDF (FAILURE)</text>

  <!-- CMC+SBR Profile (Selected) -->
  <path d="M 300 60 L 460 170 L 350 240 L 220 260 L 250 180 Z" stroke="#238636" stroke-width="3" fill="rgba(35, 134, 54, 0.3)" />
  <text x="320" y="90" fill="#238636" font-size="12" font-weight="bold">CMC+SBR (OPTIMAL)</text>

  <!-- Optimization Marker -->
  <circle cx="300" cy="150" r="5" fill="#58a6ff">
    <animate attributeName="r" values="5;8;5" dur="2s" repeatCount="indefinite" />
  </circle>
</svg>
</p>

---

### Mathematical Optimization: Nash Equilibrium (LaTeX)

$$ \theta^* = \arg \max_{\theta \in \mathcal{C}} \left( \text{Perf}(\theta) \times \text{Compliance}(\theta) \times \text{Cost}^{-1}(\theta) \right) $$
$$ \forall i, \mathcal{U}_i(\theta^*) \ge \mathcal{U}_i(\theta_i, \theta^*_{-i}) $$
*(The chosen material $\theta^*$ is the equilibrium point where no single property can be improved without violating the compliance veto)*
