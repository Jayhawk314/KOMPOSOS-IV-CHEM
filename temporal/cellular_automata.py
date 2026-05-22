# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Cellular Automata for Temporal Dynamics

Simulates temporal evolution of protein/climate networks:
- Protein folding pathways (unfolded → folded)
- Drug resistance evolution (cancer mutations)
- Climate regime transitions (stable → unstable)
- Signaling cascades (activation propagation)

Integrates with HoTT for path analysis and Nash for equilibria.
"""

import numpy as np
from typing import Dict, List, Tuple, Callable, Optional, Set
from dataclasses import dataclass
from enum import Enum


class UpdateRule(Enum):
    """Standard CA update rules."""
    CONWAY = "conway"  # Conway's Game of Life
    MAJORITY = "majority"  # Majority vote
    THRESHOLD = "threshold"  # Activation threshold
    CUSTOM = "custom"  # User-defined


class BoundaryCondition(Enum):
    """Boundary handling."""
    PERIODIC = "periodic"  # Wrap around (torus)
    FIXED = "fixed"  # Fixed values at boundary
    OPEN = "open"  # No influence from outside


@dataclass
class CAState:
    """Cellular automaton state at a time step."""
    grid: np.ndarray  # State values
    time: int
    metadata: Dict


class CellularAutomaton:
    """
    Discrete-time, discrete-space dynamical system.

    State transitions via local rules:
    s_i(t+1) = f(s_i(t), neighbors(i, t))

    Applications:
    - Protein folding: residue states (unfolded/folded)
    - Drug resistance: cell states (sensitive/resistant)
    - Climate: regime states (stable/unstable)
    - Signaling: activation states (inactive/active)
    """

    def __init__(
        self,
        shape: Tuple[int, ...],
        states: int = 2,
        rule: UpdateRule = UpdateRule.MAJORITY,
        boundary: BoundaryCondition = BoundaryCondition.PERIODIC,
        custom_rule: Optional[Callable] = None
    ):
        """
        Initialize cellular automaton.

        Args:
            shape: Grid dimensions (1D, 2D, or 3D)
            states: Number of possible states per cell
            rule: Update rule type
            boundary: Boundary condition
            custom_rule: Custom update function if rule=CUSTOM
        """
        self.shape = shape
        self.ndim = len(shape)
        self.states = states
        self.rule = rule
        self.boundary = boundary
        self.custom_rule = custom_rule

        # Initialize grid
        self.grid = np.zeros(shape, dtype=int)
        self.time = 0

        # History
        self.history: List[CAState] = []

    def set_initial_state(self, state: np.ndarray):
        """Set initial grid state."""
        if state.shape != self.shape:
            raise ValueError(f"State shape {state.shape} != grid shape {self.shape}")
        self.grid = state.copy()
        self.time = 0
        self.history = [CAState(self.grid.copy(), self.time, {})]

    def get_neighbors(self, index: Tuple[int, ...]) -> List[int]:
        """
        Get neighbor states for a cell.

        Uses Moore neighborhood (8 neighbors in 2D, 26 in 3D).
        """
        neighbors = []

        # Generate neighbor offsets
        offsets = self._get_neighbor_offsets()

        for offset in offsets:
            neighbor_idx = tuple(index[i] + offset[i] for i in range(self.ndim))

            # Handle boundaries
            if self.boundary == BoundaryCondition.PERIODIC:
                neighbor_idx = tuple(idx % self.shape[i] for i, idx in enumerate(neighbor_idx))
                neighbors.append(self.grid[neighbor_idx])
            elif self.boundary == BoundaryCondition.FIXED:
                if all(0 <= neighbor_idx[i] < self.shape[i] for i in range(self.ndim)):
                    neighbors.append(self.grid[neighbor_idx])
            elif self.boundary == BoundaryCondition.OPEN:
                if all(0 <= neighbor_idx[i] < self.shape[i] for i in range(self.ndim)):
                    neighbors.append(self.grid[neighbor_idx])

        return neighbors

    def _get_neighbor_offsets(self) -> List[Tuple[int, ...]]:
        """Generate neighbor offsets for Moore neighborhood."""
        if self.ndim == 1:
            return [(-1,), (1,)]
        elif self.ndim == 2:
            return [(-1, -1), (-1, 0), (-1, 1),
                    (0, -1),           (0, 1),
                    (1, -1),  (1, 0),  (1, 1)]
        elif self.ndim == 3:
            # 26 neighbors in 3D
            offsets = []
            for i in [-1, 0, 1]:
                for j in [-1, 0, 1]:
                    for k in [-1, 0, 1]:
                        if i == 0 and j == 0 and k == 0:
                            continue
                        offsets.append((i, j, k))
            return offsets
        else:
            raise ValueError(f"Unsupported dimension: {self.ndim}")

    def apply_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """
        Apply update rule to determine next state.

        Args:
            cell_state: Current cell state
            neighbors: States of neighboring cells

        Returns:
            New state for cell
        """
        if self.rule == UpdateRule.CONWAY:
            return self._conway_rule(cell_state, neighbors)
        elif self.rule == UpdateRule.MAJORITY:
            return self._majority_rule(cell_state, neighbors)
        elif self.rule == UpdateRule.THRESHOLD:
            return self._threshold_rule(cell_state, neighbors)
        elif self.rule == UpdateRule.CUSTOM:
            if self.custom_rule is None:
                raise ValueError("Custom rule specified but no function provided")
            return self.custom_rule(cell_state, neighbors)
        else:
            raise ValueError(f"Unknown rule: {self.rule}")

    def _conway_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """Conway's Game of Life rule."""
        alive_neighbors = sum(neighbors)

        if cell_state == 1:  # Currently alive
            if alive_neighbors < 2 or alive_neighbors > 3:
                return 0  # Dies
            return 1  # Survives
        else:  # Currently dead
            if alive_neighbors == 3:
                return 1  # Birth
            return 0  # Stays dead

    def _majority_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """Majority vote rule."""
        if not neighbors:
            return cell_state

        # Count each state
        counts = np.bincount(neighbors, minlength=self.states)
        return np.argmax(counts)

    def _threshold_rule(self, cell_state: int, neighbors: List[int], threshold: float = 0.5) -> int:
        """Threshold activation rule (for signaling cascades)."""
        if not neighbors:
            return cell_state

        active_fraction = sum(1 for n in neighbors if n > 0) / len(neighbors)

        if active_fraction >= threshold:
            return min(cell_state + 1, self.states - 1)  # Activate
        else:
            return max(cell_state - 1, 0)  # Deactivate

    def step(self) -> np.ndarray:
        """
        Advance CA by one time step.

        Returns:
            New grid state
        """
        new_grid = np.zeros_like(self.grid)

        # Apply rule to each cell
        for index in np.ndindex(self.shape):
            cell_state = self.grid[index]
            neighbors = self.get_neighbors(index)
            new_grid[index] = self.apply_rule(cell_state, neighbors)

        self.grid = new_grid
        self.time += 1

        # Record history
        self.history.append(CAState(self.grid.copy(), self.time, {}))

        return self.grid.copy()

    def run(self, steps: int, record_interval: int = 1) -> List[CAState]:
        """
        Run CA for multiple steps.

        Args:
            steps: Number of time steps
            record_interval: Record state every N steps

        Returns:
            List of recorded states
        """
        recorded = []

        for i in range(steps):
            self.step()

            if i % record_interval == 0:
                recorded.append(self.history[-1])

        return recorded

    def detect_fixed_points(self, max_steps: int = 100) -> Optional[np.ndarray]:
        """
        Detect fixed point (stable state).

        Returns state if fixed point reached, None otherwise.
        """
        for _ in range(max_steps):
            prev_grid = self.grid.copy()
            self.step()

            if np.array_equal(self.grid, prev_grid):
                return self.grid.copy()

        return None

    def detect_cycles(self, max_steps: int = 100) -> Optional[List[np.ndarray]]:
        """
        Detect periodic cycles.

        Returns cycle states if found, None otherwise.
        """
        seen_states = {}

        for i in range(max_steps):
            state_hash = self.grid.tobytes()

            if state_hash in seen_states:
                # Found cycle
                cycle_start = seen_states[state_hash]
                cycle_length = i - cycle_start

                cycle_states = [
                    self.history[j].grid
                    for j in range(cycle_start, i)
                ]

                return cycle_states

            seen_states[state_hash] = i
            self.step()

        return None

    def compute_entropy(self) -> float:
        """
        Compute Shannon entropy of current state.

        Measures disorder/randomness.
        """
        flat = self.grid.flatten()
        counts = np.bincount(flat, minlength=self.states)
        probs = counts / len(flat)

        # Shannon entropy
        entropy = -np.sum(probs * np.log2(probs + 1e-10))

        return entropy

    def compute_density(self, state_value: int = 1) -> float:
        """Compute density of a particular state."""
        return np.sum(self.grid == state_value) / self.grid.size


class ProteinFoldingCA(CellularAutomaton):
    """
    CA specialized for protein folding simulation.

    States:
    0 = Unfolded
    1 = Partially folded
    2 = Folded

    Rule: Residues fold when surrounded by folded neighbors (hydrophobic collapse).
    """

    def __init__(self, sequence_length: int, contact_map: Optional[np.ndarray] = None):
        """
        Initialize protein folding CA.

        Args:
            sequence_length: Number of residues
            contact_map: (N,N) matrix of residue contacts
        """
        # 1D CA representing linear sequence
        super().__init__(
            shape=(sequence_length,),
            states=3,  # unfolded, partial, folded
            rule=UpdateRule.CUSTOM,
            boundary=BoundaryCondition.FIXED
        )

        self.contact_map = contact_map

        # Define custom folding rule
        self.custom_rule = self._folding_rule

    def _folding_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """
        Folding rule based on hydrophobic collapse.

        Residues fold when enough neighbors are folded.
        """
        if cell_state == 2:  # Already folded
            return 2

        # Count folded neighbors
        folded_neighbors = sum(1 for n in neighbors if n == 2)

        if cell_state == 0:  # Unfolded
            if folded_neighbors >= 1:
                return 1  # Start folding
            return 0

        if cell_state == 1:  # Partially folded
            if folded_neighbors >= 2:
                return 2  # Complete folding
            return 1

        return cell_state

    def set_nucleation_site(self, position: int):
        """Set initial folding nucleation site."""
        self.grid[position] = 2


class DrugResistanceCA(CellularAutomaton):
    """
    CA for cancer drug resistance evolution.

    States:
    0 = Sensitive
    1 = Partially resistant
    2 = Resistant

    Rule: Cells gain resistance through mutations and selection.
    """

    def __init__(
        self,
        grid_size: Tuple[int, int],
        mutation_rate: float = 0.01,
        selection_pressure: float = 0.5
    ):
        """
        Initialize drug resistance CA.

        Args:
            grid_size: 2D grid of cells
            mutation_rate: Probability of resistance mutation
            selection_pressure: Drug pressure (kills sensitive cells)
        """
        super().__init__(
            shape=grid_size,
            states=3,
            rule=UpdateRule.CUSTOM,
            boundary=BoundaryCondition.FIXED
        )

        self.mutation_rate = mutation_rate
        self.selection_pressure = selection_pressure

        self.custom_rule = self._resistance_rule

    def _resistance_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """
        Resistance evolution rule.

        - Sensitive cells die under drug pressure
        - Cells gain resistance from resistant neighbors
        - Random mutations occur
        """
        # Drug kills sensitive cells
        if cell_state == 0 and np.random.random() < self.selection_pressure:
            return 0  # Dies (stays 0)

        # Mutation
        if np.random.random() < self.mutation_rate:
            return min(cell_state + 1, self.states - 1)

        # Resistance spread from neighbors
        resistant_neighbors = sum(1 for n in neighbors if n >= 2)

        if cell_state < 2 and resistant_neighbors >= 3:
            return cell_state + 1

        return cell_state


class SignalingCascadeCA(CellularAutomaton):
    """
    CA for protein signaling cascade simulation.

    States represent activation levels (0-10).
    """

    def __init__(self, network_size: int, activation_threshold: float = 0.5):
        """
        Initialize signaling cascade CA.

        Args:
            network_size: Number of proteins in network
            activation_threshold: Threshold for activation propagation
        """
        super().__init__(
            shape=(network_size,),
            states=11,  # 0-10 activation levels
            rule=UpdateRule.CUSTOM,
            boundary=BoundaryCondition.OPEN
        )

        self.activation_threshold = activation_threshold
        self.custom_rule = self._signaling_rule

    def _signaling_rule(self, cell_state: int, neighbors: List[int]) -> int:
        """
        Signaling propagation rule.

        Activation spreads from highly activated neighbors.
        """
        if not neighbors:
            # Decay without input
            return max(cell_state - 1, 0)

        avg_activation = np.mean(neighbors) / self.states

        if avg_activation >= self.activation_threshold:
            # Activate
            return min(cell_state + 2, self.states - 1)
        else:
            # Decay
            return max(cell_state - 1, 0)

    def add_stimulus(self, position: int, strength: int = 10):
        """Add external stimulus to protein."""
        self.grid[position] = strength


def find_ca_attractors(ca: CellularAutomaton, max_steps: int = 200) -> Dict:
    """
    Find attractors (fixed points and cycles) of CA.

    Integrates with Nash equilibrium - attractors are stable equilibria.

    Args:
        ca: Cellular automaton
        max_steps: Maximum steps to search

    Returns:
        Dictionary with attractor info
    """
    # Try to find fixed point
    ca_copy = CellularAutomaton(ca.shape, ca.states, ca.rule, ca.boundary, ca.custom_rule)
    ca_copy.grid = ca.grid.copy()

    fixed_point = ca_copy.detect_fixed_points(max_steps)

    # Try to find cycles
    ca_copy.grid = ca.grid.copy()
    ca_copy.time = ca.time
    cycles = ca_copy.detect_cycles(max_steps)

    return {
        'fixed_point': fixed_point,
        'cycles': cycles,
        'has_attractor': fixed_point is not None or cycles is not None
    }


def ca_to_trajectory(ca_history: List[CAState]) -> np.ndarray:
    """
    Convert CA history to trajectory for HoTT path analysis.

    Returns:
        (T, N) array where T=time steps, N=grid size
    """
    trajectories = []

    for state in ca_history:
        trajectories.append(state.grid.flatten())

    return np.array(trajectories)
