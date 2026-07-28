# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Ceramic Assembly Analysis
=========================

Compositional chain analysis for complete ceramic assembly configurations.
Analogous to metal_bridge/joint_analyzer.py.

Given a candidate assembly (primary + secondary ceramics + coatings), it:
1. Enumerates all pairwise interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation risk paths
5. Scores overall assembly viability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ceramic_bridge.material_properties import (
    CeramicMaterial, CeramicClass, CeramicFailureMode,
    get_ceramic, ALL_CERAMICS,
)
from ceramic_bridge.interface_validator import (
    CeramicInterfaceValidator, CeramicInterfaceScore,
    CeramicConditions, CeramicWeights,
)


@dataclass
class AssemblyConfiguration:
    """
    A candidate ceramic assembly configuration.

    Mirrors JointConfiguration from metal_bridge.
    """
    name: str
    primary_ceramic: str                    # Base material
    secondary_ceramics: List[str] = field(default_factory=list)
    coating_ceramics: List[str] = field(default_factory=list)
    environment: str = "indoor"
    service_temp_C: Optional[float] = None
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the assembly."""
    ceramic_a: str
    ceramic_b: str
    score: CeramicInterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationRisk:
    """A degradation risk in the assembly."""
    trigger_interface: str
    trigger_mode: str
    consequence: str
    secondary_effects: List[str] = field(default_factory=list)


@dataclass
class AssemblyAnalysis:
    """
    Complete analysis of a ceramic assembly configuration.

    Mirrors JointAnalysis from metal_bridge.
    """
    assembly_name: str
    overall_compatibility: float    # 0-1 composite score
    compatible: bool                # Above threshold?
    interfaces: List[InterfaceResult]
    bottleneck: Optional[InterfaceResult]
    degradation_risks: List[DegradationRisk]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            'assembly_name': self.assembly_name,
            'overall_compatibility': round(self.overall_compatibility, 4),
            'compatible': self.compatible,
            'num_interfaces': len(self.interfaces),
            'bottleneck': (
                f"{self.bottleneck.ceramic_a}<->{self.bottleneck.ceramic_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.ceramic_a}<->{ir.ceramic_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class CeramicAssemblyAnalyzer:
    """
    Analyzes complete ceramic assembly configurations.

    Mirrors MetalJointAnalyzer pattern exactly.
    """

    def __init__(
        self,
        validator: Optional[CeramicInterfaceValidator] = None,
        viability_threshold: float = 0.45,
    ):
        self.validator = validator or CeramicInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_assembly(
        self,
        config: AssemblyConfiguration,
        conditions: Optional[CeramicConditions] = None,
    ) -> AssemblyAnalysis:
        """
        Analyze a complete assembly configuration.

        Args:
            config: Assembly configuration to analyze
            conditions: Operating conditions (overrides config.environment if given)

        Returns:
            AssemblyAnalysis with full breakdown
        """
        if conditions is None:
            conditions = CeramicConditions(environment=config.environment)
            if config.service_temp_C is not None:
                conditions.temperature_C = config.service_temp_C

        warnings = []

        # Resolve material objects
        primary = get_ceramic(config.primary_ceramic)
        secondaries = [get_ceramic(s) for s in config.secondary_ceramics]
        coatings = [get_ceramic(c) for c in config.coating_ceramics]

        if primary is None:
            warnings.append(f"Unknown primary ceramic: {config.primary_ceramic}")

        secondaries = [s for s in secondaries if s is not None]
        coatings = [c for c in coatings if c is not None]

        # --- Enumerate all pairwise interfaces ---
        all_components = []
        if primary:
            all_components.append(primary)
        all_components.extend(secondaries)
        all_components.extend(coatings)

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
                    ceramic_a=mat_a.formula,
                    ceramic_b=mat_b.formula,
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
            primary, secondaries, coatings, interface_results, conditions
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

        return AssemblyAnalysis(
            assembly_name=config.name,
            overall_compatibility=max(0.0, min(1.0, overall)),
            compatible=overall >= self.viability_threshold,
            interfaces=interface_results,
            bottleneck=bottleneck,
            degradation_risks=degradation_risks,
            warnings=warnings,
        )

    def _predict_degradation_risks(
        self,
        primary: Optional[CeramicMaterial],
        secondaries: List[CeramicMaterial],
        coatings: List[CeramicMaterial],
        interface_results: List[InterfaceResult],
        conditions: CeramicConditions,
    ) -> List[DegradationRisk]:
        """Predict degradation risk paths."""
        risks = []
        all_mats = [m for m in [primary] if m]
        all_mats.extend(secondaries)
        all_mats.extend(coatings)

        # --- Risk 1: CTE mismatch cracking ---
        for ir in interface_results:
            if ir.score.cte_match < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.ceramic_a}<->{ir.ceramic_b}',
                    trigger_mode='cte_cracking',
                    consequence='CTE mismatch generates interfacial stress on cooling; '
                                'cracking at interface during thermal cycling',
                    secondary_effects=['delamination', 'spallation', 'structural_failure'],
                ))

        # --- Risk 2: Sintering incompatibility ---
        for ir in interface_results:
            if ir.score.sintering_compatibility < 0.3:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.ceramic_a}<->{ir.ceramic_b}',
                    trigger_mode='sintering_incompatibility',
                    consequence='Cannot co-sinter; one material decomposes before other densifies',
                    secondary_effects=['poor_densification', 'weak_interface', 'porosity'],
                ))

        # --- Risk 3: Hydrolysis ---
        hygro = [m for m in all_mats
                 if CeramicFailureMode.HYDROLYSIS in m.failure_modes
                 or m.chemical_stability == 'hygroscopic']
        if hygro and conditions.humidity_pct > 60:
            risks.append(DegradationRisk(
                trigger_interface=f'{hygro[0].formula}<->environment',
                trigger_mode='hydrolysis',
                consequence='Moisture attack degrades material and interfaces; '
                            'particularly dangerous for AlN, MgO, sulfide SEs',
                secondary_effects=['surface_degradation', 'strength_loss', 'conductivity_loss'],
            ))

        # --- Risk 4: Thermal shock failure ---
        ts_susceptible = [m for m in all_mats
                          if CeramicFailureMode.THERMAL_SHOCK in m.failure_modes]
        if ts_susceptible and conditions.thermal_cycling:
            risks.append(DegradationRisk(
                trigger_interface=f'{ts_susceptible[0].formula}<->environment',
                trigger_mode='thermal_shock',
                consequence='Rapid temperature change causes catastrophic fracture; '
                            'ceramics with low toughness and high CTE most vulnerable',
                secondary_effects=['catastrophic_fracture', 'spallation'],
            ))

        # --- Risk 5: Chemical reaction at interface ---
        for ir in interface_results:
            if ir.score.chemical_compatibility < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.ceramic_a}<->{ir.ceramic_b}',
                    trigger_mode='interface_reaction',
                    consequence='Phase reaction at interface during sintering or service; '
                                'new phases may be weak or porous',
                    secondary_effects=['new_phase_formation', 'interface_weakness', 'property_degradation'],
                ))

        return risks

    def compare_assemblies(
        self,
        configs: List[AssemblyConfiguration],
        conditions: Optional[CeramicConditions] = None,
    ) -> List[AssemblyAnalysis]:
        """
        Analyze and rank multiple assembly configurations.

        Args:
            configs: List of assembly configurations
            conditions: Shared operating conditions

        Returns:
            List of AssemblyAnalysis, sorted by compatibility (best first)
        """
        analyses = [self.analyze_assembly(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_compatibility, reverse=True)
        return analyses


# =============================================================================
# Pre-defined assembly configurations for testing
# =============================================================================

ALUMINA_ZIRCONIA_COMPOSITE = AssemblyConfiguration(
    name='Alumina + Zirconia Composite (ZTA)',
    primary_ceramic='Al2O3',
    secondary_ceramics=['ZrO2_YSZ'],
    notes='Zirconia-toughened alumina; standard structural composite',
)

SIC_SI3N4_COMPOSITE = AssemblyConfiguration(
    name='SiC + Si3N4 High-Temp Composite',
    primary_ceramic='SiC',
    secondary_ceramics=['Si3N4'],
    environment='furnace',
    service_temp_C=1200.0,
    notes='Non-oxide composite for high-temperature structural use',
)

ALUMINA_SUBSTRATE = AssemblyConfiguration(
    name='Alumina Substrate + TiN Coating',
    primary_ceramic='Al2O3',
    coating_ceramics=['TiN'],
    notes='Cutting tool: alumina substrate with hard TiN coating',
)

DENTAL_ZIRCONIA = AssemblyConfiguration(
    name='Zirconia Dental Restoration',
    primary_ceramic='ZrO2_YSZ',
    secondary_ceramics=['Al2O3'],
    environment='biomedical',
    notes='Dental crown: YSZ framework with alumina sub-structure',
)

SOLID_STATE_BATTERY = AssemblyConfiguration(
    name='LLZO Solid-State Battery Interface',
    primary_ceramic='LLZO',
    secondary_ceramics=['Al2O3'],
    notes='Oxide solid electrolyte with alumina scaffold',
)

PROBLEMATIC_SIO2_MGO = AssemblyConfiguration(
    name='SiO2 + MgO (CTE Mismatch)',
    primary_ceramic='SiO2',
    secondary_ceramics=['MgO'],
    notes='Extreme CTE mismatch (0.55 vs 13.5); MgO is hygroscopic',
)

PROBLEMATIC_LGPS_OXIDE = AssemblyConfiguration(
    name='LGPS + Al2O3 (Incompatible)',
    primary_ceramic='LGPS',
    secondary_ceramics=['Al2O3'],
    notes='Sulfide SE + oxide: decomposition, extreme mechanical mismatch',
)

PROBLEMATIC_BIOGLASS_SIC = AssemblyConfiguration(
    name='Bioglass + SiC (Incompatible)',
    primary_ceramic='Bioglass',
    secondary_ceramics=['SiC'],
    notes='Cannot co-sinter; extreme sintering temp mismatch',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Ceramic Assembly Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = CeramicAssemblyAnalyzer()

    assemblies = [
        ALUMINA_ZIRCONIA_COMPOSITE,
        SIC_SI3N4_COMPOSITE,
        ALUMINA_SUBSTRATE,
        DENTAL_ZIRCONIA,
        SOLID_STATE_BATTERY,
        PROBLEMATIC_SIO2_MGO,
        PROBLEMATIC_LGPS_OXIDE,
        PROBLEMATIC_BIOGLASS_SIC,
    ]

    for config in assemblies:
        analysis = analyzer.analyze_assembly(config)
        print(f"--- {analysis.assembly_name} ---")
        print(f"  Compatibility: {analysis.overall_compatibility:.3f}  "
              f"Compatible: {analysis.compatible}")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.ceramic_a}<->{bn.ceramic_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_risks:
            print(f"  Degradation risks: {len(analysis.degradation_risks)}")
            for dr in analysis.degradation_risks[:2]:
                print(f"    - {dr.trigger_mode}: {dr.consequence[:70]}...")
        if analysis.warnings:
            for w in analysis.warnings:
                print(f"  WARNING: {w}")
        print()
