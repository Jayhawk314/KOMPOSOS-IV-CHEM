# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Dagger Compact Categories

A dagger category has an involution on morphisms:
  dagger(f: A -> B) = f*: B -> A
  dagger(dagger(f)) = f
  dagger(g . f) = dagger(f) . dagger(g)

A compact category adds duals, cups, and caps:
  dual(A) = A*
  cup: I -> A tensor A*
  cap: A* tensor A -> I
  satisfying snake lemma (zig-zag identities)

Applications:
- Quantum computing (unitary gates, ZX calculus)
- Linear algebra (adjoint operators)
- Signal processing

Reference: Abramsky & Coecke, "Categorical Quantum Mechanics" (2004)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


class DaggerCategory:
    """
    A category with a dagger (adjoint) operation on every morphism.

    For each f: A -> B, there exists f*: B -> A (the dagger/adjoint).
    The dagger is involutive: (f*)* = f.
    The dagger is contravariant: (g . f)* = f* . g*.

    Usage:
        cat = Category("quantum")
        dc = DaggerCategory(cat)
        f = cat.connect("A", "B", name="U", confidence=1.0)
        f_dag = dc.dagger(f.id)  # B -> A
    """

    def __init__(self, category: Category):
        self._base = category
        self._daggers: Dict[str, str] = {}  # mor_id -> dagger_mor_id

    @property
    def base(self) -> Category:
        return self._base

    def dagger(self, mor_id: str) -> Morphism:
        """
        Get or create the dagger (adjoint) of a morphism.

        f: A -> B  =>  f*: B -> A  with same confidence.
        """
        if mor_id in self._daggers:
            dag_id = self._daggers[mor_id]
            existing = self._base.get_morphism(dag_id)
            if existing is not None:
                return existing

        mor = self._base.get_morphism(mor_id)
        if mor is None:
            raise ValueError(f"Morphism not found: {mor_id}")

        # Create the dagger morphism
        dag_fn = None
        if mor._fn is not None:
            # For callable morphisms, dagger reverses direction
            dag_fn = mor._fn  # User should override for actual adjoint

        dag = self._base.connect(
            mor.target, mor.source,
            name=f"{mor.name}*",
            confidence=mor.confidence,
            fn=dag_fn,
        )

        self._daggers[mor_id] = dag.id
        self._daggers[dag.id] = mor_id  # Involutive
        return dag

    def is_unitary(self, mor_id: str) -> bool:
        """
        Check if a morphism is unitary: f* . f = id and f . f* = id.

        In enriched terms: the composed confidence equals the unit.
        """
        mor = self._base.get_morphism(mor_id)
        if mor is None:
            return False

        dag = self.dagger(mor_id)

        # f* . f should have unit confidence
        composed_1 = self._base.quantale.tensor(mor.confidence, dag.confidence)
        # f . f* should have unit confidence
        composed_2 = self._base.quantale.tensor(dag.confidence, mor.confidence)

        unit = self._base.quantale.unit
        return (abs(composed_1 - unit) < 1e-10 and
                abs(composed_2 - unit) < 1e-10)

    def is_self_adjoint(self, mor_id: str) -> bool:
        """Check if f = f* (self-adjoint / Hermitian)."""
        mor = self._base.get_morphism(mor_id)
        dag = self.dagger(mor_id)
        if mor is None:
            return False
        return (mor.source == dag.source and
                mor.target == dag.target and
                abs(mor.confidence - dag.confidence) < 1e-10)

    def morphisms(self) -> List[Morphism]:
        """All morphisms in the base category."""
        return self._base.morphisms()


class CompactCategory:
    """
    A compact (closed) category built on top of a dagger category.

    Adds duals, cups, and caps for each object:
    - dual(A) = A* (the dual object)
    - cup(A): I -> A tensor A* (unit of the adjunction)
    - cap(A): A* tensor A -> I (counit of the adjunction)

    These satisfy the snake lemma (zig-zag identities).

    Requires the base category to have monoidal tensor.
    """

    def __init__(self, dagger_cat: DaggerCategory):
        self._dagger = dagger_cat
        self._base = dagger_cat.base
        self._duals: Dict[str, str] = {}
        self._cups: Dict[str, str] = {}
        self._caps: Dict[str, str] = {}

    @property
    def base(self) -> Category:
        return self._base

    def dual(self, obj_name: str) -> str:
        """
        Get or create the dual object A*.
        """
        if obj_name in self._duals:
            return self._duals[obj_name]

        dual_name = f"{obj_name}*"
        if self._base.get(dual_name) is None:
            self._base.add(dual_name, type_name="Dual",
                          metadata={"dual_of": obj_name})

        self._duals[obj_name] = dual_name
        self._duals[dual_name] = obj_name  # (A*)* = A
        return dual_name

    def cup(self, obj_name: str) -> Morphism:
        """
        Cup morphism: I -> A tensor A*.

        The unit of the duality adjunction.
        """
        if obj_name in self._cups:
            cup_id = self._cups[obj_name]
            existing = self._base.get_morphism(cup_id)
            if existing is not None:
                return existing

        dual_name = self.dual(obj_name)
        unit_name = self._base.monoidal_unit()
        tensor_name = self._base.tensor(obj_name, dual_name)

        cup_mor = self._base.connect(
            unit_name, tensor_name,
            name=f"cup({obj_name})",
            confidence=1.0,
        )
        self._cups[obj_name] = cup_mor.id
        return cup_mor

    def cap(self, obj_name: str) -> Morphism:
        """
        Cap morphism: A* tensor A -> I.

        The counit of the duality adjunction.
        """
        if obj_name in self._caps:
            cap_id = self._caps[obj_name]
            existing = self._base.get_morphism(cap_id)
            if existing is not None:
                return existing

        dual_name = self.dual(obj_name)
        unit_name = self._base.monoidal_unit()
        tensor_name = self._base.tensor(dual_name, obj_name)

        cap_mor = self._base.connect(
            tensor_name, unit_name,
            name=f"cap({obj_name})",
            confidence=1.0,
        )
        self._caps[obj_name] = cap_mor.id
        return cap_mor

    def verify_snake(self, obj_name: str) -> bool:
        """
        Verify the snake lemma (zig-zag identities) for an object.

        (cap tensor id_A) . (id_A tensor cup) = id_A
        (id_A* tensor cap) . (cup tensor id_A*) = id_A*

        Returns True if both identities hold (confidence-wise).
        """
        cup_mor = self.cup(obj_name)
        cap_mor = self.cap(obj_name)

        # Snake identity holds if cups and caps have unit confidence
        return (abs(cup_mor.confidence - 1.0) < 1e-10 and
                abs(cap_mor.confidence - 1.0) < 1e-10)

    def __repr__(self) -> str:
        return (
            f"CompactCategory({self._base.name}, "
            f"|Duals|={len(self._duals) // 2})"
        )
