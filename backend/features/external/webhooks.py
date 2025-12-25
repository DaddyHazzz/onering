"""
Webhook delivery system (Phase 10.3).

Handles webhook subscriptions, event emission, and delivery with retries.
Uses HMAC-SHA256 signatures for security.

Event types:
- draft.published
- ring.passed
- ring.earned (token issuance)
- enforcement.failed
"""
import os
import hmac
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
import httpx


WEBHOOK_TIMEOUT_SECONDS = 10
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min


def is_webhooks_enabled() -> bool:
    """Check if webhooks are enabled."""
    return os.getenv("ONERING_WEBHOOKS_ENABLED", "0") == "1"


def generate_webhook_secret() -> str:
    """Generate webhook signing secret."""
    return f"whsec_{secrets.token_hex(32)}"


def sign_webhook_payload(payload: dict, secret: str, timestamp: int) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.
    Signature format: v1,<hex_signature>
    Signed data: <timestamp>.<json_payload>
    """
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    signed_content = f"{timestamp}.{payload_str}"
    signature = hmac.new(
        secret.encode(),
        signed_content.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"v1,{signature}"


def verify_webhook_signature(payload: dict, signature: str, secret: str, timestamp: int, tolerance_seconds: int = 300) -> bool:
    """
    Verify webhook signature.
    Allows timestamp tolerance to prevent replay attacks.
    """
    # Check timestamp freshness
    now = int(datetime.utcnow().timestamp())
    if abs(now - timestamp) > tolerance_seconds:
        return False
    
    # Verify signature
    expected_sig = sign_webhook_payload(payload, secret, timestamp)
    return hmac.compare_digest(signature, expected_sig)


def create_webhook_subscription(
    db: Session,
    owner_user_id: str,
    url: str,
    events: List[str],
) -> Dict:
    """
    Create webhook subscription.
    Returns subscription details including secret (only shown once).
    """
    secret = generate_webhook_secret()
    
    result = db.execute(
        text("""
            INSERT INTO external_webhooks (owner_user_id, url, secret, events)
            VALUES (:owner_user_id, :url, :secret, :events)
            RETURNING id
        """),
        {
            "owner_user_id": owner_user_id,
            "url": url,
            "secret": secret,
            "events": events,
        }
    )
    db.commit()
    
    return {
        "id": str(result.scalar()),
        "url": url,
        "secret": secret,  # Only shown once
        "events": events,
    }


def list_webhook_subscriptions(db: Session, owner_user_id: str) -> List[Dict]:
    """List webhook subscriptions for user."""
    rows = db.execute(
        text("""
            SELECT id, url, events, is_active, created_at, last_delivered_at
            FROM external_webhooks
            WHERE owner_user_id = :owner_user_id
            ORDER BY created_at DESC
        """),
        {"owner_user_id": owner_user_id}
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
    """Delete webhook subscription (if owned by user)."""
    result = db.execute(
        text("""
            UPDATE external_webhooks
            SET is_active = false
            WHERE id = :webhook_id AND owner_user_id = :owner_user_id
            RETURNING id
        """),
        {"webhook_id": webhook_id, "owner_user_id": owner_user_id}
    )
    db.commit()
    return result.rowcount > 0


def emit_webhook_event(
    db: Session,
    event_type: str,
    payload: Dict,
    user_id: Optional[str] = None,
) -> int:
    """
    Emit webhook event to all matching subscriptions.
    Returns count of deliveries created.
    """
    if not is_webhooks_enabled():
        return 0
    
    event_id = f"evt_{secrets.token_hex(16)}"
    
    # Find matching webhooks
    if user_id:
        webhooks = db.execute(
            text("""
                SELECT id, url, secret
                FROM external_webhooks
                WHERE owner_user_id = :user_id
                AND is_active = true
                AND :event_type = ANY(events)
            """),
            {"user_id": user_id, "event_type": event_type}
        ).fetchall()
    else:
        # Global events (e.g., enforcement.failed)
        webhooks = db.execute(
            text("""
                SELECT id, url, secret
                FROM external_webhooks
                WHERE is_active = true
                AND :event_type = ANY(events)
            """),
            {"event_type": event_type}
        ).fetchall()
    
    if not webhooks:
        return 0
    
    # Create delivery records
    delivery_count = 0
    for webhook in webhooks:
        webhook_id, url, secret = webhook
        
        db.execute(
            text("""
                INSERT INTO webhook_deliveries
                (webhook_id, event_id, event_type, status, payload, next_retry_at)
                VALUES (:webhook_id, :event_id, :event_type, 'pending', :payload, NOW())
            """),
            {
                "webhook_id": webhook_id,
                "event_id": event_id,
                "event_type": event_type,
                "payload": json.dumps(payload),
            }
        )
        delivery_count += 1
    
    db.commit()
    return delivery_count


async def deliver_webhook(db: Session, delivery_id: str) -> bool:
    """
    Attempt to deliver a single webhook.
    Returns True if successful, False otherwise.
    Updates delivery record with result.
    """
    # Fetch delivery + webhook info
    row = db.execute(
        text("""
            SELECT d.webhook_id, d.event_id, d.event_type, d.payload, d.attempts,
                   w.url, w.secret
            FROM webhook_deliveries d
            JOIN external_webhooks w ON w.id = d.webhook_id
            WHERE d.id = :delivery_id AND d.status = 'pending'
        """),
        {"delivery_id": delivery_id}
    ).fetchone()
    
    if not row:
        return False
    
    webhook_id, event_id, event_type, payload_json, attempts, url, secret = row
    payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
    
    # Prepare webhook delivery
    timestamp = int(datetime.utcnow().timestamp())
    full_payload = {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "data": payload,
    }
    
    signature = sign_webhook_payload(full_payload, secret, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-OneRing-Signature": signature,
        "X-OneRing-Event-Type": event_type,
        "X-OneRing-Event-ID": event_id,
        "X-OneRing-Timestamp": str(timestamp),
    }
    
    # Attempt delivery
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=full_payload, headers=headers)
            response.raise_for_status()
        
        # Success
        db.execute(
            text("""
                UPDATE webhook_deliveries
                SET status = 'succeeded', delivered_at = NOW(), attempts = :attempts
                WHERE id = :delivery_id
            """),
            {"delivery_id": delivery_id, "attempts": attempts + 1}
        )
        
        # Update webhook last_delivered_at
        db.execute(
            text("UPDATE external_webhooks SET last_delivered_at = NOW() WHERE id = :webhook_id"),
            {"webhook_id": webhook_id}
        )
        
        db.commit()
        return True
    
    except Exception as e:
        # Failure - schedule retry or mark failed
        attempts += 1
        
        if attempts >= MAX_RETRY_ATTEMPTS:
            # Give up
            db.execute(
                text("""
                    UPDATE webhook_deliveries
                    SET status = 'failed', attempts = :attempts, last_error = :error
                    WHERE id = :delivery_id
                """),
                {
                    "delivery_id": delivery_id,
                    "attempts": attempts,
                    "error": str(e)[:500],
                }
            )
        else:
            # Schedule retry
            retry_delay = RETRY_DELAYS[attempts - 1] if attempts <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
            next_retry = datetime.utcnow() + timedelta(seconds=retry_delay)
            
            db.execute(
                text("""
                    UPDATE webhook_deliveries
                    SET attempts = :attempts, last_error = :error, next_retry_at = :next_retry
                    WHERE id = :delivery_id
                """),
                {
                    "delivery_id": delivery_id,
                    "attempts": attempts,
                    "error": str(e)[:500],
                    "next_retry": next_retry,
                }
            )
        
        db.commit()
        return False


def get_pending_deliveries(db: Session, limit: int = 100) -> List[str]:
    """Get pending webhook deliveries ready for retry."""
    rows = db.execute(
        text("""
            SELECT id
            FROM webhook_deliveries
            WHERE status = 'pending'
            AND (next_retry_at IS NULL OR next_retry_at <= NOW())
            ORDER BY created_at
            LIMIT :limit
        """),
        {"limit": limit}
    ).fetchall()
    
    return [str(row[0]) for row in rows]
