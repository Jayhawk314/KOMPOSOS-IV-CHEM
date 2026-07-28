# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-SEC: Cybersecurity Threat Detection via Category Theory

This module applies the same mathematical framework used for protein discovery
and fusion reactor design to cybersecurity threat detection.

Key innovations:
1. Temporal sheaves: Event streams with time-window coherence
2. Ricci curvature: Compress 1M-node networks to 10K supernodes
3. Cubical Kan filling: Predict missing attack steps from partial chains
4. Compositional proofs: Explainable attack chains as morphism composition

Unlike signature-based detection, this detects APTs and zero-days via
compositional structure: attack chains must compose according to MITRE ATT&CK.
"""

from cyber.attack_chain_strategies import AttackChainStrategy, MITRECompositionStrategy
from cyber.temporal_sheaves import TemporalSheafChecker, EventStreamCoherence
from cyber.ricci_compression import RicciFlowCompressor, NetworkSupernodes
from cyber.kan_filling import CubicalKanFiller, AttackPathPredictor
from cyber.mitre_integration import MITREDatabase, ATTACKTechnique
from cyber.cyber_oracle import CyberSecurityOracle
from cyber.supply_chain import SupplyChainCategory, SupplyChainStrategy
from cyber.persistent_homology import TDAAttackDetector, PersistenceDiagram

__all__ = [
    "AttackChainStrategy",
    "MITRECompositionStrategy",
    "TemporalSheafChecker",
    "EventStreamCoherence",
    "RicciFlowCompressor",
    "NetworkSupernodes",
    "CubicalKanFiller",
    "AttackPathPredictor",
    "MITREDatabase",
    "ATTACKTechnique",
    "CyberSecurityOracle",
    "SupplyChainCategory",
    "SupplyChainStrategy",
    "TDAAttackDetector",
    "PersistenceDiagram",
]

__version__ = "0.2.0"
