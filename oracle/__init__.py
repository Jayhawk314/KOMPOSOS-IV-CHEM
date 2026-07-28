# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS-III Categorical Oracle
================================

The Oracle system generates predictions using 9 rigorous inference strategies:
1. KanExtensionStrategy - Categorical Kan extensions (colimit computation)
2. SemanticSimilarityStrategy - Embedding-based similarity
3. TemporalReasoningStrategy - Temporal metadata analysis
4. TypeHeuristicStrategy - Type-constrained inference
5. YonedaPatternStrategy - Morphism pattern matching
6. CompositionStrategy - Path composition (transitive closure)
7. FibrationLiftStrategy - Cartesian lift predictions
8. StructuralHoleStrategy - Triangle closure
9. GeometricStrategy - Ollivier-Ricci curvature analysis

Predictions are validated by:
- SheafCoherenceChecker - Ensures predictions agree on overlaps
- PredictionOptimizer - Game-theoretic selection
- OracleLearner - Bayesian confidence adjustment

Usage:
    from oracle import CategoricalOracle

    oracle = CategoricalOracle(store, embeddings)
    predictions = oracle.predict(source, target)
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.prediction import Prediction, PredictionBatch, PredictionType
from oracle.strategies import (
    InferenceStrategy,
    KanExtensionStrategy,
    SemanticSimilarityStrategy,
    TemporalReasoningStrategy,
    TypeHeuristicStrategy,
    YonedaPatternStrategy,
    CompositionStrategy,
    FibrationLiftStrategy,
    StructuralHoleStrategy,
    GeometricStrategy,
)
from oracle.coherence import SheafCoherenceChecker, CoherenceResult
from oracle.optimizer import PredictionOptimizer, OptimizationResult
from oracle.learner import OracleLearner

from data import KomposOSStore, EmbeddingsEngine


@dataclass
class OracleResult:
    """Complete result from Oracle prediction."""
    predictions: List[Prediction]
    coherence_result: CoherenceResult
    optimization_result: OptimizationResult
    strategy_contributions: Dict[str, int]
    total_candidates: int
    computation_time_ms: float


class CategoricalOracle:
    """
    The KOMPOSOS-III Categorical Oracle.

    Uses 8 inference strategies backed by:
    - Category theory (Kan extensions)
    - Semantic analysis (embeddings)
    - Game theory (Nash equilibrium)
    - Bayesian learning (confidence adjustment)

    Requires embeddings to be initialized for semantic similarity strategy.
    """

    def __init__(self,
                 store: KomposOSStore,
                 embeddings: EmbeddingsEngine,
                 min_confidence: float = 0.4,
                 max_predictions: int = 20):
        """
        Initialize the Categorical Oracle.

        Args:
            store: KOMPOSOS-III data store
            embeddings: Embeddings engine (REQUIRED)
            min_confidence: Minimum confidence threshold for predictions
            max_predictions: Maximum predictions to return

        Raises:
            ValueError: If embeddings is None or not available
        """
        if embeddings is None or not embeddings.is_available:
            raise ValueError(
                "CategoricalOracle requires initialized embeddings. "
                "Run 'python cli.py embed' first to compute embeddings."
            )

        self.store = store
        self.embeddings = embeddings
        self.min_confidence = min_confidence
        self.max_predictions = max_predictions

        # Shared cache so all strategies reuse the same morphism/object lists
        # instead of each loading a separate ~2 GB copy from the store.
        _cache: dict = {}

        # Initialize all 9 core strategies
        self.strategies: List[InferenceStrategy] = [
            KanExtensionStrategy(store, _shared_cache=_cache),
            SemanticSimilarityStrategy(store, embeddings, _shared_cache=_cache),
            TemporalReasoningStrategy(store, _shared_cache=_cache),
            TypeHeuristicStrategy(store, _shared_cache=_cache),
            YonedaPatternStrategy(store, _shared_cache=_cache),
            CompositionStrategy(store, _shared_cache=_cache),
            FibrationLiftStrategy(store, _shared_cache=_cache),
            StructuralHoleStrategy(store, _shared_cache=_cache),
            GeometricStrategy(store, _shared_cache=_cache),
        ]

        # Initialize validation and optimization components
        self.coherence_checker = SheafCoherenceChecker(embeddings)
        self.optimizer = PredictionOptimizer(
            min_confidence=min_confidence,
            max_predictions=max_predictions,
        )
        self.learner = OracleLearner()

    def predict(self, source: str, target: str) -> OracleResult:
        """
        Generate predictions for source -> target relationship.

        Process:
        1. Run all 8 inference strategies
        2. Merge duplicate predictions
        3. Apply sheaf coherence validation
        4. Optimize selection via game theory
        5. Adjust confidences via learning

        Args:
            source: Source object name
            target: Target object name

        Returns:
            OracleResult with predictions and metadata
        """
        start_time = time.time()

        # Verify objects exist
        source_obj = self.store.get_object(source)
        target_obj = self.store.get_object(target)

        if not source_obj:
            return self._empty_result(f"Source object '{source}' not found")
        if not target_obj:
            return self._empty_result(f"Target object '{target}' not found")

        # Step 1: Collect predictions from all strategies
        all_predictions: List[Prediction] = []
        strategy_contributions: Dict[str, int] = {}

        for strategy in self.strategies:
            try:
                preds = strategy.predict(source, target)
                strategy_contributions[strategy.name] = len(preds)
                all_predictions.extend(preds)
            except Exception as e:
                # Log error but continue with other strategies
                print(f"Warning: Strategy {strategy.name} failed: {e}")
                strategy_contributions[strategy.name] = 0

        total_candidates = len(all_predictions)

        if not all_predictions:
            return self._empty_result("No predictions generated", start_time)

        # Step 2: Merge duplicate predictions
        merged = self._merge_predictions(all_predictions)

        # Step 3: Apply sheaf coherence validation
        coherence_result = self.coherence_checker.check_coherence(merged)
        coherent_predictions = coherence_result.filtered_predictions

        # Step 4: Adjust confidences based on coherence
        adjusted = self.coherence_checker.adjust_confidences(coherent_predictions)

        # Step 5: Apply learning-based confidence adjustment
        learned = [
            p.with_adjusted_confidence(self.learner.adjust_confidence(p))
            for p in adjusted
        ]

        # Step 6: Game-theoretic optimization
        optimization_result = self.optimizer.optimize(learned)

        computation_time = (time.time() - start_time) * 1000

        return OracleResult(
            predictions=optimization_result.selected_predictions,
            coherence_result=coherence_result,
            optimization_result=optimization_result,
            strategy_contributions=strategy_contributions,
            total_candidates=total_candidates,
            computation_time_ms=computation_time,
        )

    def predict_simple(self, source: str, target: str) -> List[Prediction]:
        """
        Simplified prediction interface - just returns predictions.

        Args:
            source: Source object name
            target: Target object name

        Returns:
            List of predictions sorted by confidence
        """
        result = self.predict(source, target)
        return result.predictions

    def predict_batch(self, pairs: List[tuple]) -> Dict[tuple, List[Prediction]]:
        """
        Predict for multiple source-target pairs.

        Args:
            pairs: List of (source, target) tuples

        Returns:
            Dict mapping each pair to its predictions
        """
        results = {}
        for source, target in pairs:
            results[(source, target)] = self.predict_simple(source, target)
        return results

    def record_outcome(self, prediction: Prediction, was_correct: bool):
        """
        Record prediction outcome for learning.

        Call this when a prediction has been validated or rejected.

        Args:
            prediction: The prediction that was evaluated
            was_correct: True if prediction was confirmed
        """
        self.learner.record_outcome(prediction, was_correct)

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics summary."""
        return self.learner.get_summary()

    def _merge_predictions(self, predictions: List[Prediction]) -> List[Prediction]:
        """
        Merge predictions with the same key.

        Predictions from multiple strategies for the same (source, target, relation)
        are combined with boosted confidence.
        """
        by_key: Dict[tuple, List[Prediction]] = {}

        for pred in predictions:
            if pred.key not in by_key:
                by_key[pred.key] = []
            by_key[pred.key].append(pred)

        merged = []
        for key, preds in by_key.items():
            if len(preds) == 1:
                merged.append(preds[0])
            else:
                # Merge multiple predictions
                base = preds[0]
                for other in preds[1:]:
                    base = base.merge_with(other)
                merged.append(base)

        return merged

    def _empty_result(self, reason: str, start_time: float = None) -> OracleResult:
        """Create empty result for error cases."""
        computation_time = 0.0
        if start_time:
            computation_time = (time.time() - start_time) * 1000

        return OracleResult(
            predictions=[],
            coherence_result=CoherenceResult(
                is_coherent=True,
                coherence_score=0.0,
                min_similarity=0.0,
                contradictions=[],
                filtered_predictions=[],
            ),
            optimization_result=OptimizationResult(
                selected_predictions=[],
                total_utility=0.0,
                strategy_profile={},
                iterations=0,
            ),
            strategy_contributions={},
            total_candidates=0,
            computation_time_ms=computation_time,
        )


# Export main classes
__all__ = [
    'CategoricalOracle',
    'OracleResult',
    'Prediction',
    'PredictionType',
    'PredictionBatch',
]
