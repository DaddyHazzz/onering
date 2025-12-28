"""
Phase 10.2: Daily Reconciliation Job

Checks ledger integrity and detects balance mismatches.
Shadow mode only: writes ADJUSTMENT entries.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.features.tokens.ledger import (
    get_token_issuance_mode,
    append_ledger_entry,
    LedgerEntry,
    get_user_balance,
    update_user_balance,
)
from backend.features.external.webhooks import enqueue_webhook_event


def run_reconciliation(db: Session) -> Dict:
    """
    Run daily reconciliation.
    
    Checks:
    1. Ledger sum vs user balance for each user
    2. Creates ADJUSTMENT entries if mismatches found (shadow mode only)
    
    Returns reconciliation report.
    """
    mode = get_token_issuance_mode()
    
    if mode == "off":
        return {
            "status": "skipped",
            "mode": "off",
            "mismatches": [],
            "adjustments": [],
        }
    
    # Get all users with ledger activity
    result = db.execute(
        text("""
            SELECT DISTINCT user_id
            FROM ring_ledger
        """)
    )
    user_ids = [row[0] for row in result.fetchall()]
    
    mismatches = []
    adjustments = []
    publish_missing = []
    publish_duplicates = []
    
    max_amount = 2_000_000_000
    for user_id in user_ids:
        # Sum ledger entries
        ledger_result = db.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM ring_ledger
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        )
        ledger_sum = ledger_result.scalar() or 0
        
        # Get current balance
        current_balance = get_user_balance(db, user_id)
        
        # Check mismatch
        if ledger_sum != current_balance:
            mismatch = {
                "user_id": user_id,
                "ledger_sum": ledger_sum,
                "current_balance": current_balance,
                "difference": ledger_sum - current_balance,
            }
            mismatches.append(mismatch)

            if abs(ledger_sum) > max_amount or abs(ledger_sum - current_balance) > max_amount:
                mismatch["overflow"] = True
                enqueue_webhook_event(
                    db,
                    event_type="ring.drift_detected",
                    payload={
                        "user_id": user_id,
                        "ledger_sum": ledger_sum,
                        "current_balance": current_balance,
                        "difference": ledger_sum - current_balance,
                        "mode": mode,
                        "overflow": True,
                        "reconciled_at": datetime.utcnow().isoformat(),
                    },
                    user_id=user_id,
                )
                continue

            enqueue_webhook_event(
                db,
                event_type="ring.drift_detected",
                payload={
                    "user_id": user_id,
                    "ledger_sum": ledger_sum,
                    "current_balance": current_balance,
                    "difference": ledger_sum - current_balance,
                    "mode": mode,
                    "reconciled_at": datetime.utcnow().isoformat(),
                },
                user_id=user_id,
            )
            
            # In shadow mode, log adjustment (don't apply)
            if mode == "shadow":
                adjustment_amount = ledger_sum - current_balance
                entry = LedgerEntry(
                    user_id=user_id,
                    event_type="ADJUSTMENT",
                    reason_code="reconciliation_mismatch",
                    amount=adjustment_amount,
                    balance_after=ledger_sum,
                    metadata={
                        "previous_balance": current_balance,
                        "ledger_sum": ledger_sum,
                        "reconciled_at": datetime.utcnow().isoformat(),
                    },
                )
                ledger_id = append_ledger_entry(db, entry)
                adjustments.append({
                    "ledger_id": ledger_id,
                    "user_id": user_id,
                    "adjustment": adjustment_amount,
                })
            
            # In live mode, apply adjustment
            elif mode == "live":
                adjustment_amount = ledger_sum - current_balance
                entry = LedgerEntry(
                    user_id=user_id,
                    event_type="ADJUSTMENT",
                    reason_code="reconciliation_mismatch",
                    amount=adjustment_amount,
                    balance_after=ledger_sum,
                    metadata={
                        "previous_balance": current_balance,
                        "ledger_sum": ledger_sum,
                        "reconciled_at": datetime.utcnow().isoformat(),
                    },
                )
                ledger_id = append_ledger_entry(db, entry)
                update_user_balance(db, user_id, ledger_sum)
                adjustments.append({
                    "ledger_id": ledger_id,
                    "user_id": user_id,
                    "adjustment": adjustment_amount,
                    "applied": True,
                })

    # Publish event reconciliation (idempotency + missing issuance)
    try:
        publish_rows = db.execute(
            text(
                """
                SELECT id, token_mode, token_ledger_id, token_pending_id
                FROM publish_events
                WHERE token_mode IN ('shadow', 'live')
                """
            )
        ).fetchall()
        for row in publish_rows:
            event_id, token_mode, ledger_id, pending_id = row
            if token_mode == "live" and not ledger_id:
                publish_missing.append({"event_id": str(event_id), "reason": "ledger_missing"})
            if token_mode == "shadow" and not pending_id:
                publish_missing.append({"event_id": str(event_id), "reason": "pending_missing"})

        duplicate_ledger_rows = db.execute(
            text(
                """
                SELECT metadata->>'publish_event_id' AS event_id, COUNT(*)
                FROM ring_ledger
                WHERE metadata ? 'publish_event_id'
                GROUP BY metadata->>'publish_event_id'
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        for row in duplicate_ledger_rows:
            publish_duplicates.append({"event_id": row[0], "count": int(row[1]), "source": "ring_ledger"})

        duplicate_pending_rows = db.execute(
            text(
                """
                SELECT metadata->>'publish_event_id' AS event_id, COUNT(*)
                FROM ring_pending
                WHERE metadata ? 'publish_event_id'
                GROUP BY metadata->>'publish_event_id'
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        for row in duplicate_pending_rows:
            publish_duplicates.append({"event_id": row[0], "count": int(row[1]), "source": "ring_pending"})
    except Exception:
        publish_missing.append({"event_id": "unknown", "reason": "publish_events_unavailable"})
    
    return {
        "status": "completed",
        "mode": mode,
        "users_checked": len(user_ids),
        "mismatches_found": len(mismatches),
        "mismatches": mismatches,
        "adjustments": adjustments,
        "publish_missing": publish_missing,
        "publish_duplicates": publish_duplicates,
        "reconciled_at": datetime.utcnow().isoformat(),
    }


def get_reconciliation_summary(db: Session) -> Dict:
    """Get latest reconciliation summary."""
    # Count adjustment entries in last 24h
    result = db.execute(
        text("""
            SELECT COUNT(*), COALESCE(SUM(ABS(amount)), 0)
            FROM ring_ledger
            WHERE event_type = 'ADJUSTMENT'
              AND reason_code = 'reconciliation_mismatch'
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
    )
    row = result.fetchone()
    
    return {
        "adjustments_last_24h": row[0] if row else 0,
        "total_adjusted": row[1] if row else 0,
    }
