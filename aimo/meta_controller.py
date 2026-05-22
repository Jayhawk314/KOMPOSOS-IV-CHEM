"""
Meta Controller - Orchestrate strategy execution and answer selection.

Manages the solve session lifecycle:
- Track candidate solutions from multiple strategies
- Weighted majority voting for answer selection
- Stagnation detection and backtracking
- Time budget management
"""

import sys
import time
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import Counter

sys.path.insert(0, '.')


@dataclass
class CandidateSolution:
    """A candidate answer from a single strategy execution."""
    answer: Optional[int]
    confidence: float
    strategy_name: str
    reasoning_trace: str
    verification: Any = None  # VerificationResult
    generation_time: float = 0.0


@dataclass
class SolveSession:
    """State for solving a single problem."""
    problem_id: str
    problem_text: str
    features: Any = None  # ProblemFeatures
    candidates: List[CandidateSolution] = field(default_factory=list)
    tried_strategies: List[str] = field(default_factory=list)
    stagnation_count: int = 0
    total_time: float = 0.0
    start_time: float = field(default_factory=time.time)

    @property
    def valid_candidates(self) -> List[CandidateSolution]:
        """Candidates with non-None answers in valid range."""
        return [c for c in self.candidates
                if c.answer is not None and 0 <= c.answer <= 99999]

    @property
    def best_candidate(self) -> Optional[CandidateSolution]:
        """Highest-confidence valid candidate."""
        valid = self.valid_candidates
        if not valid:
            return None
        return max(valid, key=lambda c: c.confidence)

    @property
    def elapsed(self) -> float:
        """Time elapsed since session started."""
        return time.time() - self.start_time


class MetaController:
    """
    Meta-level controller for the olympiad solver.

    Responsibilities:
    - Select final answer via weighted majority voting
    - Detect stagnation (repeated low-confidence answers)
    - Suggest backtrack strategies when stuck
    - Manage per-problem time budget
    """

    def __init__(
        self,
        time_budget_per_problem: float = 150.0,
        min_confidence: float = 0.3,
        stagnation_threshold: int = 3,
        verbose: bool = False,
    ):
        self.time_budget = time_budget_per_problem
        self.min_confidence = min_confidence
        self.stagnation_threshold = stagnation_threshold
        self.verbose = verbose
        self._failure_memory: Dict[str, List[str]] = {}  # problem_id -> failed strategies

    def select_answer(self, session: SolveSession) -> Tuple[int, float]:
        """
        Select the final answer using weighted majority voting.

        Algorithm:
        1. Filter candidates with valid answers
        2. Group by answer value
        3. Score each answer: sum of confidences * verification bonus
        4. Return highest-scoring answer

        Args:
            session: Current solve session

        Returns:
            (answer, confidence)
        """
        valid = session.valid_candidates
        if not valid:
            return 0, 0.0

        # Group by answer, accumulate weighted votes
        votes: Dict[int, float] = {}
        vote_counts: Dict[int, int] = {}

        for c in valid:
            ans = c.answer
            weight = c.confidence

            # Bonus for verified answers
            if c.verification is not None and hasattr(c.verification, 'is_valid'):
                if c.verification.is_valid:
                    weight *= 1.5
                else:
                    weight *= 0.7

            votes[ans] = votes.get(ans, 0.0) + weight
            vote_counts[ans] = vote_counts.get(ans, 0) + 1

        if not votes:
            return 0, 0.0

        # Select answer with highest weighted vote
        best_answer = max(votes, key=votes.get)
        total_weight = sum(votes.values())
        confidence = votes[best_answer] / total_weight if total_weight > 0 else 0.0

        # Boost confidence if multiple strategies agree
        count = vote_counts[best_answer]
        if count >= 3:
            confidence = min(1.0, confidence * 1.2)
        elif count >= 2:
            confidence = min(1.0, confidence * 1.1)

        if self.verbose:
            print(f"  [Meta] Votes: {dict(sorted(votes.items(), key=lambda x: -x[1]))}", file=sys.stderr)
            print(f"  [Meta] Selected: {best_answer} (conf={confidence:.2f}, votes={count})", file=sys.stderr)

        return best_answer, confidence

    def should_backtrack(self, session: SolveSession) -> bool:
        """
        Detect stagnation: should we try different strategies?

        Stagnation indicators:
        - Multiple low-confidence answers
        - Same wrong-looking answer repeated
        - No improvement over last N candidates
        """
        valid = session.valid_candidates
        if len(valid) < 2:
            return False

        # Check if recent candidates are all low confidence
        recent = valid[-3:] if len(valid) >= 3 else valid
        avg_conf = sum(c.confidence for c in recent) / len(recent)
        if avg_conf < self.min_confidence:
            session.stagnation_count += 1
            if self.verbose:
                print(f"  [Meta] Low confidence detected: avg={avg_conf:.2f}, "
                      f"stagnation={session.stagnation_count}", file=sys.stderr)
            return session.stagnation_count >= self.stagnation_threshold

        # Check if same answer keeps appearing with low confidence
        recent_answers = [c.answer for c in recent]
        counter = Counter(recent_answers)
        most_common_answer, most_common_count = counter.most_common(1)[0]
        if most_common_count >= 2:
            # Same answer repeated - check if it's high or low confidence
            same_answer_confs = [c.confidence for c in recent if c.answer == most_common_answer]
            if max(same_answer_confs) < 0.5:
                session.stagnation_count += 1
                return session.stagnation_count >= self.stagnation_threshold

        # Reset stagnation if things are going well
        if avg_conf > 0.5:
            session.stagnation_count = max(0, session.stagnation_count - 1)

        return False

    def get_backtrack_strategies(
        self,
        session: SolveSession,
        all_strategies: List[Any],
    ) -> List[Any]:
        """
        Get untried strategies for backtracking.

        Prioritizes:
        1. Strategies not yet tried for this problem
        2. Strategies from different domains
        3. General-purpose strategies

        Returns:
            List of LLMStrategy objects to try next
        """
        tried = set(session.tried_strategies)
        untried = [s for s in all_strategies if s.name not in tried]

        # Also filter out strategies that have failed for this problem before
        failed = set(self._failure_memory.get(session.problem_id, []))
        untried = [s for s in untried if s.name not in failed]

        if self.verbose and untried:
            print(f"  [Meta] Backtrack: {len(untried)} untried strategies available", file=sys.stderr)

        return untried

    def record_failure(self, problem_id: str, strategy_name: str):
        """Record that a strategy failed for a problem (for backtrack memory)."""
        if problem_id not in self._failure_memory:
            self._failure_memory[problem_id] = []
        self._failure_memory[problem_id].append(strategy_name)

    def has_time_budget(self, session: SolveSession) -> bool:
        """Check if we still have time budget for this problem."""
        remaining = self.time_budget - session.elapsed
        has_budget = remaining > 5.0  # Need at least 5s for another attempt
        if self.verbose and not has_budget:
            print(f"  [Meta] Time budget exhausted: {session.elapsed:.1f}s / {self.time_budget}s",
                  file=sys.stderr)
        return has_budget

    def report(self, session: SolveSession) -> Dict[str, Any]:
        """
        Generate a debugging report for a solve session.

        Returns:
            Dictionary with session statistics and candidate details
        """
        valid = session.valid_candidates
        answer_counts = Counter(c.answer for c in valid)

        return {
            "problem_id": session.problem_id,
            "total_candidates": len(session.candidates),
            "valid_candidates": len(valid),
            "tried_strategies": session.tried_strategies,
            "stagnation_count": session.stagnation_count,
            "elapsed_time": round(session.elapsed, 2),
            "answer_distribution": dict(answer_counts),
            "best_candidate": {
                "answer": session.best_candidate.answer if session.best_candidate else None,
                "confidence": round(session.best_candidate.confidence, 3) if session.best_candidate else 0,
                "strategy": session.best_candidate.strategy_name if session.best_candidate else None,
            },
            "candidates": [
                {
                    "answer": c.answer,
                    "confidence": round(c.confidence, 3),
                    "strategy": c.strategy_name,
                    "verified": c.verification.is_valid if c.verification and hasattr(c.verification, 'is_valid') else None,
                    "time": round(c.generation_time, 2),
                }
                for c in session.candidates
            ],
        }
