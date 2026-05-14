#!/usr/bin/env python3
"""
Demonstration: Bioorthogonal Stability Filtering

Shows how Boltz2Bridge catches drugs with unstable reactive groups
that won't survive to reach their target.

This addresses: "Models hallucinate binding poses for molecules that
can't physically reach the binding site because their reactive groups
got hydrolyzed in the lysosome."
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from boltz2_bridge import Boltz2Bridge, BioorthogonalWarhead

print("=" * 80)
print("BIOORTHOGONAL STABILITY FILTERING")
print("=" * 80)

boltz = Boltz2Bridge()

# Test drugs with different warhead types
test_drugs = [
    ("Azide-Erlotinib", "azide"),        # Stable
    ("Tetrazine-Gefitinib", "tetrazine"), # UNSTABLE - fails in lysosome
    ("TCO-Lapatinib", "tco"),             # Stable
    ("Alkyne-Imatinib", "alkyne"),        # Moderate
    ("Erlotinib", "none"),                # No warhead - stable
]

print("\n[1] Stability Analysis:")
print("-" * 80)

for drug, expected_type in test_drugs:
    stability = boltz.check_bioorthogonal_stability(drug)

    print(f"\n{drug}:")
    print(f"  Warhead: {stability.warhead.value}")
    print(f"  Survives lysosome (pH 4.5): {stability.survives_lysosome}")
    print(f"  Survives nucleophiles (GSH): {stability.survives_nucleophiles}")
    print(f"  Survives oxidation: {stability.survives_oxidation}")
    print(f"  Plasma half-life: {stability.plasma_half_life_hours:.1f} hours")
    print(f"  Overall stability: {stability.overall_stability:.2f}")
    print(f"  Stable enough? {stability.is_stable()}")

    if len(stability.failure_modes) > 0:
        print(f"  [WARNING] Failure modes: {', '.join(stability.failure_modes)}")

print("\n\n[2] Impact on Oracle Predictions:")
print("-" * 80)

# Simulate oracle predictions for EGFR
protein = "EGFR"
oracle_confidence = 0.85  # High categorical confidence

print(f"\nTarget: {protein}")
print(f"Oracle base confidence: {oracle_confidence:.3f}")
print()

for drug, _ in test_drugs:
    # Enhance with Boltz-2 + stability check
    enhanced, binding = boltz.enhance_oracle_prediction(drug, protein, oracle_confidence)
    stability = boltz.check_bioorthogonal_stability(drug)

    delta = enhanced - oracle_confidence
    direction = "BOOST" if delta > 0 else "PENALTY"

    print(f"{drug}:")
    print(f"  Binding score: {binding.binding_score:.3f}")
    print(f"  Warhead stability: {stability.overall_stability:.2f}")
    print(f"  Enhanced confidence: {enhanced:.3f} ({direction} {abs(delta):.3f})")

    if not stability.is_stable():
        print(f"  [REJECTED] Unstable warhead: {', '.join(stability.failure_modes)}")
    print()

print("\n" + "=" * 80)
print("KEY INSIGHT:")
print("=" * 80)
print()
print("Tetrazine-Gefitinib shows HIGH binding score but gets REJECTED because")
print("tetrazines are hydrolyzed at lysosomal pH (4.5-5.0).")
print()
print("Structure prediction says 'this binds' but chemistry says 'it never")
print("reaches the binding site intact'.")
print()
print("This gap is now closed by bioorthogonal stability filtering.")
print("=" * 80)
