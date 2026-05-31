# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Tests for Phase 16 external calibration utilities."""

from composition_engine.phase16_calibration import (
    CalibrationScale,
    Phase16CalibrationModel,
    classify_chemistry,
)
from composition_engine.parser import parse_formula


def test_classify_chemistry_core_strata():
    assert classify_chemistry(parse_formula("Al2O3")) == "oxide"
    assert classify_chemistry(parse_formula("MoS2")) == "sulfide"
    assert classify_chemistry(parse_formula("LiF")) == "halide"
    assert classify_chemistry(parse_formula("TiC")) == "carbide"
    assert classify_chemistry(parse_formula("GaN")) == "nitride"
    assert classify_chemistry(parse_formula("NiAl")) == "intermetallic"


def test_calibration_intervals_are_monotonic_and_class_specific():
    model = Phase16CalibrationModel(
        version="test",
        created_at="2026-05-20T00:00:00Z",
        target="formation_energy_per_atom",
        manifest_sha256="abc",
        global_scale=CalibrationScale(
            count=100,
            scale_by_level={"50": 1.0, "80": 2.0, "95": 3.0},
            median_abs_error=0.1,
            mae=0.2,
        ),
        class_scales={
            "oxide": CalibrationScale(
                count=50,
                scale_by_level={"50": 0.8, "80": 1.5, "95": 2.5},
                median_abs_error=0.08,
                mae=0.16,
            )
        },
    )

    intervals = model.intervals(0.2, "oxide")
    assert intervals["50"] == 0.16
    assert intervals["80"] == 0.3
    assert intervals["95"] == 0.5
    assert intervals["50"] <= intervals["80"] <= intervals["95"]

    fallback = model.intervals(0.2, "sulfide")
    assert fallback["50"] == 0.2
    assert fallback["80"] == 0.4
    assert fallback["95"] == 0.6

