# SPDX-License-Identifier: LicenseRef-Proprietary-Commercial
# SPDX-FileCopyrightText: 2026 James Hawkins <jhawk314@gmail.com>

"""
Mathematics Domain -- The Self-Referential Domain

Treats mathematics itself as a category: theorems as objects,
proofs/dependencies as morphisms. This is the reference domain
every other domain matches against.

The math kernel manages three independent Category instances
(MMLKG, LeanDojo, NaturalProofs) and runs convergent analysis
across them.
"""

from .schema import (
    THEOREM_TYPE,
    DEFINITION_TYPE,
    AXIOM_TYPE,
    LEMMA_TYPE,
    CONJECTURE_TYPE,
    PROOF_TYPE,
    theorem_object,
    definition_object,
    axiom_object,
    lemma_object,
    conjecture_object,
    proof_morphism,
)

__all__ = [
    "THEOREM_TYPE",
    "DEFINITION_TYPE",
    "AXIOM_TYPE",
    "LEMMA_TYPE",
    "CONJECTURE_TYPE",
    "PROOF_TYPE",
    "theorem_object",
    "definition_object",
    "axiom_object",
    "lemma_object",
    "conjecture_object",
    "proof_morphism",
]
