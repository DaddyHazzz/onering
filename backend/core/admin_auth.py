"""
Admin authentication for billing operations (Phase 4.4).

Simple, deterministic auth gate:
- Requires X-Admin-Key header
- Compares against ADMIN_API_KEY (preferred) or Settings.ADMIN_KEY (fallback)
- Returns 401 on mismatch; 503 if no key configured at all
"""
import os
from fastapi import Request
from backend.core.errors import PermissionError
from backend.core.config import settings


def get_admin_api_key() -> str | None:
    """Get admin API key.
    Prefer ADMIN_API_KEY env var; fall back to settings.ADMIN_KEY for backward compatibility.
    """
    env_key = os.getenv("ADMIN_API_KEY")
    if env_key:
        return env_key
    # Backward-compatible fallback
    return settings.ADMIN_KEY


def require_admin_auth(request: Request) -> None:
    """
    Validate admin request header.
    
    Raises PermissionError (401) if X-Admin-Key missing or wrong.
    Raises 503 if admin key is not configured at all.
    """
    expected_key = get_admin_api_key()
    
    # If no key configured anywhere, disable admin operations
    if not expected_key:
        raise PermissionError(
            "Admin operations disabled (ADMIN_API_KEY/ADMIN_KEY not configured)",
            code="admin_disabled",
            status_code=503,
        )
    
    # Check header
    header_key = request.headers.get("X-Admin-Key", "").strip()
    
    if not header_key or header_key != expected_key:
        raise PermissionError(
            "Invalid or missing X-Admin-Key header",
            code="invalid_admin_key",
            status_code=401,
        )
