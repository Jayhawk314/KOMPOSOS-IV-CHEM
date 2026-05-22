# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This bridge plugin is dual-licensed (Apache-2.0 OR KOMPOSOS-IV-Commercial).
# It integrates with Orion Core, which is separately licensed under MIT.
# Orion Core (c) Borkwork (https://github.com/borkwork/orion-framework)

"""
Activity System Plugin for Orion

Formalizes and tracks Activity Theory diagrams within the Orion/KOMPOSOS-IV ecosystem.
Detects systemic contradictions (obstructions) and triggers OPTIMUS evolution.
Publishes events to ThreatIntelligenceBus for cross-module coordination.
"""

from __future__ import annotations

import logging
import sys
import os
from typing import Any, Dict, List, Optional

# Add orion-main to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'orion-main', 'src'))

logger = logging.getLogger(__name__)

# Import from Orion (MIT licensed by Borkwork)
from orion_core import Plugin
from orion_core.plugin import on, hook

from categorical.cat_advanced import ActivityDiagram, CATEngine, Obstruction
from categorical.activity_system import ActivitySystem, ActivitySystemBuilder
from core.optimus import OptimusEngine


class ActivitySystemPlugin(Plugin):
    """
    Wires Categorical Activity Theory (CAT) into the Orion/KOMPOSOS-IV ecosystem.

    Capabilities provided:
    - activity_theory: Register and evaluate formal activity diagrams
    - systemic_evolution: Trigger OPTIMUS adaptation for activity contradictions

    Events published:
    - activity.registered: Activity diagram initialized
    - activity.contradiction_detected: Systemic friction found
    - activity.evolved: System has self-extended to resolve tension
    """

    def __init__(
        self,
        core,
        *,
        category: Optional[Any] = None,
        optimus: Optional[OptimusEngine] = None,
    ):
        """Initialize Activity System plugin."""
        super().__init__(
            core,
            name="activity_system",
            version="0.2.0",
            description="Categorical Activity Theory and systemic evolution",
            provides={"activity_theory", "systemic_evolution"},
            events_published={
                "activity.registered",
                "activity.contradiction_detected",
                "activity.evolved"
            },
        )

        # Initialize core components
        from core.category import Category
        self.category = category or Category("activity_core", db_path=":memory:")
        self.optimus = optimus or OptimusEngine(self.category)
        self.cat_engine = CATEngine(
            self.category,
            optimus=self.optimus,
            publish_events=True,
        )

        self.active_activities: Dict[str, ActivityDiagram] = {}

    async def on_start(self):
        """Plugin startup."""
        logger.info("Activity System Plugin started.")

    # ========================================================================
    # Public API Methods (Orion capability interface)
    # ========================================================================

    async def register_activity(
        self,
        activity_id: str,
        subject: str,
        obj: str,
        tool: str,
        rules: List[str],
        community: Optional[List[str]] = None,
        division: Optional[List[str]] = None,
    ) -> ActivityDiagram:
        """
        Register a formal Activity Diagram.

        Args:
            activity_id: Unique ID for the activity
            subject: The active agent/subject node name
            obj: The target object/goal node name
            tool: The mediating tool morphism name
            rules: List of rule/constraint node names
            community: List of community node names
            division: List of division of labor node names

        Returns:
            The created ActivityDiagram
        """
        diagram = ActivityDiagram(
            activity_id=activity_id,
            subjects=[subject],
            objects=[obj],
            tools=[tool],
            rules=rules,
            community=community or [],
            division=division or []
        )
        self.active_activities[activity_id] = diagram

        await self.emit("activity.registered", {"activity_id": activity_id})
        return diagram

    async def check_for_contradictions(self, activity_id: str) -> Dict[str, Any]:
        """
        Check for systemic contradictions in a registered activity.

        Uses the CAT engine for obstruction detection, with optional COG
        evaluation if the reasoning capability is available.
        """
        diagram = self.active_activities.get(activity_id)
        if not diagram:
            raise ValueError(f"Activity {activity_id} not found")

        results = {"status": "PENDING", "evidence_weight": 0.0}

        # Try COG evaluation first (if Orion reasoning capability is available)
        try:
            reasoning = await self.core.get_capability("reasoning")
            if hasattr(reasoning, 'engine') and hasattr(reasoning.engine, "evaluate_diagram"):
                cog_eval = reasoning.engine.evaluate_diagram(diagram)
                results.update(cog_eval)
        except Exception as e:
            logger.debug(f"COG reasoning not available, using CAT engine: {e}")

        # Always run CAT engine detection as well
        obstructions = self.cat_engine.detect_obstructions(diagram)
        if obstructions:
            # Use worst status from CAT engine if COG didn't already set REJECT
            max_tension = max(obs.tension for obs in obstructions)
            if results.get("status") not in ("REJECT",):
                worst = max(obstructions, key=lambda o: o.tension)
                results["status"] = worst.status
            results["evidence_weight"] = max(
                results.get("evidence_weight", 0.0), max_tension
            )
            results["obstructions"] = [
                {
                    "triad": obs.triad,
                    "components": obs.components,
                    "tension": obs.tension,
                    "status": obs.status,
                    "description": obs.description,
                }
                for obs in obstructions
            ]

        if results["status"] == "REJECT" or results["evidence_weight"] > 0.6:
            await self.emit("activity.contradiction_detected", {
                "activity_id": activity_id,
                "tension": results["evidence_weight"],
                "status": results["status"]
            })

            # Automatically trigger evolution if tension is high
            await self.evolve_activity(activity_id, obstructions)

        return results

    async def evolve_activity(
        self,
        activity_id: str,
        obstructions: List[Obstruction],
        max_steps: int = 10,
    ):
        """
        Trigger OPTIMUS evolution for an activity system.

        Args:
            activity_id: ID of the activity to evolve.
            obstructions: List of Obstruction objects from CAT engine.
            max_steps: OPTIMUS refinement steps (increase for deep pivots).
        """
        logger.info(f"Evolving activity {activity_id} to resolve contradictions...")

        self.cat_engine.evolve_system(
            activity_id, obstructions, max_steps=max_steps
        )

        await self.emit("activity.evolved", {"activity_id": activity_id})

    # ========================================================================
    # Event Handlers
    # ========================================================================

    @on("activity.telemetry")
    async def on_activity_telemetry(self, event):
        """
        Automatically build and register an activity from telemetry.
        """
        builder = ActivitySystemBuilder()
        system = builder.build(
            event.data.get("objects", []),
            event.data.get("morphisms", []),
        )
        diagram = self.cat_engine.model_activity(system)
        self.active_activities[diagram.activity_id] = diagram

        await self.emit("activity.registered", {"activity_id": diagram.activity_id})

        # Immediate check
        await self.check_for_contradictions(diagram.activity_id)
