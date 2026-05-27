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
  h2 { color: #bc8cff; border-bottom: 2px solid #bc8cff; }
  .box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 15px;
  }
---

# The Drug-Disease Morphism
## Treatment as Categorical Transformation

### Voiceover Script

"Once we have the Patient Object, we can reason about the Cure. In **KOMPOSOS-IV-PHARM**, a Drug is not just a chemical; it is a **Morphism**.

It represents a transformation from a 'diseased' state to a 'healthy' state. 

We aren't just looking for molecules that kill cancer cells; we are looking for morphisms that restore the integrity of the patient's biological category. 

Because interactions are compositional, we can even model **Combination Therapies**. Composing two drugs—Drug A and Drug B—creates a new therapeutic path that neither could achieve alone. This is clinical reasoning as a mathematical proof."

---

### Visual Asset: Therapeutic Transformation (Inline SVG)

<p align="center">
<svg width="600" height="300" viewBox="0 0 600 300" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Diseased State -->
  <circle cx="100" cy="150" r="40" fill="#161b22" stroke="#f85149" stroke-width="2" />
  <path d="M 80 130 L 120 170 M 120 130 L 80 170" stroke="#f85149" stroke-width="2" />
  <text x="60" y="210" fill="#f85149" font-size="12" font-weight="bold">DISEASED STATE (P_d)</text>

  <!-- Healthy State -->
  <circle cx="500" cy="150" r="40" fill="#161b22" stroke="#238636" stroke-width="2" />
  <path d="M 490 150 L 497 160 L 510 140" stroke="#238636" stroke-width="3" />
  <text x="460" y="210" fill="#238636" font-size="12" font-weight="bold">HEALTHY STATE (P_h)</text>

  <!-- Drug Morphism f -->
  <path d="M 150 130 Q 300 50 450 130" stroke="#bc8cff" stroke-width="4" marker-end="url(#arrow-purple)" />
  <text x="280" y="70" fill="#bc8cff" font-size="16" font-weight="bold">Drug Morphism (f)</text>

  <!-- Combination Path (Drug A -> Intermediate -> Drug B) -->
  <circle cx="300" cy="220" r="10" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
  <path d="M 140 170 L 280 210" stroke="#58a6ff" stroke-width="2" stroke-dasharray="4 2" marker-end="url(#arrow-blue)" />
  <path d="M 320 210 L 460 170" stroke="#58a6ff" stroke-width="2" stroke-dasharray="4 2" marker-end="url(#arrow-blue)" />
  <text x="250" y="260" fill="#58a6ff" font-size="14">A ∘ B (Combination)</text>

  <defs>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#bc8cff" /></marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" /></marker>
  </defs>
</svg>
</p>

---

### Mathematical Treatment (LaTeX)

<div class="box">

$$ f : P_{\text{diseased}} \to P_{\text{healthy}} \in \text{Morphisms}(\text{Pharm}) $$
$$ (g \circ f)(P) = g(f(P)) $$
*(Proving that combination therapy $g \circ f$ is a valid logical derivation in the clinical category)*

</div>
