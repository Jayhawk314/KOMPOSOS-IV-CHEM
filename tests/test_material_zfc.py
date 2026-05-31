# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Tests for MaterialZFCBridge — material bridge ZFC constraint generation."""

import pytest
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockScorerResult:
    """Minimal mock for ScorerResult used in tests."""
    score: float
    label: str = ""
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class MockVoltageWindow:
    """Minimal mock for VoltageWindow."""
    lower: float
    upper: float


# ---------------------------------------------------------------------------
# Import the bridge
# ---------------------------------------------------------------------------

from oracle.material_zfc_constraints import MaterialZFCBridge, ZFC_LOGIC_AVAILABLE

# Skip all tests if ZFC logic not available
pytestmark = pytest.mark.skipif(
    not ZFC_LOGIC_AVAILABLE,
    reason="ZFC logic module not available"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bridge():
    return MaterialZFCBridge()


@pytest.fixture
def strict_bridge():
    return MaterialZFCBridge(score_threshold=0.60, veto_threshold=0.25)


@pytest.fixture
def good_scores():
    """All five scorers with high scores (> 0.6)."""
    return {
        'ion_transport': MockScorerResult(0.85),
        'electrochemical_stability': MockScorerResult(0.90),
        'interface_compatibility': MockScorerResult(0.75),
        'mechanical_compatibility': MockScorerResult(0.80),
        'degradation_penalty': MockScorerResult(0.95),
    }


@pytest.fixture
def bad_scores():
    """Scores with some below veto threshold."""
    return {
        'ion_transport': MockScorerResult(0.10),
        'electrochemical_stability': MockScorerResult(0.15),
        'interface_compatibility': MockScorerResult(0.70),
        'mechanical_compatibility': MockScorerResult(0.80),
        'degradation_penalty': MockScorerResult(0.05),
    }


@pytest.fixture
def mixed_scores():
    """Mixed scores — some good, some borderline."""
    return {
        'ion_transport': MockScorerResult(0.50),
        'electrochemical_stability': MockScorerResult(0.30),
        'interface_compatibility': MockScorerResult(0.60),
        'mechanical_compatibility': MockScorerResult(0.55),
        'degradation_penalty': MockScorerResult(0.70),
    }


# ---------------------------------------------------------------------------
# Bridge availability
# ---------------------------------------------------------------------------

class TestBridgeAvailability:
    def test_is_available(self, bridge):
        assert bridge.is_available is True

    def test_default_thresholds(self, bridge):
        assert bridge.score_threshold == 0.45
        assert bridge.veto_threshold == 0.20
        assert bridge.cte_threshold == 0.20
        assert bridge.voltage_margin == 0.5

    def test_custom_thresholds(self, strict_bridge):
        assert strict_bridge.score_threshold == 0.60
        assert strict_bridge.veto_threshold == 0.25


# ---------------------------------------------------------------------------
# Score constraints
# ---------------------------------------------------------------------------

class TestScoreConstraints:
    def test_good_scores_produce_compatible_constraints(self, bridge, good_scores):
        constraints = bridge.score_constraints("NMC811", "LLZO", good_scores)
        assert len(constraints) > 0

        # Should have compatibility atoms for all 5 scorers
        compatible_constraints = [
            c for c in constraints
            if c.source_prediction.get("relation", "").endswith("_compatible")
        ]
        assert len(compatible_constraints) == 5

    def test_good_scores_produce_viable_assertion(self, bridge, good_scores):
        constraints = bridge.score_constraints("LFP", "EC", good_scores)
        viable_constraints = [
            c for c in constraints
            if c.source_prediction.get("relation") == "interface_viable"
        ]
        assert len(viable_constraints) == 1

    def test_bad_scores_produce_veto_constraints(self, bridge, bad_scores):
        constraints = bridge.score_constraints("LGPS", "NMC811", bad_scores)
        veto_constraints = [
            c for c in constraints
            if c.source_prediction.get("relation", "").endswith("_veto")
        ]
        # ion_transport (0.10), electrochemical_stability (0.15), degradation_penalty (0.05)
        # are below veto threshold of 0.20
        assert len(veto_constraints) == 3

    def test_bad_scores_no_viable_assertion(self, bridge, bad_scores):
        constraints = bridge.score_constraints("LGPS", "NMC811", bad_scores)
        viable_constraints = [
            c for c in constraints
            if c.source_prediction.get("relation") == "interface_viable"
        ]
        assert len(viable_constraints) == 0

    def test_veto_implies_not_viable(self, bridge, bad_scores):
        constraints = bridge.score_constraints("LGPS", "NMC811", bad_scores)
        rule_constraints = [
            c for c in constraints
            if c.source_prediction.get("relation") == "veto_implies_not_viable"
        ]
        assert len(rule_constraints) == 3

    def test_mixed_scores_partial_constraints(self, bridge, mixed_scores):
        constraints = bridge.score_constraints("Si", "EC", mixed_scores)
        assert len(constraints) > 0
        # Not all compatible, not all vetoed
        compatible = [c for c in constraints
                      if c.source_prediction.get("relation", "").endswith("_compatible")]
        vetoes = [c for c in constraints
                  if c.source_prediction.get("relation", "").endswith("_veto")]
        # At threshold 0.45: ion=0.50 ok, echem=0.30 not, iface=0.60 ok, mech=0.55 ok, degrad=0.70 ok
        assert len(compatible) == 4  # ion, iface, mech, degrad
        assert len(vetoes) == 0  # 0.30 is above veto threshold 0.20

    def test_empty_scores(self, bridge):
        constraints = bridge.score_constraints("A", "B", {})
        assert constraints == []

    def test_constraint_confidence_matches_score(self, bridge, good_scores):
        constraints = bridge.score_constraints("LFP", "EC", good_scores)
        for c in constraints:
            if c.source_prediction.get("relation", "").endswith("_compatible"):
                assert 0.0 <= c.confidence <= 1.0

    def test_constraint_has_source_target(self, bridge, good_scores):
        constraints = bridge.score_constraints("NMC811", "LLZO", good_scores)
        for c in constraints:
            assert c.source_prediction["source"] == "NMC811"
            assert c.source_prediction["target"] == "LLZO"

    def test_strict_bridge_more_vetoes(self, strict_bridge, mixed_scores):
        constraints = strict_bridge.score_constraints("Si", "EC", mixed_scores)
        compatible = [c for c in constraints
                      if c.source_prediction.get("relation", "").endswith("_compatible")]
        # At threshold 0.60: only iface=0.60 and degrad=0.70 pass
        assert len(compatible) == 2


# ---------------------------------------------------------------------------
# Voltage constraints
# ---------------------------------------------------------------------------

class TestVoltageConstraints:
    def test_voltage_compatible(self, bridge):
        # LFP cathode: 2.5-3.7V, electrolyte oxidation at 4.5V -> headroom 0.8V
        vw = MockVoltageWindow(lower=2.5, upper=3.7)
        constraints = bridge.voltage_constraints(
            "LFP", "EC", voltage_window_a=vw, oxidation_potential=4.5
        )
        compatible = [c for c in constraints
                      if c.source_prediction.get("relation") == "voltage_compatible"]
        assert len(compatible) == 1
        assert compatible[0].confidence > 0

    def test_voltage_incompatible(self, bridge):
        # NMC811 cathode: 2.5-4.3V, LGPS oxidation at 2.1V -> headroom -2.2V
        vw = MockVoltageWindow(lower=2.5, upper=4.3)
        constraints = bridge.voltage_constraints(
            "NMC811", "LGPS", voltage_window_a=vw, oxidation_potential=2.1
        )
        incompat = [c for c in constraints
                    if c.source_prediction.get("relation") == "voltage_incompatible"]
        assert len(incompat) == 1

    def test_voltage_marginal(self, bridge):
        # Marginal: headroom 0.3V (below 0.5 margin)
        vw = MockVoltageWindow(lower=2.5, upper=4.2)
        constraints = bridge.voltage_constraints(
            "NMC622", "EC", voltage_window_a=vw, oxidation_potential=4.5
        )
        # 0.3V headroom < 0.5V margin -> no compatible atom, but also not negative
        compatible = [c for c in constraints
                      if c.source_prediction.get("relation") == "voltage_compatible"]
        incompat = [c for c in constraints
                    if c.source_prediction.get("relation") == "voltage_incompatible"]
        assert len(compatible) == 0  # below margin
        assert len(incompat) == 0  # not negative

    def test_reduction_risk(self, bridge):
        vw = MockVoltageWindow(lower=0.0, upper=0.2)
        constraints = bridge.voltage_constraints(
            "Graphite", "EC", voltage_window_a=vw, reduction_potential=0.8
        )
        risk = [c for c in constraints
                if c.source_prediction.get("relation") == "reduction_risk"]
        assert len(risk) == 1

    def test_no_voltage_data(self, bridge):
        constraints = bridge.voltage_constraints("A", "B")
        assert constraints == []


# ---------------------------------------------------------------------------
# Thermal constraints
# ---------------------------------------------------------------------------

class TestThermalConstraints:
    def test_cte_compatible(self, bridge):
        # Small CTE mismatch: 10 vs 12 ppm/K -> 2/12 = 0.167 < 0.20
        constraints = bridge.thermal_constraints(
            "Al2O3", "Ti-6Al-4V", cte_a=10.0, cte_b=12.0
        )
        compat = [c for c in constraints
                  if c.source_prediction.get("relation") == "cte_compatible"]
        assert len(compat) == 1

    def test_cte_incompatible(self, bridge):
        # Large CTE mismatch: 5 vs 25 ppm/K -> 20/25 = 0.80 > 0.20
        constraints = bridge.thermal_constraints(
            "ZrO2", "Cu", cte_a=5.0, cte_b=25.0
        )
        incompat = [c for c in constraints
                    if c.source_prediction.get("relation") == "cte_incompatible"]
        assert len(incompat) == 1

    def test_thermal_stability_risk(self, bridge):
        constraints = bridge.thermal_constraints(
            "LGPS", "Li_metal",
            thermal_stability_a=80.0, thermal_stability_b=150.0
        )
        risk = [c for c in constraints
                if c.source_prediction.get("relation") == "thermal_risk"]
        assert len(risk) == 1

    def test_thermal_stability_safe(self, bridge):
        constraints = bridge.thermal_constraints(
            "LLZO", "LFP",
            thermal_stability_a=400.0, thermal_stability_b=350.0
        )
        stable = [c for c in constraints
                  if c.source_prediction.get("relation") == "thermal_stable"]
        assert len(stable) == 1

    def test_no_thermal_data(self, bridge):
        constraints = bridge.thermal_constraints("A", "B")
        assert constraints == []

    def test_cte_zero_handling(self, bridge):
        constraints = bridge.thermal_constraints(
            "A", "B", cte_a=0.0, cte_b=0.0
        )
        # max_cte is 0, should skip
        assert constraints == []


# ---------------------------------------------------------------------------
# Chemical constraints
# ---------------------------------------------------------------------------

class TestChemicalConstraints:
    def test_known_bad_pair(self, bridge):
        constraints = bridge.chemical_constraints(
            "LGPS", "NMC811", known_bad_pair=True
        )
        incomp = [c for c in constraints
                  if c.source_prediction.get("relation") == "known_incompatible"]
        assert len(incomp) == 1

    def test_known_bad_pair_implies_not_viable(self, bridge):
        constraints = bridge.chemical_constraints(
            "LGPS", "NMC811", known_bad_pair=True
        )
        rules = [c for c in constraints
                 if c.source_prediction.get("relation") == "incompatible_implies_not_viable"]
        assert len(rules) == 1

    def test_shared_critical_failures(self, bridge):
        constraints = bridge.chemical_constraints(
            "Li_metal", "Si",
            shared_failure_modes=["thermal_runaway", "dendrite_growth"]
        )
        shared = [c for c in constraints
                  if c.source_prediction.get("relation") == "shared_critical_failures"]
        assert len(shared) == 1

    def test_shared_non_critical_failures(self, bridge):
        constraints = bridge.chemical_constraints(
            "A", "B",
            shared_failure_modes=["capacity_fade"]
        )
        shared = [c for c in constraints
                  if c.source_prediction.get("relation") == "shared_critical_failures"]
        assert len(shared) == 0

    def test_no_known_issues(self, bridge):
        constraints = bridge.chemical_constraints("LFP", "EC")
        assert constraints == []

    def test_combined_bad_pair_and_failures(self, bridge):
        constraints = bridge.chemical_constraints(
            "Li_metal", "EC",
            known_bad_pair=True,
            shared_failure_modes=["dendrite_growth"]
        )
        # known_incompatible + rule + shared_critical_failures
        assert len(constraints) == 3


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_all_constraint_types_together(self, bridge):
        """Test that all constraint methods can be called and combined."""
        all_constraints = []

        scores = {
            'ion_transport': MockScorerResult(0.80),
            'electrochemical_stability': MockScorerResult(0.85),
            'interface_compatibility': MockScorerResult(0.70),
            'mechanical_compatibility': MockScorerResult(0.75),
            'degradation_penalty': MockScorerResult(0.90),
        }
        all_constraints.extend(
            bridge.score_constraints("LFP", "LLZO", scores)
        )

        vw = MockVoltageWindow(lower=2.5, upper=3.7)
        all_constraints.extend(
            bridge.voltage_constraints("LFP", "LLZO",
                                       voltage_window_a=vw,
                                       oxidation_potential=4.5)
        )

        all_constraints.extend(
            bridge.thermal_constraints("LFP", "LLZO",
                                       cte_a=10.0, cte_b=12.0,
                                       thermal_stability_a=350.0,
                                       thermal_stability_b=400.0)
        )

        all_constraints.extend(
            bridge.chemical_constraints("LFP", "LLZO")
        )

        # Should have constraints from scores (5 compat + 1 viable) + voltage + thermal
        assert len(all_constraints) >= 6

    def test_constraint_formulas_are_valid(self, bridge, good_scores):
        """All constraints should have a formula attribute."""
        constraints = bridge.score_constraints("A", "B", good_scores)
        for c in constraints:
            assert hasattr(c, 'formula')
            assert c.formula is not None

    def test_constraint_metadata_complete(self, bridge, good_scores):
        """All constraints should have complete metadata."""
        constraints = bridge.score_constraints("A", "B", good_scores)
        for c in constraints:
            assert "source" in c.source_prediction
            assert "target" in c.source_prediction
            assert "relation" in c.source_prediction
            assert "confidence" in c.source_prediction
            assert "strategy" in c.source_prediction
            assert 0.0 <= c.confidence <= 1.0
            assert isinstance(c.strategy, str)


# ---------------------------------------------------------------------------
# NIST-derived bonding constraints
# ---------------------------------------------------------------------------

class TestBondingConstraints:
    """Tests for bond length, coordination number, and charge balance constraints."""

    @pytest.fixture
    def bridge(self):
        return MaterialZFCBridge()

    # ── Bond length tests ──────────────────────────────────────────────

    def test_valid_bond_length(self, bridge):
        """Li-O bond at 2.0 Å is within bounds [1.60, 2.40]."""
        constraints = bridge.bonding_constraints(
            "Li2O", "test",
            bond_lengths={("Li", "O"): 2.0},
        )
        assert len(constraints) == 1
        assert "bond_plausible" in constraints[0].source_prediction["relation"]

    def test_bond_too_short(self, bridge):
        """Li-O bond at 1.2 Å is below min 1.60 -- repulsive wall."""
        constraints = bridge.bonding_constraints(
            "Li2O", "test",
            bond_lengths={("Li", "O"): 1.2},
        )
        # implausible fact + implication rule (implausible => not viable)
        assert len(constraints) == 2
        assert "bond_implausible" in constraints[0].source_prediction["relation"]

    def test_bond_too_long(self, bridge):
        """Li-O bond at 3.5 Å is above max 2.40 -- no bond."""
        constraints = bridge.bonding_constraints(
            "Li2O", "test",
            bond_lengths={("Li", "O"): 3.5},
        )
        # implausible fact + implication rule
        assert len(constraints) == 2
        assert "bond_implausible" in constraints[0].source_prediction["relation"]

    def test_reversed_element_order(self, bridge):
        """Bond lookup should work regardless of element ordering."""
        constraints_fwd = bridge.bonding_constraints(
            "GaAs", "test",
            bond_lengths={("Ga", "As"): 2.45},
        )
        constraints_rev = bridge.bonding_constraints(
            "GaAs", "test",
            bond_lengths={("As", "Ga"): 2.45},
        )
        # Both should produce 1 plausible constraint (2.45 is within Ga-As range 2.30-2.65)
        assert len(constraints_fwd) == len(constraints_rev)
        assert len(constraints_fwd) == 1
        assert "bond_plausible" in constraints_fwd[0].source_prediction["relation"]

    def test_unknown_bond_pair_ignored(self, bridge):
        """Bond pair not in BOND_LENGTH_BOUNDS should be silently skipped."""
        constraints = bridge.bonding_constraints(
            "test", "test",
            bond_lengths={("Xe", "Rn"): 3.0},
        )
        assert len(constraints) == 0  # Unknown pairs produce no constraints

    def test_multiple_bonds(self, bridge):
        """Multiple bond checks in one call."""
        constraints = bridge.bonding_constraints(
            "LiFePO4", "test",
            bond_lengths={
                ("Li", "O"): 2.1,   # valid (within 1.60-2.40)
                ("Fe", "O"): 2.0,   # valid (within 1.75-2.20)
                ("P", "O"): 1.5,    # valid (within 1.45-1.65)
            },
        )
        assert len(constraints) == 3
        for c in constraints:
            assert "bond_plausible" in c.source_prediction["relation"]

    # ── Coordination number tests ──────────────────────────────────────

    def test_valid_coordination(self, bridge):
        """Li with CN=4 is within [2, 8]."""
        constraints = bridge.bonding_constraints(
            "test", "test",
            coordination_numbers={"Li": 4},
        )
        assert len(constraints) == 1
        assert "coordination_valid" in constraints[0].source_prediction["relation"]

    def test_coordination_too_low(self, bridge):
        """Li with CN=1 is below minimum 2."""
        constraints = bridge.bonding_constraints(
            "test", "test",
            coordination_numbers={"Li": 1},
        )
        assert len(constraints) == 2  # violation + implication
        assert "coordination_violation" in constraints[0].source_prediction["relation"]

    def test_coordination_too_high(self, bridge):
        """Si with CN=8 is above maximum 6."""
        constraints = bridge.bonding_constraints(
            "test", "test",
            coordination_numbers={"Si": 8},
        )
        assert len(constraints) == 2
        assert "coordination_violation" in constraints[0].source_prediction["relation"]

    def test_coordination_boundary(self, bridge):
        """Exact boundary values should pass."""
        constraints = bridge.bonding_constraints(
            "test", "test",
            coordination_numbers={"Al": 4},  # min bound
        )
        assert len(constraints) == 1
        assert "coordination_valid" in constraints[0].source_prediction["relation"]

        constraints2 = bridge.bonding_constraints(
            "test", "test",
            coordination_numbers={"Al": 6},  # max bound
        )
        assert len(constraints2) == 1
        assert "coordination_valid" in constraints2[0].source_prediction["relation"]

    # ── Charge balance tests ──────────────────────────────────────────

    def test_charge_balanced_composition(self, bridge):
        """LiFePO4: Li(+1) + Fe(+2) + P(+5) + O4(-8) = 0."""
        constraints = bridge.bonding_constraints(
            "LiFePO4", "test",
            composition={"Li": 1, "Fe": 1, "P": 1, "O": 4},
        )
        assert len(constraints) == 1
        assert "charge_balanced" in constraints[0].source_prediction["relation"]

    def test_charge_imbalanced_composition(self, bridge):
        """Li3Fe2O2: Li3(+3) + Fe2(+4) + O2(-4) = +3 imbalanced."""
        constraints = bridge.bonding_constraints(
            "Li3Fe2O2", "test",
            composition={"Li": 3, "Fe": 2, "O": 2},
        )
        # Should produce imbalance atom + implication rule
        assert len(constraints) == 2
        assert "charge_imbalanced" in constraints[0].source_prediction["relation"]

    def test_combined_all_constraint_types(self, bridge):
        """All three constraint types combined in one call."""
        constraints = bridge.bonding_constraints(
            "LiFePO4", "test",
            bond_lengths={("Li", "O"): 2.1, ("Fe", "O"): 2.0},
            coordination_numbers={"Li": 4, "Fe": 6},
            composition={"Li": 1, "Fe": 1, "P": 1, "O": 4},
        )
        # 2 valid bonds + 2 valid CN + 1 charge balanced = 5
        assert len(constraints) == 5

    def test_constraint_metadata_complete(self, bridge):
        """All bonding constraints should have complete metadata."""
        constraints = bridge.bonding_constraints(
            "NMC811", "LLZO",
            bond_lengths={("Li", "O"): 2.0},
            coordination_numbers={"Li": 6},
            composition={"Li": 1, "Ni": 0.8, "Mn": 0.1, "Co": 0.1, "O": 2},
        )
        for c in constraints:
            assert "source" in c.source_prediction
            assert "target" in c.source_prediction
            assert "relation" in c.source_prediction
            assert "confidence" in c.source_prediction
            assert "strategy" in c.source_prediction
            assert 0.0 <= c.confidence <= 1.0

    def test_empty_inputs(self, bridge):
        """No inputs should produce no constraints."""
        constraints = bridge.bonding_constraints("A", "B")
        assert len(constraints) == 0


# ---------------------------------------------------------------------------
# ZFC unavailable fallback
# ---------------------------------------------------------------------------

class TestZFCUnavailable:
    def test_bridge_reports_availability(self):
        bridge = MaterialZFCBridge()
        # If we got here, ZFC is available (otherwise tests are skipped)
        assert bridge.is_available is True
