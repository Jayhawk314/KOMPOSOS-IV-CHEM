# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS Integration Layer for Ceramic Bridge
=================================================

Wires ceramic materials, interfaces, and assembly analysis into the existing
KOMPOSOS-III categorical infrastructure:

- Objects = Ceramics (oxides, carbides, nitrides, glasses, etc.)
- Morphisms = Composite compatibility, CTE match, chemical compatibility
- Ricci curvature = Identifies bottleneck components in multi-ceramic assemblies
- Sheaf coherence = Cross-validates consistency across all assembly interfaces

Mirrors metal_bridge/integration.py exactly.
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

from ceramic_bridge.material_properties import (
    CeramicMaterial, CeramicClass, ALL_CERAMICS, get_ceramic,
)
from ceramic_bridge.interface_validator import (
    CeramicInterfaceValidator, CeramicInterfaceScore,
)
from ceramic_bridge.assembly_analyzer import (
    CeramicAssemblyAnalyzer, AssemblyConfiguration, AssemblyAnalysis,
)


# =============================================================================
# Ceramic -> StoredObject
# =============================================================================

def ceramic_to_stored_object(ceramic: CeramicMaterial) -> 'StoredObject':
    """
    Convert a CeramicMaterial to a StoredObject for the categorical store.

    Args:
        ceramic: Ceramic material

    Returns:
        StoredObject for the KOMPOSOS data store

    Raises:
        ImportError: If data.store is not available
    """
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'formula': ceramic.formula,
        'ceramic_class': ceramic.ceramic_class.value,
        'crystal_system': ceramic.crystal_system.value,
        'sintering_temp_C': ceramic.sintering_temp_C,
        'elastic_modulus_GPa': ceramic.elastic_modulus_GPa,
        'fracture_toughness_MPa_m05': ceramic.fracture_toughness_MPa_m05,
        'failure_modes': [fm.value for fm in ceramic.failure_modes],
        'domain': 'ceramic_engineering',
    }

    return StoredObject(
        name=ceramic.formula,
        type_name=ceramic.ceramic_class.value,
        metadata=metadata,
        provenance='ceramic_bridge.material_properties',
    )


# =============================================================================
# Interface -> StoredMorphism
# =============================================================================

@dataclass
class CeramicMorphism:
    """
    A ceramic interface/composite compatibility as a categorical morphism.

    Mirrors MetalMorphism from metal_bridge/integration.py.
    """
    ceramic_a: CeramicMaterial
    ceramic_b: CeramicMaterial
    interface_score: CeramicInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        """Convert to StoredMorphism for the categorical store."""
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='ceramic_interface',
            source_name=self.ceramic_a.formula,
            target_name=self.ceramic_b.formula,
            metadata={
                'sintering_compatibility': self.interface_score.sintering_compatibility,
                'cte_match': self.interface_score.cte_match,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'chemical_compatibility': self.interface_score.chemical_compatibility,
                'degradation_penalty': self.interface_score.degradation_penalty,
                'viable': self.interface_score.viable,
                'domain': 'ceramic_engineering',
            },
            confidence=self.interface_score.total,
            provenance='ceramic_bridge.interface_validator',
        )


def create_ceramic_morphism(
    ceramic_a_name: str,
    ceramic_b_name: str,
    validator: Optional[CeramicInterfaceValidator] = None,
) -> CeramicMorphism:
    """
    Create a CeramicMorphism between two ceramics.

    Args:
        ceramic_a_name: Name of first ceramic
        ceramic_b_name: Name of second ceramic
        validator: Optional pre-configured validator

    Returns:
        CeramicMorphism
    """
    mat_a = get_ceramic(ceramic_a_name)
    mat_b = get_ceramic(ceramic_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown ceramic: {ceramic_a_name} or {ceramic_b_name}")

    validator = validator or CeramicInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return CeramicMorphism(
        ceramic_a=mat_a,
        ceramic_b=mat_b,
        interface_score=score,
    )


# =============================================================================
# Build Ceramic Category
# =============================================================================

def build_ceramic_category(
    ceramics: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from ceramic materials and their interfaces.

    Objects = ceramics, Morphisms = compatible interfaces.

    Args:
        ceramics: List of ceramic names (uses all if None)

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    ceramics = ceramics or list(ALL_CERAMICS.keys())
    cat = Category(name="CeramicMaterials")
    validator = CeramicInterfaceValidator()

    # Add objects
    for name in ceramics:
        mat = get_ceramic(name)
        if mat:
            obj = Object(
                name=mat.formula,
                type_info={
                    'full_name': mat.name,
                    'class': mat.ceramic_class.value,
                    'crystal': mat.crystal_system.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for viable interfaces
    for i, name_a in enumerate(ceramics):
        for name_b in ceramics[i + 1:]:
            mat_a = get_ceramic(name_a)
            mat_b = get_ceramic(name_b)
            if mat_a is None or mat_b is None:
                continue

            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(mat_a.formula)
                    tgt = cat.objects.get(mat_b.formula)
                    if src and tgt:
                        mor = Morphism(
                            name=f"composite_{mat_a.formula}_{mat_b.formula}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'ceramic_composite_interface',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat


# =============================================================================
# Ricci Curvature on Ceramic Graph
# =============================================================================

def compute_ceramic_curvature(
    assembly_analysis: AssemblyAnalysis,
) -> Optional[Dict]:
    """
    Compute Ollivier-Ricci curvature on the ceramic interface graph.

    Negative curvature -> bottleneck component
    Positive curvature -> redundant compatibility paths

    Args:
        assembly_analysis: Result from CeramicAssemblyAnalyzer

    Returns:
        Dict with curvature analysis, or None if geometry module unavailable
    """
    if not RICCI_AVAILABLE:
        return None

    interfaces = assembly_analysis.interfaces
    if len(interfaces) < 2:
        return None

    nodes = set()
    for ir in interfaces:
        nodes.add(ir.ceramic_a)
        nodes.add(ir.ceramic_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.ceramic_a]
        j = node_idx[ir.ceramic_b]
        weight = ir.score.total
        adj[i, j] = weight
        adj[j, i] = weight

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.ceramic_a]
            j = node_idx[ir.ceramic_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.ceramic_a}<->{ir.ceramic_b}"] = curv

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
# Sheaf Coherence: Assembly Consistency
# =============================================================================

def check_assembly_coherence(
    assembly_analysis: AssemblyAnalysis,
) -> Dict:
    """
    Check consistency across all interfaces in a ceramic assembly.

    Analogous to check_joint_coherence in metal_bridge.

    Args:
        assembly_analysis: Result from CeramicAssemblyAnalyzer

    Returns:
        Dict with coherence analysis
    """
    interfaces = assembly_analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'coherence_score': 1.0, 'num_violations': 0,
                'violations': [], 'num_shared_nodes': 0}

    violations = []

    # Group interfaces by shared ceramic
    ceramic_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for ceramic_name in (ir.ceramic_a, ir.ceramic_b):
            if ceramic_name not in ceramic_interfaces:
                ceramic_interfaces[ceramic_name] = []
            ceramic_interfaces[ceramic_name].append(ir)

    # Check CTE consistency at shared nodes
    for ceramic_name, ceramic_ifs in ceramic_interfaces.items():
        if len(ceramic_ifs) < 2:
            continue

        cte_scores = [ir.score.cte_match for ir in ceramic_ifs]
        if len(cte_scores) >= 2:
            score_range = max(cte_scores) - min(cte_scores)
            if score_range > 0.5:
                violations.append({
                    'ceramic': ceramic_name,
                    'type': 'cte_inconsistency',
                    'scores': [round(s, 3) for s in cte_scores],
                    'range': round(score_range, 3),
                    'note': (f'{ceramic_name} shows inconsistent CTE compatibility '
                             f'across its interfaces (range={score_range:.2f})'),
                })

    # Check mechanical consistency at shared nodes
    for ceramic_name, ceramic_ifs in ceramic_interfaces.items():
        if len(ceramic_ifs) < 2:
            continue

        mech_scores = [ir.score.mechanical_compatibility for ir in ceramic_ifs]
        if len(mech_scores) >= 2:
            score_range = max(mech_scores) - min(mech_scores)
            if score_range > 0.4:
                violations.append({
                    'ceramic': ceramic_name,
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
        'num_shared_nodes': sum(1 for v in ceramic_interfaces.values() if len(v) >= 2),
    }


# =============================================================================
# Convenience: Full Categorical Analysis Pipeline
# =============================================================================

def run_ceramic_categorical_analysis(
    config: AssemblyConfiguration,
) -> Dict:
    """
    Run full KOMPOSOS categorical analysis on a ceramic assembly configuration.

    Combines:
    1. Assembly analysis
    2. Category construction
    3. Ricci curvature (if available)
    4. Sheaf coherence check

    Args:
        config: Assembly configuration

    Returns:
        Dict with all analysis results
    """
    analyzer = CeramicAssemblyAnalyzer()
    assembly_analysis = analyzer.analyze_assembly(config)

    result = {
        'assembly': assembly_analysis.to_dict(),
        'coherence': check_assembly_coherence(assembly_analysis),
    }

    # Ricci curvature (optional)
    curvature = compute_ceramic_curvature(assembly_analysis)
    if curvature:
        result['curvature'] = curvature

    # Category construction (optional)
    ceramics = [config.primary_ceramic]
    ceramics.extend(config.secondary_ceramics)
    ceramics.extend(config.coating_ceramics)

    cat = build_ceramic_category(ceramics)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result
