"""
External Platform API endpoints (Phase 10.3).

Read-only endpoints for third-party integrations.
Requires API key authentication with scope enforcement.

Kill switch: ONERING_EXTERNAL_API_ENABLED (default 0)
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.features.external.api_keys import (
    validate_api_key,
    check_scope,
    check_rate_limit,
    is_external_api_enabled,
)


router = APIRouter(prefix="/v1/external", tags=["external"])


class ExternalApiKeyInfo(BaseModel):
    key_id: str
    owner_user_id: str
    scopes: List[str]
    rate_limit_tier: str


async def require_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> ExternalApiKeyInfo:
    """
    Dependency to require valid API key.
    Validates key, checks rate limits, and returns key info.
    """
    if not is_external_api_enabled():
        raise HTTPException(
            status_code=503,
            detail="External API is currently disabled"
        )
    
    # Extract Bearer token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header (expected Bearer token)"
        )
    
    api_key = authorization[7:]  # Strip "Bearer "
    
    # Validate key
    key_info = validate_api_key(db, api_key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    
    # Check rate limit
    allowed, current_count, limit = check_rate_limit(
        db, key_info["key_id"], key_info["rate_limit_tier"]
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({current_count}/{limit} requests this hour)"
        )
    
    return ExternalApiKeyInfo(**key_info)


def require_scope(required_scope: str):
    """Dependency factory to require specific scope."""
    async def _check_scope(key_info: ExternalApiKeyInfo = Depends(require_api_key)):
        if not check_scope(key_info.dict(), required_scope):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope: {required_scope}"
            )
        return key_info
    return _check_scope


# --- External API Endpoints ---


class WhoAmIResponse(BaseModel):
    key_id: str
    scopes: List[str]
    rate_limit_tier: str
    rate_limit_remaining: int
    rate_limit_limit: int


@router.get("/me", response_model=WhoAmIResponse)
async def get_whoami(
    key_info: ExternalApiKeyInfo = Depends(require_api_key),
    db: Session = Depends(get_db),
):
    """Get information about the authenticated API key."""
    # Get current rate limit status
    _, current_count, limit = check_rate_limit(db, key_info.key_id, key_info.rate_limit_tier)
    
    return WhoAmIResponse(
        key_id=key_info.key_id,
        scopes=key_info.scopes,
        rate_limit_tier=key_info.rate_limit_tier,
        rate_limit_remaining=limit - current_count,
        rate_limit_limit=limit,
    )


class RingItem(BaseModel):
    id: str
    user_id: str
    balance: int
    verified: bool
    created_at: str


class RingsListResponse(BaseModel):
    rings: List[RingItem]


@router.get("/rings", response_model=RingsListResponse)
async def list_rings(
    key_info: ExternalApiKeyInfo = Depends(require_scope("read:rings")),
    db: Session = Depends(get_db),
):
    """List rings accessible to the authenticated user."""
    # For now, just return the owner's ring info
    row = db.execute(
        text("""
            SELECT id, "clerkId", "ringBalance", verified, "createdAt"
            FROM users
            WHERE "clerkId" = :user_id
            LIMIT 1
        """),
        {"user_id": key_info.owner_user_id}
    ).fetchone()
    
    if not row:
        return RingsListResponse(rings=[])
    
    return RingsListResponse(
        rings=[
            RingItem(
                id=str(row[0]),
                user_id=row[1],
                balance=row[2],
                verified=row[3],
                created_at=row[4].isoformat(),
            )
        ]
    )


class RingDetailResponse(BaseModel):
    id: str
    user_id: str
    balance: int
    verified: bool
    created_at: str
    updated_at: str


@router.get("/rings/{ring_id}", response_model=RingDetailResponse)
async def get_ring_detail(
    ring_id: str,
    key_info: ExternalApiKeyInfo = Depends(require_scope("read:rings")),
    db: Session = Depends(get_db),
):
    """Get ring metadata by ID."""
    row = db.execute(
        text("""
            SELECT id, "clerkId", "ringBalance", verified, "createdAt", "updatedAt"
            FROM users
            WHERE id = :ring_id AND "clerkId" = :user_id
            LIMIT 1
        """),
        {"ring_id": ring_id, "user_id": key_info.owner_user_id}
    ).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Ring not found")
    
    return RingDetailResponse(
        id=str(row[0]),
        user_id=row[1],
        balance=row[2],
        verified=row[3],
        created_at=row[4].isoformat(),
        updated_at=row[5].isoformat() if row[5] else row[4].isoformat(),
    )


class DraftItem(BaseModel):
    id: str
    ring_id: str
    status: str
    word_count: int
    created_at: str


class DraftsListResponse(BaseModel):
    drafts: List[DraftItem]


@router.get("/drafts", response_model=DraftsListResponse)
async def list_drafts(
    ring_id: Optional[str] = None,
    limit: int = 20,
    key_info: ExternalApiKeyInfo = Depends(require_scope("read:drafts")),
    db: Session = Depends(get_db),
):
    """List drafts (metadata only, no content)."""
    # Note: Actual draft table structure may differ - this is placeholder logic
    # For now, return empty list as drafts table doesn't exist in current schema
    return DraftsListResponse(drafts=[])


class LedgerEntry(BaseModel):
    id: str
    event_type: str
    amount: int
    balance_after: int
    reason_code: str
    created_at: str


class LedgerListResponse(BaseModel):
    entries: List[LedgerEntry]


@router.get("/ledger", response_model=LedgerListResponse)
async def list_ledger_entries(
    limit: int = 20,
    key_info: ExternalApiKeyInfo = Depends(require_scope("read:ledger")),
    db: Session = Depends(get_db),
):
    """Get token ledger entries for authenticated user."""
    rows = db.execute(
        text("""
            SELECT id, event_type, amount, balance_after, reason_code, created_at
            FROM ring_ledger
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"user_id": key_info.owner_user_id, "limit": min(limit, 100)}
    ).fetchall()
    
    return LedgerListResponse(
        entries=[
            LedgerEntry(
                id=str(row[0]),
                event_type=row[1],
                amount=row[2],
                balance_after=row[3],
                reason_code=row[4],
                created_at=row[5].isoformat(),
            )
            for row in rows
        ]
    )


class EnforcementStats(BaseModel):
    total_checks: int
    pass_count: int
    fail_count: int
    window_hours: int


class EnforcementResponse(BaseModel):
    stats: EnforcementStats


@router.get("/enforcement", response_model=EnforcementResponse)
async def get_enforcement_stats(
    hours: int = 24,
    key_info: ExternalApiKeyInfo = Depends(require_scope("read:enforcement")),
    db: Session = Depends(get_db),
):
    """Get enforcement outcome statistics."""
    # Count outcomes from audit_agent_decisions table
    row = db.execute(
        text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE qa_status = 'PASS') as pass_count,
                COUNT(*) FILTER (WHERE qa_status = 'FAIL') as fail_count
            FROM audit_agent_decisions
            WHERE caller_user_id = :user_id
            AND created_at >= NOW() - INTERVAL ':hours hours'
        """),
        {"user_id": key_info.owner_user_id, "hours": hours}
    ).fetchone()
    
    total, pass_count, fail_count = (row[0] or 0, row[1] or 0, row[2] or 0) if row else (0, 0, 0)
    
    return EnforcementResponse(
        stats=EnforcementStats(
            total_checks=total,
            pass_count=pass_count,
            fail_count=fail_count,
            window_hours=hours,
        )
    )
