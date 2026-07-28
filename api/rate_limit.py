# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""In-memory rate limiting for KOMPOSOS-III Chemistry API.

Simple token-bucket rate limiter keyed by API key. No external dependencies.

Usage:
    from api.rate_limit import RateLimiter, require_rate_limit

    # As FastAPI dependency (used automatically via main.py):
    app.include_router(router, dependencies=[Depends(require_rate_limit)])
"""

import os
import time
from collections import defaultdict
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from api.auth import require_api_key


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_rate_limit() -> int:
    """Requests per minute, from env or default."""
    return int(os.environ.get("KOMPOSOS_RATE_LIMIT", "120"))


def _get_burst() -> int:
    """Burst size (max tokens), from env or default."""
    return int(os.environ.get("KOMPOSOS_RATE_BURST", "20"))


# ---------------------------------------------------------------------------
# Token bucket
# ---------------------------------------------------------------------------

class RateLimiter:
    """Per-key token bucket rate limiter."""

    def __init__(self, rate_per_minute: int = 120, burst: int = 20):
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.burst = burst
        self._buckets: dict = defaultdict(lambda: {"tokens": burst, "last": time.monotonic()})

    def allow(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        bucket = self._buckets[key]
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
        bucket["last"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False

    def reset(self):
        """Clear all buckets (for testing)."""
        self._buckets.clear()


# Singleton instance
_limiter = RateLimiter(
    rate_per_minute=_get_rate_limit(),
    burst=_get_burst(),
)


def get_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _limiter


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def require_rate_limit(
    api_key: str = Depends(require_api_key),
) -> str:
    """FastAPI dependency: checks rate limit after authentication.

    Returns the API key on success. Raises 429 if rate-limited.
    """
    if not _limiter.allow(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )
    return api_key
