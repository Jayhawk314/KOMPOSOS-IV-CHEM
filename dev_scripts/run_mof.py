# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
spec = LinkerScreeningSpec(
    application_context="custom",
    num_candidates=5000,
    require_all_agree=False,
    allow_hollow=True,
)
screener = LinkerScreener()
result = screener.screen(spec)
print("DONE")