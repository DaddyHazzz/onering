"""Tests for external API monitoring endpoints."""
import pytest
import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import get_db
from sqlalchemy import text


client = TestClient(app)


@pytest.fixture
def db():
    """Get test database session."""
    session = next(get_db())
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                event_type TEXT NOT NULL,
                user_id TEXT NULL,
                payload JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    session.commit()
    return session


@pytest.fixture
def admin_key(monkeypatch):
    """Return test admin key (set in env for tests)."""
    key = "test_admin_key"
    monkeypatch.setenv("ADMIN_API_KEY", key)
    return key


def test_monitoring_external_keys_unauthorized(db):
    """Test monitoring endpoint requires admin key."""
    response = client.get("/v1/monitoring/external/keys")
    assert response.status_code == 401


def test_monitoring_external_keys_metrics(db, admin_key):
    """Test external keys metrics endpoint."""
    baseline = client.get(
        "/v1/monitoring/external/keys",
        headers={"X-Admin-Key": admin_key},
    ).json()
    baseline_active = baseline["total_active"]
    baseline_revoked = baseline["total_revoked"]

    key_id_a = f"osk_{uuid.uuid4().hex[:12]}"
    key_id_b = f"osk_{uuid.uuid4().hex[:12]}"
    key_id_c = f"osk_{uuid.uuid4().hex[:12]}"
    # Seed test data
    db.execute(
        text(
            """
            INSERT INTO external_api_keys (key_id, key_hash, owner_user_id, scopes, rate_limit_tier, is_active)
            VALUES (:key_a, '$2b$12$test1', 'user1', ARRAY['read:rings'], 'free', true),
                   (:key_b, '$2b$12$test2', 'user2', ARRAY['read:rings'], 'pro', true),
                   (:key_c, '$2b$12$test3', 'user3', ARRAY['read:rings'], 'free', false)
            """
        ),
        {"key_a": key_id_a, "key_b": key_id_b, "key_c": key_id_c},
    )
    db.commit()

    response = client.get(
        "/v1/monitoring/external/keys",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_active"] >= baseline_active + 2
    assert data["total_revoked"] >= baseline_revoked + 1
    assert len(data["totals"]) >= 1


def test_monitoring_webhooks_metrics(db, admin_key):
    """Test webhook metrics endpoint."""
    baseline = client.get(
        "/v1/monitoring/webhooks/metrics",
        headers={"X-Admin-Key": admin_key},
    ).json()
    webhook_id = str(uuid.uuid4())
    event_id_a = str(uuid.uuid4())
    event_id_b = str(uuid.uuid4())
    delivery_a = str(uuid.uuid4())
    delivery_b = str(uuid.uuid4())
    delivery_c = str(uuid.uuid4())
    # Seed webhook deliveries
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, 'user1', 'https://example.com', 'whsec_test', ARRAY['draft.published'], true)
            """
        ),
        {"id": webhook_id},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id_a, 'draft.published', 'user1', '{}'),
                   (:id_b, 'ring.earned', 'user1', '{}')
            """
        ),
        {"id_a": event_id_a, "id_b": event_id_b},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload)
            VALUES (:del_a, :wh, :evt_a, 'draft.published', 'succeeded', 1, '{}'),
                   (:del_b, :wh, :evt_b, 'ring.earned', 'pending', 0, '{}'),
                   (:del_c, :wh, :evt_a, 'draft.published', 'dead', 3, '{}')
            """
        ),
        {"del_a": delivery_a, "del_b": delivery_b, "del_c": delivery_c, "wh": webhook_id, "evt_a": event_id_a, "evt_b": event_id_b},
    )
    db.commit()

    response = client.get(
        "/v1/monitoring/webhooks/metrics",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["delivered"] >= baseline["delivered"] + 1
    assert data["pending"] >= baseline["pending"] + 1
    assert data["dead"] >= baseline["dead"] + 1


def test_monitoring_webhooks_recent(db, admin_key):
    """Test recent webhook deliveries endpoint."""
    webhook_id = str(uuid.uuid4())
    event_id = str(uuid.uuid4())
    delivery_id = str(uuid.uuid4())
    event_type = f"draft.published.{uuid.uuid4().hex[:6]}"
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, 'user1', 'https://example.com', 'whsec_test', ARRAY[:event_type], true)
            """
        ),
        {"id": webhook_id, "event_type": event_type},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id, :event_type, 'user1', '{}')
            """
        ),
        {"id": event_id, "event_type": event_type},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload)
            VALUES (:id, :webhook_id, :event_id, :event_type, 'succeeded', 1, '{}')
            """
        ),
        {"id": delivery_id, "webhook_id": webhook_id, "event_id": event_id, "event_type": event_type},
    )
    db.commit()

    response = client.get(
        f"/v1/monitoring/webhooks/recent?limit=10&event_type={event_type}",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["id"] == delivery_id
    assert data["deliveries"][0]["status"] == "succeeded"


def test_monitoring_webhooks_recent_filters(db, admin_key):
    """Test recent deliveries with status and event_type filters."""
    webhook_id = str(uuid.uuid4())
    event_id_failed = str(uuid.uuid4())
    event_id_ok = str(uuid.uuid4())
    delivery_failed = str(uuid.uuid4())
    delivery_ok = str(uuid.uuid4())
    event_type_failed = f"draft.published.{uuid.uuid4().hex[:6]}"
    event_type_ok = f"ring.earned.{uuid.uuid4().hex[:6]}"
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES (:id, 'user1', 'https://example.com', 'whsec_test', ARRAY[:event_type_failed, :event_type_ok], true)
            """
        ),
        {"id": webhook_id, "event_type_failed": event_type_failed, "event_type_ok": event_type_ok},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES (:id_failed, :event_type_failed, 'user1', '{}'),
                   (:id_ok, :event_type_ok, 'user1', '{}')
            """
        ),
        {"id_failed": event_id_failed, "id_ok": event_id_ok, "event_type_failed": event_type_failed, "event_type_ok": event_type_ok},
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload)
            VALUES (:del_failed, :webhook_id, :event_failed, :event_type_failed, 'failed', 1, '{}'),
                   (:del_ok, :webhook_id, :event_ok, :event_type_ok, 'succeeded', 1, '{}')
            """
        ),
        {
            "del_failed": delivery_failed,
            "del_ok": delivery_ok,
            "webhook_id": webhook_id,
            "event_failed": event_id_failed,
            "event_ok": event_id_ok,
            "event_type_failed": event_type_failed,
            "event_type_ok": event_type_ok,
        },
    )
    db.commit()

    # Filter by status=failed
    response = client.get(
        f"/v1/monitoring/webhooks/recent?status=failed&event_type={event_type_failed}",
        headers={"X-Admin-Key": admin_key},
    )
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["status"] == "failed"

    # Filter by event_type=ring.earned
    response = client.get(
        f"/v1/monitoring/webhooks/recent?event_type={event_type_ok}",
        headers={"X-Admin-Key": admin_key},
    )
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["event_type"] == event_type_ok
