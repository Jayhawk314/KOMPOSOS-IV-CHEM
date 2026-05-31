# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Autonomous Discovery Workbench Orchestrator
=============================================

This module unifies the 8 primary features of KOMPOSOS-IV-CHEM into a
single discovery pipeline. It treats each feature as a 'Stage' in a
categorical discovery functor.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import time

from core.category import Category
from oracle.compatibility_service import run_compatibility_workflow
from composition_engine.designer import CompositionDesigner, DesignSpec, PropertyTarget
from composition_engine.predictor import CompositionPredictor

@dataclass
class DiscoveryCandidate:
    """A single candidate material tracked through the workbench pipeline."""
    formula: str
    composition: Dict[str, float] = field(default_factory=dict)
    proxy_material: Optional[str] = None
    domain: Optional[str] = None
    
    # Stage 1: Design Properties
    predicted_properties: Dict[str, float] = field(default_factory=dict)
    design_score: float = 0.0
    
    # Stage 2: Safety & Regulatory
    is_pfas_free: bool = True
    safety_vetoes: List[str] = field(default_factory=list)
    zfc_witnessed: bool = False
    
    # Stage 3: Interface Compatibility
    compatibility_score: float = 0.0
    compatibility_viable: bool = False
    compatibility_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Stage 4: Synthesis
    synthesizability_score: float = 0.0
    precursors: List[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    
    # Overall
    overall_confidence: float = 0.0
    pipeline_depth: int = 0 # How many stages it survived

@dataclass
class DiscoveryGoal:
    """The researcher's goal for a discovery run."""
    # Target Properties
    targets: List[PropertyTarget] = field(default_factory=list)
    
    # Constraints
    required_elements: List[str] = field(default_factory=list)
    excluded_elements: List[str] = field(default_factory=list)
    max_elements: Optional[int] = None
    
    # Compatibility Context
    target_interface_material: Optional[str] = None # e.g. "Li_metal"
    interface_role: Optional[str] = None # e.g. "anode_interface"
    
    # Performance
    max_candidates: int = 50
    min_overall_confidence: float = 0.45

class DiscoveryWorkbenchService:
    """
    Orchestrates the 8-feature discovery pipeline.
    """
    
    def __init__(self, category: Optional[Category] = None):
        self.category = category or Category(db_path=":memory:")
        self._designer = CompositionDesigner()
        self._predictor = CompositionPredictor()
        
    def run_discovery_pipeline(self, goal: DiscoveryGoal) -> List[DiscoveryCandidate]:
        """
        Execute the 'Golden Path' discovery pipeline.
        """
        start_time = time.time()
        candidates: List[DiscoveryCandidate] = []
        
        # --- STAGE 1: Generation (Inverse Design) ---
        print(f"[*] Stage 1: Generating candidates for {len(goal.targets)} targets...")
        from composition_engine.designer import ElementConstraint
        
        elem_spec = None
        if goal.required_elements or goal.excluded_elements:
            elem_spec = ElementConstraint(
                required_elements=goal.required_elements,
                excluded_elements=goal.excluded_elements,
                max_elements=goal.max_elements
            )
            
        spec = DesignSpec(
            targets=goal.targets,
            max_candidates=goal.max_candidates,
            element_constraints=elem_spec,
            domain=None
        )
        # Note: We'd normally pass goal elements to spec, but simplified for prototype
        design_result = self._designer.design(spec)

        for dr in design_result.candidates:
            candidates.append(DiscoveryCandidate(

                formula=dr.formula,
                composition=dr.composition,
                proxy_material=dr.anchor,
                domain=self._detect_domain(dr.composition),
                predicted_properties=dr.predicted_properties,
                design_score=dr.overall_score,
                synthesizability_score=dr.synthesizability,
                pipeline_depth=1
            ))
        
        if not candidates:
            return []

        # --- STAGE 2: Safety & Regulatory (PFAS/ZFC) ---
        print(f"[*] Stage 2: Screening {len(candidates)} candidates for safety...")
        from pfas_bridge.compliance_checker import PFASComplianceChecker
        checker = PFASComplianceChecker()
        
        safe_candidates = []
        for c in candidates:
            compliance = checker.check(c.formula)
            c.is_pfas_free = not compliance.is_pfas
            if compliance.is_pfas:
                c.safety_vetoes.append(f"PFAS: {compliance.urgency}")
            
            # Simple ZFC Typicality check placeholder
            # In real system, we'd call MaterialZFCBridge
            c.zfc_witnessed = True # Assume physically grounded for now
            
            if c.is_pfas_free:
                c.pipeline_depth = 2
                safe_candidates.append(c)
        
        # --- STAGE 3: Interface Compatibility (Oracle) ---
        if goal.target_interface_material:
            print(f"[*] Stage 3: Verifying {len(safe_candidates)} candidates against {goal.target_interface_material}...")
            compatible_candidates = []
            for c in safe_candidates:
                try:
                    material_for_workflow = self._resolve_known_proxy(c)
                    if material_for_workflow is None:
                        raise ValueError(
                            f"No known proxy material available for generated formula '{c.formula}'"
                        )

                    workflow = run_compatibility_workflow(
                        material_for_workflow,
                        goal.target_interface_material,
                        role=goal.interface_role,
                    )
                    c.compatibility_score = workflow.scores.get("total", 0.0)
                    c.compatibility_viable = workflow.viable
                    c.compatibility_metadata = workflow.scores.get("ensemble", {})
                    c.compatibility_metadata["workflow_material"] = material_for_workflow
                    c.compatibility_metadata["generated_formula"] = c.formula
                    
                    if c.compatibility_viable:
                        c.pipeline_depth = 3
                        compatible_candidates.append(c)
                except Exception as e:
                    # If we can't run compatibility (e.g. unknown domain), we don't necessarily reject
                    # but we mark as unverified
                    c.compatibility_metadata["error"] = str(e)
            
            active_pool = compatible_candidates if compatible_candidates else safe_candidates
        else:
            active_pool = safe_candidates

        # --- STAGE 4: Synthesis Planning ---
        print(f"[*] Stage 4: Estimating synthesizability for top {len(active_pool)} candidates...")
        from synthesis_planner.route_planner import SynthesisPlanner
        planner = SynthesisPlanner()
        
        for c in active_pool:
            try:
                synthesis_target = self._resolve_known_proxy(c) or c.formula
                analysis = planner.plan_synthesis(synthesis_target)
                if analysis.best_route is not None:
                    best_route = analysis.best_route
                    c.synthesizability_score = best_route.composite_score
                    c.precursors = list(best_route.route.precursors)
                    c.estimated_cost = analysis.precursor_cost_usd
                    c.compatibility_metadata.setdefault("synthesis_target", synthesis_target)
                    c.pipeline_depth = 4
            except Exception as e:
                c.compatibility_metadata.setdefault("synthesis_error", str(e))
        
        # --- FINAL: Overall Confidence Calculation ---
        for c in candidates:
            # Weighted average of Design (40%), Compat (40%), Synth (20%)
            c.overall_confidence = (
                (c.design_score * 0.4) +
                (c.compatibility_score * 0.4) +
                (c.synthesizability_score * 0.2)
            )
            
        # Return sorted by overall confidence
        candidates.sort(key=lambda x: x.overall_confidence, reverse=True)
        
        end_time = time.time()
        print(f"[+] Discovery Pipeline complete in {end_time - start_time:.2f}s. Found {len(candidates)} candidates.")
        
        return candidates

    def _resolve_known_proxy(self, candidate: DiscoveryCandidate) -> Optional[str]:
        """Return a known material name for services that cannot score arbitrary formulas.

        Also records, on the candidate, the proxy's composition-space *distance* so
        callers can judge how trustworthy a proxy-based score is (a distant proxy is
        a weak stand-in for the candidate's own chemistry).
        """
        if candidate.proxy_material:
            candidate.compatibility_metadata.setdefault("proxy_distance", 0.0)
            return candidate.proxy_material

        try:
            prediction = self._predictor.predict(candidate.formula, domain=candidate.domain)
        except Exception:
            return None

        if prediction.nearest_known:
            name, distance = prediction.nearest_known[0]
            candidate.compatibility_metadata["proxy_distance"] = round(float(distance), 4)
            return name
        return None

    @staticmethod
    def _detect_domain(composition: Dict[str, float]) -> Optional[str]:
        has_li = "Li" in composition
        has_o = "O" in composition
        has_tms = any(m in composition for m in ["Ni", "Mn", "Co"])
        has_fe_p = "Fe" in composition and "P" in composition

        if has_li and has_o and (has_tms or has_fe_p):
            return "battery"
        return None
