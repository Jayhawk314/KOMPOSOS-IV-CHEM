# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Spectral Anomaly Detection - Phase 3C

Detect cyber attacks using spectral graph properties:
- Spectrum perturbation detection
- Dense subgraph identification (botnets, DDoS sources)
- Anomalous traffic pattern recognition
- Attack localization via eigenvector analysis

Mathematical Foundation:
- Normal traffic → stable Laplacian spectrum
- Attack traffic → spectrum perturbation
- Botnet/DDoS → dense anomalous subgraph
- Spectral distance: ||λ_current - λ_baseline||

Detection Methods:
1. Spectrum Comparison: Compare eigenvalues to baseline
2. Eigenvector Perturbation: Locate anomalous nodes
3. Dense Subgraph Detection: Find attack clusters
4. Temporal Spectral Analysis: Track spectrum evolution

Applications:
- DDoS attack detection
- Botnet identification
- APT lateral movement detection
- Network topology manipulation detection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
import math
from collections import defaultdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geometry.spectral import (
    Graph,
    GraphLaplacian,
    SpectralClustering,
    CheegerConstant,
    graph_from_adjacency
)


# =============================================================================
# SPECTRAL ANOMALY DETECTOR
# =============================================================================

@dataclass
class SpectralAnomalyDetector:
    """
    Detect anomalies using graph spectral properties.

    Key insight:
    - Normal network → stable spectrum
    - Attack → spectrum perturbation

    Monitors:
    - Eigenvalue changes (lambda_1, lambda_2, ..., lambda_k)
    - Eigenvector perturbations
    - Algebraic connectivity changes
    - Spectral gap changes
    """
    baseline_graph: Graph
    baseline_laplacian: Optional[GraphLaplacian] = None
    sensitivity: float = 0.1  # Detection threshold

    def __post_init__(self):
        """Compute baseline spectrum."""
        if self.baseline_laplacian is None:
            self.baseline_laplacian = GraphLaplacian(self.baseline_graph)
            self.baseline_laplacian.compute_spectrum(k=10)

    def detect_anomaly(self, current_graph: Graph) -> Dict:
        """
        Compare current graph spectrum to baseline.

        Returns:
            Dict with anomaly detection results
        """
        # Compute current spectrum
        current_laplacian = GraphLaplacian(current_graph)
        current_laplacian.compute_spectrum(k=10)

        # Compute spectral distance
        spectral_distance = self._compute_spectral_distance(
            self.baseline_laplacian.eigenvalues,
            current_laplacian.eigenvalues
        )

        # Check connectivity changes
        baseline_lambda2 = self.baseline_laplacian.algebraic_connectivity()
        current_lambda2 = current_laplacian.algebraic_connectivity()
        connectivity_change = abs(current_lambda2 - baseline_lambda2)

        # Determine if anomalous
        is_anomalous = (
            spectral_distance > self.sensitivity or
            connectivity_change > self.sensitivity * baseline_lambda2
        )

        # Identify changed eigenvalues
        changed_eigenvalues = self._find_changed_eigenvalues(
            self.baseline_laplacian.eigenvalues,
            current_laplacian.eigenvalues
        )

        return {
            'is_anomalous': is_anomalous,
            'spectral_distance': spectral_distance,
            'connectivity_change': connectivity_change,
            'baseline_lambda2': baseline_lambda2,
            'current_lambda2': current_lambda2,
            'changed_eigenvalues': changed_eigenvalues,
            'severity': self._compute_severity(spectral_distance, connectivity_change)
        }

    def _compute_spectral_distance(
        self,
        baseline_eigenvalues: List[float],
        current_eigenvalues: List[float]
    ) -> float:
        """
        Compute distance between spectra.

        Uses Euclidean distance: ||λ_baseline - λ_current||
        """
        # Pad shorter list with zeros
        n = max(len(baseline_eigenvalues), len(current_eigenvalues))
        baseline = baseline_eigenvalues + [0.0] * (n - len(baseline_eigenvalues))
        current = current_eigenvalues + [0.0] * (n - len(current_eigenvalues))

        # Euclidean distance
        distance = math.sqrt(
            sum((b - c) ** 2 for b, c in zip(baseline[:n], current[:n]))
        )

        return distance

    def _find_changed_eigenvalues(
        self,
        baseline: List[float],
        current: List[float]
    ) -> List[Tuple[int, float, float]]:
        """
        Identify which eigenvalues changed significantly.

        Returns:
            List of (index, baseline_value, current_value) for changed eigenvalues
        """
        changed = []
        n = min(len(baseline), len(current))

        for i in range(n):
            if abs(baseline[i] - current[i]) > self.sensitivity:
                changed.append((i, baseline[i], current[i]))

        return changed

    def _compute_severity(
        self,
        spectral_distance: float,
        connectivity_change: float
    ) -> str:
        """
        Compute anomaly severity.

        Returns: "low", "medium", "high", "critical"
        """
        max_change = max(spectral_distance, connectivity_change)

        if max_change > 1.0:
            return "critical"
        elif max_change > 0.5:
            return "high"
        elif max_change > 0.2:
            return "medium"
        else:
            return "low"

    def localize_anomaly(self, anomalous_graph: Graph) -> List[int]:
        """
        Identify nodes causing the anomaly.

        Uses eigenvector perturbation theory.

        Strategy:
        1. Compute eigenvector changes
        2. Find nodes with largest component changes
        3. Return top-k anomalous nodes
        """
        current_laplacian = GraphLaplacian(anomalous_graph)
        current_laplacian.compute_spectrum(k=5)

        # Compare Fiedler vectors (eigenvector for lambda_2)
        baseline_fiedler = self.baseline_laplacian.fiedler_vector()
        current_fiedler = current_laplacian.fiedler_vector()

        if not baseline_fiedler or not current_fiedler:
            return []

        # Compute per-node perturbation
        nodes = sorted(anomalous_graph.nodes)
        perturbations = []

        n = min(len(baseline_fiedler), len(current_fiedler), len(nodes))
        for i in range(n):
            if i < len(baseline_fiedler) and i < len(current_fiedler):
                perturbation = abs(baseline_fiedler[i] - current_fiedler[i])
                perturbations.append((nodes[i], perturbation))

        # Sort by perturbation magnitude
        perturbations.sort(key=lambda x: x[1], reverse=True)

        # Return top 10 anomalous nodes
        return [node for node, _ in perturbations[:10]]


# =============================================================================
# DENSE SUBGRAPH DETECTOR
# =============================================================================

@dataclass
class DenseSubgraphDetector:
    """
    Detect dense subgraphs indicating attacks.

    Attack patterns:
    - Botnet: Densely connected C&C infrastructure
    - DDoS: Coordinated traffic from dense source set
    - Scanning: Dense probe pattern

    Uses spectral methods to find anomalously dense regions.
    """
    graph: Graph
    density_threshold: float = 0.7

    def find_dense_subgraphs(self, min_size: int = 5) -> List[Set[int]]:
        """
        Find all dense subgraphs above threshold.

        Args:
            min_size: Minimum subgraph size to consider

        Returns:
            List of dense subgraphs (as node sets)
        """
        # Use spectral clustering to identify communities
        clustering = SpectralClustering(self.graph)
        k = clustering.find_optimal_k(max_k=10)

        if k <= 1:
            k = 3  # Default to 3 clusters

        clusters_dict = clustering.cluster(k)

        # Group nodes by cluster
        clusters = defaultdict(set)
        for node, cluster_id in clusters_dict.items():
            clusters[cluster_id].add(node)

        # Find dense clusters
        dense_subgraphs = []
        for cluster_nodes in clusters.values():
            if len(cluster_nodes) >= min_size:
                density = self._compute_density(cluster_nodes)
                if density >= self.density_threshold:
                    dense_subgraphs.append(cluster_nodes)

        return dense_subgraphs

    def _compute_density(self, nodes: Set[int]) -> float:
        """
        Compute density of subgraph induced by nodes.

        Density = |E(S)| / (|S| * (|S| - 1) / 2)

        where E(S) = edges within S
        """
        if len(nodes) < 2:
            return 0.0

        # Count internal edges
        internal_edges = 0
        for u in nodes:
            for v in self.graph.get_neighbors(u):
                if v in nodes and u < v:  # Count each edge once
                    internal_edges += 1

        # Maximum possible edges
        n = len(nodes)
        max_edges = n * (n - 1) / 2

        if max_edges == 0:
            return 0.0

        return internal_edges / max_edges

    def classify_subgraph(self, subgraph_nodes: Set[int]) -> Dict:
        """
        Classify dense subgraph as attack vs. legitimate.

        Heuristics:
        - Very high density (>0.9) → likely botnet C&C
        - High degree variance → legitimate community
        - Low degree variance → coordinated attack

        Returns:
            Classification with confidence
        """
        if len(subgraph_nodes) < 2:
            return {'type': 'unknown', 'confidence': 0.0}

        density = self._compute_density(subgraph_nodes)

        # Compute degree statistics within subgraph
        degrees = []
        for node in subgraph_nodes:
            internal_degree = sum(
                1 for neighbor in self.graph.get_neighbors(node)
                if neighbor in subgraph_nodes
            )
            degrees.append(internal_degree)

        if not degrees:
            return {'type': 'unknown', 'confidence': 0.0}

        mean_degree = sum(degrees) / len(degrees)
        variance = sum((d - mean_degree) ** 2 for d in degrees) / len(degrees)

        # Classification logic
        if density > 0.9 and variance < 2.0:
            # Very dense + uniform degrees → likely botnet
            return {
                'type': 'botnet',
                'confidence': 0.85,
                'density': density,
                'degree_variance': variance
            }
        elif density > 0.8 and mean_degree > 10:
            # Dense + high connectivity → possible DDoS source
            return {
                'type': 'ddos_source',
                'confidence': 0.75,
                'density': density,
                'degree_variance': variance
            }
        elif variance > 5.0:
            # High variance → likely legitimate community
            return {
                'type': 'legitimate_community',
                'confidence': 0.7,
                'density': density,
                'degree_variance': variance
            }
        else:
            return {
                'type': 'suspicious',
                'confidence': 0.5,
                'density': density,
                'degree_variance': variance
            }


# =============================================================================
# TEMPORAL SPECTRAL ANALYSIS
# =============================================================================

@dataclass
class TemporalSpectralAnalyzer:
    """
    Track spectral properties over time to detect attacks.

    Maintains sliding window of graph snapshots and spectra.
    Detects:
    - Sudden spectrum changes (acute attacks)
    - Gradual drift (slow reconnaissance)
    - Periodic patterns (coordinated campaigns)
    """
    window_size: int = 10
    history: List[Tuple[float, Graph, List[float]]] = field(default_factory=list)  # (timestamp, graph, eigenvalues)

    def add_snapshot(self, timestamp: float, graph: Graph):
        """
        Add graph snapshot at given timestamp.

        Maintains sliding window of snapshots.
        """
        # Compute spectrum
        laplacian = GraphLaplacian(graph)
        laplacian.compute_spectrum(k=10)
        eigenvalues = laplacian.eigenvalues.copy()

        # Add to history
        self.history.append((timestamp, graph, eigenvalues))

        # Maintain window size
        if len(self.history) > self.window_size:
            self.history.pop(0)

    def detect_temporal_anomaly(self) -> Dict:
        """
        Detect anomalies in temporal evolution of spectrum.

        Returns:
            Dict with temporal anomaly analysis
        """
        if len(self.history) < 3:
            return {'error': 'Insufficient history', 'anomalies': []}

        # Compute spectral distances between consecutive snapshots
        distances = []
        for i in range(1, len(self.history)):
            prev_eigenvalues = self.history[i-1][2]
            curr_eigenvalues = self.history[i][2]

            distance = self._spectral_distance(prev_eigenvalues, curr_eigenvalues)
            distances.append((self.history[i][0], distance))

        # Compute statistics
        mean_distance = sum(d for _, d in distances) / len(distances)
        std_distance = math.sqrt(
            sum((d - mean_distance) ** 2 for _, d in distances) / len(distances)
        )

        # Find anomalies (distance > mean + 2*std)
        threshold = mean_distance + 2 * std_distance
        anomalies = [
            {'timestamp': t, 'distance': d, 'severity': (d - mean_distance) / (std_distance + 1e-9)}
            for t, d in distances
            if d > threshold
        ]

        return {
            'anomalies': anomalies,
            'mean_distance': mean_distance,
            'std_distance': std_distance,
            'threshold': threshold,
            'num_anomalies': len(anomalies)
        }

    def _spectral_distance(self, eigenvalues1: List[float], eigenvalues2: List[float]) -> float:
        """Compute Euclidean distance between eigenvalue lists."""
        n = max(len(eigenvalues1), len(eigenvalues2))
        ev1 = eigenvalues1 + [0.0] * (n - len(eigenvalues1))
        ev2 = eigenvalues2 + [0.0] * (n - len(eigenvalues2))

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(ev1, ev2)))

    def predict_trend(self) -> Dict:
        """
        Predict future spectral trend.

        Uses linear regression on algebraic connectivity (lambda_2).
        """
        if len(self.history) < 3:
            return {'error': 'Insufficient history'}

        # Extract lambda_2 time series
        lambda2_series = []
        for timestamp, _, eigenvalues in self.history:
            if len(eigenvalues) > 1:
                lambda2_series.append((timestamp, eigenvalues[1]))

        if len(lambda2_series) < 2:
            return {'error': 'Insufficient lambda_2 data'}

        # Simple linear regression
        n = len(lambda2_series)
        sum_t = sum(t for t, _ in lambda2_series)
        sum_lambda = sum(lam for _, lam in lambda2_series)
        sum_t_lambda = sum(t * lam for t, lam in lambda2_series)
        sum_t2 = sum(t * t for t, _ in lambda2_series)

        # Slope: β = (n*Σ(t*λ) - Σt*Σλ) / (n*Σt² - (Σt)²)
        denominator = n * sum_t2 - sum_t * sum_t
        if abs(denominator) < 1e-9:
            return {'error': 'Cannot fit trend'}

        slope = (n * sum_t_lambda - sum_t * sum_lambda) / denominator
        intercept = (sum_lambda - slope * sum_t) / n

        # Predict next value
        last_timestamp = lambda2_series[-1][0]
        predicted_lambda2 = slope * (last_timestamp + 1) + intercept

        return {
            'trend': 'increasing' if slope > 0 else 'decreasing',
            'slope': slope,
            'current_lambda2': lambda2_series[-1][1],
            'predicted_lambda2': predicted_lambda2,
            'confidence': self._compute_trend_confidence(lambda2_series, slope, intercept)
        }

    def _compute_trend_confidence(
        self,
        lambda2_series: List[Tuple[float, float]],
        slope: float,
        intercept: float
    ) -> float:
        """
        Compute confidence in trend prediction (R² score).

        R² = 1 - SS_res / SS_tot
        """
        if not lambda2_series:
            return 0.0

        # Mean
        mean_lambda = sum(lam for _, lam in lambda2_series) / len(lambda2_series)

        # Total sum of squares
        ss_tot = sum((lam - mean_lambda) ** 2 for _, lam in lambda2_series)

        # Residual sum of squares
        ss_res = sum((lam - (slope * t + intercept)) ** 2 for t, lam in lambda2_series)

        if ss_tot == 0:
            return 0.0

        r_squared = 1.0 - (ss_res / ss_tot)
        return max(0.0, min(1.0, r_squared))


# =============================================================================
# INTEGRATED ATTACK DETECTOR
# =============================================================================

@dataclass
class SpectralAttackDetector:
    """
    Unified spectral attack detection system.

    Combines:
    - Anomaly detection (spectrum perturbation)
    - Dense subgraph detection (botnets, DDoS)
    - Temporal analysis (attack evolution)

    Provides comprehensive attack detection and classification.
    """
    baseline_graph: Graph
    anomaly_detector: Optional[SpectralAnomalyDetector] = None
    temporal_analyzer: Optional[TemporalSpectralAnalyzer] = None

    def __post_init__(self):
        """Initialize detectors."""
        if self.anomaly_detector is None:
            self.anomaly_detector = SpectralAnomalyDetector(
                baseline_graph=self.baseline_graph,
                sensitivity=0.15
            )

        if self.temporal_analyzer is None:
            self.temporal_analyzer = TemporalSpectralAnalyzer(window_size=10)

            # Initialize with baseline
            self.temporal_analyzer.add_snapshot(0.0, self.baseline_graph)

    def analyze_network_state(
        self,
        current_graph: Graph,
        timestamp: float
    ) -> Dict:
        """
        Comprehensive analysis of current network state.

        Returns:
            Dict with all detection results
        """
        # 1. Anomaly detection
        anomaly_result = self.anomaly_detector.detect_anomaly(current_graph)

        # 2. Dense subgraph detection
        dense_detector = DenseSubgraphDetector(current_graph, density_threshold=0.75)
        dense_subgraphs = dense_detector.find_dense_subgraphs(min_size=5)

        # Classify each dense subgraph
        subgraph_classifications = []
        for subgraph in dense_subgraphs:
            classification = dense_detector.classify_subgraph(subgraph)
            classification['nodes'] = list(subgraph)
            subgraph_classifications.append(classification)

        # 3. Temporal analysis
        self.temporal_analyzer.add_snapshot(timestamp, current_graph)
        temporal_result = self.temporal_analyzer.detect_temporal_anomaly()
        trend_result = self.temporal_analyzer.predict_trend()

        # 4. Localize anomalies
        anomalous_nodes = []
        if anomaly_result['is_anomalous']:
            anomalous_nodes = self.anomaly_detector.localize_anomaly(current_graph)

        # 5. Overall threat assessment
        threat_level = self._compute_threat_level(
            anomaly_result,
            subgraph_classifications,
            temporal_result
        )

        return {
            'timestamp': timestamp,
            'anomaly_detection': anomaly_result,
            'dense_subgraphs': subgraph_classifications,
            'temporal_analysis': temporal_result,
            'trend_prediction': trend_result,
            'anomalous_nodes': anomalous_nodes,
            'threat_level': threat_level,
            'recommendations': self._generate_recommendations(
                anomaly_result,
                subgraph_classifications,
                anomalous_nodes
            )
        }

    def _compute_threat_level(
        self,
        anomaly_result: Dict,
        subgraph_classifications: List[Dict],
        temporal_result: Dict
    ) -> str:
        """
        Compute overall threat level.

        Returns: "none", "low", "medium", "high", "critical"
        """
        score = 0.0

        # Anomaly contribution
        if anomaly_result.get('is_anomalous'):
            severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            score += severity_map.get(anomaly_result.get('severity', 'low'), 0)

        # Dense subgraph contribution
        for classification in subgraph_classifications:
            if classification.get('type') == 'botnet':
                score += 4
            elif classification.get('type') == 'ddos_source':
                score += 3

        # Temporal contribution
        num_temporal_anomalies = temporal_result.get('num_anomalies', 0)
        score += min(num_temporal_anomalies, 3)

        # Map score to threat level
        if score >= 8:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        elif score >= 1:
            return "low"
        else:
            return "none"

    def _generate_recommendations(
        self,
        anomaly_result: Dict,
        subgraph_classifications: List[Dict],
        anomalous_nodes: List[int]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if anomaly_result.get('is_anomalous'):
            recommendations.append(
                f"Investigate spectral anomaly (distance: {anomaly_result['spectral_distance']:.3f})"
            )

        if anomalous_nodes:
            recommendations.append(
                f"Examine nodes {anomalous_nodes[:5]} for suspicious activity"
            )

        for classification in subgraph_classifications:
            if classification.get('type') == 'botnet':
                nodes = classification.get('nodes', [])
                recommendations.append(
                    f"URGENT: Isolate suspected botnet nodes {nodes[:5]}"
                )
            elif classification.get('type') == 'ddos_source':
                recommendations.append(
                    "Implement rate limiting on suspected DDoS source cluster"
                )

        if not recommendations:
            recommendations.append("No immediate action required")

        return recommendations
