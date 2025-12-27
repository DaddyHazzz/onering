"""Tests for webhook signing, replay protection, and delivery worker."""
import pytest
import uuid
import json
import asyncio
import httpx
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


class _FakeAsyncClient:
    def __init__(self, status_code: int):
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        request = httpx.Request("POST", "https://example.com")
        return httpx.Response(self._status_code, request=request, text="ok")


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


def test_enqueue_webhook_event_creates_deliveries(db, monkeypatch):
    """Test enqueue_webhook_event creates delivery rows for matching subscriptions."""
    monkeypatch.setattr("backend.features.external.webhooks.is_webhooks_enabled", lambda: True)
    user_id = f"user_{uuid.uuid4()}"
    # Create webhook subscription
    webhook_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, :user_id, 'https://example.com/webhook', 'whsec_test', ARRAY['draft.published'], true)
            """
        ),
        {"id": webhook_id, "user_id": user_id},
    )
    db.commit()

    # Enqueue event
    event_id, delivery_count = enqueue_webhook_event(
        db,
        event_type="draft.published",
        payload={"post_id": "post123"},
        user_id=user_id,
    )

    uuid.UUID(event_id)
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
    assert str(delivery[1]) == webhook_id
    assert delivery[2] == event_id
    assert delivery[3] == "pending"
    assert delivery[4] == 0


@pytest.mark.asyncio
async def test_deliver_webhook_success(db, monkeypatch):
    """Test successful webhook delivery marks as succeeded."""
    monkeypatch.setattr("backend.features.external.webhooks.httpx.AsyncClient", lambda **kwargs: _FakeAsyncClient(200))
    monkeypatch.setattr("backend.features.external.webhooks.is_delivery_enabled", lambda: True)
    user_id = f"user_{uuid.uuid4()}"
    # Create webhook and event
    webhook_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    delivery_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, :user_id, 'https://httpbin.org/status/200', 'whsec_test', ARRAY['ring.earned'], true)
            """
        ),
        {"id": webhook_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id, 'ring.earned', :user_id, '{"amount": 100}')
            """
        ),
        {"id": event_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES (:id, :webhook_id, :event_id, 'ring.earned', 'pending', 0, '{"amount": 100}', NOW())
            """
        ),
        {"id": delivery_id, "webhook_id": webhook_id, "event_id": event_id},
    )
    db.commit()

    # Deliver
    success = await deliver_webhook(db, delivery_id)
    assert success is True

    # Check status
    row = db.execute(
        text("SELECT status, delivered_at FROM webhook_deliveries WHERE id = :id"),
        {"id": delivery_id},
    ).fetchone()
    assert row[0] == "succeeded"
    assert row[1] is not None


@pytest.mark.asyncio
async def test_deliver_webhook_retry_backoff(db, monkeypatch):
    """Test failed delivery schedules retry with backoff."""
    monkeypatch.setattr("backend.features.external.webhooks.httpx.AsyncClient", lambda **kwargs: _FakeAsyncClient(500))
    monkeypatch.setattr("backend.features.external.webhooks.is_delivery_enabled", lambda: True)
    user_id = f"user_{uuid.uuid4()}"
    webhook_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    delivery_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, :user_id, 'https://httpbin.org/status/500', 'whsec_test', ARRAY['enforcement.failed'], true)
            """
        ),
        {"id": webhook_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id, 'enforcement.failed', :user_id, '{"reason": "QA_FAIL"}')
            """
        ),
        {"id": event_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES (:id, :webhook_id, :event_id, 'enforcement.failed', 'pending', 0, '{"reason": "QA_FAIL"}', NOW())
            """
        ),
        {"id": delivery_id, "webhook_id": webhook_id, "event_id": event_id},
    )
    db.commit()

    # Deliver (will fail)
    success = await deliver_webhook(db, delivery_id)
    assert success is False

    # Check retry scheduled
    row = db.execute(
        text(
            """
            SELECT status, attempts, next_attempt_at, last_error
            FROM webhook_deliveries
            WHERE id = :id
            """
        ),
        {"id": delivery_id},
    ).fetchone()

    assert row[0] == "pending"  # Still pending for retry
    assert row[1] == 1  # Attempts incremented
    assert row[2] is not None  # Next attempt scheduled
    assert row[3] is not None  # Error recorded


@pytest.mark.asyncio
async def test_deliver_webhook_dead_after_max_attempts(db, monkeypatch):
    """Test delivery marked dead after max attempts."""
    monkeypatch.setattr("backend.features.external.webhooks.httpx.AsyncClient", lambda **kwargs: _FakeAsyncClient(500))
    monkeypatch.setattr("backend.features.external.webhooks.is_delivery_enabled", lambda: True)
    user_id = f"user_{uuid.uuid4()}"
    webhook_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    delivery_id = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, :user_id, 'https://httpbin.org/status/500', 'whsec_test', ARRAY['ring.earned'], true)
            """
        ),
        {"id": webhook_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id, 'ring.earned', :user_id, '{"amount": 50}')
            """
        ),
        {"id": event_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES (:id, :webhook_id, :event_id, 'ring.earned', 'pending', 2, '{"amount": 50}', NOW())
            """
        ),
        {"id": delivery_id, "webhook_id": webhook_id, "event_id": event_id},
    )
    db.commit()

    # Deliver (3rd attempt, will fail and mark dead)
    success = await deliver_webhook(db, delivery_id)
    assert success is False

    # Check marked dead
    row = db.execute(
        text("SELECT status, attempts, next_attempt_at FROM webhook_deliveries WHERE id = :id"),
        {"id": delivery_id},
    ).fetchone()

    assert row[0] == "dead"
    assert row[1] == 3
    assert row[2] is None  # No next attempt


def test_get_pending_deliveries(db):
    """Test get_pending_deliveries returns due deliveries."""
    user_id = f"user_{uuid.uuid4()}"
    # Insert past-due and future-due deliveries
    webhook_id = str(uuid.uuid4())
    event_id_a = str(uuid.uuid4())
    event_id_b = str(uuid.uuid4())
    delivery_id_a = str(uuid.uuid4())
    delivery_id_b = str(uuid.uuid4())
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, :user_id, 'https://example.com', 'whsec_test', ARRAY['ring.earned'], true)
            """
        ),
        {"id": webhook_id, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id_a, 'ring.earned', :user_id, '{"amount": 10}'),
                   (:id_b, 'ring.earned', :user_id, '{"amount": 20}')
            """
        ),
        {"id_a": event_id_a, "id_b": event_id_b, "user_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, next_attempt_at, event_timestamp)
            VALUES (:delivery_a, :webhook_id, :event_a, 'ring.earned', 'pending', 0, '{}', NOW() - INTERVAL '1 hour', NOW()),
                   (:delivery_b, :webhook_id, :event_b, 'ring.earned', 'pending', 0, '{}', NOW() + INTERVAL '1 hour', NOW())
            """
        ),
        {"delivery_a": delivery_id_a, "delivery_b": delivery_id_b, "webhook_id": webhook_id, "event_a": event_id_a, "event_b": event_id_b},
    )
    db.commit()

    pending = get_pending_deliveries(db, limit=1000)
    assert delivery_id_a in pending
    assert delivery_id_b not in pending
