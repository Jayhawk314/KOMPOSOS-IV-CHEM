import json
from pathlib import Path
from types import SimpleNamespace

from audit.run_crystal_search_ablation import (
    RANDOM_SEED,
    VARIANTS,
    VARIANT_SEED_OFFSETS,
    VariantDesigner,
)
from composition_engine.designer import DesignSpec, PropertyTarget


class _FakePredictor:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def predict(self, formula, domain=None, include_structure=False):
        self.calls.append((formula, domain, include_structure))
        voltage, capacity = self.values[formula]
        return SimpleNamespace(
            properties={
                "voltage": SimpleNamespace(value=voltage),
                "theoretical_capacity": SimpleNamespace(value=capacity),
            }
        )


def _db():
    return SimpleNamespace(
        entries=[
            SimpleNamespace(name="a", formula="LiFePO4", domain="battery"),
            SimpleNamespace(name="b", formula="LiMn2O4", domain="battery"),
            SimpleNamespace(name="c", formula="Li4Ti5O12", domain="battery"),
        ]
    )


def _spec(voltage_min=3.0):
    return DesignSpec(
        targets=[
            PropertyTarget("voltage", voltage_min, 4.0),
            PropertyTarget("theoretical_capacity", 140.0, 180.0),
        ],
        domain="battery",
        max_candidates=3,
    )


def test_variant_seed_offsets_are_name_stable_and_unique():
    assert set(VARIANT_SEED_OFFSETS) == set(VARIANTS)
    assert len(set(VARIANT_SEED_OFFSETS.values())) == len(VARIANTS)
    assert RANDOM_SEED + VARIANT_SEED_OFFSETS["random_union"] == 20260811
    assert VARIANT_SEED_OFFSETS["four_strategy_union"] == 7


def test_known_retrieval_cache_is_shared_only_for_same_predictor_and_domain():
    VariantDesigner._retrieval_prediction_cache.clear()
    values = {
        "LiFePO4": (3.4, 165.0),
        "LiMn2O4": (4.1, 148.0),
        "Li4Ti5O12": (1.6, 175.0),
    }
    predictor = _FakePredictor(values)
    first = VariantDesigner(
        "known_property_retrieval", {}, RANDOM_SEED, predictor, _db()
    )
    generated = first._generate_candidates(_spec())

    assert generated[0][0] == "LiFePO4"
    assert first.retrieval_scanned == 3
    assert first.retrieval_predictions_computed == 3
    assert len(predictor.calls) == 3

    second = VariantDesigner(
        "known_property_retrieval", {}, RANDOM_SEED, predictor, _db()
    )
    second._generate_candidates(_spec(voltage_min=3.5))
    assert second.retrieval_scanned == 3
    assert second.retrieval_predictions_computed == 0
    assert len(predictor.calls) == 3

    other_predictor = _FakePredictor(values)
    third = VariantDesigner(
        "known_property_retrieval", {}, RANDOM_SEED, other_predictor, _db()
    )
    third._generate_candidates(_spec())
    assert third.retrieval_predictions_computed == 3
    assert len(other_predictor.calls) == 3


def test_versioned_report_freezes_scenarios_and_current_comparison():
    report_path = Path(__file__).resolve().parents[1] / "crystal_search_ablation_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["evidence_role"] == "development_spent"
    assert report["parameters"]["variant_seed_offsets"] == VARIANT_SEED_OFFSETS
    assert report["summary"]["known_property_retrieval"]["any_top_k_property_hits"] == 8
    assert report["summary"]["four_strategy_union"]["any_top_k_property_hits"] == 7
    assessed = [row for row in report["rows"] if row.get("status") == "assessed"]
    assert assessed
    assert all(len(row["target_windows"]) == 2 for row in assessed)
