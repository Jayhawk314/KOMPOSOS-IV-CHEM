# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins <jhawk314@gmail.com>

"""
Attack Propagation via Cellular Automata - Phase 3B

Models cyber attack spread using CA dynamics:
- Worm propagation (self-replicating malware)
- APT lateral movement (targeted, stealthy progression)
- Ransomware cascades (file encryption spread)
- DDoS amplification (botnet recruitment)

Each attack type has custom transition rules with:
- Vulnerability-dependent infection rates
- Network topology awareness
- Defense mechanisms (patching, isolation)
- Multi-stage attack chains

Integration with MITRE ATT&CK:
- T1059: Command and Scripting Interpreter (worm execution)
- T1021: Remote Services (lateral movement)
- T1486: Data Encrypted for Impact (ransomware)
- T1498: Network Denial of Service (DDoS)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import math
from collections import defaultdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from categorical.cellular_automata import (
    CellularGrid,
    CellularAutomaton,
    TransitionRule,
    AttackState,
    EpidemicMetrics
)


# =============================================================================
# ATTACK-SPECIFIC CELL STATES
# =============================================================================

class WormState(Enum):
    """States for worm propagation."""
    VULNERABLE = "vulnerable"
    INFECTED = "infected"
    PATCHED = "patched"
    QUARANTINED = "quarantined"


class APTState(Enum):
    """States for APT lateral movement."""
    SECURE = "secure"
    RECONNAISSANCE = "recon"          # T1595: Active Scanning
    INITIAL_ACCESS = "initial"        # T1566: Phishing
    EXECUTION = "execution"           # T1059: Command Execution
    PERSISTENCE = "persistence"       # T1053: Scheduled Task
    PRIVILEGE_ESCALATION = "privesc"  # T1068: Exploitation
    LATERAL_MOVEMENT = "lateral"      # T1021: Remote Services
    EXFILTRATED = "exfil"            # T1041: C2 Channel


class RansomwareState(Enum):
    """States for ransomware spread."""
    UNENCRYPTED = "unencrypted"
    ENCRYPTING = "encrypting"
    ENCRYPTED = "encrypted"
    BACKUP_DESTROYED = "backup_destroyed"
    RANSOM_PAID = "ransom_paid"


# =============================================================================
# WORM PROPAGATION MODEL
# =============================================================================

def worm_transition_rule(
    infection_rate: float = 0.5,
    patch_rate: float = 0.1,
    vulnerability_threshold: float = 0.7
):
    """
    Worm propagation transition rule.

    Models self-replicating malware (Morris worm, WannaCry, etc.)

    Parameters:
        infection_rate: Base probability of infection
        patch_rate: Rate at which systems get patched
        vulnerability_threshold: Minimum vulnerability score for infection

    MITRE ATT&CK:
        - T1059.001: PowerShell execution
        - T1210: Exploitation of Remote Services
        - T1572: Protocol Tunneling
    """
    def rule(state: WormState, neighbors: List[WormState], metadata: Dict) -> WormState:
        vulnerability = metadata.get('vulnerability_score', 0.5)

        if state == WormState.VULNERABLE:
            # Check for infected neighbors
            infected_neighbors = sum(1 for n in neighbors if n == WormState.INFECTED)

            if infected_neighbors > 0 and vulnerability >= vulnerability_threshold:
                # Infection probability increases with more infected neighbors
                prob_infection = 1.0 - (1.0 - infection_rate) ** infected_neighbors
                if metadata.get('random', 0.5) < prob_infection:
                    return WormState.INFECTED

            # Proactive patching
            if metadata.get('random', 0.5) < patch_rate:
                return WormState.PATCHED

        elif state == WormState.INFECTED:
            # Infected systems may be quarantined
            if metadata.get('ids_detected', False):
                return WormState.QUARANTINED

        return state

    return TransitionRule(
        name="Worm",
        rule_function=rule,
        parameters={
            'infection_rate': infection_rate,
            'patch_rate': patch_rate,
            'vulnerability_threshold': vulnerability_threshold
        }
    )


# =============================================================================
# APT LATERAL MOVEMENT MODEL
# =============================================================================

def apt_transition_rule(
    stealth_factor: float = 0.8,
    detection_sensitivity: float = 0.3,
    privilege_escalation_rate: float = 0.2
):
    """
    APT lateral movement transition rule.

    Models sophisticated, multi-stage attacks (APT29, APT28, etc.)

    Attack chain: Secure → Recon → Initial Access → Execution →
                  Persistence → PrivEsc → Lateral Movement → Exfiltration

    Parameters:
        stealth_factor: How well attack evades detection (higher = stealthier)
        detection_sensitivity: Security monitoring threshold
        privilege_escalation_rate: Rate of escalating privileges

    MITRE ATT&CK Coverage:
        - TA0001: Initial Access
        - TA0002: Execution
        - TA0003: Persistence
        - TA0004: Privilege Escalation
        - TA0008: Lateral Movement
        - TA0010: Exfiltration
    """
    def rule(state: APTState, neighbors: List[APTState], metadata: Dict) -> APTState:
        security_posture = metadata.get('security_level', 0.5)
        is_critical_asset = metadata.get('is_critical', False)

        # Detection check (can revert to SECURE if detected)
        detection_prob = (1.0 - stealth_factor) * detection_sensitivity
        if state != APTState.SECURE and metadata.get('random', 0.5) < detection_prob:
            return APTState.SECURE  # Detected and remediated

        if state == APTState.SECURE:
            # Check if neighbors are compromised (lateral movement vector)
            compromised_neighbors = [
                n for n in neighbors
                if n in [APTState.LATERAL_MOVEMENT, APTState.PERSISTENCE, APTState.EXECUTION]
            ]

            if compromised_neighbors and security_posture < 0.7:
                return APTState.RECONNAISSANCE

        elif state == APTState.RECONNAISSANCE:
            # Recon complete, attempt initial access
            if metadata.get('random', 0.5) < (1.0 - security_posture):
                return APTState.INITIAL_ACCESS

        elif state == APTState.INITIAL_ACCESS:
            # Execute payload
            return APTState.EXECUTION

        elif state == APTState.EXECUTION:
            # Establish persistence
            if metadata.get('random', 0.5) < 0.8:  # High success rate
                return APTState.PERSISTENCE

        elif state == APTState.PERSISTENCE:
            # Attempt privilege escalation
            if metadata.get('random', 0.5) < privilege_escalation_rate:
                return APTState.PRIVILEGE_ESCALATION

        elif state == APTState.PRIVILEGE_ESCALATION:
            # Begin lateral movement
            return APTState.LATERAL_MOVEMENT

        elif state == APTState.LATERAL_MOVEMENT:
            # Critical assets get exfiltrated
            if is_critical_asset:
                return APTState.EXFILTRATED

        return state

    return TransitionRule(
        name="APT",
        rule_function=rule,
        parameters={
            'stealth_factor': stealth_factor,
            'detection_sensitivity': detection_sensitivity,
            'privilege_escalation_rate': privilege_escalation_rate
        }
    )


# =============================================================================
# RANSOMWARE CASCADE MODEL
# =============================================================================

def ransomware_transition_rule(
    encryption_rate: float = 0.9,
    spread_rate: float = 0.6,
    backup_destruction_prob: float = 0.3,
    payment_rate: float = 0.4
):
    """
    Ransomware cascade transition rule.

    Models file encryption spread (WannaCry, Ryuk, REvil, etc.)

    Parameters:
        encryption_rate: Speed of encrypting files
        spread_rate: Lateral movement rate
        backup_destruction_prob: Probability of destroying backups
        payment_rate: Fraction of victims who pay ransom

    MITRE ATT&CK:
        - T1486: Data Encrypted for Impact
        - T1490: Inhibit System Recovery (backup destruction)
        - T1489: Service Stop
    """
    def rule(state: RansomwareState, neighbors: List[RansomwareState], metadata: Dict) -> RansomwareState:
        has_backup = metadata.get('has_backup', False)
        has_network_share = metadata.get('network_share', False)

        if state == RansomwareState.UNENCRYPTED:
            # Check for encrypting/encrypted neighbors (spread vector)
            infected_neighbors = sum(
                1 for n in neighbors
                if n in [RansomwareState.ENCRYPTING, RansomwareState.ENCRYPTED]
            )

            if infected_neighbors > 0:
                # Spread through network shares
                if has_network_share:
                    prob_spread = 1.0 - (1.0 - spread_rate) ** infected_neighbors
                    if metadata.get('random', 0.5) < prob_spread:
                        return RansomwareState.ENCRYPTING

        elif state == RansomwareState.ENCRYPTING:
            # Complete encryption
            if metadata.get('random', 0.5) < encryption_rate:
                # Attempt backup destruction
                if has_backup and metadata.get('random', 0.5) < backup_destruction_prob:
                    return RansomwareState.BACKUP_DESTROYED
                else:
                    return RansomwareState.ENCRYPTED

        elif state == RansomwareState.ENCRYPTED:
            # Victim may pay ransom
            if metadata.get('random', 0.5) < payment_rate:
                return RansomwareState.RANSOM_PAID

        return state

    return TransitionRule(
        name="Ransomware",
        rule_function=rule,
        parameters={
            'encryption_rate': encryption_rate,
            'spread_rate': spread_rate,
            'backup_destruction_prob': backup_destruction_prob,
            'payment_rate': payment_rate
        }
    )


# =============================================================================
# ATTACK CELLULAR AUTOMATA
# =============================================================================

@dataclass
class AttackPropagationCA:
    """
    Specialized CA for cyber attack propagation.

    Combines CA evolution with attack-specific analytics:
    - Initial compromise detection
    - Critical path analysis
    - Containment simulation
    - Impact assessment
    """
    ca: CellularAutomaton
    attack_type: str

    def simulate_attack(
        self,
        grid: CellularGrid,
        initial_compromised: Set[int],
        steps: int = 50
    ) -> Dict:
        """
        Simulate attack propagation.

        Args:
            grid: Network topology as cellular grid
            initial_compromised: Set of initially compromised nodes
            steps: Number of time steps to simulate

        Returns:
            Dict with trajectory, metrics, and analysis
        """
        # Set initial compromised nodes
        for node in initial_compromised:
            if self.attack_type == "worm":
                grid.states[node] = WormState.INFECTED
            elif self.attack_type == "apt":
                grid.states[node] = APTState.INITIAL_ACCESS
            elif self.attack_type == "ransomware":
                grid.states[node] = RansomwareState.ENCRYPTING

        # Evolve attack
        trajectory = self.ca.evolve(grid, steps=steps)

        # Compute metrics
        metrics = self._compute_attack_metrics(trajectory)

        return {
            'trajectory': trajectory,
            'metrics': metrics,
            'initial_compromised': initial_compromised,
            'attack_type': self.attack_type,
            'steps': steps
        }

    def _compute_attack_metrics(self, trajectory: List[CellularGrid]) -> Dict:
        """Compute attack-specific metrics."""
        metrics = {}

        if self.attack_type == "worm":
            metrics['infection_curve'] = [
                grid.count_state(WormState.INFECTED)
                for grid in trajectory
            ]
            metrics['patch_rate'] = [
                grid.count_state(WormState.PATCHED)
                for grid in trajectory
            ]
            metrics['peak_infection'] = max(metrics['infection_curve'])
            metrics['peak_metric'] = metrics['peak_infection']

        elif self.attack_type == "apt":
            metrics['compromise_stages'] = [
                {
                    'recon': grid.count_state(APTState.RECONNAISSANCE),
                    'initial': grid.count_state(APTState.INITIAL_ACCESS),
                    'lateral': grid.count_state(APTState.LATERAL_MOVEMENT),
                    'exfil': grid.count_state(APTState.EXFILTRATED)
                }
                for grid in trajectory
            ]
            final = trajectory[-1]
            metrics['exfiltration_count'] = final.count_state(APTState.EXFILTRATED)
            metrics['peak_metric'] = max(
                sum(stage.values()) for stage in metrics['compromise_stages']
            ) if metrics['compromise_stages'] else 0

        elif self.attack_type == "ransomware":
            metrics['encryption_progress'] = [
                grid.count_state(RansomwareState.ENCRYPTED) +
                grid.count_state(RansomwareState.BACKUP_DESTROYED)
                for grid in trajectory
            ]
            final = trajectory[-1]
            metrics['total_encrypted'] = final.count_state(RansomwareState.ENCRYPTED)
            metrics['backups_destroyed'] = final.count_state(RansomwareState.BACKUP_DESTROYED)
            metrics['ransom_paid'] = final.count_state(RansomwareState.RANSOM_PAID)
            metrics['peak_metric'] = max(metrics['encryption_progress']) if metrics['encryption_progress'] else 0

        return metrics

    def critical_path_analysis(self, trajectory: List[CellularGrid]) -> List[int]:
        """
        Identify critical nodes in attack propagation.

        Returns nodes that were key in spreading attack.
        """
        critical_nodes = set()

        for t in range(1, len(trajectory)):
            prev = trajectory[t-1]
            curr = trajectory[t]

            # Find nodes that transitioned and have many neighbors
            for node in curr.states:
                if prev.states.get(node) != curr.states.get(node):
                    # Node changed state
                    neighbor_count = len(curr.get_neighbors(node))
                    if neighbor_count > 3:  # High connectivity threshold
                        critical_nodes.add(node)

        return sorted(list(critical_nodes))

    def containment_simulation(
        self,
        grid: CellularGrid,
        initial_compromised: Set[int],
        containment_nodes: Set[int],
        steps: int = 50
    ) -> Dict:
        """
        Simulate attack with containment measures.

        Args:
            grid: Network grid
            initial_compromised: Initially infected nodes
            containment_nodes: Nodes to isolate/patch
            steps: Simulation steps

        Returns:
            Comparison of with/without containment
        """
        # Scenario 1: No containment
        grid_no_contain = grid.copy()
        result_no_contain = self.simulate_attack(
            grid_no_contain,
            initial_compromised,
            steps
        )

        # Scenario 2: With containment
        grid_contain = grid.copy()

        # Apply containment
        for node in containment_nodes:
            if self.attack_type == "worm":
                grid_contain.states[node] = WormState.PATCHED
            elif self.attack_type == "ransomware":
                # Disconnect from network (remove edges)
                grid_contain.adjacency[node] = set()

        result_contain = self.simulate_attack(
            grid_contain,
            initial_compromised,
            steps
        )

        return {
            'no_containment': result_no_contain,
            'with_containment': result_contain,
            'containment_nodes': containment_nodes,
            'reduction': self._compute_containment_effectiveness(
                result_no_contain,
                result_contain
            )
        }

    def _compute_containment_effectiveness(
        self,
        no_contain: Dict,
        with_contain: Dict
    ) -> Dict:
        """Measure effectiveness of containment."""
        if self.attack_type == "worm":
            peak_no = no_contain['metrics']['peak_infection']
            peak_with = with_contain['metrics']['peak_infection']
            reduction = (peak_no - peak_with) / max(peak_no, 1)

        elif self.attack_type == "ransomware":
            enc_no = no_contain['metrics']['total_encrypted']
            enc_with = with_contain['metrics']['total_encrypted']
            reduction = (enc_no - enc_with) / max(enc_no, 1)

        else:
            reduction = 0.0

        return {
            'reduction_fraction': reduction,
            'reduction_percent': reduction * 100
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_worm_ca(
    infection_rate: float = 0.5,
    patch_rate: float = 0.1
) -> AttackPropagationCA:
    """Create worm propagation cellular automaton."""
    rule = worm_transition_rule(
        infection_rate=infection_rate,
        patch_rate=patch_rate
    )
    ca = CellularAutomaton(name="Worm", transition_rule=rule)
    return AttackPropagationCA(ca=ca, attack_type="worm")


def create_apt_ca(
    stealth_factor: float = 0.8,
    detection_sensitivity: float = 0.3
) -> AttackPropagationCA:
    """Create APT lateral movement cellular automaton."""
    rule = apt_transition_rule(
        stealth_factor=stealth_factor,
        detection_sensitivity=detection_sensitivity
    )
    ca = CellularAutomaton(name="APT", transition_rule=rule)
    return AttackPropagationCA(ca=ca, attack_type="apt")


def create_ransomware_ca(
    encryption_rate: float = 0.9,
    spread_rate: float = 0.6
) -> AttackPropagationCA:
    """Create ransomware cascade cellular automaton."""
    rule = ransomware_transition_rule(
        encryption_rate=encryption_rate,
        spread_rate=spread_rate
    )
    ca = CellularAutomaton(name="Ransomware", transition_rule=rule)
    return AttackPropagationCA(ca=ca, attack_type="ransomware")


# =============================================================================
# NETWORK TOPOLOGY GENERATORS
# =============================================================================

def create_enterprise_network(
    num_workstations: int = 100,
    num_servers: int = 10,
    num_critical: int = 3
) -> Tuple[CellularGrid, Set[int]]:
    """
    Create enterprise network topology.

    Returns:
        - CellularGrid with realistic enterprise structure
        - Set of critical asset node IDs
    """
    grid = CellularGrid()

    total_nodes = num_workstations + num_servers + num_critical
    critical_nodes = set(range(total_nodes - num_critical, total_nodes))

    # Initialize all as secure/unencrypted
    for node in range(total_nodes):
        grid.states[node] = WormState.VULNERABLE

        # Add metadata
        is_critical = node in critical_nodes
        grid.metadata[node] = {
            'is_critical': is_critical,
            'vulnerability_score': 0.5 + (0.3 if not is_critical else 0.1),
            'security_level': 0.3 if not is_critical else 0.8,
            'has_backup': node >= num_workstations,  # Servers have backups
            'network_share': True,
            'random': 0.5  # Placeholder for stochastic version
        }

    # Build topology: workstations → servers → critical assets
    # Workstations connect to servers
    for ws in range(num_workstations):
        server = num_workstations + (ws % num_servers)
        grid.adjacency[ws].add(server)
        grid.adjacency[server].add(ws)

    # Servers connect to critical assets
    for server in range(num_workstations, num_workstations + num_servers):
        for critical in critical_nodes:
            grid.adjacency[server].add(critical)
            grid.adjacency[critical].add(server)

    # Some workstation peer connections
    for ws in range(0, num_workstations - 1, 10):
        for peer in range(ws + 1, min(ws + 5, num_workstations)):
            grid.adjacency[ws].add(peer)
            grid.adjacency[peer].add(ws)

    return grid, critical_nodes


def create_scale_free_network(num_nodes: int = 100, m: int = 3) -> CellularGrid:
    """
    Create scale-free network (Barabási-Albert model).

    Scale-free networks have power-law degree distribution.
    Common in real networks (Internet, social networks, etc.)

    Args:
        num_nodes: Total number of nodes
        m: Number of edges to attach from new node

    Returns:
        CellularGrid with scale-free topology
    """
    grid = CellularGrid()

    # Initialize with m+1 fully connected nodes
    for node in range(m + 1):
        grid.states[node] = WormState.VULNERABLE
        grid.metadata[node] = {
            'vulnerability_score': 0.6,
            'random': 0.5
        }

        for other in range(node):
            grid.adjacency[node].add(other)
            grid.adjacency[other].add(node)

    # Add remaining nodes with preferential attachment
    for new_node in range(m + 1, num_nodes):
        grid.states[new_node] = WormState.VULNERABLE
        grid.metadata[new_node] = {
            'vulnerability_score': 0.6,
            'random': 0.5
        }

        # Compute degree distribution
        degrees = {node: len(neighbors) for node, neighbors in grid.adjacency.items()}
        total_degree = sum(degrees.values())

        if total_degree == 0:
            total_degree = 1

        # Preferential attachment: probability ∝ degree
        targets = set()
        while len(targets) < m:
            # Simple deterministic selection based on degree
            candidates = [(node, deg) for node, deg in degrees.items()
                         if node < new_node and node not in targets]
            if not candidates:
                break

            # Pick highest degree nodes
            candidates.sort(key=lambda x: x[1], reverse=True)
            targets.add(candidates[0][0])

        # Add edges
        for target in targets:
            grid.adjacency[new_node].add(target)
            grid.adjacency[target].add(new_node)

    return grid
