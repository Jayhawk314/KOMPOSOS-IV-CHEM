# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Anchor Problems -- Millennium and Hilbert Problems

Registers important unsolved (and solved) problems as Objects in a Category
and provides proximity measurements. These serve as "north star" attractors
in the topology: bridges INTO the neighborhood of an anchor problem are
high-value findings.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.types import Object
from core.category import Category


# ---- Millennium Prize Problems (Clay Mathematics Institute, 2000) ----

MILLENNIUM_PROBLEMS: Dict[str, Dict[str, Any]] = {
    "P_vs_NP": {
        "field": "computer_science",
        "status": "open",
        "year_posed": 2000,
        "description": "Is P equal to NP? Can every problem whose solution can be "
                       "quickly verified also be quickly solved?",
        "connections": ["complexity_theory", "combinatorics", "logic_foundations"],
    },
    "Hodge_conjecture": {
        "field": "algebraic_geometry",
        "status": "open",
        "year_posed": 2000,
        "description": "Certain cohomology classes on projective algebraic varieties "
                       "are algebraic, i.e., they are rational linear combinations of "
                       "classes of algebraic subvarieties.",
        "connections": ["algebraic_topology", "complex_analysis", "differential_geometry"],
    },
    "Riemann_hypothesis": {
        "field": "number_theory",
        "status": "open",
        "year_posed": 1859,
        "description": "All non-trivial zeros of the Riemann zeta function have "
                       "real part 1/2.",
        "connections": ["complex_analysis", "probability", "harmonic_analysis"],
    },
    "Yang_Mills_mass_gap": {
        "field": "mathematical_physics",
        "status": "open",
        "year_posed": 2000,
        "description": "For any compact simple gauge group G, a non-trivial quantum "
                       "Yang-Mills theory exists on R^4 and has a mass gap > 0.",
        "connections": ["quantum_theory", "differential_geometry", "functional_analysis"],
    },
    "Navier_Stokes_regularity": {
        "field": "pde",
        "status": "open",
        "year_posed": 2000,
        "description": "Do smooth, globally defined solutions to the 3D incompressible "
                       "Navier-Stokes equations always exist?",
        "connections": ["fluid_mechanics", "functional_analysis", "dynamical_systems"],
    },
    "Birch_Swinnerton_Dyer": {
        "field": "number_theory",
        "status": "open",
        "year_posed": 2000,
        "description": "The rank of the group of rational points on an elliptic curve "
                       "E equals the order of vanishing of L(E, s) at s = 1.",
        "connections": ["algebraic_geometry", "complex_analysis", "group_theory"],
    },
    "Poincare_conjecture": {
        "field": "algebraic_topology",
        "status": "solved",
        "year_posed": 1904,
        "year_solved": 2003,
        "solver": "Grigori Perelman",
        "description": "Every simply connected, closed 3-manifold is homeomorphic "
                       "to the 3-sphere.",
        "connections": ["differential_geometry", "manifolds", "general_topology"],
    },
}


# ---- Hilbert's Problems (1900) ----

HILBERT_PROBLEMS: Dict[str, Dict[str, Any]] = {
    "Hilbert_01_continuum_hypothesis": {
        "field": "logic_foundations",
        "status": "independent",
        "year_posed": 1900,
        "description": "Is there a set whose cardinality is strictly between "
                       "that of the integers and the real numbers?",
        "connections": ["logic_foundations"],
    },
    "Hilbert_02_consistency_arithmetic": {
        "field": "logic_foundations",
        "status": "negative",
        "year_posed": 1900,
        "description": "Prove the consistency of the axioms of arithmetic.",
        "connections": ["logic_foundations"],
    },
    "Hilbert_03_scissors_congruence": {
        "field": "geometry",
        "status": "solved",
        "year_posed": 1900,
        "description": "Can two polyhedra of equal volume always be cut into "
                       "finitely many pieces and reassembled?",
        "connections": ["geometry", "group_theory"],
    },
    "Hilbert_05_lie_groups": {
        "field": "topological_groups",
        "status": "solved",
        "year_posed": 1900,
        "description": "Are continuous groups automatically differential groups?",
        "connections": ["topological_groups", "differential_geometry"],
    },
    "Hilbert_06_axiomatize_physics": {
        "field": "mathematical_physics",
        "status": "open",
        "year_posed": 1900,
        "description": "Mathematical treatment of the axioms of physics.",
        "connections": ["quantum_theory", "relativity", "mechanics"],
    },
    "Hilbert_07_transcendental_numbers": {
        "field": "number_theory",
        "status": "solved",
        "year_posed": 1900,
        "description": "Is a^b transcendental for algebraic a != 0,1 and "
                       "irrational algebraic b?",
        "connections": ["number_theory", "real_analysis"],
    },
    "Hilbert_08_riemann_hypothesis": {
        "field": "number_theory",
        "status": "open",
        "year_posed": 1900,
        "description": "The Riemann hypothesis and related prime distribution problems.",
        "connections": ["number_theory", "complex_analysis"],
    },
    "Hilbert_10_diophantine_equations": {
        "field": "number_theory",
        "status": "negative",
        "year_posed": 1900,
        "description": "Is there a general algorithm to determine whether a "
                       "Diophantine equation has integer solutions?",
        "connections": ["number_theory", "computer_science", "logic_foundations"],
    },
    "Hilbert_11_quadratic_forms": {
        "field": "number_theory",
        "status": "partially_solved",
        "year_posed": 1900,
        "description": "Classify quadratic forms over algebraic number fields.",
        "connections": ["number_theory", "field_theory"],
    },
    "Hilbert_12_abelian_extensions": {
        "field": "number_theory",
        "status": "partially_solved",
        "year_posed": 1900,
        "description": "Extend Kronecker-Weber theorem to algebraic number fields.",
        "connections": ["number_theory", "field_theory", "algebraic_geometry"],
    },
    "Hilbert_13_solving_seventh_degree": {
        "field": "algebra",
        "status": "solved",
        "year_posed": 1900,
        "description": "Can the general equation of seventh degree be solved "
                       "using functions of two arguments?",
        "connections": ["general_algebra", "real_analysis"],
    },
    "Hilbert_14_invariant_theory": {
        "field": "commutative_algebra",
        "status": "negative",
        "year_posed": 1900,
        "description": "Is the ring of invariants of an algebraic group "
                       "always finitely generated?",
        "connections": ["commutative_algebra", "group_theory"],
    },
    "Hilbert_15_schubert_calculus": {
        "field": "algebraic_geometry",
        "status": "partially_solved",
        "year_posed": 1900,
        "description": "Rigorous foundation for Schubert's enumerative calculus.",
        "connections": ["algebraic_geometry", "combinatorics"],
    },
    "Hilbert_16_topology_curves": {
        "field": "differential_geometry",
        "status": "open",
        "year_posed": 1900,
        "description": "Topology of algebraic curves and surfaces.",
        "connections": ["algebraic_geometry", "dynamical_systems"],
    },
    "Hilbert_17_sum_of_squares": {
        "field": "real_analysis",
        "status": "solved",
        "year_posed": 1900,
        "description": "Can every non-negative rational function be written "
                       "as a sum of squares of rational functions?",
        "connections": ["real_analysis", "commutative_algebra"],
    },
    "Hilbert_18_space_groups": {
        "field": "geometry",
        "status": "solved",
        "year_posed": 1900,
        "description": "Is there a finite number of crystallographic groups in "
                       "any dimension? Are there non-tile-transitive tilings?",
        "connections": ["geometry", "group_theory", "combinatorics"],
    },
    "Hilbert_19_regularity": {
        "field": "pde",
        "status": "solved",
        "year_posed": 1900,
        "description": "Are solutions of regular variational problems always analytic?",
        "connections": ["pde", "calculus_of_variations"],
    },
    "Hilbert_20_boundary_value": {
        "field": "pde",
        "status": "solved",
        "year_posed": 1900,
        "description": "Do all boundary value problems with nice boundary "
                       "conditions have solutions?",
        "connections": ["pde", "functional_analysis"],
    },
    "Hilbert_21_fuchsian": {
        "field": "ode",
        "status": "solved",
        "year_posed": 1900,
        "description": "Existence of linear ODEs with prescribed monodromy group.",
        "connections": ["ode", "complex_analysis", "group_theory"],
    },
    "Hilbert_22_uniformization": {
        "field": "complex_analysis",
        "status": "solved",
        "year_posed": 1900,
        "description": "Uniformization of analytic relations by automorphic functions.",
        "connections": ["complex_analysis", "algebraic_geometry"],
    },
    "Hilbert_23_calculus_of_variations": {
        "field": "calculus_of_variations",
        "status": "open",
        "year_posed": 1900,
        "description": "Further development of the calculus of variations.",
        "connections": ["calculus_of_variations", "pde", "differential_geometry"],
    },
}


class AnchorProblems:
    """
    Registers anchor problems (Millennium, Hilbert) as Objects in a Category
    and provides proximity measurements.

    Anchor problems serve as attractors: bridges that lead toward an anchor
    problem neighborhood are high-value findings.
    """

    def __init__(self, category: Category):
        self.category = category
        self._anchors: Dict[str, Dict[str, Any]] = {}

    def register_anchors(self) -> int:
        """
        Add all anchor problems as Objects in the category.

        Returns the number of anchors registered.
        """
        count = 0
        for name, info in MILLENNIUM_PROBLEMS.items():
            obj = Object(
                name=name,
                type_name="AnchorProblem",
                metadata={
                    "collection": "millennium",
                    **{k: v for k, v in info.items() if k != "connections"},
                },
                provenance="anchor_problems",
            )
            self.category.add_object(obj)
            self._anchors[name] = info
            count += 1

        for name, info in HILBERT_PROBLEMS.items():
            obj = Object(
                name=name,
                type_name="AnchorProblem",
                metadata={
                    "collection": "hilbert",
                    **{k: v for k, v in info.items() if k != "connections"},
                },
                provenance="anchor_problems",
            )
            self.category.add_object(obj)
            self._anchors[name] = info
            count += 1

        return count

    def connect_to_field(
        self,
        theorem_name: str,
        anchor_name: str,
        confidence: float = 0.5,
        relation: str = "related_to",
    ):
        """
        Create a morphism from a theorem to an anchor problem.

        This establishes proximity: the theorem is relevant to the problem.
        """
        if anchor_name not in self._anchors:
            raise ValueError(f"Unknown anchor problem: {anchor_name}")
        self.category.connect(
            theorem_name,
            anchor_name,
            name=relation,
            confidence=confidence,
            metadata={"anchor_connection": True},
        )

    def auto_connect_by_field(self, confidence: float = 0.3) -> int:
        """
        Automatically connect theorems to anchor problems in the same field.

        For each theorem whose metadata['field'] matches an anchor problem's
        field or connections list, create a low-confidence morphism.

        Returns the number of connections made.
        """
        count = 0
        for obj in self.category.objects():
            if obj.type_name == "AnchorProblem":
                continue
            obj_field = obj.metadata.get("field", "")
            for anchor_name, info in self._anchors.items():
                anchor_field = info.get("field", "")
                anchor_connections = info.get("connections", [])
                if obj_field == anchor_field or obj_field in anchor_connections:
                    try:
                        self.category.connect(
                            obj.name,
                            anchor_name,
                            name=f"field_related",
                            confidence=confidence,
                            metadata={"auto_connected": True, "shared_field": obj_field},
                        )
                        count += 1
                    except Exception:
                        pass  # Skip if connection already exists or other issue
        return count

    def proximity(self, obj_name: str) -> Dict[str, float]:
        """
        Compute distance from an object to each anchor problem.

        Uses Category.optimal_path() with the multiplicative quantale,
        so higher weight = stronger connection.

        Returns dict of {anchor_name: weight}. Weight 0.0 means unreachable.
        """
        results: Dict[str, float] = {}
        for anchor_name in self._anchors:
            try:
                path_result = self.category.optimal_path(
                    obj_name, anchor_name, maximize=True
                )
                if path_result and path_result[1] > 0:
                    results[anchor_name] = path_result[1]
                else:
                    results[anchor_name] = 0.0
            except Exception:
                results[anchor_name] = 0.0
        return results

    def nearest_anchor(self, obj_name: str) -> Optional[Tuple[str, float]]:
        """
        Find the closest anchor problem to the given object.

        Returns (anchor_name, weight) or None if no anchor is reachable.
        """
        prox = self.proximity(obj_name)
        reachable = {k: v for k, v in prox.items() if v > 0}
        if not reachable:
            return None
        best = max(reachable.items(), key=lambda x: x[1])
        return best

    def open_problems(self) -> List[str]:
        """Return names of all open (unsolved) anchor problems."""
        return [
            name for name, info in self._anchors.items()
            if info.get("status") == "open"
        ]

    def problems_in_field(self, field: str) -> List[str]:
        """Return anchor problems in a given mathematical field."""
        return [
            name for name, info in self._anchors.items()
            if info.get("field") == field or field in info.get("connections", [])
        ]
