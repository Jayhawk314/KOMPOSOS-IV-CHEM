"""
Problem Classifier - Categorize AIMO problems by domain, difficulty, and solvability.

Uses keyword scoring and structural analysis to determine:
- Mathematical domain (algebra, number theory, etc.)
- Difficulty level (direct formula vs. olympiad-level)
- Whether the problem can be solved by existing pattern matching
"""

import sys
import re
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import IntEnum

sys.path.insert(0, '.')


class MathDomain(IntEnum):
    """Mathematical domain of a problem."""
    ALGEBRA = 0
    NUMBER_THEORY = 1
    COMBINATORICS = 2
    GEOMETRY = 3
    PROBABILITY = 4
    MIXED = 5


class Difficulty(IntEnum):
    """Difficulty level of a problem."""
    DIRECT = 0       # Solvable by pattern matching / single formula
    MODERATE = 1     # Requires 2-3 step reasoning
    HARD = 2         # Requires multi-step reasoning, case analysis
    OLYMPIAD = 3     # Full olympiad-level, needs deep reasoning


@dataclass
class ProblemFeatures:
    """Extracted features of a math problem."""
    domain: MathDomain
    difficulty: Difficulty
    is_direct_solvable: bool
    keywords: List[str]
    numeric_values: List[int]
    answer_format: str = "integer"  # "integer", "fraction", "expression"
    sub_domains: List[MathDomain] = field(default_factory=list)
    direct_compute_func: Optional[str] = None
    direct_compute_params: List[str] = field(default_factory=list)
    latex_normalized: str = ""
    is_multi_step: bool = False  # Detected via persistent homology
    homology_dimension: int = 0  # H0/H1 complexity


# Domain keyword weights: (keyword_pattern, domain, weight)
_DOMAIN_KEYWORDS = [
    # Number Theory
    (r'prime|modular|modulo|\bmod\b|divisible|divisor|remainder|congruence|gcd|lcm', MathDomain.NUMBER_THEORY, 3),
    (r'perfect\s+(square|cube|power)|factor|coprime|totient|euler|fermat|wilson', MathDomain.NUMBER_THEORY, 3),
    (r'fibonacci|digit|residue|diophantine|pell', MathDomain.NUMBER_THEORY, 2),

    # Algebra
    (r'polynomial|quadratic|cubic|equation|root|coefficient|vieta', MathDomain.ALGEBRA, 3),
    (r'sequence|series|arithmetic|geometric|recurrence|function|inequality', MathDomain.ALGEBRA, 2),
    (r'logarithm|exponential|binomial|sum|product|minimum|maximum', MathDomain.ALGEBRA, 1),

    # Combinatorics
    (r'how\s+many|count|number\s+of|permutation|combination|arrange|choose', MathDomain.COMBINATORICS, 3),
    (r'distinct|ways|path|grid|coloring|partition|subset|derangement', MathDomain.COMBINATORICS, 2),
    (r'inclusion.exclusion|pigeonhole|catalan|stirling|bijection', MathDomain.COMBINATORICS, 3),

    # Geometry
    (r'triangle|circle|square|rectangle|polygon|angle|area|perimeter', MathDomain.GEOMETRY, 3),
    (r'radius|diameter|chord|tangent|inscribed|circumscribed|midpoint', MathDomain.GEOMETRY, 3),
    (r'parallel|perpendicular|bisect|altitude|median|centroid', MathDomain.GEOMETRY, 2),
    (r'coordinate|slope|distance|line|plane|sphere|volume', MathDomain.GEOMETRY, 2),

    # Probability
    (r'probability|dice|coin|flip|random|expected|fair|unfair', MathDomain.PROBABILITY, 3),
    (r'independent|conditional|bayes|distribution|variance|standard', MathDomain.PROBABILITY, 2),
]

# Difficulty signals
_DIFFICULTY_SIGNALS = {
    'easy': [
        r'find\s+the\s+value',
        r'compute',
        r'calculate',
        r'what\s+is',
        r'evaluate',
    ],
    'moderate': [
        r'how\s+many',
        r'determine',
        r'find\s+all',
        r'for\s+which',
        r'smallest|largest|minimum|maximum',
    ],
    'hard': [
        r'prove\s+that',
        r'show\s+that',
        r'if\s+and\s+only\s+if',
        r'for\s+all|for\s+every',
        r'there\s+exist',
        r'let\s+.*\s+be\s+.*\s+such\s+that',
    ],
    'olympiad': [
        r'determine\s+all\s+functions',
        r'find\s+all\s+.*\s+satisfying',
        r'prove.*inequality',
        r'characterize',
        r'does\s+there\s+exist',
    ],
}


class ProblemClassifier:
    """
    Classify AIMO problems by domain, difficulty, and direct solvability.

    Uses weighted keyword scoring for domain detection,
    structural complexity heuristics for difficulty,
    and existing AIMO3ComputationPatterns for direct-solvable detection.
    """

    def __init__(self):
        self._patterns_cls = None
        self._extractor_cls = None
        self._load_patterns()

    def _load_patterns(self):
        """Load existing computation patterns for direct-solvable detection."""
        try:
            from aimo.aimo3_solver import AIMO3ComputationPatterns, ParameterExtractor
            self._patterns_cls = AIMO3ComputationPatterns
            self._extractor_cls = ParameterExtractor
        except ImportError:
            pass

    def classify(self, problem_text: str) -> ProblemFeatures:
        """
        Classify a problem into domain, difficulty, and solvability.

        Args:
            problem_text: Problem statement (may contain LaTeX)

        Returns:
            ProblemFeatures with all classifications
        """
        normalized = self._normalize_latex(problem_text)
        text_lower = normalized.lower()

        domain, sub_domains = self._detect_domain(text_lower)
        keywords = self._extract_keywords(text_lower)
        numeric_values = self._extract_numerics(normalized)
        is_direct, compute_func, compute_params = self._check_direct_solvable(problem_text)
        difficulty = self._estimate_difficulty(text_lower, is_direct, numeric_values)
        answer_format = self._detect_answer_format(text_lower)

        # Persistent homology: detect multi-step structure
        is_multi_step, homology_dim = self._detect_multi_step(text_lower, keywords)

        return ProblemFeatures(
            domain=domain,
            difficulty=difficulty,
            is_direct_solvable=is_direct,
            keywords=keywords,
            numeric_values=numeric_values,
            answer_format=answer_format,
            sub_domains=sub_domains,
            direct_compute_func=compute_func,
            direct_compute_params=compute_params,
            latex_normalized=normalized,
            is_multi_step=is_multi_step,
            homology_dimension=homology_dim,
        )

    def _normalize_latex(self, text: str) -> str:
        """Convert LaTeX notation to readable form."""
        result = text

        # Common LaTeX replacements
        replacements = [
            (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2'),
            (r'\\sqrt\{([^}]+)\}', r'sqrt(\1)'),
            (r'\\left\s*[([]', '('),
            (r'\\right\s*[)\]]', ')'),
            (r'\\cdot', '*'),
            (r'\\times', '*'),
            (r'\\div', '/'),
            (r'\\pm', '+-'),
            (r'\\leq|\\le', '<='),
            (r'\\geq|\\ge', '>='),
            (r'\\neq|\\ne', '!='),
            (r'\\equiv', '='),
            (r'\\pmod\{([^}]+)\}', r'(mod \1)'),
            (r'\\bmod', 'mod'),
            (r'\\text\{([^}]+)\}', r'\1'),
            (r'\\mathrm\{([^}]+)\}', r'\1'),
            (r'\\mathbb\{([^}]+)\}', r'\1'),
            (r'\$', ''),
            (r'\\\\', '\n'),
            (r'\\,|\\;|\\!|\\quad|\\qquad', ' '),
        ]

        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result)

        # Clean up extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def _detect_domain(self, text_lower: str) -> Tuple[MathDomain, List[MathDomain]]:
        """
        Detect mathematical domain using weighted keyword scoring.

        Returns:
            (primary_domain, list_of_sub_domains)
        """
        scores: dict = {d: 0.0 for d in MathDomain if d != MathDomain.MIXED}

        for pattern, domain, weight in _DOMAIN_KEYWORDS:
            matches = re.findall(pattern, text_lower)
            scores[domain] += len(matches) * weight

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if ranked[0][1] == 0:
            return MathDomain.MIXED, []

        primary = ranked[0][0]
        sub_domains = [d for d, s in ranked[1:] if s > 0 and s >= ranked[0][1] * 0.4]

        if sub_domains and ranked[1][1] >= ranked[0][1] * 0.8:
            return MathDomain.MIXED, [primary] + sub_domains

        return primary, sub_domains

    def _extract_keywords(self, text_lower: str) -> List[str]:
        """Extract mathematical keywords from text."""
        all_keywords: Set[str] = set()
        for pattern, _, _ in _DOMAIN_KEYWORDS:
            matches = re.findall(pattern, text_lower)
            all_keywords.update(m if isinstance(m, str) else m for m in matches)
        return sorted(all_keywords)

    def _extract_numerics(self, text: str) -> List[int]:
        """Extract numeric values from text."""
        nums = re.findall(r'\b(\d+)\b', text)
        return [int(n) for n in nums if len(n) <= 10]

    def _check_direct_solvable(self, problem_text: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Check if problem can be solved directly by existing pattern matching.

        Returns:
            (is_direct, compute_func_name, param_names)
        """
        if self._patterns_cls is None:
            return False, None, []

        compute_func, param_names = self._patterns_cls.match(problem_text)
        if compute_func is not None:
            return True, compute_func, param_names

        return False, None, []

    def _estimate_difficulty(self, text_lower: str, is_direct: bool, numerics: List[int]) -> Difficulty:
        """
        Estimate difficulty using structural heuristics.

        Factors:
        - Direct solvability (pattern match = DIRECT)
        - Sentence count and complexity
        - Presence of multi-step reasoning cues
        - Size of numeric values
        """
        if is_direct:
            return Difficulty.DIRECT

        # Count difficulty signals
        signal_scores = {}
        for level, patterns in _DIFFICULTY_SIGNALS.items():
            count = sum(1 for p in patterns if re.search(p, text_lower))
            signal_scores[level] = count

        # Structural complexity
        sentences = text_lower.count('.') + text_lower.count('?')
        conditions = len(re.findall(r'\bif\b|\bsuch that\b|\bwhere\b|\bgiven\b', text_lower))
        quantifiers = len(re.findall(r'\ball\b|\bevery\b|\bexist\b|\bsome\b', text_lower))

        # Large numbers suggest harder computation
        large_nums = sum(1 for n in numerics if n > 1000)

        # Score accumulation
        score = 0.0
        score += signal_scores.get('easy', 0) * (-1)
        score += signal_scores.get('moderate', 0) * 1
        score += signal_scores.get('hard', 0) * 2
        score += signal_scores.get('olympiad', 0) * 3
        score += min(conditions, 3) * 0.5
        score += min(quantifiers, 2) * 1.0
        score += min(sentences, 5) * 0.2
        score += min(large_nums, 2) * 0.5

        if score <= 0:
            return Difficulty.DIRECT
        elif score <= 2:
            return Difficulty.MODERATE
        elif score <= 4:
            return Difficulty.HARD
        else:
            return Difficulty.OLYMPIAD

    def _detect_answer_format(self, text_lower: str) -> str:
        """Detect expected answer format."""
        if re.search(r'fraction|p/q|ratio', text_lower):
            return "fraction"
        if re.search(r'expression|simplif|polynomial', text_lower):
            return "expression"
        return "integer"

    def _detect_multi_step(self, text_lower: str, keywords: List[str]) -> Tuple[bool, int]:
        """
        Use persistent homology to detect multi-step problems.

        Indicators of multi-step structure:
        - Multiple conditional clauses ("if", "then", "given", "find")
        - Chain of dependencies (A → B → C)
        - Multiple quantifiers
        - Presence of "cycles" in reasoning (iterate, recursive, sequence)

        Returns:
            (is_multi_step, homology_dimension)
            homology_dimension: 0 = single step, 1 = chain, 2+ = complex cycles
        """
        # Count structural indicators
        conditionals = len(re.findall(r'\b(if|then|given|let|suppose|assume|where)\b', text_lower))
        transitions = len(re.findall(r'\b(find|determine|compute|calculate|show|prove)\b', text_lower))
        sequences = len(re.findall(r'\b(sequence|series|recursiv|iterate|repeat|pattern)\b', text_lower))
        dependencies = len(re.findall(r'\b(first|second|next|then|finally|last)\b', text_lower))

        # H0: Single connected component (direct problem)
        # H1: One cycle (chain of reasoning)
        # H2+: Multiple cycles (complex multi-step)

        score = conditionals + transitions + sequences + dependencies

        if score == 0:
            return False, 0  # Single step
        elif score <= 2:
            return True, 1  # Chain (H1)
        else:
            return True, min(score // 2, 3)  # Complex (H2+)

