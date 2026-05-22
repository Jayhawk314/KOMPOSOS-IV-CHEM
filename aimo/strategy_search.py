"""
Strategy Search - LLM Strategy Selection with Domain-Specific Prompts.

Selects and prioritizes LLM prompt strategies based on problem classification.
"""

import sys
sys.path.insert(0, '.')

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re


# =============================================================================
# LLM STRATEGY SYSTEM
# =============================================================================

@dataclass
class LLMStrategy:
    """An LLM-based problem-solving strategy with a prompt template."""
    name: str
    domain: str  # "algebra", "number_theory", "combinatorics", "geometry", "probability", "general"
    prompt_template: str
    priority: float = 1.0


# Math expert preamble injected into every strategy prompt
_MATH_PREAMBLE = (
    "You are an expert mathematician solving an olympiad-level competition problem. "
    "Give your final integer answer inside \\boxed{{}}. "
    "If you write Python code to verify, put it in a ```python block.\n\n"
)

# Domain-specific prompt templates for LLM strategies
# Every template includes {theorem_context} (may be empty) and {problem}.
STRATEGY_PROMPTS: Dict[str, Dict[str, str]] = {
    "algebra": {
        "substitution": (
            _MATH_PREAMBLE +
            "Solve this algebra problem using substitution.\n"
            "Look for variables that can be expressed in terms of others.\n"
            "Substitute to reduce the number of unknowns, then solve.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "vieta": (
            _MATH_PREAMBLE +
            "Solve this using Vieta's formulas.\n"
            "If we have a polynomial with roots r1, r2, ..., express the desired quantity "
            "in terms of elementary symmetric polynomials of the roots.\n"
            "Recall: for x^2 - sx + p = 0, r1+r2=s, r1*r2=p.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "generating_functions": (
            _MATH_PREAMBLE +
            "Solve this using generating functions.\n"
            "Set up the generating function for the sequence or counting problem, "
            "extract the relevant coefficient.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "invariant": (
            _MATH_PREAMBLE +
            "Solve this by finding an algebraic invariant.\n"
            "Look for a quantity that is preserved under the operations described. "
            "Use the invariant to constrain or determine the answer.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "inequality": (
            _MATH_PREAMBLE +
            "Solve this using inequality techniques.\n"
            "Consider AM-GM, Cauchy-Schwarz, Power Mean, Schur's inequality, or "
            "other standard inequality bounds.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
    "number_theory": {
        "modular_arithmetic": (
            _MATH_PREAMBLE +
            "Solve this number theory problem using modular arithmetic.\n"
            "Reduce the problem modulo appropriate values. "
            "Look for patterns in residues.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "prime_factorization": (
            _MATH_PREAMBLE +
            "Solve this by analyzing the prime factorization.\n"
            "Factor the relevant numbers and use properties of prime factorizations "
            "(multiplicativity, divisor counts, etc.).\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "crt": (
            _MATH_PREAMBLE +
            "Solve this using the Chinese Remainder Theorem.\n"
            "Decompose the modulus into coprime factors, solve each congruence "
            "separately, then combine.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "multiplicative_functions": (
            _MATH_PREAMBLE +
            "Solve this using properties of multiplicative functions.\n"
            "Consider Euler's totient, divisor function, Mobius function, etc.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "p_adic": (
            _MATH_PREAMBLE +
            "Solve this using p-adic valuation (v_p).\n"
            "Track the exact power of each prime dividing the relevant expressions. "
            "Use Lifting the Exponent Lemma if applicable.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
    "combinatorics": {
        "direct_counting": (
            _MATH_PREAMBLE +
            "Solve this combinatorics problem by direct counting.\n"
            "Break the counting into cases, use multiplication/addition principles.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "inclusion_exclusion": (
            _MATH_PREAMBLE +
            "Solve this using inclusion-exclusion.\n"
            "Identify the sets, compute individual sizes and intersections, "
            "then apply the inclusion-exclusion formula.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "bijection": (
            _MATH_PREAMBLE +
            "Solve this by finding a bijection.\n"
            "Map the objects being counted to another set that is easier to count. "
            "Verify the mapping is a bijection.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "gen_func_comb": (
            _MATH_PREAMBLE +
            "Solve this combinatorics problem using generating functions.\n"
            "Set up the generating function, multiply/compose as needed, "
            "extract the relevant coefficient.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "extremal": (
            _MATH_PREAMBLE +
            "Solve this using the extremal principle.\n"
            "Consider the extremal (maximum or minimum) element and derive "
            "constraints or contradictions.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
    "geometry": {
        "coordinate": (
            _MATH_PREAMBLE +
            "Solve this geometry problem using coordinates.\n"
            "Set up a coordinate system, express the given conditions as equations, "
            "and solve algebraically.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "trigonometric": (
            _MATH_PREAMBLE +
            "Solve this using trigonometry.\n"
            "Use law of sines, law of cosines, or trigonometric identities.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "synthetic": (
            _MATH_PREAMBLE +
            "Solve this using synthetic geometry.\n"
            "Look for similar triangles, cyclic quadrilaterals, power of a point, "
            "angle chasing, or other classical constructions.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "inversion": (
            _MATH_PREAMBLE +
            "Solve this using circle inversion.\n"
            "Choose an appropriate center and radius of inversion, "
            "transform the configuration, solve in the inverted plane.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "area_method": (
            _MATH_PREAMBLE +
            "Solve this using area methods.\n"
            "Express the desired quantity in terms of areas. "
            "Use ratios of areas to find lengths or angles.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
    "probability": {
        "counting_outcomes": (
            _MATH_PREAMBLE +
            "Solve this probability problem by counting outcomes.\n"
            "Enumerate the sample space, count favorable outcomes, "
            "compute the probability as favorable/total.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "conditional": (
            _MATH_PREAMBLE +
            "Solve this using conditional probability.\n"
            "Use Bayes' theorem or the law of total probability. "
            "Condition on appropriate events.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "expected_value": (
            _MATH_PREAMBLE +
            "Solve this by computing the expected value.\n"
            "Use linearity of expectation. Break into indicator random variables "
            "if helpful.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "recursion_prob": (
            _MATH_PREAMBLE +
            "Solve this probability problem using recursion.\n"
            "Set up a recurrence relation for the probability and solve it.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
    "general": {
        "systematic": (
            _MATH_PREAMBLE +
            "Solve this step by step with careful reasoning.\n"
            "1. Identify what is being asked\n"
            "2. Note all given conditions\n"
            "3. Choose an approach\n"
            "4. Execute carefully\n"
            "5. Verify the answer\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "small_cases": (
            _MATH_PREAMBLE +
            "Solve this by examining small cases first.\n"
            "Compute the answer for small values of the parameters, "
            "identify a pattern, then prove or apply it.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
        "code_verify": (
            _MATH_PREAMBLE +
            "Solve this problem. Write Python code to verify your answer.\n"
            "Show the mathematical reasoning, then include a ```python code block "
            "that computes the answer numerically.\n\n"
            "{theorem_context}\n"
            "Problem: {problem}\n\nSolution:"
        ),
    },
}


def _get_domain_strategies(domain: str) -> Dict[str, str]:
    """Get strategy prompts for a domain, with general fallbacks."""
    prompts = dict(STRATEGY_PROMPTS.get("general", {}))
    prompts.update(STRATEGY_PROMPTS.get(domain, {}))
    return prompts


def select_llm_strategies(
    features: Any,
    problem_text: str,
    beam_width: int = 8,
) -> List[LLMStrategy]:
    """
    Select LLM strategies based on problem features.

    Args:
        features: ProblemFeatures from ProblemClassifier
        problem_text: Original problem text
        beam_width: Maximum number of strategies to return

    Returns:
        List of LLMStrategy objects, ordered by priority
    """
    domain_name = features.domain.name.lower()
    strategies: List[LLMStrategy] = []

    # Primary domain strategies
    domain_prompts = _get_domain_strategies(domain_name)
    for name, template in domain_prompts.items():
        strategies.append(LLMStrategy(
            name=name,
            domain=domain_name,
            prompt_template=template,
            priority=1.0 if name in STRATEGY_PROMPTS.get(domain_name, {}) else 0.5,
        ))

    # Add cross-domain strategies for sub-domains
    for sub in getattr(features, 'sub_domains', []):
        sub_name = sub.name.lower()
        if sub_name != domain_name:
            sub_prompts = STRATEGY_PROMPTS.get(sub_name, {})
            for name, template in sub_prompts.items():
                strategies.append(LLMStrategy(
                    name=f"{sub_name}_{name}",
                    domain=sub_name,
                    prompt_template=template,
                    priority=0.6,
                ))

    # Sort by priority (highest first), then truncate
    strategies.sort(key=lambda s: s.priority, reverse=True)
    return strategies[:beam_width]


def score_strategy_response(
    strategy: LLMStrategy,
    response: str,
    features: Any,
) -> float:
    """
    Score an LLM response for a given strategy.

    Heuristic scoring based on:
    - Presence of boxed answer (0.3)
    - Presence of code blocks (0.2)
    - Length and structure of reasoning (0.2)
    - Presence of verification step (0.15)
    - Confidence language (0.15)

    Returns:
        Score in [0, 1]
    """
    score = 0.0

    # Has boxed answer
    if re.search(r'\\boxed\{(\d+)\}', response):
        score += 0.3

    # Has code verification
    if '```python' in response:
        score += 0.2

    # Reasoning length (between 100 and 2000 chars is good)
    length = len(response)
    if 100 <= length <= 2000:
        score += 0.2
    elif length > 50:
        score += 0.1

    # Has verification step
    if re.search(r'verify|check|confirm|indeed|we can confirm', response, re.IGNORECASE):
        score += 0.15

    # Confidence language
    if re.search(r'therefore|thus|hence|so the answer|the answer is', response, re.IGNORECASE):
        score += 0.15

    return min(1.0, score)
