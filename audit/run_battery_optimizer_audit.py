"""Battery optimizer audit (honest edition).

WHAT THE OPTIMIZER ACTUALLY OPTIMIZES: theoretical energy density (cathode
V * gravimetric capacity) after an above-threshold PARTIAL cross-domain screen. It does
NOT model cycle life, safety, thermal runaway, or cost -- those are not
computable from the data we have, so claiming them would be invented precision.
This audit therefore validates only what the objective IS, and is explicit about
what it is NOT. (Grounded safety/degradation RISK FLAGS could be added later as
constraints -- see the TODO markers below -- but never as invented numeric
targets.)

Because the real-world "best" commercial cell trades energy against safety/cost/
cycle life (e.g. LFP dominates on safety+cost despite low energy), the honest
tests are NOT "does it rank the exact commercial cell #1". They are:

  1. NO FALSE EXCLUSION ON COVERED INTERFACES: real, shipping commercial cells
     must remain in the shortlist. Missing native interface scorers prevent this
     from being a full-cell viability test.

  2. OBJECTIVE CORRECTNESS: energy_density == (V_cathode - V_anode) * capacity
     for every returned design (the objective is computed, not fudged), and the
     chemistry ordering is physically sane (Li-S / NMC-Si high; LFP / LTO low).

  3. CONSTRAINED PRESENCE (Hits@K): constrained to a commercial cell's chemistry
     palette, the real design appears in the above-threshold partial-score output.

  4. INVARIANTS: every returned design clears the partial-score threshold; ranking is monotone
     by the optimizer's own key; reported energy density is labelled THEORETICAL
     (cathode-active only), not cell-level.

Run: python audit/run_battery_optimizer_audit.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from battery_bridge.optimizer import BatteryOptimizer
from battery_bridge.material_properties import get_material
from cross_bridge.multi_domain import (
    MultiDomainAnalyzer, MultiDomainQuery, MultiDomainComponent, BATTERY_CELL_ADJACENCY,
)

# Known commercial / well-documented cell designs, components mapped to library
# names. Real cells are bimetallic: Al on the cathode collector, Cu on the anode.
# (cathode, anode, electrolyte, binder, cathode_collector, anode_collector,
#  cell_type, note)
COMMERCIAL_CELLS = [
    ("LFP",    "Graphite", "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "CATL/BYD LFP (EV, ESS)"),
    ("NMC811", "Graphite", "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "Modern NMC811 EV cell"),
    ("NCA",    "Graphite", "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "Panasonic/Tesla NCA 2170"),
    ("LCO",    "Graphite", "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "Consumer electronics LCO"),
    ("NMC622", "Graphite", "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "NMC622 EV cell"),
    ("LMO",    "LTO",      "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "LMO/LTO fast-charge"),
    ("NMC811", "Si",       "EC", "PVDF", "Al_foil", "Cu_foil", "liquid", "NMC811/Si-anode (high energy)"),
]

VIABILITY_THRESHOLD = 0.50


def _analyze(analyzer, cathode, anode, elec, binder, cath_col, anode_col):
    # Adjacency-aware bimetallic cell: cathode-side and anode-side collectors are
    # scored only against the components they physically touch.
    q = MultiDomainQuery(
        name=f"{cathode}+{elec}+{anode}",
        components=[
            MultiDomainComponent(name=cathode, role="cathode"),
            MultiDomainComponent(name=elec, role="electrolyte"),
            MultiDomainComponent(name=binder, role="binder"),
            MultiDomainComponent(name=cath_col, role="cathode_collector"),
            MultiDomainComponent(name=anode_col, role="anode_collector"),
            MultiDomainComponent(name=anode, role="anode"),
        ],
        electrolyte=elec,
        adjacency=BATTERY_CELL_ADJACENCY,
    )
    return analyzer.analyze(q)


def audit_no_false_veto():
    print("\n[1] NO FALSE EXCLUSION -- covered-interface score keeps commercial cells")
    analyzer = MultiDomainAnalyzer(viability_threshold=VIABILITY_THRESHOLD)
    passed = 0
    for cath, ano, elec, binder, ccol, acol, _ctype, note in COMMERCIAL_CELLS:
        a = _analyze(analyzer, cath, ano, elec, binder, ccol, acol)
        ok = a.overall_score >= VIABILITY_THRESHOLD
        passed += ok
        bn = a.bottleneck
        bn_s = f"{bn.component_a}-{bn.component_b} {bn.score:.2f}" if bn else "-"
        print(
            f"    [{'OK ' if ok else 'DROP'}] {note:32s} "
            f"partial_score={a.overall_score:.3f} coverage={a.coverage_fraction:.0%} "
            f"bottleneck={bn_s}"
        )
    n = len(COMMERCIAL_CELLS)
    print(f"    recall on commercial panel: {passed}/{n} = {passed / n:.3f}")
    # TODO(safety): a grounded thermal/dendrite RISK FLAG would annotate (not veto)
    # NCA/NMC at high SOC and Li-metal here -- citable facts, not invented scores.
    return passed == n


def audit_objective_correctness():
    print("\n[2] OBJECTIVE CORRECTNESS -- energy density = (V_c - V_a) * cap_c, sane order")
    o = BatteryOptimizer(viability_threshold=VIABILITY_THRESHOLD)
    res = o.optimize(fixed_components={"cell_type": "liquid"}, pfas_free_only=False,
                     enable_discovery=False, limit=99999)
    # Verify the energy-density formula on every Elite result.
    bad = 0
    for c in res:
        cat = get_material(c.cathode); ano = get_material(c.anode)
        v_c = cat.voltage_window.nominal if cat.voltage_window else 4.0
        v_a = ano.voltage_window.nominal if ano.voltage_window else 0.1
        cap = cat.theoretical_capacity or 200.0
        expected = (v_c - v_a) * cap
        if abs(expected - c.energy_density) > 1e-6:
            bad += 1
    print(f"    energy-density formula exact on {len(res)-bad}/{len(res)} returned designs")

    # Max theoretical energy density per cathode, computed ANALYTICALLY over all
    # anodes (independent of optimize()'s top-N truncation, which by design drops
    # low-energy chemistries like LFP). This isolates the objective ordering.
    anodes = o.anodes
    best = {}
    for cat in o.cathodes:
        v_c = cat.voltage_window.nominal if cat.voltage_window else 4.0
        cap = cat.theoretical_capacity or 200.0
        best_ed = max((v_c - (a.voltage_window.nominal if a.voltage_window else 0.1)) * cap
                      for a in anodes)
        best[cat.name] = best_ed
    order = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    print("    max theoretical Wh/kg by cathode (cathode-active basis):")
    for name, ed in order:
        print(f"       {name:8s} {ed:7.0f}")
    # Physically sane: Li-S (S8) highest; LFP below the NMC family.
    cathodes_ranked = [n for n, _ in order]
    sane = (cathodes_ranked[0] == "S8") and (
        cathodes_ranked.index("LFP") > cathodes_ranked.index("NMC811")
    )
    print(f"    ordering sane (S8 top; LFP below NMC811): {sane}")
    return bad == 0 and sane


def audit_constrained_hits():
    print("\n[3] CONSTRAINED PRESENCE (Hits@K) -- real design in partial-score output")
    o = BatteryOptimizer(viability_threshold=VIABILITY_THRESHOLD)
    hits = 0
    checked = 0
    for cath, ano, elec, binder, ccol, acol, ctype, note in COMMERCIAL_CELLS:
        res = o.optimize(
            fixed_components={"cell_type": ctype, "cathode": cath, "electrolyte": elec},
            pfas_free_only=False, enable_discovery=False, limit=99999,
        )
        found = any(
            c.cathode == cath and c.anode == ano and c.binder == binder
            and c.cathode_collector == ccol and c.anode_collector == acol
            for c in res
        )
        checked += 1
        hits += found
        print(f"    [{'HIT ' if found else 'MISS'}] {note:32s} (shortlisted designs for {cath}/{elec}: {len(res)})")
    print(f"    constrained recall: {hits}/{checked} = {hits / checked:.3f}")
    return hits == checked


def audit_invariants():
    print("\n[4] INVARIANTS")
    o = BatteryOptimizer(viability_threshold=VIABILITY_THRESHOLD)
    res = o.optimize(fixed_components={"cell_type": "liquid"}, pfas_free_only=True,
                     enable_discovery=False, limit=50)
    below = [c for c in res if c.viability < VIABILITY_THRESHOLD]
    falsely_complete = [c for c in res if c.interface_coverage >= 1.0 and c.unscored_interfaces]
    ranks_ok = [c.rank for c in res] == list(range(1, len(res) + 1))
    # ranking key: viable boost + energy density, then viability
    key = lambda c: (1000 + c.energy_density if c.viability >= VIABILITY_THRESHOLD else c.energy_density, c.viability)
    monotone = all(key(res[i]) >= key(res[i + 1]) for i in range(len(res) - 1))
    print(f"    none below threshold:   {not below}")
    print(f"    ranks are 1..N:         {ranks_ok}")
    print(f"    monotone by rank key:   {monotone}")
    print(f"    coverage fields agree:  {not falsely_complete}")
    if res:
        print(f"    top interface coverage: {res[0].interface_coverage:.0%} (partial)")
    print("    NOTE: energy density is THEORETICAL (cathode-active V*C); real")
    print("          cell-level Wh/kg is ~40-55% of this after anode+packaging.")
    return (not below) and ranks_ok and monotone and (not falsely_complete)


def main():
    print("=" * 66)
    print("BATTERY OPTIMIZER AUDIT (honest edition)")
    print("=" * 66)
    print("Objective = theoretical energy density after a covered-interface screen.")
    print("NOT modeled: cycle life, safety, thermal, cost. Tests validate the")
    print("objective + that real commercial cells are not excluded by covered interfaces.")
    print("Missing native scorers mean this audit emits no full-cell viability claim.")

    r1 = audit_no_false_veto()
    r2 = audit_objective_correctness()
    r3 = audit_constrained_hits()
    r4 = audit_invariants()

    print("\n" + "=" * 66)
    print("SUMMARY")
    print(f"  No false exclusion on covered interfaces: {'YES' if r1 else 'NO'}")
    print(f"  Objective correct + sane ordering: {'YES' if r2 else 'NO'}")
    print(f"  Constrained Hits@K (real present): {'YES' if r3 else 'NO'}")
    print(f"  Invariants hold:                   {'YES' if r4 else 'NO'}")
    print("=" * 66)


if __name__ == "__main__":
    main()
