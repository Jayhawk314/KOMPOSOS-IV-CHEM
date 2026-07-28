# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Synthesis Planner Integration
==============================

Wires synthesis routes into the KOMPOSOS-III categorical infrastructure:

- SynthesisStep -> StoredMorphism (each step is a morphism)
- SynthesisRoute -> StoredPath (each route is a path of morphisms)
- Precursor -> StoredObject (each precursor is an object)
- Full route graph -> Category (objects=materials, morphisms=steps)

Follows the same pattern as battery_bridge/integration.py.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from data.store import StoredObject, StoredMorphism, StoredPath
    STORE_AVAILABLE = True
except ImportError:
    STORE_AVAILABLE = False
    StoredObject = None
    StoredMorphism = None
    StoredPath = None

try:
    from categorical.category import Category, Object, Morphism
    CATEGORY_AVAILABLE = True
except ImportError:
    CATEGORY_AVAILABLE = False

try:
    from geometry.ricci import OllivierRicciCurvature
    RICCI_AVAILABLE = True
except Exception:
    RICCI_AVAILABLE = False

from synthesis_planner.route_graph import (
    SynthesisStep, SynthesisRoute, list_all_routes,
)
from synthesis_planner.precursor_db import Precursor, get_precursor


# ============================================================================
# Step -> StoredMorphism
# ============================================================================

def step_to_stored_morphism(step: SynthesisStep) -> 'StoredMorphism':
    """
    Convert a SynthesisStep to a StoredMorphism.

    Each step is a morphism from its primary input to its output,
    with conditions and hazards as metadata.
    """
    if not STORE_AVAILABLE or StoredMorphism is None:
        raise ImportError("StoredMorphism not available - data.store not found")

    source = step.inputs[0] if step.inputs else "unknown"
    return StoredMorphism(
        name=f"synthesis_{step.operation}",
        source_name=source,
        target_name=step.output,
        metadata={
            'operation': step.operation,
            'all_inputs': step.inputs,
            'temperature_C': step.conditions.temperature_C,
            'time_hours': step.conditions.time_hours,
            'atmosphere': step.conditions.atmosphere,
            'pressure_atm': step.conditions.pressure_atm,
            'equipment': step.conditions.equipment,
            'hazards': step.hazards,
            'notes': step.notes,
            'domain': 'synthesis',
        },
        confidence=step.success_probability,
        provenance=step.citation or 'synthesis_planner.route_graph',
    )


# ============================================================================
# Route -> StoredPath
# ============================================================================

def route_to_stored_path(route: SynthesisRoute) -> 'StoredPath':
    """
    Convert a SynthesisRoute to a StoredPath.

    The route is a sequence of morphisms from precursors to target.
    """
    if not STORE_AVAILABLE or StoredPath is None:
        raise ImportError("StoredPath not available - data.store not found")

    morphism_ids = []
    for step in route.steps:
        m = step_to_stored_morphism(step)
        morphism_ids.append(m.id)

    source = route.precursors[0] if route.precursors else "unknown"
    return StoredPath(
        name=f"synthesis_route_{route.name}",
        morphism_ids=morphism_ids,
        source_name=source,
        target_name=route.target,
        metadata={
            'route_name': route.name,
            'total_time_hours': route.total_time_hours,
            'max_temperature_C': route.max_temperature_C,
            'risk_level': route.risk_level,
            'all_precursors': route.precursors,
            'num_steps': len(route.steps),
            'domain': 'synthesis',
        },
        confidence=route.overall_confidence,
        provenance=route.citation or 'synthesis_planner.route_graph',
    )


# ============================================================================
# Precursor -> StoredObject
# ============================================================================

def precursor_to_stored_object(precursor: Precursor) -> 'StoredObject':
    """Convert a Precursor to a StoredObject."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    return StoredObject(
        name=precursor.name,
        type_name="Precursor",
        metadata={
            'formula': precursor.formula,
            'cost_usd_per_kg': precursor.cost_usd_per_kg,
            'purity_pct': precursor.purity_pct,
            'supplier': precursor.supplier,
            'hazard_class': precursor.hazard_class,
            'available': precursor.available,
            'domain': 'synthesis',
        },
        provenance='synthesis_planner.precursor_db',
    )


# ============================================================================
# Build Synthesis Category
# ============================================================================

def build_synthesis_category(
    routes: Optional[List[SynthesisRoute]] = None,
) -> Optional['Category']:
    """
    Build a Category from synthesis routes.

    Objects = all materials (precursors, intermediates, targets)
    Morphisms = synthesis steps connecting them
    """
    if not CATEGORY_AVAILABLE:
        return None

    if routes is None:
        routes = list_all_routes()

    cat = Category("SynthesisCategory")

    # Collect all material names
    all_materials = set()
    for route in routes:
        for step in route.steps:
            for inp in step.inputs:
                all_materials.add(inp)
            all_materials.add(step.output)

    # Add objects
    for mat in sorted(all_materials):
        cat.add_object(Object(mat))

    # Add morphisms (synthesis steps)
    for route in routes:
        for step in route.steps:
            source = step.inputs[0] if step.inputs else None
            if source and source in all_materials and step.output in all_materials:
                try:
                    cat.add_morphism(Morphism(
                        name=f"{route.name}_{step.operation}",
                        source=Object(source),
                        target=Object(step.output),
                    ))
                except (ValueError, AttributeError):
                    pass  # Duplicate or incompatible morphism

    return cat


# ============================================================================
# Curvature on Route Graph
# ============================================================================

def compute_synthesis_curvature(
    routes: Optional[List[SynthesisRoute]] = None,
) -> Dict:
    """
    Compute Ollivier-Ricci curvature on the synthesis route graph.

    Identifies bottleneck edges (negative curvature = bridge between
    disconnected regions of the synthesis space).
    """
    if not RICCI_AVAILABLE:
        return {'error': 'Ricci curvature not available', 'edges': []}

    if routes is None:
        routes = list_all_routes()

    # Build adjacency for curvature computation
    import numpy as np

    # Collect unique materials and edges
    materials = set()
    edges = []
    for route in routes:
        for step in route.steps:
            source = step.inputs[0] if step.inputs else None
            if source:
                materials.add(source)
                materials.add(step.output)
                edges.append((source, step.output, step.success_probability))

    mat_list = sorted(materials)
    mat_idx = {m: i for i, m in enumerate(mat_list)}
    n = len(mat_list)

    if n == 0:
        return {'num_materials': 0, 'edges': []}

    # Build adjacency matrix
    adj = np.zeros((n, n))
    for src, tgt, prob in edges:
        i, j = mat_idx[src], mat_idx[tgt]
        adj[i][j] = max(adj[i][j], prob)

    try:
        ricci = OllivierRicciCurvature()
        results = []
        for src, tgt, prob in edges:
            i, j = mat_idx[src], mat_idx[tgt]
            curv = ricci.compute_edge_curvature(adj, i, j)
            results.append({
                'source': src,
                'target': tgt,
                'confidence': prob,
                'curvature': float(curv) if curv is not None else None,
            })

        # Sort by curvature (most negative = biggest bottleneck)
        results.sort(key=lambda r: r['curvature'] if r['curvature'] is not None else 0)

        return {
            'num_materials': n,
            'num_edges': len(edges),
            'num_routes': len(routes),
            'edges': results,
            'bottleneck_edges': [r for r in results[:5]
                                if r['curvature'] is not None and r['curvature'] < 0],
        }
    except Exception as e:
        return {'error': str(e), 'num_materials': n, 'edges': []}
