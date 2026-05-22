# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Bulk Composition Screening — Generate hundreds of compositions, predict
properties, check against known materials, rank novel candidates.

This demonstrates KOMPOSOS as a high-throughput compositional screener:
scan composition space via Kan extension + D-S fusion + ZFC constraints
in seconds rather than hours of DFT compute.

Comparison to competitors:
- CuspAI: Generates 3D structures via GenAI + DFT validation. We predict
  properties + synthesizability WITHOUT 3D structure or DFT.
- GNoME (DeepMind): GNN-predicted 2.2M crystals. We use categorical
  extrapolation, not neural networks.
- Our niche: ultra-fast compositional screening to identify WHICH
  compositions are worth expensive DFT/experiment.

Output: showcase/outputs/bulk_screen_results.csv
"""

import csv
import sys
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from composition_engine.predictor import CompositionPredictor
from composition_engine.formation_energy import FormationEnergyPredictor, KNOWN_EF
from composition_engine.structure_predictor import StructureTypePredictor
from composition_engine.parser import parse_formula, composition_distance, SHORTHAND_MAP
from composition_engine.known_compositions import get_db


# ═══════════════════════════════════════════════════════════════════════════
# COMPOSITION GENERATORS — systematic grid over composition space
# ═══════════════════════════════════════════════════════════════════════════

def generate_nmc_grid(step: float = 0.1) -> List[Tuple[str, str]]:
    """
    Generate NMC cathode grid: LiNi_xMn_yCo_zO2 where x+y+z=1.
    Returns list of (label, formula).
    """
    compositions = []
    ni_vals = [round(v, 2) for v in _frange(0.1, 0.95, step)]
    for ni in ni_vals:
        mn_max = round(1.0 - ni, 2)
        mn_vals = [round(v, 2) for v in _frange(0.0, mn_max + 0.001, step)]
        for mn in mn_vals:
            co = round(1.0 - ni - mn, 2)
            if co < -0.001 or co > 1.001:
                continue
            co = max(0.0, co)
            if ni + mn + co < 0.99 or ni + mn + co > 1.01:
                continue
            label = f"NMC-Ni{ni:.2f}Mn{mn:.2f}Co{co:.2f}"
            formula = f"LiNi{ni}Mn{mn}Co{co}O2"
            compositions.append((label, formula))
    return compositions


def generate_nca_variants() -> List[Tuple[str, str]]:
    """NCA cathode variants: LiNi_xCo_yAl_zO2."""
    compositions = []
    for ni in [0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
        for al in [0.02, 0.05, 0.08, 0.10, 0.15]:
            co = round(1.0 - ni - al, 2)
            if co < 0:
                continue
            label = f"NCA-Ni{ni:.2f}Co{co:.2f}Al{al:.2f}"
            formula = f"LiNi{ni}Co{co}Al{al}O2"
            compositions.append((label, formula))
    return compositions


def generate_olivine_variants() -> List[Tuple[str, str]]:
    """Olivine phosphate variants: LiM_xFe_(1-x)PO4."""
    compositions = []
    metals = {"Mn": "Mn", "Co": "Co", "Ni": "Ni"}
    for metal_name, metal_sym in metals.items():
        for x in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            fe = round(1.0 - x, 2)
            label = f"Olivine-{metal_name}{x:.1f}Fe{fe:.1f}"
            if x == 0:
                formula = "LiFePO4"
            elif fe == 0:
                formula = f"Li{metal_sym}PO4"
            else:
                formula = f"Li{metal_sym}{x}Fe{fe}PO4"
            compositions.append((label, formula))
    return compositions


def generate_spinel_variants() -> List[Tuple[str, str]]:
    """Spinel variants: LiNi_xMn_(2-x)O4."""
    compositions = []
    for x in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        mn = round(2.0 - x, 2)
        label = f"Spinel-Ni{x:.1f}Mn{mn:.1f}"
        formula = f"LiNi{x}Mn{mn}O4"
        compositions.append((label, formula))
    return compositions


def generate_li_rich_nmc() -> List[Tuple[str, str]]:
    """Li-rich layered cathodes: Li_(1+d)Ni_xMn_yCo_zO2 where d > 0."""
    compositions = []
    for li_excess in [0.1, 0.2, 0.3]:
        li = round(1.0 + li_excess, 2)
        for ni in [0.2, 0.3, 0.4, 0.5]:
            for mn in [0.3, 0.4, 0.5]:
                co = round(1.0 - ni - mn, 2)
                if co < 0:
                    continue
                label = f"LiRich-Li{li:.1f}Ni{ni:.1f}Mn{mn:.1f}Co{co:.1f}"
                formula = f"Li{li}Ni{ni}Mn{mn}Co{co}O2"
                compositions.append((label, formula))
    return compositions


def _frange(start, stop, step):
    """Float range generator."""
    vals = []
    v = start
    while v <= stop + step * 0.01:
        vals.append(round(v, 4))
        v += step
    return vals


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN MATERIAL MATCHING
# ═══════════════════════════════════════════════════════════════════════════

def find_closest_known(formula: str, db, fe_db: List) -> Tuple[str, float, Optional[float]]:
    """Find the closest known material to a given formula."""
    comp = parse_formula(formula)

    # Check composition DB
    nearest = db.nearest_k(comp, k=1)
    if nearest:
        entry, dist = nearest[0]
        return entry.name, dist, None

    return "none", 999.0, None


def is_rediscovery(formula: str, db, threshold: float = 0.05) -> Tuple[bool, str, float]:
    """Check if this formula essentially matches a known material."""
    comp = parse_formula(formula)
    nearest = db.nearest_k(comp, k=1)
    if nearest:
        entry, dist = nearest[0]
        return dist < threshold, entry.name, dist
    return False, "none", 999.0


# ═══════════════════════════════════════════════════════════════════════════
# MAIN SCREENING PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 78)
    print("KOMPOSOS-III Bulk Composition Screener")
    print("Categorical property prediction over composition space")
    print("=" * 78)

    predictor = CompositionPredictor()
    fep = FormationEnergyPredictor()
    stp = StructureTypePredictor()
    db = get_db()

    # Generate all compositions
    print("\nGenerating composition grid...")
    all_compositions = []
    families = {
        "NMC layered": generate_nmc_grid(step=0.1),
        "NCA layered": generate_nca_variants(),
        "Olivine phosphate": generate_olivine_variants(),
        "Spinel": generate_spinel_variants(),
        "Li-rich layered": generate_li_rich_nmc(),
    }

    for family, comps in families.items():
        print(f"  {family}: {len(comps)} compositions")
        for label, formula in comps:
            all_compositions.append((family, label, formula))

    print(f"\nTotal compositions to screen: {len(all_compositions)}")

    # Screen all compositions
    print("\nScreening...")
    t0 = time.time()

    results = []
    n_stable = 0
    n_rediscovery = 0
    n_novel_promising = 0

    for i, (family, label, formula) in enumerate(all_compositions):
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{len(all_compositions)} ({rate:.1f} compositions/sec)")

        try:
            # Property prediction
            pred = predictor.predict(formula)

            # Formation energy
            fe_result = fep.predict(formula)

            # Structure type prediction
            struct_result = stp.predict(formula)

            # Rediscovery check
            is_known, known_name, known_dist = is_rediscovery(formula, db)

            # Extract key properties
            voltage = pred.properties.get("voltage")
            capacity = pred.properties.get("theoretical_capacity")
            thermal = pred.properties.get("thermal_stability")
            formation_e = fe_result.ef_per_atom
            synth_score = fe_result.synthesizability_score
            is_stable = fe_result.is_stable

            # ZFC constraint summary
            n_constraints = len(fe_result.constraints)
            n_satisfied = sum(1 for c in fe_result.constraints if c.satisfied)

            if is_stable:
                n_stable += 1
            if is_known:
                n_rediscovery += 1
            if is_stable and not is_known and synth_score > 0.7:
                n_novel_promising += 1

            # Nearest known materials
            nearest_3 = pred.nearest_known[:3]
            nearest_str = "; ".join(f"{n}({d:.3f})" for n, d in nearest_3)

            results.append({
                "family": family,
                "label": label,
                "formula": formula,
                "structure_type": struct_result.predicted_type,
                "structure_conf": f"{struct_result.confidence:.2f}",
                "voltage_V": f"{voltage.value:.3f}" if voltage else "",
                "voltage_conf": f"{voltage.confidence:.2f}" if voltage else "",
                "capacity_mAh_g": f"{capacity.value:.1f}" if capacity else "",
                "capacity_conf": f"{capacity.confidence:.2f}" if capacity else "",
                "thermal_C": f"{thermal.value:.0f}" if thermal else "",
                "formation_energy_eV": f"{formation_e:.3f}",
                "fe_confidence": f"{fe_result.confidence:.2f}",
                "is_stable": is_stable,
                "synthesizability": f"{synth_score:.3f}",
                "zfc_satisfied": f"{n_satisfied}/{n_constraints}",
                "is_rediscovery": is_known,
                "closest_known": known_name,
                "closest_distance": f"{known_dist:.4f}",
                "nearest_3": nearest_str,
            })

        except Exception as e:
            results.append({
                "family": family,
                "label": label,
                "formula": formula,
                "structure_type": "",
                "structure_conf": "",
                "voltage_V": "ERROR",
                "voltage_conf": "",
                "capacity_mAh_g": "",
                "capacity_conf": "",
                "thermal_C": "",
                "formation_energy_eV": "",
                "fe_confidence": "",
                "is_stable": False,
                "synthesizability": "",
                "zfc_satisfied": "",
                "is_rediscovery": False,
                "closest_known": "",
                "closest_distance": "",
                "nearest_3": str(e)[:60],
            })

    elapsed = time.time() - t0

    # ── Summary statistics ─────────────────────────────────────────────
    print(f"\n{'=' * 78}")
    print(f"SCREENING COMPLETE in {elapsed:.1f}s ({len(results)/elapsed:.1f} compositions/sec)")
    print(f"{'=' * 78}")
    print(f"  Total screened:        {len(results)}")
    print(f"  Predicted stable:      {n_stable} ({100*n_stable/len(results):.1f}%)")
    print(f"  Rediscoveries:         {n_rediscovery} (match known materials)")
    print(f"  Novel + promising:     {n_novel_promising} (stable, synth>0.7, not known)")
    print(f"  Predicted unstable:    {len(results) - n_stable}")

    # Structure type distribution
    struct_counts = {}
    for r in results:
        st = r.get("structure_type", "")
        if st:
            struct_counts[st] = struct_counts.get(st, 0) + 1
    print(f"\n  Structure type distribution:")
    for st, count in sorted(struct_counts.items(), key=lambda x: -x[1]):
        print(f"    {st:<18s} {count:>4d} ({100*count/len(results):.1f}%)")

    # ── Top novel candidates ───────────────────────────────────────────
    novel = [r for r in results
             if not r["is_rediscovery"] and r["is_stable"]
             and r["synthesizability"] and r["voltage_V"]
             and r["voltage_V"] != "ERROR"]
    novel.sort(key=lambda r: float(r["synthesizability"]), reverse=True)

    print(f"\n{'-' * 95}")
    print("TOP 20 NOVEL CANDIDATES (by synthesizability)")
    print(f"{'-' * 95}")
    print(f"{'Label':<30s} {'Structure':<14s} {'V(V)':>6s} {'Cap':>6s} {'Ef(eV)':>8s} {'Synth':>6s} {'ZFC':>5s} {'Nearest':<15s}")
    for r in novel[:20]:
        print(f"{r['label']:<30s} {r['structure_type']:<14s} {r['voltage_V']:>6s} "
              f"{r['capacity_mAh_g']:>6s} {r['formation_energy_eV']:>8s} "
              f"{r['synthesizability']:>6s} {r['zfc_satisfied']:>5s} "
              f"{r['closest_known']:<15s}")

    # ── Rediscoveries (validation) ─────────────────────────────────────
    rediscoveries = [r for r in results if r["is_rediscovery"]]
    print(f"\n{'-' * 95}")
    print(f"REDISCOVERIES ({len(rediscoveries)} compositions match known materials)")
    print(f"{'-' * 95}")
    print(f"{'Label':<30s} {'Structure':<14s} {'Matched':<12s} {'Dist':>6s} {'V(V)':>6s} {'Ef(eV)':>8s} {'Synth':>6s}")
    for r in rediscoveries[:20]:
        print(f"{r['label']:<30s} {r['structure_type']:<14s} {r['closest_known']:<12s} "
              f"{r['closest_distance']:>6s} {r['voltage_V']:>6s} "
              f"{r['formation_energy_eV']:>8s} {r['synthesizability']:>6s}")

    # ── Unstable / rejected compositions ───────────────────────────────
    unstable = [r for r in results
                if not r["is_stable"] and r["formation_energy_eV"]
                and r["formation_energy_eV"] != "ERROR"]
    print(f"\n{'-' * 78}")
    print(f"UNSTABLE / REJECTED ({len(unstable)} compositions)")
    print(f"{'-' * 78}")
    if unstable:
        for r in unstable[:10]:
            print(f"  {r['label']:<35s} Ef={r['formation_energy_eV']:>8s} eV/atom  "
                  f"ZFC: {r['zfc_satisfied']}")

    # ── Write CSV ──────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "bulk_screen_results.csv")

    fieldnames = [
        "family", "label", "formula", "structure_type", "structure_conf",
        "voltage_V", "voltage_conf",
        "capacity_mAh_g", "capacity_conf", "thermal_C",
        "formation_energy_eV", "fe_confidence", "is_stable",
        "synthesizability", "zfc_satisfied", "is_rediscovery",
        "closest_known", "closest_distance", "nearest_3",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to: {csv_path}")

    # ── Comparison to CuspAI / GNoME ──────────────────────────────────
    print(f"\n{'=' * 78}")
    print("COMPARISON TO AI MATERIALS DISCOVERY PLATFORMS")
    print(f"{'=' * 78}")
    print(f"""
  KOMPOSOS-III (this run):
    - Screened {len(results)} compositions in {elapsed:.1f}s
    - Found {n_novel_promising} novel promising candidates
    - Method: Kan extension + D-S fusion + ZFC constraints
    - Output: properties + synthesizability (NO 3D structure)
    - Cost: ~0 (pure computation, no GPU/DFT needed)

  CuspAI (for comparison):
    - Generates 3D crystal structures via diffusion models
    - Validates with actual DFT (hours per structure)
    - Output: full 3D atom positions + DFT-validated energy
    - Cost: significant GPU + DFT compute
    - What they don't do: multi-domain compatibility reasoning

  GNoME (DeepMind, 2023):
    - Graph neural network on 2.2M predicted crystals
    - Validated ~380K as stable via DFT
    - Output: crystal structures with predicted stability
    - What they don't do: compositional reasoning, property fusion

  WHERE KOMPOSOS FITS:
    KOMPOSOS is a SCREENING LAYER that sits BEFORE expensive compute.
    Use it to identify which compositions are worth DFT/experiment,
    then feed promising candidates to CuspAI/GNoME-style tools for
    3D structure prediction and validation.

    Think of it as: KOMPOSOS screens 1000s -> CuspAI validates 10s
""")


if __name__ == "__main__":
    main()
