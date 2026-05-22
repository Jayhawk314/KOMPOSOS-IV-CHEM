# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Math Kernel -- The Self-Referential Domain

Manages three independent Category instances (MMLKG, LeanDojo, NaturalProofs)
as independent views of the mathematical landscape. Cross-source edges form
a fourth sparse layer built only where multiple independent graphs agree.

Convergence across independent graphs IS the signal:
  - All 3 show the same topological feature? Triple confirmed.
  - Only 1 shows it? Likely a source artifact. Discard.

The Category class IS the kernel. Math is not separate from the engine.
The engine is reading its own grammar.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.category import Category
from domains.mathematics.name_registry import NameRegistry
from domains.mathematics.anchor_problems import AnchorProblems

if TYPE_CHECKING:
    from domains.plugin_interface import DomainPlugin, StructureMatch


@dataclass
class ConvergenceReport:
    """Results of convergent multi-source analysis."""

    # Per-source analysis results
    topology: Dict[str, Any] = field(default_factory=dict)
    geometry: Dict[str, Any] = field(default_factory=dict)
    spectral: Dict[str, Any] = field(default_factory=dict)

    # Convergent signals (appearing in 2+ sources)
    convergent_holes: List[Dict[str, Any]] = field(default_factory=list)
    convergent_clusters: List[Dict[str, Any]] = field(default_factory=list)
    convergent_bridges: List[Dict[str, Any]] = field(default_factory=list)

    # Summary
    sources_analyzed: int = 0
    total_objects: int = 0
    total_morphisms: int = 0

    def __repr__(self) -> str:
        return (
            f"ConvergenceReport(sources={self.sources_analyzed}, "
            f"holes={len(self.convergent_holes)}, "
            f"clusters={len(self.convergent_clusters)}, "
            f"bridges={len(self.convergent_bridges)})"
        )


class MathKernel:
    """
    Manages three independent Category instances for the math graph,
    plus a cross-source layer and analysis pipeline.

    The Category class IS the kernel. Three independent instances
    provide triple confirmation via convergence.

    Usage:
        kernel = MathKernel()
        kernel.load_source("mmlkg", mmlkg_adapter)
        kernel.load_source("leandojo", leandojo_adapter)

        # Run convergent analysis
        report = kernel.convergent_analysis()

        # Match a domain against math structure
        matches = kernel.find_structural_matches(physics_plugin)
    """

    def __init__(self, db_dir: str = ":memory:"):
        """
        Initialize MathKernel with three independent Categories.

        Args:
            db_dir: Directory for SQLite databases. Use ":memory:" for
                    in-memory operation (default, best for testing).
                    Use a directory path for persistent storage.
        """
        if db_dir == ":memory:":
            self.mmlkg = Category(name="mmlkg", db_path=":memory:")
            self.leandojo = Category(name="leandojo", db_path=":memory:")
            self.naturalproofs = Category(name="naturalproofs", db_path=":memory:")
            self.cross_source = Category(name="cross_source", db_path=":memory:")
        else:
            os.makedirs(db_dir, exist_ok=True)
            self.mmlkg = Category(name="mmlkg", db_path=os.path.join(db_dir, "mmlkg.db"))
            self.leandojo = Category(name="leandojo", db_path=os.path.join(db_dir, "leandojo.db"))
            self.naturalproofs = Category(name="naturalproofs", db_path=os.path.join(db_dir, "naturalproofs.db"))
            self.cross_source = Category(name="cross_source", db_path=os.path.join(db_dir, "cross_source.db"))

        self.name_registry = NameRegistry()
        self._anchors: Dict[str, AnchorProblems] = {}

    @property
    def sources(self) -> Dict[str, Category]:
        """The three independent math graph sources."""
        return {
            "mmlkg": self.mmlkg,
            "leandojo": self.leandojo,
            "naturalproofs": self.naturalproofs,
        }

    def load_source(self, source_name: str, adapter) -> Dict[str, int]:
        """
        Load data from an adapter into the appropriate Category.

        Args:
            source_name: One of "mmlkg", "leandojo", "naturalproofs"
            adapter: An adapter with load_into(category) method

        Returns:
            Dict with counts: {"objects": N, "morphisms": M}
        """
        if source_name not in self.sources:
            raise ValueError(
                f"Unknown source: {source_name}. "
                f"Must be one of: {list(self.sources.keys())}"
            )

        cat = self.sources[source_name]
        result = adapter.load_into(cat)

        # Register anchor problems in this source
        anchors = AnchorProblems(cat)
        anchors.register_anchors()
        self._anchors[source_name] = anchors

        # Apply name registry labels
        self.name_registry.label_category(cat)

        return result

    def run_topology(
        self, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run persistent homology on specified source(s).

        Returns dict of {source_name: PersistenceDiagram}.
        """
        from topology.persistent_homology import SimplicialComplex, PersistentHomologyComputer

        targets = (
            {source: self.sources[source]} if source else self.sources
        )
        results = {}

        for name, cat in targets.items():
            edges = cat.as_edges()
            if not edges:
                continue

            node_to_idx: Dict[str, int] = {}
            idx_edges = []
            for s, t, w in edges:
                for n in (s, t):
                    if n not in node_to_idx:
                        node_to_idx[n] = len(node_to_idx)
                idx_edges.append((node_to_idx[s], node_to_idx[t]))

            sc = SimplicialComplex()
            sc.build_flag_complex(idx_edges, max_dim=2)
            computer = PersistentHomologyComputer()
            results[name] = computer.compute(sc)

        return results

    def run_geometry(
        self, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run Ricci curvature on specified source(s).

        Returns dict of {source_name: CurvatureResult}.
        """
        from geometry.ricci import OllivierRicciCurvature

        targets = (
            {source: self.sources[source]} if source else self.sources
        )
        results = {}

        for name, cat in targets.items():
            if not cat.as_edges():
                continue
            ricci = OllivierRicciCurvature(cat)
            results[name] = ricci.compute_all_curvatures()

        return results

    def run_spectral(
        self, source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run spectral analysis on specified source(s).

        Returns dict of {source_name: spectral_info_dict}.
        """
        from geometry.spectral import Graph, GraphLaplacian

        targets = (
            {source: self.sources[source]} if source else self.sources
        )
        results = {}

        for name, cat in targets.items():
            edges = cat.as_edges()
            if not edges:
                continue

            # Graph uses integer nodes; build mapping
            node_to_idx: Dict[str, int] = {}
            for obj in cat.objects():
                node_to_idx[obj.name] = len(node_to_idx)

            graph = Graph()
            for s, t, w in edges:
                s_idx = node_to_idx.get(s)
                t_idx = node_to_idx.get(t)
                if s_idx is not None and t_idx is not None:
                    graph.add_edge(s_idx, t_idx, w)

            laplacian = GraphLaplacian(graph)
            laplacian.compute_spectrum()

            results[name] = {
                "algebraic_connectivity": laplacian.algebraic_connectivity(),
                "num_nodes": len(graph.nodes),
                "num_edges": len(edges),
                "eigenvalues": (
                    list(laplacian.eigenvalues[:10])
                    if hasattr(laplacian, "eigenvalues") and laplacian.eigenvalues is not None
                    else []
                ),
            }

        return results

    def convergent_analysis(self) -> ConvergenceReport:
        """
        Run all analyses on all sources and detect convergent signals.

        A signal is convergent if 2+ independent sources show the same
        feature in the same mathematical region.
        """
        report = ConvergenceReport()

        # Run analyses
        active_sources = {
            name: cat for name, cat in self.sources.items()
            if len(cat.objects()) > 0
        }
        report.sources_analyzed = len(active_sources)
        report.total_objects = sum(len(c.objects()) for c in active_sources.values())
        report.total_morphisms = sum(len(c.as_edges()) for c in active_sources.values())

        if not active_sources:
            return report

        # Topology
        try:
            report.topology = self.run_topology()
        except Exception:
            report.topology = {}

        # Geometry
        try:
            report.geometry = self.run_geometry()
        except Exception:
            report.geometry = {}

        # Spectral
        try:
            report.spectral = self.run_spectral()
        except Exception:
            report.spectral = {}

        # Detect convergent signals across sources
        report.convergent_holes = self._find_convergent_holes(report.topology)
        report.convergent_clusters = self._find_convergent_clusters(report.geometry)
        report.convergent_bridges = self._find_convergent_bridges(report.geometry)

        return report

    def _find_convergent_holes(self, topology: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find H1 features (loops/holes) appearing in 2+ sources."""
        if len(topology) < 2:
            return []

        # Compare Betti numbers across sources
        holes = []
        betti_by_source = {}
        for name, diagram in topology.items():
            try:
                betti = diagram.betti_numbers_at(1.0)
                betti_by_source[name] = betti
            except Exception:
                continue

        # If multiple sources have H1 > 0, that's convergent
        h1_sources = [
            name for name, betti in betti_by_source.items()
            if betti.get(1, 0) > 0
        ]
        if len(h1_sources) >= 2:
            holes.append({
                "type": "H1_convergent",
                "sources": h1_sources,
                "h1_values": {n: betti_by_source[n].get(1, 0) for n in h1_sources},
                "description": "Loops/holes detected in multiple independent sources",
            })

        return holes

    def _find_convergent_clusters(self, geometry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find spherical (cluster) regions appearing in 2+ sources."""
        if len(geometry) < 2:
            return []

        clusters = []
        spherical_by_source = {}
        for name, curv_result in geometry.items():
            try:
                spherical_by_source[name] = curv_result.num_spherical
            except Exception:
                continue

        # If multiple sources show significant spherical geometry
        cluster_sources = [
            name for name, count in spherical_by_source.items()
            if count > 0
        ]
        if len(cluster_sources) >= 2:
            clusters.append({
                "type": "spherical_convergent",
                "sources": cluster_sources,
                "counts": {n: spherical_by_source[n] for n in cluster_sources},
                "description": "Cluster-like geometry detected in multiple sources",
            })

        return clusters

    def _find_convergent_bridges(self, geometry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find hyperbolic (bridge) regions appearing in 2+ sources."""
        if len(geometry) < 2:
            return []

        bridges = []
        hyperbolic_by_source = {}
        for name, curv_result in geometry.items():
            try:
                hyperbolic_by_source[name] = curv_result.num_hyperbolic
            except Exception:
                continue

        bridge_sources = [
            name for name, count in hyperbolic_by_source.items()
            if count > 0
        ]
        if len(bridge_sources) >= 2:
            bridges.append({
                "type": "hyperbolic_convergent",
                "sources": bridge_sources,
                "counts": {n: hyperbolic_by_source[n] for n in bridge_sources},
                "description": "Bridge-like geometry detected in multiple sources",
            })

        return bridges

    def build_cross_source_edges(
        self, confidence_threshold: float = 0.8
    ) -> int:
        """
        Build sparse cross-source edges where multiple graphs agree.

        Matches by canonical name first (from NameRegistry).
        Only creates edges where confidence > threshold.

        Returns number of cross-source edges created.
        """
        count = 0

        # For each canonical theorem, check which sources contain it
        for canonical in self.name_registry.all_canonical_names():
            info = self.name_registry.get_info(canonical)
            if info is None:
                continue

            # Find sources that have objects matching this theorem
            found_in: Dict[str, str] = {}  # source -> object_name
            for source_name, cat in self.sources.items():
                # Check by canonical name label
                for obj in cat.objects():
                    if obj.metadata.get("canonical_name") == canonical:
                        found_in[source_name] = obj.name
                        break

            # If found in 2+ sources, create cross-source edges
            if len(found_in) >= 2:
                source_names = list(found_in.keys())
                for i in range(len(source_names)):
                    for j in range(i + 1, len(source_names)):
                        s_source = source_names[i]
                        s_target = source_names[j]
                        edge_name = f"cross:{canonical}:{s_source}-{s_target}"

                        # Add objects to cross_source category if not present
                        src_id = f"{s_source}:{found_in[s_source]}"
                        tgt_id = f"{s_target}:{found_in[s_target]}"
                        try:
                            self.cross_source.add(
                                src_id, type_name="CrossRef",
                                metadata={"source": s_source, "canonical": canonical},
                            )
                        except Exception:
                            pass
                        try:
                            self.cross_source.add(
                                tgt_id, type_name="CrossRef",
                                metadata={"source": s_target, "canonical": canonical},
                            )
                        except Exception:
                            pass
                        try:
                            self.cross_source.connect(
                                src_id, tgt_id,
                                name=edge_name,
                                confidence=confidence_threshold,
                                metadata={"cross_source": True, "canonical": canonical},
                            )
                            count += 1
                        except Exception:
                            pass

        return count

    def find_structural_matches(
        self,
        plugin: DomainPlugin,
        top_k: int = 5,
    ) -> List[StructureMatch]:
        """
        Find math subgraphs matching a domain plugin's structure.

        Delegates to StructureMatcher which uses the three-stage funnel.
        """
        from domains.mathematics.structure_match import StructureMatcher

        matcher = StructureMatcher(self)
        return matcher.find_matches(plugin, top_k=top_k)

    def statistics(self) -> Dict[str, Any]:
        """Summary statistics across all sources."""
        stats: Dict[str, Any] = {}
        for name, cat in self.sources.items():
            stats[name] = {
                "objects": len(cat.objects()),
                "morphisms": len(cat.as_edges()),
            }
        stats["cross_source"] = {
            "objects": len(self.cross_source.objects()),
            "morphisms": len(self.cross_source.as_edges()),
        }
        stats["name_registry_size"] = self.name_registry.size
        stats["total_objects"] = sum(s["objects"] for s in stats.values() if isinstance(s, dict) and "objects" in s)
        stats["total_morphisms"] = sum(s["morphisms"] for s in stats.values() if isinstance(s, dict) and "morphisms" in s)
        return stats

    def anchor_proximity(
        self,
        obj_name: str,
        source_name: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Compute distance from an object to anchor problems.

        If source_name given, search only that source.
        Otherwise, search all sources.
        """
        if source_name and source_name in self._anchors:
            return self._anchors[source_name].proximity(obj_name)

        # Search all sources
        for name, anchors in self._anchors.items():
            try:
                result = anchors.proximity(obj_name)
                if any(v > 0 for v in result.values()):
                    return result
            except Exception:
                continue

        return {}
