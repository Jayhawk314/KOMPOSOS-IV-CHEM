# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Audit 3: Strategic Hardening Audit

Simulates a 32-step Mythos-style attack chain to verify interdiction.
Focuses on:
  - OPTIMUS Depth Expansion: Look-ahead beyond 32 steps.
  - Fibration Hardening: Enforcing cartesian lifts across "Trust Boundaries".
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.category import Category
from core.optimus import OptimusEngine
from categorical.cat_advanced import CATEngine, ActivityDiagram, TrustBoundary

class StrategicHardeningAudit(unittest.TestCase):
    def setUp(self):
        self.cat = Category("hardening_cat", db_path=":memory:")
        self.optimus = OptimusEngine(self.cat)
        self.cat_engine = CATEngine(self.cat, optimus=self.optimus, publish_events=False)

    def test_32_step_pivot_interdiction(self):
        """Simulate a long 32-step chain and check if OPTIMUS depth expansion works."""
        # Setup a 32-step path in the category
        nodes = [f"node_{i}" for i in range(33)]
        for i in range(33):
            self.cat.add(nodes[i])
        for i in range(32):
            self.cat.connect(nodes[i], nodes[i+1], f"step_{i}", confidence=0.95)

        # Inject a structural "tension" at step 32
        # A direct path with very low confidence, clashing with the long 0.95^32 path
        self.cat.connect(nodes[0], nodes[32], "exploit_path", confidence=0.01)

        diagram = ActivityDiagram(
            activity_id="mythos_32_step",
            subjects=["node_0"],
            objects=["node_32"],
            tools=["exploit_path"],
            rules=[],
            community=[],
            division=[]
        )

        # Verify detection: tool "exploit_path" is not a Category object with
        # morphisms from node_0, so mediated path [node_0, exploit_path, node_32]
        # won't resolve. But direct path [node_0, node_32] = 0.01.
        # The diagram detects HOLLOW (one path missing).
        obstructions = self.cat_engine.detect_obstructions(diagram)
        self.assertTrue(len(obstructions) > 0, "System must detect tension in the 32-step chain")

        # Verify evolution with 32-step depth
        self.cat_engine.evolve_system("mythos_32_step", obstructions, max_steps=32)

    def test_fibration_hardening_trust_boundaries(self):
        """Verify that Trust Boundaries enforce strict cartesian lifts."""
        from categorical.fibrations import GenericFibration

        # Define a "Trust Boundary" as a distinguished Object type
        self.cat.add("Web_Entry", type_name="Web_Surface")
        self.cat.add("Kernel_Sink", type_name="Kernel_Surface")

        # Create a morphism across the boundary (Unauthorized Pivot)
        self.cat.connect("Web_Entry", "Kernel_Sink", "pivot", confidence=0.3)

        # Build fibration from the category backend (store)
        fibration = GenericFibration(self.cat._backend, fiber_key="type")
        fibration.build()

        # Verify that the pivot is classified as "cross_fiber"
        cross_mors = [m for m in fibration.total_morphisms if m.morphism_type == "cross_fiber"]
        self.assertTrue(any(m.source.base == "Web_Surface" and m.target.base == "Kernel_Surface"
                            for m in cross_mors), "Pivot must be identified as a cross-boundary transition")

        # Verify cartesian lift (or lack thereof for unauthorized pivot)
        lifted = fibration.cartesian_lift("Web_Surface", "Kernel_Surface", "Web_Entry")
        self.assertIn("Kernel_Sink", lifted, "Kernel sink must be identified as reachable from Web entry")

    def test_trust_boundary_via_cat_engine(self):
        """Verify CATEngine's FibrationEnforcer detects cross-surface pivots."""
        from categorical.activity_system import ActivitySystem, ActivityComponent

        self.cat.add("WebApp", type_name="Application")
        self.cat.add("KernelFunc", type_name="KernelSpace")
        self.cat.add("UserData", type_name="Application")
        self.cat.connect("WebApp", "KernelFunc", "syscall", confidence=0.3)
        self.cat.connect("KernelFunc", "UserData", "returns", confidence=0.9)

        system = ActivitySystem("boundary_test")
        system.add_component("WebApp", ActivityComponent.SUBJECT)
        system.add_component("KernelFunc", ActivityComponent.TOOL)
        system.add_component("UserData", ActivityComponent.OBJECT)

        boundary = TrustBoundary(
            name="app_to_kernel",
            source_surface="Application",
            target_surface="KernelSpace",
            policy_rules=["sandbox_required", "capability_check"],
        )

        result = self.cat_engine.full_analysis(
            system,
            trust_boundaries=[boundary],
        )

        # The fibration enforcer should find violations for cross-surface morphisms
        self.assertIsInstance(result["pivot_violations"], list)

if __name__ == "__main__":
    unittest.main()
