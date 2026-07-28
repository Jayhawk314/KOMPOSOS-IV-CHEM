# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Cubical Kan Filling for Attack Path Prediction

Key insight: Attacks form commutative diagrams in the MITRE category.
If we see 3 sides of an attack "square", we can predict the 4th.

Example:
  initial_access -> privilege_escalation
        |                    |
        v                    v
     execution  -------> credential_dump

If we observe initial_access, privilege_escalation, and execution,
Kan filling predicts: credential_dump must happen (to complete the square).

This detects:
- Multi-stage attacks in progress (predict next step)
- Parallel attack paths (distributed APT campaigns)
- Zero-day variants (same compositional structure, different technique)

Mathematical basis: Kan extension computes "optimal" fillings of partial diagrams.
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from cyber.mitre_integration import MITREDatabase, ATTACKTechnique, MITRETactic


@dataclass
class PartialAttackDiagram:
    """
    A partial commutative diagram in the attack category.

    Example (square):
      A -> B
      |    ?
      v    v
      C -> D

    We know A, B, C and want to predict D.
    """
    known_techniques: List[str]  # Technique IDs we've observed
    diagram_shape: str  # "square", "triangle", "chain"
    missing_positions: List[int]  # Which positions in diagram are unknown


@dataclass
class AttackPathPrediction:
    """A predicted attack technique based on Kan filling."""
    predicted_technique: str
    confidence: float
    reasoning: str
    supporting_techniques: List[str]  # Observed techniques that support this prediction
    diagram: PartialAttackDiagram


class CubicalKanFiller:
    """
    Predicts missing attack steps using Kan extensions.

    This is the "crystal ball" for APT detection: see partial attack,
    predict what comes next BEFORE it happens.

    Unlike ML predictions (statistical), this is compositional:
    The prediction follows from category-theoretic constraints.
    """

    def __init__(self):
        self.mitre_db = MITREDatabase()

    def predict_next_steps(self, observed_techniques: List[str]) -> List[AttackPathPrediction]:
        """
        Given observed attack techniques, predict likely next steps.

        Args:
            observed_techniques: List of MITRE technique IDs we've seen

        Returns:
            List of predicted next techniques with confidence scores
        """
        if len(observed_techniques) < 2:
            return []  # Need at least 2 techniques to form a pattern

        predictions = []

        # Strategy 1: Chain completion (A -> B -> ?)
        predictions.extend(self._predict_chain_completion(observed_techniques))

        # Strategy 2: Square filling (A -> B, A -> C, predict B -> D and C -> D)
        predictions.extend(self._predict_square_filling(observed_techniques))

        # Strategy 3: Tactic progression (if we see initial_access + execution, predict privilege_escalation)
        predictions.extend(self._predict_tactic_progression(observed_techniques))

        # Deduplicate and rank
        return self._rank_predictions(predictions)

    def _predict_chain_completion(self, observed: List[str]) -> List[AttackPathPrediction]:
        """
        Predict next technique in a linear attack chain.

        Given: A -> B -> C, predict: D such that C -> D composes validly.
        """
        if len(observed) < 2:
            return []

        predictions = []
        last_technique = observed[-1]

        # Find all techniques that can compose after the last one
        for tech_id in self.mitre_db.techniques:
            if self.mitre_db.can_compose(last_technique, tech_id):
                # Check if this tech_id fits the overall chain pattern
                confidence = self._compute_chain_confidence(observed, tech_id)

                if confidence > 0.3:  # Threshold
                    predictions.append(AttackPathPrediction(
                        predicted_technique=tech_id,
                        confidence=confidence,
                        reasoning=f"Chain completion: {last_technique} -> {tech_id}",
                        supporting_techniques=[last_technique],
                        diagram=PartialAttackDiagram(
                            known_techniques=observed,
                            diagram_shape="chain",
                            missing_positions=[len(observed)]
                        )
                    ))

        return predictions

    def _compute_chain_confidence(self, chain: List[str], next_tech: str) -> float:
        """
        Compute confidence that next_tech is the right continuation of chain.

        Higher confidence if:
        - Tactic ordering matches typical attack progression
        - Privilege requirements are satisfied
        - Common pattern in threat intelligence
        """
        # Base confidence from composition validity
        conf = 0.5

        last_tech = chain[-1]
        last_tech_obj = self.mitre_db.get_technique(last_tech)
        next_tech_obj = self.mitre_db.get_technique(next_tech)

        if not last_tech_obj or not next_tech_obj:
            return 0.0

        # Boost if tactics align with common attack progression
        if self._is_common_progression(last_tech_obj.tactics, next_tech_obj.tactics):
            conf += 0.3

        # Boost if privilege flow makes sense
        if next_tech_obj.requires_privileges and last_tech_obj.grants_privileges:
            if next_tech_obj.requires_privileges & last_tech_obj.grants_privileges:
                conf += 0.2

        return min(1.0, conf)

    def _is_common_progression(self, tactics1: List[MITRETactic], tactics2: List[MITRETactic]) -> bool:
        """Check if progression from tactics1 to tactics2 is common in attacks."""
        # Common progressions:
        # INITIAL_ACCESS -> EXECUTION
        # EXECUTION -> PRIVILEGE_ESCALATION
        # PRIVILEGE_ESCALATION -> CREDENTIAL_ACCESS
        # CREDENTIAL_ACCESS -> LATERAL_MOVEMENT
        # LATERAL_MOVEMENT -> COLLECTION
        # COLLECTION -> EXFILTRATION

        common_pairs = {
            (MITRETactic.INITIAL_ACCESS, MITRETactic.EXECUTION),
            (MITRETactic.EXECUTION, MITRETactic.PRIVILEGE_ESCALATION),
            (MITRETactic.PRIVILEGE_ESCALATION, MITRETactic.CREDENTIAL_ACCESS),
            (MITRETactic.CREDENTIAL_ACCESS, MITRETactic.LATERAL_MOVEMENT),
            (MITRETactic.LATERAL_MOVEMENT, MITRETactic.COLLECTION),
            (MITRETactic.COLLECTION, MITRETactic.EXFILTRATION),
            (MITRETactic.COLLECTION, MITRETactic.COMMAND_AND_CONTROL)
        }

        for t1 in tactics1:
            for t2 in tactics2:
                if (t1, t2) in common_pairs:
                    return True

        return False

    def _predict_square_filling(self, observed: List[str]) -> List[AttackPathPrediction]:
        """
        Fill in missing corners of attack squares (commutative diagrams).

        Square pattern:
          A -> B
          |    |
          v    v
          C -> D

        If we see A, B, C, predict D such that the square commutes:
          A -> B -> D should equal A -> C -> D
        """
        predictions = []

        if len(observed) < 3:
            return predictions

        # Try all triples as corners of a square
        for i, A in enumerate(observed):
            for j, B in enumerate(observed):
                if j <= i:
                    continue
                for k, C in enumerate(observed):
                    if k <= j:
                        continue

                    # Check if A -> B and A -> C are valid compositions
                    if not self.mitre_db.can_compose(A, B):
                        continue
                    if not self.mitre_db.can_compose(A, C):
                        continue

                    # Find D such that B -> D and C -> D both compose
                    for tech_id in self.mitre_db.techniques:
                        if (self.mitre_db.can_compose(B, tech_id) and
                            self.mitre_db.can_compose(C, tech_id)):

                            # Found a valid square filling!
                            confidence = 0.7  # High confidence for square filling

                            predictions.append(AttackPathPrediction(
                                predicted_technique=tech_id,
                                confidence=confidence,
                                reasoning=f"Square filling: {A},{B},{C} -> {tech_id}",
                                supporting_techniques=[A, B, C],
                                diagram=PartialAttackDiagram(
                                    known_techniques=[A, B, C],
                                    diagram_shape="square",
                                    missing_positions=[3]
                                )
                            ))

        return predictions

    def _predict_tactic_progression(self, observed: List[str]) -> List[AttackPathPrediction]:
        """
        Predict next technique based on MITRE tactic progression.

        If we've seen tactics [INITIAL_ACCESS, EXECUTION], we should see
        PRIVILEGE_ESCALATION or PERSISTENCE next.
        """
        predictions = []

        # Get tactics of observed techniques
        observed_tactics = set()
        for tech_id in observed:
            tech = self.mitre_db.get_technique(tech_id)
            if tech:
                observed_tactics.update(tech.tactics)

        # Determine what tactic should come next
        next_tactics = self._get_likely_next_tactics(observed_tactics)

        # Find techniques that implement those tactics
        for next_tactic in next_tactics:
            candidate_techniques = self.mitre_db.get_techniques_by_tactic(next_tactic)

            for tech in candidate_techniques:
                # Check if this technique can compose with any observed technique
                can_compose_with_any = any(
                    self.mitre_db.can_compose(obs_tech, tech.technique_id)
                    for obs_tech in observed
                )

                if can_compose_with_any:
                    predictions.append(AttackPathPrediction(
                        predicted_technique=tech.technique_id,
                        confidence=0.6,  # Medium confidence for tactic-based prediction
                        reasoning=f"Tactic progression: {next_tactic.name} follows observed tactics",
                        supporting_techniques=observed,
                        diagram=PartialAttackDiagram(
                            known_techniques=observed,
                            diagram_shape="tactic_progression",
                            missing_positions=[]
                        )
                    ))

        return predictions

    def _get_likely_next_tactics(self, observed_tactics: Set[MITRETactic]) -> List[MITRETactic]:
        """Get likely next tactics based on what's been observed."""
        next_tactics = []

        # Simple rules for tactic progression
        if MITRETactic.INITIAL_ACCESS in observed_tactics:
            if MITRETactic.EXECUTION not in observed_tactics:
                next_tactics.append(MITRETactic.EXECUTION)
            if MITRETactic.PERSISTENCE not in observed_tactics:
                next_tactics.append(MITRETactic.PERSISTENCE)

        if MITRETactic.EXECUTION in observed_tactics:
            if MITRETactic.PRIVILEGE_ESCALATION not in observed_tactics:
                next_tactics.append(MITRETactic.PRIVILEGE_ESCALATION)

        if MITRETactic.PRIVILEGE_ESCALATION in observed_tactics:
            if MITRETactic.CREDENTIAL_ACCESS not in observed_tactics:
                next_tactics.append(MITRETactic.CREDENTIAL_ACCESS)

        if MITRETactic.CREDENTIAL_ACCESS in observed_tactics:
            if MITRETactic.LATERAL_MOVEMENT not in observed_tactics:
                next_tactics.append(MITRETactic.LATERAL_MOVEMENT)

        if MITRETactic.LATERAL_MOVEMENT in observed_tactics:
            if MITRETactic.COLLECTION not in observed_tactics:
                next_tactics.append(MITRETactic.COLLECTION)

        if MITRETactic.COLLECTION in observed_tactics:
            if MITRETactic.EXFILTRATION not in observed_tactics:
                next_tactics.append(MITRETactic.EXFILTRATION)

        return next_tactics

    def _rank_predictions(self, predictions: List[AttackPathPrediction]) -> List[AttackPathPrediction]:
        """Deduplicate and rank predictions by confidence."""
        # Deduplicate by predicted technique
        best_predictions = {}

        for pred in predictions:
            tech_id = pred.predicted_technique
            if tech_id not in best_predictions or pred.confidence > best_predictions[tech_id].confidence:
                best_predictions[tech_id] = pred

        # Sort by confidence
        ranked = sorted(best_predictions.values(), key=lambda p: p.confidence, reverse=True)

        return ranked


class AttackPathPredictor:
    """
    High-level interface for attack path prediction.

    This is the production API for KOMPOSOS-SEC prediction.
    """

    def __init__(self):
        self.kan_filler = CubicalKanFiller()
        self.mitre_db = MITREDatabase()

    def predict_next_attacks(self, observed_techniques: List[str], top_n: int = 5) -> List[Dict]:
        """
        Predict next likely attack techniques.

        Args:
            observed_techniques: MITRE ATT&CK technique IDs observed so far
            top_n: Number of top predictions to return

        Returns:
            List of prediction dictionaries with technique info
        """
        predictions = self.kan_filler.predict_next_steps(observed_techniques)

        results = []
        for pred in predictions[:top_n]:
            tech = self.mitre_db.get_technique(pred.predicted_technique)

            results.append({
                "technique_id": pred.predicted_technique,
                "technique_name": tech.name if tech else "Unknown",
                "confidence": pred.confidence,
                "reasoning": pred.reasoning,
                "tactics": [t.name for t in tech.tactics] if tech else [],
                "observables": tech.observables if tech else {},
                "supporting_evidence": pred.supporting_techniques
            })

        return results

    def explain_prediction(self, prediction: AttackPathPrediction) -> str:
        """Generate human-readable explanation of a prediction."""
        tech = self.mitre_db.get_technique(prediction.predicted_technique)

        explanation = f"PREDICTED ATTACK TECHNIQUE\n"
        explanation += "=" * 60 + "\n\n"

        if tech:
            explanation += f"Technique: {tech.name} ({tech.technique_id})\n"
            explanation += f"Tactics: {', '.join(t.name for t in tech.tactics)}\n"
        else:
            explanation += f"Technique: {prediction.predicted_technique}\n"

        explanation += f"Confidence: {prediction.confidence:.2%}\n\n"

        explanation += f"Reasoning:\n{prediction.reasoning}\n\n"

        explanation += f"Supporting Evidence:\n"
        for tech_id in prediction.supporting_techniques:
            supp_tech = self.mitre_db.get_technique(tech_id)
            if supp_tech:
                explanation += f"  - {supp_tech.name} ({tech_id})\n"

        explanation += "\n" + "=" * 60 + "\n"

        if tech and tech.observables:
            explanation += "\nWHAT TO LOOK FOR:\n"
            for obs_type, obs_list in tech.observables.items():
                explanation += f"\n{obs_type.upper()}:\n"
                for obs in obs_list:
                    explanation += f"  - {obs}\n"

        return explanation
