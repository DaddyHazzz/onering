"""
Phase 10.2: RING Token Ledger and Issuance Service

Manages token accounting with:
- Append-only ledger
- Shadow/live mode switching
- Anti-gaming guardrails
- Reconciliation support
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Literal
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import get_db

# Guardrail constants (configurable via env)
DAILY_EARN_CAP = int(os.getenv("RING_DAILY_EARN_CAP", "1000"))
MIN_EARN_INTERVAL_SECONDS = int(os.getenv("RING_MIN_EARN_INTERVAL_SECONDS", "300"))  # 5 min
ANOMALY_THRESHOLD_EARNS_PER_HOUR = int(os.getenv("RING_ANOMALY_EARNS_PER_HOUR", "10"))

EventType = Literal["EARN", "SPEND", "PENALTY", "ADJUSTMENT"]


def get_token_issuance_mode() -> str:
    """Get current token issuance mode."""
    mode = getattr(settings, "ONERING_TOKEN_ISSUANCE", "off") or "off"
    if mode not in {"off", "shadow", "live"}:
        mode = "off"
    return mode


class LedgerEntry:
    """Ledger entry model."""
    
    def __init__(
        self,
        user_id: str,
        event_type: EventType,
        reason_code: str,
        amount: int,
        balance_after: int,
        draft_id: Optional[str] = None,
        request_id: Optional[str] = None,
        receipt_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.user_id = user_id
        self.event_type = event_type
        self.reason_code = reason_code
        self.amount = amount
        self.balance_after = balance_after
        self.draft_id = draft_id
        self.request_id = request_id
        self.receipt_id = receipt_id
        self.metadata = metadata or {}


def append_ledger_entry(db: Session, entry: LedgerEntry) -> str:
    """
    Append entry to ring_ledger table.
    Returns entry ID.
    """
    import json
    
    result = db.execute(
        text("""
            INSERT INTO ring_ledger 
            (user_id, draft_id, request_id, receipt_id, event_type, reason_code, amount, balance_after, metadata)
            VALUES (:user_id, :draft_id, :request_id, :receipt_id, :event_type, :reason_code, :amount, :balance_after, CAST(:metadata AS jsonb))
            RETURNING id
        """),
        {
            "user_id": entry.user_id,
            "draft_id": entry.draft_id,
            "request_id": entry.request_id,
            "receipt_id": entry.receipt_id,
            "event_type": entry.event_type,
            "reason_code": entry.reason_code,
            "amount": entry.amount,
            "balance_after": entry.balance_after,
            "metadata": json.dumps(entry.metadata),
        },
    )
    db.commit()
    ledger_id = result.scalar()
    return str(ledger_id)


def add_pending_reward(
    db: Session, user_id: str, amount: int, reason_code: str, metadata: Optional[Dict] = None, draft_id: Optional[str] = None, request_id: Optional[str] = None
) -> str:
    """Add pending reward in shadow mode."""
    import json
    
    result = db.execute(
        text("""
            INSERT INTO ring_pending 
            (user_id, draft_id, request_id, amount, reason_code, metadata)
            VALUES (:user_id, :draft_id, :request_id, :amount, :reason_code, CAST(:metadata AS jsonb))
            RETURNING id
        """),
        {
            "user_id": user_id,
            "draft_id": draft_id,
            "request_id": request_id,
            "amount": amount,
            "reason_code": reason_code,
            "metadata": json.dumps(metadata or {}),
        },
    )
    db.commit()
    return str(result.scalar())


def get_user_balance(db: Session, user_id: str) -> int:
    """Get current user balance from users table."""
    result = db.execute(
        text('SELECT "ringBalance" FROM users WHERE "clerkId" = :user_id'),
        {"user_id": user_id},
    )
    row = result.fetchone()
    return row[0] if row else 0


def update_user_balance(db: Session, user_id: str, new_balance: int) -> None:
    """Update user balance in users table."""
    db.execute(
        text('UPDATE users SET "ringBalance" = :balance WHERE "clerkId" = :user_id'),
        {"user_id": user_id, "balance": new_balance},
    )
    db.commit()


def check_guardrails(db: Session, user_id: str) -> tuple[bool, List[str], int]:
    """
    Check anti-gaming guardrails.
    Returns: (allowed, violations, reduction_factor_percentage)
    """
    violations = []
    reduction = 0
    
    # Get or create guardrail state
    result = db.execute(
        text("""
            SELECT daily_earn_count, daily_earn_total, last_earn_at, reset_at, anomaly_flags
            FROM ring_guardrails_state
            WHERE user_id = :user_id
        """),
        {"user_id": user_id},
    )
    row = result.fetchone()
    
    now = datetime.utcnow()
    
    if not row:
        # Create initial state
        db.execute(
            text("""
                INSERT INTO ring_guardrails_state (user_id, reset_at)
                VALUES (:user_id, :reset_at)
            """),
            {"user_id": user_id, "reset_at": now},
        )
        db.commit()
        return True, [], 0
    
    daily_count, daily_total, last_earn_at, reset_at, anomaly_flags = row
    
    # Check if daily reset needed
    if now >= reset_at + timedelta(days=1):
        db.execute(
            text("""
                UPDATE ring_guardrails_state
                SET daily_earn_count = 0, daily_earn_total = 0, reset_at = :reset_at, updated_at = :now
                WHERE user_id = :user_id
            """),
            {"user_id": user_id, "reset_at": now, "now": now},
        )
        db.commit()
        daily_count = 0
        daily_total = 0
    
    # Guardrail 1: Daily earn cap
    if daily_total >= DAILY_EARN_CAP:
        violations.append(f"daily_cap_reached:{DAILY_EARN_CAP}")
        reduction = 100  # Block all
    
    # Guardrail 2: Minimum interval between earns
    if last_earn_at and (now - last_earn_at).total_seconds() < MIN_EARN_INTERVAL_SECONDS:
        violations.append(f"min_interval_violation:{MIN_EARN_INTERVAL_SECONDS}s")
        reduction = max(reduction, 50)  # 50% penalty
    
    # Guardrail 3: Anomaly detection (simple rate check)
    if daily_count > ANOMALY_THRESHOLD_EARNS_PER_HOUR:
        violations.append(f"anomaly_high_frequency:{daily_count}")
        reduction = max(reduction, 75)  # 75% penalty
    
    allowed = reduction < 100
    return allowed, violations, reduction


def update_guardrail_state(db: Session, user_id: str, earn_amount: int) -> None:
    """Update guardrail state after earn."""
    now = datetime.utcnow()
    db.execute(
        text("""
            UPDATE ring_guardrails_state
            SET daily_earn_count = daily_earn_count + 1,
                daily_earn_total = daily_earn_total + :amount,
                last_earn_at = :now,
                updated_at = :now
            WHERE user_id = :user_id
        """),
        {"user_id": user_id, "amount": earn_amount, "now": now},
    )
    db.commit()


def issue_ring_for_publish(
    db: Session,
    user_id: str,
    draft_id: Optional[str],
    request_id: Optional[str],
    receipt_id: Optional[str],
    qa_status: str,
    audit_ok: bool,
    platform: str,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Core issuance logic for successful publish.
    
    Rules:
    - Earn only on QA PASS + audit_ok
    - Apply guardrails
    - Shadow mode: log pending
    - Live mode: issue tokens and update ledger
    
    Returns: {
        "issued": bool,
        "amount": int,
        "pending_id": str | None,
        "ledger_id": str | None,
        "violations": list,
        "mode": str
    }
    """
    mode = get_token_issuance_mode()
    
    if mode == "off":
        return {"issued": False, "amount": 0, "mode": "off", "violations": [], "pending_id": None, "ledger_id": None}
    
    # Rule 1: QA must pass
    if qa_status != "PASS":
        return {
            "issued": False,
            "amount": 0,
            "mode": mode,
            "violations": ["qa_not_pass"],
            "pending_id": None,
            "ledger_id": None,
        }
    
    # Rule 2: Audit must be ok
    if not audit_ok:
        return {
            "issued": False,
            "amount": 0,
            "mode": mode,
            "violations": ["audit_not_ok"],
            "pending_id": None,
            "ledger_id": None,
        }
    
    # Base earn amount (conservative)
    base_amount = 10  # 10 RING per successful publish
    
    # Check guardrails
    allowed, guardrail_violations, reduction_pct = check_guardrails(db, user_id)
    
    # Apply reduction
    final_amount = base_amount * (100 - reduction_pct) // 100
    
    if final_amount <= 0:
        final_amount = 0
    
    meta = metadata or {}
    meta["platform"] = platform
    meta["guardrail_violations"] = guardrail_violations
    meta["reduction_pct"] = reduction_pct
    
    if mode == "shadow":
        # Shadow mode: add to pending
        pending_id = add_pending_reward(
            db, user_id, final_amount, "publish_success", meta, draft_id, request_id
        )
        return {
            "issued": False,
            "amount": final_amount,
            "mode": "shadow",
            "violations": guardrail_violations,
            "pending_id": pending_id,
            "ledger_id": None,
        }
    
    elif mode == "live":
        # Live mode: update balance and ledger
        if not allowed or final_amount == 0:
            # Blocked by guardrails
            return {
                "issued": False,
                "amount": 0,
                "mode": "live",
                "violations": guardrail_violations,
                "pending_id": None,
                "ledger_id": None,
            }
        
        current_balance = get_user_balance(db, user_id)
        new_balance = current_balance + final_amount
        
        # Append ledger
        entry = LedgerEntry(
            user_id=user_id,
            event_type="EARN",
            reason_code="publish_success",
            amount=final_amount,
            balance_after=new_balance,
            draft_id=draft_id,
            request_id=request_id,
            receipt_id=receipt_id,
            metadata=meta,
        )
        ledger_id = append_ledger_entry(db, entry)
        
        # Update user balance
        update_user_balance(db, user_id, new_balance)
        
        # Update guardrails
        update_guardrail_state(db, user_id, final_amount)
        
        return {
            "issued": True,
            "amount": final_amount,
            "mode": "live",
            "violations": guardrail_violations,
            "pending_id": None,
            "ledger_id": ledger_id,
        }
    
    return {"issued": False, "amount": 0, "mode": mode, "violations": [], "pending_id": None, "ledger_id": None}


def get_user_ledger(db: Session, user_id: str, limit: int = 20) -> List[Dict]:
    """Get recent ledger entries for user."""
    import json
    
    result = db.execute(
        text("""
            SELECT id, event_type, reason_code, amount, balance_after, metadata, created_at
            FROM ring_ledger
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit},
    )
    
    entries = []
    for row in result.fetchall():
        entries.append({
            "id": str(row[0]),
            "eventType": row[1],
            "reasonCode": row[2],
            "amount": row[3],
            "balanceAfter": row[4],
            "metadata": json.loads(row[5]) if isinstance(row[5], str) else row[5],
            "createdAt": row[6].isoformat() if row[6] else None,
        })
    
    return entries


def get_pending_rewards(db: Session, user_id: str) -> Dict:
    """Get pending rewards summary for shadow mode."""
    result = db.execute(
        text("""
            SELECT COALESCE(SUM(amount), 0), COUNT(*)
            FROM ring_pending
            WHERE user_id = :user_id AND status = 'pending'
        """),
        {"user_id": user_id},
    )
    row = result.fetchone()
    total_pending = row[0] if row else 0
    count = row[1] if row else 0
    
    return {"totalPending": total_pending, "count": count}
