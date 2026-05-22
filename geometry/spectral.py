# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Spectral Graph Theory for Network Analysis

Analyzes graph structure via eigenvalues and eigenvectors of the Laplacian matrix.

Mathematical Foundation:
- Graph Laplacian: L = D - A (degree matrix minus adjacency)
- Eigendecomposition: L·v = λ·v
- λ₁ (algebraic connectivity) = coupling strength
- λ₂, λ₃, ... = oscillatory modes

Applications:
- Climate networks: coupling between CO2 reservoirs
- Protein networks: community detection
- Any relational network: structural analysis
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np

try:
    from scipy.linalg import eigh
    from scipy.sparse import csr_matrix
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from .spectral_structures import (
    Graph,
    GraphLaplacian,
    SpectralClustering,
    CheegerConstant,
    RandomWalkAnalysis,
    graph_from_adjacency,
    graph_from_edges,
    analyze_connectivity,
)


@dataclass
class SpectralResult:
    """Results of spectral analysis."""
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    node_names: List[str]
    algebraic_connectivity: float
    coupling_strength: str
    equilibration_time: float
    oscillatory_modes: List[Dict]
    analysis: str


class SpectralGraphAnalyzer:
    """
    Spectral graph theory analyzer for categorical networks.

    Computes eigenvalues/eigenvectors of graph Laplacian to reveal:
    - System coupling strength (λ₁)
    - Oscillatory modes (λ₂, λ₃, ...)
    - Most influential nodes (eigenvector centrality)
    - Network structure (communities, hierarchies)
    """

    def __init__(self, category=None):
        """
        Initialize analyzer.

        Args:
            category: Category object with objects and morphisms
        """
        self.category = category
        self.laplacian = None
        self.eigenvalues = None
        self.eigenvectors = None
        self.node_names = None

    def build_laplacian(self) -> np.ndarray:
        """
        Build graph Laplacian from category morphisms.

        Laplacian L = D - A where:
        - D = degree matrix (diagonal: sum of edge weights)
        - A = adjacency matrix (edge weights)

        Returns:
            Laplacian matrix (N x N)
        """
        if self.category is None:
            raise ValueError("No category provided")

        # Get node names
        self.node_names = list(self.category.objects.keys())
        n = len(self.node_names)

        if n == 0:
            raise ValueError("Category has no objects")

        node_to_idx = {name: i for i, name in enumerate(self.node_names)}

        # Build adjacency matrix
        A = np.zeros((n, n))

        for mor in self.category.morphisms.values():
            # Skip identity morphisms
            if mor.data.get("is_identity"):
                continue

            source_name = mor.source.name
            target_name = mor.target.name

            if source_name not in node_to_idx or target_name not in node_to_idx:
                continue

            i = node_to_idx[source_name]
            j = node_to_idx[target_name]

            # Get weight (default 1.0)
            weight = mor.data.get("weight", 1.0)

            # Make symmetric (undirected graph)
            A[i, j] = weight
            A[j, i] = weight

        # Degree matrix
        degrees = A.sum(axis=1)
        D = np.diag(degrees)

        # Laplacian
        self.laplacian = D - A

        return self.laplacian

    def compute_spectrum(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute eigenvalues and eigenvectors of Laplacian.

        Returns:
            Tuple of (eigenvalues, eigenvectors)
            - eigenvalues: sorted ascending (λ₀ = 0, λ₁, λ₂, ...)
            - eigenvectors: columns are eigenvectors
        """
        if self.laplacian is None:
            self.build_laplacian()

        if not SCIPY_AVAILABLE:
            # Fallback to numpy (slower but works)
            eigenvalues, eigenvectors = np.linalg.eigh(self.laplacian)
        else:
            eigenvalues, eigenvectors = eigh(self.laplacian)

        # Sort by eigenvalue (should already be sorted, but ensure it)
        idx = eigenvalues.argsort()
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        self.eigenvalues = eigenvalues
        self.eigenvectors = eigenvectors

        return eigenvalues, eigenvectors

    def analyze_coupling(self) -> Dict:
        """
        Analyze system coupling strength via algebraic connectivity (λ₁).

        Algebraic connectivity (Fiedler value):
        - λ₁ = 0: Disconnected graph
        - λ₁ small: Weakly coupled (slow response)
        - λ₁ large: Strongly coupled (fast response)

        Returns:
            Dictionary with coupling analysis
        """
        if self.eigenvalues is None:
            self.compute_spectrum()

        lambda_1 = self.eigenvalues[1]  # Second smallest (first is ~0)

        # Classify coupling strength
        if lambda_1 < 0.1:
            coupling_str = "very weak"
        elif lambda_1 < 0.3:
            coupling_str = "weak"
        elif lambda_1 < 0.7:
            coupling_str = "moderate"
        else:
            coupling_str = "strong"

        # Equilibration time (inverse of λ₁)
        if lambda_1 > 1e-6:
            eq_time = 1.0 / lambda_1
        else:
            eq_time = float('inf')

        analysis = {
            "algebraic_connectivity": lambda_1,
            "coupling_strength": coupling_str,
            "equilibration_time": eq_time,
            "interpretation": self._interpret_lambda1(lambda_1)
        }

        return analysis

    def _interpret_lambda1(self, lambda_1: float) -> str:
        """Generate interpretation of algebraic connectivity."""
        if lambda_1 < 0.01:
            return (
                "Very weak coupling. System takes extremely long to equilibrate. "
                "Components are nearly independent. High risk of fragmentation."
            )
        elif lambda_1 < 0.3:
            return (
                "Weak coupling. System responds slowly to perturbations. "
                "Limited information flow between components."
            )
        elif lambda_1 < 0.7:
            return (
                "Moderate coupling. System has reasonable response time. "
                "Components influence each other but maintain some independence."
            )
        else:
            return (
                "Strong coupling. System responds quickly to changes. "
                "Components are tightly interconnected. High synchronization."
            )

    def find_oscillatory_modes(self, num_modes: int = 3) -> List[Dict]:
        """
        Find dominant oscillatory modes (λ₂, λ₃, ...).

        Each eigenvalue λᵢ corresponds to an oscillatory mode with:
        - Frequency: ω = √λᵢ / (2π)
        - Period: T = 1/ω
        - Spatial pattern: eigenvector vᵢ

        Args:
            num_modes: Number of modes to return

        Returns:
            List of mode dictionaries
        """
        if self.eigenvalues is None:
            self.compute_spectrum()

        modes = []

        # Start from λ₁ (skip λ₀ which is always 0)
        for i in range(1, min(num_modes + 1, len(self.eigenvalues))):
            lambda_i = self.eigenvalues[i]
            v_i = self.eigenvectors[:, i]

            # Frequency and period
            if lambda_i > 0:
                omega = np.sqrt(lambda_i) / (2 * np.pi)
                period = 1.0 / omega if omega > 0 else float('inf')
            else:
                omega = 0.0
                period = float('inf')

            # Find nodes with highest participation in this mode
            node_weights = [(self.node_names[j], abs(v_i[j]))
                           for j in range(len(v_i))]
            node_weights.sort(key=lambda x: x[1], reverse=True)

            modes.append({
                "mode_number": i,
                "eigenvalue": lambda_i,
                "frequency": omega,
                "period": period,
                "dominant_nodes": node_weights[:5],  # Top 5 nodes
                "eigenvector": v_i
            })

        return modes

    def compute_node_centrality(self) -> Dict[str, float]:
        """
        Compute eigenvector centrality for each node.

        Uses the dominant eigenvector (largest eigenvalue).

        Returns:
            Dictionary mapping node name to centrality score
        """
        if self.eigenvectors is None:
            self.compute_spectrum()

        # Use eigenvector of largest eigenvalue
        dominant_eigenvector = self.eigenvectors[:, -1]

        # Normalize to [0, 1]
        centrality = np.abs(dominant_eigenvector)
        centrality = centrality / centrality.max() if centrality.max() > 0 else centrality

        return {
            name: centrality[i]
            for i, name in enumerate(self.node_names)
        }

    def full_analysis(self, num_modes: int = 3) -> SpectralResult:
        """
        Run complete spectral analysis.

        Args:
            num_modes: Number of oscillatory modes to analyze

        Returns:
            SpectralResult with all analysis
        """
        # Compute spectrum
        eigenvalues, eigenvectors = self.compute_spectrum()

        # Analyze coupling
        coupling = self.analyze_coupling()

        # Find oscillatory modes
        modes = self.find_oscillatory_modes(num_modes)

        # Generate analysis text
        analysis_text = self._generate_analysis(coupling, modes)

        return SpectralResult(
            eigenvalues=eigenvalues,
            eigenvectors=eigenvectors,
            node_names=self.node_names,
            algebraic_connectivity=coupling["algebraic_connectivity"],
            coupling_strength=coupling["coupling_strength"],
            equilibration_time=coupling["equilibration_time"],
            oscillatory_modes=modes,
            analysis=analysis_text
        )

    def _generate_analysis(self, coupling: Dict, modes: List[Dict]) -> str:
        """Generate human-readable analysis."""
        lines = []

        lines.append("# Spectral Graph Analysis")
        lines.append("")
        lines.append("## System Coupling")
        lines.append(f"- Algebraic connectivity (lambda_1): {coupling['algebraic_connectivity']:.4f}")
        lines.append(f"- Coupling strength: {coupling['coupling_strength']}")
        lines.append(f"- Equilibration time: {coupling['equilibration_time']:.1f} time units")
        lines.append(f"- {coupling['interpretation']}")
        lines.append("")

        lines.append("## Oscillatory Modes")
        for mode in modes:
            lines.append(f"### Mode {mode['mode_number']} (lambda = {mode['eigenvalue']:.4f})")
            lines.append(f"- Period: {mode['period']:.2f} time units")
            lines.append(f"- Dominant nodes:")
            for node, weight in mode['dominant_nodes'][:3]:
                lines.append(f"  - {node}: {weight:.3f}")
            lines.append("")

        return "\n".join(lines)


# Convenience function
def analyze_spectrum(category, num_modes: int = 3) -> SpectralResult:
    """
    Convenience function for full spectral analysis.

    Args:
        category: Category object with network structure
        num_modes: Number of oscillatory modes to analyze

    Returns:
        SpectralResult with complete analysis
    """
    analyzer = SpectralGraphAnalyzer(category)
    return analyzer.full_analysis(num_modes=num_modes)


SpectralAnalyzer = SpectralGraphAnalyzer


# Example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from categorical.category import Category, Object, Morphism

    print("=" * 70)
    print("Spectral Graph Theory - Example")
    print("=" * 70)
    print()

    # Create simple network
    cat = Category("TestNetwork")

    # Add nodes
    A = cat.add_object(Object("A"))
    B = cat.add_object(Object("B"))
    C = cat.add_object(Object("C"))
    D = cat.add_object(Object("D"))

    # Add edges with weights
    cat.add_morphism(Morphism("AB", A, B, data={"weight": 1.0}))
    cat.add_morphism(Morphism("BC", B, C, data={"weight": 1.0}))
    cat.add_morphism(Morphism("CD", C, D, data={"weight": 0.5}))
    cat.add_morphism(Morphism("DA", D, A, data={"weight": 0.5}))
    cat.add_morphism(Morphism("AC", A, C, data={"weight": 0.3}))  # Shortcut

    # Analyze
    result = analyze_spectrum(cat, num_modes=3)

    # Print results
    print(result.analysis)

    print("\nEigenvalues:")
    for i, lam in enumerate(result.eigenvalues):
        print(f"  lambda_{i}: {lam:.4f}")

    print("\nNode Centrality:")
    analyzer = SpectralGraphAnalyzer(cat)
    analyzer.compute_spectrum()
    centrality = analyzer.compute_node_centrality()
    for node, cent in sorted(centrality.items(), key=lambda x: x[1], reverse=True):
        print(f"  {node}: {cent:.3f}")
