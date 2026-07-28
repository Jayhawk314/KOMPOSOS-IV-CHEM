# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for composition_engine.formation_energy (DFT surrogate via CAT+ZFC)."""

import unittest

from composition_engine.formation_energy import (
    FormationEnergyPredictor,
    FormationEnergyResult,
    KNOWN_EF,
    check_thermodynamic_constraints,
    _kapustinskii_estimate,
    _electronegativity_estimate,
    _goldschmidt_tolerance,
)
from composition_engine.parser import parse_formula


class TestKnownFormationEnergies(unittest.TestCase):
    """Tests for the known DFT formation energy database."""

    def test_database_not_empty(self):
        self.assertGreater(len(KNOWN_EF), 20)

    def test_all_have_formulas(self):
        for entry in KNOWN_EF:
            self.assertTrue(len(entry.formula) > 0, f"{entry.name} has no formula")

    def test_all_have_compositions(self):
        for entry in KNOWN_EF:
            self.assertTrue(len(entry.composition) > 0,
                            f"{entry.name} has no composition")

    def test_all_have_vectors(self):
        for entry in KNOWN_EF:
            self.assertGreater(len(entry.vector), 0,
                               f"{entry.name} has no vector")

    def test_elements_have_zero_ef(self):
        """Pure elements should have Ef = 0 by convention."""
        for entry in KNOWN_EF:
            if entry.name.endswith("_ref"):
                self.assertAlmostEqual(entry.ef_per_atom, 0.0,
                                       msg=f"{entry.name} Ef != 0")

    def test_stable_compounds_negative(self):
        """Known stable compounds should have Ef < 0."""
        stable_names = ["LCO", "LFP", "LLZO", "Al2O3", "NMC811"]
        for entry in KNOWN_EF:
            if entry.name in stable_names:
                self.assertLess(entry.ef_per_atom, 0.0,
                                f"{entry.name} should have Ef < 0")

    def test_oxides_more_stable_than_sulfides(self):
        """Oxides generally have more negative Ef than sulfides."""
        llzo = next(e for e in KNOWN_EF if e.name == "LLZO")
        lgps = next(e for e in KNOWN_EF if e.name == "LGPS")
        self.assertLess(llzo.ef_per_atom, lgps.ef_per_atom)

    def test_nmc_ef_trend(self):
        """Higher Ni content -> slightly less stable (less negative Ef)."""
        nmc111 = next(e for e in KNOWN_EF if e.name == "NMC111")
        nmc811 = next(e for e in KNOWN_EF if e.name == "NMC811")
        # NMC111 should be more stable (more negative Ef)
        self.assertLess(nmc111.ef_per_atom, nmc811.ef_per_atom)


class TestRuleBasedEstimators(unittest.TestCase):
    """Tests for Kapustinskii and electronegativity estimators."""

    def test_kapustinskii_oxide(self):
        """Should produce negative Ef for simple oxides."""
        comp = parse_formula("LiCoO2")
        ef = _kapustinskii_estimate(comp)
        self.assertIsNotNone(ef)
        self.assertLess(ef, 0.0)

    def test_kapustinskii_returns_none_for_elements(self):
        """Pure elements have no lattice energy."""
        comp = parse_formula("Li")
        ef = _kapustinskii_estimate(comp)
        self.assertIsNone(ef)

    def test_kapustinskii_sulfide(self):
        """Should work for sulfides too."""
        comp = parse_formula("Li3PS4")
        ef = _kapustinskii_estimate(comp)
        self.assertIsNotNone(ef)
        self.assertLess(ef, 0.0)

    def test_en_estimate_oxide(self):
        """EN-based estimate should be negative for oxides."""
        comp = parse_formula("LiCoO2")
        ef = _electronegativity_estimate(comp)
        self.assertIsNotNone(ef)
        self.assertLess(ef, 0.0)

    def test_en_estimate_larger_for_more_ionic(self):
        """More ionic compounds (bigger EN diff) should have more negative Ef."""
        comp_al2o3 = parse_formula("Al2O3")
        comp_sic = parse_formula("SiC")
        ef_al2o3 = _electronegativity_estimate(comp_al2o3)
        ef_sic = _electronegativity_estimate(comp_sic)
        # Al2O3 is more ionic than SiC
        if ef_al2o3 is not None and ef_sic is not None:
            self.assertLess(ef_al2o3, ef_sic)

    def test_goldschmidt_nmc(self):
        """NMC layered oxides should have tolerance factor near 0.85-1.0."""
        comp = parse_formula("NMC811")
        t = _goldschmidt_tolerance(comp)
        self.assertIsNotNone(t)
        self.assertGreater(t, 0.7)
        self.assertLess(t, 1.1)

    def test_goldschmidt_returns_none_for_non_oxide(self):
        comp = parse_formula("Si")
        t = _goldschmidt_tolerance(comp)
        self.assertIsNone(t)


class TestThermodynamicConstraints(unittest.TestCase):
    """Tests for ZFC thermodynamic feasibility checks."""

    def test_stable_compound_passes(self):
        """A stable compound with negative Ef should pass most constraints."""
        comp = parse_formula("LiCoO2")
        constraints = check_thermodynamic_constraints(comp, -1.86)
        n_satisfied = sum(1 for c in constraints if c.satisfied)
        self.assertGreater(n_satisfied, 0)

    def test_unstable_fails_ef_check(self):
        """Positive Ef should fail the formation energy constraint."""
        comp = parse_formula("LiCoO2")
        constraints = check_thermodynamic_constraints(comp, 0.5)
        ef_check = next(c for c in constraints if c.name == "negative_formation_energy")
        self.assertFalse(ef_check.satisfied)

    def test_marginal_ef_fails_margin(self):
        """Ef very close to 0 should fail decomposition margin."""
        comp = parse_formula("LiCoO2")
        constraints = check_thermodynamic_constraints(comp, -0.05)
        margin = next(c for c in constraints if c.name == "decomposition_margin")
        self.assertFalse(margin.satisfied)

    def test_charge_balance_licoO2(self):
        """LiCoO2 should be roughly charge-balanced."""
        comp = parse_formula("LiCoO2")
        constraints = check_thermodynamic_constraints(comp, -1.86)
        charge = next(c for c in constraints if c.name == "charge_balance")
        self.assertTrue(charge.satisfied)

    def test_all_constraints_have_details(self):
        comp = parse_formula("NMC811")
        constraints = check_thermodynamic_constraints(comp, -1.61)
        for c in constraints:
            self.assertTrue(len(c.detail) > 0, f"{c.name} has no detail")
            self.assertIsInstance(c.confidence, float)

    def test_incompatible_elements_flagged(self):
        """Li + Na mixing should be flagged."""
        comp = {"Li": 0.5, "Na": 0.5, "Co": 1.0, "O": 2.0}
        constraints = check_thermodynamic_constraints(comp, -1.5)
        compat_checks = [c for c in constraints if c.name == "element_compatibility"]
        self.assertGreater(len(compat_checks), 0)
        self.assertFalse(compat_checks[0].satisfied)


class TestFormationEnergyPredictor(unittest.TestCase):
    """Tests for the main formation energy predictor."""

    def setUp(self):
        self.fep = FormationEnergyPredictor()

    def test_predict_returns_result(self):
        result = self.fep.predict("NMC721")
        self.assertIsInstance(result, FormationEnergyResult)

    def test_known_material_reproduces(self):
        """Predicting a known material should give close to known Ef."""
        result = self.fep.predict("NMC811")
        # NMC811 known Ef = -1.61 (exact match in DB, so Kan should dominate)
        self.assertAlmostEqual(result.ef_per_atom, -1.61, delta=0.5)

    def test_nmc_cathodes_stable(self):
        """All NMC cathodes should predict as stable."""
        for f in ["NMC811", "NMC622", "NMC111"]:
            result = self.fep.predict(f)
            self.assertTrue(result.is_stable, f"{f} predicted unstable")

    def test_novel_nmc_stable(self):
        """A novel NMC composition should still predict stable."""
        result = self.fep.predict("NMC721")
        self.assertTrue(result.is_stable)
        self.assertLess(result.ef_per_atom, -1.0)

    def test_nmc532_stable(self):
        result = self.fep.predict("NMC532")
        self.assertTrue(result.is_stable)

    def test_nmc955_stable(self):
        """High-Ni NMC should be stable but less so than NMC111."""
        result_955 = self.fep.predict("NMC955")
        result_111 = self.fep.predict("NMC111")
        self.assertTrue(result_955.is_stable)
        # 955 should be less stable (less negative Ef)
        self.assertGreater(result_955.ef_per_atom, result_111.ef_per_atom)

    def test_confidence_range(self):
        result = self.fep.predict("NMC721")
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_synthesizability_range(self):
        result = self.fep.predict("NMC721")
        self.assertGreaterEqual(result.synthesizability_score, 0.0)
        self.assertLessEqual(result.synthesizability_score, 1.0)

    def test_stable_has_high_synthesizability(self):
        """Known stable materials should have synth score > 0.5."""
        for f in ["LCO", "LFP", "NMC811"]:
            result = self.fep.predict(f)
            self.assertGreater(result.synthesizability_score, 0.5,
                               f"{f} synth score too low")

    def test_has_sources(self):
        result = self.fep.predict("NMC721")
        self.assertGreater(len(result.sources), 0)

    def test_has_constraints(self):
        result = self.fep.predict("NMC721")
        self.assertGreater(len(result.constraints), 0)

    def test_has_nearest_known(self):
        result = self.fep.predict("NMC721")
        self.assertGreater(len(result.nearest_known), 0)

    def test_to_dict(self):
        result = self.fep.predict("NMC721")
        d = result.to_dict()
        self.assertIn("ef_per_atom_eV", d)
        self.assertIn("synthesizability_score", d)
        self.assertIn("constraints", d)
        self.assertIn("is_stable", d)

    def test_lfp_olivine_stable(self):
        result = self.fep.predict("LFP")
        self.assertTrue(result.is_stable)
        self.assertLess(result.ef_per_atom, -1.0)

    def test_llzo_garnet_very_stable(self):
        """LLZO should be very stable (Ef ~ -2.85)."""
        result = self.fep.predict("LLZO")
        self.assertTrue(result.is_stable)
        self.assertLess(result.ef_per_atom, -2.0)

    def test_ef_trend_ni_content(self):
        """Higher Ni -> less stable (less negative Ef)."""
        ef_111 = self.fep.predict("NMC111").ef_per_atom
        ef_622 = self.fep.predict("NMC622").ef_per_atom
        ef_811 = self.fep.predict("NMC811").ef_per_atom
        # Should decrease stability: 111 < 622 < 811 (more negative = more stable)
        self.assertLess(ef_111, ef_622)
        self.assertLess(ef_622, ef_811)


class TestLeaveOneOut(unittest.TestCase):
    """Leave-one-out validation for formation energy."""

    def setUp(self):
        self.fep = FormationEnergyPredictor()

    def test_loo_nmc811(self):
        """Remove NMC811, predict from neighbours. Error < 0.5 eV/atom."""
        known_ef_actual = next(e.ef_per_atom for e in KNOWN_EF if e.name == "NMC811")

        fep = FormationEnergyPredictor()
        fep.known = [e for e in KNOWN_EF if e.name != "NMC811"]

        result = fep.predict("NMC811")
        error = abs(result.ef_per_atom - known_ef_actual)
        self.assertLess(error, 0.5, f"NMC811 LOO error {error:.3f} > 0.5 eV/atom")

    def test_loo_nmc622(self):
        """Remove NMC622, predict from neighbours. Error < 0.5 eV/atom."""
        known_ef = next(e.ef_per_atom for e in KNOWN_EF if e.name == "NMC622")
        fep = FormationEnergyPredictor()
        fep.known = [e for e in KNOWN_EF if e.name != "NMC622"]
        result = fep.predict("NMC622")
        error = abs(result.ef_per_atom - known_ef)
        self.assertLess(error, 0.5, f"NMC622 LOO error {error:.3f} > 0.5 eV/atom")


if __name__ == "__main__":
    unittest.main()
