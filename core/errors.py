# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Diagnostic exception types for the typed categorical runtime.

These exist to enforce the integrity discipline:

* An oracle that cannot produce a value RAISES ``OracleUnavailable`` -- it never
  returns a placeholder or a lower-quality value labelled as the real thing.
* Combining two quantities at incompatible levels of theory RAISES
  ``TheoryCompositionError`` -- the system never silently averages a B3LYP number
  with an experimental one, or a surrogate estimate with a DFT result.

Every exception carries machine-readable diagnostic fields (which oracle, which
theory levels) so callers and audit harnesses can react precisely instead of
parsing message strings.
"""

from __future__ import annotations

from typing import Any, Optional


class KomposorChemError(Exception):
    """Base class for all KOMPOSOS-IV-CHEM runtime errors."""


class OracleUnavailable(KomposorChemError):
    """Raised when an oracle cannot produce a value.

    The contract is: callers either catch this and downgrade the *claim*
    (e.g. fall back to a clearly different, separately-typed surrogate), or they
    propagate it. What they must NOT do is fabricate a value of the same
    morphism type.

    Attributes:
        oracle: name of the oracle that was unavailable.
        reason: short human-readable cause.
        remediation: optional hint on how to make it available.
    """

    def __init__(self, oracle: str, reason: str, remediation: Optional[str] = None):
        self.oracle = oracle
        self.reason = reason
        self.remediation = remediation
        msg = f"oracle '{oracle}' unavailable: {reason}"
        if remediation:
            msg += f" (remediation: {remediation})"
        super().__init__(msg)


class TheoryCompositionError(KomposorChemError):
    """Raised when quantities at incompatible levels of theory are combined.

    Attributes:
        left: the LevelOfTheory (or its label) of the first operand.
        right: the LevelOfTheory (or its label) of the second operand.
        operation: what was attempted (e.g. "add", "average", "compose").
    """

    def __init__(self, left: Any, right: Any, operation: str = "combine"):
        self.left = left
        self.right = right
        self.operation = operation
        super().__init__(
            f"refusing to {operation} quantities across mismatched levels of "
            f"theory: {left!s}  vs  {right!s}. Cross-level combination requires an "
            f"explicit, documented conversion (cartesian lift), not silent mixing."
        )


class ProvenancePromotionError(KomposorChemError):
    """Raised when a computational value is illegitimately promoted to measured.

    A ``provenance='computational'`` quantity may never be relabelled as
    ``'experimental'`` -- predicted is never asserted.
    """

    def __init__(self, frm: str, to: str):
        self.frm = frm
        self.to = to
        super().__init__(
            f"illegal provenance promotion {frm!r} -> {to!r}: predicted values "
            f"may not be asserted as measured."
        )
