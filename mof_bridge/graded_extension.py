# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
ZFC Graded Extension
====================

Adds Z2-graded interference detection to OracleZFCBridge.

DOES NOT MODIFY:
  - DeltaType classification (AGREE/HOLLOW/ORPHAN/REJECT)
  - ZFC or CAT verification logic
  - DualPrediction or DualResult structures
  - Any existing OracleZFCBridge behavior

ADDS:
  - Parity assignment derived from DeltaType (no new logic — falls out of
    the existing 2x2 grid)
  - GradedMorphism wrapper for each DualPrediction
  - Chain interference check across a sequence of DualPredictions
  - CollapseChain result when HOLLOW∘HOLLOW or ORPHAN∘HOLLOW detected

MATHEMATICAL BASIS:
  The parity mapping is not arbitrary — it is the natural Z2 grading
  of the validator-agreement structure:

      Consistent verdicts  (AGREE, REJECT)  → parity 0 (even)
      Inconsistent verdicts (HOLLOW, ORPHAN) → parity 1 (odd)

  Fermionic exclusion: odd ∘ odd → NULL_COLLAPSE (amplitude → 0)

  Interpretation: two consecutive validator-disagreements in a morphism
  chain = a path with zero logical support = detected exploit chain.

  This is consistent with the existing HOLLOW definition:
  "structurally plausible but logically unsound = vulnerability candidate."
  A chain of such steps is doubly unsound and collapses.

FOLDER:
  zfc/graded_extension.py
  (sits alongside zfc/bridge.py and zfc/store_adapter.py)

USAGE:
  # Existing code — unchanged:
  dual = zfc_bridge.verify_predictions(source, target, predictions)

  # New: check a chain of DualResults for interference
  from zfc.graded_extension import grade_dual_result, check_chain_interference

  graded = [grade_dual_result(dual) for dual in chain_of_duals]
  collapse = check_chain_interference(graded)
  if collapse:
      emit("cog.interference.collapse", collapse.to_dict())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from mof_bridge.graded_morphism import GradedMorphism


# ---------------------------------------------------------------------------
# Parity map — derived directly from DeltaType semantics
# ---------------------------------------------------------------------------

# Import DeltaType gracefully (same pattern as zfc_verifier.py)
try:
    from zfc.meta_kan import DeltaType
    _DELTA_PARITY: Dict[object, int] = {
        DeltaType.AGREE:  0,   # both validators agree → consistent → even
        DeltaType.REJECT: 0,   # both validators agree → consistent → even
        DeltaType.HOLLOW: 1,   # validators disagree  → inconsistent → odd
        DeltaType.ORPHAN: 1,   # validators disagree  → inconsistent → odd
    }
    ZFC_AVAILABLE = True
except ImportError:
    _DELTA_PARITY = {}
    ZFC_AVAILABLE = False


def delta_to_parity(delta_type) -> int:
    """
    Map DeltaType → Z2 parity.

    Consistent verdicts (both validators agree) → 0 (even)
    Inconsistent verdicts (validators disagree) → 1 (odd)

    Falls back to parity=1 for unknown delta types (conservative).
    """
    return _DELTA_PARITY.get(delta_type, 1)


def delta_to_amplitude(delta_type, cat_confidence: float, zfc_confidence: float) -> complex:
    """
    Map a DualPrediction's confidences to a complex amplitude.

    AGREE:  geometric mean — both validators confident
    HOLLOW: cat_confidence — CAT believes it (that's the risk signal)
    ORPHAN: zfc_confidence — ZFC believes it (that's the risk signal)
    REJECT: low amplitude  — neither believes it

    The amplitude represents "how strongly does the dangerous validator
    believe this?" — i.e. the signal strength of the inconsistency.
    """
    if not ZFC_AVAILABLE:
        return complex(cat_confidence, 0.0)

    if delta_type == DeltaType.AGREE:
        amp = (cat_confidence * zfc_confidence) ** 0.5
    elif delta_type == DeltaType.HOLLOW:
        amp = cat_confidence        # CAT signal is the risk
    elif delta_type == DeltaType.ORPHAN:
        amp = zfc_confidence        # ZFC signal is the risk
    else:  # REJECT
        amp = (1.0 - cat_confidence) * (1.0 - zfc_confidence)

    return complex(max(0.0, min(1.0, amp)), 0.0)


# ---------------------------------------------------------------------------
# GradedDualPrediction — wraps a DualPrediction with Z2 grading
# ---------------------------------------------------------------------------

@dataclass
class GradedDualPrediction:
    """
    A DualPrediction extended with Z2 grading.

    The original DualPrediction is untouched — this wraps it.
    """
    dual_prediction: object          # original DualPrediction (unmodified)
    morphism: GradedMorphism         # Z2-graded representation

    @property
    def is_odd(self) -> bool:
        return self.morphism.parity == 1

    @property
    def delta_type(self):
        return self.dual_prediction.delta_type

    @property
    def source(self) -> str:
        return self.dual_prediction.source

    @property
    def target(self) -> str:
        return self.dual_prediction.target

    def __repr__(self) -> str:
        return (
            f"GradedDualPrediction({self.source}→{self.target} "
            f"| {self.delta_type} "
            f"| parity={self.morphism.parity} "
            f"| amp={self.morphism.magnitude:.3f})"
        )


def grade_dual_prediction(dp) -> GradedDualPrediction:
    """
    Wrap a DualPrediction in a GradedDualPrediction.

    Non-destructive — original dp is untouched.
    """
    parity = delta_to_parity(dp.delta_type)
    amplitude = delta_to_amplitude(
        dp.delta_type,
        dp.cat_confidence,
        dp.zfc_confidence,
    )
    morphism = GradedMorphism(
        name=f"{dp.source}→{dp.target}[{dp.delta_type}]",
        parity=parity,
        amplitude=amplitude,
        source=dp.source,
        target=dp.target,
    )
    return GradedDualPrediction(dual_prediction=dp, morphism=morphism)


# ---------------------------------------------------------------------------
# GradedDualResult — wraps a DualResult with chain grading
# ---------------------------------------------------------------------------

@dataclass
class GradedDualResult:
    """
    A DualResult extended with graded predictions.

    The original DualResult is untouched — this wraps it.
    """
    dual_result: object                           # original DualResult
    graded_predictions: List[GradedDualPrediction]

    @property
    def odd_predictions(self) -> List[GradedDualPrediction]:
        """HOLLOW and ORPHAN predictions (validator disagreements)."""
        return [gp for gp in self.graded_predictions if gp.is_odd]

    @property
    def hollow_predictions(self) -> List[GradedDualPrediction]:
        if not ZFC_AVAILABLE:
            return []
        return [
            gp for gp in self.graded_predictions
            if gp.delta_type == DeltaType.HOLLOW
        ]

    @property
    def orphan_predictions(self) -> List[GradedDualPrediction]:
        if not ZFC_AVAILABLE:
            return []
        return [
            gp for gp in self.graded_predictions
            if gp.delta_type == DeltaType.ORPHAN
        ]

    def __repr__(self) -> str:
        n_odd = len(self.odd_predictions)
        return (
            f"GradedDualResult("
            f"{len(self.graded_predictions)} preds, "
            f"{n_odd} odd)"
        )


def grade_dual_result(dual_result) -> GradedDualResult:
    """
    Wrap a DualResult in a GradedDualResult.

    Non-destructive — original DualResult is untouched.
    """
    graded = [grade_dual_prediction(dp) for dp in dual_result.predictions]
    return GradedDualResult(
        dual_result=dual_result,
        graded_predictions=graded,
    )


# ---------------------------------------------------------------------------
# Chain interference detection
# ---------------------------------------------------------------------------

@dataclass
class CollapseChain:
    """
    A detected NULL_COLLAPSE across a chain of DualResults.

    Fired when two consecutive odd-parity (HOLLOW or ORPHAN)
    predictions compose: odd ∘ odd → NULL_COLLAPSE.

    This indicates an exploit chain: multiple validator-inconsistent
    steps that individually pass threshold but collectively collapse.
    """
    step_a: GradedDualPrediction
    step_b: GradedDualPrediction
    collapsed: GradedMorphism        # always NULL_COLLAPSE
    chain_source: str
    chain_target: str
    severity: float                  # geometric mean of input amplitudes

    # Verdict types involved
    delta_a: object                  # DeltaType of step_a
    delta_b: object                  # DeltaType of step_b

    @property
    def is_critical(self) -> bool:
        return self.severity >= 0.5

    @property
    def chain_type(self) -> str:
        """Human-readable description of what collapsed."""
        a = getattr(self.delta_a, 'name', str(self.delta_a))
        b = getattr(self.delta_b, 'name', str(self.delta_b))
        return f"{a}∘{b}"

    def to_dict(self) -> Dict:
        return {
            "type": "zfc.chain.collapse",
            "chain_type": self.chain_type,
            "chain": f"{self.chain_source} → {self.chain_target}",
            "step_a": f"{self.step_a.source}→{self.step_a.target}",
            "step_b": f"{self.step_b.source}→{self.step_b.target}",
            "severity": round(self.severity, 4),
            "critical": self.is_critical,
            "delta_a": getattr(self.delta_a, 'name', str(self.delta_a)),
            "delta_b": getattr(self.delta_b, 'name', str(self.delta_b)),
        }

    def __repr__(self) -> str:
        return (
            f"CollapseChain({self.chain_type} | "
            f"{self.chain_source}→{self.chain_target} | "
            f"severity={self.severity:.3f})"
        )


def check_chain_interference(
    graded_results: List[GradedDualResult],
    min_amplitude: float = 0.3,
) -> List[CollapseChain]:
    """
    Detect Z2 NULL_COLLAPSE across a sequence of GradedDualResults.

    A chain is a sequence of DualResults where consecutive results
    share a source/target (the output of one feeds the input of the next).

    Checks:
      For each pair of consecutive odd-parity predictions that form
      a chain (result_i.target == result_j.source), compute:

          graded_i.morphism ∘ graded_j.morphism

      If the result is NULL_COLLAPSE → exploit chain detected.

    Args:
        graded_results: Sequence of GradedDualResults (in chain order)
        min_amplitude:  Minimum signal strength to consider (filters noise)

    Returns:
        List of CollapseChain events (empty if no collapse detected)
    """
    collapses: List[CollapseChain] = []

    # Collect all odd predictions across the chain, in order
    odd_preds: List[GradedDualPrediction] = []
    for gr in graded_results:
        for gp in gr.odd_predictions:
            if gp.morphism.magnitude >= min_amplitude:
                odd_preds.append(gp)

    # Check each consecutive pair
    for i in range(len(odd_preds) - 1):
        a = odd_preds[i]
        b = odd_preds[i + 1]

        # Only compose if they form a chain
        forms_chain = (
            a.target == b.source           # sequential: A→B, B→C
            or a.source == b.source        # parallel probes on same node
        )
        if not forms_chain:
            continue

        composed = a.morphism * b.morphism  # Z2 composition

        if composed.is_collapsed:
            severity = (a.morphism.magnitude * b.morphism.magnitude) ** 0.5
            collapse = CollapseChain(
                step_a=a,
                step_b=b,
                collapsed=composed,
                chain_source=a.source,
                chain_target=b.target,
                severity=severity,
                delta_a=a.delta_type,
                delta_b=b.delta_type,
            )
            collapses.append(collapse)

    return collapses


# ---------------------------------------------------------------------------
# Convenience: grade + check in one call
# ---------------------------------------------------------------------------

def analyze_chain(
    dual_results: List,
    min_amplitude: float = 0.3,
) -> Tuple[List[GradedDualResult], List[CollapseChain]]:
    """
    Grade a list of DualResults and check for interference collapses.

    Usage:
        duals = [zfc_bridge.verify_predictions(...) for step in attack_chain]
        graded, collapses = analyze_chain(duals)

        for c in collapses:
            print(c)            # CollapseChain(HOLLOW∘HOLLOW | ...)
            emit("zfc.chain.collapse", c.to_dict())

    Returns:
        (graded_results, collapses)
    """
    graded = [grade_dual_result(dr) for dr in dual_results]
    collapses = check_chain_interference(graded, min_amplitude=min_amplitude)
    return graded, collapses
