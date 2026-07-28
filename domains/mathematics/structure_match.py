# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Structure Matching -- Fingerprint + Functor-Based Domain Matching

Three-stage funnel for finding math subgraphs that match a domain:
  1. Fingerprint comparison (cheap) -- topology + geometry + spectral -> distance
  2. Spectral embedding similarity (medium) -- Fiedler vector comparison
  3. Functor construction attempt (expensive) -- category.functor_to() + verify()

Uses existing KOMPOSOS-IV modules:
  - topology/persistent_homology.py  -> PersistentHomologyComputer, SimplicialComplex
  - geometry/ricci.py               -> OllivierRicciCurvature
  - geometry/spectral.py            -> Graph, GraphLaplacian
  - core/functor.py                 -> Functor (with verify())
  - core/category.py                -> Category (functor_to())
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.category import Category
from core.types import Object, Morphism
from domains.plugin_interface import StructureFingerprint, StructureMatch

if TYPE_CHECKING:
    from domains.mathematics.kernel import MathKernel


def compute_fingerprint(category: Category) -> StructureFingerprint:
    """
    Compute structural fingerprint of a Category.

    Uses persistent homology, Ricci curvature, and spectral analysis
    to produce a compact structural signature for fast comparison.
    """
    edges = category.as_edges()
    objs = category.objects()
    obj_count = len(objs)
    mor_count = len(edges)

    betti = {0: 0, 1: 0}
    curv_stats: Dict[str, float] = {}
    spec_data: Dict[str, float] = {}
    community_count = 1

    if mor_count == 0:
        betti[0] = obj_count
        return StructureFingerprint(
            betti_numbers=betti,
            curvature_stats={"mean": 0.0, "std": 0.0,
                             "num_spherical": 0, "num_hyperbolic": 0, "num_euclidean": 0},
            spectral_data={"algebraic_connectivity": 0.0, "spectral_gap": 0.0},
            community_count=obj_count,
            object_count=obj_count,
            morphism_count=0,
        )

    # ---- Persistent Homology ----
    try:
        from topology.persistent_homology import SimplicialComplex, PersistentHomologyComputer

        # Build integer-indexed edges for simplicial complex
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
        diagram = computer.compute(sc)
        # Get Betti numbers at a reasonable filtration value
        betti = diagram.betti_numbers_at(1.0)
    except Exception:
        # Fallback: estimate H0 from connected components via union-find
        parent = {}

        def find(x):
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for s, t, w in edges:
            union(s, t)
        for obj in objs:
            find(obj.name)
        components = len(set(find(obj.name) for obj in objs))
        betti = {0: components, 1: 0}

    # ---- Ricci Curvature ----
    try:
        from geometry.ricci import OllivierRicciCurvature

        ricci = OllivierRicciCurvature(category)
        curv_result = ricci.compute_all_curvatures()
        curv_stats = dict(curv_result.statistics)
        curv_stats["num_spherical"] = curv_result.num_spherical
        curv_stats["num_hyperbolic"] = curv_result.num_hyperbolic
        curv_stats["num_euclidean"] = curv_result.num_euclidean
    except Exception:
        curv_stats = {
            "mean": 0.0, "std": 0.0,
            "num_spherical": 0, "num_hyperbolic": 0, "num_euclidean": 0,
        }

    # ---- Spectral Analysis ----
    try:
        from geometry.spectral import Graph, GraphLaplacian

        # Build undirected graph for spectral analysis (integer nodes)
        name_to_idx: Dict[str, int] = {}
        for obj in objs:
            name_to_idx[obj.name] = len(name_to_idx)
        graph = Graph()
        for s, t, w in edges:
            s_idx = name_to_idx.get(s)
            t_idx = name_to_idx.get(t)
            if s_idx is not None and t_idx is not None:
                graph.add_edge(s_idx, t_idx, w)

        laplacian = GraphLaplacian(graph)
        laplacian.compute_spectrum()
        alg_conn = laplacian.algebraic_connectivity()
        eigenvalues = laplacian.eigenvalues if hasattr(laplacian, 'eigenvalues') else []
        spectral_gap = 0.0
        if len(eigenvalues) >= 2:
            spectral_gap = eigenvalues[1] - eigenvalues[0] if eigenvalues[1] > 0 else 0.0

        spec_data = {
            "algebraic_connectivity": alg_conn,
            "spectral_gap": spectral_gap,
        }

        # Community detection for community_count
        try:
            analyzer = laplacian  # SpectralAnalyzer if available
            if hasattr(analyzer, 'detect_communities'):
                communities = analyzer.detect_communities()
                community_count = len(set(communities.values())) if communities else 1
            else:
                community_count = 1
        except Exception:
            community_count = 1
    except Exception:
        spec_data = {"algebraic_connectivity": 0.0, "spectral_gap": 0.0}

    return StructureFingerprint(
        betti_numbers=betti,
        curvature_stats=curv_stats,
        spectral_data=spec_data,
        community_count=community_count,
        object_count=obj_count,
        morphism_count=mor_count,
    )


class StructureMatcher:
    """
    Finds math subgraphs that structurally match a domain plugin.

    Three-stage funnel:
      1. Fingerprint comparison (cheap) -- filters 95%+ of candidates
      2. Spectral similarity (medium) -- ranks surviving candidates
      3. Functor construction (expensive) -- validates top candidates
    """

    def __init__(self, kernel: MathKernel):
        self.kernel = kernel

    def find_matches(
        self,
        plugin,  # DomainPlugin
        top_k: int = 5,
    ) -> List[StructureMatch]:
        """
        Find math subgraphs matching the plugin's structure.

        Returns up to top_k StructureMatch objects sorted by confidence.
        """
        # Compute plugin's fingerprint
        plugin_fp = plugin.structure_fingerprint()

        # Stage 1: Fingerprint comparison against each source
        candidates = []
        for source_name, source_cat in self.kernel.sources.items():
            if len(source_cat.objects()) == 0:
                continue

            # Get communities from this source
            communities = self._extract_communities(source_cat)
            for comm_name, comm_cat in communities.items():
                comm_fp = compute_fingerprint(comm_cat)
                dist = plugin_fp.distance(comm_fp)
                candidates.append((source_name, comm_name, comm_cat, comm_fp, dist))

            # Also compare against the whole source
            source_fp = compute_fingerprint(source_cat)
            dist = plugin_fp.distance(source_fp)
            candidates.append((source_name, "whole", source_cat, source_fp, dist))

        if not candidates:
            return []

        # Sort by fingerprint distance (lower = better match)
        candidates.sort(key=lambda x: x[4])

        # Stage 2 + 3: Attempt functor construction for top candidates
        matches = []
        for source_name, comm_name, comm_cat, comm_fp, dist in candidates[: top_k * 3]:
            match = self._attempt_match(
                plugin, source_name, comm_name, comm_cat, dist
            )
            if match is not None:
                matches.append(match)

        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[:top_k]

    def _extract_communities(self, category: Category) -> Dict[str, Category]:
        """
        Extract spectral communities as sub-Categories.

        Each community becomes an in-memory Category containing only
        the objects and morphisms in that community.
        """
        objs = category.objects()
        if len(objs) < 4:
            return {}

        # Try spectral clustering
        try:
            from geometry.spectral import Graph, GraphLaplacian

            # Build integer-indexed graph for spectral analysis
            name_to_idx: Dict[str, int] = {}
            for obj in objs:
                name_to_idx[obj.name] = len(name_to_idx)
            idx_to_name = {v: k for k, v in name_to_idx.items()}

            graph = Graph()
            edges = category.as_edges()
            for s, t, w in edges:
                s_idx = name_to_idx.get(s)
                t_idx = name_to_idx.get(t)
                if s_idx is not None and t_idx is not None:
                    graph.add_edge(s_idx, t_idx, w)

            laplacian = GraphLaplacian(graph)
            laplacian.compute_spectrum()

            # Use Fiedler vector for bipartition as simplest community detection
            if hasattr(laplacian, 'eigenvectors') and laplacian.eigenvectors is not None:
                import numpy as np
                fiedler = laplacian.eigenvectors[:, 1] if laplacian.eigenvectors.shape[1] > 1 else None
                if fiedler is not None:
                    nodes = sorted(graph.nodes)  # integer indices
                    communities: Dict[str, Category] = {}

                    # Bipartition by Fiedler vector sign
                    for label_name, condition in [("community_A", lambda v: v >= 0),
                                                   ("community_B", lambda v: v < 0)]:
                        member_names = {
                            idx_to_name[nodes[i]] for i in range(len(nodes))
                            if i < len(fiedler) and condition(fiedler[i])
                            and nodes[i] in idx_to_name
                        }
                        if len(member_names) < 2:
                            continue

                        sub_cat = Category(name=label_name, db_path=":memory:")
                        for obj in objs:
                            if obj.name in member_names:
                                sub_cat.add_object(Object(
                                    name=obj.name,
                                    type_name=obj.type_name,
                                    metadata=dict(obj.metadata),
                                ))
                        for s, t, w in edges:
                            if s in member_names and t in member_names:
                                sub_cat.connect(s, t, name=f"{s}->{t}", confidence=w)
                        if len(sub_cat.objects()) >= 2:
                            communities[label_name] = sub_cat

                    return communities
        except Exception:
            pass

        # Fallback: field-based communities from metadata
        field_groups: Dict[str, List[Object]] = {}
        for obj in objs:
            field = obj.metadata.get("field", "unknown")
            field_groups.setdefault(field, []).append(obj)

        communities = {}
        edges = category.as_edges()
        edge_set = {(s, t): w for s, t, w in edges}

        for field_name, field_objs in field_groups.items():
            if len(field_objs) < 2:
                continue
            member_names = {o.name for o in field_objs}
            sub_cat = Category(name=f"field_{field_name}", db_path=":memory:")
            for obj in field_objs:
                sub_cat.add_object(Object(
                    name=obj.name,
                    type_name=obj.type_name,
                    metadata=dict(obj.metadata),
                ))
            for s, t, w in edges:
                if s in member_names and t in member_names:
                    sub_cat.connect(s, t, name=f"{s}->{t}", confidence=w)
            if len(sub_cat.objects()) >= 2 and len(sub_cat.as_edges()) >= 1:
                communities[f"field_{field_name}"] = sub_cat

        return communities

    def _attempt_match(
        self,
        plugin,
        source_name: str,
        comm_name: str,
        comm_cat: Category,
        fingerprint_dist: float,
    ) -> Optional[StructureMatch]:
        """
        Attempt to build a functor from plugin.category to comm_cat.

        Uses type-based or name-based heuristics for the object map,
        then calls functor_to() + verify().
        """
        plugin_objs = plugin.category.objects()
        comm_objs = comm_cat.objects()

        if not plugin_objs or not comm_objs:
            return None

        # Try to build object_map via type matching
        object_map = self._build_object_map(plugin_objs, comm_objs)

        if not object_map:
            # Even without a functor, the fingerprint match is still informative
            confidence = max(0.0, 1.0 - fingerprint_dist)
            return StructureMatch(
                domain_name=plugin.name,
                math_region=f"{source_name}/{comm_name}",
                fingerprint_distance=fingerprint_dist,
                functor_verification={},
                confidence=confidence * 0.5,  # Lower confidence without functor
            )

        # Attempt functor construction
        try:
            functor = plugin.category.functor_to(
                comm_cat,
                object_map=object_map,
            )
            verification = functor.verify()
            # Score: fingerprint closeness + functor preservation
            fp_score = max(0.0, 1.0 - fingerprint_dist)
            functor_score = sum(1 for v in verification.values() if v) / max(
                len(verification), 1
            )
            confidence = 0.4 * fp_score + 0.6 * functor_score

            return StructureMatch(
                domain_name=plugin.name,
                math_region=f"{source_name}/{comm_name}",
                fingerprint_distance=fingerprint_dist,
                functor_verification=verification,
                confidence=confidence,
                evidence={"object_map": object_map},
            )
        except Exception:
            confidence = max(0.0, 1.0 - fingerprint_dist) * 0.5
            return StructureMatch(
                domain_name=plugin.name,
                math_region=f"{source_name}/{comm_name}",
                fingerprint_distance=fingerprint_dist,
                confidence=confidence,
            )

    @staticmethod
    def _build_object_map(
        plugin_objs: list, comm_objs: list
    ) -> Dict[str, str]:
        """
        Build object map from plugin objects to math community objects.

        Uses type_name matching as primary heuristic.
        Falls back to positional matching if types don't help.
        """
        # Group community objects by type
        comm_by_type: Dict[str, List] = {}
        for obj in comm_objs:
            comm_by_type.setdefault(obj.type_name, []).append(obj)

        object_map: Dict[str, str] = {}
        used_targets = set()

        # Match by type first
        for p_obj in plugin_objs:
            candidates = comm_by_type.get(p_obj.type_name, [])
            for c_obj in candidates:
                if c_obj.name not in used_targets:
                    object_map[p_obj.name] = c_obj.name
                    used_targets.add(c_obj.name)
                    break

        # For unmatched, try any available target
        unmatched_targets = [o for o in comm_objs if o.name not in used_targets]
        unmatched_plugins = [o for o in plugin_objs if o.name not in object_map]
        for p_obj, c_obj in zip(unmatched_plugins, unmatched_targets):
            object_map[p_obj.name] = c_obj.name

        return object_map
