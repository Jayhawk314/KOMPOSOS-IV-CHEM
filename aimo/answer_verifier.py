# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Answer Verifier - Multi-layer verification for AIMO answers.

Checks:
1. Range validity [0, 99999]
2. Domain-specific sanity (counting > 0, remainder < modulus, etc.)
3. Code execution verification (if reasoning has code blocks)
4. Pattern match cross-check (if direct-solvable, verify with mathlib_calculator)
"""

import sys
import re
from typing import Optional, Any, List
from dataclasses import dataclass, field

sys.path.insert(0, '.')


@dataclass
class VerificationResult:
    """Result of answer verification."""
    answer: int
    confidence: float
    method: str
    checks_passed: int
    checks_total: int
    details: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.checks_passed == self.checks_total

    @property
    def pass_rate(self) -> float:
        return self.checks_passed / self.checks_total if self.checks_total > 0 else 0.0


class AnswerVerifier:
    """
    Multi-layer answer verification for AIMO competition.

    Applies a series of checks to validate an answer, accumulating
    a confidence score and pass/fail for each check.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._calculator = None
        self._code_executor = None
        self._load_deps()

    def _load_deps(self):
        """Lazily load dependencies."""
        try:
            from aimo.mathlib_calculator import MathLibCalculator
            self._calculator = MathLibCalculator(verbose=False)
        except ImportError:
            pass

        try:
            from aimo.execution_engine import CodeExecutor
            self._code_executor = CodeExecutor(timeout=5.0, verbose=False)
        except ImportError:
            pass

    def verify(
        self,
        answer: int,
        problem_text: str,
        features: Any = None,
        reasoning: str = "",
    ) -> VerificationResult:
        """
        Verify an answer through multiple checks.

        Args:
            answer: The proposed integer answer
            problem_text: Original problem text
            features: ProblemFeatures (optional)
            reasoning: LLM reasoning trace (optional)

        Returns:
            VerificationResult with detailed check results
        """
        checks_passed = 0
        checks_total = 0
        details = []

        # Check 1: Range [0, 99999]
        checks_total += 1
        if self._check_range(answer):
            checks_passed += 1
            details.append("PASS: range [0, 99999]")
        else:
            details.append(f"FAIL: range check (got {answer})")

        # Check 2: Domain-specific sanity
        checks_total += 1
        domain_ok, domain_msg = self._check_domain_sanity(answer, problem_text, features)
        if domain_ok:
            checks_passed += 1
            details.append(f"PASS: domain sanity ({domain_msg})")
        else:
            details.append(f"FAIL: domain sanity ({domain_msg})")

        # Check 3: Code execution verification
        if reasoning and self._code_executor is not None:
            code_result = self._check_code_execution(reasoning)
            if code_result is not None:
                checks_total += 1
                if code_result == answer:
                    checks_passed += 1
                    details.append("PASS: code execution matches")
                else:
                    details.append(f"FAIL: code execution gives {code_result}, expected {answer}")

        # Check 4: Pattern match cross-check
        if features is not None and getattr(features, 'is_direct_solvable', False):
            pattern_result = self._check_pattern_match(problem_text, features)
            if pattern_result is not None:
                checks_total += 1
                if pattern_result == answer:
                    checks_passed += 1
                    details.append("PASS: pattern match cross-check")
                else:
                    details.append(f"FAIL: pattern gives {pattern_result}, got {answer}")

        confidence = checks_passed / checks_total if checks_total > 0 else 0.0

        if self.verbose:
            for d in details:
                print(f"  [Verifier] {d}", file=sys.stderr)

        return VerificationResult(
            answer=answer,
            confidence=confidence,
            method="multi_check",
            checks_passed=checks_passed,
            checks_total=checks_total,
            details=details,
        )

    def _check_range(self, answer: int) -> bool:
        """Check if answer is in valid AIMO range [0, 99999]."""
        return 0 <= answer <= 99999

    def _check_domain_sanity(
        self,
        answer: int,
        problem_text: str,
        features: Any = None,
    ) -> tuple:
        """
        Domain-specific sanity checks.

        Returns:
            (passed: bool, message: str)
        """
        text_lower = problem_text.lower()

        # Counting problems should have positive answers
        if re.search(r'how many|count|number of', text_lower):
            if answer < 0:
                return False, "counting result should be non-negative"
            return True, "counting >= 0"

        # Remainder should be less than modulus
        mod_match = re.search(r'mod(?:ulo)?\s+(\d+)|divided\s+by\s+(\d+)', text_lower)
        if mod_match:
            modulus = int(mod_match.group(1) or mod_match.group(2))
            if 'remainder' in text_lower and answer >= modulus:
                return False, f"remainder {answer} >= modulus {modulus}"
            return True, f"remainder < modulus ({modulus})"

        # Probability numerator should be reasonable
        if re.search(r'probability', text_lower):
            if answer < 0:
                return False, "probability numerator should be non-negative"
            return True, "probability >= 0"

        # Digit problems
        if re.search(r'digit', text_lower):
            if answer < 0:
                return False, "digit count should be non-negative"
            return True, "digit sanity ok"

        return True, "no specific domain check"

    def _check_code_execution(self, reasoning: str) -> Optional[int]:
        """
        Execute code blocks from reasoning and return result.

        Returns:
            Integer result from code, or None if no code or execution failed
        """
        if self._code_executor is None:
            return None

        blocks = self._code_executor.extract_code_blocks(reasoning)
        if not blocks:
            return None

        for code in blocks:
            success, result, _ = self._code_executor.execute_safely(code, timeout=5.0)
            if success and result is not None:
                try:
                    return int(result)
                except (ValueError, TypeError):
                    continue

        return None

    def _check_pattern_match(self, problem_text: str, features: Any) -> Optional[int]:
        """
        Cross-check with pattern-based solver.

        Returns:
            Integer result from pattern matching, or None
        """
        if self._calculator is None:
            return None

        compute_func = getattr(features, 'direct_compute_func', None)
        if compute_func is None:
            return None

        try:
            from aimo.aimo3_solver import ParameterExtractor
            params = ParameterExtractor.extract(problem_text, compute_func)
            result = self._calculator.compute(compute_func, params)
            return result
        except Exception:
            return None
