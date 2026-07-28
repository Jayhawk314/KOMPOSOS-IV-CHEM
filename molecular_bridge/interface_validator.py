# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular Interface Validator
================================

Validates molecular interaction viability between two molecules,
following the exact pattern of battery_bridge/interface_validator.py.

Pattern:
  Battery bridge:   "Can material A interface with material B?"
  Molecular bridge: "Can molecule A interact safely with molecule B?"

The validator combines all five interaction scorers into a weighted
composite MolecularInterfaceScore.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from molecular_bridge.molecule_properties import Molecule, get_molecule
from molecular_bridge.interaction_scoring import (
    score_electronic_compatibility,
    score_thermodynamic_stability,
    score_steric_compatibility,
    score_solubility_compatibility,
    score_reactivity_risk,
    ScorerResult,
)


@dataclass
class MolecularInterfaceScore:
    """
    Composite molecular interaction score with component breakdown.

    Mirrors battery_bridge.interface_validator.InterfaceScore.
    """
    total: float
    electronic_compatibility: float
    thermodynamic_stability: float
    steric_compatibility: float
    solubility_compatibility: float
    reactivity_risk: float
    viable: bool
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 4),
            'electronic_compatibility': round(self.electronic_compatibility, 4),
            'thermodynamic_stability': round(self.thermodynamic_stability, 4),
            'steric_compatibility': round(self.steric_compatibility, 4),
            'solubility_compatibility': round(self.solubility_compatibility, 4),
            'reactivity_risk': round(self.reactivity_risk, 4),
            'viable': self.viable,
        }


@dataclass
class MolecularWeights:
    """Configurable weights for the five scoring components."""
    electronic_compatibility: float = 0.20
    thermodynamic_stability: float = 0.20
    steric_compatibility: float = 0.15
    solubility_compatibility: float = 0.20
    reactivity_risk: float = 0.25

    def validate(self):
        total = (self.electronic_compatibility + self.thermodynamic_stability +
                 self.steric_compatibility + self.solubility_compatibility +
                 self.reactivity_risk)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.3f}")

    @classmethod
    def default(cls) -> 'MolecularWeights':
        return cls()

    @classmethod
    def safety_focus(cls) -> 'MolecularWeights':
        """Weights emphasizing reactivity risk."""
        return cls(
            electronic_compatibility=0.15,
            thermodynamic_stability=0.15,
            steric_compatibility=0.10,
            solubility_compatibility=0.15,
            reactivity_risk=0.45,
        )

    @classmethod
    def solubility_focus(cls) -> 'MolecularWeights':
        """Weights emphasizing solubility/mixing."""
        return cls(
            electronic_compatibility=0.15,
            thermodynamic_stability=0.20,
            steric_compatibility=0.10,
            solubility_compatibility=0.35,
            reactivity_risk=0.20,
        )


class MolecularInterfaceValidator:
    """
    Validates molecular interaction viability.

    Usage:
        validator = MolecularInterfaceValidator()
        result = validator.validate('EC', 'DMC')
        print(f"Viable: {result.viable}, Score: {result.total:.2f}")
    """

    def __init__(
        self,
        weights: Optional[MolecularWeights] = None,
        viability_threshold: float = 0.50,
    ):
        self.weights = weights or MolecularWeights.default()
        self.weights.validate()
        self.viability_threshold = viability_threshold

    def validate(
        self,
        molecule_a: str,
        molecule_b: str,
    ) -> MolecularInterfaceScore:
        """
        Validate interaction between two molecules by name.

        Args:
            molecule_a: Name of first molecule
            molecule_b: Name of second molecule

        Returns:
            MolecularInterfaceScore with component breakdown

        Raises:
            ValueError: If molecule name not found
        """
        mol_a = get_molecule(molecule_a)
        mol_b = get_molecule(molecule_b)
        if mol_a is None:
            raise ValueError(f"Unknown molecule: '{molecule_a}'")
        if mol_b is None:
            raise ValueError(f"Unknown molecule: '{molecule_b}'")

        return self.validate_molecules(mol_a, mol_b)

    def validate_molecules(
        self,
        mol_a: Molecule,
        mol_b: Molecule,
    ) -> MolecularInterfaceScore:
        """
        Validate interaction between two Molecule objects.

        Args:
            mol_a: First molecule
            mol_b: Second molecule

        Returns:
            MolecularInterfaceScore with full breakdown
        """
        s_elec = score_electronic_compatibility(mol_a, mol_b)
        s_thermo = score_thermodynamic_stability(mol_a, mol_b)
        s_steric = score_steric_compatibility(mol_a, mol_b)
        s_sol = score_solubility_compatibility(mol_a, mol_b)
        s_react = score_reactivity_risk(mol_a, mol_b)

        scores = {
            'electronic_compatibility': s_elec.score,
            'thermodynamic_stability': s_thermo.score,
            'steric_compatibility': s_steric.score,
            'solubility_compatibility': s_sol.score,
            'reactivity_risk': s_react.score,
        }

        total = (
            self.weights.electronic_compatibility * scores['electronic_compatibility'] +
            self.weights.thermodynamic_stability * scores['thermodynamic_stability'] +
            self.weights.steric_compatibility * scores['steric_compatibility'] +
            self.weights.solubility_compatibility * scores['solubility_compatibility'] +
            self.weights.reactivity_risk * scores['reactivity_risk']
        )

        details = {
            'electronic_details': s_elec.details,
            'thermodynamic_details': s_thermo.details,
            'steric_details': s_steric.details,
            'solubility_details': s_sol.details,
            'reactivity_details': s_react.details,
            'molecule_a': mol_a.name,
            'molecule_b': mol_b.name,
        }

        return MolecularInterfaceScore(
            total=total,
            electronic_compatibility=scores['electronic_compatibility'],
            thermodynamic_stability=scores['thermodynamic_stability'],
            steric_compatibility=scores['steric_compatibility'],
            solubility_compatibility=scores['solubility_compatibility'],
            reactivity_risk=scores['reactivity_risk'],
            viable=total >= self.viability_threshold,
            details=details,
        )

    def validate_all_interfaces(
        self,
        molecules: List[str],
    ) -> Dict[Tuple[str, str], MolecularInterfaceScore]:
        """Validate all pairwise interfaces in a set of molecules."""
        results = {}
        for i in range(len(molecules)):
            for j in range(i + 1, len(molecules)):
                key = (molecules[i], molecules[j])
                try:
                    results[key] = self.validate(molecules[i], molecules[j])
                except ValueError:
                    pass
        return results


def validate_interface(
    molecule_a: str,
    molecule_b: str,
) -> MolecularInterfaceScore:
    """Convenience function for quick molecular interface validation."""
    validator = MolecularInterfaceValidator()
    return validator.validate(molecule_a, molecule_b)
