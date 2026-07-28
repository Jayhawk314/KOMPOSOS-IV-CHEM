# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 James Ray Hawkins

"""
Access Control for KOMPOSOS-III Streamlit UI
==============================================

DISABLED: Access control is currently disabled for open demo access.
All functions are no-ops. To re-enable, restore from git history.
Pure environment parsing helpers are kept for tests and future re-enablement.

Usage in each Streamlit page (unchanged API, just no-ops):
    from streamlit_app.access_control import render_login_sidebar, require_access, consume_use

    render_login_sidebar()  # no-op

    if st.button("Run Analysis"):
        if not require_access():  # always True
            st.stop()
        consume_use()  # no-op
        # ... run analysis ...
"""

import os


DEFAULT_ADMIN_PASSWORD = "komposos-admin"
DEFAULT_DEMO_LIMIT = 3
DEFAULT_VOUCHER_LIMIT = 20


def _load_voucher_codes() -> dict[str, int]:
    """Parse KOMPOSOS_VOUCHER_CODES as CODE or CODE:LIMIT comma entries."""
    raw = os.environ.get("KOMPOSOS_VOUCHER_CODES", "")
    vouchers: dict[str, int] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue

        if ":" in entry:
            code, limit_text = entry.split(":", 1)
        else:
            code, limit_text = entry, str(DEFAULT_VOUCHER_LIMIT)

        code = code.strip()
        if not code:
            continue

        try:
            limit = int(limit_text.strip())
        except ValueError:
            limit = DEFAULT_VOUCHER_LIMIT

        vouchers[code] = limit
    return vouchers


def _load_admin_password() -> str:
    """Load the configured admin password, preserving the legacy default."""
    return os.environ.get("KOMPOSOS_ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD


def _load_demo_limit() -> int:
    """Load the configured demo-use limit, preserving the legacy default."""
    try:
        return int(os.environ.get("KOMPOSOS_DEMO_LIMIT", str(DEFAULT_DEMO_LIMIT)))
    except ValueError:
        return DEFAULT_DEMO_LIMIT


def render_login_sidebar():
    """No-op. Access control disabled."""
    pass


def require_access() -> bool:
    """Always returns True. Access control disabled."""
    return True


def consume_use():
    """No-op. Access control disabled."""
    pass


def get_access_tier() -> str:
    """Always returns 'admin'. Access control disabled."""
    return "admin"


def get_remaining_uses():
    """Always returns None (unlimited). Access control disabled."""
    return None
