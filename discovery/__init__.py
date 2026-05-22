# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2024-2026 James Ray Hawkins
#
# Discovery pipeline -- math discovery engine, treasure hunting,
# conjecture generation, and hole navigation.
#
# Scripts in this package were ported from KOMPOSOS-IV-DISCOVERY.
# They expect PYTHONPATH to include the KOMPOSOS-IV directory
# (so that `from core.category import Category` etc. work).
#
# The IntegratedDiscoveryPipeline wires discovery output through
# COG verification, OPTIMUS refinement, and DualEngine classification.

from discovery.pipeline import IntegratedDiscoveryPipeline, PipelineResult

__all__ = ["IntegratedDiscoveryPipeline", "PipelineResult"]
