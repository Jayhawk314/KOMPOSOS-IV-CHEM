# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
CurvatureRouter — Ricci curvature-guided proof path selection.

Uses Ollivier-Ricci curvature to decide which proof paths to pursue,
monitor, or prune based on their geometric structure.
"""

import sys
from typing import Dict, List, Any, Optional

# Guard imports
try:
    from core import Category
    from geometry.ricci import OllivierRicciCurvature
    from geometry.fast_ricci import EffectiveResistanceCurvature
except ImportError as e:
    print(f"Warning: Could not import curvature modules: {e}", file=sys.stderr)
    # Stubs for testing
    class Category:
        def __init__(self, *args, **kwargs):
            self._objects = {}
            self._morphisms = []
        def objects(self):
            return self._objects.values()
        def morphisms(self):
            return self._morphisms
    class EffectiveResistanceCurvature:
        def __init__(self, *args, **kwargs):
            pass
        def compute_all_curvatures(self):
            return type('Result', (), {
                'statistics': {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0},
                'num_spherical': 0,
                'num_hyperbolic': 0,
                'num_euclidean': 0,
            })()
    class OllivierRicciCurvature:
        def __init__(self, *args, **kwargs):
            pass
        def compute_all_curvatures(self):
            return EffectiveResistanceCurvature(None).compute_all_curvatures()


class CurvatureRouter:
    """
    Router that uses Ricci curvature to allocate proof search budget.
    
    Key insight from KOMPOSOS-IV Mathlib analysis:
    Mathematical proof graphs are 100% euclidean (κ ≈ 0, linear chains).
    
    This router exploits that structure to efficiently allocate LLM retries.
    """
    
    def __init__(self, use_fast_approx: bool = True):
        """
        Initialize curvature router.
        
        Args:
            use_fast_approx: If True, use EffectiveResistanceCurvature (O(n²))
                           If False, use exact ollivier_ricci_curvature
        """
        self.use_fast_approx = use_fast_approx
    
    def _compute_curvature(self, cat: Category) -> Any:
        """Compute Ricci curvature for a category."""
        try:
            if self.use_fast_approx:
                curvature = EffectiveResistanceCurvature(cat, alpha=0.5)
                return curvature.compute_all_curvatures()
            else:
                curvature = OllivierRicciCurvature(cat, alpha=0.5)
                return curvature.compute_all_curvatures()
        except Exception as e:
            print(f"Warning: Curvature computation failed: {e}", file=sys.stderr)
            # Return dummy result
            return type('Result', (), {
                'statistics': {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0},
                'num_spherical': 0,
                'num_hyperbolic': 0,
                'num_euclidean': 0,
            })()
    
    def score_paths(
        self,
        cat: Category,
        candidate_paths: List[List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Score each candidate proof path by Ricci curvature.
        
        Args:
            cat: Category containing the proof graph
            candidate_paths: List of paths (each path is list of step IDs)
            
        Returns:
            List of scored paths, sorted by mean_curvature descending
        """
        scored = []
        
        for path in candidate_paths:
            if len(path) < 2:
                scored.append({
                    "path": path,
                    "mean_curvature": 0.0,
                    "decision": "MONITOR",
                })
                continue
            
            # Extract subgraph for this path
            # For now, use whole category (simplification)
            # In production, would extract induced subgraph
            
            curvature_result = self._compute_curvature(cat)
            
            mean_curvature = curvature_result.statistics.get('mean', 0.0)
            
            # Classify based on curvature
            if mean_curvature > 0.1:
                decision = "PURSUE"  # Convergent, promising
            elif mean_curvature < -0.1:
                decision = "PRUNE"   # Divergent, likely wrong
            else:
                decision = "MONITOR"  # Neutral, needs more info
            
            scored.append({
                "path": path,
                "mean_curvature": float(mean_curvature),
                "decision": decision,
                "geometry": {
                    "spherical": curvature_result.num_spherical,
                    "hyperbolic": curvature_result.num_hyperbolic,
                    "euclidean": curvature_result.num_euclidean,
                }
            })
        
        # Sort by curvature descending (pursue best first)
        scored.sort(key=lambda x: x["mean_curvature"], reverse=True)
        
        return scored
    
    def allocate_budget(
        self,
        scored_paths: List[Dict[str, Any]],
        total_llm_calls: int = 5
    ) -> Dict[int, int]:
        """
        Allocate LLM call budget across scored paths.
        
        Strategy:
        - PURSUE paths: 60% of budget
        - MONITOR paths: 30% of budget
        - PRUNE paths: 10% of budget
        
        Args:
            scored_paths: Output from score_paths()
            total_llm_calls: Total LLM calls available
            
        Returns:
            Dict mapping path index to allocated calls
        """
        allocation = {}
        
        # Count paths by decision
        pursue_indices = [i for i, p in enumerate(scored_paths) if p["decision"] == "PURSUE"]
        monitor_indices = [i for i, p in enumerate(scored_paths) if p["decision"] == "MONITOR"]
        prune_indices = [i for i, p in enumerate(scored_paths) if p["decision"] == "PRUNE"]
        
        # Allocate budget
        pursue_budget = int(total_llm_calls * 0.6)
        monitor_budget = int(total_llm_calls * 0.3)
        prune_budget = total_llm_calls - pursue_budget - monitor_budget
        
        # Distribute among PURSUE paths
        if pursue_indices:
            calls_per_path = max(1, pursue_budget // len(pursue_indices))
            for idx in pursue_indices:
                allocation[idx] = calls_per_path
        
        # Distribute among MONITOR paths
        if monitor_indices:
            calls_per_path = max(1, monitor_budget // len(monitor_indices))
            for idx in monitor_indices:
                allocation[idx] = calls_per_path
        
        # PRUNE paths get 1 call max
        for idx in prune_indices:
            if prune_budget > 0:
                allocation[idx] = 1
                prune_budget -= 1
        
        return allocation
    
    def find_convergence_point(
        self,
        cat: Category,
        path: List[str]
    ) -> Optional[str]:
        """
        Find where curvature transitions from negative to positive.
        
        This is the "insight point" — where the proof structure locks in.
        
        Args:
            cat: Category containing the proof
            path: Ordered list of step IDs
            
        Returns:
            Node name where transition occurs, or None
        """
        if len(path) < 3:
            return None
        
        # Compute curvature for prefixes of increasing length
        prev_curvature = 0.0
        
        for i in range(2, len(path) + 1):
            # Create subcategory for prefix
            # (simplified: just use whole category for now)
            curvature_result = self._compute_curvature(cat)
            curr_curvature = curvature_result.statistics.get('mean', 0.0)
            
            # Check for transition
            if prev_curvature < 0 and curr_curvature > 0:
                # Transition occurred at step i
                return path[i - 1] if i < len(path) else path[-1]
            
            prev_curvature = curr_curvature
        
        return None
    
    def is_euclidean_dominated(self, cat: Category) -> bool:
        """
        Check if the proof graph is predominantly euclidean.
        
        Based on KOMPOSOS-IV finding: Mathlib is 100% euclidean.
        
        Args:
            cat: Category to check
            
        Returns:
            True if >80% euclidean
        """
        curvature_result = self._compute_curvature(cat)
        
        total = (curvature_result.num_spherical +
                curvature_result.num_hyperbolic +
                curvature_result.num_euclidean)
        
        if total == 0:
            return True  # Default to euclidean for empty graphs
        
        euclidean_ratio = curvature_result.num_euclidean / total
        
        return euclidean_ratio > 0.8
