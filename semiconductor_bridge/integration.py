# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS Integration Layer for Semiconductor Bridge
=======================================================

Wires semiconductor materials, interfaces, and heterostructure analysis into
the existing KOMPOSOS-III categorical infrastructure:

- Objects = Semiconductors (elemental, III-V, nitrides, 2D, etc.)
- Morphisms = Heterostructure compatibility, lattice match, band alignment
- Ricci curvature = Identifies bottleneck layers in multi-layer stacks
- Sheaf coherence = Cross-validates consistency across all heterointerfaces

Mirrors ceramic_bridge/integration.py exactly.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Parent path for cross-module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from data.store import StoredObject, StoredMorphism
    STORE_AVAILABLE = True
except ImportError:
    STORE_AVAILABLE = False
    StoredObject = None
    StoredMorphism = None

try:
    from categorical.category import Category, Object, Morphism
    CATEGORY_AVAILABLE = True
except ImportError:
    CATEGORY_AVAILABLE = False

try:
    from geometry.ricci import OllivierRicciCurvature, CurvatureResult
    RICCI_AVAILABLE = True
except ImportError:
    RICCI_AVAILABLE = False

import numpy as np

from semiconductor_bridge.material_properties import (
    SemiconductorMaterial, SemiconductorClass, ALL_SEMICONDUCTORS, get_semiconductor,
)
from semiconductor_bridge.interface_validator import (
    SemiconductorInterfaceValidator, SemiconductorInterfaceScore,
)
from semiconductor_bridge.heterostructure_analyzer import (
    HeterostructureAnalyzer, HeterostructureConfiguration, HeterostructureAnalysis,
)


# =============================================================================
# Semiconductor -> StoredObject
# =============================================================================

def semiconductor_to_stored_object(sc: SemiconductorMaterial) -> 'StoredObject':
    """
    Convert a SemiconductorMaterial to a StoredObject for the categorical store.

    Args:
        sc: Semiconductor material

    Returns:
        StoredObject for the KOMPOSOS data store

    Raises:
        ImportError: If data.store is not available
    """
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'formula': sc.formula,
        'semiconductor_class': sc.semiconductor_class.value,
        'crystal_system': sc.crystal_system.value,
        'band_gap_eV': sc.band_gap_eV,
        'lattice_constant_A': sc.lattice_constant_A,
        'electron_mobility_cm2_Vs': sc.electron_mobility_cm2_Vs,
        'failure_modes': [fm.value for fm in sc.failure_modes],
        'domain': 'semiconductor_engineering',
    }

    return StoredObject(
        name=sc.formula,
        type_name=sc.semiconductor_class.value,
        metadata=metadata,
        provenance='semiconductor_bridge.material_properties',
    )


# =============================================================================
# Interface -> StoredMorphism
# =============================================================================

@dataclass
class SemiconductorMorphism:
    """
    A semiconductor heterointerface compatibility as a categorical morphism.

    Mirrors CeramicMorphism from ceramic_bridge/integration.py.
    """
    sc_a: SemiconductorMaterial
    sc_b: SemiconductorMaterial
    interface_score: SemiconductorInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        """Convert to StoredMorphism for the categorical store."""
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='semiconductor_interface',
            source_name=self.sc_a.formula,
            target_name=self.sc_b.formula,
            metadata={
                'lattice_match': self.interface_score.lattice_match,
                'band_alignment': self.interface_score.band_alignment,
                'thermal_compatibility': self.interface_score.thermal_compatibility,
                'process_compatibility': self.interface_score.process_compatibility,
                'degradation_penalty': self.interface_score.degradation_penalty,
                'viable': self.interface_score.viable,
                'domain': 'semiconductor_engineering',
            },
            confidence=self.interface_score.total,
            provenance='semiconductor_bridge.interface_validator',
        )


def create_semiconductor_morphism(
    sc_a_name: str,
    sc_b_name: str,
    validator: Optional[SemiconductorInterfaceValidator] = None,
) -> SemiconductorMorphism:
    """
    Create a SemiconductorMorphism between two semiconductors.

    Args:
        sc_a_name: Name of first semiconductor
        sc_b_name: Name of second semiconductor
        validator: Optional pre-configured validator

    Returns:
        SemiconductorMorphism
    """
    mat_a = get_semiconductor(sc_a_name)
    mat_b = get_semiconductor(sc_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown semiconductor: {sc_a_name} or {sc_b_name}")

    validator = validator or SemiconductorInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return SemiconductorMorphism(
        sc_a=mat_a,
        sc_b=mat_b,
        interface_score=score,
    )


# =============================================================================
# Build Semiconductor Category
# =============================================================================

def build_semiconductor_category(
    semiconductors: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from semiconductor materials and their interfaces.

    Objects = semiconductors, Morphisms = compatible interfaces.

    Args:
        semiconductors: List of semiconductor names (uses all if None)

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    semiconductors = semiconductors or list(ALL_SEMICONDUCTORS.keys())
    cat = Category(name="SemiconductorMaterials")
    validator = SemiconductorInterfaceValidator()

    # Add objects
    for name in semiconductors:
        mat = get_semiconductor(name)
        if mat:
            obj = Object(
                name=mat.formula,
                type_info={
                    'full_name': mat.name,
                    'class': mat.semiconductor_class.value,
                    'crystal': mat.crystal_system.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for viable interfaces
    for i, name_a in enumerate(semiconductors):
        for name_b in semiconductors[i + 1:]:
            mat_a = get_semiconductor(name_a)
            mat_b = get_semiconductor(name_b)
            if mat_a is None or mat_b is None:
                continue

            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(mat_a.formula)
                    tgt = cat.objects.get(mat_b.formula)
                    if src and tgt:
                        mor = Morphism(
                            name=f"hetero_{mat_a.formula}_{mat_b.formula}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'semiconductor_heterointerface',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat


# =============================================================================
# Ricci Curvature on Semiconductor Graph
# =============================================================================

def compute_semiconductor_curvature(
    analysis: HeterostructureAnalysis,
) -> Optional[Dict]:
    """
    Compute Ollivier-Ricci curvature on the semiconductor interface graph.

    Negative curvature -> bottleneck layer
    Positive curvature -> redundant compatibility paths

    Args:
        analysis: Result from HeterostructureAnalyzer

    Returns:
        Dict with curvature analysis, or None if geometry module unavailable
    """
    if not RICCI_AVAILABLE:
        return None

    interfaces = analysis.interfaces
    if len(interfaces) < 2:
        return None

    nodes = set()
    for ir in interfaces:
        nodes.add(ir.sc_a)
        nodes.add(ir.sc_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.sc_a]
        j = node_idx[ir.sc_b]
        weight = ir.score.total
        adj[i, j] = weight
        adj[j, i] = weight

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.sc_a]
            j = node_idx[ir.sc_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.sc_a}<->{ir.sc_b}"] = curv

        bottleneck_edge = None
        if edge_curvatures:
            bottleneck_edge = min(edge_curvatures, key=edge_curvatures.get)

        return {
            'edge_curvatures': {k: float(v) for k, v in edge_curvatures.items()},
            'curvature_bottleneck': bottleneck_edge,
            'mean_curvature': float(np.mean(list(edge_curvatures.values()))) if edge_curvatures else 0.0,
        }
    except Exception as e:
        return {'error': str(e)}


# =============================================================================
# Sheaf Coherence: Heterostructure Consistency
# =============================================================================

def check_heterostructure_coherence(
    analysis: HeterostructureAnalysis,
) -> Dict:
    """
    Check consistency across all interfaces in a semiconductor heterostructure.

    Analogous to check_assembly_coherence in ceramic_bridge.

    Args:
        analysis: Result from HeterostructureAnalyzer

    Returns:
        Dict with coherence analysis
    """
    interfaces = analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'coherence_score': 1.0, 'num_violations': 0,
                'violations': [], 'num_shared_nodes': 0}

    violations = []

    # Group interfaces by shared semiconductor
    sc_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for sc_name in (ir.sc_a, ir.sc_b):
            if sc_name not in sc_interfaces:
                sc_interfaces[sc_name] = []
            sc_interfaces[sc_name].append(ir)

    # Check lattice match consistency at shared nodes
    for sc_name, sc_ifs in sc_interfaces.items():
        if len(sc_ifs) < 2:
            continue

        lattice_scores = [ir.score.lattice_match for ir in sc_ifs]
        if len(lattice_scores) >= 2:
            score_range = max(lattice_scores) - min(lattice_scores)
            if score_range > 0.5:
                violations.append({
                    'semiconductor': sc_name,
                    'type': 'lattice_inconsistency',
                    'scores': [round(s, 3) for s in lattice_scores],
                    'range': round(score_range, 3),
                    'note': (f'{sc_name} shows inconsistent lattice compatibility '
                             f'across its interfaces (range={score_range:.2f})'),
                })

    # Check thermal consistency at shared nodes
    for sc_name, sc_ifs in sc_interfaces.items():
        if len(sc_ifs) < 2:
            continue

        thermal_scores = [ir.score.thermal_compatibility for ir in sc_ifs]
        if len(thermal_scores) >= 2:
            score_range = max(thermal_scores) - min(thermal_scores)
            if score_range > 0.4:
                violations.append({
                    'semiconductor': sc_name,
                    'type': 'thermal_inconsistency',
                    'scores': [round(s, 3) for s in thermal_scores],
                    'range': round(score_range, 3),
                })

    coherence_score = 1.0 - min(1.0, len(violations) * 0.2)

    return {
        'coherent': len(violations) == 0,
        'coherence_score': round(coherence_score, 3),
        'num_violations': len(violations),
        'violations': violations,
        'num_shared_nodes': sum(1 for v in sc_interfaces.values() if len(v) >= 2),
    }


# =============================================================================
# Convenience: Full Categorical Analysis Pipeline
# =============================================================================

def run_semiconductor_categorical_analysis(
    config: HeterostructureConfiguration,
) -> Dict:
    """
    Run full KOMPOSOS categorical analysis on a semiconductor heterostructure.

    Combines:
    1. Heterostructure analysis
    2. Category construction
    3. Ricci curvature (if available)
    4. Sheaf coherence check

    Args:
        config: Heterostructure configuration

    Returns:
        Dict with all analysis results
    """
    analyzer = HeterostructureAnalyzer()
    analysis = analyzer.analyze_heterostructure(config)

    result = {
        'heterostructure': analysis.to_dict(),
        'coherence': check_heterostructure_coherence(analysis),
    }

    # Ricci curvature (optional)
    curvature = compute_semiconductor_curvature(analysis)
    if curvature:
        result['curvature'] = curvature

    # Category construction (optional)
    semiconductors = [config.substrate]
    semiconductors.extend(config.epitaxial_layers)
    semiconductors.extend(config.buffer_layers)

    cat = build_semiconductor_category(semiconductors)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result
