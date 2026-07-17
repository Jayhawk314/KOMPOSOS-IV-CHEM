from copy import deepcopy

from audit.prediction_drift import evaluate


BASE_OBSERVED = {
    "benchmark": "formation_energy_strict_formula_loo",
    "n": 179,
    "skipped": 0,
    "mae_eV_per_atom": 0.4159475198746357,
    "rmse_eV_per_atom": 0.5518664385600222,
    "median_abs_error_eV_per_atom": 0.3396751384647081,
    "interval_coverage": {
        "50": 0.4972067039106145,
        "80": 0.7932960893854749,
        "95": 0.9497206703910615,
    },
}


def test_frozen_prediction_contract_agrees_and_receipt_is_stable():
    first = evaluate(observed=deepcopy(BASE_OBSERVED))
    second = evaluate(observed=deepcopy(BASE_OBSERVED))
    assert first["verdict"] == "AGREE"
    assert first["receipt_id"] == second["receipt_id"]


def test_metric_drift_cannot_be_hidden_by_artifact_receipt():
    changed = deepcopy(BASE_OBSERVED)
    changed["mae_eV_per_atom"] += 0.2
    result = evaluate(observed=changed)
    assert result["verdict"] == "CLASH"
    assert any("mae_eV_per_atom" in reason for reason in result["reasons"])
