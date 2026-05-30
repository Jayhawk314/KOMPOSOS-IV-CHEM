"""
Tests for pfas_bridge/compliance_checker.py
=============================================

25 tests covering:
- PVDF is PFAS, HDPE is not
- PFOA urgency = critical (banned)
- PFHxA urgency = high (ban within 12 months of reference date)
- Batch checks
- Alternative suggestions
- Heuristic detection
"""

import unittest
from datetime import date

from pfas_bridge.compliance_checker import (
    BatchComplianceResult,
    ComplianceResult,
    PFASComplianceChecker,
)
from pfas_bridge.replacement_scorer import UseCase


class TestSingleMaterialCheck(unittest.TestCase):
    """Single-material compliance checks."""

    def setUp(self):
        # Reference date: March 2026 (PFHxA ban Oct 2026 = 7 months away)
        self.checker = PFASComplianceChecker(reference_date=date(2026, 3, 1))

    def test_pvdf_is_pfas(self):
        result = self.checker.check("PVDF")
        self.assertTrue(result.is_pfas)

    def test_pvdf_has_pfas_category(self):
        result = self.checker.check("PVDF")
        self.assertEqual(result.pfas_category, "fluoropolymer")

    def test_hdpe_is_not_pfas(self):
        result = self.checker.check("HDPE")
        self.assertFalse(result.is_pfas)

    def test_hdpe_urgency_none(self):
        result = self.checker.check("HDPE")
        self.assertEqual(result.urgency, "none")

    def test_cmc_is_not_pfas(self):
        result = self.checker.check("CMC")
        self.assertFalse(result.is_pfas)

    def test_pfoa_urgency_critical(self):
        result = self.checker.check("PFOA")
        self.assertEqual(result.urgency, "critical")

    def test_pfos_urgency_critical(self):
        result = self.checker.check("PFOS")
        self.assertEqual(result.urgency, "critical")

    def test_pfhxa_urgency_high(self):
        """PFHxA ban is Oct 2026, reference is Mar 2026 = 7 months = high."""
        result = self.checker.check("PFHxA")
        self.assertEqual(result.urgency, "high")

    def test_pfhxa_urgency_moderate_when_far(self):
        """If reference date is early enough, PFHxA should be moderate."""
        checker = PFASComplianceChecker(reference_date=date(2024, 1, 1))
        result = checker.check("PFHxA")
        self.assertEqual(result.urgency, "moderate")

    def test_genx_urgency_moderate(self):
        """GenX is restricted in US, under review in EU -> moderate."""
        result = self.checker.check("GenX")
        self.assertEqual(result.urgency, "moderate")

    def test_pvdf_has_replacements_for_binder(self):
        result = self.checker.check("PVDF", use_case=UseCase.BATTERY_BINDER)
        self.assertGreater(len(result.replacements), 0)

    def test_unknown_material_not_pfas(self):
        result = self.checker.check("Polyethylene")
        self.assertFalse(result.is_pfas)


class TestHeuristicDetection(unittest.TestCase):
    """Heuristic detection for unregistered fluorinated materials."""

    def setUp(self):
        self.checker = PFASComplianceChecker()

    def test_heuristic_detects_fluoropolymer_x(self):
        result = self.checker.check("fluoropolymer_X")
        self.assertTrue(result.is_pfas)
        self.assertTrue(result.heuristic_match)

    def test_heuristic_urgency_is_moderate(self):
        # reliable PFAS signal (perfluoro) -> heuristic match, moderate urgency
        result = self.checker.check("NewPerfluoroCompound")
        self.assertEqual(result.urgency, "moderate")

    def test_heuristic_no_replacements(self):
        """Heuristic matches don't have curated replacements."""
        result = self.checker.check("SomeFluoroThing")
        self.assertEqual(len(result.replacements), 0)


class TestBatchCheck(unittest.TestCase):
    """Batch BOM compliance checks."""

    def setUp(self):
        self.checker = PFASComplianceChecker(reference_date=date(2026, 3, 1))

    def test_batch_with_pfas(self):
        result = self.checker.check_batch(["PVDF", "CMC", "HDPE"])
        self.assertTrue(result.has_pfas)
        self.assertEqual(result.pfas_count, 1)

    def test_batch_without_pfas(self):
        result = self.checker.check_batch(["HDPE", "CMC", "Polyethylene"])
        self.assertFalse(result.has_pfas)
        self.assertEqual(result.pfas_count, 0)

    def test_batch_max_urgency(self):
        result = self.checker.check_batch(["PFOA", "PVDF", "HDPE"])
        self.assertEqual(result.max_urgency, "critical")

    def test_batch_result_count(self):
        materials = ["PVDF", "PTFE", "HDPE", "CMC"]
        result = self.checker.check_batch(materials)
        self.assertEqual(len(result.materials), 4)

    def test_batch_to_dict(self):
        result = self.checker.check_batch(["PVDF", "HDPE"])
        d = result.to_dict()
        self.assertIn("has_pfas", d)
        self.assertIn("pfas_count", d)
        self.assertIn("max_urgency", d)
        self.assertIn("materials", d)


class TestAlternativeSuggestions(unittest.TestCase):
    """Test suggest_alternatives method."""

    def setUp(self):
        self.checker = PFASComplianceChecker()

    def test_pvdf_alternatives_for_binder(self):
        alts = self.checker.suggest_alternatives("PVDF", UseCase.BATTERY_BINDER)
        self.assertGreater(len(alts), 0)
        names = [a.name for a in alts]
        self.assertIn("CMC+SBR", names)

    def test_ptfe_alternatives_for_seal(self):
        alts = self.checker.suggest_alternatives("PTFE", UseCase.SEAL_GASKET)
        self.assertGreater(len(alts), 0)

    def test_non_pfas_no_alternatives(self):
        alts = self.checker.suggest_alternatives("HDPE")
        self.assertEqual(len(alts), 0)

    def test_alternatives_sorted_by_score(self):
        alts = self.checker.suggest_alternatives("PVDF", UseCase.BATTERY_BINDER)
        scores = [a.overall_score for a in alts]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestSerialization(unittest.TestCase):
    """Test ComplianceResult serialization."""

    def setUp(self):
        self.checker = PFASComplianceChecker()

    def test_compliance_result_to_dict(self):
        result = self.checker.check("PVDF", UseCase.BATTERY_BINDER)
        d = result.to_dict()
        self.assertIn("material_name", d)
        self.assertIn("is_pfas", d)
        self.assertIn("urgency", d)
        self.assertIn("replacements", d)
        self.assertIn("pfas_name", d)
        self.assertIn("cas_number", d)


if __name__ == "__main__":
    unittest.main()
