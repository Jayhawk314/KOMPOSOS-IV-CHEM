# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Double Categories: Two Kinds of Morphisms

A double category has:
- Objects
- Tight (horizontal) morphisms: compose strictly
- Loose (vertical) morphisms: compose loosely
- 2-cells filling squares bounded by tight/loose morphisms

Applications:
- Structured cospans for systems composition
- Relations vs functions
- Profunctors vs functors

Reference: Grandis & Pare, "Limits in double categories" (1999)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


@dataclass
class Cell:
    """
    A 2-cell in a double category.

    Fills the square:
        top
      A ---> B
      |      |
    left   right
      |      |
      v      v
      C ---> D
       bottom
    """
    name: str
    top: str  # tight morphism ID: A -> B
    bottom: str  # tight morphism ID: C -> D
    left: str  # loose morphism ID: A -> C
    right: str  # loose morphism ID: B -> D
    metadata: Dict[str, Any] = field(default_factory=dict)


class DoubleCategory:
    """
    A double category with tight and loose morphisms.

    Backed by an internal Category for persistence and composition.
    Tight and loose morphisms are distinguished by direction metadata.

    Usage:
        dc = DoubleCategory("systems")
        dc.add_object("A")
        dc.add_object("B")
        dc.add_tight("A", "B", name="f")
        dc.add_loose("A", "B", name="R")
        dc.add_cell("square1", top="f_id", bottom="g_id",
                     left="R_id", right="S_id")
    """

    def __init__(self, name: str, category: Category = None):
        self.name = name
        self._base = category or Category(name=name, db_path=":memory:")
        self._tight: Dict[str, Morphism] = {}  # overlay for direction filtering
        self._loose: Dict[str, Morphism] = {}  # overlay for direction filtering
        self._cells: Dict[str, Cell] = {}

    @property
    def base(self) -> Category:
        """The underlying Category."""
        return self._base

    def add_object(self, name: str, **kwargs) -> Object:
        """Add an object to the double category."""
        existing = self._base.get(name)
        if existing is not None:
            return existing
        return self._base.add(name, **kwargs)

    def add_tight(
        self, source: str, target: str, name: str = "f",
        confidence: float = 1.0, **metadata
    ) -> Morphism:
        """Add a tight (horizontal) morphism."""
        # Ensure objects exist
        if self._base.get(source) is None:
            self._base.add(source)
        if self._base.get(target) is None:
            self._base.add(target)

        mor = self._base.connect(
            source, target, name=name, confidence=confidence,
            direction="tight", **metadata,
        )
        self._tight[mor.id] = mor
        return mor

    def add_loose(
        self, source: str, target: str, name: str = "R",
        confidence: float = 1.0, **metadata
    ) -> Morphism:
        """Add a loose (vertical) morphism."""
        if self._base.get(source) is None:
            self._base.add(source)
        if self._base.get(target) is None:
            self._base.add(target)

        mor = self._base.connect(
            source, target, name=name, confidence=confidence,
            direction="loose", **metadata,
        )
        self._loose[mor.id] = mor
        return mor

    def add_cell(
        self, name: str,
        top: str, bottom: str, left: str, right: str,
        **metadata
    ) -> Cell:
        """
        Add a 2-cell filling a square.

        The square must commute: tight morphisms on top/bottom,
        loose morphisms on left/right.
        """
        cell = Cell(
            name=name, top=top, bottom=bottom,
            left=left, right=right, metadata=metadata,
        )
        self._cells[name] = cell
        return cell

    def objects(self) -> List[Object]:
        return self._base.objects()

    def tight_morphisms(self) -> List[Morphism]:
        return list(self._tight.values())

    def loose_morphisms(self) -> List[Morphism]:
        return list(self._loose.values())

    def cells(self) -> List[Cell]:
        return list(self._cells.values())

    def compose_tight(self, f_id: str, g_id: str) -> Morphism:
        """Compose tight morphisms: g . f."""
        f = self._tight.get(f_id)
        g = self._tight.get(g_id)
        if f is None or g is None:
            raise ValueError(f"Tight morphism not found")
        if f.target != g.source:
            raise TypeError(f"Cannot compose: {f.target} != {g.source}")

        composed = self._base.connect(
            f.source, g.target,
            name=f"{g.name}.{f.name}",
            confidence=f.confidence * g.confidence,
            direction="tight", composed_from=[f_id, g_id],
        )
        self._tight[composed.id] = composed
        return composed

    def compose_loose(self, f_id: str, g_id: str) -> Morphism:
        """Compose loose morphisms: g . f."""
        f = self._loose.get(f_id)
        g = self._loose.get(g_id)
        if f is None or g is None:
            raise ValueError(f"Loose morphism not found")
        if f.target != g.source:
            raise TypeError(f"Cannot compose: {f.target} != {g.source}")

        composed = self._base.connect(
            f.source, g.target,
            name=f"{g.name}.{f.name}",
            confidence=f.confidence * g.confidence,
            direction="loose", composed_from=[f_id, g_id],
        )
        self._loose[composed.id] = composed
        return composed

    def to_category(self) -> Category:
        """Return the underlying Category (retains all structure)."""
        return self._base

    def structured_cospan(
        self, cat: Category, f_id: str, g_id: str
    ) -> Cell:
        """
        Build a structured cospan from a pushout.

        Given f: C -> A and g: C -> B in cat, the pushout A +_C B
        gives a structured cospan C -> A +_C B <- C, represented
        as a cell in the double category.
        """
        cocone = cat.pushout(f_id, g_id)

        f = cat.get_morphism(f_id)
        g = cat.get_morphism(g_id)

        # Add objects
        for name in (f.source, f.target, g.target, cocone.apex):
            if self._base.get(name) is None:
                self.add_object(name)

        # Tight: the cospan legs
        left_tight = self.add_tight(f.target, cocone.apex, name="iota1")
        right_tight = self.add_tight(g.target, cocone.apex, name="iota2")

        # Loose: from common source
        left_loose = self.add_loose(f.source, f.source, name="id")
        right_loose = self.add_loose(f.source, f.source, name="id")

        cell = self.add_cell(
            name=f"cospan({f.name},{g.name})",
            top=left_tight.id,
            bottom=right_tight.id,
            left=left_loose.id,
            right=right_loose.id,
        )
        return cell

    def __repr__(self) -> str:
        return (
            f"DoubleCategory('{self.name}', "
            f"|Ob|={len(self._base.objects())}, "
            f"|Tight|={len(self._tight)}, "
            f"|Loose|={len(self._loose)}, "
            f"|Cells|={len(self._cells)})"
        )
