# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Topos Logic Strategy for KOMPOSOS-IV Oracle

Reasons via intuitionistic logic when classical logic fails.

Uses:
  - categorical/topos_logic.py (ToposLogic, HeytingAlgebra)
  - categorical/presheaf_topos.py (PresheafTopos, Sieve, subobject classifier)

Riehl-Verity connection:
  The subobject classifier in a presheaf topos encodes multi-valued truth.
  Truth values are sieves (sets of perspectives), not booleans.
  This gives the right semantics for uncertain reasoning.

When to use:
  - Claims with partial evidence AND partial counter-evidence
  - Claims where excluded middle fails (P ∨ ¬P ≠ TRUE)
  - Claims requiring intuitionistic implication (P → Q = ¬P ∨ Q)

This activates:
  - categorical/topos_logic.py (previously dead)
  - categorical/presheaf_topos.py (previously dead)
"""

from __future__ import annotations

from typing import List, Dict, Any

from oracle.prediction import Prediction, PredictionType, ConfidenceLevel
from oracle.strategies import InferenceStrategy
from core.category import Category


class ToposLogicStrategy(InferenceStrategy):
    """
    Reason via intuitionistic logic for partial-evidence claims.

    Uses the Heyting algebra from topos_logic.py to give nuanced
    truth values when classical boolean reasoning is insufficient.

    Usage:
        strategy = ToposLogicStrategy(category)
        predictions = strategy.predict("A", "B")
        # Returns predictions with multi-valued truth from the subobject classifier
    """

    name = "topos_logic"

    def __init__(self, category: Category):
        super().__init__(category)
        self._topos_logic = None
        self._presheaf_topos = None

    def _get_topos_logic(self):
        """Lazy import and initialize ToposLogic."""
        if self._topos_logic is None:
            from categorical.topos_logic import ToposLogic
            self._topos_logic = ToposLogic(self.category)
        return self._topos_logic

    def _get_presheaf_topos(self):
        """Lazy import and initialize PresheafTopos."""
        if self._presheaf_topos is None:
            from categorical.presheaf_topos import PresheafTopos
            try:
                self._presheaf_topos = PresheafTopos.from_enriched_category(
                    self.category
                )
            except Exception:
                self._presheaf_topos = None
        return self._presheaf_topos

    def predict(self, source: str, target: str) -> List[Prediction]:
        """
        Predict using intuitionistic logic.

        Strategy:
        1. Check if there's a direct morphism (classical truth)
        2. If not, check the Heyting algebra for partial truth
        3. If excluded middle fails for this claim, flag it
        4. Use presheaf subobject classifier for multi-perspective truth
        """
        predictions = []
        topos = self._get_topos_logic()

        # Step 1: Check classical truth
        direct = self._has_direct_edge(source, target)
        if direct:
            # Classical truth holds
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="classically_true",
                prediction_type=PredictionType.KAN_EXTENSION,
                strategy_name=self.name,
                confidence=direct.confidence,
                reasoning=f"Direct morphism exists (confidence={direct.confidence:.2f})",
                evidence={"truth_type": "classical"},
            ))
            return predictions

        # Step 2: Check Heyting algebra for partial truth
        heyting_result = self._check_heyting(source, target, topos)
        if heyting_result:
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation=f"heyting_{heyting_result['truth_type']}",
                prediction_type=PredictionType.KAN_EXTENSION,
                strategy_name=self.name,
                confidence=heyting_result["confidence"],
                reasoning=heyting_result["reason"],
                evidence={
                    "truth_type": heyting_result["truth_type"],
                    "excluded_middle_holds": heyting_result.get(
                        "excluded_middle_holds", True
                    ),
                },
            ))

        # Step 3: Check presheaf subobject classifier
        presheaf_result = self._check_subobject_classifier(source, target)
        if presheaf_result:
            predictions.append(Prediction(
                source=source,
                target=target,
                predicted_relation="sieve_truth",
                prediction_type=PredictionType.CARTESIAN_LIFT,
                strategy_name=self.name,
                confidence=presheaf_result["confidence"],
                reasoning=presheaf_result["reason"],
                evidence={
                    "truth_type": "sieve",
                    "perspectives": presheaf_result.get("perspectives", []),
                    "support_fraction": presheaf_result.get("support_fraction", 0),
                },
            ))

        return sorted(predictions, key=lambda p: -p.confidence)

    def _has_direct_edge(self, source: str, target: str):
        """Check for a direct morphism."""
        for mor in self._get_morphisms():
            if mor.source == source and mor.target == target:
                return mor
        return None

    def _check_heyting(
        self, source: str, target: str, topos
    ) -> Dict[str, Any]:
        """
        Check the Heyting algebra for partial truth.

        Returns dict with truth_type, confidence, reason, etc.
        """
        try:
            # Check if excluded middle fails for these objects
            failures = topos.where_excluded_middle_fails()

            source_fails = any(f["object"] == source for f in failures)
            target_fails = any(f["object"] == target for f in failures)

            if source_fails or target_fails:
                # Excluded middle fails -- use intuitionistic truth
                return {
                    "truth_type": "intuitionistic_partial",
                    "confidence": 0.5,  # Maximum partial truth
                    "reason": (
                        f"Excluded middle fails for "
                        f"{'source' if source_fails else 'target'}. "
                        f"Using intuitionistic partial truth."
                    ),
                    "excluded_middle_holds": False,
                    "failures": failures[:5],
                }

            # Check intuitionistic implication: source -> target
            # In Heyting algebra: ¬source ∨ target
            source_negation = topos.negate(source)
            if source_negation:
                return {
                    "truth_type": "negation_implication",
                    "confidence": 0.6,
                    "reason": (
                        f"Intuitionistic implication: ¬{source} ∨ {target}. "
                        f"Negation of source has support."
                    ),
                    "excluded_middle_holds": True,
                }

        except Exception:
            pass

        return None

    def _check_subobject_classifier(
        self, source: str, target: str
    ) -> Dict[str, Any]:
        """
        Use the presheaf subobject classifier for multi-perspective truth.

        Ω (subobject classifier): truth values are sieves.
        A sieve on T is a downward-closed set of morphisms into T.
        """
        topos = self._get_presheaf_topos()
        if topos is None:
            return None

        try:
            # Get the sieve for target
            target_morphisms = self.category.morphisms_to(target)
            if not target_morphisms:
                return None

            # Build the principal sieve for target
            from categorical.presheaf_topos import Sieve
            sieve = Sieve.principal(
                target,
                {m.name: m for m in target_morphisms},
            )

            # Check if source factors through the sieve
            source_outgoing = self.category.morphisms_from(source)
            supporting = [
                m for m in source_outgoing
                if m.target == target or any(
                    p.target == target
                    for p in self.category.find_paths(m.target, target, max_length=2)
                )
            ]

            if not supporting:
                return None

            support_fraction = len(supporting) / max(len(source_outgoing), 1)
            confidence = sieve.truth_value() if hasattr(sieve, 'truth_value') else support_fraction

            return {
                "confidence": confidence,
                "reason": (
                    f"Subobject classifier: sieve on {target} has "
                    f"{len(target_morphisms)} perspectives. "
                    f"Source supports {len(supporting)}/{len(source_outgoing)}."
                ),
                "perspectives": [m.name for m in target_morphisms],
                "support_fraction": support_fraction,
            }

        except Exception:
            return None

    def get_partial_knowledge_zones(self) -> List[Dict[str, Any]]:
        """
        Find all objects where excluded middle fails.

        These are the "partial knowledge zones" -- areas where
        classical true/false reasoning is insufficient.

        Returns:
            List of object descriptions with partial knowledge info.
        """
        topos = self._get_topos_logic()
        try:
            return topos.where_excluded_middle_fails()
        except Exception:
            return []
