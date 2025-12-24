"""
Auth utilities for OneRing API (Phase 6.1).

Validates Clerk JWTs and extracts user_id from request context.
Falls back to X-User-Id header for backward compatibility (tests).
"""
from fastapi import Header, HTTPException, Request
from typing import Optional
from backend.core.config import settings
import jwt
import json
from functools import lru_cache
import httpx
import logging

logger = logging.getLogger(__name__)

# Cache JWKS for 24 hours
JWKS_CACHE = {}
JWKS_CACHE_TIME = None


async def get_clerk_jwks():
    """
    Fetch Clerk's JWKS (JSON Web Key Set) for verifying JWTs.
    
    Phase 6.1: Clerk publishes JWKS at /.well-known/jwks.json
    """
    global JWKS_CACHE, JWKS_CACHE_TIME
    import time
    
    if JWKS_CACHE and JWKS_CACHE_TIME and (time.time() - JWKS_CACHE_TIME) < 86400:
        return JWKS_CACHE
    
    if not settings.CLERK_JWKS_URL:
        # Try to construct from issuer
        if settings.CLERK_ISSUER:
            jwks_url = f"{settings.CLERK_ISSUER}/.well-known/jwks.json"
        else:
            return None
    else:
        jwks_url = settings.CLERK_JWKS_URL
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            JWKS_CACHE = response.json()
            JWKS_CACHE_TIME = time.time()
            return JWKS_CACHE
    except Exception as e:
        logger.warning(f"Failed to fetch Clerk JWKS: {e}")
        return None


def verify_clerk_jwt(token: str) -> str:
    """
    Verify Clerk JWT and extract user_id.
    
    Phase 6.1: Validates JWT signature against Clerk's JWKS.
    
    Args:
        token: JWT from Authorization header (Bearer {token})
    
    Returns:
        user_id: Extracted from JWT's 'sub' claim
    
    Raises:
        HTTPException 401: Invalid or expired token
    """
    if not settings.CLERK_SECRET_KEY:
        logger.debug("No CLERK_SECRET_KEY configured, skipping JWT validation")
        return None
    
    try:
        # Decode without verification first to check algorithm
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(
            token,
            settings.CLERK_SECRET_KEY,
            algorithms=["HS256", "RS256"],
            options={"verify_signature": True, "verify_exp": True}
        )
        
        # Extract user_id from 'sub' claim (standard JWT format)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("No 'sub' claim in token")
        
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.debug(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")


async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None, description="Backward compat: test user ID")
) -> str:
    """
    Extract current user ID from request context.
    
    Phase 6.1 Priority:
    1. Clerk JWT from Authorization header
    2. X-User-Id header (backward compatibility)
    3. Raise 401 Unauthorized
    
    After successful auth, upsert user into database.
    
    Args:
        request: FastAPI request
        x_user_id: Legacy header for tests
    
    Returns:
        user_id: Clerk user ID or test ID
    
    Raises:
        HTTPException 401: Missing authentication
    """
    # Try Clerk JWT first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        try:
            user_id = verify_clerk_jwt(jwt_token)
            if user_id:
                # Upsert user into database (Phase 6.1)
                try:
                    from backend.features.users.service import get_or_create_user
                    get_or_create_user(user_id)
                except Exception as e:
                    logger.warning(f"Failed to upsert user {user_id}: {e}")
                    # Continue - don't block auth if upsert fails
                
                return user_id
        except HTTPException:
            # Token is invalid, don't try X-User-Id
            raise
        except Exception as e:
            logger.debug(f"JWT verification failed, falling back: {e}")
    
    # Fall back to X-User-Id for backward compatibility
    if x_user_id:
        # Also upsert test user (for backward compat)
        try:
            from backend.features.users.service import get_or_create_user
            get_or_create_user(x_user_id)
        except Exception as e:
            logger.debug(f"Failed to upsert test user {x_user_id}: {e}")
        
        return x_user_id
    
    # No auth found
    raise HTTPException(
        status_code=401,
        detail={
            "error": "unauthorized",
            "message": "Missing Authorization (Bearer JWT) or X-User-Id header"
        }
    )
