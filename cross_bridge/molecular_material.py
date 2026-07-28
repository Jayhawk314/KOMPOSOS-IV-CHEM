# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Molecular-Material Cross-Bridge Functor
=========================================

Multi-scale reasoning: molecule -> material -> device.

This is the functor F: Mol -> Mat that maps molecular-level properties
(individual solvents, salts, monomers) into material-level compatibility
checks (battery electrode-electrolyte interfaces).

Key cross-scale questions answered:
- Will this electrolyte solvent (molecule) work with this cathode (material)?
- Is this salt anion compatible with this electrode's voltage window?
- Can this polymer monomer form a binder suitable for this anode?

The bridge connects molecular_bridge (37 molecules) with battery_bridge
(22 materials), enabling queries like:
  "EC + DMC + LiPF6 with NMC811 cathode?"
  -> molecular-level: EC-DMC miscibility, LiPF6 solvation
  -> material-level: electrolyte-cathode voltage window, SEI stability

Follows the cross-bridge pattern of battery_polymer.py, battery_metal.py.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from molecular_bridge.molecule_properties import (
    Molecule, MoleculeClass,
    get_molecule, ALL_MOLECULES,
    ELECTROLYTE_SOLVENTS, SALT_ANIONS, POLYMER_MONOMERS,
)
from molecular_bridge.interaction_scoring import score_all as mol_score_all
from molecular_bridge.interface_validator import (
    MolecularInterfaceValidator, MolecularInterfaceScore,
)

try:
    from battery_bridge.material_properties import (
        BatteryMaterial, VoltageWindow,
        get_material as get_battery_material,
        ALL_MATERIALS as ALL_BATTERY_MATERIALS,
    )
    BATTERY_AVAILABLE = True
except ImportError:
    BATTERY_AVAILABLE = False


# ============================================================================
# Known cross-scale pairs (literature ground truth)
# ============================================================================

KNOWN_GOOD_PAIRS: List[Tuple[str, str]] = [
    # (molecule, battery_material) -- pairs known to work
    ('EC', 'Graphite'),       # EC forms stable SEI on graphite
    ('EC', 'LFP'),            # EC within LFP voltage window
    ('DMC', 'Graphite'),      # DMC co-solvent for graphite cells
    ('LiPF6', 'NMC811'),      # Standard salt for NMC cells
    ('LiPF6', 'Graphite'),    # Standard salt for graphite anodes
    ('FEC', 'Si'),            # FEC additive improves Si anode SEI
    ('VC', 'Graphite'),       # VC additive improves graphite SEI
    ('LiTFSI', 'LFP'),       # LiTFSI works well with low-voltage LFP
]

KNOWN_BAD_PAIRS: List[Tuple[str, str]] = [
    # (molecule, battery_material) -- pairs known to fail
    ('PC', 'Graphite'),       # PC co-intercalates into graphite, causes exfoliation
    ('H2O', 'Li_metal'),      # Water reacts violently with lithium metal
    ('H2O', 'LiPF6'),        # Water + LiPF6 -> HF (corrosive)
    ('LiClO4', 'Li_metal'),   # Perchlorate + Li metal = explosion risk
]


@dataclass
class MolecularMaterialResult:
    """Result of cross-scale molecular-material compatibility."""
    compatible: bool
    score: float                              # 0-1 composite
    molecular_compatibility: float            # Molecule-molecule level
    voltage_compatibility: float              # Molecule in electrode voltage window?
    thermal_compatibility: float              # Molecule stable at battery temp?
    chemical_compatibility: float             # Known bad reaction check
    molecule_name: str
    material_name: str
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'compatible': self.compatible,
            'score': round(self.score, 4),
            'molecular_compatibility': round(self.molecular_compatibility, 4),
            'voltage_compatibility': round(self.voltage_compatibility, 4),
            'thermal_compatibility': round(self.thermal_compatibility, 4),
            'chemical_compatibility': round(self.chemical_compatibility, 4),
            'molecule_name': self.molecule_name,
            'material_name': self.material_name,
            'warnings': self.warnings,
        }


# ============================================================================
# Cross-scale scorers
# ============================================================================

def _score_voltage_compatibility(
    molecule: Molecule,
    battery_mat: 'BatteryMaterial',
) -> Tuple[float, List[str]]:
    """
    Check if molecule's redox window is compatible with electrode voltage.

    Electrolyte solvents/salts must be stable within the electrode's
    operating voltage range. If the molecule oxidizes below the cathode
    voltage or reduces above the anode voltage, it will decompose.
    """
    warnings = []
    score = 1.0

    if not BATTERY_AVAILABLE:
        return 0.5, ['Battery bridge not available']

    # Get electrode voltage window
    vw = getattr(battery_mat, 'voltage_window', None)
    if vw is None:
        return 0.8, []  # No voltage data, mild assumption of compatibility

    # For electrolyte molecules, check redox potential vs electrode voltage
    redox = molecule.redox_potential_V
    if redox is not None:
        # If molecule is an oxidizer and electrode operates at low voltage,
        # the oxidizer may attack the anode
        if molecule.is_oxidizing and hasattr(vw, 'min_V'):
            if redox > vw.min_V + 1.0:
                score *= 0.6
                warnings.append(
                    f'{molecule.name} (E={redox:.2f}V) may oxidize '
                    f'materials at {vw.min_V:.1f}V'
                )

    # Solvents with very high dipole moments may be less stable at
    # high voltages (increased polarization-driven decomposition)
    dp = molecule.dipole_moment_debye
    if dp is not None and dp > 4.5:
        if hasattr(vw, 'max_V') and vw.max_V > 4.0:
            score *= 0.9
            warnings.append(
                f'High dipole ({dp:.1f}D) solvent may decompose '
                f'above {vw.max_V:.1f}V'
            )

    return score, warnings


def _score_thermal_compatibility(
    molecule: Molecule,
    battery_mat: 'BatteryMaterial',
) -> Tuple[float, List[str]]:
    """
    Check if molecule is thermally stable at battery operating temperature.

    Low-boiling solvents may evaporate; high-melting ones may solidify.
    """
    warnings = []
    score = 1.0

    bp = molecule.boiling_point_C
    fp = molecule.flash_point_C

    # Battery operating range is typically -20 to 60 C, with abuse up to 150 C
    if bp is not None and bp < 80:
        score *= 0.6
        warnings.append(
            f'{molecule.name} bp={bp:.0f}C: may evaporate at operating temp'
        )
    elif bp is not None and bp < 120:
        score *= 0.85
        warnings.append(
            f'{molecule.name} bp={bp:.0f}C: borderline thermal stability'
        )

    # Flash point safety
    if fp is not None and fp < 30:
        score *= 0.8
        warnings.append(
            f'{molecule.name} flash point={fp:.0f}C: fire risk in battery abuse'
        )

    return score, warnings


def _score_chemical_compatibility(
    molecule: Molecule,
    battery_mat: 'BatteryMaterial',
) -> Tuple[float, List[str]]:
    """
    Check for known bad chemical reactions between molecule and material.

    Uses the KNOWN_BAD_PAIRS table plus general chemistry rules.
    """
    warnings = []
    score = 1.0

    mol_name = molecule.name
    mat_name = battery_mat.name if BATTERY_AVAILABLE else ""

    # Check known bad pairs
    for bad_mol, bad_mat in KNOWN_BAD_PAIRS:
        if mol_name == bad_mol and mat_name == bad_mat:
            score = 0.15
            warnings.append(
                f'Known incompatible pair: {mol_name} + {mat_name}'
            )
            return score, warnings

    # General rules

    # Water with any lithium-containing material
    if mol_name == 'H2O' and BATTERY_AVAILABLE:
        score *= 0.3
        warnings.append('Water is generally incompatible with Li-ion cells')

    # Strong oxidizers with lithium metal
    if molecule.is_oxidizing and mat_name in ('Li_metal',):
        score *= 0.2
        warnings.append(
            f'{mol_name} (oxidizer) + {mat_name}: violent reaction risk'
        )

    # Known good pairs get a boost
    for good_mol, good_mat in KNOWN_GOOD_PAIRS:
        if mol_name == good_mol and mat_name == good_mat:
            score = min(1.0, score * 1.1)
            break

    return score, warnings


def score_molecule_material(
    molecule_name: str,
    material_name: str,
    viability_threshold: float = 0.50,
) -> MolecularMaterialResult:
    """
    Score cross-scale compatibility between a molecule and a battery material.

    Args:
        molecule_name: Name in molecular_bridge database (e.g. 'EC', 'LiPF6').
        material_name: Name in battery_bridge database (e.g. 'NMC811', 'Graphite').
        viability_threshold: Minimum score to be considered compatible.

    Returns:
        MolecularMaterialResult with breakdown scores and warnings.

    Raises:
        ValueError: If molecule or material not found.
    """
    molecule = get_molecule(molecule_name)
    if molecule is None:
        raise ValueError(f"Unknown molecule: '{molecule_name}'")

    if not BATTERY_AVAILABLE:
        return MolecularMaterialResult(
            compatible=False,
            score=0.0,
            molecular_compatibility=0.0,
            voltage_compatibility=0.0,
            thermal_compatibility=0.0,
            chemical_compatibility=0.0,
            molecule_name=molecule_name,
            material_name=material_name,
            warnings=['Battery bridge not available'],
        )

    battery_mat = get_battery_material(material_name)
    if battery_mat is None:
        raise ValueError(f"Unknown battery material: '{material_name}'")

    all_warnings = []

    # Molecular-level self-compatibility (does this molecule have good properties?)
    # Use a simple heuristic: check molecule against itself
    mol_validator = MolecularInterfaceValidator()
    mol_self = mol_validator.validate_molecules(molecule, molecule)
    mol_compat = mol_self.total

    # Cross-scale scores
    v_score, v_warn = _score_voltage_compatibility(molecule, battery_mat)
    t_score, t_warn = _score_thermal_compatibility(molecule, battery_mat)
    c_score, c_warn = _score_chemical_compatibility(molecule, battery_mat)

    all_warnings.extend(v_warn)
    all_warnings.extend(t_warn)
    all_warnings.extend(c_warn)

    # Weighted composite: chemical compatibility has highest weight
    # because a known bad reaction is a hard veto
    composite = (
        0.15 * mol_compat +
        0.25 * v_score +
        0.20 * t_score +
        0.40 * c_score
    )

    # Chemical compatibility acts as a veto: if it's very low (known bad pair),
    # the combination is non-viable regardless of other scores.
    chemical_veto = c_score < 0.2

    return MolecularMaterialResult(
        compatible=(composite >= viability_threshold) and not chemical_veto,
        score=composite,
        molecular_compatibility=mol_compat,
        voltage_compatibility=v_score,
        thermal_compatibility=t_score,
        chemical_compatibility=c_score,
        molecule_name=molecule_name,
        material_name=material_name,
        warnings=all_warnings,
    )


def score_electrolyte_formulation(
    solvent_names: List[str],
    salt_name: str,
    electrode_name: str,
    viability_threshold: float = 0.50,
) -> Dict:
    """
    Score a complete electrolyte formulation against an electrode.

    Multi-scale analysis:
    1. Molecular level: check solvent-solvent and solvent-salt compatibility
    2. Cross-scale level: check each molecule against the electrode

    Args:
        solvent_names: List of solvent molecule names (e.g. ['EC', 'DMC']).
        salt_name: Salt molecule name (e.g. 'LiPF6').
        electrode_name: Battery material name (e.g. 'NMC811').
        viability_threshold: Minimum score for viability.

    Returns:
        Dict with molecular_scores, material_scores, overall_score, viable.
    """
    all_mol_names = solvent_names + [salt_name]
    warnings = []

    # 1. Molecular-level: pairwise solvent-solvent and solvent-salt
    mol_validator = MolecularInterfaceValidator()
    mol_scores = {}
    for i, name_a in enumerate(all_mol_names):
        for name_b in all_mol_names[i + 1:]:
            try:
                result = mol_validator.validate(name_a, name_b)
                mol_scores[f"{name_a}-{name_b}"] = result.to_dict()
                if not result.viable:
                    warnings.append(
                        f'Molecular incompatibility: {name_a}-{name_b} '
                        f'(score={result.total:.2f})'
                    )
            except ValueError:
                pass

    # 2. Cross-scale: each molecule against the electrode
    mat_scores = {}
    for mol_name in all_mol_names:
        try:
            result = score_molecule_material(
                mol_name, electrode_name, viability_threshold,
            )
            mat_scores[f"{mol_name}-{electrode_name}"] = result.to_dict()
            warnings.extend(result.warnings)
        except ValueError:
            pass

    # Overall: geometric mean of all pairwise + cross-scale scores
    all_scores = []
    for d in mol_scores.values():
        all_scores.append(d['total'])
    for d in mat_scores.values():
        all_scores.append(d['score'])

    if all_scores:
        # Use min as bottleneck (weakest link determines system viability)
        overall = min(all_scores)
    else:
        overall = 0.0

    return {
        'solvent_names': solvent_names,
        'salt_name': salt_name,
        'electrode_name': electrode_name,
        'molecular_scores': mol_scores,
        'material_scores': mat_scores,
        'overall_score': round(overall, 4),
        'viable': overall >= viability_threshold,
        'warnings': warnings,
        'bottleneck': min(
            list(mol_scores.keys()) + list(mat_scores.keys()),
            key=lambda k: (
                mol_scores.get(k, {}).get('total', 1.0)
                if k in mol_scores
                else mat_scores.get(k, {}).get('score', 1.0)
            ),
            default=None,
        ) if (mol_scores or mat_scores) else None,
    }


if __name__ == "__main__":
    print("Molecular-Material Cross-Bridge -- Demo")
    print("=" * 60)

    # Single molecule-material check
    if BATTERY_AVAILABLE:
        result = score_molecule_material('EC', 'Graphite')
        print(f"\nEC + Graphite:")
        print(f"  Compatible: {result.compatible}")
        print(f"  Score: {result.score:.3f}")
        print(f"  Voltage: {result.voltage_compatibility:.3f}")
        print(f"  Thermal: {result.thermal_compatibility:.3f}")
        print(f"  Chemical: {result.chemical_compatibility:.3f}")
        if result.warnings:
            print(f"  Warnings: {result.warnings}")

        # Known bad pair
        result2 = score_molecule_material('PC', 'Graphite')
        print(f"\nPC + Graphite (known bad):")
        print(f"  Compatible: {result2.compatible}")
        print(f"  Score: {result2.score:.3f}")
        if result2.warnings:
            print(f"  Warnings: {result2.warnings}")

        # Full electrolyte formulation
        print("\n\nFull electrolyte formulation: EC:DMC + LiPF6 + NMC811")
        form = score_electrolyte_formulation(
            ['EC', 'DMC'], 'LiPF6', 'NMC811',
        )
        print(f"  Overall: {form['overall_score']:.3f}")
        print(f"  Viable: {form['viable']}")
        print(f"  Bottleneck: {form['bottleneck']}")
    else:
        print("Battery bridge not available. Install battery_bridge to demo.")
