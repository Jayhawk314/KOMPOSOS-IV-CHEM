# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Cross-Bridge Functors
======================

Connects material bridges across domains, enabling the replicator to reason
about multi-domain material combinations.

Available functors:
- battery_polymer: Battery electrode <-> Polymer binder/electrolyte
- battery_metal: Battery electrode <-> Metal current collector
- ceramic_metal: Ceramic coating <-> Metal substrate

Multi-domain analyzer:
- MultiDomainAnalyzer: Spans 3+ bridges in a single query
"""

__version__ = '1.0.0'

from cross_bridge.battery_polymer import (
    score_polymer_electrode_compatibility,
    BatteryPolymerResult,
    KNOWN_GOOD_PAIRS as BATTERY_POLYMER_GOOD_PAIRS,
    KNOWN_BAD_PAIRS as BATTERY_POLYMER_BAD_PAIRS,
)

from cross_bridge.battery_metal import (
    score_collector_compatibility,
    BatteryMetalResult,
    KNOWN_GOOD_PAIRS as BATTERY_METAL_GOOD_PAIRS,
    KNOWN_BAD_PAIRS as BATTERY_METAL_BAD_PAIRS,
)

from cross_bridge.ceramic_metal import (
    score_coating_compatibility,
    CeramicMetalResult,
    KNOWN_GOOD_PAIRS as CERAMIC_METAL_GOOD_PAIRS,
    KNOWN_BAD_PAIRS as CERAMIC_METAL_BAD_PAIRS,
)

from cross_bridge.multi_domain import (
    MultiDomainAnalyzer,
    MultiDomainQuery,
    MultiDomainComponent,
    MultiDomainAnalysis,
    CrossDomainScore,
    SOLID_STATE_BATTERY_QUERY,
    LFP_STANDARD_CELL_QUERY,
    GRAPHITE_ANODE_QUERY,
    THERMAL_BARRIER_QUERY,
)

__all__ = [
    # Battery-Polymer functor
    'score_polymer_electrode_compatibility',
    'BatteryPolymerResult',
    # Battery-Metal functor
    'score_collector_compatibility',
    'BatteryMetalResult',
    # Ceramic-Metal functor
    'score_coating_compatibility',
    'CeramicMetalResult',
    # Multi-domain analyzer
    'MultiDomainAnalyzer',
    'MultiDomainQuery',
    'MultiDomainComponent',
    'MultiDomainAnalysis',
    'CrossDomainScore',
    # Pre-defined queries
    'SOLID_STATE_BATTERY_QUERY',
    'LFP_STANDARD_CELL_QUERY',
    'GRAPHITE_ANODE_QUERY',
    'THERMAL_BARRIER_QUERY',
]
