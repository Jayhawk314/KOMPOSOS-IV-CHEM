# KOMPOSOS-IV-CHEM: The Flory-Huggins Polymer Fix

## 1. Problem Context
During the first clean Q8 External Blind Audit, polymer-polymer blends were one
of the clearest weak spots. A later post-remediation Q8 diagnostic artifact
reported AUROC `0.9038`, but Q8 is now spent and should not be treated as a
fresh blind claim. After integrating the production chi_c model, the spent Q9
diagnostic improved to `87.5%` with AUROC `0.9247`. The useful lesson from
Q8/Q9 is the failure mode: false positives were localized to polymer-polymer
blends such as `ABS + PVDF`, `PA66 + PEO`, and other immiscible blend pairs.

**Why did it fail?**
The current `polymer_bridge` relies on categorical proximity and basic Hansen Solubility Parameter (HSP) distances. While this works for small molecules and polymer-solvent systems, it fails for polymer-polymer blends. Due to the very small entropy of mixing for long polymer chains, two polymers are almost universally immiscible unless their enthalpic interactions are extremely favorable (or essentially identical).

## 2. Mathematical Solution: Flory-Huggins Theory
To fix this, the system must implement the rigorous thermodynamic threshold for polymer miscibility: the **Critical Chi Parameter ($\chi_c$)**.

### 2.1 The Flory-Huggins Interaction Parameter ($\chi$)
Calculated from the Hildebrand or Hansen Solubility Parameters of the two polymers, scaled by a reference molar volume ($V_r$) and thermal energy ($RT$):

$$ \chi_{12} = \frac{V_r}{RT} \left( (\delta_{d1} - \delta_{d2})^2 + 0.25(\delta_{p1} - \delta_{p2})^2 + 0.25(\delta_{h1} - \delta_{h2})^2 \right) $$

*(Note: The empirical pre-factors 0.25 are standard for HSP-derived $\chi$ calculations).*

### 2.2 The Critical Threshold ($\chi_c$)
The threshold for phase separation depends entirely on the Degree of Polymerization ($N$) of the two components.

$$ \chi_c = \frac{1}{2} \left( \frac{1}{\sqrt{N_1}} + \frac{1}{\sqrt{N_2}} \right)^2 $$

Where $N = \frac{MW_{polymer}}{MW_{monomer}}$.

**The Rule:**
- If $\chi < \chi_c$: The blend is miscible (Compatible).
- If $\chi > \chi_c$: The blend undergoes phase separation (Incompatible).

Because $N$ for polymers is typically very large (e.g., $10^3$ to $10^5$), $\chi_c$ approaches zero. This enforces the physical reality that polymers almost never mix.

## 3. Integration Design (Future Roadmap)
When this is implemented into the active KOMPOSOS system, it should take the form of a **ZFC Veto Constraint**.

1. **`polymer_bridge/material_properties.py`**: Must be updated to include $MW$ (Molecular Weight) and $m_0$ (Monomer Weight) for all polymer objects.
2. **`zfc/proof_engine.py`**: Add a `PolymerMiscibilityConstraint`.
3. **Execution**: If the Categorical Engine suggests two polymers are compatible (due to structural homology or Kan Extensions), the ZFC engine will intercept. It will compute $\chi$ and $\chi_c$. If $\chi > \chi_c$, the ZFC engine will issue a **REJECT** verdict with the reason: `Thermodynamic phase separation predicted: chi > chi_c`.

This guarantees physical grounding overrides categorical hallucination.

### 3.1 Empirical interaction safeguard

HSP-derived chi is not enough by itself. Some known miscible pairs, such as
`PS + PPO`, rely on favorable specific interactions that can make the effective
chi negative. The active constraint must check a cited empirical chi table
before falling back to HSP estimation; otherwise the veto will create false
negatives for known miscible blends.

The prototype in `G-docs/tests/prototype_polymer_chi.py` now includes this
empirical override path.

---
*G-docs Design Document | 2026-05-29*
