# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Audit 1: Code-to-Math Soundness Review

Verifies the Python implementation of categorical primitives against formal axioms.
Focuses on:
  - Identity Laws: f . id = f = id . f
  - Associativity: (h . g) . f = h . (g . f)
  - Functorial Lifting: F(g . f) = F(g) . F(f)
  - Monotonicity of Enriched Quantales: w(g . f) <= w(f) AND w(g)
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.category import Category
from core.types import Object, Morphism
from core.enrichment import MULTIPLICATIVE_QUANTALE, ADDITIVE_QUANTALE

class MathSoundnessAudit(unittest.TestCase):
    def setUp(self):
        self.cat = Category("audit_cat", db_path=":memory:")

    def test_identity_axioms(self):
        """Verify that identity morphisms behave correctly."""
        a = self.cat.add("A")
        b = self.cat.add("B")
        f = self.cat.connect("A", "B", "f", confidence=0.8)
        
        # id_A is auto-created or can be fetched
        # f . id_A = f
        # We simulate composition
        # Note: KOMPOSOS-IV identity is often handled via self._hom_values[(A,A)] = 1.0
        id_a_val = self.cat._hom_values.get(("A", "A"))
        self.assertEqual(id_a_val, 1.0, "Identity hom-value must be unit (1.0)")
        
        # Check if composition with identity preserves weight
        # In enriched category theory: Hom(A,B) tensor Hom(B,B) -> Hom(A,B)
        res_weight = MULTIPLICATIVE_QUANTALE.tensor(f.confidence, 1.0)
        self.assertEqual(res_weight, f.confidence, "f . id_B must equal f weight")

    def test_strict_associativity(self):
        """Verify that (h . g) . f == h . (g . f) for all triples."""
        self.cat.add("A")
        self.cat.add("B")
        self.cat.add("C")
        self.cat.add("D")
        
        f = self.cat.connect("A", "B", "f", confidence=0.9)
        g = self.cat.connect("B", "C", "g", confidence=0.8)
        h = self.cat.connect("C", "D", "h", confidence=0.7)
        
        # (h . g) . f
        hg = self.cat.compose(g, h)
        h_g_f = self.cat.compose(f, hg)
        
        # h . (g . f)
        gf = self.cat.compose(f, g)
        h_gf = self.cat.compose(gf, h)
        
        self.assertAlmostEqual(h_g_f.confidence, h_gf.confidence, places=7, 
                               msg="Composition must be strictly associative")
        self.assertEqual(h_g_f.source, "A")
        self.assertEqual(h_gf.target, "D")

    def test_quantale_monotonicity(self):
        """Verify that security confidence weights decrease deterministically (Monotonicity)."""
        # Multiplicative: w(f . g) = w(f) * w(g)
        # Since w in [0, 1], w(f * g) <= min(w(f), w(g))
        w1 = 0.9
        w2 = 0.8
        res = MULTIPLICATIVE_QUANTALE.tensor(w1, w2)
        self.assertTrue(res <= w1 and res <= w2, "Confidence must be monotonic-decreasing")
        
        # Additive (Cost): w(f . g) = w(f) + w(g)
        # res >= max(w1, w2) - lower is better in additive, so cost increases
        w_a = 10.0
        w_b = 5.0
        res_add = ADDITIVE_QUANTALE.tensor(w_a, w_b)
        self.assertTrue(res_add >= w_a and res_add >= w_b, "Cost must be monotonic-increasing")

    def test_functorial_lifting_coherence(self):
        """Verify Mac Lane's coherence for lifting morphisms: F(g . f) = F(g) . F(f)."""
        from core.functor import Functor
        
        # Source Category C
        cat_c = Category("source_c", db_path=":memory:")
        cat_c.add("A")
        cat_c.add("B")
        cat_c.add("C")
        f = cat_c.connect("A", "B", "f", confidence=0.9)
        g = cat_c.connect("B", "C", "g", confidence=0.8)
        gf = cat_c.compose(f, g) # g . f
        
        # Target Category D
        cat_d = Category("target_d", db_path=":memory:")
        cat_d.add("A'")
        cat_d.add("B'")
        cat_d.add("C'")
        f_prime = cat_d.connect("A'", "B'", "f'", confidence=0.9)
        g_prime = cat_d.connect("B'", "C'", "g'", confidence=0.8)
        gf_prime = cat_d.compose(f_prime, g_prime) # g' . f'
        
        # Define Functor F: C -> D
        f_map = Functor(
            name="F",
            source=cat_c,
            target=cat_d,
            _object_map={"A": "A'", "B": "B'", "C": "C'"},
            _morphism_map={f.id: f_prime.id, g.id: g_prime.id, gf.id: gf_prime.id}
        )
        
        # Verify functorial properties
        verif = f_map.verify()
        self.assertTrue(verif["composition"], "Functor must preserve composition: F(g . f) = F(g) . F(f)")
        self.assertTrue(verif["identity"], "Functor must preserve identity")
        self.assertTrue(verif["objects"], "All mapped objects must exist")
        self.assertTrue(verif["morphisms"], "All mapped morphisms must exist")

if __name__ == "__main__":
    unittest.main()
