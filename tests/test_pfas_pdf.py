# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Tests for PFAS PDF report generation."""

import unittest
from datetime import date

from reports.pfas_report import PFASComplianceReport, MaterialInput, LI_ION_DEMO_BOM
from reports.pfas_pdf import generate_pfas_pdf


class TestPDFGeneration(unittest.TestCase):
    """Test that PDF generation produces valid output."""

    @classmethod
    def setUpClass(cls):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        cls.report = gen.screen_portfolio(LI_ION_DEMO_BOM)
        cls.pdf_bytes = generate_pfas_pdf(cls.report)

    def test_pdf_returns_bytes(self):
        self.assertIsInstance(self.pdf_bytes, bytes)

    def test_pdf_starts_with_pdf_header(self):
        self.assertTrue(self.pdf_bytes.startswith(b"%PDF"))

    def test_pdf_is_not_empty(self):
        self.assertGreater(len(self.pdf_bytes), 1000)

    def test_pdf_has_multiple_pages(self):
        # PDF with 15 materials should have multiple pages
        # Count page markers in the PDF
        page_count = self.pdf_bytes.count(b"/Type /Page")
        # The Pages object also matches, so subtract catalog references
        self.assertGreaterEqual(page_count, 3)

    def test_clean_report_generates_pdf(self):
        """A BOM with no PFAS should still produce a valid PDF."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        clean_report = gen.screen_portfolio([
            MaterialInput(name="NMC811", function="cathode"),
            MaterialInput(name="Graphite", function="anode"),
        ])
        pdf = generate_pfas_pdf(clean_report)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)

    def test_single_detection_generates_pdf(self):
        """A BOM with exactly one PFAS substance."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio([
            MaterialInput(name="PVDF", function="binder"),
        ])
        pdf = generate_pfas_pdf(report)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)

    def test_full_bom_pdf_larger_than_single(self):
        """Full BOM PDF should be larger than single-material PDF."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        single_report = gen.screen_portfolio([
            MaterialInput(name="PVDF", function="binder"),
        ])
        single_pdf = generate_pfas_pdf(single_report)
        self.assertGreater(len(self.pdf_bytes), len(single_pdf))

    def test_generate_pfas_pdf_is_callable(self):
        """Verify the public API function exists and is callable."""
        self.assertTrue(callable(generate_pfas_pdf))


class TestPDFWithCustomBOM(unittest.TestCase):
    """Test PDF generation with various custom BOMs."""

    def test_many_materials(self):
        """BOM with many materials should not crash."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        materials = [
            MaterialInput(name=f"Material_{i}", function="test")
            for i in range(20)
        ]
        report = gen.screen_portfolio(materials)
        pdf = generate_pfas_pdf(report)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_materials_with_quantities(self):
        """Materials with quantity_kg should not crash."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        materials = [
            MaterialInput(name="PVDF", function="binder", quantity_kg=2.5),
            MaterialInput(name="NMC811", function="cathode", quantity_kg=45.0),
        ]
        report = gen.screen_portfolio(materials)
        pdf = generate_pfas_pdf(report)
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestClientName(unittest.TestCase):
    """Test client name branding in report and PDF."""

    def test_client_name_stored_in_report(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio(
            [MaterialInput(name="NMC811", function="cathode")],
            client_name="Acme Corp",
        )
        self.assertEqual(report.client_name, "Acme Corp")

    def test_client_name_in_to_dict(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio(
            [MaterialInput(name="NMC811", function="cathode")],
            client_name="TestCo",
        )
        d = report.to_dict()
        self.assertEqual(d["client_name"], "TestCo")

    def test_client_name_default_empty(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio(
            [MaterialInput(name="NMC811", function="cathode")],
        )
        self.assertEqual(report.client_name, "")

    def test_pdf_with_client_name(self):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio(
            LI_ION_DEMO_BOM, client_name="Acme Battery Corp",
        )
        pdf = generate_pfas_pdf(report)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)


class TestDomainScores(unittest.TestCase):
    """Test cross-bridge domain-specific scores in replacement analysis."""

    @classmethod
    def setUpClass(cls):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        cls.report = gen.screen_portfolio(LI_ION_DEMO_BOM)

    def test_pvdf_cmcsb_has_domain_scores(self):
        """CMC+SBR should get domain scores when NMC811 is in BOM."""
        pvdf_det = None
        for det in self.report.detections:
            if det.material == "PVDF":
                pvdf_det = det
                break
        self.assertIsNotNone(pvdf_det)

        cmcsb = None
        for rep in pvdf_det.replacements:
            if "CMC" in rep.name:
                cmcsb = rep
                break
        self.assertIsNotNone(cmcsb)
        self.assertIn("adhesion", cmcsb.domain_scores)
        self.assertIn("electrolyte", cmcsb.domain_scores)
        self.assertIn("thermal", cmcsb.domain_scores)
        self.assertIn("cathode", cmcsb.domain_scores)

    def test_domain_scores_are_floats(self):
        for det in self.report.detections:
            for rep in det.replacements:
                for key, val in rep.domain_scores.items():
                    self.assertIsInstance(val, float, f"{rep.name}.{key}")

    def test_cross_bridge_details_populated(self):
        """At least one replacement should have cross-bridge details."""
        has_cb = False
        for det in self.report.detections:
            for rep in det.replacements:
                if rep.cross_bridge_details:
                    has_cb = True
                    self.assertIn("polymer_tested", rep.cross_bridge_details)
                    self.assertIn("battery_material", rep.cross_bridge_details)
        self.assertTrue(has_cb, "No cross-bridge details found in any replacement")

    def test_no_cathode_gives_empty_domain_scores(self):
        """BOM without cathode should produce empty domain scores."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        report = gen.screen_portfolio([
            MaterialInput(name="PVDF", function="binder"),
        ])
        for det in report.detections:
            for rep in det.replacements:
                self.assertEqual(rep.domain_scores, {})

    def test_domain_scores_in_to_dict(self):
        for det in self.report.detections:
            for rep in det.replacements:
                d = rep.to_dict()
                self.assertIn("domain_scores", d)
                self.assertIn("cross_bridge_details", d)


class TestNarrativeContent(unittest.TestCase):
    """Test that the upgraded PDF has richer content."""

    @classmethod
    def setUpClass(cls):
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        cls.report = gen.screen_portfolio(
            LI_ION_DEMO_BOM, client_name="TestCo",
        )
        cls.pdf_bytes = generate_pfas_pdf(cls.report)

    def test_pdf_larger_with_narratives(self):
        """Upgraded PDF with full BOM should be larger than clean-only."""
        gen = PFASComplianceReport(reference_date=date(2026, 3, 24))
        clean_report = gen.screen_portfolio([
            MaterialInput(name="NMC811", function="cathode"),
            MaterialInput(name="Graphite", function="anode"),
        ])
        clean_pdf = generate_pfas_pdf(clean_report)
        # Full BOM with detections + narratives should be much larger
        self.assertGreater(len(self.pdf_bytes), len(clean_pdf) * 1.5)

    def test_pdf_more_pages_than_old(self):
        """Upgraded PDF should have more pages (richer content)."""
        page_count = self.pdf_bytes.count(b"/Type /Page")
        self.assertGreaterEqual(page_count, 4)


if __name__ == "__main__":
    unittest.main()
