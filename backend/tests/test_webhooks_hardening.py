"""Tests for webhook signing, replay protection, and delivery worker."""
import pytest
import json
import asyncio
from datetime import datetime, timedelta, timezone
from backend.features.external.webhooks import (
    sign_webhook,
    verify_webhook,
    enqueue_webhook_event,
    deliver_webhook,
    get_pending_deliveries,
    generate_webhook_secret,
    _canonical_json_bytes,
)
from backend.core.database import get_db
from sqlalchemy import text


@pytest.fixture
def db():
    """Get test database session."""
    return next(get_db())


def test_webhook_signing_correctness(db):
    """Test webhook signature generation and verification."""
    secret = generate_webhook_secret()
    timestamp = int(datetime.now(timezone.utc).timestamp())
    event_id = "evt_test123"
    payload = {"data": "test"}
    body_bytes = _canonical_json_bytes(payload)

    signature = sign_webhook(secret, timestamp, event_id, body_bytes)
    assert signature.startswith("t=")
    assert ",e=" in signature
    assert ",v1=" in signature

    # Verify signature
    is_valid = verify_webhook(secret, signature, timestamp, event_id, body_bytes, tolerance_seconds=300)
    assert is_valid is True


def test_webhook_replay_protection_expired(db):
    """Test replay protection rejects old events."""
    secret = generate_webhook_secret()
    event_id = "evt_test123"
    payload = {"data": "test"}
    body_bytes = _canonical_json_bytes(payload)

    # Sign with timestamp 10 minutes ago (outside 5-minute window)
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp())
    signature = sign_webhook(secret, old_timestamp, event_id, body_bytes)

    # Verify should fail due to replay window
    is_valid = verify_webhook(secret, signature, old_timestamp, event_id, body_bytes, tolerance_seconds=300)
    assert is_valid is False


def test_webhook_replay_protection_future_tolerance(db):
    """Test replay protection allows slight future timestamps (clock skew)."""
    secret = generate_webhook_secret()
    event_id = "evt_test123"
    payload = {"data": "test"}
    body_bytes = _canonical_json_bytes(payload)

    # Sign with timestamp 2 minutes in future (within 5-minute window)
    future_timestamp = int((datetime.now(timezone.utc) + timedelta(minutes=2)).timestamp())
    signature = sign_webhook(secret, future_timestamp, event_id, body_bytes)

    is_valid = verify_webhook(secret, signature, future_timestamp, event_id, body_bytes, tolerance_seconds=300)
    assert is_valid is True


def test_enqueue_webhook_event_creates_deliveries(db):
    """Test enqueue_webhook_event creates delivery rows for matching subscriptions."""
    # Create webhook subscription
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_test1', 'user123', 'https://example.com/webhook', 'whsec_test', ARRAY['draft.published'], true)
            """
        )
    )
    db.commit()

    # Enqueue event
    event_id, delivery_count = enqueue_webhook_event(
        db,
        event_type="draft.published",
        payload={"post_id": "post123"},
        user_id="user123",
    )

    assert event_id.startswith("evt_")
    assert delivery_count == 1

    # Check delivery was created
    delivery = db.execute(
        text(
            """
            SELECT id, webhook_id, event_id, status, attempts
            FROM webhook_deliveries
            WHERE event_id = :event_id
            """
        ),
        {"event_id": event_id},
    ).fetchone()

    assert delivery is not None
    assert delivery[1] == "wh_test1"
    assert delivery[2] == event_id
    assert delivery[3] == "pending"
    assert delivery[4] == 0


@pytest.mark.asyncio
async def test_deliver_webhook_success(db):
    """Test successful webhook delivery marks as succeeded."""
    # Create webhook and event
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_test2', 'user123', 'https://httpbin.org/status/200', 'whsec_test', ARRAY['ring.earned'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_test2', 'ring.earned', 'user123', '{"amount": 100}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES ('delivery_test2', 'wh_test2', 'evt_test2', 'ring.earned', 'pending', 0, '{"amount": 100}', NOW())
            """
        )
    )
    db.commit()

    # Deliver
    success = await deliver_webhook(db, "delivery_test2")
    assert success is True

    # Check status
    row = db.execute(
        text("SELECT status, delivered_at FROM webhook_deliveries WHERE id = 'delivery_test2'")
    ).fetchone()
    assert row[0] == "succeeded"
    assert row[1] is not None


@pytest.mark.asyncio
async def test_deliver_webhook_retry_backoff(db):
    """Test failed delivery schedules retry with backoff."""
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_test3', 'user123', 'https://httpbin.org/status/500', 'whsec_test', ARRAY['enforcement.failed'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_test3', 'enforcement.failed', 'user123', '{"reason": "QA_FAIL"}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES ('delivery_test3', 'wh_test3', 'evt_test3', 'enforcement.failed', 'pending', 0, '{"reason": "QA_FAIL"}', NOW())
            """
        )
    )
    db.commit()

    # Deliver (will fail)
    success = await deliver_webhook(db, "delivery_test3")
    assert success is False

    # Check retry scheduled
    row = db.execute(
        text(
            """
            SELECT status, attempts, next_attempt_at, last_error
            FROM webhook_deliveries
            WHERE id = 'delivery_test3'
            """
        )
    ).fetchone()

    assert row[0] == "pending"  # Still pending for retry
    assert row[1] == 1  # Attempts incremented
    assert row[2] is not None  # Next attempt scheduled
    assert row[3] is not None  # Error recorded


@pytest.mark.asyncio
async def test_deliver_webhook_dead_after_max_attempts(db):
    """Test delivery marked dead after max attempts."""
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_test4', 'user123', 'https://httpbin.org/status/500', 'whsec_test', ARRAY['ring.earned'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_test4', 'ring.earned', 'user123', '{"amount": 50}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES ('delivery_test4', 'wh_test4', 'evt_test4', 'ring.earned', 'pending', 2, '{"amount": 50}', NOW())
            """
        )
    )
    db.commit()

    # Deliver (3rd attempt, will fail and mark dead)
    success = await deliver_webhook(db, "delivery_test4")
    assert success is False

    # Check marked dead
    row = db.execute(
        text("SELECT status, attempts, next_attempt_at FROM webhook_deliveries WHERE id = 'delivery_test4'")
    ).fetchone()

    assert row[0] == "dead"
    assert row[1] == 3
    assert row[2] is None  # No next attempt


def test_get_pending_deliveries(db):
    """Test get_pending_deliveries returns due deliveries."""
    # Insert past-due and future-due deliveries
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_test5', 'user123', 'https://example.com', 'whsec_test', ARRAY['ring.earned'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_test5a', 'ring.earned', 'user123', '{"amount": 10}'),
                   ('evt_test5b', 'ring.earned', 'user123', '{"amount": 20}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, next_attempt_at, event_timestamp)
            VALUES ('delivery_test5a', 'wh_test5', 'evt_test5a', 'ring.earned', 'pending', 0, '{}', NOW() - INTERVAL '1 hour', NOW()),
                   ('delivery_test5b', 'wh_test5', 'evt_test5b', 'ring.earned', 'pending', 0, '{}', NOW() + INTERVAL '1 hour', NOW())
            """
        )
    )
    db.commit()

    pending = get_pending_deliveries(db, limit=10)
    assert "delivery_test5a" in pending
    assert "delivery_test5b" not in pending
