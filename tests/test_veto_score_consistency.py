"""A vetoed pair must never surface a score that outranks a viable one.

The bug this pins: several bridges set `viable = False` on a physical veto but
left `total` untouched, so the surfaced number contradicted the decision shown
next to it (Ni+Fe scored 0.721 -> incompatible while Al+Fe scored 0.674 ->
compatible). Beyond being confusing, it is a calibration failure: a high raw
score attached to an incompatible verdict is exactly what a calibrator cannot fit.

The rule, already documented for the MOF/polymer vetoes, is that a physical block
survives composition (min/annihilator) rather than being diluted by a weighted
sum -- and that includes the reported score.
"""

from __future__ import annotations

import pytest

BRIDGES = [
    ("metal_bridge.interface_validator", "MetalInterfaceValidator"),
    ("ceramic_bridge.interface_validator", "CeramicInterfaceValidator"),
    ("glass_bridge.interface_validator", "GlassInterfaceValidator"),
    ("semiconductor_bridge.interface_validator", "SemiconductorInterfaceValidator"),
    ("battery_bridge.interface_validator", "BatteryInterfaceValidator"),
    ("polymer_bridge.interface_validator", "PolymerInterfaceValidator"),
]


@pytest.mark.parametrize("module_name,cls_name", BRIDGES)
def test_veto_cap_is_below_viability_threshold(module_name, cls_name):
    """Whatever cap a bridge uses on veto must sit below its own threshold."""
    import importlib
    mod = importlib.import_module(module_name)
    cls = getattr(mod, cls_name)
    threshold = cls().viability_threshold
    cap = getattr(mod, "VETO_SCORE_CAP", None)
    if cap is None:
        pytest.skip(f"{module_name} caps inline rather than via VETO_SCORE_CAP")
    assert cap < threshold, (
        f"{module_name}.VETO_SCORE_CAP={cap} is not below viability_threshold="
        f"{threshold}; a vetoed pair could still be reported as viable-looking"
    )


def test_metal_veto_annihilates_score():
    """Ni+Fe is vetoed; its score must reflect that, not stay high."""
    from metal_bridge.interface_validator import (
        MetalInterfaceValidator, VETO_SCORE_CAP,
    )
    v = MetalInterfaceValidator()
    r = v.validate("Ni", "Fe")
    if r.viable:
        pytest.skip("Ni+Fe is not vetoed in this configuration")
    assert r.total <= VETO_SCORE_CAP + 1e-9, (
        f"vetoed pair surfaced score {r.total:.3f} above the veto cap"
    )
    assert r.total < v.viability_threshold


def test_no_inversion_between_a_vetoed_and_a_viable_metal_pair():
    """The concrete inversion that motivated this: Ni+Fe vs Al+Fe."""
    from metal_bridge.interface_validator import MetalInterfaceValidator
    v = MetalInterfaceValidator()
    ni_fe = v.validate("Ni", "Fe")
    al_fe = v.validate("Al", "Fe")
    for r in (ni_fe, al_fe):
        if r.viable:
            assert r.total >= v.viability_threshold
        else:
            assert r.total < v.viability_threshold
    if not ni_fe.viable and al_fe.viable:
        assert ni_fe.total < al_fe.total, (
            "a vetoed pair outranks a viable one: the surfaced score contradicts "
            "the verdict"
        )


def test_corpus_has_no_score_verdict_inversions():
    """Across dev + spent diagnostics, no incompatible pair may outrank a compatible one."""
    from audit import run_audit as RA
    from audit.run_ct_ablation import _load_pairs

    pairs, _ = _load_pairs()
    viable_scores, vetoed_scores = [], []
    for p in pairs:
        try:
            ctx = RA.CompatibilityContext.from_pair(p)
            score, pred = RA._evaluate_pair(
                p["material_a"], p["material_b"], p.get("domain", ""),
                p.get("electrolyte"), p.get("role"), ctx)
        except Exception:
            continue
        (viable_scores if pred else vetoed_scores).append(float(score))

    assert viable_scores and vetoed_scores, "corpus produced no usable predictions"
    assert max(vetoed_scores) < min(viable_scores), (
        f"score/verdict inversion: highest incompatible score "
        f"{max(vetoed_scores):.3f} >= lowest compatible score {min(viable_scores):.3f}"
    )
