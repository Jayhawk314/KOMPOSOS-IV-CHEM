# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Audit 2: Split-Brain Injection Audit

Tests the dual-engine (ZFC vs CAT) stability by injecting conflicting results.
Ensures System 3 handles "Split-Brain Scenarios" cleanly.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from zfc.category_bridge import DualEngineBridge, DualResult
from zfc.meta_kan import DeltaType
from zfc.category_store_adapter import StoreAdapter
from core.category import Category

class SplitBrainAudit(unittest.TestCase):
    def setUp(self):
        self.cat = Category("split_brain_cat", db_path=":memory:")
        self.adapter = StoreAdapter(self.cat)
        self.bridge = DualEngineBridge(self.adapter, category=self.cat)

    def test_split_brain_conflict_resolution(self):
        """Inject a scenario where ZFC and CAT engines disagree."""
        # Mocking the internal verifiers
        # ZFC says AGREE (Logical entailment exists)
        # CAT says REJECT (Structural violation exists)
        
        self.bridge.logic.predict_relation = MagicMock(return_value=(True, 0.9, "Entailed via Axiom X"))
        
        # Mock CategoricalVerifier
        mock_verdict = MagicMock()
        mock_verdict.structural_confidence = 0.1
        mock_verdict.path_count = 0
        mock_verdict.path_lengths = []
        mock_verdict.geometric_class.name = "INCONSISTENT"
        mock_verdict.explanation = "Coherence Gap Found"
        
        self.bridge._verifier = MagicMock()
        self.bridge._verifier.verify = MagicMock(return_value=mock_verdict)
        
        # This should trigger System 3 to record the disagreement
        result = self.bridge.query("User", "Admin", "privilege_escalation")
        
        self.assertEqual(result.delta_type.name, "ORPHAN", 
                         "If ZFC agrees but CAT rejects, delta should be ORPHAN.")
        
        # Check if System 3 recorded the episode
        episodes = list(self.bridge.system3.history.episodes.values())
        self.assertTrue(len(episodes) > 0, "System 3 must record the disagreement episode")
        self.assertEqual(episodes[0].delta_type.name, "ORPHAN", "Episode must be recorded as ORPHAN")

    def test_infinite_loop_prevention(self):
        """Ensure that recursive verification doesn't enter an infinite loop during conflict."""
        # Create a cyclic dependency in the category: A -> B -> A
        self.cat.add("A")
        self.cat.add("B")
        self.cat.connect("A", "B", "r1", confidence=0.9)
        self.cat.connect("B", "A", "r2", confidence=0.9)
        
        # Mock verifiers to always trigger deep-tier checks
        self.bridge.logic.predict_relation = MagicMock(return_value=(True, 0.5, "Cyclic ZFC"))
        
        mock_verdict = MagicMock()
        mock_verdict.structural_confidence = 0.5
        mock_verdict.path_count = 1
        mock_verdict.path_lengths = [2]
        mock_verdict.geometric_class.name = "CYCLIC"
        mock_verdict.explanation = "Cyclic CAT"
        
        self.bridge._verifier = MagicMock()
        self.bridge._verifier.verify = MagicMock(return_value=mock_verdict)
        
        # This call should terminate safely due to depth limits or cycle detection in COG
        try:
            result = self.bridge.query("A", "B", "r1")
            self.assertIsNotNone(result)
        except RecursionError:
            self.fail("DualEngineBridge entered an infinite recursion loop!")

if __name__ == "__main__":
    unittest.main()
