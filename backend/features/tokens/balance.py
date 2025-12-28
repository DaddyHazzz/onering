"""
Canonical balance resolution for Phase 10.2.

Ledger is the source of truth in shadow/live modes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.features.tokens.ledger import get_token_issuance_mode, get_user_ledger
from backend.features.tokens.reconciliation import get_reconciliation_summary


def assert_legacy_ring_writes_allowed() -> tuple[bool, str]:
    """Return (allowed, mode). Legacy writes are blocked in shadow/live."""
    mode = get_token_issuance_mode()
    return (mode == "off"), mode


def _iso(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _get_legacy_balance(db: Session, user_id: str) -> int:
    row = db.execute(
        text('SELECT "ringBalance" FROM users WHERE "clerkId" = :user_id'),
        {"user_id": user_id},
    ).fetchone()
    return int(row[0]) if row else 0


def _get_pending_summary(db: Session, user_id: str) -> tuple[int, int, Optional[datetime]]:
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*), MAX(created_at) AS last_at
            FROM ring_pending
            WHERE user_id = :user_id AND status = 'pending'
            """
        ),
        {"user_id": user_id},
    ).fetchone()
    if not row:
        return 0, 0, None
    return int(row[0] or 0), int(row[1] or 0), row[2]


def _get_last_ledger_state(db: Session, user_id: str) -> tuple[Optional[int], Optional[datetime]]:
    row = db.execute(
        text(
            """
            SELECT balance_after, created_at
            FROM ring_ledger
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).fetchone()
    if not row:
        return None, None
    return int(row[0]) if row[0] is not None else None, row[1]


def _get_shadow_ledger_delta(db: Session, user_id: str) -> int:
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM ring_ledger
            WHERE user_id = :user_id
              AND event_type IN ('SPEND', 'PENALTY', 'ADJUSTMENT')
            """
        ),
        {"user_id": user_id},
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _get_guardrails_state(db: Session, user_id: str) -> Optional[Dict[str, Optional[str]]]:
    row = db.execute(
        text(
            """
            SELECT daily_earn_count, daily_earn_total, last_earn_at, reset_at, updated_at
            FROM ring_guardrails_state
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).fetchone()
    if not row:
        return None
    return {
        "daily_earn_count": int(row[0] or 0),
        "daily_earn_total": int(row[1] or 0),
        "last_earn_at": _iso(row[2]),
        "reset_at": _iso(row[3]),
        "updated_at": _iso(row[4]),
    }


def _get_clerk_sync(db: Session, user_id: str) -> Dict[str, Optional[str]]:
    row = db.execute(
        text(
            """
            SELECT last_sync_at, last_error, last_error_at
            FROM ring_clerk_sync
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).fetchone()
    if not row:
        return {"last_at": None, "last_error": None, "last_error_at": None}
    return {
        "last_at": _iso(row[0]),
        "last_error": row[1],
        "last_error_at": _iso(row[2]),
    }


def get_effective_ring_balance(db: Session, user_id: str) -> Dict:
    """
    Resolve canonical balance for a user based on token issuance mode.
    """
    mode = get_token_issuance_mode()
    legacy_balance = _get_legacy_balance(db, user_id)
    pending_total, pending_count, last_pending_at = _get_pending_summary(db, user_id)
    ledger_balance, last_ledger_at = _get_last_ledger_state(db, user_id)
    guardrails_state = _get_guardrails_state(db, user_id)
    clerk_sync = _get_clerk_sync(db, user_id)

    if mode == "off":
        balance = legacy_balance
        effective_balance = legacy_balance
    elif mode == "shadow":
        shadow_delta = _get_shadow_ledger_delta(db, user_id)
        balance = legacy_balance
        effective_balance = legacy_balance + pending_total + shadow_delta
    else:
        balance = ledger_balance if ledger_balance is not None else legacy_balance
        effective_balance = balance

    return {
        "mode": mode,
        "balance": int(balance),
        "pending_total": int(pending_total),
        "pending_count": int(pending_count),
        "effective_balance": int(effective_balance),
        "last_ledger_at": _iso(last_ledger_at),
        "last_pending_at": _iso(last_pending_at),
        "guardrails_state": guardrails_state,
        "clerk_sync": clerk_sync,
    }


def get_balance_summary(db: Session, user_id: str, *, limit: int = 20) -> Dict:
    """
    Expanded balance summary with recent ledger and publish events.
    """
    summary = get_effective_ring_balance(db, user_id)

    ledger_entries = get_user_ledger(db, user_id, limit)
    publish_rows = db.execute(
        text(
            """
            SELECT id, platform, published_at, platform_post_id, token_mode,
                   token_issued_amount, token_pending_amount, token_reason_code, created_at
            FROM publish_events
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": limit},
    ).fetchall()
    publish_events = [
        {
            "event_id": str(row[0]),
            "platform": row[1],
            "published_at": _iso(row[2]),
            "platform_post_id": row[3],
            "token_mode": row[4],
            "token_issued_amount": row[5],
            "token_pending_amount": row[6],
            "token_reason_code": row[7],
            "created_at": _iso(row[8]),
        }
        for row in publish_rows
    ]

    reconciliation_summary = get_reconciliation_summary(db)

    return {
        **summary,
        "ledger_entries": ledger_entries,
        "publish_events": publish_events,
        "reconciliation_status": reconciliation_summary,
    }
