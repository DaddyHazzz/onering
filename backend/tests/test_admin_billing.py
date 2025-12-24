"""
Admin Billing Operations — End-to-end tests with real endpoint behavior.

Implements proper dependency override for DB session and checks:
- Admin auth gate (401 on missing/wrong key)
- Webhook replay semantics
- Event listing with pagination/filters
- Plan sync, entitlements override, grace period reset
- Reconciliation behavior
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Table, Column, String
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.models.billing import (
    BillingSubscription,
    BillingEvent,
    BillingGracePeriod,
    BillingAdminAudit,
    Base as BillingBase,
)

client = TestClient(app)


class TestAdminBillingAuth:
    """Test admin authentication gate."""
    
    def test_verify_admin_key_function_exists(self):
        """verify_admin_key function should exist in admin_billing module."""
        from backend.api.admin_billing import verify_admin_key
        assert callable(verify_admin_key)
    
    def test_admin_key_setting_exists(self):
        """ADMIN_KEY setting should be configurable."""
        from backend.core.config import settings
        # Should not raise AttributeError
        key = settings.ADMIN_KEY
        assert key is None or isinstance(key, str)


class TestAdminBillingModels:
    """Test that models are importable."""
    
    def test_billing_subscription_model_exists(self):
        """BillingSubscription model should be importable."""
        from backend.models.billing import BillingSubscription
        assert BillingSubscription is not None
    
    def test_billing_event_model_exists(self):
        """BillingEvent model should be importable."""
        from backend.models.billing import BillingEvent
        assert BillingEvent is not None
    
    def test_billing_grace_period_model_exists(self):
        """BillingGracePeriod model should be importable."""
        from backend.models.billing import BillingGracePeriod
        assert BillingGracePeriod is not None
    
    def test_billing_admin_audit_model_exists(self):
        """BillingAdminAudit model should be importable."""
        from backend.models.billing import BillingAdminAudit
        assert BillingAdminAudit is not None


class TestAdminBillingRouter:
    """Test that admin router is properly mounted."""
    
    def test_admin_routes_registered(self):
        """Admin billing routes should be registered in app."""
        routes = [route.path for route in app.routes]
        admin_routes = [r for r in routes if "/admin/billing/" in r]
        assert len(admin_routes) >= 4, f"Expected at least 4 admin routes, found {admin_routes}"
    
    def test_webhook_replay_route_registered(self):
        """Webhook replay route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/webhook/replay" in routes
    
    def test_events_listing_route_registered(self):
        """Events listing route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/events" in routes
    
    def test_plan_sync_route_registered(self):
        """Plan sync route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/plans/sync" in routes
    
    def test_entitlement_override_route_registered(self):
        """Entitlement override route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/entitlements/override" in routes
    
    def test_grace_period_reset_route_registered(self):
        """Grace period reset route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/grace-period/reset" in routes
    
    def test_reconcile_route_registered(self):
        """Reconciliation route should be registered."""
        routes = [route.path for route in app.routes]
        assert "/v1/admin/billing/reconcile" in routes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def orm_session():
    """Provide an isolated in-memory ORM session for admin billing tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Minimal stub for User table to satisfy FK constraints in billing models
    user_stub = Table(
        "user",
        BillingBase.metadata,
        Column("id", String, primary_key=True),
        extend_existing=True,
    )
    # Create tables individually with checkfirst to avoid duplicate index errors
    user_stub.create(bind=engine, checkfirst=True)
    # Avoid duplicate index creation for audit table in test metadata
    try:
        BillingAdminAudit.__table__.indexes.clear()
    except Exception:
        pass
    for model in [BillingSubscription, BillingEvent, BillingGracePeriod, BillingAdminAudit]:
        model.__table__.create(bind=engine, checkfirst=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def override_get_db(orm_session):
    """Override backend.core.database.get_db to use the ORM session for tests."""
    from backend.core.database import get_db

    def _override():
        try:
            yield orm_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_key():
    """Configure admin API key via environment for tests."""
    original_env = os.getenv("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = "test-admin-key-12345"
    yield os.environ["ADMIN_API_KEY"]
    if original_env is None:
        os.environ.pop("ADMIN_API_KEY", None)
    else:
        os.environ["ADMIN_API_KEY"] = original_env


@pytest.fixture
def mock_session(orm_session):
    """Expose the ORM session to tests for direct object manipulation."""
    return orm_session


# ============================================================================
# Schema Verification
# ============================================================================

def test_schema_billing_events_and_audit_tables_exist(mock_session):
    """Verify key columns exist for events and admin audit tables."""
    from sqlalchemy import inspect
    engine = mock_session.bind
    insp = inspect(engine)

    # Events table columns
    assert "billing_events" in insp.get_table_names()
    event_cols = {c['name'] for c in insp.get_columns("billing_events")}
    for col in [
        "id", "user_id", "event_type", "status", "created_at", "processed_at"
    ]:
        assert col in event_cols

    # Admin audit table columns (Phase 4.6.1 schema)
    assert "billing_admin_audit" in insp.get_table_names()
    audit_cols = {c['name'] for c in insp.get_columns("billing_admin_audit")}
    for col in [
        "id", "actor", "actor_id", "actor_type", "actor_email", "auth_mechanism", "action", "created_at"
    ]:
        assert col in audit_cols


# ============================================================================
# Tests: Admin Auth Gate
# ============================================================================

def test_admin_endpoint_requires_key(admin_key):
    """Admin endpoints should reject requests without X-Admin-Key header."""
    response = client.get("/v1/admin/billing/events")
    assert response.status_code == 401
    assert "admin_unauthorized" in response.json()["detail"]["code"]


def test_admin_endpoint_with_wrong_key(admin_key):
    """Admin endpoints should reject requests with wrong X-Admin-Key."""
    response = client.get(
        "/v1/admin/billing/events",
        headers={"X-Admin-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_admin_endpoint_with_correct_key(admin_key):
    """Admin endpoints should accept requests with correct X-Admin-Key."""
    response = client.get(
        "/v1/admin/billing/events",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code in (200, 204)


# ============================================================================
# Tests: Webhook Replay
# ============================================================================

def test_webhook_replay_not_found(admin_key):
    """Replaying non-existent webhook should return 404."""
    response = client.post(
        "/v1/admin/billing/webhook/replay",
        headers={"X-Admin-Key": admin_key},
        json={
            "event_id": "nonexistent-event-id",
            "force": False
        }
    )
    assert response.status_code == 404
    assert "Event not found" in response.json()["detail"]


def test_webhook_replay_already_processed_no_force(admin_key, mock_session):
    """Replaying processed webhook without force should return success without reprocessing."""
    # Create a processed event
    event = BillingEvent(
        user_id="user-123",
        event_type="checkout.session.completed",
        stripe_event_id="evt_test_12345",
        status="processed",
        processed_at=datetime.now(timezone.utc)
    )
    mock_session.add(event)
    mock_session.commit()
    
    response = client.post(
        "/v1/admin/billing/webhook/replay",
        headers={"X-Admin-Key": admin_key},
        json={
            "event_id": event.id,
            "force": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["reprocessed"] is False
    assert "already processed" in data["message"]


def test_webhook_replay_with_force(admin_key, mock_session):
    """Replaying with force=true should reprocess even if already processed."""
    # Create a processed event
    event = BillingEvent(
        user_id="user-123",
        event_type="checkout.session.completed",
        stripe_event_id="evt_test_12345",
        status="processed",
        processed_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    mock_session.add(event)
    mock_session.commit()
    original_processed_at = event.processed_at
    
    response = client.post(
        "/v1/admin/billing/webhook/replay",
        headers={"X-Admin-Key": admin_key},
        json={
            "event_id": event.id,
            "force": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["reprocessed"] is True
    
    # Verify event was reprocessed (processed_at updated)
    mock_session.refresh(event)
    assert event.processed_at > original_processed_at


# ============================================================================
# Tests: Event Listing
# ============================================================================

def test_list_events_empty(admin_key):
    """Listing events when none exist should return empty list."""
    response = client.get(
        "/v1/admin/billing/events",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["events"]) == 0
    assert data["has_more"] is False


def test_list_events_with_pagination(admin_key, mock_session):
    """Event listing should support pagination."""
    # Create multiple events
    for i in range(10):
        event = BillingEvent(
            user_id=f"user-{i}",
            event_type="checkout.session.completed",
            stripe_event_id=f"evt_test_{i}",
            status="processed" if i % 2 == 0 else "pending"
        )
        mock_session.add(event)
    mock_session.commit()
    
    # Get first page
    response = client.get(
        "/v1/admin/billing/events?skip=0&limit=5",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 10
    assert len(data["events"]) == 5
    assert data["has_more"] is True
    
    # Get second page
    response = client.get(
        "/v1/admin/billing/events?skip=5&limit=5",
        headers={"X-Admin-Key": admin_key}
    )
    data = response.json()
    assert len(data["events"]) == 5
    assert data["has_more"] is False


def test_list_events_filter_by_status(admin_key, mock_session):
    """Event listing should filter by status."""
    # Create events with different statuses
    for i in range(5):
        event = BillingEvent(
            user_id=f"user-{i}",
            event_type="checkout.session.completed",
            stripe_event_id=f"evt_test_{i}",
            status="pending"
        )
        mock_session.add(event)
    for i in range(3):
        event = BillingEvent(
            user_id=f"user-pending-{i}",
            event_type="subscription.updated",
            stripe_event_id=f"evt_processed_{i}",
            status="processed"
        )
        mock_session.add(event)
    mock_session.commit()
    
    # Filter for pending
    response = client.get(
        "/v1/admin/billing/events?status=pending",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert all(e["status"] == "pending" for e in data["events"])
    
    # Filter for processed
    response = client.get(
        "/v1/admin/billing/events?status=processed",
        headers={"X-Admin-Key": admin_key}
    )
    data = response.json()
    assert data["total"] == 3
    assert all(e["status"] == "processed" for e in data["events"])


def test_list_events_filter_by_user_id(admin_key, mock_session):
    """Event listing should filter by user_id."""
    # Create events for different users
    for i in range(3):
        event = BillingEvent(
            user_id="user-alice",
            event_type="checkout.session.completed",
            stripe_event_id=f"evt_alice_{i}",
            status="processed"
        )
        mock_session.add(event)
    for i in range(2):
        event = BillingEvent(
            user_id="user-bob",
            event_type="subscription.updated",
            stripe_event_id=f"evt_bob_{i}",
            status="processed"
        )
        mock_session.add(event)
    mock_session.commit()
    
    # Filter for alice
    response = client.get(
        "/v1/admin/billing/events?user_id=user-alice",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert all(e["user_id"] == "user-alice" for e in data["events"])


# ============================================================================
# Tests: Plan Sync
# ============================================================================

def test_plan_sync_not_found(admin_key):
    """Syncing plan for non-existent user should return success with no subscription."""
    response = client.post(
        "/v1/admin/billing/plans/sync",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "nonexistent-user",
            "force_update": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["subscription_id"] is None
    assert data["plan"] is None


def test_plan_sync_existing_subscription(admin_key, mock_session):
    """Syncing plan for user with subscription should return subscription data."""
    # Create subscription
    sub = BillingSubscription(
        user_id="user-123",
        plan="pro",
        status="active"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    response = client.post(
        "/v1/admin/billing/plans/sync",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "user-123",
            "force_update": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["subscription_id"] == sub.id
    assert data["plan"] == "pro"
    assert data["status"] == "active"


# ============================================================================
# Tests: Entitlement Override
# ============================================================================

def test_override_entitlements_creates_subscription(admin_key, mock_session):
    """Overriding entitlements for user without subscription should create it."""
    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "user-123",
            "credits": 1000,
            "plan": "pro"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user_id"] == "user-123"
    assert data["credits"] == 1000
    assert data["plan"] == "pro"
    assert "audit_id" in data
    
    # Verify subscription was created
    sub = mock_session.query(BillingSubscription).filter_by(user_id="user-123").first()
    assert sub is not None
    assert sub.credits == 1000
    assert sub.plan == "pro"
    
    # Verify audit entry was created
    audit = mock_session.query(BillingAdminAudit).filter_by(
        user_id="user-123",
        action="entitlement_override"
    ).first()
    assert audit is not None
    assert audit.target_credits == 1000
    assert audit.target_plan == "pro"


def test_override_entitlements_updates_existing(admin_key, mock_session):
    """Overriding entitlements for user with subscription should update it."""
    # Create existing subscription
    sub = BillingSubscription(
        user_id="user-123",
        plan="starter",
        credits=0,
        status="active"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "user-123",
            "credits": 5000,
            "plan": "enterprise"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["credits"] == 5000
    assert data["plan"] == "enterprise"
    
    # Verify subscription was updated
    mock_session.refresh(sub)
    assert sub.credits == 5000
    assert sub.plan == "enterprise"


def test_entitlement_override_fails_when_audit_fails(monkeypatch, admin_key):
    """Audit failure must bubble up with admin_audit_failed code (no silent swallow)."""
    from backend.api import admin_billing
    from backend.core.errors import AdminAuditWriteError

    def boom(*args, **kwargs):
        raise AdminAuditWriteError("forced audit failure")

    monkeypatch.setattr(admin_billing, "create_audit_log", boom)

    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers={"X-Admin-Key": admin_key},
        json={"user_id": "user-bad", "credits": 1, "plan": "starter"},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "admin_audit_failed"


# ============================================================================
# Tests: Grace Period Reset
# ============================================================================

def test_grace_period_reset_subscription_not_found(admin_key):
    """Resetting grace period for non-existent subscription should return 404."""
    response = client.post(
        "/v1/admin/billing/grace-period/reset",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "nonexistent-user",
            "days": 7
        }
    )
    assert response.status_code == 404


def test_grace_period_reset_creates_new_grace_period(admin_key, mock_session):
    """Resetting grace period should create new grace period record."""
    # Create subscription
    sub = BillingSubscription(
        user_id="user-123",
        plan="pro",
        status="past_due"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    response = client.post(
        "/v1/admin/billing/grace-period/reset",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "user-123",
            "days": 14
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user_id"] == "user-123"
    assert data["subscription_id"] == sub.id
    
    # Verify grace period was created
    grace = mock_session.query(BillingGracePeriod).filter_by(
        subscription_id=sub.id
    ).first()
    assert grace is not None
    expected_until = datetime.now(timezone.utc) + timedelta(days=14)
    # SQLite may return naive datetimes - make it aware if needed
    grace_until = grace.grace_until if grace.grace_until.tzinfo else grace.grace_until.replace(tzinfo=timezone.utc)
    assert abs((grace_until - expected_until).total_seconds()) < 60


def test_grace_period_reset_updates_existing(admin_key, mock_session):
    """Resetting grace period should update existing grace period."""
    # Create subscription and grace period
    sub = BillingSubscription(
        user_id="user-123",
        plan="pro",
        status="past_due"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    old_grace = BillingGracePeriod(
        subscription_id=sub.id,
        grace_until=datetime.now(timezone.utc)
    )
    mock_session.add(old_grace)
    mock_session.commit()
    original_id = old_grace.id
    
    response = client.post(
        "/v1/admin/billing/grace-period/reset",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": "user-123",
            "days": 30
        }
    )
    assert response.status_code == 200
    
    # Verify grace period was updated (same ID)
    grace = mock_session.query(BillingGracePeriod).filter_by(
        subscription_id=sub.id
    ).first()
    assert grace.id == original_id
    expected_until = datetime.now(timezone.utc) + timedelta(days=30)
    # SQLite may return naive datetimes - make it aware if needed
    grace_until = grace.grace_until if grace.grace_until.tzinfo else grace.grace_until.replace(tzinfo=timezone.utc)
    assert abs((grace_until - expected_until).total_seconds()) < 60


# ============================================================================
# Tests: Reconciliation
# ============================================================================

def test_reconcile_billing_no_issues(admin_key):
    """Reconciliation with no issues should return 0 issues."""
    response = client.get(
        "/v1/admin/billing/reconcile",
        headers={"X-Admin-Key": admin_key},
        params={"fix": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issues_found"] == 0
    assert len(data["mismatches"]) == 0
    assert data["corrections_applied"] == 0


def test_reconcile_billing_detect_invalid_status(admin_key, mock_session):
    """Reconciliation should detect subscriptions with invalid status."""
    # Create subscription with invalid status
    sub = BillingSubscription(
        user_id="user-123",
        plan="pro",
        status="invalid_status"  # Not in valid_statuses set
    )
    mock_session.add(sub)
    mock_session.commit()
    
    response = client.get(
        "/v1/admin/billing/reconcile",
        headers={"X-Admin-Key": admin_key},
        params={"fix": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["issues_found"] >= 1
    
    # Find the invalid status issue
    invalid_status_issues = [
        issue for issue in data["mismatches"]
        if issue.get("type") == "invalid_status"
    ]
    assert len(invalid_status_issues) > 0


def test_reconcile_billing_fix_invalid_status(admin_key, mock_session):
    """Reconciliation with fix=true should correct invalid statuses."""
    # Create subscription with invalid status
    sub = BillingSubscription(
        user_id="user-123",
        plan="pro",
        status="totally_invalid"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    response = client.get(
        "/v1/admin/billing/reconcile",
        headers={"X-Admin-Key": admin_key},
        params={"fix": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["corrections_applied"] >= 1
    
    # Verify status was fixed
    mock_session.refresh(sub)
    assert sub.status == "unpaid"


# ============================================================================
# Integration Tests
# ============================================================================

def test_admin_workflow_payment_recovery(admin_key, mock_session):
    """Test typical admin workflow: override entitlements, extend grace period."""
    user_id = "user-payment-recovery"
    
    # Step 1: Create subscription with past_due status
    sub = BillingSubscription(
        user_id=user_id,
        plan="pro",
        status="past_due"
    )
    mock_session.add(sub)
    mock_session.commit()
    
    # Step 2: Override entitlements to extend trial
    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": user_id,
            "credits": 100,
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        }
    )
    assert response.status_code == 200
    
    # Step 3: Extend grace period
    response = client.post(
        "/v1/admin/billing/grace-period/reset",
        headers={"X-Admin-Key": admin_key},
        json={
            "user_id": user_id,
            "days": 7
        }
    )
    assert response.status_code == 200
    
    # Verify final state
    grace = mock_session.query(BillingGracePeriod).filter_by(
        subscription_id=sub.id
    ).first()
    assert grace is not None
    # SQLite may return naive datetimes - make it aware if needed
    grace_until = grace.grace_until if grace.grace_until.tzinfo else grace.grace_until.replace(tzinfo=timezone.utc)
    assert grace_until > datetime.now(timezone.utc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
