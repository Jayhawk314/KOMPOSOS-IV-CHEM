# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Battery Interaction Scoring
=============================

Five electrochemical compatibility scorers, analogous to the protein bridge's
H-bond / salt-bridge / hydrophobic / vdW / electrostatic scorers.

Each scorer takes two BatteryMaterial objects and returns a float in [0, 1].

Scorer Mapping (protein bridge -> battery bridge):
---------------------------------------------------
H-bond scoring          -> Ion transport score
Salt bridge scoring     -> Electrochemical stability score
Hydrophobic scoring     -> Interface compatibility score
Van der Waals scoring   -> Mechanical compatibility score
Electrostatic repulsion -> Degradation penalty

References:
-----------
- Goodenough & Kim, Chem. Mater. 2010 -- electrochemical stability
- Monroe & Newman, J. Electrochem. Soc. 2005 -- mechanical suppression
- Peled, J. Electrochem. Soc. 1979 -- SEI layer theory
- Aurbach et al., J. Power Sources 2004 -- interface chemistry
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, FailureMode, CrystalStructure,
    get_material,
)


@dataclass
class ScorerResult:
    """Result from a single interaction scorer."""
    score: float         # 0-1 (1 = excellent compatibility)
    label: str           # Human-readable label
    details: Dict        # Breakdown / reasoning


# =============================================================================
# 1. ION TRANSPORT SCORE
# =============================================================================
# Analogous to H-bond scoring: "Can the primary interaction happen at all?"
# For batteries: "Can Li+ migrate through this interface?"

def score_ion_transport(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
    carrier_ion_radius: float = 0.76,  # Li+ Shannon radius, Angstroms
) -> ScorerResult:
    """
    Score ion transport feasibility across an interface.

    Factors:
    - Both materials must support ionic conduction
    - Crystal structure compatibility (layered->layered is easy, etc.)
    - Ionic conductivity ratio (large mismatch = bottleneck)

    Args:
        material_a: First material at the interface
        material_b: Second material at the interface
        carrier_ion_radius: Radius of the carrier ion (default: Li+)

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- Ionic conductivity mismatch ---
    cond_a = material_a.ionic_conductivity
    cond_b = material_b.ionic_conductivity

    if cond_a is not None and cond_b is not None and cond_a > 0 and cond_b > 0:
        # Log-ratio of conductivities; mismatch > 2 orders of magnitude penalized
        log_ratio = abs(math.log10(cond_a) - math.log10(cond_b))
        if log_ratio > 4:
            penalty = 0.5
        elif log_ratio > 2:
            penalty = 0.3 * (log_ratio - 2) / 2
        else:
            penalty = 0.0
        score -= penalty
        details['conductivity_log_ratio'] = round(log_ratio, 2)
    elif cond_a is None and cond_b is None:
        # Neither has explicit ionic conductivity -- e.g., cathode-anode
        # Not penalized; transport happens through electrolyte
        details['note'] = 'No ionic conductivity data; transport mediated by electrolyte'

    # --- Crystal structure compatibility ---
    struct_compatibility = _crystal_structure_compatibility(
        material_a.crystal_structure, material_b.crystal_structure
    )
    score *= struct_compatibility
    details['crystal_compatibility'] = round(struct_compatibility, 2)

    # --- Carrier ion radius vs. channel size heuristic ---
    # Solid electrolytes with garnet structure have ~1 A channels
    # LGPS has wide S-framework channels ~2.5 A
    if material_a.material_class == MaterialClass.SOLID_ELECTROLYTE:
        channel_penalty = _channel_size_penalty(material_a, carrier_ion_radius)
        score *= (1.0 - channel_penalty)
        details['channel_penalty_a'] = round(channel_penalty, 2)
    if material_b.material_class == MaterialClass.SOLID_ELECTROLYTE:
        channel_penalty = _channel_size_penalty(material_b, carrier_ion_radius)
        score *= (1.0 - channel_penalty)
        details['channel_penalty_b'] = round(channel_penalty, 2)

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='ion_transport', details=details)


def _crystal_structure_compatibility(struct_a: CrystalStructure, struct_b: CrystalStructure) -> float:
    """Heuristic compatibility between crystal structure types."""
    # Same structure family -> good lattice matching
    if struct_a == struct_b:
        return 1.0
    # Molecular solvents interface with anything (liquid wets solid)
    if struct_a == CrystalStructure.MOLECULAR or struct_b == CrystalStructure.MOLECULAR:
        return 0.95
    # Amorphous interfaces well (no grain boundary mismatch)
    if struct_a == CrystalStructure.AMORPHOUS or struct_b == CrystalStructure.AMORPHOUS:
        return 0.90
    # Mixed solid structures (e.g., layered cathode + garnet electrolyte)
    return 0.75


def _channel_size_penalty(solid_electrolyte: BatteryMaterial, ion_radius: float) -> float:
    """Penalty if ion is too large for the electrolyte channel."""
    # Approximate channel sizes by structure type
    # Garnet (LLZO): ~1.0 A bottleneck (Adams & Rao, J. Mater. Chem. 2012)
    # Thio-LISICON (LGPS): ~2.5 A (Kamaya et al. 2011)
    channel_sizes = {
        CrystalStructure.GARNET: 1.0,
        CrystalStructure.THIO_LISICON: 2.5,
        CrystalStructure.ARGYRODITE: 2.0,
        CrystalStructure.AMORPHOUS: 1.5,  # Glassy sulfides
    }
    channel = channel_sizes.get(solid_electrolyte.crystal_structure, 1.5)
    ratio = ion_radius / channel
    if ratio > 0.9:
        return 0.4   # Severely restricted
    elif ratio > 0.7:
        return 0.15
    return 0.0


# =============================================================================
# 2. ELECTROCHEMICAL STABILITY SCORE
# =============================================================================
# Analogous to salt bridge scoring: "Is the electrolyte stable at this voltage?"

def score_electrochemical_stability(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
) -> ScorerResult:
    """
    Score whether an electrolyte is electrochemically stable at the electrode potential.

    For cathodes: electrode voltage must be below electrolyte oxidation potential.
    For anodes: electrode voltage must be above electrolyte reduction potential.

    Auto-detects electrode vs. electrolyte roles from material_class so
    argument order does not matter.

    Args:
        material_a: First material (any role)
        material_b: Second material (any role)

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # Auto-detect roles: electrode (has voltage_window) vs electrolyte (has ox/red potentials)
    electrode_classes = {MaterialClass.CATHODE, MaterialClass.ANODE}
    electrolyte_classes = {MaterialClass.ELECTROLYTE_SOLVENT, MaterialClass.ELECTROLYTE_SALT,
                          MaterialClass.SOLID_ELECTROLYTE}

    electrode, electrolyte = material_a, material_b
    if material_a.material_class in electrolyte_classes and material_b.material_class in electrode_classes:
        electrode, electrolyte = material_b, material_a
    elif material_a.material_class in electrode_classes and material_b.material_class in electrolyte_classes:
        electrode, electrolyte = material_a, material_b
    # If both are electrodes or both are electrolytes, keep original order

    e_ox = electrolyte.oxidation_potential   # V vs Li/Li+
    e_red = electrolyte.reduction_potential  # V vs Li/Li+
    v_window = electrode.voltage_window

    if v_window is None or (e_ox is None and e_red is None):
        details['note'] = 'Insufficient voltage data for stability check'
        return ScorerResult(score=0.5, label='electrochemical_stability', details=details)

    # --- Cathode side: upper voltage vs. electrolyte oxidation ---
    if electrode.material_class == MaterialClass.CATHODE and e_ox is not None:
        headroom = e_ox - v_window.upper  # Positive = safe
        details['oxidation_headroom_V'] = round(headroom, 2)
        if headroom < 0:
            # Check for sulfide electrolyte + low-voltage cathode passivation.
            # Sulfide solid electrolytes (LGPS, Li3PS4) form self-limiting
            # passivating interfaces with low-voltage cathodes like LFP
            # (nominal <= 3.5V). The decomposition products (Li3P, Li2S)
            # stabilize the interface. Ref: Janek & Zeier, Nat. Energy 2016;
            # Kato et al., Nat. Energy 2016.
            is_sulfide_se = (
                electrolyte.material_class == MaterialClass.SOLID_ELECTROLYTE
                and e_ox is not None and e_ox <= 2.6  # Sulfides: LGPS=2.1, Li3PS4=2.5
            )
            is_low_v_cathode = (
                v_window.nominal is not None and v_window.nominal <= 3.5
            )
            if is_sulfide_se and is_low_v_cathode and abs(headroom) < 2.0:
                # Passivating interface: moderate penalty instead of kill
                score *= 0.55
                details['oxidation_risk'] = 'sulfide_passivating_interface'
            else:
                # Standard harsh penalty for non-passivating decomposition
                score *= max(0.0, 0.3 + 0.7 * (1.0 + headroom / 1.0))
                details['oxidation_risk'] = True
        elif headroom < 0.3:
            score *= 0.8  # Tight margin
            details['oxidation_risk'] = 'marginal'

    # --- Anode side: lower voltage vs. electrolyte reduction ---
    if electrode.material_class == MaterialClass.ANODE and e_red is not None:
        headroom = v_window.lower - e_red  # Negative = electrolyte reduces first
        details['reduction_headroom_V'] = round(headroom, 2)
        if headroom < 0:
            # Electrolyte reduces before reaching anode potential
            # This is actually normal for graphite + EC -> forms SEI
            # Penalize mildly if SEI-forming, heavily if solid electrolyte
            if electrolyte.material_class == MaterialClass.SOLID_ELECTROLYTE:
                score *= max(0.0, 0.2 + 0.5 * (1.0 + headroom / 2.0))
                details['reduction_risk'] = 'solid_electrolyte_decomposition'
            else:
                # Liquid electrolyte SEI formation is expected and manageable
                score *= 0.85
                details['reduction_risk'] = 'SEI_formation_expected'

    # --- Solid electrolyte window check ---
    if electrolyte.material_class == MaterialClass.SOLID_ELECTROLYTE:
        if e_ox is not None and e_red is not None and v_window is not None:
            window_width = e_ox - e_red
            operating_range = v_window.upper - v_window.lower
            details['electrolyte_window_V'] = round(window_width, 2)
            if window_width < operating_range:
                # Solid electrolyte window too narrow for this electrode
                overlap = max(0, min(e_ox, v_window.upper) - max(e_red, v_window.lower))
                coverage = overlap / operating_range if operating_range > 0 else 0

                # Sulfide electrolytes with low-voltage cathodes form
                # passivating decomposition layers that allow operation
                # outside the strict thermodynamic window.
                # Ref: Janek & Zeier, Nat. Energy 2016; Kato et al. 2016
                is_sulfide_passivating = (
                    e_ox <= 2.6
                    and v_window.nominal is not None
                    and v_window.nominal <= 3.5
                )
                if is_sulfide_passivating and coverage < 0.6:
                    coverage = 0.6  # Floor: passivating decomposition layer
                    details['sulfide_passivation_floor'] = True

                score *= coverage
                details['window_coverage'] = round(coverage, 2)

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='electrochemical_stability', details=details)


# =============================================================================
# 3. INTERFACE COMPATIBILITY SCORE
# =============================================================================
# Analogous to hydrophobic scoring: "Will these form a stable interface layer?"

def score_interface_compatibility(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
) -> ScorerResult:
    """
    Score interface stability (SEI/CEI layer formation and passivation).

    Factors:
    - Known good SEI formers (EC on graphite) get high scores
    - Reactive pairs that don't passivate get low scores
    - Solid-solid interfaces penalized for poor wetting/contact

    Args:
        material_a: First material
        material_b: Second material

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    classes = {material_a.material_class, material_b.material_class}

    # --- Liquid electrolyte + graphite anode -> SEI formation (well-understood) ---
    if (MaterialClass.ANODE in classes and
            MaterialClass.ELECTROLYTE_SOLVENT in classes):
        anode = material_a if material_a.material_class == MaterialClass.ANODE else material_b
        solvent = material_a if material_a.material_class == MaterialClass.ELECTROLYTE_SOLVENT else material_b

        if anode.name == 'Graphite':
            # EC forms excellent SEI on graphite (Peled & Menkin, J. Electrochem. Soc. 2017)
            if solvent.name == 'EC':
                score = 0.95
                details['sei_quality'] = 'EC forms stable SEI on graphite'
            elif solvent.name in ('DMC', 'DEC', 'EMC'):
                # Linear carbonates alone: poor SEI
                score = 0.65
                details['sei_quality'] = 'Linear carbonate alone gives poor SEI; needs EC co-solvent'
            else:
                score = 0.7
        elif anode.name == 'Li_metal':
            # Li metal + liquid electrolyte -> unstable SEI, dendrites
            score = 0.25
            details['sei_quality'] = 'Li metal SEI in liquid electrolyte is unstable'
            details['dendrite_risk'] = True
        elif anode.name == 'Si':
            # Si: SEI cracks every cycle due to volume expansion
            score = 0.30
            details['sei_quality'] = 'Si volume expansion (300%) ruptures SEI repeatedly'

    # --- Solid electrolyte + electrode: contact area problem ---
    elif (MaterialClass.SOLID_ELECTROLYTE in classes and
          (MaterialClass.CATHODE in classes or MaterialClass.ANODE in classes)):
        # Solid-solid contact is inherently limited
        score = 0.65
        details['interface_type'] = 'solid-solid'
        details['contact_issue'] = 'Limited contact area; requires pressure or sintering'

        # LLZO + Li metal is a well-studied interface
        se = material_a if material_a.material_class == MaterialClass.SOLID_ELECTROLYTE else material_b
        elec = material_a if material_a.material_class != MaterialClass.SOLID_ELECTROLYTE else material_b

        if se.name == 'LLZO' and elec.name == 'Li_metal':
            score = 0.55  # Wetting issues but actively researched
            details['note'] = 'LLZO/Li interface: poor wetting without interlayer'

    # --- Cathode + liquid electrolyte: CEI formation ---
    elif (MaterialClass.CATHODE in classes and
          MaterialClass.ELECTROLYTE_SOLVENT in classes):
        cathode = material_a if material_a.material_class == MaterialClass.CATHODE else material_b
        if cathode.voltage_window and cathode.voltage_window.upper > 4.3:
            # High-voltage cathodes decompose electrolyte at surface
            score = 0.55
            details['cei_quality'] = 'High voltage cathode promotes electrolyte oxidation'
        else:
            score = 0.85
            details['cei_quality'] = 'Moderate voltage; stable CEI expected'

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='interface_compatibility', details=details)


# =============================================================================
# 4. MECHANICAL COMPATIBILITY SCORE
# =============================================================================
# Analogous to vdW scoring: "Will cycling cause mechanical failure?"

def score_mechanical_compatibility(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
) -> ScorerResult:
    """
    Score mechanical compatibility during cycling.

    Factors:
    - Volume expansion mismatch -> delamination
    - Elastic modulus mismatch -> stress concentration
    - Known cracking-prone materials

    Args:
        material_a: First material
        material_b: Second material

    Returns:
        ScorerResult with score in [0, 1]
    """
    score = 1.0
    details = {}

    # --- Volume expansion analysis ---
    ve_a = material_a.volume_expansion
    ve_b = material_b.volume_expansion

    if ve_a is not None and ve_b is not None:
        # Large differential expansion -> delamination
        ve_diff = abs(ve_a - ve_b)
        max_ve = max(ve_a, ve_b)

        details['volume_expansion_a'] = round(ve_a, 3)
        details['volume_expansion_b'] = round(ve_b, 3)
        details['expansion_diff'] = round(ve_diff, 3)

        if max_ve > 1.0:
            # >100% expansion (Si anode territory)
            score *= 0.2
            details['expansion_severity'] = 'extreme'
        elif max_ve > 0.1:
            # >10% (moderate, manageable with engineering)
            score *= max(0.4, 1.0 - max_ve * 2)
            details['expansion_severity'] = 'moderate'
        elif ve_diff > 0.05:
            score *= 0.85
            details['expansion_severity'] = 'mild_mismatch'
    elif ve_a is not None and ve_a > 1.0:
        score *= 0.2
        details['note'] = f'{material_a.name} has extreme volume expansion ({ve_a*100:.0f}%)'
    elif ve_b is not None and ve_b > 1.0:
        score *= 0.2
        details['note'] = f'{material_b.name} has extreme volume expansion ({ve_b*100:.0f}%)'

    # --- Elastic modulus mismatch ---
    mod_a = material_a.elastic_modulus
    mod_b = material_b.elastic_modulus

    if mod_a is not None and mod_b is not None and mod_a > 0 and mod_b > 0:
        modulus_ratio = max(mod_a, mod_b) / min(mod_a, mod_b)
        details['modulus_ratio'] = round(modulus_ratio, 1)
        if modulus_ratio > 10:
            score *= 0.7  # Large mismatch
        elif modulus_ratio > 5:
            score *= 0.85

    # --- Brittle + expansion = cracking ---
    for mat in (material_a, material_b):
        if FailureMode.CRACKING in mat.failure_modes:
            if mat.volume_expansion and mat.volume_expansion > 0.05:
                score *= 0.6
                details[f'{mat.name}_crack_risk'] = True

    score = max(0.0, min(1.0, score))
    return ScorerResult(score=score, label='mechanical_compatibility', details=details)


# =============================================================================
# 5. DEGRADATION PENALTY
# =============================================================================
# Analogous to electrostatic repulsion: "Known bad pairings get penalized."

# Known problematic pairings: (material_a_name, material_b_name) -> penalty
_KNOWN_BAD_PAIRINGS: Dict[Tuple[str, str], Tuple[float, str]] = {
    ('Li_metal', 'EC'): (0.7, 'Dendrite growth through liquid carbonate electrolyte'),
    ('Li_metal', 'DMC'): (0.7, 'Dendrite growth through liquid carbonate electrolyte'),
    ('Li_metal', 'DEC'): (0.7, 'Dendrite growth through liquid carbonate electrolyte'),
    ('Li_metal', 'EMC'): (0.7, 'Dendrite growth through liquid carbonate electrolyte'),
    ('Si', 'EC'): (0.7, 'Si 300% expansion destroys SEI; rapid capacity fade'),
    ('Si', 'DMC'): (0.7, 'Si 300% expansion destroys SEI'),
    ('LGPS', 'NMC811'): (0.7, 'LGPS decomposes at NMC811 operating voltage (3.8V >> 2.1V limit)'),
    ('LGPS', 'NMC622'): (0.7, 'LGPS decomposes at NMC622 operating voltage'),
    ('LGPS', 'NMC811'): (0.7, 'LGPS decomposes at NMC811 voltage'),
    ('LGPS', 'LCO'): (0.7, 'LGPS decomposes at LCO operating voltage'),
    ('LGPS', 'LMO'): (0.7, 'LGPS decomposes at LMO operating voltage'),
    # Li3PS4 sulfide: oxidation potential ~2.5V, decomposes at high-voltage cathodes
    ('Li3PS4', 'NMC811'): (0.7, 'Li3PS4 decomposes at NMC811 voltage (3.0-4.3V >> 2.5V oxidation limit)'),
    ('Li3PS4', 'NMC622'): (0.7, 'Li3PS4 decomposes at NMC622 voltage (3.0-4.3V >> 2.5V oxidation limit)'),
    ('Li3PS4', 'LCO'): (0.7, 'Li3PS4 decomposes at LCO voltage (3.0-4.2V >> 2.5V oxidation limit)'),
    ('Li3PS4', 'LMO'): (0.7, 'Li3PS4 decomposes at LMO voltage (3.0-4.3V >> 2.5V oxidation limit)'),
    # PEO oxidation at high voltage -- penalties must produce score <= 0.4 to trigger veto
    ('PEO', 'LCO'): (0.75, 'PEO oxidizes above 3.9V; LCO operates at 3.9-4.2V (continuous decomposition)'),
    ('PEO', 'NMC811'): (0.75, 'PEO oxidizes above 3.9V; NMC811 operates at 3.8-4.3V (Armand 2008)'),
    ('PEO', 'NMC622'): (0.75, 'PEO oxidizes above 3.9V; NMC622 operates at 3.8-4.3V'),
    ('PEO', 'NMC111'): (0.75, 'PEO oxidizes above 3.9V; NMC111 operates at 3.8-4.3V'),
    ('PEO', 'LMO'): (0.75, 'PEO oxidizes above 3.9V; LMO operates at 4.1-4.3V'),
    # Thermodynamic instability with Li metal
    ('Li_metal', 'LGPS'): (0.7, 'LGPS thermodynamically unstable with Li metal (Janek 2016)'),
    ('Li_metal', 'Li3PS4'): (0.7, 'Li3PS4 thermodynamically unstable with Li metal (forms Li2S/Li3P, Janek 2016)'),
    ('Li_metal', 'LATP'): (0.8, 'LATP reduced by Li metal (Ti4+ -> Ti3+) causing electronic conduction'),
}


def score_degradation_penalty(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
) -> ScorerResult:
    """
    Apply degradation penalty for known problematic pairings.

    This is a lookup-based scorer that encodes well-established
    failure combinations from the battery literature.

    Args:
        material_a: First material
        material_b: Second material

    Returns:
        ScorerResult with score in [0, 1] (1 = no degradation concern)
    """
    penalty = 0.0
    reasons = []

    # Check both orderings
    for key in [(material_a.name, material_b.name),
                (material_b.name, material_a.name)]:
        if key in _KNOWN_BAD_PAIRINGS:
            p, reason = _KNOWN_BAD_PAIRINGS[key]
            penalty = max(penalty, p)
            reasons.append(reason)

    # --- Shared failure mode analysis ---
    shared_failures = set(material_a.failure_modes) & set(material_b.failure_modes)
    critical_shared = shared_failures & {
        FailureMode.THERMAL_RUNAWAY,
        FailureMode.DENDRITE_GROWTH,
    }
    if critical_shared:
        penalty = max(penalty, 0.3)
        reasons.append(f'Shared critical failure modes: {[f.value for f in critical_shared]}')

    # --- SEI Stability Check ---
    # FEC is a known SEI stabilizer for Si and Li metal
    has_fec = material_a.name == 'FEC' or material_b.name == 'FEC'
    if not has_fec:
        # Check if either material is Li_metal/Si and the other is a liquid carbonate (like EC)
        # These need FEC or similar for stable SEI
        is_reactive_anode = any(m.name in ('Li_metal', 'Si') for m in (material_a, material_b))
        is_liquid_carbonate = any(m.name in ('EC', 'DMC', 'DEC', 'EMC') for m in (material_a, material_b))

        if is_reactive_anode and is_liquid_carbonate:
            penalty = max(penalty, 0.5)
            reasons.append('Reactive anode + carbonate requires SEI stabilizer (e.g., FEC)')

    # --- Thermal stability mismatch ---
    ts_a = material_a.thermal_stability_max
    ts_b = material_b.thermal_stability_max
    if ts_a is not None and ts_b is not None:
        min_ts = min(ts_a, ts_b)
        if min_ts < 100:
            penalty = max(penalty, 0.4)
            reasons.append(f'Low thermal stability floor: {min_ts}C')
        elif min_ts < 150:
            penalty = max(penalty, 0.15)
            reasons.append(f'Marginal thermal stability: {min_ts}C')

    score = max(0.0, 1.0 - penalty)
    details = {
        'penalty': round(penalty, 2),
        'reasons': reasons if reasons else ['No known degradation concerns'],
    }

    return ScorerResult(score=score, label='degradation_penalty', details=details)


# =============================================================================
# COMPOSITE SCORER
# =============================================================================

def score_all(
    material_a: BatteryMaterial,
    material_b: BatteryMaterial,
) -> Dict[str, ScorerResult]:
    """
    Run all five scorers on a material pair.

    Args:
        material_a: First material
        material_b: Second material

    Returns:
        Dict mapping scorer name to ScorerResult
    """
    return {
        'ion_transport': score_ion_transport(material_a, material_b),
        'electrochemical_stability': score_electrochemical_stability(material_a, material_b),
        'interface_compatibility': score_interface_compatibility(material_a, material_b),
        'mechanical_compatibility': score_mechanical_compatibility(material_a, material_b),
        'degradation_penalty': score_degradation_penalty(material_a, material_b),
    }


if __name__ == "__main__":
    from battery_bridge.material_properties import CATHODE_MATERIALS, ANODE_MATERIALS, ELECTROLYTE_SOLVENTS

    print("=" * 70)
    print("Interaction Scoring - Demo")
    print("=" * 70)
    print()

    # Test: LFP cathode + EC solvent
    lfp = CATHODE_MATERIALS['LFP']
    ec = ELECTROLYTE_SOLVENTS['EC']

    print(f"Pair: {lfp.name} <-> {ec.name}")
    results = score_all(lfp, ec)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}")
    print()

    # Test: Si anode + EC (known bad)
    si = get_material('Si')
    print(f"Pair: {si.name} <-> {ec.name} (known problematic)")
    results = score_all(si, ec)
    for name, result in results.items():
        print(f"  {name:30s}: {result.score:.2f}  {result.details}")
