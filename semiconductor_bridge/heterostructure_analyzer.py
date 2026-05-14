# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Semiconductor Heterostructure Analysis
=========================================

Compositional chain analysis for complete semiconductor heterostructure
configurations. Analogous to ceramic_bridge/assembly_analyzer.py.

Given a candidate heterostructure (substrate + epitaxial layers), it:
1. Enumerates all pairwise interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation risk paths
5. Scores overall heterostructure viability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from semiconductor_bridge.material_properties import (
    SemiconductorMaterial, SemiconductorClass, SemiconductorFailureMode,
    get_semiconductor, ALL_SEMICONDUCTORS,
)
from semiconductor_bridge.interface_validator import (
    SemiconductorInterfaceValidator, SemiconductorInterfaceScore,
    SemiconductorConditions, SemiconductorWeights,
)


@dataclass
class HeterostructureConfiguration:
    """
    A candidate semiconductor heterostructure configuration.

    Mirrors AssemblyConfiguration from ceramic_bridge.
    """
    name: str
    substrate: str                          # Substrate material
    epitaxial_layers: List[str] = field(default_factory=list)
    buffer_layers: List[str] = field(default_factory=list)
    environment: str = "cleanroom"
    operating_temp_C: Optional[float] = None
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the heterostructure."""
    sc_a: str
    sc_b: str
    score: SemiconductorInterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationRisk:
    """A degradation risk in the heterostructure."""
    trigger_interface: str
    trigger_mode: str
    consequence: str
    secondary_effects: List[str] = field(default_factory=list)


@dataclass
class HeterostructureAnalysis:
    """
    Complete analysis of a semiconductor heterostructure configuration.

    Mirrors AssemblyAnalysis from ceramic_bridge.
    """
    heterostructure_name: str
    overall_compatibility: float    # 0-1 composite score
    compatible: bool                # Above threshold?
    interfaces: List[InterfaceResult]
    bottleneck: Optional[InterfaceResult]
    degradation_risks: List[DegradationRisk]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            'heterostructure_name': self.heterostructure_name,
            'overall_compatibility': round(self.overall_compatibility, 4),
            'compatible': self.compatible,
            'num_interfaces': len(self.interfaces),
            'bottleneck': (
                f"{self.bottleneck.sc_a}<->{self.bottleneck.sc_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.sc_a}<->{ir.sc_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class HeterostructureAnalyzer:
    """
    Analyzes complete semiconductor heterostructure configurations.

    Mirrors CeramicAssemblyAnalyzer pattern exactly.
    """

    def __init__(
        self,
        validator: Optional[SemiconductorInterfaceValidator] = None,
        viability_threshold: float = 0.45,
    ):
        self.validator = validator or SemiconductorInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_heterostructure(
        self,
        config: HeterostructureConfiguration,
        conditions: Optional[SemiconductorConditions] = None,
    ) -> HeterostructureAnalysis:
        """
        Analyze a complete heterostructure configuration.

        Args:
            config: Heterostructure configuration to analyze
            conditions: Operating conditions (overrides config.environment if given)

        Returns:
            HeterostructureAnalysis with full breakdown
        """
        if conditions is None:
            conditions = SemiconductorConditions(environment=config.environment)
            if config.operating_temp_C is not None:
                conditions.temperature_C = config.operating_temp_C

        warnings = []

        # Resolve material objects
        substrate = get_semiconductor(config.substrate)
        epi_layers = [get_semiconductor(s) for s in config.epitaxial_layers]
        buffers = [get_semiconductor(b) for b in config.buffer_layers]

        if substrate is None:
            warnings.append(f"Unknown substrate: {config.substrate}")

        epi_layers = [e for e in epi_layers if e is not None]
        buffers = [b for b in buffers if b is not None]

        # --- Enumerate all pairwise interfaces ---
        all_components = []
        if substrate:
            all_components.append(substrate)
        all_components.extend(buffers)
        all_components.extend(epi_layers)

        interface_pairs = []
        for i in range(len(all_components)):
            for j in range(i + 1, len(all_components)):
                interface_pairs.append((all_components[i], all_components[j]))

        # --- Score each interface ---
        interface_results = []
        for mat_a, mat_b in interface_pairs:
            try:
                score = self.validator.validate_materials(mat_a, mat_b, conditions)
                interface_results.append(InterfaceResult(
                    sc_a=mat_a.formula,
                    sc_b=mat_b.formula,
                    score=score,
                ))
            except Exception as e:
                warnings.append(
                    f"Failed to score {mat_a.formula}<->{mat_b.formula}: {e}"
                )

        # --- Find bottleneck ---
        bottleneck = None
        if interface_results:
            bottleneck = min(interface_results, key=lambda ir: ir.score.total)
            bottleneck.is_bottleneck = True

        # --- Predict degradation risks ---
        degradation_risks = self._predict_degradation_risks(
            substrate, epi_layers, buffers, interface_results, conditions
        )

        # --- Overall viability ---
        # Same formula: 75% bottleneck + 25% average
        if interface_results:
            min_score = bottleneck.score.total if bottleneck else 0
            avg_score = sum(ir.score.total for ir in interface_results) / len(interface_results)
            overall = 0.75 * min_score + 0.25 * avg_score
        else:
            if len(all_components) <= 1:
                overall = 1.0
            else:
                overall = 0.0
                warnings.append("No valid interfaces could be scored")

        return HeterostructureAnalysis(
            heterostructure_name=config.name,
            overall_compatibility=max(0.0, min(1.0, overall)),
            compatible=overall >= self.viability_threshold,
            interfaces=interface_results,
            bottleneck=bottleneck,
            degradation_risks=degradation_risks,
            warnings=warnings,
        )

    def _predict_degradation_risks(
        self,
        substrate: Optional[SemiconductorMaterial],
        epi_layers: List[SemiconductorMaterial],
        buffers: List[SemiconductorMaterial],
        interface_results: List[InterfaceResult],
        conditions: SemiconductorConditions,
    ) -> List[DegradationRisk]:
        """Predict degradation risk paths."""
        risks = []
        all_mats = [m for m in [substrate] if m]
        all_mats.extend(buffers)
        all_mats.extend(epi_layers)

        # --- Risk 1: Lattice mismatch dislocations ---
        for ir in interface_results:
            if ir.score.lattice_match < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.sc_a}<->{ir.sc_b}',
                    trigger_mode='lattice_mismatch_dislocations',
                    consequence='Misfit dislocations nucleate at interface; threading '
                                'dislocations propagate through epitaxial layers',
                    secondary_effects=['reduced_mobility', 'non-radiative_recombination',
                                       'leakage_current', 'device_degradation'],
                ))

        # --- Risk 2: Thermal mismatch cracking ---
        for ir in interface_results:
            if ir.score.thermal_compatibility < 0.5:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.sc_a}<->{ir.sc_b}',
                    trigger_mode='thermal_mismatch_cracking',
                    consequence='CTE mismatch generates stress during cooling from growth '
                                'temperature; wafer bow and cracking in thick layers',
                    secondary_effects=['wafer_bow', 'cracking', 'delamination'],
                ))

        # --- Risk 3: Dark line defect propagation ---
        dld_mats = [m for m in all_mats
                     if SemiconductorFailureMode.DARK_LINE_DEFECTS in m.failure_modes]
        if dld_mats:
            risks.append(DegradationRisk(
                trigger_interface=f'{dld_mats[0].formula}<->active_region',
                trigger_mode='dark_line_defects',
                consequence='Dark line defects propagate from misfit dislocations '
                            'under optical/electrical stress; catastrophic for lasers',
                secondary_effects=['laser_degradation', 'reduced_lifetime',
                                   'catastrophic_optical_damage'],
            ))

        # --- Risk 4: Moisture sensitivity ---
        moisture_mats = [m for m in all_mats
                         if SemiconductorFailureMode.MOISTURE_SENSITIVITY in m.failure_modes]
        if moisture_mats and conditions.humidity_pct > 60:
            risks.append(DegradationRisk(
                trigger_interface=f'{moisture_mats[0].formula}<->environment',
                trigger_mode='moisture_degradation',
                consequence='Moisture attacks exposed surfaces; particularly dangerous '
                            'for AlAs (oxidizes rapidly) and some nitrides',
                secondary_effects=['surface_oxidation', 'conductivity_loss',
                                   'interface_degradation'],
            ))

        # --- Risk 5: Process incompatibility ---
        for ir in interface_results:
            if ir.score.process_compatibility < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.sc_a}<->{ir.sc_b}',
                    trigger_mode='process_incompatibility',
                    consequence='Growth conditions incompatible; lower layer may degrade '
                                'during upper layer growth, or anti-phase domains form',
                    secondary_effects=['anti-phase_boundaries', 'poor_interface_quality',
                                       'interdiffusion'],
                ))

        return risks

    def compare_heterostructures(
        self,
        configs: List[HeterostructureConfiguration],
        conditions: Optional[SemiconductorConditions] = None,
    ) -> List[HeterostructureAnalysis]:
        """
        Analyze and rank multiple heterostructure configurations.

        Args:
            configs: List of heterostructure configurations
            conditions: Shared operating conditions

        Returns:
            List of HeterostructureAnalysis, sorted by compatibility (best first)
        """
        analyses = [self.analyze_heterostructure(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_compatibility, reverse=True)
        return analyses


# =============================================================================
# Pre-defined heterostructure configurations for testing
# =============================================================================

GAAS_ALGAAS_HEMT = HeterostructureConfiguration(
    name='GaAs/AlGaAs HEMT',
    substrate='GaAs',
    epitaxial_layers=['AlGaAs'],
    notes='Standard III-V HEMT; nearly lattice-matched (0.04%)',
)

INGAAS_INP_TELECOM = HeterostructureConfiguration(
    name='InGaAs/InP Telecom Detector',
    substrate='InP',
    epitaxial_layers=['InGaAs'],
    notes='Lattice-matched at In=0.53; 1.55um photodetectors and HBTs',
)

GAN_ALGAN_POWER = HeterostructureConfiguration(
    name='GaN/AlGaN Power HEMT',
    substrate='GaN',
    epitaxial_layers=['AlGaN'],
    environment='high_temp',
    operating_temp_C=200.0,
    notes='GaN HEMT for power electronics; 2DEG at interface',
)

SI_SIGE_BICMOS = HeterostructureConfiguration(
    name='Si/SiGe BiCMOS HBT',
    substrate='Si',
    epitaxial_layers=['SiGe'],
    notes='Strained SiGe on Si; standard BiCMOS for RF',
)

MOS2_WS2_2D = HeterostructureConfiguration(
    name='MoS2/WS2 2D Heterostructure',
    substrate='MoS2',
    epitaxial_layers=['WS2'],
    notes='van der Waals heterostructure; nearly lattice-matched TMDs',
)

SIC_GAN_POWER = HeterostructureConfiguration(
    name='SiC/GaN Power Device',
    substrate='SiC_4H',
    epitaxial_layers=['GaN', 'AlGaN'],
    environment='high_temp',
    operating_temp_C=250.0,
    notes='GaN-on-SiC for RF power amplifiers; good thermal conductivity',
)

PROBLEMATIC_GAAS_SI = HeterostructureConfiguration(
    name='GaAs on Si (Problematic)',
    substrate='Si',
    epitaxial_layers=['GaAs'],
    notes='4.1% lattice mismatch; anti-phase domains; high dislocation density',
)

PROBLEMATIC_INAS_GAP = HeterostructureConfiguration(
    name='InAs on GaP (Extreme Mismatch)',
    substrate='GaP',
    epitaxial_layers=['InAs'],
    notes='11.1% lattice mismatch; no viable epitaxial process',
)

PROBLEMATIC_GAN_GAAS = HeterostructureConfiguration(
    name='GaN on GaAs (Incompatible)',
    substrate='GaAs',
    epitaxial_layers=['GaN'],
    notes='Wurtzite on zincblende; ~20% a-lattice mismatch',
)

PROBLEMATIC_INSB_SI = HeterostructureConfiguration(
    name='InSb on Si (Extreme Mismatch)',
    substrate='Si',
    epitaxial_layers=['InSb'],
    notes='19.3% lattice mismatch; incompatible growth temps',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Semiconductor Heterostructure Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = HeterostructureAnalyzer()

    configs = [
        GAAS_ALGAAS_HEMT,
        INGAAS_INP_TELECOM,
        GAN_ALGAN_POWER,
        SI_SIGE_BICMOS,
        SIC_GAN_POWER,
        PROBLEMATIC_GAAS_SI,
        PROBLEMATIC_INAS_GAP,
        PROBLEMATIC_GAN_GAAS,
    ]

    for config in configs:
        analysis = analyzer.analyze_heterostructure(config)
        print(f"--- {analysis.heterostructure_name} ---")
        print(f"  Compatibility: {analysis.overall_compatibility:.3f}  "
              f"Compatible: {analysis.compatible}")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.sc_a}<->{bn.sc_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_risks:
            print(f"  Degradation risks: {len(analysis.degradation_risks)}")
            for dr in analysis.degradation_risks[:2]:
                print(f"    - {dr.trigger_mode}: {dr.consequence[:70]}...")
        print()
