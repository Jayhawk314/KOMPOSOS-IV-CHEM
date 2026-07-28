# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Tests for pfas_bridge/replacement_scorer.py
=============================================

25 tests covering:
- Scores in [0,1]
- Known mappings return candidates
- Candidates sorted by score
- Replacements are non-PFAS
- Use-case-specific lookups
"""

import unittest

from pfas_bridge.replacement_scorer import (
    REPLACEMENT_MAP,
    ReplacementCandidate,
    UseCase,
    find_replacements,
    get_all_replaceable_pfas,
    get_use_cases_for_pfas,
    score_replacement,
)
from pfas_bridge.pfas_registry import is_pfas


class TestReplacementMapIntegrity(unittest.TestCase):
    """Data integrity for the replacement map."""

    def test_replacement_map_not_empty(self):
        self.assertGreater(len(REPLACEMENT_MAP), 0)

    def test_all_scores_in_range(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertGreaterEqual(c.performance_match, 0.0, f"{c.name}")
                self.assertLessEqual(c.performance_match, 1.0, f"{c.name}")
                self.assertGreaterEqual(c.processability, 0.0, f"{c.name}")
                self.assertLessEqual(c.processability, 1.0, f"{c.name}")
                self.assertGreaterEqual(c.cost_factor, 0.0, f"{c.name}")
                self.assertLessEqual(c.cost_factor, 1.0, f"{c.name}")
                self.assertGreaterEqual(c.availability, 0.0, f"{c.name}")
                self.assertLessEqual(c.availability, 1.0, f"{c.name}")

    def test_overall_score_in_range(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertGreaterEqual(c.overall_score, 0.0, f"{c.name}")
                self.assertLessEqual(c.overall_score, 1.0, f"{c.name}")

    def test_every_candidate_has_name(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertTrue(c.name, f"Candidate in {key} missing name")

    def test_every_candidate_has_use_case(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertIsInstance(c.use_case, UseCase)

    def test_candidates_have_advantages(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertGreater(
                    len(c.advantages), 0,
                    f"{c.name} has no advantages listed",
                )


class TestPVDFBatteryBinder(unittest.TestCase):
    """Test PVDF battery binder replacements (critical use case)."""

    def test_pvdf_binder_has_replacements(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        self.assertGreater(len(candidates), 0)

    def test_pvdf_binder_includes_cmc_sbr(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        names = [c.name for c in candidates]
        self.assertIn("CMC+SBR", names)

    def test_pvdf_binder_includes_pan(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        names = [c.name for c in candidates]
        self.assertIn("PAN", names)

    def test_pvdf_binder_sorted_by_score(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        scores = [c.overall_score for c in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_pvdf_binder_cmc_sbr_top_scorer(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        self.assertEqual(candidates[0].name, "CMC+SBR")


class TestPTFESealGasket(unittest.TestCase):
    """Test PTFE seal/gasket replacements."""

    def test_ptfe_seal_has_replacements(self):
        candidates = find_replacements("PTFE", UseCase.SEAL_GASKET)
        self.assertGreater(len(candidates), 0)

    def test_ptfe_seal_includes_epdm(self):
        candidates = find_replacements("PTFE", UseCase.SEAL_GASKET)
        names = [c.name for c in candidates]
        self.assertIn("EPDM", names)

    def test_ptfe_seal_sorted(self):
        candidates = find_replacements("PTFE", UseCase.SEAL_GASKET)
        scores = [c.overall_score for c in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestReplacementsAreNonPFAS(unittest.TestCase):
    """Ensure replacement candidates are not themselves PFAS."""

    def test_no_pfas_in_replacements(self):
        for key, candidates in REPLACEMENT_MAP.items():
            for c in candidates:
                self.assertFalse(
                    is_pfas(c.name),
                    f"Replacement '{c.name}' for {key[0]} is itself PFAS",
                )


class TestLookupFunctions(unittest.TestCase):
    """Test lookup and scoring functions."""

    def test_find_replacements_unknown_pfas(self):
        candidates = find_replacements("UnknownPFAS", UseCase.GENERAL)
        self.assertEqual(len(candidates), 0)

    def test_score_replacement_found(self):
        candidate = score_replacement("PVDF", "CMC+SBR", UseCase.BATTERY_BINDER)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.name, "CMC+SBR")

    def test_score_replacement_not_found(self):
        candidate = score_replacement("PVDF", "Diamond", UseCase.BATTERY_BINDER)
        self.assertIsNone(candidate)

    def test_get_all_replaceable_pfas(self):
        names = get_all_replaceable_pfas()
        self.assertIn("PVDF", names)
        self.assertIn("PTFE", names)

    def test_get_use_cases_for_pvdf(self):
        use_cases = get_use_cases_for_pfas("PVDF")
        self.assertIn(UseCase.BATTERY_BINDER, use_cases)
        self.assertIn(UseCase.MEMBRANE, use_cases)

    def test_find_replacements_fallback_all_use_cases(self):
        """When specific use case not found, should aggregate all."""
        candidates = find_replacements("PVDF", UseCase.GENERAL)
        self.assertGreater(len(candidates), 0)


class TestSerialization(unittest.TestCase):
    """Test to_dict serialization."""

    def test_to_dict_has_fields(self):
        candidates = find_replacements("PVDF", UseCase.BATTERY_BINDER)
        d = candidates[0].to_dict()
        self.assertIn("name", d)
        self.assertIn("overall_score", d)
        self.assertIn("performance_match", d)
        self.assertIn("advantages", d)
        self.assertIn("limitations", d)


if __name__ == "__main__":
    unittest.main()
