# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
KOMPOSOS Integration Layer for PFAS Bridge
============================================

Wires PFAS substances and replacement candidates into the KOMPOSOS-III
categorical infrastructure.

- Objects = PFAS substances + replacement polymers
- Morphisms = "replaceable_by" edges with score data
- Category = Directed graph of replacement options
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from data.store import StoredObject, StoredMorphism
    STORE_AVAILABLE = True
except ImportError:
    STORE_AVAILABLE = False
    StoredObject = None
    StoredMorphism = None

try:
    from categorical.category import Category, Object, Morphism
    CATEGORY_AVAILABLE = True
except ImportError:
    CATEGORY_AVAILABLE = False

from pfas_bridge.pfas_registry import PFAS_REGISTRY, PFASSubstance
from pfas_bridge.replacement_scorer import (
    REPLACEMENT_MAP,
    ReplacementCandidate,
    UseCase,
    find_replacements,
)


def pfas_to_stored_object(substance: PFASSubstance) -> "StoredObject":
    """Convert a PFASSubstance to a StoredObject for the categorical store."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available")

    return StoredObject(
        name=substance.abbreviation,
        type_name=substance.category.value,
        metadata={
            "full_name": substance.name,
            "cas_number": substance.cas_number,
            "category": substance.category.value,
            "is_banned": substance.is_banned(),
            "is_restricted": substance.is_restricted(),
            "domain": "pfas_compliance",
        },
        provenance="pfas_bridge.pfas_registry",
    )


def replacement_to_stored_object(candidate: ReplacementCandidate) -> "StoredObject":
    """Convert a ReplacementCandidate to a StoredObject."""
    if not STORE_AVAILABLE or StoredObject is None:
        raise ImportError("StoredObject not available")

    return StoredObject(
        name=candidate.name,
        type_name="pfas_replacement",
        metadata={
            "use_case": candidate.use_case.value,
            "overall_score": candidate.overall_score,
            "performance_match": candidate.performance_match,
            "domain": "pfas_compliance",
        },
        provenance="pfas_bridge.replacement_scorer",
    )


def build_pfas_category(
    pfas_names: Optional[List[str]] = None,
    use_case: UseCase = UseCase.GENERAL,
) -> Optional["Category"]:
    """
    Build a Category object from PFAS substances and their replacements.

    Objects = PFAS substances + replacement candidates.
    Morphisms = "replaceable_by" edges (PFAS -> replacement) weighted
    by overall_score.
    """
    if not CATEGORY_AVAILABLE:
        return None

    cat = Category(name="PFASCompliance")

    # Add PFAS substances as objects
    names = pfas_names or list(PFAS_REGISTRY.keys())
    for name in names:
        if name not in PFAS_REGISTRY:
            continue
        sub = PFAS_REGISTRY[name]
        obj = Object(
            name=sub.abbreviation,
            type_info={
                "cas": sub.cas_number,
                "category": sub.category.value,
                "banned": sub.is_banned(),
            },
        )
        cat.add_object(obj)

    # Add replacement candidates and morphisms
    replacement_objects = {}
    for name in names:
        if name not in PFAS_REGISTRY:
            continue
        sub = PFAS_REGISTRY[name]
        candidates = find_replacements(sub.abbreviation, use_case)

        for cand in candidates:
            # Add replacement as object (deduplicate by name)
            if cand.name not in replacement_objects:
                rep_obj = Object(
                    name=cand.name,
                    type_info={
                        "type": "replacement",
                        "use_case": cand.use_case.value,
                        "score": cand.overall_score,
                    },
                )
                cat.add_object(rep_obj)
                replacement_objects[cand.name] = rep_obj

            # Add "replaceable_by" morphism
            src = cat.objects.get(sub.abbreviation)
            tgt = cat.objects.get(cand.name)
            if src and tgt:
                mor = Morphism(
                    name=f"replace_{sub.abbreviation}_with_{cand.name}",
                    source=src,
                    target=tgt,
                    data={
                        "type": "replaceable_by",
                        "overall_score": cand.overall_score,
                        "performance_match": cand.performance_match,
                        "use_case": cand.use_case.value,
                    },
                )
                cat.add_morphism(mor)

    return cat


if __name__ == "__main__":
    cat = build_pfas_category()
    if cat:
        print(f"PFAS Category: {len(cat.objects)} objects, "
              f"{len(cat.morphisms)} morphisms")
    else:
        print("Category module not available")
