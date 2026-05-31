import pytest
import json
from pathlib import Path

from audit.run_audit import _evaluate_pair_decision
from oracle.compatibility_calibration import (
    BinnedCompatibilityCalibrator,
    CompatibilityCalibrationStore,
    compute_classification_metrics,
)
from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_decision import COMPATIBLE, NEEDS_CONTEXT
from oracle.compatibility_capabilities import check_capabilities, capability_report
from oracle.compatibility_ensemble import build_compatibility_ensemble
from oracle.enrichment import compose_values, summarize_compatibility_components
from oracle.compatibility_failure_memory import build_failure_memory, classify_failure_pattern
from oracle.compatibility_transfer import TransferCase, guard_transfer
from oracle.typed_morphisms import infer_typed_morphism


def test_battery_metal_can_abstain_without_electrolyte_context():
    decision = _evaluate_pair_decision(
        "Al_foil",
        "NMC622",
        "battery-metal",
        allow_abstention=True,
    )

    assert decision.status == NEEDS_CONTEXT
    assert "electrolyte" in decision.missing_context
    assert decision.predicted_compatible is None


def test_battery_metal_evaluates_with_electrolyte_context():
    context = CompatibilityContext(electrolyte="LiPF6", role="cathode_collector")
    decision = _evaluate_pair_decision(
        "Al_foil",
        "NMC622",
        "battery-metal",
        electrolyte="LiPF6",
        role="cathode_collector",
        context=context,
        allow_abstention=True,
    )

    assert decision.status == COMPATIBLE
    assert decision.predicted_compatible is True
    assert decision.score > 0.5
    assert decision.metadata["typed_morphism"]["relation"] == "cathode_collector_for"


def test_typed_morphism_distinguishes_battery_collector_roles():
    cathode_context = CompatibilityContext(electrolyte="LiPF6", role="cathode_collector")
    anode_context = CompatibilityContext(electrolyte="LiPF6", role="anode_collector")

    cathode = infer_typed_morphism("Al_foil", "NMC622", "battery-metal", cathode_context)
    anode = infer_typed_morphism("Al_foil", "Si", "battery-metal", anode_context)

    assert cathode.compatible is True
    assert cathode.relation == "cathode_collector_for"
    assert anode.compatible is False
    assert anode.veto is True
    assert anode.relation == "not_anode_collector_for"


def test_calibration_metrics_include_reliability_and_coverage():
    results = [
        {"score": 0.9, "expected_compatible": True, "correct": True, "verdict": "TP"},
        {"score": 0.8, "expected_compatible": True, "correct": True, "verdict": "TP"},
        {"score": 0.2, "expected_compatible": False, "correct": True, "verdict": "TN"},
        {"score": 0.7, "expected_compatible": False, "correct": False, "verdict": "FP"},
        {"decision_status": "needs_context", "verdict": "ABSTAIN", "score": None},
    ]

    metrics = compute_classification_metrics(results)

    assert metrics["evaluated"] == 4
    assert metrics["abstentions"] == 1
    assert metrics["coverage"] == 0.8
    assert metrics["brier_score"] > 0
    assert len(metrics["score_bins"]) == 10


def test_binned_calibrator_maps_supported_bin_to_observed_rate():
    results = [
        {"score": 0.82, "expected_compatible": True, "correct": True, "verdict": "TP"},
        {"score": 0.85, "expected_compatible": True, "correct": True, "verdict": "TP"},
        {"score": 0.88, "expected_compatible": False, "correct": False, "verdict": "FP"},
    ]
    calibrator = BinnedCompatibilityCalibrator(min_bin_count=3).fit(results)

    assert calibrator.calibrate(0.86) == pytest.approx(2 / 3, abs=1e-4)


def test_runtime_calibration_store_prefers_domain_bins_then_global():
    artifact = {
        "version": "unit",
        "domain_calibrators": {
            "polymer": {
                "calibrator": {
                    "min_bin_count": 2,
                    "bins": [
                        {
                            "bin": "0.8-0.9",
                            "lower": 0.8,
                            "upper": 0.9,
                            "n": 3,
                            "mean_score": 0.84,
                            "observed_positive_rate": 0.6667,
                        }
                    ],
                }
            }
        },
        "global_calibrator": {
            "min_bin_count": 2,
            "bins": [
                {
                    "bin": "0.8-0.9",
                    "lower": 0.8,
                    "upper": 0.9,
                    "n": 10,
                    "mean_score": 0.85,
                    "observed_positive_rate": 0.8,
                }
            ],
        },
    }
    store = CompatibilityCalibrationStore(artifact)

    domain = store.calibrate(0.85, "polymer")
    fallback = store.calibrate(0.85, "metal")

    assert domain["calibrator"] == "domain:polymer"
    assert domain["calibrated_probability"] == pytest.approx(0.6667, abs=1e-4)
    assert fallback["calibrator"] == "global"
    assert fallback["calibrated_probability"] == pytest.approx(0.8, abs=1e-4)


def test_generated_calibration_artifact_excludes_current_blind_q4():
    artifact_path = (
        Path(__file__).resolve().parent.parent
        / "audit"
        / "calibration"
        / "compatibility_calibration_2026_q4_dev.json"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    excluded_versions = {item["version"] for item in artifact["excluded_sources"]}
    row_sources = {row["source"] for row in artifact["rows"]}

    assert "external_blind.compatibility.2026_q4.v1" in excluded_versions
    assert all("compatibility_2026_q4" not in source for source in row_sources)


def test_quantale_summary_exposes_bottleneck_and_compounded_risk():
    summary = summarize_compatibility_components({
        "voltage": 0.9,
        "thermal": 0.8,
        "chemical": 0.2,
    })

    assert summary["bottleneck_score"] == 0.2
    assert summary["weakest_axis"] == "chemical"
    assert summary["failure_risk_or"] == compose_values([0.1, 0.2, 0.8], "probabilistic_or")
    assert summary["confidence_product"] == pytest.approx(0.144, abs=1e-4)


def test_typed_capability_report_checks_required_addons():
    check = check_capabilities(
        "battery-metal",
        ["rule_scorer", "typed_morphisms", "calibration", "failure_memory", "yoneda_transfer_guard"],
    )
    report = capability_report("battery-metal")

    assert check.compatible is True
    assert check.missing == []
    assert {cap["name"] for cap in report["capabilities"]} >= {
        "rule_scorer",
        "typed_morphisms",
        "ensemble",
    }


def test_yoneda_transfer_guard_requires_strict_contextual_support():
    context = CompatibilityContext(interface_type="wide_bandgap_epitaxy")
    cases = [
        TransferCase(
            material_a="GaN",
            material_b="SiC_4H",
            domain="semiconductor",
            score=0.75,
            expected_compatible=True,
            source="unit",
            context={"interface_type": "wide_bandgap_epitaxy"},
        ),
        TransferCase(
            material_a="AlGaN",
            material_b="SiC_6H",
            domain="semiconductor",
            score=0.76,
            expected_compatible=True,
            source="unit",
            context={"interface_type": "wide_bandgap_epitaxy"},
        ),
    ]

    allowed = guard_transfer("GaN", "SiC_6H", "semiconductor", context, cases=cases, min_support=1)
    weak = guard_transfer("GaN", "GaAs", "semiconductor", context, cases=cases)

    assert allowed.allowed is True
    assert allowed.compatible is True
    assert allowed.support_n >= 1
    assert weak.allowed is False


def test_compatibility_ensemble_collects_locked_addon_votes():
    context = CompatibilityContext(electrolyte="LiPF6", role="anode_collector")
    result = build_compatibility_ensemble(
        "Al_foil",
        "Si",
        "battery-metal",
        0.18,
        False,
        context,
    )

    strategies = {vote.strategy for vote in result.votes}
    assert "rule_scorer" in strategies
    assert "typed_morphism" in strategies
    assert "calibration" in strategies
    assert result.capabilities["domain"] == "battery-metal"
    assert result.score < 0.5


def test_failure_memory_records_false_negative_pattern():
    row = {
        "id": 9142,
        "material_a": "SiO2",
        "material_b": "Soda_Lime",
        "domain": "glass",
        "score": 0.534,
        "predicted_compatible": False,
        "expected_compatible": True,
        "correct": False,
        "verdict": "FN",
        "decision_status": "incompatible",
        "decision": {"confidence": 0.3908, "missing_context": []},
        "context": {},
        "evidence_basis": "Family-specific glass compatibility exception.",
    }

    memory = build_failure_memory([row], dataset_name="unit")

    assert memory["episode_count"] == 1
    assert memory["pattern_counts"] == {"false_negative:glass_family_rule_gap": 1}
    assert memory["episodes"][0]["delta_type"] == "ORPHAN"
    assert memory["episodes"][0]["resolution"] == "REFUTED"


def test_failure_memory_records_needs_context_as_reframed_episode():
    row = {
        "id": 1,
        "material_a": "Al_foil",
        "material_b": "NMC622",
        "domain": "battery-metal",
        "score": None,
        "predicted_compatible": None,
        "expected_compatible": True,
        "correct": None,
        "verdict": "ABSTAIN",
        "decision_status": "needs_context",
        "decision": {"missing_context": ["electrolyte"]},
        "context": {},
    }

    assert classify_failure_pattern(row) == "abstention:missing_electrolyte"
    memory = build_failure_memory([row], dataset_name="unit")

    assert memory["episode_count"] == 1
    assert memory["episodes"][0]["delta_type"] == "UNKNOWN"
    assert memory["episodes"][0]["resolution"] == "REFRAMED"


def test_silica_glass_family_exception_keeps_reactive_oxide_false():
    from ceramic_bridge.interface_validator import CeramicInterfaceValidator

    validator = CeramicInterfaceValidator()
    silica_sodalime = validator.validate("SiO2", "Soda_Lime")
    silica_mgo = validator.validate("SiO2", "MgO")

    assert silica_sodalime.viable is True
    assert "silica_glass_family_exception" in silica_sodalime.details
    assert silica_mgo.viable is False


def test_ii_vi_buffered_family_relaxes_lattice_veto_selectively():
    from semiconductor_bridge.interface_validator import SemiconductorInterfaceValidator

    validator = SemiconductorInterfaceValidator()
    cdte_znse = validator.validate("CdTe", "ZnSe")
    cdte_zno = validator.validate("CdTe", "ZnO")

    assert cdte_znse.viable is True
    assert "lattice_veto_relaxed" in cdte_znse.details
    assert cdte_zno.viable is False


def test_q3_polymer_failure_families_are_contextualized():
    from polymer_bridge.interface_validator import PolymerInterfaceValidator

    validator = PolymerInterfaceValidator()

    assert validator.validate("PA6", "ABS").viable is False
    assert validator.validate("PVC", "PA6").viable is False
    assert validator.validate("Epoxy", "PTFE").viable is False
    assert validator.validate("PPS", "PTFE").viable is True


def test_bn_silica_family_is_vetoed_without_interlayer():
    from ceramic_bridge.interface_validator import CeramicInterfaceValidator

    validator = CeramicInterfaceValidator()
    result = validator.validate("BN_hex", "SiO2")

    assert result.viable is False
    assert result.total <= 0.35
    assert "degradation veto" in result.details["veto"]


def test_fe_base_steel_join_relaxes_galvanic_veto_only_in_dry_service():
    from metal_bridge.interface_validator import MetalConditions, MetalInterfaceValidator

    validator = MetalInterfaceValidator()
    indoor = validator.validate("SS_304", "Steel_1018")
    wet = validator.validate(
        "SS_304",
        "Steel_1018",
        MetalConditions(environment="conductive_moisture", humidity_pct=90),
    )

    assert indoor.viable is True
    assert "galvanic_veto_relaxed" in indoor.details
    assert wet.viable is False


def test_iii_v_buffered_family_relaxes_lattice_veto_selectively():
    from semiconductor_bridge.interface_validator import SemiconductorInterfaceValidator

    validator = SemiconductorInterfaceValidator()
    inas_inp = validator.validate("InAs", "InP")
    inas_gap = validator.validate("InAs", "GaP")

    assert inas_inp.viable is True
    assert "lattice_veto_relaxed" in inas_inp.details
    assert inas_gap.viable is False


def test_q4_ceramic_failure_families_use_typed_morphisms():
    from ceramic_bridge.interface_validator import CeramicInterfaceValidator

    validator = CeramicInterfaceValidator()
    oxide_sulfide = validator.validate("LLZO", "Li3PS4")
    piezo_substrate = validator.validate("PZT", "Al2O3")

    assert oxide_sulfide.viable is False
    assert oxide_sulfide.total < 0.4
    assert oxide_sulfide.details["typed_morphism"]["morphism"]["relation"] == (
        "not_direct_solid_electrolyte_interface_with"
    )
    assert piezo_substrate.viable is True
    assert piezo_substrate.details["typed_morphism"]["morphism"]["relation"] == (
        "piezoelectric_ceramic_substrate_with"
    )


def test_q4_semiconductor_gan_sic_6h_uses_wide_bandgap_morphism():
    from semiconductor_bridge.interface_validator import SemiconductorInterfaceValidator

    validator = SemiconductorInterfaceValidator()
    result = validator.validate("GaN", "SiC_6H")

    assert result.viable is True
    assert result.total >= 0.7
    assert result.details["typed_morphism"]["morphism"]["relation"] == "wide_bandgap_epitaxy_with"


def test_q4_glass_bk7_fused_silica_is_optical_assembly_not_furnace_seal():
    from glass_bridge.interface_validator import GlassConditions, GlassInterfaceValidator

    validator = GlassInterfaceValidator()
    optical = validator.validate("BK7", "FusedSilica")
    furnace = validator.validate(
        "BK7",
        "FusedSilica",
        GlassConditions(environment="furnace", temperature_C=650),
    )

    assert optical.viable is True
    assert optical.details["typed_morphism"]["morphism"]["relation"] == "optical_glass_assembly_with"
    assert furnace.viable is False
