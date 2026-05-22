# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Traced Monoidal Categories

A traced monoidal category has a trace operator:
  Tr_U: Hom(A tensor U, B tensor U) -> Hom(A, B)

This captures feedback loops: a morphism with an auxiliary port U
that loops back on itself.

Applications:
- Feedback control systems
- Fixed point computation
- Recursive programs

Reference: Joyal, Street, Verity, "Traced monoidal categories" (1996)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from core.category import Category
from core.types import Object, Morphism


def trace(
    category: Category,
    mor_id: str,
    loop_obj: str,
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> Morphism:
    """
    Trace operator: Hom(A tensor U, B tensor U) -> Hom(A, B).

    Given f: A x U -> B x U, the trace computes the fixed-point
    feedback loop and produces a morphism A -> B.

    For callable morphisms, this iterates until convergence.
    For structural morphisms, this creates the traced morphism directly.

    Args:
        category: The monoidal category.
        mor_id: Morphism ID of f: A x U -> B x U.
        loop_obj: The object U being looped.
        max_iterations: Maximum iterations for convergence.
        tolerance: Convergence tolerance.

    Returns:
        The traced morphism: A -> B.
    """
    mor = category.get_morphism(mor_id)
    if mor is None:
        raise ValueError(f"Morphism not found: {mor_id}")

    # Parse source = "A x U" and target = "B x U"
    src_parts = mor.source.split(" x ")
    tgt_parts = mor.target.split(" x ")

    if len(src_parts) < 2 or len(tgt_parts) < 2:
        raise ValueError(
            f"Morphism must be of form A x U -> B x U, "
            f"got {mor.source} -> {mor.target}"
        )

    a_obj = src_parts[0]
    b_obj = tgt_parts[0]

    # Create the traced morphism
    traced_fn = None
    if mor.is_callable:
        original_fn = mor._fn

        def traced_callable(*args, **kwargs):
            # Initialize loop variable
            u = np.zeros(1, dtype=np.float32)
            for _ in range(max_iterations):
                result = original_fn(*args, u, **kwargs)
                if isinstance(result, tuple) and len(result) == 2:
                    output, new_u = result
                    new_u = np.asarray(new_u, dtype=np.float32)
                    if np.max(np.abs(new_u - u)) < tolerance:
                        return output
                    u = new_u
                else:
                    return result
            return output  # Return last output even if not converged

        traced_fn = traced_callable

    return category.connect(
        a_obj, b_obj,
        name=f"Tr({mor.name})",
        confidence=mor.confidence,
        fn=traced_fn,
    )


def fixed_point(
    category: Category,
    mor_id: str,
    max_iterations: int = 100,
    tolerance: float = 1e-8,
) -> Optional[str]:
    """
    Compute the fixed point of an endomorphism via trace.

    Given f: A -> A, finds x such that f(x) = x.
    For structural morphisms, creates a fixed-point object.

    Args:
        category: The category.
        mor_id: Morphism ID of f: A -> A.
        max_iterations: Maximum iterations.
        tolerance: Convergence tolerance.

    Returns:
        Name of the fixed-point object, or None if not found.
    """
    mor = category.get_morphism(mor_id)
    if mor is None:
        raise ValueError(f"Morphism not found: {mor_id}")
    if mor.source != mor.target:
        raise ValueError(
            f"Fixed point requires endomorphism: "
            f"got {mor.source} -> {mor.target}"
        )

    fp_name = f"fix({mor.name})"
    category.add(fp_name, type_name="FixedPoint",
                metadata={"of_morphism": mor_id})

    # The fixed point has a morphism to the source (inclusion)
    category.connect(fp_name, mor.source, name="incl", confidence=1.0)

    # And the composition f . incl = incl (fixed-point equation)
    category.connect(fp_name, fp_name, name="id_fix", confidence=1.0)

    return fp_name


def feedback(
    category: Category,
    system_id: str,
    delay_id: str,
) -> Morphism:
    """
    Feedback loop construction.

    Given:
    - system: A x U -> B x U (the open system)
    - delay: U -> U (delay/memory in the feedback path)

    Constructs the closed-loop system A -> B.
    """
    system = category.get_morphism(system_id)
    delay = category.get_morphism(delay_id)

    if system is None or delay is None:
        raise ValueError("Morphism not found")

    # Parse A and B from system
    src_parts = system.source.split(" x ")
    tgt_parts = system.target.split(" x ")

    if len(src_parts) < 2 or len(tgt_parts) < 2:
        raise ValueError("System must be A x U -> B x U")

    a_obj = src_parts[0]
    b_obj = tgt_parts[0]

    feedback_fn = None
    if system.is_callable and delay.is_callable:
        sys_fn = system._fn
        del_fn = delay._fn

        def fb(*args, **kwargs):
            u = np.zeros(1, dtype=np.float32)
            for _ in range(100):
                result = sys_fn(*args, u, **kwargs)
                if isinstance(result, tuple) and len(result) == 2:
                    output, new_u = result
                    u = del_fn(np.asarray(new_u, dtype=np.float32))
                    if np.max(np.abs(np.asarray(new_u) - u)) < 1e-8:
                        return output
                else:
                    return result
            return output

        feedback_fn = fb

    conf = category.quantale.tensor(system.confidence, delay.confidence)
    return category.connect(
        a_obj, b_obj,
        name=f"feedback({system.name},{delay.name})",
        confidence=conf,
        fn=feedback_fn,
    )
