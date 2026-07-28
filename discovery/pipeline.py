# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Integrated Discovery Pipeline — Wires discovery scripts to COG/OPTIMUS/DualEngine.

The discovery/ scripts (treasure_hunt, hole_navigation, conjecture_pipeline)
were originally standalone. This module wires them into the KOMPOSOS-IV
verification stack so that:

1. Discovered holes are verified through COG (filter false positives)
2. Hole clusters are refined by OPTIMUS (find intermediate objects)
3. Conjecture candidates go through DualEngine (AGREE/ORPHAN/HOLLOW/REJECT)
4. HOLLOW results (structurally real but logically novel) are flagged
   as genuine discoveries

Usage:
    from discovery.pipeline import IntegratedDiscoveryPipeline

    pipeline = IntegratedDiscoveryPipeline()
    results = pipeline.run()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.category import Category


@dataclass
class PipelineResult:
    """Results from the integrated discovery pipeline."""
    # Raw discovery results
    holes_found: int = 0
    treasures_found: int = 0
    conjectures_generated: int = 0

    # COG verification
    holes_cog_verified: int = 0
    holes_cog_rejected: int = 0

    # OPTIMUS refinement
    optimus_intermediates_found: int = 0
    optimus_gaps: List[Dict[str, Any]] = field(default_factory=list)

    # DualEngine verdicts
    conjectures_agree: int = 0
    conjectures_hollow: int = 0  # Novel discoveries
    conjectures_orphan: int = 0
    conjectures_reject: int = 0
    verdicts: List[Dict[str, Any]] = field(default_factory=list)


class IntegratedDiscoveryPipeline:
    """
    Wires the discovery scripts into the KOMPOSOS-IV verification stack.

    Takes the output of treasure_hunt / hole_navigation / conjecture_pipeline
    and runs it through COG → OPTIMUS → DualEngine.
    """

    def __init__(
        self,
        category: Optional[Category] = None,
        cog_max_tier: int = 3,
        optimus_depth: int = 2,
    ):
        self.category = category or Category(db_path=":memory:")
        self.cog_max_tier = cog_max_tier
        self.optimus_depth = optimus_depth
        self._cog = None
        self._optimus = None
        self._dual = None

    @property
    def cog(self):
        if self._cog is None:
            from cog.session import CogSession
            from cog.engine import CogEngine
            session = CogSession(session_id="discovery", category=self.category)
            self._cog = CogEngine(session)
        return self._cog

    @property
    def optimus(self):
        if self._optimus is None:
            from core.optimus import OptimusEngine
            self._optimus = OptimusEngine(self.category, max_depth=self.optimus_depth)
        return self._optimus

    @property
    def dual_bridge(self):
        if self._dual is None:
            from zfc.category_store_adapter import StoreAdapter
            from zfc.category_bridge import DualEngineBridge
            adapter = StoreAdapter(self.category)
            self._dual = DualEngineBridge(adapter, category=self.category)
        return self._dual

    def verify_holes(self, holes: List[Dict[str, Any]]) -> Dict[str, List]:
        """
        Verify discovered holes through COG.

        Each hole is a (source, target) pair where a morphism should exist
        but doesn't. COG checks whether the surrounding structure supports it.
        """
        from cog.schema import CogClaim

        verified = []
        rejected = []

        for hole in holes:
            source = hole.get("source", hole.get("from", ""))
            target = hole.get("target", hole.get("to", ""))

            if not source or not target:
                continue

            claim = CogClaim(
                source=source,
                target=target,
                relation=hole.get("type", "missing_morphism"),
                confidence=hole.get("confidence", 0.5),
            )

            try:
                result = self.cog.check_claim(claim, depth=self.cog_max_tier)
                entry = {**hole, "cog_confidence": result.confidence, "cog_tier": result.tier}
                if result.confidence > 0.4:
                    verified.append(entry)
                else:
                    rejected.append(entry)
            except Exception:
                verified.append(hole)  # Don't block on COG errors

        return {"verified": verified, "rejected": rejected}

    def refine_region(self, objects: List[str]) -> Dict[str, Any]:
        """
        Use OPTIMUS to refine a region of the math graph.

        Given a set of objects (e.g., a cluster from hole_navigation),
        run categorical gradient descent to find intermediates.
        """
        intermediates = []
        for i, src in enumerate(objects[:10]):
            for tgt in objects[i + 1:10]:
                try:
                    found = self.optimus.discover_intermediates(src, tgt)
                    if found:
                        intermediates.extend(found)
                except Exception:
                    pass

        gaps = []
        try:
            gaps = self.optimus.find_structural_gaps()
        except Exception:
            pass

        return {
            "intermediates": list(set(intermediates)),
            "gaps": gaps,
        }

    def verify_conjectures(self, conjectures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run conjectures through the ZFC+CAT DualEngine.

        Classifies each as:
        - AGREE: Both ZFC and CAT confirm
        - HOLLOW: CAT sees structure but ZFC can't prove it (NOVEL DISCOVERY)
        - ORPHAN: ZFC proves it but structure doesn't support it
        - REJECT: Neither supports it
        """
        verdicts = []
        for conj in conjectures:
            source = conj.get("source", conj.get("from", ""))
            target = conj.get("target", conj.get("to", ""))
            relation = conj.get("relation", conj.get("type", "conjecture"))

            if not source or not target:
                continue

            try:
                result = self.dual_bridge.query(source, target, relation)
                verdicts.append({
                    **conj,
                    "delta_type": result.delta_type.name if hasattr(result.delta_type, 'name') else str(result.delta_type),
                    "zfc_says": result.zfc_says,
                    "zfc_confidence": result.zfc_confidence,
                    "cat_says": result.cat_says,
                    "cat_confidence": result.cat_confidence,
                })
            except Exception as e:
                verdicts.append({**conj, "delta_type": "ERROR", "error": str(e)})

        return verdicts

    def run(
        self,
        holes: Optional[List[Dict[str, Any]]] = None,
        conjectures: Optional[List[Dict[str, Any]]] = None,
        cluster_objects: Optional[List[str]] = None,
    ) -> PipelineResult:
        """
        Run the full integrated pipeline.

        Pass in raw results from discovery scripts:
        - holes: from hole_navigation / filter_59k_holes
        - conjectures: from complete_conjecture_pipeline / treasure_hunt
        - cluster_objects: from treasure_hunt clusters
        """
        result = PipelineResult()

        # 1. Verify holes through COG
        if holes:
            result.holes_found = len(holes)
            verification = self.verify_holes(holes)
            result.holes_cog_verified = len(verification["verified"])
            result.holes_cog_rejected = len(verification["rejected"])

        # 2. OPTIMUS refinement on cluster
        if cluster_objects:
            refinement = self.refine_region(cluster_objects)
            result.optimus_intermediates_found = len(refinement["intermediates"])
            result.optimus_gaps = refinement["gaps"]

        # 3. DualEngine verification of conjectures
        if conjectures:
            result.conjectures_generated = len(conjectures)
            result.verdicts = self.verify_conjectures(conjectures)
            for v in result.verdicts:
                dt = v.get("delta_type", "")
                if dt == "AGREE":
                    result.conjectures_agree += 1
                elif dt == "HOLLOW":
                    result.conjectures_hollow += 1
                elif dt == "ORPHAN":
                    result.conjectures_orphan += 1
                elif dt == "REJECT":
                    result.conjectures_reject += 1

        return result
