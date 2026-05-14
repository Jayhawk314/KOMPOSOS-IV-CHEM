# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS Integration Layer for Metal Bridge
=================================================

Wires metal materials, interfaces, and joint analysis into the existing
KOMPOSOS-III categorical infrastructure:

- Objects = Metals, Alloys
- Morphisms = Joint compatibility, galvanic coupling, thermal expansion match
- Ricci curvature = Identifies bottleneck components in multi-metal assemblies
- Sheaf coherence = Cross-validates consistency across all joint interfaces

Mirrors polymer_bridge/integration.py exactly.
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

from metal_bridge.material_properties import (
    MetalMaterial, MetalClass, ALL_METALS, get_metal,
)
from metal_bridge.interface_validator import (
    MetalInterfaceValidator, MetalInterfaceScore,
)
from metal_bridge.joint_analyzer import (
    MetalJointAnalyzer, JointConfiguration, JointAnalysis,
)


# =============================================================================
# Metal -> StoredObject
# =============================================================================

def metal_to_stored_object(metal: MetalMaterial) -> 'StoredObject':
    """
    Convert a MetalMaterial to a StoredObject for the categorical store.

    Args:
        metal: Metal material

    Returns:
        StoredObject for the KOMPOSOS data store

    Raises:
        ImportError: If data.store is not available
    """
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'formula': metal.formula,
        'metal_class': metal.metal_class.value,
        'crystal_system': metal.crystal_system.value,
        'melting_point_C': metal.melting_point_C,
        'elastic_modulus_GPa': metal.elastic_modulus_GPa,
        'galvanic_potential_V': metal.galvanic_potential_V,
        'failure_modes': [fm.value for fm in metal.failure_modes],
        'domain': 'metal_engineering',
    }

    return StoredObject(
        name=metal.formula,
        type_name=metal.metal_class.value,
        metadata=metadata,
        provenance='metal_bridge.material_properties',
    )


# =============================================================================
# Interface -> StoredMorphism
# =============================================================================

@dataclass
class MetalMorphism:
    """
    A metal interface/joint compatibility as a categorical morphism.

    Mirrors PolymerMorphism from polymer_bridge/integration.py.
    """
    metal_a: MetalMaterial
    metal_b: MetalMaterial
    interface_score: MetalInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        """Convert to StoredMorphism for the categorical store."""
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='metal_interface',
            source_name=self.metal_a.formula,
            target_name=self.metal_b.formula,
            metadata={
                'galvanic_compatibility': self.interface_score.galvanic_compatibility,
                'thermal_compatibility': self.interface_score.thermal_compatibility,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'metallurgical_compatibility': self.interface_score.metallurgical_compatibility,
                'corrosion_penalty': self.interface_score.corrosion_penalty,
                'viable': self.interface_score.viable,
                'domain': 'metal_engineering',
            },
            confidence=self.interface_score.total,
            provenance='metal_bridge.interface_validator',
        )


def create_metal_morphism(
    metal_a_name: str,
    metal_b_name: str,
    validator: Optional[MetalInterfaceValidator] = None,
) -> MetalMorphism:
    """
    Create a MetalMorphism between two metals.

    Args:
        metal_a_name: Name of first metal
        metal_b_name: Name of second metal
        validator: Optional pre-configured validator

    Returns:
        MetalMorphism
    """
    mat_a = get_metal(metal_a_name)
    mat_b = get_metal(metal_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown metal: {metal_a_name} or {metal_b_name}")

    validator = validator or MetalInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return MetalMorphism(
        metal_a=mat_a,
        metal_b=mat_b,
        interface_score=score,
    )


# =============================================================================
# Build Metal Category
# =============================================================================

def build_metal_category(
    metals: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from metal materials and their interfaces.

    Objects = metals, Morphisms = compatible joint interfaces.

    Args:
        metals: List of metal names (uses all if None)

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    metals = metals or list(ALL_METALS.keys())
    cat = Category(name="MetalMaterials")
    validator = MetalInterfaceValidator()

    # Add objects
    for name in metals:
        mat = get_metal(name)
        if mat:
            obj = Object(
                name=mat.formula,
                type_info={
                    'full_name': mat.name,
                    'class': mat.metal_class.value,
                    'crystal': mat.crystal_system.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for viable interfaces
    for i, name_a in enumerate(metals):
        for name_b in metals[i + 1:]:
            mat_a = get_metal(name_a)
            mat_b = get_metal(name_b)
            if mat_a is None or mat_b is None:
                continue

            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(mat_a.formula)
                    tgt = cat.objects.get(mat_b.formula)
                    if src and tgt:
                        mor = Morphism(
                            name=f"joint_{mat_a.formula}_{mat_b.formula}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'metal_joint_interface',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat


# =============================================================================
# Ricci Curvature on Metal Graph
# =============================================================================

def compute_metal_curvature(
    joint_analysis: JointAnalysis,
) -> Optional[Dict]:
    """
    Compute Ollivier-Ricci curvature on the metal interface graph.

    Negative curvature -> bottleneck component
    Positive curvature -> redundant compatibility paths

    Args:
        joint_analysis: Result from MetalJointAnalyzer

    Returns:
        Dict with curvature analysis, or None if geometry module unavailable
    """
    if not RICCI_AVAILABLE:
        return None

    interfaces = joint_analysis.interfaces
    if len(interfaces) < 2:
        return None

    nodes = set()
    for ir in interfaces:
        nodes.add(ir.metal_a)
        nodes.add(ir.metal_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.metal_a]
        j = node_idx[ir.metal_b]
        weight = ir.score.total
        adj[i, j] = weight
        adj[j, i] = weight

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.metal_a]
            j = node_idx[ir.metal_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.metal_a}<->{ir.metal_b}"] = curv

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
# Sheaf Coherence: Joint Consistency
# =============================================================================

def check_joint_coherence(
    joint_analysis: JointAnalysis,
) -> Dict:
    """
    Check consistency across all interfaces in a joint assembly.

    Analogous to check_blend_coherence in polymer_bridge.

    Args:
        joint_analysis: Result from MetalJointAnalyzer

    Returns:
        Dict with coherence analysis
    """
    interfaces = joint_analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'coherence_score': 1.0, 'num_violations': 0,
                'violations': [], 'num_shared_nodes': 0}

    violations = []

    # Group interfaces by shared metal
    metal_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for metal_name in (ir.metal_a, ir.metal_b):
            if metal_name not in metal_interfaces:
                metal_interfaces[metal_name] = []
            metal_interfaces[metal_name].append(ir)

    # Check galvanic consistency at shared nodes
    for metal_name, metal_ifs in metal_interfaces.items():
        if len(metal_ifs) < 2:
            continue

        galv_scores = [ir.score.galvanic_compatibility for ir in metal_ifs]
        if len(galv_scores) >= 2:
            score_range = max(galv_scores) - min(galv_scores)
            if score_range > 0.5:
                violations.append({
                    'metal': metal_name,
                    'type': 'galvanic_inconsistency',
                    'scores': [round(s, 3) for s in galv_scores],
                    'range': round(score_range, 3),
                    'note': (f'{metal_name} shows inconsistent galvanic compatibility '
                             f'across its interfaces (range={score_range:.2f})'),
                })

    # Check mechanical consistency at shared nodes
    for metal_name, metal_ifs in metal_interfaces.items():
        if len(metal_ifs) < 2:
            continue

        mech_scores = [ir.score.mechanical_compatibility for ir in metal_ifs]
        if len(mech_scores) >= 2:
            score_range = max(mech_scores) - min(mech_scores)
            if score_range > 0.4:
                violations.append({
                    'metal': metal_name,
                    'type': 'mechanical_inconsistency',
                    'scores': [round(s, 3) for s in mech_scores],
                    'range': round(score_range, 3),
                })

    coherence_score = 1.0 - min(1.0, len(violations) * 0.2)

    return {
        'coherent': len(violations) == 0,
        'coherence_score': round(coherence_score, 3),
        'num_violations': len(violations),
        'violations': violations,
        'num_shared_nodes': sum(1 for v in metal_interfaces.values() if len(v) >= 2),
    }


# =============================================================================
# Convenience: Full Categorical Analysis Pipeline
# =============================================================================

def run_metal_categorical_analysis(
    config: JointConfiguration,
) -> Dict:
    """
    Run full KOMPOSOS categorical analysis on a metal joint configuration.

    Combines:
    1. Joint analysis
    2. Category construction
    3. Ricci curvature (if available)
    4. Sheaf coherence check

    Args:
        config: Joint configuration

    Returns:
        Dict with all analysis results
    """
    analyzer = MetalJointAnalyzer()
    joint_analysis = analyzer.analyze_joint(config)

    result = {
        'joint': joint_analysis.to_dict(),
        'coherence': check_joint_coherence(joint_analysis),
    }

    # Ricci curvature (optional)
    curvature = compute_metal_curvature(joint_analysis)
    if curvature:
        result['curvature'] = curvature

    # Category construction (optional)
    metals = [config.primary_metal]
    metals.extend(config.secondary_metals)
    metals.extend(config.filler_metals)

    cat = build_metal_category(metals)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result
