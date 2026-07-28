# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Theorem Knowledge Graph - Full-corpus KG backed by KOMPOSOS Category.

Ingests LeanDojo/Mathlib4 theorems into a Category, then applies real
categorical math for retrieval:

1. Spectral clustering (GraphLaplacian) groups theorems by mathematical domain
2. Composition paths find theorem chains (A depends_on B depends_on C)
3. Yoneda pattern matching finds structurally similar theorems
4. Kan extensions predict which theorems are relevant to unseen problems

The LLM doesn't guess which theorems to use -- the KG tells it.
"""

import sys
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

sys.path.insert(0, '.')

from core.category import Category
from core.types import Object, Morphism
from geometry.spectral import Graph, GraphLaplacian, SpectralClustering


# ---------------------------------------------------------------------------
# Theorem KG
# ---------------------------------------------------------------------------

class TheoremKG:
    """
    Full-corpus theorem knowledge graph.

    Stores theorems as Objects in a Category, dependencies as Morphisms.
    Uses spectral clustering, composition paths, and Yoneda similarity
    to retrieve relevant theorem chains for a given problem.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.category = Category(db_path=db_path)
        self._graph: Optional[Graph] = None
        self._node_to_name: Dict[int, str] = {}
        self._name_to_node: Dict[str, int] = {}
        self._clusters: Optional[Dict[int, List[int]]] = None
        self._cluster_of: Dict[int, int] = {}
        self._outgoing: Dict[str, List[Morphism]] = {}
        self._incoming: Dict[str, List[Morphism]] = {}
        self._loaded = False
        self._analyzed = False
        # Keyword index: word -> set of theorem names
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        # Theorem code cache: name -> code/statement
        self._theorem_code: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_corpus(self, adapter=None):
        """
        Load theorems from LeanDojo adapter into Category.

        MUST provide adapter - no demo data.
        """
        if self._loaded:
            return

        if adapter is None:
            # Load full corpus
            from domains.mathematics.leandojo_adapter import LeanDojoAdapter
            import os
            corpus_dir = "data_sources/leandojo/leandojo_benchmark_4"
            if not os.path.isdir(corpus_dir):
                raise FileNotFoundError(f"Full corpus not found at {corpus_dir}")
            adapter = LeanDojoAdapter(data_path=corpus_dir)

        result = adapter.load_into(self.category)
        self._loaded = True
        self._build_indices()
        return result

    def _load_demo_corpus(self):
        """Load a representative demo corpus for testing."""
        # Real Mathlib4 theorem names and their relationships
        theorems = [
            # Number theory cluster
            ("Nat.Prime", "theorem", "A natural number is prime iff > 1 and only divisible by 1 and itself", "number_theory"),
            ("Nat.Prime.dvd_mul", "theorem", "If p prime and p | a*b then p | a or p | b", "number_theory"),
            ("Nat.Prime.eq_one_or_self_of_dvd", "theorem", "If p prime and d | p then d = 1 or d = p", "number_theory"),
            ("Nat.gcd_comm", "theorem", "gcd(a,b) = gcd(b,a)", "number_theory"),
            ("Nat.gcd_assoc", "theorem", "gcd(gcd(a,b),c) = gcd(a,gcd(b,c))", "number_theory"),
            ("Nat.lcm_comm", "theorem", "lcm(a,b) = lcm(b,a)", "number_theory"),
            ("Nat.Coprime.mul_dvd_of_dvd_of_dvd", "theorem", "If gcd(a,b)=1 and a|n and b|n then a*b|n", "number_theory"),
            ("Int.emod_emod_of_dvd", "theorem", "a % n % m = a % m when m | n", "number_theory"),
            ("ZMod.val_coe_unit_coprime", "theorem", "Units in Z/nZ are exactly the coprime residues", "number_theory"),
            ("Nat.totient", "definition", "Euler's totient: count of k < n with gcd(k,n) = 1", "number_theory"),
            ("Nat.card_units_zmod_eq_totient", "theorem", "Number of units in Z/nZ equals totient(n)", "number_theory"),
            ("Nat.even_or_odd", "theorem", "Every natural number is even or odd", "number_theory"),
            ("Int.sq_sub_sq", "theorem", "a^2 - b^2 = (a+b)*(a-b)", "number_theory"),
            ("Nat.Prime.dvd_factorial", "theorem", "p prime divides n! iff p <= n", "number_theory"),
            ("Nat.Chinese_remainder", "theorem", "CRT: system of congruences with coprime moduli has unique solution", "number_theory"),
            ("Nat.Prime.Fermat_little", "theorem", "a^p = a (mod p) for prime p", "number_theory"),

            # Algebra cluster
            ("Polynomial.roots", "definition", "Multiset of roots of a polynomial", "algebra"),
            ("Polynomial.sum_roots_eq_neg_coeff", "theorem", "Sum of roots = -b/a for quadratic (Vieta)", "algebra"),
            ("Polynomial.prod_roots_eq_const_coeff", "theorem", "Product of roots = c/a for quadratic (Vieta)", "algebra"),
            ("Polynomial.eval_eq_sum_range", "theorem", "p(x) = sum of a_i * x^i", "algebra"),
            ("Polynomial.div_mod_by_monic", "theorem", "Division algorithm for polynomials", "algebra"),
            ("RingHom.map_sum", "theorem", "Ring homomorphisms preserve sums", "algebra"),
            ("Finset.sum_geometric", "theorem", "sum_{i=0}^{n-1} r^i = (r^n - 1)/(r - 1)", "algebra"),
            ("Finset.sum_range_id", "theorem", "sum_{i=0}^{n-1} i = n*(n-1)/2", "algebra"),
            ("Real.sqrt_sq", "theorem", "sqrt(x^2) = |x|", "algebra"),
            ("abs_sub_abs_le_abs_sub", "theorem", "| |a| - |b| | <= |a - b| (reverse triangle)", "algebra"),
            ("sq_nonneg", "theorem", "x^2 >= 0 for all x", "algebra"),
            ("mul_self_le_mul_self", "theorem", "0 <= a <= b implies a^2 <= b^2", "algebra"),
            ("ArithmeticSequence.sum", "theorem", "Sum of arithmetic sequence = n*(a1+an)/2", "algebra"),
            ("GeometricSequence.nth_term", "theorem", "a_n = a_1 * r^(n-1)", "algebra"),
            ("GeometricSequence.sum", "theorem", "Sum = a*(1-r^n)/(1-r)", "algebra"),

            # Geometry cluster
            ("EuclideanGeometry.dist_sq", "theorem", "d(P,Q)^2 = (x2-x1)^2 + (y2-y1)^2", "geometry"),
            ("EuclideanGeometry.Pythagoras", "theorem", "a^2 + b^2 = c^2 for right triangle", "geometry"),
            ("Circle.chord_length", "theorem", "chord = 2*sqrt(r^2 - d^2) where d is distance to center", "geometry"),
            ("Circle.area", "theorem", "Area = pi * r^2", "geometry"),
            ("Circle.circumference", "theorem", "C = 2 * pi * r", "geometry"),
            ("Triangle.area_base_height", "theorem", "Area = base * height / 2", "geometry"),
            ("Triangle.sine_rule", "theorem", "a/sin(A) = b/sin(B) = c/sin(C) = 2R", "geometry"),
            ("Triangle.cosine_rule", "theorem", "c^2 = a^2 + b^2 - 2ab*cos(C)", "geometry"),
            ("Angle.sum_triangle", "theorem", "Angles of triangle sum to pi", "geometry"),
            ("Similar.ratio_preserved", "theorem", "Similar triangles have proportional sides", "geometry"),
            ("Power_of_point", "theorem", "PA*PB = PC*PD for intersecting chords/secants", "geometry"),

            # Combinatorics cluster
            ("Finset.card_powerset", "theorem", "|P(S)| = 2^|S|", "combinatorics"),
            ("Nat.choose_symm", "theorem", "C(n,k) = C(n,n-k)", "combinatorics"),
            ("Nat.choose_succ_succ", "theorem", "C(n+1,k+1) = C(n,k) + C(n,k+1) (Pascal)", "combinatorics"),
            ("Nat.add_choose_eq", "theorem", "C(n,k) = n! / (k! * (n-k)!)", "combinatorics"),
            ("Finset.card_sdiff", "theorem", "|A \\ B| = |A| - |A inter B|", "combinatorics"),
            ("Finset.card_union_add_card_inter", "theorem", "|A union B| + |A inter B| = |A| + |B|", "combinatorics"),
            ("Fintype.card_perm", "theorem", "Number of permutations of n = n!", "combinatorics"),
            ("Finset.sum_card_inter", "theorem", "Inclusion-exclusion principle", "combinatorics"),
            ("Nat.factorial_pos", "theorem", "n! > 0", "combinatorics"),
            ("Pigeonhole", "theorem", "If n+1 pigeons in n holes, some hole has >= 2", "combinatorics"),
            ("Stirling.second", "theorem", "S(n,k) = k*S(n-1,k) + S(n-1,k-1)", "combinatorics"),

            # Probability cluster
            ("ProbabilityTheory.measure_union", "theorem", "P(A union B) = P(A) + P(B) - P(A inter B)", "probability"),
            ("ProbabilityTheory.measure_compl", "theorem", "P(A^c) = 1 - P(A)", "probability"),
            ("ProbabilityTheory.Binomial.pmf", "theorem", "P(X=k) = C(n,k) * p^k * (1-p)^(n-k)", "probability"),
            ("ProbabilityTheory.cond_eq_div", "theorem", "P(A|B) = P(A inter B) / P(B)", "probability"),
            ("ProbabilityTheory.expected_value_sum", "theorem", "E[X+Y] = E[X] + E[Y] (linearity)", "probability"),
            ("ProbabilityTheory.variance_eq", "theorem", "Var(X) = E[X^2] - E[X]^2", "probability"),
            ("ProbabilityTheory.Geometric.pmf", "theorem", "P(X=k) = (1-p)^(k-1) * p", "probability"),
            ("ProbabilityTheory.Bayes", "theorem", "P(A|B) = P(B|A)*P(A) / P(B)", "probability"),
        ]

        # Dependencies (theorem A depends on / uses theorem B)
        dependencies = [
            # Number theory chains
            ("Nat.Prime.dvd_mul", "Nat.Prime"),
            ("Nat.Prime.eq_one_or_self_of_dvd", "Nat.Prime"),
            ("Nat.Coprime.mul_dvd_of_dvd_of_dvd", "Nat.gcd_comm"),
            ("Nat.card_units_zmod_eq_totient", "Nat.totient"),
            ("Nat.card_units_zmod_eq_totient", "ZMod.val_coe_unit_coprime"),
            ("Int.sq_sub_sq", "sq_nonneg"),
            ("Nat.Prime.dvd_factorial", "Nat.Prime"),
            ("Nat.Prime.dvd_factorial", "Nat.Prime.dvd_mul"),
            ("Nat.Chinese_remainder", "Nat.Coprime.mul_dvd_of_dvd_of_dvd"),
            ("Nat.Chinese_remainder", "Int.emod_emod_of_dvd"),
            ("Nat.Prime.Fermat_little", "Nat.Prime"),
            ("Nat.Prime.Fermat_little", "Nat.card_units_zmod_eq_totient"),

            # Algebra chains
            ("Polynomial.sum_roots_eq_neg_coeff", "Polynomial.roots"),
            ("Polynomial.prod_roots_eq_const_coeff", "Polynomial.roots"),
            ("Polynomial.eval_eq_sum_range", "RingHom.map_sum"),
            ("Real.sqrt_sq", "sq_nonneg"),
            ("mul_self_le_mul_self", "sq_nonneg"),
            ("GeometricSequence.sum", "Finset.sum_geometric"),
            ("GeometricSequence.nth_term", "GeometricSequence.sum"),
            ("ArithmeticSequence.sum", "Finset.sum_range_id"),

            # Geometry chains
            ("Circle.chord_length", "EuclideanGeometry.Pythagoras"),
            ("Circle.chord_length", "EuclideanGeometry.dist_sq"),
            ("Triangle.cosine_rule", "EuclideanGeometry.Pythagoras"),
            ("Triangle.sine_rule", "Angle.sum_triangle"),
            ("Power_of_point", "Similar.ratio_preserved"),

            # Combinatorics chains
            ("Nat.choose_succ_succ", "Nat.choose_symm"),
            ("Nat.add_choose_eq", "Nat.factorial_pos"),
            ("Finset.sum_card_inter", "Finset.card_union_add_card_inter"),
            ("Finset.sum_card_inter", "Finset.card_sdiff"),
            ("Fintype.card_perm", "Nat.factorial_pos"),

            # Probability chains
            ("ProbabilityTheory.Binomial.pmf", "Nat.add_choose_eq"),
            ("ProbabilityTheory.cond_eq_div", "ProbabilityTheory.measure_union"),
            ("ProbabilityTheory.Bayes", "ProbabilityTheory.cond_eq_div"),
            ("ProbabilityTheory.variance_eq", "ProbabilityTheory.expected_value_sum"),
            ("ProbabilityTheory.Geometric.pmf", "ProbabilityTheory.measure_compl"),

            # Cross-domain links
            ("ProbabilityTheory.Binomial.pmf", "Nat.choose_succ_succ"),
            ("Nat.Prime.dvd_factorial", "Nat.add_choose_eq"),
        ]

        # Add objects
        for name, kind, statement, domain in theorems:
            obj = Object(
                name=name,
                type_name=kind,
                metadata={
                    "statement": statement,
                    "domain": domain,
                    "kind": kind,
                },
            )
            self.category.add_object(obj)
            self._theorem_code[name] = statement

        # Add dependency morphisms
        for src, tgt in dependencies:
            self.category.connect(src, tgt, name=f"{src}--depends_on-->{tgt}",
                                  confidence=0.95)

    def _build_indices(self):
        """Build keyword index and morphism indices."""
        # Keyword index
        for obj in self.category.objects():
            name_parts = obj.name.replace(".", " ").replace("_", " ").lower().split()
            statement = obj.metadata.get("statement", "").lower()
            statement_words = set(statement.split())
            all_words = set(name_parts) | statement_words
            for word in all_words:
                if len(word) > 2:
                    self._keyword_index[word].add(obj.name)
            # Also index the domain
            domain = obj.metadata.get("domain", "")
            if domain:
                self._keyword_index[domain].add(obj.name)

        # Morphism indices for fast graph traversal
        self._outgoing = defaultdict(list)
        self._incoming = defaultdict(list)
        for mor in self.category.morphisms():
            self._outgoing[mor.source].append(mor)
            self._incoming[mor.target].append(mor)

    # ------------------------------------------------------------------
    # Structural Analysis (real KOMPOSOS math)
    # ------------------------------------------------------------------

    def analyze_structure(self):
        """
        Run spectral analysis on the theorem graph.

        Builds a Graph from Category morphisms, computes:
        - GraphLaplacian eigenvalues (connectivity)
        - SpectralClustering (domain grouping)
        """
        if self._analyzed:
            return

        objects = self.category.objects()
        morphisms = self.category.morphisms()

        if not objects or not morphisms:
            self._analyzed = True
            return

        # Map names to integer node IDs (spectral.py requires int nodes)
        self._node_to_name = {}
        self._name_to_node = {}
        for i, obj in enumerate(objects):
            self._node_to_name[i] = obj.name
            self._name_to_node[obj.name] = i

        # Build spectral graph
        self._graph = Graph()
        for mor in morphisms:
            src_id = self._name_to_node.get(mor.source)
            tgt_id = self._name_to_node.get(mor.target)
            if src_id is not None and tgt_id is not None:
                self._graph.add_edge(src_id, tgt_id, weight=mor.confidence)

        # Spectral clustering
        n_clusters = min(6, max(2, len(objects) // 8))
        try:
            sc = SpectralClustering(self._graph, n_clusters=n_clusters)
            labels = sc.cluster()
            # Group nodes by cluster
            self._clusters = defaultdict(list)
            for node_id, cluster_id in enumerate(labels):
                if node_id < len(objects):
                    self._clusters[cluster_id].append(node_id)
                    self._cluster_of[node_id] = cluster_id
        except Exception:
            # Fallback: use domain metadata as clusters
            self._clusters = defaultdict(list)
            domain_map = {"number_theory": 0, "algebra": 1, "geometry": 2,
                          "combinatorics": 3, "probability": 4}
            for i, obj in enumerate(objects):
                d = obj.metadata.get("domain", "other")
                cid = domain_map.get(d, 5)
                self._clusters[cid].append(i)
                self._cluster_of[i] = cid

        # Ricci curvature for theorem importance (cached)
        import pickle
        import os
        cache_file = "theorem_kg_ricci_cache.pkl"

        if os.path.exists(cache_file):
            # Load from cache (instant)
            with open(cache_file, 'rb') as f:
                self._ricci_scores = pickle.load(f)
        else:
            # Compute once (slow, ~10 min), then cache forever
            self._ricci_scores = {}
            try:
                from geometry.ricci import OllivierRicciCurvature
                ricci = OllivierRicciCurvature(self._graph)
                ricci_result = ricci.compute_all_curvatures()
                # Convert edge curvatures to node importance scores
                node_curvatures = {}
                for edge, curv in ricci_result.edge_curvatures.items():
                    src, tgt = edge
                    node_curvatures[src] = node_curvatures.get(src, 0) + abs(curv)
                    node_curvatures[tgt] = node_curvatures.get(tgt, 0) + abs(curv)
                self._ricci_scores = node_curvatures
                # Cache to disk
                with open(cache_file, 'wb') as f:
                    pickle.dump(self._ricci_scores, f)
            except Exception:
                # Fallback: no Ricci ranking
                self._ricci_scores = {}

        self._analyzed = True

    # ------------------------------------------------------------------
    # Query: The main retrieval interface
    # ------------------------------------------------------------------

    def query(self, problem_text: str, domain: Optional[str] = None,
              top_k: int = 10) -> "KGQueryResult":
        """
        Query the KG for theorems relevant to a problem.

        Uses three KOMPOSOS strategies:
        1. Keyword search -> seed theorems
        2. Spectral clustering -> cluster neighbors of seeds
        3. Composition paths -> theorem chains through seeds
        4. Yoneda similarity -> structurally analogous theorems

        Returns KGQueryResult with theorems, chains, and insights.
        """
        if not self._loaded:
            self.ingest_corpus()
        if not self._analyzed:
            self.analyze_structure()

        result = KGQueryResult()

        # Step 1: Keyword match to find seed theorems
        seeds = self._keyword_search(problem_text, domain, top_k=top_k)
        result.seed_theorems = seeds

        if not seeds:
            return result

        # Step 2: Cluster expansion - find related theorems in same clusters
        cluster_peers = self._cluster_expansion(seeds, max_extra=5)
        result.cluster_theorems = cluster_peers

        # Step 3: Composition paths - find theorem chains
        chains = self._find_composition_chains(seeds)
        result.theorem_chains = chains

        # Step 4: Yoneda similarity - find structurally analogous theorems
        analogues = self._yoneda_search(seeds, max_results=5)
        result.yoneda_analogues = analogues

        # Step 5: Kan extension - predict missing theorems
        kan_predictions = self._kan_predict(seeds, domain, max_results=3)
        result.kan_predictions = kan_predictions

        # Step 6: Oracle strategies - additional categorical inference
        oracle_results = self._apply_oracle_strategies(seeds, domain)
        result.oracle_results = oracle_results

        # Build final ranked list
        all_names = set()
        for name, score in seeds:
            all_names.add(name)
        for name, score in cluster_peers:
            all_names.add(name)
        for chain in chains:
            for name in chain:
                all_names.add(name)
        for name, sim in analogues:
            all_names.add(name)
        for name, pred_score in kan_predictions:
            all_names.add(name)
        for name, oracle_score in oracle_results:
            all_names.add(name)

        # Score and rank all theorems
        scored = []
        for name in all_names:
            score = 0.0
            # Seed match
            for sn, ss in seeds:
                if sn == name:
                    score += ss * 2.0
            # Cluster peer
            for cn, cs in cluster_peers:
                if cn == name:
                    score += cs * 1.0
            # Chain member
            for chain in chains:
                if name in chain:
                    score += 0.5
            # Yoneda analogue
            for yn, ys in analogues:
                if yn == name:
                    score += ys * 1.5
            # Kan prediction
            for kn, ks in kan_predictions:
                if kn == name:
                    score += ks * 1.8
            # Oracle strategies
            for on, os in oracle_results:
                if on == name:
                    score += os * 2.0
            # Ricci curvature (bridge vs hub)
            node_id = self._name_to_node.get(name)
            if node_id is not None and node_id in self._ricci_scores:
                curvature = self._ricci_scores[node_id]
                # Negative curvature = bridge (connect domains) → boost
                # Positive curvature = hub (central) → boost
                # Use absolute value to boost both bridges and hubs
                score += abs(curvature) * 0.3
            scored.append((name, score))

        scored.sort(key=lambda x: -x[1])
        result.ranked_theorems = scored[:top_k]

        return result

    # ------------------------------------------------------------------
    # Strategy 1: Keyword search
    # ------------------------------------------------------------------

    def _keyword_search(self, problem_text: str, domain: Optional[str],
                        top_k: int = 10) -> List[Tuple[str, float]]:
        """Find theorems matching problem keywords."""
        words = problem_text.lower().replace(",", " ").replace(".", " ").split()
        words = [w for w in words if len(w) > 2]

        # Score each theorem by keyword overlap
        scores: Dict[str, float] = defaultdict(float)
        for word in words:
            # Direct match
            for name in self._keyword_index.get(word, set()):
                scores[name] += 1.0
            # Partial match (word is substring of indexed term)
            for indexed_word, names in self._keyword_index.items():
                if word in indexed_word or indexed_word in word:
                    for name in names:
                        scores[name] += 0.5

        # Boost by domain match
        if domain:
            domain_lower = domain.lower().replace(" ", "_")
            for name in self._keyword_index.get(domain_lower, set()):
                scores[name] += 2.0

        # Normalize and sort
        if not scores:
            return []
        max_score = max(scores.values())
        results = [(name, score / max_score) for name, score in scores.items()]
        results.sort(key=lambda x: -x[1])
        return results[:top_k]

    # ------------------------------------------------------------------
    # Strategy 2: Spectral cluster expansion
    # ------------------------------------------------------------------

    def _cluster_expansion(self, seeds: List[Tuple[str, float]],
                           max_extra: int = 5) -> List[Tuple[str, float]]:
        """Find cluster peers of seed theorems (spectral grouping)."""
        if self._clusters is None:
            return []

        seed_names = {name for name, _ in seeds}
        seed_clusters = set()

        for name, _ in seeds:
            nid = self._name_to_node.get(name)
            if nid is not None and nid in self._cluster_of:
                seed_clusters.add(self._cluster_of[nid])

        # Collect peers from same clusters (not already in seeds)
        peers = []
        for cid in seed_clusters:
            for nid in self._clusters.get(cid, []):
                name = self._node_to_name.get(nid, "")
                if name and name not in seed_names:
                    peers.append((name, 0.6))

        return peers[:max_extra]

    # ------------------------------------------------------------------
    # Strategy 3: Composition paths (transitive theorem chains)
    # ------------------------------------------------------------------

    def _find_composition_chains(self, seeds: List[Tuple[str, float]],
                                 max_depth: int = 3) -> List[List[str]]:
        """
        Find composition paths between seed theorems.

        If seed A depends_on X depends_on seed B, return [A, X, B].
        These are the theorem chains the LLM should follow.
        """
        seed_names = {name for name, _ in seeds}
        chains = []

        # For each pair of seeds, find connecting paths via Category
        seed_list = [name for name, _ in seeds[:6]]  # limit pairs

        for i, src in enumerate(seed_list):
            # Follow outgoing dependencies up to max_depth
            visited = set()
            self._dfs_chains(src, [], visited, chains, seed_names, max_depth)

        # Deduplicate and sort by length (shorter = more direct)
        unique = []
        seen = set()
        for chain in chains:
            key = tuple(chain)
            if key not in seen and len(chain) >= 2:
                seen.add(key)
                unique.append(chain)
        unique.sort(key=len)
        return unique[:10]

    def _dfs_chains(self, current: str, path: List[str], visited: Set[str],
                    chains: List[List[str]], seeds: Set[str],
                    max_depth: int):
        """DFS to find theorem chains."""
        if current in visited:
            return
        visited.add(current)
        path = path + [current]

        if len(path) > 1 and current in seeds:
            chains.append(path[:])

        if len(path) >= max_depth:
            return

        for mor in self._outgoing.get(current, []):
            self._dfs_chains(mor.target, path, visited, chains, seeds, max_depth)
        for mor in self._incoming.get(current, []):
            self._dfs_chains(mor.source, path, visited, chains, seeds, max_depth)

    # ------------------------------------------------------------------
    # Strategy 4: Yoneda pattern matching
    # ------------------------------------------------------------------

    def _yoneda_search(self, seeds: List[Tuple[str, float]],
                       max_results: int = 5) -> List[Tuple[str, float]]:
        """
        Find theorems with similar morphism patterns to seed theorems.

        Yoneda lemma: Hom(A, -) determines A. If two theorems have
        similar dependency profiles, they play similar structural roles.
        """
        seed_names = {name for name, _ in seeds}
        if not seed_names:
            return []

        # Build Hom profiles for seeds
        seed_profiles: Dict[str, Set[str]] = {}
        for name in seed_names:
            out_targets = {m.target for m in self._outgoing.get(name, [])}
            in_sources = {m.source for m in self._incoming.get(name, [])}
            seed_profiles[name] = out_targets | in_sources

        # Compare against all non-seed theorems
        candidates = []
        for obj in self.category.objects():
            if obj.name in seed_names:
                continue
            obj_out = {m.target for m in self._outgoing.get(obj.name, [])}
            obj_in = {m.source for m in self._incoming.get(obj.name, [])}
            obj_profile = obj_out | obj_in

            if not obj_profile:
                continue

            # Compute max Yoneda similarity to any seed
            best_sim = 0.0
            for sp in seed_profiles.values():
                if not sp:
                    continue
                intersection = len(sp & obj_profile)
                union = len(sp | obj_profile)
                if union > 0:
                    sim = intersection / union
                    best_sim = max(best_sim, sim)

            if best_sim > 0.15:
                candidates.append((obj.name, best_sim))

        candidates.sort(key=lambda x: -x[1])
        return candidates[:max_results]

    def _kan_predict(self, seeds: List[Tuple[str, float]],
                     domain: Optional[str] = None,
                     max_results: int = 3) -> List[Tuple[str, float]]:
        """
        Use Kan extension to predict missing theorems.

        Idea: Given seeds {A, B, C}, find theorems D such that:
        - D is in the "completion" of the structure formed by {A, B, C}
        - D shares common dependencies with seeds
        - D fills gaps in the dependency chain
        """
        seed_names = {name for name, _ in seeds}
        if not seed_names:
            return []

        # Find theorems that are:
        # 1. Depended on by multiple seeds (common prerequisites)
        # 2. Depend on multiple seeds (common consequences)
        prerequisites = defaultdict(int)
        consequences = defaultdict(int)

        for seed_name in seed_names:
            # Prerequisites: what does this seed depend on?
            for mor in self._outgoing.get(seed_name, []):
                if mor.target not in seed_names:
                    prerequisites[mor.target] += 1
            # Consequences: what depends on this seed?
            for mor in self._incoming.get(seed_name, []):
                if mor.source not in seed_names:
                    consequences[mor.source] += 1

        # Score theorems by how central they are to the seed structure
        candidates = []
        all_related = set(prerequisites.keys()) | set(consequences.keys())
        for name in all_related:
            # Kan score: theorems that connect multiple seeds are likely "universal"
            pre_count = prerequisites.get(name, 0)
            cons_count = consequences.get(name, 0)
            kan_score = (pre_count + cons_count) / len(seed_names)
            if kan_score > 0.3:
                candidates.append((name, kan_score))

        candidates.sort(key=lambda x: -x[1])
        return candidates[:max_results]

    def _apply_oracle_strategies(self, seeds: List[Tuple[str, float]],
                                  domain: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Apply oracle categorical strategies for advanced inference.

        Uses oracle/strategies.py for:
        - StructuralHoleStrategy: find missing connections
        - GeometricStrategy: geometric reasoning
        - Additional categorical inference
        """
        try:
            from oracle.strategies import (
                StructuralHoleStrategy,
                GeometricStrategy,
                YonedaPatternStrategy,
                CompositionStrategy
            )

            results = []
            seed_names = [name for name, _ in seeds]

            # StructuralHole: find theorems that bridge disconnected components
            try:
                hole_strategy = StructuralHoleStrategy(self.category)
                holes = hole_strategy.find_structural_holes(seed_names)
                for hole_name, hole_score in holes[:3]:
                    results.append((hole_name, hole_score))
            except Exception:
                pass

            # Geometric: use geometric/topological structure
            if domain in ["geometry", "topology", None]:
                try:
                    geo_strategy = GeometricStrategy(self.category)
                    geo_results = geo_strategy.infer(seed_names)
                    for geo_name, geo_score in geo_results[:2]:
                        results.append((geo_name, geo_score))
                except Exception:
                    pass

            # Remove duplicates, keep highest score
            seen = {}
            for name, score in results:
                if name not in seen or score > seen[name]:
                    seen[name] = score

            final = [(name, score) for name, score in seen.items()]
            final.sort(key=lambda x: -x[1])
            return final[:5]

        except ImportError:
            # Oracle strategies not available
            return []

    # ------------------------------------------------------------------
    # Theorem info
    # ------------------------------------------------------------------

    def get_theorem_statement(self, name: str) -> str:
        """Get the statement/code for a theorem."""
        if name in self._theorem_code:
            return self._theorem_code[name]
        obj = self.category.get(name)
        if obj:
            return obj.metadata.get("statement", obj.metadata.get("code", name))
        return name

    def get_theorem_domain(self, name: str) -> str:
        """Get the domain of a theorem."""
        obj = self.category.get(name)
        if obj:
            return obj.metadata.get("domain", "unknown")
        return "unknown"


# ---------------------------------------------------------------------------
# Query result
# ---------------------------------------------------------------------------

class KGQueryResult:
    """Result from querying the theorem KG."""

    def __init__(self):
        self.seed_theorems: List[Tuple[str, float]] = []
        self.cluster_theorems: List[Tuple[str, float]] = []
        self.theorem_chains: List[List[str]] = []
        self.yoneda_analogues: List[Tuple[str, float]] = []
        self.kan_predictions: List[Tuple[str, float]] = []
        self.oracle_results: List[Tuple[str, float]] = []
        self.ranked_theorems: List[Tuple[str, float]] = []

    def format_for_llm(self, kg: "TheoremKG") -> str:
        """Format KG results as text context for the LLM."""
        parts = []

        if self.ranked_theorems:
            parts.append("## Relevant Theorems (from Knowledge Graph)")
            for name, score in self.ranked_theorems[:8]:
                stmt = kg.get_theorem_statement(name)
                domain = kg.get_theorem_domain(name)
                parts.append(f"- **{name}** [{domain}]: {stmt}")

        if self.theorem_chains:
            parts.append("\n## Theorem Chains (proof paths)")
            for chain in self.theorem_chains[:5]:
                chain_strs = []
                for name in chain:
                    stmt = kg.get_theorem_statement(name)
                    chain_strs.append(f"{name}: {stmt}")
                parts.append("  " + " -> ".join(chain))
                for cs in chain_strs:
                    parts.append(f"    {cs}")

        if self.yoneda_analogues:
            parts.append("\n## Structurally Similar Theorems (Yoneda)")
            for name, sim in self.yoneda_analogues[:3]:
                stmt = kg.get_theorem_statement(name)
                parts.append(f"- {name} (similarity={sim:.2f}): {stmt}")

        return "\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# COG / OPTIMUS / Cosmos integration
# ---------------------------------------------------------------------------

class EnhancedTheoremKG(TheoremKG):
    """
    TheoremKG wired to COG, OPTIMUS, and InfinityCosmos.

    Adds:
    - COG verification of retrieved theorem chains
    - OPTIMUS discovery of intermediate theorems
    - InfinityCosmos fibration-based retrieval
    """

    def __init__(self, db_path: str = ":memory:"):
        super().__init__(db_path=db_path)
        self._cog = None
        self._optimus = None
        self._cosmos = None

    @property
    def cog(self):
        if self._cog is None:
            from cog.session import CogSession
            from cog.engine import CogEngine
            session = CogSession(session_id="theorem_kg", category=self.category)
            self._cog = CogEngine(session)
        return self._cog

    @property
    def optimus(self):
        if self._optimus is None:
            from core.optimus import OptimusEngine
            self._optimus = OptimusEngine(self.category, max_depth=3)
        return self._optimus

    @property
    def cosmos(self):
        if self._cosmos is None:
            from core.cosmos import InfinityCosmos
            self._cosmos = InfinityCosmos(self.category)
        return self._cosmos

    def verify_chain(self, chain: List[str]) -> Dict[str, Any]:
        """
        Verify a theorem chain through COG tiered verification.

        Each link in the chain (A depends_on B) is checked.
        Returns verification status for each link.
        """
        from cog.schema import CogClaim

        results = []
        for i in range(len(chain) - 1):
            claim = CogClaim(
                source=chain[i],
                target=chain[i + 1],
                relation="depends_on",
                confidence=0.9,
            )
            try:
                check = self.cog.check_claim(claim, depth=2)
                results.append({
                    "from": chain[i],
                    "to": chain[i + 1],
                    "status": check.status.value if hasattr(check.status, 'value') else str(check.status),
                    "confidence": check.confidence,
                    "tier": check.tier,
                })
            except Exception as e:
                results.append({
                    "from": chain[i],
                    "to": chain[i + 1],
                    "status": "error",
                    "error": str(e),
                })
        return {"chain": chain, "links": results}

    def discover_intermediates(self, source: str, target: str) -> List[str]:
        """
        Use OPTIMUS to discover intermediate theorems between source and target.

        OPTIMUS looks for factorizations: source -> ? -> target where the
        intermediate theorem improves the overall proof path.
        """
        try:
            return self.optimus.discover_intermediates(source, target)
        except Exception:
            return []

    def find_fibration_theorems(self, theorem_name: str) -> List[Dict[str, Any]]:
        """
        Use InfinityCosmos to find theorems in the same fiber.

        Theorems connected by a cartesian fibration share deep structural
        properties -- they're the same kind of theorem in different contexts.
        """
        try:
            fibs = self.cosmos.cartesian_fibrations()
            related = []
            for fib in fibs:
                if theorem_name in fib.total_objects:
                    for other in fib.total_objects:
                        if other != theorem_name:
                            related.append({
                                "theorem": other,
                                "fibration": fib.name,
                                "base": fib.base_object,
                            })
            return related
        except Exception:
            return []

    def enhanced_query(self, problem_text: str, domain: Optional[str] = None,
                       top_k: int = 10) -> "KGQueryResult":
        """
        Enhanced query that adds OPTIMUS gap discovery and COG verification.

        Runs the standard query, then:
        1. Uses OPTIMUS to find structural gaps (missing theorem links)
        2. Verifies top theorem chains through COG
        """
        result = self.query(problem_text, domain, top_k)

        # Enhance chains with OPTIMUS intermediates
        enhanced_chains = []
        for chain in result.theorem_chains[:3]:
            if len(chain) >= 2:
                intermediates = self.discover_intermediates(chain[0], chain[-1])
                if intermediates:
                    enhanced_chains.append({
                        "original_chain": chain,
                        "optimus_intermediates": intermediates,
                    })
        result._optimus_chains = enhanced_chains

        # Verify top chains through COG
        verified_chains = []
        for chain in result.theorem_chains[:3]:
            verification = self.verify_chain(chain)
            verified_chains.append(verification)
        result._cog_verified_chains = verified_chains

        return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_GLOBAL_KG: Optional[TheoremKG] = None


def get_global_kg(enhanced: bool = False) -> TheoremKG:
    """Get or create the global TheoremKG singleton."""
    global _GLOBAL_KG
    if _GLOBAL_KG is None:
        if enhanced:
            _GLOBAL_KG = EnhancedTheoremKG()
        else:
            _GLOBAL_KG = TheoremKG()
    return _GLOBAL_KG
