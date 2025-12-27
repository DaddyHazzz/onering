"""Webhook delivery system (Phase 10.3 hardening).

Durable webhook event log + delivery worker with retries and replay-safe signing.
"""
from __future__ import annotations

import os
import hmac
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session


WEBHOOK_TIMEOUT_SECONDS = 10


def _parse_backoff() -> List[int]:
    raw = os.getenv("ONERING_WEBHOOKS_BACKOFF_SECONDS", "60,300,900")
    try:
        values = [int(x.strip()) for x in raw.split(",") if x.strip()]
        return values or [60, 300, 900]
    except Exception:
        return [60, 300, 900]


def get_max_attempts() -> int:
    try:
        return int(os.getenv("ONERING_WEBHOOKS_MAX_ATTEMPTS", "3"))
    except ValueError:
        return 3


def is_webhooks_enabled() -> bool:
    return os.getenv("ONERING_WEBHOOKS_ENABLED", "0") == "1"


def is_delivery_enabled() -> bool:
    return os.getenv("ONERING_WEBHOOKS_DELIVERY_ENABLED", "0") == "1"


def generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_hex(32)}"


def _canonical_json_bytes(payload: Dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def sign_webhook(secret: str, timestamp: int, event_id: str, body_bytes: bytes) -> str:
    """Sign webhook payload using HMAC-SHA256 over timestamp + event_id + raw body."""
    signed_content = f"{timestamp}.{event_id}.".encode() + body_bytes
    digest = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
    # Format includes timestamp and event id for consumer convenience
    return f"t={timestamp},e={event_id},v1={digest}"


def verify_webhook(secret: str, signature_header: str, timestamp: int, event_id: str, body_bytes: bytes, tolerance_seconds: int = 300) -> bool:
    """Verify webhook signature and replay window."""
    try:
        tolerance = int(os.getenv("ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS", str(tolerance_seconds)))
    except ValueError:
        tolerance = tolerance_seconds
    # Replay protection
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - timestamp) > tolerance:
        return False

    # Extract provided signature
    provided = None
    for part in signature_header.split(','):
        if part.strip().startswith('v1='):
            provided = part.strip().split('=', 1)[1]
            break
    if not provided:
        return False

    expected_header = sign_webhook(secret, timestamp, event_id, body_bytes)
    expected = None
    for part in expected_header.split(','):
        if part.strip().startswith('v1='):
            expected = part.strip().split('=', 1)[1]
            break
    if not expected:
        return False

    return hmac.compare_digest(provided, expected)


def create_webhook_subscription(db: Session, owner_user_id: str, url: str, events: List[str]) -> Dict:
    secret = generate_webhook_secret()
    result = db.execute(
        text(
            """
            INSERT INTO external_webhooks (owner_user_id, url, secret, events)
            VALUES (:owner_user_id, :url, :secret, :events)
            RETURNING id
            """
        ),
        {"owner_user_id": owner_user_id, "url": url, "secret": secret, "events": events},
    )
    db.commit()
    return {"id": str(result.scalar()), "url": url, "secret": secret, "events": events}


def list_webhook_subscriptions(db: Session, owner_user_id: str) -> List[Dict]:
    rows = db.execute(
        text(
            """
            SELECT id, url, events, is_active, created_at, last_delivered_at
            FROM external_webhooks
            WHERE owner_user_id = :owner_user_id
            ORDER BY created_at DESC
            """
        ),
        {"owner_user_id": owner_user_id},
    ).fetchall()

    return [
        {
            "id": str(row[0]),
            "url": row[1],
            "events": row[2],
            "is_active": row[3],
            "created_at": row[4].isoformat(),
            "last_delivered_at": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    ]


def delete_webhook_subscription(db: Session, webhook_id: str, owner_user_id: str) -> bool:
    result = db.execute(
        text(
            """
            UPDATE external_webhooks
            SET is_active = false
            WHERE id = :webhook_id AND owner_user_id = :owner_user_id
            RETURNING id
            """
        ),
        {"webhook_id": webhook_id, "owner_user_id": owner_user_id},
    )
    db.commit()
    return result.rowcount > 0


def enqueue_webhook_event(db: Session, event_type: str, payload: Dict, user_id: Optional[str] = None, event_id: Optional[str] = None) -> Tuple[str, int]:
    """Persist webhook event and create delivery rows. Returns (event_id, delivery_count)."""
    if not is_webhooks_enabled():
        return (event_id or f"evt_{secrets.token_hex(16)}", 0)

    event_id = event_id or str(uuid.uuid4())
    event_timestamp = datetime.now(timezone.utc)

    # Persist event
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload, created_at)
            VALUES (:id, :event_type, :user_id, CAST(:payload AS jsonb), :created_at)
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {
            "id": event_id,
            "event_type": event_type,
            "user_id": user_id,
            "payload": json.dumps(payload),
            "created_at": event_timestamp,
        },
    )

    # Find matching webhooks
    if user_id:
        webhooks = db.execute(
            text(
                """
                SELECT id
                FROM external_webhooks
                WHERE owner_user_id = :user_id
                  AND is_active = true
                  AND :event_type = ANY(events)
                """
            ),
            {"user_id": user_id, "event_type": event_type},
        ).fetchall()
    else:
        webhooks = db.execute(
            text(
                """
                SELECT id
                FROM external_webhooks
                WHERE is_active = true
                  AND :event_type = ANY(events)
                """
            ),
            {"event_type": event_type},
        ).fetchall()

    if not webhooks:
        db.commit()
        return event_id, 0

    delivery_count = 0
    for (webhook_id,) in webhooks:
        db.execute(
            text(
                """
                INSERT INTO webhook_deliveries
                (webhook_id, event_id, event_type, status, attempts, payload, next_attempt_at, event_timestamp)
                VALUES (:webhook_id, :event_id, :event_type, 'pending', 0, CAST(:payload AS jsonb), :next_attempt_at, :event_timestamp)
                """
            ),
            {
                "webhook_id": webhook_id,
                "event_id": event_id,
                "event_type": event_type,
                "payload": json.dumps(payload),
                "next_attempt_at": event_timestamp,
                "event_timestamp": event_timestamp,
            },
        )
        delivery_count += 1

    db.commit()
    return event_id, delivery_count


async def deliver_webhook(db: Session, delivery_id: str) -> bool:
    """Attempt a single delivery with retries/backoff. Returns True on success."""
    if not is_delivery_enabled():
        return False

    backoff = _parse_backoff()
    max_attempts = get_max_attempts()

    row = db.execute(
        text(
            """
            SELECT d.id, d.webhook_id, d.event_id, d.event_type, d.payload, d.attempts, d.next_attempt_at, d.event_timestamp,
                   w.url, w.secret
            FROM webhook_deliveries d
            JOIN external_webhooks w ON w.id = d.webhook_id
            WHERE d.id = :delivery_id AND d.status = 'pending' AND (d.next_attempt_at IS NULL OR d.next_attempt_at <= NOW())
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"delivery_id": delivery_id},
    ).fetchone()

    if not row:
        return False

    _, webhook_id, event_id, event_type, payload_json, attempts, _, event_timestamp, url, secret = row
    payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json

    current_attempt = attempts + 1
    db.execute(
        text("UPDATE webhook_deliveries SET status = 'delivering', attempts = :attempts WHERE id = :id"),
        {"id": delivery_id, "attempts": current_attempt},
    )
    db.commit()

    timestamp = int(event_timestamp.timestamp()) if isinstance(event_timestamp, datetime) else int(datetime.now(timezone.utc).timestamp())
    
    # Replay protection check
    try:
        replay_window = int(os.getenv("ONERING_WEBHOOKS_REPLAY_WINDOW_SECONDS", "300"))
    except ValueError:
        replay_window = 300
    
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if abs(now_ts - timestamp) > replay_window:
        db.execute(
            text(
                """
                UPDATE webhook_deliveries
                SET status = 'failed', last_error = 'REPLAY_EXPIRED: event outside replay window'
                WHERE id = :id
                """
            ),
            {"id": delivery_id},
        )
        db.commit()
        return False
    
    body = {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "data": payload,
    }
    body_bytes = _canonical_json_bytes(body)
    signature = sign_webhook(secret, timestamp, event_id, body_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-OneRing-Signature": signature,
        "X-OneRing-Event-Type": event_type,
        "X-OneRing-Event-ID": event_id,
        "X-OneRing-Timestamp": str(timestamp),
    }

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, content=body_bytes, headers=headers)
            status_code = response.status_code
            response.raise_for_status()

        try:
            db.execute(
                text(
                    """
                    UPDATE webhook_deliveries
                    SET status = 'succeeded', delivered_at = NOW(), last_status_code = :status_code
                    WHERE id = :id
                    """
                ),
                {"id": delivery_id, "status_code": status_code},
            )
        except ProgrammingError as exc:
            db.rollback()
            if "last_status_code" in str(exc) or "delivered_at" in str(exc):
                db.execute(
                    text(
                        """
                        UPDATE webhook_deliveries
                        SET status = 'succeeded'
                        WHERE id = :id
                        """
                    ),
                    {"id": delivery_id},
                )
            else:
                raise
        db.execute(
            text("UPDATE external_webhooks SET last_delivered_at = NOW() WHERE id = :webhook_id"),
            {"webhook_id": webhook_id},
        )
        db.commit()
        return True
    except Exception as exc:
        delay = backoff[min(current_attempt - 1, len(backoff) - 1)]
        next_attempt = datetime.now(timezone.utc) + timedelta(seconds=delay)
        status = "dead" if current_attempt >= max_attempts else "pending"

        try:
            db.execute(
                text(
                    """
                    UPDATE webhook_deliveries
                    SET status = :status, last_error = :error, last_status_code = :status_code,
                        next_attempt_at = :next_attempt
                    WHERE id = :id
                    """
                ),
                {
                    "id": delivery_id,
                    "status": status,
                    "error": str(exc)[:500],
                    "status_code": getattr(exc, "status_code", None) or (getattr(exc, "response", None).status_code if getattr(exc, "response", None) else None),
                    "next_attempt": next_attempt if status == "pending" else None,
                },
            )
        except ProgrammingError as update_exc:
            db.rollback()
            if "last_status_code" in str(update_exc) or "last_error" in str(update_exc):
                db.execute(
                    text(
                        """
                        UPDATE webhook_deliveries
                        SET status = :status, next_attempt_at = :next_attempt
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": delivery_id,
                        "status": status,
                        "next_attempt": next_attempt if status == "pending" else None,
                    },
                )
            else:
                raise
        db.commit()
        return False


def get_pending_deliveries(db: Session, limit: int = 100) -> List[str]:
    rows = db.execute(
        text(
            """
            SELECT id
            FROM webhook_deliveries
            WHERE status = 'pending'
              AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
            ORDER BY next_attempt_at NULLS FIRST, created_at
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).fetchall()
    return [str(row[0]) for row in rows]


# Backwards-compatible helper name used in earlier tests
def emit_webhook_event(db: Session, event_type: str, payload: Dict, user_id: Optional[str] = None) -> int:
    """Alias for enqueue_webhook_event; returns delivery count for compatibility."""
    _, count = enqueue_webhook_event(db, event_type=event_type, payload=payload, user_id=user_id)
    return count


# Legacy signing helpers used in existing tests
def sign_webhook_payload(payload: Dict, secret: str, timestamp: int) -> str:
    """Legacy signature format: v1,<hexdigest>."""
    body_bytes = _canonical_json_bytes(payload)
    signed_content = f"{timestamp}.".encode() + body_bytes
    digest = hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()
    return f"v1,{digest}"


def verify_webhook_signature(
    payload: Dict,
    signature: str,
    secret: str,
    timestamp: int,
    tolerance_seconds: int = 300,
) -> bool:
    """Legacy verification for v1,<hexdigest> signatures."""
    now = int(datetime.utcnow().timestamp())
    if abs(now - timestamp) > tolerance_seconds:
        return False
    if not signature.startswith("v1,"):
        return False
    expected = sign_webhook_payload(payload, secret, timestamp)
    return hmac.compare_digest(signature, expected)
