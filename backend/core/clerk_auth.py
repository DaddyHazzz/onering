"""
Clerk JWT verification (Phase 4.6).

Handles:
- JWT signature verification using JWKS
- Issuer/audience validation
- Role/permission extraction
- Test helpers for deterministic testing (no network)

Testing:
- Use test_jwt_signer() to create test tokens
- Mock JWKS fetch via dependency injection
"""
import os
import jwt
import json
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import lru_cache
from backend.core.config import settings


# Global JWKS fetch hook for testing (inject mock)
_jwks_fetch_hook: Optional[Callable[[], Dict[str, Any]]] = None


def set_jwks_fetch_hook(hook: Optional[Callable[[], Dict[str, Any]]]) -> None:
    """Set custom JWKS fetch function (for testing)."""
    global _jwks_fetch_hook
    _jwks_fetch_hook = hook


@lru_cache(maxsize=1)
def fetch_jwks() -> Dict[str, Any]:
    """
    Fetch JWKS from Clerk.
    Cached to avoid network calls per request.
    In tests, use set_jwks_fetch_hook() to inject mock data.
    """
    if _jwks_fetch_hook:
        return _jwks_fetch_hook()
    
    jwks_url = settings.CLERK_JWKS_URL
    if not jwks_url:
        # Construct default URL from issuer if not explicitly set
        issuer = settings.CLERK_ISSUER
        if not issuer:
            raise ValueError("CLERK_JWKS_URL or CLERK_ISSUER must be configured")
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    
    # In production, use requests/httpx to fetch
    # For Phase 4.6 MVP: simplified implementation
    import urllib.request
    with urllib.request.urlopen(jwks_url, timeout=5) as response:
        return json.loads(response.read())


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify Clerk JWT and return claims.
    
    Raises jwt.PyJWTError on invalid token.
    
    Args:
        token: Raw JWT string (without "Bearer " prefix)
    
    Returns:
        Decoded claims dict with keys: sub, email, name, public_metadata, etc.
    """
    # For Phase 4.6 MVP: simplified verification
    # In production, use python-jose or pyjwt with proper JWKS handling
    
    # Option 1: If CLERK_SECRET_KEY is set (development/testing)
    secret = settings.CLERK_SECRET_KEY
    if secret:
        # Symmetric verification (HS256) - simple but less secure
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True}
        )
        return claims
    
    # Option 2: JWKS-based verification (production)
    # Fetch JWKS and verify asymmetric signature
    jwks = fetch_jwks()
    
    # Get key ID from token header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    
    if not kid:
        raise jwt.PyJWTError("Token missing 'kid' in header")
    
    # Find matching key in JWKS
    matching_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            matching_key = key
            break
    
    if not matching_key:
        raise jwt.PyJWTError(f"Key ID '{kid}' not found in JWKS")
    
    # Convert JWKS key to PyJWT format
    from jwt.algorithms import RSAAlgorithm
    public_key = RSAAlgorithm.from_jwk(json.dumps(matching_key))
    
    # Verify token
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.CLERK_AUDIENCE,
        issuer=settings.CLERK_ISSUER,
        options={"verify_signature": True, "verify_exp": True}
    )
    
    return claims


def is_admin_user(claims: Dict[str, Any]) -> bool:
    """
    Check if JWT claims represent an admin user.
    
    Implementation: Check public_metadata.role == "admin"
    (This is the standard Clerk pattern for role-based access)
    
    Args:
        claims: Decoded JWT claims dict
    
    Returns:
        True if user is admin, False otherwise
    """
    # Check public_metadata.role
    public_metadata = claims.get("public_metadata", {})
    if isinstance(public_metadata, dict):
        role = public_metadata.get("role")
        if role == "admin":
            return True
    
    # Fallback: check org_role (if using Clerk organizations)
    org_role = claims.get("org_role")
    if org_role == "admin":
        return True
    
    return False


# ============================================================================
# Test Helpers (deterministic, no network)
# ============================================================================

def create_test_jwt(
    sub: str = "test_user_123",
    email: Optional[str] = "test@example.com",
    role: Optional[str] = None,
    exp_minutes: int = 60,
    secret: str = "test-secret-key-for-phase46"
) -> str:
    """
    Create a test JWT for unit testing.
    Uses HS256 (symmetric) for simplicity.
    
    Args:
        sub: User ID (subject)
        email: User email
        role: Role to set in public_metadata (e.g. "admin")
        exp_minutes: Expiration time in minutes from now
        secret: Secret key for signing (should match test config)
    
    Returns:
        Signed JWT string
    """
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + (exp_minutes * 60),
        "iss": settings.CLERK_ISSUER or "https://test.clerk.accounts.dev",
        "aud": settings.CLERK_AUDIENCE or "test-audience",
        "public_metadata": {}
    }
    
    if role:
        payload["public_metadata"]["role"] = role
    
    return jwt.encode(payload, secret, algorithm="HS256")


def mock_jwks_for_testing() -> Dict[str, Any]:
    """
    Return mock JWKS for testing (no network call).
    Use with set_jwks_fetch_hook(mock_jwks_for_testing).
    """
    return {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "n": "test-modulus",
                "e": "AQAB"
            }
        ]
    }
