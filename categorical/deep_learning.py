# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Categorical Deep Learning: Para + Optic = Neural Networks

Neural networks are morphisms in Para(C) with bidirectional structure
from Optic(C). The forward pass is the optic's forward leg; the
backward pass (backpropagation) is the optic's backward leg.

Training is gradient descent on the parameter space of Para.

This module provides:
- NeuralMorphism: morphism with forward AND backward pass
- backward: backpropagation as optic backward
- train: gradient descent as morphism optimization
- equivariant: naturality check for equivariance

Reference: Fong, Spivak, Tuyeras, "Backprop as Functor" (2019)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .para import ParametricMorphism, compose_parametric, linear_morphism, relu_morphism
from .optics import Optic, compose_optics

from core.category import Category
from core.types import Object


@dataclass
class NeuralMorphism:
    """
    A morphism with forward AND backward pass.

    Combines Para (parameters) with Optic (bidirectional):
    - forward(params, input) -> output
    - backward(params, input, output_grad) -> (param_grad, input_grad)
    """
    name: str
    source: str
    target: str
    params: Any
    forward: Callable[[Any, Any], Any]
    backward: Callable[[Any, Any, Any], Tuple[Any, Any]]
    param_shape: Optional[Any] = None

    def __call__(self, input_val: Any) -> Any:
        """Forward pass."""
        return self.forward(self.params, input_val)

    @property
    def id(self) -> str:
        return f"neural:{self.name}:{self.source}->{self.target}"


def neural_linear(
    name: str,
    source: str,
    target: str,
    in_dim: int,
    out_dim: int,
    rng: Optional[np.random.RandomState] = None,
) -> NeuralMorphism:
    """
    Create a linear neural morphism with analytic gradient.

    y = Wx + b
    dy/dW = x^T, dy/db = 1, dy/dx = W^T
    """
    if rng is None:
        rng = np.random.RandomState()

    scale = np.sqrt(2.0 / (in_dim + out_dim))
    W = rng.randn(out_dim, in_dim).astype(np.float32) * scale
    b = np.zeros(out_dim, dtype=np.float32)
    params = {"W": W, "b": b}

    def forward(params, x):
        x = np.asarray(x, dtype=np.float32)
        return params["W"] @ x + params["b"]

    def backward(params, x, output_grad):
        x = np.asarray(x, dtype=np.float32)
        output_grad = np.asarray(output_grad, dtype=np.float32)
        param_grad = {
            "W": np.outer(output_grad, x),
            "b": output_grad.copy(),
        }
        input_grad = params["W"].T @ output_grad
        return param_grad, input_grad

    return NeuralMorphism(
        name=name,
        source=source,
        target=target,
        params=params,
        forward=forward,
        backward=backward,
        param_shape={"W": (out_dim, in_dim), "b": (out_dim,)},
    )


def neural_relu(name: str, obj: str) -> NeuralMorphism:
    """ReLU activation with gradient."""
    def forward(params, x):
        return np.maximum(0, np.asarray(x, dtype=np.float32))

    def backward(params, x, output_grad):
        x = np.asarray(x, dtype=np.float32)
        output_grad = np.asarray(output_grad, dtype=np.float32)
        input_grad = output_grad * (x > 0).astype(np.float32)
        return {}, input_grad

    return NeuralMorphism(
        name=name, source=obj, target=obj,
        params={}, forward=forward, backward=backward,
    )


def neural_sigmoid(name: str, obj: str) -> NeuralMorphism:
    """Sigmoid activation with gradient."""
    def forward(params, x):
        x = np.asarray(x, dtype=np.float32)
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

    def backward(params, x, output_grad):
        x = np.asarray(x, dtype=np.float32)
        output_grad = np.asarray(output_grad, dtype=np.float32)
        s = 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
        input_grad = output_grad * s * (1 - s)
        return {}, input_grad

    return NeuralMorphism(
        name=name, source=obj, target=obj,
        params={}, forward=forward, backward=backward,
    )


def compose_neural(
    f: NeuralMorphism, g: NeuralMorphism
) -> NeuralMorphism:
    """
    Compose neural morphisms with forward AND backward.

    Forward: g(f(x))
    Backward: chain rule through both
    """
    if f.target != g.source:
        raise TypeError(
            f"Cannot compose: {f.name} targets '{f.target}' "
            f"but {g.name} sources '{g.source}'"
        )

    paired_params = {"f_params": f.params, "g_params": g.params}

    def composed_forward(params, x):
        mid = f.forward(params["f_params"], x)
        return g.forward(params["g_params"], mid)

    def composed_backward(params, x, output_grad):
        mid = f.forward(params["f_params"], x)
        g_param_grad, mid_grad = g.backward(params["g_params"], mid, output_grad)
        f_param_grad, input_grad = f.backward(params["f_params"], x, mid_grad)
        return {
            "f_params": f_param_grad,
            "g_params": g_param_grad,
        }, input_grad

    return NeuralMorphism(
        name=f"{g.name}.{f.name}",
        source=f.source,
        target=g.target,
        params=paired_params,
        forward=composed_forward,
        backward=composed_backward,
    )


def chain(*morphisms: NeuralMorphism) -> NeuralMorphism:
    """Compose a sequence of neural morphisms."""
    result = morphisms[0]
    for m in morphisms[1:]:
        result = compose_neural(result, m)
    return result


def mse_loss(predicted: np.ndarray, target: np.ndarray) -> Tuple[float, np.ndarray]:
    """Mean squared error loss with gradient."""
    predicted = np.asarray(predicted, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    diff = predicted - target
    loss = float(np.mean(diff ** 2))
    grad = 2.0 * diff / len(diff)
    return loss, grad


def _apply_grads(params, grads, lr):
    """Recursively apply gradients to nested parameter dicts."""
    if isinstance(params, dict) and isinstance(grads, dict):
        new_params = {}
        for key in params:
            if key in grads:
                new_params[key] = _apply_grads(params[key], grads[key], lr)
            else:
                new_params[key] = params[key]
        return new_params
    elif isinstance(params, np.ndarray) and isinstance(grads, np.ndarray):
        return params - lr * grads
    else:
        return params


def train(
    model: NeuralMorphism,
    data: List[Tuple[np.ndarray, np.ndarray]],
    loss_fn: Callable = mse_loss,
    lr: float = 0.01,
    epochs: int = 100,
    verbose: bool = False,
) -> Tuple[NeuralMorphism, List[float]]:
    """
    Train a neural morphism via gradient descent.

    Args:
        model: The neural morphism to train.
        data: List of (input, target) pairs.
        loss_fn: Loss function returning (loss, grad).
        lr: Learning rate.
        epochs: Number of training epochs.
        verbose: Print progress.

    Returns:
        (trained_model, loss_history)
    """
    params = model.params
    losses = []

    for epoch in range(epochs):
        epoch_loss = 0.0

        for x, y in data:
            # Forward
            output = model.forward(params, x)

            # Loss
            loss, output_grad = loss_fn(output, y)
            epoch_loss += loss

            # Backward
            param_grad, _ = model.backward(params, x, output_grad)

            # Update
            params = _apply_grads(params, param_grad, lr)

        avg_loss = epoch_loss / len(data)
        losses.append(avg_loss)

        if verbose and (epoch % (epochs // 10 or 1) == 0):
            print(f"  Epoch {epoch}: loss={avg_loss:.6f}")

    # Return new model with trained params
    trained = NeuralMorphism(
        name=model.name,
        source=model.source,
        target=model.target,
        params=params,
        forward=model.forward,
        backward=model.backward,
        param_shape=model.param_shape,
    )
    return trained, losses


def equivariant(
    model: NeuralMorphism,
    group_transforms: List[Callable],
    test_inputs: List[np.ndarray],
    tolerance: float = 1e-4,
) -> bool:
    """
    Check if a model is equivariant under group transformations.

    A model f is equivariant if f(g.x) = g.f(x) for all group elements g.
    This is a naturality condition in categorical terms.
    """
    for g in group_transforms:
        for x in test_inputs:
            # f(g(x))
            gx = g(np.asarray(x, dtype=np.float32))
            f_gx = model(gx)
            # g(f(x))
            fx = model(np.asarray(x, dtype=np.float32))
            g_fx = g(fx)
            if np.max(np.abs(np.asarray(f_gx) - np.asarray(g_fx))) > tolerance:
                return False
    return True


class NeuralCategory:
    """Neural network category: wraps Category, adding forward/backward passes."""

    def __init__(self, category: Category):
        self._base = category
        self._neural: Dict[str, NeuralMorphism] = {}

    @property
    def base(self) -> Category:
        return self._base

    def add_morphism(self, nmor: NeuralMorphism) -> NeuralMorphism:
        """Register a neural morphism, persisting structure in base."""
        if self._base.get(nmor.source) is None:
            self._base.add(nmor.source)
        if self._base.get(nmor.target) is None:
            self._base.add(nmor.target)
        self._neural[nmor.id] = nmor
        self._base.connect(nmor.source, nmor.target, name=nmor.name,
                           confidence=1.0, fn=lambda x, _n=nmor: _n(x))
        return nmor

    def compose(self, f: NeuralMorphism, g: NeuralMorphism) -> NeuralMorphism:
        """Compose neural morphisms through base Category."""
        result = compose_neural(f, g)
        self._neural[result.id] = result
        self._base.connect(result.source, result.target, name=result.name,
                           confidence=1.0, fn=lambda x, _r=result: _r(x))
        return result

    def chain(self, *layers: NeuralMorphism) -> NeuralMorphism:
        """Chain multiple neural morphisms through base Category."""
        result = chain(*layers)
        self._neural[result.id] = result
        self._base.connect(result.source, result.target, name=result.name,
                           confidence=1.0, fn=lambda x, _r=result: _r(x))
        return result

    def train(self, model: NeuralMorphism, data, **kwargs) -> tuple:
        """Train model, return (trained_model, losses)."""
        trained, losses = train(model, data, **kwargs)
        self._neural[trained.id] = trained
        return trained, losses

    def morphisms(self) -> list:
        return list(self._neural.values())

    def objects(self) -> list:
        return self._base.objects()

    def __repr__(self) -> str:
        return f"NeuralCategory(base={self._base.name}, |neural|={len(self._neural)})"
