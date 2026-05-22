# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
KOMPOSOS-III Categorical Engine (Layer A)

Category theory foundations:
- Base categories with objects and morphisms
- Sheaves for multi-source data consistency
- Kan extensions for prediction (Lan) and synthesis (Ran)
- Para bicategory for parametric maps
- Grothendieck fibrations with Cartesian lifts
- Lenses and optics for forward/backward duality
"""

from .category import Object, Morphism, Category
from .kan_extensions import Functor, LeftKanExtension, RightKanExtension
from .streaming_kan import StreamingKanExtension
from .right_kan import RightKanExtension as StructuralRightKanExtension

try:
    from .optics import register_lens, register_prism, register_optic
    from .para import Para
    from .markov import MarkovCategory
    from .deep_learning import NeuralCategory
    from .poly import register_system, run_traced, category_of_systems
    from .double_categories import DoubleCategory
except ImportError:
    register_lens = register_prism = register_optic = None
    Para = MarkovCategory = NeuralCategory = DoubleCategory = None
    register_system = run_traced = category_of_systems = None

__all__ = [
    "Object",
    "Morphism",
    "Category",
    "Functor",
    "LeftKanExtension",
    "RightKanExtension",
    "StreamingKanExtension",
    "StructuralRightKanExtension",
    "Para",
    "MarkovCategory",
    "NeuralCategory",
    "DoubleCategory",
    "register_lens",
    "register_prism",
    "register_optic",
    "register_system",
    "run_traced",
    "category_of_systems",
]
