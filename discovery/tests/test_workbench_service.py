# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from types import SimpleNamespace

from discovery.workbench_service import DiscoveryGoal, DiscoveryWorkbenchService


def test_charge_balance_failure_is_a_hard_veto(monkeypatch):
    service = DiscoveryWorkbenchService()
    designed = SimpleNamespace(
        formula="Li2O3",
        composition={"Li": 2.0, "O": 3.0},
        anchor="LFP",
        predicted_properties={},
        overall_score=0.9,
        synthesizability=0.9,
    )
    monkeypatch.setattr(
        service._designer,
        "design",
        lambda spec: SimpleNamespace(candidates=[designed]),
    )
    monkeypatch.setattr(
        "pfas_bridge.compliance_checker.PFASComplianceChecker.check",
        lambda self, formula: SimpleNamespace(is_pfas=False, urgency="none"),
    )
    monkeypatch.setattr(
        "composition_engine.physical_gates.charge_balanceable",
        lambda formula: False,
    )

    result = service.run_discovery_pipeline(DiscoveryGoal(max_candidates=1))

    assert len(result) == 1
    assert result[0].zfc_witnessed is False
    assert result[0].hard_vetoes == ["charge_balance"]
    assert result[0].overall_confidence == 0.0


def test_charge_balance_status_survives_compatibility_metadata_update(monkeypatch):
    service = DiscoveryWorkbenchService()
    candidate = SimpleNamespace(
        formula="LiFePO4",
        composition={"Li": 1.0, "Fe": 1.0, "P": 1.0, "O": 4.0},
        anchor="LFP",
        predicted_properties={},
        overall_score=0.8,
        synthesizability=0.6,
    )
    monkeypatch.setattr(
        service._designer,
        "design",
        lambda spec: SimpleNamespace(candidates=[candidate]),
    )
    monkeypatch.setattr(
        "pfas_bridge.compliance_checker.PFASComplianceChecker.check",
        lambda self, formula: SimpleNamespace(is_pfas=False, urgency="none"),
    )
    monkeypatch.setattr(
        "composition_engine.physical_gates.charge_balanceable",
        lambda formula: True,
    )
    workflow = SimpleNamespace(
        viable=True,
        scores={"total": 0.8, "ensemble": {"agreement": 0.7}},
    )
    monkeypatch.setattr("discovery.workbench_service.run_compatibility_workflow", lambda *a, **k: workflow)
    monkeypatch.setattr(
        "synthesis_planner.route_planner.SynthesisPlanner.plan_synthesis",
        lambda self, target: SimpleNamespace(best_route=None, precursor_cost_usd=0.0),
    )

    result = service.run_discovery_pipeline(
        DiscoveryGoal(max_candidates=1, target_interface_material="Li_metal")
    )

    assert result[0].compatibility_metadata["charge_balance_status"] is True
    assert result[0].compatibility_metadata["agreement"] == 0.7


def test_formula_pfas_screen_rules_out_impossible_formula_without_network():
    service = DiscoveryWorkbenchService()

    assert service._screen_formula_pfas("LiFePO4") is True
    assert service._screen_formula_pfas("LiNi0.8Mn0.1Co0.1O2") is True


def test_formula_pfas_screen_abstains_when_connectivity_is_required():
    service = DiscoveryWorkbenchService()

    assert service._screen_formula_pfas("C2F4") is None
    assert service._screen_formula_pfas("not-a-formula") is None


def test_formula_pfas_screen_preserves_exact_registry_veto():
    service = DiscoveryWorkbenchService()

    assert service._screen_formula_pfas("PVDF") is False
