# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Crystal Structure Deriver via Kan Extension over Materials Project

Derives crystal structure parameters (crystal system, space group, lattice
constants a/b/c/alpha/beta/gamma) for unknown compositions by Kan extension
over nearest known structures from the Materials Project.

This is the core competitive capability: every derived structure traces to
specific MP entries via specific Kan extension weights, giving full provenance.

Architecture:
    1. Parse formula -> composition vector
    2. Query spatial index for k nearest MP entries with lattice data
    3. Crystal system vote (IDW weighted, D-S fused)
    4. Space group vote (IDW, filtered to winning crystal system)
    5. Lattice parameter interpolation (IDW, filtered to same crystal system)
    6. Volume-per-atom cross-check
    7. Provenance chain: "Derived from mp-19017 (42%), mp-25048 (31%), ..."

Usage:
    deriver = StructureDeriver(mp_entries)
    result = deriver.derive("LiNi0.7Fe0.2Mn0.1O2")
    if result:
        print(f"{result.crystal_system} {result.space_group}")
        print(f"a={result.lattice_a:.3f} b={result.lattice_b:.3f} c={result.lattice_c:.3f}")
        print(f"Provenance: {result.provenance}")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .parser import parse_formula, composition_vector, SHORTHAND_MAP
from .spatial_index import CompositionIndex

try:
    from categorical.dempster_shafer import MassFunction, combine
    _HAS_DS = True
except ImportError:
    _HAS_DS = False


@dataclass
class NearestMP:
    """Info about a nearest MP entry used in derivation."""
    mp_id: str
    formula: str
    distance: float
    weight: float           # IDW weight (normalized, sums to 1)
    crystal_system: str
    space_group: str
    space_group_number: int


@dataclass
class DerivedStructure:
    """Crystal structure derived from nearest MP structures via Kan extension."""
    formula: str
    crystal_system: str
    space_group: str
    space_group_number: int
    lattice_a: float        # Angstrom
    lattice_b: float
    lattice_c: float
    lattice_alpha: float    # degrees
    lattice_beta: float
    lattice_gamma: float
    volume_per_atom: float  # Angstrom^3
    confidence: float       # 0-1
    nearest_mp: List[NearestMP]
    provenance: str         # Human-readable derivation chain

    def to_dict(self) -> Dict:
        return {
            "formula": self.formula,
            "crystal_system": self.crystal_system,
            "space_group": self.space_group,
            "space_group_number": self.space_group_number,
            "lattice_a": round(self.lattice_a, 4),
            "lattice_b": round(self.lattice_b, 4),
            "lattice_c": round(self.lattice_c, 4),
            "lattice_alpha": round(self.lattice_alpha, 2),
            "lattice_beta": round(self.lattice_beta, 2),
            "lattice_gamma": round(self.lattice_gamma, 2),
            "volume_per_atom": round(self.volume_per_atom, 3),
            "confidence": round(self.confidence, 3),
            "nearest_mp": [
                {
                    "mp_id": n.mp_id,
                    "formula": n.formula,
                    "distance": round(n.distance, 4),
                    "weight": round(n.weight, 4),
                    "crystal_system": n.crystal_system,
                    "space_group": n.space_group,
                }
                for n in self.nearest_mp
            ],
            "provenance": self.provenance,
        }


class StructureDeriver:
    """
    Derives crystal structure parameters via Kan extension over MP data.

    Builds a spatial index over MP entries with lattice data and uses
    inverse-distance-weighted interpolation to predict structure for
    unknown compositions.

    Args:
        mp_entries: List of MPEntry objects (must have lattice_a > 0).
        k: Number of nearest neighbors for Kan extension (default 7).
    """

    def __init__(self, mp_entries: List[Any], k: int = 7):
        self.k = k

        # Filter to entries with valid lattice data and crystal system
        self._entries = [
            e for e in mp_entries
            if (getattr(e, 'lattice_a', 0) > 0 and
                getattr(e, 'crystal_system', '') and
                len(getattr(e, 'vector', [])) > 0)
        ]

        # Build spatial index
        if self._entries:
            self._index = CompositionIndex(self._entries)
        else:
            self._index = None

    @property
    def size(self) -> int:
        """Number of indexed MP entries."""
        return len(self._entries)

    def derive(self, formula: str) -> Optional[DerivedStructure]:
        """
        Derive crystal structure for a chemical formula.

        Args:
            formula: Chemical formula or shorthand (e.g. "NMC721").

        Returns:
            DerivedStructure with lattice parameters and provenance,
            or None if insufficient data.
        """
        if self._index is None or self._index.size == 0:
            return None

        # Parse formula
        resolved = SHORTHAND_MAP.get(formula, formula)
        try:
            comp = parse_formula(resolved)
        except Exception:
            return None

        if not comp:
            return None

        query_vec = composition_vector(comp)

        # Find k nearest MP entries
        neighbours = self._index.nearest_k(query_vec, k=self.k)
        if not neighbours:
            return None

        # Compute IDW weights
        epsilon = 0.01
        raw_weights = [1.0 / (d + epsilon) for _, d in neighbours]
        total_w = sum(raw_weights)
        if total_w == 0:
            return None
        weights = [w / total_w for w in raw_weights]

        # Build NearestMP list
        nearest_mp = []
        for (entry, dist), w in zip(neighbours, weights):
            nearest_mp.append(NearestMP(
                mp_id=getattr(entry, 'mp_id', ''),
                formula=getattr(entry, 'formula', ''),
                distance=dist,
                weight=w,
                crystal_system=getattr(entry, 'crystal_system', ''),
                space_group=getattr(entry, 'space_group_symbol', ''),
                space_group_number=getattr(entry, 'space_group_number', 0),
            ))

        # Step 1: Crystal system vote (IDW weighted)
        crystal_system, cs_confidence = self._vote_crystal_system(nearest_mp)

        # Step 2: Space group vote (filtered to winning crystal system)
        space_group, sg_number, sg_confidence = self._vote_space_group(
            nearest_mp, crystal_system
        )

        # Step 3: Lattice parameter interpolation
        # Filter to same crystal system to avoid averaging cubic with hexagonal
        lattice_params = self._interpolate_lattice(
            neighbours, weights, crystal_system
        )

        # Step 4: Volume-per-atom estimate
        volume_per_atom = self._estimate_volume_per_atom(
            neighbours, weights, comp
        )

        # Overall confidence: combine system, group, and distance factors
        min_dist = neighbours[0][1]
        dist_factor = max(0.1, 1.0 - min_dist / 5.0)
        confidence = cs_confidence * 0.4 + sg_confidence * 0.3 + dist_factor * 0.3
        confidence = min(0.95, max(0.05, confidence))

        # Build provenance string
        provenance = self._build_provenance(nearest_mp)

        return DerivedStructure(
            formula=formula,
            crystal_system=crystal_system,
            space_group=space_group,
            space_group_number=sg_number,
            lattice_a=lattice_params['a'],
            lattice_b=lattice_params['b'],
            lattice_c=lattice_params['c'],
            lattice_alpha=lattice_params['alpha'],
            lattice_beta=lattice_params['beta'],
            lattice_gamma=lattice_params['gamma'],
            volume_per_atom=volume_per_atom,
            confidence=confidence,
            nearest_mp=nearest_mp,
            provenance=provenance,
        )

    def _vote_crystal_system(self, nearest_mp: List[NearestMP]
                              ) -> Tuple[str, float]:
        """IDW-weighted vote for crystal system."""
        votes: Dict[str, float] = {}
        for n in nearest_mp:
            cs = n.crystal_system.lower()
            if cs:
                votes[cs] = votes.get(cs, 0.0) + n.weight

        if not votes:
            return "unknown", 0.0

        winner = max(votes, key=votes.get)
        winner_weight = votes[winner]

        # Confidence: how concentrated is the vote?
        # If all neighbors agree, high confidence
        confidence = winner_weight  # Already normalized to [0,1]

        # D-S fusion for top two candidates if available
        if _HAS_DS and len(votes) >= 2:
            sorted_votes = sorted(votes.items(), key=lambda x: -x[1])
            top_conf = sorted_votes[0][1]
            second_conf = sorted_votes[1][1]

            frame = frozenset(["agree", "disagree"])
            agree = frozenset(["agree"])

            m1 = MassFunction(masses={
                agree: min(0.95, top_conf),
                frame: 1.0 - min(0.95, top_conf),
            })
            m2 = MassFunction(masses={
                agree: min(0.95, 1.0 - second_conf),
                frame: min(0.95, second_conf),
            })

            try:
                combined, _ = combine(m1, m2)
                confidence = combined.belief(agree)
            except ValueError:
                pass

        return winner, min(0.95, max(0.1, confidence))

    def _vote_space_group(self, nearest_mp: List[NearestMP],
                           crystal_system: str
                           ) -> Tuple[str, int, float]:
        """IDW-weighted vote for space group, filtered to winning crystal system."""
        votes: Dict[str, float] = {}
        sg_numbers: Dict[str, int] = {}

        for n in nearest_mp:
            if n.crystal_system.lower() == crystal_system.lower() and n.space_group:
                sg = n.space_group
                votes[sg] = votes.get(sg, 0.0) + n.weight
                sg_numbers[sg] = n.space_group_number

        if not votes:
            # Fall back to all neighbors
            for n in nearest_mp:
                if n.space_group:
                    sg = n.space_group
                    votes[sg] = votes.get(sg, 0.0) + n.weight
                    sg_numbers[sg] = n.space_group_number

        if not votes:
            return "", 0, 0.0

        winner = max(votes, key=votes.get)
        confidence = votes[winner]

        # Renormalize confidence by total weight of filtered neighbors
        total_filtered = sum(votes.values())
        if total_filtered > 0:
            confidence = votes[winner] / total_filtered

        return winner, sg_numbers.get(winner, 0), min(0.90, max(0.1, confidence))

    def _interpolate_lattice(self, neighbours: list, weights: list,
                              crystal_system: str) -> Dict[str, float]:
        """IDW interpolation of lattice parameters, filtered to same crystal system."""
        # Filter to same crystal system
        filtered = []
        filtered_w = []
        for (entry, dist), w in zip(neighbours, weights):
            cs = getattr(entry, 'crystal_system', '').lower()
            if cs == crystal_system.lower():
                filtered.append(entry)
                filtered_w.append(w)

        # Fall back to all neighbors if no same-system matches
        if not filtered:
            filtered = [e for e, _ in neighbours]
            filtered_w = list(weights)

        # Renormalize weights
        total_w = sum(filtered_w)
        if total_w == 0:
            return {'a': 0, 'b': 0, 'c': 0, 'alpha': 90, 'beta': 90, 'gamma': 90}
        filtered_w = [w / total_w for w in filtered_w]

        # IDW interpolation
        params = {'a': 0.0, 'b': 0.0, 'c': 0.0,
                  'alpha': 0.0, 'beta': 0.0, 'gamma': 0.0}

        for entry, w in zip(filtered, filtered_w):
            params['a'] += getattr(entry, 'lattice_a', 0.0) * w
            params['b'] += getattr(entry, 'lattice_b', 0.0) * w
            params['c'] += getattr(entry, 'lattice_c', 0.0) * w
            params['alpha'] += getattr(entry, 'lattice_alpha', 90.0) * w
            params['beta'] += getattr(entry, 'lattice_beta', 90.0) * w
            params['gamma'] += getattr(entry, 'lattice_gamma', 90.0) * w

        return params

    def _estimate_volume_per_atom(self, neighbours: list, weights: list,
                                   comp: Dict[str, float]) -> float:
        """Estimate volume per atom via IDW over neighbors."""
        total_atoms = sum(comp.values())
        if total_atoms == 0:
            return 0.0

        vpa_sum = 0.0
        vpa_weight = 0.0
        for (entry, dist), w in zip(neighbours, weights):
            entry_comp = getattr(entry, 'composition', {})
            entry_vol = getattr(entry, 'volume', 0.0)
            if entry_comp and entry_vol > 0:
                entry_atoms = sum(entry_comp.values())
                if entry_atoms > 0:
                    vpa = entry_vol / entry_atoms
                    vpa_sum += vpa * w
                    vpa_weight += w

        if vpa_weight > 0:
            return vpa_sum / vpa_weight
        return 0.0

    def _build_provenance(self, nearest_mp: List[NearestMP]) -> str:
        """Build human-readable provenance chain."""
        # Show top contributors (weight > 5%)
        significant = [n for n in nearest_mp if n.weight > 0.05]
        if not significant:
            significant = nearest_mp[:3]

        parts = []
        for n in significant:
            pct = n.weight * 100
            parts.append(f"{n.mp_id} ({pct:.0f}%)")

        return "Derived from " + ", ".join(parts)
