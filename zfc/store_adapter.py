# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Store Adapter -- Bridge between KomposOSStore and ZFC Engine

This is the ONLY file that imports both data.store and zfc internals.
All other zfc/ modules remain stdlib-only.

Mapping:
    StoredObject  -->  ZFSet   (name, metadata in .data)
    type_name     -->  container ZFSet (elements = all objects of that type)
    StoredMorphism -->  Relation (grouped by morphism name)
    (source, target) of morphism --> pair in the Relation

Theory construction:
    Auto-discovers chainable relation pairs from the graph and builds
    transitivity axioms.  Domain-agnostic -- no hardcoded relation names.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .universe import Universe, ZFSet, Relation, zfset, relation
from .logic import (
    Formula, Model, Theory, LogicOracle,
    atom, neg, conj, implies, forall, var, const,
)
from .well_ordering import OrdinalOracle, well_order_by_relation


# Known mutually-exclusive relation pairs (domain-agnostic standard)
_EXCLUSION_PAIRS = [
    ("inhibits", "activates"),
    ("upregulates", "downregulates"),
    ("agonist", "antagonist"),
    ("promotes", "suppresses"),
    ("increases", "decreases"),
]


def store_to_universe(store, limit: int = 100_000,
                      materialize_compositions: bool = True) -> Universe:
    """
    Convert KomposOSStore contents to a ZFC Universe.

    Args:
        store: KomposOSStore instance
        limit: max objects/morphisms to load
        materialize_compositions: if True, compute R;S for every
            chainable pair of relations (makes transitivity axioms consistent)

    Returns:
        Universe populated with ZFSets and Relations
    """
    V = Universe("StoreUniverse")

    # --- Objects -> ZFSets ---
    objects = store.list_objects(limit=limit)
    type_groups: Dict[str, List[str]] = defaultdict(list)

    for obj in objects:
        data = dict(obj.metadata) if obj.metadata else {}
        data["type_name"] = obj.type_name
        data["provenance"] = obj.provenance
        s = zfset(obj.name, **data)
        V.add_set(s)
        type_groups[obj.type_name].append(obj.name)

    # Create container sets for each type (e.g., "Drug", "Protein")
    for type_name, member_names in type_groups.items():
        container = zfset(type_name, elements=set(member_names))
        V.add_set(container)

    # --- Morphisms -> Relations ---
    morphisms = store.list_morphisms(limit=limit)
    rel_groups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for mor in morphisms:
        rel_groups[mor.name].append((mor.source_name, mor.target_name))

    for rel_name, pairs in rel_groups.items():
        rel = relation(rel_name, pairs)
        V.add_relation(rel)

    # --- Materialize composed relations ---
    # For every pair of relations (R, S) where R's targets overlap with
    # S's sources, compute R;S and add it to the universe.  This makes
    # the transitivity axioms satisfiable in the model.
    if materialize_compositions:
        base_rels = list(V.relations.values())
        for R in base_rels:
            for S in base_rels:
                # Check overlap: any target of R is a source of S?
                r_targets = {b for (_, b) in R.pairs}
                s_sources = {a for (a, _) in S.pairs}
                if r_targets & s_sources:
                    composed_name = f"{R.name};{S.name}"
                    if composed_name not in V.relations:
                        V.compose_relations(R, S)

    return V


def store_to_model(store, limit: int = 100_000) -> Model:
    """
    Build a ZFC Model from the store.

    The Model wraps a Universe and provides an interpretation
    for formula satisfaction checking.
    """
    universe = store_to_universe(store, limit=limit)
    return Model(universe=universe)


def build_transitivity_theory(store, limit: int = 100_000) -> Theory:
    """
    Auto-discover chainable relation pairs and build a Theory.

    For each pair of relation types (R, S) where some target of R
    is also a source of S, adds:
        forall x,y,z: R(x,y) & S(y,z) => (R;S)(x,z)

    Also adds mutual exclusion axioms for known incompatible pairs.

    Args:
        store: KomposOSStore instance
        limit: max morphisms to scan

    Returns:
        Theory with transitivity and exclusion axioms
    """
    T = Theory("StoreTheory")

    morphisms = store.list_morphisms(limit=limit)

    # Build relation -> {targets}, relation -> {sources}
    rel_targets: Dict[str, Set[str]] = defaultdict(set)
    rel_sources: Dict[str, Set[str]] = defaultdict(set)
    rel_names: Set[str] = set()

    for mor in morphisms:
        rel_names.add(mor.name)
        rel_targets[mor.name].add(mor.target_name)
        rel_sources[mor.name].add(mor.source_name)

    # Transitivity axioms: if R's targets overlap with S's sources
    for r_name in rel_names:
        for s_name in rel_names:
            overlap = rel_targets[r_name] & rel_sources[s_name]
            if overlap:
                # forall x,y,z: R(x,y) & S(y,z) => composed_R_S(x,z)
                # Name matches Universe.compose_relations format: (R;S)
                composed_name = f"({r_name};{s_name})"
                ax = forall("x", forall("y", forall("z",
                    implies(
                        conj(
                            atom(r_name, var("x"), var("y")),
                            atom(s_name, var("y"), var("z")),
                        ),
                        atom(composed_name, var("x"), var("z")),
                    )
                )))
                T.add_axiom(ax)

    # Mutual exclusion axioms
    for pos, neg_rel in _EXCLUSION_PAIRS:
        if pos in rel_names and neg_rel in rel_names:
            # forall x,y: R(x,y) => NOT S(x,y)
            ax = forall("x", forall("y",
                implies(
                    atom(pos, var("x"), var("y")),
                    neg(atom(neg_rel, var("x"), var("y"))),
                )
            ))
            T.add_axiom(ax)

    return T


def store_to_logic_oracle(store, limit: int = 100_000) -> LogicOracle:
    """
    Full pipeline: store -> Universe -> Model + Theory -> LogicOracle.

    Args:
        store: KomposOSStore instance
        limit: max objects/morphisms

    Returns:
        LogicOracle ready for prediction
    """
    model = store_to_model(store, limit=limit)
    theory = build_transitivity_theory(store, limit=limit)
    return LogicOracle(theory, model)


def store_to_ordinal_oracle(
    store,
    relation_name: Optional[str] = None,
    limit: int = 100_000,
) -> Optional[OrdinalOracle]:
    """
    Build an OrdinalOracle from the store.

    Uses the most-populated relation (or the one specified by name)
    to construct a well-ordering over the universe.

    Args:
        store: KomposOSStore instance
        relation_name: specific relation to order by (auto-detects if None)
        limit: max morphisms

    Returns:
        OrdinalOracle or None if no relations exist
    """
    universe = store_to_universe(store, limit=limit)

    if not universe.relations:
        return None

    if relation_name and relation_name in universe.relations:
        rel = universe.relations[relation_name]
    else:
        # Pick the relation with the most pairs
        rel = max(universe.relations.values(), key=lambda r: len(r.pairs))

    try:
        return OrdinalOracle(universe, rel)
    except Exception:
        return None


# --- Convenience: summary of what was loaded ---

def adapter_summary(store, limit: int = 100_000) -> Dict[str, Any]:
    """
    Summarize what the adapter would extract from a store.

    Useful for diagnostics without building the full ZFC structures.
    """
    objects = store.list_objects(limit=limit)
    morphisms = store.list_morphisms(limit=limit)

    type_counts: Dict[str, int] = defaultdict(int)
    for obj in objects:
        type_counts[obj.type_name] += 1

    rel_counts: Dict[str, int] = defaultdict(int)
    for mor in morphisms:
        rel_counts[mor.name] += 1

    return {
        "total_objects": len(objects),
        "total_morphisms": len(morphisms),
        "type_distribution": dict(type_counts),
        "relation_distribution": dict(rel_counts),
        "types": sorted(type_counts.keys()),
        "relations": sorted(rel_counts.keys()),
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from data import create_store

    # Try the drug repurposing store
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "store.db"
    )

    if os.path.exists(db_path):
        store = create_store(db_path)
        summary = adapter_summary(store)
        print("Store Adapter Summary")
        print("=" * 50)
        print(f"Objects:   {summary['total_objects']}")
        print(f"Morphisms: {summary['total_morphisms']}")
        print()
        print("Types:")
        for t, c in sorted(summary['type_distribution'].items(),
                           key=lambda x: -x[1]):
            print(f"  {t}: {c}")
        print()
        print("Relations:")
        for r, c in sorted(summary['relation_distribution'].items(),
                           key=lambda x: -x[1]):
            print(f"  {r}: {c}")
        print()

        # Build the ZFC structures
        V = store_to_universe(store)
        print(f"Universe: {V}")

        oracle = store_to_logic_oracle(store)
        print(f"LogicOracle ready: theory={oracle.theory}, model has {len(oracle.model.universe.sets)} sets")

        ordinal = store_to_ordinal_oracle(store)
        if ordinal:
            print(f"OrdinalOracle ready: well-order has {len(ordinal.well_order.elements)} elements")
        else:
            print("OrdinalOracle: no relations found")
    else:
        print(f"Store not found at {db_path}")
        print("Run with: python -m zfc.store_adapter")
