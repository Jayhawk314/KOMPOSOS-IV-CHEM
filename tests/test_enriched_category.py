# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Tests for enriched category theory module."""

import pytest
import math

from categorical.enriched_category import (
    EnrichedCategory, MonoidalStructure,
    ENERGY_QUANTALE, YIELD_QUANTALE, COMPATIBILITY_QUANTALE,
    COST_QUANTALE, RISK_QUANTALE, SUCCESS_QUANTALE, ACTIVITY_QUANTALE,
)


# ---------------------------------------------------------------------------
# Quantale construction
# ---------------------------------------------------------------------------

class TestMonoidalStructures:
    def test_energy_quantale_additive(self):
        assert ENERGY_QUANTALE.tensor(1.0, 2.0) == 3.0
        assert ENERGY_QUANTALE.unit == 0.0
        assert ENERGY_QUANTALE.compare(1.0, 2.0) is True  # lower is better

    def test_yield_quantale_multiplicative(self):
        assert YIELD_QUANTALE.tensor(0.8, 0.9) == pytest.approx(0.72)
        assert YIELD_QUANTALE.unit == 1.0
        assert YIELD_QUANTALE.compare(0.9, 0.8) is True  # higher is better

    def test_compatibility_quantale_min(self):
        assert COMPATIBILITY_QUANTALE.tensor(0.8, 0.6) == 0.6
        assert COMPATIBILITY_QUANTALE.unit == 1.0
        assert COMPATIBILITY_QUANTALE.compare(0.9, 0.5) is True  # higher is better

    def test_cost_quantale(self):
        assert COST_QUANTALE.tensor(10.0, 20.0) == 30.0
        assert COST_QUANTALE.unit == 0.0

    def test_risk_quantale_probabilistic_or(self):
        # P(A or B) = 1 - (1-P(A))(1-P(B))
        result = RISK_QUANTALE.tensor(0.3, 0.4)
        expected = 1 - (1 - 0.3) * (1 - 0.4)
        assert result == pytest.approx(expected)

    def test_success_quantale_joint(self):
        assert SUCCESS_QUANTALE.tensor(0.5, 0.6) == pytest.approx(0.3)

    def test_activity_quantale_bottleneck(self):
        assert ACTIVITY_QUANTALE.tensor(0.9, 0.3) == 0.3

    def test_custom_quantale(self):
        custom = MonoidalStructure(
            tensor=lambda a, b: max(a, b),
            unit=0.0,
            compare=lambda a, b: a <= b,
            name="Max"
        )
        assert custom.tensor(3, 7) == 7
        assert custom.unit == 0.0


# ---------------------------------------------------------------------------
# Enriched category basics
# ---------------------------------------------------------------------------

class TestEnrichedCategoryBasics:
    def test_create_category(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        assert len(cat.objects) == 0
        assert repr(cat).startswith("EnrichedCategory")

    def test_add_object(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.add_object("NMC811", {"type": "cathode"})
        assert "NMC811" in cat.objects
        # Identity hom-object should be set to unit
        assert cat.get_hom("NMC811", "NMC811") == 1.0

    def test_set_hom(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        assert cat.get_hom("A", "B") == 0.8
        assert cat.get_hom("B", "A") is None

    def test_set_hom_auto_adds_objects(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("X", "Y", 0.5)
        assert "X" in cat.objects
        assert "Y" in cat.objects

    def test_get_hom_nonexistent(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        assert cat.get_hom("A", "B") is None


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

class TestComposition:
    def test_compose_yield(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        cat.set_hom("B", "C", 0.9)
        result = cat.compose("A", "B", "C")
        assert result == pytest.approx(0.72)

    def test_compose_energy(self):
        cat = EnrichedCategory(ENERGY_QUANTALE)
        cat.set_hom("A", "B", 1.5)  # 1.5 eV
        cat.set_hom("B", "C", 2.0)  # 2.0 eV
        result = cat.compose("A", "B", "C")
        assert result == pytest.approx(3.5)

    def test_compose_compatibility(self):
        cat = EnrichedCategory(COMPATIBILITY_QUANTALE)
        cat.set_hom("A", "B", 0.85)
        cat.set_hom("B", "C", 0.70)
        result = cat.compose("A", "B", "C")
        assert result == 0.70  # min

    def test_compose_missing_hom(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        result = cat.compose("A", "B", "C")
        assert result is None


# ---------------------------------------------------------------------------
# Path weight
# ---------------------------------------------------------------------------

class TestPathWeight:
    def test_path_weight_yield(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.9)
        cat.set_hom("B", "C", 0.8)
        cat.set_hom("C", "D", 0.7)
        weight = cat.path_weight(["A", "B", "C", "D"])
        assert weight == pytest.approx(0.9 * 0.8 * 0.7)

    def test_path_weight_energy(self):
        cat = EnrichedCategory(ENERGY_QUANTALE)
        cat.set_hom("A", "B", 1.0)
        cat.set_hom("B", "C", 2.0)
        cat.set_hom("C", "D", 0.5)
        weight = cat.path_weight(["A", "B", "C", "D"])
        assert weight == pytest.approx(3.5)

    def test_path_weight_single_node(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        weight = cat.path_weight(["A"])
        assert weight == 1.0  # unit

    def test_path_weight_missing_edge(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.9)
        weight = cat.path_weight(["A", "B", "C"])
        assert weight is None


# ---------------------------------------------------------------------------
# Composition axiom verification
# ---------------------------------------------------------------------------

class TestCompositionAxiom:
    def test_axiom_satisfied(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        cat.set_hom("B", "C", 0.7)
        cat.set_hom("A", "C", 0.5)  # 0.56 >= 0.5 -> satisfied
        assert cat.verify_composition_axiom("A", "B", "C") is True

    def test_axiom_trivially_satisfied(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        # No Hom(B,C) -> trivially satisfied
        assert cat.verify_composition_axiom("A", "B", "C") is True


# ---------------------------------------------------------------------------
# Commutativity check
# ---------------------------------------------------------------------------

class TestCommutativity:
    def test_commuting_paths(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        cat.set_hom("B", "D", 0.9)
        cat.set_hom("A", "C", 0.72)
        cat.set_hom("C", "D", 1.0)
        result = cat.check_commutativity(["A", "B", "D"], ["A", "C", "D"])
        assert result["commutes"] is True
        assert result["tension"] == pytest.approx(0.0)

    def test_non_commuting_paths(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        cat.set_hom("B", "D", 0.9)
        cat.set_hom("A", "C", 0.5)
        cat.set_hom("C", "D", 0.5)
        result = cat.check_commutativity(["A", "B", "D"], ["A", "C", "D"])
        assert result["commutes"] is False
        assert result["tension"] > 0


# ---------------------------------------------------------------------------
# Optimal path finding
# ---------------------------------------------------------------------------

class TestOptimalPath:
    def test_optimal_path_yield_maximize(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.9)
        cat.set_hom("B", "D", 0.8)
        cat.set_hom("A", "C", 0.5)
        cat.set_hom("C", "D", 0.5)
        result = cat.optimal_path("A", "D", maximize=True)
        assert result is not None
        path, weight = result
        assert path == ["A", "B", "D"]
        assert weight == pytest.approx(0.72)

    def test_optimal_path_energy_minimize(self):
        cat = EnrichedCategory(ENERGY_QUANTALE)
        cat.set_hom("A", "B", 1.0)
        cat.set_hom("B", "D", 2.0)
        cat.set_hom("A", "C", 5.0)
        cat.set_hom("C", "D", 0.5)
        result = cat.optimal_path("A", "D", maximize=False)
        assert result is not None
        path, weight = result
        assert path == ["A", "B", "D"]
        assert weight == pytest.approx(3.0)

    def test_optimal_path_no_path(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.add_object("A")
        cat.add_object("B")
        result = cat.optimal_path("A", "B")
        assert result is None

    def test_optimal_path_self(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.add_object("A")
        result = cat.optimal_path("A", "A")
        assert result is not None
        assert result[0] == ["A"]
        assert result[1] == 1.0

    def test_top_k_paths(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.9)
        cat.set_hom("B", "D", 0.8)
        cat.set_hom("A", "C", 0.7)
        cat.set_hom("C", "D", 0.9)
        results = cat.top_k_paths("A", "D", k=3)
        assert len(results) >= 1
        # Best should be via B (0.72) or C (0.63)
        assert results[0][1] == pytest.approx(0.72)


# ---------------------------------------------------------------------------
# Composable successors
# ---------------------------------------------------------------------------

class TestComposableSuccessors:
    def test_get_successors(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("A", "B", 0.8)
        cat.set_hom("A", "C", 0.6)
        successors = cat.get_composable_successors("A")
        assert len(successors) == 2
        names = [s[0] for s in successors]
        assert "B" in names
        assert "C" in names

    def test_no_successors(self):
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.add_object("A")
        assert cat.get_composable_successors("A") == []


# ---------------------------------------------------------------------------
# Chemistry-specific quantale tests
# ---------------------------------------------------------------------------

class TestChemistryQuantales:
    def test_synthesis_route_yield(self):
        """Model a multi-step synthesis where yield compounds multiplicatively."""
        cat = EnrichedCategory(YIELD_QUANTALE)
        cat.set_hom("Li2CO3", "LiOH", 0.95)  # carbonate -> hydroxide
        cat.set_hom("LiOH", "LiFePO4", 0.85)  # hydroxide -> LFP
        total_yield = cat.path_weight(["Li2CO3", "LiOH", "LiFePO4"])
        assert total_yield == pytest.approx(0.95 * 0.85)

    def test_energy_barrier_path(self):
        """Model activation energy barriers along a reaction path."""
        cat = EnrichedCategory(ENERGY_QUANTALE)
        cat.set_hom("reactants", "intermediate", 1.2)  # 1.2 eV barrier
        cat.set_hom("intermediate", "products", 0.3)   # 0.3 eV barrier
        total_energy = cat.path_weight(["reactants", "intermediate", "products"])
        assert total_energy == pytest.approx(1.5)

    def test_compatibility_bottleneck(self):
        """Model multi-material stack where weakest interface limits all."""
        cat = EnrichedCategory(COMPATIBILITY_QUANTALE)
        cat.set_hom("cathode", "electrolyte", 0.85)
        cat.set_hom("electrolyte", "anode", 0.60)
        cat.set_hom("anode", "collector", 0.95)
        total = cat.path_weight(["cathode", "electrolyte", "anode", "collector"])
        assert total == 0.60  # bottleneck at electrolyte-anode
