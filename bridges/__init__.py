# SPDX-License-Identifier: Apache-2.0 OR LicenseRef-KOMPOSOS-IV-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-IV Commercial License (see LICENSE-COMMERCIAL file)

"""
Orion-KOMPOSOS-COG-OPTIMUS Bridge Plugins

Integrates the four-layer architecture:
- Orion (application framework)
- KOMPOSOS-IV (mathematical runtime)
- COG (cognitive co-processor)
- OPTIMUS (categorical gradient descent / self-refinement)
"""

__version__ = "0.3.0"

from .cyber_security_bridge import CyberSecurityBridge, ThreatIntelligence, build_cyber_bridge
from .math_discovery_bridge import DiscoveryResult, MathDiscoveryBridge

ORION_PLUGINS_AVAILABLE = True

try:
    from .cog_reasoning import CogReasoningPlugin
    from .knowledge_manager import KnowledgeManagerPlugin
    from .session_manager import SessionManagerPlugin
    from .optimus_plugin import OptimusPlugin
    from .telemetry_plugin import TelemetryPlugin
    from .infinity_cosmos_plugin import InfinityCosmosPlugin
    from .activity_system_plugin import ActivitySystemPlugin
except ModuleNotFoundError as exc:
    if exc.name != "orion_core":
        raise
    ORION_PLUGINS_AVAILABLE = False
    CogReasoningPlugin = None
    KnowledgeManagerPlugin = None
    SessionManagerPlugin = None
    OptimusPlugin = None
    TelemetryPlugin = None
    InfinityCosmosPlugin = None
    ActivitySystemPlugin = None

__all__ = [
    "CyberSecurityBridge",
    "ThreatIntelligence",
    "build_cyber_bridge",
    "DiscoveryResult",
    "MathDiscoveryBridge",
    "ORION_PLUGINS_AVAILABLE",
    "CogReasoningPlugin",
    "KnowledgeManagerPlugin",
    "SessionManagerPlugin",
    "OptimusPlugin",
    "TelemetryPlugin",
    "InfinityCosmosPlugin",
    "ActivitySystemPlugin",
]
