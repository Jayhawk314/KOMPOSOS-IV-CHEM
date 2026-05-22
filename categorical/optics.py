# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Optics: Bidirectional Transformations

Optics generalize lenses and prisms to provide bidirectional access
patterns between composite data structures.

- Lens: product-type access (get/put) -- "has-a" relationship
- Prism: sum-type access (match/build) -- "is-a" relationship
- Optic: general bidirectional process (forward/backward)

In categorical terms, a lens (S,T,A,B) is a pair of morphisms:
  get: S -> A
  put: S x B -> T

And a prism is:
  match: S -> T + A
  build: B -> T

Optics compose: if you can focus on a part, and that part has a subpart,
you can focus on the subpart directly.

Reference: Riley, "Categories of Optics" (2018)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from core.category import Category
from core.types import Object, Morphism


@dataclass
class Lens:
    """
    A lens for product-type bidirectional access.

    get: S -> A  (extract the focus)
    put: (S, B) -> T  (replace the focus)

    Laws:
    - GetPut: put(s, get(s)) = s
    - PutGet: get(put(s, b)) = b
    - PutPut: put(put(s, b1), b2) = put(s, b2)
    """
    name: str
    get: Callable[[Any], Any]
    put: Callable[[Any, Any], Any]
    source_type: str = "S"
    target_type: str = "A"

    def __call__(self, value: Any) -> Any:
        """Apply get."""
        return self.get(value)

    def modify(self, value: Any, fn: Callable[[Any], Any]) -> Any:
        """Apply a function to the focus: modify(s, f) = put(s, f(get(s)))."""
        return self.put(value, fn(self.get(value)))

    def verify_laws(self, test_s: Any, test_b: Any) -> Dict[str, bool]:
        """Check lens laws on sample values."""
        results = {}
        try:
            # GetPut: put(s, get(s)) = s
            results["get_put"] = self.put(test_s, self.get(test_s)) == test_s
        except Exception:
            results["get_put"] = False
        try:
            # PutGet: get(put(s, b)) = b
            results["put_get"] = self.get(self.put(test_s, test_b)) == test_b
        except Exception:
            results["put_get"] = False
        try:
            # PutPut: put(put(s, b1), b2) = put(s, b2)
            results["put_put"] = self.put(self.put(test_s, test_b), test_b) == self.put(test_s, test_b)
        except Exception:
            results["put_put"] = False
        return results


@dataclass
class Prism:
    """
    A prism for sum-type bidirectional access.

    match: S -> Either[T, A]  (attempt to extract)
    build: B -> T  (inject)

    Returns (True, value) for successful match, (False, remainder) for failure.
    """
    name: str
    match: Callable[[Any], Tuple[bool, Any]]
    build: Callable[[Any], Any]
    source_type: str = "S"
    target_type: str = "A"

    def preview(self, value: Any) -> Optional[Any]:
        """Try to get the focus; returns None if match fails."""
        ok, result = self.match(value)
        return result if ok else None

    def review(self, value: Any) -> Any:
        """Build from a value (inject)."""
        return self.build(value)


@dataclass
class Optic:
    """
    General bidirectional process.

    forward: S -> A  (forward pass)
    backward: (S, B) -> T  (backward pass with residual)

    Generalizes both Lens and Prism. In the context of gradient-based
    learning, forward is the forward pass and backward is backpropagation.
    """
    name: str
    forward: Callable[[Any], Any]
    backward: Callable[[Any, Any], Any]
    source_type: str = "S"
    target_type: str = "A"

    def __call__(self, value: Any) -> Any:
        """Apply forward pass."""
        return self.forward(value)


def compose_lenses(outer: Lens, inner: Lens) -> Lens:
    """
    Compose two lenses: focus through outer, then inner.

    If outer focuses S on A, and inner focuses A on B,
    the result focuses S on B.
    """
    return Lens(
        name=f"{inner.name}.{outer.name}",
        get=lambda s: inner.get(outer.get(s)),
        put=lambda s, b: outer.put(s, inner.put(outer.get(s), b)),
        source_type=outer.source_type,
        target_type=inner.target_type,
    )


def compose_prisms(outer: Prism, inner: Prism) -> Prism:
    """
    Compose two prisms.
    """
    def composed_match(s):
        ok1, result1 = outer.match(s)
        if not ok1:
            return (False, result1)
        ok2, result2 = inner.match(result1)
        if not ok2:
            return (False, s)
        return (True, result2)

    return Prism(
        name=f"{inner.name}.{outer.name}",
        match=composed_match,
        build=lambda b: outer.build(inner.build(b)),
        source_type=outer.source_type,
        target_type=inner.target_type,
    )


def compose_optics(outer: Optic, inner: Optic) -> Optic:
    """
    Compose two optics: outer then inner on forward, inner then outer on backward.
    """
    return Optic(
        name=f"{inner.name}.{outer.name}",
        forward=lambda s: inner.forward(outer.forward(s)),
        backward=lambda s, b: outer.backward(s, inner.backward(outer.forward(s), b)),
        source_type=outer.source_type,
        target_type=inner.target_type,
    )


def lens_from_key(key: str) -> Lens:
    """Create a lens that focuses on a dictionary key."""
    return Lens(
        name=f"key[{key}]",
        get=lambda d: d[key],
        put=lambda d, v: {**d, key: v},
        source_type="Dict",
        target_type="value",
    )


def lens_from_index(idx: int) -> Lens:
    """Create a lens that focuses on a list index."""
    return Lens(
        name=f"idx[{idx}]",
        get=lambda lst: lst[idx],
        put=lambda lst, v: lst[:idx] + [v] + lst[idx + 1:],
        source_type="List",
        target_type="element",
    )


def lens_from_attr(attr: str) -> Lens:
    """Create a lens that focuses on an object attribute."""
    return Lens(
        name=f".{attr}",
        get=lambda obj: getattr(obj, attr),
        put=lambda obj, v: _set_attr_copy(obj, attr, v),
        source_type="object",
        target_type="attribute",
    )


def _set_attr_copy(obj, attr, value):
    """Set an attribute, returning a modified copy if possible."""
    import copy
    new_obj = copy.copy(obj)
    setattr(new_obj, attr, value)
    return new_obj


def optic_from_morphisms(
    category: Category,
    forward_id: str,
    backward_id: str,
) -> Optic:
    """
    Build an Optic from two Category morphisms (forward and backward).

    The forward morphism f: A -> B gives the forward pass.
    The backward morphism g: B -> A gives the backward pass (with residual = identity).
    """
    f = category.get_morphism(forward_id)
    g = category.get_morphism(backward_id)
    if f is None or g is None:
        raise ValueError(f"Morphism not found: {forward_id if f is None else backward_id}")

    def fwd(x):
        if f.is_callable:
            return f(x)
        return x

    def bwd(s, b):
        if g.is_callable:
            return g(b)
        return b

    return Optic(
        name=f"optic({f.name},{g.name})",
        forward=fwd,
        backward=bwd,
        source_type=f.source,
        target_type=f.target,
    )


def category_of_optics(base_cat: Category) -> Category:
    """
    Build a Category where objects are types and morphisms are optics.

    For each pair of morphisms f: A->B and g: B->A in base_cat,
    creates an optic morphism in the optics category.
    """
    optics_cat = Category(
        name=f"Optics({base_cat.name})",
        db_path=":memory:",
        quantale=base_cat.quantale,
    )

    # Objects are the same
    for obj in base_cat.objects():
        optics_cat.add(obj.name, type_name=obj.type_name)

    # For each pair of opposing morphisms, create an optic
    morphisms = base_cat.morphisms()
    mor_by_endpoints: Dict[Tuple[str, str], Morphism] = {}
    for m in morphisms:
        mor_by_endpoints[(m.source, m.target)] = m

    for (s, t), fwd_mor in mor_by_endpoints.items():
        bwd_mor = mor_by_endpoints.get((t, s))
        if bwd_mor is not None:
            optics_cat.connect(
                s, t,
                name=f"optic({fwd_mor.name})",
                confidence=min(fwd_mor.confidence, bwd_mor.confidence),
            )

    return optics_cat


def register_lens(category: Category, lens: Lens, source: str = None, target: str = None) -> Morphism:
    """Register a Lens in a category as a callable morphism."""
    src = source or lens.source_type
    tgt = target or lens.target_type
    if category.get(src) is None:
        category.add(src)
    if category.get(tgt) is None:
        category.add(tgt)
    return category.connect(src, tgt, name=lens.name, confidence=1.0, fn=lens.get)


def register_prism(category: Category, prism: Prism, source: str = None, target: str = None) -> Morphism:
    """Register a Prism in a category as a callable morphism."""
    src = source or prism.source_type
    tgt = target or prism.target_type
    if category.get(src) is None:
        category.add(src)
    if category.get(tgt) is None:
        category.add(tgt)
    return category.connect(src, tgt, name=prism.name, confidence=1.0,
                            fn=lambda x, _p=prism: _p.preview(x))


def register_optic(category: Category, optic: Optic, source: str = None, target: str = None) -> Morphism:
    """Register an Optic in a category as a callable morphism."""
    src = source or optic.source_type
    tgt = target or optic.target_type
    if category.get(src) is None:
        category.add(src)
    if category.get(tgt) is None:
        category.add(tgt)
    return category.connect(src, tgt, name=optic.name, confidence=1.0, fn=optic.forward)
