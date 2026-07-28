# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""Materials listing endpoints."""

from dataclasses import asdict
from enum import Enum
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from api.models import DomainMaterialsResponse, MaterialsListResponse

router = APIRouter(prefix="/api/v1", tags=["materials"])

# Domain -> (module_path, dict_name)
_DOMAIN_IMPORTS = {
    "battery": ("battery_bridge.material_properties", "ALL_MATERIALS"),
    "polymer": ("polymer_bridge.material_properties", "ALL_POLYMERS"),
    "metal": ("metal_bridge.material_properties", "ALL_METALS"),
    "ceramic": ("ceramic_bridge.material_properties", "ALL_CERAMICS"),
    "semiconductor": ("semiconductor_bridge.material_properties", "ALL_SEMICONDUCTORS"),
    "glass": ("glass_bridge.material_properties", "ALL_GLASSES"),
}


def _get_materials(domain: str) -> Dict[str, Any]:
    """Lazily import and return materials dict for a domain."""
    import importlib

    mod_path, attr = _DOMAIN_IMPORTS[domain]
    mod = importlib.import_module(mod_path)
    return getattr(mod, attr)


def _serialize_material(mat: Any) -> Dict[str, Any]:
    """Convert a material dataclass to a JSON-safe dict."""
    d = asdict(mat)
    # Convert Enum values to their string names
    return {
        k: (v.name if isinstance(v, Enum) else v)
        for k, v in d.items()
    }


@router.get("/materials", response_model=MaterialsListResponse)
def list_all_materials():
    """List all 169 materials grouped by domain."""
    domains = {}
    total = 0
    for domain in _DOMAIN_IMPORTS:
        mats = _get_materials(domain)
        domains[domain] = sorted(mats.keys())
        total += len(mats)
    return MaterialsListResponse(total=total, domains=domains)


@router.get("/materials/{domain}", response_model=DomainMaterialsResponse)
def list_domain_materials(domain: str):
    """List materials for a specific domain with full property details."""
    if domain not in _DOMAIN_IMPORTS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown domain '{domain}'. "
            f"Valid: {', '.join(sorted(_DOMAIN_IMPORTS))}",
        )
    mats = _get_materials(domain)
    return DomainMaterialsResponse(
        domain=domain,
        count=len(mats),
        materials={name: _serialize_material(m) for name, m in mats.items()},
    )
