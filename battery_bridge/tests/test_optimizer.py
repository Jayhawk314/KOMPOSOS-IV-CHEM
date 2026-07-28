# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

import pytest
from battery_bridge.optimizer import BatteryOptimizer

def test_battery_optimizer_basic():
    optimizer = BatteryOptimizer()

    # Current collectors are not active materials even though old class labels
    # encoded their electrode side.
    assert "Al_foil" not in [m.name for m in optimizer.cathodes]
    assert "Cu_foil" not in [m.name for m in optimizer.anodes]
    
    # Test Elite Sweep (Stage 1)
    results = optimizer.optimize(
        fixed_components={"cell_type": "liquid"},
        pfas_free_only=False,
        enable_discovery=False,
        limit=5
    )
    
    assert len(results) > 0
    assert results[0].type == "Elite"
    assert 0.0 < results[0].interface_coverage <= 1.0
    assert results[0].to_dict()["coverage_complete"] == (
        results[0].interface_coverage == 1.0
    )
    print(f"Top Elite: {results[0].cathode} / {results[0].anode} / {results[0].electrolyte} (ED={results[0].energy_density})")

def test_battery_optimizer_pfas_free():
    optimizer = BatteryOptimizer()
    
    results = optimizer.optimize(
        fixed_components={"cell_type": "liquid"},
        pfas_free_only=True,
        enable_discovery=False
    )
    
    for res in results:
        assert res.binder != "PVDF"
        assert res.binder != "PTFE"
        assert res.is_pfas_free is True

def test_battery_optimizer_discovery():
    optimizer = BatteryOptimizer()

    results = optimizer.optimize(
        fixed_components={"cell_type": "solid", "cathode": "NMC811"},
        enable_discovery=True,
        limit=10
    )

    discoveries = [r for r in results if r.type == "Discovery"]
    assert discoveries, "enabled refinement must produce a visible discovery result"
    assert all(r.mp_id for r in discoveries)
    assert all(r.interface_coverage > 0 for r in discoveries)

if __name__ == "__main__":
    test_battery_optimizer_basic()
    test_battery_optimizer_pfas_free()
    test_battery_optimizer_discovery()
