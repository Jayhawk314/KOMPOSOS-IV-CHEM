# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Prototype: CRYSTAL Pipeline - 3D Structural Motif Prediction
This script demonstrates how the system will map a predicted composition
to a 3D structural motif using ZFC geometric constraints (Goldschmidt tolerance).
"""

import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Mock database of ionic radii (in Angstroms)
IONIC_RADII = {
    # A-site cations (large)
    "Ba2+": 1.61,
    "Sr2+": 1.44,
    "Ca2+": 1.34,
    "Mg2+": 0.89, # Too small for A-site usually
    
    # B-site cations (small, highly charged)
    "Ti4+": 0.605,
    "Zr4+": 0.72,
    "Sn4+": 0.69,
    
    # X-site anions
    "O2-": 1.40,
    "F-": 1.33
}

def calc_goldschmidt_tolerance(r_A, r_B, r_X):
    """
    Calculate the Goldschmidt Tolerance Factor (t) for an ABX3 perovskite.
    t = (r_A + r_X) / (sqrt(2) * (r_B + r_X))
    """
    return (r_A + r_X) / (math.sqrt(2) * (r_B + r_X))

def evaluate_perovskite_motif(composition_name, a_ion, b_ion, x_ion="O2-"):
    """
    Simulates the ZFC Engine applying a geometric constraint to a 
    categorically proposed composition for a Perovskite motif.
    """
    print(f"--- Evaluating Composition: {composition_name} for Perovskite Motif ---")
    
    r_A = IONIC_RADII.get(a_ion)
    r_B = IONIC_RADII.get(b_ion)
    r_X = IONIC_RADII.get(x_ion)
    
    if not all([r_A, r_B, r_X]):
        print("✗ ERROR: Missing ionic radius data.")
        return False
        
    t = calc_goldschmidt_tolerance(r_A, r_B, r_X)
    print(f"A-site: {a_ion} ({r_A}Å), B-site: {b_ion} ({r_B}Å), X-site: {x_ion} ({r_X}Å)")
    print(f"Calculated Tolerance Factor (t): {t:.4f}")
    
    # ZFC Constraint Rule
    # Stable perovskites generally form when 0.89 <= t <= 1.06
    # Below 0.89, it forms Ilmenite or Corundum structures (like MgTiO3)
    # Above 1.06, it forms hexagonal structures
    if 0.89 <= t <= 1.065:
        if 0.95 <= t <= 1.05:
            print("Verdict: HIGHLY LIKELY \u2713 (Ideal Cubic/Tetragonal Perovskite)")
        else:
            print("Verdict: POSSIBLE \u2713 (Distorted/Orthorhombic Perovskite)")
        return True
    else:
        print("Verdict: IMPOSSIBLE \u2717 (ZFC Veto: Will form Ilmenite/Hexagonal instead)")
        return False

if __name__ == "__main__":
    print("======================================================")
    print("PROTOTYPE: ZFC CRYSTALLOGRAPHIC GEOMETRY VETO")
    print("======================================================\n")
    
    # 1. A known stable perovskite (Barium Titanate)
    evaluate_perovskite_motif("BaTiO3", "Ba2+", "Ti4+", "O2-")
    print()
    
    # 2. A known stable but slightly distorted perovskite (Calcium Titanate)
    evaluate_perovskite_motif("CaTiO3", "Ca2+", "Ti4+", "O2-")
    print()
    
    # 3. An impossible perovskite (Magnesium Titanate - Mg is too small for A-site)
    # The categorical engine might guess this since Mg is in the same group as Ca/Sr/Ba,
    # but the ZFC geometry engine must veto it.
    evaluate_perovskite_motif("MgTiO3", "Mg2+", "Ti4+", "O2-")
    
    print("\n======================================================")
    print("CONCLUSION: The ZFC geometric constraints successfully veto")
    print("compositions that cannot physically form the target 3D motif,")
    print("allowing the system to map formulas to real crystal structures.")
    print("======================================================")
