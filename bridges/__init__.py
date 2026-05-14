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

from .cog_reasoning import CogReasoningPlugin
from .knowledge_manager import KnowledgeManagerPlugin
from .session_manager import SessionManagerPlugin
from .optimus_plugin import OptimusPlugin
from .telemetry_plugin import TelemetryPlugin
from .infinity_cosmos_plugin import InfinityCosmosPlugin

__all__ = [
    "CogReasoningPlugin",
    "KnowledgeManagerPlugin",
    "SessionManagerPlugin",
    "OptimusPlugin",
    "TelemetryPlugin",
    "InfinityCosmosPlugin",
]
