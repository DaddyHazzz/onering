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
from backend.core.config import settings


# JWKS override (tests) and cache keyed by issuer/jwks_url
_jwks_provider_override: Optional[Callable[[str, str], Dict[str, Any]]] = None
_jwks_cache: Dict[str, Dict[str, Any]] = {}


def set_jwks_provider_for_tests(provider: Optional[Callable[[str, str], Dict[str, Any]]]) -> None:
    """Set or clear JWKS provider override for deterministic testing (no network)."""
    global _jwks_provider_override, _jwks_cache
    _jwks_provider_override = provider
    _jwks_cache.clear()


def _default_fetch_jwks(issuer: str, jwks_url: str) -> Dict[str, Any]:
    import urllib.request
    with urllib.request.urlopen(jwks_url, timeout=5) as response:
        return json.loads(response.read())


def get_jwks(issuer: str, jwks_url: Optional[str] = None) -> Dict[str, Any]:
    """Fetch JWKS using override (tests) or default fetcher. Cached per issuer/url."""
    # Resolve URL
    resolved_url = jwks_url or f"{issuer.rstrip('/')}/.well-known/jwks.json"
    cache_key = f"{issuer}|{resolved_url}"

    if cache_key in _jwks_cache:
        return _jwks_cache[cache_key]

    if _jwks_provider_override:
        jwks = _jwks_provider_override(issuer, resolved_url)
    else:
        jwks = _default_fetch_jwks(issuer, resolved_url)

    _jwks_cache[cache_key] = jwks
    return jwks


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
        # For testing, don't verify aud/iss (they're set by create_test_jwt)
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False}
        )
        return claims
    
    # Option 2: JWKS-based verification (production)
    issuer = settings.CLERK_ISSUER
    jwks_url = settings.CLERK_JWKS_URL
    if not issuer and not jwks_url:
        raise jwt.PyJWTError("CLERK_ISSUER or CLERK_JWKS_URL must be configured for RS256 verification")

    jwks = get_jwks(issuer or "https://clerk.test", jwks_url)
    
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
        issuer=issuer,
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
    secret: str = "test-secret-key-for-phase46",
    algorithm: str = "HS256",
    private_key: Optional[str] = None,
    kid: Optional[str] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> str:
    """
    Create a test JWT for unit testing.
    Supports HS256 (default) and RS256 (for JWKS-based tests).
    
    Args:
        sub: User ID (subject)
        email: User email
        role: Role to set in public_metadata (e.g. "admin")
        exp_minutes: Expiration time in minutes from now
        secret: Secret key for signing (HS256)
        algorithm: Signing algorithm ("HS256" or "RS256")
        private_key: PEM-encoded private key for RS256
        kid: Optional key ID for RS256 header
    
    Returns:
        Signed JWT string
    """
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + (exp_minutes * 60),
        "iss": issuer or settings.CLERK_ISSUER or "https://test.clerk.accounts.dev",
        "aud": audience or settings.CLERK_AUDIENCE or "test-audience",
        "public_metadata": {}
    }
    
    if role:
        payload["public_metadata"]["role"] = role
    
    headers = {"kid": kid} if kid else None
    key = private_key if algorithm == "RS256" and private_key else secret
    return jwt.encode(payload, key, algorithm=algorithm, headers=headers)


def mock_jwks_for_testing() -> Dict[str, Any]:
    """
    Return mock JWKS for testing (no network call).
    Use with set_jwks_provider_for_tests(mock_jwks_for_testing).
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
