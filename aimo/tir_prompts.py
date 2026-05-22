"""
TIR Prompts - Tool-Integrated Reasoning prompt templates.

System prompts and few-shot examples that teach the LLM to:
1. Think step by step
2. Write Python code in ```python blocks when computation is needed
3. Read code output from ```output blocks
4. Continue reasoning based on output
5. End with \\boxed{answer}
"""

# System prompt for TIR mode
TIR_SYSTEM_PROMPT = """\
You are an expert mathematician solving competition-level math problems.

IMPORTANT RULES:
- Think step by step, showing your mathematical reasoning clearly.
- When you need to compute, verify, or explore, write Python code in a ```python block.
- After each code block, you will see the execution result in a ```output block.
- Use the output to continue your reasoning.
- You may write multiple code blocks as needed.
- Your final answer MUST be a non-negative integer.
- Put your final answer inside \\boxed{}.
- Available Python modules: math, itertools, functools, collections, fractions, decimal, statistics, re, copy, bisect, heapq, random, string, operator.
- Do NOT import numpy, scipy, sympy, or any other external library.

STRATEGY:
- Start by understanding what the problem asks.
- Try small cases first to build intuition.
- Write code to verify your reasoning or brute-force when feasible.
- For counting problems, write code to enumerate and count.
- For number theory, use modular arithmetic in code.
- Double-check your answer with a different method if possible.
"""

# Domain-specific additions to system prompt
DOMAIN_HINTS = {
    "number_theory": (
        "\nFor this number theory problem, consider:\n"
        "- Modular arithmetic and Chinese Remainder Theorem\n"
        "- Prime factorization\n"
        "- Euler's totient and Fermat's little theorem\n"
        "- Try computing for small cases to find patterns\n"
    ),
    "algebra": (
        "\nFor this algebra problem, consider:\n"
        "- Vieta's formulas for polynomial roots\n"
        "- Substitution to simplify expressions\n"
        "- Newton's identities for power sums\n"
        "- Verify with code by plugging in computed values\n"
    ),
    "combinatorics": (
        "\nFor this combinatorics problem, consider:\n"
        "- Direct counting with multiplication principle\n"
        "- Inclusion-exclusion\n"
        "- Generating functions\n"
        "- Write code to enumerate small cases or verify formulas\n"
    ),
    "geometry": (
        "\nFor this geometry problem, consider:\n"
        "- Coordinate geometry (set up coordinates, compute algebraically)\n"
        "- Trigonometry (law of sines, cosines)\n"
        "- Use code for numerical computation with exact arithmetic (fractions)\n"
    ),
    "probability": (
        "\nFor this probability problem, consider:\n"
        "- Count favorable outcomes / total outcomes\n"
        "- Conditional probability and Bayes' theorem\n"
        "- Use code to simulate or enumerate outcomes\n"
    ),
}


# Few-shot examples for TIR
# Each example shows the full TIR loop: reasoning -> code -> output -> reasoning -> answer
FEW_SHOT_EXAMPLES = {
    "number_theory": """\
Problem: Find the number of integers between 1 and 1000 (inclusive) that can be expressed as the difference of two perfect squares.

A number n can be written as a^2 - b^2 = (a+b)(a-b). Let me think about which numbers have this property.

If n is odd, say n = 2k+1, then n = (k+1)^2 - k^2. So all odd numbers work.
If n is divisible by 4, say n = 4m, then n = (m+1)^2 - (m-1)^2. So multiples of 4 work.
If n = 2 mod 4, then n = 2(2j+1) for some j. We need (a+b)(a-b) = n where a+b and a-b have the same parity. Since n = 2 mod 4, one factor is even and one odd, which is impossible. So n = 2 mod 4 does NOT work.

Let me verify and count with code:

```python
count = 0
for n in range(1, 1001):
    found = False
    for a in range(1, n + 1):
        for b in range(0, a):
            if a*a - b*b == n:
                found = True
                break
        if found:
            break
    if found:
        count += 1
print(count)
```

```output
750
```

The code confirms: 750 numbers between 1 and 1000 can be expressed as the difference of two perfect squares. These are exactly the odd numbers (500) plus the multiples of 4 (250).

\\boxed{750}
""",

    "algebra": """\
Problem: The quadratic x^2 - 5x + 6 = 0 has roots r1 and r2. Find the value of r1^2 + r2^2.

By Vieta's formulas:
- r1 + r2 = 5
- r1 * r2 = 6

We know that r1^2 + r2^2 = (r1 + r2)^2 - 2*r1*r2.

```python
sum_roots = 5
prod_roots = 6
sum_squares = sum_roots**2 - 2*prod_roots
print(sum_squares)
```

```output
13
```

Therefore r1^2 + r2^2 = 5^2 - 2(6) = 25 - 12 = 13.

\\boxed{13}
""",

    "combinatorics": """\
Problem: How many 3-digit numbers have all distinct digits?

A 3-digit number has digits d1 d2 d3 where d1 is from 1-9 and d2, d3 are from 0-9.
- d1: 9 choices (1 through 9, cannot be 0)
- d2: 9 choices (0 through 9, minus d1)
- d3: 8 choices (0 through 9, minus d1 and d2)

```python
import itertools
count = sum(1 for p in itertools.permutations(range(10), 3) if p[0] != 0)
print(count)
```

```output
648
```

By the multiplication principle: 9 * 9 * 8 = 648. The code confirms.

\\boxed{648}
""",

    "geometry": """\
Problem: A circle has radius 5. A chord is at distance 3 from the center. Find the length of the chord.

Let r = 5 (radius) and d = 3 (distance from center to chord).
By the Pythagorean theorem, if half the chord length is h, then:
r^2 = d^2 + h^2
h^2 = r^2 - d^2 = 25 - 9 = 16
h = 4

The full chord length is 2h = 8.

```python
import math
r = 5
d = 3
half_chord = math.sqrt(r**2 - d**2)
chord = 2 * half_chord
print(int(chord))
```

```output
8
```

\\boxed{8}
""",

    "general": """\
Problem: Find the smallest perfect cube that is divisible by 12.

12 = 2^2 * 3. For a perfect cube divisible by 12, each prime factor must appear at least as many times as in 12, and the total exponent must be a multiple of 3.
- For 2: need at least 2, round up to 3 (next multiple of 3)
- For 3: need at least 1, round up to 3 (next multiple of 3)

So the smallest perfect cube divisible by 12 is 2^3 * 3^3 = 8 * 27 = 216.

```python
# Verify by checking all cubes
n = 1
while True:
    cube = n ** 3
    if cube % 12 == 0:
        print(cube)
        break
    n += 1
```

```output
216
```

\\boxed{216}
""",
}


def build_tir_prompt(problem_text: str, domain: str = "general") -> str:
    """
    Build a complete TIR prompt for a problem.

    Args:
        problem_text: The math problem text
        domain: Problem domain for selecting hints and examples

    Returns:
        Complete prompt string ready for LLM
    """
    parts = [TIR_SYSTEM_PROMPT]

    # Add domain hint
    domain_lower = domain.lower()
    if domain_lower in DOMAIN_HINTS:
        parts.append(DOMAIN_HINTS[domain_lower])

    # Add few-shot example
    example_key = domain_lower if domain_lower in FEW_SHOT_EXAMPLES else "general"
    parts.append("\nHere is an example of how to solve a problem:\n")
    parts.append(FEW_SHOT_EXAMPLES[example_key])

    # Add the actual problem
    parts.append(f"\nNow solve this problem:\n\nProblem: {problem_text}\n")

    return "\n".join(parts)


def build_tir_messages(problem_text: str, domain: str = "general") -> list:
    """
    Build TIR prompt as chat messages (for chat completion APIs).

    Args:
        problem_text: The math problem text
        domain: Problem domain

    Returns:
        List of message dicts [{role, content}, ...]
    """
    system = TIR_SYSTEM_PROMPT
    domain_lower = domain.lower()
    if domain_lower in DOMAIN_HINTS:
        system += DOMAIN_HINTS[domain_lower]

    # Build user message with example + problem
    example_key = domain_lower if domain_lower in FEW_SHOT_EXAMPLES else "general"
    user_content = (
        f"Here is an example of how to solve a problem:\n\n"
        f"{FEW_SHOT_EXAMPLES[example_key]}\n\n"
        f"Now solve this problem:\n\nProblem: {problem_text}\n"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
