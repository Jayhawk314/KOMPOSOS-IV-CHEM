# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""Tests for the glass-metal, metal-semiconductor, and polymer-glass cross-bridges.

These assert *general physics*, not benchmark-specific answers: each bridge is
checked on representative compatible and incompatible pairs and for
order-independence and honest abstention on unknown materials.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cross_bridge.glass_metal import (
    score_glass_metal_compatibility,
    UnknownMaterialError as GMUnknown,
)
from cross_bridge.metal_semiconductor import (
    score_metal_semiconductor_compatibility,
    UnknownMaterialError as MSUnknown,
)
from cross_bridge.polymer_glass import (
    score_polymer_glass_compatibility,
    UnknownMaterialError as PGUnknown,
)


class TestGlassMetal(unittest.TestCase):
    def test_kovar_borosilicate_matched_seal(self):
        r = score_glass_metal_compatibility("Kovar", "Borosilicate")
        self.assertTrue(r.compatible)
        self.assertGreater(r.cte_compatibility, 0.6)

    def test_titanium_glass_fails_on_reactivity_not_cte(self):
        r = score_glass_metal_compatibility("Titanium", "Soda_Lime")
        self.assertFalse(r.compatible)
        # CTE is actually a good match; the failure must be chemical reactivity.
        self.assertGreater(r.cte_compatibility, 0.8)
        self.assertLess(r.chemical_compatibility, 0.3)

    def test_order_independent(self):
        a = score_glass_metal_compatibility("Kovar", "Borosilicate")
        b = score_glass_metal_compatibility("Borosilicate", "Kovar")
        self.assertAlmostEqual(a.score, b.score, places=4)

    def test_abstains_on_unknown(self):
        with self.assertRaises(GMUnknown):
            score_glass_metal_compatibility("NOTAGLASS", "NOTAMETAL")


class TestMetalSemiconductor(unittest.TestCase):
    def test_standard_si_contacts(self):
        for metal in ("Cu", "Al"):
            r = score_metal_semiconductor_compatibility(metal, "Si")
            self.assertTrue(r.compatible, metal)

    def test_reactive_on_compound_semiconductor(self):
        r = score_metal_semiconductor_compatibility("Al", "GaAs")
        self.assertFalse(r.compatible)

    def test_order_independent(self):
        a = score_metal_semiconductor_compatibility("Cu", "Si")
        b = score_metal_semiconductor_compatibility("Si", "Cu")
        self.assertAlmostEqual(a.score, b.score, places=4)

    def test_abstains_on_unknown(self):
        with self.assertRaises(MSUnknown):
            score_metal_semiconductor_compatibility("NOPE", "ALSONOPE")


class TestPolymerGlass(unittest.TestCase):
    def test_epoxy_bonds_glass(self):
        r = score_polymer_glass_compatibility("Epoxy", "Borosilicate")
        self.assertTrue(r.compatible)

    def test_silicone_bonds_glass(self):
        r = score_polymer_glass_compatibility("Silicone", "Soda_Lime")
        self.assertTrue(r.compatible)

    def test_fluoropolymer_poor_adhesion(self):
        r = score_polymer_glass_compatibility("PTFE", "Soda_Lime")
        self.assertFalse(r.compatible)

    def test_order_independent(self):
        a = score_polymer_glass_compatibility("Epoxy", "Borosilicate")
        b = score_polymer_glass_compatibility("Borosilicate", "Epoxy")
        self.assertAlmostEqual(a.score, b.score, places=4)

    def test_abstains_on_unknown(self):
        with self.assertRaises(PGUnknown):
            score_polymer_glass_compatibility("NOTAPOLYMER", "NOTAGLASS")


if __name__ == "__main__":
    unittest.main()
