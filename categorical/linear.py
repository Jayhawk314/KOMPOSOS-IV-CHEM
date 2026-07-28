# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Linear Categories: Resource-Sensitive Morphisms

In a linear category, every morphism must be used exactly once.
There is no implicit copy or discard. To reuse a morphism, you must
explicitly promote it with the bang (!) modality.

This enforces resource discipline: every input is consumed, every
output is produced. Useful for:
- Protocol verification (each message sent exactly once)
- Quantum computing (no-cloning theorem)
- Memory management (ownership semantics)

Reference: Girard, "Linear logic" (1987)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


class LinearResourceError(Exception):
    """Raised when a linear resource is used incorrectly."""
    pass


class LinearCategory:
    """
    A category enforcing linear resource discipline.

    Morphisms must be used exactly once. Attempting to use a
    morphism twice raises LinearResourceError. Use bang() to
    explicitly allow reuse.

    Usage:
        cat = Category("resources")
        lc = LinearCategory(cat)
        f = lc.add("f", "A", "B")
        result = lc.use(f)  # OK
        lc.use(f)  # Raises LinearResourceError!
    """

    def __init__(self, category: Category):
        self._base = category
        self._used: Set[str] = set()
        self._promoted: Set[str] = set()  # bang'd morphisms (reusable)

    @property
    def base(self) -> Category:
        return self._base

    def add(
        self,
        name: str,
        source: str,
        target: str,
        confidence: float = 1.0,
        fn: Callable = None,
        **metadata,
    ) -> Morphism:
        """Add a linear morphism (must be used exactly once)."""
        return self._base.connect(
            source, target,
            name=name, confidence=confidence, fn=fn,
            **metadata,
        )

    def use(self, mor: Morphism) -> Any:
        """
        Use a linear morphism (consumes it).

        Raises LinearResourceError if the morphism has already been used
        and hasn't been bang'd.
        """
        if mor.id in self._used and mor.id not in self._promoted:
            raise LinearResourceError(
                f"Linear morphism '{mor.name}' ({mor.id}) "
                f"has already been consumed. Use bang() to allow reuse."
            )
        self._used.add(mor.id)
        return mor

    def bang(self, mor: Morphism) -> Morphism:
        """
        Promote a morphism to allow unlimited reuse (!A).

        In linear logic, ! (bang/of course) allows a resource
        to be used any number of times.
        """
        self._promoted.add(mor.id)
        return mor

    def linear_compose(self, f: Morphism, g: Morphism) -> Morphism:
        """
        Compose two linear morphisms, consuming both.

        Both f and g are consumed by this operation.
        """
        self.use(f)
        self.use(g)
        return self._base.compose(f, g)

    def is_used(self, mor: Morphism) -> bool:
        """Check if a morphism has been consumed."""
        return mor.id in self._used

    def is_promoted(self, mor: Morphism) -> bool:
        """Check if a morphism has been bang'd."""
        return mor.id in self._promoted

    def unused_morphisms(self) -> List[Morphism]:
        """List morphisms that haven't been consumed yet."""
        return [
            m for m in self._base.morphisms()
            if m.id not in self._used
        ]

    def check_all_consumed(self) -> List[Morphism]:
        """
        Check that all linear morphisms have been consumed.

        Returns list of unconsumed morphisms (should be empty
        for a well-typed linear program).
        """
        return [
            m for m in self._base.morphisms()
            if m.id not in self._used and m.id not in self._promoted
        ]

    def reset(self) -> None:
        """Reset usage tracking (for re-evaluation)."""
        self._used.clear()

    def __repr__(self) -> str:
        total = len(self._base.morphisms())
        used = len(self._used)
        promoted = len(self._promoted)
        return (
            f"LinearCategory({self._base.name}, "
            f"|Mor|={total}, used={used}, promoted={promoted})"
        )
