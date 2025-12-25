"""
Phase 10.2: RING Token API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from backend.core.database import get_db
from backend.features.tokens.ledger import (
    get_user_ledger,
    get_pending_rewards,
    get_user_balance,
    get_token_issuance_mode,
)
from backend.features.tokens.reconciliation import (
    run_reconciliation,
    get_reconciliation_summary,
)

router = APIRouter(prefix="/v1/tokens", tags=["tokens"])


@router.get("/balance/{user_id}")
def get_balance(user_id: str, db: Session = Depends(get_db)) -> Dict:
    """Get user RING balance and pending rewards."""
    mode = get_token_issuance_mode()
    balance = get_user_balance(db, user_id)
    pending = get_pending_rewards(db, user_id) if mode == "shadow" else {"totalPending": 0, "count": 0}
    
    return {
        "userId": user_id,
        "balance": balance,
        "pending": pending,
        "mode": mode,
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
