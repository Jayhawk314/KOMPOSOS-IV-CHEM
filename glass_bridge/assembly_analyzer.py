# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Glass Assembly Analysis
=========================

Compositional chain analysis for complete glass assembly configurations.
Analogous to ceramic_bridge/assembly_analyzer.py.

Given a candidate glass assembly (primary + secondary glasses + coatings), it:
1. Enumerates all pairwise interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation risk paths
5. Scores overall assembly viability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from glass_bridge.material_properties import (
    GlassMaterial, GlassClass, GlassFailureMode, CompositionType,
    get_glass, ALL_GLASSES,
)
from glass_bridge.interface_validator import (
    GlassInterfaceValidator, GlassInterfaceScore,
    GlassConditions, GlassWeights,
)


@dataclass
class GlassAssemblyConfiguration:
    """
    A candidate glass assembly configuration.

    Mirrors AssemblyConfiguration from ceramic_bridge.
    """
    name: str
    primary_glass: str                     # Base material
    secondary_glasses: List[str] = field(default_factory=list)
    coating_glasses: List[str] = field(default_factory=list)
    environment: str = "indoor"
    service_temp_C: Optional[float] = None
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the assembly."""
    glass_a: str
    glass_b: str
    score: GlassInterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationRisk:
    """A degradation risk in the assembly."""
    trigger_interface: str
    trigger_mode: str
    consequence: str
    secondary_effects: List[str] = field(default_factory=list)


@dataclass
class GlassAssemblyAnalysis:
    """
    Complete analysis of a glass assembly configuration.

    Mirrors AssemblyAnalysis from ceramic_bridge.
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
                f"{self.bottleneck.glass_a}<->{self.bottleneck.glass_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.glass_a}<->{ir.glass_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class GlassAssemblyAnalyzer:
    """
    Analyzes complete glass assembly configurations.

    Mirrors CeramicAssemblyAnalyzer pattern exactly.
    """

    def __init__(
        self,
        validator: Optional[GlassInterfaceValidator] = None,
        viability_threshold: float = 0.50,
    ):
        self.validator = validator or GlassInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_assembly(
        self,
        config: GlassAssemblyConfiguration,
        conditions: Optional[GlassConditions] = None,
    ) -> GlassAssemblyAnalysis:
        """
        Analyze a complete assembly configuration.

        Args:
            config: Assembly configuration to analyze
            conditions: Operating conditions (overrides config if given)

        Returns:
            GlassAssemblyAnalysis with full breakdown
        """
        if conditions is None:
            conditions = GlassConditions(environment=config.environment)
            if config.service_temp_C is not None:
                conditions.temperature_C = config.service_temp_C

        warnings = []

        # Resolve material objects
        primary = get_glass(config.primary_glass)
        secondaries = [get_glass(s) for s in config.secondary_glasses]
        coatings = [get_glass(c) for c in config.coating_glasses]

        if primary is None:
            warnings.append(f"Unknown primary glass: {config.primary_glass}")

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
                    glass_a=mat_a.formula,
                    glass_b=mat_b.formula,
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

        return GlassAssemblyAnalysis(
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
        primary: Optional[GlassMaterial],
        secondaries: List[GlassMaterial],
        coatings: List[GlassMaterial],
        interface_results: List[InterfaceResult],
        conditions: GlassConditions,
    ) -> List[DegradationRisk]:
        """Predict degradation risk paths."""
        risks = []
        all_mats = [m for m in [primary] if m]
        all_mats.extend(secondaries)
        all_mats.extend(coatings)

        # --- Risk 1: CTE mismatch cracking ---
        for ir in interface_results:
            if ir.score.thermal_expansion_match < 0.4:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.glass_a}<->{ir.glass_b}',
                    trigger_mode='cte_cracking',
                    consequence='CTE mismatch generates interfacial stress on cooling '
                                'from seal/anneal temperature; cracking at seal',
                    secondary_effects=['seal_failure', 'delamination', 'structural_failure'],
                ))

        # --- Risk 2: Viscosity incompatibility ---
        for ir in interface_results:
            if ir.score.viscosity_compatibility < 0.3:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.glass_a}<->{ir.glass_b}',
                    trigger_mode='viscosity_incompatibility',
                    consequence='No common working temperature range; cannot seal or fuse',
                    secondary_effects=['poor_seal_quality', 'incomplete_wetting', 'bubbling'],
                ))

        # --- Risk 3: Weathering ---
        weather_mats = [m for m in all_mats
                        if GlassFailureMode.WEATHERING in m.failure_modes]
        if weather_mats and conditions.environment in ("outdoor", "chemical"):
            risks.append(DegradationRisk(
                trigger_interface=f'{weather_mats[0].formula}<->environment',
                trigger_mode='weathering',
                consequence='Moisture and atmospheric attack degrades glass surface; '
                            'blooming, haze, surface corrosion',
                secondary_effects=['surface_bloom', 'haze', 'strength_reduction'],
            ))

        # --- Risk 4: Devitrification ---
        devit_mats = [m for m in all_mats
                      if GlassFailureMode.DEVITRIFICATION in m.failure_modes
                      or GlassFailureMode.CRYSTALLIZATION in m.failure_modes]
        if devit_mats:
            risks.append(DegradationRisk(
                trigger_interface=f'{devit_mats[0].formula}<->thermal_process',
                trigger_mode='devitrification',
                consequence='Crystallization during sealing/annealing; changes optical '
                            'and mechanical properties; scattering in optical path',
                secondary_effects=['opacity', 'strength_change', 'property_degradation'],
            ))

        # --- Risk 5: Solarization under UV ---
        if conditions.uv_exposure:
            solar_mats = [m for m in all_mats
                          if GlassFailureMode.SOLARIZATION in m.failure_modes]
            if solar_mats:
                risks.append(DegradationRisk(
                    trigger_interface=f'{solar_mats[0].formula}<->UV',
                    trigger_mode='solarization',
                    consequence='UV radiation causes color center formation; '
                                'transmission loss in UV-visible range',
                    secondary_effects=['transmission_loss', 'coloration'],
                ))

        return risks

    def compare_assemblies(
        self,
        configs: List[GlassAssemblyConfiguration],
        conditions: Optional[GlassConditions] = None,
    ) -> List[GlassAssemblyAnalysis]:
        """
        Analyze and rank multiple assembly configurations.

        Args:
            configs: List of assembly configurations
            conditions: Shared operating conditions

        Returns:
            List of GlassAssemblyAnalysis, sorted by compatibility (best first)
        """
        analyses = [self.analyze_assembly(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_compatibility, reverse=True)
        return analyses


# =============================================================================
# Pre-defined assembly configurations for testing
# =============================================================================

ACHROMATIC_DOUBLET = GlassAssemblyConfiguration(
    name='BK7 + F2 Achromatic Doublet',
    primary_glass='BK7',
    secondary_glasses=['F2'],
    environment='optical_clean',
    notes='Standard achromatic lens; crown + flint corrects chromatic aberration',
)

BOROSILICATE_GRADED_SEAL = GlassAssemblyConfiguration(
    name='Borosilicate Graded Seal',
    primary_glass='Boro_33',
    secondary_glasses=['Boro_51'],
    notes='Intermediate CTE step for graded glass-to-metal seals',
)

PRECISION_OPTICAL = GlassAssemblyConfiguration(
    name='Zerodur + Fused Silica Precision Assembly',
    primary_glass='LAS_Zerodur',
    secondary_glasses=['FusedSilica'],
    environment='optical_clean',
    notes='Ultra-low CTE assembly for precision optics / metrology',
)

SODA_LIME_ASSEMBLY = GlassAssemblyConfiguration(
    name='Soda-Lime Float + Container',
    primary_glass='SodaLime_Float',
    secondary_glasses=['SodaLime_Container'],
    notes='Same family; trivially compatible',
)

BIOACTIVE_ASSEMBLY = GlassAssemblyConfiguration(
    name='45S5 Bioglass + S53P4 Assembly',
    primary_glass='Bioglass_45S5',
    secondary_glasses=['S53P4'],
    environment='biomedical',
    notes='Two bioactive glasses; both designed for bone bonding',
)

CHALCOGENIDE_ASSEMBLY = GlassAssemblyConfiguration(
    name='As2S3 + Ge-Sb-Se IR Assembly',
    primary_glass='As2S3',
    secondary_glasses=['Ge28Sb12Se60'],
    notes='Chalcogenide doublet for mid-IR imaging',
)

PROBLEMATIC_FUSED_SODALIME = GlassAssemblyConfiguration(
    name='Fused Silica + Soda-Lime (CTE Mismatch)',
    primary_glass='FusedSilica',
    secondary_glasses=['SodaLime_Float'],
    notes='Extreme CTE mismatch: 0.55 vs 9.0 x10^-6/K',
)

PROBLEMATIC_CHALCO_BORO = GlassAssemblyConfiguration(
    name='As2S3 + Borosilicate (Incompatible)',
    primary_glass='As2S3',
    secondary_glasses=['Boro_33'],
    notes='Chalcogenide + oxide glass: incompatible chemistry and CTE',
)

PROBLEMATIC_ZBLAN_SODALIME = GlassAssemblyConfiguration(
    name='ZBLAN + Soda-Lime (Incompatible)',
    primary_glass='ZBLAN',
    secondary_glasses=['SodaLime_Float'],
    notes='Fluoride + silicate: incompatible glass networks',
)

PROBLEMATIC_BIOGLASS_FUSED = GlassAssemblyConfiguration(
    name='Bioglass + Fused Silica (CTE Mismatch)',
    primary_glass='Bioglass_45S5',
    secondary_glasses=['FusedSilica'],
    notes='Bioactive (CTE=15.1) + fused silica (CTE=0.55); bioglass dissolves intentionally',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Glass Assembly Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = GlassAssemblyAnalyzer()

    configs = [
        ACHROMATIC_DOUBLET,
        BOROSILICATE_GRADED_SEAL,
        PRECISION_OPTICAL,
        SODA_LIME_ASSEMBLY,
        BIOACTIVE_ASSEMBLY,
        PROBLEMATIC_FUSED_SODALIME,
        PROBLEMATIC_CHALCO_BORO,
        PROBLEMATIC_ZBLAN_SODALIME,
    ]

    for config in configs:
        analysis = analyzer.analyze_assembly(config)
        print(f"--- {analysis.assembly_name} ---")
        print(f"  Compatibility: {analysis.overall_compatibility:.3f}  "
              f"Compatible: {analysis.compatible}")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.glass_a}<->{bn.glass_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_risks:
            print(f"  Degradation risks: {len(analysis.degradation_risks)}")
        print()
