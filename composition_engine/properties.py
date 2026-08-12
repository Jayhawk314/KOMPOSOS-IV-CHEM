# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Rule-Based Property Estimation

Estimates material properties from chemical composition using established
physical chemistry rules (Faraday's law, Vegard's law, electronegativity
correlations). These serve as one evidence source for Dempster-Shafer
fusion with Kan extension predictions.

Each property estimate includes a confidence value reflecting how
applicable the rule is to the given composition.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from .parser import (
    parse_formula, molar_mass, average_electronegativity,
    metal_fraction, ELEMENT_TABLE, SHORTHAND_MAP,
)

# Faraday constant (C/mol)
FARADAY = 96485.0


@dataclass
class PropertyEstimate:
    """A single property estimate with internal confidence and evidence."""
    value: float
    confidence: float   # 0-1 internal source confidence, not empirical coverage
    method: str         # Which rule or interpolation produced it
    evidence: Dict[str, object] = field(default_factory=dict)


@dataclass
class EstimatedProperties:
    """Collection of estimated properties for a composition."""
    formula: str
    properties: Dict[str, PropertyEstimate] = field(default_factory=dict)

    def get(self, name: str) -> Optional[PropertyEstimate]:
        return self.properties.get(name)

    def to_dict(self) -> Dict:
        return {
            "formula": self.formula,
            "properties": {
                k: {"value": v.value, "confidence": v.confidence, "method": v.method}
                for k, v in self.properties.items()
            },
        }


# ── Known end-member voltages for interpolation ────────────────────────────

# Voltage vs Li/Li+ for binary layered oxides LiMO2
END_MEMBER_VOLTAGES: Dict[str, float] = {
    "Ni": 3.85,   # LiNiO2 avg discharge ~3.85V (Dahn et al.)
    "Mn": 3.95,   # LiMnO2 layered ~3.95V (but unstable)
    "Co": 3.90,   # LiCoO2 avg ~3.9V (Goodenough 1980)
    "Al": 4.50,   # Al doesn't cycle -- raises voltage via inductive effect
    "Fe": 3.40,   # LiFeO2 / LiFePO4 ~3.4V (olivine benchmark)
}

# Specific capacity of end-member LiMO2 (mAh/g, theoretical 1-electron)
END_MEMBER_CAPACITY: Dict[str, float] = {
    "Ni": 275.0,   # LiNiO2
    "Mn": 285.0,   # LiMnO2 layered
    "Co": 274.0,   # LiCoO2
}

# Thermal stability reference (onset temp in C for O2 release)
END_MEMBER_THERMAL: Dict[str, float] = {
    "Ni": 160.0,   # High Ni -> low thermal stability
    "Mn": 300.0,   # Mn stabilizes structure
    "Co": 200.0,   # Moderate
    "Al": 280.0,   # Al doping improves thermal stability
    "Fe": 400.0,   # Olivine Fe very stable
}

# Volume expansion per TM in NMC family (fraction)
END_MEMBER_EXPANSION: Dict[str, float] = {
    "Ni": 0.06,    # High Ni -> more H2-H3 phase transition strain
    "Mn": 0.02,    # Mn is structurally stabilizing
    "Co": 0.03,    # Moderate
}


def estimate_properties(formula: str) -> EstimatedProperties:
    """
    Estimate material properties from chemical formula.

    Uses:
    - Faraday's law for theoretical capacity
    - Weighted end-member interpolation for voltage (Vegard's-like)
    - Electronegativity correlation for voltage correction
    - Empirical TM-content correlations for thermal/expansion
    """
    resolved = SHORTHAND_MAP.get(formula, formula)
    comp = parse_formula(resolved)
    result = EstimatedProperties(formula=formula)

    if not comp:
        return result

    # Detect if this is a layered oxide cathode (Li + TMs + O)
    is_layered_cathode = ("Li" in comp and "O" in comp and
                          any(m in comp for m in ["Ni", "Mn", "Co"]))
    is_olivine = ("Li" in comp and "Fe" in comp and
                  "P" in comp and "O" in comp)
    is_spinel = ("Li" in comp and "Mn" in comp and
                 "O" in comp and comp.get("Mn", 0) > 1.0)

    # ── Molar mass ──────────────────────────────────────────────────────
    mm = molar_mass(comp)
    if mm > 0:
        result.properties["molar_mass"] = PropertyEstimate(
            value=mm, confidence=0.99, method="exact_calculation"
        )

    # ── Average electronegativity ───────────────────────────────────────
    avg_en = average_electronegativity(comp)
    if avg_en > 0:
        result.properties["avg_electronegativity"] = PropertyEstimate(
            value=avg_en, confidence=0.95, method="pauling_weighted_avg"
        )

    # ── Theoretical capacity (Faraday's law) ────────────────────────────
    if is_layered_cathode and mm > 0:
        # For layered LiTMO2: 1 electron per formula unit
        # Q = nF / (3.6 * M)  [mAh/g, n=1 for Li intercalation]
        n_electrons = 1.0
        capacity = n_electrons * FARADAY / (3.6 * mm)
        result.properties["theoretical_capacity"] = PropertyEstimate(
            value=capacity, confidence=0.85, method="faraday_law"
        )

        # Also estimate via end-member interpolation
        tm_frac = metal_fraction(comp, ["Ni", "Mn", "Co"])
        if tm_frac:
            cap_interp = sum(
                END_MEMBER_CAPACITY.get(m, 275.0) * f
                for m, f in tm_frac.items()
            )
            # Average of Faraday and interpolation
            avg_cap = (capacity + cap_interp) / 2.0
            result.properties["theoretical_capacity"] = PropertyEstimate(
                value=avg_cap, confidence=0.88, method="faraday_plus_interpolation"
            )

    elif is_olivine and mm > 0:
        capacity = FARADAY / (3.6 * mm)
        result.properties["theoretical_capacity"] = PropertyEstimate(
            value=capacity, confidence=0.90, method="faraday_law_olivine"
        )

    elif is_spinel and mm > 0:
        capacity = FARADAY / (3.6 * mm)
        result.properties["theoretical_capacity"] = PropertyEstimate(
            value=capacity, confidence=0.85, method="faraday_law_spinel"
        )

    # ── Voltage (end-member interpolation + EN correction) ──────────────
    if is_layered_cathode:
        tm_frac = metal_fraction(comp, ["Ni", "Mn", "Co", "Al"])
        if tm_frac:
            # Vegard's-law-like interpolation over end-member voltages
            voltage = sum(
                END_MEMBER_VOLTAGES.get(m, 3.8) * f
                for m, f in tm_frac.items()
            )

            # Electronegativity correction: higher average EN -> slightly
            # higher voltage (inductive effect, Padhi & Goodenough)
            en_correction = (avg_en - 2.0) * 0.05  # Small correction
            voltage += en_correction

            result.properties["voltage"] = PropertyEstimate(
                value=voltage, confidence=0.80, method="end_member_interpolation"
            )

    elif is_olivine:
        result.properties["voltage"] = PropertyEstimate(
            value=3.4, confidence=0.90, method="olivine_reference"
        )

    elif is_spinel:
        ni_content = comp.get("Ni", 0)
        if ni_content > 0:
            # LNMO high-voltage spinel
            result.properties["voltage"] = PropertyEstimate(
                value=4.7, confidence=0.85, method="high_voltage_spinel"
            )
        else:
            result.properties["voltage"] = PropertyEstimate(
                value=4.1, confidence=0.85, method="spinel_reference"
            )

    # ── Density estimate ────────────────────────────────────────────────
    if is_layered_cathode:
        # Layered oxide densities scale with average atomic mass
        # Empirical: density ~ 4.5 + 0.3*(Ni_frac - 0.33)
        ni_frac = comp.get("Ni", 0.33)
        total_tm = sum(comp.get(m, 0) for m in ["Ni", "Mn", "Co", "Al"])
        if total_tm > 0:
            ni_frac_norm = comp.get("Ni", 0) / total_tm
        else:
            ni_frac_norm = 0.33
        density = 4.70 + 0.3 * (ni_frac_norm - 0.33)
        result.properties["density"] = PropertyEstimate(
            value=density, confidence=0.70, method="empirical_nm_correlation"
        )

    # ── Thermal stability ───────────────────────────────────────────────
    if is_layered_cathode:
        tm_frac = metal_fraction(comp, ["Ni", "Mn", "Co", "Al", "Fe"])
        if tm_frac:
            thermal = sum(
                END_MEMBER_THERMAL.get(m, 200.0) * f
                for m, f in tm_frac.items()
            )
            result.properties["thermal_stability"] = PropertyEstimate(
                value=thermal, confidence=0.75, method="end_member_interpolation"
            )

    elif is_olivine:
        result.properties["thermal_stability"] = PropertyEstimate(
            value=400.0, confidence=0.85, method="olivine_reference"
        )

    # ── Volume expansion ────────────────────────────────────────────────
    if is_layered_cathode:
        tm_frac = metal_fraction(comp, ["Ni", "Mn", "Co"])
        if tm_frac:
            expansion = sum(
                END_MEMBER_EXPANSION.get(m, 0.03) * f
                for m, f in tm_frac.items()
            )
            result.properties["volume_expansion"] = PropertyEstimate(
                value=expansion, confidence=0.72, method="tm_fraction_correlation"
            )

    return result


if __name__ == "__main__":
    formulas = [
        "NMC811", "NMC622", "NMC111", "NMC532", "NMC721",
        "LCO", "LFP", "LMO", "NCA",
    ]
    for f in formulas:
        est = estimate_properties(f)
        print(f"\n{f}:")
        for name, prop in est.properties.items():
            print(f"  {name:25s} = {prop.value:8.2f}  (conf={prop.confidence:.2f}, {prop.method})")
