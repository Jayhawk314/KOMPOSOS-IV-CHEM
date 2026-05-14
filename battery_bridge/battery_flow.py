# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery Flow Analysis
========================

Compositional chain analysis for complete battery cell configurations.
Analogous to how resistance_flow.py traces antibiotic resistance paths,
this module traces electrochemical interfaces through a full cell.

Given a candidate cell (cathode, anode, electrolyte, separator), it:
1. Enumerates all material interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation cascade paths
5. Scores overall cell viability

This is the battery-domain analogue of compositional morphism chains
in the categorical framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, FailureMode,
    get_material, ALL_MATERIALS,
)
from battery_bridge.interface_validator import (
    BatteryInterfaceValidator, InterfaceScore, InterfaceConditions, InterfaceWeights,
)


@dataclass
class CellConfiguration:
    """
    A candidate battery cell configuration.

    Mirrors how the protein bridge validates full protein structures,
    not just individual contacts.
    """
    name: str
    cathode: str               # Material name
    anode: str                 # Material name
    electrolyte_salt: str      # Material name
    electrolyte_solvents: List[str] = field(default_factory=list)
    solid_electrolyte: Optional[str] = None
    separator: Optional[str] = None  # Not scored; placeholder for future
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the cell."""
    material_a: str
    material_b: str
    score: InterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationStep:
    """A single step in a degradation cascade."""
    trigger_interface: str       # Which interface fails first
    trigger_failure: str         # What failure mode triggers
    consequence: str             # What happens next
    secondary_interfaces: List[str] = field(default_factory=list)


@dataclass
class CellAnalysis:
    """
    Complete analysis of a battery cell configuration.

    Analogous to the full EnergyBreakdown from the protein bridge's
    energy_functions.py, but for electrochemical cells.
    """
    cell_name: str
    overall_viability: float       # 0-1 composite score
    viable: bool                   # Above threshold?
    interfaces: List[InterfaceResult]
    bottleneck: Optional[InterfaceResult]
    degradation_cascades: List[DegradationStep]
    warnings: List[str]
    cell_voltage: Optional[float]  # Nominal cell voltage (cathode - anode)
    theoretical_energy_density: Optional[float]  # Wh/kg estimate

    def to_dict(self) -> Dict:
        return {
            'cell_name': self.cell_name,
            'overall_viability': round(self.overall_viability, 4),
            'viable': self.viable,
            'num_interfaces': len(self.interfaces),
            'bottleneck': (
                f"{self.bottleneck.material_a}<->{self.bottleneck.material_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'cell_voltage_V': round(self.cell_voltage, 2) if self.cell_voltage else None,
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.material_a}<->{ir.material_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class BatteryFlowAnalyzer:
    """
    Analyzes complete battery cell configurations by tracing all interfaces.

    This is the compositional analysis layer that sits above the pairwise
    interface validator, analogous to how the Oracle composes individual
    morphism predictions into coherent paths.
    """

    def __init__(
        self,
        validator: Optional[BatteryInterfaceValidator] = None,
        viability_threshold: float = 0.45,
    ):
        self.validator = validator or BatteryInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_cell(
        self,
        config: CellConfiguration,
        conditions: Optional[InterfaceConditions] = None,
    ) -> CellAnalysis:
        """
        Analyze a complete cell configuration.

        Steps:
        1. Enumerate all interfaces
        2. Score each interface
        3. Find bottleneck
        4. Predict degradation cascades
        5. Compute overall viability

        Args:
            config: Cell configuration to analyze
            conditions: Operating conditions

        Returns:
            CellAnalysis with full breakdown
        """
        conditions = conditions or InterfaceConditions()
        warnings = []

        # Resolve material objects
        cathode = get_material(config.cathode)
        anode = get_material(config.anode)
        salt = get_material(config.electrolyte_salt)
        solvents = [get_material(s) for s in config.electrolyte_solvents]
        solid_elec = get_material(config.solid_electrolyte) if config.solid_electrolyte else None

        # Validate all materials exist
        for name, mat in [('cathode', cathode), ('anode', anode), ('salt', salt)]:
            if mat is None:
                warnings.append(f"Unknown {name}: {getattr(config, name, '?')}")

        solvents = [s for s in solvents if s is not None]

        # --- Enumerate interfaces ---
        interface_pairs = self._enumerate_interfaces(
            cathode, anode, salt, solvents, solid_elec
        )

        # --- Score each interface ---
        interface_results = []
        for mat_a, mat_b, label in interface_pairs:
            try:
                score = self.validator.validate_materials(mat_a, mat_b, conditions)
                interface_results.append(InterfaceResult(
                    material_a=mat_a.name,
                    material_b=mat_b.name,
                    score=score,
                ))
            except Exception as e:
                warnings.append(f"Failed to score {mat_a.name}<->{mat_b.name}: {e}")

        # --- Find bottleneck (lowest scoring interface) ---
        bottleneck = None
        if interface_results:
            bottleneck = min(interface_results, key=lambda ir: ir.score.total)
            bottleneck.is_bottleneck = True

        # --- Predict degradation cascades ---
        cascades = self._predict_degradation_cascades(
            cathode, anode, salt, solvents, solid_elec, interface_results
        )

        # --- Overall viability ---
        # Cell is as strong as its weakest interface (bottleneck-limited)
        # but also penalized for multiple weak interfaces
        if interface_results:
            min_score = bottleneck.score.total if bottleneck else 0
            avg_score = sum(ir.score.total for ir in interface_results) / len(interface_results)
            # 75% bottleneck, 25% average -- cell is only as good as its weakest link
            overall = 0.75 * min_score + 0.25 * avg_score
        else:
            overall = 0.0
            warnings.append("No valid interfaces could be scored")

        # --- Cell voltage and energy density ---
        cell_voltage = None
        energy_density = None
        if cathode and anode and cathode.voltage_window and anode.voltage_window:
            cell_voltage = cathode.voltage_window.nominal - anode.voltage_window.nominal
            # Rough energy density: V * min(capacity_cathode, capacity_anode) for limiting electrode
            if cathode.theoretical_capacity and anode.theoretical_capacity:
                # Simplified: use cathode capacity (typically limiting)
                energy_density = cell_voltage * cathode.theoretical_capacity  # Wh/kg cathode

        return CellAnalysis(
            cell_name=config.name,
            overall_viability=max(0.0, min(1.0, overall)),
            viable=overall >= self.viability_threshold,
            interfaces=interface_results,
            bottleneck=bottleneck,
            degradation_cascades=cascades,
            warnings=warnings,
            cell_voltage=cell_voltage,
            theoretical_energy_density=energy_density,
        )

    def _enumerate_interfaces(
        self,
        cathode: Optional[BatteryMaterial],
        anode: Optional[BatteryMaterial],
        salt: Optional[BatteryMaterial],
        solvents: List[BatteryMaterial],
        solid_electrolyte: Optional[BatteryMaterial],
    ) -> List[Tuple[BatteryMaterial, BatteryMaterial, str]]:
        """
        Enumerate all physically real interfaces in the cell.

        In a liquid-electrolyte cell:
          cathode <-> electrolyte_solvent(s)
          anode <-> electrolyte_solvent(s)

        In a solid-state cell:
          cathode <-> solid_electrolyte
          anode <-> solid_electrolyte

        Returns list of (material_a, material_b, label) tuples.
        """
        pairs = []

        if solid_electrolyte:
            # Solid-state cell interfaces
            if cathode:
                pairs.append((cathode, solid_electrolyte, 'cathode-SE'))
            if anode:
                pairs.append((anode, solid_electrolyte, 'anode-SE'))
        else:
            # Liquid electrolyte interfaces
            for solvent in solvents:
                if cathode:
                    pairs.append((cathode, solvent, f'cathode-{solvent.name}'))
                if anode:
                    pairs.append((anode, solvent, f'anode-{solvent.name}'))

        # Salt interacts with both electrodes (dissolved in electrolyte)
        if salt:
            if cathode:
                pairs.append((cathode, salt, 'cathode-salt'))
            if anode:
                pairs.append((anode, salt, 'anode-salt'))

        return pairs

    def _predict_degradation_cascades(
        self,
        cathode: Optional[BatteryMaterial],
        anode: Optional[BatteryMaterial],
        salt: Optional[BatteryMaterial],
        solvents: List[BatteryMaterial],
        solid_electrolyte: Optional[BatteryMaterial],
        interface_results: List[InterfaceResult],
    ) -> List[DegradationStep]:
        """
        Predict degradation cascade paths.

        Identifies which failure at one interface triggers failures elsewhere.
        """
        cascades = []

        # Collect all materials and their failure modes
        all_mats = [m for m in [cathode, anode, salt, solid_electrolyte] if m]
        all_mats.extend(solvents)

        # --- Cascade 1: Cathode oxygen release -> electrolyte decomposition -> thermal runaway ---
        if cathode and FailureMode.OXYGEN_RELEASE in cathode.failure_modes:
            cascades.append(DegradationStep(
                trigger_interface=f'{cathode.name}<->electrolyte',
                trigger_failure='oxygen_release',
                consequence='Released O2 reacts exothermically with electrolyte -> gas + heat',
                secondary_interfaces=['electrolyte_thermal_decomposition', 'cell_venting'],
            ))

        # --- Cascade 2: Anode dendrite -> short circuit -> thermal runaway ---
        if anode and FailureMode.DENDRITE_GROWTH in anode.failure_modes:
            cascades.append(DegradationStep(
                trigger_interface=f'{anode.name}<->electrolyte',
                trigger_failure='dendrite_growth',
                consequence='Dendrite penetrates separator -> internal short -> thermal runaway',
                secondary_interfaces=['separator_puncture', 'thermal_runaway'],
            ))

        # --- Cascade 3: Volume expansion -> SEI cracking -> capacity fade ---
        if anode and FailureMode.VOLUME_EXPANSION in anode.failure_modes:
            cascades.append(DegradationStep(
                trigger_interface=f'{anode.name}<->electrolyte',
                trigger_failure='volume_expansion',
                consequence='Expansion cracks SEI -> fresh surface exposed -> '
                            'electrolyte consumed -> capacity fade + impedance rise',
                secondary_interfaces=['sei_reformation', 'electrolyte_depletion'],
            ))

        # --- Cascade 4: Transition metal dissolution -> anode poisoning ---
        if cathode and FailureMode.TRANSITION_METAL_DISSOLUTION in cathode.failure_modes:
            cascades.append(DegradationStep(
                trigger_interface=f'{cathode.name}<->electrolyte',
                trigger_failure='tm_dissolution',
                consequence='Dissolved TM ions migrate to anode -> deposit in SEI -> '
                            'increased impedance + capacity loss',
                secondary_interfaces=['anode_sei_contamination'],
            ))

        # --- Cascade 5: Solid electrolyte decomposition -> resistance rise ---
        if solid_electrolyte and FailureMode.ELECTROLYTE_DECOMPOSITION in solid_electrolyte.failure_modes:
            cascades.append(DegradationStep(
                trigger_interface=f'{solid_electrolyte.name}<->electrode',
                trigger_failure='electrochemical_decomposition',
                consequence='Decomposition products form resistive interphase -> '
                            'impedance rise -> reduced rate capability',
                secondary_interfaces=['interphase_growth'],
            ))

        return cascades

    def compare_cells(
        self,
        configs: List[CellConfiguration],
        conditions: Optional[InterfaceConditions] = None,
    ) -> List[CellAnalysis]:
        """
        Analyze and rank multiple cell configurations.

        Args:
            configs: List of cell configurations
            conditions: Shared operating conditions

        Returns:
            List of CellAnalysis, sorted by viability (best first)
        """
        analyses = [self.analyze_cell(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_viability, reverse=True)
        return analyses


# =============================================================================
# Pre-defined cell configurations for testing
# =============================================================================

STANDARD_LFP_CELL = CellConfiguration(
    name='Standard LFP Cell',
    cathode='LFP',
    anode='Graphite',
    electrolyte_salt='LiPF6',
    electrolyte_solvents=['EC', 'DMC'],
    notes='Mature, safe chemistry (BYD Blade)',
)

STANDARD_NMC811_CELL = CellConfiguration(
    name='NMC811 EV Cell',
    cathode='NMC811',
    anode='Graphite',
    electrolyte_salt='LiPF6',
    electrolyte_solvents=['EC', 'EMC'],
    notes='High energy density EV cell',
)

SOLID_STATE_CELL = CellConfiguration(
    name='Solid-State LFP/LLZO',
    cathode='LFP',
    anode='Li_metal',
    electrolyte_salt='LiPF6',  # May not be needed with SE
    solid_electrolyte='LLZO',
    notes='Solid-state with garnet electrolyte',
)

PROBLEMATIC_SI_CELL = CellConfiguration(
    name='Si Anode Cell (problematic)',
    cathode='NMC811',
    anode='Si',
    electrolyte_salt='LiPF6',
    electrolyte_solvents=['EC', 'DMC'],
    notes='High energy but severe cycling degradation',
)

PROBLEMATIC_LGPS_CELL = CellConfiguration(
    name='LGPS + NMC811 (unstable)',
    cathode='NMC811',
    anode='Graphite',
    electrolyte_salt='LiPF6',
    solid_electrolyte='LGPS',
    notes='LGPS decomposes at NMC811 voltage',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Battery Flow Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = BatteryFlowAnalyzer()

    cells = [
        STANDARD_LFP_CELL,
        STANDARD_NMC811_CELL,
        SOLID_STATE_CELL,
        PROBLEMATIC_SI_CELL,
        PROBLEMATIC_LGPS_CELL,
    ]

    for config in cells:
        analysis = analyzer.analyze_cell(config)
        print(f"--- {analysis.cell_name} ---")
        print(f"  Viability: {analysis.overall_viability:.3f}  Viable: {analysis.viable}")
        if analysis.cell_voltage:
            print(f"  Cell voltage: {analysis.cell_voltage:.2f} V")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.material_a}<->{bn.material_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_cascades:
            print(f"  Degradation cascades: {len(analysis.degradation_cascades)}")
            for dc in analysis.degradation_cascades[:2]:
                print(f"    - {dc.trigger_failure}: {dc.consequence[:80]}...")
        if analysis.warnings:
            for w in analysis.warnings:
                print(f"  WARNING: {w}")
        print()
