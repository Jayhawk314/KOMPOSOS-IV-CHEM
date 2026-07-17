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
    BatteryMaterial, MaterialClass, get_material, ALL_MATERIALS as BATTERY_MATS,
    CATHODE_MATERIALS, ANODE_MATERIALS,
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
    cathode_collector: str   # cathode-side current collector (e.g. Al)
    anode_collector: str     # anode-side current collector (e.g. Cu)
    energy_density: float  # Wh/kg
    viability: float       # 0-1 partial aggregate over interfaces with native scorers
    is_pfas_free: bool
    interface_coverage: float = 0.0  # fraction of physical contacts with a native scorer
    unscored_interfaces: List[str] = field(default_factory=list)
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
            "cathode_collector": self.cathode_collector,
            "anode_collector": self.anode_collector,
            "energy_density": round(self.energy_density, 2),
            "viability": round(self.viability, 3),
            "interface_coverage": round(self.interface_coverage, 3),
            "coverage_complete": self.interface_coverage >= 1.0,
            "unscored_interfaces": self.unscored_interfaces,
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
        # Use role-specific registries. The table also contains Al/Cu foils
        # whose historical class labels encode their electrode side; filtering
        # by class allowed Al foil as a cathode and Cu foil as an anode.
        self.cathodes = list(CATHODE_MATERIALS.values())
        self.anodes = list(ANODE_MATERIALS.values())
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
        # Primary: covered-interface score > threshold, then Energy Density.
        # `interface_coverage` prevents callers from reading this as a full-cell
        # verdict when a physical contact lacks a native scorer.
        def _rank_key(c: OptimizedCell):
            v_boost = 1000 if c.viability >= self.viability_threshold else 0
            return (v_boost + c.energy_density, c.viability)
            
        all_results.sort(key=_rank_key, reverse=True)
        
        selected = all_results[:limit]
        # Enabling discovery must have an observable result. A large elite pool
        # can otherwise fill every display slot even though refinement succeeded.
        if enable_discovery and discovery_results and selected and \
                not any(item.type == "Discovery" for item in selected):
            selected[-1] = max(discovery_results, key=_rank_key)
            selected.sort(key=_rank_key, reverse=True)

        # Assign ranks after the display selection is final.
        for i, res in enumerate(selected):
            res.rank = i + 1

        return selected

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

        Models the real bimetallic cell stack with PHYSICAL ADJACENCY:
            cathode_collector -- cathode -- electrolyte -- anode -- anode_collector
        with the binder in both electrode coatings. Only components in contact are
        scored, so the cathode-side collector is never scored against the anode (and
        vice-versa) -- this removes the phantom Al<->anode interface. Mirrors
        MultiDomainAnalyzer + BATTERY_CELL_ADJACENCY exactly (verified).

        The composite factorizes, so we precompute the adjacency-correct partial
        scores once per (cathode, anode, electrolyte) core and assemble cheaply:
          core-core      : cathode<->electrolyte, anode<->electrolyte
          binder<->       : cathode, anode, electrolyte
          cathode_coll<-> : cathode, electrolyte
          anode_coll<->   : anode, electrolyte
        Each material's actual domain (Si->semiconductor, etc.) drives functor
        choice. The anode collector defaults to Cu (the universal standard; Al
        alloys with Li at low potential), overridable via fixed['anode_collector'].
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

        # Cathode-side collector is swept; anode-side defaults to Cu (physical
        # standard) unless the user locks a specific one.
        cath_collectors = [c for c in self.collectors
                           if fixed.get("cathode_collector") in (None, c)]
        if fixed.get("anode_collector"):
            anode_collectors = [fixed["anode_collector"]]
        elif "Cu_foil" in self.collectors:
            anode_collectors = ["Cu_foil"]
        else:
            anode_collectors = [self.collectors[0]] if self.collectors else []

        # Precompute per-binder PFAS status once (independent of the sweep).
        binder_pfas_free = {b: not self.pfas_checker.check(b).is_pfas for b in binders}

        # Memoize pairwise functor scores across the whole sweep. Each underlying
        # scorer is a pure function of its argument names. Returns None when no
        # functor applies to the domain pair or the scorer raises (an unscorable
        # pair simply contributes no interface).
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

        def scores_against(name: str, neighbours) -> List[float]:
            """Functor scores of `name` against each adjacent (nbr_name, elec)."""
            dom = domain_of(name)
            out = []
            for nbr, dn, elec in neighbours:
                v = pair_score(name, dom, nbr, dn, elec)
                if v is not None:
                    out.append(v)
            return out

        for cat in cathodes:
            v_c = cat.voltage_window.nominal if cat.voltage_window else 4.0
            cap = cat.theoretical_capacity or 200.0
            d_cat = domain_of(cat.name)
            for ano in anodes:
                v_a = ano.voltage_window.nominal if ano.voltage_window else 0.1
                cell_v = v_c - v_a
                if cell_v <= 0:
                    continue
                ed = cell_v * cap  # depends only on (cathode, anode)
                d_ano = domain_of(ano.name)

                for elec in electrolytes:
                    d_elec = domain_of(elec)

                    # Core-core: only adjacent pairs (cathode<->elec, anode<->elec);
                    # cathode and anode are NOT in contact (electrolyte separates).
                    core_scores: List[float] = []
                    for v in (pair_score(cat.name, d_cat, elec, d_elec, elec),
                              pair_score(ano.name, d_ano, elec, d_elec, elec)):
                        if v is not None:
                            core_scores.append(v)

                    # Binder touches both electrodes and the electrolyte.
                    binder_nbrs = [(cat.name, d_cat, elec), (ano.name, d_ano, elec),
                                   (elec, d_elec, elec)]
                    binder_scores = {b: scores_against(b, binder_nbrs) for b in binders}

                    # Cathode-side collector touches the cathode and electrolyte.
                    cc_nbrs = [(cat.name, d_cat, elec), (elec, d_elec, elec)]
                    cc_scores = {cc: scores_against(cc, cc_nbrs) for cc in cath_collectors}

                    # Anode-side collector touches the anode and electrolyte.
                    ac_nbrs = [(ano.name, d_ano, elec), (elec, d_elec, elec)]
                    ac_scores = {ac: scores_against(ac, ac_nbrs) for ac in anode_collectors}

                    for b in binders:
                        bs = binder_scores[b]
                        for cc in cath_collectors:
                            ccs = cc_scores[cc]
                            for ac in anode_collectors:
                                physical_contacts = [
                                    (cat.name, d_cat, elec, d_elec),
                                    (ano.name, d_ano, elec, d_elec),
                                    (b, domain_of(b), cat.name, d_cat),
                                    (b, domain_of(b), ano.name, d_ano),
                                    (b, domain_of(b), elec, d_elec),
                                    (cc, domain_of(cc), cat.name, d_cat),
                                    (cc, domain_of(cc), elec, d_elec),
                                    (ac, domain_of(ac), ano.name, d_ano),
                                    (ac, domain_of(ac), elec, d_elec),
                                ]
                                scored_values = []
                                unscored = []
                                for left, dl, right, dr in physical_contacts:
                                    value = pair_score(left, dl, right, dr, elec)
                                    if value is None:
                                        unscored.append(f"{left}<->{right}")
                                    else:
                                        scored_values.append(value)
                                viability = self._overall_score(scored_values)
                                if viability < self.viability_threshold:
                                    continue
                                results.append(OptimizedCell(
                                    rank=0,
                                    type="Elite",
                                    cathode=cat.name,
                                    anode=ano.name,
                                    electrolyte=elec,
                                    binder=b,
                                    cathode_collector=cc,
                                    anode_collector=ac,
                                    energy_density=ed,
                                    viability=viability,
                                    is_pfas_free=binder_pfas_free[b],
                                    interface_coverage=len(scored_values) / len(physical_contacts),
                                    unscored_interfaces=unscored,
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
            from composition_engine.mp_loader import MPCache

            cache = MPCache()
            if not cache.is_available():
                return []
            entries = cache.load_entries()
            index = CompositionIndex(entries)
            predictor = CompositionPredictor()
        except Exception:
            return []

        for base in top_elite:
            # Find neighbors for the cathode
            try:
                # We need the vector for the cathode formula
                from composition_engine.parser import parse_formula, composition_vector
                base_comp = parse_formula(get_material(base.cathode).formula)
                base_vec = composition_vector(base_comp)
                
                # Search 103K cache for top 5 chemical neighbors
                neighbors = index.nearest_k(base_vec, k=10)
                
                for entry, dist in neighbors:
                    if entry.formula == get_material(base.cathode).formula:
                        continue # Skip exact match
                        
                    # Predict properties for this novel cathode
                    pred = predictor.predict(entry.formula, include_structure=False)
                    
                    # Energy Density
                    v_ano = get_material(base.anode).voltage_window.nominal if get_material(base.anode).voltage_window else 0.1
                    # predictor voltage is a list/dict usually, let's assume nominal exists
                    pred_v = (
                        pred.properties['voltage'].value
                        if 'voltage' in pred.properties else 4.0
                    )
                    cell_v = pred_v - v_ano
                    pred_capacity = (
                        pred.properties['theoretical_capacity'].value
                        if 'theoretical_capacity' in pred.properties else 200.0
                    )
                    ed = cell_v * pred_capacity
                    
                    # Viability (assuming same compatibility as base for now, 
                    # but we could run the analyzer if we had a way to map novel materials)
                    # For discovery, we score by "Similarity * Base Viability"
                    viability = base.viability * max(0.0, 1.0 - dist)
                    
                    results.append(OptimizedCell(
                        rank=0,
                        type="Discovery",
                        cathode=entry.formula,
                        anode=base.anode,
                        electrolyte=base.electrolyte,
                        binder=base.binder,
                        cathode_collector=base.cathode_collector,
                        anode_collector=base.anode_collector,
                        energy_density=ed,
                        viability=viability,
                        is_pfas_free=base.is_pfas_free,
                        interface_coverage=base.interface_coverage,
                        unscored_interfaces=list(base.unscored_interfaces),
                        mp_id=entry.mp_id,
                        notes=f"Structural variant of {base.cathode} (dist={dist:.3f})"
                    ))
            except Exception:
                continue
                
        return results
