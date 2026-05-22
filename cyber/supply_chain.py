# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Supply Chain Attack Category - Category-Theoretic Dependency Analysis

Models software supply chain as a category:
- Objects: packages, libraries, CI/CD pipelines, registries, developers
- Morphisms: dependency relationships (DEPENDS_ON, IMPORTS, BUILDS_WITH, etc.)

Key capabilities:
- Transitive dependency closure (category composition)
- Critical dependency identification (hub analysis)
- Typosquatting risk detection (string distance)
- Dependency confusion detection (namespace conflicts)
- Trust propagation analysis (functorial mapping)
- Circular dependency detection (cycle finding)

MITRE ATT&CK Coverage:
- T1195: Supply Chain Compromise
- T1195.001: Compromise Software Dependencies
- T1195.002: Compromise Software Supply Chain
- T1195.003: Compromise Hardware Supply Chain
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
from collections import defaultdict, deque
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class SupplyChainObjectType(Enum):
    """Types of objects in the supply chain category."""
    PACKAGE = "package"
    LIBRARY = "library"
    CI_PIPELINE = "ci_pipeline"
    CD_PIPELINE = "cd_pipeline"
    REGISTRY = "registry"
    REPOSITORY = "repository"
    BUILD_SYSTEM = "build_system"
    SIGNING_KEY = "signing_key"
    DEVELOPER = "developer"


class SupplyChainMorphismType(Enum):
    """Types of morphisms (relationships) in the supply chain."""
    DEPENDS_ON = "depends_on"
    IMPORTS = "imports"
    BUILDS_WITH = "builds_with"
    PUBLISHES_TO = "publishes_to"
    SIGNS_WITH = "signs_with"
    MAINTAINED_BY = "maintained_by"
    PULLS_FROM = "pulls_from"
    TRANSITIVELY_DEPENDS_ON = "transitively_depends_on"


@dataclass
class SupplyChainNode:
    """A node in the supply chain graph."""
    name: str
    node_type: SupplyChainObjectType
    version: str = ""
    namespace: str = ""  # e.g., "npm", "pypi", "maven"
    maintainers: List[str] = field(default_factory=list)
    trust_score: float = 1.0  # 0.0 (untrusted) to 1.0 (fully trusted)
    metadata: Dict = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.namespace))

    def __eq__(self, other):
        return isinstance(other, SupplyChainNode) and self.name == other.name and self.namespace == other.namespace


@dataclass
class SupplyChainEdge:
    """An edge (morphism) in the supply chain."""
    source: str  # node name
    target: str  # node name
    edge_type: SupplyChainMorphismType
    version_constraint: str = ""  # e.g., ">=1.0,<2.0"
    is_dev_dependency: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class SupplyChainVulnerability:
    """A detected supply chain vulnerability."""
    vuln_type: str
    severity: str  # "critical", "high", "medium", "low"
    affected_nodes: List[str]
    description: str
    evidence: Dict
    remediation: str


class SupplyChainCategory:
    """
    Category-theoretic model of a software supply chain.

    Objects = supply chain entities (packages, registries, etc.)
    Morphisms = dependency relationships
    Composition = transitive dependency chains

    The categorical structure enforces:
    - Transitivity: A depends_on B depends_on C => A transitively_depends_on C
    - Trust propagation: trust is functorial (preserves composition)
    """

    def __init__(self):
        self.nodes: Dict[str, SupplyChainNode] = {}
        self.edges: List[SupplyChainEdge] = []
        self._adjacency: Dict[str, List[str]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self._transitive_closure: Optional[Dict[str, Set[str]]] = None

    def add_node(self, node: SupplyChainNode):
        """Add a supply chain node."""
        self.nodes[node.name] = node
        self._transitive_closure = None  # Invalidate cache

    def add_edge(self, edge: SupplyChainEdge):
        """Add a dependency edge."""
        self.edges.append(edge)
        self._adjacency[edge.source].append(edge.target)
        self._reverse_adjacency[edge.target].append(edge.source)
        self._transitive_closure = None

    def compute_transitive_closure(self) -> Dict[str, Set[str]]:
        """
        Compute transitive closure of dependency graph.

        This is the categorical composition: if A->B and B->C, then A->C.

        Returns:
            Dict mapping each node to the set of all its transitive dependencies.
        """
        if self._transitive_closure is not None:
            return self._transitive_closure

        closure: Dict[str, Set[str]] = {}

        for node_name in self.nodes:
            # BFS from this node
            visited = set()
            queue = deque(self._adjacency.get(node_name, []))

            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                for neighbor in self._adjacency.get(current, []):
                    if neighbor not in visited:
                        queue.append(neighbor)

            closure[node_name] = visited

        self._transitive_closure = closure
        return closure

    def find_critical_dependencies(self, top_k: int = 10) -> List[Tuple[str, int]]:
        """
        Find critical dependencies (high-impact nodes).

        A dependency is critical if many packages transitively depend on it.
        This is the "reverse reachability" count.

        Returns:
            List of (node_name, dependent_count) sorted by count descending.
        """
        closure = self.compute_transitive_closure()

        # Count how many nodes depend on each node
        dependency_count: Dict[str, int] = defaultdict(int)
        for node_name, deps in closure.items():
            for dep in deps:
                dependency_count[dep] += 1

        ranked = sorted(dependency_count.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def detect_typosquatting_risk(self, threshold: float = 0.85) -> List[SupplyChainVulnerability]:
        """
        Detect potential typosquatting attacks.

        Typosquatting: attacker publishes package with name similar to popular package.
        Detection: find pairs of packages with high string similarity.

        Args:
            threshold: Minimum similarity to flag (0.0 to 1.0)

        Returns:
            List of typosquatting risk vulnerabilities
        """
        vulns = []
        node_names = list(self.nodes.keys())

        for i in range(len(node_names)):
            for j in range(i + 1, len(node_names)):
                name_a = node_names[i]
                name_b = node_names[j]

                # Skip if same namespace
                node_a = self.nodes[name_a]
                node_b = self.nodes[name_b]
                if node_a.namespace != node_b.namespace:
                    continue

                sim = self._string_similarity(name_a, name_b)
                if sim >= threshold and sim < 1.0:
                    # Flag as potential typosquatting
                    # Higher risk if one has much lower trust
                    trust_diff = abs(node_a.trust_score - node_b.trust_score)
                    severity = "high" if trust_diff > 0.5 else "medium"

                    vulns.append(SupplyChainVulnerability(
                        vuln_type="typosquatting_risk",
                        severity=severity,
                        affected_nodes=[name_a, name_b],
                        description=f"Packages '{name_a}' and '{name_b}' have similar names "
                                    f"(similarity: {sim:.2f}) - potential typosquatting",
                        evidence={"similarity": sim, "trust_diff": trust_diff},
                        remediation="Verify package authenticity and check publisher identity"
                    ))

        return vulns

    def detect_dependency_confusion(self) -> List[SupplyChainVulnerability]:
        """
        Detect dependency confusion risks.

        Dependency confusion: private package name collides with public registry.
        Detection: find packages with same name in different namespaces.
        """
        vulns = []

        # Group by name (across namespaces)
        name_to_nodes: Dict[str, List[SupplyChainNode]] = defaultdict(list)
        for node in self.nodes.values():
            if node.node_type in (SupplyChainObjectType.PACKAGE, SupplyChainObjectType.LIBRARY):
                base_name = node.name.split("/")[-1] if "/" in node.name else node.name
                name_to_nodes[base_name].append(node)

        for name, nodes in name_to_nodes.items():
            namespaces = set(n.namespace for n in nodes)
            if len(namespaces) > 1:
                vulns.append(SupplyChainVulnerability(
                    vuln_type="dependency_confusion",
                    severity="high",
                    affected_nodes=[n.name for n in nodes],
                    description=f"Package '{name}' exists in multiple namespaces: {namespaces} "
                                "- risk of dependency confusion attack",
                    evidence={"namespaces": list(namespaces),
                              "node_count": len(nodes)},
                    remediation="Pin dependencies to specific registries and use namespace scoping"
                ))

        return vulns

    def analyze_trust_propagation(self) -> Dict[str, float]:
        """
        Analyze trust propagation through the supply chain.

        Trust is functorial: if A trusts B with score t1, and B trusts C with score t2,
        then A's transitive trust in C is t1 * t2 (trust decays through composition).

        Returns:
            Dict mapping each node to its effective trust score.
        """
        effective_trust: Dict[str, float] = {}

        for node_name, node in self.nodes.items():
            effective_trust[node_name] = node.trust_score

        # Propagate trust through dependency edges
        # Use BFS from each node, multiplying trust scores
        closure = self.compute_transitive_closure()

        for node_name in self.nodes:
            min_trust = self.nodes[node_name].trust_score

            for dep in closure.get(node_name, set()):
                if dep in self.nodes:
                    dep_trust = self.nodes[dep].trust_score
                    # Trust is limited by weakest link
                    min_trust = min(min_trust, dep_trust)

            effective_trust[node_name] = min_trust

        return effective_trust

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies in the supply chain.

        Uses DFS-based cycle detection.

        Returns:
            List of cycles (each cycle is a list of node names)
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.discard(node)

        for node_name in self.nodes:
            if node_name not in visited:
                dfs(node_name, [])

        return cycles

    def get_dependency_depth(self, node_name: str) -> int:
        """Get maximum dependency chain depth from a node."""
        visited = set()

        def dfs_depth(name: str) -> int:
            if name in visited:
                return 0
            visited.add(name)
            deps = self._adjacency.get(name, [])
            if not deps:
                return 0
            return 1 + max(dfs_depth(d) for d in deps)

        return dfs_depth(node_name)

    def scan_all(self) -> List[SupplyChainVulnerability]:
        """Run all supply chain vulnerability scans."""
        vulns = []
        vulns.extend(self.detect_typosquatting_risk())
        vulns.extend(self.detect_dependency_confusion())

        # Check for deeply nested dependencies
        for node_name in self.nodes:
            depth = self.get_dependency_depth(node_name)
            if depth > 10:
                vulns.append(SupplyChainVulnerability(
                    vuln_type="deep_dependency_chain",
                    severity="medium",
                    affected_nodes=[node_name],
                    description=f"Package '{node_name}' has dependency chain depth {depth}",
                    evidence={"depth": depth},
                    remediation="Review transitive dependencies and consider flattening"
                ))

        # Check for circular dependencies
        cycles = self.detect_circular_dependencies()
        for cycle in cycles:
            vulns.append(SupplyChainVulnerability(
                vuln_type="circular_dependency",
                severity="high",
                affected_nodes=cycle,
                description=f"Circular dependency detected: {' -> '.join(cycle)}",
                evidence={"cycle": cycle},
                remediation="Break circular dependency by refactoring shared code"
            ))

        return vulns

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Compute normalized Levenshtein similarity between two strings."""
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        # Levenshtein distance
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )

        distance = dp[m][n]
        max_len = max(m, n)
        return 1.0 - (distance / max_len)


class SupplyChainStrategy:
    """
    Oracle strategy for supply chain attack prediction.

    Analyzes dependency graphs to predict supply chain compromise risks.
    """

    def __init__(self, store=None):
        self.store = store
        self.name = "supply_chain_analysis"

    def predict(self, source_obj) -> list:
        """
        Analyze supply chain for attack risks.

        Args:
            source_obj: Should contain supply chain data in metadata

        Returns:
            List of Prediction objects for supply chain risks
        """
        from oracle.prediction import Prediction

        if not hasattr(source_obj, "metadata"):
            return []

        metadata = source_obj.metadata
        nodes_data = metadata.get("supply_chain_nodes", [])
        edges_data = metadata.get("supply_chain_edges", [])

        if not nodes_data:
            return []

        # Build supply chain category
        sc = SupplyChainCategory()

        for nd in nodes_data:
            node = SupplyChainNode(
                name=nd.get("name", ""),
                node_type=SupplyChainObjectType(nd.get("type", "package")),
                namespace=nd.get("namespace", ""),
                trust_score=nd.get("trust_score", 1.0)
            )
            sc.add_node(node)

        for ed in edges_data:
            edge = SupplyChainEdge(
                source=ed.get("source", ""),
                target=ed.get("target", ""),
                edge_type=SupplyChainMorphismType(ed.get("type", "depends_on"))
            )
            sc.add_edge(edge)

        # Run analysis
        vulns = sc.scan_all()
        critical_deps = sc.find_critical_dependencies(top_k=5)
        trust_scores = sc.analyze_trust_propagation()

        predictions = []
        for vuln in vulns:
            severity_to_confidence = {
                "critical": 0.95, "high": 0.80, "medium": 0.60, "low": 0.40
            }
            predictions.append(Prediction(
                source=vuln.affected_nodes[0] if vuln.affected_nodes else "unknown",
                target="supply_chain",
                predicted_relation=f"supply_chain_{vuln.vuln_type}",
                prediction_type="COMPOSITION",
                strategy_name=self.name,
                confidence=severity_to_confidence.get(vuln.severity, 0.5),
                reasoning=vuln.description,
                evidence={
                    "vuln_type": vuln.vuln_type,
                    "severity": vuln.severity,
                    "affected": vuln.affected_nodes,
                    "evidence": vuln.evidence,
                    "remediation": vuln.remediation,
                    "critical_dependencies": critical_deps[:3],
                    "low_trust_nodes": [
                        (name, score) for name, score in trust_scores.items()
                        if score < 0.5
                    ]
                }
            ))

        return predictions
