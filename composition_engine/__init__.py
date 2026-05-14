# SPDX-License-Identifier: Apache-2.0 OR KOMPOSOS-III-Commercial
# Copyright (c) 2024-2026 James Ray Hawkins
#
# This file is dual-licensed. You may use it under either:
# 1. Apache License 2.0 (see LICENSE file), OR
# 2. KOMPOSOS-III Commercial License (see LICENSE-COMMERCIAL file)

"""
Composition Engine -- Predict properties of unknown material compositions.

Uses Kan extension over known compositions + rule-based estimates +
Dempster-Shafer fusion to predict voltage, capacity, density, thermal
stability for novel chemical formulas.

Example:
    from composition_engine.predictor import CompositionPredictor
    pred = CompositionPredictor()
    result = pred.predict("LiNi0.7Mn0.15Co0.15O2")
    print(result.properties["voltage"])  # ~3.85V
"""
