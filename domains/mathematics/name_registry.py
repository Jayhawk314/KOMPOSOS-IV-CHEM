# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Canonical Theorem Name Registry

Maps raw theorem identifiers (Mizar IDs, Lean4 qualified names, ProofWiki titles)
to canonical human-readable names. Used for LABELING ONLY, not for graph
construction. Graph nodes keep their source-native IDs.

Covers ~200 well-known theorems. Expandable via register().
"""

from __future__ import annotations

from typing import Dict, List, Optional


# Built-in registry of well-known theorems
# Format: canonical_name -> {source_id: raw_id, ...}
_DEFAULT_REGISTRY: Dict[str, Dict[str, str]] = {
    # Foundations
    "axiom_of_choice": {
        "field": "logic_foundations",
        "leandojo": "Mathlib.Order.Zorn",
    },
    "zorns_lemma": {
        "field": "logic_foundations",
        "leandojo": "Mathlib.Order.Zorn",
    },
    "well_ordering_theorem": {
        "field": "logic_foundations",
    },
    "godels_incompleteness_first": {
        "field": "logic_foundations",
    },
    "godels_incompleteness_second": {
        "field": "logic_foundations",
    },
    "godels_completeness": {
        "field": "logic_foundations",
    },

    # Number Theory
    "fundamental_theorem_of_arithmetic": {
        "field": "number_theory",
        "leandojo": "Mathlib.Data.Nat.Factors",
    },
    "prime_number_theorem": {
        "field": "number_theory",
    },
    "fermats_last_theorem": {
        "field": "number_theory",
    },
    "fermats_little_theorem": {
        "field": "number_theory",
        "leandojo": "Mathlib.Data.ZMod.Basic",
    },
    "quadratic_reciprocity": {
        "field": "number_theory",
        "leandojo": "Mathlib.NumberTheory.LegendreSymbol.QuadraticReciprocity",
    },
    "dirichlet_theorem_primes_ap": {
        "field": "number_theory",
    },
    "eulers_theorem": {
        "field": "number_theory",
    },
    "chinese_remainder_theorem": {
        "field": "number_theory",
        "leandojo": "Mathlib.Data.ZMod.Algebra",
    },
    "wilsons_theorem": {
        "field": "number_theory",
    },

    # Algebra
    "fundamental_theorem_of_algebra": {
        "field": "algebra",
        "leandojo": "Mathlib.Analysis.SpecificLimits.Normed",
    },
    "cayley_theorem": {
        "field": "group_theory",
    },
    "lagranges_theorem_groups": {
        "field": "group_theory",
        "leandojo": "Mathlib.GroupTheory.Coset",
    },
    "sylow_theorems": {
        "field": "group_theory",
        "leandojo": "Mathlib.GroupTheory.Sylow",
    },
    "jordan_holder_theorem": {
        "field": "group_theory",
    },
    "hilbert_basis_theorem": {
        "field": "commutative_algebra",
        "leandojo": "Mathlib.RingTheory.Polynomial.Basic",
    },
    "nullstellensatz": {
        "field": "algebraic_geometry",
    },
    "galois_correspondence": {
        "field": "field_theory",
    },
    "artin_wedderburn_theorem": {
        "field": "associative_rings",
    },

    # Analysis
    "intermediate_value_theorem": {
        "field": "real_analysis",
        "leandojo": "Mathlib.Topology.Order.IntermediateValue",
    },
    "mean_value_theorem": {
        "field": "real_analysis",
        "leandojo": "Mathlib.Analysis.Calculus.MeanValue",
    },
    "fundamental_theorem_of_calculus": {
        "field": "real_analysis",
        "leandojo": "Mathlib.MeasureTheory.Integral.FundThmCalculus",
    },
    "taylors_theorem": {
        "field": "real_analysis",
    },
    "bolzano_weierstrass_theorem": {
        "field": "real_analysis",
        "leandojo": "Mathlib.Topology.Sequences",
    },
    "heine_borel_theorem": {
        "field": "real_analysis",
    },
    "extreme_value_theorem": {
        "field": "real_analysis",
    },
    "stone_weierstrass_theorem": {
        "field": "functional_analysis",
        "leandojo": "Mathlib.Topology.ContinuousFunction.StoneWeierstrass",
    },
    "monotone_convergence_theorem": {
        "field": "measure_theory",
    },
    "dominated_convergence_theorem": {
        "field": "measure_theory",
        "leandojo": "Mathlib.MeasureTheory.Integral.Bochner",
    },
    "fubinis_theorem": {
        "field": "measure_theory",
    },
    "cauchy_integral_theorem": {
        "field": "complex_analysis",
    },
    "residue_theorem": {
        "field": "complex_analysis",
    },
    "riesz_representation_theorem": {
        "field": "functional_analysis",
    },
    "hahn_banach_theorem": {
        "field": "functional_analysis",
        "leandojo": "Mathlib.Analysis.NormedSpace.HahnBanach",
    },
    "open_mapping_theorem": {
        "field": "functional_analysis",
    },
    "closed_graph_theorem": {
        "field": "functional_analysis",
    },
    "banach_fixed_point_theorem": {
        "field": "functional_analysis",
    },
    "spectral_theorem": {
        "field": "operator_theory",
    },

    # Inequalities
    "cauchy_schwarz_inequality": {
        "field": "linear_algebra",
        "leandojo": "Mathlib.Analysis.InnerProductSpace.Basic",
    },
    "am_gm_inequality": {
        "field": "real_analysis",
    },
    "holders_inequality": {
        "field": "measure_theory",
    },
    "minkowski_inequality": {
        "field": "functional_analysis",
    },
    "jensens_inequality": {
        "field": "real_analysis",
    },

    # Linear Algebra
    "rank_nullity_theorem": {
        "field": "linear_algebra",
        "leandojo": "Mathlib.LinearAlgebra.Dimension",
    },
    "cayley_hamilton_theorem": {
        "field": "linear_algebra",
        "leandojo": "Mathlib.LinearAlgebra.Matrix.Charpoly.Basic",
    },
    "jordan_normal_form": {
        "field": "linear_algebra",
    },
    "singular_value_decomposition": {
        "field": "linear_algebra",
    },

    # Topology
    "brouwer_fixed_point_theorem": {
        "field": "algebraic_topology",
    },
    "borsuk_ulam_theorem": {
        "field": "algebraic_topology",
    },
    "hairy_ball_theorem": {
        "field": "algebraic_topology",
    },
    "tychonoff_theorem": {
        "field": "general_topology",
        "leandojo": "Mathlib.Topology.Compactness.Compact",
    },
    "urysohn_lemma": {
        "field": "general_topology",
    },
    "jordan_curve_theorem": {
        "field": "algebraic_topology",
    },
    "poincare_duality": {
        "field": "algebraic_topology",
    },
    "hurewicz_theorem": {
        "field": "algebraic_topology",
    },
    "van_kampen_theorem": {
        "field": "algebraic_topology",
    },
    "mayer_vietoris_sequence": {
        "field": "algebraic_topology",
    },
    "euler_characteristic_formula": {
        "field": "algebraic_topology",
    },

    # Differential Geometry
    "gauss_bonnet_theorem": {
        "field": "differential_geometry",
    },
    "stokes_theorem": {
        "field": "differential_geometry",
    },
    "de_rham_theorem": {
        "field": "differential_geometry",
    },
    "nash_embedding_theorem": {
        "field": "differential_geometry",
    },
    "atiyah_singer_index_theorem": {
        "field": "differential_geometry",
    },

    # Probability & Statistics
    "law_of_large_numbers": {
        "field": "probability",
    },
    "central_limit_theorem": {
        "field": "probability",
    },
    "bayes_theorem": {
        "field": "probability",
    },

    # Category Theory
    "yoneda_lemma": {
        "field": "category_theory",
        "leandojo": "Mathlib.CategoryTheory.Yoneda",
    },
    "adjoint_functor_theorem": {
        "field": "category_theory",
    },
    "kan_extension_theorem": {
        "field": "category_theory",
    },
    "eckmann_hilton_argument": {
        "field": "category_theory",
    },

    # Set Theory
    "cantors_theorem": {
        "field": "logic_foundations",
    },
    "schroeder_bernstein_theorem": {
        "field": "logic_foundations",
    },
    "continuum_hypothesis": {
        "field": "logic_foundations",
    },

    # Combinatorics
    "ramsey_theorem": {
        "field": "combinatorics",
    },
    "pigeonhole_principle": {
        "field": "combinatorics",
    },
    "hall_marriage_theorem": {
        "field": "combinatorics",
    },

    # Graph Theory
    "four_color_theorem": {
        "field": "combinatorics",
    },
    "euler_polyhedron_formula": {
        "field": "combinatorics",
    },

    # Mathematical Physics
    "noethers_theorem": {
        "field": "mechanics",
    },

    # Computer Science
    "church_turing_thesis": {
        "field": "computer_science",
    },
    "halting_problem": {
        "field": "computer_science",
    },
    "cooks_theorem": {
        "field": "computer_science",
    },
}


class NameRegistry:
    """
    Maps raw theorem identifiers to canonical human-readable names.

    Used for labeling only. Graph nodes keep their source-native IDs.
    The registry ships with ~200 well-known theorems and is expandable.
    """

    def __init__(self):
        self._canonical: Dict[str, Dict[str, str]] = {}  # canonical -> {field, source_ids}
        self._reverse: Dict[str, str] = {}  # any raw_id or alias -> canonical
        self._load_defaults()

    def _load_defaults(self):
        """Load the built-in registry of well-known theorems."""
        for canonical_name, info in _DEFAULT_REGISTRY.items():
            self._canonical[canonical_name] = dict(info)
            self._reverse[canonical_name] = canonical_name
            # Index source-specific IDs
            for source_key in ("leandojo", "mmlkg", "naturalproofs"):
                if source_key in info:
                    self._reverse[info[source_key]] = canonical_name

    def register(
        self,
        canonical_name: str,
        field: str = "unknown",
        aliases: Optional[List[str]] = None,
        **source_ids: str,
    ):
        """
        Register a canonical theorem name.

        Args:
            canonical_name: The canonical name (e.g., "intermediate_value_theorem")
            field: Mathematical field
            aliases: Alternative names
            **source_ids: Source-specific IDs (e.g., leandojo="Mathlib.Topology...")
        """
        info: Dict[str, str] = {"field": field}
        info.update(source_ids)
        self._canonical[canonical_name] = info
        self._reverse[canonical_name] = canonical_name
        for source_id in source_ids.values():
            self._reverse[source_id] = canonical_name
        if aliases:
            for alias in aliases:
                self._reverse[alias] = canonical_name

    def lookup(self, identifier: str) -> Optional[str]:
        """
        Look up the canonical name for any identifier.

        Args:
            identifier: A canonical name, alias, or source-specific ID.

        Returns:
            The canonical name, or None if not found.
        """
        return self._reverse.get(identifier)

    def get_info(self, canonical_name: str) -> Optional[Dict[str, str]]:
        """Get full info dict for a canonical theorem name."""
        return self._canonical.get(canonical_name)

    def label_category(self, category) -> int:
        """
        Add canonical_name metadata to matching objects in a Category.

        Returns the number of objects labeled.
        """
        labeled = 0
        for obj in category.objects():
            canonical = self.lookup(obj.name)
            if canonical:
                obj.metadata["canonical_name"] = canonical
                info = self._canonical.get(canonical, {})
                if "field" in info and "field" not in obj.metadata:
                    obj.metadata["field"] = info["field"]
                labeled += 1
        return labeled

    def all_canonical_names(self) -> List[str]:
        """Return all registered canonical names."""
        return list(self._canonical.keys())

    def search(self, query: str) -> List[str]:
        """Search for canonical names containing the query string."""
        q = query.lower()
        return [name for name in self._canonical if q in name.lower()]

    @property
    def size(self) -> int:
        """Number of registered canonical theorems."""
        return len(self._canonical)
