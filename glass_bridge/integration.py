# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS Integration Layer for Glass Bridge
================================================

Wires glass materials, interfaces, and assembly analysis into the existing
KOMPOSOS-III categorical infrastructure:

- Objects = Glasses (soda-lime, borosilicate, optical, chalcogenide, etc.)
- Morphisms = Seal/assembly compatibility, CTE match, chemical compatibility
- Ricci curvature = Identifies bottleneck components in multi-glass assemblies
- Sheaf coherence = Cross-validates consistency across all assembly interfaces

Mirrors ceramic_bridge/integration.py exactly.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

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

from glass_bridge.material_properties import (
    GlassMaterial, GlassClass, ALL_GLASSES, get_glass,
)
from glass_bridge.interface_validator import (
    GlassInterfaceValidator, GlassInterfaceScore,
)
from glass_bridge.assembly_analyzer import (
    GlassAssemblyAnalyzer, GlassAssemblyConfiguration, GlassAssemblyAnalysis,
)


def glass_to_stored_object(glass: GlassMaterial) -> 'StoredObject':
    """Convert a GlassMaterial to a StoredObject for the categorical store."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'formula': glass.formula,
        'glass_class': glass.glass_class.value,
        'composition_type': glass.composition_type.value,
        'Tg_C': glass.Tg_C,
        'cte_per_K': glass.cte_per_K,
        'refractive_index': glass.refractive_index,
        'failure_modes': [fm.value for fm in glass.failure_modes],
        'domain': 'glass_engineering',
    }

    return StoredObject(
        name=glass.formula,
        type_name=glass.glass_class.value,
        metadata=metadata,
        provenance='glass_bridge.material_properties',
    )


@dataclass
class GlassMorphism:
    """A glass interface compatibility as a categorical morphism."""
    glass_a: GlassMaterial
    glass_b: GlassMaterial
    interface_score: GlassInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='glass_interface',
            source_name=self.glass_a.formula,
            target_name=self.glass_b.formula,
            metadata={
                'thermal_expansion_match': self.interface_score.thermal_expansion_match,
                'viscosity_compatibility': self.interface_score.viscosity_compatibility,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'chemical_compatibility': self.interface_score.chemical_compatibility,
                'degradation_penalty': self.interface_score.degradation_penalty,
                'viable': self.interface_score.viable,
                'domain': 'glass_engineering',
            },
            confidence=self.interface_score.total,
            provenance='glass_bridge.interface_validator',
        )


def create_glass_morphism(
    glass_a_name: str,
    glass_b_name: str,
    validator: Optional[GlassInterfaceValidator] = None,
) -> GlassMorphism:
    """Create a GlassMorphism between two glasses."""
    mat_a = get_glass(glass_a_name)
    mat_b = get_glass(glass_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown glass: {glass_a_name} or {glass_b_name}")

    validator = validator or GlassInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return GlassMorphism(glass_a=mat_a, glass_b=mat_b, interface_score=score)


def build_glass_category(
    glasses: Optional[List[str]] = None,
) -> Optional['Category']:
    """Build a Category from glass materials and their interfaces."""
    if not CATEGORY_AVAILABLE:
        return None

    glasses = glasses or list(ALL_GLASSES.keys())
    cat = Category(name="GlassMaterials")
    validator = GlassInterfaceValidator()

    for name in glasses:
        mat = get_glass(name)
        if mat:
            obj = Object(
                name=mat.formula,
                type_info={
                    'full_name': mat.name,
                    'class': mat.glass_class.value,
                    'composition': mat.composition_type.value,
                },
            )
            cat.add_object(obj)

    for i, name_a in enumerate(glasses):
        for name_b in glasses[i + 1:]:
            mat_a = get_glass(name_a)
            mat_b = get_glass(name_b)
            if mat_a is None or mat_b is None:
                continue
            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(mat_a.formula)
                    tgt = cat.objects.get(mat_b.formula)
                    if src and tgt:
                        mor = Morphism(
                            name=f"seal_{mat_a.formula}_{mat_b.formula}",
                            source=src, target=tgt,
                            data={'score': score.total, 'type': 'glass_seal_interface'},
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat


def compute_glass_curvature(
    assembly_analysis: GlassAssemblyAnalysis,
) -> Optional[Dict]:
    """Compute Ollivier-Ricci curvature on the glass interface graph."""
    if not RICCI_AVAILABLE:
        return None

    interfaces = assembly_analysis.interfaces
    if len(interfaces) < 2:
        return None

    nodes = set()
    for ir in interfaces:
        nodes.add(ir.glass_a)
        nodes.add(ir.glass_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.glass_a]
        j = node_idx[ir.glass_b]
        adj[i, j] = ir.score.total
        adj[j, i] = ir.score.total

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.glass_a]
            j = node_idx[ir.glass_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.glass_a}<->{ir.glass_b}"] = curv

        bottleneck_edge = min(edge_curvatures, key=edge_curvatures.get) if edge_curvatures else None

        return {
            'edge_curvatures': {k: float(v) for k, v in edge_curvatures.items()},
            'curvature_bottleneck': bottleneck_edge,
            'mean_curvature': float(np.mean(list(edge_curvatures.values()))) if edge_curvatures else 0.0,
        }
    except Exception as e:
        return {'error': str(e)}


def check_assembly_coherence(
    assembly_analysis: GlassAssemblyAnalysis,
) -> Dict:
    """Check consistency across all interfaces in a glass assembly."""
    interfaces = assembly_analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'coherence_score': 1.0, 'num_violations': 0,
                'violations': [], 'num_shared_nodes': 0}

    violations = []

    glass_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for glass_name in (ir.glass_a, ir.glass_b):
            if glass_name not in glass_interfaces:
                glass_interfaces[glass_name] = []
            glass_interfaces[glass_name].append(ir)

    for glass_name, glass_ifs in glass_interfaces.items():
        if len(glass_ifs) < 2:
            continue

        cte_scores = [ir.score.thermal_expansion_match for ir in glass_ifs]
        if len(cte_scores) >= 2:
            score_range = max(cte_scores) - min(cte_scores)
            if score_range > 0.5:
                violations.append({
                    'glass': glass_name,
                    'type': 'cte_inconsistency',
                    'scores': [round(s, 3) for s in cte_scores],
                    'range': round(score_range, 3),
                })

    for glass_name, glass_ifs in glass_interfaces.items():
        if len(glass_ifs) < 2:
            continue

        mech_scores = [ir.score.mechanical_compatibility for ir in glass_ifs]
        if len(mech_scores) >= 2:
            score_range = max(mech_scores) - min(mech_scores)
            if score_range > 0.4:
                violations.append({
                    'glass': glass_name,
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
        'num_shared_nodes': sum(1 for v in glass_interfaces.values() if len(v) >= 2),
    }


def run_glass_categorical_analysis(
    config: GlassAssemblyConfiguration,
) -> Dict:
    """Run full KOMPOSOS categorical analysis on a glass assembly."""
    analyzer = GlassAssemblyAnalyzer()
    assembly_analysis = analyzer.analyze_assembly(config)

    result = {
        'assembly': assembly_analysis.to_dict(),
        'coherence': check_assembly_coherence(assembly_analysis),
    }

    curvature = compute_glass_curvature(assembly_analysis)
    if curvature:
        result['curvature'] = curvature

    glasses = [config.primary_glass]
    glasses.extend(config.secondary_glasses)
    glasses.extend(config.coating_glasses)

    cat = build_glass_category(glasses)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result
