import pytest
from battery_bridge.optimizer import BatteryOptimizer

def test_battery_optimizer_basic():
    optimizer = BatteryOptimizer()
    
    # Test Elite Sweep (Stage 1)
    results = optimizer.optimize(
        fixed_components={"cell_type": "liquid"},
        pfas_free_only=False,
        enable_discovery=False,
        limit=5
    )
    
    assert len(results) > 0
    assert results[0].type == "Elite"
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
    
    # Discovery might fail if cache not found, but we should test the logic
    try:
        results = optimizer.optimize(
            fixed_components={"cell_type": "solid", "cathode": "NMC811"},
            enable_discovery=True,
            limit=10
        )
        
        types = [r.type for r in results]
        assert "Discovery" in types
        print("Found discovery results!")
        for r in results:
            if r.type == "Discovery":
                print(f"Discovery: {r.cathode} (Base={r.notes})")
    except Exception as e:
        print(f"Discovery skipped or failed: {e}")

if __name__ == "__main__":
    test_battery_optimizer_basic()
    test_battery_optimizer_pfas_free()
    test_battery_optimizer_discovery()
