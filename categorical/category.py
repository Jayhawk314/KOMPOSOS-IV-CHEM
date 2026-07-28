# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Base Category Structure

A category C consists of:
- Objects: Ob(C)
- Morphisms: for each pair (A, B), a set Hom(A, B)
- Composition: for f: A → B and g: B → C, we have g ∘ f: A → C
- Identity: for each A, there is id_A: A → A

Axioms:
- Associativity: h ∘ (g ∘ f) = (h ∘ g) ∘ f
- Identity: f ∘ id_A = f = id_B ∘ f
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple


@dataclass
class Object:
    """
    An object in a category.

    Objects are determined by their morphisms (Yoneda lemma),
    but we store metadata for practical purposes.
    """
    name: str
    type_info: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Object):
            return self.name == other.name
        return False

    def __repr__(self):
        return f"Object({self.name})"


@dataclass
class Morphism:
    """
    A morphism f: A → B in a category.

    Morphisms are the arrows that encode relationships.
    In KOMPOSOS-III, morphisms can carry additional data
    for enriched categorical structure.
    """
    name: str
    source: Object
    target: Object
    data: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.name, self.source.name, self.target.name))

    def __eq__(self, other):
        if isinstance(other, Morphism):
            return (self.name == other.name and
                    self.source == other.source and
                    self.target == other.target)
        return False

    def __repr__(self):
        return f"{self.name}: {self.source.name} → {self.target.name}"


class Category:
    """
    A category with objects and morphisms.

    This is the foundational structure for KOMPOSOS-III.
    All data, concepts, and relationships live in categories.
    """

    def __init__(self, name: str = "C"):
        self.name = name
        self.objects: Dict[str, Object] = {}
        self.morphisms: Dict[str, Morphism] = {}
        self._hom_sets: Dict[Tuple[str, str], List[Morphism]] = {}
        self._identities: Dict[str, Morphism] = {}

    def add_object(self, obj: Object) -> Object:
        """Add an object to the category."""
        self.objects[obj.name] = obj
        # Create identity morphism
        id_mor = Morphism(
            name=f"id_{obj.name}",
            source=obj,
            target=obj,
            data={"is_identity": True}
        )
        self._identities[obj.name] = id_mor
        self.morphisms[id_mor.name] = id_mor
        return obj

    def add_morphism(self, mor: Morphism) -> Morphism:
        """Add a morphism to the category."""
        # Ensure source and target exist
        if mor.source.name not in self.objects:
            self.add_object(mor.source)
        if mor.target.name not in self.objects:
            self.add_object(mor.target)

        self.morphisms[mor.name] = mor

        # Update hom set
        key = (mor.source.name, mor.target.name)
        if key not in self._hom_sets:
            self._hom_sets[key] = []
        self._hom_sets[key].append(mor)

        return mor

    def identity(self, obj: Object) -> Morphism:
        """Get the identity morphism for an object."""
        if obj.name not in self._identities:
            raise ValueError(f"Object {obj.name} not in category")
        return self._identities[obj.name]

    def hom(self, source: Object, target: Object) -> List[Morphism]:
        """Get the hom-set Hom(source, target)."""
        key = (source.name, target.name)
        return self._hom_sets.get(key, [])

    def compose(self, f: Morphism, g: Morphism) -> Morphism:
        """
        Compose morphisms: given f: A → B and g: B → C,
        return g ∘ f: A → C.

        Note: We write composition in diagrammatic order,
        so compose(f, g) means "f then g".
        """
        if f.target != g.source:
            raise ValueError(
                f"Cannot compose {f} and {g}: "
                f"{f.target.name} ≠ {g.source.name}"
            )

        # Handle identity morphisms
        if f.data.get("is_identity"):
            return g
        if g.data.get("is_identity"):
            return f

        def composition_path(mor: Morphism) -> List[str]:
            return list(mor.data.get("composed_from", [mor.name]))

        composed_data = {
            **{
                k: v for k, v in f.data.items()
                if k not in {"is_identity", "composed_from"}
            },
            **{
                k: v for k, v in g.data.items()
                if k not in {"is_identity", "composed_from"}
            },
            "composed_from": composition_path(f) + composition_path(g),
        }

        # Create composed morphism
        composed = Morphism(
            name=f"{g.name}∘{f.name}",
            source=f.source,
            target=g.target,
            data=composed_data,
        )

        return self.add_morphism(composed)

    def compose_path(self, morphisms: List[Morphism]) -> Morphism:
        """Compose a list of morphisms in sequence."""
        if not morphisms:
            raise ValueError("Cannot compose empty path")
        if len(morphisms) == 1:
            return morphisms[0]

        result = morphisms[0]
        for mor in morphisms[1:]:
            result = self.compose(result, mor)
        return result

    def check_associativity(self, f: Morphism, g: Morphism, h: Morphism) -> bool:
        """
        Check associativity: h ∘ (g ∘ f) = (h ∘ g) ∘ f
        """
        try:
            left = self.compose(self.compose(f, g), h)
            right = self.compose(f, self.compose(g, h))
            # They should have same source and target
            return left.source == right.source and left.target == right.target
        except ValueError:
            return False

    def find_paths(self, source: Object, target: Object,
                   max_length: int = 5) -> List[List[Morphism]]:
        """
        Find all paths from source to target up to max_length.

        This is useful for discovering relationships and
        for Kan extension computations.
        """
        if source.name not in self.objects or target.name not in self.objects:
            return []

        paths = []

        def dfs(current: Object, path: List[Morphism], visited: set):
            if len(path) > max_length:
                return
            if current == target:
                if path:  # non-empty path
                    paths.append(path.copy())
                return

            for mor in self.morphisms.values():
                if mor.source == current and mor.name not in visited:
                    if not mor.data.get("is_identity"):
                        visited.add(mor.name)
                        path.append(mor)
                        dfs(mor.target, path, visited)
                        path.pop()
                        visited.remove(mor.name)

        dfs(source, [], set())
        return paths

    def __repr__(self):
        return (f"Category({self.name}, "
                f"|Ob|={len(self.objects)}, "
                f"|Mor|={len(self.morphisms)})")


# Convenience functions for creating objects and morphisms

def obj(name: str, **kwargs) -> Object:
    """Create an object."""
    return Object(name=name, type_info=kwargs)


def mor(name: str, source: Object, target: Object, **kwargs) -> Morphism:
    """Create a morphism."""
    return Morphism(name=name, source=source, target=target, data=kwargs)


# Example usage and tests
if __name__ == "__main__":
    # Create a simple category
    C = Category("Physics")

    # Add objects (concepts)
    classical = C.add_object(obj("classical_physics", domain="physics"))
    hamilton = C.add_object(obj("hamiltonian_mechanics", domain="physics"))
    quantum = C.add_object(obj("quantum_mechanics", domain="physics"))

    # Add morphisms (relationships)
    f = C.add_morphism(mor("reformulation", classical, hamilton,
                           year=1833, author="Hamilton"))
    g = C.add_morphism(mor("quantization", hamilton, quantum,
                           year=1925, author="Heisenberg"))

    # Compose
    h = C.compose(f, g)
    print(f"Composed: {h}")

    # Find paths
    paths = C.find_paths(classical, quantum)
    print(f"Paths from classical to quantum: {paths}")

    print(C)
