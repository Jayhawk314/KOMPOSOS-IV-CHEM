# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Algebraic Rewriting: DPO and SPO Graph Transformation

Graph transformation via category-theoretic rewriting rules.

A rewrite rule is a span L <- K -> R:
- L: left-hand side (pattern to match)
- K: interface (preserved structure)
- R: right-hand side (replacement)

Double Pushout (DPO): most restrictive, guarantees reversibility
Single Pushout (SPO): more permissive, handles dangling edges

Reference: Ehrig et al., "Fundamentals of Algebraic Graph Transformation" (2006)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from core.category import Category
from core.types import Object, Morphism


@dataclass
class Match:
    """A match of a pattern in a target category."""
    rule_name: str
    mapping: Dict[str, str]  # pattern object name -> target object name
    morphism_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class RewriteRule:
    """
    A rewrite rule as a span L <- K -> R.

    L: left-hand side (what to match)
    K: interface (what to preserve)
    R: right-hand side (what to create)

    The interface K is a sub-pattern common to both L and R.
    """
    name: str
    lhs: Category  # L
    interface: Category  # K
    rhs: Category  # R
    lhs_embedding: Dict[str, str] = field(default_factory=dict)  # K -> L
    rhs_embedding: Dict[str, str] = field(default_factory=dict)  # K -> R


def match(rule: RewriteRule, target: Category) -> List[Match]:
    """
    Find all matches of a rule's LHS in the target category.

    A match is an injective mapping from LHS objects to target objects
    that preserves morphism structure.
    """
    lhs_objects = rule.lhs.objects()
    lhs_morphisms = rule.lhs.morphisms()
    target_objects = target.objects()

    if not lhs_objects:
        return []

    matches: List[Match] = []

    # Try all injective mappings from LHS objects to target objects
    def _find_matches(
        remaining: List[Object],
        current_map: Dict[str, str],
        used: Set[str],
    ):
        if not remaining:
            # Verify morphism structure
            valid = True
            mor_map = {}
            for lhs_mor in lhs_morphisms:
                src = current_map.get(lhs_mor.source)
                tgt = current_map.get(lhs_mor.target)
                if src is None or tgt is None:
                    valid = False
                    break
                # Check that target has a morphism from src to tgt
                target_mors = target.morphisms_from(src)
                found = False
                for tm in target_mors:
                    if tm.target == tgt:
                        mor_map[lhs_mor.id] = tm.id
                        found = True
                        break
                if not found:
                    valid = False
                    break

            if valid:
                matches.append(Match(
                    rule_name=rule.name,
                    mapping=dict(current_map),
                    morphism_mapping=mor_map,
                ))
            return

        obj = remaining[0]
        rest = remaining[1:]

        for tgt_obj in target_objects:
            if tgt_obj.name not in used:
                current_map[obj.name] = tgt_obj.name
                used.add(tgt_obj.name)
                _find_matches(rest, current_map, used)
                del current_map[obj.name]
                used.discard(tgt_obj.name)

    _find_matches(lhs_objects, {}, set())
    return matches


def apply_dpo(
    rule: RewriteRule,
    m: Match,
    target: Category,
) -> Category:
    """
    Apply a rewrite rule via Double Pushout (DPO).

    1. Remove matched LHS elements (not in interface K)
    2. Add RHS elements (not in interface K)
    3. Preserve interface elements

    Returns a new Category with the transformation applied.
    """
    result = Category(
        name=f"{target.name}_rewritten",
        db_path=":memory:",
        quantale=target.quantale,
    )

    # Determine what to keep from target
    matched_objs = set(m.mapping.values())
    interface_objs = set()
    for k_name in rule.interface.objects():
        l_name = rule.lhs_embedding.get(k_name.name, k_name.name)
        t_name = m.mapping.get(l_name)
        if t_name:
            interface_objs.add(t_name)

    # Objects to remove: matched but not in interface
    remove_objs = matched_objs - interface_objs

    # Copy all target objects except removed ones
    for obj in target.objects():
        if obj.name not in remove_objs:
            result.add(obj.name, type_name=obj.type_name,
                      metadata=dict(obj.metadata))

    # Copy all target morphisms except those touching removed objects
    for mor in target.morphisms():
        if mor.source not in remove_objs and mor.target not in remove_objs:
            if mor.id not in m.morphism_mapping.values():
                result.connect(
                    mor.source, mor.target,
                    name=mor.name, confidence=mor.confidence,
                )

    # Add RHS objects not in interface
    rhs_to_target: Dict[str, str] = {}
    for k_obj in rule.interface.objects():
        r_name = rule.rhs_embedding.get(k_obj.name, k_obj.name)
        l_name = rule.lhs_embedding.get(k_obj.name, k_obj.name)
        t_name = m.mapping.get(l_name)
        if t_name:
            rhs_to_target[r_name] = t_name

    for rhs_obj in rule.rhs.objects():
        if rhs_obj.name not in rhs_to_target:
            new_name = f"{rhs_obj.name}_{rule.name}"
            rhs_to_target[rhs_obj.name] = new_name
            result.add(new_name, type_name=rhs_obj.type_name)

    # Add RHS morphisms
    for rhs_mor in rule.rhs.morphisms():
        src = rhs_to_target.get(rhs_mor.source)
        tgt = rhs_to_target.get(rhs_mor.target)
        if src and tgt:
            result.connect(src, tgt, name=rhs_mor.name,
                         confidence=rhs_mor.confidence)

    return result


def apply_spo(
    rule: RewriteRule,
    m: Match,
    target: Category,
) -> Category:
    """
    Apply a rewrite rule via Single Pushout (SPO).

    More permissive than DPO: removes dangling edges automatically.
    """
    result = Category(
        name=f"{target.name}_rewritten",
        db_path=":memory:",
        quantale=target.quantale,
    )

    # Remove all matched LHS objects (SPO removes dangling)
    matched_objs = set(m.mapping.values())
    interface_objs = set()
    for k_name in rule.interface.objects():
        l_name = rule.lhs_embedding.get(k_name.name, k_name.name)
        t_name = m.mapping.get(l_name)
        if t_name:
            interface_objs.add(t_name)

    remove_objs = matched_objs - interface_objs

    # Copy surviving structure
    for obj in target.objects():
        if obj.name not in remove_objs:
            result.add(obj.name, type_name=obj.type_name)

    for mor in target.morphisms():
        if mor.source not in remove_objs and mor.target not in remove_objs:
            result.connect(mor.source, mor.target,
                         name=mor.name, confidence=mor.confidence)

    # Add RHS
    rhs_to_target: Dict[str, str] = {}
    for k_obj in rule.interface.objects():
        r_name = rule.rhs_embedding.get(k_obj.name, k_obj.name)
        l_name = rule.lhs_embedding.get(k_obj.name, k_obj.name)
        t_name = m.mapping.get(l_name)
        if t_name:
            rhs_to_target[r_name] = t_name

    for rhs_obj in rule.rhs.objects():
        if rhs_obj.name not in rhs_to_target:
            new_name = f"{rhs_obj.name}_{rule.name}"
            rhs_to_target[rhs_obj.name] = new_name
            result.add(new_name, type_name=rhs_obj.type_name)

    for rhs_mor in rule.rhs.morphisms():
        src = rhs_to_target.get(rhs_mor.source)
        tgt = rhs_to_target.get(rhs_mor.target)
        if src and tgt:
            result.connect(src, tgt, name=rhs_mor.name,
                         confidence=rhs_mor.confidence)

    return result


def rewrite_system(
    rules: List[RewriteRule],
    target: Category,
    strategy: str = "parallel",
    max_steps: int = 10,
) -> Category:
    """
    Apply multiple rewrite rules to a target category.

    Strategies:
    - "parallel": apply all matching rules simultaneously
    - "sequential": apply rules one at a time in order
    """
    current = target

    for step in range(max_steps):
        applied = False

        if strategy == "sequential":
            for rule in rules:
                matches = match(rule, current)
                if matches:
                    current = apply_dpo(rule, matches[0], current)
                    applied = True
                    break
        else:  # parallel
            for rule in rules:
                matches = match(rule, current)
                if matches:
                    current = apply_dpo(rule, matches[0], current)
                    applied = True

        if not applied:
            break

    return current
