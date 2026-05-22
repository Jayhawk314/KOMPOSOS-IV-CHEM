# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins

"""
Typed compatibility context for bridge scoring and audits.

The material pair alone is often not enough to make a reliable compatibility
claim.  This small schema carries the experimental/application context that
changes the answer: role, electrolyte, coating, voltage context, processing
route, compatibilizer, interface type, environment, and temperature.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


ROLE_SENSITIVE_BATTERY_POLYMERS = {"CMC", "SBR", "PEO"}
HIGH_VOLTAGE_CATHODE_NAMES = {"LCO", "LMO", "NMC111", "NMC532", "NMC622", "NMC811", "NCA"}


@dataclass(frozen=True)
class CompatibilityContext:
    """Optional typed context for material compatibility decisions."""

    role: Optional[str] = None
    electrolyte: Optional[str] = None
    voltage_context: Optional[str] = None
    coating: Optional[str] = None
    processing_route: Optional[str] = None
    compatibilizer: Optional[str] = None
    interface_type: Optional[str] = None
    environment: Optional[str] = None
    temperature_C: Optional[float] = None

    @classmethod
    def from_pair(cls, pair: Dict[str, Any]) -> "CompatibilityContext":
        """Build context from an audit/benchmark pair dictionary."""

        return cls(
            role=pair.get("role"),
            electrolyte=pair.get("electrolyte"),
            voltage_context=pair.get("voltage_context"),
            coating=pair.get("coating") or pair.get("metal_coating"),
            processing_route=pair.get("processing_route"),
            compatibilizer=pair.get("compatibilizer"),
            interface_type=pair.get("interface_type"),
            environment=pair.get("environment"),
            temperature_C=pair.get("temperature_C"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return only context fields that were explicitly provided."""

        values = {
            "role": self.role,
            "electrolyte": self.electrolyte,
            "voltage_context": self.voltage_context,
            "coating": self.coating,
            "processing_route": self.processing_route,
            "compatibilizer": self.compatibilizer,
            "interface_type": self.interface_type,
            "environment": self.environment,
            "temperature_C": self.temperature_C,
        }
        return {key: value for key, value in values.items() if value is not None}

    def missing_required_fields(self, domain: str, material_a: str, material_b: str) -> List[str]:
        """
        Return context fields needed before a high-confidence forced verdict.

        This is intentionally conservative.  It does not block legacy scorers;
        callers can choose whether missing fields cause a `needs_context`
        decision or simply lower confidence.
        """

        missing: List[str] = []
        domain_key = (domain or "").lower()

        if domain_key == "battery-metal":
            if not self.electrolyte:
                missing.append("electrolyte")
            if not self.role and not (
                material_a.endswith("_foil")
                or material_a.endswith("_tab")
                or material_b.endswith("_foil")
                or material_b.endswith("_tab")
            ):
                missing.append("role")

        elif domain_key == "battery-polymer":
            polymer = material_a if material_a in ROLE_SENSITIVE_BATTERY_POLYMERS else material_b
            battery = material_b if polymer == material_a else material_a
            high_voltage_name = battery in HIGH_VOLTAGE_CATHODE_NAMES or battery.startswith("NMC")
            if polymer in ROLE_SENSITIVE_BATTERY_POLYMERS and high_voltage_name and not self.role:
                missing.append("role")
            if polymer == "PEO" and not (self.role or self.voltage_context):
                missing.append("role_or_voltage_context")

        elif domain_key == "polymer":
            if self.compatibilizer is None and {
                material_a,
                material_b,
            } in ({"PE", "PET"}, {"HDPE", "PET"}):
                missing.append("compatibilizer")

        return missing
