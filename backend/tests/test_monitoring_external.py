"""Tests for external API monitoring endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import get_db
from sqlalchemy import text


client = TestClient(app)


@pytest.fixture
def db():
    """Get test database session."""
    return next(get_db())


@pytest.fixture
def admin_key():
    """Return test admin key (set in env for tests)."""
    return "test_admin_key"


def test_monitoring_external_keys_unauthorized(db):
    """Test monitoring endpoint requires admin key."""
    response = client.get("/v1/monitoring/external/keys")
    assert response.status_code == 401


def test_monitoring_external_keys_metrics(db, admin_key):
    """Test external keys metrics endpoint."""
    # Seed test data
    db.execute(
        text(
            """
            INSERT INTO external_api_keys (key_id, key_hash, owner_user_id, scopes, rate_limit_tier, is_active)
            VALUES ('osk_test1', '$2b$12$test1', 'user1', ARRAY['read:rings'], 'free', true),
                   ('osk_test2', '$2b$12$test2', 'user2', ARRAY['read:rings'], 'pro', true),
                   ('osk_test3', '$2b$12$test3', 'user3', ARRAY['read:rings'], 'free', false)
            """
        )
    )
    db.commit()

    response = client.get(
        "/v1/monitoring/external/keys",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_active"] == 2
    assert data["total_revoked"] == 1
    assert len(data["totals"]) >= 1


def test_monitoring_webhooks_metrics(db, admin_key):
    """Test webhook metrics endpoint."""
    # Seed webhook deliveries
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_mon1', 'user1', 'https://example.com', 'whsec_test', ARRAY['draft.published'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_mon1', 'draft.published', 'user1', '{}'),
                   ('evt_mon2', 'ring.earned', 'user1', '{}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES ('del_mon1', 'wh_mon1', 'evt_mon1', 'draft.published', 'succeeded', 1, '{}', NOW()),
                   ('del_mon2', 'wh_mon1', 'evt_mon2', 'ring.earned', 'pending', 0, '{}', NOW()),
                   ('del_mon3', 'wh_mon1', 'evt_mon1', 'draft.published', 'dead', 3, '{}', NOW())
            """
        )
    )
    db.commit()

    response = client.get(
        "/v1/monitoring/webhooks/metrics",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["delivered"] == 1
    assert data["pending"] == 1
    assert data["dead"] == 1


def test_monitoring_webhooks_recent(db, admin_key):
    """Test recent webhook deliveries endpoint."""
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_rec1', 'user1', 'https://example.com', 'whsec_test', ARRAY['draft.published'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_rec1', 'draft.published', 'user1', '{}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp, last_status_code)
            VALUES ('del_rec1', 'wh_rec1', 'evt_rec1', 'draft.published', 'succeeded', 1, '{}', NOW(), 200)
            """
        )
    )
    db.commit()

    response = client.get(
        "/v1/monitoring/webhooks/recent?limit=10",
        headers={"X-Admin-Key": admin_key},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["id"] == "del_rec1"
    assert data["deliveries"][0]["status"] == "succeeded"
    assert data["deliveries"][0]["last_status_code"] == 200


def test_monitoring_webhooks_recent_filters(db, admin_key):
    """Test recent deliveries with status and event_type filters."""
    db.execute(
        text(
            """
            INSERT INTO external_webhooks (id, owner_user_id, url, secret, events, is_active)
            VALUES ('wh_filter1', 'user1', 'https://example.com', 'whsec_test', ARRAY['draft.published', 'ring.earned'], true)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_events (id, event_type, user_id, payload)
            VALUES ('evt_filter1', 'draft.published', 'user1', '{}'),
                   ('evt_filter2', 'ring.earned', 'user1', '{}')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO webhook_deliveries (id, webhook_id, event_id, event_type, status, attempts, payload, event_timestamp)
            VALUES ('del_filter1', 'wh_filter1', 'evt_filter1', 'draft.published', 'failed', 1, '{}', NOW()),
                   ('del_filter2', 'wh_filter1', 'evt_filter2', 'ring.earned', 'succeeded', 1, '{}', NOW())
            """
        )
    )
    db.commit()

    # Filter by status=failed
    response = client.get(
        "/v1/monitoring/webhooks/recent?status=failed",
        headers={"X-Admin-Key": admin_key},
    )
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["status"] == "failed"

    # Filter by event_type=ring.earned
    response = client.get(
        "/v1/monitoring/webhooks/recent?event_type=ring.earned",
        headers={"X-Admin-Key": admin_key},
    )
    data = response.json()
    assert len(data["deliveries"]) == 1
    assert data["deliveries"][0]["event_type"] == "ring.earned"
