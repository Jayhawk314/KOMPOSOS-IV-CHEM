# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Advanced Categorical Activity Theory (CAT) Engine for KOMPOSOS-IV

Formalizes Engestrom's Activity Theory using Grothendieck Fibrations,
ContradictionDetector, and OPTIMUS for real-time interdiction of
multi-stage pivots and structural evolution.

Key Concepts:
  - ActivityDiagram: Formal diagram (S, O, T, R, C, D) with trust boundaries.
  - Obstruction: Non-commuting diagram quantified as cohomological tension.
  - TrustBoundary: Explicit categorical Object forcing cartesian lifts across
    security surfaces (Fibration Hardening).
  - FibrationEnforcer: Wraps GenericFibration to enforce cartesian lifts on
    activity diagrams -- blocks cross-surface pivots that fail to lift.
  - Dialectical Evolution: OPTIMUS morphism factorization to resolve tension.

Integrates with:
  - activity_system.py: ContradictionDetector (primary/secondary/tertiary/quaternary)
  - fibrations.py: GenericFibration (cartesian lifts, cross-fiber paths)
  - core/optimus.py: OptimusEngine (categorical gradient descent)
  - core/threat_intelligence_bus.py: ThreatIntelligenceBus (event publishing)

Mathematical basis:
  - Engestrom, Y. (1987). Learning by Expanding.
  - Grothendieck, A. (1961). Technique de descente.
  - Riehl & Verity (2022). Elements of infinity-Category Theory.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .activity_system import (
    ActivitySystem,
    ActivityComponent,
    MorphismClass,
    ContradictionDetector,
    Contradiction,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class TrustBoundary:
    """
    An explicit security boundary registered as a categorical Object.

    Forces strict cartesian lifts when activity morphisms cross from
    source_surface to target_surface. If the lift fails (no valid
    morphism in the fibration), the pivot is blocked.

    This implements the "Fibration Hardening" recommendation: since
    Mythos excels at Cross-Surface Fibrations (web -> kernel), we
    register trust boundaries as explicit Objects in the ActivityDiagram
    to force compliance checking.
    """
    name: str
    source_surface: str       # e.g., "Application", "UserSpace"
    target_surface: str       # e.g., "Network", "KernelSpace"
    policy_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityDiagram:
    """
    A formal categorical diagram representing an Activity System.

    Unlike a flat 6-tuple, this preserves ALL components per type
    (multiple subjects, tools, etc.) and carries trust boundaries.
    """
    activity_id: str
    subjects: List[str]       # S: Agents / Plugins / Processes
    objects: List[str]        # O: Target Type Spaces / Goals
    tools: List[str]          # T: Mediating Morphisms / Scripts / API calls
    rules: List[str]          # R: Constraints / Policy Invariants
    community: List[str]      # C: Interconnected Plugins / Agents / Networks
    division: List[str]       # D: Task Allocation / Role Assignment
    trust_boundaries: List[TrustBoundary] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_subject(self) -> str:
        return self.subjects[0] if self.subjects else "unknown_subject"

    @property
    def primary_object(self) -> str:
        return self.objects[0] if self.objects else "unknown_object"

    @property
    def primary_tool(self) -> str:
        return self.tools[0] if self.tools else "unknown_tool"


@dataclass
class Obstruction:
    """
    A cohomological obstruction in the activity diagram.

    Represents a failure of a diagram to commute, quantified as a
    tensor-valued tension metric. Status maps to COG vocabulary:
    AGREE/ORPHAN/HOLLOW/REJECT.
    """
    activity_id: str
    triad: str                  # "production", "regulation", "distribution"
    components: List[str]       # Nodes involved in the non-commuting diagram
    tension: float              # 0.0 = commutes, higher = greater friction
    status: str                 # COG vocabulary: AGREE, ORPHAN, HOLLOW, REJECT
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PivotViolation:
    """
    A trust boundary violation detected by the FibrationEnforcer.

    Represents a cross-surface pivot that failed to produce a
    cartesian lift -- the operation is structurally unauthorized.
    """
    boundary: TrustBoundary
    source_element: str
    target_element: str
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Fibration Enforcer
# =============================================================================

class FibrationEnforcer:
    """
    Enforces cartesian lifts across trust boundaries using GenericFibration.

    When an activity diagram includes trust boundaries, the enforcer
    checks that every morphism crossing a boundary has a valid cartesian
    lift in the fibration. If not, the pivot is blocked.

    This addresses the "Fibration Hardening" recommendation: Mythos
    excels at Cross-Surface Fibrations, so we force strict compliance.
    """

    def __init__(self, category):
        self.category = category

    def check_boundaries(
        self,
        diagram: ActivityDiagram,
        fiber_key: str = "type",
    ) -> List[PivotViolation]:
        """
        Check all trust boundaries in the diagram for lift violations.

        For each trust boundary, verifies that morphisms crossing from
        source_surface to target_surface have valid cartesian lifts.

        Args:
            diagram: The ActivityDiagram with trust boundaries.
            fiber_key: The metadata key used to classify objects into
                       fibers/surfaces (default: "type").

        Returns:
            List of PivotViolation for each failed lift.
        """
        if not diagram.trust_boundaries:
            return []

        violations = []

        # Build the fibration from the category's backend store
        # (GenericFibration expects list_objects/list_morphisms interface)
        try:
            from .fibrations import GenericFibration
            fibration = GenericFibration(self.category._backend, fiber_key=fiber_key)
            fibration.build()
        except Exception as e:
            logger.warning(f"Could not build fibration: {e}")
            return violations

        # For each trust boundary, check that cross-surface morphisms lift
        # AND that the crossing morphism has sufficient confidence.
        # A low-confidence crossing indicates an unauthorized/suspicious pivot
        # even if a fibration lift technically exists.
        CONFIDENCE_THRESHOLD = 0.3

        for boundary in diagram.trust_boundaries:
            # Get all activity components that might cross this boundary
            crossers = self._find_cross_boundary_morphisms(
                diagram, boundary, fiber_key
            )

            for src, tgt in crossers:
                # Attempt cartesian lift
                lifted = fibration.cartesian_lift(
                    boundary.source_surface,
                    boundary.target_surface,
                    src,
                )

                # Also check the crossing morphism's confidence:
                # a low-confidence cross-boundary morphism is suspicious
                # regardless of whether a technical lift exists.
                crossing_confidence = 1.0
                for mor in self.category.morphisms_from(src):
                    if mor.target == tgt:
                        crossing_confidence = mor.confidence
                        break

                if not lifted or crossing_confidence < CONFIDENCE_THRESHOLD:
                    reason = "no cartesian lift" if not lifted else (
                        f"low-confidence crossing ({crossing_confidence:.2f})"
                    )
                    violations.append(PivotViolation(
                        boundary=boundary,
                        source_element=src,
                        target_element=tgt,
                        description=(
                            f"Cross-surface pivot blocked: {src} "
                            f"({boundary.source_surface}) -> {tgt} "
                            f"({boundary.target_surface}): {reason}. "
                            f"Policy: {boundary.policy_rules}"
                        ),
                        evidence={
                            "source_surface": boundary.source_surface,
                            "target_surface": boundary.target_surface,
                            "boundary": boundary.name,
                            "attempted_source": src,
                            "attempted_target": tgt,
                            "crossing_confidence": crossing_confidence,
                        },
                    ))

        return violations

    def _find_cross_boundary_morphisms(
        self,
        diagram: ActivityDiagram,
        boundary: TrustBoundary,
        fiber_key: str,
    ) -> List[Tuple[str, str]]:
        """
        Find morphisms in the category that cross the given trust boundary.

        Returns (source_name, target_name) pairs for morphisms where
        source is in boundary.source_surface and target is in
        boundary.target_surface.
        """
        crossers = []

        # Collect all diagram node names
        all_nodes = set(
            diagram.subjects + diagram.objects + diagram.tools +
            diagram.rules + diagram.community + diagram.division
        )

        for node in all_nodes:
            obj = self.category.get(node)
            if obj is None:
                continue

            # Determine this node's surface
            node_surface = getattr(obj, 'type_name', '') or ''
            if hasattr(obj, 'metadata') and isinstance(obj.metadata, dict):
                node_surface = obj.metadata.get(fiber_key, node_surface)

            if node_surface != boundary.source_surface:
                continue

            # Check outgoing morphisms
            for mor in self.category.morphisms_from(node):
                target_obj = self.category.get(mor.target)
                if target_obj is None:
                    continue

                target_surface = getattr(target_obj, 'type_name', '') or ''
                if hasattr(target_obj, 'metadata') and isinstance(target_obj.metadata, dict):
                    target_surface = target_obj.metadata.get(
                        fiber_key, target_surface
                    )

                if target_surface == boundary.target_surface:
                    crossers.append((node, mor.target))

        return crossers


# =============================================================================
# CAT Engine
# =============================================================================

class CATEngine:
    """
    Executable Categorical Activity Theory (CAT) Engine.

    Bridges Activity Theory with ContradictionDetector, GenericFibration,
    OPTIMUS, and ThreatIntelligenceBus for active defense and structural
    evolution.

    Usage:
        from core.category import Category
        from core.optimus import OptimusEngine
        from categorical.cat_advanced import CATEngine

        category = Category(db_path=":memory:")
        optimus = OptimusEngine(category)
        engine = CATEngine(category, optimus=optimus)

        # Model an activity system
        diagram = engine.model_activity(activity_system)

        # Detect obstructions
        obstructions = engine.detect_obstructions(diagram)

        # Enforce trust boundaries
        violations = engine.check_trust_boundaries(diagram)

        # Evolve the system to resolve friction
        engine.evolve_system(diagram.activity_id, obstructions, max_steps=15)
    """

    def __init__(
        self,
        category,
        *,
        optimus=None,
        contradiction_detector: Optional[ContradictionDetector] = None,
        publish_events: bool = True,
    ):
        """
        Initialize the CAT Engine.

        Args:
            category: KOMPOSOS-IV Category instance.
            optimus: OptimusEngine instance (optional, created if None).
            contradiction_detector: ContradictionDetector instance (optional).
            publish_events: Whether to publish to ThreatIntelligenceBus.
        """
        self.category = category
        self.detector = contradiction_detector or ContradictionDetector()
        self.fibration_enforcer = FibrationEnforcer(category)
        self._publish_events = publish_events

        # Lazy OPTIMUS initialization
        self._optimus = optimus
        self._optimus_initialized = optimus is not None

    @property
    def optimus(self):
        """Lazy-load OptimusEngine to avoid circular imports at init time."""
        if not self._optimus_initialized:
            try:
                from core.optimus import OptimusEngine
                self._optimus = OptimusEngine(self.category)
                self._optimus_initialized = True
            except ImportError:
                logger.warning("OptimusEngine not available")
                self._optimus = None
                self._optimus_initialized = True
        return self._optimus

    def model_activity(self, system: ActivitySystem) -> ActivityDiagram:
        """
        Transform an ActivitySystem into a formal ActivityDiagram.

        Preserves ALL components per type (not just the first).
        """
        return ActivityDiagram(
            activity_id=system.name,
            subjects=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.SUBJECT)
            ],
            objects=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.OBJECT)
            ],
            tools=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.TOOL)
            ],
            rules=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.RULE)
            ],
            community=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.COMMUNITY)
            ],
            division=[
                c.name for c in
                system.get_components_by_type(ActivityComponent.DIVISION_OF_LABOR)
            ],
            metadata=system.summary(),
        )

    def detect_obstructions(
        self,
        diagram: ActivityDiagram,
        tension_threshold: float = 0.1,
    ) -> List[Obstruction]:
        """
        Detect systemic contradictions as cohomological obstructions.

        Uses the existing ContradictionDetector for full 4-level
        contradiction detection on the enriched category, plus direct
        path tension analysis for the three AT triads.

        Args:
            diagram: The ActivityDiagram to check.
            tension_threshold: Minimum tension to report (default 0.1).

        Returns:
            List of Obstruction objects with COG status classification.
        """
        obstructions = []

        # Check all three triads via direct path analysis
        obstructions.extend(
            self._check_production_triad(diagram, tension_threshold)
        )
        obstructions.extend(
            self._check_regulation_triad(diagram, tension_threshold)
        )
        obstructions.extend(
            self._check_distribution_triad(diagram, tension_threshold)
        )

        # Publish events
        if self._publish_events and obstructions:
            self._publish_contradictions(diagram, obstructions)

        return obstructions

    def detect_contradictions(
        self,
        system: ActivitySystem,
    ) -> List[Contradiction]:
        """
        Detect contradictions using the full ContradictionDetector.

        This provides all 4 Engestrom levels (primary through quaternary)
        via the existing activity_system.py infrastructure.

        Args:
            system: The ActivitySystem to analyze.

        Returns:
            List of Contradiction objects from ContradictionDetector.
        """
        return self.detector.detect_all(system)

    def check_trust_boundaries(
        self,
        diagram: ActivityDiagram,
        fiber_key: str = "type",
    ) -> List[PivotViolation]:
        """
        Check trust boundaries for cartesian lift violations.

        Uses FibrationEnforcer to verify that cross-surface morphisms
        have valid lifts in the Grothendieck fibration.

        Args:
            diagram: The ActivityDiagram with trust boundaries.
            fiber_key: Metadata key for surface classification.

        Returns:
            List of PivotViolation for each failed lift.
        """
        violations = self.fibration_enforcer.check_boundaries(
            diagram, fiber_key=fiber_key
        )

        if self._publish_events and violations:
            self._publish_pivot_violations(diagram, violations)

        return violations

    def evolve_system(
        self,
        activity_id: str,
        obstructions: List[Obstruction],
        max_steps: int = 10,
        depth: int = 2,
    ):
        """
        Execute Dialectical Self-Extension via OPTIMUS.

        Finds intermediate factorizations to resolve structural tension.
        The max_steps parameter should be increased when defending against
        deep pivot chains (e.g., 32-step Mythos pivots need max_steps >= 15).

        Args:
            activity_id: ID of the activity being evolved.
            obstructions: List of detected obstructions.
            max_steps: Maximum OPTIMUS refinement steps. Increase for
                       deep Mythos pivots (default 10, recommend 15-20
                       for 32-step chains).
            depth: Factorization depth for intermediate discovery.
        """
        if not self.optimus:
            logger.warning("OPTIMUS not available for evolution")
            return

        # First, refine specific high-tension morphisms
        for obs in obstructions:
            if obs.status == "REJECT" and obs.tension > 0.3:
                # Get source and target from the obstruction components
                if len(obs.components) >= 2:
                    src, tgt = obs.components[0], obs.components[-1]
                    try:
                        self.optimus.refine_morphism(src, tgt, depth=depth)
                    except Exception as e:
                        logger.debug(
                            f"Could not refine {src}->{tgt}: {e}"
                        )

        # Then run full descent to reach fixpoint
        try:
            self.optimus.refine(max_steps=max_steps, depth=depth)
        except Exception as e:
            logger.warning(f"OPTIMUS descent failed: {e}")

    def full_analysis(
        self,
        system: ActivitySystem,
        trust_boundaries: Optional[List[TrustBoundary]] = None,
        tension_threshold: float = 0.1,
        evolve: bool = False,
        max_steps: int = 10,
    ) -> Dict[str, Any]:
        """
        Run full CAT analysis: model -> detect -> enforce -> optionally evolve.

        Convenience method that runs the complete pipeline.

        Args:
            system: The ActivitySystem to analyze.
            trust_boundaries: Optional trust boundaries to enforce.
            tension_threshold: Minimum tension to report.
            evolve: Whether to trigger OPTIMUS evolution.
            max_steps: OPTIMUS refinement steps (increase for deep pivots).

        Returns:
            Dict with keys: diagram, obstructions, contradictions,
            pivot_violations, evolved.
        """
        # Model
        diagram = self.model_activity(system)
        if trust_boundaries:
            diagram.trust_boundaries = trust_boundaries

        # Detect obstructions (path-based)
        obstructions = self.detect_obstructions(diagram, tension_threshold)

        # Detect contradictions (enriched category based)
        contradictions = self.detect_contradictions(system)

        # Check trust boundaries
        pivot_violations = self.check_trust_boundaries(diagram)

        # Evolve if requested
        evolved = False
        if evolve and (obstructions or contradictions):
            self.evolve_system(
                diagram.activity_id, obstructions, max_steps=max_steps
            )
            evolved = True

        return {
            "diagram": diagram,
            "obstructions": obstructions,
            "contradictions": contradictions,
            "pivot_violations": pivot_violations,
            "evolved": evolved,
            "summary": {
                "total_obstructions": len(obstructions),
                "total_contradictions": len(contradictions),
                "total_pivot_violations": len(pivot_violations),
                "max_tension": max(
                    (o.tension for o in obstructions), default=0.0
                ),
                "reject_count": sum(
                    1 for o in obstructions if o.status == "REJECT"
                ),
            },
        }

    # =========================================================================
    # Private: Triad Checking
    # =========================================================================

    def _check_production_triad(
        self,
        diagram: ActivityDiagram,
        threshold: float,
    ) -> List[Obstruction]:
        """
        Production Triad: S -> T -> O vs S -> O.

        Checks if the tool-mediated path and direct path commute.
        """
        obstructions = []
        for s in diagram.subjects:
            for t in diagram.tools:
                for o in diagram.objects:
                    tension, status, evidence = self._compute_path_tension(
                        [s, t, o], [s, o]
                    )
                    if tension > threshold:
                        obstructions.append(Obstruction(
                            activity_id=diagram.activity_id,
                            triad="production",
                            components=[s, t, o],
                            tension=round(tension, 4),
                            status=status,
                            description=(
                                f"Production: tool-mediated path "
                                f"({s}->{t}->{o}) diverges from "
                                f"direct ({s}->{o}), tension={tension:.3f}"
                            ),
                            evidence=evidence,
                        ))
        return obstructions

    def _check_regulation_triad(
        self,
        diagram: ActivityDiagram,
        threshold: float,
    ) -> List[Obstruction]:
        """
        Regulation Triad: S -> R -> C vs S -> C.

        Checks if rule-mediated subject-community paths commute.
        """
        obstructions = []
        for s in diagram.subjects:
            for r in diagram.rules:
                for c in diagram.community:
                    tension, status, evidence = self._compute_path_tension(
                        [s, r, c], [s, c]
                    )
                    if tension > threshold:
                        obstructions.append(Obstruction(
                            activity_id=diagram.activity_id,
                            triad="regulation",
                            components=[s, r, c],
                            tension=round(tension, 4),
                            status=status,
                            description=(
                                f"Regulation: rule-mediated path "
                                f"({s}->{r}->{c}) diverges from "
                                f"direct ({s}->{c}), tension={tension:.3f}"
                            ),
                            evidence=evidence,
                        ))
        return obstructions

    def _check_distribution_triad(
        self,
        diagram: ActivityDiagram,
        threshold: float,
    ) -> List[Obstruction]:
        """
        Distribution Triad: C -> D -> O vs C -> O.

        Checks if labor-mediated community-object paths commute.
        """
        obstructions = []
        for c in diagram.community:
            for d in diagram.division:
                for o in diagram.objects:
                    tension, status, evidence = self._compute_path_tension(
                        [c, d, o], [c, o]
                    )
                    if tension > threshold:
                        obstructions.append(Obstruction(
                            activity_id=diagram.activity_id,
                            triad="distribution",
                            components=[c, d, o],
                            tension=round(tension, 4),
                            status=status,
                            description=(
                                f"Distribution: labor-mediated path "
                                f"({c}->{d}->{o}) diverges from "
                                f"direct ({c}->{o}), tension={tension:.3f}"
                            ),
                            evidence=evidence,
                        ))
        return obstructions

    # =========================================================================
    # Private: Path Tension Computation
    # =========================================================================

    def _compute_path_tension(
        self,
        mediated_path: List[str],
        direct_path: List[str],
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Compute tension between two paths using enriched confidence weights.

        Returns:
            (tension, status, evidence) where status is COG vocabulary.
        """
        conf_mediated = self._path_confidence(mediated_path)
        conf_direct = self._path_confidence(direct_path)

        evidence = {
            "mediated_path": mediated_path,
            "direct_path": direct_path,
            "mediated_confidence": conf_mediated,
            "direct_confidence": conf_direct,
        }

        # ORPHAN: neither path exists
        if conf_mediated is None and conf_direct is None:
            return 0.0, "ORPHAN", evidence

        # HOLLOW: one path exists but the other is broken
        if conf_mediated is None or conf_direct is None:
            return 1.0, "HOLLOW", evidence

        # Compute tension as absolute difference
        tension = abs(conf_mediated - conf_direct)

        # Classify
        if tension > 0.5:
            status = "REJECT"
        elif tension > 0.1:
            status = "HOLLOW"
        else:
            status = "AGREE"

        evidence["tension_raw"] = tension
        return tension, status, evidence

    def _path_confidence(self, path: List[str]) -> Optional[float]:
        """
        Compute the product of morphism confidences along a path.

        Returns None if any edge in the path is missing.
        """
        if len(path) < 2:
            return 1.0

        conf = 1.0
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            mors = [
                m for m in self.category.morphisms_from(src)
                if m.target == tgt
            ]
            if not mors:
                return None
            conf *= max(m.confidence for m in mors)

        return conf

    # =========================================================================
    # Private: Event Publishing
    # =========================================================================

    def _publish_contradictions(
        self,
        diagram: ActivityDiagram,
        obstructions: List[Obstruction],
    ):
        """Publish contradiction events to the ThreatIntelligenceBus."""
        try:
            from core.threat_intelligence_bus import ThreatIntelligenceBus
            bus = ThreatIntelligenceBus.get_instance()

            max_tension = max(o.tension for o in obstructions)
            rejects = [o for o in obstructions if o.status == "REJECT"]

            bus.publish(
                event_type="activity.contradiction",
                payload={
                    "activity_id": diagram.activity_id,
                    "obstruction_count": len(obstructions),
                    "reject_count": len(rejects),
                    "max_tension": max_tension,
                    "triads_affected": list(set(
                        o.triad for o in obstructions
                    )),
                },
                source="cat_engine",
            )
        except Exception as e:
            logger.debug(f"Could not publish to bus: {e}")

    def _publish_pivot_violations(
        self,
        diagram: ActivityDiagram,
        violations: List[PivotViolation],
    ):
        """Publish pivot violation events to the ThreatIntelligenceBus."""
        try:
            from core.threat_intelligence_bus import ThreatIntelligenceBus
            bus = ThreatIntelligenceBus.get_instance()

            for v in violations:
                bus.publish(
                    event_type="activity.pivot_blocked",
                    payload={
                        "activity_id": diagram.activity_id,
                        "boundary": v.boundary.name,
                        "source_surface": v.boundary.source_surface,
                        "target_surface": v.boundary.target_surface,
                        "source_element": v.source_element,
                        "target_element": v.target_element,
                    },
                    source="cat_engine",
                )
        except Exception as e:
            logger.debug(f"Could not publish to bus: {e}")
