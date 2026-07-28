# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Constraint-Based Molecular Search
====================================

Filters molecules by exact structural constraints. Never hallucinates —
returns ONLY molecules that exist in the curated database and match ALL
constraints.

This directly addresses Prof. Heather Kulik's (MIT) challenge:
    "I constantly ask LLMs: design me a ligand with exactly 22 heavy atoms.
     I can never get an answer that has 22 atoms."

KOMPOSOS doesn't generate text — it searches real molecular data with
exact constraint satisfaction.

Usage:
    from molecular_bridge.constraint_search import search_by_constraints

    # Kulik's 22-atom challenge
    results = search_by_constraints(heavy_atom_count=22)

    # Range query: 5-10 heavy atoms, no fluorine
    results = search_by_constraints(
        heavy_atom_range=(5, 10),
        exclude_elements=["F"],
    )
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from molecular_bridge.molecule_properties import (
    ALL_MOLECULES,
    Molecule,
    MoleculeClass,
)


# ---------------------------------------------------------------------------
# Heavy atom counting from molecular formula
# ---------------------------------------------------------------------------

_ELEMENT_RE = re.compile(r'([A-Z][a-z]?)(\d*)')


def count_heavy_atoms_from_formula(formula: str) -> int:
    """Count non-hydrogen atoms from a molecular formula.

    Handles standard chemical formulas like 'C3H4O3', 'LiPF6',
    'C8HF15O2'.  Parenthesized groups like '(NO3)3' are also handled.

    Args:
        formula: Chemical formula string.

    Returns:
        Number of non-hydrogen atoms (heavy atoms).
    """
    # Expand parenthesized groups: (NO3)3 -> N1O3 * 3 = N3O9
    expanded = _expand_parentheses(formula)

    total = 0
    for match in _ELEMENT_RE.finditer(expanded):
        element = match.group(1)
        count_str = match.group(2)
        count = int(count_str) if count_str else 1

        if element and element != 'H':
            total += count

    return total


def _expand_parentheses(formula: str) -> str:
    """Recursively expand parenthesized groups in a formula."""
    while '(' in formula:
        # Find innermost parenthetical group
        inner = re.search(r'\(([^()]+)\)(\d*)', formula)
        if not inner:
            break
        group = inner.group(1)
        multiplier = int(inner.group(2)) if inner.group(2) else 1
        expanded = _multiply_group(group, multiplier)
        formula = formula[:inner.start()] + expanded + formula[inner.end():]
    return formula


def _multiply_group(group: str, multiplier: int) -> str:
    """Multiply element counts in a formula group."""
    result_parts = []
    for match in _ELEMENT_RE.finditer(group):
        element = match.group(1)
        count_str = match.group(2)
        if not element:
            continue
        count = int(count_str) if count_str else 1
        result_parts.append(f"{element}{count * multiplier}")
    return ''.join(result_parts)


def get_heavy_atom_count(mol: Molecule) -> int:
    """Get heavy atom count for a molecule.

    Counts non-hydrogen atoms from the molecular formula.
    """
    return count_heavy_atoms_from_formula(mol.formula)


# ---------------------------------------------------------------------------
# Element extraction from formula
# ---------------------------------------------------------------------------

def _get_elements_in_formula(formula: str) -> set:
    """Extract set of element symbols from a formula string."""
    expanded = _expand_parentheses(formula)
    elements = set()
    for match in _ELEMENT_RE.finditer(expanded):
        element = match.group(1)
        if element:
            elements.add(element)
    return elements


# ---------------------------------------------------------------------------
# Constraint search
# ---------------------------------------------------------------------------

def search_by_constraints(
    heavy_atom_count: Optional[int] = None,
    heavy_atom_range: Optional[Tuple[int, int]] = None,
    functional_groups: Optional[List[str]] = None,
    molecular_weight_range: Optional[Tuple[float, float]] = None,
    exclude_elements: Optional[List[str]] = None,
    include_elements: Optional[List[str]] = None,
    molecule_class: Optional[MoleculeClass] = None,
) -> List[Molecule]:
    """Filter molecules by exact structural constraints.

    All constraints are combined with AND logic. Returns ONLY molecules
    that exist in the curated database and match ALL constraints.

    This function NEVER hallucinates. It returns an empty list if no
    molecules match — never a fabricated molecule.

    Args:
        heavy_atom_count: Exact number of non-H atoms.
        heavy_atom_range: Inclusive (min, max) range of heavy atoms.
        functional_groups: Must contain ALL listed groups.
        molecular_weight_range: Inclusive (min, max) MW in g/mol.
        exclude_elements: Exclude molecules containing any of these.
        include_elements: Must contain ALL of these elements.
        molecule_class: Filter by MoleculeClass enum.

    Returns:
        List of Molecule objects matching ALL constraints. May be empty.

    Example:
        >>> results = search_by_constraints(heavy_atom_count=6)
        >>> for mol in results:
        ...     print(f"{mol.name}: {mol.formula}")
    """
    results = list(ALL_MOLECULES.values())

    # Exact heavy atom count
    if heavy_atom_count is not None:
        results = [
            m for m in results
            if get_heavy_atom_count(m) == heavy_atom_count
        ]

    # Heavy atom count range
    if heavy_atom_range is not None:
        lo, hi = heavy_atom_range
        results = [
            m for m in results
            if lo <= get_heavy_atom_count(m) <= hi
        ]

    # Functional groups (AND)
    if functional_groups is not None:
        results = [
            m for m in results
            if all(fg in m.functional_groups for fg in functional_groups)
        ]

    # Molecular weight range
    if molecular_weight_range is not None:
        lo, hi = molecular_weight_range
        results = [
            m for m in results
            if lo <= m.molecular_weight <= hi
        ]

    # Exclude elements (use proper element parsing, not substring)
    if exclude_elements is not None:
        excl = set(exclude_elements)
        results = [
            m for m in results
            if not (_get_elements_in_formula(m.formula) & excl)
        ]

    # Include elements (must contain all, use proper element parsing)
    if include_elements is not None:
        incl = set(include_elements)
        results = [
            m for m in results
            if incl.issubset(_get_elements_in_formula(m.formula))
        ]

    # Molecule class
    if molecule_class is not None:
        results = [
            m for m in results
            if m.molecule_class == molecule_class
        ]

    return results


def get_atom_count_distribution() -> Dict[int, List[str]]:
    """Get a mapping of heavy_atom_count -> list of molecule names.

    Useful for understanding what counts are available in the database.
    """
    dist: Dict[int, List[str]] = {}
    for name, mol in ALL_MOLECULES.items():
        count = get_heavy_atom_count(mol)
        dist.setdefault(count, []).append(name)
    return dict(sorted(dist.items()))


if __name__ == "__main__":
    print("=" * 70)
    print("Molecular Constraint Search")
    print("=" * 70)

    dist = get_atom_count_distribution()
    print(f"\nHeavy atom count distribution ({len(ALL_MOLECULES)} molecules):")
    for count, names in dist.items():
        print(f"  {count:3d} atoms: {', '.join(names)}")

    print("\n--- Kulik's 22-atom challenge ---")
    results = search_by_constraints(heavy_atom_count=22)
    if results:
        for mol in results:
            print(f"  {mol.name} ({mol.formula}): {get_heavy_atom_count(mol)} heavy atoms")
    else:
        print("  No molecules with exactly 22 heavy atoms in database.")
        print("  (This is the CORRECT answer — not a hallucination.)")

    print("\n--- 5-10 heavy atoms, no fluorine ---")
    results = search_by_constraints(heavy_atom_range=(5, 10), exclude_elements=["F"])
    for mol in results:
        print(f"  {mol.name} ({mol.formula}): {get_heavy_atom_count(mol)} heavy atoms")
