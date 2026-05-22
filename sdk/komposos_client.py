"""KOMPOSOS-III Chemistry Python SDK.

Thin client wrapping all 14 API endpoints.

Usage:
    from sdk import KomposClient

    client = KomposClient(api_key="your-key")

    # Check compatibility
    result = client.check_compatibility("NMC811", "EC")
    print(result["viable"])

    # Predict composition
    pred = client.predict_composition("LiNi0.8Mn0.1Co0.1O2")
    print(pred["voltage"])

    # PFAS check
    pfas = client.check_pfas("PVDF")
    print(pfas["is_pfas"])
"""

from typing import Any, Dict, List, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    import urllib.request
    import urllib.error
    import json as _json
    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False


class KomposClient:
    """Python client for the KOMPOSOS-III Chemistry API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "komposos-demo-key",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        if _HAS_HTTPX:
            self._http = httpx.Client(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
            self._get = self._httpx_get
            self._post = self._httpx_post
        elif _HAS_URLLIB:
            self._http = None
            self._get = self._urllib_get
            self._post = self._urllib_post
        else:
            raise ImportError("Either httpx or urllib is required")

    # ------------------------------------------------------------------
    # HTTP backends
    # ------------------------------------------------------------------

    def _httpx_get(self, path: str) -> Dict[str, Any]:
        r = self._http.get(path)
        r.raise_for_status()
        return r.json()

    def _httpx_post(self, path: str, data: dict) -> Dict[str, Any]:
        r = self._http.post(path, json=data)
        r.raise_for_status()
        return r.json()

    def _urllib_get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers={"X-API-Key": self.api_key})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return _json.loads(resp.read())

    def _urllib_post(self, path: str, data: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = _json.dumps(data).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return _json.loads(resp.read())

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """GET / — health check (no auth required)."""
        if _HAS_HTTPX and self._http:
            r = self._http.get("/")
            return r.json()
        url = f"{self.base_url}/"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return _json.loads(resp.read())

    # --- Materials ---

    def list_materials(self) -> Dict[str, Any]:
        """GET /api/v1/materials — all materials grouped by domain."""
        return self._get("/api/v1/materials")

    def list_domain_materials(self, domain: str) -> Dict[str, Any]:
        """GET /api/v1/materials/{domain} — materials for a specific domain."""
        return self._get(f"/api/v1/materials/{domain}")

    # --- Compatibility ---

    def check_compatibility(self, material_a: str, material_b: str) -> Dict[str, Any]:
        """POST /api/v1/compatibility — two-material same-domain check."""
        return self._post("/api/v1/compatibility", {
            "material_a": material_a,
            "material_b": material_b,
        })

    # --- Multi-domain ---

    def multi_domain(
        self,
        name: str,
        components: List[Dict[str, str]],
        electrolyte: Optional[str] = None,
        viability_threshold: float = 0.50,
    ) -> Dict[str, Any]:
        """POST /api/v1/multi-domain — cross-domain analysis."""
        payload: Dict[str, Any] = {
            "name": name,
            "components": components,
            "viability_threshold": viability_threshold,
        }
        if electrolyte:
            payload["electrolyte"] = electrolyte
        return self._post("/api/v1/multi-domain", payload)

    # --- Molecules ---

    def list_molecules(self) -> Dict[str, Any]:
        """GET /api/v1/molecules — all molecules grouped by class."""
        return self._get("/api/v1/molecules")

    def check_molecular_compatibility(
        self, molecule_a: str, molecule_b: str
    ) -> Dict[str, Any]:
        """POST /api/v1/molecular-compatibility — two-molecule check."""
        return self._post("/api/v1/molecular-compatibility", {
            "molecule_a": molecule_a,
            "molecule_b": molecule_b,
        })

    # --- PFAS ---

    def check_pfas(self, material_name: str) -> Dict[str, Any]:
        """POST /api/v1/pfas-check — PFAS compliance check."""
        return self._post("/api/v1/pfas-check", {"material_name": material_name})

    def list_pfas_substances(self) -> Dict[str, Any]:
        """GET /api/v1/pfas-substances — all PFAS substances."""
        return self._get("/api/v1/pfas-substances")

    def pfas_alternatives(
        self, material_name: str, use_case: Optional[str] = None
    ) -> Dict[str, Any]:
        """POST /api/v1/pfas-alternatives — replacement suggestions."""
        payload: Dict[str, Any] = {"material_name": material_name}
        if use_case:
            payload["use_case"] = use_case
        return self._post("/api/v1/pfas-alternatives", payload)

    # --- Composition prediction ---

    def predict_composition(self, formula: str) -> Dict[str, Any]:
        """POST /api/v1/predict-composition — predict properties from formula."""
        return self._post("/api/v1/predict-composition", {"formula": formula})

    def interpolate(
        self,
        formula_a: str,
        formula_b: str,
        fraction: float = 0.5,
    ) -> Dict[str, Any]:
        """POST /api/v1/interpolate — interpolate between compositions."""
        return self._post("/api/v1/interpolate", {
            "formula_a": formula_a,
            "formula_b": formula_b,
            "fraction": fraction,
        })

    # --- Synthesis ---

    def plan_synthesis(
        self,
        target: str,
        budget_usd: Optional[float] = None,
        available_equipment: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """POST /api/v1/synthesis — plan synthesis routes."""
        payload: Dict[str, Any] = {"target": target}
        if budget_usd is not None:
            payload["budget_usd"] = budget_usd
        if available_equipment:
            payload["available_equipment"] = available_equipment
        return self._post("/api/v1/synthesis", payload)

    def list_synthesis_targets(self) -> List[str]:
        """GET /api/v1/synthesis/targets — list synthesizable materials."""
        return self._get("/api/v1/synthesis/targets")

    # --- ZFC ---

    def zfc_verify(self, material_a: str, material_b: str) -> Dict[str, Any]:
        """POST /api/v1/zfc-verify — ZFC constraint verification."""
        return self._post("/api/v1/zfc-verify", {
            "material_a": material_a,
            "material_b": material_b,
        })

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self):
        """Close the underlying HTTP client."""
        if self._http and hasattr(self._http, "close"):
            self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
