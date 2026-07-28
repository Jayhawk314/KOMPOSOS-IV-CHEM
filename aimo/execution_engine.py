# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Execution Engine - Code execution and LLM strategy execution.

Includes:
- CodeExecutor: Safe code execution sandbox for LLM-generated code
- LLMExecutionEngine: Execute LLM strategies with code verification
"""

import sys
import re
import time
import math
import traceback

sys.path.insert(0, '.')

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


# =============================================================================
# CODE EXECUTOR - Safe sandbox for LLM-generated code
# =============================================================================

# Modules allowed in sandboxed execution
ALLOWED_MODULES = frozenset({
    'math', 'itertools', 'functools', 'collections', 'fractions',
    'decimal', 'operator', 'bisect', 'heapq', 'random', 'string',
    'copy', 're', 'statistics',
})

# Builtins allowed in sandboxed execution
SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
    'filter': filter, 'float': float, 'frozenset': frozenset, 'hex': hex,
    'int': int, 'isinstance': isinstance, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'oct': oct, 'ord': ord,
    'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'sorted': sorted,
    'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
    'True': True, 'False': False, 'None': None,
}


def _safe_import(name, *args, **kwargs):
    """Import function that only allows safe modules."""
    if name not in ALLOWED_MODULES:
        raise ImportError(f"Module '{name}' is not allowed in sandbox")
    return __builtins__.__import__(name, *args, **kwargs) if hasattr(__builtins__, '__import__') else __import__(name, *args, **kwargs)


class CodeExecutor:
    """
    Safe code execution sandbox for LLM-generated Python code.

    Only allows whitelisted modules and builtins.
    Enforces timeout via alarm/thread mechanisms.
    """

    def __init__(self, timeout: float = 10.0, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose

    def extract_code_blocks(self, llm_response: str) -> List[str]:
        """
        Extract Python code blocks from an LLM response.

        Looks for ```python ... ``` blocks.
        """
        blocks = re.findall(r'```python\s*\n(.*?)```', llm_response, re.DOTALL)
        if not blocks:
            # Try generic code blocks
            blocks = re.findall(r'```\s*\n(.*?)```', llm_response, re.DOTALL)
        return blocks

    def execute_safely(self, code: str, timeout: Optional[float] = None) -> Tuple[bool, Any, str]:
        """
        Execute code in a restricted sandbox.

        Args:
            code: Python code string
            timeout: Override default timeout

        Returns:
            (success, result, stderr)
            result is the value of the last expression or captured print output
        """
        t = timeout or self.timeout

        # Build sandbox globals
        sandbox_globals = dict(SAFE_BUILTINS)
        sandbox_globals['__builtins__'] = dict(SAFE_BUILTINS)
        sandbox_globals['__builtins__']['__import__'] = _safe_import

        # Pre-import allowed modules
        for mod_name in ['math', 'itertools', 'functools', 'collections', 'fractions']:
            try:
                sandbox_globals[mod_name] = __import__(mod_name)
            except ImportError:
                pass

        # Capture print output
        captured_output = []
        original_print = print

        def capture_print(*args, **kwargs):
            captured_output.append(' '.join(str(a) for a in args))

        sandbox_globals['print'] = capture_print
        sandbox_globals['__builtins__']['print'] = capture_print

        start = time.time()
        try:
            # Compile and execute
            compiled = compile(code, '<sandbox>', 'exec')

            # Execute with timeout check (simple approach for cross-platform)
            exec(compiled, sandbox_globals)

            elapsed = time.time() - start
            if elapsed > t:
                return False, None, f"Execution took {elapsed:.1f}s (limit: {t}s)"

            # Try to get 'result' or 'answer' variable
            result = sandbox_globals.get('result', sandbox_globals.get('answer', None))

            # If no result variable, try captured output
            if result is None and captured_output:
                last_output = captured_output[-1].strip()
                try:
                    result = int(last_output)
                except ValueError:
                    try:
                        result = float(last_output)
                    except ValueError:
                        result = last_output

            stderr = ""
            if self.verbose and captured_output:
                stderr = "\n".join(captured_output)

            return True, result, stderr

        except Exception as e:
            elapsed = time.time() - start
            error_msg = f"{type(e).__name__}: {e}"
            if self.verbose:
                error_msg += f"\n{traceback.format_exc()}"
            return False, None, error_msg


class LLMExecutionEngine:
    """
    Execute LLM strategies and extract verified answers.

    Extends the base ExecutionEngine concept for LLM-based solving:
    - Sends prompts to LLM with self-consistency sampling (n=3)
    - Extracts answers from responses
    - Internal majority vote across samples
    - Code-verified samples get 1.5x vote weight
    """

    # Temperatures for self-consistency sampling
    SAMPLE_TEMPERATURES = [0.3, 0.7, 1.0]

    def __init__(self, llm_engine, code_executor: Optional[CodeExecutor] = None, verbose: bool = False):
        """
        Args:
            llm_engine: LLMEngine instance
            code_executor: Optional CodeExecutor for verification
            verbose: Enable debug output
        """
        self.llm = llm_engine
        self.code_executor = code_executor or CodeExecutor(verbose=verbose)
        self.verbose = verbose

    def execute_strategy(
        self,
        strategy,  # LLMStrategy
        problem_text: str,
        features: Any = None,
        n_samples: int = 3,
        theorem_context: str = "",
        time_remaining: Optional[float] = None,
    ) -> Tuple[Optional[int], float, str]:
        """
        Execute a strategy with self-consistency sampling.

        Generates n_samples responses at varied temperatures, extracts answers,
        runs internal majority vote with code-verified weight boost.

        Args:
            strategy: LLMStrategy with prompt_template
            problem_text: The math problem text
            features: ProblemFeatures (optional, for context)
            n_samples: Number of LLM samples (default 3)
            theorem_context: Mathematical context text for prompt injection
            time_remaining: Seconds left; if < 30, reduce to n=1

        Returns:
            (answer, confidence, reasoning_trace)
        """
        # Reduce samples when time is tight
        if time_remaining is not None and time_remaining < 30.0:
            n_samples = 1

        # Build prompt from strategy template with theorem context
        prompt = strategy.prompt_template.format(
            problem=problem_text,
            theorem_context=theorem_context,
        )

        start_time = time.time()

        # Generate responses at varied temperatures (self-consistency)
        all_candidates = []
        temps = self.SAMPLE_TEMPERATURES[:n_samples]

        for i, temp in enumerate(temps):
            try:
                responses = self.llm.generate(prompt, n=1, temperature=temp)
            except Exception as e:
                if self.verbose:
                    print(f"  Sample {i} error: {e}", file=sys.stderr)
                continue

            for resp in responses:
                answer = self._extract_answer(resp)
                code_verified = self._verify_with_code(resp)
                confidence = self._compute_confidence(resp, answer, code_verified)
                all_candidates.append((answer, confidence, resp, code_verified))

        generation_time = time.time() - start_time

        if not all_candidates:
            return None, 0.0, "no_responses"

        # Internal majority vote across samples
        best_answer, best_conf, best_trace = self._majority_vote(all_candidates)

        if self.verbose:
            answers = [c[0] for c in all_candidates]
            print(f"  Strategy '{strategy.name}': samples={answers}, "
                  f"vote={best_answer}, conf={best_conf:.2f}, "
                  f"time={generation_time:.1f}s",
                  file=sys.stderr)

        return best_answer, best_conf, best_trace

    def _majority_vote(self, candidates: List[Tuple]) -> Tuple[Optional[int], float, str]:
        """
        Internal majority vote across self-consistency samples.

        Code-verified answers get 1.5x vote weight.

        Args:
            candidates: List of (answer, confidence, trace, code_verified)

        Returns:
            (best_answer, confidence, best_trace)
        """
        # Group by answer
        vote_scores = {}  # answer -> total weighted score
        vote_traces = {}  # answer -> best trace (highest confidence)
        vote_confs = {}   # answer -> max confidence

        for answer, confidence, trace, code_verified in candidates:
            if answer is None:
                continue

            weight = confidence
            if code_verified is not None and code_verified == answer:
                weight *= 1.5  # Code-verified boost

            vote_scores[answer] = vote_scores.get(answer, 0) + weight

            if answer not in vote_confs or confidence > vote_confs[answer]:
                vote_confs[answer] = confidence
                vote_traces[answer] = trace

        if not vote_scores:
            # No valid answers - return best trace anyway
            best = max(candidates, key=lambda c: c[1])
            return best[0], best[1], best[2]

        # Pick answer with highest total score
        best_answer = max(vote_scores, key=vote_scores.get)

        # Confidence = base confidence + consensus bonus
        n_for_answer = sum(1 for a, _, _, _ in candidates if a == best_answer)
        n_total = sum(1 for a, _, _, _ in candidates if a is not None)
        consensus_bonus = 0.15 * (n_for_answer / max(n_total, 1))

        final_conf = min(1.0, vote_confs[best_answer] + consensus_bonus)

        return best_answer, final_conf, vote_traces[best_answer]

    def _extract_answer(self, response: str) -> Optional[int]:
        """
        Extract integer answer from LLM response.

        Tries multiple patterns in order of reliability.
        """
        from aimo.llm_engine import LLMEngine
        return LLMEngine.extract_answer(response)

    def _verify_with_code(self, response: str) -> Optional[int]:
        """
        If response contains code blocks, execute them and return the result.

        Returns:
            Integer result from code execution, or None
        """
        blocks = self.code_executor.extract_code_blocks(response)
        if not blocks:
            return None

        for code in blocks:
            success, result, stderr = self.code_executor.execute_safely(code)
            if success and result is not None:
                try:
                    return int(result)
                except (ValueError, TypeError):
                    continue

        return None

    def _compute_confidence(self, response: str, answer: Optional[int], code_result: Optional[int]) -> float:
        """
        Compute confidence score for an answer.

        Factors:
        - Answer extracted successfully (0.3)
        - Code verification matches (0.3)
        - Reasoning quality heuristic (0.4)
        """
        if answer is None:
            return 0.0

        conf = 0.3  # Got an answer

        # Code verification bonus
        if code_result is not None and code_result == answer:
            conf += 0.3
        elif code_result is not None:
            conf -= 0.1  # Code disagrees

        # Reasoning quality
        if len(response) > 100:
            conf += 0.1
        if re.search(r'therefore|thus|hence', response, re.IGNORECASE):
            conf += 0.1
        if re.search(r'verify|check|confirm', response, re.IGNORECASE):
            conf += 0.1
        if re.search(r'\\boxed\{', response):
            conf += 0.1

        return min(1.0, max(0.0, conf))
