"""Staged D-light measurement: how does the Dempster-Shafer ensemble verdict
track the authoritative bridge verdict and ground truth on dev + Q9?

Throwaway measurement script (not part of the audit harness). Read-only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oracle.compatibility_context import CompatibilityContext
from oracle.compatibility_ensemble import build_compatibility_ensemble
from audit.run_audit import (
    _evaluate_pair,
    _load_development_compatibility_pairs,
    _load_external_blind_pairs,
)


def measure(name, pairs):
    n = bridge_correct = ds_correct = agree = skips = 0
    ds_flips_to_truth = ds_flips_from_truth = 0
    for pair in pairs:
        mat_a, mat_b = pair["material_a"], pair["material_b"]
        expected = bool(pair["expected_compatible"])
        domain = pair["domain"]
        context = CompatibilityContext.from_pair(pair)
        try:
            score, predicted = _evaluate_pair(
                mat_a, mat_b, domain, pair.get("electrolyte"), pair.get("role"), context
            )
        except Exception:
            skips += 1
            continue

        ens = build_compatibility_ensemble(
            mat_a, mat_b, domain, score, predicted, context
        ).to_dict()
        ds_compatible = bool(ens["compatible"])

        n += 1
        bridge_ok = predicted == expected
        ds_ok = ds_compatible == expected
        bridge_correct += bridge_ok
        ds_correct += ds_ok
        agree += (ds_compatible == predicted)
        if ds_compatible != predicted:
            if ds_ok and not bridge_ok:
                ds_flips_to_truth += 1
            elif bridge_ok and not ds_ok:
                ds_flips_from_truth += 1

    print(f"\n=== {name} ({n} evaluated, {skips} skipped) ===")
    if n:
        print(f"  Bridge (authoritative)  : {bridge_correct}/{n} = {bridge_correct/n:.1%}")
        print(f"  DS ensemble             : {ds_correct}/{n} = {ds_correct/n:.1%}")
        print(f"  DS agrees with bridge   : {agree}/{n} = {agree/n:.1%}")
        print(f"  DS flips that FIX a miss: {ds_flips_to_truth}")
        print(f"  DS flips that BREAK a hit: {ds_flips_from_truth}")


dev = _load_development_compatibility_pairs()[0]
measure("DEVELOPMENT", dev)

q9_path = Path("audit/external_blind/compatibility_2026_q9.json")
q9 = _load_external_blind_pairs(q9_path)[0]
measure("Q9 (spent diagnostic)", q9)
