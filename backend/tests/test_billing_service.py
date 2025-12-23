"""
Test billing service (Phase 4.3).

Tests with mocked Stripe provider (no real API calls).
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from backend.features.billing.service import (
    ensure_customer_for_user,
    start_checkout,
    start_portal,
    apply_subscription_state,
    get_billing_status,
)
from backend.features.billing.provider import BillingProviderError
from backend.core.database import get_db_session, billing_customers, billing_subscriptions, user_plans, users
from sqlalchemy import select, delete, insert


@pytest.fixture
def create_test_user():
    """Create a test user for billing tests."""
    with get_db_session() as session:
        # Check if users exist first
        existing = session.execute(
            select(users.c.user_id).where(users.c.user_id == "user_alice")
        ).fetchone()
        
        if not existing:
            # Create user_alice
            session.execute(
                insert(users).values(
                    user_id="user_alice",
                    display_name="Alice",
                    status="active",
                )
            )
        
        existing_bob = session.execute(
            select(users.c.user_id).where(users.c.user_id == "user_bob")
        ).fetchone()
        
        if not existing_bob:
            # Create user_bob
            session.execute(
                insert(users).values(
                    user_id="user_bob",
                    display_name="Bob",
                    status="active",
                )
            )
        session.commit()
    yield
    # Cleanup handled by reset_db


@pytest.fixture
def mock_stripe_provider():
    """Mock Stripe provider for testing."""
    with patch("backend.features.billing.service.StripeProvider") as mock:
        instance = Mock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def clean_billing_tables():
    """Clean billing tables before each test."""
    with get_db_session() as session:
        session.execute(delete(billing_subscriptions))
        session.execute(delete(billing_customers))
        session.commit()
    yield
    with get_db_session() as session:
        session.execute(delete(billing_subscriptions))
        session.execute(delete(billing_customers))
        session.commit()


def test_ensure_customer_creates_new_customer(mock_stripe_provider, clean_billing_tables, create_test_user, monkeypatch):
    """ensure_customer_for_user should create new customer if not exists."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    mock_stripe_provider.ensure_customer.return_value = "cus_test123"
    
    result = ensure_customer_for_user("user_alice")
    
    assert result == "cus_test123"
    mock_stripe_provider.ensure_customer.assert_called_once_with("user_alice", None, None)
    
    # Verify stored in database
    with get_db_session() as session:
        row = session.execute(
            select(billing_customers).where(billing_customers.c.user_id == "user_alice")
        ).fetchone()
        assert row is not None
        assert row.stripe_customer_id == "cus_test123"


def test_ensure_customer_returns_existing_customer(mock_stripe_provider, clean_billing_tables, create_test_user, monkeypatch):
    """ensure_customer_for_user should return existing customer if already created."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    # Create customer first
    mock_stripe_provider.ensure_customer.return_value = "cus_test123"
    result1 = ensure_customer_for_user("user_alice")
    
    # Call again - should not call provider again
    mock_stripe_provider.ensure_customer.reset_mock()
    result2 = ensure_customer_for_user("user_alice")
    
    assert result1 == result2
    mock_stripe_provider.ensure_customer.assert_not_called()


def test_start_checkout_creates_session(mock_stripe_provider, clean_billing_tables, create_test_user, monkeypatch):
    """start_checkout should create checkout session."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_PRICE_CREATOR", "price_creator123")
    
    mock_stripe_provider.ensure_customer.return_value = "cus_test123"
    mock_stripe_provider.create_checkout_session.return_value = "https://checkout.stripe.com/session123"
    
    result = start_checkout(
        user_id="user_alice",
        plan_id="creator",
        success_url="http://example.com/success",
        cancel_url="http://example.com/cancel",
    )
    
    assert result == "https://checkout.stripe.com/session123"
    mock_stripe_provider.create_checkout_session.assert_called_once()


def test_start_checkout_raises_on_invalid_plan(mock_stripe_provider, monkeypatch):
    """start_checkout should raise ValueError if plan not mapped to Stripe price."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    # Don't set STRIPE_PRICE_CREATOR
    
    with pytest.raises(ValueError, match="No Stripe price configured"):
        start_checkout(
            user_id="user_alice",
            plan_id="creator",
            success_url="http://example.com/success",
            cancel_url="http://example.com/cancel",
        )


def test_start_portal_creates_session(mock_stripe_provider, clean_billing_tables, create_test_user, monkeypatch):
    """start_portal should create portal session."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    # Pre-create customer
    with get_db_session() as session:
        session.execute(
            billing_customers.insert().values(
                user_id="user_alice",
                stripe_customer_id="cus_test123",
            )
        )
        session.commit()
    
    mock_stripe_provider.create_portal_session.return_value = "https://billing.stripe.com/portal123"
    
    result = start_portal(user_id="user_alice", return_url="http://example.com")
    
    assert result == "https://billing.stripe.com/portal123"
    mock_stripe_provider.create_portal_session.assert_called_once_with(
        customer_id="cus_test123",
        return_url="http://example.com",
    )


def test_start_portal_returns_none_if_no_customer(mock_stripe_provider, clean_billing_tables, monkeypatch):
    """start_portal should return None if customer doesn't exist."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    result = start_portal(user_id="user_alice", return_url="http://example.com")
    
    assert result is None


def test_apply_subscription_state_creates_subscription(clean_billing_tables, create_test_user, reset_db):
    """apply_subscription_state should create new subscription."""
    period_end = datetime.utcnow() + timedelta(days=30)
    
    apply_subscription_state(
        user_id="user_alice",
        stripe_subscription_id="sub_test123",
        plan_id="creator",
        status="active",
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    
    with get_db_session() as session:
        sub = session.execute(
            select(billing_subscriptions).where(
                billing_subscriptions.c.stripe_subscription_id == "sub_test123"
            )
        ).fetchone()
        
        assert sub is not None
        assert sub.user_id == "user_alice"
        assert sub.plan_id == "creator"
        assert sub.status == "active"


def test_apply_subscription_state_updates_user_plan(clean_billing_tables, create_test_user, reset_db):
    """apply_subscription_state should sync user_plans when active."""
    apply_subscription_state(
        user_id="user_alice",
        stripe_subscription_id="sub_test123",
        plan_id="creator",
        status="active",
        current_period_end=None,
        cancel_at_period_end=False,
    )
    
    with get_db_session() as session:
        user_plan = session.execute(
            select(user_plans).where(user_plans.c.user_id == "user_alice")
        ).fetchone()
        
        assert user_plan is not None
        assert user_plan.plan_id == "creator"


def test_apply_subscription_state_idempotent(clean_billing_tables, create_test_user, reset_db):
    """apply_subscription_state should be idempotent (safe to call multiple times)."""
    period_end = datetime.utcnow() + timedelta(days=30)
    
    # Call twice with same data
    apply_subscription_state(
        user_id="user_alice",
        stripe_subscription_id="sub_test123",
        plan_id="creator",
        status="active",
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    
    apply_subscription_state(
        user_id="user_alice",
        stripe_subscription_id="sub_test123",
        plan_id="creator",
        status="active",
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    
    with get_db_session() as session:
        count = session.execute(
            select(billing_subscriptions).where(
                billing_subscriptions.c.stripe_subscription_id == "sub_test123"
            )
        ).fetchall()
        
        assert len(count) == 1  # Only one record


def test_get_billing_status_returns_active_subscription(clean_billing_tables, create_test_user, reset_db, monkeypatch):
    """get_billing_status should return active subscription."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    period_end = datetime.utcnow() + timedelta(days=30)
    
    with get_db_session() as session:
        session.execute(
            billing_subscriptions.insert().values(
                user_id="user_alice",
                stripe_subscription_id="sub_test123",
                plan_id="creator",
                status="active",
                current_period_end=period_end,
                cancel_at_period_end=False,
            )
        )
        session.commit()
    
    status = get_billing_status("user_alice")
    
    assert status["enabled"] is True
    assert status["plan_id"] == "creator"
    assert status["status"] == "active"
    assert status["period_end"] == period_end
    assert status["cancel_at_period_end"] is False


def test_get_billing_status_no_subscription(clean_billing_tables, monkeypatch):
    """get_billing_status should return no subscription if none exists."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    status = get_billing_status("user_alice")
    
    assert status["enabled"] is True
    assert status["plan_id"] is None
    assert status["status"] is None
