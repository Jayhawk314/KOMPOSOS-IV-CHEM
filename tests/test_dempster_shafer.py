# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for Dempster-Shafer evidence theory module."""

import pytest

from categorical.dempster_shafer import (
    MassFunction, combine, weighted_combine, discount,
)


# ---------------------------------------------------------------------------
# MassFunction basics
# ---------------------------------------------------------------------------

class TestMassFunction:
    def test_create_simple(self):
        m = MassFunction(masses={
            frozenset({"compatible"}): 0.7,
            frozenset({"compatible", "incompatible"}): 0.3,
        })
        assert len(m.focal_elements) == 2

    def test_normalization(self):
        m = MassFunction(masses={
            frozenset({"A"}): 2.0,
            frozenset({"B"}): 3.0,
        })
        total = sum(m.masses.values())
        assert total == pytest.approx(1.0)

    def test_empty_set_removed(self):
        m = MassFunction(masses={
            frozenset(): 0.1,
            frozenset({"A"}): 0.9,
        })
        assert frozenset() not in m.masses

    def test_frame(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.3,
            frozenset({"B"}): 0.3,
            frozenset({"A", "B"}): 0.4,
        })
        assert m.frame == frozenset({"A", "B"})

    def test_focal_elements(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.5,
            frozenset({"B"}): 0.0,
            frozenset({"A", "B"}): 0.5,
        })
        focals = m.focal_elements
        assert frozenset({"A"}) in focals
        assert frozenset({"A", "B"}) in focals


# ---------------------------------------------------------------------------
# Belief and plausibility
# ---------------------------------------------------------------------------

class TestBeliefPlausibility:
    def test_belief_single_element(self):
        m = MassFunction(masses={
            frozenset({"compatible"}): 0.7,
            frozenset({"compatible", "incompatible"}): 0.3,
        })
        bel = m.belief(frozenset({"compatible"}))
        assert bel == pytest.approx(0.7)

    def test_plausibility_single_element(self):
        m = MassFunction(masses={
            frozenset({"compatible"}): 0.7,
            frozenset({"compatible", "incompatible"}): 0.3,
        })
        pl = m.plausibility(frozenset({"compatible"}))
        assert pl == pytest.approx(1.0)  # both focal elements intersect

    def test_uncertainty_interval(self):
        m = MassFunction(masses={
            frozenset({"compatible"}): 0.7,
            frozenset({"compatible", "incompatible"}): 0.3,
        })
        unc = m.uncertainty(frozenset({"compatible"}))
        assert unc == pytest.approx(0.3)

    def test_belief_full_frame(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.3,
            frozenset({"B"}): 0.3,
            frozenset({"A", "B"}): 0.4,
        })
        bel = m.belief(frozenset({"A", "B"}))
        assert bel == pytest.approx(1.0)

    def test_plausibility_disjoint(self):
        m = MassFunction(masses={
            frozenset({"A"}): 1.0,
        })
        pl = m.plausibility(frozenset({"B"}))
        assert pl == pytest.approx(0.0)

    def test_pignistic_probability(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.6,
            frozenset({"A", "B"}): 0.4,
        })
        # BetP(A) = 0.6/1 + 0.4/2 = 0.8
        assert m.pignistic_probability("A") == pytest.approx(0.8)
        # BetP(B) = 0.4/2 = 0.2
        assert m.pignistic_probability("B") == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Dempster's combination rule
# ---------------------------------------------------------------------------

class TestCombination:
    def test_combine_no_conflict(self):
        m1 = MassFunction(masses={
            frozenset({"compatible"}): 0.6,
            frozenset({"compatible", "incompatible"}): 0.4,
        })
        m2 = MassFunction(masses={
            frozenset({"compatible"}): 0.8,
            frozenset({"compatible", "incompatible"}): 0.2,
        })
        result, conflict = combine(m1, m2)
        assert conflict == pytest.approx(0.0, abs=1e-9)
        bel = result.belief(frozenset({"compatible"}))
        assert bel > 0.6  # Stronger after combination

    def test_combine_with_conflict(self):
        m1 = MassFunction(masses={
            frozenset({"A"}): 0.9,
            frozenset({"A", "B"}): 0.1,
        })
        m2 = MassFunction(masses={
            frozenset({"B"}): 0.9,
            frozenset({"A", "B"}): 0.1,
        })
        result, conflict = combine(m1, m2)
        assert conflict > 0.5
        assert conflict < 1.0

    def test_combine_total_conflict_raises(self):
        m1 = MassFunction(masses={frozenset({"A"}): 1.0})
        m2 = MassFunction(masses={frozenset({"B"}): 1.0})
        with pytest.raises(ValueError, match="Total conflict"):
            combine(m1, m2)

    def test_combine_strengthens_agreement(self):
        m1 = MassFunction(masses={
            frozenset({"viable"}): 0.7,
            frozenset({"viable", "not_viable"}): 0.3,
        })
        m2 = MassFunction(masses={
            frozenset({"viable"}): 0.6,
            frozenset({"viable", "not_viable"}): 0.4,
        })
        result, _ = combine(m1, m2)
        bel = result.belief(frozenset({"viable"}))
        assert bel > 0.7  # Stronger than either source


# ---------------------------------------------------------------------------
# Discounting and weighted combination
# ---------------------------------------------------------------------------

class TestDiscounting:
    def test_discount_full_reliability(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.8,
            frozenset({"A", "B"}): 0.2,
        })
        discounted = discount(m, reliability=1.0)
        assert discounted.masses[frozenset({"A"})] == pytest.approx(0.8)

    def test_discount_zero_reliability(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.8,
            frozenset({"A", "B"}): 0.2,
        })
        discounted = discount(m, reliability=0.0)
        # All mass should go to full frame
        frame = m.frame
        assert discounted.masses.get(frame, 0) == pytest.approx(1.0)

    def test_discount_half_reliability(self):
        m = MassFunction(masses={
            frozenset({"A"}): 0.8,
            frozenset({"A", "B"}): 0.2,
        })
        discounted = discount(m, reliability=0.5)
        assert discounted.masses[frozenset({"A"})] == pytest.approx(0.4)

    def test_weighted_combine(self):
        m1 = MassFunction(masses={
            frozenset({"compatible"}): 0.9,
            frozenset({"compatible", "incompatible"}): 0.1,
        })
        m2 = MassFunction(masses={
            frozenset({"compatible"}): 0.5,
            frozenset({"compatible", "incompatible"}): 0.5,
        })
        result = weighted_combine([(m1, 1.0), (m2, 0.5)])
        bel = result.belief(frozenset({"compatible"}))
        assert bel > 0.5

    def test_weighted_combine_empty(self):
        result = weighted_combine([])
        assert len(result.masses) == 0


# ---------------------------------------------------------------------------
# Chemistry-specific usage
# ---------------------------------------------------------------------------

class TestChemistryUsage:
    def test_material_compatibility_evidence_fusion(self):
        """Fuse evidence from 3 scorers about material compatibility."""
        # Scorer 1: ion transport says compatible (high confidence)
        m_ion = MassFunction(masses={
            frozenset({"compatible"}): 0.85,
            frozenset({"compatible", "incompatible"}): 0.15,
        })
        # Scorer 2: electrochemical stability says compatible (medium)
        m_echem = MassFunction(masses={
            frozenset({"compatible"}): 0.60,
            frozenset({"compatible", "incompatible"}): 0.40,
        })
        # Scorer 3: degradation says maybe incompatible
        m_degrad = MassFunction(masses={
            frozenset({"incompatible"}): 0.30,
            frozenset({"compatible", "incompatible"}): 0.70,
        })

        result = weighted_combine([
            (m_ion, 0.9),    # high reliability
            (m_echem, 0.8),  # medium reliability
            (m_degrad, 0.7), # lower reliability
        ])

        bel_compat = result.belief(frozenset({"compatible"}))
        bel_incompat = result.belief(frozenset({"incompatible"}))

        # Compatible should dominate
        assert bel_compat > bel_incompat
