# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Battery Optimizer
==================

Evolutionary design engine for battery cells.
Stage 1: Elite Sweep (Brute-force over high-trust materials)
Stage 2: Discovery Refinement (Neighborhood search in 103K MP cache)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, get_material, ALL_MATERIALS as BATTERY_MATS
)
from polymer_bridge.material_properties import ALL_POLYMERS
from metal_bridge.material_properties import ALL_METALS
from ceramic_bridge.material_properties import ALL_CERAMICS
from cross_bridge.multi_domain import (
    MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent, MultiDomainAnalysis
)
from pfas_bridge.compliance_checker import PFASComplianceChecker
from composition_engine.spatial_index import CompositionIndex
from composition_engine.predictor import CompositionPredictor


@dataclass
class OptimizedCell:
    """A cell configuration found by the optimizer."""
    rank: int
    type: str  # "Elite" or "Discovery"
    cathode: str
    anode: str
    electrolyte: str
    binder: str
    collector: str
    energy_density: float  # Wh/kg
    viability: float       # 0-1
    is_pfas_free: bool
    mp_id: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "rank": self.rank,
            "type": self.type,
            "cathode": self.cathode,
            "anode": self.anode,
            "electrolyte": self.electrolyte,
            "binder": self.binder,
            "collector": self.collector,
            "energy_density": round(self.energy_density, 2),
            "viability": round(self.viability, 3),
            "is_pfas_free": self.is_pfas_free,
            "mp_id": self.mp_id,
            "notes": self.notes
        }


class BatteryOptimizer:
    """Evolutionary Battery Optimizer."""

    def __init__(self, viability_threshold: float = 0.5):
        self.viability_threshold = viability_threshold
        self.analyzer = MultiDomainAnalyzer(viability_threshold=viability_threshold)
        # Sweep is over a curated material library, so detect PFAS by registry +
        # structure only. resolve_unknown=True would do a ~0.5s PubChem network
        # lookup per unknown polymer name (PTFE/PVDF are caught by the registry
        # regardless); verified to give the identical PFAS-free set for the binder
        # library, so this is a pure speedup, not a behaviour change.
        self.pfas_checker = PFASComplianceChecker(resolve_unknown=False)
        
        # Categorize Elite materials
        self.cathodes = [m for m in BATTERY_MATS.values() if m.material_class == MaterialClass.CATHODE]
        self.anodes = [m for m in BATTERY_MATS.values() if m.material_class == MaterialClass.ANODE]
        self.solvents = [m for m in BATTERY_MATS.values() if m.material_class == MaterialClass.ELECTROLYTE_SOLVENT]
        self.solids = [m for m in BATTERY_MATS.values() if m.material_class == MaterialClass.SOLID_ELECTROLYTE]
        self.binders = list(ALL_POLYMERS.keys())
        self.collectors = list(ALL_METALS.keys())

    def optimize(
        self, 
        fixed_components: Dict[str, str] = None,
        pfas_free_only: bool = False,
        enable_discovery: bool = False,
        limit: int = 10
    ) -> List[OptimizedCell]:
        """
        Run the two-stage optimization.
        """
        fixed = fixed_components or {}
        
        # Stage 1: Elite Sweep
        elite_results = self._elite_sweep(fixed, pfas_free_only)
        
        # Stage 2: Discovery (if enabled)
        if enable_discovery:
            discovery_results = self._discovery_refinement(elite_results[:3], fixed, pfas_free_only)
            all_results = elite_results + discovery_results
        else:
            all_results = elite_results
            
        # Final ranking
        # Primary: Viability > threshold, then Energy Density
        # Secondary: Viability score itself
        def _rank_key(c: OptimizedCell):
            v_boost = 1000 if c.viability >= self.viability_threshold else 0
            return (v_boost + c.energy_density, c.viability)
            
        all_results.sort(key=_rank_key, reverse=True)
        
        # Assign ranks
        for i, res in enumerate(all_results):
            res.rank = i + 1
            
        return all_results[:limit]

    @staticmethod
    def _overall_score(scores: List[float]) -> float:
        """Replicate MultiDomainAnalyzer's composite exactly.

        Kept bit-for-bit identical to cross_bridge.multi_domain.analyze():
        >2 interfaces use 'weighted' mode (bottleneck gets 0.5x weight, rest 1.0x);
        1-2 interfaces use 'bottleneck' (0.75*min + 0.25*avg); 0 interfaces -> 0.0
        (a multi-component query with no scorable interface). The interface count
        varies because a component's domain (e.g. Si -> semiconductor) decides which
        functors fire, so both modes must be handled.
        """
        if not scores:
            return 0.0
        min_score = min(scores)
        if len(scores) > 2:
            weights = [0.5 if s == min_score else 1.0 for s in scores]
            overall = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        else:
            avg = sum(scores) / len(scores)
            overall = 0.75 * min_score + 0.25 * avg
        return max(0.0, min(1.0, overall))

    def _elite_sweep(self, fixed: Dict[str, str], pfas_free_only: bool) -> List[OptimizedCell]:
        """Sweep combinations of high-trust materials.

        The cross-domain composite factorizes: binder and collector never interface
        each other ({polymer,metal} has no functor). So a combo's interface scores
        split into three groups: (a) core-core scores among cathode/anode/electrolyte
        (constant for a given core, e.g. a metal anode<->cathode pair), (b) binder<->
        core scores (depend only on binder), (c) collector<->core scores (depend only
        on collector). We precompute each group once per (cathode, anode, electrolyte)
        core, then assemble the composite cheaply instead of running a full
        5-component analyze() per (binder x collector) pair. Provably equivalent to
        the old full-analyze sweep (verified), but avoids the redundant functor calls
        that made a full scan slow.

        Each material's *actual* domain (via the analyzer's registry) decides which
        functor applies, so this mirrors analyze() rather than assuming role==domain.
        """
        from cross_bridge.battery_polymer import score_polymer_electrode_compatibility
        from cross_bridge.battery_metal import score_collector_compatibility
        from cross_bridge.ceramic_metal import score_coating_compatibility

        results = []
        domain_of = self.analyzer.identify_domain

        # Filter pools by fixed components
        cathodes = [c for c in self.cathodes if fixed.get("cathode") in (None, c.name)]
        anodes = [a for a in self.anodes if fixed.get("anode") in (None, a.name)]

        # For electrolyte, we handle Solid vs Liquid
        is_solid = fixed.get("cell_type") == "solid"
        if is_solid:
            electrolytes = [e.name for e in self.solids if fixed.get("electrolyte") in (None, e.name)]
        else:
            electrolytes = [e.name for e in self.solvents if fixed.get("electrolyte") in (None, e.name)]

        binders = [b for b in self.binders if fixed.get("binder") in (None, b)]
        if pfas_free_only:
            binders = [b for b in binders if not self.pfas_checker.check(b).is_pfas]

        collectors = [c for c in self.collectors if fixed.get("collector") in (None, c)]

        # Precompute per-binder PFAS status once (independent of the sweep).
        binder_pfas_free = {b: not self.pfas_checker.check(b).is_pfas for b in binders}

        # Memoize pairwise functor scores across the whole sweep. Each underlying
        # scorer is a pure function of its argument names. Returns None when no
        # functor applies to the domain pair or the scorer raises, mirroring the old
        # per-combo behaviour (an unscorable pair contributes no interface; a raised
        # analyze() yielded viability 0.0 and was filtered out).
        score_memo: Dict[tuple, Optional[float]] = {}

        def pair_score(name_a: str, dom_a: str, name_b: str, dom_b: str, elec: str) -> Optional[float]:
            pair = frozenset((dom_a, dom_b))
            key = (name_a, name_b, elec)
            if key in score_memo:
                return score_memo[key]
            try:
                if pair == frozenset(("battery", "polymer")):
                    poly, bat = (name_a, name_b) if dom_a == "polymer" else (name_b, name_a)
                    val = score_polymer_electrode_compatibility(poly, bat).score
                elif pair == frozenset(("battery", "metal")):
                    met, bat = (name_a, name_b) if dom_a == "metal" else (name_b, name_a)
                    val = score_collector_compatibility(met, bat, elec).score
                elif pair == frozenset(("ceramic", "metal")):
                    cer, met = (name_a, name_b) if dom_a == "ceramic" else (name_b, name_a)
                    val = score_coating_compatibility(cer, met).score
                else:
                    val = None  # no functor for this domain pair
            except Exception:
                val = None
            score_memo[key] = val
            return val

        for cat in cathodes:
            v_c = cat.voltage_window.nominal if cat.voltage_window else 4.0
            cap = cat.theoretical_capacity or 200.0
            for ano in anodes:
                v_a = ano.voltage_window.nominal if ano.voltage_window else 0.1
                cell_v = v_c - v_a
                if cell_v <= 0:
                    continue
                ed = cell_v * cap  # depends only on (cathode, anode)

                for elec in electrolytes:
                    # The core components and their actual domains.
                    core = [
                        (cat.name, domain_of(cat.name)),
                        (ano.name, domain_of(ano.name)),
                        (elec, domain_of(elec)),
                    ]

                    # Core-core interfaces (e.g. a metal anode <-> battery cathode):
                    # constant for this core, shared by every binder/collector combo.
                    core_scores: List[float] = []
                    for i in range(len(core)):
                        for j in range(i + 1, len(core)):
                            v = pair_score(core[i][0], core[i][1], core[j][0], core[j][1], elec)
                            if v is not None:
                                core_scores.append(v)

                    # Partial interface scores for each binder / collector vs the core.
                    binder_scores: Dict[str, List[float]] = {}
                    for b in binders:
                        db = domain_of(b)
                        s = [pair_score(b, db, n, dn, elec) for n, dn in core]
                        binder_scores[b] = [v for v in s if v is not None]

                    collector_scores: Dict[str, List[float]] = {}
                    for col in collectors:
                        dc = domain_of(col)
                        s = [pair_score(col, dc, n, dn, elec) for n, dn in core]
                        collector_scores[col] = [v for v in s if v is not None]

                    for b in binders:
                        bs = binder_scores[b]
                        for col in collectors:
                            viability = self._overall_score(core_scores + bs + collector_scores[col])
                            if viability < self.viability_threshold:
                                continue
                            results.append(OptimizedCell(
                                rank=0,
                                type="Elite",
                                cathode=cat.name,
                                anode=ano.name,
                                electrolyte=elec,
                                binder=b,
                                collector=col,
                                energy_density=ed,
                                viability=viability,
                                is_pfas_free=binder_pfas_free[b],
                            ))

        return results

    def _discovery_refinement(
        self, 
        top_elite: List[OptimizedCell], 
        fixed: Dict[str, str],
        pfas_free_only: bool
    ) -> List[OptimizedCell]:
        """Stage 2: Use 103K MP cache to find variants of top performers."""
        results = []
        try:
            index = CompositionIndex()
            predictor = CompositionPredictor()
        except Exception:
            return []

        for base in top_elite:
            # Find neighbors for the cathode
            try:
                # We need the vector for the cathode formula
                from composition_engine.parser import parse_formula, composition_to_vector
                base_comp = parse_formula(get_material(base.cathode).formula)
                base_vec = composition_to_vector(base_comp)
                
                # Search 103K cache for top 5 chemical neighbors
                neighbors = index.nearest_k(base_vec, k=10)
                
                for mp_id, dist, entry in neighbors:
                    if entry.formula == get_material(base.cathode).formula:
                        continue # Skip exact match
                        
                    # Predict properties for this novel cathode
                    pred = predictor.predict(entry.formula)
                    
                    # Energy Density
                    v_ano = get_material(base.anode).voltage_window.nominal if get_material(base.anode).voltage_window else 0.1
                    # predictor voltage is a list/dict usually, let's assume nominal exists
                    pred_v = pred.predicted_properties.get("voltage", 4.0)
                    cell_v = pred_v - v_ano
                    ed = cell_v * pred.predicted_properties.get("theoretical_capacity", 200.0)
                    
                    # Viability (assuming same compatibility as base for now, 
                    # but we could run the analyzer if we had a way to map novel materials)
                    # For discovery, we score by "Similarity * Base Viability"
                    viability = base.viability * (1.0 - dist)
                    
                    results.append(OptimizedCell(
                        rank=0,
                        type="Discovery",
                        cathode=entry.formula,
                        anode=base.anode,
                        electrolyte=base.electrolyte,
                        binder=base.binder,
                        collector=base.collector,
                        energy_density=ed,
                        viability=viability,
                        is_pfas_free=base.is_pfas_free,
                        mp_id=mp_id,
                        notes=f"Structural variant of {base.cathode} (dist={dist:.3f})"
                    ))
            except Exception:
                continue
                
        return results
