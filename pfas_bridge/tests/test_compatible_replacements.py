# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import pytest
from pfas_bridge.replacement_scorer import find_compatible_replacements, UseCase

def test_compatible_replacements():
    # PVDF as a battery binder, checked against a common electrolyte salt (LiPF6)
    results = find_compatible_replacements(
        pfas_name="PVDF",
        adjoining_material="LiPF6",
        use_case=UseCase.BATTERY_BINDER
    )
    
    assert len(results) > 0
    for cand, comp_res in results:
        assert cand.use_case == UseCase.BATTERY_BINDER
        if comp_res:
            assert comp_res.material_a in cand.name
            assert comp_res.material_b == "LiPF6"
            print(f"Candidate: {cand.name}, Compatibility: {comp_res.scores.get('total')}")

if __name__ == "__main__":
    test_compatible_replacements()
