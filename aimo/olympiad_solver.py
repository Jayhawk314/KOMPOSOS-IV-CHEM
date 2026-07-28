# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Olympiad Solver - Main entry point for AIMO3 competition.

Two solver modes:
1. TIR mode (production): Tool-Integrated Reasoning with multi-sample voting.
   LLM reasons step-by-step, writes and executes Python code, sees output,
   continues reasoning. N=32 independent solutions, majority vote.

2. Legacy mode (fallback): Strategy beam + pattern matching.
   Used when TIR solver is unavailable or for backward compatibility.

Kaggle entry point: OlympiadSolver.kaggle_predict(problem_text) -> int
"""

import sys
import time
from typing import Dict, Optional, Tuple, List

sys.path.insert(0, '.')

from aimo.llm_engine import LLMEngine, LLMConfig
from aimo.problem_classifier import ProblemClassifier, ProblemFeatures, Difficulty
from aimo.strategy_search import select_llm_strategies, score_strategy_response
from aimo.execution_engine import LLMExecutionEngine, CodeExecutor
from aimo.answer_verifier import AnswerVerifier
from aimo.meta_controller import MetaController, SolveSession, CandidateSolution
from aimo.math_context import MathContextBuilder, MathContext


# Singleton for Kaggle to avoid reloading the model
_SINGLETON_SOLVER = None


class OlympiadSolver:
    """
    Full olympiad-level math problem solver.

    Primary path: TIR (Tool-Integrated Reasoning)
    - Generates N independent solution traces with interleaved code execution
    - Majority vote weighted by code verification

    Fallback path: Strategy beam + pattern matching
    - LLM strategy prompts with self-consistency sampling
    - Pattern-based direct solve for known problem types

    Never crashes - always returns an integer in [0, 99999].
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        beam_width: int = 8,
        max_candidates: int = 16,
        time_budget_per_problem: float = 150.0,
        n_tir_samples: int = 32,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.beam_width = beam_width
        self.max_candidates = max_candidates
        self.time_budget = time_budget_per_problem

        # Initialize components
        config = llm_config or LLMConfig(backend="mock")
        self.llm = LLMEngine(config)
        self.classifier = ProblemClassifier()
        self.code_executor = CodeExecutor(timeout=10.0, verbose=verbose)
        self.exec_engine = LLMExecutionEngine(self.llm, self.code_executor, verbose=verbose)
        self.verifier = AnswerVerifier(verbose=verbose)
        self.meta = MetaController(
            time_budget_per_problem=time_budget_per_problem,
            verbose=verbose,
        )

        # Math context builder (KG-backed theorem retrieval)
        self.context_builder = MathContextBuilder(verbose=verbose)

        # TIR solver (primary path when LLM is available)
        # DISABLED: Using legacy path with full TheoremKG categorical retrieval
        self._tir_solver = None
        # self._init_tir(config, n_tir_samples)

        # Pattern-based fallback solver (last resort)
        self._rag_solver = None
        self._load_rag_solver()

    def _init_tir(self, config: LLMConfig, n_samples: int):
        """Initialize TIR solver if possible."""
        try:
            from aimo.tir_solver import TIRSolver
            self._tir_solver = TIRSolver(
                llm_config=config,
                n_samples=n_samples,
                time_budget=self.time_budget,
                verbose=self.verbose,
            )
        except Exception:
            pass

    def _load_rag_solver(self):
        """Load the pattern-based RAG solver as last-resort fallback."""
        try:
            from aimo.aimo3_solver import AIMO3RAGSolver
            self._rag_solver = AIMO3RAGSolver(verbose=False)
        except ImportError:
            pass

    def solve(self, problem_text: str, problem_id: str = "unknown") -> int:
        """
        Solve a single AIMO problem.

        Never raises - always returns an integer in [0, 99999].

        Args:
            problem_text: Problem statement (may contain LaTeX)
            problem_id: Optional problem identifier for logging

        Returns:
            Integer answer in [0, 99999]
        """
        try:
            return self._solve_impl(problem_text, problem_id)
        except Exception as e:
            if self.verbose:
                print(f"  [Solver] Fatal error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
            return 0

    def _solve_impl(self, problem_text: str, problem_id: str) -> int:
        """Internal solve implementation."""
        if self.verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"  Solving: {problem_text[:80]}...", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

        # Try TIR solver first (primary path)
        if self._tir_solver is not None:
            answer = self._tir_solver.solve(problem_text, problem_id)
            if answer is not None and answer > 0:
                return self._clamp(answer)

        # Fallback to legacy strategy beam
        return self._solve_legacy(problem_text, problem_id)

    def _solve_legacy(self, problem_text: str, problem_id: str) -> int:
        """Legacy solver: KG context + strategy beam + pattern matching."""
        # Step 1: Classify problem
        features = self.classifier.classify(problem_text)

        if self.verbose:
            print(f"  Domain: {features.domain.name}, "
                  f"Difficulty: {features.difficulty.name}, "
                  f"Direct: {features.is_direct_solvable}",
                  file=sys.stderr)

        # Step 2: Build math context from Theorem KG
        try:
            math_ctx = self.context_builder.build_context(problem_text, features)
            theorem_context = math_ctx.context_text
            # If KG computation hint matches, use as early signal
            if math_ctx.computation_hint is not None:
                if self.verbose:
                    print(f"  KG hint: {math_ctx.computation_hint}", file=sys.stderr)
        except Exception as e:
            if self.verbose:
                print(f"  [KG] Context build failed: {e}", file=sys.stderr)
            theorem_context = ""
            math_ctx = None

        # Step 3: Create solve session
        session = SolveSession(
            problem_id=problem_id,
            problem_text=problem_text,
            features=features,
        )
        session._theorem_context = theorem_context  # attach for strategies

        # Step 4: Select LLM strategies
        strategies = select_llm_strategies(features, problem_text, self.beam_width)

        if self.verbose:
            print(f"  Strategies: {[s.name for s in strategies]}", file=sys.stderr)

        # Step 5: Execute strategies (with KG context)
        self._execute_strategies(session, strategies)

        # Step 6: Backtrack if stagnated
        backtrack_round = 0
        while (self.meta.should_backtrack(session)
               and self.meta.has_time_budget(session)
               and backtrack_round < 2):
            backtrack_round += 1
            backtrack_strategies = self.meta.get_backtrack_strategies(session, strategies)
            if not backtrack_strategies:
                break
            self._execute_strategies(session, backtrack_strategies[:4])

        # Step 7: Select final answer via majority vote
        answer, confidence = self.meta.select_answer(session)

        # Step 8: Last-resort fallback (check KG hint first, then patterns)
        if answer == 0 and confidence < 0.2:
            # Try KG computation hint
            if math_ctx and math_ctx.computation_hint is not None:
                answer = math_ctx.computation_hint
                if self.verbose:
                    print(f"  KG computation hint used: {answer}", file=sys.stderr)
            else:
                fallback = self._try_direct_solve(problem_text, features)
                if fallback is not None:
                    if self.verbose:
                        print(f"  Fallback direct solve: {fallback}", file=sys.stderr)
                    answer = fallback

        if self.verbose:
            report = self.meta.report(session)
            print(f"  Final: {answer} (conf={confidence:.2f}, "
                  f"candidates={report['valid_candidates']}, "
                  f"time={report['elapsed_time']}s)", file=sys.stderr)

        return self._clamp(answer)

    def _execute_strategies(self, session: SolveSession, strategies: List) -> None:
        """Execute a batch of strategies and add candidates."""
        # Get theorem context from KG (attached to session)
        theorem_context = getattr(session, '_theorem_context', "")

        for strategy in strategies:
            if not self.meta.has_time_budget(session):
                break
            if len(session.candidates) >= self.max_candidates:
                break

            start_time = time.time()
            time_remaining = self.meta.time_budget - session.elapsed

            answer, confidence, trace = self.exec_engine.execute_strategy(
                strategy, session.problem_text, session.features,
                theorem_context=theorem_context,
                time_remaining=time_remaining,
            )

            gen_time = time.time() - start_time

            verification = None
            if answer is not None:
                verification = self.verifier.verify(
                    answer, session.problem_text, session.features, trace
                )
                if verification.is_valid:
                    confidence = max(confidence, verification.confidence)
                else:
                    confidence *= 0.5

            candidate = CandidateSolution(
                answer=answer,
                confidence=confidence,
                strategy_name=strategy.name,
                reasoning_trace=trace,
                verification=verification,
                generation_time=gen_time,
            )
            session.candidates.append(candidate)
            session.tried_strategies.append(strategy.name)

            if answer is None or confidence < 0.2:
                self.meta.record_failure(session.problem_id, strategy.name)

    def _try_direct_solve(self, problem_text: str, features: ProblemFeatures) -> Optional[int]:
        """Last-resort: try to solve directly using pattern matching."""
        if features.direct_compute_func is None:
            return self._try_rag_fallback(problem_text)

        try:
            from aimo.aimo3_solver import ParameterExtractor
            from aimo.mathlib_calculator import MathLibCalculator

            params = ParameterExtractor.extract(problem_text, features.direct_compute_func)
            calculator = MathLibCalculator(verbose=False)
            result = calculator.compute(features.direct_compute_func, params)
            return result
        except Exception:
            return self._try_rag_fallback(problem_text)

    def _try_rag_fallback(self, problem_text: str) -> Optional[int]:
        """Try the RAG solver as a last resort."""
        if self._rag_solver is None:
            return None

        try:
            answer, trace = self._rag_solver.solve(problem_text)
            return answer
        except Exception:
            return None

    def _clamp(self, answer: int) -> int:
        """Clamp answer to valid AIMO range [0, 99999]."""
        if answer is None:
            return 0
        return max(0, min(99999, int(answer)))

    def solve_batch(self, problems: Dict[str, str]) -> Dict[str, int]:
        """Solve multiple problems."""
        results = {}
        for pid, text in problems.items():
            results[pid] = self.solve(text, problem_id=pid)
        return results

    @staticmethod
    def kaggle_predict(problem_text: str) -> int:
        """
        Kaggle API entry point.

        Uses singleton pattern to avoid reloading model between problems.

        Args:
            problem_text: Problem statement

        Returns:
            Integer answer in [0, 99999]
        """
        global _SINGLETON_SOLVER
        if _SINGLETON_SOLVER is None:
            config = _detect_best_config()
            _SINGLETON_SOLVER = OlympiadSolver(
                llm_config=config,
                beam_width=8,
                max_candidates=16,
                time_budget_per_problem=150.0,
                n_tir_samples=32,
                verbose=False,
            )
        return _SINGLETON_SOLVER.solve(problem_text)


def _detect_best_config() -> LLMConfig:
    """
    Auto-detect the best available backend.

    Priority: vllm (H100) > transformers (local GPU) > hf_api (online) > mock
    """
    import os

    # Try vLLM first (Kaggle H100)
    try:
        import vllm  # noqa: F401
        return LLMConfig(
            model_name="Qwen/Qwen2.5-Math-72B-Instruct",
            backend="vllm",
            tensor_parallel_size=4,
            max_tokens=4096,
            temperature=0.7,
        )
    except ImportError:
        pass

    # Try transformers with GPU
    try:
        import torch
        if torch.cuda.is_available():
            return LLMConfig(
                model_name="Qwen/Qwen2.5-Math-1.5B-Instruct",
                backend="transformers",
                max_tokens=2048,
                temperature=0.7,
            )
    except ImportError:
        pass

    # Try OpenRouter API (GPT-OSS-120B - best for competition math)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if not openrouter_key:
        for env_path in [os.path.join(os.path.dirname(__file__), '..', '.env'),
                         os.path.join('.', '.env')]:
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('OPENROUTER_API_KEY='):
                            openrouter_key = line.split('=', 1)[1].strip()
                            break
                if openrouter_key:
                    break
            except FileNotFoundError:
                pass
    if openrouter_key:
        return LLMConfig(
            model_name="openai/gpt-oss-120b",
            backend="openrouter",
            api_token=openrouter_key,
            max_tokens=4096,
            temperature=0.7,
        )

    # Try HuggingFace Inference API (online)
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        try:
            from huggingface_hub import HfFolder
            hf_token = HfFolder.get_token()
        except Exception:
            pass
    if not hf_token:
        for env_path in [os.path.join(os.path.dirname(__file__), '..', '.env'),
                         os.path.join('.', '.env')]:
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('HF_TOKEN='):
                            hf_token = line.split('=', 1)[1].strip()
                            break
                if hf_token:
                    break
            except FileNotFoundError:
                pass
    if hf_token:
        return LLMConfig(
            model_name="Qwen/Qwen2.5-Math-7B-Instruct",
            backend="hf_api",
            api_token=hf_token,
            max_tokens=2048,
            temperature=0.7,
        )

    # No LLM available - raise so it's obvious
    raise RuntimeError(
        "No LLM backend available. Need one of: "
        "vllm (pip install vllm), "
        "GPU + transformers (pip install transformers torch), "
        "OPENROUTER_API_KEY for OpenRouter API, "
        "or HF_TOKEN env var for HuggingFace API"
    )


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  OLYMPIAD SOLVER - Live LLM Test")
    print("=" * 80)

    config = _detect_best_config()
    print(f"  Backend: {config.backend}, Model: {config.model_name}")
    solver = OlympiadSolver(llm_config=config, verbose=True)

    test_problems = [
        ("diff_squares",
         "Find the number of integers between 1 and 1000 that can be expressed as difference of squares",
         750),
        ("vieta",
         "The quadratic x^2 - 5x + 6 = 0 has roots. Find sum of their squares",
         13),
        ("chord",
         "Circle radius 5, chord at distance 3. Find chord length",
         8),
        ("cube",
         "Smallest perfect cube divisible by 12",
         216),
        ("digits",
         "How many 3-digit numbers have all distinct digits",
         648),
    ]

    correct = 0
    for name, problem, expected in test_problems:
        answer = solver.solve(problem, problem_id=name)
        status = "PASS" if answer == expected else "FAIL"
        print(f"  {status}: {name} = {answer} (expected {expected})")
        if answer == expected:
            correct += 1

    print(f"\n  Results: {correct}/{len(test_problems)} correct")
    print("=" * 80)
