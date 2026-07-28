# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Regression tests for MD verification fallback behavior."""

from oracle.md_integration import GROMACSRunner
from oracle.material_zfc_constraints import MaterialZFCBridge, ZFC_LOGIC_AVAILABLE


def test_missing_gromacs_returns_low_confidence_fallback():
    runner = GROMACSRunner(gmx_bin="definitely_missing_gmx_binary")

    result = runner.run_interface_simulation("LGPS", "NMC811")

    assert result.verdict == "no_verdict"
    assert result.measured_md is False
    assert result.confidence < 0.5
    assert result.score < 0.5
    assert result.simulation_metadata["engine"] == "heuristic_fallback_no_gromacs"
    assert "GROMACS Result" not in result.detail
    assert "no GROMACS trajectory was executed" in result.detail


def test_missing_gromacs_inputs_returns_no_verdict(monkeypatch):
    monkeypatch.setattr("oracle.md_integration.shutil.which", lambda _: "fake-gmx")
    runner = GROMACSRunner()

    result = runner.run_interface_simulation("A", "B")

    assert result.verdict == "no_verdict"
    assert result.measured_md is False
    assert result.confidence == 0.0
    assert result.simulation_metadata["engine"] == "no_verdict_missing_gromacs_inputs"
    assert result.simulation_metadata["input_status"]["missing_required"] == [
        "gro_path",
        "top_path",
    ]
    assert "Supply gro_path/top_path or input_dir" in result.detail


def test_input_dir_resolves_real_gromacs_bundle(tmp_path):
    (tmp_path / "system.gro").write_text("mock gro", encoding="utf-8")
    (tmp_path / "topol.top").write_text("mock top", encoding="utf-8")
    (tmp_path / "run.mdp").write_text("mock mdp", encoding="utf-8")
    runner = GROMACSRunner()

    bundle = runner._resolve_input_bundle("A", "B", {"input_dir": str(tmp_path)})

    assert bundle["source"] == "input_dir"
    assert bundle["missing_required"] == []
    assert bundle["gro_path"].endswith("system.gro")
    assert bundle["top_path"].endswith("topol.top")
    assert bundle["mdp_path"].endswith("run.mdp")


def test_missing_configured_file_paths_are_no_verdict(monkeypatch, tmp_path):
    monkeypatch.setattr("oracle.md_integration.shutil.which", lambda _: "fake-gmx")
    gro_path = tmp_path / "missing.gro"
    top_path = tmp_path / "missing.top"

    result = GROMACSRunner().run_interface_simulation(
        "A",
        "B",
        {"gro_path": str(gro_path), "top_path": str(top_path)},
    )

    assert result.verdict == "no_verdict"
    assert result.simulation_metadata["engine"] == "no_verdict_missing_gromacs_inputs"
    assert str(gro_path.resolve()) in result.simulation_metadata["input_status"]["missing_required"]


def test_xvg_parser_ignores_gromacs_metadata(tmp_path):
    xvg = tmp_path / "potential.xvg"
    xvg.write_text(
        '\n'.join([
            '# comment',
            '@ title "Potential"',
            '0.0 -1000.0',
            '1.0 -1001.5',
            'bad line',
            '2.0 -1002.0',
        ]),
        encoding="utf-8",
    )

    assert GROMACSRunner._parse_xvg_series(xvg) == [
        (0.0, -1000.0),
        (1.0, -1001.5),
        (2.0, -1002.0),
    ]


def test_stability_analysis_classifies_stable_energy_and_low_diffusion():
    energy = [(0.0, -1000.0), (1.0, -1001.0), (2.0, -1002.0), (3.0, -1001.0)]
    msd = [(0.0, 0.0), (100.0, 1e-9), (200.0, 2e-9)]

    result = GROMACSRunner._classify_stability_signals(energy, msd)

    assert result["viable"] is True
    assert result["confidence"] >= 0.8
    assert result["energy_stable"] is True
    assert result["diffusion_stable"] is True
    assert result["relative_energy_drift"] < result["energy_drift_threshold"]
    assert result["diffusion_coefficient_cm2_s"] < result["diffusion_threshold_cm2_s"]


def test_stability_analysis_flags_energy_drift_and_diffusion():
    energy = [(0.0, -1000.0), (1.0, -900.0), (2.0, -850.0), (3.0, -800.0)]
    msd = [(0.0, 0.0), (100.0, 1e-4), (200.0, 2e-4)]

    result = GROMACSRunner._classify_stability_signals(energy, msd)

    assert result["viable"] is False
    assert result["energy_stable"] is False
    assert result["diffusion_stable"] is False
    assert result["score"] < 0.5


def test_stability_analysis_without_signals_is_low_confidence_no_verdict():
    result = GROMACSRunner._classify_stability_signals([], [])

    assert result["viable"] is False
    assert result["confidence"] < 0.5
    assert result["measured_signals"] == 0
    assert "no analyzable energy/MSD signals" in result["verdict_detail"]


def test_measured_md_result_exports_zfc_constraint_scores_and_ds_fusion():
    analysis = GROMACSRunner._classify_stability_signals(
        [(0.0, -1000.0), (1.0, -1001.0), (2.0, -1001.5)],
        [(0.0, 0.0), (100.0, 1e-9), (200.0, 2e-9)],
    )
    result = GROMACSRunner()._heuristic_fallback("A", "B", 298.15, "unused")
    result.score = analysis["score"]
    result.confidence = analysis["confidence"]
    result.simulation_metadata = {"engine": "GROMACS", "analysis": analysis}

    constraint_scores = result.constraint_scores()
    fusion = result.fuse_with_categorical(0.7, True)

    assert "md_energy_stability" in constraint_scores
    assert "md_diffusion_stability" in constraint_scores
    assert constraint_scores["md_analysis_confidence"] >= 0.8
    assert fusion["used"] is True
    assert fusion["fused_viable"] is True


def test_md_constraint_scores_feed_zfc_vetoes():
    if not ZFC_LOGIC_AVAILABLE:
        return

    constraints = MaterialZFCBridge().score_constraints(
        "A",
        "B",
        {"md_energy_stability": 0.05, "md_diffusion_stability": 0.9},
    )
    relations = {c.source_prediction.get("relation") for c in constraints}

    assert "md_energy_stability_veto" in relations
    assert "md_diffusion_stability_compatible" in relations
