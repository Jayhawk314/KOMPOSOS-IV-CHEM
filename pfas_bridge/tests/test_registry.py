"""
Tests for pfas_bridge/pfas_registry.py
=======================================

30 tests covering:
- Registry integrity (counts, required fields, CAS format)
- No duplicates
- Cross-reference with polymer_bridge
- Specific regulation checks (PFOA banned, PFHxA Oct 2026)
- Category lookups
- Heuristic detection
"""

import re
import unittest
from datetime import date

from pfas_bridge.pfas_registry import (
    PFAS_REGISTRY,
    PFASCategory,
    PFASSubstance,
    POLYMER_BRIDGE_PFAS,
    RegulationStatus,
    get_all_pfas_names,
    get_banned_pfas,
    get_pfas,
    get_pfas_by_category,
    get_restricted_pfas,
    is_pfas,
)


class TestRegistryIntegrity(unittest.TestCase):
    """Registry-wide data integrity checks."""

    def test_registry_has_at_least_30_substances(self):
        self.assertGreaterEqual(len(PFAS_REGISTRY), 30)

    def test_every_substance_has_name(self):
        for key, sub in PFAS_REGISTRY.items():
            self.assertTrue(sub.name, f"{key} missing name")

    def test_every_substance_has_abbreviation(self):
        for key, sub in PFAS_REGISTRY.items():
            self.assertTrue(sub.abbreviation, f"{key} missing abbreviation")

    def test_every_substance_has_cas_number(self):
        for key, sub in PFAS_REGISTRY.items():
            self.assertTrue(sub.cas_number, f"{key} missing CAS number")

    def test_cas_number_format(self):
        """CAS numbers should match NN..N-NN-N pattern."""
        cas_re = re.compile(r"^\d{2,7}-\d{2}-\d$")
        for key, sub in PFAS_REGISTRY.items():
            self.assertRegex(
                sub.cas_number, cas_re,
                f"{key} CAS '{sub.cas_number}' doesn't match format",
            )

    def test_every_substance_has_category(self):
        for key, sub in PFAS_REGISTRY.items():
            self.assertIsInstance(sub.category, PFASCategory, f"{key}")

    def test_every_substance_has_at_least_one_regulation(self):
        for key, sub in PFAS_REGISTRY.items():
            self.assertGreaterEqual(
                len(sub.regulations), 1,
                f"{key} has no regulations",
            )

    def test_no_duplicate_cas_numbers(self):
        cas_numbers = [sub.cas_number for sub in PFAS_REGISTRY.values()]
        self.assertEqual(len(cas_numbers), len(set(cas_numbers)))

    def test_no_duplicate_abbreviations(self):
        abbrevs = [sub.abbreviation for sub in PFAS_REGISTRY.values()]
        self.assertEqual(len(abbrevs), len(set(abbrevs)))

    def test_all_categories_represented(self):
        """At least 5 of the 7 categories should have entries."""
        represented = {sub.category for sub in PFAS_REGISTRY.values()}
        self.assertGreaterEqual(len(represented), 5)


class TestSpecificSubstances(unittest.TestCase):
    """Spot-checks for key PFAS substances."""

    def test_pfoa_exists(self):
        pfoa = get_pfas("PFOA")
        self.assertIsNotNone(pfoa)
        self.assertEqual(pfoa.cas_number, "335-67-1")

    def test_pfoa_is_banned_eu(self):
        pfoa = get_pfas("PFOA")
        self.assertTrue(pfoa.is_banned("EU"))

    def test_pfoa_is_banned_stockholm(self):
        pfoa = get_pfas("PFOA")
        self.assertTrue(pfoa.is_banned("Stockholm Convention"))

    def test_pfos_exists_and_banned(self):
        pfos = get_pfas("PFOS")
        self.assertIsNotNone(pfos)
        self.assertTrue(pfos.is_banned())

    def test_pfhxa_exists(self):
        pfhxa = get_pfas("PFHxA")
        self.assertIsNotNone(pfhxa)

    def test_pfhxa_ban_date_is_oct_2026(self):
        pfhxa = get_pfas("PFHxA")
        rd = pfhxa.restriction_date()
        self.assertIsNotNone(rd)
        self.assertEqual(rd.year, 2026)
        self.assertEqual(rd.month, 10)

    def test_pvdf_is_fluoropolymer(self):
        pvdf = get_pfas("PVDF")
        self.assertIsNotNone(pvdf)
        self.assertEqual(pvdf.category, PFASCategory.FLUOROPOLYMER)

    def test_ptfe_is_fluoropolymer(self):
        ptfe = get_pfas("PTFE")
        self.assertIsNotNone(ptfe)
        self.assertEqual(ptfe.category, PFASCategory.FLUOROPOLYMER)

    def test_genx_exists(self):
        genx = get_pfas("GenX")
        self.assertIsNotNone(genx)

    def test_nafion_exists(self):
        nafion = get_pfas("Nafion")
        self.assertIsNotNone(nafion)
        self.assertEqual(nafion.category, PFASCategory.FLUOROPOLYMER)


class TestCrossReference(unittest.TestCase):
    """Cross-reference with polymer_bridge."""

    def test_polymer_bridge_pfas_set(self):
        self.assertEqual(POLYMER_BRIDGE_PFAS, {"PVDF", "PTFE"})

    def test_pvdf_in_both_registries(self):
        self.assertIn("PVDF", PFAS_REGISTRY)
        self.assertIn("PVDF", POLYMER_BRIDGE_PFAS)

    def test_ptfe_in_both_registries(self):
        self.assertIn("PTFE", PFAS_REGISTRY)
        self.assertIn("PTFE", POLYMER_BRIDGE_PFAS)


class TestLookupFunctions(unittest.TestCase):
    """Test lookup functions."""

    def test_get_pfas_by_name(self):
        self.assertIsNotNone(get_pfas("PFOA"))

    def test_get_pfas_case_insensitive(self):
        self.assertIsNotNone(get_pfas("pfoa"))
        self.assertIsNotNone(get_pfas("Pfoa"))

    def test_get_pfas_unknown_returns_none(self):
        self.assertIsNone(get_pfas("HDPE"))
        self.assertIsNone(get_pfas("Unobtanium"))

    def test_is_pfas_known_substance(self):
        self.assertTrue(is_pfas("PVDF"))
        self.assertTrue(is_pfas("PTFE"))
        self.assertTrue(is_pfas("PFOA"))

    def test_is_pfas_heuristic(self):
        """Heuristic catches reliable PFAS signals (fluoropolymer, perfluoro, brands)."""
        self.assertTrue(is_pfas("fluoropolymer_X"))
        self.assertTrue(is_pfas("SomePerfluoroCompound"))
        # Bare 'fluoro' is intentionally NOT a PFAS signal: fluorobenzene,
        # 5-fluorouracil, etc. are fluorinated but not PFAS. They route to the
        # structural OECD path instead.
        self.assertFalse(is_pfas("fluorobenzene"))

    def test_is_pfas_non_pfas(self):
        self.assertFalse(is_pfas("HDPE"))
        self.assertFalse(is_pfas("CMC"))
        self.assertFalse(is_pfas("Polyethylene"))

    def test_get_all_pfas_names_sorted(self):
        names = get_all_pfas_names()
        self.assertEqual(names, sorted(names))
        self.assertGreaterEqual(len(names), 30)

    def test_get_pfas_by_category(self):
        fluoropolymers = get_pfas_by_category(PFASCategory.FLUOROPOLYMER)
        self.assertIn("PVDF", fluoropolymers)
        self.assertIn("PTFE", fluoropolymers)

    def test_get_banned_pfas(self):
        banned = get_banned_pfas()
        self.assertIn("PFOA", banned)
        self.assertIn("PFOS", banned)

    def test_get_restricted_pfas(self):
        restricted = get_restricted_pfas()
        # Should include banned + restricted substances
        self.assertIn("PFOA", restricted)


class TestSerialization(unittest.TestCase):
    """Test to_dict serialization."""

    def test_to_dict_has_required_fields(self):
        pfoa = get_pfas("PFOA")
        d = pfoa.to_dict()
        self.assertIn("name", d)
        self.assertIn("abbreviation", d)
        self.assertIn("cas_number", d)
        self.assertIn("category", d)
        self.assertIn("regulations", d)


if __name__ == "__main__":
    unittest.main()
