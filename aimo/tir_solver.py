"""
TIR Solver - Multi-sample Tool-Integrated Reasoning solver.

Main entry point for competition solving:
1. Classify problem domain
2. Build TIR prompt with domain-specific examples
3. Generate N independent TIR solutions (N=32-64 on H100, less on smaller GPUs)
4. Extract \\boxed{answer} from each solution
5. Majority vote weighted by code-verification success
6. Return final answer

Budget: ~150s per problem. With vLLM on 4xH100 and Qwen2.5-Math-72B,
can generate ~32 solutions of ~2048 tokens each within budget.
"""

import sys
import time
from typing import Optional, Dict, List, Tuple
from collections import Counter

sys.path.insert(0, '.')

from aimo.llm_engine import LLMEngine, LLMConfig
from aimo.problem_classifier import ProblemClassifier, ProblemFeatures
from aimo.execution_engine import CodeExecutor
from aimo.tir_engine import TIREngine, TIRResult
from aimo.tir_prompts import build_tir_prompt, build_tir_messages


class TIRSolver:
    """
    Multi-sample TIR solver for math competitions.

    Generates N independent TIR solutions per problem, extracts answers,
    and selects the final answer by weighted majority vote.
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        n_samples: int = 32,
        temperature: float = 0.7,
        time_budget: float = 150.0,
        code_timeout: float = 10.0,
        verbose: bool = False,
    ):
        """
        Args:
            llm_config: LLM backend configuration
            n_samples: Number of independent solutions to generate
            temperature: Sampling temperature (0.7-1.0 for diversity)
            time_budget: Total seconds per problem
            code_timeout: Max seconds per code execution
            verbose: Print progress
        """
        self.verbose = verbose
        self.n_samples = n_samples
        self.temperature = temperature
        self.time_budget = time_budget

        config = llm_config or LLMConfig(backend="mock")
        self.llm = LLMEngine(config)
        self.classifier = ProblemClassifier()
        self.executor = CodeExecutor(timeout=code_timeout, verbose=verbose)
        self.tir = TIREngine(
            self.llm,
            self.executor,
            max_code_rounds=8,
            code_timeout=code_timeout,
            verbose=verbose,
        )

        # Pattern-based fallback (last resort)
        self._rag_solver = None
        self._load_fallback()

    def _load_fallback(self):
        """Load pattern-based solver as last resort."""
        try:
            from aimo.aimo3_solver import AIMO3RAGSolver
            self._rag_solver = AIMO3RAGSolver(verbose=False)
        except ImportError:
            pass

    def solve(self, problem_text: str, problem_id: str = "unknown") -> int:
        """
        Solve a single problem using multi-sample TIR.

        Never raises - always returns an integer in [0, 99999].

        Args:
            problem_text: Problem text (may contain LaTeX)
            problem_id: Optional identifier for logging

        Returns:
            Integer answer in [0, 99999]
        """
        try:
            return self._solve_impl(problem_text, problem_id)
        except Exception as e:
            if self.verbose:
                print(f"  [TIRSolver] Fatal error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
            return 0

    def _solve_impl(self, problem_text: str, problem_id: str) -> int:
        """Internal solve implementation."""
        start_time = time.time()

        if self.verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"  [TIR] Solving: {problem_text[:80]}...", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

        # Step 1: Classify
        features = self.classifier.classify(problem_text)
        domain = features.domain.name.lower()

        if self.verbose:
            print(f"  [TIR] Domain: {domain}, Difficulty: {features.difficulty.name}",
                  file=sys.stderr)

        # Step 2: Build TIR prompt
        messages = build_tir_messages(problem_text, domain)

        # Step 3: Generate N solutions
        results: List[TIRResult] = []
        time_per_sample = max(5.0, (self.time_budget - 5.0) / max(self.n_samples, 1))

        for i in range(self.n_samples):
            elapsed = time.time() - start_time
            remaining = self.time_budget - elapsed
            if remaining < 5.0:
                if self.verbose:
                    print(f"  [TIR] Time budget exhausted after {i} samples", file=sys.stderr)
                break

            # Vary temperature slightly across samples for diversity
            temp = self.temperature + (i % 5) * 0.05

            result = self.tir.solve_once(
                messages,
                temperature=min(temp, 1.0),
                time_limit=min(time_per_sample, remaining - 2.0),
            )
            results.append(result)

            if self.verbose and (i + 1) % 8 == 0:
                answers = [r.answer for r in results]
                print(f"  [TIR] {i+1}/{self.n_samples} samples, "
                      f"answers so far: {Counter(a for a in answers if a is not None).most_common(3)}",
                      file=sys.stderr)

        # Step 4: Majority vote
        answer, confidence = self._majority_vote(results)

        if self.verbose:
            elapsed = time.time() - start_time
            print(f"  [TIR] Vote: {answer} (conf={confidence:.2f}, "
                  f"samples={len(results)}, time={elapsed:.1f}s)", file=sys.stderr)

        # Step 5: Fallback if no valid answer
        if answer is None or (answer == 0 and confidence < 0.2):
            fallback = self._try_fallback(problem_text, features)
            if fallback is not None:
                if self.verbose:
                    print(f"  [TIR] Fallback: {fallback}", file=sys.stderr)
                return self._clamp(fallback)

        return self._clamp(answer if answer is not None else 0)

    def _majority_vote(self, results: List[TIRResult]) -> Tuple[Optional[int], float]:
        """
        Weighted majority vote across TIR results.

        Code-verified answers get 2x weight.
        Answers that appeared as code output get 1.5x weight.

        Returns:
            (answer, confidence)
        """
        if not results:
            return None, 0.0

        votes: Dict[int, float] = {}
        vote_counts: Dict[int, int] = {}

        for r in results:
            if r.answer is None:
                continue

            weight = 1.0

            # Code-verified bonus: boxed answer matches code output
            if r.code_verified:
                weight = 2.0
            elif r.code_blocks_succeeded > 0:
                weight = 1.5

            ans = r.answer
            votes[ans] = votes.get(ans, 0.0) + weight
            vote_counts[ans] = vote_counts.get(ans, 0) + 1

        if not votes:
            return None, 0.0

        # Select answer with highest weighted vote
        best_answer = max(votes, key=votes.get)
        total_weight = sum(votes.values())
        confidence = votes[best_answer] / total_weight if total_weight > 0 else 0.0

        # Boost for consensus
        count = vote_counts[best_answer]
        total_valid = sum(vote_counts.values())
        if total_valid > 0:
            consensus = count / total_valid
            if consensus >= 0.5:
                confidence = min(1.0, confidence + 0.1)

        return best_answer, confidence

    def _try_fallback(self, problem_text: str, features: ProblemFeatures) -> Optional[int]:
        """Try pattern-based fallback solver."""
        # Direct computation if available
        if features.direct_compute_func:
            try:
                from aimo.aimo3_solver import ParameterExtractor
                from aimo.mathlib_calculator import MathLibCalculator

                params = ParameterExtractor.extract(problem_text, features.direct_compute_func)
                calc = MathLibCalculator(verbose=False)
                result = calc.compute(features.direct_compute_func, params)
                return result
            except Exception:
                pass

        # RAG solver
        if self._rag_solver:
            try:
                answer, _ = self._rag_solver.solve(problem_text)
                return answer
            except Exception:
                pass

        return None

    def _clamp(self, answer: int) -> int:
        """Clamp to valid AIMO range [0, 99999]."""
        if answer is None:
            return 0
        return max(0, min(99999, int(answer)))

    def solve_batch(self, problems: Dict[str, str]) -> Dict[str, int]:
        """Solve multiple problems."""
        results = {}
        for pid, text in problems.items():
            results[pid] = self.solve(text, problem_id=pid)
        return results
