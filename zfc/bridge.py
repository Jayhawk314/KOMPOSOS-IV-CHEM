# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Dual Engine Bridge -- Runs CAT and ZFC on the same query

Architecture:
    KomposOSStore (any domain)
           |
       StoreAdapter
        /        \\
      CAT        ZFC
   (System 2)  (System 1)
        \\        /
    DualEngineBridge
           |
       System 3
      (Meta Kan)

The bridge:
1. Runs CategoricalOracle (CAT) -> List[Prediction]
2. Runs LogicOracle + OrdinalOracle (ZFC) on each prediction
3. Classifies the delta: AGREE / ORPHAN / HOLLOW / REJECT
4. Records an Episode in System 3 for meta-learning
5. Returns a DualResult with both sides + analysis

Usage:
    from zfc.bridge import DualEngineBridge

    bridge = DualEngineBridge(store, embeddings, domain="drug_repurposing")
    result = bridge.predict("Celecoxib", "Inflammation")
    print(result.analysis)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .meta_kan import (
    DeltaType,
    Resolution,
    Episode,
    System3Oracle,
    MetaPrediction,
)
from .separation import (
    SeparationChecker,
    SeparationResult,
)
from .store_adapter import (
    store_to_logic_oracle,
    store_to_ordinal_oracle,
    adapter_summary,
)


# Threshold: CAT prediction is "yes" if confidence >= this
_CAT_THRESHOLD = 0.4


@dataclass
class DualPrediction:
    """One prediction annotated with both engine's judgments."""
    source: str
    target: str
    relation: str
    # CAT side
    cat_confidence: float
    cat_strategy: str
    # ZFC side
    zfc_says: bool
    zfc_confidence: float
    zfc_witness: Optional[Dict] = None
    # Ordinal side
    rank_gap: int = 0
    rank_direction: str = ""
    # Delta
    delta_type: DeltaType = DeltaType.UNKNOWN

    @property
    def cat_says(self) -> bool:
        return self.cat_confidence >= _CAT_THRESHOLD

    def summary(self) -> str:
        return (
            f"{self.source} --[{self.relation}]--> {self.target}  "
            f"CAT={self.cat_confidence:.2f}({self.cat_strategy}) "
            f"ZFC={'Y' if self.zfc_says else 'N'}({self.zfc_confidence:.2f}) "
            f"rank_gap={self.rank_gap} "
            f"delta={self.delta_type.name}"
        )


@dataclass
class DualResult:
    """Combined result from both engines."""
    predictions: List[DualPrediction]
    cat_result: Any  # OracleResult from CategoricalOracle
    episode: Episode
    meta_prediction: Optional[MetaPrediction] = None
    computation_time_ms: float = 0.0
    analysis: str = ""

    @property
    def agrees(self) -> List[DualPrediction]:
        return [p for p in self.predictions if p.delta_type == DeltaType.AGREE]

    @property
    def orphans(self) -> List[DualPrediction]:
        return [p for p in self.predictions if p.delta_type == DeltaType.ORPHAN]

    @property
    def hollows(self) -> List[DualPrediction]:
        return [p for p in self.predictions if p.delta_type == DeltaType.HOLLOW]

    @property
    def rejects(self) -> List[DualPrediction]:
        return [p for p in self.predictions if p.delta_type == DeltaType.REJECT]


class DualEngineBridge:
    """
    Runs both CAT and ZFC engines on the same query.

    CAT (System 2): "Do the arrows compose? What paths exist?"
    ZFC (System 1): "Is this logically entailed? Does a witness exist?"
    System 3: "Given past disagreements, what should I expect?"

    The delta between the two is where discoveries live.
    """

    def __init__(self, store, embeddings=None, domain: str = "",
                 min_confidence: float = 0.4):
        """
        Args:
            store: KomposOSStore instance
            embeddings: EmbeddingsEngine (needed for CategoricalOracle)
            domain: domain tag for System 3 episodes (e.g., "drug_repurposing")
            min_confidence: threshold for CAT predictions
        """
        self.store = store
        self.embeddings = embeddings
        self.domain = domain
        self.min_confidence = min_confidence

        # ZFC side (always available -- stdlib only)
        self.logic_oracle = store_to_logic_oracle(store)
        self.ordinal_oracle = store_to_ordinal_oracle(store)

        # CAT side (requires embeddings)
        self.cat_oracle = None
        if embeddings is not None:
            try:
                from oracle import CategoricalOracle
                self.cat_oracle = CategoricalOracle(
                    store, embeddings,
                    min_confidence=min_confidence,
                )
            except Exception:
                pass  # CAT unavailable -- bridge still works ZFC-only

        # System 3
        self.system3 = System3Oracle(f"Bridge_{domain}" if domain else "Bridge")

        # Separation checker for batch coherence
        self.separation = SeparationChecker(self.logic_oracle.model.universe)

        # Store summary for diagnostics
        self._summary = adapter_summary(store)

    @staticmethod
    def classify_dual_result(cat_says: bool, zfc_says: bool) -> DeltaType:
        """Standardized classification of CAT vs ZFC delta."""
        if cat_says and zfc_says:
            return DeltaType.AGREE
        elif not cat_says and zfc_says:
            return DeltaType.ORPHAN
        elif cat_says and not zfc_says:
            return DeltaType.HOLLOW
        else:
            return DeltaType.REJECT

    def predict(self, source: str, target: str) -> DualResult:
        """
        Run both engines on a (source, target) query.

        Steps:
        1. Run CAT oracle -> List[Prediction]
        2. For each prediction, check ZFC entailment
        3. Check ordinal rank gap
        4. Classify delta per prediction
        5. Build Episode, record in System 3
        6. Return DualResult
        """
        start = time.time()
        dual_preds: List[DualPrediction] = []
        cat_result = None

        # --- CAT side ---
        cat_predictions = []
        if self.cat_oracle is not None:
            try:
                cat_result = self.cat_oracle.predict(source, target)
                cat_predictions = cat_result.predictions
            except Exception:
                pass

        # --- ZFC side: check each CAT prediction ---
        best_cat_conf = 0.0
        best_cat_strategy = ""
        best_zfc_conf = 0.0
        best_zfc_says = False
        zfc_witness = None
        path_count = 0
        path_lengths = []

        if cat_predictions:
            for pred in cat_predictions:
                # ZFC entailment check
                zfc_says, zfc_conf, witness = self.logic_oracle.predict_relation(
                    pred.predicted_relation, pred.source, pred.target
                )

                # Ordinal rank gap
                rank_gap = 0
                rank_dir = ""
                if self.ordinal_oracle is not None:
                    try:
                        _, _, evidence = self.ordinal_oracle.predict_by_rank(
                            pred.source, pred.target
                        )
                        rank_gap = evidence.get("rank_gap", 0)
                        rank_dir = evidence.get("direction", "")
                    except Exception:
                        pass

                # Classify delta
                cat_says = pred.confidence >= _CAT_THRESHOLD
                if cat_says and zfc_says:
                    delta = DeltaType.AGREE
                elif not cat_says and zfc_says:
                    delta = DeltaType.ORPHAN
                elif cat_says and not zfc_says:
                    delta = DeltaType.HOLLOW
                else:
                    delta = DeltaType.REJECT

                dp = DualPrediction(
                    source=pred.source,
                    target=pred.target,
                    relation=pred.predicted_relation,
                    cat_confidence=pred.confidence,
                    cat_strategy=pred.strategy_name,
                    zfc_says=zfc_says,
                    zfc_confidence=zfc_conf,
                    zfc_witness=witness,
                    rank_gap=rank_gap,
                    rank_direction=rank_dir,
                    delta_type=delta,
                )
                dual_preds.append(dp)

                # Track best for episode
                if pred.confidence > best_cat_conf:
                    best_cat_conf = pred.confidence
                    best_cat_strategy = pred.strategy_name
                if zfc_conf > best_zfc_conf:
                    best_zfc_conf = zfc_conf
                    best_zfc_says = zfc_says
                    zfc_witness = witness

            path_count = len(cat_predictions)
            path_lengths = [1]  # placeholder -- CAT doesn't expose path lengths
        else:
            # No CAT predictions -- run ZFC standalone
            # Check all known relations for this pair
            for rel_name in self._summary.get("relations", []):
                zfc_says, zfc_conf, witness = self.logic_oracle.predict_relation(
                    rel_name, source, target
                )
                if zfc_says:
                    rank_gap = 0
                    rank_dir = ""
                    if self.ordinal_oracle is not None:
                        try:
                            _, _, ev = self.ordinal_oracle.predict_by_rank(source, target)
                            rank_gap = ev.get("rank_gap", 0)
                            rank_dir = ev.get("direction", "")
                        except Exception:
                            pass

                    dp = DualPrediction(
                        source=source,
                        target=target,
                        relation=rel_name,
                        cat_confidence=0.0,
                        cat_strategy="none",
                        zfc_says=True,
                        zfc_confidence=zfc_conf,
                        zfc_witness=witness,
                        rank_gap=rank_gap,
                        rank_direction=rank_dir,
                        delta_type=DeltaType.ORPHAN,
                    )
                    dual_preds.append(dp)
                    if zfc_conf > best_zfc_conf:
                        best_zfc_conf = zfc_conf
                        best_zfc_says = True

        # --- Build Episode ---
        ep_id = f"dual_{source}_{target}_{int(time.time() * 1000)}"
        episode = Episode(
            id=ep_id,
            source=source,
            target=target,
            relation=dual_preds[0].relation if dual_preds else "",
            domain=self.domain,
            cat_says=best_cat_conf >= _CAT_THRESHOLD,
            cat_confidence=best_cat_conf,
            cat_strategy=best_cat_strategy,
            cat_path_count=path_count,
            cat_path_lengths=path_lengths,
            zfc_says=best_zfc_says,
            zfc_confidence=best_zfc_conf,
            zfc_witness=str(zfc_witness) if zfc_witness else None,
            zfc_rank_gap=dual_preds[0].rank_gap if dual_preds else 0,
        )
        self.system3.record(episode)

        # --- System 3 meta-prediction ---
        meta_pred = None
        try:
            meta_pred = self.system3.predict(
                source, target,
                dual_preds[0].relation if dual_preds else "",
                self.domain,
                best_cat_conf, best_zfc_conf,
            )
        except Exception:
            pass

        elapsed = (time.time() - start) * 1000

        # --- Analysis ---
        analysis = self._build_analysis(
            source, target, dual_preds, episode, meta_pred, elapsed
        )

        return DualResult(
            predictions=dual_preds,
            cat_result=cat_result,
            episode=episode,
            meta_prediction=meta_pred,
            computation_time_ms=elapsed,
            analysis=analysis,
        )

    def predict_batch(self, pairs: List[Tuple[str, str]]) -> List[DualResult]:
        """Run dual prediction on multiple pairs."""
        return [self.predict(src, tgt) for src, tgt in pairs]

    def resolve(self, episode_id: str, resolution: Resolution,
                notes: str = ""):
        """Record the actual outcome for System 3 learning."""
        self.system3.resolve(episode_id, resolution, notes)

    def coherence_check(
        self, predictions: List[Dict[str, Any]]
    ) -> SeparationResult:
        """
        Run ZFC separation checker on a batch of prediction dicts.

        Each dict: {"source": str, "target": str, "relation": str,
                     "confidence": float, "strategy": str}
        """
        return self.separation.check(predictions)

    def report(self) -> str:
        """System 3 performance report."""
        return self.system3.report()

    def _build_analysis(self, source, target, dual_preds, episode,
                        meta_pred, elapsed_ms) -> str:
        lines = []
        lines.append(f"Dual Engine Bridge: {source} -> {target}")
        lines.append("=" * 60)
        lines.append(f"Domain: {self.domain or '(unspecified)'}")
        lines.append(f"Time: {elapsed_ms:.0f}ms")
        lines.append("")

        # Delta summary
        counts = {dt: 0 for dt in DeltaType}
        for dp in dual_preds:
            counts[dp.delta_type] += 1

        lines.append(f"Predictions: {len(dual_preds)}")
        if counts[DeltaType.AGREE]:
            lines.append(f"  AGREE:  {counts[DeltaType.AGREE]}  (both engines say yes)")
        if counts[DeltaType.ORPHAN]:
            lines.append(f"  ORPHAN: {counts[DeltaType.ORPHAN]}  (ZFC yes, CAT no -- gap in graph)")
        if counts[DeltaType.HOLLOW]:
            lines.append(f"  HOLLOW: {counts[DeltaType.HOLLOW]}  (CAT yes, ZFC no -- structural coincidence)")
        if counts[DeltaType.REJECT]:
            lines.append(f"  REJECT: {counts[DeltaType.REJECT]}  (both say no)")
        lines.append("")

        # Episode summary
        lines.append(f"Episode: {episode.id}")
        lines.append(f"  Delta type: {episode.delta_type.name}")
        lines.append(f"  CAT: says={'yes' if episode.cat_says else 'no'} "
                     f"conf={episode.cat_confidence:.2f} "
                     f"strategy={episode.cat_strategy or 'n/a'}")
        lines.append(f"  ZFC: says={'yes' if episode.zfc_says else 'no'} "
                     f"conf={episode.zfc_confidence:.2f}")
        lines.append("")

        # System 3 meta-prediction
        if meta_pred:
            lines.append("System 3 (Meta Kan):")
            lines.append(f"  Predicted delta: {meta_pred.predicted_delta.name} "
                        f"({meta_pred.delta_confidence:.0%})")
            lines.append(f"  Predicted resolution: {meta_pred.predicted_resolution.name} "
                        f"({meta_pred.resolution_confidence:.0%})")
            lines.append(f"  Run both engines? {meta_pred.should_run_both}")
            lines.append("")

        # Top predictions
        if dual_preds:
            lines.append("Top predictions:")
            for dp in dual_preds[:10]:
                lines.append(f"  {dp.summary()}")

        return "\n".join(lines)


# --- Demo ---

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from data import create_store, create_memory_store, StoredObject, StoredMorphism

    # Build a small demo store
    store = create_memory_store()

    # Add objects
    for name, typ in [
        ("Aspirin", "Drug"), ("Celecoxib", "Drug"), ("Ibuprofen", "Drug"),
        ("COX1", "Protein"), ("COX2", "Protein"),
        ("Inflammation", "Disease"), ("Pain", "Disease"),
    ]:
        store.add_object(StoredObject(name=name, type_name=typ))

    # Add morphisms
    for src, tgt, rel in [
        ("Aspirin", "COX1", "inhibits"), ("Aspirin", "COX2", "inhibits"),
        ("Ibuprofen", "COX1", "inhibits"), ("Ibuprofen", "COX2", "inhibits"),
        ("Celecoxib", "COX2", "inhibits"),
        ("COX1", "Pain", "associated_with"),
        ("COX2", "Inflammation", "associated_with"),
        ("COX2", "Pain", "associated_with"),
        ("Aspirin", "Inflammation", "treats"),
        ("Ibuprofen", "Pain", "treats"),
    ]:
        store.add_morphism(StoredMorphism(name=rel, source_name=src, target_name=tgt))

    # Create bridge (ZFC-only mode -- no embeddings)
    bridge = DualEngineBridge(store, embeddings=None, domain="demo")

    print("ZFC Engine Summary:")
    print(f"  Universe: {bridge.logic_oracle.model.universe}")
    print(f"  Theory: {bridge.logic_oracle.theory}")
    print()

    # Query: does Celecoxib treat Inflammation?
    result = bridge.predict("Celecoxib", "Inflammation")
    print(result.analysis)
    print()

    # Query: does Celecoxib treat Pain?
    result2 = bridge.predict("Celecoxib", "Pain")
    print(result2.analysis)
    print()

    # System 3 report
    print(bridge.report())
