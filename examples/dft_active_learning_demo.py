# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
End-to-end demo: level-of-theory typing + DFT terminal oracle, wired to the
REAL KOMPOSOS formation-energy surrogate.

It shows the three load-bearing pieces working against existing code:

1.  Surrogate predictions are tagged ``surrogate:kan+miedema`` and therefore
    *cannot* be silently combined with a DFT or experimental number.
2.  Active learning picks the predictions where the surrogate is least
    trustworthy (sparse discovery / large error) -- the materials where a real
    DFT calculation buys the most.
3.  The DFT oracle either runs (if pyscf/psi4 is installed) or fails *honestly*
    with OracleUnavailable -- it never fabricates a DFT number.

Run:  python -m examples.dft_active_learning_demo
"""

from __future__ import annotations

from composition_engine.formation_energy import FormationEnergyPredictor
from core.errors import OracleUnavailable, TheoryCompositionError
from core.level_of_theory import (
    PBE_MP, Provenance, TypedQuantity, from_formation_energy_result,
)
from oracle import dft_integration as dft


def rule(c: str = "-") -> None:
    print(c * 72)


def main() -> None:
    predictor = FormationEnergyPredictor()

    # A mix: well-known (confident) and deliberately novel (sparse-discovery).
    formulas = ["LiCoO2", "LiNi0.8Mn0.1Co0.1O2", "Na2Mn3O7", "K2FeSiO4", "LiZnPO4F"]

    rule("=")
    print("1) SURROGATE PREDICTIONS, TAGGED WITH LEVEL OF THEORY")
    rule("=")
    results = []
    for f in formulas:
        r = predictor.predict(f)
        results.append(r)
        tq = from_formation_energy_result(r)
        print(f"  {f:24s}  {tq}")

    rule("=")
    print("2) LEVEL-OF-THEORY GUARD (the new safety net)")
    rule("=")
    surrogate_tq = from_formation_energy_result(results[0])
    fake_dft = TypedQuantity(-1.58, "eV/atom", PBE_MP, Provenance.COMPUTATIONAL)
    print(f"  surrogate: {surrogate_tq}")
    print(f"  dft      : {fake_dft}")
    try:
        _ = surrogate_tq - fake_dft
        print("  [!] combination unexpectedly allowed")
    except TheoryCompositionError as e:
        print(f"  refused to subtract across levels -> {type(e).__name__}")
        print("    (this is the point: no silent surrogate-vs-DFT mixing)")

    rule("=")
    print("3) ACTIVE LEARNING: where is a DFT calculation worth spending?")
    rule("=")
    picks = dft.select_for_dft(results, max_picks=5, error_floor_eV=0.10)
    if not picks:
        print("  (every prediction is confident; no DFT needed)")
    for i, c in enumerate(picks, 1):
        print(f"  {i}. {c.formula:24s} tier={c.tier:24s} "
              f"err={c.error_estimate_eV:.3f} eV  priority={c.priority:.3f}")

    rule("=")
    print("4) DFT TERMINAL ORACLE (honest about availability)")
    rule("=")
    print(f"  backends detected: {dft.available_backends() or 'none'}")
    shortlist_smiles = ["c1ccccc1C(=O)O", "OC(=O)c1ccc(cc1)C(=O)O"]  # benzoic, terephthalic
    try:
        verdicts = dft.verify_candidates(shortlist_smiles, top_n=2)
        for v in verdicts:
            print(f"  {v.smiles}: ok={v.ok} {v.result.total_energy if v.result else v.error}")
    except OracleUnavailable as e:
        print(f"  OracleUnavailable -> {e.reason}")
        print(f"    remediation: {e.remediation}")
        print("    (correct behaviour: no fabricated DFT number is returned)")


if __name__ == "__main__":
    main()
