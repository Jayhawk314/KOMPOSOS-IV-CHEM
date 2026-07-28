# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Dependency-free quantale utilities for enriched compatibility scoring."""

from dataclasses import dataclass
from functools import reduce
from typing import Any, Callable, Dict, Iterable, Mapping


@dataclass(frozen=True)
class MonoidalStructure:
    """
    Monoidal structure used as a quantale-like composition rule.

    Examples:
    - multiplicative: confidence along a path
    - probabilistic: failure-risk OR
    - min: bottleneck/weakest compatible axis
    - max: worst stress/cost axis
    - additive: accumulated cost
    """

    tensor: Callable[[float, float], float]
    unit: float
    compare: Callable[[float, float], bool]
    name: str

    def compose(self, values: Iterable[float]) -> float:
        return reduce(self.tensor, values, self.unit)


MULTIPLICATIVE_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a * b,
    unit=1.0,
    compare=lambda a, b: a >= b,
    name="multiplicative",
)

ADDITIVE_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: a + b,
    unit=0.0,
    compare=lambda a, b: a <= b,
    name="additive",
)

PROBABILISTIC_OR_QUANTALE = MonoidalStructure(
    tensor=lambda a, b: 1 - (1 - a) * (1 - b),
    unit=0.0,
    compare=lambda a, b: a <= b,
    name="probabilistic_or",
)

MAX_QUANTALE = MonoidalStructure(
    tensor=max,
    unit=0.0,
    compare=lambda a, b: a <= b,
    name="max",
)

MIN_QUANTALE = MonoidalStructure(
    tensor=min,
    unit=1.0,
    compare=lambda a, b: a >= b,
    name="min",
)

QUANTALE_REGISTRY: Dict[str, MonoidalStructure] = {
    "multiplicative": MULTIPLICATIVE_QUANTALE,
    "additive": ADDITIVE_QUANTALE,
    "probabilistic": PROBABILISTIC_OR_QUANTALE,
    "probabilistic_or": PROBABILISTIC_OR_QUANTALE,
    "max": MAX_QUANTALE,
    "min": MIN_QUANTALE,
}


def get_quantale(name: str) -> MonoidalStructure:
    """Look up a quantale composition rule by name."""

    if name not in QUANTALE_REGISTRY:
        raise KeyError(f"Unknown quantale: {name}. Valid: {sorted(QUANTALE_REGISTRY)}")
    return QUANTALE_REGISTRY[name]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compose_values(values: Iterable[float], quantale: str) -> float:
    """Compose values with a named quantale and clamp to [0, 1] where appropriate."""

    q = get_quantale(quantale)
    composed = q.compose(float(v) for v in values)
    if quantale in {"multiplicative", "probabilistic", "probabilistic_or", "max", "min"}:
        return round(clamp01(composed), 4)
    return round(composed, 4)


def summarize_compatibility_components(components: Mapping[str, float]) -> Dict[str, Any]:
    """
    Summarize component compatibility scores with multiple enriched views.

    This keeps weighted averages separate from the mathematical facts that one
    weak axis can bottleneck the interface and multiple medium risks compound.
    """

    clean = {name: clamp01(score) for name, score in components.items()}
    if not clean:
        return {
            "component_count": 0,
            "bottleneck_score": None,
            "failure_risk_or": None,
            "confidence_product": None,
            "weakest_axis": None,
        }

    weakest_axis = min(clean, key=clean.get)
    risks = [1.0 - score for score in clean.values()]
    return {
        "component_count": len(clean),
        "bottleneck_score": compose_values(clean.values(), "min"),
        "failure_risk_or": compose_values(risks, "probabilistic_or"),
        "confidence_product": compose_values(clean.values(), "multiplicative"),
        "weakest_axis": weakest_axis,
        "weakest_axis_score": round(clean[weakest_axis], 4),
    }

