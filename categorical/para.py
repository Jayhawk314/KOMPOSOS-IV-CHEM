# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Para Construction: Parametric Morphisms

Para(C) is a category where:
- Objects are the same as in C
- Morphisms carry learnable parameters

A parametric morphism (P, f): A -> B consists of:
- A parameter object P
- A function f: P x A -> B

Composition in Para(C):
  (Q, g) . (P, f) = (P x Q, h)
  where h(p, q, a) = g(q, f(p, a))

This is the categorical foundation for parameterized models:
neural networks, controllers, probabilistic programs, etc.

Reference: Fong, Spivak, Tuyeras, "Backprop as Functor" (2019)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.category import Category
from core.types import Object, Morphism


@dataclass
class ParametricMorphism:
    """
    A morphism carrying learnable parameters.

    Fields:
        name: Identifier.
        source: Source object name.
        target: Target object name.
        params: Current parameter values (numpy array or dict).
        forward: Function (params, input) -> output.
        param_shape: Shape descriptor for parameters.
    """
    name: str
    source: str
    target: str
    params: Any  # np.ndarray or dict
    forward: Callable[[Any, Any], Any]
    param_shape: Optional[Any] = None

    def __call__(self, input_val: Any) -> Any:
        """Evaluate the parametric morphism at current parameters."""
        return self.forward(self.params, input_val)

    @property
    def id(self) -> str:
        return f"para:{self.name}:{self.source}->{self.target}"


def compose_parametric(
    f: ParametricMorphism, g: ParametricMorphism
) -> ParametricMorphism:
    """
    Compose parametric morphisms: g . f in Para(C).

    Given f: (P, A -> B) and g: (Q, B -> C),
    produces (P x Q, A -> C) where params are paired.
    """
    if f.target != g.source:
        raise TypeError(
            f"Cannot compose: {f.name} targets '{f.target}' "
            f"but {g.name} sources '{g.source}'"
        )

    # Pair the parameters
    paired_params = {"f_params": f.params, "g_params": g.params}

    def composed_forward(params, input_val):
        intermediate = f.forward(params["f_params"], input_val)
        return g.forward(params["g_params"], intermediate)

    return ParametricMorphism(
        name=f"{g.name}.{f.name}",
        source=f.source,
        target=g.target,
        params=paired_params,
        forward=composed_forward,
    )


def update_params(pmor: ParametricMorphism, new_params: Any) -> ParametricMorphism:
    """
    Return a new ParametricMorphism with updated parameters.
    """
    return ParametricMorphism(
        name=pmor.name,
        source=pmor.source,
        target=pmor.target,
        params=new_params,
        forward=pmor.forward,
        param_shape=pmor.param_shape,
    )


def linear_morphism(
    name: str,
    source: str,
    target: str,
    in_dim: int,
    out_dim: int,
    rng: Optional[np.random.RandomState] = None,
) -> ParametricMorphism:
    """
    Create a linear parametric morphism: y = Wx + b.

    Args:
        name: Identifier.
        source: Source object name.
        target: Target object name.
        in_dim: Input dimension.
        out_dim: Output dimension.
        rng: Random state for initialization.
    """
    if rng is None:
        rng = np.random.RandomState()

    # Xavier initialization
    scale = np.sqrt(2.0 / (in_dim + out_dim))
    W = rng.randn(out_dim, in_dim).astype(np.float32) * scale
    b = np.zeros(out_dim, dtype=np.float32)

    params = {"W": W, "b": b}

    def forward(params, x):
        return params["W"] @ np.asarray(x, dtype=np.float32) + params["b"]

    return ParametricMorphism(
        name=name,
        source=source,
        target=target,
        params=params,
        forward=forward,
        param_shape={"W": (out_dim, in_dim), "b": (out_dim,)},
    )


def relu_morphism(name: str, obj: str) -> ParametricMorphism:
    """
    Create a ReLU activation (parameter-free morphism in Para).
    """
    return ParametricMorphism(
        name=name,
        source=obj,
        target=obj,
        params={},
        forward=lambda p, x: np.maximum(0, np.asarray(x, dtype=np.float32)),
    )


class Para:
    """
    The Para(C) construction.

    Wraps a Category C, producing a parametric category where
    morphisms carry learnable parameters.

    Usage:
        cat = Category("base")
        cat.add("R2")
        cat.add("R3")
        para = Para(cat)
        f = para.add_morphism(linear_morphism("W1", "R2", "R3", 2, 3))
        output = f(np.array([1.0, 2.0]))
    """

    def __init__(self, category: Category):
        self._base = category
        self._morphisms: Dict[str, ParametricMorphism] = {}

    @property
    def base(self) -> Category:
        """The underlying category."""
        return self._base

    def add_morphism(self, pmor: ParametricMorphism) -> ParametricMorphism:
        """Register a parametric morphism."""
        # Ensure objects exist in base category
        if self._base.get(pmor.source) is None:
            self._base.add(pmor.source)
        if self._base.get(pmor.target) is None:
            self._base.add(pmor.target)

        self._morphisms[pmor.id] = pmor

        # Register in base category as executable morphism
        self._base.connect(
            pmor.source, pmor.target,
            name=pmor.name,
            confidence=1.0,
            fn=lambda x, _p=pmor: _p(x),
        )
        return pmor

    def get_morphism(self, pmor_id: str) -> Optional[ParametricMorphism]:
        """Get a parametric morphism by ID."""
        return self._morphisms.get(pmor_id)

    def morphisms(self) -> List[ParametricMorphism]:
        """List all parametric morphisms."""
        return list(self._morphisms.values())

    def compose(
        self, f: ParametricMorphism, g: ParametricMorphism
    ) -> ParametricMorphism:
        """Compose in Para(C)."""
        result = compose_parametric(f, g)
        self._morphisms[result.id] = result
        self._base.connect(
            result.source, result.target,
            name=result.name,
            confidence=1.0,
            fn=lambda x, _r=result: _r(x),
        )
        return result

    def evaluate(self, pmor: ParametricMorphism, input_val: Any) -> Any:
        """Evaluate a parametric morphism."""
        return pmor(input_val)

    def objects(self) -> List[Object]:
        """Objects are same as base category."""
        return self._base.objects()

    def __repr__(self) -> str:
        return (
            f"Para({self._base.name}, "
            f"|PMor|={len(self._morphisms)})"
        )
