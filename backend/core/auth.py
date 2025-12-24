"""
Auth utilities for OneRing API (Phase 5.1).

Minimal auth dependency for extracting user_id from request context.
Designed to be overrideable in tests.
"""
from fastapi import Header, HTTPException
from typing import Optional


async def get_current_user_id(
    x_user_id: Optional[str] = Header(None, description="User ID (test override or Clerk integration)")
) -> str:
    """
    Extract current user ID from request context.
    
    Phase 5.1 implementation: reads X-User-Id header (for testing).
    Future: integrate with Clerk JWT validation.
    
    Returns:
        user_id: Clerk user ID
    
    Raises:
        HTTPException 401: Missing authentication
    """
    if not x_user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "unauthorized",
                "message": "Missing X-User-Id header (authentication required)"
            }
        )
    return x_user_id
