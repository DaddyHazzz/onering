"""
Billing retry engine (Phase 4.5).

Deterministic, idempotent retry scheduling for failed webhook events.
No external Stripe calls are made here; processing marks events as processed
based on stored local state only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, insert
from sqlalchemy.orm import Session

from backend.core.database import (
    get_db_session,
    billing_retry_queue,
    billing_events,
    billing_admin_audit,
)


MAX_ATTEMPTS_DEFAULT = 10


def _compute_backoff(attempt_count: int) -> timedelta:
    """Exponential backoff with floor 30s and cap 1 hour."""
    base = max(30, 2 ** attempt_count)
    seconds = min(base, 3600)
    return timedelta(seconds=seconds)


def enqueue_retry(stripe_event_id: str, error: str, now: Optional[datetime] = None) -> None:
    """Upsert a retry queue row for a failed webhook event.

    If a row exists, updates last_error and schedules next_attempt_at based on backoff.
    """
    ts = now or datetime.now(timezone.utc)
    with get_db_session() as session:
        existing = session.execute(
            select(
                billing_retry_queue.c.id,
                billing_retry_queue.c.attempt_count,
                billing_retry_queue.c.status,
            ).where(billing_retry_queue.c.stripe_event_id == stripe_event_id)
        ).fetchone()

        if existing:
            attempt = int(existing.attempt_count or 0)
            next_attempt = ts + _compute_backoff(attempt)
            session.execute(
                update(billing_retry_queue)
                .where(billing_retry_queue.c.stripe_event_id == stripe_event_id)
                .values(
                    last_error=error,
                    next_attempt_at=next_attempt,
                    status='pending',
                    updated_at=ts,
                )
            )
        else:
            next_attempt = ts + _compute_backoff(0)
            session.execute(
                insert(billing_retry_queue).values(
                    stripe_event_id=stripe_event_id,
                    last_error=error,
                    attempt_count=0,
                    next_attempt_at=next_attempt,
                    status='pending',
                    created_at=ts,
                    updated_at=ts,
                )
            )

        # Audit enqueue
        session.execute(
            insert(billing_admin_audit).values(
                actor="system_job",
                action="billing.retry.enqueue",
                target_user_id=None,
                target_resource=stripe_event_id,
                payload_json=f"{{\"last_error\": {repr(error)}, \"next_attempt_at\": \"{next_attempt.isoformat()}\"}}",
            )
        )
        session.commit()


def claim_due_retries(limit: int, now: Optional[datetime] = None, owner: str = "scheduler") -> List[Dict[str, Any]]:
    """Claim due retry rows by marking them processing and locking them.

    SQLite doesn't support SKIP LOCKED; tests run single-threaded so this is safe.
    """
    ts = now or datetime.now(timezone.utc)
    claimed = []
    with get_db_session() as session:
        rows = session.execute(
            select(
                billing_retry_queue.c.id,
                billing_retry_queue.c.stripe_event_id,
                billing_retry_queue.c.attempt_count,
                billing_retry_queue.c.next_attempt_at,
            )
            .where(billing_retry_queue.c.status == 'pending')
            .where(billing_retry_queue.c.next_attempt_at <= ts)
            .order_by(billing_retry_queue.c.next_attempt_at.asc())
            .limit(limit)
        ).fetchall()

        for r in rows:
            session.execute(
                update(billing_retry_queue)
                .where(billing_retry_queue.c.id == r.id)
                .values(status='processing', locked_at=ts, lock_owner=owner, updated_at=ts)
            )
            claimed.append({
                'id': r.id,
                'stripe_event_id': r.stripe_event_id,
                'attempt_count': int(r.attempt_count or 0),
                'next_attempt_at': r.next_attempt_at,
            })
        session.commit()
    return claimed


def process_retry(row: Dict[str, Any], max_attempts: int = MAX_ATTEMPTS_DEFAULT, now: Optional[datetime] = None) -> bool:
    """Process a single retry row.

    Returns True if succeeded, False otherwise.
    """
    ts = now or datetime.now(timezone.utc)
    event_id = row['stripe_event_id']
    attempt = int(row['attempt_count'] or 0)

    with get_db_session() as session:
        # If event is already processed, mark succeeded
        ev = session.execute(
            select(
                billing_events.c.id,
                billing_events.c.processed,
                billing_events.c.error,
            ).where(billing_events.c.stripe_event_id == event_id)
        ).fetchone()

        succeeded = False
        if ev and bool(ev.processed):
            succeeded = True
        elif ev:
            # Deterministic local processing: mark processed
            session.execute(
                update(billing_events)
                .where(billing_events.c.stripe_event_id == event_id)
                .values(processed=True, processed_at=ts, error=None)
            )
            succeeded = True
        else:
            # Missing payload/event; cannot process
            succeeded = False

        # Compute next state
        new_attempt = attempt + 1
        if succeeded:
            session.execute(
                update(billing_retry_queue)
                .where(billing_retry_queue.c.stripe_event_id == event_id)
                .values(status='succeeded', attempt_count=new_attempt, locked_at=None, lock_owner=None, updated_at=ts)
            )
        else:
            if new_attempt >= max_attempts:
                session.execute(
                    update(billing_retry_queue)
                    .where(billing_retry_queue.c.stripe_event_id == event_id)
                    .values(status='failed', attempt_count=new_attempt, locked_at=None, lock_owner=None, updated_at=ts)
                )
            else:
                next_attempt = ts + _compute_backoff(new_attempt)
                session.execute(
                    update(billing_retry_queue)
                    .where(billing_retry_queue.c.stripe_event_id == event_id)
                    .values(status='pending', attempt_count=new_attempt, next_attempt_at=next_attempt, locked_at=None, lock_owner=None, updated_at=ts)
                )

        # Audit
        session.execute(
            insert(billing_admin_audit).values(
                actor="system_job",
                action="billing.retry.attempt",
                target_user_id=None,
                target_resource=event_id,
                payload_json=f"{{\"attempt\": {new_attempt}, \"succeeded\": {str(succeeded).lower()} }}",
            )
        )
        session.commit()

    return succeeded


def mark_succeeded(stripe_event_id: str, now: Optional[datetime] = None) -> None:
    ts = now or datetime.now(timezone.utc)
    with get_db_session() as session:
        session.execute(
            update(billing_retry_queue)
            .where(billing_retry_queue.c.stripe_event_id == stripe_event_id)
            .values(status='succeeded', updated_at=ts)
        )
        session.commit()


def mark_failed(stripe_event_id: str, now: Optional[datetime] = None) -> None:
    ts = now or datetime.now(timezone.utc)
    with get_db_session() as session:
        session.execute(
            update(billing_retry_queue)
            .where(billing_retry_queue.c.stripe_event_id == stripe_event_id)
            .values(status='failed', updated_at=ts)
        )
        session.commit()
