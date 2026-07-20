"""Head-to-head: CHGNet MLIP vs the composition-only KOMPOSOS surrogate.

Both are scored against Materials Project PBE formation energies on the SAME
materials, so the comparison is like-for-like.

Structure sourcing -- the honest constraint. The local MP cache stores lattice
parameters and space groups but NOT atomic coordinates, so structures cannot be
reconstructed for arbitrary entries. This benchmark therefore uses only
prototypes that are FULLY DETERMINED by (space group, stoichiometry, lattice
constant), where every atom sits on a special position with no free internal
parameter:

    SG 225 (Fm-3m) + AB    -> rocksalt
    SG 216 (F-43m) + AB    -> zincblende
    SG 221 (Pm-3m) + AB    -> CsCl
    SG 225 (Fm-3m) + AB2   -> fluorite   (A2B -> antifluorite)
    SG 221 (Pm-3m) + ABC3  -> cubic perovskite

Prototypes with a free parameter (rutile u, wurtzite u, spinel u, corundum z)
are EXCLUDED rather than guessed -- inventing coordinates would fabricate the
input and make the comparison meaningless.

Elemental chemical potentials are FITTED on a train split and evaluated on a
disjoint test split (see --train-frac); the split is by material, seeded, and
reported.

Run:
    python audit/run_mlip_benchmark.py --json audit/mlip_benchmark_report.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_MP_CACHE = Path(__file__).resolve().parent.parent / "data" / "cache" / "materials_project" / "mp_summaries.json.gz"


def _build_structure(entry) -> Optional[object]:
    """Construct a structure ONLY for fully-determined prototypes, else None."""
    from pymatgen.core import Composition, Lattice, Structure

    sg = entry.get("space_group_number")
    a = entry.get("lattice_a")
    formula = entry.get("formula")
    if not sg or not a or not formula:
        return None
    # cubic only: a==b==c and all angles 90
    for k in ("lattice_b", "lattice_c"):
        if entry.get(k) is None or abs(entry[k] - a) > 1e-3:
            return None
    for k in ("lattice_alpha", "lattice_beta", "lattice_gamma"):
        if entry.get(k) is None or abs(entry[k] - 90.0) > 1e-3:
            return None

    try:
        comp = Composition(formula)
    except Exception:
        return None
    els = sorted(comp.element_composition, key=lambda e: str(e))
    counts = [comp.element_composition[e] for e in els]
    total = sum(counts)
    ratios = tuple(sorted(round(c / min(counts), 4) for c in counts))
    lat = Lattice.cubic(a)

    try:
        if len(els) == 2 and ratios == (1.0, 1.0):
            if sg == 225:   # rocksalt
                return Structure.from_spacegroup(
                    "Fm-3m", lat, [str(els[0]), str(els[1])],
                    [[0, 0, 0], [0.5, 0.5, 0.5]])
            if sg == 216:   # zincblende
                return Structure.from_spacegroup(
                    "F-43m", lat, [str(els[0]), str(els[1])],
                    [[0, 0, 0], [0.25, 0.25, 0.25]])
            if sg == 221:   # CsCl
                return Structure.from_spacegroup(
                    "Pm-3m", lat, [str(els[0]), str(els[1])],
                    [[0, 0, 0], [0.5, 0.5, 0.5]])
        if len(els) == 2 and ratios == (1.0, 2.0) and sg == 225:  # fluorite
            major = els[0] if comp.element_composition[els[0]] > comp.element_composition[els[1]] else els[1]
            minor = els[1] if major == els[0] else els[0]
            return Structure.from_spacegroup(
                "Fm-3m", lat, [str(minor), str(major)],
                [[0, 0, 0], [0.25, 0.25, 0.25]])
        if len(els) == 3 and sg == 221:  # cubic perovskite ABX3
            amt = {str(e): comp.element_composition[e] for e in els}
            x = [e for e in amt if abs(amt[e] / min(amt.values()) - 3.0) < 1e-3]
            if len(x) == 1:
                bx = x[0]
                rest = [e for e in amt if e != bx]
                if len(rest) == 2:
                    # A is the LARGER cation (12-coordinate corner site), B the
                    # smaller (6-coordinate octahedral centre). Assigning these
                    # alphabetically puts e.g. Hf on the A-site of KHfO3 and
                    # produces a physically wrong crystal.
                    from pymatgen.core.periodic_table import Element
                    def _radius(sym: str) -> float:
                        el = Element(sym)
                        r = el.atomic_radius or el.average_ionic_radius
                        return float(r) if r else 0.0
                    a_site, b_site = sorted(rest, key=_radius, reverse=True)
                    return Structure.from_spacegroup(
                        "Pm-3m", lat, [a_site, b_site, bx],
                        [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.0]])
    except Exception:
        return None
    return None


def _stats(errs: List[float]) -> Dict[str, float]:
    if not errs:
        return {"n": 0, "mae": 0.0, "rmse": 0.0, "median": 0.0}
    s = sorted(errs)
    return {
        "n": len(s),
        "mae": sum(s) / len(s),
        "rmse": (sum(e * e for e in s) / len(s)) ** 0.5,
        "median": s[len(s) // 2],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0,
                    help="max materials (0 = all constructible)")
    ap.add_argument("--train-frac", type=float, default=0.6)
    ap.add_argument("--relax", action="store_true",
                    help="relax structures with the MLIP before scoring (correct protocol)")
    ap.add_argument("--fmax", type=float, default=0.1)
    ap.add_argument("--relax-steps", type=int, default=100)
    ap.add_argument("--min-element-count", type=int, default=3,
                    help="minimum training materials an element must appear in "
                         "for its chemical potential to be identifiable")
    ap.add_argument("--seed", type=int, default=20260720)
    args = ap.parse_args()

    from oracle.mlip_integration import (
        backend_available, fit_elemental_potentials, predict_formation_energy,
        relax_structure, CHGNET_MPTRJ,
    )

    print("=" * 72)
    print("MLIP (CHGNet) vs composition-only surrogate -- formation energy")
    print("=" * 72)
    if not backend_available():
        print("\nNo MLIP backend installed (`pip install chgnet`). Nothing to run.")
        return 1

    print(f"\nLoading MP cache: {_MP_CACHE.name}")
    with gzip.open(_MP_CACHE, "rt", encoding="utf-8") as fh:
        entries = json.load(fh)
    print(f"  {len(entries)} MP entries")

    built = []
    for e in entries:
        if e.get("formation_energy_per_atom") is None:
            continue
        s = _build_structure(e)
        if s is not None:
            built.append((e, s))
    print(f"  {len(built)} have a FULLY DETERMINED constructible prototype")

    rng = random.Random(args.seed)
    rng.shuffle(built)
    if args.limit:
        built = built[: args.limit]
    n_train = int(len(built) * args.train_frac)
    train, test = built[:n_train], built[n_train:]
    print(f"  using {len(built)} (train {len(train)} / test {len(test)}), seed {args.seed}")

    # An elemental potential is only identifiable if that element appears in
    # enough training materials. With fewer training rows than elements the
    # normal equations are rank-deficient and the fitted mu are meaningless, so
    # under-covered elements are excluded rather than silently fitted to noise.
    from pymatgen.core import Composition
    el_counts: Dict[str, int] = {}
    for e, s in train:
        for el in {str(x) for x in Composition(e["formula"]).element_composition}:
            el_counts[el] = el_counts.get(el, 0) + 1
    covered = {el for el, c in el_counts.items() if c >= args.min_element_count}
    print(f"  elements in train: {len(el_counts)}; "
          f"covered (>={args.min_element_count} materials): {len(covered)}")

    train_ok = [(e, s) for e, s in train
                if {str(x) for x in Composition(e["formula"]).element_composition} <= covered]
    test_ok = [(e, s) for e, s in test
               if {str(x) for x in Composition(e["formula"]).element_composition} <= covered]
    print(f"  usable train {len(train_ok)}/{len(train)}, test {len(test_ok)}/{len(test)} "
          f"after coverage filter")
    if args.relax:
        print(f"\nRelaxing structures with the MLIP (fmax={args.fmax})...")
        def _relax_all(pairs, label):
            out = []
            for i, (e, s) in enumerate(pairs, 1):
                try:
                    rs, _ = relax_structure(s, fmax=args.fmax, steps=args.relax_steps)
                    out.append((e, rs))
                except Exception:
                    out.append((e, s))
                if i % 50 == 0:
                    print(f"    {label}: {i}/{len(pairs)}")
            return out
        train_ok = _relax_all(train_ok, "train")
        test_ok = _relax_all(test_ok, "test")
    if len(train_ok) < 2 * len(covered):
        print(f"  WARNING: {len(train_ok)} training rows for {len(covered)} unknowns "
              "-- fit may still be poorly conditioned")
    train, test = train_ok, test_ok

    print("\nFitting elemental chemical potentials on the TRAIN split only...")
    mu = fit_elemental_potentials([(s, e["formation_energy_per_atom"]) for e, s in train])
    print(f"  fitted {len(mu)} elemental potentials for {len(train)} training rows")

    # Train residual diagnoses WHERE a failure lives: a large train residual
    # means the structures/fit are wrong; a small train residual with a large
    # test error means extrapolation.
    tr_errs = []
    for e, s in train:
        try:
            r = predict_formation_energy(s, mu)
            tr_errs.append(abs(r.formation_energy_per_atom.value - float(e["formation_energy_per_atom"])))
        except Exception:
            pass
    tr = _stats(tr_errs)
    print(f"  TRAIN residual: MAE {tr['mae']:.3f}  median {tr['median']:.3f} (n={tr['n']})")

    print("\nEvaluating on the held-out TEST split...")
    mlip_errs, surr_errs, paired = [], [], []
    from composition_engine.formation_energy import FormationEnergyPredictor
    predictor = FormationEnergyPredictor(use_mp_cache=False)

    skipped_mlip = skipped_surr = 0
    for e, s in test:
        truth = float(e["formation_energy_per_atom"])
        formula = e["formula"]

        try:
            r = predict_formation_energy(s, mu)
            mlip_ef = r.formation_energy_per_atom.value
            mlip_err = abs(mlip_ef - truth)
        except Exception:
            skipped_mlip += 1
            continue

        try:
            sr = predictor.predict(formula, exclude_formula=formula)
            surr_ef = sr.ef_per_atom
            surr_err = abs(surr_ef - truth) if surr_ef is not None else None
        except Exception:
            surr_ef, surr_err = None, None
        if surr_err is None:
            skipped_surr += 1

        mlip_errs.append(mlip_err)
        if surr_err is not None:
            surr_errs.append(surr_err)
            paired.append((mlip_err, surr_err))
        rec = {"formula": formula, "mp_id": e.get("mp_id"), "truth": truth,
               "mlip_ef": mlip_ef, "mlip_abs_err": mlip_err,
               "surrogate_ef": surr_ef, "surrogate_abs_err": surr_err}
        if len(mlip_errs) <= 8:
            print(f"    {formula:14s} truth {truth:+.3f}  MLIP {mlip_ef:+.3f} "
                  f"(err {mlip_err:.3f})  surr "
                  + (f"{surr_ef:+.3f} (err {surr_err:.3f})" if surr_ef is not None else "n/a"))

    m = _stats(mlip_errs)
    su = _stats(surr_errs)
    pm = _stats([a for a, _ in paired])
    ps = _stats([b for _, b in paired])

    print("\n" + "-" * 72)
    print(f"{'model':34s} {'n':>5} {'MAE':>8} {'RMSE':>8} {'median':>8}")
    print("-" * 72)
    print(f"{'CHGNet MLIP (needs structure)':34s} {m['n']:5d} {m['mae']:8.3f} "
          f"{m['rmse']:8.3f} {m['median']:8.3f}")
    print(f"{'KOMPOSOS surrogate (formula only)':34s} {su['n']:5d} {su['mae']:8.3f} "
          f"{su['rmse']:8.3f} {su['median']:8.3f}")
    if paired:
        print(f"\nOn the {len(paired)} materials BOTH scored (like-for-like):")
        print(f"  CHGNet MLIP        MAE {pm['mae']:.3f}  RMSE {pm['rmse']:.3f}")
        print(f"  KOMPOSOS surrogate MAE {ps['mae']:.3f}  RMSE {ps['rmse']:.3f}")
        wins = sum(1 for a, b in paired if a < b)
        print(f"  MLIP closer on {wins}/{len(paired)} materials "
              f"({wins/len(paired):.1%})")
    print(f"\n  skipped: MLIP {skipped_mlip}, surrogate {skipped_surr}")

    print("\n" + "=" * 72)
    print("SCOPE: cubic fully-determined prototypes only (rocksalt, zincblende,")
    print("CsCl, fluorite, cubic perovskite). This is NOT the 179-material")
    print("formation-energy benchmark and must not be compared to its 0.416")
    print("eV/atom headline -- different materials, and the MLIP additionally")
    print("requires a structure the composition surrogate does not need.")
    print("=" * 72)

    if args.json:
        args.json.write_text(json.dumps({
            "benchmark": "mlip_vs_composition_surrogate_formation_energy",
            "level_of_theory": CHGNET_MPTRJ.label,
            "ground_truth": "Materials Project PBE formation_energy_per_atom",
            "structure_policy": "fully-determined cubic prototypes only; no invented coordinates",
            "seed": args.seed,
            "n_constructible": len(built),
            "n_train": len(train),
            "n_test": len(test),
            "mlip": m,
            "surrogate": su,
            "paired_mlip": pm,
            "paired_surrogate": ps,
            "paired_n": len(paired),
            "mlip_wins": sum(1 for a, b in paired if a < b),
            "skipped_mlip": skipped_mlip,
            "skipped_surrogate": skipped_surr,
            "scope_note": (
                "Cubic fully-determined prototypes only. NOT comparable to the "
                "179-material strict-LOO benchmark (0.416 eV/atom); different "
                "materials, and the MLIP requires a structure."
            ),
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
