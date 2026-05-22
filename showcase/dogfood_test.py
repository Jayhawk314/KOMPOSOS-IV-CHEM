# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Dogfood Test -- Use KOMPOSOS the way a real user would.

Instead of unit tests, this asks REAL materials science questions and
checks whether the answers are correct against published literature.

Each test is a question a battery engineer or materials scientist
might actually ask. Pass = the system gives the right answer.

Published reference data:
- Manthiram, Nature Comm. 11, 1550 (2020) -- NMC cathode properties
- Nitta et al., Materials Today 18, 252 (2015) -- Li-ion cathode overview
- Xu, Chem. Rev. 104, 4303 (2004) -- electrolyte review
- Bresser et al., EES 11, 3096 (2018) -- aqueous binders
- EU REACH PFAS restriction proposal (2023)
- Yaghi et al., Nature 2003 -- MOF-5 (DOI: 10.1038/nature01650)
- Cavka et al., JACS 2008 -- UiO-66 family (DOI: 10.1021/ja8057953)
- Park et al., PNAS 2006 -- ZIF-8 (DOI: 10.1073/pnas.0602439103)
- Kulik, Nature Comp. Sci. 2022 -- "design me a ligand with exactly 22 heavy atoms"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def p(status, question, detail=""):
    """Print a test result."""
    icon = "PASS" if status else "FAIL"
    print(f"  [{icon}] {question}")
    if detail:
        print(f"         {detail}")
    return status


def main():
    passed = 0
    failed = 0
    total = 0

    def check(ok, question, detail=""):
        nonlocal passed, failed, total
        total += 1
        if p(ok, question, detail):
            passed += 1
        else:
            failed += 1

    print("=" * 78)
    print("KOMPOSOS-III DOGFOOD TEST")
    print("Real materials questions with known-correct answers")
    print("=" * 78)

    # ===================================================================
    # SECTION 1: "What properties does this cathode have?"
    # Composition engine predictions vs published literature
    # ===================================================================
    print("\n--- SECTION 1: Property Prediction vs Published Data ---\n")

    from composition_engine.predictor import CompositionPredictor
    pred = CompositionPredictor()

    # Q1: NMC811 voltage should be ~3.8V (Manthiram 2020: 3.7-3.8V avg)
    r = pred.predict("NMC811")
    v = r.properties.get("voltage")
    check(v and 3.6 <= v.value <= 4.0,
          "NMC811 voltage ~ 3.8V?",
          f"Got {v.value:.2f}V (published: 3.7-3.8V)")

    # Q2: LFP voltage should be ~3.4V (Padhi 1997: 3.45V)
    r = pred.predict("LFP")
    v = r.properties.get("voltage")
    check(v and 3.2 <= v.value <= 3.6,
          "LFP voltage ~ 3.4V?",
          f"Got {v.value:.2f}V (published: 3.45V)")

    # Q3: NMC811 should have higher voltage than LFP
    r811 = pred.predict("NMC811")
    rlfp = pred.predict("LFP")
    v811 = r811.properties["voltage"].value
    vlfp = rlfp.properties["voltage"].value
    check(v811 > vlfp,
          "NMC811 voltage > LFP voltage?",
          f"NMC811={v811:.2f}V > LFP={vlfp:.2f}V")

    # Q4: NMC532 (not in DB) should predict ~3.7V (published: 3.6-3.7V)
    r = pred.predict("NMC532")
    v = r.properties.get("voltage")
    check(v and 3.5 <= v.value <= 4.0,
          "NMC532 (novel) voltage ~ 3.7V?",
          f"Got {v.value:.2f}V (published: 3.6-3.7V)")

    # Q5: All NMC cathodes should have similar voltage (~3.7-3.9V)
    # Literature: NMC111=3.8V, NMC622=3.8V, NMC811=3.8V -- nearly identical avg voltages
    # (Voltage profiles differ in shape, but avg is similar across NMC family)
    r111 = pred.predict("NMC111")
    r622 = pred.predict("NMC622")
    r811 = pred.predict("NMC811")
    v111 = r111.properties["voltage"].value
    v622 = r622.properties["voltage"].value
    v811 = r811.properties["voltage"].value
    all_in_range = all(3.6 <= v <= 4.1 for v in [v111, v622, v811])
    spread = max(v111, v622, v811) - min(v111, v622, v811)
    check(all_in_range and spread < 0.3,
          "All NMC voltages in 3.6-4.1V, spread < 0.3V?",
          f"111={v111:.3f}, 622={v622:.3f}, 811={v811:.3f}, spread={spread:.3f}V")

    # Q6: LMO (spinel) should have ~4.0V (published: 4.0-4.1V avg)
    r = pred.predict("LMO")
    v = r.properties.get("voltage")
    check(v and 3.8 <= v.value <= 4.3,
          "LMO spinel voltage ~ 4.0V?",
          f"Got {v.value:.2f}V (published: 4.0-4.1V)")

    # ===================================================================
    # SECTION 2: "Is this material thermodynamically stable?"
    # Formation energy + synthesizability
    # ===================================================================
    print("\n--- SECTION 2: Stability & Synthesizability ---\n")

    from composition_engine.formation_energy import FormationEnergyPredictor
    fep = FormationEnergyPredictor()

    # Q7: NMC811 should be stable (Ef < 0)
    fe = fep.predict("NMC811")
    check(fe.is_stable and fe.ef_per_atom < -1.0,
          "NMC811 thermodynamically stable?",
          f"Ef={fe.ef_per_atom:.2f} eV/atom, synth={fe.synthesizability_score:.2f}")

    # Q8: LFP should be MORE stable than NMC811 (olivine very robust)
    fe_lfp = fep.predict("LFP")
    fe_811 = fep.predict("NMC811")
    check(fe_lfp.ef_per_atom < fe_811.ef_per_atom,
          "LFP more stable than NMC811?",
          f"LFP Ef={fe_lfp.ef_per_atom:.2f} < NMC811 Ef={fe_811.ef_per_atom:.2f}")

    # Q9: LLZO garnet should be very stable (Ef ~ -2.85)
    fe = fep.predict("LLZO")
    check(fe.is_stable and fe.ef_per_atom < -2.0,
          "LLZO garnet very stable (Ef < -2.0)?",
          f"Ef={fe.ef_per_atom:.2f} eV/atom")

    # Q10: Higher Ni -> less stable (more positive Ef)
    ef111 = fep.predict("NMC111").ef_per_atom
    ef811 = fep.predict("NMC811").ef_per_atom
    check(ef111 < ef811,
          "NMC111 more stable than NMC811 (higher Ni = less stable)?",
          f"NMC111 Ef={ef111:.2f} < NMC811 Ef={ef811:.2f}")

    # Q11: Li+Na mixing should be flagged as problematic
    fe = fep.predict("Li0.5Na0.5CoO2")
    compat = [c for c in fe.constraints if c.name == "element_compatibility"]
    check(len(compat) > 0 and not compat[0].satisfied,
          "Li+Na mixing flagged as incompatible?",
          f"Found {len(compat)} compatibility warnings")

    # ===================================================================
    # SECTION 3: "What crystal structure will this form?"
    # Structure type prediction
    # ===================================================================
    print("\n--- SECTION 3: Crystal Structure Prediction ---\n")

    from composition_engine.structure_predictor import StructureTypePredictor
    stp = StructureTypePredictor()

    # Q12-Q18: Known structure types
    known_structures = [
        ("NMC811", "layered", "R-3m, published"),
        ("LFP", "olivine", "Pnma, published"),
        ("LMO", "spinel", "Fd-3m, published"),
        ("LLZO", "garnet", "Ia-3d, published"),
        ("LGPS", "thio-LISICON", "P42/nmc, published"),
        ("BaTiO3", "perovskite", "Pm-3m, published"),
        ("Al2O3", "corundum", "R-3c, published"),
    ]
    for formula, expected, note in known_structures:
        r = stp.predict(formula)
        check(r.predicted_type == expected,
              f"{formula} -> {expected}?",
              f"Got {r.predicted_type} (conf={r.confidence:.2f}, {note})")

    # Q19: Novel NMC should still be layered
    r = stp.predict("NMC721")
    check(r.predicted_type == "layered",
          "Novel NMC721 -> layered?",
          f"Got {r.predicted_type} (conf={r.confidence:.2f})")

    # Q20: LiMnPO4 should be olivine (same family as LFP)
    r = stp.predict("LiMnPO4")
    check(r.predicted_type == "olivine",
          "LiMnPO4 -> olivine?",
          f"Got {r.predicted_type} (conf={r.confidence:.2f})")

    # ===================================================================
    # SECTION 4: "Is PVDF a PFAS? What can replace it?"
    # PFAS compliance + replacements
    # ===================================================================
    print("\n--- SECTION 4: PFAS Compliance ---\n")

    from pfas_bridge.compliance_checker import PFASComplianceChecker
    from pfas_bridge.replacement_scorer import UseCase
    checker = PFASComplianceChecker()

    # Q21: PVDF is a PFAS
    result = checker.check("PVDF")
    check(result.is_pfas,
          "PVDF detected as PFAS?",
          f"is_pfas={result.is_pfas}, urgency={result.urgency}")

    # Q22: PTFE is a PFAS
    result = checker.check("PTFE")
    check(result.is_pfas,
          "PTFE detected as PFAS?",
          f"is_pfas={result.is_pfas}, urgency={result.urgency}")

    # Q23: Polyethylene is NOT a PFAS
    result = checker.check("Polyethylene")
    check(not result.is_pfas,
          "Polyethylene is NOT PFAS?",
          f"is_pfas={result.is_pfas}")

    # Q24: PVDF battery binder replacement -> CMC+SBR should be top
    # (Bresser 2018: CMC+SBR is the established PVDF alternative for anodes)
    result = checker.check("PVDF", use_case=UseCase.BATTERY_BINDER)
    replacements = result.replacements
    check(len(replacements) > 0 and replacements[0].name == "CMC+SBR",
          "PVDF binder replacement #1 = CMC+SBR?",
          f"Got: {[r.name for r in replacements[:3]]}")

    # Q25: PFOA should be BANNED (Stockholm Convention)
    result = checker.check("PFOA")
    check(result.is_pfas and result.urgency in ("critical", "high"),
          "PFOA flagged as critical/high urgency?",
          f"urgency={result.urgency}")

    # Q26: Batch check a BOM
    bom = ["NMC811", "PVDF", "Carbon_Black", "Aluminum_foil"]
    batch = checker.check_batch(bom)
    check(batch.has_pfas and batch.pfas_count == 1,
          "BOM check: exactly 1 PFAS in [NMC811, PVDF, CB, Al]?",
          f"pfas_count={batch.pfas_count}, max_urgency={batch.max_urgency}")

    # ===================================================================
    # SECTION 5: "Are these materials compatible?"
    # Bridge compatibility checks
    # ===================================================================
    print("\n--- SECTION 5: Material Compatibility ---\n")

    from battery_bridge.interaction_scoring import score_all
    from battery_bridge.material_properties import get_material

    # Q27: NMC811 + LLZO should be compatible (published solid-state cell)
    try:
        nmc = get_material("NMC811")
        llzo = get_material("LLZO")
        scores = score_all(nmc, llzo)
        avg = sum(s.score for s in scores.values()) / len(scores) if scores else 0
        check(avg > 0.4,
              "NMC811 + LLZO compatible (solid-state cell)?",
              f"avg score={avg:.2f}")
    except Exception as e:
        check(False, "NMC811 + LLZO compatible?", f"Error: {e}")

    # Q28: NMC811 + Graphite should be compatible (standard Li-ion)
    try:
        nmc = get_material("NMC811")
        gr = get_material("Graphite")
        scores = score_all(nmc, gr)
        avg = sum(s.score for s in scores.values()) / len(scores) if scores else 0
        check(avg > 0.4,
              "NMC811 + Graphite compatible (standard Li-ion)?",
              f"avg score={avg:.2f}")
    except Exception as e:
        check(False, "NMC811 + Graphite compatible?", f"Error: {e}")

    # ===================================================================
    # SECTION 6: "How do I make LFP?"
    # Synthesis planning
    # ===================================================================
    print("\n--- SECTION 6: Synthesis Planning ---\n")

    from synthesis_planner.route_planner import SynthesisPlanner
    planner = SynthesisPlanner()

    # Q29: LFP should have synthesis routes
    analysis = planner.plan_synthesis("LFP")
    check(analysis.best_route is not None,
          "LFP has synthesis routes?",
          f"Found {len(analysis.routes)} route(s), "
          f"best={analysis.best_route.route.name if analysis.best_route else 'none'}")

    # Q30: NMC811 should have synthesis routes
    analysis = planner.plan_synthesis("NMC811")
    check(analysis.best_route is not None,
          "NMC811 has synthesis routes?",
          f"Found {len(analysis.routes)} route(s)")

    # Q31: Synthesis should need a furnace (all cathodes need calcination)
    check("furnace" in analysis.equipment_needed,
          "NMC811 synthesis needs a furnace?",
          f"Equipment: {analysis.equipment_needed[:5]}")

    # ===================================================================
    # SECTION 7: "Cross-domain: Electrolyte + Cathode"
    # Molecular-material cross-bridge
    # ===================================================================
    print("\n--- SECTION 7: Electrolyte-Cathode Compatibility ---\n")

    from cross_bridge.molecular_material import (
        score_molecule_material, score_electrolyte_formulation,
    )

    # Q32: EC + NMC811 should work (standard electrolyte solvent)
    try:
        result = score_molecule_material("EC", "NMC811")
        check(result.compatible,
              "EC + NMC811 compatible?",
              f"score={result.score:.2f}")
    except Exception as e:
        check(False, "EC + NMC811 compatible?", f"Error: {e}")

    # Q33: EC+DMC+LiPF6 electrolyte should be viable
    try:
        result = score_electrolyte_formulation(
            solvent_names=["EC", "DMC"],
            salt_name="LiPF6",
            electrode_name="NMC811",
        )
        check(result.get("viable", False),
              "EC+DMC+LiPF6 with NMC811 viable?",
              f"viable={result.get('viable')}, "
              f"score={result.get('overall_score', 0):.2f}")
    except Exception as e:
        check(False, "EC+DMC+LiPF6 with NMC811 viable?", f"Error: {e}")

    # Q34: PC + Graphite should be INCOMPATIBLE (PC co-intercalation destroys graphite)
    try:
        result = score_molecule_material("PC", "Graphite")
        check(not result.compatible,
              "PC + Graphite incompatible (co-intercalation)?",
              f"compatible={result.compatible}, score={result.score:.2f}")
    except Exception as e:
        check(False, "PC + Graphite incompatible?", f"Error: {e}")

    # ===================================================================
    # SECTION 8: End-to-end scenario
    # "Design a solid-state NMC811 cell with no PFAS"
    # ===================================================================
    print("\n--- SECTION 8: Full Cell Design Scenario ---\n")

    # Q35: Predict NMC811 properties + structure + stability
    r = pred.predict("NMC811")
    fe = fep.predict("NMC811")
    st = stp.predict("NMC811")
    check(
        r.properties.get("voltage") is not None
        and fe.is_stable
        and st.predicted_type == "layered",
        "NMC811 full characterization (voltage + stable + layered)?",
        f"V={r.properties['voltage'].value:.2f}, "
        f"Ef={fe.ef_per_atom:.2f}, struct={st.predicted_type}")

    # Q36: LLZO solid electrolyte should also be stable + garnet
    fe_llzo = fep.predict("LLZO")
    st_llzo = stp.predict("LLZO")
    check(fe_llzo.is_stable and st_llzo.predicted_type == "garnet",
          "LLZO: stable garnet electrolyte?",
          f"Ef={fe_llzo.ef_per_atom:.2f}, struct={st_llzo.predicted_type}")

    # Q37: Check PVDF-free BOM
    cell_bom = ["NMC811", "LLZO", "Li_metal", "CMC", "Carbon_Black"]
    batch = checker.check_batch(cell_bom)
    check(not batch.has_pfas,
          "PFAS-free cell BOM [NMC811, LLZO, Li, CMC, CB]?",
          f"pfas_count={batch.pfas_count}")

    # Q38: Can we synthesize both NMC811 and LLZO?
    a1 = planner.plan_synthesis("NMC811")
    a2 = planner.plan_synthesis("LLZO")
    check(a1.best_route is not None and a2.best_route is not None,
          "Both NMC811 and LLZO have synthesis routes?",
          f"NMC811: {len(a1.routes)} routes, LLZO: {len(a2.routes)} routes")

    # ===================================================================
    # SECTION 9: "Find me a ligand with exactly N heavy atoms"
    # Constraint-based molecular search (Kulik challenge)
    # ===================================================================
    print("\n--- SECTION 9: Ligand Constraint Search (Kulik Challenge) ---\n")

    from molecular_bridge.constraint_search import (
        search_by_constraints, count_heavy_atoms_from_formula,
        get_atom_count_distribution,
    )
    from molecular_bridge.molecule_properties import MoleculeClass

    # Q39: Kulik's 22-atom challenge -- should return real answer or empty, never hallucinate
    results_22 = search_by_constraints(heavy_atom_count=22)
    # Whether we have 0 or some, every result MUST actually have 22 heavy atoms
    all_correct_22 = all(
        count_heavy_atoms_from_formula(m.formula) == 22 for m in results_22
    )
    check(all_correct_22,
          "22-atom search: all results actually have 22 heavy atoms (no hallucination)?",
          f"Found {len(results_22)} molecule(s), all verified={all_correct_22}")

    # Q40: EC (C3H4O3) should have 6 heavy atoms (3C + 3O)
    ec_count = count_heavy_atoms_from_formula("C3H4O3")
    check(ec_count == 6,
          "EC (C3H4O3) has 6 heavy atoms?",
          f"Got {ec_count}")

    # Q41: LiPF6 should have 8 heavy atoms (1Li + 1P + 6F)
    lipf6_count = count_heavy_atoms_from_formula("LiPF6")
    check(lipf6_count == 8,
          "LiPF6 has 8 heavy atoms?",
          f"Got {lipf6_count}")

    # Q42: H2 should have 0 heavy atoms (hydrogen only)
    h2_count = count_heavy_atoms_from_formula("H2")
    check(h2_count == 0,
          "H2 has 0 heavy atoms?",
          f"Got {h2_count}")

    # Q43: Range query: 5-10 heavy atoms, no fluorine -- should find solvents
    results_range = search_by_constraints(
        heavy_atom_range=(5, 10), exclude_elements=["F"]
    )
    all_in_range = all(
        5 <= count_heavy_atoms_from_formula(m.formula) <= 10
        for m in results_range
    )
    no_fluorine = all("F" not in m.formula.replace("Fe", "XX") for m in results_range)
    check(len(results_range) > 0 and all_in_range,
          "Range query (5-10 atoms, no F): results exist and all in range?",
          f"Found {len(results_range)}, all_in_range={all_in_range}")

    # Q44: Search for molecules containing lithium (salt anions)
    li_mols = search_by_constraints(include_elements=["Li"])
    all_have_li = all("Li" in m.formula for m in li_mols)
    check(len(li_mols) > 0 and all_have_li,
          "Lithium-containing molecules found?",
          f"Found {len(li_mols)}: {[m.name for m in li_mols[:4]]}")

    # Q45: Fe-containing search should NOT match F (element parsing, not substring)
    fe_mols = search_by_constraints(include_elements=["Fe"])
    # Every result must actually contain iron, not just fluorine
    all_have_fe = all("Fe" in m.formula for m in fe_mols)
    check(all_have_fe,
          "Fe search finds iron, not fluorine (element parsing)?",
          f"Found {len(fe_mols)} Fe-containing molecule(s)")

    # Q46: Atom count distribution should cover the full database
    dist = get_atom_count_distribution()
    total_in_dist = sum(len(names) for names in dist.values())
    from molecular_bridge.molecule_properties import ALL_MOLECULES
    check(total_in_dist == len(ALL_MOLECULES),
          "Atom count distribution covers all molecules?",
          f"{total_in_dist} in dist vs {len(ALL_MOLECULES)} total")

    # ===================================================================
    # SECTION 10: "Generate a PFAS compliance report for this BOM"
    # PFAS report generator with provenance
    # ===================================================================
    print("\n--- SECTION 10: PFAS Compliance Report ---\n")

    from reports.pfas_report import PFASComplianceReport, MaterialInput

    report_gen = PFASComplianceReport()

    # Q47: Report for battery BOM should detect PVDF + PTFE
    bom_materials = [
        MaterialInput(name="PVDF", function="cathode binder", quantity_kg=2.5),
        MaterialInput(name="NMC811", function="cathode active", quantity_kg=45.0),
        MaterialInput(name="PTFE", function="separator coating", quantity_kg=0.5),
        MaterialInput(name="EC", function="electrolyte solvent", quantity_kg=8.0),
        MaterialInput(name="Graphite", function="anode active", quantity_kg=30.0),
    ]
    report = report_gen.screen_portfolio(bom_materials)
    check(report.summary["screened"] == 5 and report.summary["detected"] == 2,
          "Report: 5 screened, 2 PFAS detected (PVDF + PTFE)?",
          f"screened={report.summary['screened']}, detected={report.summary['detected']}")

    # Q48: Report should have a report ID
    check(report.report_id.startswith("PFAS-"),
          "Report has PFAS-YYYY-MMDD-NNNN ID?",
          f"Got {report.report_id}")

    # Q49: Detections should have replacements with provenance
    has_provenance = all(
        len(d.replacements) > 0 and
        all(len(r.provenance) > 0 for r in d.replacements)
        for d in report.detections
    )
    check(has_provenance,
          "All detections have replacements with provenance chains?",
          f"Detections: {len(report.detections)}, "
          f"total replacements: {sum(len(d.replacements) for d in report.detections)}")

    # Q50: Replacements should have verdicts (VALIDATED / CAUTION / VETOED)
    all_verdicts = [
        r.verdict for d in report.detections for r in d.replacements
    ]
    valid_verdicts = {"VALIDATED", "CAUTION", "VETOED"}
    check(len(all_verdicts) > 0 and all(v in valid_verdicts for v in all_verdicts),
          "All replacements have valid verdicts?",
          f"Verdicts: {set(all_verdicts)}")

    # Q51: Report should have regulatory timeline
    check(len(report.regulatory_timeline) > 0,
          "Report has regulatory timeline?",
          f"Found {len(report.regulatory_timeline)} regulations")

    # Q52: Report should have action plan
    check(len(report.action_plan) > 0,
          "Report has prioritized action plan?",
          f"Found {len(report.action_plan)} action items")

    # Q53: Clean BOM should produce CLEAN risk level
    clean_bom = [
        MaterialInput(name="NMC811", function="cathode"),
        MaterialInput(name="Graphite", function="anode"),
        MaterialInput(name="CMC", function="binder"),
    ]
    clean_report = report_gen.screen_portfolio(clean_bom)
    check(clean_report.summary["risk_level"] == "CLEAN" and
          clean_report.summary["detected"] == 0,
          "PFAS-free BOM -> CLEAN risk level?",
          f"risk={clean_report.summary['risk_level']}, "
          f"detected={clean_report.summary['detected']}")

    # Q54: PVDF binder replacement #1 should be VALIDATED (score >= 0.7)
    pvdf_det = [d for d in report.detections if d.material == "PVDF"]
    if pvdf_det and pvdf_det[0].replacements:
        top_repl = pvdf_det[0].replacements[0]
        check(top_repl.verdict == "VALIDATED" and top_repl.overall_score >= 0.7,
              "PVDF top replacement is VALIDATED with score >= 0.7?",
              f"{top_repl.name}: score={top_repl.overall_score:.3f}, verdict={top_repl.verdict}")
    else:
        check(False, "PVDF top replacement is VALIDATED?", "No PVDF detection found")

    # ===================================================================
    # SECTION 11: "Which MOF is best for CO2 capture?"
    # MOF bridge -- suitability scoring
    # ===================================================================
    print("\n--- SECTION 11: MOF Bridge ---\n")

    from mof_bridge.material_properties import ALL_MOFS, get_mof, MOFApplication
    from mof_bridge.interface_validator import (
        MOFInterfaceValidator, MOFConditions, validate_mof,
    )

    # Q55: ZIF-8 should exist with published BET > 1000 m2/g (Park 2006: 1630)
    zif8 = get_mof("ZIF-8")
    check(zif8 is not None and zif8.bet_surface_area_m2g > 1000,
          "ZIF-8 exists with BET > 1000 m2/g?",
          f"BET={zif8.bet_surface_area_m2g} m2/g" if zif8 else "NOT FOUND")

    # Q56: MOF-5 should be pcu topology (Yaghi 2003)
    mof5 = get_mof("MOF-5")
    check(mof5 is not None and mof5.topology.value == "pcu",
          "MOF-5 has pcu topology?",
          f"topology={mof5.topology.value}" if mof5 else "NOT FOUND")

    # Q57: UiO-66 should be water-stable (Cavka 2008 -- Zr-based, famously robust)
    uio66 = get_mof("UiO-66")
    check(uio66 is not None and uio66.water_stability in ("excellent", "good"),
          "UiO-66 is water-stable?",
          f"water_stability={uio66.water_stability}" if uio66 else "NOT FOUND")

    # Q58: We should have 30 MOFs in the database
    check(len(ALL_MOFS) == 30,
          "Database has 30 MOFs?",
          f"Got {len(ALL_MOFS)}")

    # Q59: Every MOF should have a DOI (published data, no hallucinations)
    all_have_doi = all(mof.doi != "" for mof in ALL_MOFS.values())
    check(all_have_doi,
          "Every MOF has a DOI reference?",
          f"MOFs without DOI: {[m.name for m in ALL_MOFS.values() if m.doi == ''][:3]}")

    # Q60: ZIF-8 should be suitable for gas separation (CO2 kinetic diameter 3.3A, ZIF-8 pore ~3.4A)
    score_zif8 = validate_mof(
        "ZIF-8",
        conditions=MOFConditions(
            target_molecule_diameter=3.3,
            target_application=MOFApplication.SEPARATION,
        ),
    )
    check(score_zif8.suitable and score_zif8.total > 0.5,
          "ZIF-8 suitable for CO2 separation (3.3A molecule)?",
          f"score={score_zif8.total:.2f}, suitable={score_zif8.suitable}")

    # Q61: HKUST-1 should be in the database (famous Cu-BTC MOF, Chui 1999)
    hkust = get_mof("HKUST-1")
    check(hkust is not None and "Cu" in hkust.metal_node,
          "HKUST-1 exists with Cu metal node?",
          f"metal_node={hkust.metal_node}" if hkust else "NOT FOUND")

    # Q62: Screen all MOFs for high-temperature catalysis (300C)
    # Thermal stability varies widely: UiO-66 decomposes ~540C, HKUST-1 ~280C
    # At 300C, thermal COMPONENT scores should spread (some high, some near 0)
    validator = MOFInterfaceValidator()
    hot_results = validator.screen_all(
        conditions=MOFConditions(
            operating_temp_C=300,
            target_application=MOFApplication.CATALYSIS,
        ),
    )
    thermal_scores = [s.thermal_compatibility for _, s in hot_results]
    thermal_spread = max(thermal_scores) - min(thermal_scores)
    check(thermal_spread > 0.5,
          "300C screen: thermal scores spread > 0.5 (stability varies)?",
          f"spread={thermal_spread:.2f}, min={min(thermal_scores):.2f}, max={max(thermal_scores):.2f}")

    # Q63: UiO-66 should score higher than MOF-5 in water (UiO-66 water-stable, MOF-5 not)
    score_uio = validate_mof("UiO-66", conditions=MOFConditions(
        environment="aqueous", requires_water_stable=True))
    score_mof5 = validate_mof("MOF-5", conditions=MOFConditions(
        environment="aqueous", requires_water_stable=True))
    check(score_uio.total > score_mof5.total,
          "UiO-66 > MOF-5 in aqueous conditions?",
          f"UiO-66={score_uio.total:.2f} > MOF-5={score_mof5.total:.2f}")

    # Q64: MOF screen results should be sorted by score descending
    scores_descending = all(
        hot_results[i][1].total >= hot_results[i+1][1].total
        for i in range(len(hot_results) - 1)
    )
    check(scores_descending,
          "Screen results sorted by score descending?",
          f"Top 3: {[(n, f'{s.total:.2f}') for n, s in hot_results[:3]]}")

    # ===================================================================
    # RESULTS
    # ===================================================================
    print(f"\n{'=' * 78}")
    print(f"DOGFOOD TEST RESULTS")
    print(f"{'=' * 78}")
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {failed}/{total}")
    pct = 100 * passed / total if total > 0 else 0
    print(f"  Score:  {pct:.0f}%")

    if failed == 0:
        print("\n  ALL TESTS PASSED -- the system gives correct answers")
        print("  to real materials science questions!")
    else:
        print(f"\n  {failed} question(s) got wrong answers -- needs investigation")

    return failed


if __name__ == "__main__":
    sys.exit(main())
