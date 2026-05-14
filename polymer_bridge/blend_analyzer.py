# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Polymer Blend Analysis
=========================

Compositional chain analysis for complete polymer blend configurations.
Analogous to battery_bridge/battery_flow.py which traces electrochemical
interfaces through a full battery cell.

Given a candidate blend (primary + secondary polymers + additives), it:
1. Enumerates all pairwise interfaces
2. Validates each interface
3. Identifies the weakest interface (bottleneck)
4. Predicts degradation risk paths
5. Scores overall blend viability
6. Estimates blend Tg via Fox equation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from polymer_bridge.material_properties import (
    PolymerMaterial, PolymerClass, PolymerFailureMode,
    get_polymer, ALL_POLYMERS,
)
from polymer_bridge.interface_validator import (
    PolymerInterfaceValidator, PolymerInterfaceScore,
    PolymerConditions, PolymerWeights,
)


@dataclass
class BlendConfiguration:
    """
    A candidate polymer blend configuration.

    Mirrors CellConfiguration from battery_bridge.
    """
    name: str
    primary_polymer: str           # Main polymer component
    secondary_polymers: List[str] = field(default_factory=list)
    additives: List[str] = field(default_factory=list)
    processing_temp_C: Optional[float] = None
    notes: str = ""


@dataclass
class InterfaceResult:
    """Result for a single interface in the blend."""
    polymer_a: str
    polymer_b: str
    score: PolymerInterfaceScore
    is_bottleneck: bool = False


@dataclass
class DegradationRisk:
    """A degradation risk in the blend."""
    trigger_interface: str
    trigger_mode: str
    consequence: str
    secondary_effects: List[str] = field(default_factory=list)


@dataclass
class BlendAnalysis:
    """
    Complete analysis of a polymer blend configuration.

    Mirrors CellAnalysis from battery_bridge.
    """
    blend_name: str
    overall_compatibility: float    # 0-1 composite score
    compatible: bool                # Above threshold?
    interfaces: List[InterfaceResult]
    bottleneck: Optional[InterfaceResult]
    degradation_risks: List[DegradationRisk]
    estimated_tg_C: Optional[float]  # Fox equation estimate
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            'blend_name': self.blend_name,
            'overall_compatibility': round(self.overall_compatibility, 4),
            'compatible': self.compatible,
            'num_interfaces': len(self.interfaces),
            'bottleneck': (
                f"{self.bottleneck.polymer_a}<->{self.bottleneck.polymer_b} "
                f"(score={self.bottleneck.score.total:.3f})"
                if self.bottleneck else None
            ),
            'estimated_tg_C': round(self.estimated_tg_C, 1) if self.estimated_tg_C is not None else None,
            'warnings': self.warnings,
            'interface_scores': {
                f"{ir.polymer_a}<->{ir.polymer_b}": round(ir.score.total, 3)
                for ir in self.interfaces
            },
        }


class PolymerBlendAnalyzer:
    """
    Analyzes complete polymer blend configurations by tracing all interfaces.

    Mirrors BatteryFlowAnalyzer pattern exactly.
    """

    def __init__(
        self,
        validator: Optional[PolymerInterfaceValidator] = None,
        viability_threshold: float = 0.45,
    ):
        self.validator = validator or PolymerInterfaceValidator()
        self.viability_threshold = viability_threshold

    def analyze_blend(
        self,
        config: BlendConfiguration,
        conditions: Optional[PolymerConditions] = None,
    ) -> BlendAnalysis:
        """
        Analyze a complete blend configuration.

        Steps:
        1. Enumerate all pairwise interfaces
        2. Score each interface
        3. Find bottleneck
        4. Predict degradation risks
        5. Estimate blend Tg
        6. Compute overall viability

        Args:
            config: Blend configuration to analyze
            conditions: Operating conditions

        Returns:
            BlendAnalysis with full breakdown
        """
        conditions = conditions or PolymerConditions()
        warnings = []

        # Resolve material objects
        primary = get_polymer(config.primary_polymer)
        secondaries = [get_polymer(s) for s in config.secondary_polymers]
        additives = [get_polymer(a) for a in config.additives]

        if primary is None:
            warnings.append(f"Unknown primary polymer: {config.primary_polymer}")

        secondaries = [s for s in secondaries if s is not None]
        additives = [a for a in additives if a is not None]

        # --- Enumerate all pairwise interfaces ---
        all_components = []
        if primary:
            all_components.append(primary)
        all_components.extend(secondaries)
        all_components.extend(additives)

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
                    polymer_a=mat_a.abbreviation,
                    polymer_b=mat_b.abbreviation,
                    score=score,
                ))
            except Exception as e:
                warnings.append(
                    f"Failed to score {mat_a.abbreviation}<->{mat_b.abbreviation}: {e}"
                )

        # --- Find bottleneck (lowest scoring interface) ---
        bottleneck = None
        if interface_results:
            bottleneck = min(interface_results, key=lambda ir: ir.score.total)
            bottleneck.is_bottleneck = True

        # --- Predict degradation risks ---
        degradation_risks = self._predict_degradation_risks(
            primary, secondaries, additives, interface_results
        )

        # --- Estimate blend Tg via Fox equation ---
        estimated_tg = self._estimate_blend_tg(primary, secondaries + additives)

        # --- Overall viability ---
        # Same formula as battery bridge: 75% bottleneck + 25% average
        if interface_results:
            min_score = bottleneck.score.total if bottleneck else 0
            avg_score = sum(ir.score.total for ir in interface_results) / len(interface_results)
            overall = 0.75 * min_score + 0.25 * avg_score
        else:
            if len(all_components) <= 1:
                overall = 1.0  # Single component: trivially compatible
            else:
                overall = 0.0
                warnings.append("No valid interfaces could be scored")

        return BlendAnalysis(
            blend_name=config.name,
            overall_compatibility=max(0.0, min(1.0, overall)),
            compatible=overall >= self.viability_threshold,
            interfaces=interface_results,
            bottleneck=bottleneck,
            degradation_risks=degradation_risks,
            estimated_tg_C=estimated_tg,
            warnings=warnings,
        )

    def _estimate_blend_tg(
        self,
        primary: Optional[PolymerMaterial],
        secondaries: List[PolymerMaterial],
    ) -> Optional[float]:
        """
        Estimate blend Tg using Fox equation.

        1/Tg_blend = w1/Tg1 + w2/Tg2 (in Kelvin)

        Assumes equal weight fractions for simplicity.
        Only works for miscible blends.
        """
        components = []
        if primary and primary.glass_transition_C is not None:
            components.append(primary.glass_transition_C)
        for s in secondaries:
            if s.glass_transition_C is not None:
                components.append(s.glass_transition_C)

        if len(components) < 2:
            return components[0] if components else None

        # Fox equation: 1/Tg = sum(wi/Tgi) where Tgi in Kelvin
        n = len(components)
        weight = 1.0 / n  # Equal weight fractions
        try:
            inv_tg_sum = sum(weight / (tg + 273.15) for tg in components)
            tg_blend_K = 1.0 / inv_tg_sum
            return round(tg_blend_K - 273.15, 1)
        except ZeroDivisionError:
            return None

    def _predict_degradation_risks(
        self,
        primary: Optional[PolymerMaterial],
        secondaries: List[PolymerMaterial],
        additives: List[PolymerMaterial],
        interface_results: List[InterfaceResult],
    ) -> List[DegradationRisk]:
        """Predict degradation risk paths."""
        risks = []
        all_mats = [m for m in [primary] if m]
        all_mats.extend(secondaries)
        all_mats.extend(additives)

        # --- Risk 1: UV degradation cascade ---
        uv_sensitive = [m for m in all_mats
                        if PolymerFailureMode.UV_DEGRADATION in m.failure_modes]
        if len(uv_sensitive) >= 2:
            risks.append(DegradationRisk(
                trigger_interface='blend_surface',
                trigger_mode='uv_degradation',
                consequence='UV exposure degrades multiple components; '
                            'chain scission and crosslinking compete',
                secondary_effects=['yellowing', 'embrittlement', 'surface_cracking'],
            ))

        # --- Risk 2: Hydrolysis cascade ---
        hydrolytic = [m for m in all_mats
                      if PolymerFailureMode.HYDROLYSIS in m.failure_modes]
        if hydrolytic:
            risks.append(DegradationRisk(
                trigger_interface=f'{hydrolytic[0].abbreviation}<->moisture',
                trigger_mode='hydrolysis',
                consequence='Moisture absorption leads to chain scission; '
                            'mechanical property loss over time',
                secondary_effects=['molecular_weight_loss', 'crazing'],
            ))

        # --- Risk 3: Thermal degradation during processing ---
        if primary:
            for s in secondaries:
                td_min = None
                if primary.decomposition_temp_C and s.decomposition_temp_C:
                    td_min = min(primary.decomposition_temp_C, s.decomposition_temp_C)
                process_t = None
                if primary.melting_point_C:
                    process_t = primary.melting_point_C + 20
                elif s.melting_point_C:
                    process_t = s.melting_point_C + 20

                if td_min and process_t and process_t > td_min - 30:
                    risks.append(DegradationRisk(
                        trigger_interface=f'{primary.abbreviation}<->{s.abbreviation}',
                        trigger_mode='thermal_degradation',
                        consequence=f'Processing temp ({process_t}C) near decomposition '
                                    f'({td_min}C); risk of degradation during melt blending',
                        secondary_effects=['discoloration', 'gas_evolution', 'property_loss'],
                    ))

        # --- Risk 4: Delamination in immiscible blends ---
        for ir in interface_results:
            if ir.score.solubility_compatibility < 0.3:
                risks.append(DegradationRisk(
                    trigger_interface=f'{ir.polymer_a}<->{ir.polymer_b}',
                    trigger_mode='delamination',
                    consequence='Immiscible components phase-separate; '
                                'weak interface leads to delamination under stress',
                    secondary_effects=['interfacial_failure', 'reduced_toughness'],
                ))

        return risks

    def compare_blends(
        self,
        configs: List[BlendConfiguration],
        conditions: Optional[PolymerConditions] = None,
    ) -> List[BlendAnalysis]:
        """
        Analyze and rank multiple blend configurations.

        Args:
            configs: List of blend configurations
            conditions: Shared operating conditions

        Returns:
            List of BlendAnalysis, sorted by compatibility (best first)
        """
        analyses = [self.analyze_blend(cfg, conditions) for cfg in configs]
        analyses.sort(key=lambda a: a.overall_compatibility, reverse=True)
        return analyses


# =============================================================================
# Pre-defined blend configurations for testing
# =============================================================================

STANDARD_PEO_ELECTROLYTE = BlendConfiguration(
    name='PEO Polymer Electrolyte',
    primary_polymer='PEO',
    secondary_polymers=[],
    additives=['PMMA'],
    notes='PEO-based solid polymer electrolyte with PMMA for mechanical strength',
)

STANDARD_PVDF_BINDER = BlendConfiguration(
    name='PVDF Binder in NMP',
    primary_polymer='PVDF',
    secondary_polymers=[],
    additives=['NMP'],
    notes='Standard battery electrode binder dissolved in NMP solvent',
)

STANDARD_CMC_SBR_BINDER = BlendConfiguration(
    name='CMC+SBR Water-Based Binder',
    primary_polymer='CMC',
    secondary_polymers=['SBR'],
    additives=['Water'],
    notes='Eco-friendly water-based binder for graphite anodes',
)

ENGINEERING_BLEND = BlendConfiguration(
    name='PC+ABS Engineering Blend',
    primary_polymer='PC',
    secondary_polymers=['ABS'],
    notes='Common engineering blend for automotive and electronics',
)

PROBLEMATIC_PE_NYLON = BlendConfiguration(
    name='HDPE+Nylon (Immiscible)',
    primary_polymer='HDPE',
    secondary_polymers=['PA6'],
    notes='Known immiscible blend; requires maleic anhydride compatibilizer',
)

PROBLEMATIC_PTFE_BLEND = BlendConfiguration(
    name='PTFE+PS (Incompatible)',
    primary_polymer='PTFE',
    secondary_polymers=['PS'],
    notes='PTFE resists blending with virtually everything',
)


if __name__ == "__main__":
    print("=" * 70)
    print("Polymer Blend Analysis - Demo")
    print("=" * 70)
    print()

    analyzer = PolymerBlendAnalyzer()

    blends = [
        STANDARD_PEO_ELECTROLYTE,
        STANDARD_PVDF_BINDER,
        STANDARD_CMC_SBR_BINDER,
        ENGINEERING_BLEND,
        PROBLEMATIC_PE_NYLON,
        PROBLEMATIC_PTFE_BLEND,
    ]

    for config in blends:
        analysis = analyzer.analyze_blend(config)
        print(f"--- {analysis.blend_name} ---")
        print(f"  Compatibility: {analysis.overall_compatibility:.3f}  "
              f"Compatible: {analysis.compatible}")
        if analysis.estimated_tg_C is not None:
            print(f"  Estimated Tg: {analysis.estimated_tg_C:.1f} C")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.polymer_a}<->{bn.polymer_b} "
                  f"(score={bn.score.total:.3f})")
        if analysis.degradation_risks:
            print(f"  Degradation risks: {len(analysis.degradation_risks)}")
            for dr in analysis.degradation_risks[:2]:
                print(f"    - {dr.trigger_mode}: {dr.consequence[:70]}...")
        if analysis.warnings:
            for w in analysis.warnings:
                print(f"  WARNING: {w}")
        print()
