# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""KOMPOSOS-IV Core: The Fused Categorical Runtime."""

from .types import Object, Morphism, Path, HigherMorphism, EquivalenceClass, Cone, Cocone
from .enrichment import (
    MonoidalStructure,
    MULTIPLICATIVE_QUANTALE,
    ADDITIVE_QUANTALE,
    PROBABILISTIC_QUANTALE,
    MAX_QUANTALE,
    MIN_QUANTALE,
    get_quantale,
)
from .category import Category
from .bridge import Bridge
from .hooks import HookRegistry
from .functor import Functor, NaturalTransformation
from .adjunction import Adjunction, adjunction_from_hom_iso, free_forgetful
from .limits import (
    product,
    coproduct,
    equalizer,
    pullback,
    pushout,
    terminal,
    initial,
)
from .gray_coherence import (
    GrayCategoryLayer,
    CoherenceVulnerabilityMapper,
    MythosRace,
    CoherenceGapType,
    TwoCellProxy,
    VulnerabilityCandidate,
    Modification,
    SoftwareCategoryBuilder,
)
from .gray_coherence_bridge import (
    MythosShield,
    build_shield,
    GapFinding,
    ShieldReport,
)

__all__ = [
    "Object",
    "Morphism",
    "Path",
    "HigherMorphism",
    "EquivalenceClass",
    "Cone",
    "Cocone",
    "MonoidalStructure",
    "MULTIPLICATIVE_QUANTALE",
    "ADDITIVE_QUANTALE",
    "PROBABILISTIC_QUANTALE",
    "MAX_QUANTALE",
    "MIN_QUANTALE",
    "get_quantale",
    "Category",
    "Bridge",
    "HookRegistry",
    "Functor",
    "NaturalTransformation",
    "Adjunction",
    "adjunction_from_hom_iso",
    "free_forgetful",
    "product",
    "coproduct",
    "equalizer",
    "pullback",
    "pushout",
    "terminal",
    "initial",
    "GrayCategoryLayer",
    "CoherenceVulnerabilityMapper",
    "MythosRace",
    "CoherenceGapType",
    "TwoCellProxy",
    "VulnerabilityCandidate",
    "Modification",
    "SoftwareCategoryBuilder",
    "MythosShield",
    "build_shield",
    "GapFinding",
    "ShieldReport",
]
