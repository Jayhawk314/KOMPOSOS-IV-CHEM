# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Z2-Graded Morphism — Foundation Layer
======================================

Pure math, zero external dependencies.

A Z2-graded (superalgebra) morphism where parity ∈ {0, 1}:
  - Parity 0 (Even / Bosonic): normal composition
  - Parity 1 (Odd / Fermionic): obeys Pauli exclusion — two odd morphisms
    composing produce NULL_COLLAPSE (amplitude → 0)

This is classical computation, not quantum hardware.
The algebraic structure is identical to a graded ring / exterior algebra.

Used by CogReasoningPlugin for interference-based chain detection:
  A single odd probe passes.
  Two odd probes chained together collapse.
  Mythos-style exploit chains require multiple odd compositions — they cancel.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GradedMorphism:
    """
    A morphism in a Z2-graded category.

    Attributes:
        name:      Human-readable label (e.g. technique ID or claim source→target)
        parity:    0 = even (benign/known), 1 = odd (anomalous/unverified)
        amplitude: Complex confidence weight ∈ [0+0j, 1+0j] nominally
        source:    Optional source node
        target:    Optional target node
    """
    name: str
    parity: int           # 0 or 1
    amplitude: complex = 1.0 + 0j
    source: Optional[str] = None
    target: Optional[str] = None

    def __post_init__(self):
        self.parity = self.parity % 2  # enforce Z2

    def compose(self, other: GradedMorphism) -> GradedMorphism:
        """
        Z2-graded composition.

        Rules:
          - Parity adds mod 2  (Z2 group law)
          - Odd ∘ Odd → NULL_COLLAPSE  (Fermionic exclusion)
          - All others → standard amplitude multiplication

        Returns a new GradedMorphism representing the composition.
        """
        new_parity = (self.parity + other.parity) % 2

        if self.parity == 1 and other.parity == 1:
            # Pauli exclusion: two fermions cannot occupy the same state
            return GradedMorphism(
                name="NULL_COLLAPSE",
                parity=new_parity,       # 0 — collapsed to even
                amplitude=0.0 + 0j,
                source=self.source,
                target=other.target,
            )

        return GradedMorphism(
            name=f"{self.name}∘{other.name}",
            parity=new_parity,
            amplitude=self.amplitude * other.amplitude,
            source=self.source,
            target=other.target,
        )

    # Operator alias
    def __mul__(self, other: GradedMorphism) -> GradedMorphism:
        return self.compose(other)

    @property
    def is_collapsed(self) -> bool:
        return self.name == "NULL_COLLAPSE" or abs(self.amplitude) < 1e-9

    @property
    def magnitude(self) -> float:
        return abs(self.amplitude)

    def __repr__(self) -> str:
        return (
            f"GradedMorphism({self.name!r}, "
            f"parity={self.parity}, "
            f"amplitude={self.amplitude:.3f})"
        )
