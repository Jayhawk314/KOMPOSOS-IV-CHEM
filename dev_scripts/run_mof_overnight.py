# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

from mof_bridge.linker_screening import LinkerScreener, LinkerScreeningSpec
import json
spec = LinkerScreeningSpec(
    application_context="custom",
    num_candidates=25000,
    require_all_agree=False,
    allow_hollow=True,
    ranking_mode="morphism_integrity",
)
screener = LinkerScreener()
result = screener.screen(spec)
with open("overnight_mof_results.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)
print("Saved to overnight_mof_results.json")
