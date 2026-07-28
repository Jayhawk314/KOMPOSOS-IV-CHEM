# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS Integration Layer for Polymer Bridge
=================================================

Wires polymer materials, interfaces, and blend analysis into the existing
KOMPOSOS-III categorical infrastructure:

- Objects = Polymers, Solvents, Additives
- Morphisms = Blend compatibility, solvent dissolution, interfacial adhesion
- Ricci curvature = Identifies bottleneck components in multi-polymer systems
- Sheaf coherence = Cross-validates consistency across all blend interfaces

Mirrors battery_bridge/integration.py exactly.
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

from polymer_bridge.material_properties import (
    PolymerMaterial, PolymerClass, ALL_POLYMERS, get_polymer,
)
from polymer_bridge.interface_validator import (
    PolymerInterfaceValidator, PolymerInterfaceScore,
)
from polymer_bridge.blend_analyzer import (
    PolymerBlendAnalyzer, BlendConfiguration, BlendAnalysis,
)


# =============================================================================
# Polymer -> StoredObject
# =============================================================================

def polymer_to_stored_object(polymer: PolymerMaterial) -> 'StoredObject':
    """
    Convert a PolymerMaterial to a StoredObject for the categorical store.

    Mirrors material_to_stored_object from battery_bridge/integration.py.

    Args:
        polymer: Polymer material

    Returns:
        StoredObject for the KOMPOSOS data store

    Raises:
        ImportError: If data.store is not available
    """
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    metadata = {
        'abbreviation': polymer.abbreviation,
        'polymer_class': polymer.polymer_class.value,
        'structure': polymer.structure.value,
        'glass_transition_C': polymer.glass_transition_C,
        'melting_point_C': polymer.melting_point_C,
        'elastic_modulus_GPa': polymer.elastic_modulus_GPa,
        'failure_modes': [fm.value for fm in polymer.failure_modes],
        'domain': 'polymer_engineering',
    }
    if polymer.hansen:
        metadata['hansen_delta_total'] = round(polymer.hansen.delta_total, 2)

    return StoredObject(
        name=polymer.abbreviation,
        type_name=polymer.polymer_class.value,
        metadata=metadata,
        provenance='polymer_bridge.material_properties',
    )


# =============================================================================
# Interface -> StoredMorphism
# =============================================================================

@dataclass
class PolymerMorphism:
    """
    A polymer interface/blend compatibility as a categorical morphism.

    Mirrors InterfaceMorphism from battery_bridge/integration.py.
    """
    polymer_a: PolymerMaterial
    polymer_b: PolymerMaterial
    interface_score: PolymerInterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        """Convert to StoredMorphism for the categorical store."""
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='polymer_interface',
            source_name=self.polymer_a.abbreviation,
            target_name=self.polymer_b.abbreviation,
            metadata={
                'solubility_compatibility': self.interface_score.solubility_compatibility,
                'thermal_compatibility': self.interface_score.thermal_compatibility,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'chemical_resistance': self.interface_score.chemical_resistance,
                'aging_penalty': self.interface_score.aging_penalty,
                'viable': self.interface_score.viable,
                'domain': 'polymer_engineering',
            },
            confidence=self.interface_score.total,
            provenance='polymer_bridge.interface_validator',
        )


def create_polymer_morphism(
    polymer_a_name: str,
    polymer_b_name: str,
    validator: Optional[PolymerInterfaceValidator] = None,
) -> PolymerMorphism:
    """
    Create a PolymerMorphism between two polymers.

    Args:
        polymer_a_name: Name of first polymer
        polymer_b_name: Name of second polymer
        validator: Optional pre-configured validator

    Returns:
        PolymerMorphism
    """
    mat_a = get_polymer(polymer_a_name)
    mat_b = get_polymer(polymer_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown polymer: {polymer_a_name} or {polymer_b_name}")

    validator = validator or PolymerInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return PolymerMorphism(
        polymer_a=mat_a,
        polymer_b=mat_b,
        interface_score=score,
    )


# =============================================================================
# Build Polymer Category
# =============================================================================

def build_polymer_category(
    polymers: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from polymer materials and their interfaces.

    Objects = polymers, Morphisms = compatible blend interfaces.

    Args:
        polymers: List of polymer names (uses all if None)

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    polymers = polymers or list(ALL_POLYMERS.keys())
    cat = Category(name="PolymerMaterials")
    validator = PolymerInterfaceValidator()

    # Add objects
    for name in polymers:
        mat = get_polymer(name)
        if mat:
            obj = Object(
                name=mat.abbreviation,
                type_info={
                    'full_name': mat.name,
                    'class': mat.polymer_class.value,
                    'structure': mat.structure.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for viable interfaces
    for i, name_a in enumerate(polymers):
        for name_b in polymers[i + 1:]:
            mat_a = get_polymer(name_a)
            mat_b = get_polymer(name_b)
            if mat_a is None or mat_b is None:
                continue

            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(mat_a.abbreviation)
                    tgt = cat.objects.get(mat_b.abbreviation)
                    if src and tgt:
                        mor = Morphism(
                            name=f"blend_{mat_a.abbreviation}_{mat_b.abbreviation}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'polymer_blend_interface',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass

    return cat


# =============================================================================
# Ricci Curvature on Polymer Graph
# =============================================================================

def compute_polymer_curvature(
    blend_analysis: BlendAnalysis,
) -> Optional[Dict]:
    """
    Compute Ollivier-Ricci curvature on the polymer interface graph.

    Negative curvature -> bottleneck component
    Positive curvature -> redundant compatibility paths

    Args:
        blend_analysis: Result from PolymerBlendAnalyzer

    Returns:
        Dict with curvature analysis, or None if geometry module unavailable
    """
    if not RICCI_AVAILABLE:
        return None

    interfaces = blend_analysis.interfaces
    if len(interfaces) < 2:
        return None

    nodes = set()
    for ir in interfaces:
        nodes.add(ir.polymer_a)
        nodes.add(ir.polymer_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.polymer_a]
        j = node_idx[ir.polymer_b]
        weight = ir.score.total
        adj[i, j] = weight
        adj[j, i] = weight

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.polymer_a]
            j = node_idx[ir.polymer_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.polymer_a}<->{ir.polymer_b}"] = curv

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
# Sheaf Coherence: Blend Consistency
# =============================================================================

def check_blend_coherence(
    blend_analysis: BlendAnalysis,
) -> Dict:
    """
    Check consistency across all interfaces in a blend.

    Analogous to sheaf coherence in battery_bridge: if polymer A is
    compatible with B and B is compatible with C, the scores at B
    should be self-consistent.

    Args:
        blend_analysis: Result from PolymerBlendAnalyzer

    Returns:
        Dict with coherence analysis
    """
    interfaces = blend_analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'coherence_score': 1.0, 'num_violations': 0,
                'violations': [], 'num_shared_nodes': 0}

    violations = []

    # Group interfaces by shared polymer
    polymer_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for poly_name in (ir.polymer_a, ir.polymer_b):
            if poly_name not in polymer_interfaces:
                polymer_interfaces[poly_name] = []
            polymer_interfaces[poly_name].append(ir)

    # Check solubility consistency at shared nodes
    for poly_name, poly_ifs in polymer_interfaces.items():
        if len(poly_ifs) < 2:
            continue

        sol_scores = [ir.score.solubility_compatibility for ir in poly_ifs]
        if len(sol_scores) >= 2:
            score_range = max(sol_scores) - min(sol_scores)
            if score_range > 0.5:
                violations.append({
                    'polymer': poly_name,
                    'type': 'solubility_inconsistency',
                    'scores': [round(s, 3) for s in sol_scores],
                    'range': round(score_range, 3),
                    'note': (f'{poly_name} shows inconsistent solubility compatibility '
                             f'across its interfaces (range={score_range:.2f})'),
                })

    # Check mechanical consistency at shared nodes
    for poly_name, poly_ifs in polymer_interfaces.items():
        if len(poly_ifs) < 2:
            continue

        mech_scores = [ir.score.mechanical_compatibility for ir in poly_ifs]
        if len(mech_scores) >= 2:
            score_range = max(mech_scores) - min(mech_scores)
            if score_range > 0.4:
                violations.append({
                    'polymer': poly_name,
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
        'num_shared_nodes': sum(1 for v in polymer_interfaces.values() if len(v) >= 2),
    }


# =============================================================================
# Convenience: Full Categorical Analysis Pipeline
# =============================================================================

def run_polymer_categorical_analysis(
    config: BlendConfiguration,
) -> Dict:
    """
    Run full KOMPOSOS categorical analysis on a polymer blend configuration.

    Combines:
    1. Blend analysis
    2. Category construction
    3. Ricci curvature (if available)
    4. Sheaf coherence check

    Args:
        config: Blend configuration

    Returns:
        Dict with all analysis results
    """
    analyzer = PolymerBlendAnalyzer()
    blend_analysis = analyzer.analyze_blend(config)

    result = {
        'blend': blend_analysis.to_dict(),
        'coherence': check_blend_coherence(blend_analysis),
    }

    # Ricci curvature (optional)
    curvature = compute_polymer_curvature(blend_analysis)
    if curvature:
        result['curvature'] = curvature

    # Category construction (optional)
    polymers = [config.primary_polymer]
    polymers.extend(config.secondary_polymers)
    polymers.extend(config.additives)

    cat = build_polymer_category(polymers)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result


if __name__ == "__main__":
    from polymer_bridge.blend_analyzer import (
        STANDARD_PEO_ELECTROLYTE, STANDARD_PVDF_BINDER,
    )

    print("=" * 70)
    print("KOMPOSOS Integration - Polymer Bridge")
    print("=" * 70)
    print()

    for config in [STANDARD_PEO_ELECTROLYTE, STANDARD_PVDF_BINDER]:
        print(f"--- {config.name} ---")
        result = run_polymer_categorical_analysis(config)

        blend = result['blend']
        print(f"  Compatibility: {blend['overall_compatibility']:.3f}")
        print(f"  Compatible: {blend['compatible']}")
        if blend.get('bottleneck'):
            print(f"  Bottleneck: {blend['bottleneck']}")

        coherence = result['coherence']
        print(f"  Coherent: {coherence['coherent']} "
              f"(score={coherence['coherence_score']:.2f})")

        if 'curvature' in result:
            curv = result['curvature']
            if 'mean_curvature' in curv:
                print(f"  Mean Ricci curvature: {curv['mean_curvature']:.3f}")

        if 'category' in result:
            cat = result['category']
            print(f"  Category: {cat['num_objects']} objects, "
                  f"{cat['num_morphisms']} morphisms")

        print()
