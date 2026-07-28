# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""KOMPOSOS-III Chemistry API — FastAPI application."""

import logging
import os
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.rate_limit import require_rate_limit
from api.routes import compatibility, designer, materials, mof_designer, molecular, multi_domain, pfas, pfas_report, predict, synthesis

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LEVEL = os.environ.get("KOMPOSOS_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("komposos.api")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KOMPOSOS-III Chemistry API",
    version="1.1.0",
    description=(
        "Compositional reasoning engine for chemistry and materials. "
        "Predicts material compatibility using category theory and ZFC set theory. "
        "All /api/v1/* endpoints require an X-API-Key header."
    ),
)

# CORS — permissive for development, tighten for production
_CORS_ORIGINS = os.environ.get("KOMPOSOS_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status, and response time."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Mask API key for logging
    api_key = request.headers.get("X-API-Key", "")
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"

    logger.info(
        "%s %s %d %.1fms key=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        masked,
    )
    return response


# ---------------------------------------------------------------------------
# Authenticated routes (require API key + rate limit)
# ---------------------------------------------------------------------------

_auth_deps = [Depends(require_rate_limit)]

app.include_router(materials.router, dependencies=_auth_deps)
app.include_router(compatibility.router, dependencies=_auth_deps)
app.include_router(molecular.router, dependencies=_auth_deps)
app.include_router(multi_domain.router, dependencies=_auth_deps)
app.include_router(pfas.router, dependencies=_auth_deps)
app.include_router(pfas_report.router, dependencies=_auth_deps)
app.include_router(predict.router, dependencies=_auth_deps)
app.include_router(synthesis.router, dependencies=_auth_deps)
app.include_router(designer.router, dependencies=_auth_deps)
app.include_router(mof_designer.router, dependencies=_auth_deps)


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Health check / welcome (no auth required)."""
    return {
        "name": "KOMPOSOS-III Chemistry API",
        "version": "1.1.0",
        "auth": "X-API-Key header required for /api/v1/* endpoints",
        "docs": "/docs",
        "endpoints": [
            "GET  /api/v1/materials",
            "GET  /api/v1/materials/{domain}",
            "POST /api/v1/compatibility",
            "GET  /api/v1/molecules",
            "POST /api/v1/molecular-compatibility",
            "POST /api/v1/search-molecules",
            "POST /api/v1/multi-domain",
            "POST /api/v1/pfas-check",
            "GET  /api/v1/pfas-substances",
            "POST /api/v1/pfas-alternatives",
            "POST /api/v1/pfas-report",
            "POST /api/v1/predict-composition",
            "POST /api/v1/interpolate",
            "POST /api/v1/synthesis",
            "GET  /api/v1/synthesis/targets",
            "POST /api/v1/design-composition",
            "POST /api/v1/design-mof-linker",
        ],
    }


@app.get("/health")
def health():
    """Health check for load balancers / Docker."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def run_server():
    """Entry point for `komposos-api` console script."""
    import uvicorn

    host = os.environ.get("KOMPOSOS_HOST", "0.0.0.0")
    port = int(os.environ.get("KOMPOSOS_PORT", "8000"))
    reload = os.environ.get("KOMPOSOS_RELOAD", "true").lower() == "true"
    uvicorn.run("api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
