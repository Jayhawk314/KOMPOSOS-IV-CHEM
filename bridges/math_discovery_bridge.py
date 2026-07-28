# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Math Discovery Bridge — Wires MathKernel into COG/OPTIMUS/Cosmos/DualEngine.

The MathKernel has 3 independent Category instances (MMLKG, LeanDojo,
NaturalProofs) plus a cross-source layer. This bridge connects them to
the full KOMPOSOS-IV verification/refinement stack:

    MathKernel (3 Categories)
         |
    MathDiscoveryBridge
         |
    +----+----+--------+-----------+
    |         |        |           |
   COG    OPTIMUS   Cosmos   DualEngine
  (verify) (refine) (∞-cat)  (ZFC+CAT)

Key operations:
  - verify_convergence(): Run COG on convergent signals from multiple sources
  - refine_sources(): Run OPTIMUS on each source graph to discover intermediates
  - build_cosmos(): Build InfinityCosmos on cross-source layer
  - verify_conjecture(): Run DualEngine on discovered conjectures
  - full_discovery(): End-to-end pipeline wiring everything together
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.category import Category
from domains.mathematics.kernel import MathKernel, ConvergenceReport


# ================================================================
# Discovery Result
# ================================================================

@dataclass
class DiscoveryResult:
    """Complete result from a math discovery pipeline run."""

    # Convergence analysis
    convergence: Optional[ConvergenceReport] = None

    # COG verification of convergent signals
    cog_verified: List[Dict[str, Any]] = field(default_factory=list)
    cog_rejected: List[Dict[str, Any]] = field(default_factory=list)

    # OPTIMUS refinement discoveries
    optimus_intermediates: Dict[str, List[str]] = field(default_factory=dict)
    optimus_gaps: List[Dict[str, Any]] = field(default_factory=list)

    # InfinityCosmos higher structure
    cosmos_fibrations: List[Dict[str, Any]] = field(default_factory=list)
    cosmos_yoneda: Optional[Dict[str, Any]] = None
    cosmos_2cells: int = 0

    # DualEngine conjecture verdicts
    conjecture_verdicts: List[Dict[str, Any]] = field(default_factory=list)

    # Cross-source edges built
    cross_source_edges: int = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "convergence_sources": self.convergence.sources_analyzed if self.convergence else 0,
            "convergent_holes": len(self.convergence.convergent_holes) if self.convergence else 0,
            "cog_verified": len(self.cog_verified),
            "cog_rejected": len(self.cog_rejected),
            "optimus_sources_refined": len(self.optimus_intermediates),
            "optimus_gaps_found": len(self.optimus_gaps),
            "cosmos_fibrations": len(self.cosmos_fibrations),
            "cosmos_2cells": self.cosmos_2cells,
            "conjectures_verified": sum(
                1 for v in self.conjecture_verdicts if v.get("delta_type") == "AGREE"
            ),
            "conjectures_hollow": sum(
                1 for v in self.conjecture_verdicts if v.get("delta_type") == "HOLLOW"
            ),
            "cross_source_edges": self.cross_source_edges,
        }


# ================================================================
# Math Discovery Bridge
# ================================================================

class MathDiscoveryBridge:
    """
    Wires MathKernel to COG, OPTIMUS, InfinityCosmos, and DualEngine.

    Usage:
        kernel = MathKernel()
        kernel.load_source("leandojo", adapter)

        bridge = MathDiscoveryBridge(kernel)
        result = bridge.full_discovery()

        # Or individually:
        bridge.verify_convergence()
        bridge.refine_sources()
        bridge.build_cosmos()
        bridge.verify_conjecture("A", "B", "implies")
    """

    def __init__(
        self,
        kernel: MathKernel,
        cog_max_tier: int = 3,
        optimus_depth: int = 2,
        optimus_max_steps: int = 20,
    ):
        self.kernel = kernel
        self.cog_max_tier = cog_max_tier
        self.optimus_depth = optimus_depth
        self.optimus_max_steps = optimus_max_steps

        # Lazily initialized engines (one per source Category)
        self._cog_engines: Dict[str, Any] = {}
        self._optimus_engines: Dict[str, Any] = {}
        self._cosmos: Optional[Any] = None
        self._dual_bridge: Optional[Any] = None

    # ----------------------------------------------------------------
    # Engine initialization (lazy)
    # ----------------------------------------------------------------

    def _get_cog(self, category: Category, name: str = "default"):
        """Get or create a COG engine for a Category."""
        if name not in self._cog_engines:
            from cog.session import CogSession
            from cog.engine import CogEngine
            session = CogSession(session_id=f"math_{name}", category=category)
            self._cog_engines[name] = CogEngine(session)
        return self._cog_engines[name]

    def _get_optimus(self, category: Category, name: str = "default"):
        """Get or create an OPTIMUS engine for a Category."""
        if name not in self._optimus_engines:
            from core.optimus import OptimusEngine
            self._optimus_engines[name] = OptimusEngine(
                category, max_depth=self.optimus_depth
            )
        return self._optimus_engines[name]

    def _get_cosmos(self):
        """Get or create InfinityCosmos on the cross-source layer."""
        if self._cosmos is None:
            from core.cosmos import InfinityCosmos
            self._cosmos = InfinityCosmos(self.kernel.cross_source)
        return self._cosmos

    def _get_dual_bridge(self, category: Category):
        """Get or create DualEngine bridge for a Category."""
        if self._dual_bridge is None:
            from zfc.category_store_adapter import StoreAdapter
            from zfc.category_bridge import DualEngineBridge
            adapter = StoreAdapter(category)
            self._dual_bridge = DualEngineBridge(adapter, category=category)
        return self._dual_bridge

    # ----------------------------------------------------------------
    # Phase 1: Verify convergent signals through COG
    # ----------------------------------------------------------------

    def verify_convergence(self, report: Optional[ConvergenceReport] = None) -> Dict[str, Any]:
        """
        Run COG verification on convergent signals from MathKernel.

        Convergent signals (holes/clusters/bridges appearing in 2+ sources)
        are checked through COG's tiered verification to filter noise.
        """
        from cog.schema import CogClaim

        if report is None:
            report = self.kernel.convergent_analysis()

        verified = []
        rejected = []

        # Verify convergent holes through COG on the cross-source Category
        cog = self._get_cog(self.kernel.cross_source, "cross_source")

        for hole in report.convergent_holes:
            sources = hole.get("sources", [])
            hole_type = hole.get("type", "unknown")

            # Create a claim: "These sources agree on this topological feature"
            claim = CogClaim(
                source=sources[0] if sources else "unknown",
                target=sources[1] if len(sources) > 1 else "unknown",
                relation=f"convergent_{hole_type}",
                confidence=len(sources) / 3.0,  # 2/3 or 3/3 agreement
            )

            try:
                result = cog.check_claim(claim, depth=self.cog_max_tier)
                entry = {
                    "signal": hole,
                    "cog_status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "cog_confidence": result.confidence,
                    "cog_tier": result.tier,
                }
                if result.confidence > 0.5:
                    verified.append(entry)
                else:
                    rejected.append(entry)
            except Exception as e:
                # COG failure shouldn't block discovery
                verified.append({
                    "signal": hole,
                    "cog_status": "skipped",
                    "cog_error": str(e),
                })

        # Also verify convergent clusters and bridges
        for signal_list, signal_type in [
            (report.convergent_clusters, "cluster"),
            (report.convergent_bridges, "bridge"),
        ]:
            for signal in signal_list:
                sources = signal.get("sources", [])
                claim = CogClaim(
                    source=sources[0] if sources else "unknown",
                    target=sources[1] if len(sources) > 1 else "unknown",
                    relation=f"convergent_{signal_type}",
                    confidence=len(sources) / 3.0,
                )
                try:
                    result = cog.check_claim(claim, depth=min(self.cog_max_tier, 2))
                    entry = {
                        "signal": signal,
                        "cog_status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                        "cog_confidence": result.confidence,
                    }
                    if result.confidence > 0.4:
                        verified.append(entry)
                    else:
                        rejected.append(entry)
                except Exception:
                    verified.append({"signal": signal, "cog_status": "skipped"})

        return {"verified": verified, "rejected": rejected}

    # ----------------------------------------------------------------
    # Phase 2: OPTIMUS refinement on each source
    # ----------------------------------------------------------------

    def refine_sources(self) -> Dict[str, Any]:
        """
        Run OPTIMUS categorical gradient descent on each source Category.

        Discovers intermediate objects (factorizations) and structural gaps
        in each independent math graph. These are candidate conjectures.
        """
        intermediates: Dict[str, List[str]] = {}
        all_gaps: List[Dict[str, Any]] = []

        for source_name, cat in self.kernel.sources.items():
            if len(cat.objects()) == 0:
                continue

            optimus = self._get_optimus(cat, source_name)

            # Run categorical gradient descent
            try:
                refine_result = optimus.refine(
                    max_steps=self.optimus_max_steps,
                    depth=self.optimus_depth,
                )
                synced = refine_result.get("synced_morphisms", [])
                if synced:
                    intermediates[source_name] = synced
            except Exception:
                pass

            # Find structural gaps (missing direct morphisms)
            try:
                gaps = optimus.find_structural_gaps()
                for gap in gaps:
                    gap["source_graph"] = source_name
                    all_gaps.append(gap)
            except Exception:
                pass

        return {"intermediates": intermediates, "gaps": all_gaps}

    # ----------------------------------------------------------------
    # Phase 3: Build InfinityCosmos on cross-source layer
    # ----------------------------------------------------------------

    def build_cosmos(self) -> Dict[str, Any]:
        """
        Build InfinityCosmos on the cross-source Category.

        First ensures cross-source edges exist, then builds the
        homotopy 2-category, detects fibrations, and computes
        Yoneda embedding on the unified math graph.
        """
        # Build cross-source edges if not already done
        edge_count = self.kernel.build_cross_source_edges()

        if len(self.kernel.cross_source.objects()) == 0:
            return {"skipped": True, "reason": "no cross-source data"}

        cosmos = self._get_cosmos()
        result: Dict[str, Any] = {"cross_source_edges": edge_count}

        # Build homotopy 2-category
        try:
            h2k = cosmos.homotopy_2_category()
            result["two_cells"] = len(h2k.two_cells) if hasattr(h2k, 'two_cells') else 0
            result["h2k_built"] = True
        except Exception as e:
            result["h2k_built"] = False
            result["h2k_error"] = str(e)

        # Detect cartesian fibrations
        try:
            fibs = cosmos.cartesian_fibrations()
            result["fibrations"] = [
                {
                    "name": f.name,
                    "base": f.base_object,
                    "total_objects": len(f.total_objects),
                }
                for f in fibs
            ] if fibs else []
        except Exception:
            result["fibrations"] = []

        # Yoneda embedding
        try:
            yoneda = cosmos.yoneda_embedding()
            result["yoneda"] = {
                "fully_faithful": yoneda.is_fully_faithful,
                "faithfulness_score": yoneda.faithfulness_score,
                "objects_mapped": len(yoneda.objects_mapped),
            }
        except Exception:
            result["yoneda"] = None

        return result

    # ----------------------------------------------------------------
    # Phase 4: Verify conjectures through DualEngine
    # ----------------------------------------------------------------

    def verify_conjecture(
        self,
        source: str,
        target: str,
        relation: str,
        source_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify a discovered conjecture through the ZFC+CAT DualEngine.

        Returns delta classification: AGREE, ORPHAN, HOLLOW, REJECT.

        HOLLOW results are the most interesting -- structurally real
        (CAT sees the pattern) but logically baseless (ZFC can't prove it).
        These are genuine novel discoveries.
        """
        # Pick the Category to verify against
        if source_category and source_category in self.kernel.sources:
            cat = self.kernel.sources[source_category]
        else:
            cat = self.kernel.cross_source

        dual = self._get_dual_bridge(cat)

        try:
            result = dual.query(source, target, relation)
            return {
                "source": source,
                "target": target,
                "relation": relation,
                "delta_type": result.delta_type.name if hasattr(result.delta_type, 'name') else str(result.delta_type),
                "zfc_says": result.zfc_says,
                "zfc_confidence": result.zfc_confidence,
                "cat_says": result.cat_says,
                "cat_confidence": result.cat_confidence,
                "meta_prediction": str(result.meta_prediction) if result.meta_prediction else None,
            }
        except Exception as e:
            return {
                "source": source,
                "target": target,
                "relation": relation,
                "delta_type": "ERROR",
                "error": str(e),
            }

    def verify_structural_gaps(self, gaps: List[Dict[str, Any]], max_verify: int = 50) -> List[Dict[str, Any]]:
        """
        Verify OPTIMUS-discovered structural gaps through DualEngine.

        Each gap (A->B->C exists but no A->C) is a candidate conjecture.
        Run through DualEngine to classify as AGREE/ORPHAN/HOLLOW/REJECT.
        """
        verdicts = []
        for gap in gaps[:max_verify]:
            source = gap.get("source", gap.get("from", ""))
            target = gap.get("target", gap.get("to", ""))
            source_graph = gap.get("source_graph", None)

            if source and target:
                verdict = self.verify_conjecture(
                    source, target, "structural_gap",
                    source_category=source_graph,
                )
                verdict["gap"] = gap
                verdicts.append(verdict)

        return verdicts

    # ----------------------------------------------------------------
    # Full discovery pipeline
    # ----------------------------------------------------------------

    def full_discovery(self) -> DiscoveryResult:
        """
        Run the complete math discovery pipeline:

        1. Convergent analysis across all sources
        2. COG verification of convergent signals
        3. OPTIMUS refinement of each source
        4. Build cross-source edges
        5. InfinityCosmos on unified graph
        6. DualEngine verification of structural gaps
        """
        result = DiscoveryResult()

        # 1. Convergent analysis
        result.convergence = self.kernel.convergent_analysis()

        # 2. COG verification
        cog_result = self.verify_convergence(result.convergence)
        result.cog_verified = cog_result["verified"]
        result.cog_rejected = cog_result["rejected"]

        # 3. OPTIMUS refinement
        optimus_result = self.refine_sources()
        result.optimus_intermediates = optimus_result["intermediates"]
        result.optimus_gaps = optimus_result["gaps"]

        # 4+5. Cosmos (includes building cross-source edges)
        cosmos_result = self.build_cosmos()
        result.cross_source_edges = cosmos_result.get("cross_source_edges", 0)
        result.cosmos_fibrations = cosmos_result.get("fibrations", [])
        result.cosmos_yoneda = cosmos_result.get("yoneda")
        result.cosmos_2cells = cosmos_result.get("two_cells", 0)

        # 6. DualEngine verification of structural gaps
        if result.optimus_gaps:
            result.conjecture_verdicts = self.verify_structural_gaps(
                result.optimus_gaps
            )

        return result
