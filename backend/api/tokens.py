"""
Phase 10.2: RING Token API Endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Dict, Optional

from backend.core.database import get_db
from backend.features.tokens.ledger import (
    get_user_ledger,
    get_token_issuance_mode,
    spend_ring,
    earn_ring,
)
from backend.features.tokens.balance import get_effective_ring_balance, get_balance_summary
from backend.features.tokens.publish import handle_publish_event
from backend.features.tokens.reconciliation import (
    run_reconciliation,
    get_reconciliation_summary,
)

router = APIRouter(prefix="/v1/tokens", tags=["tokens"])

class PublishEventIn(BaseModel):
    event_id: str
    user_id: str
    platform: str
    content_hash: str
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    enforcement_request_id: Optional[str] = None
    enforcement_receipt_id: Optional[str] = None
    metadata: Optional[Dict] = None

    @field_validator("event_id", "user_id", "platform", "content_hash", "platform_post_id", "enforcement_request_id", "enforcement_receipt_id")
    @classmethod
    def _trim(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class SpendRequest(BaseModel):
    user_id: str
    amount: int
    reason_code: str
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict] = None

    @field_validator("user_id", "reason_code", "idempotency_key")
    @classmethod
    def _trim(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class EarnRequest(BaseModel):
    user_id: str
    amount: int
    reason_code: str
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict] = None

    @field_validator("user_id", "reason_code", "idempotency_key")
    @classmethod
    def _trim(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


@router.get("/balance/{user_id}")
def get_balance(user_id: str, db: Session = Depends(get_db)) -> Dict:
    """Get user RING balance and pending rewards."""
    summary = get_effective_ring_balance(db, user_id)
    pending = {
        "totalPending": summary["pending_total"],
        "count": summary["pending_count"],
    }

    return {
        "userId": user_id,
        "balance": summary["balance"],
        "pending": pending,
        "mode": summary["mode"],
        "effective_balance": summary["effective_balance"],
        "last_ledger_at": summary["last_ledger_at"],
        "last_pending_at": summary["last_pending_at"],
    }


@router.get("/ledger/{user_id}")
def get_ledger(user_id: str, limit: int = 20, db: Session = Depends(get_db)) -> Dict:
    """Get user ledger entries."""
    entries = get_user_ledger(db, user_id, limit)
    return {
        "userId": user_id,
        "entries": entries,
        "count": len(entries),
    }


@router.get("/summary/{user_id}")
def get_summary(user_id: str, limit: int = 20, db: Session = Depends(get_db)) -> Dict:
    """Get canonical token balance summary."""
    summary = get_balance_summary(db, user_id, limit=limit)
    return {"userId": user_id, **summary}


@router.post("/reconcile")
def reconcile(db: Session = Depends(get_db)) -> Dict:
    """Run reconciliation (admin only in production)."""
    result = run_reconciliation(db)
    return result


@router.get("/reconcile/summary")
def reconcile_summary(db: Session = Depends(get_db)) -> Dict:
    """Get reconciliation summary."""
    summary = get_reconciliation_summary(db)
    return summary


@router.post("/publish")
def publish_event(body: PublishEventIn, db: Session = Depends(get_db)) -> Dict:
    """Persist publish event and issue tokens if eligible."""
    if not body.event_id or not body.user_id:
        raise HTTPException(status_code=400, detail="event_id and user_id are required")
    published_at = body.published_at or datetime.now(timezone.utc)
    try:
        result = handle_publish_event(
            db,
            event_id=body.event_id,
            user_id=body.user_id,
            platform=body.platform,
            content_hash=body.content_hash,
            published_at=published_at,
            platform_post_id=body.platform_post_id,
            enforcement_request_id=body.enforcement_request_id,
            enforcement_receipt_id=body.enforcement_receipt_id,
            metadata=body.metadata,
        )
        return result
    except Exception as exc:
        return {"ok": False, "error": "publish_event_failed", "detail": str(exc)}


@router.post("/spend")
def spend(body: SpendRequest, db: Session = Depends(get_db)) -> Dict:
    """Spend RING via ledger (shadow/live only)."""
    if not body.user_id or not body.reason_code:
        raise HTTPException(status_code=400, detail="user_id and reason_code are required")
    result = spend_ring(
        db,
        user_id=body.user_id,
        amount=body.amount,
        reason_code=body.reason_code,
        metadata=body.metadata,
        idempotency_key=body.idempotency_key,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/earn")
def earn(body: EarnRequest, db: Session = Depends(get_db)) -> Dict:
    """Earn RING via ledger (shadow/live only)."""
    if not body.user_id or not body.reason_code:
        raise HTTPException(status_code=400, detail="user_id and reason_code are required")
    result = earn_ring(
        db,
        user_id=body.user_id,
        amount=body.amount,
        reason_code=body.reason_code,
        metadata=body.metadata,
        idempotency_key=body.idempotency_key,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result
