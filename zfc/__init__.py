# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-ZFC -- Set-Theoretic Reasoning Engine

The independent ZFC foundation for dual-engine verification.
Mirrors KOMPOSOS-CAT (categorical/) at every layer:

    CAT Layer           ->   ZFC Layer
    -----------------------------------------
    category.py         ->   universe.py
    kan_extensions.py   ->   logic.py
    cubical/paths.py    ->   well_ordering.py
    coherence.py        ->   separation.py

CAT and ZFC never see each other's internals.
Both read the same runtime Category through adapters.
Both produce independent judgments.
Category theory (CAT applied to the delta) is the bridge.

The delta types:
    AGREE   -- both engines say yes (high confidence)
    ORPHAN  -- ZFC yes, CAT no (exists but doesn't compose)
    HOLLOW  -- CAT yes, ZFC no (composes but doesn't exist)
    REJECT  -- both say no (high confidence rejection)
"""

from .universe import (
    Universe,
    ZFSet,
    Relation,
    zfset,
    relation,
)

from .logic import (
    # Language
    Formula,
    FormulaKind,
    Term,
    # Constructors
    atom,
    member,
    equals,
    neg,
    conj,
    disj,
    implies,
    iff,
    forall,
    exists,
    var,
    const,
    conj_all,
    # Model theory
    Model,
    satisfies,
    find_witness,
    # Theory
    Theory,
    # Oracle
    LogicOracle,
)

from .well_ordering import (
    Ordinal,
    WellOrder,
    InductionResult,
    # Constructors
    well_order_by_rank,
    well_order_by_relation,
    well_order_by_key,
    # Rank
    von_neumann_rank,
    rank_all,
    # Induction
    transfinite_induction,
    bounded_induction,
    # Analysis
    RankProfile,
    rank_profile,
    classify_relation_by_rank,
    # Oracle
    OrdinalOracle,
)

from .separation import (
    Constraint,
    Contradiction,
    SeparationResult,
    SeparationChecker,
    # Utilities
    prediction_to_constraint,
    predictions_to_constraints,
    detect_pairwise_contradictions,
    find_minimal_conflict,
)

from .proof_engine import (
    ProofStep,
    ProofResult,
    Proof,
    ZFCVerifier,
    CATVerifier,
    StepMethod,
    StepStatus,
    step,
    axiom,
)

from .meta_kan import (
    DeltaType,
    Resolution,
    Episode,
    EpisodeCategory,
    MetaPrediction,
    MetaKanExtension,
    System3Oracle,
    episode_similarity,
    cosine_similarity,
)

from .category_store_adapter import StoreAdapter
from .bridge import (
    DualEngineBridge as StoreDualEngineBridge,
    DualResult as StoreDualResult,
)
from .category_bridge import DualEngineBridge, DualResult

CategoryDualEngineBridge = DualEngineBridge
CategoryDualResult = DualResult
from .proof_bridge import (
    load_proof_graph,
    ProofGraphBridge,
    ConjectureResult,
    ProofVerificationResult,
)
from .axiom_miner import AxiomMiner, AxiomPattern, DiscoveredAxioms
from .evolved_bridge import EvolvedDualEngineBridge

__all__ = [
    # Universe (Layer 1)
    "Universe", "ZFSet", "Relation", "zfset", "relation",
    # Logic (Layer 2)
    "Formula", "FormulaKind", "Term",
    "atom", "member", "equals", "neg", "conj", "disj",
    "implies", "iff", "forall", "exists", "var", "const", "conj_all",
    "Model", "satisfies", "find_witness",
    "Theory", "LogicOracle",
    # Well-Ordering (Layer 3)
    "Ordinal", "WellOrder", "InductionResult",
    "well_order_by_rank", "well_order_by_relation", "well_order_by_key",
    "von_neumann_rank", "rank_all",
    "transfinite_induction", "bounded_induction",
    "RankProfile", "rank_profile", "classify_relation_by_rank",
    "OrdinalOracle",
    # Separation (Layer 4)
    "Constraint", "Contradiction", "SeparationResult", "SeparationChecker",
    "prediction_to_constraint", "predictions_to_constraints",
    "detect_pairwise_contradictions", "find_minimal_conflict",
    # Proof Engine (Layer 5)
    "ProofStep", "ProofResult", "Proof",
    "ZFCVerifier", "CATVerifier",
    "StepMethod", "StepStatus",
    "step", "axiom",
    # Meta Kan / System 3 (Layer 6)
    "DeltaType", "Resolution",
    "Episode", "EpisodeCategory",
    "MetaPrediction", "MetaKanExtension",
    "System3Oracle",
    "episode_similarity", "cosine_similarity",
    # Integration / proof bridge / evolved checks
    "StoreAdapter", "DualEngineBridge", "DualResult",
    "CategoryDualEngineBridge", "CategoryDualResult",
    "StoreDualEngineBridge", "StoreDualResult",
    "load_proof_graph", "ProofGraphBridge", "ConjectureResult",
    "ProofVerificationResult",
    "AxiomMiner", "AxiomPattern", "DiscoveredAxioms",
    "EvolvedDualEngineBridge",
]
