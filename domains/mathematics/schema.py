# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Mathematics Domain Schema

Maps formal mathematical concepts to KOMPOSOS-IV's Object/Morphism types.
Provides factory functions for creating theorem objects, proof morphisms,
and other mathematical entities with consistent metadata structure.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.types import Object, Morphism

# Type constants for mathematical entities
THEOREM_TYPE = "Theorem"
DEFINITION_TYPE = "Definition"
AXIOM_TYPE = "Axiom"
LEMMA_TYPE = "Lemma"
CONJECTURE_TYPE = "Conjecture"
PROOF_TYPE = "Proof"

# MSC (Mathematics Subject Classification) top-level fields
MSC_FIELDS = {
    "00": "general",
    "03": "logic_foundations",
    "05": "combinatorics",
    "06": "order_lattices",
    "08": "general_algebra",
    "11": "number_theory",
    "12": "field_theory",
    "13": "commutative_algebra",
    "14": "algebraic_geometry",
    "15": "linear_algebra",
    "16": "associative_rings",
    "17": "nonassociative_rings",
    "18": "category_theory",
    "19": "k_theory",
    "20": "group_theory",
    "22": "topological_groups",
    "26": "real_analysis",
    "28": "measure_theory",
    "30": "complex_analysis",
    "32": "several_complex_variables",
    "34": "ode",
    "35": "pde",
    "37": "dynamical_systems",
    "39": "difference_equations",
    "40": "sequences_series",
    "42": "harmonic_analysis",
    "43": "abstract_harmonic_analysis",
    "44": "integral_transforms",
    "45": "integral_equations",
    "46": "functional_analysis",
    "47": "operator_theory",
    "49": "calculus_of_variations",
    "51": "geometry",
    "52": "convex_geometry",
    "53": "differential_geometry",
    "54": "general_topology",
    "55": "algebraic_topology",
    "57": "manifolds",
    "58": "global_analysis",
    "60": "probability",
    "62": "statistics",
    "65": "numerical_analysis",
    "68": "computer_science",
    "70": "mechanics",
    "74": "continuum_mechanics",
    "76": "fluid_mechanics",
    "78": "optics_electromagnetics",
    "80": "thermodynamics",
    "81": "quantum_theory",
    "82": "statistical_mechanics",
    "83": "relativity",
    "85": "astronomy",
    "90": "operations_research",
    "91": "game_theory_economics",
    "92": "mathematical_biology",
    "93": "systems_control",
    "94": "information_communication",
    "97": "math_education",
}


def msc_field_name(code: str) -> str:
    """Convert MSC code (e.g. '55') to field name (e.g. 'algebraic_topology')."""
    prefix = code[:2] if len(code) >= 2 else code
    return MSC_FIELDS.get(prefix, "unknown")


def theorem_object(
    name: str,
    statement: str = "",
    field: str = "unknown",
    year: Optional[int] = None,
    difficulty: Optional[float] = None,
    source: str = "math_kernel",
    **kwargs: Any,
) -> Object:
    """
    Create a theorem as a categorical Object.

    Args:
        name: Unique identifier (e.g., "lean:Mathlib.Topology.Basic.isOpen_inter")
        statement: The theorem statement text
        field: Mathematical field (e.g., "topology", "number_theory")
        year: Year discovered/proved (for temporal analysis)
        difficulty: Difficulty score [0, 1] if available
        source: Provenance tag (e.g., "leandojo", "mmlkg")
        **kwargs: Additional metadata
    """
    metadata: Dict[str, Any] = {"statement": statement, "field": field}
    if year is not None:
        metadata["year"] = year
    if difficulty is not None:
        metadata["difficulty"] = difficulty
    metadata.update(kwargs)
    return Object(name=name, type_name=THEOREM_TYPE, metadata=metadata, provenance=source)


def definition_object(
    name: str,
    statement: str = "",
    field: str = "unknown",
    source: str = "math_kernel",
    **kwargs: Any,
) -> Object:
    """Create a mathematical definition as a categorical Object."""
    metadata: Dict[str, Any] = {"statement": statement, "field": field}
    metadata.update(kwargs)
    return Object(name=name, type_name=DEFINITION_TYPE, metadata=metadata, provenance=source)


def axiom_object(
    name: str,
    statement: str = "",
    field: str = "unknown",
    system: str = "ZFC",
    source: str = "math_kernel",
    **kwargs: Any,
) -> Object:
    """Create an axiom as a categorical Object."""
    metadata: Dict[str, Any] = {"statement": statement, "field": field, "system": system}
    metadata.update(kwargs)
    return Object(name=name, type_name=AXIOM_TYPE, metadata=metadata, provenance=source)


def lemma_object(
    name: str,
    statement: str = "",
    field: str = "unknown",
    source: str = "math_kernel",
    **kwargs: Any,
) -> Object:
    """Create a lemma as a categorical Object."""
    metadata: Dict[str, Any] = {"statement": statement, "field": field}
    metadata.update(kwargs)
    return Object(name=name, type_name=LEMMA_TYPE, metadata=metadata, provenance=source)


def conjecture_object(
    name: str,
    statement: str = "",
    field: str = "unknown",
    status: str = "open",
    source: str = "math_kernel",
    **kwargs: Any,
) -> Object:
    """Create a conjecture as a categorical Object."""
    metadata: Dict[str, Any] = {"statement": statement, "field": field, "status": status}
    metadata.update(kwargs)
    return Object(name=name, type_name=CONJECTURE_TYPE, metadata=metadata, provenance=source)


def proof_morphism(
    name: str,
    source_thm: str,
    target_thm: str,
    confidence: float = 1.0,
    proof_type: str = "dependency",
    source: str = "math_kernel",
    **kwargs: Any,
) -> Morphism:
    """
    Create a proof dependency as a categorical Morphism.

    A morphism from source_thm to target_thm means:
    "source_thm depends on / uses / implies target_thm"

    Args:
        name: Morphism name (e.g., "dep_ivt_to_lub")
        source_thm: Source theorem name
        target_thm: Target theorem name
        confidence: Confidence in the dependency [0, 1]
        proof_type: One of "dependency", "generalization", "specialization",
                    "equivalence", "application"
        source: Provenance tag
        **kwargs: Additional metadata
    """
    metadata: Dict[str, Any] = {"proof_type": proof_type}
    metadata.update(kwargs)
    return Morphism(
        name=name,
        source=source_thm,
        target=target_thm,
        confidence=confidence,
        metadata=metadata,
    )
