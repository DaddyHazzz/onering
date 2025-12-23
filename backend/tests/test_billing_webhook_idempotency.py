"""
Test billing webhook idempotency (Phase 4.3).

Verifies duplicate webhook events are not reprocessed.
"""
import pytest
import hashlib
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from backend.features.billing.service import process_webhook_event
from backend.features.billing.provider import BillingWebhookResult
from backend.core.database import get_db_session, billing_events, billing_subscriptions, users, plans
from sqlalchemy import select, delete, insert


@pytest.fixture
def create_test_users(reset_db):
    """Create test users for webhook tests. Depends on reset_db to ensure proper ordering."""
    # reset_db has already truncated all tables
    # Now create fresh test data: plans first, then users
    with get_db_session() as session:
        # Create plans (needed for foreign key constraints)
        session.execute(
            insert(plans).values(
                plan_id="free",
                name="Free Plan",
                is_default=True,
            )
        )
        session.execute(
            insert(plans).values(
                plan_id="creator",
                name="Creator Plan",
                is_default=False,
            )
        )
        session.execute(
            insert(plans).values(
                plan_id="team",
                name="Team Plan",
                is_default=False,
            )
        )
        # Create test users
        for user_id, display_name in [("user_alice", "Alice"), ("user_bob", "Bob"), ("user_error", "Error User")]:
            session.execute(
                insert(users).values(
                    user_id=user_id,
                    display_name=display_name,
                    status="active",
                )
            )
        session.commit()
    yield


@pytest.fixture
def clean_billing_events():
    """Clean billing_events table."""
    with get_db_session() as session:
        session.execute(delete(billing_events))
        session.execute(delete(billing_subscriptions))
        session.commit()
    yield
    with get_db_session() as session:
        session.execute(delete(billing_events))
        session.execute(delete(billing_subscriptions))
        session.commit()


@pytest.fixture
def mock_webhook_provider():
    """Mock provider that returns webhook result."""
    with patch("backend.features.billing.service.get_provider") as mock_get:
        mock_provider = Mock()
        mock_get.return_value = mock_provider
        yield mock_provider


def test_webhook_idempotency_skips_duplicate_events(mock_webhook_provider, clean_billing_events, create_test_users, reset_db, monkeypatch):
    """process_webhook_event should skip events with duplicate stripe_event_id."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test123")
    
    headers = {"stripe-signature": "sig123"}
    body = b'{"id": "evt_test123", "type": "customer.subscription.updated"}'
    
    # Mock provider response
    webhook_result = BillingWebhookResult(
        event_id="evt_test123",
        event_type="customer.subscription.updated",
        user_id="user_alice",
        subscription_id="sub_test123",
        plan_id="creator",
        status="active",
        current_period_end=datetime.utcnow() + timedelta(days=30),
        cancel_at_period_end=False,
        metadata={},
    )
    mock_webhook_provider.handle_webhook.return_value = webhook_result
    
    # Process first time
    result1 = process_webhook_event(headers, body)
    assert result1.event_id == "evt_test123"
    
    # Verify event recorded
    with get_db_session() as session:
        event = session.execute(
            select(billing_events).where(
                billing_events.c.stripe_event_id == "evt_test123"
            )
        ).fetchone()
        assert event is not None
        assert event.processed is True
    
    # Process again (duplicate)
    result2 = process_webhook_event(headers, body)
    assert result2.event_id == "evt_test123"
    
    # Verify only one event record
    with get_db_session() as session:
        events = session.execute(
            select(billing_events).where(
                billing_events.c.stripe_event_id == "evt_test123"
            )
        ).fetchall()
        assert len(events) == 1


def test_webhook_payload_hash_computed(mock_webhook_provider, clean_billing_events, create_test_users, reset_db, monkeypatch):
    """process_webhook_event should compute and store payload hash."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test123")
    
    headers = {"stripe-signature": "sig123"}
    body = b'{"id": "evt_test456", "type": "customer.subscription.created"}'
    expected_hash = hashlib.sha256(body).hexdigest()
    
    webhook_result = BillingWebhookResult(
        event_id="evt_test456",
        event_type="customer.subscription.created",
        user_id="user_alice",
        subscription_id="sub_test456",
        plan_id="team",
        status="active",
        current_period_end=None,
        cancel_at_period_end=False,
        metadata={},
    )
    mock_webhook_provider.handle_webhook.return_value = webhook_result
    
    process_webhook_event(headers, body)
    
    with get_db_session() as session:
        event = session.execute(
            select(billing_events).where(
                billing_events.c.stripe_event_id == "evt_test456"
            )
        ).fetchone()
        assert event is not None
        assert event.payload_hash == expected_hash


def test_webhook_marks_event_as_processed(mock_webhook_provider, clean_billing_events, create_test_users, reset_db, monkeypatch):
    """process_webhook_event should mark event as processed after applying state."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test123")
    
    headers = {"stripe-signature": "sig123"}
    body = b'{"id": "evt_test789", "type": "customer.subscription.updated"}'
    
    webhook_result = BillingWebhookResult(
        event_id="evt_test789",
        event_type="customer.subscription.updated",
        user_id="user_bob",
        subscription_id="sub_test789",
        plan_id="creator",
        status="active",
        current_period_end=datetime.utcnow() + timedelta(days=30),
        cancel_at_period_end=False,
        metadata={},
    )
    mock_webhook_provider.handle_webhook.return_value = webhook_result
    
    process_webhook_event(headers, body)
    
    with get_db_session() as session:
        event = session.execute(
            select(billing_events).where(
                billing_events.c.stripe_event_id == "evt_test789"
            )
        ).fetchone()
        assert event is not None
        assert event.processed is True
        assert event.processed_at is not None


def test_webhook_stores_error_on_failure(mock_webhook_provider, clean_billing_events, create_test_users, reset_db, monkeypatch):
    """process_webhook_event should store error if applying state fails."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test123")
    
    headers = {"stripe-signature": "sig123"}
    body = b'{"id": "evt_test_error", "type": "customer.subscription.updated"}'
    
    # Mock result that will cause apply_subscription_state to fail
    # (e.g., invalid plan_id or database error)
    webhook_result = BillingWebhookResult(
        event_id="evt_test_error",
        event_type="customer.subscription.updated",
        user_id="user_error",
        subscription_id="sub_test_error",
        plan_id="invalid_plan",  # This might cause issues
        status="active",
        current_period_end=None,
        cancel_at_period_end=False,
        metadata={},
    )
    mock_webhook_provider.handle_webhook.return_value = webhook_result
    
    # Mock apply_subscription_state to raise error
    with patch("backend.features.billing.service.apply_subscription_state") as mock_apply:
        mock_apply.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            process_webhook_event(headers, body)
        
        # Verify error recorded
        with get_db_session() as session:
            event = session.execute(
                select(billing_events).where(
                    billing_events.c.stripe_event_id == "evt_test_error"
                )
            ).fetchone()
            assert event is not None
            assert event.processed is False
            assert "Database error" in event.error
