"""Tests for PFAS compliance report generator."""

import unittest
from datetime import date

from reports.pfas_report import (
    PFASComplianceReport,
    MaterialInput,
    ReportData,
    LI_ION_DEMO_BOM,
    _compute_risk_level,
    _compute_verdict,
    _extract_replacement_provenance,
    _build_regulatory_timeline,
    _generate_action_plan,
)
from pfas_bridge.replacement_scorer import ReplacementCandidate, UseCase


class TestReportIdFormat(unittest.TestCase):
    """Report ID: PFAS-{YYYY}-{MMDD}-{count:04d}."""

    def test_report_id_format(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        rid = gen._generate_report_id(15)
        self.assertEqual(rid, "PFAS-2026-0324-0015")

    def test_report_id_single_digit_month(self):
        gen = PFASComplianceReport(reference_date=date(2026, 1, 5))
        rid = gen._generate_report_id(3)
        self.assertEqual(rid, "PFAS-2026-0105-0003")

    def test_report_id_large_count(self):
        gen = PFASComplianceReport(reference_date=date(2026, 12, 31))
        rid = gen._generate_report_id(9999)
        self.assertEqual(rid, "PFAS-2026-1231-9999")


class TestLiIonBOMScreening(unittest.TestCase):
    """Full Li-Ion BOM screening smoke tests."""

    @classmethod
    def setUpClass(cls):
        cls.gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        cls.report = cls.gen.screen_portfolio(LI_ION_DEMO_BOM)

    def test_report_is_report_data(self):
        self.assertIsInstance(self.report, ReportData)

    def test_report_has_report_id(self):
        self.assertTrue(self.report.report_id.startswith("PFAS-2026-"))

    def test_summary_screened_count(self):
        self.assertEqual(self.report.summary["screened"], len(LI_ION_DEMO_BOM))

    def test_detects_pvdf(self):
        detected_names = [d.material for d in self.report.detections]
        self.assertIn("PVDF", detected_names)

    def test_detects_ptfe(self):
        detected_names = [d.material for d in self.report.detections]
        self.assertIn("PTFE", detected_names)

    def test_nmc811_is_clean(self):
        clean_names = [c["name"] for c in self.report.clean_materials]
        self.assertIn("NMC811", clean_names)

    def test_clean_materials_have_pfas_free_status(self):
        for c in self.report.clean_materials:
            self.assertEqual(c["status"], "PFAS-FREE")

    def test_pvdf_has_replacements(self):
        pvdf = [d for d in self.report.detections if d.material == "PVDF"][0]
        self.assertGreater(len(pvdf.replacements), 0)

    def test_replacements_have_provenance(self):
        for det in self.report.detections:
            for r in det.replacements:
                self.assertGreater(len(r.provenance), 0, f"No provenance for {r.name}")

    def test_replacements_have_verdict(self):
        for det in self.report.detections:
            for r in det.replacements:
                self.assertIn(r.verdict, ("VALIDATED", "CAUTION", "VETOED", "REVIEW"))

    def test_risk_level_not_clean(self):
        self.assertNotEqual(self.report.summary["risk_level"], "CLEAN")

    def test_regulatory_timeline_nonempty(self):
        self.assertGreater(len(self.report.regulatory_timeline), 0)

    def test_action_plan_nonempty(self):
        self.assertGreater(len(self.report.action_plan), 0)

    def test_action_plan_sorted_by_priority(self):
        priorities = [a.priority for a in self.report.action_plan]
        self.assertEqual(priorities, sorted(priorities))

    def test_methodology_has_databases(self):
        self.assertIn("databases", self.report.methodology)

    def test_audit_certificate_has_report_id(self):
        self.assertEqual(
            self.report.audit_certificate["report_id"],
            self.report.report_id,
        )

    def test_to_dict_round_trip(self):
        d = self.report.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("report_id", d)
        self.assertIn("detections", d)
        self.assertIn("action_plan", d)


class TestRegulatoryLandscape(unittest.TestCase):
    """The regulatory section is date-free by design (no lock-in)."""

    def test_timeframe_is_qualitative_not_dated(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        materials = [MaterialInput(name="PVDF", function="binder")]
        report = gen.screen_portfolio(materials)
        self.assertTrue(len(report.regulatory_timeline) > 0)
        for t in report.regulatory_timeline:
            # Every regime has a non-empty qualitative timeframe...
            self.assertTrue(t.timeframe)
            # ...and the date-locking fields are gone entirely.
            self.assertFalse(hasattr(t, "days_remaining"))
            self.assertFalse(hasattr(t, "effective_date"))
            self.assertNotIn("effective_date", t.to_dict())

    def test_in_force_regimes_present(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio([MaterialInput(name="PFOA")])
        in_force = [t for t in report.regulatory_timeline if t.timeframe == "In force"]
        self.assertGreater(len(in_force), 0)


class TestVerdictLogic(unittest.TestCase):
    """Test VALIDATED / CAUTION / VETOED verdict logic."""

    def _make_candidate(self, score_performance, score_process, score_cost, score_avail):
        return ReplacementCandidate(
            name="Test",
            use_case=UseCase.GENERAL,
            performance_match=score_performance,
            processability=score_process,
            cost_factor=score_cost,
            availability=score_avail,
        )

    def test_validated_high_score_with_provenance(self):
        cand = self._make_candidate(0.8, 0.8, 0.8, 0.8)
        prov = [{"a": 1}, {"b": 2}, {"c": 3}]
        self.assertEqual(_compute_verdict(cand, prov), "VALIDATED")

    def test_caution_medium_score(self):
        cand = self._make_candidate(0.5, 0.5, 0.5, 0.5)
        prov = [{"a": 1}]
        self.assertEqual(_compute_verdict(cand, prov), "CAUTION")

    def test_vetoed_low_score(self):
        cand = self._make_candidate(0.2, 0.2, 0.2, 0.2)
        prov = []
        self.assertEqual(_compute_verdict(cand, prov), "VETOED")

    def test_caution_high_score_sparse_provenance(self):
        cand = self._make_candidate(0.9, 0.9, 0.9, 0.9)
        prov = [{"a": 1}]  # Only 1 provenance entry
        self.assertEqual(_compute_verdict(cand, prov), "CAUTION")


class TestRiskLevel(unittest.TestCase):

    def test_clean_when_no_detections(self):
        self.assertEqual(_compute_risk_level([]), "CLEAN")


class TestProvenanceExtraction(unittest.TestCase):

    def test_provenance_has_four_entries(self):
        cand = ReplacementCandidate(
            name="CMC+SBR",
            use_case=UseCase.BATTERY_BINDER,
            performance_match=0.75,
            processability=0.85,
            cost_factor=0.90,
            availability=0.95,
        )
        prov = _extract_replacement_provenance(cand)
        self.assertEqual(len(prov), 4)

    def test_provenance_has_citation(self):
        cand = ReplacementCandidate(
            name="Test",
            use_case=UseCase.GENERAL,
            performance_match=0.5,
            processability=0.5,
            cost_factor=0.5,
            availability=0.5,
        )
        prov = _extract_replacement_provenance(cand)
        for entry in prov:
            self.assertIn("citation", entry)
            self.assertIsNotNone(entry["citation"])


class TestFunctionToUseCaseMapping(unittest.TestCase):

    def test_binder_maps_to_battery_binder(self):
        uc = PFASComplianceReport._map_function_to_use_case("cathode binder", UseCase.GENERAL)
        self.assertEqual(uc, UseCase.BATTERY_BINDER)

    def test_separator_maps_to_membrane(self):
        uc = PFASComplianceReport._map_function_to_use_case("separator coating", UseCase.GENERAL)
        self.assertEqual(uc, UseCase.MEMBRANE)

    def test_unknown_maps_to_default(self):
        uc = PFASComplianceReport._map_function_to_use_case("mystery part", UseCase.GENERAL)
        self.assertEqual(uc, UseCase.GENERAL)


if __name__ == "__main__":
    unittest.main()
