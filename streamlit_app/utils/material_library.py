# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Material library utility for Streamlit UI autofill and selection."""

import functools
from typing import List, Dict, Set

@functools.lru_cache(maxsize=1)
def get_all_material_names() -> List[str]:
    """Aggregate all unique material names from all bridge domains."""
    names: Set[str] = set()
    
    # 1. Battery
    try:
        from battery_bridge.material_properties import ALL_MATERIALS
        names.update(ALL_MATERIALS.keys())
    except ImportError:
        pass
        
    # 2. Polymer
    try:
        from polymer_bridge.material_properties import ALL_POLYMERS
        names.update(ALL_POLYMERS.keys())
    except ImportError:
        pass
        
    # 3. Ceramic
    try:
        from ceramic_bridge.material_properties import ALL_CERAMICS
        names.update(ALL_CERAMICS.keys())
    except ImportError:
        pass
        
    # 4. Metal
    try:
        from metal_bridge.material_properties import ALL_METALS
        names.update(ALL_METALS.keys())
    except ImportError:
        pass
        
    # 5. Semiconductor
    try:
        from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS
        names.update(ALL_SEMICONDUCTORS.keys())
    except ImportError:
        pass
        
    # 6. Glass
    try:
        from glass_bridge.material_properties import ALL_GLASSES
        names.update(ALL_GLASSES.keys())
    except ImportError:
        pass

    # 7. PFAS Registry (Curated)
    try:
        from pfas_bridge.pfas_registry import PFAS_REGISTRY
        names.update(PFAS_REGISTRY.keys())
    except ImportError:
        pass
        
    return sorted(list(names))

def get_materials_by_domain() -> Dict[str, List[str]]:
    """Get material names grouped by their primary bridge domain."""
    domains: Dict[str, List[str]] = {
        "Battery": [],
        "Polymer": [],
        "Ceramic": [],
        "Metal": [],
        "Semiconductor": [],
        "Glass": [],
        "PFAS": []
    }
    
    try:
        from battery_bridge.material_properties import ALL_MATERIALS
        domains["Battery"] = sorted(list(ALL_MATERIALS.keys()))
    except ImportError:
        pass
        
    try:
        from polymer_bridge.material_properties import ALL_POLYMERS
        domains["Polymer"] = sorted(list(ALL_POLYMERS.keys()))
    except ImportError:
        pass
        
    try:
        from ceramic_bridge.material_properties import ALL_CERAMICS
        domains["Ceramic"] = sorted(list(ALL_CERAMICS.keys()))
    except ImportError:
        pass
        
    try:
        from metal_bridge.material_properties import ALL_METALS
        domains["Metal"] = sorted(list(ALL_METALS.keys()))
    except ImportError:
        pass
        
    try:
        from semiconductor_bridge.material_properties import ALL_SEMICONDUCTORS
        domains["Semiconductor"] = sorted(list(ALL_SEMICONDUCTORS.keys()))
    except ImportError:
        pass
        
    try:
        from glass_bridge.material_properties import ALL_GLASSES
        domains["Glass"] = sorted(list(ALL_GLASSES.keys()))
    except ImportError:
        pass

    try:
        from pfas_bridge.pfas_registry import PFAS_REGISTRY
        domains["PFAS"] = sorted(list(PFAS_REGISTRY.keys()))
    except ImportError:
        pass
        
    return domains
