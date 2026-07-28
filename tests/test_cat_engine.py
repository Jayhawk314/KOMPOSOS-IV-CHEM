# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
CAT Engine Tests

Tests for the Categorical Activity Theory engine:
1. ActivityDiagram construction from ActivitySystem
2. Obstruction detection with known contradictory paths
3. Trust boundary enforcement via fibration lifting
4. OPTIMUS evolution with configurable depth
5. COG evaluate_diagram with real path data
6. Full pipeline integration test
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.category import Category
from categorical.activity_system import (
    ActivitySystem,
    ActivityComponent,
    MorphismClass,
    ContradictionDetector,
)
from categorical.cat_advanced import (
    CATEngine,
    ActivityDiagram,
    Obstruction,
    TrustBoundary,
    FibrationEnforcer,
    PivotViolation,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. ActivityDiagram Construction
# ══════════════════════════════════════════════════════════════════════════════

class TestActivityDiagramConstruction(unittest.TestCase):
    """Test that ActivitySystem -> ActivityDiagram preserves all components."""

    def test_model_activity_preserves_all_components(self):
        system = ActivitySystem("test")
        system.add_component("Alice", ActivityComponent.SUBJECT)
        system.add_component("Bob", ActivityComponent.SUBJECT)
        system.add_component("ToolX", ActivityComponent.TOOL)
        system.add_component("ToolY", ActivityComponent.TOOL)
        system.add_component("GoalA", ActivityComponent.OBJECT)
        system.add_component("RuleZ", ActivityComponent.RULE)
        system.add_component("TeamA", ActivityComponent.COMMUNITY)
        system.add_component("DevOps", ActivityComponent.DIVISION_OF_LABOR)

        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)
        diagram = engine.model_activity(system)

        self.assertEqual(diagram.activity_id, "test")
        self.assertEqual(sorted(diagram.subjects), ["Alice", "Bob"])
        self.assertEqual(sorted(diagram.tools), ["ToolX", "ToolY"])
        self.assertEqual(diagram.objects, ["GoalA"])
        self.assertEqual(diagram.rules, ["RuleZ"])
        self.assertEqual(diagram.community, ["TeamA"])
        self.assertEqual(diagram.division, ["DevOps"])

    def test_empty_system(self):
        system = ActivitySystem("empty")
        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)
        diagram = engine.model_activity(system)

        self.assertEqual(diagram.subjects, [])
        self.assertEqual(diagram.objects, [])
        self.assertEqual(diagram.tools, [])

    def test_primary_accessors(self):
        diagram = ActivityDiagram(
            activity_id="t",
            subjects=["S1", "S2"],
            objects=["O1"],
            tools=["T1"],
            rules=[],
            community=[],
            division=[],
        )
        self.assertEqual(diagram.primary_subject, "S1")
        self.assertEqual(diagram.primary_object, "O1")
        self.assertEqual(diagram.primary_tool, "T1")

    def test_primary_accessors_empty(self):
        diagram = ActivityDiagram(
            activity_id="t",
            subjects=[],
            objects=[],
            tools=[],
            rules=[],
            community=[],
            division=[],
        )
        self.assertEqual(diagram.primary_subject, "unknown_subject")
        self.assertEqual(diagram.primary_object, "unknown_object")
        self.assertEqual(diagram.primary_tool, "unknown_tool")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Obstruction Detection
# ══════════════════════════════════════════════════════════════════════════════

class TestObstructionDetection(unittest.TestCase):
    """Test that non-commuting paths are detected as obstructions."""

    def setUp(self):
        self.category = Category(db_path=":memory:")
        self.engine = CATEngine(self.category, publish_events=False)

    def test_production_triad_contradiction(self):
        """S -> T -> O = 0.72, S -> O = 0.2 => tension = 0.52."""
        self.category.add("Alice")
        self.category.add("ToolX")
        self.category.add("GoalY")
        self.category.connect("Alice", "ToolX", "uses", confidence=0.9)
        self.category.connect("ToolX", "GoalY", "processes", confidence=0.8)
        self.category.connect("Alice", "GoalY", "direct", confidence=0.2)

        diagram = ActivityDiagram(
            activity_id="prod_test",
            subjects=["Alice"],
            objects=["GoalY"],
            tools=["ToolX"],
            rules=[],
            community=[],
            division=[],
        )

        obstructions = self.engine.detect_obstructions(diagram)
        self.assertTrue(len(obstructions) > 0)
        obs = obstructions[0]
        self.assertEqual(obs.triad, "production")
        self.assertEqual(obs.components, ["Alice", "ToolX", "GoalY"])
        self.assertAlmostEqual(obs.tension, 0.52, places=2)
        self.assertEqual(obs.status, "REJECT")

    def test_no_obstruction_when_paths_agree(self):
        """S -> T -> O = 0.81, S -> O = 0.8 => tension = 0.01 (AGREE)."""
        self.category.add("Alice")
        self.category.add("ToolX")
        self.category.add("GoalY")
        self.category.connect("Alice", "ToolX", "uses", confidence=0.9)
        self.category.connect("ToolX", "GoalY", "processes", confidence=0.9)
        self.category.connect("Alice", "GoalY", "direct", confidence=0.8)

        diagram = ActivityDiagram(
            activity_id="agree_test",
            subjects=["Alice"],
            objects=["GoalY"],
            tools=["ToolX"],
            rules=[],
            community=[],
            division=[],
        )

        obstructions = self.engine.detect_obstructions(diagram, tension_threshold=0.1)
        # Tension = |0.81 - 0.8| = 0.01, below threshold
        self.assertEqual(len(obstructions), 0)

    def test_regulation_triad_contradiction(self):
        """Rule-mediated path diverges from direct subject-community path."""
        self.category.add("Alice")
        self.category.add("RuleX")
        self.category.add("TeamA")
        self.category.connect("Alice", "RuleX", "obeys", confidence=0.9)
        self.category.connect("RuleX", "TeamA", "governs", confidence=0.3)
        self.category.connect("Alice", "TeamA", "member_of", confidence=0.9)

        diagram = ActivityDiagram(
            activity_id="reg_test",
            subjects=["Alice"],
            objects=[],
            tools=[],
            rules=["RuleX"],
            community=["TeamA"],
            division=[],
        )

        obstructions = self.engine.detect_obstructions(diagram)
        reg_obs = [o for o in obstructions if o.triad == "regulation"]
        self.assertTrue(len(reg_obs) > 0)
        # Tension = |0.27 - 0.9| = 0.63
        self.assertGreater(reg_obs[0].tension, 0.5)

    def test_hollow_status_when_one_path_missing(self):
        """One path exists, other doesn't => HOLLOW."""
        self.category.add("Alice")
        self.category.add("ToolX")
        self.category.add("GoalY")
        # Only mediated path exists, no direct
        self.category.connect("Alice", "ToolX", "uses", confidence=0.9)
        self.category.connect("ToolX", "GoalY", "processes", confidence=0.8)
        # No Alice -> GoalY direct path

        diagram = ActivityDiagram(
            activity_id="hollow_test",
            subjects=["Alice"],
            objects=["GoalY"],
            tools=["ToolX"],
            rules=[],
            community=[],
            division=[],
        )

        obstructions = self.engine.detect_obstructions(diagram)
        self.assertTrue(len(obstructions) > 0)
        self.assertEqual(obstructions[0].status, "HOLLOW")

    def test_distribution_triad(self):
        """Community -> DoL -> Object vs Community -> Object."""
        self.category.add("TeamA")
        self.category.add("DevOps")
        self.category.add("GoalY")
        self.category.connect("TeamA", "DevOps", "assigns", confidence=0.8)
        self.category.connect("DevOps", "GoalY", "delivers", confidence=0.7)
        self.category.connect("TeamA", "GoalY", "produces", confidence=0.2)

        diagram = ActivityDiagram(
            activity_id="dist_test",
            subjects=[],
            objects=["GoalY"],
            tools=[],
            rules=[],
            community=["TeamA"],
            division=["DevOps"],
        )

        obstructions = self.engine.detect_obstructions(diagram)
        dist_obs = [o for o in obstructions if o.triad == "distribution"]
        self.assertTrue(len(dist_obs) > 0)
        # Tension = |0.56 - 0.2| = 0.36
        self.assertGreater(dist_obs[0].tension, 0.3)


# ══════════════════════════════════════════════════════════════════════════════
# 3. ContradictionDetector Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestContradictionDetectorIntegration(unittest.TestCase):
    """Test that CATEngine delegates to ContradictionDetector properly."""

    def test_detect_contradictions_delegates(self):
        system = ActivitySystem("test")
        system.add_component("Alice", ActivityComponent.SUBJECT)
        system.add_component("GoalY", ActivityComponent.OBJECT)
        system.add_morphism("Alice", "GoalY", MorphismClass.PRODUCTION, confidence=0.9)

        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)
        contradictions = engine.detect_contradictions(system)

        # Should return Contradiction objects (may be empty if no contradictions)
        self.assertIsInstance(contradictions, list)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Trust Boundary Enforcement
# ══════════════════════════════════════════════════════════════════════════════

class TestTrustBoundaryEnforcement(unittest.TestCase):
    """Test FibrationEnforcer for trust boundary violations."""

    def test_no_boundaries_no_violations(self):
        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)

        diagram = ActivityDiagram(
            activity_id="no_bounds",
            subjects=["S"],
            objects=["O"],
            tools=["T"],
            rules=[],
            community=[],
            division=[],
        )

        violations = engine.check_trust_boundaries(diagram)
        self.assertEqual(len(violations), 0)

    def test_trust_boundary_dataclass(self):
        boundary = TrustBoundary(
            name="web_to_kernel",
            source_surface="Application",
            target_surface="KernelSpace",
            policy_rules=["no_direct_syscall", "must_use_sandbox"],
        )
        self.assertEqual(boundary.name, "web_to_kernel")
        self.assertEqual(boundary.source_surface, "Application")
        self.assertEqual(len(boundary.policy_rules), 2)


# ══════════════════════════════════════════════════════════════════════════════
# 5. OPTIMUS Evolution
# ══════════════════════════════════════════════════════════════════════════════

class TestOptimusEvolution(unittest.TestCase):
    """Test that evolve_system triggers OPTIMUS without errors."""

    def test_evolve_with_obstructions(self):
        cat = Category(db_path=":memory:")
        cat.add("A")
        cat.add("B")
        cat.add("C")
        cat.connect("A", "B", "r1", confidence=0.9)
        cat.connect("B", "C", "r2", confidence=0.8)
        cat.connect("A", "C", "r3", confidence=0.3)

        engine = CATEngine(cat, publish_events=False)

        obs = Obstruction(
            activity_id="test",
            triad="production",
            components=["A", "B", "C"],
            tension=0.6,
            status="REJECT",
            description="Test obstruction",
        )

        # Should not raise
        engine.evolve_system("test", [obs], max_steps=3, depth=2)

    def test_evolve_with_no_obstructions(self):
        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)

        # Should not raise with empty list
        engine.evolve_system("test", [], max_steps=5)

    def test_configurable_max_steps(self):
        """Verify max_steps parameter is accepted (for 32-step Mythos pivots)."""
        cat = Category(db_path=":memory:")
        engine = CATEngine(cat, publish_events=False)

        # Should accept large max_steps without error
        engine.evolve_system("test", [], max_steps=32, depth=3)


# ══════════════════════════════════════════════════════════════════════════════
# 6. COG evaluate_diagram
# ══════════════════════════════════════════════════════════════════════════════

class TestCogEvaluateDiagram(unittest.TestCase):
    """Test COG engine evaluate_diagram with real data."""

    def _make_cog(self, category):
        from cog.session import CogSession
        from cog.engine import CogEngine
        session = CogSession(category=category)
        return CogEngine(session)

    def test_evaluate_diagram_production_reject(self):
        cat = Category(db_path=":memory:")
        cat.add("Alice")
        cat.add("ToolX")
        cat.add("GoalY")
        cat.connect("Alice", "ToolX", "uses", confidence=0.9)
        cat.connect("ToolX", "GoalY", "processes", confidence=0.8)
        cat.connect("Alice", "GoalY", "direct", confidence=0.2)

        cog = self._make_cog(cat)

        diagram = ActivityDiagram(
            activity_id="cog_test",
            subjects=["Alice"],
            objects=["GoalY"],
            tools=["ToolX"],
            rules=[],
            community=[],
            division=[],
        )

        result = cog.evaluate_diagram(diagram)
        self.assertEqual(result["activity_id"], "cog_test")
        self.assertIn(result["status"], ["REJECT", "HOLLOW"])
        self.assertGreater(result["evidence_weight"], 0.3)
        self.assertGreater(result["production_tension"], 0.3)

    def test_evaluate_diagram_agree(self):
        cat = Category(db_path=":memory:")
        cat.add("Alice")
        cat.add("ToolX")
        cat.add("GoalY")
        cat.connect("Alice", "ToolX", "uses", confidence=0.9)
        cat.connect("ToolX", "GoalY", "processes", confidence=0.9)
        cat.connect("Alice", "GoalY", "direct", confidence=0.8)

        cog = self._make_cog(cat)

        diagram = ActivityDiagram(
            activity_id="agree_test",
            subjects=["Alice"],
            objects=["GoalY"],
            tools=["ToolX"],
            rules=[],
            community=[],
            division=[],
        )

        result = cog.evaluate_diagram(diagram)
        self.assertEqual(result["status"], "AGREE")
        self.assertLess(result["evidence_weight"], 0.1)

    def test_evaluate_diagram_invalid_type(self):
        cat = Category(db_path=":memory:")
        cog = self._make_cog(cat)
        result = cog.evaluate_diagram("not_a_diagram")
        self.assertEqual(result["status"], "REJECT")

    def test_evaluate_diagram_orphan_empty(self):
        """Empty diagram with no subjects/objects => ORPHAN."""
        cat = Category(db_path=":memory:")
        cog = self._make_cog(cat)

        diagram = ActivityDiagram(
            activity_id="orphan_test",
            subjects=[],
            objects=[],
            tools=[],
            rules=[],
            community=[],
            division=[],
        )

        result = cog.evaluate_diagram(diagram)
        self.assertEqual(result["status"], "ORPHAN")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Full Pipeline Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestFullPipeline(unittest.TestCase):
    """Integration test: system -> diagram -> obstructions -> evolution."""

    def test_full_analysis_pipeline(self):
        cat = Category(db_path=":memory:")
        cat.add("Alice")
        cat.add("ToolX")
        cat.add("GoalY")
        cat.add("RuleZ")
        cat.add("TeamA")
        cat.connect("Alice", "ToolX", "uses", confidence=0.9)
        cat.connect("ToolX", "GoalY", "processes", confidence=0.8)
        cat.connect("Alice", "GoalY", "direct", confidence=0.2)
        cat.connect("Alice", "RuleZ", "obeys", confidence=0.8)
        cat.connect("RuleZ", "TeamA", "governs", confidence=0.7)
        cat.connect("Alice", "TeamA", "member_of", confidence=0.9)

        # Build ActivitySystem
        system = ActivitySystem("pipeline_test")
        system.add_component("Alice", ActivityComponent.SUBJECT)
        system.add_component("ToolX", ActivityComponent.TOOL)
        system.add_component("GoalY", ActivityComponent.OBJECT)
        system.add_component("RuleZ", ActivityComponent.RULE)
        system.add_component("TeamA", ActivityComponent.COMMUNITY)
        system.add_morphism("Alice", "ToolX", MorphismClass.PRODUCTION, 0.9)
        system.add_morphism("ToolX", "GoalY", MorphismClass.PRODUCTION, 0.8)
        system.add_morphism("Alice", "GoalY", MorphismClass.PRODUCTION, 0.2)

        engine = CATEngine(cat, publish_events=False)
        result = engine.full_analysis(system, evolve=True, max_steps=5)

        self.assertIn("diagram", result)
        self.assertIn("obstructions", result)
        self.assertIn("contradictions", result)
        self.assertIn("pivot_violations", result)
        self.assertIn("summary", result)
        self.assertTrue(result["evolved"])
        self.assertGreater(result["summary"]["total_obstructions"], 0)

    def test_full_analysis_with_trust_boundaries(self):
        cat = Category(db_path=":memory:")
        cat.add("WebApp")
        cat.add("KernelCall")
        cat.add("SystemState")
        cat.connect("WebApp", "KernelCall", "invokes", confidence=0.5)
        cat.connect("KernelCall", "SystemState", "modifies", confidence=0.9)

        system = ActivitySystem("boundary_test")
        system.add_component("WebApp", ActivityComponent.SUBJECT)
        system.add_component("KernelCall", ActivityComponent.TOOL)
        system.add_component("SystemState", ActivityComponent.OBJECT)

        boundary = TrustBoundary(
            name="web_to_kernel",
            source_surface="Application",
            target_surface="Kernel",
            policy_rules=["sandbox_required"],
        )

        engine = CATEngine(cat, publish_events=False)
        result = engine.full_analysis(
            system,
            trust_boundaries=[boundary],
        )

        self.assertIn("pivot_violations", result)
        # Violations depend on metadata/type classification
        self.assertIsInstance(result["pivot_violations"], list)


if __name__ == "__main__":
    unittest.main()
