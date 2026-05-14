# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS Integration Layer for Battery Bridge
================================================

Wires battery materials, interfaces, and flow analysis into the existing
KOMPOSOS-III categorical infrastructure:

- Objects = Materials, Phases, Ions
- Morphisms = Electrochemical reactions, phase transitions, ion transport
- Ricci curvature = Identifies bottleneck phases in charge/discharge
- Persistent homology = Dendrite topology, pore network analysis
- Sheaf coherence = Cross-validates thermodynamic constraints across full cell

This mirrors how chemistry/hydrogen_bonds.py creates HBondMorphism objects
that map into the StoredMorphism / StoredObject framework in data/store.py.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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

try:
    from topology.persistence import PersistentHomologyAnalyzer
    TOPOLOGY_AVAILABLE = True
except ImportError:
    TOPOLOGY_AVAILABLE = False

import numpy as np

from battery_bridge.material_properties import (
    BatteryMaterial, MaterialClass, ALL_MATERIALS, get_material,
)
from battery_bridge.interface_validator import (
    BatteryInterfaceValidator, InterfaceScore,
)
from battery_bridge.battery_flow import (
    BatteryFlowAnalyzer, CellConfiguration, CellAnalysis,
)


# =============================================================================
# Material -> StoredObject
# =============================================================================

def material_to_stored_object(material: BatteryMaterial) -> 'StoredObject':
    """
    Convert a BatteryMaterial to a StoredObject for the categorical store.

    This is the battery analogue of creating residue objects in the protein bridge.

    Args:
        material: Battery material

    Returns:
        StoredObject for the KOMPOSOS data store

    Raises:
        ImportError: If data.store is not available
    """
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available - data.store not found")

    return StoredObject(
        name=material.name,
        type_name=material.material_class.value,
        metadata={
            'formula': material.formula,
            'crystal_structure': material.crystal_structure.value,
            'theoretical_capacity': material.theoretical_capacity,
            'ionic_conductivity': material.ionic_conductivity,
            'thermal_stability_max': material.thermal_stability_max,
            'failure_modes': [fm.value for fm in material.failure_modes],
            'domain': 'battery_engineering',
        },
        provenance='battery_bridge.material_properties',
    )


# =============================================================================
# Interface -> StoredMorphism
# =============================================================================

@dataclass
class InterfaceMorphism:
    """
    An electrochemical interface as a categorical morphism.

    Mirrors chemistry/hydrogen_bonds.py HBondMorphism:
    - H-bond donor/acceptor -> electrode/electrolyte
    - H-bond strength -> interface viability score
    - H-bond type -> interface type (anode-SE, cathode-solvent, etc.)
    """
    material_a: BatteryMaterial
    material_b: BatteryMaterial
    interface_score: InterfaceScore

    def to_stored_morphism(self) -> 'StoredMorphism':
        """Convert to StoredMorphism for the categorical store."""
        if not STORE_AVAILABLE or StoredMorphism is None:
            raise ImportError("StoredMorphism not available")

        return StoredMorphism(
            name='electrochemical_interface',
            source_name=self.material_a.name,
            target_name=self.material_b.name,
            metadata={
                'ion_transport': self.interface_score.ion_transport,
                'electrochemical_stability': self.interface_score.electrochemical_stability,
                'interface_compatibility': self.interface_score.interface_compatibility,
                'mechanical_compatibility': self.interface_score.mechanical_compatibility,
                'degradation_penalty': self.interface_score.degradation_penalty,
                'viable': self.interface_score.viable,
                'domain': 'battery_engineering',
            },
            confidence=self.interface_score.total,
            provenance='battery_bridge.interface_validator',
        )


def create_interface_morphism(
    material_a_name: str,
    material_b_name: str,
    validator: Optional[BatteryInterfaceValidator] = None,
) -> InterfaceMorphism:
    """
    Create an InterfaceMorphism between two materials.

    Args:
        material_a_name: Name of first material
        material_b_name: Name of second material
        validator: Optional pre-configured validator

    Returns:
        InterfaceMorphism
    """
    mat_a = get_material(material_a_name)
    mat_b = get_material(material_b_name)
    if mat_a is None or mat_b is None:
        raise ValueError(f"Unknown material: {material_a_name} or {material_b_name}")

    validator = validator or BatteryInterfaceValidator()
    score = validator.validate_materials(mat_a, mat_b)

    return InterfaceMorphism(
        material_a=mat_a,
        material_b=mat_b,
        interface_score=score,
    )


# =============================================================================
# Build Battery Category
# =============================================================================

def build_battery_category(
    materials: Optional[List[str]] = None,
) -> Optional['Category']:
    """
    Build a Category object from battery materials and their interfaces.

    Objects = materials, Morphisms = viable interfaces.
    This is the battery-domain analogue of building a protein contact
    category from residues and their interactions.

    Args:
        materials: List of material names (uses all if None)

    Returns:
        Category object, or None if categorical module unavailable
    """
    if not CATEGORY_AVAILABLE:
        return None

    materials = materials or list(ALL_MATERIALS.keys())
    cat = Category(name="BatteryMaterials")
    validator = BatteryInterfaceValidator()

    # Add objects
    for name in materials:
        mat = get_material(name)
        if mat:
            obj = Object(
                name=mat.name,
                type_info={
                    'formula': mat.formula,
                    'class': mat.material_class.value,
                    'crystal': mat.crystal_structure.value,
                },
            )
            cat.add_object(obj)

    # Add morphisms for viable interfaces
    for i, name_a in enumerate(materials):
        for name_b in materials[i + 1:]:
            mat_a = get_material(name_a)
            mat_b = get_material(name_b)
            if mat_a is None or mat_b is None:
                continue

            try:
                score = validator.validate_materials(mat_a, mat_b)
                if score.viable:
                    src = cat.objects.get(name_a)
                    tgt = cat.objects.get(name_b)
                    if src and tgt:
                        mor = Morphism(
                            name=f"interface_{name_a}_{name_b}",
                            source=src,
                            target=tgt,
                            data={
                                'score': score.total,
                                'type': 'electrochemical_interface',
                            },
                        )
                        cat.add_morphism(mor)
            except Exception:
                pass  # Skip problematic pairs

    return cat


# =============================================================================
# Ricci Curvature on Battery Graph
# =============================================================================

def compute_battery_curvature(
    cell_analysis: CellAnalysis,
) -> Optional[Dict]:
    """
    Compute Ollivier-Ricci curvature on the battery interface graph.

    Negative curvature -> bottleneck (ion transport highway with few alternatives)
    Positive curvature -> redundant paths (robust interface)
    Zero curvature -> chain-like topology

    This identifies which interfaces are topological bottlenecks in the
    electrochemical network, analogous to how Ricci curvature identifies
    information bottlenecks in the drug-protein-disease graph.

    Args:
        cell_analysis: Result from BatteryFlowAnalyzer

    Returns:
        Dict with curvature analysis, or None if geometry module unavailable
    """
    if not RICCI_AVAILABLE:
        return None

    # Build adjacency from interface scores
    interfaces = cell_analysis.interfaces
    if len(interfaces) < 2:
        return None

    # Collect unique node names
    nodes = set()
    for ir in interfaces:
        nodes.add(ir.material_a)
        nodes.add(ir.material_b)
    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    # Build weighted adjacency matrix
    n = len(nodes)
    adj = np.zeros((n, n))
    for ir in interfaces:
        i = node_idx[ir.material_a]
        j = node_idx[ir.material_b]
        weight = ir.score.total
        adj[i, j] = weight
        adj[j, i] = weight

    try:
        ricci = OllivierRicciCurvature()
        result = ricci.compute_all_curvatures(adj)

        # Map curvatures back to interface pairs
        edge_curvatures = {}
        for ir in interfaces:
            i = node_idx[ir.material_a]
            j = node_idx[ir.material_b]
            curv = result.edge_curvatures.get((i, j), 0.0)
            edge_curvatures[f"{ir.material_a}<->{ir.material_b}"] = curv

        # Find most negative curvature = biggest bottleneck
        if edge_curvatures:
            bottleneck_edge = min(edge_curvatures, key=edge_curvatures.get)
        else:
            bottleneck_edge = None

        return {
            'node_curvatures': {nodes[i]: float(c) for i, c in enumerate(result.node_curvatures)}
                if hasattr(result, 'node_curvatures') else {},
            'edge_curvatures': {k: float(v) for k, v in edge_curvatures.items()},
            'curvature_bottleneck': bottleneck_edge,
            'mean_curvature': float(np.mean(list(edge_curvatures.values()))) if edge_curvatures else 0.0,
        }
    except Exception as e:
        return {'error': str(e)}


# =============================================================================
# Persistent Homology on Cycling Data
# =============================================================================

def analyze_cycling_topology(
    capacity_values: List[float],
    voltage_values: List[float],
) -> Optional[Dict]:
    """
    Apply persistent homology to battery cycling data.

    Constructs a point cloud in (capacity, voltage) space and detects:
    - H0 features: clusters = distinct operating regimes
    - H1 features: loops = hysteresis cycles, degradation loops
    - Persistence: long-lived features = stable behaviors

    This is analogous to how topology/persistence.py detects feedback
    loops in climate data point clouds.

    Args:
        capacity_values: Discharge capacity per cycle
        voltage_values: Average voltage per cycle

    Returns:
        Dict with topological features, or None if topology module unavailable
    """
    if not TOPOLOGY_AVAILABLE:
        return None

    if len(capacity_values) < 5 or len(voltage_values) < 5:
        return None

    # Build 2D point cloud: (capacity, voltage)
    n = min(len(capacity_values), len(voltage_values))
    point_cloud = np.column_stack([
        np.array(capacity_values[:n]),
        np.array(voltage_values[:n]),
    ])

    # Normalize to [0, 1] range for numerical stability
    for col in range(point_cloud.shape[1]):
        col_range = point_cloud[:, col].max() - point_cloud[:, col].min()
        if col_range > 0:
            point_cloud[:, col] = (
                (point_cloud[:, col] - point_cloud[:, col].min()) / col_range
            )

    try:
        analyzer = PersistentHomologyAnalyzer(
            point_cloud,
            variable_names=['capacity', 'voltage'],
        )
        result = analyzer.compute()

        return {
            'num_components_h0': len(result.features_h0),
            'num_loops_h1': len(result.features_h1),
            'max_persistence_h0': max((f.persistence for f in result.features_h0), default=0),
            'max_persistence_h1': max((f.persistence for f in result.features_h1), default=0),
            'analysis': result.analysis,
        }
    except Exception as e:
        return {'error': str(e)}


# =============================================================================
# Sheaf Coherence: Thermodynamic Consistency
# =============================================================================

def check_thermodynamic_coherence(
    cell_analysis: CellAnalysis,
) -> Dict:
    """
    Check thermodynamic consistency across all interfaces in a cell.

    Analogous to sheaf coherence checking in the Oracle: predictions from
    different strategies must agree on overlapping regions.

    For batteries: interface scores at shared nodes (materials that appear
    in multiple interfaces) must be self-consistent.

    Example: if cathode-electrolyte interface says "electrolyte is stable"
    but anode-electrolyte interface says "electrolyte decomposes", that's
    a coherence violation (the electrolyte can't be both stable and unstable).

    Args:
        cell_analysis: Result from BatteryFlowAnalyzer

    Returns:
        Dict with coherence analysis
    """
    interfaces = cell_analysis.interfaces
    if len(interfaces) < 2:
        return {'coherent': True, 'violations': []}

    violations = []

    # Group interfaces by shared material
    material_interfaces: Dict[str, List] = {}
    for ir in interfaces:
        for mat_name in (ir.material_a, ir.material_b):
            if mat_name not in material_interfaces:
                material_interfaces[mat_name] = []
            material_interfaces[mat_name].append(ir)

    # Check: electrochemical stability should be consistent for same electrolyte
    for mat_name, mat_interfaces in material_interfaces.items():
        if len(mat_interfaces) < 2:
            continue

        echem_scores = [ir.score.electrochemical_stability for ir in mat_interfaces]
        # Large variance in echem stability for the same electrolyte = incoherent
        if len(echem_scores) >= 2:
            score_range = max(echem_scores) - min(echem_scores)
            if score_range > 0.5:
                violations.append({
                    'material': mat_name,
                    'type': 'electrochemical_inconsistency',
                    'scores': [round(s, 3) for s in echem_scores],
                    'range': round(score_range, 3),
                    'note': (f'{mat_name} shows inconsistent electrochemical stability '
                             f'across its interfaces (range={score_range:.2f})'),
                })

    # Check: mechanical scores at shared nodes
    for mat_name, mat_interfaces in material_interfaces.items():
        if len(mat_interfaces) < 2:
            continue

        mech_scores = [ir.score.mechanical_compatibility for ir in mat_interfaces]
        if len(mech_scores) >= 2:
            score_range = max(mech_scores) - min(mech_scores)
            if score_range > 0.4:
                violations.append({
                    'material': mat_name,
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
        'num_shared_nodes': sum(1 for v in material_interfaces.values() if len(v) >= 2),
    }


# =============================================================================
# Convenience: Full Categorical Analysis Pipeline
# =============================================================================

def run_battery_categorical_analysis(
    config: CellConfiguration,
) -> Dict:
    """
    Run full KOMPOSOS categorical analysis on a battery cell configuration.

    Combines:
    1. Interface flow analysis (battery_flow)
    2. Category construction
    3. Ricci curvature (if available)
    4. Sheaf coherence check

    This is the battery-domain entry point, analogous to running
    mutation_impact.py for the drug repurposing pipeline.

    Args:
        config: Cell configuration

    Returns:
        Dict with all analysis results
    """
    analyzer = BatteryFlowAnalyzer()
    cell_analysis = analyzer.analyze_cell(config)

    result = {
        'cell': cell_analysis.to_dict(),
        'coherence': check_thermodynamic_coherence(cell_analysis),
    }

    # ZFC constraint verification (optional)
    try:
        from oracle.material_zfc_constraints import MaterialZFCBridge, ZFC_LOGIC_AVAILABLE
        if ZFC_LOGIC_AVAILABLE:
            from battery_bridge.interaction_scoring import score_all as battery_score_all
            zfc_bridge = MaterialZFCBridge()
            zfc_constraints = []
            for ir in cell_analysis.interfaces:
                mat_a = get_material(ir.material_a)
                mat_b = get_material(ir.material_b)
                if mat_a is not None and mat_b is not None:
                    scores = battery_score_all(mat_a, mat_b)
                    pair_constraints = zfc_bridge.score_constraints(
                        ir.material_a, ir.material_b, scores
                    )
                    zfc_constraints.extend(pair_constraints)
            result['zfc_constraints'] = {
                'num_constraints': len(zfc_constraints),
                'has_vetoes': any(
                    c.source_prediction.get("relation", "").endswith("_veto")
                    for c in zfc_constraints
                ),
            }
    except ImportError:
        pass

    # Ricci curvature (optional)
    curvature = compute_battery_curvature(cell_analysis)
    if curvature:
        result['curvature'] = curvature

    # Category construction (optional)
    materials = [config.cathode, config.anode, config.electrolyte_salt]
    materials.extend(config.electrolyte_solvents)
    if config.solid_electrolyte:
        materials.append(config.solid_electrolyte)

    cat = build_battery_category(materials)
    if cat:
        result['category'] = {
            'num_objects': len(cat.objects),
            'num_morphisms': len(cat.morphisms),
        }

    return result


if __name__ == "__main__":
    from battery_bridge.battery_flow import STANDARD_LFP_CELL, STANDARD_NMC811_CELL

    print("=" * 70)
    print("KOMPOSOS Integration - Battery Bridge")
    print("=" * 70)
    print()

    for config in [STANDARD_LFP_CELL, STANDARD_NMC811_CELL]:
        print(f"--- {config.name} ---")
        result = run_battery_categorical_analysis(config)

        cell = result['cell']
        print(f"  Viability: {cell['overall_viability']:.3f}")
        print(f"  Viable: {cell['viable']}")
        if cell.get('bottleneck'):
            print(f"  Bottleneck: {cell['bottleneck']}")

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
