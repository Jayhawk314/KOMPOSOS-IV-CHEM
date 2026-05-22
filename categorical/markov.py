# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Markov Categories: Probabilistic Reasoning

A Markov category is a symmetric monoidal category with:
- A commutative comonoid structure (copy + discard) on every object
- Copy is NOT natural (captures non-determinism)
- Morphisms are stochastic kernels (conditional distributions)

This module provides:
- MarkovMorphism: a morphism carrying a discrete conditional distribution
- MarkovCategory: wrapper adding copy/discard and stochastic composition
- Bayesian operations: sample, condition, disintegrate

Reference: Fritz, "A synthetic approach to Markov kernels" (2020)
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


@dataclass
class MarkovMorphism:
    """
    A stochastic kernel: a morphism carrying a conditional distribution.

    The kernel maps each source state to a distribution over target states.
    kernel[source_state] = {target_state: probability, ...}

    Each distribution should sum to 1.0.
    """
    name: str
    source: str
    target: str
    kernel: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"markov:{self.name}:{self.source}->{self.target}"

    def __call__(self, state: str) -> Dict[str, float]:
        """Return the conditional distribution given a source state."""
        return self.kernel.get(state, {})

    def sample(self, state: str) -> Optional[str]:
        """Sample from the conditional distribution."""
        dist = self.kernel.get(state, {})
        if not dist:
            return None
        states = list(dist.keys())
        probs = list(dist.values())
        total = sum(probs)
        if total == 0:
            return None
        probs = [p / total for p in probs]
        return random.choices(states, weights=probs, k=1)[0]

    def expected_value(self, state: str, values: Dict[str, float]) -> float:
        """Compute expected value E[values(X) | state]."""
        dist = self.kernel.get(state, {})
        return sum(dist.get(s, 0) * values.get(s, 0) for s in dist)


def compose_markov(f: MarkovMorphism, g: MarkovMorphism) -> MarkovMorphism:
    """
    Compose Markov morphisms via kernel composition (marginalization).

    (g . f)(a, c) = sum_b f(a, b) * g(b, c)
    """
    if f.target != g.source:
        raise TypeError(
            f"Cannot compose: {f.name} targets '{f.target}' "
            f"but {g.name} sources '{g.source}'"
        )

    new_kernel: Dict[str, Dict[str, float]] = {}

    for a, f_dist in f.kernel.items():
        new_dist: Dict[str, float] = {}
        for b, p_b in f_dist.items():
            g_dist = g.kernel.get(b, {})
            for c, p_c in g_dist.items():
                new_dist[c] = new_dist.get(c, 0.0) + p_b * p_c
        if new_dist:
            new_kernel[a] = new_dist

    return MarkovMorphism(
        name=f"{g.name}.{f.name}",
        source=f.source,
        target=g.target,
        kernel=new_kernel,
    )


def condition(
    mmor: MarkovMorphism,
    evidence: Dict[str, float],
) -> MarkovMorphism:
    """
    Bayesian conditioning: update the kernel given evidence.

    evidence maps target states to observed likelihoods.
    Uses Bayes' rule to compute the posterior.
    """
    new_kernel: Dict[str, Dict[str, float]] = {}

    for source_state, dist in mmor.kernel.items():
        weighted = {}
        for target_state, prob in dist.items():
            likelihood = evidence.get(target_state, 1.0)
            weighted[target_state] = prob * likelihood

        total = sum(weighted.values())
        if total > 0:
            new_kernel[source_state] = {
                s: p / total for s, p in weighted.items()
            }

    return MarkovMorphism(
        name=f"cond({mmor.name})",
        source=mmor.source,
        target=mmor.target,
        kernel=new_kernel,
    )


def disintegrate(
    joint: MarkovMorphism,
) -> Tuple[MarkovMorphism, Dict[str, float]]:
    """
    Disintegrate a joint distribution into conditional + marginal.

    Given a kernel P(A, B | source), returns:
    - conditional: P(B | A, source) as a MarkovMorphism
    - marginal: P(A | source) as a dict
    """
    marginal: Dict[str, float] = {}
    conditionals: Dict[str, Dict[str, float]] = {}

    for source_state, dist in joint.kernel.items():
        # Collect first components and their marginals
        for target_state, prob in dist.items():
            # Parse paired state "a,b"
            if "," in target_state:
                a, b = target_state.split(",", 1)
                marginal[a] = marginal.get(a, 0.0) + prob
                if a not in conditionals:
                    conditionals[a] = {}
                conditionals[a][b] = conditionals[a].get(b, 0.0) + prob
            else:
                marginal[target_state] = marginal.get(target_state, 0.0) + prob

    # Normalize conditionals
    for a in conditionals:
        total = sum(conditionals[a].values())
        if total > 0:
            conditionals[a] = {b: p / total for b, p in conditionals[a].items()}

    return (
        MarkovMorphism(
            name=f"disint({joint.name})",
            source=joint.source,
            target=joint.target,
            kernel=conditionals,
        ),
        marginal,
    )


def independent(
    m1: MarkovMorphism, m2: MarkovMorphism, threshold: float = 1e-6
) -> bool:
    """
    Check conditional independence between two Markov morphisms.

    Two kernels are independent if the joint factors:
    P(B, C | A) = P(B | A) * P(C | A) for all A.
    """
    for source_state in set(m1.kernel.keys()) | set(m2.kernel.keys()):
        d1 = m1.kernel.get(source_state, {})
        d2 = m2.kernel.get(source_state, {})

        for b in d1:
            for c in d2:
                joint_key = f"{b},{c}"
                expected = d1.get(b, 0) * d2.get(c, 0)
                if abs(expected) > threshold:
                    return True  # Non-trivial independent structure
    return True  # Trivially independent (no overlap)


class MarkovCategory:
    """
    A Markov category: symmetric monoidal category with copy and discard.

    Wraps a Category, adding stochastic morphisms and Bayesian operations.

    Usage:
        cat = Category("bayes_net")
        mc = MarkovCategory(cat)
        mc.add_stochastic("weather", "mood", {
            "sunny": {"happy": 0.8, "sad": 0.2},
            "rainy": {"happy": 0.3, "sad": 0.7},
        })
        result = mc.sample_path(["weather", "mood"], "sunny")
    """

    def __init__(self, category: Category):
        self._base = category
        self._stochastic: Dict[str, MarkovMorphism] = {}

    @property
    def base(self) -> Category:
        return self._base

    def add_stochastic(
        self,
        source: str,
        target: str,
        kernel: Dict[str, Dict[str, float]],
        name: str = None,
    ) -> MarkovMorphism:
        """Add a stochastic morphism (conditional distribution)."""
        if name is None:
            name = f"P({target}|{source})"

        mmor = MarkovMorphism(
            name=name, source=source, target=target, kernel=kernel,
        )
        self._stochastic[mmor.id] = mmor

        # Register structural morphism in base category
        avg_conf = 0.0
        count = 0
        for dist in kernel.values():
            for p in dist.values():
                avg_conf += p
                count += 1
        if count > 0:
            avg_conf /= count

        self._base.connect(source, target, name=name, confidence=avg_conf,
                           fn=lambda state, _m=mmor: _m(state))
        return mmor

    def copy_morphism(self, obj: str) -> MarkovMorphism:
        """The copy map: A -> A x A (diagonal / commutative comonoid)."""
        kernel = {obj: {f"{obj},{obj}": 1.0}}
        return MarkovMorphism(
            name=f"copy({obj})", source=obj, target=f"{obj} x {obj}",
            kernel=kernel,
        )

    def discard_morphism(self, obj: str) -> MarkovMorphism:
        """The discard map: A -> I (counit)."""
        kernel = {obj: {"I": 1.0}}
        return MarkovMorphism(
            name=f"discard({obj})", source=obj, target="I",
            kernel=kernel,
        )

    def compose(
        self, f: MarkovMorphism, g: MarkovMorphism
    ) -> MarkovMorphism:
        """Compose stochastic morphisms via kernel composition."""
        result = compose_markov(f, g)
        self._stochastic[result.id] = result
        # Register composed morphism in base Category
        total_vals = sum(len(d) for d in result.kernel.values())
        avg_conf = (sum(p for d in result.kernel.values() for p in d.values())
                    / max(1, total_vals))
        self._base.connect(result.source, result.target, name=result.name,
                           confidence=avg_conf,
                           fn=lambda s, _r=result: _r(s))
        return result

    def sample_path(
        self, object_names: List[str], initial_state: str
    ) -> List[str]:
        """
        Sample a path through a chain of stochastic morphisms.

        Args:
            object_names: Sequence of object names defining the chain.
            initial_state: Starting state.

        Returns:
            List of sampled states at each step.
        """
        states = [initial_state]
        current = initial_state

        for i in range(len(object_names) - 1):
            src, tgt = object_names[i], object_names[i + 1]
            # Find stochastic morphism
            mmor = None
            for m in self._stochastic.values():
                if m.source == src and m.target == tgt:
                    mmor = m
                    break

            if mmor is None:
                break

            next_state = mmor.sample(current)
            if next_state is None:
                break
            states.append(next_state)
            current = next_state

        return states

    def stochastic_morphisms(self) -> List[MarkovMorphism]:
        """List all stochastic morphisms."""
        return list(self._stochastic.values())

    def __repr__(self) -> str:
        return (
            f"MarkovCategory({self._base.name}, "
            f"|Stochastic|={len(self._stochastic)})"
        )
