# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from api.monitoring_export import export_compatibility, export_prediction


def test_prediction_export_is_typed_and_content_addressed():
    result = export_prediction("LiFePO4", domain="battery")
    assert result["schema"] == "komposos-chem-monitor.v1"
    assert result["kind"] == "composition_prediction"
    assert result["evidence_role"] == "screening_model_estimate"
    assert len(result["receipt_id"]) == 64


def test_compatibility_export_preserves_native_scope():
    result = export_compatibility("PVDF", "NMC811")
    assert result["kind"] == "compatibility_workflow"
    assert result["evidence_role"] == "screening_decision"
    assert "not independent physical measurements" in result["payload"]["scope_note"]
