# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""Tests for composition_engine.structure_predictor (crystal structure type)."""

import unittest

from composition_engine.structure_predictor import (
    StructureTypePredictor,
    StructurePrediction,
    STRUCTURE_TYPES,
    ELEMENT_STRUCTURES,
)
from composition_engine.formation_energy import KNOWN_EF
from composition_engine.parser import parse_formula


class TestKnownMaterialStructures(unittest.TestCase):
    """Validate that known materials predict correct structure types."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_nmc811_layered(self):
        r = self.stp.predict("NMC811")
        self.assertEqual(r.predicted_type, "layered")

    def test_nmc622_layered(self):
        r = self.stp.predict("NMC622")
        self.assertEqual(r.predicted_type, "layered")

    def test_nmc111_layered(self):
        r = self.stp.predict("NMC111")
        self.assertEqual(r.predicted_type, "layered")

    def test_lco_layered(self):
        r = self.stp.predict("LCO")
        self.assertEqual(r.predicted_type, "layered")

    def test_nca_layered(self):
        r = self.stp.predict("NCA")
        self.assertEqual(r.predicted_type, "layered")

    def test_lfp_olivine(self):
        r = self.stp.predict("LFP")
        self.assertEqual(r.predicted_type, "olivine")

    def test_lmo_spinel(self):
        r = self.stp.predict("LMO")
        self.assertEqual(r.predicted_type, "spinel")

    def test_lnmo_spinel(self):
        r = self.stp.predict("LNMO")
        self.assertEqual(r.predicted_type, "spinel")

    def test_llzo_garnet(self):
        r = self.stp.predict("LLZO")
        self.assertEqual(r.predicted_type, "garnet")

    def test_lgps_thio_lisicon(self):
        r = self.stp.predict("LGPS")
        self.assertEqual(r.predicted_type, "thio-LISICON")

    def test_latp_nasicon(self):
        r = self.stp.predict("LATP")
        self.assertEqual(r.predicted_type, "NASICON")

    def test_batio3_perovskite(self):
        r = self.stp.predict("BaTiO3")
        self.assertEqual(r.predicted_type, "perovskite")

    def test_al2o3_corundum(self):
        r = self.stp.predict("Al2O3")
        self.assertEqual(r.predicted_type, "corundum")

    def test_tio2_rutile(self):
        r = self.stp.predict("TiO2")
        self.assertEqual(r.predicted_type, "rutile")

    def test_zro2_monoclinic(self):
        r = self.stp.predict("ZrO2")
        self.assertEqual(r.predicted_type, "monoclinic")

    def test_nio_rock_salt(self):
        r = self.stp.predict("NiO")
        self.assertEqual(r.predicted_type, "rock_salt")

    def test_mgo_rock_salt(self):
        r = self.stp.predict("MgO")
        self.assertEqual(r.predicted_type, "rock_salt")

    def test_gaas_zinc_blende(self):
        r = self.stp.predict("GaAs")
        self.assertEqual(r.predicted_type, "zinc_blende")

    def test_gan_wurtzite(self):
        r = self.stp.predict("GaN")
        self.assertEqual(r.predicted_type, "wurtzite")

    def test_si_diamond(self):
        r = self.stp.predict("Si")
        self.assertEqual(r.predicted_type, "diamond")

    def test_li_bcc(self):
        r = self.stp.predict("Li")
        self.assertEqual(r.predicted_type, "bcc")


class TestNovelCompositions(unittest.TestCase):
    """Novel compositions should still get reasonable structure predictions."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_nmc721_layered(self):
        r = self.stp.predict("NMC721")
        self.assertEqual(r.predicted_type, "layered")

    def test_nmc532_layered(self):
        r = self.stp.predict("NMC532")
        self.assertEqual(r.predicted_type, "layered")

    def test_nmc955_layered(self):
        r = self.stp.predict("NMC955")
        self.assertEqual(r.predicted_type, "layered")

    def test_novel_nmc_layered(self):
        r = self.stp.predict("LiNi0.7Mn0.15Co0.15O2")
        self.assertEqual(r.predicted_type, "layered")

    def test_novel_olivine_mn(self):
        """LiMnPO4 should be olivine."""
        r = self.stp.predict("LiMnPO4")
        self.assertEqual(r.predicted_type, "olivine")

    def test_novel_olivine_co(self):
        """LiCoPO4 should be olivine."""
        r = self.stp.predict("LiCoPO4")
        self.assertEqual(r.predicted_type, "olivine")

    def test_li_rich_layered(self):
        """Li1.2Ni0.2Mn0.4Co0.2O2 should still be layered."""
        r = self.stp.predict("Li1.2Ni0.2Mn0.4Co0.2O2")
        self.assertEqual(r.predicted_type, "layered")


class TestConfidenceAndProbabilities(unittest.TestCase):
    """Confidence and probability output format checks."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_confidence_range(self):
        r = self.stp.predict("NMC811")
        self.assertGreaterEqual(r.confidence, 0.0)
        self.assertLessEqual(r.confidence, 1.0)

    def test_probabilities_sum_near_one(self):
        r = self.stp.predict("NMC721")
        total = sum(r.probabilities.values())
        # Top-5 filtered, so might not sum to exactly 1.0
        self.assertGreater(total, 0.5)
        self.assertLessEqual(total, 1.05)

    def test_top_prediction_has_highest_probability(self):
        r = self.stp.predict("NMC811")
        if r.probabilities:
            top_prob = r.probabilities.get(r.predicted_type, 0)
            for st, p in r.probabilities.items():
                self.assertGreaterEqual(top_prob, p - 0.001)

    def test_high_confidence_for_clear_cases(self):
        """Known clear-cut structures should have high confidence."""
        for formula in ["NMC811", "LFP", "LMO", "LLZO"]:
            r = self.stp.predict(formula)
            self.assertGreater(r.confidence, 0.80,
                               f"{formula} confidence too low: {r.confidence}")


class TestGoldschmidt(unittest.TestCase):
    """Goldschmidt tolerance factor integration."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_nmc_has_goldschmidt(self):
        r = self.stp.predict("NMC811")
        self.assertIsNotNone(r.goldschmidt_t)
        self.assertGreater(r.goldschmidt_t, 0.7)
        self.assertLess(r.goldschmidt_t, 1.1)

    def test_simple_oxide_no_goldschmidt(self):
        """Non Li-TM-O compounds may not have Goldschmidt."""
        r = self.stp.predict("Al2O3")
        # Goldschmidt requires Li + TM + O, so Al2O3 should be None
        self.assertIsNone(r.goldschmidt_t)


class TestLeaveOneOut(unittest.TestCase):
    """Remove a known material, predict from neighbours."""

    def test_loo_nmc811_still_layered(self):
        stp = StructureTypePredictor()
        stp.known = [e for e in KNOWN_EF if e.name != "NMC811"]
        r = stp.predict("NMC811")
        self.assertEqual(r.predicted_type, "layered")

    def test_loo_lfp_still_olivine(self):
        stp = StructureTypePredictor()
        stp.known = [e for e in KNOWN_EF if e.name != "LFP"]
        r = stp.predict("LFP")
        self.assertEqual(r.predicted_type, "olivine")

    def test_loo_lmo_still_spinel(self):
        stp = StructureTypePredictor()
        stp.known = [e for e in KNOWN_EF if e.name != "LMO"]
        r = stp.predict("LMO")
        self.assertEqual(r.predicted_type, "spinel")


class TestSerialization(unittest.TestCase):
    """Test to_dict output."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_to_dict_has_required_fields(self):
        r = self.stp.predict("NMC811")
        d = r.to_dict()
        self.assertIn("predicted_type", d)
        self.assertIn("probabilities", d)
        self.assertIn("confidence", d)
        self.assertIn("goldschmidt_t", d)
        self.assertIn("sources", d)
        self.assertIn("detail", d)

    def test_to_dict_predicted_type_matches(self):
        r = self.stp.predict("LFP")
        d = r.to_dict()
        self.assertEqual(d["predicted_type"], "olivine")


class TestSources(unittest.TestCase):
    """Verify multiple evidence sources are reported."""

    def setUp(self):
        self.stp = StructureTypePredictor()

    def test_has_rule_source(self):
        r = self.stp.predict("NMC811")
        self.assertIn("rule", r.sources)

    def test_has_kan_source(self):
        r = self.stp.predict("NMC811")
        self.assertIn("kan_extension", r.sources)

    def test_detail_not_empty(self):
        r = self.stp.predict("NMC721")
        self.assertGreater(len(r.detail), 0)


if __name__ == "__main__":
    unittest.main()
