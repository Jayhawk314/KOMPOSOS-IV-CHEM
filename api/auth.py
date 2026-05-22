"""API key authentication for KOMPOSOS-III Chemistry API.

Keys are configured via the KOMPOSOS_API_KEYS environment variable (comma-separated).
If not set, a demo key is used for development.

Usage in routes:
    from api.auth import require_api_key
    router = APIRouter(dependencies=[Depends(require_api_key)])
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ENV_KEY = "KOMPOSOS_API_KEYS"
_DEMO_KEY = "komposos-demo-key"

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _load_api_keys() -> set:
    """Load valid API keys from environment, falling back to demo key."""
    raw = os.environ.get(_ENV_KEY, "")
    if raw.strip():
        return {k.strip() for k in raw.split(",") if k.strip()}
    return {_DEMO_KEY}


def get_valid_keys() -> set:
    """Return the current set of valid API keys (re-reads env each call)."""
    return _load_api_keys()


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def require_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> str:
    """FastAPI dependency that validates the X-API-Key header.

    Returns the validated key string on success.
    Raises 401 if missing, 403 if invalid.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header.",
        )
    valid = get_valid_keys()
    if api_key not in valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    return api_key
