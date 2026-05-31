# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Multi-Domain Analyzer
======================

The replicator brain. Takes components from ANY bridge domain and produces
a unified compatibility analysis spanning all relevant bridges and functors.

Example query:
    "NMC811 cathode + LLZO electrolyte + PEO coating + Cu collector"
    -> battery scores NMC811<->LLZO
    -> battery_polymer scores PEO<->NMC811
    -> battery_metal scores Cu<->NMC811
    -> ceramic_metal scores LLZO<->Cu
    -> unified report with bottleneck, warnings, overall viability
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# Physical adjacency for a battery cell, by component ROLE. A real cell is a
# layered stack:
#   cathode_collector -- cathode -- electrolyte -- anode -- anode_collector
# with binder mixed into both electrode coatings. Only components that are
# physically in contact share an interface; e.g. the cathode-side (Al) collector
# never touches the anode. Passing this as MultiDomainQuery.adjacency restricts
# scoring to real interfaces and drops phantom ones (the Al<->anode bottleneck).
BATTERY_CELL_ADJACENCY: Set[FrozenSet[str]] = {
    frozenset({"cathode_collector", "cathode"}),
    frozenset({"cathode_collector", "electrolyte"}),
    frozenset({"anode_collector", "anode"}),
    frozenset({"anode_collector", "electrolyte"}),
    frozenset({"binder", "cathode"}),
    frozenset({"binder", "anode"}),
    frozenset({"binder", "electrolyte"}),
    frozenset({"cathode", "electrolyte"}),
    frozenset({"anode", "electrolyte"}),
}

from cross_bridge.battery_polymer import (
    score_polymer_electrode_compatibility,
    BatteryPolymerResult,
)
from cross_bridge.battery_metal import (
    score_collector_compatibility,
    BatteryMetalResult,
)
from cross_bridge.ceramic_metal import (
    score_coating_compatibility,
    CeramicMetalResult,
)


# ============================================================================
# Domain registry: maps material names to their bridge domain
# ============================================================================

def _build_domain_registry() -> Dict[str, str]:
    """Build a lookup from material name -> domain string."""
    registry = {}

    try:
        from battery_bridge.material_properties import ALL_MATERIALS as BAT
        for name in BAT:
            registry[name] = 'battery'
    except ImportError:
        pass

    try:
        from polymer_bridge.material_properties import ALL_POLYMERS as POLY
        for name in POLY:
            registry[name] = 'polymer'
    except ImportError:
        pass

    try:
        from ceramic_bridge.material_properties import ALL_CERAMICS as CER
        for name in CER:
            registry[name] = 'ceramic'
    except ImportError:
        pass

    try:
        from metal_bridge.material_properties import ALL_METALS as MET
        for name in MET:
            registry[name] = 'metal'
    except ImportError:
        pass

    try:
        from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS as SEMI
        for name in SEMI:
            registry[name] = 'semiconductor'
    except ImportError:
        pass

    try:
        from glass_bridge.material_properties import ALL_GLASSES as GLASS
        for name in GLASS:
            registry[name] = 'glass'
    except ImportError:
        pass

    return registry


@dataclass
class MultiDomainComponent:
    """A component in a multi-domain query."""
    name: str
    role: str = ""  # e.g., "cathode", "collector", "coating", "electrolyte"
    domain: str = ""  # auto-detected or user-specified


@dataclass
class CrossDomainScore:
    """Score for a single cross-domain interface."""
    component_a: str
    component_b: str
    domain_a: str
    domain_b: str
    functor_used: str       # e.g., "battery_polymer", "ceramic_metal"
    score: float
    compatible: bool
    warnings: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


@dataclass
class MultiDomainAnalysis:
    """
    Complete analysis spanning multiple material domains.
    This is the replicator's answer to a multi-domain query.
    """
    query_name: str
    components: List[MultiDomainComponent]
    domains_involved: List[str]
    cross_domain_scores: List[CrossDomainScore]
    overall_score: float        # 0-1 composite
    viable: bool                # Above threshold?
    bottleneck: Optional[CrossDomainScore]
    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            'query_name': self.query_name,
            'components': [
                {'name': c.name, 'role': c.role, 'domain': c.domain}
                for c in self.components
            ],
            'domains_involved': self.domains_involved,
            'overall_score': round(self.overall_score, 4),
            'viable': self.viable,
            'bottleneck': (
                f"{self.bottleneck.component_a}<->{self.bottleneck.component_b} "
                f"({self.bottleneck.functor_used}: {self.bottleneck.score:.3f})"
                if self.bottleneck else None
            ),
            'cross_domain_scores': {
                f"{s.component_a}<->{s.component_b}": {
                    'functor': s.functor_used,
                    'score': round(s.score, 3),
                    'compatible': s.compatible,
                }
                for s in self.cross_domain_scores
            },
            'warnings': self.warnings,
        }


@dataclass
class MultiDomainQuery:
    """
    A multi-domain query specification.

    Components can come from any bridge. The analyzer figures out which
    bridges and functors to use.
    """
    name: str
    components: List[MultiDomainComponent]
    electrolyte: Optional[str] = None   # For battery-metal functor
    viability_threshold: float = 0.50
    scoring_mode: Optional[str] = None  # "bottleneck" | "weighted" | None (auto)
    # Optional physical adjacency by ROLE (set of frozenset({role_a, role_b})).
    # When None (default), every cross-domain pair is scored (legacy behaviour).
    # When provided, only pairs whose roles are adjacent are scored — see
    # BATTERY_CELL_ADJACENCY.
    adjacency: Optional[Set[FrozenSet[str]]] = None


class MultiDomainAnalyzer:
    """
    Analyzes multi-domain material combinations.

    This is the core replicator reasoning engine. Given components from
    different material domains, it:
    1. Identifies which domain each component belongs to
    2. Determines which cross-domain functors apply
    3. Scores each cross-domain interface
    4. Identifies the bottleneck
    5. Produces a unified viability assessment
    """

    def __init__(self, viability_threshold: float = 0.50):
        self.viability_threshold = viability_threshold
        self._registry = _build_domain_registry()

    def identify_domain(self, material_name: str) -> str:
        """Identify which bridge domain a material belongs to."""
        return self._registry.get(material_name, 'unknown')

    def analyze(self, query: MultiDomainQuery) -> MultiDomainAnalysis:
        """
        Analyze a multi-domain query.

        Args:
            query: MultiDomainQuery with components from any bridges

        Returns:
            MultiDomainAnalysis with cross-domain scores and bottleneck
        """
        warnings = []
        scores = []

        # Step 1: Identify domains for each component
        for comp in query.components:
            if not comp.domain:
                comp.domain = self.identify_domain(comp.name)
            if comp.domain == 'unknown':
                warnings.append(f"Unknown domain for: {comp.name}")

        domains_involved = sorted(set(
            c.domain for c in query.components if c.domain != 'unknown'
        ))

        # Step 2: Find all cross-domain pairs and score them
        for i, comp_a in enumerate(query.components):
            for comp_b in query.components[i+1:]:
                if comp_a.domain == 'unknown' or comp_b.domain == 'unknown':
                    continue

                # Physical adjacency filter (opt-in): skip pairs that are not in
                # contact (e.g. cathode-side collector vs anode).
                if query.adjacency is not None and \
                        frozenset({comp_a.role, comp_b.role}) not in query.adjacency:
                    continue

                # Try each functor that applies to this domain pair
                result = self._try_score_pair(
                    comp_a, comp_b, query.electrolyte
                )
                if result is not None:
                    scores.append(result)

        # Step 3: Find bottleneck
        bottleneck = None
        if scores:
            bottleneck = min(scores, key=lambda s: s.score)

        # Step 4: Overall viability
        # Auto-select scoring mode: weighted for >2 interfaces (multi-domain
        # designs), bottleneck for single/dual interface queries.
        if scores:
            min_score = bottleneck.score if bottleneck else 0
            avg_score = sum(s.score for s in scores) / len(scores)

            mode = query.scoring_mode or (
                'weighted' if len(scores) > 2 else 'bottleneck'
            )

            if mode == 'weighted':
                # Weighted average: the bottleneck interface gets 0.5x weight
                # instead of dominating the entire score. This prevents a
                # single mediocre interface from killing an otherwise viable
                # multi-component design.
                weights = [0.5 if s.score == min_score else 1.0 for s in scores]
                overall = sum(s.score * w for s, w in zip(scores, weights)) / sum(weights)
            else:
                # Original bottleneck formula (75% min + 25% avg)
                overall = 0.75 * min_score + 0.25 * avg_score
        elif len(query.components) <= 1:
            overall = 1.0
        else:
            overall = 0.0
            warnings.append("No cross-domain interfaces could be scored")

        viable = overall >= (query.viability_threshold or self.viability_threshold)

        # Collect all warnings from individual scores
        for s in scores:
            warnings.extend(s.warnings)

        return MultiDomainAnalysis(
            query_name=query.name,
            components=query.components,
            domains_involved=domains_involved,
            cross_domain_scores=scores,
            overall_score=max(0.0, min(1.0, overall)),
            viable=viable,
            bottleneck=bottleneck,
            warnings=warnings,
        )

    def _try_score_pair(
        self,
        comp_a: MultiDomainComponent,
        comp_b: MultiDomainComponent,
        electrolyte: Optional[str] = None,
    ) -> Optional[CrossDomainScore]:
        """Try to score a cross-domain pair using available functors."""

        da, db = comp_a.domain, comp_b.domain
        pair = frozenset([da, db])

        # Battery + Polymer
        if pair == frozenset(['battery', 'polymer']):
            poly = comp_a if comp_a.domain == 'polymer' else comp_b
            bat = comp_a if comp_a.domain == 'battery' else comp_b
            r = score_polymer_electrode_compatibility(poly.name, bat.name)
            return CrossDomainScore(
                component_a=poly.name, component_b=bat.name,
                domain_a='polymer', domain_b='battery',
                functor_used='battery_polymer',
                score=r.score, compatible=r.compatible,
                warnings=r.warnings,
                details={'voltage': r.voltage_compatibility,
                         'thermal': r.thermal_compatibility,
                         'mechanical': r.mechanical_compatibility,
                         'chemical': r.chemical_compatibility},
            )

        # Battery + Metal
        if pair == frozenset(['battery', 'metal']):
            met = comp_a if comp_a.domain == 'metal' else comp_b
            bat = comp_a if comp_a.domain == 'battery' else comp_b
            r = score_collector_compatibility(met.name, bat.name, electrolyte)
            return CrossDomainScore(
                component_a=met.name, component_b=bat.name,
                domain_a='metal', domain_b='battery',
                functor_used='battery_metal',
                score=r.score, compatible=r.compatible,
                warnings=r.warnings,
                details={'electrochemical': r.electrochemical_stability,
                         'galvanic': r.galvanic_risk,
                         'cte': r.cte_compatibility,
                         'conductivity': r.conductivity_score,
                         'corrosion': r.corrosion_risk},
            )

        # Ceramic + Metal
        if pair == frozenset(['ceramic', 'metal']):
            cer = comp_a if comp_a.domain == 'ceramic' else comp_b
            met = comp_a if comp_a.domain == 'metal' else comp_b
            r = score_coating_compatibility(cer.name, met.name)
            return CrossDomainScore(
                component_a=cer.name, component_b=met.name,
                domain_a='ceramic', domain_b='metal',
                functor_used='ceramic_metal',
                score=r.score, compatible=r.compatible,
                warnings=r.warnings,
                details={'cte': r.cte_compatibility,
                         'thermal_processing': r.thermal_processing,
                         'mechanical': r.mechanical_compatibility,
                         'chemical': r.chemical_interaction},
            )

        # Same domain — skip (handled by native bridge validators)
        if da == db:
            return None

        # No functor available for this domain pair
        return None


# ============================================================================
# Pre-defined multi-domain queries for testing and demos
# ============================================================================

SOLID_STATE_BATTERY_QUERY = MultiDomainQuery(
    name="NMC811 + LLZO + PEO coating + Cu collector",
    components=[
        MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
        MultiDomainComponent(name='LLZO', role='electrolyte', domain='ceramic'),
        MultiDomainComponent(name='PEO', role='coating', domain='polymer'),
        MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
    ],
    electrolyte='LLZO',
)

LFP_STANDARD_CELL_QUERY = MultiDomainQuery(
    name="LFP + PVDF binder + Al collector + LiPF6",
    components=[
        MultiDomainComponent(name='LFP', role='cathode', domain='battery'),
        MultiDomainComponent(name='PVDF', role='binder', domain='polymer'),
        MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
    ],
    electrolyte='LiPF6',
)

GRAPHITE_ANODE_QUERY = MultiDomainQuery(
    name="Graphite + CMC/SBR binder + Cu collector",
    components=[
        MultiDomainComponent(name='Graphite', role='anode', domain='battery'),
        MultiDomainComponent(name='CMC', role='binder', domain='polymer'),
        MultiDomainComponent(name='Cu_foil', role='collector', domain='metal'),
    ],
    electrolyte='LiPF6',
)

THERMAL_BARRIER_QUERY = MultiDomainQuery(
    name="YSZ thermal barrier on Inconel 718",
    components=[
        MultiDomainComponent(name='ZrO2_YSZ', role='coating', domain='ceramic'),
        MultiDomainComponent(name='Inconel_718', role='substrate', domain='metal'),
    ],
)

PROBLEMATIC_PEO_NMC_QUERY = MultiDomainQuery(
    name="PEO electrolyte + NMC811 (voltage problem)",
    components=[
        MultiDomainComponent(name='PEO', role='electrolyte', domain='polymer'),
        MultiDomainComponent(name='NMC811', role='cathode', domain='battery'),
        MultiDomainComponent(name='Al_foil', role='collector', domain='metal'),
    ],
    electrolyte='LiTFSI',  # LiTFSI corrodes Al
)


if __name__ == "__main__":
    print("=" * 70)
    print("KOMPOSOS-III Multi-Domain Replicator Demo")
    print("=" * 70)
    print()

    analyzer = MultiDomainAnalyzer()

    queries = [
        SOLID_STATE_BATTERY_QUERY,
        LFP_STANDARD_CELL_QUERY,
        GRAPHITE_ANODE_QUERY,
        THERMAL_BARRIER_QUERY,
        PROBLEMATIC_PEO_NMC_QUERY,
    ]

    for query in queries:
        analysis = analyzer.analyze(query)
        status = "VIABLE" if analysis.viable else "NOT VIABLE"
        print(f"--- {analysis.query_name} ---")
        print(f"  Domains: {', '.join(analysis.domains_involved)}")
        print(f"  Overall: {analysis.overall_score:.3f}  [{status}]")
        print(f"  Cross-domain interfaces: {len(analysis.cross_domain_scores)}")
        for s in analysis.cross_domain_scores:
            flag = "OK" if s.compatible else "!!"
            print(f"    [{flag}] {s.component_a}<->{s.component_b} "
                  f"({s.functor_used}): {s.score:.3f}")
        if analysis.bottleneck:
            bn = analysis.bottleneck
            print(f"  Bottleneck: {bn.component_a}<->{bn.component_b} "
                  f"({bn.functor_used}: {bn.score:.3f})")
        if analysis.warnings:
            for w in analysis.warnings:
                print(f"  WARNING: {w}")
        print()
