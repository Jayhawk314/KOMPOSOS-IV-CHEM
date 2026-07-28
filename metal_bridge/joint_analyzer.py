# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Metal Joint Analysis
=========================

Compositional chain analysis for complete metal joint/assembly configurations.
Analogous to polymer_bridge/blend_analyzer.py.

Given a candidate joint (primary + secondary metals + fillers), it:
1. Enumerates all pairwise interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation risk paths
5. Scores overall joint viability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from metal_bridge.material_properties import (
    MetalMaterial, MetalClass, MetalFailureMode,
    get_metal, ALL_METALS,
)
from metal_bridge.interface_validator import (
    MetalInterfaceValidator, MetalInterfaceScore,
    MetalConditions, MetalWeights,
)


@dataclass
class JointConfiguration:
    """
    A candidate metal joint/assembly configuration.

    Mirrors BlendConfiguration from polymer_bridge.
    """
    name: str
    primary_metal: str                  # Base material
    secondary_metals: List[str] = field(default_factory=list)
    filler_metals: List[str] = field(default_factory=list)  # Weld/braze filler
    environment: str = "indoor"
    service_temp_C: Optional[float] = None
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the joint."""
    metal_a: str
    metal_b: str
    score: MetalInterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationRisk:
    """A degradation risk in the joint."""
    trigger_interface: str
    trigger_mode: str
    consequence: str
    secondary_effects: List[str] = field(default_factory=list)


@dataclass
class JointAnalysis:
    """
    Complete analysis of a metal joint/assembly configuration.

    Mirrors BlendAnalysis from polymer_bridge.
    """
    joint_name: str
    overall_compatibility: float    # 0-1 composite score
    compatible: bool                # Above threshold?
    interfaces: List[InterfaceResult]
    bottleneck: Optional[InterfaceResult]
    degradation_risks: List[DegradationRisk]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            'joint_name': self.joint_name,
            'overall_compatibility': round(self.overall_compatibility, 4),
            'compatible': self.compatible,
            'num_interfaces': len(self.interfaces),
            'bottleneck': (
                f"{self.bottleneck.metal_a}<->{self.bottleneck.metal_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.metal_a}<->{ir.metal_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class MetalJointAnalyzer:
    """
    Analyzes complete metal joint configurations by tracing all interfaces.

    Mirrors PolymerBlendAnalyzer pattern exactly.
    """

    def __init__(
        self,
        validator: Optional[MetalInterfaceValidator] = None,
        viability_threshold: float = 0.45,
    ):
        self.validator = validator or MetalInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_joint(
        self,
        config: JointConfiguration,
        conditions: Optional[MetalConditions] = None,
    ) -> JointAnalysis:
        """
        Analyze a complete joint configuration.

        Args:
            config: Joint configuration to analyze
            conditions: Operating conditions (overrides config.environment if given)

        Returns:
            JointAnalysis with full breakdown
        """
        if conditions is None:
            conditions = MetalConditions(environment=config.environment)
            if config.service_temp_C is not None:
                conditions.temperature_C = config.service_temp_C

        warnings = []

        # Resolve material objects
        primary = get_metal(config.primary_metal)
        secondaries = [get_metal(s) for s in config.secondary_metals]
        fillers = [get_metal(f) for f in config.filler_metals]

        if primary is None:
            warnings.append(f"Unknown primary metal: {config.primary_metal}")

        secondaries = [s for s in secondaries if s is not None]
        fillers = [f for f in fillers if f is not None]

        # --- Enumerate all pairwise interfaces ---
        all_components = []
        if primary:
            all_components.append(primary)
        all_components.extend(secondaries)
        all_components.extend(fillers)

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
                    metal_a=mat_a.formula,
                    metal_b=mat_b.formula,
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
            primary, secondaries, fillers, interface_results, conditions
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

        return JointAnalysis(
            joint_name=config.name,
            overall_compatibility=max(0.0, min(1.0, overall)),
            compatible=overall >= self.viability_threshold,
            interfaces=interface_results,
            bottleneck=bottleneck,
            degradation_risks=degradation_risks,
            warnings=warnings,
        )

    def _predict_degradation_risks(
        self,
        primary: Optional[MetalMaterial],
        secondaries: List[MetalMaterial],
        fillers: List[MetalMaterial],
        interface_results: List[InterfaceResult],
        conditions: MetalConditions,
    ) -> List[DegradationRisk]:
        """Predict degradation risk paths."""
        risks = []
        all_mats = [m for m in [primary] if m]
        all_mats.extend(secondaries)
        all_mats.extend(fillers)

        # --- Risk 1: Galvanic corrosion cascade ---
        for ir in interface_results:
            if ir.score.galvanic_compatibility < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.metal_a}<->{ir.metal_b}',
                    trigger_mode='galvanic_corrosion',
                    consequence='Large potential difference drives galvanic corrosion; '
                                'anode corrodes preferentially',
                    secondary_effects=['material_loss', 'pit_formation', 'structural_weakening'],
                ))

        # --- Risk 2: Thermal fatigue from CTE mismatch ---
        for ir in interface_results:
            if ir.score.thermal_compatibility < 0.5:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.metal_a}<->{ir.metal_b}',
                    trigger_mode='thermal_fatigue',
                    consequence='CTE mismatch generates interfacial stress during thermal cycling; '
                                'fatigue cracking at joint',
                    secondary_effects=['crack_initiation', 'delamination', 'joint_failure'],
                ))

        # --- Risk 3: Hydrogen embrittlement ---
        h2_susceptible = [m for m in all_mats
                          if MetalFailureMode.HYDROGEN_EMBRITTLEMENT in m.failure_modes]
        if h2_susceptible:
            risks.append(DegradationRisk(
                trigger_interface=f'{h2_susceptible[0].formula}<->environment',
                trigger_mode='hydrogen_embrittlement',
                consequence='Hydrogen absorption causes delayed cracking; '
                            'particularly dangerous for high-strength steels',
                secondary_effects=['delayed_fracture', 'reduced_ductility'],
            ))

        # --- Risk 4: Stress corrosion cracking ---
        scc_susceptible = [m for m in all_mats
                           if MetalFailureMode.STRESS_CORROSION_CRACKING in m.failure_modes]
        if scc_susceptible and conditions.environment in ("marine", "industrial"):
            risks.append(DegradationRisk(
                trigger_interface=f'{scc_susceptible[0].formula}<->environment',
                trigger_mode='stress_corrosion_cracking',
                consequence=f'SCC risk in {conditions.environment} environment; '
                            f'combined stress + corrosion causes cracking',
                secondary_effects=['brittle_fracture', 'crack_propagation'],
            ))

        # --- Risk 5: Intermetallic formation during welding ---
        for ir in interface_results:
            if ir.score.metallurgical_compatibility < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.metal_a}<->{ir.metal_b}',
                    trigger_mode='intermetallic_formation',
                    consequence='Brittle intermetallic compounds form at interface during '
                                'welding or high-temperature service',
                    secondary_effects=['embrittlement', 'reduced_toughness', 'joint_weakness'],
                ))

        return risks

    def compare_joints(
        self,
        configs: List[JointConfiguration],
        conditions: Optional[MetalConditions] = None,
    ) -> List[JointAnalysis]:
        """
        Analyze and rank multiple joint configurations.

        Args:
            configs: List of joint configurations
            conditions: Shared operating conditions

        Returns:
            List of JointAnalysis, sorted by compatibility (best first)
        """
        analyses = [self.analyze_joint(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_compatibility, reverse=True)
        return analyses


# =============================================================================
# Pre-defined joint configurations for testing
# =============================================================================

STANDARD_SS_WELD = JointConfiguration(
    name='304SS + 316SS Weld',
    primary_metal='SS_304',
    secondary_metals=['SS_316'],
    notes='Same austenitic family; standard industrial weld',
)

STEEL_STRUCTURE = JointConfiguration(
    name='Mild Steel + 4140 Structure',
    primary_metal='Steel_1018',
    secondary_metals=['Steel_4140'],
    notes='Carbon steel + alloy steel structural joint',
)

ALUMINUM_AIRFRAME = JointConfiguration(
    name='Aluminum Airframe Assembly',
    primary_metal='Al_2024',
    secondary_metals=['Al_7075'],
    notes='Aerospace aluminum assembly; riveted',
)

TI_ASSEMBLY = JointConfiguration(
    name='Ti-6Al-4V + CP Ti Assembly',
    primary_metal='Ti6Al4V',
    secondary_metals=['CP_Ti_Gr2'],
    notes='Titanium assembly; fully compatible',
)

BATTERY_CURRENT_COLLECTORS = JointConfiguration(
    name='Battery Current Collectors',
    primary_metal='Al_foil',
    secondary_metals=['Cu_foil'],
    filler_metals=['Ni_tab'],
    notes='Li-ion battery current collector assembly with Ni tab',
)

PROBLEMATIC_CU_AL = JointConfiguration(
    name='Cu + Al Joint (Galvanic Risk)',
    primary_metal='Cu',
    secondary_metals=['Al'],
    notes='Known galvanic couple; intermetallics form; requires insulation',
)

PROBLEMATIC_MG_STEEL = JointConfiguration(
    name='Mg + Steel (Extreme Galvanic)',
    primary_metal='Mg',
    secondary_metals=['Steel_1018'],
    notes='Extreme galvanic couple; Mg is sacrificial anode',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Metal Joint Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = MetalJointAnalyzer()

    joints = [
        STANDARD_SS_WELD,
        STEEL_STRUCTURE,
        ALUMINUM_AIRFRAME,
        TI_ASSEMBLY,
        BATTERY_CURRENT_COLLECTORS,
        PROBLEMATIC_CU_AL,
        PROBLEMATIC_MG_STEEL,
    ]

    for config in joints:
        analysis = analyzer.analyze_joint(config)
        print(f"--- {analysis.joint_name} ---")
        print(f"  Compatibility: {analysis.overall_compatibility:.3f}  "
              f"Compatible: {analysis.compatible}")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.metal_a}<->{bn.metal_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_risks:
            print(f"  Degradation risks: {len(analysis.degradation_risks)}")
            for dr in analysis.degradation_risks[:2]:
                print(f"    - {dr.trigger_mode}: {dr.consequence[:70]}...")
        if analysis.warnings:
            for w in analysis.warnings:
                print(f"  WARNING: {w}")
        print()
