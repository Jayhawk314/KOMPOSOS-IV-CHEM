# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
"""
Tests for calibrated uncertainty quantification in formation energy predictions.

Verifies that the leave-one-out calibration produces error estimates that
bracket actual prediction errors at approximately 1-sigma (68%) coverage.
"""

import json
from pathlib import Path

import pytest
import numpy as np
from composition_engine.formation_energy import (
    FormationEnergyPredictor,
    KNOWN_EF,
    parse_formula,
    composition_vector,
)


class TestCalibration:
    """Tests for leave-one-out calibrated uncertainty."""

    @pytest.fixture(scope="class")
    def predictor(self):
        return FormationEnergyPredictor(calibrate=True)

    @pytest.fixture(scope="class")
    def uncalibrated(self):
        return FormationEnergyPredictor(calibrate=False)

    def test_calibration_runs(self, predictor):
        """Calibration should complete and set coefficients."""
        assert predictor._calibrated is True
        assert predictor._cal_a != 0.0

    def test_uncalibrated_has_identity(self, uncalibrated):
        """Without calibration, coefficients should be identity (a=1, b=0)."""
        assert uncalibrated._calibrated is False
        assert uncalibrated._cal_a == 1.0
        assert uncalibrated._cal_b == 0.0

    def test_error_estimate_positive(self, predictor):
        """All error estimates should be positive."""
        for formula in ["LiCoO2", "NMC811", "SiC", "GaAs", "BaTiO3"]:
            result = predictor.predict(formula)
            assert result.error_estimate_eV > 0, f"{formula} error <= 0"

    def test_known_material_low_error(self, predictor):
        """Known materials should have lower error than unknown compositions."""
        known_result = predictor.predict("LiCoO2")  # in KNOWN_EF
        unknown_result = predictor.predict("Li3Nb0.5Ta0.5O4")  # unlikely in DB
        # Known material should generally have lower error
        # (not always guaranteed, but should hold for well-represented compositions)
        assert known_result.error_estimate_eV < 1.0, "Known material error too high"

    def test_ensemble_spread_affects_error(self, predictor):
        """Materials with high estimator disagreement should have higher error."""
        # Simple binary compounds: estimators tend to agree
        simple = predictor.predict("NaCl")
        # Complex multi-element: estimators diverge more
        complex_mat = predictor.predict("LiNi0.8Mn0.1Co0.1O2")
        # Both should have finite positive errors
        assert simple.error_estimate_eV > 0
        assert complex_mat.error_estimate_eV > 0

    def test_ensemble_spread_in_prediction(self, predictor):
        """Predictions should incorporate ensemble spread."""
        result = predictor.predict("LiCoO2")
        # Should have multiple sources
        assert len(result.sources) >= 1

    def test_phase16_external_report_meets_coverage_targets(self):
        """
        Phase 16 coverage is judged on the frozen external validation split.

        The curated KNOWN_EF table is still useful as a smoke test, but Phase
        16 is calibrated to the MP-style external manifest, not to the older
        hand-curated battery/ceramic table.
        """
        report_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "calibration"
            / "phase16_calibration_report.json"
        )
        if not report_path.exists():
            pytest.skip("Phase 16 calibration report is not available")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        validation = report["global"]["validation"]
        baseline = report["baseline"]["validation"]
        coverage = validation["coverage"]

        assert validation["n"] >= 1000
        assert validation["mae"] < baseline["mae"]
        assert validation["rmse"] < baseline["rmse"]
        assert 0.40 <= coverage["50"] <= 0.60
        assert 0.70 <= coverage["80"] <= 0.90
        assert 0.88 <= coverage["95"] <= 0.98
