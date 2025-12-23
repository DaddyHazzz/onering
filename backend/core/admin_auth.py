"""
Admin authentication for billing operations (Phase 4.6).

Supports hybrid authentication:
- Clerk JWT (preferred): Bearer token with role validation
- Legacy X-Admin-Key: Shared secret (deprecated, feature-flagged)

Auth modes (ADMIN_AUTH_MODE):
- "clerk": Only Clerk JWT allowed (production default)
- "legacy": Only X-Admin-Key allowed (testing/migration)
- "hybrid": Both allowed (default for rollout)

Security guarantees:
- In prod (ENVIRONMENT=prod), legacy keys blocked unless explicitly enabled
- All admin actions audited with actor identity
- JWT verification uses cached JWKS (no network per request)
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Literal
from dataclasses import dataclass
from fastapi import Request, Depends, HTTPException
from backend.core.errors import PermissionError
from backend.core.config import settings


@dataclass
class AdminActor:
    """Represents an authenticated admin actor."""
    actor_type: Literal["clerk", "legacy_key"]
    actor_id: str  # Clerk user ID or "legacy:<hash>"
    actor_email: Optional[str] = None
    actor_display: Optional[str] = None  # Display name
    auth_mechanism: Literal["clerk_jwt", "x_admin_key"] = "clerk_jwt"


def get_admin_api_key() -> str | None:
    """Get admin API key for legacy auth.
    Prefer ADMIN_API_KEY env var; fall back to settings.ADMIN_KEY.
    """
    env_key = os.getenv("ADMIN_API_KEY")
    if env_key:
        return env_key
    return settings.ADMIN_KEY


def verify_legacy_key(request: Request) -> Optional[AdminActor]:
    """
    Verify legacy X-Admin-Key header.
    Returns AdminActor if valid, None if not present/invalid.
    """
    expected_key = get_admin_api_key()
    if not expected_key:
        return None
    
    header_key = request.headers.get("X-Admin-Key", "").strip()
    if not header_key or header_key != expected_key:
        return None
    
    # Create legacy actor identity
    key_hash = hashlib.sha256(header_key.encode()).hexdigest()[:16]
    return AdminActor(
        actor_type="legacy_key",
        actor_id=f"legacy:{key_hash}",
        actor_display="Legacy Admin Key",
        auth_mechanism="x_admin_key"
    )


def verify_clerk_jwt(request: Request) -> Optional[AdminActor]:
    """
    Verify Clerk JWT from Authorization header.
    Returns AdminActor if valid, None if not present/invalid.
    
    For Phase 4.6 MVP: simplified validation (full JWT verification in clerk_auth.py)
    """
    from backend.core.clerk_auth import verify_jwt_token, is_admin_user
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:].strip()
    if not token:
        return None
    
    try:
        claims = verify_jwt_token(token)
        if not is_admin_user(claims):
            return None
        
        return AdminActor(
            actor_type="clerk",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            actor_display=claims.get("name") or claims.get("email"),
            auth_mechanism="clerk_jwt"
        )
    except Exception:
        return None


def get_admin_actor(request: Request) -> Optional[AdminActor]:
    """
    Attempt to authenticate admin from request.
    Returns AdminActor or None (does not raise).
    
    Order of preference:
    1. Clerk JWT (if ADMIN_AUTH_MODE in {"clerk", "hybrid"})
    2. Legacy key (if ADMIN_AUTH_MODE in {"legacy", "hybrid"} AND env allows)
    """
    mode = settings.ADMIN_AUTH_MODE.lower()
    env = settings.ENVIRONMENT.lower()
    
    # Try Clerk JWT first
    if mode in {"clerk", "hybrid"}:
        actor = verify_clerk_jwt(request)
        if actor:
            return actor
    
    # Try legacy key
    if mode in {"legacy", "hybrid"}:
        # In production, block legacy unless explicitly overridden
        if env == "prod" and mode != "legacy":
            return None
        
        actor = verify_legacy_key(request)
        if actor:
            # Add deprecation warning header (caller should attach to response)
            return actor
    
    return None


def require_admin(request: Request) -> AdminActor:
    """
    FastAPI dependency: Require admin authentication.
    Raises HTTPException if authentication fails.
    
    Usage:
        @router.get("/admin/endpoint")
        def admin_endpoint(actor: AdminActor = Depends(require_admin)):
            # actor contains verified identity
            pass
    """
    actor = get_admin_actor(request)
    
    if not actor:
        mode = settings.ADMIN_AUTH_MODE.lower()
        
        # Check if auth is configured at all
        has_clerk = bool(settings.CLERK_SECRET_KEY or settings.CLERK_JWKS_URL)
        has_legacy = bool(get_admin_api_key())
        
        if not has_clerk and not has_legacy:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Admin authentication not configured",
                    "code": "admin_auth_unconfigured",
                    "hint": "Set ADMIN_KEY (legacy) or CLERK_SECRET_KEY (recommended)"
                }
            )
        
        # Auth configured but credentials invalid
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized: invalid or missing admin credentials",
                "code": "admin_unauthorized",
                "hint": f"Mode: {mode}. Use Clerk Bearer token or X-Admin-Key header."
            }
        )
    
    return actor


# Legacy shim for backward compatibility
def require_admin_auth(request: Request) -> None:
    """
    Deprecated: Use require_admin() instead.
    This shim maintains backward compatibility with Phase 4.4 code.
    """
    require_admin(request)

